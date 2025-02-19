"""Serial interface for communicating with PSLab devices."""

import os
import platform

import serial

import pslab
from pslab.connection.connection import ConnectionHandler


def _check_serial_access_permission():
    """Check that we have permission to use the tty on Linux."""
    if platform.system() == "Linux":
        import grp

        if os.geteuid() == 0:  # Running as root?
            return

        for group in os.getgroups():
            if grp.getgrgid(group).gr_name in (
                "dialout",
                "uucp",
            ):
                return

        udev_paths = [
            "/run/udev/rules.d/",
            "/etc/udev/rules.d/",
            "/lib/udev/rules.d/",
        ]
        for p in udev_paths:
            udev_rules = os.path.join(p, "99-pslab.rules")
            if os.path.isfile(udev_rules):
                return
        else:
            raise PermissionError(
                "The current user does not have permission to access "
                "the PSLab device. To solve this, either:"
                "\n\n"
                "1. Add the user to the 'dialout' (on Debian-based "
                "systems) or 'uucp' (on Arch-based systems) group."
                "\n"
                "2. Install a udev rule to allow any user access to the "
                "device by running 'pslab install' as root, or by "
                "manually copying "
                f"{pslab.__path__[0]}/99-pslab.rules into {udev_paths[1]}."
                "\n\n"
                "You may also need to reboot the system for the "
                "permission changes to take effect."
            )


class SerialHandler(ConnectionHandler):
    """Interface for controlling a PSLab over a serial port.

    Parameters
    ----------
        port : str
        baudrate : int, default 1 MBd
        timeout : float, default 1 s
    """

    #            V5      V6
    _USB_VID = [0x04D8, 0x10C4]
    _USB_PID = [0x00DF, 0xEA60]

    def __init__(
        self,
        port: str,
        baudrate: int = 1000000,
        timeout: float = 1.0,
    ):
        self._port = port
        self._ser = serial.Serial(
            baudrate=baudrate,
            timeout=timeout,
            write_timeout=timeout,
        )
        _check_serial_access_permission()

    @property
    def port(self) -> str:
        """Serial port."""
        return self._port

    @property
    def baudrate(self) -> int:
        """Symbol rate."""
        return self._ser.baudrate

    @baudrate.setter
    def baudrate(self, value: int) -> None:
        self._ser.baudrate = value

    @property
    def timeout(self) -> float:
        """Timeout in seconds."""
        return self._ser.timeout

    @timeout.setter
    def timeout(self, value: float) -> None:
        self._ser.timeout = value
        self._ser.write_timeout = value

    def connect(self) -> None:
        """Connect to PSLab."""
        self._ser.port = self.port
        self._ser.open()

        try:
            self.get_version()
        except Exception:
            self._ser.close()
            raise

    def disconnect(self):
        """Disconnect from PSLab."""
        self._ser.close()

    def read(self, number_of_bytes: int) -> bytes:
        """Read bytes from serial port.

        Parameters
        ----------
        number_of_bytes : int
            Number of bytes to read from the serial port.

        Returns
        -------
        bytes
            Bytes read from the serial port.
        """
        return self._ser.read(number_of_bytes)

    def write(self, data: bytes) -> int:
        """Write bytes to serial port.

        Parameters
        ----------
        data : int
            Bytes to write to the serial port.

        Returns
        -------
        int
            Number of bytes written.
        """
        return self._ser.write(data)

    def __repr__(self) -> str:  # noqa
        return (
            f"{self.__class__.__name__}"
            "["
            f"{self.port}, "
            f"{self.baudrate} baud"
            "]"
        )
