"""These tests are intended to run against real hardware.

Before running the tests, connect SQ1<->ID1, SQ2<->ID2, SQ3<->ID3, and SQ4<->ID4.
"""

import time

import numpy as np
import pytest

import PSL.commands_proto as CP
from PSL import logic_analyzer
from PSL import sciencelab

MAX_SAMPLES = CP.MAX_SAMPLES // 4 - 2
FREQUENCY = 1e5
DUTY_CYCLE = 0.5
PHASE = 0.25
MICROSECONDS = 1e6
RELTOL = 0.02


@pytest.fixture
def la():
    psl = sciencelab.connect()
    psl.sqrPWM(
        freq=FREQUENCY,
        h0=DUTY_CYCLE,
        p1=PHASE,
        h1=DUTY_CYCLE,
        p2=2 * PHASE,
        h2=DUTY_CYCLE,
        p3=3 * PHASE,
        h3=DUTY_CYCLE,
    )
    return logic_analyzer.LogicAnalyzer(psl.H)


def test_capture_one_channel(la):
    t = la.capture(1)
    assert len(t[0]) == MAX_SAMPLES


def test_capture_two_channels(la):
    t1, t2 = la.capture(2)
    assert len(t1) == len(t2) == MAX_SAMPLES


def test_capture_four_channels(la):
    t1, t2, t3, t4 = la.capture(4)
    assert len(t1) == len(t2) == len(t3) == len(t4) == MAX_SAMPLES


def test_capture_four_low_frequency():
    psl = sciencelab.connect()
    frequency = 200
    psl.sqrPWM(
        frequency,
        DUTY_CYCLE,
        PHASE,
        DUTY_CYCLE,
        2 * PHASE,
        DUTY_CYCLE,
        3 * PHASE,
        DUTY_CYCLE,
    )

    la = logic_analyzer.LogicAnalyzer(psl.H)
    e2e_time = (frequency ** -1) / 2
    t1, t2, t3, t4 = la.capture(4, 10, e2e_time=e2e_time)
    assert np.array(9 * [e2e_time * MICROSECONDS]) == pytest.approx(
        np.diff(t1), rel=RELTOL
    )


def test_capture_four_lower_frequency():
    psl = sciencelab.connect()
    frequency = 50
    psl.sqrPWM(
        frequency,
        DUTY_CYCLE,
        PHASE,
        DUTY_CYCLE,
        2 * PHASE,
        DUTY_CYCLE,
        3 * PHASE,
        DUTY_CYCLE,
    )

    la = logic_analyzer.LogicAnalyzer(psl.H)
    e2e_time = (frequency ** -1) / 2
    t1, t2, t3, t4 = la.capture(4, 10, e2e_time=e2e_time)
    assert np.array(9 * [e2e_time * MICROSECONDS]) == pytest.approx(
        np.diff(t1), rel=RELTOL
    )


def test_capture_four_lowest_frequency():
    psl = sciencelab.connect()
    frequency = 50
    psl.sqrPWM(
        frequency,
        DUTY_CYCLE,
        PHASE,
        DUTY_CYCLE,
        2 * PHASE,
        DUTY_CYCLE,
        3 * PHASE,
        DUTY_CYCLE,
    )

    la = logic_analyzer.LogicAnalyzer(psl.H)
    e2e_time = (frequency ** -1) * 4
    t1, t2, t3, t4 = la.capture(4, 10, modes=4 * ["four rising"], e2e_time=e2e_time)
    assert np.array(9 * [e2e_time * MICROSECONDS]) == pytest.approx(
        np.diff(t1), rel=RELTOL
    )


def test_capture_four_too_low_frequency():
    psl = sciencelab.connect()
    frequency = 50
    psl.sqrPWM(
        frequency,
        DUTY_CYCLE,
        PHASE,
        DUTY_CYCLE,
        2 * PHASE,
        DUTY_CYCLE,
        3 * PHASE,
        DUTY_CYCLE,
    )

    la = logic_analyzer.LogicAnalyzer(psl.H)
    e2e_time = (frequency ** -1) * 16
    with pytest.raises(ValueError):
        la.capture(4, 10, modes=4 * ["sixteen rising"], e2e_time=e2e_time)


def test_capture_nonblocking(la):
    la.capture(1, block=False)
    time.sleep(MAX_SAMPLES * FREQUENCY ** -1)
    t = la.fetch_data()
    assert len(t[0]) == MAX_SAMPLES


def test_capture_rising_edges(la):
    t1, t2 = la.capture(2, 100, modes=["any", "rising"])
    t1 -= t1[0]
    t2 -= t2[0]
    assert t2[-1] == pytest.approx(2 * t1[-1], rel=RELTOL)


def test_capture_four_rising_edges(la):
    t1, t2 = la.capture(2, 100, modes=["rising", "four rising"])
    t1 -= t1[0]
    t2 -= t2[0]
    assert t2[-1] == pytest.approx(4 * t1[-1], rel=RELTOL)


def test_capture_sixteen_rising_edges(la):
    t1, t2 = la.capture(2, 100, modes=["four rising", "sixteen rising"])
    t1 -= t1[0]
    t2 -= t2[0]
    assert t2[-1] == pytest.approx(4 * t1[-1], rel=RELTOL)


def test_capture_too_many_events(la):
    with pytest.raises(ValueError):
        la.capture(1, MAX_SAMPLES + 1)


def test_capture_too_many_channels(la):
    with pytest.raises(ValueError):
        la.capture(5)


def test_capture_timeout():
    psl = sciencelab.connect()
    frequency = 100
    psl.sqrPWM(
        frequency,
        DUTY_CYCLE,
        PHASE,
        DUTY_CYCLE,
        2 * PHASE,
        DUTY_CYCLE,
        3 * PHASE,
        DUTY_CYCLE,
    )
    events = 100
    timeout = (events * frequency ** -1) / 4
    la = logic_analyzer.LogicAnalyzer(psl.H)
    with pytest.raises(RuntimeError):
        la.capture(1, timeout=timeout)


def test_measure_frequency(la):
    frequency = la.measure_frequency("ID1", timeout=0.1)
    assert FREQUENCY == pytest.approx(frequency, rel=RELTOL)


def test_measure_frequency_firmware(la):
    frequency = la.measure_frequency("ID2", timeout=0.1, simultaneous_oscilloscope=True)
    assert FREQUENCY == pytest.approx(frequency, rel=RELTOL)


def test_measure_interval(la):
    la.configure_trigger("ID1", "falling")
    interval = la.measure_interval(
        channels=["ID1", "ID2"], modes=["rising", "falling"], timeout=0.1
    )
    expected_interval = FREQUENCY ** -1 * -PHASE * MICROSECONDS
    assert expected_interval == pytest.approx(interval, rel=RELTOL)


def test_measure_interval_same_channel(la):
    la.configure_trigger("ID1", "falling")
    interval = la.measure_interval(
        channels=["ID1", "ID1"], modes=["rising", "falling"], timeout=0.1
    )
    expected_interval = FREQUENCY ** -1 * DUTY_CYCLE * MICROSECONDS
    assert expected_interval == pytest.approx(interval, rel=RELTOL)


def test_measure_interval_same_channel_any(la):
    la.configure_trigger("ID1", "falling")
    interval = la.measure_interval(
        channels=["ID1", "ID1"], modes=["any", "any"], timeout=0.1
    )
    expected_interval = FREQUENCY ** -1 * DUTY_CYCLE * MICROSECONDS
    assert expected_interval == pytest.approx(interval, rel=RELTOL)


def test_measure_interval_same_channel_four_rising(la):
    la.configure_trigger("ID1", "falling")
    interval = la.measure_interval(
        channels=["ID1", "ID1"], modes=["rising", "four rising"], timeout=0.1
    )
    expected_interval = FREQUENCY ** -1 * 3 * MICROSECONDS
    assert expected_interval == pytest.approx(interval, rel=RELTOL)


def test_measure_interval_same_channel_sixteen_rising(la):
    la.configure_trigger("ID1", "falling")
    interval = la.measure_interval(
        channels=["ID1", "ID1"], modes=["rising", "sixteen rising"], timeout=0.1
    )
    expected_interval = FREQUENCY ** -1 * 15 * MICROSECONDS
    assert expected_interval == pytest.approx(interval, rel=RELTOL)


def test_measure_interval_same_channel_same_event(la):
    la.configure_trigger("ID1", "falling")
    interval = la.measure_interval(
        channels=["ID3", "ID3"], modes=["rising", "rising"], timeout=0.1
    )
    expected_interval = FREQUENCY ** -1 * MICROSECONDS
    assert expected_interval == pytest.approx(interval, rel=RELTOL)


def test_measure_duty_cycle(la):
    period, duty_cycle = la.measure_duty_cycle("ID4", timeout=0.1)
    expected_period = FREQUENCY ** -1 * MICROSECONDS
    assert (expected_period, DUTY_CYCLE) == pytest.approx(
        (period, duty_cycle), rel=RELTOL
    )


def test_get_xy_rising_trigger(la):
    la.configure_trigger("ID1", "rising")
    t = la.capture(1, 100)
    _, y = la.get_xy(t)
    assert y[0]


def test_get_xy_falling_trigger(la):
    la.configure_trigger("ID1", "falling")
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
    la.capture(1, modes=["sixteen rising"], block=False)
    time.sleep(MAX_SAMPLES * FREQUENCY ** -1)
    progress = la.get_progress()
    la.stop()
    time.sleep(MAX_SAMPLES * FREQUENCY ** -1)
    assert progress < 2500
    abstol = FREQUENCY // 1e4  # Some time passes between get_progress() and stop().
    assert progress == pytest.approx(la.get_progress(), abs=abstol)


def test_get_states():
    psl = sciencelab.connect()
    la = logic_analyzer.LogicAnalyzer(psl.H)
    frequency = 50
    psl.sqrPWM(frequency, DUTY_CYCLE, 0.5, DUTY_CYCLE, 0, DUTY_CYCLE, 0.5, DUTY_CYCLE)
    time.sleep(frequency ** -1)
    states = la.get_states()
    # Should be one of these, can't tell which in advance.
    expected_states1 = {"ID1": True, "ID2": False, "ID3": True, "ID4": False}
    expected_states2 = {"ID1": False, "ID2": True, "ID3": False, "ID4": True}
    assert states in (expected_states1, expected_states2)


def test_count_pulses(la):
    interval = 0.2
    pulses = la.count_pulses("ID2", interval)
    expected_pulses = FREQUENCY * interval
    assert expected_pulses == pytest.approx(pulses, rel=0.1)  # Pretty bad accuracy.
