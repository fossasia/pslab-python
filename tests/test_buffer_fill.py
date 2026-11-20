"""ADC buffer destinations must not skip values in the input data."""

from unittest.mock import Mock, call

import pytest

import pslab.protocol as CP
from pslab.connection import ConnectionHandler
from pslab.instrument.buffer import ADCBufferMixin


@pytest.mark.parametrize("starting_position", [0, 1, 10, 200])
@pytest.mark.parametrize("samples", [3, 128, 129, 260])
def test_fill_buffer_writes_all_data_at_requested_destination(
    starting_position, samples
):
    """Verify fill_buffer writes all samples when starting_position is nonzero."""
    buf = ADCBufferMixin()
    buf._device = Mock(spec=ConnectionHandler)
    data = list(range(samples))
    buf.fill_buffer(data, starting_position)
    expected = []
    for offset in range(0, samples, 128):
        values = data[offset : offset + 128]
        expected += [
            call.send_byte(CP.COMMON),
            call.send_byte(CP.FILL_BUFFER),
            call.send_int(starting_position + offset),
            call.send_int(len(values)),
        ]
        expected += [call.send_int(value) for value in values]
        expected.append(call.get_ack())
    assert buf._device.mock_calls == expected
    assert data == list(range(samples))


def test_fill_buffer_at_zero_keeps_existing_command_sequence():
    """Verify fill_buffer starting at 0 retains the original command sequence."""
    buf = ADCBufferMixin()
    buf._device = Mock(spec=ConnectionHandler)
    buf.fill_buffer([7, 8, 9])
    assert buf._device.mock_calls == [
        call.send_byte(CP.COMMON),
        call.send_byte(CP.FILL_BUFFER),
        call.send_int(0),
        call.send_int(3),
        call.send_int(7),
        call.send_int(8),
        call.send_int(9),
        call.get_ack(),
    ]


def test_fill_buffer_empty_data_does_not_send_commands():
    """Verify empty input data does not issue commands to the device."""
    buf = ADCBufferMixin()
    buf._device = Mock(spec=ConnectionHandler)
    buf.fill_buffer([], starting_position=200)
    assert buf._device.mock_calls == []
