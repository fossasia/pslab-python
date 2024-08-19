"""Tests for pslab.waveform_generator.

Before running the tests, connect:
    SQ1 -> LA1
    SQ2 -> LA2
    SQ3 -> LA3
    SQ4 -> LA4
    SI1 -> CH1
    SI2 -> CH2
"""

import time

import numpy as np
import pytest
from scipy.optimize import curve_fit
from _pytest.logging import LogCaptureFixture

from pslab.instrument.logic_analyzer import LogicAnalyzer
from pslab.instrument.oscilloscope import Oscilloscope
from pslab.instrument.waveform_generator import PWMGenerator, WaveformGenerator
from pslab.serial_handler import SerialHandler


MICROSECONDS = 1e-6
RELTOL = 0.05
GOOD_FIT = 0.99


def r_squared(y: np.ndarray, y_fit: np.ndarray) -> float:
    """Calculate the coefficient of determination."""
    ss_res = np.sum((y - y_fit) ** 2)  # Residual sum of squares.
    ss_tot = np.sum((y - y.mean()) ** 2)  # Total sum of squares.
    return 1 - (ss_res / ss_tot)


@pytest.fixture
def pwm(handler: SerialHandler) -> PWMGenerator:
    return PWMGenerator(handler)


@pytest.fixture
def wave(handler: SerialHandler) -> WaveformGenerator:
    return WaveformGenerator(handler)


@pytest.fixture
def la(handler: SerialHandler) -> LogicAnalyzer:
    return LogicAnalyzer(handler)


@pytest.fixture
def scope(handler: SerialHandler) -> Oscilloscope:
    return Oscilloscope(handler)


def test_sine_wave(wave: WaveformGenerator, scope: Oscilloscope):
    frequency = 500
    wave.load_function("SI1", "sine")
    wave.generate("SI1", frequency)
    time.sleep(0.1)
    x, y = scope.capture(1, 10000, 1, trigger=0)

    def expected_f(x, amplitude, frequency, phase):
        return amplitude * np.sin(2 * np.pi * frequency * x + phase)

    amplitude = 3.3
    guess = [amplitude, frequency, 0]
    [amplitude_est, frequency_est, phase_est], _ = curve_fit(
        expected_f, x * MICROSECONDS, y, guess
    )

    assert amplitude_est == pytest.approx(amplitude, rel=RELTOL)
    assert frequency_est == pytest.approx(frequency, rel=RELTOL)

    coeff_of_det = r_squared(
        y, expected_f(x * MICROSECONDS, amplitude_est, frequency_est, phase_est)
    )

    assert coeff_of_det >= GOOD_FIT


def test_triangle_wave(wave: WaveformGenerator, scope: Oscilloscope):
    frequency = 2000
    wave.load_function("SI1", "tria")
    wave.generate("SI1", frequency)
    time.sleep(0.1)
    x, y = scope.capture(1, 10000, 1, trigger=0)

    def expected_f(x, amplitude, frequency, phase):
        return (
            2 * amplitude / np.pi * np.arcsin(np.sin(2 * np.pi * frequency * x + phase))
        )

    amplitude = 3.3
    guess = [amplitude, frequency, 0]
    [amplitude_est, frequency_est, phase_est], _ = curve_fit(
        expected_f, x * MICROSECONDS, y, guess
    )

    assert amplitude_est == pytest.approx(amplitude, rel=RELTOL)
    assert frequency_est == pytest.approx(frequency, rel=RELTOL)

    coeff_of_det = r_squared(
        y, expected_f(x * MICROSECONDS, amplitude_est, frequency_est, phase_est)
    )

    assert coeff_of_det >= GOOD_FIT


def test_superposition(wave: WaveformGenerator, scope: Oscilloscope):
    frequency = 1000
    amplitude1 = 2
    amplitude2 = 1

    def super_sine(x):
        return amplitude1 * np.sin(x) + amplitude2 * np.sin(5 * x)

    wave.load_function("SI1", super_sine, [0, 2 * np.pi])
    wave.generate("SI1", frequency)
    time.sleep(0.1)
    x, y = scope.capture(1, 10000, 1, trigger=0)

    def expected_f(x, amplitude1, amplitude2, frequency, phase):
        return amplitude1 * np.sin(
            2 * np.pi * frequency * x + phase
        ) + amplitude2 * np.sin(5 * (2 * np.pi * frequency * x + phase))

    amplitude1 = 2
    amplitude2 = 1
    guess = [amplitude1, amplitude2, frequency, 0]
    [amplitude1_est, amplitude2_est, frequency_est, phase_est], _ = curve_fit(
        expected_f, x * MICROSECONDS, y, guess
    )

    assert amplitude1_est == pytest.approx(amplitude1, rel=RELTOL)
    assert amplitude2_est == pytest.approx(amplitude2, rel=RELTOL)
    assert frequency_est == pytest.approx(frequency, rel=RELTOL)

    coeff_of_det = r_squared(
        y,
        expected_f(
            x * MICROSECONDS, amplitude1_est, amplitude2_est, frequency_est, phase_est
        ),
    )

    assert coeff_of_det >= GOOD_FIT


def test_sine_phase(wave: WaveformGenerator, scope: Oscilloscope):
    frequency = 500
    phase = 90
    wave.load_function("SI1", "sine")
    wave.load_function("SI2", "sine")
    wave.generate(["SI1", "SI2"], frequency, phase)
    time.sleep(0.1)
    x, y1, y2 = scope.capture(2, 5000, 2, trigger=0)

    def expected_f(x, amplitude, frequency, phase):
        return amplitude * np.sin(2 * np.pi * frequency * x + phase)

    guess1 = [3.3, frequency, 0]
    [_, _, phase1_est], _ = curve_fit(expected_f, x * MICROSECONDS, y1, guess1)
    guess2 = [3.3, frequency, phase * np.pi / 180]
    [_, _, phase2_est], _ = curve_fit(expected_f, x * MICROSECONDS, y2, guess2)

    assert phase2_est - phase1_est == pytest.approx(phase * np.pi / 180, rel=RELTOL)


def test_low_frequency_warning(caplog: LogCaptureFixture, wave: WaveformGenerator):
    wave.generate("SI1", 1)
    assert "AC coupling" in caplog.text


def test_low_frequency_error(wave: WaveformGenerator):
    with pytest.raises(ValueError):
        wave.generate("SI1", 0.05)


def test_high_frequency_warning(caplog: LogCaptureFixture, wave: WaveformGenerator):
    wave.generate("SI1", 1e4)
    assert "Frequencies above"


def test_dimension_mismatch(wave: WaveformGenerator):
    with pytest.raises(ValueError):
        wave.generate("SI2", [500, 1000])


def test_pwm(pwm: PWMGenerator, la: LogicAnalyzer):
    frequency = 5e4
    duty_cycle = 0.4
    pwm.generate("SQ1", frequency, duty_cycle)
    time.sleep(0.1)

    assert la.measure_frequency("LA1") == pytest.approx(frequency, rel=RELTOL)
    assert la.measure_duty_cycle("LA1")[1] == pytest.approx(duty_cycle, rel=RELTOL)


def test_pwm_phase(pwm: PWMGenerator, la: LogicAnalyzer):
    frequency = 1e4
    duty_cycle = 0.5
    phase = 0.25
    pwm.generate(["SQ1", "SQ2"], frequency, duty_cycle, phase)
    time.sleep(0.1)
    interval = la.measure_interval(["LA1", "LA2"], ["rising", "rising"])

    if interval < 0:
        interval += frequency**-1 / MICROSECONDS

    assert interval * MICROSECONDS == pytest.approx(frequency**-1 * phase, rel=RELTOL)


def test_set_state(pwm: PWMGenerator, la: LogicAnalyzer):
    states = [True, False, True, True]
    pwm.set_state(*states)
    time.sleep(0.1)
    assert list(la.get_states().values()) == states


def test_unchanged_state(pwm: PWMGenerator, la: LogicAnalyzer):
    frequency = 2.5e3
    duty_cycle = 0.9
    pwm.generate(["SQ1", "SQ4"], frequency, duty_cycle)
    states = [None, True, False, None]
    pwm.set_state(*states)
    time.sleep(0.1)

    assert list(la.get_states().values())[1:3] == states[1:3]
    assert la.measure_frequency("LA1") == pytest.approx(frequency, rel=RELTOL)
    assert la.measure_frequency("LA4") == pytest.approx(frequency, rel=RELTOL)
    assert la.measure_duty_cycle("LA1")[1] == pytest.approx(duty_cycle, rel=RELTOL)
    assert la.measure_duty_cycle("LA4")[1] == pytest.approx(duty_cycle, rel=RELTOL)


def test_map_reference_clock(pwm: PWMGenerator, la: LogicAnalyzer):
    prescaler = 5
    pwm.map_reference_clock(["SQ3"], prescaler)
    assert la.measure_frequency("LA3") == pytest.approx(
        128e6 / (1 << prescaler), rel=RELTOL
    )


def test_pwm_high_frequency_error(pwm: PWMGenerator):
    with pytest.raises(ValueError):
        pwm.generate("SQ1", 2e7, 0.5)


def test_pwm_get_frequency(pwm: PWMGenerator):
    frequency = 1500
    pwm.generate("SQ2", frequency, 0.1)
    assert pwm.frequency == pytest.approx(frequency, rel=RELTOL)


def test_pwm_set_negative_frequency(pwm: PWMGenerator):
    with pytest.raises(ValueError):
        pwm.generate("SQ1", -1, 0.5)
