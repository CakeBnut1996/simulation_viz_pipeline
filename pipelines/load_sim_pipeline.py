from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path
import tomllib

import dlt

from io_utils.xml_extractors import discover_xml_files, parse_sumo_xml_file, sanitize_identifier


DEFAULT_DATASET_NAME = "bronze_sim"
DEFAULT_PIPELINE_NAME = "sumo_bronze_pipeline"
DEFAULT_DESTINATION = "motherduck"
DEFAULT_SOURCE_FILE = Path(__file__).with_name("source_file.yml")
DEFAULT_DLT_SECRETS_FILE = Path(".dlt/secrets.toml")


def validate_destination_credentials(destination: str) -> None:
    """Fail fast when destination credentials are missing or malformed."""
    if destination != "motherduck":
        return

    if not DEFAULT_DLT_SECRETS_FILE.is_file():
        raise RuntimeError(
            "MotherDuck requires credentials in .dlt/secrets.toml, but the file was not found. "
            "Add a token/password under [destination.motherduck.credentials]."
        )

    try:
        secrets = tomllib.loads(DEFAULT_DLT_SECRETS_FILE.read_text(encoding="utf-8"))
    except Exception as exc:
        raise RuntimeError(
            "Could not parse .dlt/secrets.toml. Fix the TOML format and add "
            "[destination.motherduck.credentials] token/password."
        ) from exc

    credentials = (
        secrets.get("destination", {})
        .get("motherduck", {})
        .get("credentials", {})
    )
    token = credentials.get("token") or credentials.get("password")
    if not token or not str(token).strip():
        raise RuntimeError(
            "MotherDuck token is missing in .dlt/secrets.toml. "
            "Expected [destination.motherduck.credentials] with token or password."
        )


def build_pipeline(
    pipeline_name: str = DEFAULT_PIPELINE_NAME,
    dataset_name: str = DEFAULT_DATASET_NAME,
    destination: str = DEFAULT_DESTINATION,
) -> dlt.Pipeline: # creates a dlt Pipeline object
    validate_destination_credentials(destination)
    return dlt.pipeline(
        pipeline_name=pipeline_name,
        destination=destination,
        dataset_name=dataset_name,
    )


def resolve_source_files(config_path: str | Path = DEFAULT_SOURCE_FILE) -> list[Path]:
    """Load and resolve XML files from source_file.yml configuration.
    
    source_file.yml format:
    - Each line is a path to an XML file or directory containing XML files
    - Lines starting with '#' are comments and are ignored
    - Blank lines are ignored
    - Optional YAML list prefix '- ' is supported (e.g., '- /path/to/file.xml')
    
    Example source_file.yml:
        # SUMO simulation outputs
        - /data/baseline_20260430/tripinfo.xml
        /data/baseline_20260430/e2_output.xml
        # Another job
        /data/alternate_run/tripinfo.xml
    """
    path = Path(config_path).expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Default source file not found: {path}")

    resolved_files: list[Path] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        
        configured_source = Path(line).expanduser().resolve()
        resolved_files.extend(discover_xml_files(configured_source))

    if not resolved_files:
        raise ValueError(f"No XML files resolved from {path}")
    
    return resolved_files


def load_simulation_results(
    job_id: str,
    description: str = "",
    dataset_name: str = DEFAULT_DATASET_NAME,
    pipeline_name: str = DEFAULT_PIPELINE_NAME,
    destination: str = DEFAULT_DESTINATION,
    write_disposition: str = "append",
) -> list[dict[str, object]]:
    files = resolve_source_files()
    if not files:
        raise ValueError("No XML files resolved from source_file.yml")
    
    resolved_job_id = sanitize_identifier(job_id)
    job_source_path = files[0].parent
    pipeline = build_pipeline(
        pipeline_name=pipeline_name,
        dataset_name=dataset_name,
        destination=destination,
    )

    audit_rows: list[dict[str, object]] = []

    for file_path in files:
        payload = parse_sumo_xml_file(file_path, resolved_job_id)
        if not payload.rows:
            continue

        pipeline.run(
            payload.rows,
            table_name=payload.table_name,
            write_disposition=write_disposition,
        )
        audit_rows.append(
            {
                "sim_job_id": resolved_job_id,
                "source_file_name": file_path.name,
                "source_file_path": str(file_path),
                "record_type": payload.record_type,
                "target_table_name": payload.table_name,
                "loaded_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )

    if audit_rows:
        pipeline.run(
            audit_rows,
            table_name="bronze_load_audit",
            write_disposition=write_disposition,
        )

    total_files = len(audit_rows) if audit_rows else 0
    job_metadata = [
        {
            "sim_job_id": resolved_job_id,
            "description": description,
            "source_directory": str(job_source_path),
            "total_files_loaded": total_files,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
        }
    ]

    pipeline.run(
        job_metadata,
        table_name="bronze_job_metadata",
        write_disposition=write_disposition,
    )

    return audit_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract SUMO simulation XML outputs (configured in source_file.yml) and load into MotherDuck bronze tables with dlt."
    )
    parser.add_argument("--job-id", required=True, help="Simulation run identifier (required).")
    parser.add_argument("--description", default="", help="Human-readable description of this job run.")
    parser.add_argument("--dataset-name", default=DEFAULT_DATASET_NAME)
    parser.add_argument("--pipeline-name", default=DEFAULT_PIPELINE_NAME)
    parser.add_argument(
        "--destination",
        default=DEFAULT_DESTINATION,
        choices=["motherduck", "duckdb"],
        help="Destination backend for dlt pipeline.",
    )
    parser.add_argument(
        "--write-disposition",
        choices=["append", "replace"],
        default="append",
        help="Should dlt replace or append the target bronze tables?",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audit_rows = load_simulation_results(
        job_id=args.job_id,
        description=args.description,
        dataset_name=args.dataset_name,
        pipeline_name=args.pipeline_name,
        destination=args.destination,
        write_disposition=args.write_disposition,
    )

    for row in audit_rows:
        print(
            f"Loaded from {row['source_file_name']} into "
            f"{row['target_table_name']} ({row['record_type']})"
        )


if __name__ == "__main__":
    main()

# Example usage 
# python pipelines/load_sim_pipeline.py \
#   --job-id baseline_20260430 \
#   --description "Baseline network with new charging infrastructure" \
#   --write-disposition append