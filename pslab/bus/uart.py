"""Control the PSLab's UART bus and devices connected on the bus.

Examples
--------
Set UART2 bus baudrate to 1000000:

>>> from pslab.bus.uart improt UART
>>> bus = UART()
>>> bus.configure(1e6)

Send a byte over UART:

>>> bus.write_byte(0x55)
"""

from typing import Tuple

import pslab.protocol as CP
from pslab.bus import classmethod_
from pslab.serial_handler import SerialHandler

__all__ = "UART"
_BRGVAL = 0x22  # BaudRate = 460800.
_MODE = (0, 0)  # 8-bit data and no parity, 1 stop bit.


class _UARTPrimitive:
    """UART primitive commands.

    Handles all the UART subcommands coded in pslab-firmware.

    Parameters
    ----------
    device : :class:`SerialHandler`, optional
        Serial connection to PSLab device. If not provided, a new one will be created.
    """

    _MIN_BRGVAL = 0
    _MAX_BRGVAL = 2**16 - 1

    _brgval = _BRGVAL
    _mode = _MODE

    def __init__(self, device: SerialHandler = None):
        self._device = device if device is not None else SerialHandler()

    @classmethod_
    @property
    def _baudrate(cls) -> float:
        return cls._get_uart_baudrate(cls._brgval)

    @staticmethod
    def _get_uart_brgval(baudrate: float, BRGH: int = 1) -> int:
        return round(((CP.CLOCK_RATE / baudrate) / (4 if BRGH else 16)) - 1)

    @staticmethod
    def _get_uart_baudrate(brgval: int, BRGH: int = 1) -> float:
        return (CP.CLOCK_RATE / (brgval + 1)) / (4 if BRGH else 16)

    @staticmethod
    def _save_config(brgval: int = None, mode: Tuple[int] = None):
        """Save the UART barval and mode bits.

        Parameters
        ----------
        brgval : int, optional
            Set value to `_UARTPrimitive._brgval`. Will be skipped if None.
            Defaults to None.
        mode : tuple of int, optional
            Set value to `_UARTPrimitive._mode`. Will be skipped if None.
            Defaults to None.
        """
        if brgval is not None:
            _UARTPrimitive._brgval = brgval
        if mode is not None:
            _UARTPrimitive._mode = mode

    def _set_uart_baud(self, baudrate: int):
        """Set the baudrate of the UART bus.

        It is a primitive UART method, prefered to use :meth:`UART.configure`.

        Parameters
        ----------
        baudrate : int
            Baudrate to set on the UART bus.

        Raises
        ------
        ValueError
            If given baudrate in not supported by PSLab board.
        """
        brgval = self._get_uart_brgval(baudrate)

        if self._MIN_BRGVAL <= brgval <= self._MAX_BRGVAL:
            self._device.send_byte(CP.UART_2)
            self._device.send_byte(CP.SET_BAUD)
            self._device.send_int(brgval)
            self._device.get_ack()
            self._save_config(brgval=brgval)
        else:
            min_baudrate = self._get_uart_baudrate(self._MIN_BRGVAL)
            max_baudrate = self._get_uart_baudrate(self._MAX_BRGVAL)
            e = f"Baudrate must be between {min_baudrate} and {max_baudrate}."
            raise ValueError(e)

    def _set_uart_mode(self, pd: int, st: int):
        """Set UART mode.

        Parameters
        ----------
        pd : {0, 1, 2, 3}
            Parity and data selection bits.
            {0: 8-bit data and no parity,
             1: 8-bit data and even parity,
             2: 8-bit data and odd parity,
             3: 9-bit data and no parity}
        st : {0, 1}
            Selects number of stop bits for each one-byte UART transmission.
            {0: one stop bit,
             1: two stop bits}

        Raises
        ------
        ValueError
            If any one of arguments is not in its shown range.
        RuntimeError
            If this functionality is not supported by the firmware.
            Since it is newly implemented, earlier firmware version don't support.
        """
        error_message = []
        if pd not in range(0, 4):
            error_message.append("Parity and data selection bits must be 2-bits.")
        if st not in (0, 1):
            error_message.append("Stop bits select must be a bit.")
        # Verifying whether the firmware support current subcommand.
        if self._device.version not in ["PSLab V6"]:
            raise RuntimeError(
                "This firmware version doesn't support this functionality."
            )

        self._device.send_byte(CP.UART_2)
        self._device.send_byte(CP.SET_MODE)
        self._device.send_byte((pd << 1) | st)
        self._device.get_ack()
        self._save_config(mode=(pd, st))

    def _read_uart_status(self) -> int:
        """Return whether receive buffer has data.

        Returns
        -------
        status : int
            1 if at least one more character can be read else 0.
        """
        self._device.send_byte(CP.UART_2)
        self._device.send_byte(CP.READ_UART2_STATUS)
        return self._device.get_byte()

    def _write_byte(self, data: int):
        """Write a single byte to the UART bus.

        It is a primitive UART method, prefered to use :meth:`UART.write_byte`.

        Parameters
        ----------
        data : int
            Byte value to write to the UART bus.
        """
        self._device.send_byte(CP.UART_2)
        self._device.send_byte(CP.SEND_BYTE)
        self._device.send_byte(data)

        if self._device.firmware.major < 3:
            self._device.get_ack()

    def _write_int(self, data: int):
        """Write a single int to the UART bus.

        It is a primitive UART method, prefered to use :meth:`UART.write_int`.

        Parameters
        ----------
        data : int
            Int value to write to the UART bus.
        """
        self._device.send_byte(CP.UART_2)
        self._device.send_byte(CP.SEND_INT)
        self._device.send_int(data)
        self._device.get_ack()

    def _read_byte(self) -> int:
        """Read a single byte from the UART bus.

        It is a primitive UART method, prefered to use :meth:`UART.read_byte`.

        Returns
        -------
        data : int
            A Byte interpreted as a uint8 read from the UART bus.
        """
        self._device.send_byte(CP.UART_2)
        self._device.send_byte(CP.READ_BYTE)
        return self._device.get_byte()

    def _read_int(self) -> int:
        """Read a two byte value from the UART bus.

        It is a primitive UART method, prefered to use :meth:`UART.read_int`.

        Returns
        -------
        data : int
            Two bytes interpreted as a uint16 read from the UART bus.
        """
        self._device.send_byte(CP.UART_2)
        self._device.send_byte(CP.READ_INT)
        return self._device.get_int()


class UART(_UARTPrimitive):
    """UART2 bus.

    Parameters
    ----------
    device : :class:`SerialHandler`, optional
        Serial connection to PSLab device. If not provided, a new one will be created.
    """

    def __init__(self, device: SerialHandler = None):
        super().__init__(device)
        # Reset baudrate and mode
        self.configure(self._get_uart_baudrate(_BRGVAL))

        try:
            self._set_uart_mode(*_MODE)
        except RuntimeError:
            pass

    def configure(self, baudrate: float):
        """Configure UART bus baudrate.

        Parameters
        ----------
        baudrate : float

        Raises
        ------
        ValueError
            If given baudrate is not supported by PSLab board.
        """
        self._set_uart_baud(baudrate)

    def write_byte(self, data: int):
        """Write a single byte to the UART bus.

        Parameters
        ----------
        data : int
            Byte value to write to the UART bus.
        """
        self._write_byte(data)

    def write_int(self, data: int):
        """Write a single int to the UART bus.

        Parameters
        ----------
        data : int
            Int value to write to the UART bus.
        """
        self._write_int(data)

    def read_byte(self) -> int:
        """Read a single byte from the UART bus.

        Returns
        -------
        data : int
            A Byte interpreted as a uint8 read from the UART bus.
        """
        return self._read_byte()

    def read_int(self) -> int:
        """Read a two byte value from the UART bus.

        It is a primitive UART method, prefered to use :meth:`UART.read_int`.

        Returns
        -------
        data : int
            Two bytes interpreted as a uint16 read from the UART bus.
        """
        return self._read_int()
