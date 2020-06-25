from math import isclose

import numpy as np

GAIN_VALUES = (1, 2, 4, 5, 8, 10, 16, 32, 1 / 11)
gains = GAIN_VALUES  # Backwards compatibility

ALL_ANALOG_CHANNELS = (
    "CH1",
    "CH2",
    "CH3",
    "MIC",
    "CAP",
    "SEN",
    "AN8",
)
allAnalogChannels = ALL_ANALOG_CHANNELS  # Backwards compatibility

INPUT_RANGES = {
    "CH1": (16.5, -16.5),  # Specify inverted channels explicitly by reversing range!
    "CH2": (16.5, -16.5),
    "CH3": (-3.3, 3.3),  # external gain control analog input
    "MIC": (-3.3, 3.3),  # connected to MIC amplifier
    "CAP": (0, 3.3),
    "SEN": (0, 3.3),
    "AN8": (0, 3.3),
}

PIC_ADC_MULTIPLEX = {
    "CH1": 3,
    "CH2": 0,
    "CH3": 1,
    "MIC": 2,
    "AN4": 4,
    "SEN": 7,
    "CAP": 5,
    "AN8": 8,
}

RESOLUTION_10BIT = 2 ** 10 - 1
RESOLUTION_12BIT = 2 ** 12 - 1


class AnalogInputSource:
    def __init__(self, name, **kwargs):
        self.name = name  # The generic name of the input. like 'CH1', 'IN1' etc.

        if name == "CH1":
            self.programmable_gain_amplifier = 1
        elif name == "CH2":
            self.programmable_gain_amplifier = 2
        else:
            self.programmable_gain_amplifier = None

        self.cal_poly10 = np.poly1d([3.3 / RESOLUTION_10BIT, 0])
        self.cal_poly12 = np.poly1d([3.3 / RESOLUTION_12BIT, 0])
        self.calibration_ready = False
        self.chosa = PIC_ADC_MULTIPLEX[self.name]
        self.adc_shifts = []
        self.polynomials = []
        self.gain_idx = 0
        self.reset_calibration()

        # Backwards compatibility
        self.gainPGA = self.programmable_gain_amplifier
        self.CHOSA = self.chosa
        self.calPoly10 = self.cal_poly10
        self.calPoly12 = self.cal_poly12
        self.calibrationReady = self.calibration_ready
        self.regenerateCalibration = self.reset_calibration
        self.setGain = self.set_gain

    def set_gain(self, g):
        if self.name not in ("CH1", "CH2"):
            raise RuntimeError(f"Analog gain is not available on {self.name}")
        self.gain_idx = GAIN_VALUES.index(g)
        self.reset_calibration()

    def load_calibration_table(self, table, slope, intercept):
        self.adc_shifts = np.array(table) * slope - intercept

    def _ignore_calibration(self):
        self.calibration_ready = False

    def load_polynomials(self, polys):
        self.polynomials = []
        for p in polys:
            epoly = [float(b) for b in p]
            self.polynomials.append(np.poly1d(epoly))

    def reset_calibration(self):
        B = INPUT_RANGES[self.name][1]
        A = INPUT_RANGES[self.name][0]

        if self.gain_idx is not None:
            gain = GAIN_VALUES[self.gain_idx]
            B /= gain
            A /= gain

        slope = B - A
        intercept = A

        if self.calibration_ready and self.gain_idx != 8:
            self.cal_poly10 = self._cal10
            self.cal_poly12 = self._cal12
        else:  # special case for 1/11 gain
            self.cal_poly10 = np.poly1d([slope / RESOLUTION_10BIT, intercept])
            self.cal_poly12 = np.poly1d([slope / RESOLUTION_12BIT, intercept])

        self.volt2code10 = np.poly1d(
            [RESOLUTION_10BIT / slope, -RESOLUTION_10BIT * intercept / slope]
        )
        self.voltToCode10 = self.volt2code10  # Backwards compatibility
        self.volt2code12 = np.poly1d(
            [RESOLUTION_12BIT / slope, -RESOLUTION_12BIT * intercept / slope]
        )
        self.voltToCode12 = self.volt2code12  # Backwards compatibility

    def _cal12(self, raw):
        avg_shifts = (
            self.adc_shifts[np.floor(raw)] + self.adc_shifts[np.ceil(raw)]
        ) / 2  # Interpolate instead?
        raw -= RESOLUTION_12BIT * avg_shifts / 3.3

        return self.polynomials[self.gain_idx](raw)

    def _cal10(self, raw):
        raw *= RESOLUTION_12BIT / RESOLUTION_10BIT
        avg_shifts = (
            self.adc_shifts[np.floor(raw)] + self.adc_shifts[np.ceil(raw)]
        ) / 2  # Interpolate instead?
        raw -= RESOLUTION_12BIT * avg_shifts / 3.3

        return self.polynomials[self.gain_idx](raw)


analogInputSource = AnalogInputSource  # Backwards compatibility


class AnalogAcquisitionChannel(AnalogInputSource):
    """Takes care of oscilloscope data fetched from the device.

    Each instance may be linked to a particular input. Since only up to two channels
    may be captured at a time with the PSLab, only two instances will be required.

    Each instance will be linked to a particular inputSource instance by the capture
    routines. When data is requested , it will return after applying calibration and
    gain details stored in the selected inputSource.
    """

    def __init__(
        self,
        channel: str,
        resolution: int = 10,
        length: int = 100,
        timebase: float = 1.0,
    ):
        self.resolution = resolution
        self.length = length
        self.timebase = timebase
        self._xaxis = np.zeros(10000)
        self._yaxis = np.zeros(10000)
        self._update_xaxis()
        super().__init__(channel)

    def fix_value(self, val):
        if self.resolution == 12:
            return self.cal_poly12(val)
        else:
            return self.cal_poly10(val)

    @property
    def xaxis(self) -> np.ndarray:
        return self._xaxis[: self.length]

    @xaxis.setter
    def xaxis(self, value: np.ndarray):
        self._xaxis[: self.length] = value

    def _update_xaxis(self):
        self.xaxis = self.timebase * np.arange(self.length)

    @property
    def yaxis(self):
        return self._yaxis[: self.length]

    @yaxis.setter
    def yaxis(self, value):
        self._yaxis[: self.length] = value

    # Backwards compatibility
    def set_params(self, channel, resolution, length, timebase, **keys):
        if channel != self.name:
            self.__init__(channel, resolution, length, timebase)
        else:
            self.resolution = resolution
            self.length = length
            self.timebase = timebase
            self._update_xaxis()

    def set_xval(self, pos, val):
        self.xaxis[pos] = val

    def set_yval(self, pos, val):
        self.yaxis[pos] = self.fix_value(val)

    def get_xaxis(self):
        return self.xaxis

    def get_yaxis(self):
        return self.yaxis


analogAcquisitionChannel = AnalogAcquisitionChannel  # Backwards compatibility
