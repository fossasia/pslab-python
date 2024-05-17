"""Ultrasonic distance sensors."""

import time

from pslab.instrument.logic_analyzer import LogicAnalyzer
from pslab.instrument.waveform_generator import PWMGenerator
from pslab.serial_handler import SerialHandler


class HCSR04:
    """Read data from ultrasonic distance sensor HC-SR04/HC-SR05.

    These sensors can measure distances between 2 cm to 4 m (SR04) / 4.5 m
    (SR05).

    Sensors must have separate trigger and echo pins. First a 10 µs pulse is
    output on the trigger pin. The trigger pin must be connected to the TRIG
    pin on the sensor prior to use.

    Upon receiving this pulse, the sensor emits a sequence of sound pulses, and
    the logic level of its echo pin is also set high.  The logic level goes LOW
    when the sound packet returns to the sensor, or when a timeout occurs.
    Timeout occurs if no echo is received within the time slot determinded by
    the sensor's maximum range.

    The ultrasound sensor outputs a series of eight sound pulses at 40 kHz,
    which corresponds to a time period of 25 µs per pulse. These pulses reflect
    off of the nearest object in front of the sensor, and return to it. The
    time between sending and receiving of the pulse packet is used to estimate
    the distance. If the reflecting object is either too far away or absorbs
    sound, less than eight pulses may be received, and this can cause a
    measurement error of 25 µs which corresponds to 8 mm.

    Parameters
    ----------
    device : :class:`SerialHandler`
        Serial connection to PSLab device.
    trig : str, optional
        Name of the trigger pin. Defaults to SQ1.
    echo : str, optional
        Name of the echo pin. Defaults to LA1.

    Example
    -------
    In this example the sensor's Vcc pin is connected to the PSLab's PV1 pin,
    the Trig pin is connected to SQ1, Echo to LA1, and Gnd to GND.

    >>> import pslab
    >>> from pslab.external.hcsr04 import HCSR04
    >>> psl = pslab.ScienceLab()
    >>> distance_sensor = HCSR04(psl)
    >>> psl.power_supply.pv1 = 5  # Power the sensor.
    >>> distance_sensor.estimate_distance()
    2.36666667
    """

    def __init__(
        self,
        device: SerialHandler,
        trig: str = "SQ1",
        echo: str = "LA1",
    ):
        self._device = device
        self._la = LogicAnalyzer(self._device)
        self._pwm = PWMGenerator(self._device)
        self._trig = trig
        self._echo = echo
        self._measure_period = 60e-3  # Minimum recommended by datasheet.
        self._trigger_pulse_length = 10e-6

    def estimate_distance(
        self,
        average: int = 10,
        speed_of_sound: float = 340,
    ) -> float:
        """Estimate distance to an object.

        Parameters
        ----------
        average : int, optional
            Number of times to repeat the measurement and average the results.
            Defaults to 10.
        speed_of_sound : float, optional
            Speed of sound in air. Defaults to 340 m/s.

        Returns
        -------
        distance : float
            Distance to object in meters.

        Raises
        ------
        RuntimeError if the ECHO pin is not LOW at start of measurement.
        TimeoutError if the end of the ECHO pulse is not detected (i.e. the
                     object is too far away).
        """
        self._la.capture(
            channels=self._echo,
            events=2 * average,
            block=False,
        )
        self._pwm.generate(
            channels=self._trig,
            frequency=self._measure_period**-1,
            duty_cycles=self._trigger_pulse_length / self._measure_period,
        )
        # Wait one extra period to make sure we don't miss the final edge.
        time.sleep(self._measure_period * (average + 1))
        self._pwm.set_state(**{self._trig.lower(): 0})
        (t,) = self._la.fetch_data()
        self._sanity_check(len(t), 2 * average)
        high_times = t[1::2] - t[::2]
        return speed_of_sound * high_times.mean() / 2 * 1e-6

    def _sanity_check(self, events: int, expected_events: int):
        if self._la.get_initial_states()[self._echo]:
            raise RuntimeError("ECHO pin was HIGH when measurement started.")
        if events < expected_events:
            raise TimeoutError
