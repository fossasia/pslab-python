"""Wireless interface for communicating with PSLab devices equiped with ESP8266."""

import socket

from pslab.connection.connection import ConnectionHandler


class WLANHandler(ConnectionHandler):
    """Interface for controlling a PSLab over WLAN.

    Paramaters
    ----------
    host : str, default 192.168.4.1
        Network address of the PSLab.
    port : int, default 80
    timeout : float, default 1 s
    """

    def __init__(
        self,
        host: str = "192.168.4.1",
        port: int = 80,
        timeout: float = 1.0,
    ) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.settimeout(timeout)

    @property
    def host(self) -> int:
        """Network address of the PSLab."""
        return self._host

    @property
    def port(self) -> int:
        """TCP port number."""
        return self._port

    @property
    def timeout(self) -> float:
        """Timeout in seconds."""
        return self._timeout

    @timeout.setter
    def timeout(self, value: float) -> None:
        self._sock.settimeout(value)

    def connect(self) -> None:
        """Connect to PSLab."""
        if self._sock.fileno() == -1:
            # Socket has been closed.
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.settimeout(self.timeout)

        self._sock.connect((self.host, self.port))

        try:
            self.get_version()
        except Exception:
            self._sock.close()
            raise

    def disconnect(self) -> None:
        """Disconnect from PSLab."""
        self._sock.close()

    def read(self, numbytes: int) -> bytes:
        """Read data over WLAN.

        Parameters
        ----------
        numbytes : int
            Number of bytes to read.

        Returns
        -------
        data : bytes
        """
        received = b""
        buf_size = 4096
        remaining = numbytes

        while remaining > 0:
            chunk = self._sock.recv(min(remaining, buf_size))
            received += chunk
            remaining -= len(chunk)

        return received

    def write(self, data: bytes) -> int:
        """Write data over WLAN.

        Parameters
        ----------
        data : bytes

        Returns
        -------
        numbytes : int
            Number of bytes written.
        """
        buf_size = 4096
        remaining = len(data)
        sent = 0

        while remaining > 0:
            chunk = data[sent : sent + min(remaining, buf_size)]
            sent += self._sock.send(chunk)
            remaining -= len(chunk)

        return sent

    def __repr__(self) -> str:  # noqa
        return f"{self.__class__.__name__}[{self.host}:{self.port}]"
