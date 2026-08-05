"""Looker Studio-facing BigQuery view definitions.

Each query selects from {table} (the fully-qualified oil_production table)
left-joined to {districts_table} (rrc_districts) to bring in district_name —
joined on rrc_district_id where the view already carries that column,
otherwise on district_code. LEFT JOIN so an unmapped district code would
surface as a null district_name rather than silently dropping the row.
"""

OIL_PRODUCTION_VIOLATIONS_VIEW_QUERY = """WITH p AS (
    SELECT *, CONCAT(district_code, '-', lease_nbr) AS lease_id
    FROM `{table}`
)
SELECT
    p.lease_id,
    p.rrc_district_id,
    d.district_name,
    lo.operator_number,
    lo.organization_name,
    p.report_month,
    p.oil_production_bbl,
    p.oil_allowable_cycle_bbls,
    p.present_oil_status_bbl AS cumulative_overproduction_bbl,
    SAFE_DIVIDE(p.oil_production_bbl, NULLIF(p.oil_allowable_cycle_bbls, 0)) AS allowable_utilization_ratio
FROM p
LEFT JOIN `{districts_table}` d ON p.rrc_district_id = d.rrc_district_id
LEFT JOIN `{lease_operators_table}` lo ON p.lease_id = lo.lease_id
WHERE p.present_oil_status_bbl > 0
ORDER BY p.present_oil_status_bbl DESC"""

TOTAL_OIL_PRODUCTION_BY_LEASE_ID_VIEW_QUERY = """WITH p AS (
  SELECT *, CONCAT(district_code, '-', lease_nbr) AS lease_id
  FROM `{table}`
)
SELECT
  p.lease_id,
  p.district_code,
  d.district_name,
  lo.operator_number,
  lo.organization_name,
  SUM(p.oil_production_bbl) AS total_oil_production_bbl
FROM p
LEFT JOIN `{districts_table}` d ON p.district_code = d.district_code
LEFT JOIN `{lease_operators_table}` lo ON p.lease_id = lo.lease_id
GROUP BY p.lease_id, p.district_code, d.district_name, lo.operator_number, lo.organization_name
ORDER BY p.lease_id, p.district_code ASC"""

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
    lease_operators_table: str = "lease_operators",
) -> str:
    """Build a CREATE OR REPLACE VIEW statement for one of the VIEW_QUERIES definitions."""
    query = VIEW_QUERIES[view_name].format(
        table=f"{project}.{dataset}.{source_table}",
        districts_table=f"{project}.{dataset}.{districts_table}",
        lease_operators_table=f"{project}.{dataset}.{lease_operators_table}",
    )
    return f"CREATE OR REPLACE VIEW `{project}.{dataset}.{view_name}` AS\n{query}"
