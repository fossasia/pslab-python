"""Control the PSLab's I2C bus and devices connected on the bus.

Examples
--------
Set I2C bus speed to 400 kbit/s:

>>> from pslab.bus.i2c import I2CMaster, I2CSlave
>>> bus = I2CMaster()
>>> bus.configure(frequency=4e5)

Scan for connected devices:

>>> bus.scan()
[96, 104]

Connect to the PSLab's built-in DS1307 RTC:

>>> rtc = I2CSlave(address=104)
"""
import logging
from typing import List

import pslab.protocol as CP
from pslab.serial_handler import SerialHandler
from pslab.external.sensorlist import sensors

logger = logging.getLogger(__name__)


class I2CMaster:
    """I2C bus controller.

    Handles slave independent functionality with the I2C port.

    Parameters
    ----------
    device : :class:`SerialHandler`, optional
        Serial connection to PSLab device. If not provided, a new one will be
        created.
    """

    _MIN_BRGVAL = 2
    _MAX_BRGVAL = 511
    # Specs say typical delay is 110 ns to 130 ns; 150 ns from testing.
    _SCL_DELAY = 150e-9

    def __init__(self, device: SerialHandler = None):
        self._device = device if device is not None else SerialHandler()
        self._device.send_byte(CP.I2C_HEADER)
        self._device.send_byte(CP.I2C_INIT)
        self._device.get_ack()
        self.configure(125e3)  # 125 kHz is as low as the PSLab can go.

    def configure(self, frequency: float):
        """Configure bus frequency.

        Parameters
        ----------
        frequency : float
            Frequency of SCL in Hz.
        """
        brgval = int((1 / frequency - self._SCL_DELAY) * CP.CLOCK_RATE - 2)

        if self._MIN_BRGVAL <= brgval <= self._MAX_BRGVAL:
            self._device.send_byte(CP.I2C_HEADER)
            self._device.send_byte(CP.I2C_CONFIG)
            self._device.send_int(brgval)
            self._device.get_ack()
        else:
            min_frequency = self._get_i2c_frequency(self._MAX_BRGVAL)
            max_frequency = self._get_i2c_frequency(self._MIN_BRGVAL)
            e = f"Frequency must be between {min_frequency} and {max_frequency} Hz."
            raise ValueError(e)

    def _get_i2c_frequency(self, brgval: int) -> float:
        return 1 / ((brgval + 2) / CP.CLOCK_RATE + self._SCL_DELAY)

    def scan(self) -> List[int]:
        """Scan I2C port for connected devices.

        Returns
        -------
        addrs : list of int
            List of 7-bit addresses on which slave devices replied.
        """
        addrs = []

        for address in range(1, 128):  # 0 is the general call address.
            slave = I2CSlave(address, self._device)

            if slave.ping():
                addrs.append(address)
                logger.info(
                    f"Response from slave on {hex(address)} "
                    + f"({sensors.get(address, 'None')})."
                )

        return addrs

    @property
    def _status(self):
        """int: Contents of the I2C2STAT register.

        bit 15  ACKSTAT: Acknowledge Status
                1 = NACK received from slave.
                0 = ACK received from slave.
        bit 14  TRSTAT: Transmit Status
                1 = Master transmit is in progress (8 bits + ACK).
                0 = Master transmit is not in progress.
        bit 10  BCL: Bus Collision Detect
                1 = A bus collision has been detected.
                0 = No collision.
        bit 7   IWCOL: I2C Write Collision Detect
                1 = An attempt to write to the I2C2TRN register failed because
                    the I2C module is busy.
                0 = No collision.
        bit 6   I2COV: I2C Receive Overflow Flag
                1 = A byte is received while the I2C2RCV register is still
                    holding the previous byte.
                0 = No overflow.
        bit 4   P: Stop
                1 = Indicates that a Stop bit has been detected last.
                0 = Stop bit was not detected last.
        bit 3   S: Start
                1 = Indicates that a Start (or Repeated Start) bit has been
                    detected last.
                0 = Start bit was not detected last.
        bit 1   RBF: Receive Buffer Full Status
                1 = Receive completes; the I2C2RCV register is full.
                0 = Receive is not complete; the I2C2RCV register is empty.
        bit 0   TBF: Transmit Buffer Full Status
                1 = Transmit is in progress; the I2C2TRN register is full.
                0 = Transmit completes; the I2C2TRN register is empty.
        """
        self._device.send_byte(CP.I2C_HEADER)
        self._device.send_byte(CP.I2C_STATUS)
        status = self._device.get_int()
        self._device.get_ack()
        return status


class I2CSlave:
    """I2C slave device.

    Parameters
    ----------
    address : int
        7-bit I2C device address.
    device : :class:`SerialHandler`, optional
        Serial interface for communicating with the PSLab device. If not
        provided, a new one will be created.

    Attributes
    ----------
    address : int
        7-bit I2C device address.
    """

    _ACK = 0
    _READ = 1
    _WRITE = 0

    def __init__(
        self,
        address: int,
        device: SerialHandler = None,
    ):
        self._device = device if device is not None else SerialHandler()
        self.address = address
        self._running = False
        self._mode = None

    def ping(self) -> bool:
        """Ping the I2C slave.

        Returns
        -------
        response : bool
            True is slave responded, False otherwise.
        """
        response = self._start(self._READ)
        self._stop()
        return response == self._ACK

    def _start(self, mode: int) -> int:
        """Initiate I2C transfer.

        Parameters
        ----------
        mode : {0, 1}
            0: write
            1: read

        Returns
        -------
        response : int
            Response from I2C slave device.
        """
        if self._mode == mode:
            return self._ACK

        self._device.send_byte(CP.I2C_HEADER)
        secondary = CP.I2C_START if not self._running else CP.I2C_RESTART
        self._device.send_byte(secondary)
        self._device.send_byte((self.address << 1) | mode)
        response = self._device.get_ack() >> 4  # ACKSTAT
        self._running = True
        return response

    def _stop(self):
        """Stop I2C transfer."""
        if self._running or self._mode:
            self._device.send_byte(CP.I2C_HEADER)
            self._device.send_byte(CP.I2C_STOP)
            self._device.get_ack()
            self._running = False
            self._mode = None

    def read(self, bytes_to_read: int, register_address: int = 0x0) -> bytearray:
        """Read data from I2C device.

        This method relies on the slave device auto incrementing its internal
        pointer after each read. Most devices do, but it is not part of the
        I2C standard. Refer to the device's documentation.

        If the slave device does not auto increment, use one of
        :meth:`read_byte`, :meth:`read_int`, or :meth:`read_long` instead,
        depending on how wide the device registers are.

        Parameters
        ----------
        bytes_to_read : int
            Number of bytes to read from slave device.
        register_address : int, optional
            Slave device internal memory address to read from. The default
            value is 0x0.

        Returns
        -------
        data : bytearray
            Read data as a bytearray.
        """
        self._device.send_byte(CP.I2C_HEADER)
        self._device.send_byte(CP.I2C_READ_BULK)
        self._device.send_byte(self.address)
        self._device.send_byte(register_address)
        self.pointer = register_address
        self._device.send_byte(bytes_to_read)
        data = self._device.read(bytes_to_read)
        self._device.get_ack()
        return bytearray(data)

    def read_byte(self, register_address: int = 0x0) -> int:
        """Read a single byte from the I2C slave.

        Parameters
        ----------
        register_address : int, optional
            Slave device internal memory address to read from. The default
            value is 0x0.

        Returns
        -------
        data : int
            A byte interpreted as a uint8.
        """
        return self.read(1, register_address)[0]

    def read_int(self, register_address: int = 0x0) -> int:
        """Read a two byte value from the I2C slave.

        Parameters
        ----------
        register_address : int, optional
            Slave device internal memory address to read from. The default
            value is 0x0.

        Returns
        -------
        data : int
            Two bytes interpreted as a uint16.
        """
        data = self.read(2, register_address)
        return CP.ShortInt.unpack(data)[0]

    def read_long(self, register_address: int = 0x0) -> int:
        """Read a four byte value from the I2C slave.

        Parameters
        ----------
        register_address : int, optional
            Slave device internal memory address to read from. The default
            value is 0x0.

        Returns
        -------
        data : int
            Four bytes interpreted as a uint32.
        """
        data = self.read(4, register_address)
        return CP.Integer.unpack(data)[0]

    def write(self, bytes_to_write: bytearray, register_address: int = 0x0):
        """Write data to I2C slave.

        This method relies on the slave device auto incrementing its internal
        pointer after each write. Most devices do, but it is not part of the
        I2C standard. Refer to the device's documentation.

        If the slave device does not auto increment, use one of
        :meth:`write_byte`, :meth:`write_int`, or :meth:`write_long` instead,
        depending on how wide the device registers are.

        Parameters
        ----------
        bytes_to_write : bytearray
            Data to write to the slave.
        register_address : int
            Slave device internal memory address to write to. The default
            value is 0x0.
        """
        self._device.send_byte(CP.I2C_HEADER)
        self._device.send_byte(CP.I2C_WRITE_BULK)
        self._device.send_byte(self.address)
        self._device.send_byte(len(bytes_to_write) + 1)  # +1 is register address.
        self._device.send_byte(register_address)

        for byte in bytes_to_write:
            self._device.send_byte(byte)

        self._device.get_ack()

    def write_byte(self, data: int, register_address: int = 0x0):
        """Write a single byte to the I2C slave.

        Parameters
        ----------
        data : int
            An integer that fits in a uint8.
        register_address : int, optional
            Slave device internal memory address to write to. The default
            value is 0x0.
        """
        self.write(CP.Byte.pack(data), register_address)

    def write_int(self, data: int, register_address: int = 0x0):
        """Write a two byte value to the I2C slave.

        Parameters
        ----------
        data : int
            An integer that fits in a uint16.
        register_address : int, optional
            Slave device internal memory address to write to. The default
            value is 0x0.
        """
        self.write(CP.ShortInt.pack(data), register_address)

    def write_long(self, data: int, register_address: int = 0x0):
        """Write a four byte value to the I2C slave.

        Parameters
        ----------
        data : int
            An integer that fits in a uint32.
        register_address : int, optional
            Slave device internal memory address to write to. The default
            value is 0x0.
        """
        self.write(CP.Integer.pack(data), register_address)
