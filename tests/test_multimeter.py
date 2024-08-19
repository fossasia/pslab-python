"""Tests for PSL.multimeter.

Before running the tests, connect:
    PV1 -> 10K resistor -> VOL
    RES -> 10K resistor -> GND
    CAP -> 1 nF capacitor -> GND
"""

import pytest

from pslab.instrument.multimeter import Multimeter
from pslab.instrument.power_supply import PowerSupply
from pslab.serial_handler import SerialHandler


RELTOL = 0.05


@pytest.fixture
def multi(handler: SerialHandler) -> Multimeter:
    return Multimeter(handler)


@pytest.fixture
def source(handler: SerialHandler):
    ps = PowerSupply()
    ps.pv1.voltage = 2.2


def test_measure_resistance(multi: Multimeter):
    assert multi.measure_resistance() == pytest.approx(1e4, rel=RELTOL)


def test_measure_voltage(multi: Multimeter, source):
    assert multi.measure_voltage("VOL") == pytest.approx(2.2, rel=RELTOL)


def test_voltmeter_autorange(multi: Multimeter):
    assert multi._voltmeter_autorange("CH1") <= 3.3


def test_calibrate_capacitance(multi: Multimeter):
    multi.calibrate_capacitance()
    # Need bigger tolerance because measurement will be 1 nF + actual stray
    # capacitance (ca 50 pF).
    assert multi._stray_capacitance == pytest.approx(1e-9, rel=3 * RELTOL)


def test_measure_capacitance(multi: Multimeter):
    assert multi.measure_capacitance() == pytest.approx(1e-9, rel=RELTOL)


def test_measure_rc_capacitance(multi: Multimeter):
    assert multi._measure_rc_capacitance() == pytest.approx(1e-9, rel=RELTOL)
