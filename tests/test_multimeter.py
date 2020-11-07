"""Tests for PSL.multimeter.

When integration testing, connect:
    PV1 -> 10K resistor -> VOL
    RES -> 10K resistor -> GND
    CAP -> 1 nF capacitor -> GND
"""

import pytest

from PSL.multimeter import Multimeter
from PSL.packet_handler import Handler, MockHandler
from PSL.sciencelab import ScienceLab

RELTOL = 0.05


@pytest.fixture
def multi(handler: Handler) -> Multimeter:
    handler._logging = True
    return Multimeter(handler)


@pytest.fixture
def source(handler: Handler):
    if not isinstance(handler, MockHandler):
        psl = ScienceLab()
        psl.set_pv1(2.2)


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
