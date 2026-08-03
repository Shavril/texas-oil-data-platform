"""Entry point: load the RRC Statewide Production Data (Oil) tape file and print summary stats.

Run from the project root:
    uv run python main.py
"""

import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / "src"))

from oil_pipeline.extract import load_pdf100
from oil_pipeline.load import load_parquet_to_bigquery, run_bigquery_sql, save_parquet, save_tables, upload_to_gcs
from oil_pipeline.transform import VIEW_QUERIES, build_district_lookup_sql, build_view_sql, transform

RAW_DATA_PATH = Path(__file__).parent / "data" / "raw" / "production" / "PDF100.ebc"
DB_PATH = Path(__file__).parent / "data" / "database" / "pdf100.duckdb"
PROCESSED_DATA_PATH = Path(__file__).parent / "data" / "processed"

GCP_PROJECT_ID = "texas-oil-data-platform"
GCS_BUCKET_NAME = "texas-oil-data-platform"
BQ_DATASET = "analytics"


def load_from_raw_to_duckdb() -> Path:
    # Load the files into DuckDB

    results = load_pdf100(RAW_DATA_PATH)

    print()
    print("Record type breakdown:")
    print(results["key_counts"].to_string(index=False))

    print()
    print(f"Root (leases):             {len(results['root']):,}")
    print(f"Reporting Cycle:           {len(results['cycle']):,}")
    print(f"Production:                {len(results['production']):,}")
    print(f"Previous Production Rpt:   {len(results['prev_production']):,}")

    save_tables(results, DB_PATH)
    print()
    print(f"Saved tables to {DB_PATH}")
    return DB_PATH


def transform_duckdb_to_analytics_tables(db_path: Path) -> dict[str, pd.DataFrame]:
    analytics_tables = transform(db_path)

    print()
    for name, df in analytics_tables.items():
        print(f"{name}: {len(df):,} rows")

    save_tables(analytics_tables, db_path)
    print()
    print(f"Saved analytics tables to {db_path}")
    return analytics_tables


def save_analytics_to_parquet(analytics_tables: dict[str, pd.DataFrame]) -> dict[str, Path]:
    parquet_paths = save_parquet(analytics_tables, PROCESSED_DATA_PATH)

    print()
    for name, path in parquet_paths.items():
        print(f"Wrote {name} -> {path}")

    return parquet_paths


def upload_parquet_to_gcs(parquet_paths: dict[str, Path]) -> dict[str, str]:
    gcs_uris = {}
    print()
    for name, path in parquet_paths.items():
        blob_name = f"{name}.parquet"
        upload_to_gcs(path, GCS_BUCKET_NAME, blob_name, project=GCP_PROJECT_ID)
        gcs_uris[name] = f"gs://{GCS_BUCKET_NAME}/{blob_name}"
        print(f"Uploaded {path} -> {gcs_uris[name]}")

    return gcs_uris


def load_gcs_to_bigquery(gcs_uris: dict[str, str]) -> None:
    print()
    for name, gcs_uri in gcs_uris.items():
        load_parquet_to_bigquery(gcs_uri, project=GCP_PROJECT_ID, dataset=BQ_DATASET, table=name)
        print(f"Loaded {gcs_uri} -> {GCP_PROJECT_ID}.{BQ_DATASET}.{name}")


def create_district_lookup_table() -> None:
    sql = build_district_lookup_sql(project=GCP_PROJECT_ID, dataset=BQ_DATASET)
    run_bigquery_sql(sql, project=GCP_PROJECT_ID)
    print()
    print(f"Created {GCP_PROJECT_ID}.{BQ_DATASET}.rrc_districts")


def create_analytics_views() -> None:
    print()
    for view_name in VIEW_QUERIES:
        sql = build_view_sql(GCP_PROJECT_ID, BQ_DATASET, view_name)
        run_bigquery_sql(sql, project=GCP_PROJECT_ID)
        print(f"Created {GCP_PROJECT_ID}.{BQ_DATASET}.{view_name}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Load the files into DuckDB
    db_path = load_from_raw_to_duckdb()

    # Transform into analytics-ready tables
    analytics_tables = transform_duckdb_to_analytics_tables(db_path)

    # Save analytics tables locally as Parquet
    parquet_paths = save_analytics_to_parquet(analytics_tables)

    # Upload the Parquet files to GCS
    gcs_uris = upload_parquet_to_gcs(parquet_paths)

    # Load from GCS into BigQuery
    load_gcs_to_bigquery(gcs_uris)

    # Create/refresh the small static district code/name lookup table
    create_district_lookup_table()

    # Create/refresh the Looker Studio-facing views
    create_analytics_views()


if __name__ == "__main__":
    main()
