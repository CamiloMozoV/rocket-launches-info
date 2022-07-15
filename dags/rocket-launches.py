from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator

dag = DAG(
    dag_id='rocket-launches-info',
    description='Simple data pipeline for extract information about recently launched rockets.',
    start_date=datetime(2022, 7, 14),
    schedule_interval='@daily'
)


download_launches = BashOperator(
    task_id='download_launches',
    bash_command="curl -o /tmp/launches.json -L 'https://ll.thespacedevs.com/2.0.0/launch/upcoming'",
    dag=dag
)

download_launches