"""Convenience module that creates instances of every instrument for you.

Every PSLab instrument can be imported and instantiated individually. However,
if you need to use several at once the ScienceLab class provides a convenient
collection.
"""

from __future__ import annotations

import time
from typing import Iterable, List

import pslab.protocol as CP
from pslab.connection import ConnectionHandler, SerialHandler, autoconnect
from pslab.instrument.logic_analyzer import LogicAnalyzer
from pslab.instrument.multimeter import Multimeter
from pslab.instrument.oscilloscope import Oscilloscope
from pslab.instrument.power_supply import PowerSupply
from pslab.instrument.waveform_generator import PWMGenerator, WaveformGenerator


class ScienceLab:
    """Aggregate interface for the PSLab's instruments.

    Attributes
    ----------
    logic_analyzer : pslab.LogicAnalyzer
    oscilloscope : pslab.Oscilloscope
    waveform_generator : pslab.WaveformGenerator
    pwm_generator : pslab.PWMGenerator
    multimeter : pslab.Multimeter
    power_supply : pslab.PowerSupply
    i2c : pslab.I2CMaster
    nrf : pslab.peripherals.NRF24L01
    """

    def __init__(self, device: ConnectionHandler | None = None):
        self.device = device if device is not None else autoconnect()
        self.firmware = self.device.get_firmware_version()
        self.logic_analyzer = LogicAnalyzer(device=self.device)
        self.oscilloscope = Oscilloscope(device=self.device)
        self.waveform_generator = WaveformGenerator(device=self.device)
        self.pwm_generator = PWMGenerator(device=self.device)
        self.multimeter = Multimeter(device=self.device)
        self.power_supply = PowerSupply(device=self.device)

    @property
    def temperature(self):
        """float: Temperature of the MCU in degrees Celsius."""
        # TODO: Get rid of magic numbers.
        cs = 3
        V = self._get_ctmu_voltage(0b11110, cs, 0)

        if cs == 1:
            return (646 - V * 1000) / 1.92  # current source = 1
        elif cs == 2:
            return (701.5 - V * 1000) / 1.74  # current source = 2
        elif cs == 3:
            return (760 - V * 1000) / 1.56  # current source = 3

    def _get_ctmu_voltage(self, channel: int, current_range: int, tgen: bool = True):
        """Control the Charge Time Measurement Unit (CTMU).

        ctmu_voltage(5, 2) will activate a constant current source of 5.5 µA on
        CAP and then measure the voltage at the output.

        If a diode is used to connect CAP to ground, the forward voltage drop
        of the diode will be returned, e.g. 0.6 V for a 4148 diode.

        If a resistor is connected, Ohm's law will be followed within
        reasonable limits.

        Parameters
        ----------
        channel : int
            Pin number on which to generate a current and measure output
            voltage. Refer to the PIC24EP64GP204 datasheet for channel
            numbering.
        current_range : {0, 1, 2, 3}
            0 -> 550 µA
            1 -> 550 nA
            2 -> 5.5 µA
            3 -> 55 µA
        tgen : bool, optional
            Use Time Delay mode instead of Measurement mode. The default value
            is True.

        Returns
        -------
        voltage : float
        """
        self.device.send_byte(CP.COMMON)
        self.device.send_byte(CP.GET_CTMU_VOLTAGE)
        self.device.send_byte((channel) | (current_range << 5) | (tgen << 7))
        raw_voltage = self.get_int() / 16  # 16*voltage across the current source
        self.device.get_ack()
        vmax = 3.3
        resolution = 12
        voltage = vmax * raw_voltage / (2**resolution - 1)
        return voltage

    def _start_ctmu(self, current_range: int, trim: int, tgen: int = 1):
        self.device.send_byte(CP.COMMON)
        self.device.send_byte(CP.START_CTMU)
        self.device.send_byte((current_range) | (tgen << 7))
        self.device.send_byte(trim)
        self.device.get_ack()

    def _stop_ctmu(self):
        self.device.send_byte(CP.COMMON)
        self.device.send_byte(CP.STOP_CTMU)
        self.device.get_ack()

    def reset(self):
        """Reset the device."""
        self.device.send_byte(CP.COMMON)
        self.device.send_byte(CP.RESTORE_STANDALONE)

    def enter_bootloader(self):
        """Reboot and stay in bootloader mode."""
        if not isinstance(self.device, SerialHandler):
            msg = "cannot enter bootloader over wireless"
            raise RuntimeError(msg)

        self.reset()
        self.device.interface.baudrate = 460800
        # The PSLab's RGB LED flashes some colors on boot.
        boot_lightshow_time = 0.6
        # Wait before sending magic number to make sure UART is initialized.
        time.sleep(boot_lightshow_time / 2)
        # PIC24 UART RX buffer is four bytes deep; no need to time it perfectly.
        self.device.write(CP.Integer.pack(0xDECAFBAD))
        # Wait until lightshow is done to prevent accidentally overwriting magic number.
        time.sleep(boot_lightshow_time)

    def rgb_led(self, colors: List, output: str = "RGB", order: str = "GRB"):
        """Set shade of a WS2812B RGB LED.

        Parameters
        ----------
        colors : list
            List of three values between 0-255, where each value is the
            intensity of red, green, and blue, respectively. When daisy
            chaining several LEDs, colors should be a list of three-value
            lists.
        output : {"RGB", "PGC", "SQ1"}, optional
            Pin on which to output the pulse train setting the LED color. The
            default value, "RGB", sets the color of the built-in WS2812B
            (PSLab v6 only).
        order : str, optional
            Color order of the connected LED as a three-letter string. The
            built-in LED has order "GRB", which is the default.

        Examples
        --------
        Set the built-in WS2812B to yellow.

        >>> import pslab
        >>> psl = pslab.ScienceLab()
        >>> psl.rgb_led([10, 10, 0])

        Set a chain of three RGB WS2812B connected to SQ1 to red, cyan, and
        magenta.

        >>> psl.rgb_led([[10,0,0],[0,10,10],[10,0,10]], output="SQ1", order="RGB")
        """
        if "6" in self.device.version:
            pins = {"ONBOARD": 0, "SQ1": 1, "SQ2": 2, "SQ3": 3, "SQ4": 4}
        else:
            pins = {"RGB": CP.SET_RGB1, "PGC": CP.SET_RGB2, "SQ1": CP.SET_RGB3}

        try:
            pin = pins[output]
        except KeyError:
            pinnames = ", ".join(pins.keys())
            raise ValueError(
                f"Invalid output: {output}. output must be  one of {pinnames}."
            )

        if not isinstance(colors[0], Iterable):
            colors = [colors]

        if not all([len(color) == 3 for color in colors]):
            raise ValueError("Invalid color; each color list must have three values.")

        order = order.upper()

        if not sorted(order) == ["B", "G", "R"]:
            raise ValueError(
                f"Invalid order: {order}. order must contain 'R', 'G', and 'B'."
            )

        self.device.send_byte(CP.COMMON)

        if "6" in self.device.version:
            self.device.send_byte(CP.SET_RGB_COMMON)
        else:
            self.device.send_byte(pin)

        self.device.send_byte(len(colors) * 3)

        for color in colors:
            self.device.send_byte(color[order.index("R")])
            self.device.send_byte(color[order.index("G")])
            self.device.send_byte(color[order.index("B")])

        if "6" in self.device.version:
            self.device.send_byte(pin)

        self.device.get_ack()

    def _read_program_address(self, address: int):
        """Return the value stored at the specified address in program memory.

        Parameters
        ----------
        address : int
            Address to read from. Refer to PIC24EP64GP204 programming manual.

        Returns
        -------
        data : int
            16-bit wide value read from program memory.
        """
        self.device.send_byte(CP.COMMON)
        self.device.send_byte(CP.READ_PROGRAM_ADDRESS)
        self.device.send_int(address & 0xFFFF)
        self.device.send_int((address >> 16) & 0xFFFF)
        data = self.device.get_int()
        self.device.get_ack()
        return data

    def _device_id(self):
        a = self._read_program_address(0x800FF8)
        b = self._read_program_address(0x800FFA)
        c = self._read_program_address(0x800FFC)
        d = self._read_program_address(0x800FFE)
        val = d | (c << 16) | (b << 32) | (a << 48)
        return val

    def _read_data_address(self, address: int):
        """Return the value stored at the specified address in RAM.

        Parameters
        ----------
        address : int
            Address to read from. Refer to PIC24EP64GP204 programming manual.

        Returns
        -------
        data : int
            16-bit wide value read from RAM.
        """
        self.device.send_byte(CP.COMMON)
        self.device.send_byte(CP.READ_DATA_ADDRESS)
        self.device.send_int(address & 0xFFFF)
        data = self.device.get_int()
        self.device.get_ack()
        return data

    def _write_data_address(self, address: int, value: int):
        """Write a value to the specified address in RAM.

        Parameters
        ----------
        address : int
            Address to write to.  Refer to PIC24EP64GP204 programming manual.
        value : int
            Value to write to RAM.
        """
        self.device.send_byte(CP.COMMON)
        self.device.send_byte(CP.WRITE_DATA_ADDRESS)
        self.device.send_int(address & 0xFFFF)
        self.device.send_int(value)
        self.device.get_ack()

    def enable_uart_passthrough(self, baudrate: int):
        """Relay all data received by the device to TXD/RXD.

        Can be used to load programs into secondary microcontrollers with
        bootloaders such ATMEGA or ESP8266

        Parameters
        ----------
        baudrate : int
            Baudrate of the UART2 bus.
        """
        if self.firmware.major < 3:
            self._uart_passthrough_legacy(baudrate)
        else:
            self._uart_passthrough(baudrate)

    def _uart_passthrough(self, baudrate: int) -> None:
        self.device.send_byte(CP.PASSTHROUGHS)
        self.device.send_byte(CP.PASS_UART)
        self.device.send_int(self._get_brgval(baudrate))
        self.device.baudrate = baudrate

    def _uart_passthrough_legacy(self, baudrate: int) -> None:
        self.device.send_byte(CP.PASSTHROUGHS_LEGACY)
        self.device.send_byte(CP.PASS_UART)
        disable_watchdog = 1
        self.device.send_byte(disable_watchdog)
        self.device.send_int(self._get_brgval(baudrate))

    @staticmethod
    def _get_brgval(baudrate: int) -> int:
        return int((CP.CLOCK_RATE / (4 * baudrate)) - 1)

    def read_log(self):
        """Read hardware debug log.

        Returns
        -------
        log : bytes
            Bytes read from the hardware debug log.
        """
        self.device.send_byte(CP.COMMON)
        self.device.send_byte(CP.READ_LOG)
        log = self.device.interface.readline().strip()
        self.get_ack()
        return log
