"""Empty I2C reads must not consume sensor bytes or resize output buffers."""

import pytest

import pslab.protocol as CP
from pslab.bus.busio import I2C


class I2CConnection:
    """Record primitive commands and provide deterministic sensor bytes."""

    def __init__(self):
        self.commands = []
        self.bytes_read = 0

    def send_byte(self, value):
        """Record command and parameter bytes."""
        self.commands.append(value)

    def send_int(self, value):
        """Accept the constructor's bus frequency configuration."""
        assert 0 <= value <= 65535

    def get_ack(self):
        """Acknowledge commands and the addressed peripheral."""
        return 1

    def get_byte(self):
        """Return a distinct byte for each sensor read."""
        self.bytes_read += 1
        return 0x40 + self.bytes_read


@pytest.mark.parametrize("combined", [False, True])
@pytest.mark.parametrize("view", [False, True])
@pytest.mark.parametrize("initial, offset", [(b"", 0), (b"abc", 1)])
def test_empty_read_preserves_buffer_and_does_not_read_sensor(
    combined, view, initial, offset
):
    connection = I2CConnection()
    bus = I2C(connection)
    storage = bytearray(initial)
    output = memoryview(storage) if view else storage

    connection.commands.clear()

    with pytest.raises(ValueError, match="at least one byte"):
        if combined:
            bus.writeto_then_readfrom(
                0x40, b"\x10", output, in_start=offset, in_end=offset
            )
        else:
            bus.readfrom_into(0x40, output, start=offset, end=offset)

    assert storage == initial
    assert connection.bytes_read == 0
    assert CP.I2C_READ_MORE not in connection.commands
    assert CP.I2C_READ_END not in connection.commands
    assert connection.commands == []
    assert bus._running is False
    assert bus._mode is None


@pytest.mark.parametrize("combined", [False, True])
@pytest.mark.parametrize("count", [1, 3])
def test_nonempty_read_keeps_ack_nack_sequence_and_slice(combined, count):
    connection = I2CConnection()
    bus = I2C(connection)
    storage = bytearray(b"z" * (count + 2))

    if combined:
        bus.writeto_then_readfrom(0x40, b"\x10", storage, in_start=1, in_end=count + 1)
    else:
        bus.readfrom_into(0x40, storage, start=1, end=count + 1)

    assert storage == b"z" + bytes(range(0x41, 0x41 + count)) + b"z"
    assert connection.bytes_read == count
    assert connection.commands.count(CP.I2C_READ_MORE) == count - 1
    assert connection.commands.count(CP.I2C_READ_END) == 1
    assert connection.commands[-2:] == [CP.I2C_HEADER, CP.I2C_STOP]
