"""Invalid logic capture modes must preserve previous acquisition data."""

import copy

import pytest

import pslab.protocol as CP
from pslab.instrument.digital import MODES
from pslab.instrument.logic_analyzer import LogicAnalyzer


class CaptureConnection:
    """Record device commands without connecting to physical hardware."""

    def __init__(self):
        self.commands = []

    def send_byte(self, value):
        """Record a protocol byte."""
        self.commands.append(value)

    def send_int(self, value):
        """Record a protocol integer."""
        self.commands.append(value)

    def get_ack(self):
        """Acknowledge each command."""
        return 1


@pytest.mark.parametrize("channels", [1, 2, 4, "LA3", ["LA3", "LA4"]])
@pytest.mark.parametrize("modes", [("invalid",), ("rising", "invalid")])
def test_invalid_modes_leave_running_capture_and_buffer_untouched(channels, modes):
    connection = CaptureConnection()
    analyzer = LogicAnalyzer(connection)
    analyzer._prescaler = 2
    analyzer._channels["LA1"].events_in_buffer = 12
    analyzer._channels["LA1"].buffer_idx = 0
    analyzer._channels["LA1"]._logic_mode = MODES["falling"]
    before = copy.deepcopy(analyzer.__dict__)

    with pytest.raises(KeyError, match="invalid"):
        analyzer.capture(channels, events=5, modes=modes, block=False)

    assert connection.commands == []
    assert analyzer._prescaler == before["_prescaler"]
    assert analyzer._channel_one_map == before["_channel_one_map"]
    assert analyzer._channel_two_map == before["_channel_two_map"]
    for name, channel in analyzer._channels.items():
        assert channel.__dict__ == before["_channels"][name].__dict__


@pytest.mark.parametrize("mode", list(MODES))
def test_valid_modes_still_start_capture_with_expected_protocol(mode):
    connection = CaptureConnection()
    analyzer = LogicAnalyzer(connection)

    assert analyzer.capture("LA3", events=5, modes=[mode], block=False) is None

    assert connection.commands[:2] == [CP.TIMING, CP.STOP_LA]
    assert CP.CLEAR_BUFFER in connection.commands
    assert CP.START_ALTERNATE_ONE_CHAN_LA in connection.commands
    assert analyzer._channels["LA3"]._logic_mode == MODES[mode]
    assert analyzer._channels["LA3"].events_in_buffer == 5
