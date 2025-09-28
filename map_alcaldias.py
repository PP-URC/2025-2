# map_alcaldias.py
# Choropleth of dropout by alcaldía + URC campuses

import sqlite3
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import os

DB_PATH = "unrc.db"
OUT_DIR = "./out_pipeline"
os.makedirs(OUT_DIR, exist_ok=True)

import requests

# File paths
BASE_DIR = os.path.dirname(__file__)
GEOJSON_FILE = os.path.join(BASE_DIR, "limite-de-las-alcaldas.json")

# Download if not present
if not os.path.exists(GEOJSON_FILE):
    url = "https://datos.cdmx.gob.mx/dataset/bae265a8-d1f6-4614-b399-4184bc93e027/resource/deb5c583-84e2-4e07-a706-1b3a0dbc99b0/download/limite-de-las-alcaldas.json"
    print(f"⬇️ Downloading GeoJSON from {url} ...")
    r = requests.get(url)
    r.raise_for_status()
    with open(GEOJSON_FILE, "wb") as f:
        f.write(r.content)
    print(f"✅ Saved to {GEOJSON_FILE}")


# --- Use uploaded file ---



# --- Load DB ---
conn = sqlite3.connect(DB_PATH)
students = pd.read_sql("SELECT * FROM students_raw", conn)
panel = pd.read_sql("SELECT * FROM inscripciones", conn)
conn.close()

# Derive abandono: last semester < 8 → dropout
panel = panel.sort_values(["student_id", "semestre"])
panel["abandono"] = 0
for sid, group in panel.groupby("student_id"):
    max_sem = group["semestre"].max()
    if max_sem < 8:
        panel.loc[(panel["student_id"] == sid) &
                  (panel["semestre"] == max_sem), "abandono"] = 1

# Merge with alcaldía
merged = panel.merge(students[["student_id", "alcaldia_residencia"]],
                     on="student_id", how="left")
dropout_map = merged.groupby("alcaldia_residencia")["abandono"].mean().reset_index()

# --- Load GeoJSON ---
gdf = gpd.read_file(GEOJSON_FILE)

# CDMX official file: alcaldía names under 'nomgeo'
merge_key = "NOMGEO"
gdf = gdf.merge(dropout_map, left_on=merge_key,
                right_on="alcaldia_residencia", how="left")

# --- Plot choropleth ---
fig, ax = plt.subplots(1, 1, figsize=(10, 8))
gdf.plot(column="abandono", cmap="Reds", legend=True,
         edgecolor="black", ax=ax, linewidth=0.5)
ax.set_title("Tasa de abandono por alcaldía (URC - datos sintéticos)", fontsize=14)

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
              marker="*", color="blue", s=120, ax=ax, label="Planteles URC")

for _, row in campuses.iterrows():
    ax.text(row["lon"], row["lat"], row["plantel"],
            fontsize=8, ha="left", va="bottom")

plt.legend()
plt.savefig(os.path.join(OUT_DIR, "figura6_alcaldias.png"), dpi=200)
plt.close()

print("✅ Saved map with URC campuses at out_pipeline/figura6_alcaldias.png")
