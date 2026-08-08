"""BigQuery-warehouse-facing view assets (Looker Studio-facing, currently).

Kept separate from assets.py's data pipeline assets since this file is
expected to grow as more views/warehouse-side objects are added on top of
the data those assets load -- these aren't part of the raw->transform->
parquet->GCS->BigQuery data flow itself.

One asset per view in oil_pipeline.transform.views.VIEW_DEFINITIONS, each
deps-ing on exactly the BigQuery tables its own SQL joins (not a blanket
dependency on every table) -- see each view's query in transform/views.py
for which tables that is.
"""

from dagster import asset

from oil_pipeline.config import get_settings
from oil_pipeline.dagster_defs.assets import (
    district_lookup_table,
    lease_operators_bigquery,
    oil_production_bigquery,
    wells_bigquery,
)
from oil_pipeline.load.bigquery import run_bigquery_sql
from oil_pipeline.transform.views import build_view_sql

settings = get_settings()

GCP_PROJECT_ID = settings.gcp_project_id
BQ_DATASET = settings.bq_dataset


@asset(
    group_name="bigquery_warehouse",
    deps=[oil_production_bigquery, lease_operators_bigquery, wells_bigquery, district_lookup_table],
)
def oil_production_violations_view() -> None:
    """Joins oil_production, lease_operators, wells (for county) and rrc_districts."""
    view_name = "oil_production_violations_view"
    sql = build_view_sql(GCP_PROJECT_ID, BQ_DATASET, view_name)
    run_bigquery_sql(sql, project=GCP_PROJECT_ID)
    print()
    print(f"Created {GCP_PROJECT_ID}.{BQ_DATASET}.{view_name}")


@asset(
    group_name="bigquery_warehouse",
    deps=[oil_production_bigquery, lease_operators_bigquery, wells_bigquery, district_lookup_table],
)
def total_oil_production_by_lease_id_view() -> None:
    """Joins oil_production, lease_operators, wells (for county) and rrc_districts."""
    view_name = "total_oil_production_by_lease_id_view"
    sql = build_view_sql(GCP_PROJECT_ID, BQ_DATASET, view_name)
    run_bigquery_sql(sql, project=GCP_PROJECT_ID)
    print()
    print(f"Created {GCP_PROJECT_ID}.{BQ_DATASET}.{view_name}")


@asset(
    group_name="bigquery_warehouse",
    deps=[oil_production_bigquery, district_lookup_table],
)
def total_oil_production_by_month_and_district_code_view() -> None:
    """Joins oil_production and rrc_districts only."""
    view_name = "total_oil_production_by_month_and_district_code_view"
    sql = build_view_sql(GCP_PROJECT_ID, BQ_DATASET, view_name)
    run_bigquery_sql(sql, project=GCP_PROJECT_ID)
    print()
    print(f"Created {GCP_PROJECT_ID}.{BQ_DATASET}.{view_name}")


@asset(
    group_name="bigquery_warehouse",
    deps=[wells_bigquery, lease_operators_bigquery, district_lookup_table],
)
def wells_view() -> None:
    """Joins wells, lease_operators and rrc_districts."""
    view_name = "wells_view"
    sql = build_view_sql(GCP_PROJECT_ID, BQ_DATASET, view_name)
    run_bigquery_sql(sql, project=GCP_PROJECT_ID)
    print()
    print(f"Created {GCP_PROJECT_ID}.{BQ_DATASET}.{view_name}")
