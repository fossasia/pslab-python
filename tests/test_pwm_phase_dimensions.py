"""Validate PWM list dimensions before changing outputs or local state."""

from unittest.mock import Mock

import pytest

from pslab.connection import ConnectionHandler
from pslab.instrument.waveform_generator import PWMGenerator


@pytest.fixture
def generator():
    """Return a real PWM generator with a mocked connection backend."""
    return PWMGenerator(Mock(spec=ConnectionHandler))


@pytest.mark.parametrize(
    "channels,phases",
    [
        (["SQ1", "SQ2"], []),
        (["SQ1", "SQ2"], [0.1]),
        (["SQ1", "SQ2"], [0.1, 0.2, 0.3]),
        ("SQ1", [0.1, 0.2]),
        (2, [0.1]),
    ],
)
def test_invalid_phase_dimensions_do_not_program_outputs(generator, channels, phases):
    with pytest.raises(ValueError, match="Dimension mismatch"):
        generator.generate(channels, 1000, 0.5, phases)
    assert generator.frequency == 0
    assert generator._device.mock_calls == []
    assert all(output.duty_cycle == 0 for output in generator._channels.values())


@pytest.mark.parametrize("channels", [["SQ1", "SQ2"], 2])
def test_matched_phase_list_configures_each_channel(generator, channels):
    phases = [0.1, 0.2]
    generator.generate(channels, 1000, [0.25, 0.5], phases)
    assert generator._channels["SQ1"].phase == 0.1
    assert generator._channels["SQ2"].phase == 0.2
    assert generator._channels["SQ1"].duty_cycle == 0.25
    assert generator._channels["SQ2"].duty_cycle == 0.5
    assert phases == [0.1, 0.2]
    generator._device.get_ack.assert_called()


def test_scalar_phase_keeps_incremental_phase_behavior():
    scalar = PWMGenerator(Mock(spec=ConnectionHandler))
    explicit = PWMGenerator(Mock(spec=ConnectionHandler))
    channels = ["SQ1", "SQ2", "SQ3", "SQ4"]
    scalar.generate(channels, 1000, 0.5, 0.1)
    explicit.generate(channels, 1000, 0.5, [i * 0.1 for i in range(4)])
    assert scalar._device.mock_calls == explicit._device.mock_calls
    assert [output.phase for output in scalar._channels.values()] == [
        i * 0.1 for i in range(4)
    ]


def test_invalid_phase_list_preserves_previous_configuration(generator):
    generator.generate(["SQ1", "SQ2"], 1000, 0.5, [0.1, 0.2])
    generator._device.reset_mock()
    with pytest.raises(ValueError, match="Dimension mismatch"):
        generator.generate(["SQ1", "SQ2"], 2000, 0.25, [0.3])
    assert generator.frequency == 1000
    assert generator._channels["SQ1"].phase == 0.1
    assert generator._channels["SQ2"].phase == 0.2
    assert generator._channels["SQ1"].duty_cycle == 0.5
    assert generator._device.mock_calls == []


def test_invalid_duty_list_preserves_previous_frequency(generator):
    generator.generate("SQ1", 1000, 0.5)
    generator._device.reset_mock()
    with pytest.raises(ValueError, match="Dimension mismatch"):
        generator.generate(["SQ1", "SQ2"], 2000, [0.25], [0.1, 0.2])
    assert generator.frequency == 1000
    assert generator._device.mock_calls == []
