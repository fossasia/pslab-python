"""Tests for pslab.external.motor.

Connect SQ1 -> LA1.
"""

import pytest

from pslab.external.motor import Servo
from pslab.instrument.logic_analyzer import LogicAnalyzer
from pslab.instrument.waveform_generator import PWMGenerator
from pslab.serial_handler import SerialHandler

RELTOL = 0.01


@pytest.fixture
def servo(handler: SerialHandler) -> Servo:
    return Servo("SQ1", PWMGenerator(handler))


@pytest.fixture
def la(handler: SerialHandler) -> LogicAnalyzer:
    return LogicAnalyzer(handler)


def test_set_angle(servo: Servo, la: LogicAnalyzer):
    servo.angle = 90
    wavelength, duty_cycle = la.measure_duty_cycle("LA1")
    assert wavelength * duty_cycle == pytest.approx(1500, rel=RELTOL)


def test_get_angle(servo: Servo):
    servo.angle = 90
    assert servo.angle == 90
