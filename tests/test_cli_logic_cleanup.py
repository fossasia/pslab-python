"""Hardware-independent CLI cleanup tests using real logic-analyzer commands."""

from unittest.mock import Mock, call

import numpy as np
import pytest

from pslab import cli
from pslab import protocol as CP
from pslab.connection import ConnectionHandler
from pslab.instrument.logic_analyzer import LogicAnalyzer


@pytest.fixture
def analyzer(monkeypatch):
    device = Mock(spec=ConnectionHandler)
    instrument = LogicAnalyzer(device)
    monkeypatch.setattr(cli, "LogicAnalyzer", lambda connection: instrument)
    return device, instrument


@pytest.mark.parametrize("channels", [1, 2, 3, 4])
@pytest.mark.parametrize("error", [KeyboardInterrupt, RuntimeError, ValueError])
def test_interrupted_wait_stops_acquisition(analyzer, monkeypatch, channels, error):
    device, instrument = analyzer
    failure = error("interrupted acquisition wait")
    fetch = Mock()
    monkeypatch.setattr(instrument, "fetch_data", fetch)

    def interrupted_wait(duration):
        assert duration == 60
        device.reset_mock()
        raise failure

    monkeypatch.setattr(cli.time, "sleep", interrupted_wait)

    with pytest.raises(error) as caught:
        cli.logic_analyzer(device, channels, 60)

    assert caught.value is failure
    assert device.send_byte.call_args_list == [call(CP.TIMING), call(CP.STOP_LA)]
    device.get_ack.assert_called_once_with()
    fetch.assert_not_called()


@pytest.mark.parametrize("channels", [1, 2, 3, 4])
def test_success_stops_before_fetch_and_keeps_channel_data(
    analyzer, monkeypatch, channels
):
    device, instrument = analyzer
    timestamps = [np.array([10, 20]) for _ in range(channels)]

    def wait(duration):
        assert duration == 0.25
        device.reset_mock()

    def fetch():
        assert device.send_byte.call_args_list == [call(CP.TIMING), call(CP.STOP_LA)]
        device.get_ack.assert_called_once_with()
        return timestamps

    monkeypatch.setattr(cli.time, "sleep", wait)
    monkeypatch.setattr(instrument, "fetch_data", fetch)
    headers, data = cli.logic_analyzer(device, channels, 0.25)
    assert headers == ["LA1", "LA2", "LA3", "LA4"][:channels]
    assert data is timestamps


def test_failed_capture_does_not_attempt_additional_stop(analyzer, monkeypatch):
    device, instrument = analyzer
    failure = OSError("capture initiation failed")
    monkeypatch.setattr(instrument, "_capture_one", Mock(side_effect=failure))
    wait = Mock()
    monkeypatch.setattr(cli.time, "sleep", wait)

    with pytest.raises(OSError) as caught:
        cli.logic_analyzer(device, 1, 60)

    assert caught.value is failure
    wait.assert_not_called()
    # capture() stops the prior acquisition before attempting to start a new one.
    assert device.send_byte.call_args_list.count(call(CP.STOP_LA)) == 1


def test_failed_stop_keeps_the_wait_error_as_context(analyzer, monkeypatch):
    device, instrument = analyzer
    failure = KeyboardInterrupt("interrupted acquisition wait")
    cleanup_failure = OSError("device transport unavailable")
    fetch = Mock()
    monkeypatch.setattr(instrument, "fetch_data", fetch)

    def interrupted_wait(duration):
        device.reset_mock()
        device.get_ack.side_effect = cleanup_failure
        raise failure

    monkeypatch.setattr(cli.time, "sleep", interrupted_wait)
    with pytest.raises(OSError) as caught:
        cli.logic_analyzer(device, 1, 60)

    assert caught.value is cleanup_failure
    assert caught.value.__context__ is failure

    assert device.send_byte.call_args_list == [call(CP.TIMING), call(CP.STOP_LA)]
    fetch.assert_not_called()
