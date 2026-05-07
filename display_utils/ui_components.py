import streamlit as st
import folium
import pandas as pd
from streamlit_folium import folium_static
from shapely import wkt
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# --- UI COMPONENTS ---
def sidebar_job_selector(con):
    st.sidebar.subheader("📁 Simulation Data")
    jobs = con.execute("SELECT job_id, scenario FROM sim_jobs").df()
    if not jobs.empty:
        jobs['label'] = jobs['job_id'] + " (" + jobs['scenario'] + ")"
        selected_label = st.sidebar.selectbox("Select Sim Job", jobs['label'])
        return selected_label.split(" ")[0]
    return None


def sidebar_edge_metric_selector():
    st.sidebar.subheader("Traffic Metrics")
    metrics = {
        "meanSpeed": "Avg Speed (mph)",
        "maxJamLengthInMeters": "Queue Length (miles)",
        "meanOccupancy": "Lane Occupancy (%)",

    }
    label = st.sidebar.selectbox("Attribute", list(metrics.values()))
    return [k for k, v in metrics.items() if v == label][0]

def sidebar_vehicle_metric_selector():
    st.sidebar.subheader("Vehicle Metrics (TripInfo)")
    v_metrics = {
        "duration": "Trip Duration (minutes)",
        'routeLength': "Trip Distance (miles)",
        "waitingTime": "Total Waiting (minutes)"
    }
    label = st.sidebar.selectbox("Vehicle Attribute", list(v_metrics.values()))
    return [k for k, v in v_metrics.items() if v == label][0]

def sidebar_time_selector():
    st.sidebar.subheader("🕒 Temporal Control")

    # 24 hours * 4 quarters per hour = 96 total steps
    time_step = st.sidebar.slider(
        "Time of Day",
        min_value=0,
        max_value=95,
        value=32,  # Defaults to 8:00 AM (8 * 4)
        step=1,
        format=""  # We will use the label below for better readability
    )

    # Calculate hours and minutes for display
    h = time_step // 4
    m = (time_step % 4) * 15
    st.sidebar.caption(f"Selected Time: **{h:02d}:{m:02d}**")

    return time_step


def sidebar_style_customization():
    st.sidebar.subheader("🎨 Map Style")
    style_dict = {
        "Light": "mapbox://styles/mapbox/light-v9",
        "Dark": "mapbox://styles/mapbox/dark-v9",
        "Satellite": "mapbox://styles/mapbox/satellite-v9",
        "Road": "mapbox://styles/mapbox/streets-v11"
    }
    style = st.sidebar.selectbox("Basemap", list(style_dict.keys()))
    line_weight = st.sidebar.slider("Line Thickness", 1, 10, 3)
    return style_dict[style], line_weight


# --- RENDERING ---

def show_map(df, metric_name, map_style, line_weight):
    if df.empty:
        st.warning("No data available for the selected filters.")
        return

    # Center on Nashville
    m = folium.Map(location=[36.1627, -86.7816], zoom_start=12, tiles="cartodbpositron")

    # Normalize values for color scaling
    max_val = df['value'].max() if df['value'].max() > 0 else 1

    for _, row in df.iterrows():
        # Convert WKT to Folium-friendly (lat, lon) coordinates
        geom = wkt.loads(row['geometry_wkt'])
        coords = [(p[1], p[0]) for p in geom.coords]

        # Color Logic
        norm = row['value'] / max_val
        if metric_name == "meanSpeed":
            # Speed: Green is fast (High), Red is slow (Low)
            color = f"#{int(255 * (1 - norm)):02x}{int(255 * norm):02x}00"
        else:
            # Jams: Red is long (High), Green is short (Low)
            color = f"#{int(255 * norm):02x}{int(255 * (1 - norm)):02x}00"

        folium.PolyLine(
            locations=coords,
            color=color,
            weight=line_weight,
            opacity=0.8,
            tooltip=f"Link: {row['edge_id']} | Value: {row['value']:.2f}"
        ).add_to(m)

    # Render in Streamlit
    folium_static(m, width=1200, height=600)

def show_histogram(df, metric_name):
    if df is None or df.empty:
        st.warning(f"No data available for {metric_name} in this time window.")
        return

    # 1. Clean and Convert
    column_name = "value"
    # Use .copy() to ensure numeric conversion sticks for Plotly
    plot_df = df[[column_name]].copy()
    plot_df[column_name] = pd.to_numeric(plot_df[column_name], errors='coerce')
    plot_df = plot_df.dropna()
    avg_val = plot_df[column_name].mean()
    std_val = plot_df[column_name].std()
    total_veh = len(plot_df)
    st.info(f"**{metric_name} Stats** | Mean: `{avg_val:.2f}` | Std Dev: `{std_val:.2f}` | Vehicles: `{total_veh:,}`")

    # 2. Plot
    fig = px.histogram(
        plot_df,
        x=column_name,
        nbins=50,
        template="plotly_white",
        color_discrete_sequence=['#2ECC71'],  # Green for vehicles
        title=f"Vehicle Distribution: {column_name}"
    )

    fig.update_layout(
        bargap=0.1,
        xaxis_title=metric_name,
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

        # 1. Clean and Convert
    column_name = "value"
    plot_df = df[[column_name]].copy()
    plot_df[column_name] = pd.to_numeric(plot_df[column_name], errors='coerce')
    plot_df = plot_df.dropna().sort_values(by=column_name)

    # Stats
    avg_val = plot_df[column_name].mean()
    p85 = plot_df[column_name].quantile(0.85)
    n_count = len(plot_df)

    st.info(f"**{metric_name}** | Mean: `{avg_val:.2f}` | 85th %-tile: `{p85:.2f}` | N: `{n_count:,}`")

    # 2. Create the Figure (Matplotlib)
    fig, ax = plt.subplots(figsize=(10, 5))

    # Use Seaborn's ecdfplot for a clean, reliable line
    sns.ecdfplot(data=plot_df, x=column_name, ax=ax, color='#2ECC71', linewidth=2.5)

    # Add the 85th Percentile Line
    ax.axvline(p85, color='#E74C3C', linestyle='--', linewidth=2, label=f'85th % ({p85:.1f}s)')

    # Formatting
    ax.set_title(f"Cumulative Distribution: {metric_name}", fontsize=14)
    ax.set_xlabel(f"{metric_name} (Seconds)", fontsize=12)
    ax.set_ylabel("Cumulative Probability", fontsize=12)
    ax.grid(True, linestyle=':', alpha=0.6)
    ax.legend()

    # Set y-axis to percentage
    vals = ax.get_yticks()
    ax.set_yticklabels(['{:,.0%}'.format(x) for x in vals])

    # 3. Render in Streamlit
    st.pyplot(fig)