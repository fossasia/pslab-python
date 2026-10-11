"""CLI output resources are released without closing caller-owned streams."""

import argparse
import builtins
import io
import json

import numpy as np
import pytest

from pslab import cli


class FailingOutput:
    """Delegate file ownership while simulating a failed output write."""

    def __init__(self, file):
        self.file = file
        self.error = OSError("output storage unavailable")

    def write(self, text):
        self.file.write(text[:1])
        raise self.error

    def close(self):
        self.file.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


@pytest.fixture
def output_args(monkeypatch):
    monkeypatch.setitem(
        cli.INSTRUMENTS,
        "test-instrument",
        lambda *args: (["CH1"], [np.array([1.0, 2.0])]),
    )
    return argparse.Namespace(
        instrument="test-instrument", channels=1, duration=1, file_path=None, json=False
    )


@pytest.mark.parametrize("as_json", [False, True])
def test_failed_file_output_is_closed(tmp_path, monkeypatch, output_args, as_json):
    """Release the real file even when the write exception retains its frame."""
    destination = tmp_path / "capture"
    file = builtins.open(destination, "w")
    output = FailingOutput(file)
    monkeypatch.setattr(cli, "open", lambda *args: output, raising=False)
    output_args.file_path = str(destination)
    output_args.json = as_json
    try:
        with pytest.raises(OSError) as raised:
            cli.collect(None, output_args)
        assert raised.value is output.error
        assert file.closed
    finally:
        file.close()


@pytest.mark.parametrize("as_json", [False, True])
def test_failed_stdout_is_not_closed(monkeypatch, output_args, as_json):
    """Preserve caller ownership after either formatter encounters a write error."""
    file = io.StringIO()
    output = FailingOutput(file)
    monkeypatch.setattr(cli.sys, "stdout", output)
    output_args.json = as_json
    with pytest.raises(OSError) as raised:
        cli.collect(None, output_args)
    assert raised.value is output.error
    assert not file.closed


@pytest.mark.parametrize("as_json", [False, True])
def test_successful_file_output_is_closed(tmp_path, monkeypatch, output_args, as_json):
    """Close successful output while retaining CSV and JSON content."""
    destination = tmp_path / "capture"
    file = builtins.open(destination, "w")
    monkeypatch.setattr(cli, "open", lambda *args: file, raising=False)
    output_args.file_path = str(destination)
    output_args.json = as_json
    cli.collect(None, output_args)
    assert file.closed
    if as_json:
        assert json.loads(destination.read_text()) == {"CH1": [1.0, 2.0]}
    else:
        assert destination.read_text().splitlines() == ["CH1", "1.0", "2.0"]
