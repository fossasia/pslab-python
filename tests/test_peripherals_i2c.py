from unittest.mock import Mock, call as H_interface
import pytest

from PSL import commands_proto as CP
from PSL.Peripherals import I2CMaster, I2CSlave
from PSL.packet_handler import Handler

ADDRESS = 0X52
REGISTER_ADDRESS = 0x06

class MockHandler(Handler):
    def connect(
        self, port: str = None, baudrate: int = 1000000, timeout: float = 1.0,
    ):
        pass

@pytest.fixture
def handler():
    mock_handler = MockHandler()
    mock_handler.interface = Mock()
    mock_handler.interface.read.return_value=CP.ACKNOWLEDGE
    mock_handler.interface.write.return_value=None
    return mock_handler

@pytest.fixture
def master(handler):
    return I2CMaster(handler)

@pytest.fixture
def slave(handler):
    return I2CSlave(handler, ADDRESS)

class Response:
    def __init__(self, interface, responses, default):
        self.interface = interface # mocked
        self.responses = responses
        self.default = default
    def __call__(self, request):
        if request in self.responses:
            self.interface.read.return_value = self.responses[request]
        else:
            self.interface.read.return_value = self.default


CONFIG = list(map(H_interface.write,[
    CP.I2C_HEADER,
    CP.I2C_CONFIG,
]))

ACK = [H_interface.read(1)]

def test_config_frequency(master):
    MAX_BRGVAL = master.MAX_BRGVAL

    # <= MAX_BRGVAL
    BRGVAL = MAX_BRGVAL - 1
    freq = round(1.0/((BRGVAL+1.0)/64e6+1.0/1e7))
    master.config(freq, verbose=True)
    calls = CONFIG + [H_interface.write(CP.ShortInt.pack(BRGVAL))] + ACK
    assert master.H.interface.method_calls == calls

def test_config_low_frequency(master, capsys):
    MAX_BRGVAL = master.MAX_BRGVAL

    # > MAX_BRGVAL
    BRGVAL = MAX_BRGVAL + 1
    freq = round(1.0/((BRGVAL+1.0)/64e6+1.0/1e7))
    master.config(freq, verbose=True)
    calls = CONFIG + [H_interface.write(CP.ShortInt.pack(MAX_BRGVAL))] + ACK
    assert master.H.interface.method_calls == calls
    captured = capsys.readouterr()
    assert captured.out == f'Frequency too low. Setting to : {1/((MAX_BRGVAL+1.0)/64e6+1.0/1e7)}\n'

def test_scan(master):
    address = CP.Byte.pack(((ADDRESS << 1) | 0) & 0xFF)
    interface = master.H.interface
    success = CP.Byte.pack(1)
    responses = {address : success}

    interface.write.side_effect = Response(interface, responses, CP.ACKNOWLEDGE)
    assert master.scan() == [ADDRESS]


START_READ = list(map(H_interface.write,[
    CP.I2C_HEADER,
    CP.I2C_START,
    CP.Byte.pack(((ADDRESS << 1) | 1) & 0xFF),
]))

START_WRITE = list(map(H_interface.write,[
    CP.I2C_HEADER,
    CP.I2C_START,
    CP.Byte.pack(((ADDRESS << 1) | 0) & 0xFF),
]))

STOP = list(map(H_interface.write,[
    CP.I2C_HEADER,
    CP.I2C_STOP,
]))

SEND = list(map(H_interface.write,[
    CP.I2C_HEADER,
    CP.I2C_SEND,
]))

SEND_BURST = list(map(H_interface.write,[
    CP.I2C_HEADER,
    CP.I2C_SEND_BURST,
]))

RESTART_READ = list(map(H_interface.write,[
    CP.I2C_HEADER,
    CP.I2C_RESTART,
    CP.Byte.pack(((ADDRESS << 1) | 1) & 0xFF),
]))

RESTART_WRITE = list(map(H_interface.write,[
    CP.I2C_HEADER,
    CP.I2C_RESTART,
    CP.Byte.pack(((ADDRESS << 1) | 0) & 0xFF),
]))

READ_MORE = list(map(H_interface.write,[
    CP.I2C_HEADER,
    CP.I2C_READ_MORE,
]))

READ_END = list(map(H_interface.write,[
    CP.I2C_HEADER,
    CP.I2C_READ_END,
]))

READ_BULK = list(map(H_interface.write,[
    CP.I2C_HEADER,
    CP.I2C_READ_BULK,
    CP.Byte.pack(ADDRESS),
    CP.Byte.pack(REGISTER_ADDRESS),
]))

WRITE_BULK = list(map(H_interface.write,[
    CP.I2C_HEADER,
    CP.I2C_WRITE_BULK,
    CP.Byte.pack(ADDRESS),
]))

CAPTURE_START = list(map(H_interface.write,[
    CP.I2C_HEADER,
    CP.I2C_START_SCOPE,
    CP.Byte.pack(ADDRESS),
    CP.Byte.pack(REGISTER_ADDRESS),
]))

def test_send(slave):
    slave.start(0)
    slave.send(0xFF)
    slave.stop()
    calls = START_WRITE + ACK
    calls += SEND + [H_interface.write(CP.Byte.pack(0xFF))] + ACK
    calls += STOP + ACK
    assert slave.H.interface.method_calls == calls

def test_send_burst(slave):
    slave.start(0)
    slave.send_burst(0xFF)
    slave.stop()
    calls = START_WRITE + ACK
    calls += SEND_BURST + [H_interface.write(CP.Byte.pack(0xFF))]
    calls += STOP + ACK
    assert slave.H.interface.method_calls == calls

def test_restart(slave):
    slave.start(1)
    slave.restart(0)
    slave.stop()
    calls = START_READ + ACK
    calls += RESTART_WRITE + ACK
    calls += STOP + ACK
    assert slave.H.interface.method_calls == calls

def test_read(slave):
    slave.start(1)
    bytes_read = [CP.ACKNOWLEDGE] * 4*2
    bytes_read[::2] = [b'd', b'a', b't', b'a']
    slave.H.interface.read.side_effect = bytes_read + [CP.ACKNOWLEDGE]
    assert slave.read(4) == list(b'data')
    slave.stop()

    calls = START_READ + ACK
    calls += (READ_MORE + [H_interface.read(1)] + ACK)*3
    calls += READ_END + [H_interface.read(1)] + ACK
    calls += STOP + ACK
    assert slave.H.interface.method_calls == calls

def test_simple_read(slave):
    bytes_read = [CP.ACKNOWLEDGE] * 4*2
    bytes_read[::2] = [b'd', b'a', b't', b'a']
    slave.H.interface.read.side_effect = [CP.ACKNOWLEDGE] + bytes_read
    assert slave.simple_read(4) == list(b'data')

    calls = START_READ + ACK
    calls += (READ_MORE + [H_interface.read(1)] + ACK)*3
    calls += READ_END + [H_interface.read(1)] + ACK
    assert slave.H.interface.method_calls == calls

def test_simple_read_byte(slave):
    bytes_read = [b'\xFF', CP.ACKNOWLEDGE]
    slave.H.interface.read.side_effect = [CP.ACKNOWLEDGE] + bytes_read
    assert slave.simple_read_byte() == 0xFF

    calls = START_READ + ACK
    calls += READ_END + [H_interface.read(1)] + ACK
    assert slave.H.interface.method_calls == calls

def test_simple_read_int(slave):
    bytes_read = [b'\xFF', CP.ACKNOWLEDGE] * 2
    slave.H.interface.read.side_effect = [CP.ACKNOWLEDGE] + bytes_read
    assert slave.simple_read_int() == 0xFFFF

    calls = START_READ + ACK
    calls += (READ_MORE + [H_interface.read(1)] + ACK)*1
    calls += READ_END + [H_interface.read(1)] + ACK
    assert slave.H.interface.method_calls == calls

def test_simple_read_long(slave):
    bytes_read = [b'\xFF', CP.ACKNOWLEDGE] * 4
    slave.H.interface.read.side_effect = [CP.ACKNOWLEDGE] + bytes_read
    assert slave.simple_read_long() == 0xFFFFFFFF

    calls = START_READ + ACK
    calls += (READ_MORE + [H_interface.read(1)] + ACK)*3
    calls += READ_END + [H_interface.read(1)] + ACK
    assert slave.H.interface.method_calls == calls

def test_read_bulk(slave):
    slave.H.interface.read.side_effect = [b'data', CP.ACKNOWLEDGE]
    assert slave.read_bulk(REGISTER_ADDRESS, 4) == list(b'data')

    calls = READ_BULK + [H_interface.write(CP.Byte.pack(4))]
    calls += [H_interface.read(4)] + ACK
    assert slave.H.interface.method_calls == calls

def test_read_bulk_byte(slave):
    slave.H.interface.read.side_effect = [b'\xFF', CP.ACKNOWLEDGE]
    assert slave.read_bulk_byte(REGISTER_ADDRESS) == 0xFF

    calls = READ_BULK + [H_interface.write(CP.Byte.pack(1))]
    calls += [H_interface.read(1)] + ACK
    assert slave.H.interface.method_calls == calls

def test_read_bulk_int(slave):
    slave.H.interface.read.side_effect = [b'\xFF'*2, CP.ACKNOWLEDGE]
    assert slave.read_bulk_int(REGISTER_ADDRESS) == 0xFFFF

    calls = READ_BULK + [H_interface.write(CP.Byte.pack(2))]
    calls += [H_interface.read(2)] + ACK
    assert slave.H.interface.method_calls == calls

def test_read_bulk_long(slave):
    slave.H.interface.read.side_effect = [b'\xFF'*4, CP.ACKNOWLEDGE]
    assert slave.read_bulk_long(REGISTER_ADDRESS) == 0xFFFFFFFF

    calls = READ_BULK + [H_interface.write(CP.Byte.pack(4))]
    calls += [H_interface.read(4)] + ACK
    assert slave.H.interface.method_calls == calls

def test_write_bulk(slave):
    slave.write_bulk(b'data')

    calls = WRITE_BULK + [H_interface.write(CP.Byte.pack(4))]
    calls += list(map(H_interface.write, [b'd',b'a',b't',b'a']))
    calls += ACK
    assert slave.H.interface.method_calls == calls

def test_capture(slave):
    pass #TODO
