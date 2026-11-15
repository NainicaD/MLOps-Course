"""Validation logic for daily bike-rental CSV batches (no GCP dependencies)."""
import csv
import io
from datetime import date

SCHEMA = {
    "date":      {"type": "date"},
    "season":    {"type": "int", "allowed": {1, 2, 3, 4}},
    "temp":      {"type": "float", "min": 0.0, "max": 1.0},
    "humidity":  {"type": "float", "min": 0.0, "max": 1.0},
    "windspeed": {"type": "float", "min": 0.0, "max": 1.0},
    "rentals":   {"type": "int", "min": 0},
}
MAX_ERRORS = 20


def _parse(value, kind):
    if kind == "date":
        return date.fromisoformat(value)
    if kind == "int":
        return int(value)
    return float(value)


def validate_csv(text):
    """Validate CSV text against SCHEMA and return a report dict."""
    errors = []
    reader = csv.DictReader(io.StringIO(text))
    header = reader.fieldnames or []

    missing = [c for c in SCHEMA if c not in header]
    extra = [c for c in header if c not in SCHEMA]
    if missing:
        errors.append(f"missing columns: {missing}")
    if extra:
        errors.append(f"unexpected columns: {extra}")

    numeric = {c: [] for c, r in SCHEMA.items() if r["type"] != "date"}
    seen_dates = set()
    n_rows = 0

    if not missing:
        for line_no, row in enumerate(reader, start=2):
            n_rows += 1
            for col, rule in SCHEMA.items():
                raw = (row.get(col) or "").strip()
                if raw == "":
                    errors.append(f"line {line_no}: {col} is empty")
                    continue
                try:
                    val = _parse(raw, rule["type"])
                except ValueError:
                    errors.append(f"line {line_no}: {col}={raw!r} is not a valid {rule['type']}")
                    continue
                if col == "date":
                    if val in seen_dates:
                        errors.append(f"line {line_no}: duplicate date {raw}")
                    seen_dates.add(val)
                    continue
                ok = True
                if "allowed" in rule and val not in rule["allowed"]:
                    errors.append(f"line {line_no}: {col}={val} not in {sorted(rule['allowed'])}")
                    ok = False
                if "min" in rule and val < rule["min"]:
                    errors.append(f"line {line_no}: {col}={val} below {rule['min']}")
                    ok = False
                if "max" in rule and val > rule["max"]:
                    errors.append(f"line {line_no}: {col}={val} above {rule['max']}")
                    ok = False
                if ok:
                    numeric[col].append(val)

        if n_rows == 0:
            errors.append("file has no data rows")

    stats = {
        col: {"min": min(v), "max": max(v), "mean": round(sum(v) / len(v), 4)}
        for col, v in numeric.items() if v
    }
    return {
        "status": "ACCEPTED" if not errors else "REJECTED",
        "rows": n_rows,
        "error_count": len(errors),
        "errors": errors[:MAX_ERRORS],
        "stats": stats,
    }
