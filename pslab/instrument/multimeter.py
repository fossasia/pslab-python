"""The PSLab's multimeter can measure voltage, resistance, and capacitance."""

import time
from typing import Tuple

import numpy as np
from scipy.optimize import curve_fit

import pslab.protocol as CP
from pslab.instrument.analog import GAIN_VALUES, INPUT_RANGES
from pslab.instrument.oscilloscope import Oscilloscope
from pslab.serial_handler import SerialHandler

_MICROSECONDS = 1e-6


class Multimeter(Oscilloscope):
    """Measure voltage, resistance and capacitance.

    Parameters
    ----------
    device : Handler
        Serial interface for communicating with the PSLab device. If not
        provided, a new one will be created.
    """

    _CURRENTS = [5.5e-4, 5.5e-7, 5.5e-6, 5.5e-5]
    _CURRENTS_RANGES = [1, 2, 3, 0]  # Smallest first,
    _RC_RESISTANCE = 1e4
    _CAPACITOR_CHARGED_VOLTAGE = 0.9 * max(INPUT_RANGES["CAP"])
    _CAPACITOR_DISCHARGED_VOLTAGE = 0.01 * max(INPUT_RANGES["CAP"])

    def __init__(self, device: SerialHandler = None):
        self._stray_capacitance = 46e-12
        super().__init__(device)

    def measure_resistance(self) -> float:
        """Measure the resistance of a resistor connected between RES and GND.

        Returns
        -------
        resistance : float
            Resistance in ohm.
        """
        voltage = self.measure_voltage("RES")
        resolution = max(INPUT_RANGES["RES"]) / (
            2 ** self._channels["RES"].resolution - 1
        )

        if voltage >= max(INPUT_RANGES["RES"]) - resolution:
            return np.inf

        pull_up_resistance = 5.1e3
        current = (INPUT_RANGES["RES"][1] - voltage) / pull_up_resistance
        return voltage / current

    def measure_voltage(self, channel: str = "VOL") -> float:
        """Measure the voltage on the selected channel.

        Parameters
        ----------
        channel : {"CH1", "CH2", "CH3", "MIC", "CAP", "RES", "VOL"}, optional
            The name of the analog input on which to measure the voltage. The
            default channel is VOL.

        Returns
        -------
        voltage : float
            Voltage in volts.
        """
        self._voltmeter_autorange(channel)
        return self._measure_voltage(channel)

    def _measure_voltage(self, channel: str) -> float:
        self._channels[channel].resolution = 12
        scale = self._channels[channel].scale
        chosa = self._channels[channel].chosa
        self._device.send_byte(CP.ADC)
        self._device.send_byte(CP.GET_VOLTAGE_SUMMED)
        self._device.send_byte(chosa)
        raw_voltage_sum = self._device.get_int()  # Sum of 16 samples.
        self._device.get_ack()
        raw_voltage_mean = round(raw_voltage_sum / 16)
        voltage = scale(raw_voltage_mean)
        return voltage

    def _voltmeter_autorange(self, channel: str) -> float:
        if channel in ("CH1", "CH2"):
            self._set_gain(channel, 1)  # Reset gain.
            voltage = self._measure_voltage(channel)

            for gain in GAIN_VALUES[::-1]:
                rng = max(INPUT_RANGES[channel]) / gain
                if abs(voltage) < rng:
                    break

            self._set_gain(channel, gain)

            return rng
        else:
            return max(INPUT_RANGES[channel])

    def calibrate_capacitance(self):
        """Calibrate stray capacitance.

        Correctly calibrated stray capacitance is important when measuring
        small capacitors (picofarad range).

        Stray capacitace should be recalibrated if external wiring is connected
        to the CAP pin.
        """
        for charge_time in np.unique(np.int16(np.logspace(2, 3))):
            self._discharge_capacitor()
            voltage, capacitance = self._measure_capacitance(1, 0, charge_time)
            if voltage >= self._CAPACITOR_CHARGED_VOLTAGE:
                break
        self._stray_capacitance += capacitance

    def measure_capacitance(self) -> float:
        """Measure the capacitance of a capacitor connected between CAP and GND.

        Returns
        -------
        capacitance : float
            Capacitance in Farad.
        """
        for current_range in self._CURRENTS_RANGES:
            charge_time = 10
            for _ in range(10):
                if charge_time > 50000:
                    break  # Increase current.
                voltage, capacitance = self._measure_capacitance(
                    current_range, 0, charge_time
                )
                if 0.98 < voltage / self._CAPACITOR_CHARGED_VOLTAGE < 1.02:
                    return capacitance
                charge_time = int(
                    charge_time * self._CAPACITOR_CHARGED_VOLTAGE / voltage
                )

        # Capacitor too big, use alternative method.
        return self._measure_rc_capacitance()

    def _set_cap(self, state, charge_time):
        """Set CAP HIGH or LOW."""
        self._device.send_byte(CP.ADC)
        self._device.send_byte(CP.SET_CAP)
        self._device.send_byte(state)
        self._device.send_int(charge_time)
        self._device.get_ack()

    def _discharge_capacitor(
        self, discharge_time: int = 50000, timeout: float = 1
    ) -> float:
        start_time = time.time()
        voltage = previous_voltage = self.measure_voltage("CAP")

        while voltage > self._CAPACITOR_DISCHARGED_VOLTAGE:
            self._set_cap(0, discharge_time)
            voltage = self.measure_voltage("CAP")

            if abs(previous_voltage - voltage) < self._CAPACITOR_DISCHARGED_VOLTAGE:
                break

            previous_voltage = voltage

            if time.time() - start_time > timeout:
                break

        return voltage

    def _measure_capacitance(
        self, current_range: int, trim: int, charge_time: int
    ) -> Tuple[float, float]:
        self._discharge_capacitor()
        self._channels["CAP"].resolution = 12
        self._device.send_byte(CP.COMMON)
        self._device.send_byte(CP.GET_CAPACITANCE)
        self._device.send_byte(current_range)

        if trim < 0:
            self._device.send_byte(int(31 - abs(trim) / 2) | 32)
        else:
            self._device.send_byte(int(trim / 2))

        self._device.send_int(charge_time)
        time.sleep(charge_time * _MICROSECONDS)
        raw_voltage = self._device.get_int()
        voltage = self._channels["CAP"].scale(raw_voltage)
        self._device.get_ack()
        charge_current = self._CURRENTS[current_range] * (100 + trim) / 100

        if voltage:
            capacitance = (
                charge_current * charge_time * _MICROSECONDS / voltage
                - self._stray_capacitance
            )
        else:
            capacitance = 0

        return voltage, capacitance

    def _measure_rc_capacitance(self) -> float:
        """Measure the capacitance by discharge through a 10K resistor."""
        (x,) = self.capture("CAP", CP.MAX_SAMPLES, 10, block=False)
        x *= _MICROSECONDS
        self._set_cap(1, 50000)  # charge
        self._set_cap(0, 50000)  # discharge
        (y,) = self.fetch_data()

        if y.max() >= self._CAPACITOR_CHARGED_VOLTAGE:
            discharge_start = np.where(y >= self._CAPACITOR_CHARGED_VOLTAGE)[0][-1]
        else:
            discharge_start = np.where(y == y.max())[0][-1]

        x = x[discharge_start:]
        y = y[discharge_start:]

        # CAP floats for a brief period of time (~500 µs) between being set
        # HIGH until it is set LOW. This data is not useful and should be
        # discarded. When CAP is set LOW the voltage declines sharply, which
        # manifests as a negative peak in the time derivative.
        dydx = np.diff(y) / np.diff(x)
        cap_low = np.where(dydx == dydx.min())[0][0]
        x = x[cap_low:]
        y = y[cap_low:]

        # Discard data after the voltage reaches zero (improves fit).
        try:
            v_zero = np.where(y == 0)[0][0]
            x = x[:v_zero]
            y = y[:v_zero]
        except IndexError:
            pass

        # Remove time offset.
        x -= x[0]

        def discharging_capacitor_voltage(
            x: np.ndarray, v_init: float, rc_time_constant: float
        ) -> np.ndarray:
            return v_init * np.exp(-x / rc_time_constant)

        # Solve discharging_capacitor_voltage for rc_time_constant.
        rc_time_constant_guess = (-x[1:] / np.log(y[1:] / y[0])).mean()
        guess = [y[0], rc_time_constant_guess]
        popt, _ = curve_fit(discharging_capacitor_voltage, x, y, guess)
        rc_time_constant = popt[1]
        rc_capacitance = rc_time_constant / self._RC_RESISTANCE
        return rc_capacitance
