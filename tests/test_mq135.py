import pytest

from pslab.external.gas_sensor import MQ135

R_LOAD = 22e3
R0 = 50e3
VCC = 5
VOUT = 2
A, B, C, D = *MQ135._TEMPERATURE_CORRECTION, MQ135._HUMIDITY_CORRECTION
E, F = MQ135._PARAMS["CO2"]
STANDARD_CORRECTION = A * 20 ** 2 + B * 20 + C + D * (0.65 - 0.65)
EXPECTED_SENSOR_RESISTANCE = (VCC / VOUT - 1) * R_LOAD / STANDARD_CORRECTION
CALIBRATION_CONCENTRATION = E * (EXPECTED_SENSOR_RESISTANCE / R0) ** F


@pytest.fixture
def mq135(mocker):
    mock = mocker.patch("pslab.external.gas_sensor.Multimeter")
    mock().measure_voltage.return_value = VOUT
    return MQ135("CO2", R_LOAD)


def test_correction(mq135):
    assert mq135._correction == STANDARD_CORRECTION


def test_sensor_resistance(mq135):
    assert mq135._sensor_resistance == EXPECTED_SENSOR_RESISTANCE


def test_measure_concentration(mq135):
    mq135.r0 = R0
    assert mq135.measure_concentration() == E * (EXPECTED_SENSOR_RESISTANCE / R0) ** F


def test_measure_concentration_r0_unset(mq135):
    with pytest.raises(TypeError):
        mq135.measure_concentration()


def test_measure_r0(mq135):
    assert mq135.measure_r0(CALIBRATION_CONCENTRATION) == pytest.approx(R0)
