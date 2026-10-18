# Airflow Lab 1: Predicting Diabetes Progression with a Random Forest

## What this lab does

This lab builds a small machine learning pipeline and runs it with **Apache Airflow**.

The model looks at basic health measurements for a diabetes patient (age, sex, BMI, blood pressure and six blood test results) and predicts how much their disease will progress over the next year. The prediction is a single number called the **progression score**; higher means the disease got worse.

Instead of running the code as one script, Airflow runs it as four separate steps, one after another. Airflow keeps track of which steps succeeded or failed, shows their output in a web interface, and lets you rerun any step on its own.

## Key terms

- **Airflow:** A tool for scheduling and running data pipelines. It runs here inside Docker, so nothing needs to be installed on your computer except Docker.
- **DAG:** The pipeline definition. This lab's DAG is called `Airflow_Lab1_RF` and is defined in `dags/airflow.py`.
- **Task:** One step of the pipeline. Each task calls one Python function from `dags/src/lab.py`.
- **XCom:** How Airflow passes a task's output to the next task.

## The pipeline

The four tasks run in this order:

```
load_data_task → data_preprocessing_task → build_save_model_task → load_model_task
```

1. **Load the data** (`load_data`): Reads 376 patient records from `dags/data/file.csv`.
2. **Prepare the data** (`data_preprocessing`): Removes incomplete rows, separates the measurements from the progression score, and sets aside 20% of the patients as a validation set to compare models fairly.
3. **Train and save the model** (`build_save_model`): Trains 15 Random Forest models, each allowed to grow trees of a different depth (1 to 15). It checks each one on the validation set and saves the most accurate one as `dags/model/model.sav`.
4. **Evaluate the model** (`load_model_evaluate`): Loads the saved model and tests it on 66 patients in `dags/data/test.csv` that it has never seen, then reports how accurate it was and which measurements mattered most.

## Folder contents

```
Lab_1_RandomForest/
├── dags/
│   ├── airflow.py        # defines the pipeline (DAG) and the order of tasks
│   ├── src/
│   │   ├── __init__.py
│   │   └── lab.py        # the Python code for each of the four steps
│   ├── data/
│   │   ├── file.csv      # patients used for training and validation
│   │   └── test.csv      # patients used only for the final test
│   └── model/            # the trained model is saved here
├── docker-compose.yaml   # starts Airflow in Docker (already configured)
├── .gitignore
└── README.md
```

`docker-compose.yaml` is already set up for this lab: example DAGs are turned off, `pandas` and `scikit-learn` are installed automatically, and the login is `airflow2` / `airflow2`.

## Before you start

- Install **Docker Desktop** and open it. Wait until it shows that Docker is running.
- In Docker Desktop → Settings → Resources, give Docker at least **4 GB** of memory (8 GB is better).
- Make sure nothing else is using port **8080** (for example, another Airflow lab that is still running).

## How to run it

All commands are run in a terminal. On Windows, use Git Bash so the same commands work.

**Step 1. Download the repo and go to this lab's folder**

```bash
git clone https://github.com/NainicaD/MLOps-course.git
cd MLOps-course/Labs/Airflow_Labs/Lab_1_RandomForest
```

**Step 2. Create the folders and settings file Airflow needs**

```bash
mkdir -p ./logs ./plugins ./config
echo -e "AIRFLOW_UID=$(id -u)" > .env
```

On Windows, if the second command fails, create a file named `.env` in this folder containing `AIRFLOW_UID=50000`.

**Step 3. Set up Airflow** (first time only, takes a few minutes)

```bash
docker compose up airflow-init
```

Wait until the output ends with `airflow-init-1 exited with code 0`.

**Step 4. Start Airflow**

```bash
docker compose up
```

Keep this terminal open; Airflow stops if you close it. Airflow is ready when you see a line containing `GET /health HTTP/1.1" 200`.

**Step 5. Open Airflow and run the pipeline**

1. Go to http://localhost:8080 and log in with username `airflow2` and password `airflow2`.
2. Find `Airflow_Lab1_RF` in the list. If it isn't there yet, wait 30 seconds and refresh.
3. Click the switch on the left of the DAG name to turn it on.
4. Click the ▶ button on the right to start a run.

**Step 6. Stop Airflow when you are done**

Open a second terminal in the same folder and run:

```bash
docker compose down
```

## How to check that it worked

**1. The run finished successfully**

On the main DAG list, look at the `Airflow_Lab1_RF` row:

| What you see | What it means |
|---|---|
| Light green circle under **Runs** | Still running; wait a minute |
| Dark green circle under **Runs**, and **4** in a green circle under **Recent Tasks** | All four tasks succeeded |
| Red circle | A task failed (see Troubleshooting) |

**2. All four steps are green**

Click `Airflow_Lab1_RF`, then the **Graph** tab. All four boxes should have a dark green border.

**3. The model comparison makes sense**

Click the `build_save_model_task` box → **Logs**. You should see one line per tree depth:

```
max_depth= 1  validation RMSE=61.16
max_depth= 2  validation RMSE=55.35
max_depth= 3  validation RMSE=54.35
max_depth= 4  validation RMSE=54.65
...
```

**RMSE** is the typical size of the model's error, in progression-score points; lower is better. The error drops until depth 3 and then slowly rises. Deeper trees start memorizing the training patients instead of learning general patterns (overfitting), so depth 3 is chosen.

**4. The final test results**

Click the `load_model_task` box → **Logs**:

```
Best max_depth (lowest validation RMSE): 3
Test metrics: {'best_max_depth': 3, 'test_rmse': 56.24, 'test_mae': 45.58, 'test_r2': 0.306}
Top features: s5 (0.56), bmi (0.26), bp (0.06)
```

How to read this:

- **test_rmse (about 56)** and **test_mae (about 46):** On new patients, predictions are typically off by about 45 to 55 points. Progression scores in the data range from roughly 25 to 346.
- **test_r2 (about 0.31):** The model explains about 31% of the differences in progression between patients. That is modest, which is expected: these ten measurements only partly predict how the disease develops.
- **Top features:** `s5` (a blood triglyceride measure) and `bmi` drive most of the predictions. The numbers show each feature's share of importance.

Your numbers may differ slightly depending on the scikit-learn version installed in Docker.

**5. The model file was saved**

In this folder on your computer, `dags/model/model.sav` should now exist.

**Optional checks in the Airflow UI**

- **Gantt** tab: Shows how long each task took. Training (`build_save_model_task`) is the slowest because it trains 15 models.
- Click any task → **XCom**: Shows what that task passed to the next one. `build_save_model_task` passes the list of 15 RMSE values, and `load_model_task` returns the final metrics.

## Troubleshooting

| Problem | What to do |
|---|---|
| `command not found: docker` | Open Docker Desktop, wait for it to start, then open a new terminal |
| The DAG doesn't appear in the list | Wait 30 seconds and refresh. Check that `airflow.py` is directly inside the `dags` folder |
| A red error banner appears at the top of the Airflow page | Click it to read the error. It usually points to a typo in `airflow.py` or `lab.py` |
| `ModuleNotFoundError: sklearn` in a task log | Run `docker compose down`, then `docker compose up` again so the packages reinstall |
| `port is already allocated` | Another program (often another Airflow lab) is using port 8080. Stop it with `docker compose down` in that folder |
| Containers keep restarting | Give Docker more memory in Docker Desktop → Settings → Resources |
| A task is red | Click the task → **Logs**, scroll to the bottom, and read the error message |
