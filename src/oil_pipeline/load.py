"""Persist parsed RRC production DataFrames into DuckDB, Parquet, GCS, and BigQuery.

Physical database/Parquet files live under data/database/ and data/processed/
(excluded from git, see .gitignore), consistent with CLAUDE.md's "Development:
Parquet files, DuckDB" storage guidance.
"""

import logging
from pathlib import Path

import duckdb
import pandas as pd
from google.cloud import bigquery, storage

logger = logging.getLogger(__name__)


def save_tables(tables: dict[str, pd.DataFrame], db_path: Path) -> None:
    """Write each DataFrame in `tables` as a table in a DuckDB database file.

    Each table is replaced wholesale (CREATE OR REPLACE) — this is a full
    reload, not an incremental upsert.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    with duckdb.connect(str(db_path)) as con:
        for name, df in tables.items():
            con.register("_incoming", df)
            con.execute(f'CREATE OR REPLACE TABLE "{name}" AS SELECT * FROM _incoming')
            con.unregister("_incoming")
            logger.info("Wrote table %r (%s rows) to %s", name, f"{len(df):,}", db_path)


def save_parquet(tables: dict[str, pd.DataFrame], processed_dir: Path) -> dict[str, Path]:
    """Write each DataFrame in `tables` to its own Parquet file under processed_dir.

    Returns a dict mapping table name to the Parquet file path written.
    """
    processed_dir.mkdir(parents=True, exist_ok=True)

    paths = {}
    for name, df in tables.items():
        path = processed_dir / f"{name}.parquet"
        df.to_parquet(path, index=False)
        paths[name] = path
        logger.info("Wrote %s rows to %s", f"{len(df):,}", path)

    return paths


def upload_to_gcs(local_path: Path, bucket_name: str, blob_name: str, project: str | None = None) -> None:
    """Upload a local file to a GCS bucket, overwriting any existing object at blob_name."""
    client = storage.Client(project=project)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(str(local_path))
    logger.info("Uploaded %s to gs://%s/%s", local_path, bucket_name, blob_name)


def load_parquet_to_bigquery(gcs_uri: str, project: str, dataset: str, table: str) -> None:
    """Load a Parquet file from GCS into a BigQuery table.

    The table is replaced wholesale (WRITE_TRUNCATE) — this is a full
    reload, not an incremental upsert. The dataset must already exist.
    """
    client = bigquery.Client(project=project)
    table_ref = f"{project}.{dataset}.{table}"
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    load_job = client.load_table_from_uri(gcs_uri, table_ref, job_config=job_config)
    load_job.result()

    destination = client.get_table(table_ref)
    logger.info("Loaded %s rows into %s from %s", f"{destination.num_rows:,}", table_ref, gcs_uri)
