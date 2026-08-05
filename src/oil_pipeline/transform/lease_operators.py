"""Build the lease_operators analytics table by joining P-4 leases to P-5 organizations."""

from pathlib import Path

import duckdb
import pandas as pd


def build_lease_operators(db_path: Path) -> pd.DataFrame:
    """Join P-4 Root (oil leases only) to P-5 Organization on operator_number.

    Grain: one row per oil lease (district_code, lease_nbr). P-4 Root also
    contains gas wells (oil_gas_code = 'G') — filtered out here, since the
    production tape is oil-only and a gas well could otherwise coincidentally
    share a (district_code, lease_nbr) with an oil lease (see
    docs/data_p4_operators.md Known Issues).

    LEFT JOIN to P-5 so a lease whose operator number has no matching P-5
    organization record surfaces as a null organization_name rather than
    silently dropping the lease.
    """
    with duckdb.connect(str(db_path), read_only=True) as con:
        df = con.execute("""
            SELECT
                p4.district_code,
                p4.lease_nbr,
                CONCAT(p4.district_code, '-', p4.lease_nbr) AS lease_id,
                p4.operator_number,
                p5.organization_name,
                p5.p5_status
            FROM p4_root p4
            LEFT JOIN p5_organizations p5
              ON p4.operator_number = p5.operator_number
            WHERE p4.oil_gas_code = 'O'
        """).fetchdf()

    return df
