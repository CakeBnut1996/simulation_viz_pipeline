from pathlib import Path

from dagster import (
    AssetExecutionContext,
    Config,
    Definitions,
    MaterializeResult,
    asset,
    define_asset_job,
)
from dagster_dbt import DbtCliResource

from pipelines.load_sim_pipeline import load_simulation_results


REPO_ROOT = Path(__file__).resolve().parent.parent
DBT_PROJECT_DIR = REPO_ROOT / "dbt_project"
DBT_EXECUTABLE = REPO_ROOT / ".venv" / "bin" / "dbt"


class DltLoadConfig(Config):
    job_id: str
    description: str = ""
    dataset_name: str = "bronze_sim"
    pipeline_name: str = "sumo_bronze_pipeline"
    destination: str = "motherduck"
    write_disposition: str = "append"


@asset(compute_kind="dlt", group_name="ingestion")
def dlt_bronze_load(
    context: AssetExecutionContext,
    config: DltLoadConfig,
) -> MaterializeResult:
    audit_rows = load_simulation_results(
        job_id=config.job_id,
        description=config.description,
        dataset_name=config.dataset_name,
        pipeline_name=config.pipeline_name,
        destination=config.destination,
        write_disposition=config.write_disposition,
    )

    context.log.info("Loaded %s source files into bronze tables", len(audit_rows))

    return MaterializeResult(
        metadata={
            "loaded_source_files": len(audit_rows),
            "job_id": config.job_id,
            "dataset_name": config.dataset_name,
            "destination": config.destination,
        }
    )


@asset(
    deps=[dlt_bronze_load],
    compute_kind="dbt",
    group_name="transformations",
)
def dbt_build(
    context: AssetExecutionContext,
    dbt: DbtCliResource,
) -> None:
    yield from dbt.cli(
        [
            "build",
            "--project-dir",
            str(DBT_PROJECT_DIR),
            "--profiles-dir",
            str(DBT_PROJECT_DIR),
        ],
        context=context,
    ).stream()


sumo_pipeline_job = define_asset_job(
    name="sumo_pipeline_job",
    selection=["dlt_bronze_load", "dbt_build"],
)


defs = Definitions(
    assets=[dlt_bronze_load, dbt_build],
    jobs=[sumo_pipeline_job],
    resources={
        "dbt": DbtCliResource(
            project_dir=str(DBT_PROJECT_DIR),
            profiles_dir=str(DBT_PROJECT_DIR),
            dbt_executable=str(DBT_EXECUTABLE),
        )
    },
)
