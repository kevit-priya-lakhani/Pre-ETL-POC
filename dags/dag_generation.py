# keep import to ensure the dag processor parses this file
from airflow.sdk import dag  # noqa: F401
from dagfactory import load_yaml_dags

load_yaml_dags(globals_dict=globals())
