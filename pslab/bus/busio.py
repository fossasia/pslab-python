"""Circuitpython's busio compatibility layer for pslab-python.

This module emulates the CircuitPython's busio API for devices or hosts running
CPython or MicroPython using pslab-python.
This helps to access many sensors using Adafruit's drivers via PSLab board.

Notes
-----
Documentation:
    https://circuitpython.readthedocs.io/en/6.3.x/shared-bindings/busio/index.html

Examples
--------
Get humidity from Si7021 temperature and humidity sensor using adafruit_si7021 module.

>>> import adafruit_si7021
>>> from pslab.bus import busio   # import board, busio
>>> i2c = busio.I2C()   # i2c = busio.I2C(board.SCL, board.SDA)
>>> sensor = adafruit_si7021.SI7021(i2c)
>>> print(sensor.relative_humidity)

Get gyro reading from BNO055 using adafruit_bno055, board(just a wrapper for busio).

>>> import adafruit_bno055
>>> from pslab.bus import busio   # import board
>>> i2c = busio.I2C()   # i2c = board.I2C()
>>> sensor = adafruit_bno055.BNO055_I2C(i2c)
>>> print(sensor.gyro)
"""

import time
from enum import Enum
from itertools import zip_longest
from typing import List, Union, Optional

from pslab.bus.i2c import _I2CPrimitive
from pslab.bus.spi import _SPIPrimitive
from pslab.bus.uart import _UARTPrimitive
from pslab.serial_handler import SerialHandler

__all__ = (
    "I2C",
    "SPI",
    "UART",
)
ReadableBuffer = Union[bytes, bytearray, memoryview]
WriteableBuffer = Union[bytearray, memoryview]


class I2C(_I2CPrimitive):
    """Busio I2C Class for CircuitPython Compatibility.

    Parameters
    ----------
    device : :class:`SerialHandler`, optional
        Serial connection to PSLab device. If not provided, a new one will be
        created.
    frequency : float, optional
        Frequency of SCL in Hz.
    """

    def __init__(self, device: SerialHandler = None, *, frequency: int = 125e3):
        # 125 kHz is as low as the PSLab can go.
        super().__init__(device)
        self._init()
        self._configure(frequency)

    def deinit(self) -> None:
        """Just a dummy method."""
        pass

    def __enter__(self):
        """Just a dummy context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Call :meth:`deinit` on context exit."""
        self.deinit()

    def scan(self) -> List[int]:
        """Scan all I2C addresses between 0x08 and 0x77 inclusive.

        Returns
        -------
        addrs : list of int
            List of 7-bit addresses on which slave devices replied.
        """
        return self._scan(0x08, 0x77)

    def try_lock(self) -> bool:  # pylint: disable=no-self-use
        """Just a dummy method."""
        return True

    def unlock(self) -> None:
        """Just a dummy method."""
        pass

    def readfrom_into(
        self, address: int, buffer: WriteableBuffer, *, start: int = 0, end: int = None
    ) -> None:
        """Read from a device at specified address into a buffer.

        Parameters
        ----------
        address : int
            7-bit I2C device address.
        buffer : bytearray or memoryview
            buffer to write into.
        start : int
            Index to start writing at.
        end : int
            Index to write up to but not include. Defaults to length of `buffer`.
        """
        end = len(buffer) if end is None else end
        bytes_to_read = end - start
        self._start(address, 1)
        buffer[start:end] = self._read(bytes_to_read)
        self._stop()

    def writeto(
        self,
        address: int,
        buffer: ReadableBuffer,
        *,
        start: int = 0,
        end: int = None,
        stop: bool = True,
    ) -> None:
        """Write to a device at specified address from a buffer.

        Parameters
        ----------
        address : int
            7-bit I2C device address.
        buffer : bytes or bytearray or memoryview
            buffer containing the bytes to write.
        start : int
            Index to start writing from.
        end : int
            Index to read up to but not include. Defaults to length of `buffer`.
        stop : bool
            Enable to transmit a stop bit. Defaults to True.
        """
        end = len(buffer) if end is None else end

        if stop:
            self._write_bulk(address, buffer[start:end])
        else:
            self._start(address, 0)
            self._send(buffer[start:end])

    def writeto_then_readfrom(
        self,
        address: int,
        buffer_out: ReadableBuffer,
        buffer_in: WriteableBuffer,
        *,
        out_start: int = 0,
        out_end: int = None,
        in_start: int = 0,
        in_end: int = None,
    ):
        """Write to then read from a device at specified address.

        Parameters
        ----------
        address : int
            7-bit I2C device address.
        out_buffer : bytes or bytearray or memoryview
            buffer containing the bytes to write.
        in_buffer : bytearray or memoryview
            buffer to write into.
        out_start : int
            Index to start writing from.
        out_end : int
            Index to read up to but not include. Defaults to length of `out_buffer`.
        in_start : int
            Index to start writing at.
        in_end : int
            Index to write up to but not include. Defaults to length of `in_buffer`.
        """
        out_end = len(buffer_out) if out_end is None else out_end
        in_end = len(buffer_in) if in_end is None else in_end
        bytes_to_read = in_end - in_start
        self._start(address, 0)
        self._send(buffer_out[out_start:out_end])
        self._restart(address, 1)
        buffer_in[in_start:in_end] = self._read(bytes_to_read)
        self._stop()


class SPI(_SPIPrimitive):
    """Busio SPI Class for CircuitPython Compatibility.

    Parameters
    ----------
    device : :class:`SerialHandler`, optional
        Serial connection to PSLab device. If not provided, a new one will be
        created.
    """

    def __init__(self, device: SerialHandler = None):
        super().__init__(device)
        ppre, spre = self._get_prescaler(25e4)
        self._set_parameters(ppre, spre, 1, 0, 1)
        self._bits = 8

    @property
    def frequency(self) -> int:
        """Get the actual SPI bus frequency (rounded).

        This may not match the frequency requested due to internal limitations.
        """
        return round(self._frequency)

    def deinit(self) -> None:
        """Just a dummy method."""
        pass

    def __enter__(self):
        """Just a dummy context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Call :meth:`deinit` on context exit."""
        self.deinit()

    def configure(
        self,
        *,
        baudrate: int = 100000,
        polarity: int = 0,
        phase: int = 0,
        bits: int = 8,
    ) -> None:
        """Configure the SPI bus.

        Parameters
        ----------
        baudrate : int
            The desired clock rate in Hertz. The actual clock rate may be
            higher or lower due to the granularity of available clock settings.
            Check the frequency attribute for the actual clock rate.
        polarity : int
            The base state of the clock line (0 or 1)
        phase : int
            The edge of the clock that data is captured. First (0) or second (1).
            Rising or falling depends on clock polarity.
        bits : int
            The number of bits per word.
        """
        if polarity not in (0, 1):
            raise ValueError("Invalid polarity")
        if phase not in (0, 1):
            raise ValueError("Invalid phase")
        if bits not in self._INTEGER_TYPE_MAP:
            raise ValueError("Invalid number of bits")

        ppre, spre = self._get_prescaler(baudrate)
        cke = (phase ^ 1) & 1
        self._set_parameters(ppre, spre, cke, polarity, 1)
        self._bits = bits

    def try_lock(self) -> bool:  # pylint: disable=no-self-use
        """Just a dummy method."""
        return True

    def unlock(self) -> None:
        """Just a dummy method."""
        pass

    def write(
        self,
        buffer: Union[ReadableBuffer, List[int]],
        *,
        start: int = 0,
        end: int = None,
    ) -> None:
        """Write the data contained in buffer. If the buffer is empty, nothing happens.

        Parameters
        ----------
        buffer : bytes or bytearray or memoryview or list_of_int (for bits >8)
            Write out the data in this buffer.
        start : int
            Start of the slice of `buffer` to write out: `buffer[start:end]`.
        end : int
            End of the slice; this index is not included. Defaults to `len(buffer)`.
        """
        end = len(buffer) if end is None else end
        buffer = buffer[start:end]

        if not buffer:
            return

        self._start()
        self._write_bulk(buffer, self._bits)
        self._stop()

    def readinto(
        self,
        buffer: Union[WriteableBuffer, List[int]],
        *,
        start: int = 0,
        end: int = None,
        write_value: int = 0,
    ) -> None:
        """Read into `buffer` while writing `write_value` for each byte read.

        If the number of bytes to read is 0, nothing happens.

        Parameters
        ----------
        buffer : bytearray or memoryview or list_of_int (for bits >8)
            Read data into this buffer.
        start : int
            Start of the slice of `buffer` to read into: `buffer[start:end]`.
        end : int
            End of the slice; this index is not included. Defaults to `len(buffer)`.
        write_value : int
            Value to write while reading. (Usually ignored.)
        """
        end = len(buffer) if end is None else end
        bytes_to_read = end - start

        if bytes_to_read == 0:
            return

        self._start()
        data = self._transfer_bulk([write_value] * bytes_to_read, self._bits)
        self._stop()

        for i, v in zip(range(start, end), data):
            buffer[i] = v

    def write_readinto(
        self,
        buffer_out: Union[ReadableBuffer, List[int]],
        buffer_in: Union[WriteableBuffer, List[int]],
        *,
        out_start: int = 0,
        out_end: int = None,
        in_start: int = 0,
        in_end: int = None,
    ):
        """Write out the data in buffer_out while simultaneously read into buffer_in.

        The lengths of the slices defined by buffer_out[out_start:out_end] and
        buffer_in[in_start:in_end] must be equal. If buffer slice lengths are both 0,
        nothing happens.

        Parameters
        ----------
        buffer_out : bytes or bytearray or memoryview or list_of_int (for bits >8)
            Write out the data in this buffer.
        buffer_in : bytearray or memoryview or list_of_int (for bits >8)
            Read data into this buffer.
        out_start : int
            Start of the slice of `buffer_out` to write out:
            `buffer_out[out_start:out_end]`.
        out_end : int
            End of the slice; this index is not included. Defaults to `len(buffer_out)`
        in_start : int
            Start of the slice of `buffer_in` to read into:`buffer_in[in_start:in_end]`
        in_end : int
            End of the slice; this index is not included. Defaults to `len(buffer_in)`
        """
        out_end = len(buffer_out) if out_end is None else out_end
        in_end = len(buffer_in) if in_end is None else in_end
        buffer_out = buffer_out[out_start:out_end]
        bytes_to_read = in_end - in_start

        if len(buffer_out) != bytes_to_read:
            raise ValueError("buffer slices must be of equal length")
        if bytes_to_read == 0:
            return

        self._start()
        data = self._transfer_bulk(buffer_out, self._bits)
        self._stop()

        for i, v in zip(range(in_start, in_end), data):
            buffer_in[i] = v


class Parity(Enum):
    EVEN = 1
    ODD = 2


class UART(_UARTPrimitive):
    """Busio UART Class for CircuitPython Compatibility.

    Parameters
    ----------
    device : :class:`SerialHandler`, optional
        Serial connection to PSLab device. If not provided, a new one will be
        created.
    baudrate : int, optional
        The transmit and receive speed. Defaults to 9600.
    bits : int, optional
        The number of bits per byte, 8 or 9. Defaults to 8 bits.
    parity : :class:`Parity`, optional
        The parity used for error checking. Defaults to None.
        Only 8 bits per byte supports parity.
    stop : int, optional
        The number of stop bits, 1 or 2. Defaults to 1.
    timeout : float, optional
        The timeout in seconds to wait for the first character and between
        subsequent characters when reading. Defaults to 1.
    """

    def __init__(
        self,
        device: SerialHandler = None,
        *,
        baudrate: int = 9600,
        bits: int = 8,
        parity: Parity = None,
        stop: int = 1,
        timeout: float = 1,
    ):
        super().__init__(device)
        self._set_uart_baud(baudrate)

        if bits == 8:
            pd = 0
        elif bits == 9:
            pd = 3
        else:
            raise ValueError("Invalid number of bits")

        if bits == 9 and parity is not None:
            raise ValueError("Invalid parity")
        if stop not in (1, 2):
            raise ValueError("Invalid number of stop bits")

        pd += parity.value

        try:
            self._set_uart_mode(pd, stop - 1)
        except RuntimeError:
            pass

        self._timeout = timeout

    @property
    def baudrate(self):
        """Get the current baudrate."""
        return self._baudrate

    @property
    def in_waiting(self):
        """Get the number of bytes in the input buffer, available to be read.

        PSLab is limited to check, whether at least one byte in the buffer(1) or not(0).
        """
        return self._read_uart_status()

    @property
    def timeout(self):
        """Get the current timeout, in seconds (float)."""
        return self._timeout

    def deinit(self) -> None:
        """Just a dummy method."""
        pass

    def __enter__(self):
        """Just a dummy context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Call :meth:`deinit` on context exit."""
        self.deinit()

    def _read_with_timeout(self, nbytes: int = None, *, line=False):
        if nbytes == 0:
            return None

        start_time = time.time()
        data = bytearray()
        total_read = 0

        while (time.time() - start_time) <= self._timeout:
            has_char = self._read_uart_status()
            if has_char:
                char = self._read_byte()
                start_time = time.time()

                if line and char == 0xA:
                    break

                data.append(char)
                total_read += 1

            if nbytes and total_read == nbytes:
                break

            time.sleep(0.01)

        return bytes(data) if data else None

    def read(self, nbytes: int = None) -> Optional[bytes]:
        """Read characters.

        If `nbytes` is specified then read at most that many bytes. Otherwise,
        read everything that arrives until the connection times out.

        Providing the number of bytes expected is highly recommended because
        it will be faster.

        Parameters
        ----------
        nbytes : int, optional
            Number of bytes to read. Defaults to None.

        Returns
        -------
        bytes or None
            Data read.
        """
        return self._read_with_timeout(nbytes)

    def readinto(self, buf: WriteableBuffer) -> int:
        """Read bytes into the `buf`. Read at most `len(buf)` bytes.

        Parameters
        ----------
        buf : bytearray or memoryview
            Read data into this buffer.

        Returns
        -------
        int
            Number of bytes read and stored into `buf`.
        """
        nbytes = len(buf)
        data = self._read_with_timeout(nbytes)

        if data is None:
            return 0
        else:
            nbuf = len(data)

            for i, c in zip(range(nbuf), data):
                buf[i] = c

            return nbuf

    def readline(self) -> Optional[bytes]:
        """Read a line, ending in a newline character.

        return None if a timeout occurs sooner, or return everything readable
        if no newline is found within timeout.

        Returns
        -------
        bytes or None
            Data read.
        """
        return self._read_with_timeout(None, line=True)

    def write(self, buf: ReadableBuffer) -> int:
        """Write the buffer of bytes to the bus.

        Parameters
        ----------
        buf : bytes or bytearray or memoryview
            Write out the char in this buffer.

        Returns
        -------
        int
            Number of bytes written.
        """
        written = 0

        for msb, lsb in zip_longest(buf[1::2], buf[::2]):
            if msb is not None:
                self._write_int((msb << 8) | lsb)
                written += 2
            else:
                self._write_byte(lsb)
                written += 1

        return written
