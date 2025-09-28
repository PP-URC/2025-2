# map_colonias.py
import sqlite3, os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt

DB_PATH = "unrc.db"
COLONIAS_FILE = "catlogo-de-colonias.json"
OUT_DIR = "./out_pipeline"
os.makedirs(OUT_DIR, exist_ok=True)

# --- Leer colonias ---
gdf = gpd.read_file(COLONIAS_FILE)
print("Campos colonias:", gdf.columns)

# --- Cargar DB ---
conn = sqlite3.connect(DB_PATH)
students = pd.read_sql("SELECT * FROM students_raw", conn)
panel = pd.read_sql("SELECT * FROM inscripciones", conn)
conn.close()

# --- Derivar abandono ---
panel = panel.sort_values(["student_id","semestre"])
panel["abandono"] = 0
for sid, group in panel.groupby("student_id"):
    max_sem = group["semestre"].max()
    if max_sem < 8:
        panel.loc[(panel["student_id"]==sid) &
                  (panel["semestre"]==max_sem),"abandono"] = 1

merged = panel.merge(students[["student_id","colonia_residencia"]],
                     on="student_id")
dropout_map = merged.groupby("colonia_residencia")["abandono"].mean().reset_index()

# --- Unir ---
merge_key = "nom_col"  # nombre de la colonia en el GeoJSON
gdf = gdf.merge(dropout_map, left_on=merge_key,
                right_on="colonia_residencia", how="left")

# --- Graficar ---
fig, ax = plt.subplots(figsize=(12,10))
gdf.plot(column="abandono", cmap="Reds", legend=True,
         edgecolor="black", ax=ax, linewidth=0.1)
ax.set_title("Tasa de abandono por colonia (URC - datos sintéticos)")

plt.savefig(os.path.join(OUT_DIR,"mapa_colonias.png"), dpi=200)
plt.close()

print("✅ Mapa guardado en out_pipeline/mapa_colonias.png")
