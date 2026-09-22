"""Tests for pslab.external.motor.RoboticArm CSV import and export.

These tests do not require a connected PSLab.
"""

from unittest.mock import MagicMock

import pytest

from pslab.external.motor import RoboticArm, Servo


def make_arm(servo_count: int) -> RoboticArm:
    pwm = MagicMock()
    return RoboticArm([Servo(f"SQ{i + 1}", pwm) for i in range(servo_count)])


def write_csv(path, rows):
    header = "Timestep,Servo1,Servo2,Servo3,Servo4\n"
    path.write_text(header + "".join(f"{row}\n" for row in rows))
    return str(path)


@pytest.mark.parametrize("servo_count", [1, 2, 3, 4])
def test_export_import_round_trip(tmp_path, servo_count):
    arm = make_arm(servo_count)
    timeline = [
        [10 * (i + 1) for i in range(servo_count)],
        [None] + [90] * (servo_count - 1),
    ]

    arm.export_timeline_to_csv(timeline, str(tmp_path))
    (exported,) = tmp_path.glob("*.csv")

    assert arm.import_timeline_from_csv(str(exported)) == timeline


def test_export_pads_rows_to_four_servos(tmp_path):
    make_arm(2).export_timeline_to_csv([[10, 20]], str(tmp_path))
    (exported,) = tmp_path.glob("*.csv")

    assert exported.read_text().splitlines()[1] == "0,10,20,null,null"


def test_imported_timeline_runs_on_a_smaller_arm(tmp_path):
    arm = make_arm(2)
    path = write_csv(tmp_path / "t.csv", ["0,10,20,null,null"])

    arm.run_schedule(arm.import_timeline_from_csv(path), time_step=0)

    assert [servo.angle for servo in arm.servos] == [10, 20]


def test_import_accepts_short_rows(tmp_path):
    path = write_csv(tmp_path / "t.csv", ["0,10,20"])

    assert make_arm(2).import_timeline_from_csv(path) == [[10, 20]]


def test_import_rejects_angles_for_missing_servos(tmp_path):
    path = write_csv(tmp_path / "t.csv", ["0,10,20,30,null"])

    with pytest.raises(ValueError, match="more than 2 servos"):
        make_arm(2).import_timeline_from_csv(path)


def test_import_rejects_missing_servo_columns(tmp_path):
    path = tmp_path / "t.csv"
    path.write_text("Timestep,Servo1,Servo2\n0,10,20\n")

    with pytest.raises(ValueError, match="Servo1-Servo4"):
        make_arm(2).import_timeline_from_csv(str(path))


def test_export_rejects_more_than_four_angles(tmp_path):
    with pytest.raises(ValueError, match="more than 4 angles"):
        make_arm(4).export_timeline_to_csv([[1, 2, 3, 4, 5]], str(tmp_path))

    assert list(tmp_path.iterdir()) == []
