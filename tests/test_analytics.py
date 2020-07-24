import unittest

from PSL import analyticsClass


class TestAnalytics(unittest.TestCase):
    def test_frexp10(self):
        input_value = 43.0982
        expected_result = (4.30982, 1)
        self.assertAlmostEqual(analyticsClass.frexp10(input_value), expected_result)

    def test_apply_si_prefix_rounding(self):
        input_value = {
            "value": 7545.230053,
            "unit": "J",
        }
        expected_result = "7.55 kJ"
        self.assertEqual(analyticsClass.apply_si_prefix(**input_value), expected_result)

    def test_apply_si_prefix_high_precision(self):
        input_value = {
            "value": -0.000002000008,
            "unit": "A",
            "precision": 6,
        }
        expected_result = "-2.000008 µA"
        self.assertEqual(analyticsClass.apply_si_prefix(**input_value), expected_result)

    def test_apply_si_prefix_low_precision(self):
        input_value = {
            "value": -1,
            "unit": "V",
            "precision": 0,
        }
        expected_result = "-1 V"
        self.assertEqual(analyticsClass.apply_si_prefix(**input_value), expected_result)

    def test_apply_si_prefix_too_big(self):
        input_value = {
            "value": 1e27,
            "unit": "V",
        }
        self.assertRaises(ValueError, analyticsClass.apply_si_prefix, **input_value)

    def test_apply_si_prefix_too_small(self):
        input_value = {
            "value": 1e-25,
            "unit": "V",
        }
        self.assertRaises(ValueError, analyticsClass.apply_si_prefix, **input_value)
