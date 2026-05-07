# Dagster orchestration

This package orchestrates:
1. dlt bronze ingestion from XML files configured in `pipelines/source_file.yml`
2. dbt model build in `dbt_project`

## Run Dagster UI

```bash
dagster dev -m dagster_orchestration
```

Then materialize `dlt_bronze_load` and `dbt_build`, or launch `sumo_pipeline_job`.

## Required run config for dlt asset

`dlt_bronze_load` requires a `job_id` in run config:

```yaml
ops:
  dlt_bronze_load:
    config:
      job_id: baseline_20260505
      description: "Baseline run"
      destination: motherduck
      write_disposition: append
```

## Environment

- Make sure `MOTHERDUCK_TOKEN` is set for dbt (`dbt_project/profiles.yml` uses `env_var('MOTHERDUCK_TOKEN')`).
- Make sure `.dlt/secrets.toml` has `destination.motherduck.credentials` token/password for dlt.
