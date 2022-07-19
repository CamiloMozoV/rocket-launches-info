import json
import pathlib
import logging
import requests
import requests.exceptions as requests_exceptions
from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.amazon.aws.operators.s3 import S3CreateBucketOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
import pandas as pd

dag = DAG(
    dag_id='rocket-launches-info',
    description='Simple data pipeline for extract information about recently launched rockets.',
    start_date=datetime(2022, 7, 18),
    schedule_interval='@daily',
    catchup=False,
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

def _get_pictures(read_path: str, output_path: str) -> None:
    """Downloads the respective images of each of the rocket launches.

    parameter:
    read_path [str]: the path to the file from which the image urls is to 
                     be extrated.
    output_path [str]: the path where the images will be saved.
    """
    pathlib.Path(output_path).mkdir(parents=True, exist_ok=True)

    with open(read_path, 'r') as file:
        launches = json.load(file)
        image_urls = [launche['image'] for launche in launches['results']]
        iterator = 0

        for image_url in image_urls:
            try:
                response = requests.get(image_url)
                image_filename = launches['results'][iterator]['slug']
                target_file = f"{output_path}/{image_filename}.png"

                with open(target_file, 'wb') as file:
                    file.write(response.content)

                logging.info(f"= = = Downloaded {image_url} ---> {target_file} = = =")
                iterator+=1
            except requests_exceptions.MissingSchema:
                logging.info(f"= = = {image_url} appears to be an invalid URL = = =")
        
def _write_postgres(read_path: str) -> None:
    """Stores the information of interest in the database.
    
    parameter:
    read_path [str]: the path to the file where the information of interest was stored.
    """
    df = pd.read_csv(read_path)
    hook = PostgresHook(postgres_conn_id='postgres_conn_id')
    conn = hook.get_conn()
    cursor = conn.cursor()

    for row in df.itertuples():
        cursor.execute(f"INSERT INTO launches_info VALUES("
                       f"'{row.service_provider_name}', '{row.service_provider_type}', '{row.slug}', "
                       f"'{row.rocket_full_name}', '{row.window_start}', '{row.window_end}'"
                       ");")
    cursor.close()
    conn.commit()

def _upload_info_s3(read_path: str, execution_date) -> None:
    """Upload the information in CSV format to S3.

    parameter:
    read_path [str]: the path to the file where the information of interest was stored.
    execution_date: context variable of the airflow task.
    """

    year, month, day, *_ = execution_date.timetuple()
    s3_hook = S3Hook(aws_conn_id='minio_conn_id')
    s3_hook.load_file(
        filename=read_path,
        key=f'rocket_launches_info/{year}-{month:0>2}-{day:0>2}.csv',
        bucket_name='rocket-info',
        replace=True
    )
    logging.info(f"= = = Rocket launches info <rocket_launches_info/{year}-{month:0>2}-{day:0>2}.csv> has been pushed to S3.")

download_launches = BashOperator(
    task_id='download_info_launches',
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

get_pictures = PythonOperator(
    task_id='get_rocket_pictures',
    python_callable=_get_pictures,
    op_kwargs={
        'read_path': '/tmp/launches.json',
        'output_path': '/tmp/images'
    },
    dag=dag
)

write_postgres = PythonOperator(
    task_id='write_postgres',
    python_callable=_write_postgres,
    op_kwargs={
        'read_path': '/tmp/basic_rocket_info.csv'
    },
    dag=dag
)

create_infoBucket = S3CreateBucketOperator(
    task_id='create_infobucket',
    bucket_name='rocket-info',
    aws_conn_id='minio_conn_id',
    dag=dag
)

create_imageBucket = S3CreateBucketOperator(
    task_id='create_imagebucket',
    bucket_name='rocket-images',
    aws_conn_id='minio_conn_id',
    dag=dag
)

upload_info_s3 = PythonOperator(
    task_id='upload_info_s3',
    python_callable=_upload_info_s3,
    op_kwargs={
        'read_path': '/tmp/basic_rocket_info.csv',
    },
    dag=dag
)

download_launches >> [extract_basic_info, get_pictures]
extract_basic_info >> [create_infoBucket, write_postgres]

get_pictures >> create_imageBucket

create_infoBucket >> upload_info_s3