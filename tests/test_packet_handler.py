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
def mock_handler(mocker, mock_serial):
    mocker.patch("PSL.packet_handler.Handler._check_udev")
    return Handler()


@pytest.fixture
def mock_list_ports(mocker):
    return mocker.patch("PSL.packet_handler.list_ports")


def test_connect_scan_port(mocker, mock_serial, mock_list_ports):
    mock_serial().is_open = False
    mock_list_ports.grep.return_value = mock_ListPortInfo()
    mocker.patch("PSL.packet_handler.Handler._check_udev")
    Handler()
    mock_serial().open.assert_called()


def test_connect_scan_failure(mocker, mock_serial, mock_list_ports):
    mock_serial().is_open = False
    mock_list_ports.grep.return_value = mock_ListPortInfo(found=False)
    mocker.patch("PSL.packet_handler.Handler._check_udev")
    with pytest.raises(SerialException):
        Handler()


def test_disconnect(mock_serial, mock_handler):
    mock_handler.disconnect()
    mock_serial().close.assert_called()


def test_reconnect(mock_serial, mock_handler):
    mock_handler.reconnect()
    mock_serial().close.assert_called()


def test_get_version(mock_serial, mock_handler):
    mock_handler.get_version()
    mock_serial().write.assert_called_with(CP.GET_VERSION)
    assert mock_handler.version == VERSION


def test_get_ack_success(mock_serial, mock_handler):
    H = Handler()
    success = 1
    mock_serial().read.return_value = CP.Byte.pack(success)
    assert H.get_ack() == success


def test_get_ack_burst_mode(mock_serial, mock_handler):
    success = 1
    mock_handler.load_burst = True
    queue_size = mock_handler.input_queue_size
    mock_serial().read.return_value = b""

    assert mock_handler.get_ack() == success
    assert mock_handler.input_queue_size == queue_size + 1


def test_get_ack_failure(mock_serial, mock_handler):
    error = 3
    mock_serial().read.return_value = b""
    assert mock_handler.get_ack() == error


def test_send_bytes(mock_serial, mock_handler):
    mock_handler.send_byte(CP.Byte.pack(0xFF))
    mock_serial().write.assert_called_with(CP.Byte.pack(0xFF))


def test_send_byte(mock_serial, mock_handler):
    mock_handler.send_byte(0xFF)
    mock_serial().write.assert_called_with(CP.Byte.pack(0xFF))


def test_send_byte_burst_mode(mock_serial, mock_handler):
    mock_handler.load_burst = True
    mock_handler.send_byte(0xFF)
    assert mock_handler.burst_buffer == CP.Byte.pack(0xFF)


def test_receive(mock_serial, mock_handler):
    mock_serial().read.return_value = CP.Byte.pack(0xFF)
    r = mock_handler.get_byte()
    mock_serial().read.assert_called_with(1)
    assert r == 0xFF


def test_receive_failure(mock_serial, mock_handler):
    mock_serial().read.return_value = b""
    r = mock_handler.get_byte()
    mock_serial().read.assert_called_with(1)
    assert r == -1


def test_wait_for_data(mock_serial, mock_handler):
    mock_serial().in_waiting = True
    assert mock_handler.wait_for_data()


def test_wait_for_data_timeout(mock_serial, mock_handler):
    mock_serial().in_waiting = False
    assert not mock_handler.wait_for_data()


def test_send_burst(mock_serial, mock_handler):
    mock_handler.load_burst = True

    for b in b"abc":
        mock_handler.send_byte(b)
        mock_handler.get_ack()

    mock_serial().read.return_value = b"\x01\x01\x01"
    acks = mock_handler.send_burst()

    mock_serial().write.assert_called_with(b"abc")
    mock_serial().read.assert_called_with(3)
    assert not mock_handler.load_burst
    assert mock_handler.burst_buffer == b""
    assert mock_handler.input_queue_size == 0
    assert acks == [1, 1, 1]


def test_get_integer_unsupported_size(mock_serial, mock_handler):
    with pytest.raises(ValueError):
        mock_handler._get_integer_type(size=3)


def test_list_ports(mock_serial, mock_handler):
    assert isinstance(mock_handler._list_ports(), list)
