# Lab 1: Monthly Data-Quality Monitoring with TFDV and ML Metadata

## Purpose

In a production ML system, the schema for the training data is defined once, but new data keeps arriving. Every new batch has to be checked before it is used for training: is it valid, has its distribution shifted, and if something looks different, is the data broken or has the world legitimately changed?

Those decisions matter later. When a model misbehaves months afterwards, the team needs to know which batches were accepted, which were rejected and why, and why the schema looks the way it does today. This lab builds a data-monitoring loop that makes those decisions and records every step in an ML Metadata (MLMD) store, so they can be audited from the store alone.

## What the lab does

The lab uses the UCI Bike Sharing dataset (hourly bike rentals in Washington D.C., 2011-2012), split into monthly batches.

1. **Baseline schema.** TFDV infers a schema from January to March 2011 (version 0). The schema is then curated from the dataset's documentation (version 1): value ranges, the full list of weather categories, training and serving environments, and drift thresholds.
2. **Monthly validation.** Each month from April to September 2011 is validated against the current schema and compared with the last accepted month to detect drift.
3. **Decision policy.** Based on TFDV's anomaly reason codes, each batch is:
   - **ACCEPTED**: no anomalies
   - **ACCEPTED_WITH_DRIFT**: valid values, but the distribution moved
   - **REJECTED**: broken data (out-of-range or missing values)
   - **NEEDS_SCHEMA_UPDATE**: a legitimate new value appeared (a new season)
4. **Schema evolution.** When a new season appears (June and September), a new schema version is created and the batch is validated again. Each new version is linked in the store to the anomaly report that triggered it.
5. **Simulated data bug.** August 2011 is corrupted on purpose (temperature sent in Celsius, some windspeed values missing) and should be rejected.
6. **Serving validation.** An October batch without label columns is validated under the training and serving environments.
7. **Audit.** Using only the metadata store, the lab builds a monitoring dashboard, explains why each schema version exists, and lists which batches each schema version validated.

## What gets recorded in the metadata store

| Kind | Name | Purpose |
|---|---|---|
| Artifact | `DataBatch` | A monthly CSV batch, with its final status |
| Artifact | `ExampleStatistics` | TFDV statistics for a batch |
| Artifact | `Schema` | Every schema version, with a content hash |
| Artifact | `ExampleAnomalies` | One validation result and its decision |
| Execution | `GenerateStatistics`, `InferSchema`, `CurateSchema`, `ValidateBatch` | Each step that was run |
| Context | `MonitoringCycle` | Groups everything done for one month |

Events record each artifact's role (`statistics`, `previous_statistics`, `schema`, `trigger`), so lineage queries can tell inputs apart.

## How to run

**Requirements:** Python 3.10, TensorFlow Data Validation (TFDV) and ML Metadata.

1. Create the environment:

```bash
   conda create -n mlmd python=3.10 -y
   conda activate mlmd
   python -m pip install tensorflow-data-validation ml-metadata ipykernel
```

   This was tested with TFDV 1.21.0 on an Apple Silicon Mac.

2. Open this folder in VS Code and open `Lab_Data_Monitoring_MLMD.ipynb`.
3. Click **Select Kernel**, choose **Python Environments**, then **mlmd**.
4. Click **Run All**.

The first run downloads the dataset. All outputs are written inside this folder:

| Folder | Contents |
|---|---|
| `raw/` | Downloaded `hour.csv` |
| `data/batches/` | One CSV per batch |
| `artifacts/` | Statistics, schema versions and anomaly reports |
| `metadata/monitoring.sqlite` | The ML Metadata store |

Re-running the notebook deletes and rebuilds the metadata store, so every run starts clean.

## Outputs

### Monthly batches
![Monthly batches](screenshots/01_batches.png)

### Curated schema (version 1)
![Curated schema](screenshots/02_curated_schema.png)

### Monitoring loop decisions
![Monitoring loop](screenshots/03_monitoring_loop.png)

### Anomalies in the rejected August batch
![Rejected batch anomalies](screenshots/04_rejected_batch_anomalies.png)

### Serving batch validated under each environment
![Serving validation](screenshots/05_serving_validation.png)

### Monitoring dashboard (built from the metadata store)
![Dashboard](screenshots/06_dashboard.png)

### Why each schema version exists
![Schema history](screenshots/07_schema_history.png)

### Batches validated by each schema version
![Schema impact](screenshots/08_schema_impact.png)

## Dataset

Fanaee-T, H. (2013). Bike Sharing [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5W894 (CC BY 4.0).