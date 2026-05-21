import os
import duckdb

MOTHERDUCK_PATH = os.getenv("MOTHERDUCK_PATH", "md:sumo_visualization")
con = duckdb.connect(MOTHERDUCK_PATH)

print("Checking gis_layer_baseline geometry sample...")
try:
    res = con.execute("SELECT geometry_wkt FROM \"sumo_visualization\".\"bronze\".\"gis_layer_baseline\" LIMIT 1").fetchone()
    if res:
        print(f"Sample: {res[0][:100]}...")
    else:
        print("No data in gis_layer_baseline")
except Exception as e:
    print(f"Error: {e}")

print("\nChecking a few edge IDs...")
try:
    res = con.execute("SELECT id FROM \"sumo_visualization\".\"bronze\".\"gis_layer_baseline\" LIMIT 5").fetchall()
    print(f"Edge IDs: {res}")
except Exception as e:
    print(f"Error: {e}")

print("\nChecking a few e2 IDs...")
try:
    res = con.execute("SELECT id FROM \"sumo_visualization\".\"bronze\".\"bronze_e2\" LIMIT 5").fetchall()
    print(f"e2 IDs: {res}")
except Exception as e:
    print(f"Error: {e}")
