import duckdb
import pandas as pd

RELATION_CANDIDATES = {
    "jobs": ("sim_jobs",),
    "edges": ("gis_layer_baseline", "edge", "edges"),
    "e2": ("all_e2", "bronze_e2"),
    "trips": ("all_trips", "bronze_tripinfo", "trips"),
}


def quote_relation(schema: str, table: str) -> str:
    return f'"{schema}"."{table}"' if schema else f'"{table}"'


def resolve_relations(con: duckdb.DuckDBPyConnection) -> dict[str, str | None]:
    """Find available tables for simulation data, prioritizing curated schemas."""
    flat_candidates = [name.lower() for names in RELATION_CANDIDATES.values() for name in names]

    rows = con.execute(
        f"""
        SELECT lower(table_name) AS lookup_name, table_schema, table_name
        FROM information_schema.tables
        WHERE lower(table_name) IN ({", ".join("?" for _ in flat_candidates)})
        ORDER BY CASE lower(table_schema)
            WHEN 'main' THEN 0 WHEN 'analytics' THEN 1
            WHEN 'staging' THEN 2 WHEN 'bronze' THEN 3 ELSE 4
        END
        """,
        flat_candidates,
    ).fetchall()

    discovered = {lookup: quote_relation(sch, tbl) for lookup, sch, tbl in rows}

    return {
        key: next((discovered[n.lower()] for n in names if n.lower() in discovered), None)
        for key, names in RELATION_CANDIDATES.items()
    }


def load_jobs(con: duckdb.DuckDBPyConnection, relations: dict[str, str | None]) -> pd.DataFrame:
    """Retrieve unique simulation job IDs from any available source table."""
    for relation in (relations["jobs"], relations["e2"], relations["trips"]):
        if not relation:
            continue

        jobs = con.execute(
            f"""
            SELECT DISTINCT CAST(sim_job_id AS VARCHAR) AS sim_job_id
            FROM {relation}
            WHERE sim_job_id IS NOT NULL AND trim(CAST(sim_job_id AS VARCHAR)) <> ''
            ORDER BY sim_job_id DESC
            """
        ).df()

        if not jobs.empty:
            return jobs

    return pd.DataFrame(columns=["sim_job_id"])


def fetch_edge_metrics(
    con: duckdb.DuckDBPyConnection,
    relations: dict[str, str | None],
    sim_job_id: str,
    metric: str,
    start_time: float,
    end_time: float,
) -> pd.DataFrame:
    """Join edge geometry with performance metrics for a specific time window."""
    if not relations["edges"] or not relations["e2"]:
        return pd.DataFrame(columns=["geometry_wkt", "edge_id", "value"])

    query = f"""
        SELECT e.geometry_wkt, e.ID AS edge_id, r."{metric}" AS value
        FROM {relations['e2']} AS r
        JOIN {relations['edges']} AS e
            ON CAST(e.ID AS VARCHAR) = regexp_replace(CAST(r.id AS VARCHAR), '_[^_]+$', '')
        WHERE CAST(r.sim_job_id AS VARCHAR) = ? AND r.begin >= ? AND r.begin < ?
    """
    return con.execute(query, [sim_job_id, start_time, end_time]).df()


def fetch_vehicle_metrics(
    con: duckdb.DuckDBPyConnection,
    trips_relation: str | None,
    sim_job_id: str,
    metric: str,
    start_time: float,
    end_time: float,
) -> pd.DataFrame:
    """Extract vehicle performance samples for a specific time window."""
    if not trips_relation:
        return pd.DataFrame(columns=["value"])

    query = f"""
        SELECT "{metric}" AS value FROM {trips_relation}
        WHERE CAST(sim_job_id AS VARCHAR) = ? AND depart >= ? AND depart < ?
    """
    return con.execute(query, [sim_job_id, start_time, end_time]).df()