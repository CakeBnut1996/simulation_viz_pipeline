import streamlit as st
import folium
import pandas as pd
from streamlit_folium import folium_static
from shapely import wkt
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

EDGE_METRICS = {
    "meanSpeed": "Avg Speed (mph)",
    "maxJamLengthInMiles": "Queue Length (miles)",
    "meanOccupancy": "Lane Occupancy (%)",
}

VEHICLE_METRICS = {
    "duration": "Trip Duration (minutes)",
    "routeLength": "Trip Distance (miles)",
    "waitingTime": "Total Waiting (minutes)",
}

def get_metric_label(metric_name: str) -> str:
    """Get human-readable label for a metric name."""
    return EDGE_METRICS.get(metric_name, VEHICLE_METRICS.get(metric_name, metric_name))

# --- UI COMPONENTS ---
def sidebar_job_selector(jobs: pd.DataFrame) -> str | None:
    st.sidebar.subheader("📁 Simulation Data")
    if jobs.empty:
        st.sidebar.warning("No simulation jobs available in MotherDuck.")
        return None

    return st.sidebar.selectbox("Select Sim Job", jobs["sim_job_id"].tolist())


def sidebar_edge_metric_selector():
    st.sidebar.subheader("Traffic Metrics")
    label = st.sidebar.selectbox("Attribute", list(EDGE_METRICS.values()))
    return [k for k, v in EDGE_METRICS.items() if v == label][0]

def sidebar_vehicle_metric_selector():
    st.sidebar.subheader("Vehicle Metrics (TripInfo)")
    label = st.sidebar.selectbox("Vehicle Attribute", list(VEHICLE_METRICS.values()))
    return [k for k, v in VEHICLE_METRICS.items() if v == label][0]

def sidebar_time_selector():
    st.sidebar.subheader("🕒 Temporal Control")

    # 0 to 24 hours display
    time_step = st.sidebar.slider(
        "Time of Day",
        min_value=0.0,
        max_value=24.0,
        value=8.0,  # Defaults to 8:00 AM
        step=0.25,
        format="%.2f"
    )

    # Calculate hours and minutes for display
    h = int(time_step)
    m = int((time_step - h) * 60)
    st.sidebar.caption(f"Selected Time: **{h:02d}:{m:02d}**")

    return time_step


def sidebar_style_customization():
    st.sidebar.subheader("🎨 Map Style")
    line_weight = st.sidebar.slider("Line Thickness", 1, 10, 3)
    return line_weight


# --- RENDERING ---

def show_map(df, metric_name):
    if df.empty:
        st.warning("No data available for the selected filters.")
        return

    # Center on Nashville
    m = folium.Map(location=[36.1627, -86.7816], zoom_start=12, tiles="cartodbpositron")

    # Normalize values for color scaling
    max_val = df['value'].max() if df['value'].max() > 0 else 1

    for _, row in df.iterrows():
        # Skip rendering for zero values in speed to clear map clutter
        if metric_name == "meanSpeed" and row['value'] <= 0:
            continue

        # Convert WKT to Folium-friendly (lat, lon) coordinates
        geom = wkt.loads(row['geometry_wkt'])
        coords = [(p[1], p[0]) for p in geom.coords]

        # Color Logic
        norm = row['value'] / max_val
        if metric_name == "meanSpeed": # instead of actual speed, the color should represent actual speed / speed limit
            # Speed: Green is fast (High), Red is slow (Low)
            color = f"#{int(255 * (1 - norm)):02x}{int(255 * norm):02x}00"
        else:
            # Jams: Red is long (High), Green is short (Low)
            color = f"#{int(255 * norm):02x}{int(255 * (1 - norm)):02x}00"

        folium.PolyLine(
            locations=coords,
            color=color,
            weight=3, # lineweight
            opacity=0.8,
            tooltip=f"Link: {row['edge_id']} | Value: {row['value']:.2f}"
        ).add_to(m)

    # Render in Streamlit
    folium_static(m, width=1200, height=600)

def show_histogram(df, metric_name):
    if df is None or df.empty:
        st.warning(f"No data available for {metric_name} in this time window.")
        return

    metric_label = get_metric_label(metric_name)

    # 1. Clean and Convert
    column_name = "value"
    # Use .copy() to ensure numeric conversion sticks for Plotly
    plot_df = df[[column_name]].copy()
    plot_df[column_name] = pd.to_numeric(plot_df[column_name], errors='coerce')
    plot_df = plot_df.dropna()
    avg_val = plot_df[column_name].mean()
    std_val = plot_df[column_name].std()
    total_veh = len(plot_df)
    st.info(f"**{metric_label} Stats** | Mean: `{avg_val:.2f}` | Std Dev: `{std_val:.2f}` | Vehicles: `{total_veh:,}`")

    # 2. Plot
    fig = px.histogram(
        plot_df,
        x=column_name,
        nbins=50,
        template="plotly_white",
        color_discrete_sequence=['#2ECC71'],  # Green for vehicles
        title=f"Vehicle Distribution: {metric_label}"
    )

    fig.update_layout(
        bargap=0.1,
        xaxis_title=metric_label,
        yaxis_title="Number of Vehicles",
        # These settings force the chart to recalculate the view every time
        xaxis=dict(autorange=True),
        yaxis=dict(autorange=True),
        margin=dict(l=10, r=10, t=40, b=10),
        height=400
    )

    plot_spot = st.empty()  # holding the spot for the graph
    with plot_spot:
        st.plotly_chart(fig, use_container_width=True)


def show_cdf_distribution(df, metric_name):
    if df is None or df.empty:
        st.warning(f"No data available for {metric_name} in this time window.")
        return

    metric_label = get_metric_label(metric_name)

    # 1. Clean and Convert
    column_name = "value"
    plot_df = df[[column_name]].copy()
    plot_df[column_name] = pd.to_numeric(plot_df[column_name], errors='coerce')
    plot_df = plot_df.dropna().sort_values(by=column_name)

    # Stats
    avg_val = plot_df[column_name].mean()
    p85 = plot_df[column_name].quantile(0.85)
    n_count = len(plot_df)

    st.info(f"**{metric_label}** | Mean: `{avg_val:.2f}` | 85th %-tile: `{p85:.2f}` | N: `{n_count:,}`")

    # 2. Create the Figure (Matplotlib)
    fig, ax = plt.subplots(figsize=(10, 5))

    # Use Seaborn's ecdfplot for a clean, reliable line
    sns.ecdfplot(data=plot_df, x=column_name, ax=ax, color='#2ECC71', linewidth=2.5)

    # Add the 85th Percentile Line
    ax.axvline(p85, color='#E74C3C', linestyle='--', linewidth=2, label=f'85th % ({p85:.1f}s)')

    # Formatting
    ax.set_title(f"Cumulative Distribution: {metric_label}", fontsize=14)
    ax.set_xlabel(f"{metric_label}", fontsize=12)
    ax.set_ylabel("Cumulative Probability", fontsize=12)
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend()

    # Set y-axis to percentage
    vals = ax.get_yticks()
    ax.set_yticklabels(['{:,.0%}'.format(x) for x in vals])

    # 3. Render in Streamlit
    st.pyplot(fig)