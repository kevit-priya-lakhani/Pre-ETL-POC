import json
import logging
from pathlib import Path

import pandas as pd
from airflow import settings
from airflow.exceptions import AirflowException
from airflow.providers.sftp.hooks.sftp import SFTPHook

try:
    from airflow.models.connection import Connection
except ImportError:
    from airflow.models import Connection


LOGGER = logging.getLogger(__name__)


def upsert_sftp_connection(
    conn_id: str,
    host: str,
    port: int = 22,
    username: str | None = None,
    password: str | None = None,
    extra: dict | None = None,
) -> str:
    session = settings.Session()
    extra_json = json.dumps(extra or {})

    try:
        connection = session.query(Connection).filter(Connection.conn_id == conn_id).one_or_none()

        if connection is None:
            connection = Connection(
                conn_id=conn_id,
                conn_type="sftp",
                host=host,
                port=port,
                login=username,
                password=password,
                extra=extra_json,
            )
            session.add(connection)
            action = "created"
        else:
            connection.conn_type = "sftp"
            connection.host = host
            connection.port = port
            connection.login = username
            connection.password = password
            connection.extra = extra_json
            action = "updated"

        session.commit()
        LOGGER.info("SFTP connection %s %s", conn_id, action)
        return conn_id
    finally:
        session.close()


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