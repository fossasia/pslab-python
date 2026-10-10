"""Hardware-independent tests for ultrasonic trigger cleanup."""

from unittest.mock import Mock

import numpy as np
import pytest

from pslab.external.hcsr04 import HCSR04


@pytest.fixture
def sensor(monkeypatch):
    """Return a sensor using controlled capture and PWM interfaces."""
    logic = Mock()
    pwm = Mock()
    monkeypatch.setattr("pslab.external.hcsr04.LogicAnalyzer", Mock(return_value=logic))
    monkeypatch.setattr("pslab.external.hcsr04.PWMGenerator", Mock(return_value=pwm))
    sensor = HCSR04(device=Mock())
    sensor._la.fetch_data.return_value = (np.array([100, 1100, 60100, 61100]),)
    sensor._la.get_initial_states.return_value = {"LA1": False}
    return sensor


@pytest.mark.parametrize("trig", ["SQ1", "SQ4"])
@pytest.mark.parametrize("error", [KeyboardInterrupt, RuntimeError])
def test_interrupted_wait_stops_trigger_before_propagating(
    sensor, monkeypatch, trig, error
):
    sensor._trig = trig
    failure = error("measurement interrupted")
    wait = Mock(side_effect=failure)
    monkeypatch.setattr("pslab.external.hcsr04.time.sleep", wait)

    with pytest.raises(error) as raised:
        sensor.estimate_distance(average=2)

    assert raised.value is failure
    sensor._pwm.generate.assert_called_once()
    sensor._pwm.set_state.assert_called_once_with(**{trig.lower(): 0})
    sensor._la.fetch_data.assert_not_called()
    sensor._la.get_initial_states.assert_not_called()


@pytest.mark.parametrize("trig", ["SQ1", "SQ4"])
def test_success_stops_trigger_before_fetch_and_keeps_distance(
    sensor, monkeypatch, trig
):
    sensor._trig = trig
    wait = Mock()
    monkeypatch.setattr("pslab.external.hcsr04.time.sleep", wait)
    calls = Mock()
    calls.attach_mock(sensor._pwm.generate, "generate")
    calls.attach_mock(wait, "wait")
    calls.attach_mock(sensor._pwm.set_state, "stop")
    calls.attach_mock(sensor._la.fetch_data, "fetch")

    assert sensor.estimate_distance(average=2) == pytest.approx(0.17)

    assert [call[0] for call in calls.mock_calls] == [
        "generate",
        "wait",
        "stop",
        "fetch",
    ]
    wait.assert_called_once_with(0.18)
    sensor._pwm.set_state.assert_called_once_with(**{trig.lower(): 0})
    sensor._la.capture.assert_called_once_with(channels="LA1", events=4, block=False)
    sensor._pwm.generate.assert_called_once_with(
        channels=trig, frequency=1 / 0.06, duty_cycles=10e-6 / 0.06
    )


@pytest.mark.parametrize("failure", ["timeout", "high_echo"])
def test_capture_errors_keep_trigger_stopped(sensor, monkeypatch, failure):
    monkeypatch.setattr("pslab.external.hcsr04.time.sleep", Mock())
    if failure == "timeout":
        sensor._la.fetch_data.return_value = (np.array([100, 1100]),)
        error = TimeoutError
    else:
        sensor._la.get_initial_states.return_value = {"LA1": True}
        error = RuntimeError

    with pytest.raises(error):
        sensor.estimate_distance(average=2)

    sensor._pwm.set_state.assert_called_once_with(sq1=0)
