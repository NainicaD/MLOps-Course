"""Stage 1: clean an uploaded batch, split it, and hand it to training via Pub/Sub."""
import io
import json
import os
from datetime import datetime, timezone

import functions_framework
import pandas as pd
from google.cloud import pubsub_v1, storage
from sklearn.model_selection import train_test_split

PROJECT_ID = os.environ.get("PROJECT_ID", "")
ARTIFACT_BUCKET = os.environ.get("ARTIFACT_BUCKET", "")
TRAINING_TOPIC = os.environ.get("TRAINING_TOPIC", "model-training-trigger")

FEATURES = ["season", "temp", "humidity", "windspeed", "workingday"]
TARGET = "rentals"
REQUIRED = ["date"] + FEATURES + [TARGET]


def _now():
    return datetime.now(timezone.utc).isoformat()


def _log(severity, message, **fields):
    print(json.dumps({"severity": severity, "message": message, **fields}))


def clean(df):
    """Keep required columns, coerce types, drop unusable rows. Returns (df, rows_dropped)."""
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}")
    df = df[REQUIRED].copy()
    for col in FEATURES + [TARGET]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    before = len(df)
    df = df.dropna(subset=FEATURES + [TARGET])
    df = df[df[TARGET] >= 0]
    return df, before - len(df)


@functions_framework.cloud_event
def process_data(cloud_event):
    bucket_name, name = cloud_event.data["bucket"], cloud_event.data["name"]
    if not name.lower().endswith(".csv"):
        _log("INFO", f"skipping non-CSV object {name}")
        return

    run_id = name.rsplit("/", 1)[-1][:-4]
    client = storage.Client()
    artifacts = client.bucket(ARTIFACT_BUCKET)
    raw_text = client.bucket(bucket_name).blob(name).download_as_text()

    try:
        df, dropped = clean(pd.read_csv(io.StringIO(raw_text)))
    except ValueError as err:
        record = {"run_id": run_id, "status": "FAILED", "reason": str(err), "recorded_at": _now()}
        artifacts.blob(f"registry/runs/{run_id}.json").upload_from_string(
            json.dumps(record, indent=2), content_type="application/json")
        _log("ERROR", f"{run_id}: {err}", run_id=run_id)
        return

    train, holdout = train_test_split(df, test_size=0.2, random_state=42)
    prefix = f"processed/{run_id}"
    artifacts.blob(f"{prefix}/train.csv").upload_from_string(train.to_csv(index=False), content_type="text/csv")
    artifacts.blob(f"{prefix}/holdout.csv").upload_from_string(holdout.to_csv(index=False), content_type="text/csv")

    message = {
        "run_id": run_id,
        "train_path": f"{prefix}/train.csv",
        "holdout_path": f"{prefix}/holdout.csv",
        "rows_dropped": dropped,
        "train_rows": len(train),
        "holdout_rows": len(holdout),
    }
    publisher = pubsub_v1.PublisherClient()
    publisher.publish(publisher.topic_path(PROJECT_ID, TRAINING_TOPIC),
                      json.dumps(message).encode("utf-8")).result()
    _log("INFO", f"{run_id}: processed, published to {TRAINING_TOPIC}", **message)
