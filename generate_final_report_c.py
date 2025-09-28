# generate_final_report_c.py
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import geopandas as gpd
import matplotlib as mpl

DB_PATH = "unrc.db"
COLONIAS_FILE = "catlogo-de-colonias.json"

# --- Load data ---
conn = sqlite3.connect(DB_PATH)
students = pd.read_sql("SELECT * FROM students_raw", conn)
inscripciones = pd.read_sql("SELECT * FROM inscripciones", conn)
conn.close()

# Merge for analysis
merged = inscripciones.merge(students, on="student_id", how="left")

# --- Summary statistics ---
abandono_rate = merged["abandono"].mean()
print(f"📊 Tasa global de abandono: {abandono_rate:.2%}")

# --- Choropleth map ---
gdf = gpd.read_file(COLONIAS_FILE)
gdf = gdf.rename(columns={"colonia": "colonia_residencia"})

dropout_map = merged.groupby("colonia_residencia")["abandono"].mean().reset_index()
gdf = gdf.merge(dropout_map, on="colonia_residencia", how="left")

fig, ax = plt.subplots(figsize=(12,12))
gdf.plot(column="abandono", cmap="RdYlGn_r", legend=True,
         legend_kwds={"label":"Tasa de abandono promedio"},
         ax=ax, edgecolor="black", linewidth=0.2)

# Planteles demo coords
planteles = pd.DataFrame({
    "plantel":["Plantel Norte","Plantel Centro","Plantel Sur"],
    "lon":[-99.15,-99.12,-99.18],
    "lat":[19.5,19.4,19.3]
})
gdfp = gpd.GeoDataFrame(planteles,
                        geometry=gpd.points_from_xy(planteles.lon, planteles.lat),
                        crs="EPSG:4326")

gdfp.plot(ax=ax, color="blue", markersize=40)

for _, row in gdfp.iterrows():
    ax.text(row.geometry.x, row.geometry.y, row["plantel"],
            fontsize=9, color="white", ha="center", va="center",
            path_effects=[mpl.patheffects.withStroke(linewidth=2, foreground="black")])

ax.set_title("Tasa de abandono por colonia con planteles", fontsize=14)
plt.savefig("out_pipeline/map_colonias.png", dpi=300)

print("✅ Map saved to out_pipeline/map_colonias.png")
