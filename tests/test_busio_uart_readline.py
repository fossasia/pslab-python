"""Exercise UART line framing with controlled firmware replies, without hardware."""

from collections import deque

import pytest

import pslab.bus.busio as busio
import pslab.protocol as CP
from pslab.bus.uart import _UARTPrimitive


class Clock:
    """Advance the read timeout only when the poller sleeps."""

    def __init__(self):
        self.now = 0.0

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class UARTTransport:
    """Answer actual UART status/read commands from a receive buffer."""

    version = "PSLab V6"

    def __init__(self, data):
        self.received = deque(data)
        self.command = []
        self.read_commands = []

    def send_byte(self, value):
        self.command.append(value)

    def send_int(self, value):
        self.command.append(value)

    def get_ack(self):
        self.command.clear()
        return 1

    def get_byte(self):
        command = tuple(self.command)
        self.read_commands.append(command)
        self.command.clear()
        assert command[0] == CP.UART_2
        if command[1] == CP.READ_UART2_STATUS:
            return int(bool(self.received))
        assert command[1] == CP.READ_BYTE
        return self.received.popleft()


@pytest.fixture
def uart_factory(monkeypatch):
    """Use an explicit parity to isolate reads from the constructor defect."""
    monkeypatch.setattr(busio, "time", Clock())
    monkeypatch.setattr(_UARTPrimitive, "_brgval", _UARTPrimitive._brgval)
    monkeypatch.setattr(_UARTPrimitive, "_mode", _UARTPrimitive._mode)

    def create(data):
        device = UARTTransport(data)
        uart = busio.UART(device, parity=busio.Parity.EVEN, timeout=0.03)
        return uart, device

    return create


@pytest.mark.parametrize("line", [b"\n", b"hello\n", b"hello\r\n", b"\x00\n"])
def test_readline_retains_terminator_without_consuming_next_line(uart_factory, line):
    uart, device = uart_factory(line + b"next\n")
    assert uart.readline() == line
    assert bytes(device.received) == b"next\n"
    assert device.read_commands.count((CP.UART_2, CP.READ_BYTE)) == len(line)


def test_successive_lines_distinguish_blank_line_from_timeout(uart_factory):
    uart, device = uart_factory(b"\nnext\nlast")
    assert uart.readline() == b"\n"
    assert uart.readline() == b"next\n"
    assert uart.readline() == b"last"
    assert uart.readline() is None
    assert not device.received


def test_readline_no_data_returns_none(uart_factory):
    uart, device = uart_factory(b"")
    assert uart.readline() is None
    assert all(command[1] == CP.READ_UART2_STATUS for command in device.read_commands)


def test_readline_returns_partial_line_on_timeout(uart_factory):
    uart, _ = uart_factory(b"partial\r")
    assert uart.readline() == b"partial\r"


def test_raw_read_retains_newline_and_respects_byte_limit(uart_factory):
    uart, device = uart_factory(b"x\nytail")
    assert uart.read(3) == b"x\ny"
    assert bytes(device.received) == b"tail"


def test_readinto_retains_newline_and_binary_data(uart_factory):
    uart, device = uart_factory(b"\n\x00atail")
    buffer = bytearray(3)
    assert uart.readinto(buffer) == 3
    assert buffer == b"\n\x00a"
    assert bytes(device.received) == b"tail"


def test_zero_length_read_does_not_touch_receive_buffer(uart_factory):
    uart, device = uart_factory(b"\n")
    assert uart.read(0) is None
    assert bytes(device.received) == b"\n"
    assert not device.read_commands
