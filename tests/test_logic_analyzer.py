"""Tests for pslab.instrument.logic_analyzer.

When integration testing, the PSLab's PWM output is used to generate a signal
which is analyzed by the logic analyzer. Before running the integration tests,
connect:
    SQ1 -> LA1
    SQ2 -> LA2
    SQ3 -> LA3
    SQ4 -> LA4
"""

import time

import numpy as np
import pytest

import pslab.protocol as CP
from pslab.instrument.logic_analyzer import LogicAnalyzer
from pslab.instrument.waveform_generator import PWMGenerator


EVENTS = 2495
FREQUENCY = 1e5
DUTY_CYCLE = 0.5
LOW_FREQUENCY = 100
LOWER_FREQUENCY = 10
MICROSECONDS = 1e6
TWO_CLOCK_CYCLES = 2 * CP.CLOCK_RATE**-1 * MICROSECONDS


@pytest.fixture
def la(handler, request):
    """Turn on PWM output and return a LogicAnalyzer instance."""
    pwm = PWMGenerator(handler)
    enable_pwm(pwm, request.node.name)
    return LogicAnalyzer(handler)


def enable_pwm(pwm: PWMGenerator, test_name: str):
    """Enable PWM output for integration testing."""
    low_frequency_tests = (
        "test_capture_four_low_frequency",
        "test_capture_four_lower_frequency",
        "test_capture_four_lowest_frequency",
        "test_capture_timeout",
        "test_get_states",
    )
    if test_name in low_frequency_tests:
        frequency = LOW_FREQUENCY
    elif test_name == "test_capture_four_too_low_frequency":
        frequency = LOWER_FREQUENCY
    else:
        frequency = FREQUENCY

    pwm.generate(
        ["SQ1", "SQ2", "SQ3", "SQ4"],
        frequency,
        DUTY_CYCLE,
        0,
    )


def test_capture_one_channel(la):
    t = la.capture(1, EVENTS)
    assert len(t[0]) == EVENTS


def test_capture_two_channels(la):
    t1, t2 = la.capture(2, EVENTS)
    assert len(t1) == len(t2) == EVENTS


def test_capture_four_channels(la):
    t1, t2, t3, t4 = la.capture(4, EVENTS)
    assert len(t1) == len(t2) == len(t3) == len(t4) == EVENTS


def test_capture_four_low_frequency(la):
    e2e_time = (LOW_FREQUENCY**-1) / 2
    t1 = la.capture(4, 10, e2e_time=e2e_time)[0]
    # When capturing every edge, the accuracy seems to depend on
    # the PWM prescaler as well as the logic analyzer prescaler.
    pwm_abstol = TWO_CLOCK_CYCLES * LogicAnalyzer._PRESCALERS[2]
    assert np.array(9 * [e2e_time * MICROSECONDS]) == pytest.approx(
        np.diff(t1), abs=TWO_CLOCK_CYCLES * LogicAnalyzer._PRESCALERS[1] + pwm_abstol
    )


def test_capture_four_lower_frequency(la):
    e2e_time = LOW_FREQUENCY**-1
    t1 = la.capture(4, 10, modes=4 * ["rising"], e2e_time=e2e_time)[0]
    assert np.array(9 * [e2e_time * MICROSECONDS]) == pytest.approx(
        np.diff(t1), abs=TWO_CLOCK_CYCLES * LogicAnalyzer._PRESCALERS[2]
    )


def test_capture_four_lowest_frequency(la):
    e2e_time = (LOW_FREQUENCY**-1) * 16
    t1 = la.capture(4, 10, modes=4 * ["sixteen rising"], e2e_time=e2e_time, timeout=2)[
        0
    ]
    assert np.array(9 * [e2e_time * MICROSECONDS]) == pytest.approx(
        np.diff(t1), abs=TWO_CLOCK_CYCLES * LogicAnalyzer._PRESCALERS[3]
    )


def test_capture_four_too_low_frequency(la):
    e2e_time = (LOWER_FREQUENCY**-1) * 4
    with pytest.raises(ValueError):
        la.capture(4, 10, modes=4 * ["four rising"], e2e_time=e2e_time, timeout=5)


def test_capture_nonblocking(la):
    la.capture(1, EVENTS, block=False)
    time.sleep(EVENTS * FREQUENCY**-1)
    t = la.fetch_data()
    assert len(t[0]) >= EVENTS


def test_capture_rising_edges(la):
    events = 100
    t1, t2 = la.capture(2, events, modes=["any", "rising"])
    expected = FREQUENCY**-1 * MICROSECONDS / 2
    result = t2 - t1 - (t2 - t1)[0]
    assert np.arange(0, expected * events, expected) == pytest.approx(
        result, abs=TWO_CLOCK_CYCLES
    )


def test_capture_four_rising_edges(la):
    events = 100
    t1, t2 = la.capture(2, events, modes=["rising", "four rising"])
    expected = FREQUENCY**-1 * MICROSECONDS * 3
    result = t2 - t1 - (t2 - t1)[0]
    assert np.arange(0, expected * events, expected) == pytest.approx(
        result, abs=TWO_CLOCK_CYCLES
    )


def test_capture_sixteen_rising_edges(la):
    events = 100
    t1, t2 = la.capture(2, events, modes=["four rising", "sixteen rising"])
    expected = FREQUENCY**-1 * MICROSECONDS * 12
    result = t2 - t1 - (t2 - t1)[0]
    assert np.arange(0, expected * events, expected) == pytest.approx(
        result, abs=TWO_CLOCK_CYCLES
    )


def test_capture_too_many_events(la):
    with pytest.raises(ValueError):
        la.capture(1, CP.MAX_SAMPLES // 4 + 1)


def test_capture_too_many_channels(la):
    with pytest.raises(ValueError):
        la.capture(5)


def test_measure_frequency(la):
    frequency = la.measure_frequency("LA1", timeout=0.1)
    assert FREQUENCY == pytest.approx(frequency)


def test_measure_frequency_firmware(la):
    frequency = la.measure_frequency("LA2", timeout=0.1, simultaneous_oscilloscope=True)
    assert FREQUENCY == pytest.approx(frequency)


def test_measure_interval(la):
    la.configure_trigger("LA1", "falling")
    interval = la.measure_interval(
        channels=["LA1", "LA2"], modes=["rising", "falling"], timeout=0.1
    )
    expected_interval = FREQUENCY**-1 * MICROSECONDS * 0.5
    assert expected_interval == pytest.approx(interval, abs=TWO_CLOCK_CYCLES)


def test_measure_interval_same_channel(la):
    la.configure_trigger("LA1", "falling")
    interval = la.measure_interval(
        channels=["LA1", "LA1"], modes=["rising", "falling"], timeout=0.1
    )
    expected_interval = FREQUENCY**-1 * DUTY_CYCLE * MICROSECONDS
    assert expected_interval == pytest.approx(interval, abs=TWO_CLOCK_CYCLES)


def test_measure_interval_same_channel_any(la):
    la.configure_trigger("LA1", "falling")
    interval = la.measure_interval(
        channels=["LA1", "LA1"], modes=["any", "any"], timeout=0.1
    )
    expected_interval = FREQUENCY**-1 * DUTY_CYCLE * MICROSECONDS
    assert expected_interval == pytest.approx(interval, abs=TWO_CLOCK_CYCLES)


def test_measure_interval_same_channel_four_rising(la):
    la.configure_trigger("LA1", "falling")
    interval = la.measure_interval(
        channels=["LA1", "LA1"], modes=["rising", "four rising"], timeout=0.1
    )
    expected_interval = FREQUENCY**-1 * 3 * MICROSECONDS
    assert expected_interval == pytest.approx(interval, abs=TWO_CLOCK_CYCLES)


def test_measure_interval_same_channel_sixteen_rising(la):
    la.configure_trigger("LA1", "falling")
    interval = la.measure_interval(
        channels=["LA1", "LA1"], modes=["rising", "sixteen rising"], timeout=0.1
    )
    expected_interval = FREQUENCY**-1 * 15 * MICROSECONDS
    assert expected_interval == pytest.approx(interval, abs=TWO_CLOCK_CYCLES)


def test_measure_interval_same_channel_same_event(la):
    la.configure_trigger("LA1", "falling")
    interval = la.measure_interval(
        channels=["LA3", "LA3"], modes=["rising", "rising"], timeout=0.1
    )
    expected_interval = FREQUENCY**-1 * MICROSECONDS
    assert expected_interval == pytest.approx(interval, abs=TWO_CLOCK_CYCLES)


def test_measure_duty_cycle(la):
    period, duty_cycle = la.measure_duty_cycle("LA4", timeout=0.1)
    expected_period = FREQUENCY**-1 * MICROSECONDS
    assert (expected_period, DUTY_CYCLE) == pytest.approx(
        (period, duty_cycle), abs=TWO_CLOCK_CYCLES
    )


def test_get_xy_rising_trigger(la):
    la.configure_trigger("LA1", "rising")
    t = la.capture(1, 100)
    _, y = la.get_xy(t)
    assert y[0]


def test_get_xy_falling_trigger(la):
    la.configure_trigger("LA1", "falling")
    t = la.capture(1, 100)
    _, y = la.get_xy(t)
    assert not y[0]


def test_get_xy_rising_capture(la):
    t = la.capture(1, 100, modes=["rising"])
    _, y = la.get_xy(t)
    assert sum(y) == 100


def test_get_xy_falling_capture(la):
    t = la.capture(1, 100, modes=["falling"])
    _, y = la.get_xy(t)
    assert sum(~y) == 100


def test_stop(la):
    la.capture(1, EVENTS, modes=["sixteen rising"], block=False)
    time.sleep(EVENTS * FREQUENCY**-1)
    progress_time = time.time()
    progress = la.get_progress()
    la.stop()
    stop_time = time.time()
    time.sleep(EVENTS * FREQUENCY**-1)
    assert progress < CP.MAX_SAMPLES // 4
    abstol = FREQUENCY * (stop_time - progress_time)
    assert progress == pytest.approx(la.get_progress(), abs=abstol)


def test_get_states(la):
    time.sleep(LOW_FREQUENCY**-1)
    states = la.get_states()
    expected_states = {"LA1": True, "LA2": True, "LA3": True, "LA4": True}
    assert states == expected_states


def test_count_pulses(la):
    interval = 0.2
    pulses = la.count_pulses("LA2", interval)
    expected_pulses = FREQUENCY * interval
    assert expected_pulses == pytest.approx(pulses, rel=0.1)  # Pretty bad accuracy.
