import unittest
from unittest.mock import patch

import numpy as np

import PSL.commands_proto as CP
from PSL import oscilloscope


class TestOscilloscope(unittest.TestCase):
    def setUp(self):
        self.Handler_patcher = patch("PSL.oscilloscope.packet_handler.Handler")
        self.mock_device = self.Handler_patcher.start()
        example_signal = np.sin(np.arange(200) / 20)
        self.scope = oscilloscope.Oscilloscope(device=self.mock_device)
        unscale = self.scope._channels["CH1"].unscale
        example_raw_signal = [unscale(s) for s in example_signal]
        example_incoming_bytes = b""
        for r in example_raw_signal:
            example_incoming_bytes += CP.ShortInt.pack(r)
        self.mock_device.interface.read.return_value = example_incoming_bytes
        self.mock_device.get_byte.return_value = 1
        self.mock_device.get_int.return_value = 200

    def tearDown(self):
        self.Handler_patcher.stop()

    def test_capture_one_12bit(self):
        xy = self.scope.capture(channels=1, samples=200, timegap=2)
        self.assertEqual(np.shape(xy), (2, 200))
        self.assertEqual(self.scope._channels["CH1"].resolution, 12)

    def test_capture_one_high_speed(self):
        xy = self.scope.capture(channels=1, samples=200, timegap=0.5)
        self.assertEqual(np.shape(xy), (2, 200))
        self.assertEqual(self.scope._channels["CH1"].resolution, 10)

    def test_capture_one_trigger(self):
        self.scope.trigger_enabled = True
        xy = self.scope.capture(channels=1, samples=200, timegap=1)
        self.assertEqual(np.shape(xy), (2, 200))
        self.assertEqual(self.scope._channels["CH1"].resolution, 10)

    def test_capture_two(self):
        xy = self.scope.capture(channels=2, samples=200, timegap=2)
        self.assertEqual(np.shape(xy), (3, 200))

    def test_capture_four(self):
        xy = self.scope.capture(channels=4, samples=200, timegap=2)
        self.assertEqual(np.shape(xy), (5, 200))

    def test_capture_invalid_channel_one(self):
        self.scope.channel_one_map = "BAD"
        with self.assertRaises(ValueError):
            self.scope.capture(channels=1, samples=200, timegap=2)

    def test_capture_timegap_too_small(self):
        with self.assertRaises(ValueError):
            self.scope.capture(channels=1, samples=200, timegap=0.2)

    def test_capture_too_many_channels(self):
        with self.assertRaises(ValueError):
            self.scope.capture(channels=5, samples=200, timegap=2)

    def test_capture_too_many_samples(self):
        with self.assertRaises(ValueError):
            self.scope.capture(channels=4, samples=3000, timegap=2)

    def test_invalidate_buffer(self):
        self.scope._channels["CH1"].samples_in_buffer = 100
        self.scope._channels["CH1"].buffer_idx = 0
        self.scope.channel_one_map = "CH2"
        self.scope.capture(channels=1, samples=200, timegap=2)
        self.assertEqual(self.scope._channels["CH1"].samples_in_buffer, 0)
        self.assertIsNone(self.scope._channels["CH1"].buffer_idx)

    def test_configure_trigger(self):
        self.scope.configure_trigger(channel="CH3", voltage=1.5)
        self.assertTrue(self.scope.trigger_enabled)
        self.mock_device.send_byte.assert_any_call(CP.CONFIGURE_TRIGGER)

    def test_configure_trigger_on_unmapped(self):
        with self.assertRaises(TypeError):
            self.scope.configure_trigger(channel="AN8", voltage=1.5)

    def test_configure_trigger_on_remapped_ch1(self):
        self.scope.channel_one_map = "CAP"
        with self.assertRaises(TypeError):
            self.scope.configure_trigger(channel="CH1", voltage=1.5)

    def test_trigger_enabled(self):
        self.scope.trigger_enabled = True
        self.mock_device.send_byte.assert_any_call(CP.CONFIGURE_TRIGGER)

    def test_select_range(self):
        self.scope.select_range("CH1", 1.5)
        self.mock_device.send_byte.assert_called()
        self.assertEqual(self.scope._channels["CH1"].gain, 10)

    def test_select_range_invalid(self):
        with self.assertRaises(ValueError):
            self.scope.select_range("CH1", 15)
