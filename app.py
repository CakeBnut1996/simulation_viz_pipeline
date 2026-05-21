import os
import duckdb
import streamlit as st

from utils.data_queries import (
    fetch_edge_metrics,
    fetch_vehicle_metrics,
    load_jobs,
    resolve_relations,
)
from utils.ui_components import (
    sidebar_edge_metric_selector,
    sidebar_job_selector,
    sidebar_style_customization,
    sidebar_time_selector,
    sidebar_vehicle_metric_selector,
    get_metric_label,
    show_cdf_distribution,
    show_map,
)

MOTHERDUCK_PATH = os.getenv("MOTHERDUCK_PATH", "md:sumo_visualization")
TIME_WINDOW_SECONDS = 0.25

st.set_page_config(layout="wide", page_title="Nashville Transportation Microsim")


@st.cache_resource
def get_connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(MOTHERDUCK_PATH, read_only=True)


# --- Main App Execution ---
try:
    con = get_connection()
except duckdb.Error as exc:
    st.error("Unable to connect to MotherDuck. Verify path or environment tokens.")
    st.exception(exc)
    st.stop()

relations = resolve_relations(con)
jobs = load_jobs(con, relations)

sim_job_id = sidebar_job_selector(jobs)
edge_metric = sidebar_edge_metric_selector()
veh_metric = sidebar_vehicle_metric_selector()
time_step = sidebar_time_selector()

st.title("Nashville Microscopic Traffic Sim Outputs")

if not sim_job_id:
    st.stop()

start_time = time_step - TIME_WINDOW_SECONDS
end_time = time_step + TIME_WINDOW_SECONDS

df_edges = fetch_edge_metrics(con, relations, sim_job_id, edge_metric, start_time, end_time) 
df_vehicles = fetch_vehicle_metrics(con, relations["trips"], sim_job_id, veh_metric, start_time, end_time)

st.subheader(f"Edge-based Metrics: {get_metric_label(edge_metric)}")
show_map(df_edges, edge_metric)
st.divider()
st.subheader(f"Vehicle-based Metrics: {get_metric_label(veh_metric)}")
show_cdf_distribution(df_vehicles, veh_metric)