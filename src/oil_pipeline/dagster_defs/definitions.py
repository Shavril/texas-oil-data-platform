from dagster import AssetSelection, Definitions, define_asset_job, in_process_executor, load_assets_from_modules

from oil_pipeline.dagster_defs import assets, view_assets
from oil_pipeline.dagster_defs.view_assets import (
    oil_production_violations_view,
    total_oil_production_by_lease_id_view,
    total_oil_production_by_month_and_district_code_view,
    wells_view,
)

# Dagster's default multiprocess executor deadlocks on Windows for this
# pipeline: its compute-log capture (poll_compute_logs.py) hangs waiting on
# the spawned step subprocess. in_process_executor runs every step in a
# single process instead, sidestepping it -- fine at this pipeline's scale.

# view_assets.py's assets just (re-)define BigQuery views -- since a view is
# a saved query evaluated fresh at query time (not a materialized
# snapshot), they only need to run again when their SQL changes, not on
# every routine data refresh. Excluded from all_assets_job; use
# analytics_views_job to (re-)create them on demand. If you add another
# view asset to view_assets.py, add it to view_asset_selection below too.
view_asset_selection = AssetSelection.assets(
    oil_production_violations_view,
    total_oil_production_by_lease_id_view,
    total_oil_production_by_month_and_district_code_view,
    wells_view,
)

all_assets_job = define_asset_job(
    "all_assets_job",
    selection=AssetSelection.all() - view_asset_selection,
    executor_def=in_process_executor,
)

analytics_views_job = define_asset_job(
    "analytics_views_job",
    selection=view_asset_selection,
    executor_def=in_process_executor,
)

defs = Definitions(
    assets=load_assets_from_modules([assets, view_assets]),
    jobs=[all_assets_job, analytics_views_job],
)
