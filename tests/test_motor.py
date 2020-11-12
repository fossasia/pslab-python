import pytest

from PSL.logic_analyzer import LogicAnalyzer
from PSL.motor import Servo
from PSL.packet_handler import Handler
from PSL.waveform_generator import PWMGenerator

RELTOL = 0.01


@pytest.fixture
def servo(handler: Handler) -> Servo:
    handler._logging = True
    return Servo("SQ1", PWMGenerator(handler))


@pytest.fixture
def la(handler: Handler) -> LogicAnalyzer:
    handler._logging = True
    return LogicAnalyzer(handler)


def test_set_angle(servo: Servo, la: LogicAnalyzer):
    servo.angle = 90
    wavelength, duty_cycle = la.measure_duty_cycle("LA1")
    assert wavelength * duty_cycle == pytest.approx(1500, rel=RELTOL)


def test_get_angle(servo: Servo):
    servo.angle = 90
    assert servo.angle == 90
