"""Test wireless transfers without a connected PSLab."""

import socket
from unittest.mock import Mock

import pytest

from pslab.connection.wlan import WLANHandler


@pytest.fixture
def handler():
    """Return a handler with a controlled socket."""
    device = WLANHandler()
    device.disconnect()
    device._sock = Mock()
    return device


@pytest.mark.parametrize("size", [10, 5000])
def test_write_partial_sends(handler, size):
    """Send every byte even when the socket accepts only part of a chunk."""
    received = bytearray()
    data = bytes(index % 256 for index in range(size))

    def send(chunk):
        count = min(len(chunk), 3)
        received.extend(chunk[:count])
        return count

    handler._sock.send.side_effect = send
    assert handler.write(data) == len(data)
    assert received == data


@pytest.mark.parametrize("prefix", [b"", b"abc"])
def test_read_closed_connection(handler, prefix):
    """Stop at EOF instead of retrying a closed socket indefinitely."""
    responses = [prefix] if prefix else []
    handler._sock.recv.side_effect = responses + [
        b"",
        AssertionError("Read continued after EOF"),
    ]
    with pytest.raises(ConnectionError):
        handler.read(10)


def test_write_closed_connection(handler):
    """Reject a zero-byte send instead of reporting a truncated transfer."""
    handler._sock.send.return_value = 0
    with pytest.raises(ConnectionError):
        handler.write(b"abc")


def test_socket_transfer(handler):
    """Exercise both directions over real connected sockets."""
    client, peer = socket.socketpair()
    with client, peer:
        client.settimeout(1)
        peer.settimeout(1)
        handler._sock = client
        peer.sendall(b"response")
        assert handler.read(8) == b"response"
        assert handler.write(b"request") == 7
        with peer.makefile("rb") as stream:
            assert stream.read(7) == b"request"


def test_empty_transfer(handler):
    """Zero-length transfers require no socket access."""
    assert handler.read(0) == b""
    assert handler.write(b"") == 0
    handler._sock.recv.assert_not_called()
    handler._sock.send.assert_not_called()
