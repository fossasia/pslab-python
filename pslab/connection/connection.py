"""Interface objects common to all types of connections."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

import pslab.protocol as CP


@dataclass(frozen=True)
class FirmwareVersion:
    """Version of pslab-firmware running on connected device.

    Uses semantic versioning conventions.

    Attributes
    ----------
    major : int
        Major version. Incremented when backward imcompatible changes are made.
    minor : int
        Minor version. Incremented when new functionality is added, or existing
        functionality is changed in a backward compatible manner.
    patch : int
        Patch version. Incremented when bug fixes are made with do not change the
        PSLab's documented behavior.
    """

    major: int
    minor: int
    patch: int


class ConnectionHandler(ABC):
    """Abstract base class for PSLab control interfaces."""

    @abstractmethod
    def connect(self) -> None:
        """Connect to PSLab."""
        ...

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect PSLab."""
        ...

    @abstractmethod
    def read(self, numbytes: int) -> bytes:
        """Read data from PSLab.

        Parameters
        ----------
        numbytes : int

        Returns
        -------
        data : bytes
        """
        ...

    @abstractmethod
    def write(self, data: bytes) -> int:
        """Write data to PSLab.

        Parameters
        ----------
        data : bytes

        Returns
        -------
        numbytes : int
        """
        ...

    def get_byte(self) -> int:
        """Read a single one-byte of integer value.

        Returns
        -------
        int
        """
        return int.from_bytes(self.read(1), byteorder="little")

    def get_int(self) -> int:
        """Read a single two-byte integer value.

        Returns
        -------
        int
        """
        return int.from_bytes(self.read(2), byteorder="little")

    def get_long(self) -> int:
        """Read a single four-byte integer value.

        Returns
        -------
        int
        """
        return int.from_bytes(self.read(4), byteorder="little")

    def send_byte(self, data: int | bytes) -> None:
        """Write a single one-byte integer value.

        Parameters
        ----------
        data : int
        """
        if isinstance(data, int):
            data = data.to_bytes(length=1, byteorder="little")
        self.write(data)

    def send_int(self, data: int | bytes) -> None:
        """Write a single two-byte integer value.

        Parameters
        ----------
        data : int | bytes
        """
        if isinstance(data, int):
            data = data.to_bytes(length=2, byteorder="little")
        self.write(data)

    def send_long(self, data: int | bytes) -> None:
        """Write a single four-byte integer value.

        Parameters
        ----------
        data : int | bytes
        """
        if isinstance(data, int):
            data = data.to_bytes(length=4, byteorder="little")
        self.write(data)

    def get_ack(self) -> int:
        """Get response code from PSLab.

        Returns
        -------
        int
            Response code. Meanings:
                0x01 ACK
                0x10 I2C ACK
                0x20 I2C bus collision
                0x10 Radio max retransmits
                0x20 Radio not present
                0x40 Radio reply timout
        """
        response = self.read(1)

        if not response:
            raise TimeoutError

        ack = CP.Byte.unpack(response)[0]

        if not (ack & 0x01):
            raise RuntimeError("Received non ACK byte while waiting for ACK.")

        return ack

    def get_version(self) -> str:
        """Query PSLab for its version and return it as a decoded string.

        Returns
        -------
        str
            Version string.
        """
        self.send_byte(CP.COMMON)
        self.send_byte(CP.GET_VERSION)
        version_length = 9
        version = self.read(version_length)

        try:
            if b"PSLab" not in version:
                msg = f"got unexpected hardware version: {version}"
                raise ConnectionError(msg)
        except Exception as exc:
            msg = "device not found"
            raise ConnectionError(msg) from exc

        return version.decode("utf-8")

    def get_firmware_version(self) -> FirmwareVersion:
        """Get firmware version.

        Returns
        -------
        tuple[int, int, int]
            major, minor, patch.

        """
        self.send_byte(CP.COMMON)
        self.send_byte(CP.GET_FW_VERSION)

        # Firmware version query was added in firmware version 3.0.0.
        major = self.get_byte()
        minor = self.get_byte()
        patch = self.get_byte()

        return FirmwareVersion(major, minor, patch)
