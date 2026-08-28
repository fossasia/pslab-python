"""Tests for MLX90614 infrared thermometer (Issue #182).

These are mock-based unit tests that run without a physical PSLab device.
"""

from unittest.mock import MagicMock, patch

import pytest

from pslab.external.MLX90614 import MLX90614


@pytest.fixture
def mock_device():
    """Return a mock ConnectionHandler."""
    device = MagicMock()
    device.send_byte = MagicMock()
    device.send_int = MagicMock()
    device.get_ack = MagicMock(return_value=1)
    return device


@pytest.fixture
def sensor(mock_device):
    """Return an MLX90614 with a mocked device."""
    with patch("pslab.bus.i2c.autoconnect", return_value=mock_device):
        return MLX90614(device=mock_device)


# ============================================================
# Test 1: Initialization
# ============================================================
class TestInitialization:

    def test_default_address(self, sensor):
        """Sensor should use address 0x5A."""
        assert sensor.address == 0x5A

    def test_default_source_is_object(self, sensor):
        """Default measurement source should be the object register."""
        assert sensor._source == 0x07

    def test_name_is_set(self, sensor):
        """Sensor should have a descriptive name."""
        assert sensor.name == "Passive IR temperature sensor"

    def test_accepts_device_parameter(self, mock_device):
        """Sensor should accept an optional device parameter."""
        with patch("pslab.bus.i2c.autoconnect", return_value=mock_device):
            s = MLX90614(device=mock_device)
            assert s.address == 0x5A


# ============================================================
# Test 2: Source selection
# ============================================================
class TestSourceSelection:

    def test_select_object_temperature(self, sensor):
        """Selecting 'object temperature' sets source to OBJ register."""
        sensor.select_source("object temperature")
        assert sensor._source == 0x07

    def test_select_ambient_temperature(self, sensor):
        """Selecting 'ambient temperature' sets source to AMB register."""
        sensor.select_source("ambient temperature")
        assert sensor._source == 0x06

    def test_invalid_source_no_change(self, sensor):
        """Selecting an invalid source should not change the current one."""
        original = sensor._source
        sensor.select_source("invalid source")
        assert sensor._source == original


# ============================================================
# Test 3: Temperature calculation
# ============================================================
class TestTemperatureCalculation:

    def test_known_temperature_conversion(self, sensor, mock_device):
        """Verify temperature conversion math with known raw bytes.

        Raw value 0x3A98 (15000) at 0.02 K per LSB = 300.00 K - 0.01
        = 299.99 K = 26.84 °C.
        """
        # 15000 = 0x3A98: LSB = 0x98, MSB = 0x3A, PEC = 0x00
        mock_device.read = MagicMock(return_value=b"\x98\x3A\x00")

        with patch.object(sensor, "read", return_value=bytearray(b"\x98\x3A\x00")):
            result = sensor.get_raw()

        assert result is not None
        assert len(result) == 1
        expected = ((((0x3A & 0x7F) << 8) + 0x98) * 0.02 - 0.01) - 273.15
        assert result[0] == pytest.approx(expected)

    def test_get_raw_returns_none_on_empty_read(self, sensor):
        """get_raw should return None when read returns empty data."""
        with patch.object(sensor, "read", return_value=bytearray()):
            result = sensor.get_raw()
            assert result is None

    def test_get_raw_returns_none_on_short_read(self, sensor):
        """get_raw should return None when fewer than 3 bytes are read."""
        with patch.object(sensor, "read", return_value=bytearray(b"\x00\x01")):
            result = sensor.get_raw()
            assert result is None


# ============================================================
# Test 4: High-level temperature methods
# ============================================================
class TestTemperatureMethods:

    def test_get_object_temperature_sets_source(self, sensor):
        """get_object_temperature should set source to OBJ register."""
        with patch.object(sensor, "read", return_value=bytearray(b"\x98\x3A\x00")):
            sensor.get_object_temperature()
            assert sensor._source == 0x07

    def test_get_ambient_temperature_sets_source(self, sensor):
        """get_ambient_temperature should set source to AMB register."""
        with patch.object(sensor, "read", return_value=bytearray(b"\x98\x3A\x00")):
            sensor.get_ambient_temperature()
            assert sensor._source == 0x06

    def test_get_object_temperature_returns_float(self, sensor):
        """get_object_temperature should return a single float."""
        with patch.object(sensor, "read", return_value=bytearray(b"\x98\x3A\x00")):
            result = sensor.get_object_temperature()
            assert isinstance(result, float)

    def test_get_ambient_temperature_returns_none_on_failure(self, sensor):
        """Should return None when the read fails."""
        with patch.object(sensor, "read", return_value=bytearray()):
            result = sensor.get_ambient_temperature()
            assert result is None


# ============================================================
# Test 5: read_reg uses logging
# ============================================================
class TestReadReg:

    def test_read_reg_logs_value(self, sensor, caplog):
        """read_reg should log the register value, not print it."""
        with patch.object(sensor, "read", return_value=bytearray(b"\x34\x12")):
            import logging
            with caplog.at_level(logging.INFO):
                sensor.read_reg(0x07)

            assert "0x1234" in caplog.text


# ============================================================
# Test 6: Return types
# ============================================================
class TestReturnTypes:

    def test_get_raw_returns_list_of_float(self, sensor):
        """get_raw should return a list containing one float."""
        with patch.object(sensor, "read", return_value=bytearray(b"\x98\x3A\x00")):
            result = sensor.get_raw()
            assert isinstance(result, list)
            assert isinstance(result[0], float)

    def test_temperature_is_reasonable(self, sensor):
        """A known raw value should produce a reasonable temperature."""
        # Room temp ~25°C: raw ~14915 (0x3A43)
        with patch.object(sensor, "read", return_value=bytearray(b"\x43\x3A\x00")):
            temp = sensor.get_object_temperature()
            assert -40 < temp < 85  # Sensor operating range


# ============================================================
# Test 7: Class attributes
# ============================================================
class TestClassAttributes:

    def test_numplots(self):
        assert MLX90614.NUMPLOTS == 1

    def test_plotnames(self):
        assert MLX90614.PLOTNAMES == ["Temp"]

    def test_class_name(self):
        assert MLX90614.name == "PIR temperature"
