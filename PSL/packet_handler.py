"""Low-level communication for PSLab.

Example
-------
>>> from PSL.packet_handler import Handler
>>> device = Handler()
>>> version = device.get_version()
>>> device.disconnect()
"""
import logging
import struct
import time
from functools import partial
from typing import List, Union

import serial
from serial.tools import list_ports

import PSL.commands_proto as CP

logger = logging.getLogger(__name__)

USB_VID = 0x04D8
USB_PID = 0x00DF


class Handler:
    """Provides methods for communicating with the PSLab hardware.

    When instantiated, Handler tries to connect to the PSLab. A port can optionally
    be specified; otherwise Handler will try to find the correct port automatically.

    Parameters
    ----------
    See :meth:`connect. <PSL.packet_handler.Handler.connect>`.
    """

    def __init__(
        self,
        port: str = None,
        baudrate: int = 1000000,
        timeout: float = 1.0,
        **kwargs,  # Backward compatibility
    ):
        self.burst_buffer = b""
        self.load_burst = False
        self.input_queue_size = 0
        self.version = ""
        self._log = b""
        self._logging = False
        self.interface = serial.Serial()
        self.send_byte = partial(self._send, size=1)
        self.send_int = partial(self._send, size=2)
        self.get_byte = partial(self._receive, size=1)
        self.get_int = partial(self._receive, size=2)
        self.get_long = partial(self._receive, size=4)
        self.connect(port=port, baudrate=baudrate, timeout=timeout)

        # Backwards compatibility
        self.fd = self.interface
        self.occupiedPorts = set()
        self.connected = self.interface.is_open
        self.__sendByte__ = partial(self._send, size=1)
        self.__sendInt__ = partial(self._send, size=2)
        self.__get_ack__ = self.get_ack
        self.__getByte__ = partial(self._receive, size=1)
        self.__getInt__ = partial(self._receive, size=2)
        self.__getLong__ = partial(self._receive, size=4)
        self.waitForData = self.wait_for_data
        self.sendBurst = self.send_burst
        self.portname = self.interface.name
        self.listPorts = self._list_ports

    @staticmethod
    def _list_ports() -> List[str]:  # Promote to public?
        """Return a list of serial port names."""
        return [p.device for p in list_ports.comports()]

    def connect(
        self, port: str = None, baudrate: int = 1000000, timeout: float = 1.0,
    ):
        """Connect to PSLab.

        Parameters
        ----------
        port : str, optional
            The name of the port to which the PSLab is connected as a string. On
            Posix this is a path, e.g. "/dev/ttyACM0". On Windows, it's a numbered
            COM port, e.g. "COM5". Will be autodetected if not specified.
        baudrate : int, optional
            Symbol rate in bit/s. The default value is 1000000.
        timeout : float, optional
            Time in seconds to wait before cancelling a read or write command. The
            default value is 1.0.

        Raises
        ------
        SerialException
            If connection could not be established.
        """
        # serial.Serial opens automatically if port is not None.
        self.interface = serial.Serial(
            port=port, baudrate=baudrate, timeout=timeout, write_timeout=timeout,
        )

        if self.interface.is_open:
            # User specified a port.
            version = self.get_version()
        else:
            port_info_generator = list_ports.grep(f"{USB_VID:04x}:{USB_PID:04x}")

            for port_info in port_info_generator:
                self.interface.port = port_info.device
                self.interface.open()
                version = self.get_version()
                if any(expected in version for expected in ["PSLab", "CSpark"]):
                    break
            else:
                version = ""

        if any(expected in version for expected in ["PSLab", "CSpark"]):
            self.version = version
            self.fd = self.interface  # Backward compatibility
            logger.info(f"Connected to {self.version} on {self.interface.port}.")
        else:
            self.interface.close()
            self.version = ""
            raise serial.SerialException("Device not found.")

    def disconnect(self):
        """Disconnect from PSLab."""
        self.interface.close()

    def reconnect(
        self, port: str = None, baudrate: int = None, timeout: float = None,
    ):
        """Reconnect to PSLab.

        Will reuse previous settings (port, baudrate, timeout) unless new ones are
        provided.

        Parameters
        ----------
        See :meth:`connect. <PSL.packet_handler.Handler.connect>`.
        """
        self.disconnect()

        # Reuse previous settings unless user provided new ones.
        baudrate = self.interface.baudrate if baudrate is None else baudrate
        port = self.interface.port if port is None else port
        timeout = self.interface.timeout if timeout is None else timeout

        self.interface = serial.Serial(
            port=port, baudrate=baudrate, timeout=timeout, write_timeout=timeout,
        )
        self.connect()

    def __del__(self):  # Is this necessary?
        """Disconnect before garbage collection."""
        self.interface.close()

    def get_version(self, *args) -> str:  # *args for backwards compatibility
        """Query PSLab for its version and return it as a decoded string.

        Returns
        -------
        str
            Version string.
        """
        self.send_byte(CP.COMMON)
        self.send_byte(CP.GET_VERSION)
        version = self.interface.readline()
        self._write_log(version, "RX")
        return version.decode("utf-8")

    def get_ack(self) -> int:  # Make _internal?
        """Get response code from PSLab.

        Also functions as handshake.

        Returns
        -------
        int
            Response code. Meanings:
                1 SUCCESS
                2 ARGUMENT_ERROR
                3 FAILED
        """
        if not self.load_burst:
            response = self.read(1)
        else:
            self.input_queue_size += 1
            return 1

        try:
            return CP.Byte.unpack(response)[0]
        except Exception as e:
            logger.error(e)
            return 3  # raise exception instead?

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

    def _send(self, value: Union[bytes, int], size: int = None):
        """Send a value to the PSLab.

        Optionally handles conversion from int to bytes.

        Parameters
        ----------
        value : bytes, int
            Value to send to PSLab. Must fit in four bytes.
        size : int, optional
            Number of bytes to send. If not specified, the number of bytes sent
            depends on the size of :value:.
        """
        if isinstance(value, bytes):
            packet = value
        else:
            # True + True == 2, see PEP 285.
            size = 2 ** ((value > 0xFF) + (value > 0xFFFF)) if size is None else size
            packer = self._get_integer_type(size)
            packet = packer.pack(value)

        if self.load_burst:
            self.burst_buffer += packet
        else:
            self.write(packet)

    def _receive(self, size: int) -> int:
        """Read and unpack the specified number of bytes from the serial port.

        Parameters
        ----------
        size : int
            Number of bytes to read from the serial port.

        Returns
        -------
        int
            Unpacked bytes, or -1 if too few bytes were read.
        """
        received = self.read(size)

        if len(received) == size:
            if size in (1, 2, 4):
                unpacker = self._get_integer_type(size)
                retval = unpacker.unpack(received)[0]
            else:
                retval = int.from_bytes(
                    bytes=received, byteorder="little", signed=False
                )
        else:
            logger.error(f"Requested {size} bytes, got {len(received)}.")
            retval = -1  # raise an exception instead?

        return retval

    def read(self, number_of_bytes: int) -> bytes:
        data = self.interface.read(number_of_bytes)
        self._write_log(data, "RX")
        return data

    def write(self, data: bytes):
        self.interface.write(data)
        self._write_log(data, "TX")

    def _write_log(self, data: bytes, direction: str):
        if self._logging:
            self._log += direction.encode() + data + "STOP".encode()

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

    def send_burst(self) -> List[int]:
        """Transmit the commands stored in the burst_buffer.

        The burst_buffer and input buffer are both emptied.

        The following example initiates the capture routine and sets OD1 HIGH
        immediately. It is used by the Transient response experiment where the input
        needs to be toggled soon after the oscilloscope has been started.

        Example
        -------
        >>> I.load_burst = True
        >>> I.capture_traces(4, 800, 2)
        >>> I.set_state(I.OD1, I.HIGH)
        >>> I.send_burst()

        Returns
        -------
        list
            List of response codes
            (see :meth:`get_ack <PSL.packet_handler.Handler.get_ack>`).
        """
        self.write(self.burst_buffer)
        self.burst_buffer = b""
        self.load_burst = False
        acks = self.read(self.input_queue_size)
        self.input_queue_size = 0

        return list(acks)
