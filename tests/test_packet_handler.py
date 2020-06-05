import unittest
from unittest.mock import patch

import serial
from serial.tools.list_ports_common import ListPortInfo

import PSL.commands_proto as CP
from PSL.packet_handler import Handler

VERSION = "PSLab vMOCK\n"
PORT = "mockport"


class TestHandler(unittest.TestCase):
    @staticmethod
    def mock_ListPortInfo(found=True):
        if found:
            yield ListPortInfo(device=PORT)
        else:
            return

    def setUp(self):
        self.Serial_patcher = patch("PSL.packet_handler.serial.Serial")
        self.list_ports_patcher = patch("PSL.packet_handler.list_ports")
        self.mock_Serial = self.Serial_patcher.start()
        self.mock_list_ports = self.list_ports_patcher.start()
        self.mock_Serial().readline.return_value = VERSION.encode("utf-8")

    def tearDown(self):
        self.Serial_patcher.stop()
        self.list_ports_patcher.stop()

    def test_connect_port_provided(self):
        Handler(port=PORT)
        self.assertTrue(self.mock_Serial().is_open)

    def test_connect_scan_port(self):
        self.mock_Serial().is_open = False
        self.mock_list_ports.grep.return_value = self.mock_ListPortInfo()
        Handler()
        self.mock_Serial().open.assert_called()

    def test_connect_scan_failure(self):
        self.mock_Serial().is_open = False
        self.mock_list_ports.grep.return_value = self.mock_ListPortInfo(found=False)
        self.assertRaises(serial.SerialException, Handler)

    def test_disconnect(self):
        H = Handler()
        H.disconnect()
        self.mock_Serial().close.assert_called()

    def test_reconnect(self):
        H = Handler(port=PORT)
        H.reconnect(port=PORT[::-1])
        self.assertIn({"port": PORT}, self.mock_Serial.call_args_list)
        self.assertIn({"port": PORT[::-1]}, self.mock_Serial.call_args_list)
        self.mock_Serial().close.assert_called()

    def test_del(self):
        H = Handler()
        H.__del__()
        self.mock_Serial().close.assert_called()

    def test_get_version(self):
        H = Handler()

        self.mock_Serial().write.assert_called_with(CP.GET_VERSION)
        self.assertEqual(H.version, VERSION)

    def test_get_ack_success(self):
        H = Handler()
        success = 1
        self.mock_Serial().read.return_value = CP.Byte.pack(success)
        self.assertEqual(H.get_ack(), success)

    def test_get_ack_burst_mode(self):
        H = Handler()
        success = 1
        H.load_burst = True
        queue_size = H.input_queue_size
        self.mock_Serial().read.return_value = b""

        self.assertEqual(H.get_ack(), success)
        self.assertEqual(H.input_queue_size, queue_size + 1)

    def test_get_ack_failure(self):
        H = Handler()
        error = 3
        self.mock_Serial().read.return_value = b""
        self.assertEqual(H.get_ack(), error)

    def test_send_bytes(self):
        H = Handler()
        H.send(CP.Byte.pack(0xFF))
        self.mock_Serial().write.assert_called_with(CP.Byte.pack(0xFF))

    def test_send_byte(self):
        H = Handler()
        H.send(0xFF)
        self.mock_Serial().write.assert_called_with(CP.Byte.pack(0xFF))

    def test_send_byte_burst_mode(self):
        H = Handler()
        H.load_burst = True
        H.send(0xFF)
        self.assertEqual(H.burst_buffer, CP.Byte.pack(0xFF))

    def test_send_int(self):
        H = Handler()
        H.send(0xFFFF)
        self.mock_Serial().write.assert_called_with(CP.ShortInt.pack(0xFFFF))

    def test_send_int_burst_mode(self):
        H = Handler()
        H.load_burst = True
        H.send(0xFFFF)
        self.assertEqual(H.burst_buffer, CP.ShortInt.pack(0xFFFF))

    def test_send_long(self):
        H = Handler()
        H.send(0xFFFFFFFF)
        self.mock_Serial().write.assert_called_with(CP.Integer.pack(0xFFFFFFFF))

    def test_send_long_burst_mode(self):
        H = Handler()
        H.load_burst = True
        H.send(0xFFFFFFFF)
        self.assertEqual(H.burst_buffer, CP.Integer.pack(0xFFFFFFFF))

    def test_receive(self):
        H = Handler()
        self.mock_Serial().read.return_value = CP.Byte.pack(0xFF)
        r = H.receive(1)
        self.mock_Serial().read.assert_called_with(1)
        self.assertEqual(r, 0xFF)

    def test_receive_uneven_bytes(self):
        H = Handler()
        self.mock_Serial().read.return_value = int.to_bytes(
            0xFFFFFF, length=3, byteorder="little", signed=False
        )
        r = H.receive(3)
        self.mock_Serial().read.assert_called_with(3)
        self.assertEqual(r, 0xFFFFFF)

    def test_receive_failure(self):
        H = Handler()
        self.mock_Serial().read.return_value = b""
        r = H.receive(1)
        self.mock_Serial().read.assert_called_with(1)
        self.assertEqual(r, -1)

    def test_wait_for_data(self):
        H = Handler()
        self.assertTrue(H.wait_for_data())

    def test_wait_for_data_timeout(self):
        H = Handler()
        self.mock_Serial().in_waiting = False
        self.assertFalse(H.wait_for_data())

    def test_send_burst(self):
        H = Handler()
        H.load_burst = True

        for b in b"abc":
            H.send(b)
            H.get_ack()

        self.mock_Serial().read.return_value = b"\x01\x01\x01"
        acks = H.send_burst()

        self.mock_Serial().write.assert_called_with(b"abc")
        self.mock_Serial().read.assert_called_with(3)
        self.assertFalse(H.load_burst)
        self.assertEqual(H.burst_buffer, b"")
        self.assertEqual(H.input_queue_size, 0)
        self.assertEqual(acks, [1, 1, 1])

    def test_get_integer_unsupported_size(self):
        H = Handler()
        self.assertRaises(ValueError, H._get_integer_type, size=3)

    def test_list_ports(self):
        self.list_ports_patcher.stop()
        H = Handler()
        self.assertTrue(isinstance(H._list_ports(), list))
        self.list_ports_patcher.start()


if __name__ == "__main__":
    unittest.main()
