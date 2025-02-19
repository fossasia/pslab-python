"""Common fixtures for pslab tests."""

import pytest

from pslab.connection import SerialHandler


@pytest.fixture
def handler():
    """Return a SerialHandler instance."""
    sh = SerialHandler()
    sh.connect()
    return sh
