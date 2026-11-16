"""Stage 2: train a challenger, compare it with the current champion, promote or reject."""
import base64
import io
import json
import os
import tempfile
from datetime import datetime, timezone

import functions_framework
import joblib
import pandas as pd
from google.cloud import pubsub_v1, storage
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

PROJECT_ID = os.environ.get("PROJECT_ID", "")
ARTIFACT_BUCKET = os.environ.get("ARTIFACT_BUCKET", "")
EVENTS_TOPIC = os.environ.get("EVENTS_TOPIC", "model-events")
MIN_IMPROVEMENT = 0.02  # challenger must beat the champion's MAE by at least 2%

FEATURES = ["season", "temp", "humidity", "windspeed", "workingday"]
TARGET = "rentals"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _read_csv(bucket, path):
    return pd.read_csv(io.StringIO(bucket.blob(path).download_as_text()))


def _save_model(bucket, model, path):
    with tempfile.NamedTemporaryFile(suffix=".joblib") as tmp:
        joblib.dump(model, tmp.name)
        bucket.blob(path).upload_from_filename(tmp.name)


def _load_model(bucket, path):
    with tempfile.NamedTemporaryFile(suffix=".joblib") as tmp:
        bucket.blob(path).download_to_filename(tmp.name)
        return joblib.load(tmp.name)


def _mae(model, df):
    return round(float(mean_absolute_error(df[TARGET], model.predict(df[FEATURES]))), 2)


@functions_framework.cloud_event
def train_model(cloud_event):
    msg = json.loads(base64.b64decode(cloud_event.data["message"]["data"]))
    run_id = msg["run_id"]
    bucket = storage.Client().bucket(ARTIFACT_BUCKET)

    train = _read_csv(bucket, msg["train_path"])
    holdout = _read_csv(bucket, msg["holdout_path"])

    challenger = RandomForestRegressor(n_estimators=200, min_samples_leaf=3, random_state=42)
    challenger.fit(train[FEATURES], train[TARGET])
    challenger_mae = _mae(challenger, holdout)
    model_path = f"models/{run_id}/model.joblib"
    _save_model(bucket, challenger, model_path)

    champion_blob = bucket.blob("registry/champion.json")
    champion = json.loads(champion_blob.download_as_text()) if champion_blob.exists() else None

    if champion is None:
        champion_mae, promote = None, True
        reason = "no existing champion"
    elif champion["run_id"] == run_id:
        champion_mae, promote = None, True
        reason = "re-run of the current champion's batch; champion refreshed"
    else:
        # Both models are scored on the SAME new holdout set, so the comparison is fair.
        champion_mae = _mae(_load_model(bucket, champion["model_path"]), holdout)
        required = round(champion_mae * (1 - MIN_IMPROVEMENT), 2)
        promote = challenger_mae <= required
        reason = (f"challenger MAE {challenger_mae} {'<=' if promote else '>'} {required} "
                  f"(champion {champion['run_id']} MAE {champion_mae} minus 2%)")

    record = {
        "run_id": run_id,
        "status": "PROMOTED" if promote else "REJECTED",
        "reason": reason,
        "challenger_mae": challenger_mae,
        "previous_champion": champion["run_id"] if champion else None,
        "previous_champion_mae_on_holdout": champion_mae,
        "model_path": model_path,
        "train_rows": msg["train_rows"],
        "holdout_rows": msg["holdout_rows"],
        "rows_dropped": msg["rows_dropped"],
        "recorded_at": _now(),
    }

    # Update the champion pointer before writing the run record, so anyone who
    # sees the run record also sees the champion that results from it.
    if promote:
        champion_blob.upload_from_string(json.dumps({
            "run_id": run_id, "model_path": model_path,
            "mae": challenger_mae, "promoted_at": record["recorded_at"],
        }, indent=2), content_type="application/json")
    bucket.blob(f"registry/runs/{run_id}.json").upload_from_string(
        json.dumps(record, indent=2), content_type="application/json")

    publisher = pubsub_v1.PublisherClient()
    publisher.publish(publisher.topic_path(PROJECT_ID, EVENTS_TOPIC),
                      json.dumps(record).encode("utf-8"), status=record["status"]).result()

    print(json.dumps({
        "severity": "INFO" if promote else "WARNING",
        "message": f"{run_id}: {record['status']} - {reason}",
        "run_id": run_id, "status": record["status"],
    }))
