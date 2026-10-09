"""WLAN timeout configuration tests without a physical PSLab device."""

import socket

import pytest

from pslab.connection.wlan import WLANHandler


@pytest.mark.parametrize("timeout", [0.25, 2.0, None])
def test_timeout_update_survives_reconnect(monkeypatch, timeout):
    """Keep the requested timeout on the current and replacement sockets."""
    monkeypatch.setattr(WLANHandler, "get_version", lambda self: "PSLab V6")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        handler = WLANHandler(host="127.0.0.1", port=server.getsockname()[1])

        try:
            handler.timeout = timeout
            assert handler._sock.gettimeout() == timeout

            handler.connect()
            connection, _ = server.accept()
            connection.close()
            handler.disconnect()

            handler.connect()
            connection, _ = server.accept()
            connection.close()
            assert handler._sock.gettimeout() == timeout
            assert handler.timeout == timeout
        finally:
            handler.disconnect()


@pytest.mark.parametrize("timeout", [0.25, 2.0, None])
def test_timeout_property_tracks_update(timeout):
    """Report the updated value consistently with the live socket."""
    handler = WLANHandler()

    try:
        handler.timeout = timeout
        assert handler._sock.gettimeout() == timeout
        assert handler.timeout == timeout
    finally:
        handler.disconnect()


@pytest.mark.parametrize("timeout, error", [(-1, ValueError), ("invalid", TypeError)])
def test_invalid_timeout_preserves_previous_value(timeout, error):
    """Reject an invalid value without changing the configured timeout."""
    handler = WLANHandler(timeout=0.5)

    try:
        with pytest.raises(error):
            handler.timeout = timeout

        assert handler.timeout == 0.5
        assert handler._sock.gettimeout() == 0.5
    finally:
        handler.disconnect()


def test_initial_timeout_matches_socket():
    """Expose the configured constructor timeout without an update."""
    handler = WLANHandler(timeout=0.5)

    try:
        assert handler.timeout == 0.5
        assert handler._sock.gettimeout() == 0.5
    finally:
        handler.disconnect()


def test_timeout_update_preserves_transfers(monkeypatch):
    """Keep normal transfers working after changing the timeout."""
    monkeypatch.setattr(WLANHandler, "get_version", lambda self: "PSLab V6")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        handler = WLANHandler(host="127.0.0.1", port=server.getsockname()[1])

        try:
            handler.timeout = 0.5
            handler.connect()
            connection, _ = server.accept()

            with connection:
                connection.settimeout(0.5)
                assert handler.write(b"PSLab") == 5
                with connection.makefile("rb") as response:
                    assert response.read(5) == b"PSLab"
                connection.sendall(b"OK")
                assert handler.read(2) == b"OK"
                assert handler.write(b"") == 0
                assert handler.read(0) == b""

            assert repr(handler) == f"WLANHandler[127.0.0.1:{handler.port}]"
        finally:
            handler.disconnect()


def test_failed_handshake_closes_socket(monkeypatch):
    """Preserve socket cleanup when the device handshake fails."""

    def fail_handshake(self):
        raise ConnectionError("Not a PSLab device")

    monkeypatch.setattr(WLANHandler, "get_version", fail_handshake)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.bind(("127.0.0.1", 0))
        server.listen()
        handler = WLANHandler(host="127.0.0.1", port=server.getsockname()[1])

        try:
            with pytest.raises(ConnectionError, match="Not a PSLab device"):
                handler.connect()

            connection, _ = server.accept()
            connection.close()
            assert handler._sock.fileno() == -1
        finally:
            handler.disconnect()
