"""Control the PSLab's waveform generators.

Two types of waveform generator are available: WaveformGenerator and
PWMGenerator. WaveformGenerator can output arbitrary waveforms on pins SI1 and
SI2. PWMGenerator can output square waveforms on pins SQ1, SQ2, SQ3, and SQ4.
"""

import logging
from typing import Callable, List, Tuple, Union

import numpy as np

import pslab.protocol as CP
from pslab.instrument.analog import AnalogOutput
from pslab.instrument.digital import DigitalOutput, DIGITAL_OUTPUTS
from pslab.serial_handler import SerialHandler

logger = logging.getLogger(__name__)

_PRESCALERS = [1, 8, 64, 256]


def _listify(channel, maxlen, *args):
    if not isinstance(channel, list):
        channel = [channel]
    elif len(channel) > maxlen:
        raise ValueError("Too many channels.")

    ret = [channel]

    for arg in args:
        if isinstance(arg, list):
            if len(arg) == len(channel):
                ret.append(arg)
            else:
                raise ValueError("Dimension mismatch.")
        else:
            ret.append(len(channel) * [arg])

    return ret


def _get_wavelength(frequency: float, table_size: int = 1) -> Tuple[int, int]:
    """Get the wavelength of a PWM signal in clock cycles, and the clock prescaler.

    For an analog signal, the wavelength of the underlying PWM signal is equal
    to the time gap between two points in the analog waveform.

    Parameters
    ----------
    frequency : float
        Frequency of the signal in Hz.
    table_size : int, optional
        Number of points in the analog signal. The default value is 1, which
        implies a digital signal.

    Returns
    -------
    wavelength : int
        Signal wavelength in clock cycles.
    prescaler : int
        Factor by which the clock rate is reduced, e.g. a prescaler of 64 means
        that the clock rate is 1 Mhz instead of the original 64 MHz.
    """
    for prescaler in _PRESCALERS:
        timegap = int(round(CP.CLOCK_RATE / frequency / prescaler / table_size))
        if 0 < timegap < 2 ** 16:
            return timegap, prescaler

    e = (
        "Prescaler out of range. This should not happen."
        + " "
        + "Please report this bug, including steps to trigger it, to"
        + " "
        + "https://github.com/fossasia/pslab-python/issues."
    )
    raise ValueError(e)


class WaveformGenerator:
    """Generate analog waveforms on SI1 or SI2.

    Parameters
    ----------
    device : :class:`SerialHandler`, optional
        Serial connection with which to communicate with the device. A new
        instance is created automatically if not specified.

    Examples
    --------
    Output the default function (3.3*sin(t)) on SI2 with frequency 2.5 kHz:

    >>> from pslab import WaveformGenerator
    >>> wavegen = WaveformGenerator()
    >>> wavegen.generate("SI2", 2500)
    [2500]

    Output phase shifted sine waves on SI1 and SI2:

    >>> wavegen.generate(["SI1", "SI2"], 1000, 90)
    [1000, 1000]

    Reduce the amplitude on SI1:

    >>> import numpy as np
    >>> wavegen.load_equation("SI1", lambda x: 1.5*np.sin(x), [0, 2*np.pi])

    Output two superimposed sine waves on SI2:

    >>> wavegen.load_equation("SI2", lambda x: 2*np.sin(x) + np.sin(5*x), [0, 2*np.pi])
    """

    _HIGHRES_TABLE_SIZE = 512
    _LOWRES_TABLE_SIZE = 32
    _LOW_FREQUENCY_WARNING = 20
    _LOW_FREQUENCY_LIMIT = 0.1
    _HIGH_FREQUENCY_WARNING = 5e3
    _HIGHRES_FREQUENCY_LIMIT = 1100

    def __init__(self, device: SerialHandler = None):
        self._channels = {n: AnalogOutput(n) for n in ("SI1", "SI2")}
        self._device = device if device is not None else SerialHandler()

    def generate(
        self,
        channels: Union[str, List[str]],
        frequency: Union[float, List[float]],
        phase: float = 0,
    ) -> List[float]:
        """Generate analog waveforms on SI1 or SI2.

        The default waveform is a sine wave with amplitude 3.3 V. Other
        waveforms can be set using :meth:`load_function` or :meth:`load_table`.

        Parameters
        ----------
        channels : {1, 2} or {'SI1', 'SI2', ['SI1', 'SI2']}
            Pin(s) on which to generate a waveform.
        frequency : float or list of floats
            Frequency in Hz. Can be a list containing two different values when
            'channel' is ['SI1', 'SI2']. Must be greater than 0.1 Hz. For
            frequencies below 1 Hz the signal is noticably attenuated by AC
            coupling.
        phase : float, optional
            Phase between waveforms when generating waveforms on both SI1 and
            SI2 in degrees. The default is 0.

        Returns
        -------
        frequency : List[float]
            The actual frequency may differ from the requested value due to
            the device-interal integer representation. The actual frequency is
            therefore returned as a list. The length of the list is equal to
            the number of channels used to generate waveforms.
        """
        if isinstance(channels, int):
            channels = ["SI1", "SI2"][:channels]

        channels, frequency = _listify(channels, 2, frequency)
        table_size = len(channels) * [None]
        timegap = len(channels) * [None]
        prescaler = len(channels) * [None]

        for i, (chan, freq) in enumerate(zip(channels, frequency)):
            if freq < self._LOW_FREQUENCY_WARNING:
                w = (
                    f"Frequencies under {self._LOW_FREQUENCY_WARNING} Hz have"
                    + " "
                    + "reduced amplitude due to AC coupling restrictions."
                )
                logger.warning(w)
            elif freq > self._HIGH_FREQUENCY_WARNING:
                w = (
                    f"Frequencies above {self._HIGH_FREQUENCY_WARNING} Hz have"
                    + " "
                    + "reduced amplitude."
                )
                logger.warning(w)

            table_size[i] = self._get_table_size(freq)
            timegap[i], prescaler[i] = _get_wavelength(freq, table_size[i])
            frequency[i] = CP.CLOCK_RATE / timegap[i] / prescaler[i] / table_size[i]
            self._channels[chan].frequency = frequency[i]

        if len(channels) == 1:
            self._output_one(channels, table_size, prescaler, timegap)
        else:
            self._output_two(table_size, phase, prescaler, timegap)

        return frequency

    def _output_one(self, channel: str, table_size: int, prescaler: int, timegap: int):
        self._device.send_byte(CP.WAVEGEN)
        secondary_cmd = CP.SET_SINE1 if channel[0] == "SI1" else CP.SET_SINE2
        self._device.send_byte(secondary_cmd)
        # Use larger table for low frequencies.
        highres = table_size[0] == self._HIGHRES_TABLE_SIZE
        self._device.send_byte(highres | (_PRESCALERS.index(prescaler[0]) << 1))
        self._device.send_int(timegap[0] - 1)
        self._device.get_ack()

    def _output_two(self, table_size: int, phase: float, prescaler: int, timegap: int):
        self._device.send_byte(CP.WAVEGEN)
        phase_coarse = int(table_size[1] * phase / 360)
        phase_fine = int(
            timegap[1]
            * (phase - phase_coarse * 360 / table_size[1])
            / (360 / table_size[1])
        )
        self._device.send_byte(CP.SET_BOTH_WG)
        self._device.send_int(timegap[0] - 1)
        self._device.send_int(timegap[1] - 1)
        self._device.send_int(phase_coarse)  # Table position for phase adjust.
        self._device.send_int(phase_fine)  # Timer delay / fine phase adjust.
        highres = [t == self._HIGHRES_TABLE_SIZE for t in table_size]
        self._device.send_byte(
            (_PRESCALERS.index(prescaler[1]) << 4)
            | (_PRESCALERS.index(prescaler[0]) << 2)
            | (highres[1] << 1)
            | (highres[0])
        )
        self._device.get_ack()

    def _get_table_size(self, frequency: float) -> int:
        if frequency < self._LOW_FREQUENCY_LIMIT:
            e = f"Frequency must be greater than {self._LOW_FREQUENCY_LIMIT} Hz."
            raise ValueError(e)
        elif frequency < self._HIGHRES_FREQUENCY_LIMIT:
            table_size = self._HIGHRES_TABLE_SIZE
        else:
            table_size = self._LOWRES_TABLE_SIZE

        return table_size

    def load_equation(
        self, channel: str, function: Union[str, Callable], span: List[float] = None
    ):
        """Load a custom waveform equation.

        Parameters
        ----------
        channel : {'SI1', 'SI2'}
            The output pin on which to generate the waveform.
        function : Union[str, Callable]
            A callable function which takes a numpy.ndarray of x values as
            input and returns a corresponding numpy.ndarray of y values. The
            y-values should be voltages in V, and should lie between -3.3 V
            and 3.3 V. Values outside this range will be clipped.

            Alternatively, 'function' can be a string literal 'sine' or 'tria',
            for a sine wave or triangle wave with amplitude 3.3 V.
        span : List[float], optional
            The minimum and maximum x values between which to evaluate
            'function'. Omit if 'function' is 'sine' or 'tria'.
        """
        if function == "sine":

            def sine(x):
                return AnalogOutput.RANGE[1] * np.sin(x)

            function = sine
            span = [0, 2 * np.pi]
            self._channels[channel].wavetype = "sine"
        elif function == "tria":

            def tria(x):
                return AnalogOutput.RANGE[1] * (abs(x % 4 - 2) - 1)

            function = tria
            span = [-1, 3]
            self._channels[channel].wavetype = "tria"
        else:
            self._channels[channel].wavetype = "custom"

        x = np.arange(span[0], span[1], (span[1] - span[0]) / 512)
        y = function(x)
        self._load_table(
            channel=channel, points=y, mode=self._channels[channel].wavetype
        )

    def load_table(self, channel: str, points: np.ndarray):
        """Load a custom waveform as a table.

        Parameters
        ----------
        channel : {'SI1', 'SI2'}
            The output pin on which to generate the waveform.
        points : np.ndarray
            Array of voltage values which make up the waveform. Array length
            must be 512. Values outside the range -3.3 V to 3.3 V will be
            clipped.
        """
        self._load_table(channel, points, "custom")

    def _load_table(self, channel, points, mode="custom"):
        self._channels[channel].wavetype = mode
        self._channels[channel].waveform_table = points
        logger.info(f"Reloaded waveform table for {channel}: {mode}.")
        self._device.send_byte(CP.WAVEGEN)

        if self._channels[channel].name == "SI1":
            self._device.send_byte(CP.LOAD_WAVEFORM1)
        else:
            self._device.send_byte(CP.LOAD_WAVEFORM2)

        for val in self._channels[channel].waveform_table:
            self._device.send_int(val)
        for val in self._channels[channel].lowres_waveform_table:
            self._device.send_byte(val)

        self._device.get_ack()


class PWMGenerator:
    """Generate PWM signals on SQ1, SQ2, SQ3, and SQ4.

    Parameters
    ----------
    device : :class:`SerialHandler`
        Serial connection with which to communicate with the device. A new
        instance will be created automatically if not specified.

    Examples
    --------
    Output 40 kHz PWM signals on SQ1 and SQ3 phase shifted by 50%. Set the duty
    cycles to 75% and 33%, respectivelly:

    >>> from pslab import PWMGenerator
    >>> pwmgen = PWMGenerator()
    >>> pwmgen.generate(["SQ1", "SQ2"], 4e4, [0.75, 0.33], 0.5)

    Output a 32 MHz PWM signal on SQ4 with a duty cycle of 50%:

    >>> pwmgen.map_reference_clock(["SQ4"], 2)

    Set SQ2 high:

    >>> pwmgen.set_states(sq2=True)
    """

    _HIGH_FREQUENCY_LIMIT = 1e7

    def __init__(self, device: SerialHandler = None):
        self._device = device if device is not None else SerialHandler()
        self._channels = {n: DigitalOutput(n) for n in DIGITAL_OUTPUTS}
        self._frequency = 0
        self._reference_prescaler = 0

    @property
    def frequency(self) -> float:
        """Get the common frequency for all digital outputs in Hz."""
        return self._frequency

    def generate(
        self,
        channels: Union[str, List[str]],
        frequency: float,
        duty_cycles: Union[float, List[float]],
        phases: Union[float, List[float]] = 0,
    ):
        """Generate PWM signals on SQ1, SQ2, SQ3, and SQ4.

        Parameters
        ----------
        channels : {1, 2, 3, 4} or {'SQ1', 'SQ2', 'SQ3', 'SQ4'} or list of the same
            Pin name or list of pin names on which to generate PWM signals.
            Pins which are not included in the argument will not be affected.
        frequency : float
            Frequency in Hz. Shared by all outputs.
        duty_cycles : float or list of floats
            Duty cycle between 0 and 1 as either a single value or a list of
            values.

            If 'duty_cycles' is a single value, it is applied to all channels
            given in 'channels'.

            If 'duty_cycles' is a list, the values in the list will be applied
            to the corresponding channel in the 'channels' list. The lists must
            have the same length.
        phases : float or list of floats
            Phase between 0 and 1 as either a single value or a list of values.

            If 'phases' is a single value, it will be the phase between each
            subsequent channel in 'channels'. For example,

            >>> generate(['SQ1', 'SQ2', 'SQ3', 'SQ4'], 1000, 0.5, 0.1)

            SQ2 will be shifted relative to SQ1 by 10%, SQ3 will be shifted
            relative to SQ2 by 10% (i.e. 20% relative to SQ1), and SQ4 will be
            shifted relative to SQ3 by 10% (i.e. 30% relative to SQ1).

            If 'phases' is a list, the values in the list will be applied to
            the corresponding channel in the 'channels' list. The lists must
            have the same length.
        """
        if isinstance(channels, int):
            channels = ["SQ1", "SQ2", "SQ3", "SQ4"][:channels]

        if frequency > self._HIGH_FREQUENCY_LIMIT:
            e = (
                "Frequency is greater than 10 MHz."
                + " "
                + "Please use map_reference_clock for 16 & 32 MHz outputs."
            )
            raise ValueError(e)
        elif frequency <= 0:
            raise ValueError("Frequency must be positive.")
        else:
            self._frequency = frequency
            channels, duty_cycles = _listify(channels, 4, duty_cycles)

            if not isinstance(phases, list):
                phases = [i * phases for i in range(len(channels))]

            for channel, duty_cycle, phase in zip(channels, duty_cycles, phases):
                self._channels[channel].duty_cycle = duty_cycle
                self._channels[channel].phase = phase
                self._channels[channel].remapped = False

            # Turn on all channels, minimum duty cycle of 1 wavelength.
            self._generate(
                [self._channels[c].duty_cycle for c in DIGITAL_OUTPUTS],
                [self._channels[c].phase for c in DIGITAL_OUTPUTS],
            )
            # Reset channels which should be LOW or HIGH to correct duty cycle.
            self.set_state(**{k.lower(): v.state for k, v in self._channels.items()})

            # Remap channels which should be mapped to the referene clock.
            remapped = [c.name for c in self._channels.values() if c.remapped]
            self.map_reference_clock(remapped, self._reference_prescaler)

    def _generate(
        self,
        duty_cycles: List[float],
        phases: List[float],
    ):
        """Generate PWM signals on all four digital output pins.

        Paramaters
        ----------
        duty_cycles : list of floats
            List of length four containing duty cycles for each output as a
            float in the open interval (0, 1). Note that it is not possible
            to set the duty cycle to exactly 0 or 1; use :meth:`set_state`
            instead.
        phases : list of floats
            List of length four containing phases for each output as a float in
            the half open interval [0, 1). A phase of 1 is identical to a phase
            of 0.
        """
        wavelength, prescaler = _get_wavelength(self._frequency)
        self._frequency = CP.CLOCK_RATE / wavelength / prescaler
        continuous = 1 << 5

        for i, (duty_cycle, phase) in enumerate(zip(duty_cycles, phases)):
            duty_cycles[i] = int((duty_cycle + phase) % 1 * wavelength)
            duty_cycles[i] = max(1, duty_cycles[i] - 1)  # Zero index.
            phases[i] = int(phase % 1 * wavelength)
            phases[i] = max(0, phases[i] - 1)  # Zero index.

        self._device.send_byte(CP.WAVEGEN)
        self._device.send_byte(CP.SQR4)
        self._device.send_int(wavelength - 1)  # Zero index.
        self._device.send_int(duty_cycles[0])
        self._device.send_int(phases[1])
        self._device.send_int(duty_cycles[1])
        self._device.send_int(phases[2])
        self._device.send_int(duty_cycles[2])
        self._device.send_int(phases[3])
        self._device.send_int(duty_cycles[3])
        self._device.send_byte(_PRESCALERS.index(prescaler) | continuous)
        self._device.get_ack()

    def set_state(
        self,
        sq1: Union[bool, str, None] = None,
        sq2: Union[bool, str, None] = None,
        sq3: Union[bool, str, None] = None,
        sq4: Union[bool, str, None] = None,
    ):
        """Set the digital outputs HIGH or LOW.

        Parameters
        ----------
        sq1 : {True, False, None, 'HIGH', 'LOW', 'PWM'}, optional
            Set the state of SQ1. True or "HIGH" sets it HIGH, False or "LOW"
            sets it low, and None or "PWM" leaves it in its current state. The
            default value is None.
        sq2 : {True, False, None, 'HIGH', 'LOW', 'PWM'}, optional
            See 'sq1'.
        sq3 : {True, False, None, 'HIGH', 'LOW', 'PWM'}, optional
            See 'sq1'.
        sq4 : {True, False, None, 'HIGH', 'LOW', 'PWM'}, optional
            See 'sq1'.
        """
        states = 0

        for i, sq in enumerate([sq1, sq2, sq3, sq4]):
            if sq in (True, False, "HIGH", "LOW"):
                sq = 1 if sq in (True, "HIGH") else 0
                self._channels[DIGITAL_OUTPUTS[i]].duty_cycle = sq
                states |= self._channels[DIGITAL_OUTPUTS[i]].state_mask | (sq << i)

        self._device.send_byte(CP.DOUT)
        self._device.send_byte(CP.SET_STATE)
        self._device.send_byte(states)
        self._device.get_ack()

    def map_reference_clock(self, channels: List[str], prescaler: int):
        """Map the internal oscillator output to a digital output.

        The duty cycle of the output is locked to 50%.

        Parameters
        ----------
        channels : {'SQ1', 'SQ2', 'SQ3', 'SQ4'} or list of the same
            Digital output pin(s) to which to map the internal oscillator.
        prescaler : int
            Prescaler value in interval [0, 15]. The output frequency is
            128 / (1 << prescaler) MHz.
        """
        (channels,) = _listify(channels, 4)
        self._device.send_byte(CP.WAVEGEN)
        self._device.send_byte(CP.MAP_REFERENCE)
        self._reference_prescaler = prescaler
        maps = 0

        for channel in channels:
            self._channels[channel].duty_cycle = 0.5
            self._channels[channel].phase = 0
            self._channels[channel].remapped = True
            maps |= self._channels[channel].reference_clock_map

        self._device.send_byte(maps)
        self._device.send_byte(prescaler)
        self._device.get_ack()
