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
