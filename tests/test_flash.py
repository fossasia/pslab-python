"""Tests for flashing firmware from the CLI.

These tests do not require a connected PSLab.
"""

import argparse
from unittest.mock import MagicMock

import pytest
import serial

import pslab
from pslab import cli
from pslab.connection import SerialHandler


@pytest.fixture
def handler() -> SerialHandler:
    sh = SerialHandler("loop://")
    sh._ser = serial.serial_for_url("loop://", baudrate=1000000, timeout=0.1)
    return sh


@pytest.fixture
def psl(handler: SerialHandler) -> pslab.ScienceLab:
    psl = pslab.ScienceLab.__new__(pslab.ScienceLab)
    psl.device = handler
    return psl


def test_enter_bootloader_switches_baudrate(psl, monkeypatch):
    monkeypatch.setattr("time.sleep", lambda _: None)

    psl.enter_bootloader()

    assert psl.device.baudrate == 460800


def test_flash_uses_the_serial_connection(psl, monkeypatch):
    bootflash = MagicMock()
    bootflash.chunked.return_value = (0, [])
    monkeypatch.setattr(cli, "mcbootflash", bootflash)
    monkeypatch.setattr(psl, "enter_bootloader", MagicMock())

    cli.flash(psl, "firmware.hex")

    psl.enter_bootloader.assert_called_once()
    assert psl.device.timeout == 5
    bootflash.get_boot_attrs.assert_called_once_with(psl.device)
    bootflash.reset.assert_called_once_with(psl.device)


def test_main_flashes_through_the_opened_handler(handler, monkeypatch):
    monkeypatch.setattr(cli, "SerialHandler", lambda port: handler)
    monkeypatch.setattr(
        pslab.ScienceLab,
        "__init__",
        lambda self, device: setattr(self, "device", device),
    )
    flash = MagicMock()
    monkeypatch.setattr(cli, "flash", flash)

    cli.main(argparse.Namespace(function="flash", port=None, hexfile="firmware.hex"))

    psl, hexfile = flash.call_args.args
    assert psl.device is handler
    assert hexfile == "firmware.hex"
