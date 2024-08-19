"""Low-level communication for PSLab.

Example
-------
>>> from pslab.serial_handler import SerialHandler
>>> device = SerialHandler()
>>> version = device.get_version()
>>> device.disconnect()
"""

from __future__ import annotations

try:
    import grp
except ImportError:
    pass

import logging
import os
import platform
import struct
import time
from dataclasses import dataclass
from functools import partial, update_wrapper
from typing import List, Union

import serial
from serial.tools import list_ports

import pslab
import pslab.protocol as CP

logger = logging.getLogger(__name__)


def detect():
    """Detect connected PSLab devices.

    Returns
    -------
    devices : dict of str: str
        Dictionary containing port name as keys and device version on that
        port as values.
    """
    regex = []

    for vid, pid in zip(SerialHandler._USB_VID, SerialHandler._USB_PID):
        regex.append(f"{vid:04x}:{pid:04x}")

    regex = "(" + "|".join(regex) + ")"
    port_info_generator = list_ports.grep(regex)
    pslab_devices = {}

    for port_info in port_info_generator:
        version = _get_version(port_info.device)
        if any(expected in version for expected in ["PSLab", "CSpark"]):
            pslab_devices[port_info.device] = version

    return pslab_devices


def _get_version(port: str) -> str:
    interface = serial.Serial(port=port, baudrate=1e6, timeout=1)
    interface.write(CP.COMMON)
    interface.write(CP.GET_VERSION)
    version = interface.readline()
    return version.decode("utf-8")


@dataclass
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


class SerialHandler:
    """Provides methods for communicating with the PSLab hardware.

    When instantiated, SerialHandler tries to connect to the PSLab. A port can
    optionally be specified; otherwise Handler will try to find the correct
    port automatically.

    Parameters
    ----------
    See :meth:`connect`.
    """

    #            V5      V6
    _USB_VID = [0x04D8, 0x10C4]
    _USB_PID = [0x00DF, 0xEA60]

    def __init__(
        self,
        port: str = None,
        baudrate: int = 1000000,
        timeout: float = 1.0,
    ):
        self.version = ""
        self.interface = serial.Serial()

        self.send_byte = partial(self._send, size=1)
        update_wrapper(self.send_byte, self._send)
        self.send_int = partial(self._send, size=2)
        update_wrapper(self.send_int, self._send)
        self.send_long = partial(self._send, size=4)
        update_wrapper(self.send_long, self._send)
        self.get_byte = partial(self._receive, size=1)
        update_wrapper(self.get_byte, self._receive)
        self.get_int = partial(self._receive, size=2)
        update_wrapper(self.get_int, self._receive)
        self.get_long = partial(self._receive, size=4)
        update_wrapper(self.get_long, self._receive)

        self.check_serial_access_permission()
        self.connect(port=port, baudrate=baudrate, timeout=timeout)
        self.connected = self.interface.is_open
        self.firmware = self.get_firmware_version()

    @staticmethod
    def check_serial_access_permission():
        """Check that we have permission to use the tty on Linux."""
        if platform.system() == "Linux":
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

    @staticmethod
    def _list_ports() -> List[str]:
        """Return a list of serial port names."""
        return [p.device for p in list_ports.comports()]

    def connect(
        self,
        port: str = None,
        baudrate: int = 1000000,
        timeout: float = 1.0,
    ):
        """Connect to PSLab.

        Parameters
        ----------
        port : str, optional
            The name of the port to which the PSLab is connected as a string.
            On Posix this is a path, e.g. "/dev/ttyACM0". On Windows, it's a
            numbered COM port, e.g. "COM5". Will be autodetected if not
            specified. If multiple PSLab devices are connected, port must be
            specified.
        baudrate : int, optional
            Symbol rate in bit/s. The default value is 1000000.
        timeout : float, optional
            Time in seconds to wait before cancelling a read or write command. The
            default value is 1.0.

        Raises
        ------
        SerialException
            If connection could not be established.
        RuntimeError
            If ultiple devices are connected and no port was specified.
        """
        # serial.Serial opens automatically if port is not None.
        self.interface = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
            write_timeout=timeout,
        )
        pslab_devices = detect()

        if self.interface.is_open:
            # User specified a port.
            version = self.get_version()
        else:
            if len(pslab_devices) == 1:
                self.interface.port = list(pslab_devices.keys())[0]
                self.interface.open()
                version = self.get_version()
            elif len(pslab_devices) > 1:
                found = ""

                for port, version in pslab_devices.items():
                    found += f"{port}: {version}"

                raise RuntimeError(
                    "Multiple PSLab devices found:\n"
                    f"{found}"
                    "Please choose a device by specifying a port."
                )
            else:
                version = ""

        if self.interface.port in pslab_devices:
            self.version = version
            logger.info(f"Connected to {self.version} on {self.interface.port}.")
        else:
            self.interface.close()
            self.version = ""
            raise serial.SerialException("Device not found.")

    def disconnect(self):
        """Disconnect from PSLab."""
        self.interface.close()

    def reconnect(
        self,
        port: str = None,
        baudrate: int = None,
        timeout: float = None,
    ):
        """Reconnect to PSLab.

        Will reuse previous settings (port, baudrate, timeout) unless new ones are
        provided.

        Parameters
        ----------
        See :meth:`connect`.
        """
        self.disconnect()

        # Reuse previous settings unless user provided new ones.
        baudrate = self.interface.baudrate if baudrate is None else baudrate
        port = self.interface.port if port is None else port
        timeout = self.interface.timeout if timeout is None else timeout

        self.connect(
            port=port,
            baudrate=baudrate,
            timeout=timeout,
        )

    def get_version(self) -> str:
        """Query PSLab for its version and return it as a decoded string.

        Returns
        -------
        str
            Version string.
        """
        self.send_byte(CP.COMMON)
        self.send_byte(CP.GET_VERSION)
        version = self.interface.readline()
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

        try:
            # Firmware version query was added in firmware version 3.0.0.
            major = self.get_byte()
            minor = self.get_byte()
            patch = self.get_byte()
        except serial.SerialException:
            major = 2
            minor = 0
            patch = 0

        return FirmwareVersion(major, minor, patch)

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
            raise serial.SerialException("Timeout while waiting for ACK.")

        ack = CP.Byte.unpack(response)[0]

        if not (ack & 0x01):
            raise serial.SerialException("Received non ACK byte while waiting for ACK.")

        return ack

    @staticmethod
    def _get_integer_type(size: int) -> struct.Struct:
        if size == 1:
            return CP.Byte
        elif size == 2:
            return CP.ShortInt
        elif size == 4:
            return CP.Integer
        else:
            raise ValueError("size must be 1, 2, or 4.")

    def _send(self, value: Union[bytes, int], size: int):
        """Send a value to the PSLab.

        Parameters
        ----------
        value : int
            Value to send to PSLab. Must fit in four bytes.
        """
        if isinstance(value, bytes):
            packet = value
        else:
            packer = self._get_integer_type(size)
            packet = packer.pack(value)

        self.write(packet)

    def _receive(self, size: int) -> int:
        """Read and unpack data from the serial port.

        Returns
        -------
        int
            Unpacked data.

        Raises
        ------
        SerialException if too few bytes received.
        """
        received = self.read(size)

        if len(received) == size:
            unpacker = self._get_integer_type(size)
            retval = unpacker.unpack(received)[0]
        else:
            raise serial.SerialException(
                f"Requested {size} bytes, got {len(received)}."
            )

        return retval

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
        return self.interface.read(number_of_bytes)

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
        return self.interface.write(data)

    def wait_for_data(self, timeout: float = 0.2) -> bool:
        """Wait for :timeout: seconds or until there is data in the input buffer.

        Parameters
        ----------
        timeout : float, optional
            Time in seconds to wait. The default is 0.2.

        Returns
        -------
        bool
            True iff the input buffer is not empty.
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.interface.in_waiting:
                return True
            time.sleep(0.02)

        return False


class ADCBufferMixin:
    """Mixin for classes that need to read or write to the ADC buffer."""

    def fetch_buffer(self, samples: int, starting_position: int = 0):
        """Fetch a section of the ADC buffer.

        Parameters
        ----------
        samples : int
            Number of samples to fetch.
        starting_position : int, optional
            Location in the ADC buffer to start from. By default samples will
            be fetched from the beginning of the buffer.

        Returns
        -------
        received : list of int
            List of received samples.
        """
        self._device.send_byte(CP.COMMON)
        self._device.send_byte(CP.RETRIEVE_BUFFER)
        self._device.send_int(starting_position)
        self._device.send_int(samples)
        received = [self._device.get_int() for i in range(samples)]
        self._device.get_ack()
        return received

    def clear_buffer(self, samples: int, starting_position: int = 0):
        """Clear a section of the ADC buffer.

        Parameters
        ----------
        samples : int
            Number of samples to clear from the buffer.
        starting_position : int, optional
            Location in the ADC buffer to start from. By default samples will
            be cleared from the beginning of the buffer.
        """
        self._device.send_byte(CP.COMMON)
        self._device.send_byte(CP.CLEAR_BUFFER)
        self._device.send_int(starting_position)
        self._device.send_int(samples)
        self._device.get_ack()

    def fill_buffer(self, data: List[int], starting_position: int = 0):
        """Fill a section of the ADC buffer with data.

        Parameters
        ----------
        data : list of int
            Values to write to the ADC buffer.
        starting_position : int, optional
            Location in the ADC buffer to start from. By default writing will
            start at the beginning of the buffer.
        """
        self._device.send_byte(CP.COMMON)
        self._device.send_byte(CP.FILL_BUFFER)
        self._device.send_int(starting_position)
        self._device.send_int(len(data))

        for value in data:
            self._device.send_int(value)

        self._device.get_ack()
