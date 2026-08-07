"""Entry point: load the RRC Statewide Production Data (Oil) tape file and print summary stats.

Run from the project root:
    uv run python main.py
"""

import logging
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / "src"))

from oil_pipeline.config import get_settings
from oil_pipeline.extract.p4_operators import load_p4f606
from oil_pipeline.extract.p5_organizations import load_orf850
from oil_pipeline.extract.production import load_pdf100
from oil_pipeline.extract.wells import load_dbf900
from oil_pipeline.load.bigquery import load_parquet_to_bigquery, run_bigquery_sql
from oil_pipeline.load.duckdb import save_tables
from oil_pipeline.load.gcs import upload_to_gcs
from oil_pipeline.load.parquet import save_parquet
from oil_pipeline.transform.districts import build_district_lookup_sql
from oil_pipeline.transform.lease_operators import build_lease_operators
from oil_pipeline.transform.oil_production import build_oil_production
from oil_pipeline.transform.views import VIEW_DEFINITIONS, build_view_sql
from oil_pipeline.transform.wells import build_wells
from oil_pipeline.validation.raw import (
    validate_p4_raw,
    validate_p5_raw,
    validate_production_raw,
    validate_wells_raw,
)
from oil_pipeline.validation.transformed import (
    validate_lease_operators,
    validate_oil_production,
    validate_wells,
)

settings = get_settings()

RAW_DATA_PATH = settings.raw_production_path
P4_DATA_PATH = settings.raw_p4_path
P5_DATA_PATH = settings.raw_p5_path
WELLS_DATA_PATH = settings.raw_wells_path
DB_PATH = settings.db_path
PROCESSED_DATA_PATH = settings.processed_data_path

GCP_PROJECT_ID = settings.gcp_project_id
GCS_BUCKET_NAME = settings.gcs_bucket_name
BQ_DATASET = settings.bq_dataset


def load_from_raw_to_duckdb() -> Path:
    # Load the files into DuckDB

    results = validate_production_raw(load_pdf100(RAW_DATA_PATH))

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


def load_p4_to_duckdb() -> None:
    p4_results = validate_p4_raw(load_p4f606(P4_DATA_PATH))
    print()
    print(f"P4 Root (oil + gas leases): {len(p4_results['root']):,}")
    save_tables({"p4_root": p4_results["root"]}, DB_PATH)
    print(f"Saved p4_root table to {DB_PATH}")


def load_p5_to_duckdb() -> None:
    p5_results = validate_p5_raw(load_orf850(P5_DATA_PATH))
    print()
    print(f"P5 Organizations:           {len(p5_results['organizations']):,}")
    save_tables({"p5_organizations": p5_results["organizations"]}, DB_PATH)
    print(f"Saved p5_organizations table to {DB_PATH}")


def load_wells_to_duckdb() -> None:
    wells_results = validate_wells_raw(load_dbf900(WELLS_DATA_PATH))
    print()
    print(f"Wells Root:               {len(wells_results['root']):,}")
    print(f"Wells Completion:         {len(wells_results['completion']):,}")
    print(f"Wells New Location:       {len(wells_results['new_location']):,}")
    save_tables(
        {
            "wells_root": wells_results["root"],
            "wells_completion": wells_results["completion"],
            "wells_new_location": wells_results["new_location"],
        },
        DB_PATH,
    )
    print(f"Saved wells_root, wells_completion, and wells_new_location tables to {DB_PATH}")


def transform_oil_production(db_path: Path) -> pd.DataFrame:
    df = validate_oil_production(build_oil_production(db_path))
    print()
    print(f"oil_production: {len(df):,} rows")
    save_tables({"oil_production": df}, db_path)
    print(f"Saved oil_production table to {db_path}")
    return df


def transform_lease_operators(db_path: Path) -> pd.DataFrame:
    df = validate_lease_operators(build_lease_operators(db_path))
    print()
    print(f"lease_operators: {len(df):,} rows")
    save_tables({"lease_operators": df}, db_path)
    print(f"Saved lease_operators table to {db_path}")
    return df


def transform_wells(db_path: Path) -> pd.DataFrame:
    df = validate_wells(build_wells(db_path))
    print()
    print(f"wells: {len(df):,} rows")
    save_tables({"wells": df}, db_path)
    print(f"Saved wells table to {db_path}")
    return df


def save_oil_production_to_parquet(df: pd.DataFrame) -> Path:
    paths = save_parquet({"oil_production": df}, PROCESSED_DATA_PATH)
    print()
    print(f"Wrote oil_production -> {paths['oil_production']}")
    return paths["oil_production"]


def save_lease_operators_to_parquet(df: pd.DataFrame) -> Path:
    paths = save_parquet({"lease_operators": df}, PROCESSED_DATA_PATH)
    print()
    print(f"Wrote lease_operators -> {paths['lease_operators']}")
    return paths["lease_operators"]


def save_wells_to_parquet(df: pd.DataFrame) -> Path:
    paths = save_parquet({"wells": df}, PROCESSED_DATA_PATH)
    print()
    print(f"Wrote wells -> {paths['wells']}")
    return paths["wells"]


def upload_oil_production_to_gcs(path: Path) -> str:
    blob_name = "oil_production.parquet"
    upload_to_gcs(path, GCS_BUCKET_NAME, blob_name, project=GCP_PROJECT_ID)
    gcs_uri = f"gs://{GCS_BUCKET_NAME}/{blob_name}"
    print()
    print(f"Uploaded {path} -> {gcs_uri}")
    return gcs_uri


def upload_lease_operators_to_gcs(path: Path) -> str:
    blob_name = "lease_operators.parquet"
    upload_to_gcs(path, GCS_BUCKET_NAME, blob_name, project=GCP_PROJECT_ID)
    gcs_uri = f"gs://{GCS_BUCKET_NAME}/{blob_name}"
    print()
    print(f"Uploaded {path} -> {gcs_uri}")
    return gcs_uri


def upload_wells_to_gcs(path: Path) -> str:
    blob_name = "wells.parquet"
    upload_to_gcs(path, GCS_BUCKET_NAME, blob_name, project=GCP_PROJECT_ID)
    gcs_uri = f"gs://{GCS_BUCKET_NAME}/{blob_name}"
    print()
    print(f"Uploaded {path} -> {gcs_uri}")
    return gcs_uri


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
    for view_name in VIEW_DEFINITIONS:
        sql = build_view_sql(GCP_PROJECT_ID, BQ_DATASET, view_name)
        run_bigquery_sql(sql, project=GCP_PROJECT_ID)
        print(f"Created {GCP_PROJECT_ID}.{BQ_DATASET}.{view_name}")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Load the oil production raw data into DuckDB
    db_path = load_from_raw_to_duckdb()
    # Load P-4 operator raw data into DuckDB
    load_p4_to_duckdb()
    # Load P-5 organization raw data into DuckDB
    load_p5_to_duckdb()
    # Load wells raw data into DuckDB
    load_wells_to_duckdb()

    # Transform into analytics-ready tables
    oil_production_df = transform_oil_production(db_path)
    lease_operators_df = transform_lease_operators(db_path)
    wells_df = transform_wells(db_path)

    # Save analytics tables locally as Parquet
    oil_production_parquet_path = save_oil_production_to_parquet(oil_production_df)
    lease_operators_parquet_path = save_lease_operators_to_parquet(lease_operators_df)
    wells_parquet_path = save_wells_to_parquet(wells_df)

    # Upload the Parquet files to GCS
    oil_production_gcs_uri = upload_oil_production_to_gcs(oil_production_parquet_path)
    lease_operators_gcs_uri = upload_lease_operators_to_gcs(lease_operators_parquet_path)
    wells_gcs_uri = upload_wells_to_gcs(wells_parquet_path)

    # Load from GCS into BigQuery
    load_gcs_to_bigquery({
        "oil_production": oil_production_gcs_uri,
        "lease_operators": lease_operators_gcs_uri,
        "wells": wells_gcs_uri,
    })

    # Create/refresh the small static district code/name lookup table
    create_district_lookup_table()

    # Create/refresh the Looker Studio-facing views
    create_analytics_views()


if __name__ == "__main__":
    main()
