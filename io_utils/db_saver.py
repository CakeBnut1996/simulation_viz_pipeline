import duckdb, os
import pandas as pd
import xml.etree.ElementTree as ET
import geopandas as gpd


def register_or_update_job(job_id, scenario_name, notes, db_conn):
    """Updates the job metadata if it exists, otherwise creates it."""
    db_conn.execute("""
        CREATE TABLE IF NOT EXISTS sim_jobs (
            job_id VARCHAR PRIMARY KEY, 
            scenario VARCHAR, 
            runtime TIMESTAMP, 
            notes VARCHAR
        )
    """)

    # Check if job exists
    exists = db_conn.execute("SELECT 1 FROM sim_jobs WHERE job_id = ?", [job_id]).fetchone()

    if exists:
        # Update existing record
        db_conn.execute("""
            UPDATE sim_jobs 
            SET scenario = ?, runtime = now(), notes = ? 
            WHERE job_id = ?
        """, [scenario_name, notes, job_id])
        print(f"🔄 Updated metadata for job: {job_id}")
    else:
        # Insert new record
        db_conn.execute("INSERT INTO sim_jobs VALUES (?, ?, now(), ?)", [job_id, scenario_name, notes])
        print(f"📝 Registered new job: {job_id}")


def save_e2_to_db(xml_path, job_id, db_conn, rewrite=True):
    """
    Parses E2 XML and saves to DB.
    If rewrite=True, it removes existing data for this job_id first.
    """
    # 1. Parse XML
    tree = ET.parse(xml_path)
    data = [el.attrib for el in tree.getroot().findall('interval')]

    if not data:
        print(f"⚠️ No E2 data found in {xml_path}")
        return

    df = pd.DataFrame(data)
    df['sim_job_id'] = job_id
    df['id'] = df['id'].str.replace('^e2_', '', regex=True) # remove prefix

    # 2. Numeric Conversion
    cols = [
        'begin', 'end', 'sampledSeconds', 'nVehEntered', 'nVehLeft',
        'nVehSeen', 'meanSpeed', 'meanTimeLoss', 'meanOccupancy',
        'maxOccupancy', 'meanMaxJamLengthInVehicles', 'meanMaxJamLengthInMeters',
        'maxJamLengthInVehicles', 'maxJamLengthInMeters', 'jamLengthInVehiclesSum',
        'jamLengthInMetersSum', 'meanHaltingDuration', 'maxHaltingDuration',
        'haltingDurationSum', 'meanIntervalHaltingDuration', 'maxIntervalHaltingDuration',
        'intervalHaltingDurationSum', 'startedHalts', 'meanVehicleNumber', 'maxVehicleNumber'
    ]
    for col in cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    if 'meanSpeed' in df.columns:
        # 1 m/s ≈ 2.23694 mph
        # Note: SUMO uses -1.0 for intervals with no vehicles.
        # We keep -1.0 as is or set to 0 to avoid weird math.
        df.loc[df['meanSpeed'] > 0, 'meanSpeed'] = df['meanSpeed'] * 2.23694
        df.loc[df['meanSpeed'] < 0, 'meanSpeed'] = 0  # Optional: Clean up "no data" values
    # Convert distance: meters to miles (1 m ≈ 0.000621371 miles)
    if 'meanMaxJamLengthInMeters' in df.columns:
        df['meanMaxJamLengthInMeters'] = df['meanMaxJamLengthInMeters'] * 0.000621371

    # 3. Create table if it doesn't exist
    db_conn.execute("CREATE TABLE IF NOT EXISTS all_e2 AS SELECT * FROM df WHERE 1=0")

    # 4. Handle Rewrite (The "Clean" Step)
    if rewrite:
        db_conn.execute("DELETE FROM all_e2 WHERE sim_job_id = ?", [job_id])

    # 5. Insert New Data
    db_conn.execute("INSERT INTO all_e2 SELECT * FROM df")
    print(f"✅ Job '{job_id}' data {'rewritten' if rewrite else 'appended'} in all_e2 table.")


def save_tripinfo_to_db(xml_path, job_id, db_conn, rewrite=True):
    """
    Parses TripInfo XML and saves to a master DuckDB table.
    If rewrite=True, it clears existing data for the specific job_id first.
    """
    # 1. Parse XML
    tree = ET.parse(xml_path)
    data = [el.attrib for el in tree.getroot().findall('tripinfo')]

    if not data:
        print(f"⚠️ No trip data found in {xml_path}")
        return

    df = pd.DataFrame(data)
    df['sim_job_id'] = job_id

    # 2. Numeric Conversion
    cols_to_fix = [
        'depart', 'departPos', 'departSpeed', 'departDelay',
        'arrival', 'arrivalPos', 'arrivalSpeed', 'duration',
        'routeLength', 'waitingTime', 'waitingCount', 'stopTime',
        'timeLoss', 'rerouteNo', 'speedFactor'
    ]
    for col in cols_to_fix:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    # Convert speeds: m/s to mph (1 m/s ≈ 2.23694 mph)
    speed_cols = ['departSpeed', 'arrivalSpeed']
    for col in speed_cols:
        if col in df.columns:
            df[col] = df[col] * 2.23694
    # Convert distance: meters to miles (1 m ≈ 0.000621371 miles)
    if 'routeLength' in df.columns:
        df['routeLength'] = df['routeLength'] * 0.000621371
    time_cols = ['duration', 'waitingTime', 'stopTime', 'timeLoss']
    for col in time_cols:
        if col in df.columns:
            df[col] = df[col] / 60  # Convert seconds to minutes

    # 3. Ensure the master table exists
    # We create it based on the dataframe structure if it's missing
    db_conn.execute(f"CREATE TABLE IF NOT EXISTS all_trips AS SELECT * FROM df WHERE 1=0")

    # 4. Handle Rewrite Logic
    if rewrite:
        # Delete only the rows belonging to this specific job
        db_conn.execute(f"DELETE FROM all_trips WHERE sim_job_id = ?", [job_id])

    # 5. Append the new data
    db_conn.execute(f"INSERT INTO all_trips SELECT * FROM df")

    action = "rewritten" if rewrite else "appended"
    print(f"✅ TripInfo for Job '{job_id}' {action} in table all_trips.")


def save_shp_to_4326db(shp_path, job_id, table_name, db_conn):
    """Saves Shapefile geometry to DuckDB after ensuring correct CRS."""
    # Load and transform
    gdf = gpd.read_file(shp_path)
    gdf['sim_job_id'] = job_id

    # EPSG:4326 check
    if gdf.crs != "EPSG:4326":
        gdf = gdf.to_crs(epsg=4326)

    # Convert geometry to string (WKT) for DB compatibility
    gdf['geometry_wkt'] = gdf.geometry.apply(lambda x: x.wkt)
    df = pd.DataFrame(gdf.drop(columns='geometry'))

    db_conn.execute(f"CREATE OR REPLACE TABLE {table_name} AS SELECT * FROM df")
    print(f"✅ Geometry table '{table_name}' created/overwritten.")


def export_table_to_parquet(table_name, output_path, db_conn):
    """Exports a specific DB table to a Parquet file for external use."""
    db_conn.execute(f"COPY {table_name} TO '{output_path}' (FORMAT PARQUET)")
    print(f"📦 Exported {table_name} to {output_path}")


def inspect_database(db_path):
    # 1. Check File Info
    if os.path.exists(db_path):
        size_bytes = os.path.getsize(db_path)
        size_mb = size_bytes / (1024 * 1024)
        print(f"📂 Database File: {os.path.abspath(db_path)}")
        print(f"⚖️  File Size: {size_mb:.2f} MB")
    else:
        print("❌ Database file not found at the specified path.")
        return

    # 2. Connect and Inspect Tables
    with duckdb.connect(db_path) as con:
        # Get list of all tables
        tables = con.execute("SHOW TABLES").df()

        if tables.empty:
            print("ℹ️  The database is currently empty (no tables found).")
            return

        print("\n📊 Database Structure:")
        print("-" * 50)

        for table_name in tables['name']:
            # Get row count
            row_count = con.execute(f"SELECT count(*) FROM {table_name}").fetchone()[0]

            # Get column info
            columns = con.execute(f"DESCRIBE {table_name}").df()
            col_names = ", ".join(columns['column_name'].tolist())

            print(f"Table: **{table_name}**")
            print(f"  └─ Rows: {row_count:,}")
            print(f"  └─ Columns: {col_names}")
            print("-" * 50)