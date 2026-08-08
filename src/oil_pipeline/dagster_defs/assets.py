"""Data pipeline assets: extract/validate -> DuckDB -> transform/validate ->
Parquet -> GCS -> BigQuery tables. (Analytics views live in view_assets.py
-- a separate, growing file of BigQuery-warehouse-facing view assets, kept
apart from this data-flow file to avoid clutter.)

Each asset's body is the pipeline logic itself (extract/validate, transform/
validate, save, upload, load), not a delegate call elsewhere. main.py stays
in sync with Dagster because it imports and calls these same
@asset-decorated functions directly -- Dagster supports invoking them as
plain Python functions outside of a run (arguments passed straight through,
no execution context needed), so there's exactly one copy of this logic to
maintain, not two.

production_raw/p4_raw/p5_raw/wells_raw have no dependency edges between
them -- they aren't data-dependent, just four writers to the same
analytics.duckdb file (DuckDB allows only one writer at a time). This is
safe only because dagster_defs.definitions.all_assets_job pins
in_process_executor, which runs steps one at a time regardless of the
dependency graph (verified empirically, not just assumed). If the
executor ever changes to something that runs independent steps in
parallel (e.g. the default multiprocess_executor), these four would need
real serialization again -- a Dagster concurrency-key/pool, not a fake
`deps=` edge.
"""

from pathlib import Path

import pandas as pd
from dagster import asset

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


@asset(
    group_name="raw",
)
def production_raw() -> Path:
    """Load the oil production raw data from PDF100.ebc
    into DuckDB tables root/cycle/production/prev_production/key_counts
    """
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


@asset(
    group_name="raw",
)
def p4_raw() -> None:
    """Load P-4 operator raw data from p4f606.ebc
    into DuckDB table p4_root
    """
    p4_results = validate_p4_raw(load_p4f606(P4_DATA_PATH))
    print()
    print(f"P4 Root (oil + gas leases): {len(p4_results['root']):,}")
    save_tables({"p4_root": p4_results["root"]}, DB_PATH)
    print(f"Saved p4_root table to {DB_PATH}")


@asset(
    group_name="raw",
)
def p5_raw() -> None:
    """Load P-5 organization raw data from orf850.ebc
    into DuckDB table p5_organizations
    """
    p5_results = validate_p5_raw(load_orf850(P5_DATA_PATH))
    print()
    print(f"P5 Organizations:           {len(p5_results['organizations']):,}")
    save_tables({"p5_organizations": p5_results["organizations"]}, DB_PATH)
    print(f"Saved p5_organizations table to {DB_PATH}")


@asset(
    group_name="raw",
)
def wells_raw() -> None:
    """Load wells raw data from dbf900.ebc into
    DuckDB tables wells_root/wells_completion/wells_new_location
    """
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


@asset(
    group_name="duck_db_analytics",
    deps=[production_raw],
)
def oil_production() -> pd.DataFrame:
    """DuckDB table oil_production: one row per lease per reporting month."""
    df = validate_oil_production(build_oil_production(DB_PATH))
    print()
    print(f"oil_production: {len(df):,} rows")
    save_tables({"oil_production": df}, DB_PATH)
    print(f"Saved oil_production table to {DB_PATH}")
    return df


@asset(
    group_name="duck_db_analytics",
    deps=[p4_raw, p5_raw],
)
def lease_operators() -> pd.DataFrame:
    """DuckDB table lease_operators: one row per oil lease."""
    df = validate_lease_operators(build_lease_operators(DB_PATH))
    print()
    print(f"lease_operators: {len(df):,} rows")
    save_tables({"lease_operators": df}, DB_PATH)
    print(f"Saved lease_operators table to {DB_PATH}")
    return df


@asset(
    group_name="duck_db_analytics",
    deps=[wells_raw],
)
def wells() -> pd.DataFrame:
    """DuckDB table wells: one row per oil well."""
    df = validate_wells(build_wells(DB_PATH))
    print()
    print(f"wells: {len(df):,} rows")
    save_tables({"wells": df}, DB_PATH)
    print(f"Saved wells table to {DB_PATH}")
    return df


@asset(
    group_name="parquet_local_files",
)
def oil_production_parquet(oil_production: pd.DataFrame) -> Path:
    """Save analytics table locally as Parquet file"""
    paths = save_parquet({"oil_production": oil_production}, PROCESSED_DATA_PATH)
    print()
    print(f"Wrote oil_production -> {paths['oil_production']}")
    return paths["oil_production"]


@asset(
    group_name="parquet_local_files",
)
def lease_operators_parquet(lease_operators: pd.DataFrame) -> Path:
    """Save analytics table locally as Parquet file"""
    paths = save_parquet({"lease_operators": lease_operators}, PROCESSED_DATA_PATH)
    print()
    print(f"Wrote lease_operators -> {paths['lease_operators']}")
    return paths["lease_operators"]


@asset(
    group_name="parquet_local_files",
)
def wells_parquet(wells: pd.DataFrame) -> Path:
    """Save analytics table locally as Parquet file"""
    paths = save_parquet({"wells": wells}, PROCESSED_DATA_PATH)
    print()
    print(f"Wrote wells -> {paths['wells']}")
    return paths["wells"]


@asset(
    group_name="gcs_cloud_storage",
)
def oil_production_gcs(oil_production_parquet: Path) -> str:
    """Upload the Parquet file to GCS Cloud Storage"""
    blob_name = "oil_production.parquet"
    upload_to_gcs(oil_production_parquet, GCS_BUCKET_NAME, blob_name, project=GCP_PROJECT_ID)
    gcs_uri = f"gs://{GCS_BUCKET_NAME}/{blob_name}"
    print()
    print(f"Uploaded {oil_production_parquet} -> {gcs_uri}")
    return gcs_uri


@asset(
    group_name="gcs_cloud_storage",
)
def lease_operators_gcs(lease_operators_parquet: Path) -> str:
    """Upload the Parquet file to GCS Cloud Storage"""
    blob_name = "lease_operators.parquet"
    upload_to_gcs(lease_operators_parquet, GCS_BUCKET_NAME, blob_name, project=GCP_PROJECT_ID)
    gcs_uri = f"gs://{GCS_BUCKET_NAME}/{blob_name}"
    print()
    print(f"Uploaded {lease_operators_parquet} -> {gcs_uri}")
    return gcs_uri


@asset(
    group_name="gcs_cloud_storage",
)
def wells_gcs(wells_parquet: Path) -> str:
    """Upload the Parquet file to GCS Cloud Storage"""
    blob_name = "wells.parquet"
    upload_to_gcs(wells_parquet, GCS_BUCKET_NAME, blob_name, project=GCP_PROJECT_ID)
    gcs_uri = f"gs://{GCS_BUCKET_NAME}/{blob_name}"
    print()
    print(f"Uploaded {wells_parquet} -> {gcs_uri}")
    return gcs_uri


@asset(
    group_name="bigquery_warehouse",
)
def oil_production_bigquery(oil_production_gcs: str) -> None:
    """Loads the oil_production Parquet file from GCS into its BigQuery table."""
    load_parquet_to_bigquery(
        oil_production_gcs, project=GCP_PROJECT_ID, dataset=BQ_DATASET, table="oil_production"
    )
    print()
    print(f"Loaded {oil_production_gcs} -> {GCP_PROJECT_ID}.{BQ_DATASET}.oil_production")


@asset(
    group_name="bigquery_warehouse",
)
def lease_operators_bigquery(lease_operators_gcs: str) -> None:
    """Loads the lease_operators Parquet file from GCS into its BigQuery table."""
    load_parquet_to_bigquery(
        lease_operators_gcs, project=GCP_PROJECT_ID, dataset=BQ_DATASET, table="lease_operators"
    )
    print()
    print(f"Loaded {lease_operators_gcs} -> {GCP_PROJECT_ID}.{BQ_DATASET}.lease_operators")


@asset(
    group_name="bigquery_warehouse",
)
def wells_bigquery(wells_gcs: str) -> None:
    """Loads the wells Parquet file from GCS into its BigQuery table."""
    load_parquet_to_bigquery(wells_gcs, project=GCP_PROJECT_ID, dataset=BQ_DATASET, table="wells")
    print()
    print(f"Loaded {wells_gcs} -> {GCP_PROJECT_ID}.{BQ_DATASET}.wells")


@asset(
    group_name="bigquery_warehouse",
)
def district_lookup_table() -> None:
    """Create/refresh the small static district code/id/name lookup table rrc_districts"""
    sql = build_district_lookup_sql(project=GCP_PROJECT_ID, dataset=BQ_DATASET)
    run_bigquery_sql(sql, project=GCP_PROJECT_ID)
    print()
    print(f"Created {GCP_PROJECT_ID}.{BQ_DATASET}.rrc_districts")
