"""Objects related to the PSLab's analog input channels.

This module contains several module level variables with details on the analog
inputs' capabilities, including possible gain values, voltage ranges, and
firmware-interal enumeration.

This module also contains the AnalogInput class, an instance of which functions
as a model of a particular analog input.
"""

import logging
from typing import List, Union

import numpy as np

logger = logging.getLogger(__name__)

GAIN_VALUES = (1, 2, 4, 5, 8, 10, 16, 32)

ANALOG_CHANNELS = (
    "CH1",
    "CH2",
    "CH3",
    "MIC",
    "CAP",
    "RES",
    "VOL",
    "AN4",
)

INPUT_RANGES = {
    "CH1": (16.5, -16.5),  # Specify inverted channels explicitly by reversing range!
    "CH2": (16.5, -16.5),
    "CH3": (-3.3, 3.3),  # external gain control analog input
    "MIC": (-3.3, 3.3),  # connected to MIC amplifier
    "CAP": (0, 3.3),
    "RES": (0, 3.3),
    "VOL": (0, 3.3),
    "AN4": (0, 3.3),
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

    Attributes
    ----------
    samples_in_buffer : int
        Number of samples collected on this channel currently being held in the
        device's ADC buffer.
    buffer_idx : int or None
        Location in the device's ADC buffer where the samples are stored. None
        if no samples captured by this channel are currently held in the
        buffer.
    chosa : int
        Number used to refer to this channel in the firmware.
    """

    def __init__(self, name: str):
        self._name = name
        self._resolution = 2 ** 10 - 1

        if self._name == "CH1":
            self.programmable_gain_amplifier = 1
            self._gain = 1
        elif self._name == "CH2":
            self.programmable_gain_amplifier = 2
            self._gain = 1
        else:
            self.programmable_gain_amplifier = None
            self._gain = 1

        self.samples_in_buffer = 0
        self.buffer_idx = None
        self._scale = np.poly1d(0)
        self._unscale = np.poly1d(0)
        self.chosa = PIC_ADC_MULTIPLEX[self._name]
        self._calibrate()

    @property
    def gain(self) -> Union[int, None]:
        """int: Analog gain.

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

        self._gain = value
        self._calibrate()

    @property
    def resolution(self) -> int:
        """int: Resolution in bits.

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

        Inverse of :meth:`unscale`.

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

        Inverse of :meth:`scale`.

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


class AnalogOutput:
    """Model of the PSLab's analog outputs.

    Parameters
    ----------
    name : str
        Name of the analog output pin represented by this instance.

    Attributes
    ----------
    frequency : float
        Frequency of the waveform on this pin in Hz.
    wavetype : {'sine', 'tria', 'custom'}
        Type of waveform on this pin. 'sine' is a sine wave with amplitude
        3.3 V, 'tria' is a triangle wave with amplitude 3.3 V, 'custom' is any
        other waveform set with :meth:`load_equation` or :meth:`load_table`.
    """

    RANGE = (-3.3, 3.3)

    def __init__(self, name):
        self.name = name
        self.frequency = 0
        self.wavetype = "sine"
        self._waveform_table = self.RANGE[1] * np.sin(
            np.arange(
                self.RANGE[0], self.RANGE[1], (self.RANGE[1] - self.RANGE[0]) / 512
            )
        )

    @property
    def waveform_table(self) -> np.ndarray:
        """numpy.ndarray: 512-value waveform table loaded on this output."""
        # A form of amplitude control. Max PWM duty cycle out of 512 clock cycles.
        return self._range_normalize(self._waveform_table, 511)

    @waveform_table.setter
    def waveform_table(self, points: np.ndarray):
        if max(points) - min(points) > self.RANGE[1] - self.RANGE[0]:
            logger.warning(f"Analog output {self.name} saturated.")
        self._waveform_table = np.clip(points, self.RANGE[0], self.RANGE[1])

    @property
    def lowres_waveform_table(self) -> np.ndarray:
        """numpy.ndarray: 32-value waveform table loaded on this output."""
        # Max PWM duty cycle out of 64 clock  cycles.
        return self._range_normalize(self._waveform_table[::16], 63)

    def _range_normalize(self, x: np.ndarray, norm: int = 1) -> np.ndarray:
        """Normalize waveform table to the digital output range."""
        x = (x - self.RANGE[0]) / (self.RANGE[1] - self.RANGE[0]) * norm
        return np.int16(np.round(x)).tolist()
