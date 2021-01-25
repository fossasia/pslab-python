"""Motor control related classes.

Examples
--------
>>> from pslab.external.motor import Servo
>>> servo = Servo("SQ1")
>>> servo.angle = 30  # Turn motor to 30 degrees position.
"""
from typing import Union

from pslab.instrument.waveform_generator import PWMGenerator

MICROSECONDS = 1e6


class Servo:
    """Control servo motors on SQ1-4.

    Parameters
    ----------
    pin : {"SQ1", "SQ2", "SQ3", "SQ4"}
        Name of the digital output on which to generate the control signal.
    pwm_generator : :class:`PWMGenerator`, optional
        PWMGenerator instance with which to generate the control signal.
        Created automatically if not specified. When contolling multiple
        servos, they should all use the same PWMGenerator instance.
    min_angle_pulse : int, optional
        Pulse length in microseconds corresponding to the minimum (0 degree)
        angle of the servo. The default value is 500.
    max_angle_pulse : int, optional
        Pulse length in microseconds corresponding to the maximum (180 degree)
        angle of the servo. The default value is 2500.
    angle_range : int
        Range of the servo in degrees. The default value is 180.
    frequency : float, optional
        Frequency of the control signal in Hz. The default value is 50.
    """

    def __init__(
        self,
        pin: str,
        pwm_generator: PWMGenerator = None,
        min_angle_pulse: int = 500,
        max_angle_pulse: int = 2500,
        angle_range: int = 180,
        frequency: float = 50,
    ):
        self._pwm = PWMGenerator() if pwm_generator is None else pwm_generator
        self._pin = pin
        self._angle = None
        self._min_angle_pulse = min_angle_pulse
        self._max_angle_pulse = max_angle_pulse
        self._angle_range = angle_range
        self._frequency = frequency

    @property
    def angle(self) -> Union[int, None]:
        """:obj:`int` or :obj:`None`: Angle of the servo in degrees."""
        return self._angle

    @angle.setter
    def angle(self, value: int):
        duty_cycle = self._get_duty_cycle(value)
        self._pwm.generate(self._pin, self._frequency, duty_cycle)
        self._angle = value

    def _get_duty_cycle(self, angle):
        angle /= self._angle_range  # Normalize
        angle *= self._max_angle_pulse - self._min_angle_pulse  # Scale
        angle += self._min_angle_pulse  # Offset
        return angle / (self._frequency ** -1 * MICROSECONDS)
