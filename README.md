# SUMO Simulation Data Pipeline (MotherDuck + dbt + Streamlit)

This project is a lightweight data pipeline for transportation modeling outputs.

Goal: after a transportation modeler runs Simulation of Urban MObility (SUMO), the pipeline ingests its XML outputs into cloud database (MotherDuck), transforms them with dbt, and use Streamlit for visualization.

## What It Does

1. A new/updated simulation output folder is detected.
2. XML files (for example edge and trip outputs) are parsed and normalized.
3. Parsed records are loaded into MotherDuck.
4. dbt models build curated tables for analysis.
5. A Streamlit app reads those tables for interactive exploration.

## Tech Stack

- Raw data: SUMO XML outputs
- Ingestion/parsing: Python
- Warehouse: MotherDuck (DuckDB)
- Transformation: dbt
- Orchestration scaffolding: Dagster
- Consumption layer: Streamlit

## Repository Layout

- `dlt_project/`: ingestion entrypoints for loading simulation outputs
- `utils/`: XML extractors, query helpers, and UI helpers
- `dbt_project/`: dbt models (staging + marts)
- `dagster_orchestration/`: orchestration definitions
- `app.py`: Streamlit dashboard

## Intended Audience

Transportation modelers who need a fast rendering from simulation output.
