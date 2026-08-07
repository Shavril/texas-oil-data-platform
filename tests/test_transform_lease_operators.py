from pathlib import Path

import pandas as pd

from oil_pipeline.load.duckdb import save_tables
from oil_pipeline.transform.lease_operators import build_lease_operators


def _seed(db_path: Path, p4_root: pd.DataFrame, p5_organizations: pd.DataFrame) -> None:
    save_tables({"p4_root": p4_root, "p5_organizations": p5_organizations}, db_path)


def test_build_lease_operators_filters_to_oil_leases_only(tmp_path: Path):
    db_path = tmp_path / "analytics.duckdb"
    p4_root = pd.DataFrame(
        {
            "district_code": ["01", "01"],
            "lease_nbr": ["000001", "000002"],
            "oil_gas_code": ["O", "G"],
            "operator_number": ["111111", "222222"],
        }
    )
    p5_organizations = pd.DataFrame(
        {
            "operator_number": ["111111", "222222"],
            "organization_name": ["Acme Oil", "Widget Gas"],
            "p5_status": ["A", "A"],
        }
    )
    _seed(db_path, p4_root, p5_organizations)

    df = build_lease_operators(db_path)

    assert len(df) == 1
    assert df.iloc[0]["lease_id"] == "01-000001"
    assert df.iloc[0]["organization_name"] == "Acme Oil"


def test_build_lease_operators_left_join_keeps_unmatched_operator(tmp_path: Path):
    db_path = tmp_path / "analytics.duckdb"
    p4_root = pd.DataFrame(
        {
            "district_code": ["01"],
            "lease_nbr": ["000001"],
            "oil_gas_code": ["O"],
            "operator_number": ["999999"],  # no matching P-5 record
        }
    )
    p5_organizations = pd.DataFrame(
        {
            "operator_number": pd.Series([], dtype="string"),
            "organization_name": pd.Series([], dtype="string"),
            "p5_status": pd.Series([], dtype="string"),
        }
    )
    _seed(db_path, p4_root, p5_organizations)

    df = build_lease_operators(db_path)

    assert len(df) == 1
    assert pd.isna(df.iloc[0]["organization_name"])
