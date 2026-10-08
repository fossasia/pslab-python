"""Test oscilloscope buffer limits without connected hardware."""

from unittest.mock import Mock, call

import numpy as np
import pytest

import pslab.protocol as CP
from pslab.connection import ConnectionHandler
from pslab.instrument.oscilloscope import Oscilloscope


@pytest.fixture
def scope():
    """Return an oscilloscope using a mock connection."""
    device = Mock(spec=ConnectionHandler)
    instrument = Oscilloscope(device)
    device.reset_mock()
    return instrument


@pytest.mark.parametrize(
    "channels,capacity", [(1, 10000), (2, 5000), (3, 2500), (4, 2500)]
)
@pytest.mark.parametrize("offset", [1, 833])
def test_capture_rejects_samples_beyond_buffer(scope, channels, capacity, offset):
    with pytest.raises(ValueError, match=f"Cannot collect more than {capacity}"):
        scope.capture(channels, capacity + offset, timegap=2, block=False)

    assert scope._device.mock_calls == []


@pytest.mark.parametrize(
    "channels,capacity", [(1, 10000), (2, 5000), (3, 2500), (4, 2500)]
)
def test_capture_accepts_full_buffer(scope, channels, capacity):
    timestamps = scope.capture(channels, capacity, timegap=2, block=False)[0]

    np.testing.assert_array_equal(timestamps, 2 * np.arange(capacity))
    assert call(capacity) in scope._device.send_int.call_args_list
    for channel in scope._channels.values():
        if channel.buffer_idx is not None:
            assert channel.buffer_idx + channel.samples_in_buffer <= CP.MAX_SAMPLES


def test_three_channel_capture_uses_four_channel_command(scope, monkeypatch):
    voltages = [np.zeros(2500) for _ in range(4)]
    monkeypatch.setattr(scope, "progress", lambda: (True, 2500))
    monkeypatch.setattr(scope, "fetch_data", lambda: voltages)
    monkeypatch.setattr("pslab.instrument.oscilloscope.time.sleep", lambda _: None)

    result = scope.capture(3, 2500, timegap=2)

    assert len(result) == 4
    assert all(result[i + 1] is voltages[i] for i in range(3))
    scope._device.send_byte.assert_any_call(CP.CAPTURE_FOUR)
    assert scope._channels["MIC"].buffer_idx == 7500
    assert scope._channels["MIC"].samples_in_buffer == 2500
