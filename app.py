import streamlit as st
import duckdb

from display_utils.ui_components import (
    sidebar_job_selector,
    sidebar_edge_metric_selector,
    sidebar_vehicle_metric_selector,
    sidebar_time_selector,
    sidebar_style_customization,
    show_map,
    show_histogram,
    show_cdf_distribution
)

# Configuration
DB_PATH = "sumo_output.db"

st.set_page_config(layout="wide", page_title="Nashville Transportation Microsim")


@st.cache_resource
def get_con():
    return duckdb.connect(DB_PATH, read_only=True)

con = get_con()

# 1. Sidebar
job_id = sidebar_job_selector(con)
edge_metric = sidebar_edge_metric_selector()    # Metric for the map
veh_metric = sidebar_vehicle_metric_selector()  # Metric for the vehicle figures
time_step = sidebar_time_selector()
map_style, line_weight = sidebar_style_customization()

# 2. Data Fetching 15 minutes * 60 seconds
edge_query = f"""
    SELECT e.geometry_wkt, e.ID as edge_id, r.{edge_metric} as value
    FROM all_e2 r
    JOIN edge e ON e.ID = regexp_replace(r.id, '_[^_]+$', '')
    WHERE r.sim_job_id = '{job_id}' 
    AND r.begin >= {time_step * 900} AND r.begin < {(time_step + 1) * 900} 
"""
df_edges = con.execute(edge_query).df()

veh_query = f"""
    SELECT {veh_metric} as value
    FROM all_trips
    WHERE sim_job_id = '{job_id}'
    AND depart >= {time_step * 900} AND depart < {(time_step + 1) * 900}
"""
df_vehicles = con.execute(veh_query).df()

# 3. Main Display
st.title("Nashville Microscopic Traffic Sim Outputs")
st.subheader(f"Edge-based Metrics: {edge_metric}")
show_map(df_edges, edge_metric, map_style, line_weight)
st.markdown("---") # Visual separator
st.markdown("---")
st.subheader(f"Vehicle-based Metrics: {veh_metric}")
show_cdf_distribution(df_vehicles, veh_metric)