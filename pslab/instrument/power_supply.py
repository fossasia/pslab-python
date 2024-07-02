"""Control voltage and current with the PSLab's PV1, PV2, PV3, and PCS pins.

Examples
--------
>>> from pslab import PowerSupply
>>> ps = PowerSupply()
>>> ps.pv1 = 4.5
>>> ps.pv1
4.5

>>> ps.pcs = 2e-3
>>> ps.pcs
0.002
"""

import pslab.protocol as CP
from pslab.serial_handler import SerialHandler


class PowerSupply:
    """Control the PSLab's programmable voltage and current sources.

    An instance of PowerSupply controls three programmable voltage sources on
    pins PV1, PV2, and PV3, as well as a programmable current source on pin
    PCS.

    Parameters
    ----------
    device : :class:`SerialHandler`
        Serial connection with which to communicate with the device. A new
        instance will be created automatically if not specified.
    """

    _REFERENCE = 3300
    _PV1_CH = 3
    _PV1_RANGE = (-5, 5)
    _PV2_CH = 2
    _PV2_RANGE = (-3.3, 3.3)
    _PV3_CH = 1
    _PV3_RANGE = (0, 3.3)
    _PCS_CH = 0
    _PCS_RANGE = (3.3e-3, 0)

    def __init__(self, device: SerialHandler = None):
        self._device = device if device is not None else SerialHandler()
        self._pv1 = None
        self._pv2 = None
        self._pv3 = None
        self._pcs = None

    def _set_power(self, channel, output):
        self._device.send_byte(CP.DAC)
        self._device.send_byte(CP.SET_POWER)
        self._device.send_byte(channel)
        self._device.send_int(output)
        return self._device.get_ack()

    @staticmethod
    def _bound(value, output_range):
        return max(min(value, max(output_range)), min(output_range))

    def _scale(self, value, output_range):
        scaled = (value - output_range[0]) / (output_range[1] - output_range[0])
        return int(scaled * self._REFERENCE)

    @property
    def pv1(self):
        """float: Voltage on PV1; range [-5, 5] V."""
        return self._pv1

    @pv1.setter
    def pv1(self, value: float):
        value = self._bound(value, self._PV1_RANGE)
        ret = self._set_power(self._PV1_CH, self._scale(value, self._PV1_RANGE))
        self._pv1 = value
        return ret

    @property
    def pv2(self):
        """float: Voltage on PV2; range [-3.3, 3.3] V."""
        return self._pv2

    @pv2.setter
    def pv2(self, value: float):
        value = self._bound(value, self._PV2_RANGE)
        self._set_power(self._PV2_CH, self._scale(value, self._PV2_RANGE))
        self._pv2 = value

    @property
    def pv3(self):
        """float: Voltage on PV3; range [0, 3.3] V."""
        return self._pv3

    @pv3.setter
    def pv3(self, value: float):
        value = self._bound(value, self._PV3_RANGE)
        self._set_power(self._PV3_CH, self._scale(value, self._PV3_RANGE))
        self._pv3 = value

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
        return self._pcs

    @pcs.setter
    def pcs(self, value: float):
        value = self._bound(value, self._PCS_RANGE)
        self._set_power(self._PCS_CH, self._scale(value, self._PCS_RANGE))
        self._pcs = value
