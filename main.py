"""Entry point: load the RRC Statewide Production Data (Oil) tape file and print summary stats.

Run from the project root:
    uv run python main.py
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from oil_pipeline.extract import load_pdf100
from oil_pipeline.load import save_tables

RAW_DATA_PATH = Path(__file__).parent / "data" / "raw" / "production" / "PDF100.ebc"
DB_PATH = Path(__file__).parent / "data" / "database" / "pdf100.duckdb"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

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


if __name__ == "__main__":
    main()
