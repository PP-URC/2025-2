import sqlite3
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import json
from shapely.geometry import shape
import os

DB_PATH = "unrc.db"
COLONIAS_FILE = "catlogo-de-colonias.json"
OUT_DIR = "./out_pipeline"
os.makedirs(OUT_DIR, exist_ok=True)

# --- Load colonias GeoJSON ---
print("📥 Loading colonias...")
with open(COLONIAS_FILE, "r", encoding="utf-8") as f:
    raw = json.load(f)

features = raw["features"]
rows = []
for ft in features:
    props = ft["properties"]
    geom = shape(ft["geometry"])
    props["geometry"] = geom
    rows.append(props)

gdf_colonias = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")

# Ensure column is called 'colonia_residencia'
if "colonia" in gdf_colonias.columns:
    gdf_colonias = gdf_colonias.rename(columns={"colonia": "colonia_residencia"})

print("✅ Colonias loaded:", len(gdf_colonias))

# --- Load dropout data from DB ---
conn = sqlite3.connect(DB_PATH)
students = pd.read_sql("SELECT * FROM students_raw", conn)
panel = pd.read_sql("SELECT * FROM inscripciones", conn)
conn.close()

# Derive abandono: last semester dropout if <8
panel = panel.sort_values(["student_id", "semestre"])
panel["abandono"] = 0
for sid, group in panel.groupby("student_id"):
    max_sem = group["semestre"].max()
    if max_sem < 8:
        panel.loc[(panel["student_id"]==sid) & (panel["semestre"]==max_sem),"abandono"] = 1

# Merge dropout with student colonias
merged = panel.merge(students[["student_id","colonia_residencia"]], on="student_id", how="left")

dropout_map = merged.groupby("colonia_residencia")["abandono"].mean().reset_index()

# --- Join with polygons ---
gdf = gdf_colonias.merge(dropout_map, on="colonia_residencia", how="left")

# --- Plot ---
fig, ax = plt.subplots(1, 1, figsize=(12, 12))
gdf.plot(column="abandono", cmap="Reds", linewidth=0.5, edgecolor="black",
         legend=True, ax=ax, missing_kwds={"color": "lightgrey", "label": "Sin datos"})
ax.set_title("Tasa de abandono por colonia (sintético)", fontsize=16)

out_file = os.path.join(OUT_DIR, "mapa_abandono_colonias.png")
plt.savefig(out_file, dpi=150)
plt.close()

print(f"✅ Map saved to {out_file}")
