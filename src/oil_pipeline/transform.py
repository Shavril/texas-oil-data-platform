"""Transform raw DuckDB segment tables into analytics-ready tables for BigQuery/Looker Studio.

The physical DuckDB tables (see oil_pipeline.extract / oil_pipeline.load) mirror the RRC
tape's segment structure one-to-one. This module reshapes them into wide, denormalized
tables shaped for downstream BI consumption.
"""

import logging
from pathlib import Path

import duckdb
import pandas as pd

logger = logging.getLogger(__name__)

# PD-OIL-DISTRICT stored value -> public-facing RRC district ID (docs/data_rrc_production.md)
DISTRICT_ID_BY_CODE = {
    "01": "1",
    "02": "2",
    "03": "3",
    "04": "4",
    "05": "5",
    "06": "6",
    "07": "6E",
    "08": "7B",
    "09": "7C",
    "10": "8",
    "11": "8A",
    "12": "8B",
    "13": "9",
    "14": "10",
}

# Informal/commonly used regional names for each RRC district. NOT an official
# RRC designation — RRC districts have no official names, only these numeric/
# alphanumeric codes. Best-effort industry-common shorthand, not sourced from
# any RRC data file and not independently verified.
DISTRICT_NAME_BY_ID = {
    "1": "South Texas",
    "2": "Coastal Bend",
    "3": "Gulf Coast",
    "4": "South Texas",
    "5": "North-Central Texas",
    "6": "East Texas",
    "6E": "East Texas East",
    "7B": "Eastern Permian",
    "7C": "Central Permian",
    "8": "Permian Basin",
    "8A": "Northern Permian",
    "8B": "RESERVED",
    "9": "North Texas",
    "10": "Panhandle",
}


def build_district_lookup_sql(project: str, dataset: str, table: str = "rrc_districts") -> str:
    """Build a CREATE OR REPLACE TABLE statement for the district code/name lookup.

    Small and static enough to inline as literal rows rather than staging
    through Parquet/GCS like the other analytics tables.
    """
    rows = ",\n".join(
        f"    STRUCT('{code}' AS district_code, '{district_id}' AS rrc_district_id, "
        f"'{DISTRICT_NAME_BY_ID[district_id]}' AS district_name)"
        for code, district_id in sorted(DISTRICT_ID_BY_CODE.items())
    )
    return f"""CREATE OR REPLACE TABLE `{project}.{dataset}.{table}` AS
SELECT * FROM UNNEST([
{rows}
])"""


# Looker Studio-facing views. Each query selects from {table} (the fully-
# qualified oil_production table) left-joined to {districts_table}
# (rrc_districts) to bring in district_name — joined on rrc_district_id where
# the view already carries that column, otherwise on district_code. LEFT JOIN
# so an unmapped district code would surface as a null district_name rather
# than silently dropping the row.

OIL_PRODUCTION_VIOLATIONS_VIEW_QUERY = """SELECT
    CONCAT(p.district_code, '-', p.lease_nbr) AS lease_id,
    p.rrc_district_id,
    d.district_name,
    p.report_month,
    p.oil_production_bbl,
    p.oil_allowable_cycle_bbls,
    p.present_oil_status_bbl AS cumulative_overproduction_bbl,
    SAFE_DIVIDE(p.oil_production_bbl, NULLIF(p.oil_allowable_cycle_bbls, 0)) AS allowable_utilization_ratio
FROM `{table}` p
LEFT JOIN `{districts_table}` d ON p.rrc_district_id = d.rrc_district_id
WHERE p.present_oil_status_bbl > 0
ORDER BY p.present_oil_status_bbl DESC"""

TOTAL_OIL_PRODUCTION_BY_LEASE_ID_VIEW_QUERY = """SELECT
  CONCAT(p.district_code, '-', p.lease_nbr) AS lease_id,
  p.district_code,
  d.district_name,
  SUM(p.oil_production_bbl) AS total_oil_production_bbl
FROM `{table}` p
LEFT JOIN `{districts_table}` d ON p.district_code = d.district_code
GROUP BY lease_id, p.district_code, d.district_name
ORDER BY lease_id, p.district_code ASC"""

TOTAL_OIL_PRODUCTION_BY_MONTH_AND_DISTRICT_CODE_VIEW_QUERY = """SELECT
  p.report_month,
  p.district_code,
  d.district_name,
  SUM(p.oil_production_bbl) AS total_oil_production_bbl
FROM `{table}` p
LEFT JOIN `{districts_table}` d ON p.district_code = d.district_code
GROUP BY p.report_month, p.district_code, d.district_name
ORDER BY p.report_month, p.district_code ASC"""

# Maps each view name to its query variable above — the single place that
# wires a view name to the query that defines it.
VIEW_QUERIES = {
    "oil_production_violations_view": OIL_PRODUCTION_VIOLATIONS_VIEW_QUERY,
    "total_oil_production_by_lease_id_view": TOTAL_OIL_PRODUCTION_BY_LEASE_ID_VIEW_QUERY,
    "total_oil_production_by_month_and_district_code_view": TOTAL_OIL_PRODUCTION_BY_MONTH_AND_DISTRICT_CODE_VIEW_QUERY,
}


def build_view_sql(
    project: str,
    dataset: str,
    view_name: str,
    source_table: str = "oil_production",
    districts_table: str = "rrc_districts",
) -> str:
    """Build a CREATE OR REPLACE VIEW statement for one of the VIEW_QUERIES definitions."""
    query = VIEW_QUERIES[view_name].format(
        table=f"{project}.{dataset}.{source_table}",
        districts_table=f"{project}.{dataset}.{districts_table}",
    )
    return f"CREATE OR REPLACE VIEW `{project}.{dataset}.{view_name}` AS\n{query}"


def build_oil_production(db_path: Path) -> pd.DataFrame:
    """Join production + cycle into one row per lease per reporting month.

    Grain: one row per (district_code, lease_nbr, report_month) — verified 1:1
    against the source tables (production has no duplicate lease-months, and
    an inner join drops cycles where no production was actually reported that
    month, e.g. idle/allowable-only cycles).

    report_month is parsed from the YYMM reporting-cycle key. Month is the
    finest time grain the source data has — RRC leases file one total
    production volume per month, not a daily breakdown.
    """
    with duckdb.connect(str(db_path), read_only=True) as con:
        df = con.execute("""
            SELECT
                p.district_code,
                p.lease_nbr,
                MAKE_DATE(
                    2000 + CAST(SUBSTR(p.rpt_cycle_key_yymm, 1, 2) AS INTEGER),
                    CAST(SUBSTR(p.rpt_cycle_key_yymm, 3, 2) AS INTEGER),
                    1
                ) AS report_month,
                p.oil_production_bbl,
                p.casinghead_gas_mcf,
                p.casinghead_gas_lift_mcf,
                c.oil_allowable_cycle_bbls,
                c.present_oil_status_bbl,
                p.corrected_report_flag = 'Y' AS is_corrected_report,
                p.filed_by_edi_flag = 'Y' AS is_filed_by_edi
            FROM production p
            JOIN cycle c
              ON p.district_code = c.district_code
             AND p.lease_nbr = c.lease_nbr
             AND p.rpt_cycle_key_yymm = c.rpt_cycle_key_yymm
        """).fetchdf()

    df["rrc_district_id"] = df["district_code"].map(DISTRICT_ID_BY_CODE)
    return df


def transform(db_path: Path) -> dict[str, pd.DataFrame]:
    """Build all analytics-ready tables from the raw DuckDB segment tables."""
    return {
        "oil_production": build_oil_production(db_path),
    }
