import os, yaml, json
from datetime import datetime
from pathlib import Path
from dagster import (
    AssetExecutionContext, Config, Definitions, MaterializeResult,
    RunRequest, SensorEvaluationContext, SkipReason, asset,
    define_asset_job, sensor
)
from dagster_dbt import DbtProject, DbtCliResource, dbt_assets
from dlt_project.load_sim_pipeline import load_simulation_results
from dotenv import load_dotenv
load_dotenv() # This must run before any assets are defined

# 1. Load Configuration from YAML
CONFIG_PATH = Path(__file__).resolve().parent.parent / "source_file.yml"
with open(CONFIG_PATH, "r") as f:
    config_data = yaml.safe_load(f)

# Pull variables from YAML
WATCH_DIR = Path(config_data["sumo_xml_watch_dir"]).expanduser()
DBT_PROJECT_DIR = Path(__file__).resolve().parent.parent / "dbt_project"

dbt_project = DbtProject(project_dir=DBT_PROJECT_DIR)
dbt_project.prepare_if_dev()

# 2. Config Class
class DltLoadConfig(Config):
    sim_job_id: str = config_data.get("sim_job_id", "")
    dataset_name: str = config_data.get("bronze_dataset_name", "bronze")
    write_disposition: str = config_data.get("write_disposition", "overwrite")

# 3. Assets
@asset(compute_kind="dlt", group_name="ingestion")
def dlt_bronze_load(context: AssetExecutionContext, config: DltLoadConfig) -> MaterializeResult:
    load_simulation_results(
        sim_job_id=config.sim_job_id,
        write_disposition=config.write_disposition,
    )

    return MaterializeResult(metadata={"sim_job_id": config.sim_job_id})

DBT_MANIFEST_PATH = DBT_PROJECT_DIR / "target" / "manifest.json"

@dbt_assets(manifest=DBT_MANIFEST_PATH)
def sumo_dbt_assets(context: AssetExecutionContext, dbt: DbtCliResource):
    # This runs 'dbt build' for all models in your project
    yield from dbt.cli(["build"], context=context).stream()

# 4. The Job
sumo_pipeline_job = define_asset_job(name="sumo_pipeline_job", selection="*")

# 5. Sensor
@sensor(job=sumo_pipeline_job, minimum_interval_seconds=30)
def xml_settle_sensor(context: SensorEvaluationContext):
    """Triggers when files in WATCH_DIR stop changing."""
    target_files = config_data.get("output_files", [])
    
    current_files = {}
    for f_path in target_files:
        p = Path(f_path).expanduser().resolve()
        if p.exists() and p.is_file():
            # Only track the files you actually care about
            current_files[str(p)] = p.stat().st_mtime_ns
    
    if not current_files:
        return SkipReason("Target output files (tripinfo/e2) not found yet.")
    
    # Retrieve previous state
    # We store the last known file state and the timestamp of the last change
    prev_state = json.loads(context.cursor) if context.cursor else {}
    prev_files = prev_state.get("files", {})
    last_change_time = prev_state.get("last_change_time", 0)
    already_run_hash = prev_state.get("run_hash", "")

    current_hash = str(hash(frozenset(current_files.items())))
    now = datetime.now().timestamp()

    # If files changed, update timestamp and wait
    if current_files != prev_files:
        context.update_cursor(json.dumps({"files": current_files, "last_change_time": now, "run_hash": already_run_hash}))
        return SkipReason("Files are changing... waiting for simulation to finish.")

    # If files are stable, check if we've already run for THIS specific set of data
    if now - last_change_time > 30: # 30 second quiet period
        if current_hash == already_run_hash:
            return SkipReason("Simulation results already processed.")
        
        # Trigger!
        context.update_cursor(json.dumps({"files": current_files, "last_change_time": now, "run_hash": current_hash}))
        return RunRequest(
            run_key=current_hash,
            run_config={
                "ops": {
                    "dlt_bronze_load": {
                        "config": {"sim_job_id": f"sim_{int(now)}"}
                    }
                }
            }
        )
    
# 6. Definitions Object (This was missing!)
defs = Definitions(
    assets=[dlt_bronze_load, sumo_dbt_assets],
    jobs=[sumo_pipeline_job],
    sensors=[xml_settle_sensor],
    resources={
        "dbt": DbtCliResource(
            # Use project-local dbt config and executable.
            project_dir=str(DBT_PROJECT_DIR),
            profiles_dir=str(DBT_PROJECT_DIR),
            dbt_executable=str(Path(__file__).resolve().parent.parent / ".venv" / "bin" / "dbt"),
        )
    },
)