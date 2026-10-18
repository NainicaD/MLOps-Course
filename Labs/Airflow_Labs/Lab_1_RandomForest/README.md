# Airflow Lab 1: Diabetes Progression Prediction with a Random Forest

## Overview

This lab uses Apache Airflow, running in Docker, to orchestrate a small machine learning pipeline. The pipeline trains a Random Forest regressor that predicts how much a patient's diabetes progresses over one year, then evaluates it on patients the model has never seen.

The data is the diabetes dataset from scikit-learn: 442 patients with ten baseline measurements (age, sex, BMI, average blood pressure and six blood serum measurements `s1`-`s6`). The target column, `progression`, is a quantitative measure of disease progression one year after baseline.

The pipeline is defined as an Airflow DAG named `Airflow_Lab1_RF` with four tasks that run in sequence:

```
load_data_task >> data_preprocessing_task >> build_save_model_task >> load_model_task
```

| Task | Function | What it does |
|---|---|---|
| `load_data_task` | `load_data()` | Reads `data/file.csv` (376 patients) and passes it on, serialized |
| `data_preprocessing_task` | `data_preprocessing(data)` | Drops missing values, separates features from the target, splits 80/20 into training and validation sets |
| `build_save_model_task` | `build_save_model(data, filename)` | Trains a 200-tree Random Forest for each `max_depth` from 1 to 15, records validation RMSE for each, and saves the best model to `model/model.sav` |
| `load_model_task` | `load_model_evaluate(filename, val_rmse)` | Loads the saved model, reports the best depth, and evaluates it on the 66 held-out patients in `data/test.csv` (RMSE, MAE, R², top features, sample predictions) |

Tasks pass data to each other through Airflow's XCom. Each payload is pickled and base64-encoded so it can be stored as a plain string.

## Project structure

```
Airflow_Lab1_RF/
├── dags/
│   ├── data/
│   │   ├── file.csv        # training + validation data
│   │   └── test.csv        # held-out test patients
│   ├── model/              # model.sav is written here
│   ├── src/
│   │   ├── __init__.py
│   │   └── lab.py          # pipeline functions
│   └── airflow.py          # DAG definition
├── docker-compose.yaml
├── .env
├── .gitignore
└── README.md
```

`logs/`, `plugins/` and `config/` are created during setup and are not committed.

## Prerequisites

- Docker Desktop, running, with at least 4 GB of memory allocated (8 GB recommended) under Settings → Resources
- Port 8080 free on your machine

No Python packages need to be installed locally. Airflow and the pipeline's dependencies run inside the containers.

## Setup

Run all commands from the project root (the folder containing `dags/`).

**1. Download the Airflow Docker Compose file**

```bash
# Mac / Linux
curl -LfO 'https://airflow.apache.org/docs/apache-airflow/2.9.2/docker-compose.yaml'

# Windows
curl -o docker-compose.yaml https://airflow.apache.org/docs/apache-airflow/2.9.2/docker-compose.yaml
```

**2. Create the folders Airflow needs**

```bash
# Mac / Linux
mkdir -p ./logs ./plugins ./config

# Windows (cmd)
mkdir logs plugins config
```

**3. Set the Airflow user**

```bash
# Mac / Linux
echo -e "AIRFLOW_UID=$(id -u)" > .env
```

On Windows, create a file named `.env` containing:

```
AIRFLOW_UID=50000
```

**4. Edit `docker-compose.yaml`**

In the `environment` section of `x-airflow-common`:

```yaml
AIRFLOW__CORE__LOAD_EXAMPLES: 'false'
_PIP_ADDITIONAL_REQUIREMENTS: ${_PIP_ADDITIONAL_REQUIREMENTS:- pandas scikit-learn}
```

In the `airflow-init` service, set the login credentials:

```yaml
_AIRFLOW_WWW_USER_USERNAME: ${_AIRFLOW_WWW_USER_USERNAME:-airflow2}
_AIRFLOW_WWW_USER_PASSWORD: ${_AIRFLOW_WWW_USER_PASSWORD:-airflow2}
```

## Running the pipeline

**1. Initialize the Airflow database** (first run only; takes a few minutes)

```bash
docker compose up airflow-init
```

Wait for `airflow-init-1 exited with code 0`.

**2. Start Airflow**

```bash
docker compose up
```

Leave this terminal running. Airflow is ready when the webserver logs a line containing `GET /health HTTP/1.1" 200`.

**3. Open the UI**

Go to http://localhost:8080 and log in with `airflow2` / `airflow2`.

**4. Trigger the DAG**

Find `Airflow_Lab1_RF` in the DAG list, switch the toggle on, and click ▶ (Trigger DAG).

**5. Stop Airflow when finished**

In a second terminal, from the project root:

```bash
docker compose down
```

## Validating the results in Airflow

**Check the run succeeded**

On the DAG list page, a successful run shows a dark green circle under **Runs** and a green circle with **4** under **Recent Tasks**. **Running** and **Failed** at the top of the page should both read 0. A light green circle means the run is still in progress; red means a task failed.

**Check each task**

Click `Airflow_Lab1_RF` → **Graph**. All four task boxes should have a dark green border (success). Click any box → **Logs** to see its output.

**Check model selection**

Open the logs for `build_save_model_task`. You should see the validation RMSE for every depth:

```
max_depth= 1  validation RMSE=61.16
max_depth= 2  validation RMSE=55.35
max_depth= 3  validation RMSE=54.35
max_depth= 4  validation RMSE=54.65
...
```

Validation error drops sharply up to depth 3 and then slowly rises as deeper trees start to overfit.

**Check the final evaluation**

Open the logs for `load_model_task`:

```
Best max_depth (lowest validation RMSE): 3
Test metrics: {'best_max_depth': 3, 'test_rmse': 56.24, 'test_mae': 45.58, 'test_r2': 0.306}
Top features: s5 (0.56), bmi (0.26), bp (0.06)
```

Exact numbers can vary slightly with the scikit-learn version installed in the container. The target is noisy, so a test R² around 0.3 on 66 patients is expected; `s5` (a blood triglyceride measure) and BMI are the strongest predictors.

**Check data passed between tasks**

Click a task → **XCom**. `build_save_model_task` returns the list of 15 validation RMSE values, and `load_model_task` returns the test metrics dictionary. The earlier tasks return long base64 strings, which are the serialized data.

**Check the saved model**

After a successful run, `dags/model/model.sav` exists in the project folder. The container writes it directly into this folder through the mounted `dags/` directory.

**Check task timing**

The **Gantt** tab shows how long each task took. `build_save_model_task` takes the longest because it trains 15 forests.

## Troubleshooting

| Problem | Fix |
|---|---|
| DAG does not appear | Make sure `airflow.py` is directly inside `dags/` (lowercase) and wait about 30 seconds, then refresh |
| Import error shown at the top of the UI | Click it to read the error; usually a typo in `airflow.py` or `lab.py` |
| `ModuleNotFoundError: sklearn` | Check the `_PIP_ADDITIONAL_REQUIREMENTS` line, then run `docker compose down` and `docker compose up` |
| Port 8080 already in use | Change `"8080:8080"` to `"8081:8080"` in `docker-compose.yaml` and use `localhost:8081` |
| Containers keep restarting | Increase Docker's memory under Settings → Resources |
| `command not found: docker` | Start Docker Desktop and open a new terminal |
