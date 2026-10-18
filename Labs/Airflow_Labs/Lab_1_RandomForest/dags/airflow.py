# Import necessary libraries and modules
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
from src.lab import load_data, data_preprocessing, build_save_model, load_model_evaluate

# Define default arguments for your DAG
default_args = {
    'owner': 'Nainica',
    'start_date': datetime(2026, 10, 1),
    'retries': 0,  # Number of retries in case of task failure
    'retry_delay': timedelta(minutes=5),  # Delay before retries
}

# Create a DAG instance named 'Airflow_Lab1_RF' with the defined default arguments
dag = DAG(
    'Airflow_Lab1_RF',
    default_args=default_args,
    description='Diabetes progression prediction with a Random Forest; max_depth chosen on validation RMSE',
    schedule_interval=None,  # Manual triggering
    catchup=False,
)

# Task to load data, calls the 'load_data' Python function
load_data_task = PythonOperator(
    task_id='load_data_task',
    python_callable=load_data,
    dag=dag,
)

# Task to perform data preprocessing, depends on 'load_data_task'
data_preprocessing_task = PythonOperator(
    task_id='data_preprocessing_task',
    python_callable=data_preprocessing,
    op_args=[load_data_task.output],
    dag=dag,
)

# Task to build and save a model, depends on 'data_preprocessing_task'
build_save_model_task = PythonOperator(
    task_id='build_save_model_task',
    python_callable=build_save_model,
    op_args=[data_preprocessing_task.output, "model.sav"],
    dag=dag,
)

# Task to load the model and evaluate it on test data, depends on 'build_save_model_task'
load_model_task = PythonOperator(
    task_id='load_model_task',
    python_callable=load_model_evaluate,
    op_args=["model.sav", build_save_model_task.output],
    dag=dag,
)

# Set task dependencies
load_data_task >> data_preprocessing_task >> build_save_model_task >> load_model_task

# If this script is run directly, allow command-line interaction with the DAG
if __name__ == "__main__":
    dag.cli()
