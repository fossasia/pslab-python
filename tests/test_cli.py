"""Tests for PSL.cli.

Before running the tests, connect:
    SQ1 -> LA1
    SQ2 -> LA2
    SQ3 -> LA3
    SQ4 -> LA4
    SI1 -> CH1
    SI2 -> CH2
    SI1 -> CH3
"""

import csv
import json

import numpy as np
import pytest

import pslab.protocol as CP
from pslab import cli
from pslab.instrument.analog import AnalogOutput
from pslab.instrument.waveform_generator import WaveformGenerator

LA_CHANNELS = 4
EVENTS = 2450
LA_DURATION = 1.5

SCOPE_CHANNELS = 4
SAMPLES = CP.MAX_SAMPLES // SCOPE_CHANNELS
SCOPE_DURATION = 0.5


@pytest.fixture
def la(mocker):
    mock = mocker.patch("pslab.cli.LogicAnalyzer")
    mock().fetch_data.return_value = [np.arange(2500)] * LA_CHANNELS
    return mock


@pytest.fixture
def scope(mocker):
    mock = mocker.patch("pslab.cli.Oscilloscope")
    mock()._lookup_mininum_timegap.return_value = 0.5
    mock().capture.return_value = [np.zeros(SAMPLES)] * (SCOPE_CHANNELS + 1)
    mock()._channel_one_map = "CH1"
    mock()._CH234 = ["CH2", "CH3", "MIC"]
    return mock


def logic_analyzer(device, channels, duration):
    headers = ["LA1", "LA2", "LA3", "LA4"][:channels]
    timestamps = [np.arange(0, duration * 1e6, (duration * 1e6) / EVENTS)] * channels
    return headers, timestamps


def oscilloscope(device, channels, duration):
    headers = ["Timestamp", "CH1", "CH2", "CH3", "MIC"][: 1 + channels]
    timestamp = np.arange(0, duration * 1e6, (duration * 1e6) / SAMPLES)
    data = [np.random.random_sample(SAMPLES)] * channels
    return headers, [timestamp] + data


@pytest.fixture(name="collect")
def setup_collect(mocker, monkeypatch):
    """Return a ArgumentParser instance with all arguments added."""
    mocker.patch("pslab.cli.SerialHandler")
    INSTRUMENTS = {
        "logic_analyzer": logic_analyzer,
        "oscilloscope": oscilloscope,
    }
    monkeypatch.setattr(cli, "INSTRUMENTS", INSTRUMENTS)


@pytest.fixture(name="wave")
def setup_wave(mocker):
    mocker.patch("pslab.cli.SerialHandler")


def test_logic_analyzer(la):
    channels, timestamps = cli.logic_analyzer(la, LA_CHANNELS, LA_DURATION)
    assert len(channels) == LA_CHANNELS
    for timestamp in timestamps:
        assert len(timestamp) > EVENTS


def test_oscilloscope(scope):
    headers, values = cli.oscilloscope(scope, SCOPE_CHANNELS, SCOPE_DURATION)
    assert len(headers) == 1 + SCOPE_CHANNELS
    for value in values:
        assert len(value) > SAMPLES


def test_collect_csv_stdout(collect, capsys):
    cli.cmdline(["collect", "logic_analyzer", "--channels", str(LA_CHANNELS)])
    output = list(csv.reader(capsys.readouterr().out.splitlines()))
    assert len(output[0]) == LA_CHANNELS
    assert len(output) == 1 + EVENTS

    cli.cmdline(["collect", "oscilloscope", "--channels", str(SCOPE_CHANNELS)])
    output = list(csv.reader(capsys.readouterr().out.splitlines()))
    assert len(output[0]) == 1 + SCOPE_CHANNELS
    assert len(output) == 1 + SAMPLES


def test_collect_csv_file(collect, tmp_path):
    la_temp_csv = str(tmp_path / "logic_analyzer.csv")
    cli.cmdline(
        [
            "collect",
            "logic_analyzer",
            "--channels",
            str(LA_CHANNELS),
            "--output",
            la_temp_csv,
        ]
    )
    with open(la_temp_csv) as csv_file:
        output = list(csv.reader(csv_file.read().splitlines()))
        assert len(output[0]) == LA_CHANNELS
        assert len(output) == 1 + EVENTS

    scope_temp_csv = str(tmp_path / "oscilloscope.csv")
    cli.cmdline(
        [
            "collect",
            "oscilloscope",
            "--channels",
            str(SCOPE_CHANNELS),
            "--output",
            scope_temp_csv,
        ]
    )
    with open(scope_temp_csv) as csv_file:
        output = list(csv.reader(csv_file.read().splitlines()))
        assert len(output[0]) == 1 + SCOPE_CHANNELS
        assert len(output) == 1 + SAMPLES


def test_collect_json_stdout(collect, capsys):
    cli.cmdline(["collect", "logic_analyzer", "--channels", str(LA_CHANNELS), "--json"])
    output = json.loads(capsys.readouterr().out)
    assert len(output) == LA_CHANNELS
    assert len(list(output.values())[0]) == EVENTS

    cli.cmdline(
        ["collect", "oscilloscope", "--channels", str(SCOPE_CHANNELS), "--json"]
    )
    output = json.loads(capsys.readouterr().out)
    assert len(output) == 1 + SCOPE_CHANNELS
    assert len(list(output.values())[0]) == SAMPLES


def test_collect_json_file(collect, tmp_path):
    la_tmp_json = str(tmp_path / "logic_analyzer.json")
    cli.cmdline(
        [
            "collect",
            "logic_analyzer",
            "--channels",
            str(LA_CHANNELS),
            "--output",
            la_tmp_json,
            "--json",
        ]
    )
    with open(la_tmp_json) as json_file:
        output = json.load(json_file)
        assert len(output) == LA_CHANNELS
        assert len(list(output.values())[0]) == EVENTS

    scope_tmp_json = str(tmp_path / "oscilloscope.json")
    cli.cmdline(
        [
            "collect",
            "oscilloscope",
            "--channels",
            str(SCOPE_CHANNELS),
            "--output",
            scope_tmp_json,
            "--json",
        ]
    )
    with open(scope_tmp_json) as json_file:
        output = json.load(json_file)
        assert len(output) == 1 + SCOPE_CHANNELS
        assert len(list(output.values())[0]) == SAMPLES


def test_wave_load_table(wave, mocker):
    wavegen = WaveformGenerator(mocker.Mock())
    wavegen.load_function("SI1", "tria")

    def tria(x):
        return AnalogOutput.RANGE[1] * (abs(x % 4 - 2) - 1)

    span = [-1, 3]
    x = np.arange(span[0], span[1], (span[1] - span[0]) / 512)
    table = json.dumps(tria(x).tolist())
    cli.cmdline(["wave", "load", "SI2", "--table", table])
    assert AnalogOutput("SI1").waveform_table == AnalogOutput("SI2").waveform_table


def test_wave_load_table_expand(wave):
    table1 = json.dumps([0, 1])
    cli.cmdline(["wave", "load", "SI1", "--table", table1])
    table2 = json.dumps(([0] * (512 // 2)) + ([1] * (512 // 2)))
    cli.cmdline(["wave", "load", "SI2", "--table", table2])
    assert AnalogOutput("SI1").waveform_table == AnalogOutput("SI2").waveform_table


def test_wave_load_tablefile(wave, mocker, tmp_path):
    wavegen = WaveformGenerator(mocker.Mock())
    wavegen.load_function("SI1", "tria")

    def tria(x):
        return AnalogOutput.RANGE[1] * (abs(x % 4 - 2) - 1)

    span = [-1, 3]
    x = np.arange(span[0], span[1], (span[1] - span[0]) / 512)
    table_tmp_json = str(tmp_path / "table.json")
    with open(table_tmp_json, "w") as json_file:
        json.dump(tria(x).tolist(), json_file)
    cli.cmdline(["wave", "load", "SI2", "--table-file", table_tmp_json])
    assert AnalogOutput("SI1").waveform_table == AnalogOutput("SI2").waveform_table


def test_wave_load_tablefile_expand(wave, tmp_path):
    table1_tmp_json = str(tmp_path / "table1.json")
    with open(table1_tmp_json, "w") as json_file:
        json.dump([0, 1], json_file)
    cli.cmdline(["wave", "load", "SI1", "--table-file", table1_tmp_json])
    table2_tmp_json = str(tmp_path / "table2.json")
    with open(table2_tmp_json, "w") as json_file:
        json.dump(([0] * (512 // 2)) + ([1] * (512 // 2)), json_file)
    cli.cmdline(["wave", "load", "SI2", "--table-file", table2_tmp_json])
    assert AnalogOutput("SI1").waveform_table == AnalogOutput("SI2").waveform_table
