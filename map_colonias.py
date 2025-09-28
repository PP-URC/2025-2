import sqlite3
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import json
from shapely.geometry import shape
import os
import matplotlib.patheffects as path_effects


DB_PATH = "unrc.db"
COLONIAS_FILE = "catlogo-de-colonias.json"
OUT_DIR = "./out_pipeline"
os.makedirs(OUT_DIR, exist_ok=True)

# --- Load colonias ---
with open(COLONIAS_FILE, "r") as f:
    raw = json.load(f)

features = raw["features"]
rows = []
for ft in features:
    props = ft["properties"]
    geom = shape(ft["geometry"])
    props["geometry"] = geom
    rows.append(props)

gdf_colonias = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")

if "colonia" in gdf_colonias.columns:
    gdf_colonias = gdf_colonias.rename(columns={"colonia": "colonia_residencia"})

# --- Load dropout from DB ---
conn = sqlite3.connect(DB_PATH)
students = pd.read_sql("SELECT * FROM students_raw", conn)
panel = pd.read_sql("SELECT * FROM inscripciones", conn)
conn.close()

dropout_map = panel.merge(
    students[["student_id","colonia_residencia"]],
    on="student_id", how="left"
).groupby("colonia_residencia")["abandono"].mean().reset_index()

gdf = gdf_colonias.merge(dropout_map, on="colonia_residencia", how="left")

# --- Planteles (example coords, replace with real) ---
planteles = pd.DataFrame({
    "plantel": ["Azcapotzalco","Coyoacán","Gustavo A. Madero","Iztapalapa"],
    "lon": [-99.185, -99.150, -99.120, -99.080],
    "lat": [19.490, 19.330, 19.470, 19.350]
})
gdf_planteles = gpd.GeoDataFrame(
    planteles,
    geometry=gpd.points_from_xy(planteles["lon"], planteles["lat"]),
    crs="EPSG:4326"
)

# --- Plot ---
fig, ax = plt.subplots(1, 1, figsize=(12, 12))
gdf.plot(column="abandono", cmap="Reds", linewidth=0.5, edgecolor="black",
         legend=True, ax=ax, missing_kwds={"color": "lightgrey", "label": "Sin datos"})

colors = ["blue","green","orange","purple"]
for i, row in gdf_planteles.iterrows():
    ax.scatter(row.geometry.x, row.geometry.y, color=colors[i % len(colors)], s=100, marker="o", edgecolor="white", linewidth=1.5, zorder=5)
    ax.text(row.geometry.x, row.geometry.y, row["plantel"],
            fontsize=9, ha="left", va="bottom", color="white",
            path_effects=[plt.matplotlib.patheffects.withStroke(linewidth=2, foreground="black")])

ax.set_title("Tasa de abandono por colonia con planteles", fontsize=16)
plt.savefig(os.path.join(OUT_DIR, "mapa_abandono_colonias_con_planteles.png"), dpi=150)
plt.close()
