"""CircuitPython-compatible scans include both permitted address endpoints."""

import pytest

import pslab.protocol as CP
from pslab.bus.busio import I2C
from pslab.connection import ConnectionHandler


class ScanningConnection(ConnectionHandler):
    """Interpret scan commands and return address-dependent firmware ACKs."""

    def __init__(self, responding_addresses):
        self.responding_addresses = responding_addresses
        self.pending = bytearray()
        self.probed = []
        self.stopped = []
        self.active = None

    def connect(self):
        """No physical connection is needed."""

    def disconnect(self):
        """No physical connection is needed."""

    def write(self, data):
        """Accumulate one firmware command."""
        self.pending.extend(data)
        return len(data)

    def read(self, numbytes):
        """Return the transport ACK with its I2C address response bit."""
        assert numbytes == 1
        assert self.pending[:1] == CP.I2C_HEADER
        command = bytes(self.pending[1:2])
        ack = 1
        if command == CP.I2C_START:
            assert self.active is None
            assert self.pending[2] & 1 == 0
            self.active = self.pending[2] >> 1
            self.probed.append(self.active)
            if self.active not in self.responding_addresses:
                ack |= 0x10
        elif command == CP.I2C_STOP:
            assert self.active is not None
            self.stopped.append(self.active)
            self.active = None
        else:
            assert command in (CP.I2C_INIT, CP.I2C_CONFIG)
        self.pending.clear()
        return bytes([ack])


@pytest.mark.parametrize(
    "responders", [{0x77}, {0x08}, {0x08, 0x76, 0x77}, set(), {0x07, 0x78}]
)
def test_scan_finds_devices_through_last_nonreserved_address(responders):
    wire = ScanningConnection(responders)
    bus = I2C(wire)
    assert bus.scan() == sorted(responders & set(range(0x08, 0x78)))
    assert wire.probed == list(range(0x08, 0x78))
    assert wire.stopped == wire.probed
    assert wire.active is None
    assert wire.pending == b""
