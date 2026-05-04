import logging
from pathlib import Path

import pandas as pd
from airflow.exceptions import AirflowException
from airflow.providers.sftp.hooks.sftp import SFTPHook


LOGGER = logging.getLogger(__name__)


def upsert_sftp_connection(
    conn_id: str,
    host: str,
    port: int = 22,
    username: str | None = None,
    password: str | None = None,
    extra: dict | None = None,
) -> str:
    """Validate that the connection is resolvable.

    In Airflow 3.0, connections must be defined externally (env vars, secrets
    backend, or the UI) rather than written to the DB from within a task.
    The env var AIRFLOW_CONN_<CONN_ID_UPPER> is the recommended approach and
    is picked up automatically — no DB write is required.
    """
    LOGGER.info(
        "Verifying SFTP connection '%s' is resolvable (expected via AIRFLOW_CONN_%s env var)",
        conn_id,
        conn_id.upper(),
    )
    hook = SFTPHook(ssh_conn_id=conn_id)
    # Accessing the connection property forces resolution; raises if not found.
    _ = hook.get_connection(conn_id)
    LOGGER.info("SFTP connection '%s' resolved successfully", conn_id)
    return conn_id


def validate_sftp_connection(conn_id: str, remote_path: str) -> dict:
    hook = SFTPHook(ssh_conn_id=conn_id)

    if not hook.path_exists(remote_path):
        raise AirflowException(f"Remote path does not exist: {remote_path}")

    LOGGER.info("Validated SFTP connection %s for %s", conn_id, remote_path)
    return {"conn_id": conn_id, "remote_path": remote_path}


def ingest_sftp_file(conn_id: str, remote_path: str, local_directory: str = "/tmp/pre_etl") -> str:
    local_dir = Path(local_directory)
    local_dir.mkdir(parents=True, exist_ok=True)
    local_path = local_dir / Path(remote_path).name

    hook = SFTPHook(ssh_conn_id=conn_id)
    hook.retrieve_file(remote_full_path=remote_path, local_full_path=str(local_path))

    LOGGER.info("Downloaded %s to %s", remote_path, local_path)
    return str(local_path)


def read_csv_file(local_path: str, preview_rows: int = 5) -> dict:
    dataframe = pd.read_csv(local_path)
    preview = dataframe.head(preview_rows).to_dict(orient="records")

    result = {
        "local_path": local_path,
        "row_count": int(len(dataframe.index)),
        "columns": dataframe.columns.tolist(),
        "preview": preview,
    }
    LOGGER.info("Read %s rows from %s", result["row_count"], local_path)
    return result