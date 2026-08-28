import csv
import json
import pytest
from pslab.utils.data_export import export_to_csv, export_to_json


def test_export_csv_creates_file(tmp_path):
    data = [{"a": 1, "b": 2}]
    file_path = tmp_path / "data.csv"

    export_to_csv(data, str(file_path))
    assert file_path.exists()

    with file_path.open(newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ["a", "b"]

        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["a"] == "1"
        assert rows[0]["b"] == "2"


def test_export_json_creates_file(tmp_path):
    data = [{"x": 10}]
    file_path = tmp_path / "data.json"

    export_to_json(data, str(file_path))
    assert file_path.exists()

    with file_path.open("r", encoding="utf-8") as f:
        loaded = json.load(f)

    assert loaded == data


def test_export_empty_data_raises_error():
    with pytest.raises(ValueError):
        export_to_csv([], "dummy.csv")
