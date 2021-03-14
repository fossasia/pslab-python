import pytest
from serial import SerialException
from serial.tools.list_ports_common import ListPortInfo

import pslab.protocol as CP
from pslab.serial_handler import detect, SerialHandler

VERSION = "PSLab vMOCK\n"
PORT = "mock_port"
PORT2 = "mock_port_2"


def mock_ListPortInfo(found=True, multiple=False):
    if found:
        if multiple:
            yield from [ListPortInfo(device=PORT), ListPortInfo(device=PORT2)]
        else:
            yield ListPortInfo(device=PORT)
    else:
        return


@pytest.fixture
def mock_serial(mocker):
    serial_patch = mocker.patch("pslab.serial_handler.serial.Serial")
    serial_patch().readline.return_value = VERSION.encode()
    serial_patch().is_open = False
    return serial_patch


@pytest.fixture
def mock_handler(mocker, mock_serial, mock_list_ports):
    mocker.patch("pslab.serial_handler.SerialHandler.check_serial_access_permission")
    mock_list_ports.grep.return_value = mock_ListPortInfo()
    return SerialHandler()


@pytest.fixture
def mock_list_ports(mocker):
    return mocker.patch("pslab.serial_handler.list_ports")


def test_detect(mocker, mock_serial, mock_list_ports):
    mock_list_ports.grep.return_value = mock_ListPortInfo(multiple=True)
    assert len(detect()) == 2


def test_connect_scan_port(mocker, mock_serial, mock_list_ports):
    mock_list_ports.grep.return_value = mock_ListPortInfo()
    mocker.patch("pslab.serial_handler.SerialHandler.check_serial_access_permission")
    SerialHandler()
    mock_serial().open.assert_called()


def test_connect_scan_failure(mocker, mock_serial, mock_list_ports):
    mock_list_ports.grep.return_value = mock_ListPortInfo(found=False)
    mocker.patch("pslab.serial_handler.SerialHandler.check_serial_access_permission")
    with pytest.raises(SerialException):
        SerialHandler()


def test_connect_multiple_connected(mocker, mock_serial, mock_list_ports):
    mock_list_ports.grep.return_value = mock_ListPortInfo(multiple=True)
    mocker.patch("pslab.serial_handler.SerialHandler.check_serial_access_permission")
    with pytest.raises(RuntimeError):
        SerialHandler()


def test_disconnect(mock_serial, mock_handler):
    mock_handler.disconnect()
    mock_serial().close.assert_called()


def test_reconnect(mock_serial, mock_handler, mock_list_ports):
    mock_list_ports.grep.return_value = mock_ListPortInfo()
    mock_handler.reconnect()
    mock_serial().close.assert_called()


def test_get_version(mock_serial, mock_handler):
    mock_handler.get_version()
    mock_serial().write.assert_called_with(CP.GET_VERSION)
    assert mock_handler.version == VERSION


def test_get_ack_success(mock_serial, mock_handler):
    success = 1
    mock_serial().read.return_value = CP.Byte.pack(success)
    assert mock_handler.get_ack() == success


def test_get_ack_failure(mock_serial, mock_handler):
    mock_serial().read.return_value = b""
    with pytest.raises(SerialException):
        mock_handler.get_ack()


def test_send_bytes(mock_serial, mock_handler):
    mock_handler.send_byte(CP.Byte.pack(0xFF))
    mock_serial().write.assert_called_with(CP.Byte.pack(0xFF))


def test_send_byte(mock_serial, mock_handler):
    mock_handler.send_byte(0xFF)
    mock_serial().write.assert_called_with(CP.Byte.pack(0xFF))


def test_receive(mock_serial, mock_handler):
    mock_serial().read.return_value = CP.Byte.pack(0xFF)
    r = mock_handler.get_byte()
    mock_serial().read.assert_called_with(1)
    assert r == 0xFF


def test_receive_failure(mock_serial, mock_handler):
    mock_serial().read.return_value = b""
    with pytest.raises(SerialException):
        mock_handler.get_byte()


def test_wait_for_data(mock_serial, mock_handler):
    mock_serial().in_waiting = True
    assert mock_handler.wait_for_data()


def test_wait_for_data_timeout(mock_serial, mock_handler):
    mock_serial().in_waiting = False
    assert not mock_handler.wait_for_data()


def test_get_integer_unsupported_size(mock_serial, mock_handler):
    with pytest.raises(ValueError):
        mock_handler._get_integer_type(size=3)


def test_list_ports(mock_serial, mock_handler):
    assert isinstance(mock_handler._list_ports(), list)
