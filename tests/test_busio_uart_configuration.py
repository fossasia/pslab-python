"""Hardware-independent regressions for CircuitPython UART configuration."""

from unittest.mock import Mock, call

import pytest

import pslab.protocol as CP
from pslab.bus.busio import Parity, UART
from pslab.bus.uart import _UARTPrimitive
from pslab.connection import ConnectionHandler


@pytest.fixture
def device():
    """Provide a connection without opening a physical device."""
    connection = Mock(spec=ConnectionHandler)
    connection.version = "PSLab V6"
    return connection


@pytest.fixture(autouse=True)
def restore_uart_configuration():
    """Keep process-wide cached UART settings independent between cases."""
    brgval, mode = _UARTPrimitive._brgval, _UARTPrimitive._mode
    yield
    _UARTPrimitive._save_config(brgval, mode)


@pytest.mark.parametrize(
    "options, mode",
    [({}, 0), ({"bits": 9}, 6), ({"stop": 2}, 1), ({"bits": 9, "stop": 2}, 7)],
)
def test_uart_without_parity(device, options, mode):
    """Default and nine-bit UARTs encode no parity without an Enum value."""
    uart = UART(device, **options)

    assert device.send_byte.call_args_list == [
        call(CP.UART_2),
        call(CP.SET_BAUD),
        call(CP.UART_2),
        call(CP.SET_MODE),
        call(mode),
    ]
    device.send_int.assert_called_once_with(_UARTPrimitive._get_uart_brgval(9600))
    assert device.get_ack.call_count == 2
    assert uart.timeout == 1
    assert _UARTPrimitive._mode == (mode >> 1, mode & 1)


@pytest.mark.parametrize("parity", [Parity.EVEN, Parity.ODD])
@pytest.mark.parametrize("stop", [1, 2])
def test_uart_with_parity(device, parity, stop):
    """Supported parity options retain their existing mode encoding."""
    UART(device, parity=parity, stop=stop)

    assert device.send_byte.call_args_list[-3:] == [
        call(CP.UART_2),
        call(CP.SET_MODE),
        call((parity.value << 1) | (stop - 1)),
    ]
    assert _UARTPrimitive._mode == (parity.value, stop - 1)


def test_uart_without_parity_on_older_firmware(device):
    """No-parity construction retains the unsupported-mode fallback."""
    device.version = "PSLab V5"

    uart = UART(device, timeout=0.25)

    assert device.send_byte.call_args_list == [call(CP.UART_2), call(CP.SET_BAUD)]
    assert device.get_ack.call_count == 1
    assert uart.timeout == 0.25


@pytest.mark.parametrize("parity", [Parity.EVEN, Parity.ODD])
def test_nine_bit_uart_rejects_parity(device, parity):
    """The no-parity fix does not permit parity with nine data bits."""
    with pytest.raises(ValueError, match="Invalid parity"):
        UART(device, bits=9, parity=parity)

    assert device.send_byte.call_args_list == [call(CP.UART_2), call(CP.SET_BAUD)]
