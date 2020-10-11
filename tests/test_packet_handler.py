import pytest
from serial import SerialException
from serial.tools.list_ports_common import ListPortInfo

import PSL.commands_proto as CP
from PSL.packet_handler import Handler

VERSION = "PSLab vMOCK\n"
PORT = "mock_port"


def mock_ListPortInfo(found=True):
    if found:
        yield ListPortInfo(device=PORT)
    else:
        return


@pytest.fixture
def mock_serial(mocker):
    serial_patch = mocker.patch("PSL.packet_handler.serial.Serial")
    serial_patch().readline.return_value = VERSION.encode()
    return serial_patch


@pytest.fixture
def mock_list_ports(mocker):
    return mocker.patch("PSL.packet_handler.list_ports")


def test_connect_scan_port(mock_serial, mock_list_ports):
    mock_serial().is_open = False
    mock_list_ports.grep.return_value = mock_ListPortInfo()
    Handler()
    mock_serial().open.assert_called()


def test_connect_scan_failure(mock_serial, mock_list_ports):
    mock_serial().is_open = False
    mock_list_ports.grep.return_value = mock_ListPortInfo(found=False)
    with pytest.raises(SerialException):
        Handler()


def test_disconnect(mock_serial):
    H = Handler()
    H.disconnect()
    mock_serial().close.assert_called()


def test_reconnect(mock_serial):
    H = Handler()
    H.reconnect()
    mock_serial().close.assert_called()


def test_get_version(mock_serial):
    H = Handler()
    mock_serial().write.assert_called_with(CP.GET_VERSION)
    assert H.version == VERSION


def test_get_ack_success(mock_serial):
    H = Handler()
    success = 1
    mock_serial().read.return_value = CP.Byte.pack(success)
    assert H.get_ack() == success


def test_get_ack_burst_mode(mock_serial):
    H = Handler()
    success = 1
    H.load_burst = True
    queue_size = H.input_queue_size
    mock_serial().read.return_value = b""

    assert H.get_ack() == success
    assert H.input_queue_size == queue_size + 1


def test_get_ack_failure(mock_serial):
    H = Handler()
    error = 3
    mock_serial().read.return_value = b""
    assert H.get_ack() == error


def test_send_bytes(mock_serial):
    H = Handler()
    H.send_byte(CP.Byte.pack(0xFF))
    mock_serial().write.assert_called_with(CP.Byte.pack(0xFF))


def test_send_byte(mock_serial):
    H = Handler()
    H.send_byte(0xFF)
    mock_serial().write.assert_called_with(CP.Byte.pack(0xFF))


def test_send_byte_burst_mode(mock_serial):
    H = Handler()
    H.load_burst = True
    H.send_byte(0xFF)
    assert H.burst_buffer == CP.Byte.pack(0xFF)


def test_receive(mock_serial):
    H = Handler()
    mock_serial().read.return_value = CP.Byte.pack(0xFF)
    r = H.get_byte()
    mock_serial().read.assert_called_with(1)
    assert r == 0xFF


def test_receive_failure(mock_serial):
    H = Handler()
    mock_serial().read.return_value = b""
    r = H.get_byte()
    mock_serial().read.assert_called_with(1)
    assert r == -1


def test_wait_for_data(mock_serial):
    H = Handler()
    mock_serial().in_waiting = True
    assert H.wait_for_data()


def test_wait_for_data_timeout(mock_serial):
    H = Handler()
    mock_serial().in_waiting = False
    assert not H.wait_for_data()


def test_send_burst(mock_serial):
    H = Handler()
    H.load_burst = True

    for b in b"abc":
        H.send_byte(b)
        H.get_ack()

    mock_serial().read.return_value = b"\x01\x01\x01"
    acks = H.send_burst()

    mock_serial().write.assert_called_with(b"abc")
    mock_serial().read.assert_called_with(3)
    assert not H.load_burst
    assert H.burst_buffer == b""
    assert H.input_queue_size == 0
    assert acks == [1, 1, 1]


def test_get_integer_unsupported_size(mock_serial):
    H = Handler()
    with pytest.raises(ValueError):
        H._get_integer_type(size=3)


def test_list_ports(mock_serial):
    H = Handler()
    assert isinstance(H._list_ports(), list)
