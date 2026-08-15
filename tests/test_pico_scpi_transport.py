import socket

import pytest

from pslab.pico import (
    PicoDevice,
    PicoWifiTransport,
    ScpiClient,
    ScpiError,
    ScpiTimeoutError,
)


class FakeTransport:
    def __init__(self):
        self.output = bytearray()
        self.writes = []
        self.timeout = 1.0
        self.closed = False
        self.connected = False
        self.transport_mode = "USB"

    def connect(self):
        self.connected = True

    def close(self):
        self.closed = True

    def read(self, size):
        data = self.output[:size]
        del self.output[:size]
        return bytes(data)

    def readline(self):
        try:
            end = self.output.index(ord("\n")) + 1
        except ValueError:
            end = len(self.output)
        return self.read(end)

    def write(self, data):
        self.writes.append(data)
        command = data.strip().decode("ascii")
        responses = {
            "*IDN?": b"FOSSASIA,PSLab Pico,1.0,v0.1.0\n",
            "SYST:ERR:COUN?": b"1\n",
            "SYST:ERR?": b"-113,\"Undefined header\"\n",
            "COMM:WIFI:STAT?": b"1,12,3,4\n",
        }
        if command == "LA:READ?":
            payload = b"abcd"
            self.output.extend(b"#14" + payload + b"\n")
        elif command.startswith("COMM:TRAN "):
            self.transport_mode = command.split(" ", 1)[1]
        elif command == "COMM:TRAN?":
            self.output.extend(f"{self.transport_mode}\n".encode("ascii"))
        elif command == "BAD:BLOCK?":
            self.output.extend(b"-200,\"Execution error\"\n")
        elif command in responses:
            self.output.extend(responses[command])
        return len(data)

    def flush(self):
        pass

    def reset_input_buffer(self):
        self.output.clear()


class FakeSocket:
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.recv_sizes = []
        self.timeout = None
        self.connected_to = None

    def settimeout(self, timeout):
        self.timeout = timeout

    def connect(self, address):
        self.connected_to = address

    def recv(self, size):
        self.recv_sizes.append(size)
        if not self.chunks:
            return b""
        chunk = self.chunks.pop(0)
        if isinstance(chunk, BaseException):
            raise chunk
        return chunk

    def sendall(self, data):
        self.sent = data

    def close(self):
        self.closed = True


def test_query_writes_newline_and_reads_text_response():
    transport = FakeTransport()
    client = ScpiClient(transport)

    response = client.query("*IDN?")

    assert response == "FOSSASIA,PSLab Pico,1.0,v0.1.0"
    assert transport.writes == [b"*IDN?\n"]


def test_command_rejects_query_commands():
    client = ScpiClient(FakeTransport())

    with pytest.raises(ValueError):
        client.command("*IDN?")


def test_command_sends_silent_command():
    transport = FakeTransport()
    client = ScpiClient(transport)

    client.command("*RST")

    assert transport.writes == [b"*RST\n"]


def test_query_block_reads_definite_length_payload():
    client = ScpiClient(FakeTransport())

    payload = client.query_block("LA:READ?")

    assert payload == b"abcd"


def test_query_block_allows_missing_terminator():
    transport = FakeTransport()
    transport.output.extend(b"#14abcd")
    client = ScpiClient(transport)

    payload = client.query_block("CUSTOM:BLOCK?")

    assert payload == b"abcd"


def test_query_block_rejects_unexpected_terminator():
    transport = FakeTransport()
    transport.output.extend(b"#14abcdX")
    client = ScpiClient(transport)

    with pytest.raises(ScpiError, match="Unexpected SCPI block terminator"):
        client.query_block("CUSTOM:BLOCK?")


@pytest.mark.parametrize("terminator", [b"\n", b"\r", b"\r\n"])
def test_query_block_accepts_line_terminator_variants(terminator):
    transport = FakeTransport()
    transport.output.extend(b"#14abcd" + terminator)
    client = ScpiClient(transport)

    assert client.query_block("CUSTOM:BLOCK?") == b"abcd"
    assert transport.output == bytearray()


def test_query_block_rejects_unexpected_byte_after_carriage_return():
    transport = FakeTransport()
    transport.output.extend(b"#14abcd\rX")
    client = ScpiClient(transport)

    with pytest.raises(ScpiError, match="Unexpected SCPI block terminator"):
        client.query_block("CUSTOM:BLOCK?")


def test_query_block_raises_scpi_error_when_response_is_text_error():
    client = ScpiClient(FakeTransport())

    with pytest.raises(ScpiError, match="Execution error"):
        client.query_block("BAD:BLOCK?")


def test_system_error_parses_code_and_message():
    client = ScpiClient(FakeTransport())

    code, message = client.system_error()

    assert code == -113
    assert message == "Undefined header"


def test_transport_helpers_parse_status_values():
    transport = FakeTransport()
    client = ScpiClient(transport)

    client.set_transport("wifi")
    assert client.get_transport() == "WIFI"
    assert client.wifi_status() == (True, 12, 3, 4)
    assert b"COMM:TRAN WIFI\n" in transport.writes


def test_pico_device_wraps_scpi_client():
    transport = FakeTransport()
    device = PicoDevice.from_transport(transport)

    with device:
        assert device.identify() == "FOSSASIA,PSLab Pico,1.0,v0.1.0"

    assert transport.connected
    assert transport.closed


def test_wifi_read_zero_returns_empty_without_socket_read():
    transport = PicoWifiTransport("example.test")
    transport._socket = FakeSocket([b"unexpected"])

    assert transport.read(0) == b""
    assert transport._socket.recv_sizes == []


def test_wifi_read_rejects_negative_size():
    transport = PicoWifiTransport("example.test")

    with pytest.raises(ValueError):
        transport.read(-1)


def test_wifi_read_wraps_socket_timeout():
    transport = PicoWifiTransport("example.test")
    transport._socket = FakeSocket([socket.timeout()])

    with pytest.raises(ScpiTimeoutError):
        transport.read(1)


def test_wifi_readline_wraps_socket_timeout():
    transport = PicoWifiTransport("example.test")
    transport._socket = FakeSocket([socket.timeout()])

    with pytest.raises(ScpiTimeoutError):
        transport.readline()
