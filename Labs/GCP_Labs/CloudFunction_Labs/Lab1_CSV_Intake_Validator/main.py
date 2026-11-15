"""Cloud Functions: validate uploaded CSV batches and serve their reports."""
import json
import os
from datetime import datetime, timezone

import functions_framework
from google.cloud import storage

from validator import validate_csv

RESULTS_BUCKET = os.environ.get("RESULTS_BUCKET", "")
_client = None


def _storage():
    global _client
    if _client is None:
        _client = storage.Client()
    return _client


def _report_path(name):
    return f"reports/{name[:-4] if name.lower().endswith('.csv') else name}.json"


@functions_framework.cloud_event
def validate_upload(cloud_event):
    """Triggered when an object is finalized in the intake bucket."""
    data = cloud_event.data
    bucket_name, name = data["bucket"], data["name"]
    if not name.lower().endswith(".csv"):
        print(json.dumps({"severity": "INFO", "message": f"skipping non-CSV object {name}"}))
        return

    client = _storage()
    src_bucket = client.bucket(bucket_name)
    blob = src_bucket.blob(name)
    report = validate_csv(blob.download_as_text())
    report.update({
        "file": name,
        "source_bucket": bucket_name,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    })

    results = client.bucket(RESULTS_BUCKET)
    folder = "accepted" if report["status"] == "ACCEPTED" else "quarantine"
    src_bucket.copy_blob(blob, results, f"{folder}/{name}")
    results.blob(_report_path(name)).upload_from_string(
        json.dumps(report, indent=2), content_type="application/json"
    )

    print(json.dumps({
        "severity": "INFO" if folder == "accepted" else "WARNING",
        "message": f"{name}: {report['status']} ({report['error_count']} errors)",
        "file": name,
        "status": report["status"],
        "rows": report["rows"],
    }))


@functions_framework.http
def batch_status(request):
    """GET ?file=<name>.csv returns one report; with no file param, a summary of all batches."""
    bucket = _storage().bucket(RESULTS_BUCKET)
    file = request.args.get("file")

    if file:
        blob = bucket.blob(_report_path(file))
        if not blob.exists():
            return {"error": f"no report for {file}"}, 404
        return json.loads(blob.download_as_text()), 200

    batches = []
    for blob in _storage().list_blobs(RESULTS_BUCKET, prefix="reports/"):
        r = json.loads(blob.download_as_text())
        batches.append({k: r[k] for k in ("file", "status", "rows", "error_count", "checked_at")})
    batches.sort(key=lambda b: b["checked_at"])
    return {
        "total": len(batches),
        "accepted": sum(b["status"] == "ACCEPTED" for b in batches),
        "rejected": sum(b["status"] == "REJECTED" for b in batches),
        "batches": batches,
    }, 200
