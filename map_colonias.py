# map_colonias.py
# Choropleth of dropout by colonia + URC campuses

import sqlite3
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import os
import requests





DB_PATH = "unrc.db"
OUT_DIR = "./out_pipeline"
os.makedirs(OUT_DIR, exist_ok=True)

# --- Ensure GeoJSON ---
BASE_DIR = os.path.dirname(__file__)
GEOJSON_FILE = os.path.join(BASE_DIR, "coloniascdmx.geojson")

if not os.path.exists(GEOJSON_FILE):
    url = "https://datos.cdmx.gob.mx/dataset/04a1900a-0c2f-41ed-94dc-3d2d5bad4065/resource/f1408eeb-4e97-4548-bc69-61ff83838b1d/download/coloniascdmx.geojson"
    print("⬇️ Downloading colonias GeoJSON...")
    r = requests.get(url)
    r.raise_for_status()
    with open(GEOJSON_FILE, "wb") as f:
        f.write(r.content)
    print(f"✅ Saved {GEOJSON_FILE}")

# --- Load DB ---
conn = sqlite3.connect(DB_PATH)
students = pd.read_sql("SELECT * FROM students_raw", conn)
panel = pd.read_sql("SELECT * FROM inscripciones", conn)
conn.close()

# Derive abandono
panel = panel.sort_values(["student_id", "semestre"])
panel["abandono"] = 0
for sid, group in panel.groupby("student_id"):
    max_sem = group["semestre"].max()
    if max_sem < 8:
        panel.loc[(panel["student_id"] == sid) &
                  (panel["semestre"] == max_sem), "abandono"] = 1

# Merge with colonias
merged = panel.merge(students[["student_id", "colonia_residencia"]],
                     on="student_id", how="left")
dropout_map = merged.groupby("colonia_residencia")["abandono"].mean().reset_index()

# --- Load GeoJSON ---

gdf = gpd.read_file(GEOJSON_FILE, engine="pyogrio")

# Detect name column
possible_keys = ["nom_col", "NOM_COL", "colonia", "NOMBRE"]
merge_key = None
for k in possible_keys:
    if k in gdf.columns:
        merge_key = k
        break
if merge_key is None:
    raise KeyError(f"No colonia name column found. Available: {list(gdf.columns)}")

print(f"ℹ️ Using '{merge_key}' for merge")

# Merge dropout data
gdf = gdf.merge(dropout_map, left_on=merge_key,
                right_on="colonia_residencia", how="left")

# --- Plot choropleth ---
fig, ax = plt.subplots(1, 1, figsize=(14, 12))
gdf.plot(column="abandono", cmap="Reds", legend=True,
         edgecolor="black", ax=ax, linewidth=0.1)
ax.set_title("Tasa de abandono por colonia (URC - datos sintéticos)", fontsize=14)

# --- Add URC campuses ---
campuses = pd.DataFrame({
    "plantel": [
        "Cuautepec (GAM)", "Gustavo A. Madero", "Iztapalapa I",
        "Iztapalapa II", "Benito Juárez", "Azcapotzalco", "Coyoacán"
    ],
    "lat": [19.5586, 19.4855, 19.3553, 19.3826, 19.3731, 19.4822, 19.3019],
    "lon": [-99.1379, -99.1344, -99.0555, -99.0098, -99.1835, -99.1764, -99.1465]
})

campuses.plot(kind="scatter", x="lon", y="lat",
              marker="*", color="blue", s=100, ax=ax, label="Planteles URC")

for _, row in campuses.iterrows():
    ax.text(row["lon"], row["lat"], row["plantel"], fontsize=7, ha="left", va="bottom")

plt.legend()
plt.savefig(os.path.join(OUT_DIR, "figura_colonias.png"), dpi=200)
plt.close()

print("✅ Saved map with URC campuses at out_pipeline/figura_colonias.png")
