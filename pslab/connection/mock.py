"""Mock connection handler for PSLab.

This module provides a minimal in-memory `ConnectionHandler` implementation for
use in tests and development without physical PSLab hardware.
"""

from __future__ import annotations
from collections import deque
import pslab.protocol as CP
from pslab.connection.connection import ConnectionHandler


class MockHandler(ConnectionHandler):
    """In-memory mock implementation of `ConnectionHandler`.

    The handler queues deterministic responses based on bytes written via
    `write()` so higher-level code can be exercised without an actual device.
    """

    def __init__(self, version: str = "PSLab V6 ", fw=(3, 0, 0)) -> None:
        self._rx = deque()  # bytes to be read
        self._tx = bytearray()  # bytes written by client
        self.version = version  # convenient attribute for callers
        self._fw = fw
        self._connected = False

    def connect(self) -> None:
        """Mark the handler as connected."""
        self._connected = True
        # Optional: validate the mock “device” by answering get_version
        # self.version = self.get_version()

    def disconnect(self) -> None:
        """Mark the handler as disconnected."""
        self._connected = False

    def read(self, numbytes: int) -> bytes:
        """Read bytes from the internal receive buffer.

        Parameters
        ----------
        numbytes : int
            Number of bytes to read.

        Returns
        -------
        bytes
            Bytes read from the receive buffer (may be shorter if insufficient data
            is available).
        """
        out = bytearray()
        while len(out) < numbytes and self._rx:
            out.append(self._rx.popleft())
        return bytes(out)

    def write(self, data: bytes) -> int:
        """Write bytes to the handler and queue any corresponding responses.

        Parameters
        ----------
        data : bytes
            Bytes written by the caller.

        Returns
        -------
        int
            Number of bytes written.
        """
        self._tx.extend(data)
        self._maybe_respond()
        return len(data)

    def _queue(self, payload: bytes) -> None:
        """Append bytes to the internal receive buffer.

        Parameters
        ----------
        payload : bytes
            Bytes to enqueue so they can be returned by `read()`.
        """
        self._rx.extend(payload)

    def _maybe_respond(self) -> None:
        """Inspect written bytes and enqueue protocol responses.

        This method implements minimal protocol handling for mock mode.
        When known command patterns are detected in the transmit buffer,
        corresponding response bytes are queued for later reads.
        """
        # Detect “CP.COMMON, <cmd>” patterns
        while len(self._tx) >= 2:
            if self._tx[0] != CP.COMMON:
                # Drop unknown leading bytes
                self._tx.pop(0)
                continue

            cmd = self._tx[1]

            # GET_VERSION: ConnectionHandler.get_version reads 9 bytes
            #  and checks b"PSLab"
            if cmd == CP.GET_VERSION:
                self._tx = self._tx[2:]
                self._queue(self.version.encode("utf-8")[:9].ljust(9, b" "))
                continue

            # GET_FW_VERSION: reads 3 bytes (major, minor, patch)
            if cmd == CP.GET_FW_VERSION:
                self._tx = self._tx[2:]
                major, minor, patch = self._fw
                self._queue(bytes([major, minor, patch]))
                continue

            # Unknown command under CP.COMMON: drop and stop
            break
