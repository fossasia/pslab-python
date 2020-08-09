import unittest
from unittest.mock import patch

from PSL import achan


class TestAnalogInput(unittest.TestCase):
    def setUp(self):
        self.Handler_patcher = patch("PSL.achan.packet_handler.Handler")
        self.mock_device = self.Handler_patcher.start()

    def tearDown(self):
        self.Handler_patcher.stop()

    def test_gain(self):
        ch1 = achan.AnalogInput("CH1", self.mock_device)
        example_gain = 8
        ch1.gain = example_gain
        self.assertEqual(ch1.gain, example_gain)
        gain_idx = achan.GAIN_VALUES.index(example_gain)
        self.mock_device.send_byte.assert_called_with(gain_idx)

    def test_gain_unsupported_value(self):
        ch2 = achan.AnalogInput("CH2", self.mock_device)
        bad_gain = 3
        with self.assertRaises(ValueError):
            ch2.gain = bad_gain

    def test_gain_set_unsupported_channel(self):
        ch3 = achan.AnalogInput("CH3", self.mock_device)
        example_gain = 10
        with self.assertRaises(TypeError):
            ch3.gain = example_gain

    def test_gain_get_unsupported_channel(self):
        ch3 = achan.AnalogInput("CH3", self.mock_device)
        self.assertIsNone(ch3.gain)
        self.assertEqual(ch3._gain, 1)

    def test_resolution(self):
        mic = achan.AnalogInput("MIC", self.mock_device)
        resolution_12bit = 12
        mic.resolution = resolution_12bit
        self.assertEqual(mic.resolution, resolution_12bit)
        self.assertEqual(mic._resolution, 2 ** resolution_12bit - 1)

    def test_resolution_unsupported_value(self):
        cap = achan.AnalogInput("CAP", self.mock_device)
        bad_resolution = 8
        with self.assertRaises(ValueError):
            cap.resolution = bad_resolution

    def test_scale(self):
        ch1 = achan.AnalogInput("CH1", self.mock_device)
        example_gain = 16
        ch1.gain = example_gain
        resolution_10bit = 10
        ch1.resolution = resolution_10bit
        raw_value = 588
        corresponding_voltage = -0.154233870967742
        self.assertAlmostEqual(ch1.scale(raw_value), corresponding_voltage)

    def test_unscale(self):
        ch1 = achan.AnalogInput("CH1", self.mock_device)
        example_gain = 16
        ch1.gain = example_gain
        resolution_10bit = 10
        ch1.resolution = resolution_10bit
        raw_value = 588
        corresponding_voltage = -0.154233870967742
        self.assertEqual(ch1.unscale(corresponding_voltage), raw_value)

    def test_unscale_clip(self):
        ch1 = achan.AnalogInput("CH1", self.mock_device)
        example_gain = 16
        ch1.gain = example_gain
        resolution_10bit = 10
        ch1.resolution = resolution_10bit
        raw_max = 2 ** resolution_10bit - 1  # 1023
        voltage_outside_range = -3.001008064516129  # raw = 2000
        self.assertEqual(ch1.unscale(voltage_outside_range), raw_max)
