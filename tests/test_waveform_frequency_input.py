"""Requested analog frequencies remain distinct from generated frequencies."""

from unittest.mock import Mock

import pytest

from pslab.connection import ConnectionHandler
from pslab.instrument.waveform_generator import WaveformGenerator


@pytest.mark.parametrize(
    "channels,requested",
    [("SI1", [1001]), ("SI2", [2003]), (["SI1", "SI2"], [1001, 2003])],
)
def test_generate_does_not_replace_requested_frequency_list(channels, requested):
    generator = WaveformGenerator(Mock(spec=ConnectionHandler))
    original = requested.copy()
    actual = generator.generate(channels, requested)
    assert requested == original
    assert actual != original
    names = channels if isinstance(channels, list) else [channels]
    assert actual == [generator._channels[name].frequency for name in names]


def test_failed_generation_does_not_partially_replace_requested_frequencies():
    generator = WaveformGenerator(Mock(spec=ConnectionHandler))
    requested = [1001, 0.05]
    with pytest.raises(ValueError, match="Frequency must be greater"):
        generator.generate(["SI1", "SI2"], requested)
    assert requested == [1001, 0.05]
    assert generator._device.mock_calls == []


def test_list_and_scalar_requests_program_identical_commands():
    list_generator = WaveformGenerator(Mock(spec=ConnectionHandler))
    scalar_generator = WaveformGenerator(Mock(spec=ConnectionHandler))
    actual = list_generator.generate(["SI1", "SI2"], [1001, 1001], phase=90)
    scalar_actual = scalar_generator.generate(["SI1", "SI2"], 1001, phase=90)
    assert actual == scalar_actual
    assert list_generator._device.mock_calls == scalar_generator._device.mock_calls
