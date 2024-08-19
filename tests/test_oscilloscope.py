"""Tests for PSL.oscilloscope.

The PSLab's waveform generator is used to generate a signal which is sampled by the
oscilloscope. Before running the tests, connect:
    SI1 -> CH1
    SI2 -> CH2
    SI1 -> CH3
"""

import numpy as np
import pytest

from pslab.instrument.oscilloscope import Oscilloscope
from pslab.instrument.waveform_generator import WaveformGenerator


FREQUENCY = 1000
MICROSECONDS = 1e-6
ABSTOL = 4 * (16.5 - (-16.5)) / (2**10 - 1)  # Four times lowest CH1/CH2 resolution.


@pytest.fixture
def scope(handler):
    """Enable waveform generator and return an Oscilloscope instance."""
    wave = WaveformGenerator(handler)
    wave.generate(["SI1", "SI2"], FREQUENCY)
    return Oscilloscope(handler)


def count_zero_crossings(x, y):
    sample_rate = (np.diff(x)[0] * MICROSECONDS) ** -1
    samples_per_period = sample_rate / FREQUENCY
    zero_crossings = np.where(np.diff(np.sign(y)))[0]
    real_crossings = np.where(np.diff(zero_crossings) > samples_per_period * 0.01)
    real_crossings = np.append(real_crossings, True)

    if len(real_crossings) % 1:
        if y[0] * y[-1] <= 0:
            return len(real_crossings) + 1

    return len(real_crossings)


def verify_periods(x, y, channel, periods=1):
    zero_crossings = count_zero_crossings(x, y)
    assert zero_crossings == 2 * periods
    assert y[0] == pytest.approx(y[-1], abs=ABSTOL)


def test_capture_one_12bit(scope):
    _, y = scope.capture(channels=1, samples=1000, timegap=1)
    y.sort()
    resolution = min(np.diff(y)[np.diff(y) > 0])
    expected = (16.5 - (-16.5)) / (2**12 - 1)
    assert resolution == pytest.approx(expected)


def test_capture_one_high_speed(scope):
    x, y = scope.capture(channels=1, samples=2000, timegap=0.5)
    verify_periods(x, y, scope._channels["CH1"])


def test_capture_one_trigger(scope):
    _, y = scope.capture(channels=1, samples=1, timegap=1, trigger=0)
    assert y[0] == pytest.approx(0, abs=ABSTOL)


def test_capture_two(scope):
    x, y1, y2 = scope.capture(channels=2, samples=500, timegap=2)
    verify_periods(x, y1, scope._channels["CH1"])
    verify_periods(x, y2, scope._channels["CH2"])


def test_capture_three(scope):
    x, y1, y2, y3 = scope.capture(channels=3, samples=500, timegap=2)
    verify_periods(x, y1, scope._channels["CH1"])
    verify_periods(x, y2, scope._channels["CH2"])
    verify_periods(x, y3, scope._channels["CH3"])


def test_capture_four(scope):
    x, y1, y2, y3, _ = scope.capture(channels=4, samples=500, timegap=2)
    verify_periods(x, y1, scope._channels["CH1"])
    verify_periods(x, y2, scope._channels["CH2"])
    verify_periods(x, y3, scope._channels["CH3"])


def test_capture_invalid_channel_one(scope):
    with pytest.raises(ValueError):
        scope.capture(channels="BAD", samples=200, timegap=2)


def test_capture_timegap_too_small(scope):
    with pytest.raises(ValueError):
        scope.capture(channels=1, samples=200, timegap=0.2)


def test_capture_too_many_channels(scope):
    with pytest.raises(ValueError):
        scope.capture(channels=5, samples=200, timegap=2)


def test_capture_too_many_samples(scope):
    with pytest.raises(ValueError):
        scope.capture(channels=4, samples=3000, timegap=2)


def test_select_range(scope):
    scope.select_range("CH1", 1.5)
    _, y = scope.capture(channels=1, samples=1000, timegap=1)
    assert 1.5 <= max(y) <= 1.65
