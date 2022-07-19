ARG AIRFLOW_BASE_IMAGE='apache/airflow:2.2.5'
FROM ${AIRFLOW_BASE_IMAGE}

RUN pip install --user --no-cache-dir --upgrade pip

RUN pip install --user --no-cache-dir \
    psycopg2-binary>=2.7.4 \
    apache-airflow-providers-postgres==4.0.0 \
    pandas \
    apache-airflow-providers-amazon==4.0.0