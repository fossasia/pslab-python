"""Control voltage and current with the PSLab's PV1, PV2, PV3, and PCS pins.

Examples
--------
>>> from PSL.power_supply import PowerSupply
>>> ps = PowerSupply()
>>> ps.pv1.voltage = 4.5
>>> ps.pv1.voltage
4.499389499389499

>>> ps.pcs.current = 2e-3
>>> ps.pcs.current
0.00200014652014652
"""
import numpy as np

from PSL.i2c import I2CSlave
from PSL.packet_handler import Handler


class PowerSupply:
    """Control the PSLab's programmable voltage and current sources.

    An instance of PowerSupply controls three programmable voltage sources on
    pins PV1, PV2, and PV3, as well as a programmable current source on pin
    PCS. The voltage/current on each source can be set via the voltage/current
    properties of each source.

    Parameters
    ----------
    device : PSL.packet_handler.Handler
        Serial connection with which to communicate with the device. A new
        instance will be created automatically if not specified.

    Attributes
    ----------
    pv1 : VoltageSource
        Use this to set a voltage between -5 V and 5 V on pin PV1.
    pv2 : VoltageSource
        Use this to set a voltage between -3.3 V and 3.3 V on pin PV2.
    pv3 : VoltageSource
        Use this to set a voltage between 0 V and 3.3 V on pin PV3.
    pcs : CurrentSource
        Use this to output a current between 0 A and 3.3 mA on pin PCS. Subject
        to load resistance, see Notes.

    Notes
    -----
    The maximum available current that can be output by the current source is
    dependent on load resistance:

        I_max = 3.3 V / (1 kΩ + R_load)

    For example, the maximum current that can be driven across a 100 Ω load is
    3.3 V / 1.1 kΩ = 3 mA. If the load is 10 kΩ, the maximum current is only
    3.3 V / 11 kΩ = 300µA.

    Be careful to not set a current higher than available for a given load. If
    a current greater than the maximum for a certain load is requested, the
    actual current will instead be much smaller. For example, if a current of
    3 mA is requested when connected to a 1 kΩ load, the actual current will
    be only a few hundred µA instead of the maximum available 1.65 mA.
    """

    ADDRESS = 0x60

    def __init__(self, device: Handler = None):
        self._device = device if device is not None else Handler()
        self._mcp4728 = I2CSlave(self.ADDRESS, self._device)
        self.pv1 = VoltageSource(self._mcp4728, "PV1")
        self.pv2 = VoltageSource(self._mcp4728, "PV2")
        self.pv3 = VoltageSource(self._mcp4728, "PV3")
        self.pcs = CurrentSource(self._mcp4728)

    @property
    def _registers(self):
        """Return the contents of the MCP4728's input registers and EEPROM."""
        return self._mcp4728.read(24)


class _Source:
    RANGE = {
        "PV1": (-5, 5),
        "PV2": (-3.3, 3.3),
        "PV3": (0, 3.3),
        "PCS": (3.3e-3, 0),
    }
    CHANNEL_NUMBER = {
        "PV1": 3,
        "PV2": 2,
        "PV3": 1,
        "PCS": 0,
    }
    RESOLUTION = 2 ** 12 - 1
    MULTI_WRITE = 0b01000000

    def __init__(self, mcp4728: I2CSlave, name: str):
        self._mcp4728 = mcp4728
        self.name = name
        self.channel_number = self.CHANNEL_NUMBER[self.name]
        slope = self.RANGE[self.name][1] - self.RANGE[self.name][0]
        intercept = self.RANGE[self.name][0]
        self._unscale = np.poly1d(
            [self.RESOLUTION / slope, -self.RESOLUTION * intercept / slope]
        )
        self._scale = np.poly1d([slope / self.RESOLUTION, intercept])

    def unscale(self, current: float):
        return int(round(self._unscale(current)))

    def scale(self, raw: int):
        return self._scale(raw)

    def _multi_write(self, raw: int):
        channel_select = self.channel_number << 1
        command_byte = self.MULTI_WRITE | channel_select
        data_byte1 = (raw >> 8) & 0x0F
        data_byte2 = raw & 0xFF
        self._mcp4728.write([data_byte1, data_byte2], register_address=command_byte)


class VoltageSource(_Source):
    """Helper class for interfacing with PV1, PV2, and PV3."""

    def __init__(self, mcp4728: I2CSlave, name: str):
        self._voltage = 0
        super().__init__(mcp4728, name)

    @property
    def voltage(self):
        """float: Most recent voltage set on PVx."""
        return self._voltage

    @voltage.setter
    def voltage(self, value: float):
        raw = self.unscale(value)
        raw = int(np.clip(raw, 0, self.RESOLUTION))
        self._multi_write(raw)
        self._voltage = self.scale(raw)


class CurrentSource(_Source):
    """Helper class for interfacing with PCS."""

    def __init__(self, mcp4728: I2CSlave):
        self._current = 0
        super().__init__(mcp4728, "PCS")

    @property
    def current(self):
        """float: Most recent current value set on PCS."""
        return self._current

    @current.setter
    def current(self, value: float):
        raw = 0 if value == 0 else self.unscale(value)
        raw = int(np.clip(raw, 0, self.RESOLUTION))
        self._multi_write(raw)
        self._current = self.scale(raw)
