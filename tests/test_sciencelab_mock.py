from unittest.mock import patch

from pslab.sciencelab import ScienceLab


def test_sciencelab_mock_does_not_autoconnect():
    # If autoconnect is called, the test should fail immediately.
    with patch(
        "pslab.sciencelab.autoconnect",
        side_effect=AssertionError("autoconnect should not be called"),
    ):
        psl = ScienceLab(mock=True)

    # It should initialize and provide the expected mock firmware version object.
    assert psl.firmware.major == 3
    assert psl.firmware.minor == 0
    assert psl.firmware.patch == 0

    # In mock mode, instruments should not be instantiated (no hardware required).
    assert psl.logic_analyzer is None
    assert psl.oscilloscope is None
    assert psl.waveform_generator is None
    assert psl.pwm_generator is None
    assert psl.multimeter is None
    assert psl.power_supply is None
