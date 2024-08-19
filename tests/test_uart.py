"""Tests for pslab.bus.uart.

The PSLab's logic analyzer is used to verify the function of the UART bus. Before
running the tests, connect:
    TxD2->LA1 | PGD2 -> LA1 (for v5)
    RxD2->SQ1 | PGC2 -> SQ1 (for v5)
"""

import pytest

from pslab.bus.uart import UART
from pslab.instrument.logic_analyzer import LogicAnalyzer
from pslab.instrument.waveform_generator import PWMGenerator
from pslab.serial_handler import SerialHandler

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
