"""Tests for PSL.oscilloscope.

When integration testing, the PSLab's analog output is used to generate a signal
which is sampled by the oscilloscope. Before running the integration tests,
connect SI1->CH1->CH2->CH3.
"""

import numpy as np
import pytest
from scipy.optimize import curve_fit

import PSL.commands_proto as CP
from PSL import achan
from PSL import oscilloscope
from PSL import packet_handler
from PSL import sciencelab

FREQUENCY = 1000
AMPLITUDE = 3
ABSTOL = 0.25  # 250 mV
MICROSECONDS = 1e-6


@pytest.fixture
def scope(handler):
    """Return an Oscilloscope instance.

    In integration test mode, this function also enables the analog output.
    """
    if not isinstance(handler, packet_handler.MockHandler):
        psl = sciencelab.connect()
        psl.H.disconnect()
        psl.H = handler
        psl.set_sine1(FREQUENCY)
        handler._logging = True
    return oscilloscope.Oscilloscope(handler)


def estimate_sin(x, y):
    phase = estimate_phase(x, y)
    return sinfunc(x, phase)


def sinfunc(x, phase):
    return AMPLITUDE * np.sin(2 * np.pi * FREQUENCY * MICROSECONDS * x + phase)


def estimate_phase(x, y):
    return curve_fit(sinfunc, x, y)[0][0]


def test_capture_one_12bit(scope):
    _, y = scope.capture(channels=1, samples=1000, timegap=1)
    y.sort()
    resolution = min(np.diff(y)[np.diff(y) > 0])
    irange = achan.INPUT_RANGES["CH1"][0] - achan.INPUT_RANGES["CH1"][1]
    assert resolution == pytest.approx(irange / (2 ** 12 - 1))


def test_capture_one_high_speed(scope):
    x, y = scope.capture(channels=1, samples=2000, timegap=0.5)
    expected = estimate_sin(x, y)
    assert y == pytest.approx(expected, abs=ABSTOL)


def test_capture_one_trigger(scope):
    scope.trigger_enabled = True
    _, y = scope.capture(channels=1, samples=1, timegap=1)
    assert y[0] == pytest.approx(0, abs=ABSTOL)


def test_capture_two(scope):
    x, y1, y2 = scope.capture(channels=2, samples=500, timegap=2)
    expected = estimate_sin(x, y1)
    assert y1 == pytest.approx(expected, abs=ABSTOL)
    assert y2 == pytest.approx(expected, abs=ABSTOL)


def test_capture_four(scope):
    x, y1, y2, y3, _ = scope.capture(channels=4, samples=500, timegap=2)
    expected = estimate_sin(x, y1)
    assert y1 == pytest.approx(expected, abs=ABSTOL)
    assert y2 == pytest.approx(expected, abs=ABSTOL)
    assert y3 == pytest.approx(expected, abs=ABSTOL)


def test_capture_invalid_channel_one(scope):
    scope.channel_one_map = "BAD"
    with pytest.raises(ValueError):
        scope.capture(channels=1, samples=200, timegap=2)


def test_capture_timegap_too_small(scope):
    with pytest.raises(ValueError):
        scope.capture(channels=1, samples=200, timegap=0.2)


def test_capture_too_many_channels(scope):
    with pytest.raises(ValueError):
        scope.capture(channels=5, samples=200, timegap=2)


def test_capture_too_many_samples(scope):
    with pytest.raises(ValueError):
        scope.capture(channels=4, samples=3000, timegap=2)


def test_configure_trigger(scope):
    scope.channel_one_map = "CH3"
    scope.configure_trigger(channel="CH3", voltage=1.5)
    _, y = scope.capture(channels=1, samples=1, timegap=1)
    assert y[0] == pytest.approx(1.5, abs=ABSTOL)


def test_configure_trigger_on_unmapped(scope):
    with pytest.raises(TypeError):
        scope.configure_trigger(channel="AN8", voltage=1.5)


def test_configure_trigger_on_remapped_ch1(scope):
    scope.channel_one_map = "CAP"
    with pytest.raises(TypeError):
        scope.configure_trigger(channel="CH1", voltage=1.5)


def test_select_range(scope):
    scope.select_range("CH1", 1.5)
    _, y = scope.capture(channels=1, samples=1000, timegap=1)
    assert 1.5 <= max(y) <= 1.65


def test_select_range_invalid(scope):
    with pytest.raises(ValueError):
        scope.select_range("CH1", 15)
