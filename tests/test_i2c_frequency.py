"""Tests for I2C baudrate readback feature (Issue #195).

These are unit tests that use a mock ConnectionHandler, so they can run
without a physical PSLab device connected.
"""

from unittest.mock import MagicMock, patch

import pytest

from pslab.bus.i2c import I2CMaster, I2CSlave, _I2CPrimitive
import pslab.protocol as CP


@pytest.fixture
def mock_device():
    """Return a mock ConnectionHandler that responds to I2C commands."""
    device = MagicMock()
    device.send_byte = MagicMock()
    device.send_int = MagicMock()
    device.get_ack = MagicMock(return_value=1)  # ACK
    device.read = MagicMock(return_value=b"\x01")
    return device


@pytest.fixture
def master(mock_device):
    """Return an I2CMaster with a mocked device."""
    with patch("pslab.bus.i2c.autoconnect", return_value=mock_device):
        return I2CMaster(device=mock_device)


@pytest.fixture
def primitive(mock_device):
    """Return a bare _I2CPrimitive with a mocked device."""
    with patch("pslab.bus.i2c.autoconnect", return_value=mock_device):
        return _I2CPrimitive(device=mock_device)


# ============================================================
# Test 1: _frequency is None before _configure is called
# ============================================================
class TestFrequencyInitialization:

    def test_primitive_frequency_is_none_on_init(self, primitive):
        """_I2CPrimitive should have _frequency=None before any configure."""
        # _I2CPrimitive.__init__ does NOT call _configure, so it stays None.
        assert primitive._frequency is None

    def test_master_frequency_is_set_after_init(self, master):
        """I2CMaster.__init__ calls configure(125e3), so frequency should be set."""
        assert master.frequency is not None
        assert isinstance(master.frequency, float)


# ============================================================
# Test 2: Default frequency is ~125 kHz after I2CMaster init
# ============================================================
class TestDefaultFrequency:

    def test_default_frequency_value(self, master):
        """I2CMaster should default to ~125 kHz (the lowest PSLab supports)."""
        # The exact value depends on brgval rounding.
        # brgval = int((1/125000 - 150e-9) * 64e6 - 2) = int(509.39) = 509
        # actual_freq = 1 / ((509 + 2) / 64e6 + 150e-9)
        expected_brgval = _I2CPrimitive._get_i2c_brgval(125e3)
        expected_freq = _I2CPrimitive._get_i2c_frequency(expected_brgval)
        assert master.frequency == pytest.approx(expected_freq)


# ============================================================
# Test 3: frequency stores ACTUAL hardware freq, not requested
# ============================================================
class TestActualFrequency:

    def test_frequency_is_actual_not_requested(self, master):
        """Stored frequency should be the actual hardware freq, not the requested one."""
        requested = 400000  # User requests 400 kHz
        master.configure(requested)
        # Due to brgval rounding, actual != requested.
        brgval = _I2CPrimitive._get_i2c_brgval(requested)
        actual = _I2CPrimitive._get_i2c_frequency(brgval)
        assert master.frequency == pytest.approx(actual)
        # Actual will be slightly different from requested.
        assert master.frequency != requested

    def test_frequency_matches_brgval_computation(self, master):
        """Verify frequency computation matches the brgval->freq math."""
        test_frequencies = [125e3, 250e3, 400e3, 1e6, 3.2e6]

        for freq in test_frequencies:
            brgval = _I2CPrimitive._get_i2c_brgval(freq)

            if _I2CPrimitive._MIN_BRGVAL <= brgval <= _I2CPrimitive._MAX_BRGVAL:
                master.configure(freq)
                expected = _I2CPrimitive._get_i2c_frequency(brgval)
                assert master.frequency == pytest.approx(expected), (
                    f"Mismatch for requested freq {freq}: "
                    f"got {master.frequency}, expected {expected}"
                )


# ============================================================
# Test 4: frequency updates on reconfigure
# ============================================================
class TestFrequencyUpdate:

    def test_frequency_updates_after_reconfigure(self, master):
        """Frequency should update each time configure() is called."""
        master.configure(125e3)
        freq1 = master.frequency

        master.configure(400e3)
        freq2 = master.frequency

        assert freq1 != freq2
        assert freq2 > freq1  # 400 kHz > 125 kHz

    def test_frequency_updates_multiple_times(self, master):
        """Frequency should correctly track through multiple reconfigurations."""
        frequencies = [125e3, 250e3, 400e3, 250e3, 125e3]

        for requested in frequencies:
            master.configure(requested)
            brgval = _I2CPrimitive._get_i2c_brgval(requested)
            expected = _I2CPrimitive._get_i2c_frequency(brgval)
            assert master.frequency == pytest.approx(expected)


# ============================================================
# Test 5: frequency unchanged on invalid configure (ValueError)
# ============================================================
class TestFrequencyOnError:

    def test_frequency_unchanged_on_invalid_frequency(self, master):
        """If configure() raises ValueError, frequency should remain unchanged."""
        master.configure(125e3)
        original_freq = master.frequency

        # Too low frequency should raise ValueError.
        with pytest.raises(ValueError):
            master.configure(1)  # Way too low

        # Frequency should be unchanged.
        assert master.frequency == original_freq

    def test_frequency_unchanged_on_too_high_frequency(self, master):
        """If configure() raises ValueError for too-high freq, frequency unchanged."""
        master.configure(125e3)
        original_freq = master.frequency

        # Too high frequency should raise ValueError.
        with pytest.raises(ValueError):
            master.configure(100e6)  # Way too high (100 MHz)

        assert master.frequency == original_freq

    def test_frequency_unchanged_on_device_io_error(self, master, mock_device):
        """If the device raises IOError during configure, frequency stays unchanged."""
        master.configure(125e3)
        original_freq = master.frequency

        # Simulate a communication failure.
        mock_device.send_byte.side_effect = IOError("Simulated I/O failure")

        with pytest.raises(IOError):
            master.configure(400e3)

        assert master.frequency == original_freq

        # Restore normal behavior for other tests.
        mock_device.send_byte.side_effect = None


# ============================================================
# Test 6: frequency property is read-only
# ============================================================
class TestFrequencyReadOnly:

    def test_frequency_property_is_read_only(self, master):
        """Setting frequency directly should raise AttributeError."""
        with pytest.raises(AttributeError):
            master.frequency = 500000


# ============================================================
# Test 7: frequency property returns float
# ============================================================
class TestFrequencyType:

    def test_frequency_is_float(self, master):
        """Frequency should always be a float."""
        assert isinstance(master.frequency, float)

    def test_frequency_is_positive(self, master):
        """Frequency should always be positive."""
        assert master.frequency > 0


# ============================================================
# Test 8: _configure sends correct bytes to hardware
# ============================================================
class TestConfigureHardwareInteraction:

    def test_configure_sends_correct_protocol_bytes(self, master, mock_device):
        """Verify that _configure sends the correct I2C header and config bytes."""
        mock_device.reset_mock()
        master.configure(400e3)

        brgval = _I2CPrimitive._get_i2c_brgval(400e3)
        calls = mock_device.send_byte.call_args_list

        # Should send I2C_HEADER then I2C_CONFIG.
        assert any(c.args[0] == CP.I2C_HEADER for c in calls)
        assert any(c.args[0] == CP.I2C_CONFIG for c in calls)

        # Should send brgval as int.
        mock_device.send_int.assert_called_with(brgval)


# ============================================================
# Test 9: Boundary values — min and max valid frequencies
# ============================================================
class TestBoundaryFrequencies:

    def test_min_valid_frequency(self, master):
        """Test with the minimum valid frequency (brgval = MAX_BRGVAL = 511)."""
        min_freq = _I2CPrimitive._get_i2c_frequency(_I2CPrimitive._MAX_BRGVAL)
        master.configure(min_freq)
        assert master.frequency == pytest.approx(min_freq)

    def test_max_valid_frequency(self, master):
        """Test with a high frequency whose brgval equals MIN_BRGVAL + 1."""
        # _get_i2c_frequency(MIN_BRGVAL) gives the theoretical max, but due
        # to int() truncation in _get_i2c_brgval, that value may not
        # round-trip. Instead, find a frequency that computes to MIN_BRGVAL + 1.
        max_brgval_freq = _I2CPrimitive._get_i2c_frequency(
            _I2CPrimitive._MIN_BRGVAL + 1
        )
        # Verify brgval round-trips correctly.
        computed_brgval = _I2CPrimitive._get_i2c_brgval(max_brgval_freq)
        assert computed_brgval == _I2CPrimitive._MIN_BRGVAL + 1
        master.configure(max_brgval_freq)
        roundtrip_freq = _I2CPrimitive._get_i2c_frequency(computed_brgval)
        assert master.frequency == pytest.approx(roundtrip_freq)

    def test_just_below_min_frequency_raises(self, master):
        """Frequency just below minimum should raise ValueError."""
        min_freq = _I2CPrimitive._get_i2c_frequency(_I2CPrimitive._MAX_BRGVAL)

        with pytest.raises(ValueError):
            master.configure(min_freq * 0.5)  # Half of minimum

    def test_just_above_max_frequency_raises(self, master):
        """Frequency just above maximum should raise ValueError."""
        max_freq = _I2CPrimitive._get_i2c_frequency(_I2CPrimitive._MIN_BRGVAL)

        with pytest.raises(ValueError):
            master.configure(max_freq * 2)  # Double of maximum


# ============================================================
# Test 10: I2CSlave inherits _frequency from _I2CPrimitive
# ============================================================
class TestSlaveInheritsFrequency:

    def test_slave_has_frequency_attribute(self, mock_device):
        """I2CSlave should also have _frequency from _I2CPrimitive."""
        with patch("pslab.bus.i2c.autoconnect", return_value=mock_device):
            slave = I2CSlave(address=0x48, device=mock_device)
            # Slave doesn't call _configure, so it should be None.
            assert slave._frequency is None
