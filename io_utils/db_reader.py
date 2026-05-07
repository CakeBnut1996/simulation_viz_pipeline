import duckdb, os
import pandas as pd
import geopandas as gpd

def load_table_to_df(table_name, db_conn, job_id=None):
    """
    Reads a DuckDB table into a Pandas DataFrame.
    If job_id is provided, it filters the data for that specific simulation run.
    """
    try:
        if job_id:
            query = f"SELECT * FROM {table_name} WHERE sim_job_id = ?"
            df = db_conn.execute(query, [job_id]).df()
        else:
            query = f"SELECT * FROM {table_name}"
            df = db_conn.execute(query).df()

        print(f"📖 Loaded {len(df)} rows from '{table_name}'")
        return df
    except Exception as e:
        print(f"❌ Error reading table '{table_name}': {e}")
        return pd.DataFrame()  # Return empty DF on failure
    
def load_gis_to_df(db_path, table_name, crs="EPSG:3857"):
    """Reads a table from DuckDB and returns a GeoDataFrame."""
    conn = duckdb.connect(db_path)

    # Just select everything. If you saved it using .to_wkb(),
    # the geometry column is already a BLOB containing WKB.
    query = f"SELECT * FROM {table_name}"
    df = conn.execute(query).df()
    conn.close()

    # Convert the WKB column to actual geometries and create GDF in one step
    df['geometry'] = df['geometry'].apply(lambda x: bytes(x) if isinstance(x, bytearray) else x)
    geometry = gpd.GeoSeries.from_wkb(df['geometry'])
    gdf = gpd.GeoDataFrame(df.drop(columns=['geometry']), geometry=geometry, crs=crs)

    return gdf