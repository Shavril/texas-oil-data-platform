"""Entry point: load the RRC Statewide Production Data (Oil) tape file and print summary stats.

Run from the project root:
    uv run python main.py
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from oil_pipeline.dagster_defs.assets import (
    district_lookup_table,
    lease_operators,
    lease_operators_bigquery,
    lease_operators_gcs,
    lease_operators_parquet,
    oil_production,
    oil_production_bigquery,
    oil_production_gcs,
    oil_production_parquet,
    p4_raw,
    p5_raw,
    production_raw,
    wells,
    wells_bigquery,
    wells_gcs,
    wells_parquet,
    wells_raw,
)
from oil_pipeline.dagster_defs.view_assets import (
    oil_production_violations_view,
    total_oil_production_by_lease_id_view,
    total_oil_production_by_month_and_district_code_view,
    wells_view,
)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Load the oil production raw data into DuckDB
    db_path = production_raw()
    # Load P-4 operator raw data into DuckDB
    p4_raw()
    # Load P-5 organization raw data into DuckDB
    p5_raw()
    # Load wells raw data into DuckDB
    wells_raw()

    # Transform into analytics-ready tables
    oil_production_df = oil_production()
    lease_operators_df = lease_operators()
    wells_df = wells()

    # Save analytics tables locally as Parquet
    oil_production_parquet_path = oil_production_parquet(oil_production_df)
    lease_operators_parquet_path = lease_operators_parquet(lease_operators_df)
    wells_parquet_path = wells_parquet(wells_df)

    # Upload the Parquet files to GCS
    oil_production_gcs_uri = oil_production_gcs(oil_production_parquet_path)
    lease_operators_gcs_uri = lease_operators_gcs(lease_operators_parquet_path)
    wells_gcs_uri = wells_gcs(wells_parquet_path)

    # Load from GCS into BigQuery
    oil_production_bigquery(oil_production_gcs_uri)
    lease_operators_bigquery(lease_operators_gcs_uri)
    wells_bigquery(wells_gcs_uri)

    # Create/refresh the small static district code/name lookup table
    district_lookup_table()

    # Create/refresh the Looker Studio-facing views
    oil_production_violations_view()
    total_oil_production_by_lease_id_view()
    total_oil_production_by_month_and_district_code_view()
    wells_view()


if __name__ == "__main__":
    main()
