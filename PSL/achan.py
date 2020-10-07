"""Objects related to the PSLab's analog input channels.

This module contains several module level variables with details on the analog inputs'
capabilities, including possible gain values, voltage ranges, and firmware-interal
enumeration.

This module also contains the AnalogInput class, an instance of which functions as a
model of a particular analog input.
"""

from typing import List, Union

import numpy as np

import PSL.commands_proto as CP
from PSL import packet_handler

GAIN_VALUES = (1, 2, 4, 5, 8, 10, 16, 32)

ANALOG_CHANNELS = (
    "CH1",
    "CH2",
    "CH3",
    "MIC",
    "CAP",
    "RES",
    "VOL",
)

INPUT_RANGES = {
    "CH1": (16.5, -16.5),  # Specify inverted channels explicitly by reversing range!
    "CH2": (16.5, -16.5),
    "CH3": (-3.3, 3.3),  # external gain control analog input
    "MIC": (-3.3, 3.3),  # connected to MIC amplifier
    "CAP": (0, 3.3),
    "RES": (0, 3.3),
    "VOL": (0, 3.3),
}

PIC_ADC_MULTIPLEX = {
    "CH1": 3,
    "CH2": 0,
    "CH3": 1,
    "MIC": 2,
    "AN4": 4,
    "RES": 7,
    "CAP": 5,
    "VOL": 8,
}


class AnalogInput:
    """Model of the PSLab's analog inputs, used to scale raw values to voltages.

    Parameters
    ----------
    name : {'CH1', 'CH2', 'CH3', 'MIC', 'CAP', 'RES', 'VOL'}
        Name of the analog channel to model.
    device : :class:`Handler`
        Serial interface for communicating with the PSLab device.

    Attributes
    ----------
    gain
    resolution
    samples_in_buffer : int
        Number of samples collected on this channel currently being held in the
        device's ADC buffer.
    buffer_idx : Union[int, None]
        Location in the device's ADC buffer where the samples are stored. None if no
        samples captured by this channel are currently held in the buffer.
    chosa : int
        Number used to refer to this channel in the firmware.
    """

    def __init__(self, name: str, device: packet_handler.Handler):
        self._name = name
        self._device = device

        if self._name == "CH1":
            self._programmable_gain_amplifier = 1
        elif self._name == "CH2":
            self._programmable_gain_amplifier = 2
        else:
            self._programmable_gain_amplifier = None

        self._gain = 1
        self._resolution = 2 ** 10 - 1
        self.samples_in_buffer = 0
        self.buffer_idx = None
        self._scale = np.poly1d(0)
        self._unscale = np.poly1d(0)
        self.chosa = PIC_ADC_MULTIPLEX[self._name]
        self._calibrate()

    @property
    def gain(self) -> Union[int, float, None]:
        """Get or set the analog gain.

        Setting a new gain level will automatically recalibrate the channel.
        On channels other than CH1 and CH2 gain is None.

        Raises
        ------
        TypeError
            If gain is set on a channel which does not support it.
        ValueError
            If a gain value other than 1, 2, 4, 5, 8, 10, 16, 32 is set.
        """
        if self._name in ("CH1", "CH2"):
            return self._gain
        else:
            return None

    @gain.setter
    def gain(self, value: Union[int, float]):
        if self._name not in ("CH1", "CH2"):
            raise TypeError(f"Analog gain is not available on {self._name}.")

        if value not in GAIN_VALUES:
            raise ValueError(f"Invalid gain. Valid values are {GAIN_VALUES}.")

        gain_idx = GAIN_VALUES.index(value)
        self._device.send_byte(CP.ADC)
        self._device.send_byte(CP.SET_PGA_GAIN)
        self._device.send_byte(self._programmable_gain_amplifier)
        self._device.send_byte(gain_idx)
        self._device.get_ack()
        self._gain = value
        self._calibrate()

    @property
    def resolution(self) -> int:
        """Get or set the resolution in bits.

        Setting a new resolution will automatically recalibrate the channel.

        Raises
        ------
        ValueError
            If a resolution other than 10 or 12 is set.
        """
        return int(np.log2((self._resolution + 1)))

    @resolution.setter
    def resolution(self, value: int):
        if value not in (10, 12):
            raise ValueError("Resolution must be 10 or 12 bits.")
        self._resolution = 2 ** value - 1
        self._calibrate()

    def _calibrate(self):
        A = INPUT_RANGES[self._name][0] / self._gain
        B = INPUT_RANGES[self._name][1] / self._gain
        slope = B - A
        intercept = A
        self._scale = np.poly1d([slope / self._resolution, intercept])
        self._unscale = np.poly1d(
            [self._resolution / slope, -self._resolution * intercept / slope]
        )

    def scale(self, raw: Union[int, List[int]]) -> float:
        """Translate raw integer value from device to corresponding voltage.

        Inverse of :meth:`unscale. <PSL.achan.AnalogInputSource.unscale>`.

        Parameters
        ----------
        raw : int, List[int]
            An integer, or a list of integers, received from the device.

        Returns
        -------
        float
            Voltage, translated from raw based on channel range, gain, and resolution.
        """
        return self._scale(raw)

    def unscale(self, voltage: float) -> int:
        """Translate a voltage to a raw integer value interpretable by the device.

        Inverse of :meth:`scale. <PSL.achan.AnalogInputSource.scale>`.

        Parameters
        ----------
        voltage : float
            Voltage in volts.

        Returns
        -------
        int
            Corresponding integer value, adjusted for resolution and gain and clipped
            to the channel's range.
        """
        level = self._unscale(voltage)
        level = np.clip(level, 0, self._resolution)
        level = np.round(level)
        return int(level)
