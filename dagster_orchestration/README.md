# Dagster Orchestration

This package orchestrates two steps:
- Load SUMO XML outputs into MotherDuck via dlt (`dlt_bronze_load`)
- Run dbt transformations (`sumo_dbt_assets`)

## Run locally

```bash
dagster dev -m dagster_orchestration
```

Then launch `sumo_pipeline_job` (or materialize assets from the UI).

## Sensor behavior

`xml_settle_sensor` (in `definitions.py`) monitors the XML files listed in `source_file.yml` (`output_files`).

High-level behavior:
- Checks file changes every 30 seconds
- Waits until files are stable (no recent modification)
- Triggers one run per unique settled file snapshot
- Skips reruns for the same snapshot using cursor state