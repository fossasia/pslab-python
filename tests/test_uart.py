"""Tests for pslab.bus.uart.

The PSLab's logic analyzer is used to verify the function of the UART bus. Before
running the tests, connect:
    TxD2->LA1 | PGD2 -> LA1 (for v5)
    RxD2->SQ1 | PGC2 -> SQ1 (for v5)
"""

import pytest

from pslab import protocol as CP
from pslab.bus import busio
from pslab.bus.uart import UART
from pslab.instrument.logic_analyzer import LogicAnalyzer
from pslab.instrument.waveform_generator import PWMGenerator
from pslab.connection import SerialHandler

WRITE_DATA = 0x55
TXD2 = "LA1"
RXD2 = "SQ1"
PWM_FERQUENCY = UART._baudrate // 2
MICROSECONDS = 1e-6
RELTOL = 0.05
# Number of expected logic level changes.
TXD_START = 1
TXD_WRITE_DATA = 8  # if LSB is 1
TXD_STOP = 1  # if data MSB is 0


@pytest.fixture
def uart(handler: SerialHandler) -> UART:
    return UART(device=handler)


@pytest.fixture
def la(handler: SerialHandler) -> LogicAnalyzer:
    return LogicAnalyzer(handler)


@pytest.fixture
def pwm(handler: SerialHandler) -> None:
    pwm = PWMGenerator(handler)
    pwm.generate(RXD2, PWM_FERQUENCY, 0.5)


def test_configure(la: LogicAnalyzer, uart: UART):
    baudrate = 1000000
    uart.configure(baudrate)
    la.capture(1, block=False)
    uart.write_byte(WRITE_DATA)
    la.stop()
    (txd2,) = la.fetch_data()
    start_to_stop = 9
    period = (txd2[-1] - txd2[0]) / start_to_stop

    assert (period * MICROSECONDS) ** -1 == pytest.approx(baudrate, rel=RELTOL)


def test_write_byte(la: LogicAnalyzer, uart: UART):
    la.capture(1, block=False)
    uart.write_byte(WRITE_DATA)
    la.stop()
    (txd2,) = la.fetch_data()

    assert len(txd2) == (TXD_START + TXD_WRITE_DATA + TXD_STOP)


def test_write_int(la: LogicAnalyzer, uart: UART):
    la.capture(1, block=False)
    uart.write_int((WRITE_DATA << 8) | WRITE_DATA)
    la.stop()
    (txd2,) = la.fetch_data()

    assert len(txd2) == 2 * (TXD_START + TXD_WRITE_DATA + TXD_STOP)


def test_read_byte(pwm: PWMGenerator, uart: UART):
    value = uart.read_byte()

    assert value in (0x55, 0xAA)


def test_read_int(pwm: PWMGenerator, uart: UART):
    value = uart.read_int()

    assert value in (0x5555, 0x55AA, 0xAA55, 0xAAAA)


class _FakeUARTDevice:
    """Mock connection handler providing scripted byte streams for UART tests."""

    def __init__(self, stream: bytes = b""):
        self.stream = list(stream)
        self.version = "PSLab V5"
        self._last_cmd = None

    def send_byte(self, val):
        self._last_cmd = val

    def send_int(self, val):
        pass

    def get_ack(self):
        return b"\x00"

    def get_byte(self) -> int:
        if self._last_cmd == CP.READ_UART2_STATUS:
            return 1 if self.stream else 0
        if self._last_cmd == CP.READ_BYTE and self.stream:
            return self.stream.pop(0)
        return 0


def _make_uart(device: _FakeUARTDevice, timeout: float = 0.1) -> busio.UART:
    """Helper to initialize a UART instance for read testing without hardware setup."""
    uart = busio.UART.__new__(busio.UART)
    uart._device = device
    uart._timeout = timeout
    return uart


def test_busio_uart_readline_preserves_newline():
    device = _FakeUARTDevice(b"hello\r\n")
    uart = _make_uart(device)
    assert uart.readline() == b"hello\r\n"


def test_busio_uart_readline_blank_line():
    device = _FakeUARTDevice(b"\n")
    uart = _make_uart(device)
    assert uart.readline() == b"\n"


def test_busio_uart_readline_successive_lines():
    device = _FakeUARTDevice(b"first\r\nsecond\n")
    uart = _make_uart(device)
    assert uart.readline() == b"first\r\n"
    assert uart.readline() == b"second\n"


def test_busio_uart_readline_timeout_empty():
    device = _FakeUARTDevice(b"")
    uart = _make_uart(device, timeout=0.05)
    assert uart.readline() is None


def test_busio_uart_readline_timeout_partial():
    device = _FakeUARTDevice(b"partial")
    uart = _make_uart(device, timeout=0.05)
    assert uart.readline() == b"partial"


def test_busio_uart_read_nbytes():
    device = _FakeUARTDevice(b"12345678")
    uart = _make_uart(device)
    assert uart.read(4) == b"1234"

