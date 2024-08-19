"""Common fixtures for pslab tests."""

import pytest

from pslab import serial_handler


@pytest.fixture
def handler():
    """Return a SerialHandler instance."""
    return serial_handler.SerialHandler()
