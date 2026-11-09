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
from pslab.instrument.oscilloscope import Oscilloscope
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


# The tests below use a stand-in transport and do not need a connected PSLab.


class FakeDevice:
    """Stand-in for a SerialHandler, recording the commands it receives."""

    def __init__(self):
        self.commands = []

    def send_byte(self, value):
        self.commands.append(value)

    def send_int(self, value):
        self.commands.append(value)

    def get_ack(self):
        return True

    def get_byte(self):
        return 0

    def get_int(self):
        return 0


def test_count_pulses_from_the_measured_period(mocker):
    la = LogicAnalyzer(FakeDevice())
    # A 100 kHz signal, sampled every 16th rising edge.
    mocker.patch.object(la, "capture", return_value=[np.array([0, 160])])
    assert la.count_pulses("LA2", 0.2) == FREQUENCY * 0.2


@pytest.mark.parametrize("timestamps", [np.array([]), np.array([500, 500])])
def test_count_pulses_without_a_measurable_period(mocker, timestamps):
    la = LogicAnalyzer(FakeDevice())
    mocker.patch.object(la, "capture", return_value=[timestamps])
    assert la.count_pulses("LA2", 0.2) == 0


def test_count_pulses_does_not_use_the_firmware_counter(mocker):
    device = FakeDevice()
    la = LogicAnalyzer(device)
    mocker.patch.object(la, "capture", return_value=[np.array([0, 160])])
    la.count_pulses("LA2", 0.2)
    assert CP.START_COUNTING not in device.commands
    assert CP.FETCH_COUNT not in device.commands


def capture_updating_the_channel_map(la, timestamps):
    """Stand-in for capture(), which maps a channel name to channel one."""

    def capture(channels, events, **kwargs):
        la._check_arguments(channels, events)
        return [timestamps]

    return capture


def test_count_pulses_restores_the_channel_map(mocker):
    la = LogicAnalyzer(FakeDevice())
    mocker.patch.object(
        la,
        "capture",
        side_effect=capture_updating_the_channel_map(la, np.array([0, 160])),
    )
    assert la.count_pulses("LA2", 0.2) == FREQUENCY * 0.2
    assert la._channel_one_map == "LA1"


def test_count_pulses_restores_the_channel_map_when_capture_fails(mocker):
    la = LogicAnalyzer(FakeDevice())

    def capture(channels, events, **kwargs):
        la._check_arguments(channels, events)
        raise ValueError("capture failed")

    mocker.patch.object(la, "capture", side_effect=capture)
    with pytest.raises(ValueError):
        la.count_pulses("LA2", 0.2)
    assert la._channel_one_map == "LA1"


def test_count_pulses_rejects_a_negative_interval(mocker):
    la = LogicAnalyzer(FakeDevice())
    capture = mocker.patch.object(la, "capture", return_value=[np.array([0, 160])])
    with pytest.raises(ValueError):
        la.count_pulses("LA2", -0.2)
    assert not capture.called


@pytest.mark.parametrize("timeout", [0, 0.05, 1])
def test_count_pulses_keeps_the_positional_timeout(mocker, timeout):
    la = LogicAnalyzer(FakeDevice())
    capture = mocker.patch.object(la, "capture", return_value=[np.array([0, 160])])

    assert la.count_pulses("LA2", 0.2, timeout) == 20000
    assert capture.call_args.kwargs["timeout"] == timeout
    assert capture.call_args.kwargs["block"] is True


def test_count_pulses_keeps_the_nonblocking_api(mocker):
    la = LogicAnalyzer(FakeDevice())
    capture = mocker.patch.object(la, "capture", return_value=None)
    clock = mocker.patch(
        "pslab.instrument.logic_analyzer.time.monotonic", return_value=10
    )

    assert la.count_pulses("LA2", 0.1, False) is None
    assert capture.call_args.kwargs["block"] is False

    fetch = mocker.patch.object(la, "fetch_data", return_value=[np.array([0, 160])])
    clock.return_value = 10.2
    assert la.fetch_pulse_count() == 20000
    fetch.assert_called_once_with()
    assert la._channel_one_map == "LA1"


def test_nonblocking_pulse_capture_returns_before_fetching(mocker):
    la = LogicAnalyzer(FakeDevice())
    clock = mocker.patch(
        "pslab.instrument.logic_analyzer.time.monotonic", return_value=10
    )
    fetch = mocker.patch.object(la, "fetch_data", return_value=[np.array([0, 160])])

    assert la.count_pulses("LA2", block=False) is None
    fetch.assert_not_called()
    assert la._channel_one_map == "LA1"

    def fetched_channel():
        assert la._channel_one_map == "LA2"
        return [np.array([0, 160])]

    fetch.side_effect = fetched_channel
    clock.return_value = 10.2
    assert la.fetch_pulse_count() == 20000
    clock.return_value = 10.4
    assert la.fetch_pulse_count() == 40000
    assert la._channel_one_map == "LA1"


@pytest.mark.parametrize(
    "timestamps", [np.array([]), np.array([160]), np.array([160, 160])]
)
def test_nonblocking_pulse_fetch_waits_for_a_measurable_period(mocker, timestamps):
    la = LogicAnalyzer(FakeDevice())
    mocker.patch.object(la, "capture", return_value=None)
    la.count_pulses("LA2", block=False)
    mocker.patch.object(la, "fetch_data", return_value=[timestamps])
    assert la.fetch_pulse_count() == 0


def test_nonblocking_pulse_fetch_restores_channel_map_after_error(mocker):
    la = LogicAnalyzer(FakeDevice())
    mocker.patch.object(la, "capture", return_value=None)
    la.count_pulses("LA2", block=False)
    mocker.patch.object(la, "fetch_data", side_effect=OSError("read failed"))
    with pytest.raises(OSError, match="read failed"):
        la.fetch_pulse_count()
    assert la._channel_one_map == "LA1"


def test_nonblocking_pulse_capture_failure_leaves_no_pending_count(mocker):
    la = LogicAnalyzer(FakeDevice())
    capture = mocker.patch.object(la, "capture", return_value=None)
    la.count_pulses("LA2", block=False)
    capture.side_effect = OSError("capture failed")
    with pytest.raises(OSError, match="capture failed"):
        la.count_pulses("LA3", block=False)
    with pytest.raises(RuntimeError, match="No nonblocking pulse count is active"):
        la.fetch_pulse_count()
    assert la._channel_one_map == "LA1"


def test_another_capture_invalidates_the_pending_pulse_count(mocker):
    la = LogicAnalyzer(FakeDevice())
    la.count_pulses("LA2", block=False)

    la.capture("LA3", events=2, block=False)

    with pytest.raises(RuntimeError, match="No nonblocking pulse count is active"):
        la.fetch_pulse_count()


def test_count_pulses_across_a_counter_rollover(mocker):
    la = LogicAnalyzer(FakeDevice())
    # Same 100 kHz signal, but the second event is seen after the 32-bit
    # capture counter has wrapped.
    wrap = 2**32 / CP.CLOCK_RATE * 1e6
    mocker.patch.object(la, "capture", return_value=[np.array([wrap - 80, 80])])
    assert la.count_pulses("LA2", 0.2) == FREQUENCY * 0.2


@pytest.mark.parametrize("writer", ["same_analyzer", "other_analyzer", "scope"])
@pytest.mark.parametrize("operation", ["fill", "clear", "capture"])
def test_buffer_writers_invalidate_the_pending_pulse_count(mocker, writer, operation):
    device = FakeDevice()
    la = LogicAnalyzer(device)
    la.count_pulses("LA2", block=False)
    mocker.patch.object(la, "fetch_data", return_value=[np.array([0, 160])])
    if writer == "same_analyzer":
        instrument = la
    elif writer == "other_analyzer":
        instrument = LogicAnalyzer(device)
    else:
        instrument = Oscilloscope(device)

    if operation == "fill":
        instrument.fill_buffer([1, 2, 3, 4])
    elif operation == "clear":
        instrument.clear_buffer(4)
    elif writer == "scope":
        instrument.capture(1, 4, 1, block=False)
    else:
        instrument.capture("LA3", events=2, block=False)

    with pytest.raises(RuntimeError, match="No nonblocking pulse count is active"):
        la.fetch_pulse_count()


@pytest.mark.parametrize(
    "operation", ["read", "empty_fill", "empty_clear", "other_device_write"]
)
def test_buffer_operations_preserve_an_unmodified_pulse_capture(mocker, operation):
    device = FakeDevice()
    la = LogicAnalyzer(device)
    clock = mocker.patch(
        "pslab.instrument.logic_analyzer.time.monotonic", return_value=10
    )
    la.count_pulses("LA2", block=False)
    mocker.patch.object(la, "fetch_data", return_value=[np.array([0, 160])])
    other = LogicAnalyzer(device)

    if operation == "read":
        other.fetch_buffer(4)
    elif operation == "empty_fill":
        other.fill_buffer([])
    elif operation == "empty_clear":
        other.clear_buffer(0)
    else:
        LogicAnalyzer(FakeDevice()).fill_buffer([1, 2, 3, 4])

    clock.return_value = 10.2
    assert la.fetch_pulse_count() == 20000


@pytest.mark.parametrize("operation", ["fill", "clear", "capture"])
def test_failed_buffer_writes_invalidate_the_pending_pulse_count(mocker, operation):
    device = FakeDevice()
    la = LogicAnalyzer(device)
    la.count_pulses("LA2", block=False)
    scope = Oscilloscope(device)
    # Bypass PGA setup so the failed ACK belongs to the buffer-writing command.
    mocker.patch.object(scope, "_set_gain")
    mocker.patch.object(device, "get_ack", side_effect=OSError("ack failed"))
    mocker.patch.object(la, "fetch_data", return_value=[np.array([0, 160])])

    with pytest.raises(OSError, match="ack failed"):
        if operation == "fill":
            scope.fill_buffer([1, 2, 3, 4])
        elif operation == "clear":
            scope.clear_buffer(4)
        else:
            scope.capture(1, 4, 1, block=False)

    with pytest.raises(RuntimeError, match="No nonblocking pulse count is active"):
        la.fetch_pulse_count()


@pytest.mark.parametrize("block", [False, True])
def test_pulse_count_rejects_ambiguous_long_gap(mocker, block):
    la = LogicAnalyzer(FakeDevice())
    clock = mocker.patch(
        "pslab.instrument.logic_analyzer.time.monotonic", return_value=10
    )
    wrap = 2**32 / CP.CLOCK_RATE
    # A 0.1 Hz signal has 160 seconds between every 16th rising edge.
    timestamps = np.array([1, (161 % wrap)]) * 1e6

    def capture(*args, **kwargs):
        clock.return_value = 171
        return [timestamps] if block else None

    mocker.patch.object(la, "capture", side_effect=capture)
    mocker.patch.object(la, "fetch_data", return_value=[timestamps])
    result = la.count_pulses("LA2", interval=161, timeout=200, block=block)
    if not block:
        result = la.fetch_pulse_count()
    assert result == 0


@pytest.mark.parametrize("block", [False, True])
@pytest.mark.parametrize("offset", [-1e-6, 0, 1e-6])
def test_pulse_count_bounds_capture_duration_not_count_interval(mocker, block, offset):
    la = LogicAnalyzer(FakeDevice())
    clock = mocker.patch(
        "pslab.instrument.logic_analyzer.time.monotonic", return_value=0
    )
    elapsed = 2**32 / CP.CLOCK_RATE + offset
    timestamps = np.array([100, 260])

    def capture(*args, **kwargs):
        if block:
            clock.return_value = elapsed
            return [timestamps]

    def fetch():
        # The duration check must include time spent retrieving timestamps.
        clock.return_value = elapsed
        return [timestamps]

    mocker.patch.object(la, "capture", side_effect=capture)
    mocker.patch.object(la, "fetch_data", side_effect=fetch)
    result = la.count_pulses("LA2", interval=1000, block=block)
    if not block:
        result = la.fetch_pulse_count()
    expected = round((1000 if block else elapsed) * FREQUENCY) if offset < 0 else 0
    assert result == expected
    assert la._channel_one_map == "LA1"


def test_repeated_pulse_fetch_rejects_a_later_ambiguous_capture(mocker):
    la = LogicAnalyzer(FakeDevice())
    clock = mocker.patch(
        "pslab.instrument.logic_analyzer.time.monotonic", return_value=0
    )
    la.count_pulses("LA2", block=False)
    mocker.patch.object(la, "fetch_data", return_value=[np.array([100, 260])])
    clock.return_value = 0.2
    assert la.fetch_pulse_count() == 20000
    clock.return_value = 160
    assert la.fetch_pulse_count() == 0
