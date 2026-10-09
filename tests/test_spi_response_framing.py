"""SPI response words and acknowledgement bytes stay separately framed."""

from io import BytesIO

import pytest

import pslab.protocol as CP
from pslab.bus.spi import SPISlave
from pslab.connection import ConnectionHandler


class ResponseStream(ConnectionHandler):
    """Byte-oriented transport with preloaded firmware response words."""

    def __init__(self, responses):
        self.responses = BytesIO(responses)
        self.writes = []
        self.read_sizes = []

    def connect(self):
        """No physical connection is needed."""

    def disconnect(self):
        """No physical connection is needed."""

    def read(self, numbytes):
        """Read bytes, including ACKs if the caller requests too many."""
        self.read_sizes.append(numbytes)
        return self.responses.read(numbytes)

    def write(self, data):
        """Record the exact command stream."""
        self.writes.append(data)
        return len(data)


@pytest.mark.parametrize("bits,word", [(8, CP.Byte), (16, CP.ShortInt)])
@pytest.mark.parametrize("operation", ["transfer", "read", "write"])
@pytest.mark.parametrize("bulk", [False, True])
def test_public_spi_operations_keep_word_and_ack_separate(bits, word, operation, bulk):
    values = [0x35, 0xA5] if bits == 8 else [0x1234, 0xFEDC]
    if not bulk:
        values = values[:1]
    wire = ResponseStream(b"".join(word.pack(value) + b"\x01" for value in values))
    slave = SPISlave(wire)
    method = getattr(slave, f"{operation}{bits}" + ("_bulk" if bulk else ""))
    if operation == "read":
        result = method(len(values)) if bulk else method()
    else:
        result = method(values if bulk else values[0])
    expected = values if bulk else values[0]
    assert result == (None if operation == "write" else expected)
    assert wire.responses.read() == b""
    assert wire.read_sizes == [size for _ in values for size in (word.size, 1)]
    assert wire.writes[:3] == [CP.SPI_HEADER, CP.START_SPI, b"\x07"]
    assert wire.writes[-3:] == [CP.SPI_HEADER, CP.STOP_SPI, b"\x07"]
    transmitted = (
        [b"\x00" * word.size] * len(values)
        if operation == "read"
        else [word.pack(value) for value in values]
    )
    command = CP.SEND_SPI8 if bits == 8 else CP.SEND_SPI16
    expected_payload = [
        part for value in transmitted for part in (CP.SPI_HEADER, command, value)
    ]
    assert wire.writes[3:-3] == expected_payload


@pytest.mark.parametrize("bits,word", [(8, CP.Byte), (16, CP.ShortInt)])
def test_sequential_spi_transfers_leave_the_next_reply_available(bits, word):
    values = [0x25, 0x37]
    wire = ResponseStream(b"".join(word.pack(value) + b"\x01" for value in values))
    slave = SPISlave(wire)
    transfer = getattr(slave, f"transfer{bits}")
    assert [transfer(0) for _ in values] == values
    assert wire.responses.read() == b""
