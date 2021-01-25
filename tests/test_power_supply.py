"""Tests for PSL.power_supply.

When running integration tests, connect:
    PV1 -> CH1
    PV2 -> CH2
    PV3 -> VOL
    PCS -> 100R -> GND
    PCS -> CH3
"""
import pytest
import numpy as np

from pslab.serial_handler import SerialHandler
from pslab.instrument.multimeter import Multimeter
from pslab.instrument.power_supply import PowerSupply

RELTOL = 0.05
ABSTOL = 0.05


@pytest.fixture
def power(handler: SerialHandler) -> PowerSupply:
    handler._logging = True
    return PowerSupply(handler)


@pytest.fixture
def multi(handler: SerialHandler) -> Multimeter:
    handler._logging = True
    return Multimeter(handler)


def test_set_voltage_pv1(power: PowerSupply, multi: Multimeter):
    voltages = np.arange(-5, 5, 0.1)
    measured = np.zeros(len(voltages))

    for i, v in enumerate(voltages):
        power.pv1 = v
        measured[i] = multi.measure_voltage("CH1")

    assert measured == pytest.approx(voltages, rel=RELTOL * 2, abs=ABSTOL * 2)


def test_set_voltage_pv2(power: PowerSupply, multi: Multimeter):
    voltages = np.arange(-3.3, 3.3, 0.1)
    measured = np.zeros(len(voltages))

    for i, v in enumerate(voltages):
        power.pv2 = v
        measured[i] = multi.measure_voltage("CH2")

    assert measured == pytest.approx(voltages, rel=RELTOL * 2, abs=ABSTOL * 2)


def test_set_voltage_pv3(power: PowerSupply, multi: Multimeter):
    voltages = np.arange(0, 3.3, 0.1)
    measured = np.zeros(len(voltages))

    for i, v in enumerate(voltages):
        power.pv3 = v
        measured[i] = multi.measure_voltage("VOL")

    assert measured == pytest.approx(voltages, rel=RELTOL * 2, abs=ABSTOL * 2)


def test_set_current(power: PowerSupply, multi: Multimeter):
    currents = np.arange(0, 3e-3, 1e-4)
    measured = np.zeros(len(currents))

    for i, c in enumerate(currents):
        power.pcs = c
        measured[i] = multi.measure_voltage("CH3")

    resistor = 100
    assert measured == pytest.approx(currents * resistor, rel=RELTOL, abs=ABSTOL)
