"""Tests for pslab.bus.i2c.

The PSLab's logic analyzer is used to verify the function of the I2C bus. Before running
the tests, connect:
    SCL->LA1
    SDA->LA2
"""

import pytest

from pslab.bus.i2c import I2CMaster, I2CSlave
from pslab.instrument.logic_analyzer import LogicAnalyzer
from pslab.serial_handler import SerialHandler

ADDRESS = 0x52  # Not a real device.
REGISTER_ADDRESS = 0x06
WRITE_DATA = 0x0
SCL = "LA1"
SDA = "LA2"
MICROSECONDS = 1e-6
RELTOL = 0.05
# Number of expected logic level changes.
SCL_START = 1
SCL_RESTART = 2
SCL_READ = 18
SCL_WRITE = 18
SCL_STOP = 1
SDA_START = 1
SDA_DEVICE_ADDRESS = 7
SDA_REGISTER_ADDRESS = 4
SDA_RESTART = 1
SDA_READ = 0
SDA_NACK = 0
SDA_ACK = 2
SDA_WRITE = 2


@pytest.fixture
def master(handler: SerialHandler) -> I2CMaster:
    return I2CMaster(device=handler)


@pytest.fixture
def slave(handler: SerialHandler) -> I2CSlave:
    return I2CSlave(ADDRESS, device=handler)


@pytest.fixture
def la(handler: SerialHandler) -> LogicAnalyzer:
    return LogicAnalyzer(handler)


def test_configure(la: LogicAnalyzer, master: I2CMaster, slave: I2CSlave):
    frequency = 1.25e5
    master.configure(frequency)
    la.capture(1, block=False)
    slave._start(ADDRESS, 1)
    slave._stop()
    la.stop()
    (scl,) = la.fetch_data()
    write_start = scl[1]  # First event is start bit.
    write_stop = scl[-2]  # Final event is stop bit.
    start_to_stop = 8.5  # 9 periods, but initial and final states are the same.
    period = (write_stop - write_start) / start_to_stop
    assert (period * MICROSECONDS) ** -1 == pytest.approx(frequency, rel=RELTOL)


def test_scan(master: I2CMaster):
    mcp4728_address = 0x60
    assert mcp4728_address in master.scan()


def test_status(master: I2CMaster):
    master.configure(1.25e5)
    # No status bits should be set on a newly configured bus.
    assert not master._status


def test_start_slave(la: LogicAnalyzer, slave: I2CSlave):
    la.capture(2, block=False)
    slave._start(ADDRESS, 1)
    la.stop()
    slave._stop()
    init = la.get_initial_states()
    scl, sda = la.fetch_data()

    assert all([init[c] for c in [SCL, SDA]])  # Both start HIGH.
    assert sda[0] < scl[0]  # Start bit: SDA 1->0 while SCL is 1.


def test_stop_slave(la: LogicAnalyzer, slave: I2CSlave):
    slave._start(ADDRESS, 1)
    la.capture(2, block=False)
    slave._stop()
    la.stop()
    init = la.get_initial_states()
    scl, sda = la.fetch_data()

    assert not init[SCL] and init[SDA]  # SDA starts HIGH, SCL starts LOW.
    assert sda[0] < scl[0] < sda[1]  # Stop bit: SDA 0->1 while SCL is 1.


def test_ping_slave(slave: I2CSlave):
    assert not slave.ping()


def test_read(la: LogicAnalyzer, slave: I2CSlave):
    la.capture(2, block=False)
    slave.read(1, REGISTER_ADDRESS)
    la.stop()
    scl, sda = la.fetch_data()

    assert len(scl) == (
        SCL_START + SCL_WRITE * 2 + SCL_RESTART + SCL_WRITE + SCL_READ + SCL_STOP
    )
    assert len(sda) == (
        SDA_START
        + (SDA_DEVICE_ADDRESS + SDA_NACK)
        + (SDA_REGISTER_ADDRESS + SDA_NACK)
        + SDA_RESTART
        + (SDA_DEVICE_ADDRESS + SDA_NACK)
        + (SDA_READ + SDA_ACK)
    )


def test_read_byte(la: LogicAnalyzer, slave: I2CSlave):
    la.capture(2, block=False)
    slave.read_byte(REGISTER_ADDRESS)
    la.stop()
    scl, sda = la.fetch_data()

    assert len(scl) == (
        SCL_START + SCL_WRITE * 2 + SCL_RESTART + SCL_WRITE + SCL_READ + SCL_STOP
    )
    assert len(sda) == (
        SDA_START
        + (SDA_DEVICE_ADDRESS + SDA_NACK)
        + (SDA_REGISTER_ADDRESS + SDA_NACK)
        + SDA_RESTART
        + (SDA_DEVICE_ADDRESS + SDA_NACK)
        + (SDA_READ + SDA_ACK)
    )


def test_read_int(la: LogicAnalyzer, slave: I2CSlave):
    la.capture(2, block=False)
    slave.read_int(REGISTER_ADDRESS)
    la.stop()
    scl, sda = la.fetch_data()

    assert len(scl) == (
        SCL_START + SCL_WRITE * 2 + SCL_RESTART + SCL_WRITE + SCL_READ * 2 + SCL_STOP
    )
    assert len(sda) == (
        SDA_START
        + (SDA_DEVICE_ADDRESS + SDA_NACK)
        + (SDA_REGISTER_ADDRESS + SDA_NACK)
        + SDA_RESTART
        + (SDA_DEVICE_ADDRESS + SDA_NACK)
        + (SDA_READ + SDA_ACK) * 2
    )


def test_read_long(la: LogicAnalyzer, slave: I2CSlave):
    la.capture(2, block=False)
    slave.read_long(REGISTER_ADDRESS)
    la.stop()
    scl, sda = la.fetch_data()

    assert len(scl) == (
        SCL_START + SCL_WRITE * 2 + SCL_RESTART + SCL_WRITE + SCL_READ * 4 + SCL_STOP
    )
    assert len(sda) == (
        SDA_START
        + (SDA_DEVICE_ADDRESS + SDA_NACK)
        + (SDA_REGISTER_ADDRESS + SDA_NACK)
        + SDA_RESTART
        + (SDA_DEVICE_ADDRESS + SDA_NACK)
        + (SDA_READ + SDA_ACK) * 4
    )


def test_write(la: LogicAnalyzer, slave: I2CSlave):
    la.capture(2, block=False)
    slave.write(bytearray(b"\x00"), REGISTER_ADDRESS)
    la.stop()
    scl, sda = la.fetch_data()

    assert len(scl) == (SCL_START + SCL_WRITE * 3 + SCL_STOP)
    assert len(sda) == (
        SDA_START + SDA_DEVICE_ADDRESS + SDA_REGISTER_ADDRESS + SDA_WRITE + SDA_ACK
    )


def test_write_byte(la: LogicAnalyzer, slave: I2CSlave):
    la.capture(2, block=False)
    slave.write_byte(WRITE_DATA, REGISTER_ADDRESS)
    la.stop()
    scl, sda = la.fetch_data()

    assert len(scl) == (SCL_START + SCL_WRITE * 3 + SCL_STOP)
    assert len(sda) == (
        SDA_START + SDA_DEVICE_ADDRESS + SDA_REGISTER_ADDRESS + SDA_WRITE + SDA_ACK
    )


def test_write_int(la: LogicAnalyzer, slave: I2CSlave):
    la.capture(2, block=False)
    slave.write_int(WRITE_DATA, REGISTER_ADDRESS)
    la.stop()
    scl, sda = la.fetch_data()

    assert len(scl) == (SCL_START + SCL_WRITE * 4 + SCL_STOP)
    assert len(sda) == (
        SDA_START + SDA_DEVICE_ADDRESS + SDA_REGISTER_ADDRESS + SDA_WRITE * 2 + SDA_ACK
    )


def test_write_long(la: LogicAnalyzer, slave: I2CSlave):
    la.capture(2, block=False)
    slave.write_long(WRITE_DATA, REGISTER_ADDRESS)
    la.stop()
    scl, sda = la.fetch_data()

    assert len(scl) == (SCL_START + SCL_WRITE * 6 + SCL_STOP)
    assert len(sda) == (
        SDA_START + SDA_DEVICE_ADDRESS + SDA_REGISTER_ADDRESS + SDA_WRITE * 4 + SDA_ACK
    )
