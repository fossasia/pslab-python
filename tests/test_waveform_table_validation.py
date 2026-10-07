"""Hardware-independent validation of waveform uploads and command framing."""

from unittest.mock import Mock

import numpy as np
import pytest

import pslab.protocol as CP
from pslab.connection import ConnectionHandler
from pslab.instrument.waveform_generator import WaveformGenerator


@pytest.mark.parametrize("loader", ["table", "function"])
@pytest.mark.parametrize(
    "points",
    [
        np.zeros(0),
        np.zeros(1),
        np.zeros(511),
        np.zeros(513),
        np.zeros((512, 1)),
        np.zeros((2, 256)),
        np.full(512, np.nan),
        np.full(512, np.inf),
        np.full(512, -np.inf),
        np.full(512, 1j),
    ],
)
def test_invalid_table_does_not_write_or_change_channel(points, loader):
    device = Mock(spec=ConnectionHandler)
    generator = WaveformGenerator(device)
    channel = generator._channels["SI1"]
    previous_table = channel.waveform_table.copy()
    with pytest.raises(ValueError):
        if loader == "table":
            generator.load_table("SI1", points)
        else:
            generator.load_function("SI1", lambda x: points, [0, 1])
    assert device.mock_calls == []
    assert channel.wavetype == "sine"
    assert channel.waveform_table == previous_table


@pytest.mark.parametrize("channel", ["SI1", "SI2"])
@pytest.mark.parametrize("dtype", [np.float64, np.int16])
def test_valid_table_preserves_upload_framing(channel, dtype):
    device = Mock(spec=ConnectionHandler)
    generator = WaveformGenerator(device)
    points = np.linspace(-5, 5, 512).astype(dtype)
    original = points.copy()
    generator.load_table(channel, points)
    clipped = np.clip(points, -3.3, 3.3)
    expected = np.round((clipped + 3.3) / 6.6 * 511).astype(np.int16).tolist()
    assert [call.args[0] for call in device.send_int.call_args_list] == expected
    commands = [call.args[0] for call in device.send_byte.call_args_list]
    assert commands[:2] == [
        CP.WAVEGEN,
        CP.LOAD_WAVEFORM1 if channel == "SI1" else CP.LOAD_WAVEFORM2,
    ]
    assert (
        commands[2:]
        == np.round((clipped[::16] + 3.3) / 6.6 * 63).astype(np.int16).tolist()
    )
    device.get_ack.assert_called_once_with()
    assert generator._channels[channel].wavetype == "custom"
    np.testing.assert_array_equal(points, original)


@pytest.mark.parametrize("function", ["sine", "tria"])
def test_builtin_functions_keep_fixed_upload_sizes(function):
    device = Mock(spec=ConnectionHandler)
    generator = WaveformGenerator(device)
    generator.load_function("SI1", function)
    assert device.send_int.call_count == 512
    assert device.send_byte.call_count == 34
    assert generator._channels["SI1"].wavetype == function
