"""Motor control related classes.

Examples
--------
>>> from pslab.external.motor import Servo
>>> servo = Servo("SQ1")
>>> servo.angle = 30  # Turn motor to 30 degrees position.
"""

import time
from typing import List
from typing import Union
import csv
import os

from pslab.instrument.waveform_generator import PWMGenerator
from datetime import datetime

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
        return angle / (self._frequency**-1 * MICROSECONDS)


class RoboticArm:
    """Robotic arm controller for up to 4 servos."""

    MAX_SERVOS = 4

    def __init__(self, servos: List[Servo]) -> None:
        if len(servos) > RoboticArm.MAX_SERVOS:
            raise ValueError(
                f"At most {RoboticArm.MAX_SERVOS} servos can be used, got {len(servos)}"
            )
        self.servos = servos

    def run_schedule(self, timeline: List[List[int]], time_step: float = 1.0) -> None:
        """Run a time-based schedule to move servos.

        Parameters
        ----------
        timeline : List[List[int]]
            A list of timesteps,where each sublist represents one timestep,
            with angles corresponding to each servo.

        time_step : float, optional
            Delay in seconds between each timestep. Default is 1.0.
        """
        if len(timeline[0]) != len(self.servos):
            raise ValueError("Each timestep must specify an angle for every servo")

        tl_len = len(timeline[0])
        if not all(len(tl) == tl_len for tl in timeline):
            raise ValueError("All timeline entries must have the same length")

        for tl in timeline:
            for i, s in enumerate(self.servos):
                if tl[i] is not None:
                    s.angle = tl[i]
            time.sleep(time_step)

    def import_timeline_from_csv(self, filepath: str) -> List[List[int]]:
        """Import timeline from a CSV file.

        Parameters
        ----------
        filepath : str
            Absolute or relative path to the CSV file to be read.

        Returns
        -------
        List[List[int]]
            A timeline consisting of servo angle values per timestep.
        """
        timeline = []

        with open(filepath, mode="r", newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                angles = []
                for key in ["Servo1", "Servo2", "Servo3", "Servo4"]:
                    value = row.get(key, "").strip().lower()
                    if value in ("", "null", "none"):
                        angles.append(None)
                    else:
                        angles.append(int(value))
                timeline.append(angles)

        return timeline

    def export_timeline_to_csv(
        self, timeline: List[List[Union[int, None]]], folderpath: str
    ) -> None:
        """Export timeline to a CSV file.

        Parameters
        ----------
        timeline : List[List[Union[int, None]]]
            A list of timesteps where each sublist contains servo angles.

        folderpath : str
            Directory path where the CSV file will be saved. The filename
            will include a timestamp to ensure uniqueness.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"Robotic_Arm{timestamp}.csv"
        filepath = os.path.join(folderpath, filename)

        with open(filepath, mode="w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Timestep", "Servo1", "Servo2", "Servo3", "Servo4"])
            for i, row in enumerate(timeline):
                pos = ["null" if val is None else val for val in row]
                writer.writerow([i] + pos)
