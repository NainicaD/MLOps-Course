from pathlib import Path

from validator import validate_csv

DATA = Path(__file__).parent.parent / "sample_data"
HEADER = "date,season,temp,humidity,windspeed,rentals\n"


def test_clean_batch_accepted():
    r = validate_csv((DATA / "2026_01_week1.csv").read_text())
    assert r["status"] == "ACCEPTED"
    assert r["rows"] == 7
    assert r["error_count"] == 0
    assert r["stats"]["rentals"]["min"] == 801


def test_bad_batch_reports_each_problem():
    r = validate_csv((DATA / "2026_01_week2.csv").read_text())
    assert r["status"] == "REJECTED"
    assert r["error_count"] == 4
    joined = " ".join(r["errors"])
    assert "temp=1.4 above 1.0" in joined
    assert "season=5 not in" in joined
    assert "rentals='abc' is not a valid int" in joined
    assert "duplicate date 2026-01-11" in joined


def test_missing_column_rejected():
    r = validate_csv((DATA / "2026_01_week3.csv").read_text())
    assert r["status"] == "REJECTED"
    assert r["errors"] == ["missing columns: ['humidity']"]


def test_extra_column_rejected():
    text = HEADER.strip() + ",notes\n2026-02-01,1,0.2,0.5,0.1,900,hi\n"
    r = validate_csv(text)
    assert "unexpected columns: ['notes']" in r["errors"]


def test_header_only_rejected():
    r = validate_csv(HEADER)
    assert r["errors"] == ["file has no data rows"]


def test_empty_value_rejected():
    r = validate_csv(HEADER + "2026-02-01,1,,0.5,0.1,900\n")
    assert "line 2: temp is empty" in r["errors"]


def test_negative_rentals_rejected():
    r = validate_csv(HEADER + "2026-02-01,1,0.2,0.5,0.1,-3\n")
    assert r["status"] == "REJECTED"
    assert "rentals" not in r["stats"]
