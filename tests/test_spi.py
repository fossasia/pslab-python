"""Tests for pslab.bus.spi.

The PSLab's logic analyzer and PWM output are used to verify the function of the SPI
bus. Before running the tests, connect:
    SCK    -> LA1
    SDO    -> LA2
    SDI    -> SQ1 and LA4
    SPI.CS -> LA3
"""

import pytest
import re
from numpy import ndarray

from pslab.bus.spi import SPIMaster, SPISlave
from pslab.instrument.logic_analyzer import LogicAnalyzer
from pslab.instrument.waveform_generator import PWMGenerator
from pslab.serial_handler import SerialHandler

SPI_SUPPORTED_DEVICES = [
    # "PSLab vMOCK",  # Uncomment after adding recording json files.
    "PSLab V6\n",
]

WRITE_DATA8 = 0b10100101
WRITE_DATA16 = 0xAA55
SCK = "LA1"
SDO = "LA2"
SDI = ["LA4", "SQ1"]
CS = "LA3"
SPIMaster._primary_prescaler = PPRE = 0
SPIMaster._secondary_prescaler = SPRE = 0
PWM_FERQUENCY = SPIMaster._frequency * 2 / 3
MICROSECONDS = 1e-6
RELTOL = 0.05
# Number of expected logic level changes.
CS_START = 1
CS_STOP = 1
SCK_WRITE8 = 16
SCK_WRITE16 = 2 * 16
SDO_WRITE_DATA8 = 8
SDO_WRITE_DATA16 = 16


@pytest.fixture
def master(handler: SerialHandler) -> SPIMaster:
    if handler.version not in SPI_SUPPORTED_DEVICES:
        pytest.skip("SPI not supported by this device.")
    spi_master = SPIMaster(device=handler)
    yield spi_master
    spi_master.set_parameters()


@pytest.fixture
def slave(handler: SerialHandler) -> SPISlave:
    if handler.version not in SPI_SUPPORTED_DEVICES:
        pytest.skip("SPI not supported by this device.")
    return SPISlave(device=handler)


@pytest.fixture
def la(handler: SerialHandler) -> LogicAnalyzer:
    pwm = PWMGenerator(handler)
    pwm.generate(SDI[1], PWM_FERQUENCY, 0.5)
    return LogicAnalyzer(handler)


def verify_value(
    value: int,
    sck_timestamps: ndarray,
    sdi_initstate: int,
    sdi_timestamps: ndarray,
    smp: int = 0,
):
    sck_ts = sck_timestamps[smp::2]
    pwm_half_period = ((1 / PWM_FERQUENCY) * 1e6) / 2  # microsecond

    pattern = ""
    for t in sck_ts:
        d, m = divmod(t - sdi_timestamps[0], pwm_half_period)
        if m == pytest.approx(0, abs=0.1) or m == pytest.approx(
            pwm_half_period, abs=0.1
        ):
            pattern += "[0,1]"
        elif d % 2:
            pattern += "1" if sdi_initstate else "0"
        else:
            pattern += "0" if sdi_initstate else "1"

    pattern = re.compile(pattern)
    bits = len(sck_ts)
    value = bin(value)[2:].zfill(bits)

    return bool(pattern.match(value))


def test_set_parameter_frequency(la: LogicAnalyzer, master: SPIMaster, slave: SPISlave):
    # frequency 166666.66666666666
    ppre = 0
    spre = 2
    master.set_parameters(primary_prescaler=ppre, secondary_prescaler=spre)
    la.capture(1, block=False)
    slave.write8(0)
    la.stop()
    (sck,) = la.fetch_data()
    write_start = sck[0]
    write_stop = sck[-2]  # Output data on rising edge only (in mode 0)
    start_to_stop = 7
    period = (write_stop - write_start) / start_to_stop
    assert (period * MICROSECONDS) ** -1 == pytest.approx(master._frequency, rel=RELTOL)


@pytest.mark.parametrize("ckp", [0, 1])
def test_set_parameter_clock_polarity(
    la: LogicAnalyzer, master: SPIMaster, slave: SPISlave, ckp: int
):
    master.set_parameters(CKP=ckp)
    assert la.get_states()[SCK] == bool(ckp)


@pytest.mark.parametrize("cke", [0, 1])
def test_set_parameter_clock_edge(
    la: LogicAnalyzer, master: SPIMaster, slave: SPISlave, cke: int
):
    master.set_parameters(CKE=cke)
    la.capture(2, block=False)
    slave.write8(WRITE_DATA8)
    la.stop()
    (sck, sdo) = la.fetch_data()
    idle_to_active = sck[0]
    first_bit = sdo[0]
    # Serial output data changes on transition
    # {0: from Idle clock state to active state (first event before data change),
    #  1: from active clock state to Idle state (data change before first event)}.
    assert first_bit < idle_to_active == bool(cke)


@pytest.mark.parametrize("smp", [0, 1])
def test_set_parameter_smp(
    la: LogicAnalyzer, master: SPIMaster, slave: SPISlave, pwm: PWMGenerator, smp: int
):
    master.set_parameters(SMP=smp)
    la.capture([SCK, SDI[0]], block=False)
    value = slave.read8()
    la.stop()
    (sck, sdi) = la.fetch_data()
    sdi_initstate = la.get_initial_states()[SDI[0]]

    assert verify_value(value, sck, sdi_initstate, sdi, smp)


def test_chip_select(la: LogicAnalyzer, slave: SPISlave):
    assert la.get_states()[CS]

    la.capture(CS, block=False)
    slave._start()
    slave._stop()
    la.stop()
    (cs,) = la.fetch_data()
    assert len(cs) == (CS_START + CS_STOP)


def test_write8(la: LogicAnalyzer, slave: SPISlave):
    la.capture(3, block=False)
    slave.write8(WRITE_DATA8)
    la.stop()
    (sck, sdo, cs) = la.fetch_data()

    assert len(cs) == (CS_START + CS_STOP)
    assert len(sck) == SCK_WRITE8
    assert len(sdo) == SDO_WRITE_DATA8


def test_write16(la: LogicAnalyzer, slave: SPISlave):
    la.capture(3, block=False)
    slave.write16(WRITE_DATA16)
    la.stop()
    (sck, sdo, cs) = la.fetch_data()

    assert len(cs) == (CS_START + CS_STOP)
    assert len(sck) == SCK_WRITE16
    assert len(sdo) == SDO_WRITE_DATA16


def test_read8(la: LogicAnalyzer, slave: SPISlave):
    la.capture(4, block=False)
    value = slave.read8()
    la.stop()
    (sck, sdo, cs, sdi) = la.fetch_data()
    sdi_initstate = la.get_initial_states()[SDI[0]]

    assert len(cs) == (CS_START + CS_STOP)
    assert len(sck) == SCK_WRITE8
    assert len(sdo) == 0
    assert verify_value(value, sck, sdi_initstate, sdi)


def test_read16(la: LogicAnalyzer, slave: SPISlave):
    la.capture(4, block=False)
    value = slave.read16()
    la.stop()
    (sck, sdo, cs, sdi) = la.fetch_data()
    sdi_initstate = la.get_initial_states()[SDI[0]]

    assert len(cs) == (CS_START + CS_STOP)
    assert len(sck) == SCK_WRITE16
    assert len(sdo) == 0
    assert verify_value(value, sck, sdi_initstate, sdi)


def test_transfer8(la: LogicAnalyzer, slave: SPISlave):
    la.capture(4, block=False)
    value = slave.transfer8(WRITE_DATA8)
    la.stop()
    (sck, sdo, cs, sdi) = la.fetch_data()
    sdi_initstate = la.get_initial_states()[SDI[0]]

    assert len(cs) == (CS_START + CS_STOP)
    assert len(sck) == SCK_WRITE8
    assert len(sdo) == SDO_WRITE_DATA8
    assert verify_value(value, sck, sdi_initstate, sdi)


def test_transfer16(la: LogicAnalyzer, slave: SPISlave):
    la.capture(4, block=False)
    value = slave.transfer16(WRITE_DATA16)
    la.stop()
    (sck, sdo, cs, sdi) = la.fetch_data()
    sdi_initstate = la.get_initial_states()[SDI[0]]

    assert len(cs) == (CS_START + CS_STOP)
    assert len(sck) == SCK_WRITE16
    assert len(sdo) == SDO_WRITE_DATA16
    assert verify_value(value, sck, sdi_initstate, sdi)


def test_write8_bulk(la: LogicAnalyzer, slave: SPISlave):
    la.capture(3, block=False)
    slave.write8_bulk([WRITE_DATA8, WRITE_DATA8])
    la.stop()
    (sck, sdo, cs) = la.fetch_data()

    assert len(cs) == (CS_START + CS_STOP)
    assert len(sck) == SCK_WRITE8 + SCK_WRITE8
    assert len(sdo) == SDO_WRITE_DATA8 + SDO_WRITE_DATA16


def test_write16_bulk(la: LogicAnalyzer, slave: SPISlave):
    la.capture(3, block=False)
    slave.write16_bulk([WRITE_DATA16, WRITE_DATA16])
    la.stop()
    (sck, sdo, cs) = la.fetch_data()

    assert len(cs) == (CS_START + CS_STOP)
    assert len(sck) == SCK_WRITE16 + SCK_WRITE16
    assert len(sdo) == SDO_WRITE_DATA16 + SDO_WRITE_DATA16


def test_read8_bulk(la: LogicAnalyzer, slave: SPISlave):
    la.capture(4, block=False)
    value = slave.read8_bulk(2)
    la.stop()
    (sck, sdo, cs, sdi) = la.fetch_data()
    sdi_initstate = la.get_initial_states()[SDI[0]]

    assert len(cs) == (CS_START + CS_STOP)
    assert len(sck) == SCK_WRITE8 + SCK_WRITE8
    assert len(sdo) == 0
    assert verify_value(value[0], sck, sdi_initstate, sdi[:16])
    assert verify_value(value[1], sck, sdi_initstate, sdi[16:])


def test_read16_bulk(la: LogicAnalyzer, slave: SPISlave):
    la.capture(4, block=False)
    value = slave.read16_bulk(2)
    la.stop()
    (sck, sdo, cs, sdi) = la.fetch_data()
    sdi_initstate = la.get_initial_states()[SDI[0]]

    assert len(cs) == (CS_START + CS_STOP)
    assert len(sck) == SCK_WRITE16 + SCK_WRITE16
    assert len(sdo) == 0
    assert verify_value(value[0], sck, sdi_initstate, sdi[:32])
    assert verify_value(value[1], sck, sdi_initstate, sdi[32:])


def test_transfer8_bulk(la: LogicAnalyzer, slave: SPISlave):
    la.capture(4, block=False)
    value = slave.transfer8_bulk([WRITE_DATA8, WRITE_DATA8])
    la.stop()
    (sck, sdo, cs, sdi) = la.fetch_data()
    sdi_initstate = la.get_initial_states()[SDI[0]]

    assert len(cs) == (CS_START + CS_STOP)
    assert len(sck) == SCK_WRITE8 + SCK_WRITE8
    assert len(sdo) == 0
    assert verify_value(value[0], sck, sdi_initstate, sdi[:16])
    assert verify_value(value[1], sck, sdi_initstate, sdi[16:])


def test_transfer16_bulk(la: LogicAnalyzer, slave: SPISlave):
    la.capture(4, block=False)
    value = slave.transfer16_bulk([WRITE_DATA16, WRITE_DATA16])
    la.stop()
    (sck, sdo, cs, sdi) = la.fetch_data()
    sdi_initstate = la.get_initial_states()[SDI[0]]

    assert len(cs) == (CS_START + CS_STOP)
    assert len(sck) == SCK_WRITE16 + SCK_WRITE16
    assert len(sdo) == 0
    assert verify_value(value[0], sck, sdi_initstate, sdi[:32])
    assert verify_value(value[1], sck, sdi_initstate, sdi[32:])
