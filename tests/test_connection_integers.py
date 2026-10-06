"""Integer responses must be complete before they are decoded."""

from unittest.mock import Mock

import pytest

from pslab.connection import SerialHandler
from pslab.connection.connection import FirmwareVersion


@pytest.fixture
def handler():
    """Return a serial handler without opening a physical device."""
    device = SerialHandler.__new__(SerialHandler)
    device._ser = Mock()
    return device


@pytest.mark.parametrize(
    "method,size", [("get_byte", 1), ("get_int", 2), ("get_long", 4)]
)
def test_integer_reads_reject_truncated_response(handler, method, size):
    for received in range(size):
        handler._ser.read.return_value = b"\x01" * received
        with pytest.raises(TimeoutError):
            getattr(handler, method)()
        handler._ser.read.assert_called_with(size)


@pytest.mark.parametrize(
    "method,size", [("get_byte", 1), ("get_int", 2), ("get_long", 4)]
)
@pytest.mark.parametrize("value", [0, 1, 255])
def test_integer_reads_decode_complete_response(handler, method, size, value):
    handler._ser.read.return_value = value.to_bytes(size, "little")
    assert getattr(handler, method)() == value
    handler._ser.read.assert_called_once_with(size)


@pytest.mark.parametrize("method,size", [("get_int", 2), ("get_long", 4)])
def test_integer_reads_preserve_little_endian_order(handler, method, size):
    data = bytes(range(1, size + 1))
    handler._ser.read.return_value = data
    assert getattr(handler, method)() == int.from_bytes(data, "little")


@pytest.mark.parametrize("received", [0, 1, 2])
def test_firmware_version_rejects_missing_component(handler, received):
    handler._ser.read.side_effect = [b"\x03", b"\x00", b"\x01"][:received] + [b""]
    with pytest.raises(TimeoutError):
        handler.get_firmware_version()


def test_firmware_version_preserves_zero_component(handler):
    handler._ser.read.side_effect = [b"\x03", b"\x00", b"\x01"]
    assert handler.get_firmware_version() == FirmwareVersion(3, 0, 1)
