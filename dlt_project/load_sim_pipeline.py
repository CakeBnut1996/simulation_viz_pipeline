from __future__ import annotations
import yaml, os
import dlt
from pathlib import Path
from collections import defaultdict
import geopandas as gpd
from utils.xml_extractors import parse_sumo_xml_file

# Load configuration once at the top
CONFIG_PATH = Path(__file__).resolve().parent.parent / "source_file.yml"
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

def build_pipeline() -> dlt.Pipeline:
    """Creates a dlt Pipeline object using the standardized dlt config lookup."""
    db_name = config.get("motherduck_db", "sumo_visualization")
    os.environ["DESTINATION__MOTHERDUCK__CREDENTIALS__DATABASE"] = db_name
    os.environ["SCHEMA__NAMING"] = "direct"

    return dlt.pipeline(
        pipeline_name=config.get("dlt_pipeline_name"),
        destination="motherduck", 
        dataset_name=config.get("bronze_dataset_name")
    )

def read_output_files(config: dict) -> list[Path]:
    """Resolve and return unique XML file paths from config."""
    raw_paths = config.get("output_files", [])
    
    # Clean, filter, and deduplicate in one clean pass
    resolved = {
        p for raw in raw_paths 
        if (p := Path(raw).expanduser().resolve()).suffix.lower() == ".xml"
    }
    
    return sorted(resolved)

def load_simulation_results(sim_job_id: str = "", write_disposition: str = "append"):
    files = read_output_files(config)
    if not files:
        raise ValueError(f"No XML files found based on {CONFIG_PATH}")

    pipeline = build_pipeline()
    table_data = defaultdict(list)

    for file_path in files:
        payload = parse_sumo_xml_file(file_path, sim_job_id)
        if payload.rows:
            table_data[payload.table_name].extend(payload.rows)

    # Optimized: Batch load each table once
    for table_name, rows in table_data.items():
        pipeline.run(rows, table_name=table_name, write_disposition=write_disposition, table_format="direct" if hasattr(dlt, 'table_format') else None, columns=None)

