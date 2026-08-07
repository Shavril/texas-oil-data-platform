"""Central pipeline configuration.

Every field is required -- it must come from an
OIL_PIPELINE_-prefixed environment variable or a .env file at the repo
root (see .env.example, gitignored once copied to .env). Settings() raises
a validation error listing exactly which ones are missing if it isn't set
up yet.
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OIL_PIPELINE_", env_file=".env", extra="ignore")

    raw_production_path: Path
    raw_p4_path: Path
    raw_p5_path: Path
    raw_wells_path: Path
    db_path: Path
    processed_data_path: Path

    gcp_project_id: str
    gcs_bucket_name: str
    bq_dataset: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
