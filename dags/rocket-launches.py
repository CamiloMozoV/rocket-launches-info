import json
from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
import pandas as pd

dag = DAG(
    dag_id='rocket-launches-info',
    description='Simple data pipeline for extract information about recently launched rockets.',
    start_date=datetime(2022, 7, 14),
    schedule_interval='@daily'
)

def _extract_basic_info(read_path: str, output_path: str) -> None:
    """Extract the basic information about rocket launches.
    
    parameter:
    read_path [str]: path to the file from which the information is to 
                     be extrated.
    output_path [str]: the path where the data of interest will
                       be saved.
    """

    info = {
        'service_provider_name': [],
        'service_provider_type': [],
        'slug': [],
        'rocket_full_name': [],
        'window_start': [],
        'window_end': []
    }

    with open(read_path, 'r') as file:
        launches = json.load(file)
        
        for launche in launches['results']:
            try:
                info['service_provider_name'].append(launche['launch_service_provider']['name'])
                info['service_provider_type'].append(launche['launch_service_provider']['type'])
                info['slug'].append(launche['slug'])
                info['rocket_full_name'].append(launche['rocket']['configuration']['full_name'])
                info['window_start'].append(launche['window_start'])
                info['window_end'].append(launche['window_end'])
            except TypeError as e:
                print('= = =' * 20)
                print(e)
                print('= = =' * 20)

        pd.DataFrame(data=info).to_csv(output_path, index=False)


download_launches = BashOperator(
    task_id='download_launches',
    bash_command="curl -o /tmp/launches.json -L 'https://ll.thespacedevs.com/2.0.0/launch/upcoming'",
    dag=dag
)

extract_basic_info = PythonOperator(
    task_id='extract_basic_info',
    python_callable=_extract_basic_info,
    op_kwargs={
        'read_path': '/tmp/launches.json',
        'output_path': '/tmp/basic_rocket_info.csv'
    },
    dag=dag
)

download_launches >> extract_basic_info