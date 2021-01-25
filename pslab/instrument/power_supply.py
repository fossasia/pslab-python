"""Control voltage and current with the PSLab's PV1, PV2, PV3, and PCS pins.

Examples
--------
>>> from pslab import PowerSupply
>>> ps = PowerSupply()
>>> ps.pv1 = 4.5
>>> ps.pv1
4.499389499389499

>>> ps.pcs = 2e-3
>>> ps.pcs
0.00200014652014652
"""
import numpy as np

from pslab.bus.i2c import I2CSlave
from pslab.serial_handler import SerialHandler


class PowerSupply:
    """Control the PSLab's programmable voltage and current sources.

    An instance of PowerSupply controls three programmable voltage sources on
    pins PV1, PV2, and PV3, as well as a programmable current source on pin
    PCS. The voltage/current on each source can be set via the voltage/current
    properties of each source.

    Parameters
    ----------
    device : :class:`SerialHandler`
        Serial connection with which to communicate with the device. A new
        instance will be created automatically if not specified.
    """

    _ADDRESS = 0x60

    def __init__(self, device: SerialHandler = None):
        self._device = device if device is not None else SerialHandler()
        self._mcp4728 = I2CSlave(self._ADDRESS, self._device)
        self._pv1 = VoltageSource(self._mcp4728, "PV1")
        self._pv2 = VoltageSource(self._mcp4728, "PV2")
        self._pv3 = VoltageSource(self._mcp4728, "PV3")
        self._pcs = CurrentSource(self._mcp4728)

    @property
    def pv1(self):
        """float: Voltage on PV1; range [-5, 5] V."""
        return self._pv1.voltage

    @pv1.setter
    def pv1(self, value: float):
        self._pv1.voltage = value

    @property
    def pv2(self):
        """float: Voltage on PV2; range [-3.3, 3.3] V."""
        return self._pv2.voltage

    @pv2.setter
    def pv2(self, value: float):
        self._pv2.voltage = value

    @property
    def pv3(self):
        """float: Voltage on PV3; range [0, 3.3] V."""
        return self._pv3.voltage

    @pv3.setter
    def pv3(self, value: float):
        self._pv3.voltage = value

    @property
    def pcs(self):
        """float: Current on PCS; range [0, 3.3e-3] A.

        Notes
        -----
        The maximum available current that can be output by the current source
        is dependent on load resistance:

            I_max = 3.3 V / (1 kΩ + R_load)

        For example, the maximum current that can be driven across a 100 Ω load
        is 3.3 V / 1.1 kΩ = 3 mA. If the load is 10 kΩ, the maximum current is
        only 3.3 V / 11 kΩ = 300 µA.

        Be careful to not set a current higher than available for a given load.
        If a current greater than the maximum for a certain load is requested,
        the actual current will instead be much smaller. For example, if a
        current of 3 mA is requested when connected to a 1 kΩ load, the actual
        current will be only a few hundred µA instead of the maximum available
        1.65 mA.
        """
        return self._pcs.current

    @pcs.setter
    def pcs(self, value: float):
        self._pcs.current = value

    @property
    def _registers(self):
        """Return the contents of the MCP4728's input registers and EEPROM."""
        return self._mcp4728.read(24)


class Source:
    """Base class for voltage/current/power sources."""

    _RANGE = {
        "PV1": (-5, 5),
        "PV2": (-3.3, 3.3),
        "PV3": (0, 3.3),
        "PCS": (3.3e-3, 0),
    }
    _CHANNEL_NUMBER = {
        "PV1": 3,
        "PV2": 2,
        "PV3": 1,
        "PCS": 0,
    }
    _RESOLUTION = 2 ** 12 - 1
    _MULTI_WRITE = 0b01000000

    def __init__(self, mcp4728: I2CSlave, name: str):
        self._mcp4728 = mcp4728
        self.name = name
        self.channel_number = self._CHANNEL_NUMBER[self.name]
        slope = self._RANGE[self.name][1] - self._RANGE[self.name][0]
        intercept = self._RANGE[self.name][0]
        self._unscale = np.poly1d(
            [self._RESOLUTION / slope, -self._RESOLUTION * intercept / slope]
        )
        self._scale = np.poly1d([slope / self._RESOLUTION, intercept])

    def unscale(self, voltage: float) -> int:
        """Return integer representation of a voltage.

        Parameters
        ----------
        voltage : float
            Voltage in Volt.

        Returns
        -------
        raw : int
            Integer represention of the voltage.
        """
        return int(round(self._unscale(voltage)))

    def scale(self, raw: int) -> float:
        """Convert an integer value to a voltage value.

        Parameters
        ----------
        raw : int
            Integer representation of a voltage value.

        Returns
        -------
        voltage : float
            Voltage in Volt.
        """
        return self._scale(raw)

    def _multi_write(self, raw: int):
        channel_select = self.channel_number << 1
        command_byte = self._MULTI_WRITE | channel_select
        data_byte1 = (raw >> 8) & 0x0F
        data_byte2 = raw & 0xFF
        self._mcp4728.write([data_byte1, data_byte2], register_address=command_byte)


class VoltageSource(Source):
    """Helper class for interfacing with PV1, PV2, and PV3."""

    def __init__(self, mcp4728: I2CSlave, name: str):
        self._voltage = 0
        super().__init__(mcp4728, name)

    @property
    def voltage(self):
        """float: Most recent voltage set on PVx in Volt.

        The voltage on PVx can be set by writing to this attribute.
        """
        return self._voltage

    @voltage.setter
    def voltage(self, value: float):
        raw = self.unscale(value)
        raw = int(np.clip(raw, 0, self._RESOLUTION))
        self._multi_write(raw)
        self._voltage = self.scale(raw)


class CurrentSource(Source):
    """Helper class for interfacing with PCS."""

    def __init__(self, mcp4728: I2CSlave):
        self._current = 0
        super().__init__(mcp4728, "PCS")

    @property
    def current(self):
        """float: Most recent current value set on PCS in Ampere.

        The current on PCS can be set by writing to this attribute.
        """
        return self._current

    @current.setter
    def current(self, value: float):
        raw = 0 if value == 0 else self.unscale(value)
        raw = int(np.clip(raw, 0, self._RESOLUTION))
        self._multi_write(raw)
        self._current = self.scale(raw)
