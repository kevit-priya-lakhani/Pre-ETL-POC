FROM apache/airflow:3.0.0-python3.12

COPY requirements.txt /tmp/requirements.txt

RUN pip install --no-cache-dir apache-airflow-providers-google -r /tmp/requirements.txt