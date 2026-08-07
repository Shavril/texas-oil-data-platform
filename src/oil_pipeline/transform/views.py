"""Looker Studio-facing BigQuery view definitions.

Each query selects from {table} (the fully-qualified source table for that
view — oil_production or wells) left-joined to {districts_table}
(rrc_districts) to bring in district_name — joined on rrc_district_id where
the view already carries that column, otherwise on district_code. LEFT JOIN
so an unmapped district code would surface as a null district_name rather
than silently dropping the row.
"""

# Texas's FIPS state prefix, used to build a county FIPS code (state prefix
# + 3-digit county code) from wells.county_code for Looker Studio's Geo
# (county) map type. A lease's wells occasionally span more than one county
# (9,642 of 191,095 leases, ~5%, per notebooks/04_explore_wells.ipynb-style
# checks against real data) — lease_county below picks one deterministically
# (MIN) per lease_id, an arbitrary but reproducible approximation in that
# minority of cases, matching the same kind of approximation already made in
# oil_pipeline.transform.wells.build_wells for multi-lease wells.
LEASE_COUNTY_CTE = """lease_county AS (
    SELECT lease_id, MIN(county_code) AS county_code
    FROM `{wells_table}`
    WHERE county_code IS NOT NULL
    GROUP BY lease_id
)"""

OIL_PRODUCTION_VIOLATIONS_VIEW_QUERY = f"""WITH p AS (
    SELECT *, CONCAT(district_code, '-', lease_nbr) AS lease_id
    FROM `{{table}}`
),
{LEASE_COUNTY_CTE}
SELECT
    p.lease_id,
    p.rrc_district_id,
    d.district_name,
    lo.operator_number,
    lo.organization_name,
    lc.county_code,
    CONCAT('48', lc.county_code) AS county_fips,
    p.report_month,
    p.oil_production_bbl,
    p.oil_allowable_cycle_bbls,
    p.present_oil_status_bbl AS cumulative_overproduction_bbl,
    SAFE_DIVIDE(p.oil_production_bbl, NULLIF(p.oil_allowable_cycle_bbls, 0)) AS allowable_utilization_ratio
FROM p
LEFT JOIN `{{districts_table}}` d ON p.rrc_district_id = d.rrc_district_id
LEFT JOIN `{{lease_operators_table}}` lo ON p.lease_id = lo.lease_id
LEFT JOIN lease_county lc ON p.lease_id = lc.lease_id
WHERE p.present_oil_status_bbl > 0
ORDER BY p.present_oil_status_bbl DESC"""

TOTAL_OIL_PRODUCTION_BY_LEASE_ID_VIEW_QUERY = f"""WITH p AS (
  SELECT *, CONCAT(district_code, '-', lease_nbr) AS lease_id
  FROM `{{table}}`
),
{LEASE_COUNTY_CTE}
SELECT
  p.lease_id,
  p.district_code,
  d.district_name,
  lo.operator_number,
  lo.organization_name,
  lc.county_code,
  CONCAT('48', lc.county_code) AS county_fips,
  SUM(p.oil_production_bbl) AS total_oil_production_bbl
FROM p
LEFT JOIN `{{districts_table}}` d ON p.district_code = d.district_code
LEFT JOIN `{{lease_operators_table}}` lo ON p.lease_id = lo.lease_id
LEFT JOIN lease_county lc ON p.lease_id = lc.lease_id
GROUP BY p.lease_id, p.district_code, d.district_name, lo.operator_number, lo.organization_name, lc.county_code
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

# One generic, row-level view over `wells` (not pre-aggregated) — deliberately
# kept reusable rather than building one narrow view per chart. Every column
# needed for all 7 wells visualizations (map, county/district breakdown,
# wells-drilled-per-year, active/plugged split, depth distribution,
# wells-per-lease, land/water breakdown) is present at well grain; Looker
# Studio does the GROUP BY / histogram bucketing per-chart on top of this
# single view.
WELLS_VIEW_QUERY = """SELECT
  w.api_number,
  w.lease_id,
  w.district_code,
  d.district_name,
  lo.operator_number,
  lo.organization_name,
  w.well_nbr,
  w.county_code,
  CONCAT('48', w.county_code) AS county_fips,
  w.latitude,
  w.longitude,
  CASE WHEN w.latitude IS NOT NULL AND w.longitude IS NOT NULL
       THEN CONCAT(CAST(w.latitude AS STRING), ',', CAST(w.longitude AS STRING))
  END AS lat_long,
  w.orig_compl_year,
  w.total_depth_ft,
  w.is_active,
  w.is_plugged,
  w.water_land_code
FROM `{table}` w
LEFT JOIN `{districts_table}` d ON w.district_code = d.district_code
LEFT JOIN `{lease_operators_table}` lo ON w.lease_id = lo.lease_id"""

# Maps each view name to its query template + the source table it reads
# from — the single place that wires a view name to its definition.
VIEW_DEFINITIONS = {
    "oil_production_violations_view": {
        "query": OIL_PRODUCTION_VIOLATIONS_VIEW_QUERY,
        "source_table": "oil_production",
    },
    "total_oil_production_by_lease_id_view": {
        "query": TOTAL_OIL_PRODUCTION_BY_LEASE_ID_VIEW_QUERY,
        "source_table": "oil_production",
    },
    "total_oil_production_by_month_and_district_code_view": {
        "query": TOTAL_OIL_PRODUCTION_BY_MONTH_AND_DISTRICT_CODE_VIEW_QUERY,
        "source_table": "oil_production",
    },
    "wells_view": {
        "query": WELLS_VIEW_QUERY,
        "source_table": "wells",
    },
}


def build_view_sql(
    project: str,
    dataset: str,
    view_name: str,
    source_table: str | None = None,
    districts_table: str = "rrc_districts",
    lease_operators_table: str = "lease_operators",
    wells_table: str = "wells",
) -> str:
    """Build a CREATE OR REPLACE VIEW statement for one of the VIEW_DEFINITIONS.

    source_table defaults to the view's own definition (VIEW_DEFINITIONS[view_name]["source_table"])
    but can be overridden if ever needed (e.g. pointing at a differently-named table).
    """
    definition = VIEW_DEFINITIONS[view_name]
    if source_table is None:
        source_table = definition["source_table"]
    query = definition["query"].format(
        table=f"{project}.{dataset}.{source_table}",
        wells_table=f"{project}.{dataset}.{wells_table}",
        districts_table=f"{project}.{dataset}.{districts_table}",
        lease_operators_table=f"{project}.{dataset}.{lease_operators_table}",
    )
    return f"CREATE OR REPLACE VIEW `{project}.{dataset}.{view_name}` AS\n{query}"
