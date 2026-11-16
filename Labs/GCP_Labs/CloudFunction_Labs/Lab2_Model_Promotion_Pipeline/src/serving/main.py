"""Stage 3: serve predictions from the current champion and expose the run registry."""
import json
import os
import tempfile

import functions_framework
import joblib
import pandas as pd
from google.cloud import storage

ARTIFACT_BUCKET = os.environ.get("ARTIFACT_BUCKET", "")
FEATURES = ["season", "temp", "humidity", "windspeed", "workingday"]

_client = None
_cache = {"run_id": None, "model": None}


def _storage():
    global _client
    if _client is None:
        _client = storage.Client()
    return _client


def _champion(bucket):
    blob = bucket.blob("registry/champion.json")
    return json.loads(blob.download_as_text()) if blob.exists() else None


def _champion_model(bucket, champion):
    """Load the champion model, reusing the cached copy unless a new champion was promoted."""
    if _cache["run_id"] != champion["run_id"]:
        with tempfile.NamedTemporaryFile(suffix=".joblib") as tmp:
            bucket.blob(champion["model_path"]).download_to_filename(tmp.name)
            _cache["model"] = joblib.load(tmp.name)
        _cache["run_id"] = champion["run_id"]
    return _cache["model"]


@functions_framework.http
def serve(request):
    bucket = _storage().bucket(ARTIFACT_BUCKET)

    if request.method == "GET":
        run_id = request.args.get("run_id")
        if run_id:
            blob = bucket.blob(f"registry/runs/{run_id}.json")
            if not blob.exists():
                return {"run_id": run_id, "status": "pending"}, 200
            return json.loads(blob.download_as_text()), 200

        runs = [json.loads(b.download_as_text())
                for b in _storage().list_blobs(ARTIFACT_BUCKET, prefix="registry/runs/")]
        runs.sort(key=lambda r: r["recorded_at"])
        history = [{k: r.get(k) for k in ("run_id", "status", "challenger_mae",
                                           "previous_champion_mae_on_holdout")} for r in runs]
        return {"champion": _champion(bucket), "runs": history}, 200

    if request.method == "POST":
        body = request.get_json(silent=True) or {}
        instances = body.get("instances")
        if not isinstance(instances, list) or not instances:
            return {"error": "body must be {\"instances\": [{...}, ...]}"}, 400
        missing = sorted({f for inst in instances for f in FEATURES if f not in inst})
        if missing:
            return {"error": f"missing features: {missing}"}, 400

        champion = _champion(bucket)
        if champion is None:
            return {"error": "no champion model has been promoted yet"}, 503
        model = _champion_model(bucket, champion)
        preds = model.predict(pd.DataFrame(instances)[FEATURES])
        return {"model_run_id": champion["run_id"],
                "predictions": [int(round(p)) for p in preds]}, 200

    return {"error": "method not allowed"}, 405
