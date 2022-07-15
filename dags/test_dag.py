"""
    Test DAG to know is airflow working properly
"""
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

with DAG(
    dag_id='is_working',
    default_args={
        'depends_on_past': False,
        'email': ['admin@example.com'],
        'email_on_failure': False,
        'email_on_retry': False,
        'retries': 1,
        'retry_delay': timedelta(minutes=5),
    },
    description='A simple DAG',
    schedule_interval=timedelta(days=1),
    start_date=datetime(year=2022, month=5, day=2),
    catchup=False,
    tags=['test'],
    ) as dag:
    
    task_1 = BashOperator(
        task_id='test',
        bash_command='echo ====== IS WORKING! ============'
    )

    task_1