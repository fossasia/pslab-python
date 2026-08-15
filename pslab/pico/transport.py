"""SCPI transport helpers for PSLab Pico firmware."""

from __future__ import annotations

import socket
from typing import List, Optional, Tuple

import serial
from serial.tools import list_ports


class ScpiError(RuntimeError):
    """Raised when the device returns a SCPI error response."""


class ScpiTimeoutError(TimeoutError):
    """Raised when a SCPI response is not received before timeout."""


class PicoTransport:
    """Small byte-oriented transport interface used by :class:`ScpiClient`."""

    timeout: Optional[float]

    def connect(self) -> None:
        """Open the transport."""
        raise NotImplementedError

    def close(self) -> None:
        """Close the transport."""
        raise NotImplementedError

    def read(self, size: int) -> bytes:
        """Read up to ``size`` bytes."""
        raise NotImplementedError

    def readline(self) -> bytes:
        """Read one newline-terminated line."""
        raise NotImplementedError

    def write(self, data: bytes) -> int:
        """Write bytes to the device."""
        raise NotImplementedError

    def flush(self) -> None:
        """Flush pending output bytes if the backend supports it."""

    def reset_input_buffer(self) -> None:
        """Discard unread input bytes if the backend supports it."""


class PicoUsbTransport(PicoTransport):
    """USB CDC transport for PSLab Pico SCPI firmware."""

    USB_IDS = ((0xCAFE, 0x4010),)

    def __init__(
        self,
        port: Optional[str] = None,
        baudrate: int = 115200,
        timeout: Optional[float] = 2.0,
        serial_instance=None,
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self._serial = serial_instance

    @classmethod
    def find_ports(cls) -> List[str]:
        """Return candidate serial ports for PSLab Pico devices."""

        ports = []
        for port in list_ports.comports():
            if (port.vid, port.pid) in cls.USB_IDS:
                ports.append(port.device)
                continue
            if port.product and port.product.startswith("PSLab Pico"):
                ports.append(port.device)
        return ports

    @classmethod
    def find_port(cls) -> str:
        """Return the only detected PSLab Pico serial port."""

        ports = cls.find_ports()
        if not ports:
            raise ConnectionError("PSLab Pico USB CDC port not found.")
        if len(ports) > 1:
            raise ConnectionError(f"Multiple PSLab Pico ports found: {ports}")
        return ports[0]

    @property
    def is_open(self) -> bool:
        return bool(self._serial is not None and getattr(self._serial, "is_open", True))

    def connect(self) -> None:
        if self.is_open:
            return
        if self.port is None:
            self.port = self.find_port()
        self._serial = serial.Serial(
            self.port,
            baudrate=self.baudrate,
            timeout=self.timeout,
            write_timeout=self.timeout,
        )

    def close(self) -> None:
        if self._serial is not None:
            self._serial.close()

    def read(self, size: int) -> bytes:
        self.connect()
        return self._serial.read(size)

    def readline(self) -> bytes:
        self.connect()
        return self._serial.readline()

    def write(self, data: bytes) -> int:
        self.connect()
        return self._serial.write(data)

    def flush(self) -> None:
        if self._serial is not None:
            self._serial.flush()

    def reset_input_buffer(self) -> None:
        if self._serial is not None and hasattr(self._serial, "reset_input_buffer"):
            self._serial.reset_input_buffer()


class PicoWifiTransport(PicoTransport):
    """TCP transport for the ESP32-C3 PSLab Pico SCPI bridge."""

    DEFAULT_PORT = 5006

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        timeout: Optional[float] = 2.0,
    ) -> None:
        self.host = host
        self.port = int(port)
        self.timeout = timeout
        self._socket = None
        self._rx_buffer = bytearray()

    @property
    def is_open(self) -> bool:
        return self._socket is not None

    def connect(self) -> None:
        if self._socket is not None:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect((self.host, self.port))
        self._socket = sock

    def close(self) -> None:
        if self._socket is not None:
            self._socket.close()
            self._socket = None
        self._rx_buffer.clear()

    def read(self, size: int) -> bytes:
        if size < 0:
            raise ValueError("size must be non-negative.")
        if size == 0:
            return b""

        self.connect()
        while len(self._rx_buffer) < size:
            try:
                chunk = self._socket.recv(size - len(self._rx_buffer))
            except socket.timeout as exc:
                raise ScpiTimeoutError("Timed out waiting for SCPI TCP data.") from exc
            if not chunk:
                raise ScpiTimeoutError("SCPI TCP connection closed.")
            self._rx_buffer.extend(chunk)
        data = bytes(self._rx_buffer[:size])
        del self._rx_buffer[:size]
        return data

    def readline(self) -> bytes:
        self.connect()
        while b"\n" not in self._rx_buffer:
            try:
                chunk = self._socket.recv(4096)
            except socket.timeout as exc:
                raise ScpiTimeoutError("Timed out waiting for SCPI TCP line.") from exc
            if not chunk:
                raise ScpiTimeoutError("SCPI TCP connection closed.")
            self._rx_buffer.extend(chunk)
        end = self._rx_buffer.index(b"\n") + 1
        line = bytes(self._rx_buffer[:end])
        del self._rx_buffer[:end]
        return line

    def write(self, data: bytes) -> int:
        self.connect()
        self._socket.sendall(data)
        return len(data)

    def reset_input_buffer(self) -> None:
        self._rx_buffer.clear()


class ScpiClient:
    """Line-oriented SCPI client for PSLab Pico firmware."""

    def __init__(self, transport: PicoTransport) -> None:
        self.transport = transport

    def connect(self) -> None:
        self.transport.connect()

    def close(self) -> None:
        self.transport.close()

    def command(self, command: str) -> None:
        """Send a command that does not return a response."""

        if command.rstrip().endswith("?"):
            raise ValueError("Use query() or query_block() for SCPI queries.")
        self._write_line(command)

    def query(self, command: str) -> str:
        """Send a query and return one decoded response line."""

        self._write_line(command)
        line = self.transport.readline()
        if not line:
            raise ScpiTimeoutError(f"Timed out waiting for response to {command!r}.")
        return line.decode("ascii", errors="replace").strip()

    def query_block(self, command: str) -> bytes:
        """Send a query and return a SCPI definite-length block payload."""

        self._write_line(command)
        return self.read_block()

    def read_block(self) -> bytes:
        """Read one SCPI definite-length arbitrary block payload."""

        marker = self._read_exact(1)
        if marker != b"#":
            rest = self.transport.readline()
            message = (marker + rest).decode("ascii", errors="replace").strip()
            raise ScpiError(message)

        digit_count_text = self._read_exact(1)
        try:
            digit_count = int(digit_count_text.decode("ascii"))
            byte_count = int(self._read_exact(digit_count).decode("ascii"))
        except ValueError as exc:
            raise ScpiError("Invalid SCPI arbitrary block header.") from exc

        payload = self._read_exact(byte_count)
        self._drain_block_terminator()
        return payload

    def identify(self) -> str:
        """Return the firmware identification string."""

        return self.query("*IDN?")

    def reset(self) -> None:
        """Reset instrument state."""

        self.command("*RST")

    def clear_status(self) -> None:
        """Clear SCPI status/error state."""

        self.command("*CLS")

    def error_count(self) -> int:
        """Return the number of queued SCPI errors."""

        return int(self.query("SYST:ERR:COUN?").strip())

    def system_error(self) -> Tuple[int, str]:
        """Pop one SCPI error from the device error queue."""

        response = self.query("SYST:ERR?")
        code_text, _, message = response.partition(",")
        return int(code_text), message.strip().strip('"')

    def drain_errors(self) -> List[Tuple[int, str]]:
        """Pop all queued SCPI errors."""

        errors = []
        while True:
            error = self.system_error()
            errors.append(error)
            if error[0] == 0:
                return errors

    def set_transport(self, mode: str) -> None:
        """Select firmware capture transport: ``USB``, ``WIFI``, or ``AUTO``."""

        normalized = mode.strip().upper()
        if normalized not in ("USB", "WIFI", "WIRELESS", "AUTO"):
            raise ValueError("mode must be USB, WIFI, WIRELESS, or AUTO.")
        self.command(f"COMM:TRAN {normalized}")

    def get_transport(self) -> str:
        """Return selected firmware capture transport."""

        return self.query("COMM:TRAN?")

    def wifi_status(self) -> Tuple[bool, int, int, int]:
        """Return Wi-Fi transport counters.

        Returns
        -------
        effective, sent_frames, dropped_frames, timeouts
        """

        fields = self.query("COMM:WIFI:STAT?").split(",")
        if len(fields) != 4:
            raise ScpiError(f"Unexpected Wi-Fi status response: {fields!r}")
        return bool(int(fields[0])), int(fields[1]), int(fields[2]), int(fields[3])

    def _write_line(self, command: str) -> None:
        self.transport.write(command.encode("ascii") + b"\n")
        self.transport.flush()

    def _read_exact(self, size: int) -> bytes:
        data = self.transport.read(size)
        if len(data) != size:
            raise ScpiTimeoutError(f"Expected {size} bytes, received {len(data)}.")
        return data

    def _drain_block_terminator(self) -> None:
        try:
            char = self.transport.read(1)
        except TimeoutError:
            return
        if not char:
            return
        if char == b"\n":
            return
        if char == b"\r":
            try:
                next_char = self.transport.read(1)
            except TimeoutError:
                return
            if not next_char or next_char == b"\n":
                return
            raise ScpiError(
                f"Unexpected SCPI block terminator byte: {next_char!r}"
            )
        raise ScpiError(f"Unexpected SCPI block terminator byte: {char!r}")
