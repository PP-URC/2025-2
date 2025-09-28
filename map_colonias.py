# map_colonias.py
import os, sqlite3, requests, unicodedata
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from generate_colonias import COLONIAS_FILE, COLONIAS_URL, OUT_DIR


os.makedirs(OUT_DIR, exist_ok=True)

DB_PATH = "unrc.db"


if not os.path.exists(COLONIAS_FILE):
    r = requests.get(COLONIAS_URL, timeout=90)
    r.raise_for_status()
    with open(COLONIAS_FILE, "wb") as f:
        f.write(r.content)

gdf_col = gpd.read_file(COLONIAS_FILE)

def norm(s):
    if pd.isna(s): return s
    s = str(s)
    s = unicodedata.normalize("NFKD", s).encode("ASCII","ignore").decode("utf-8")
    return s.upper().strip()

# Load DB + compute risk by colonia
conn = sqlite3.connect(DB_PATH)
students = pd.read_sql("SELECT * FROM students_raw", conn)
panel    = pd.read_sql("SELECT * FROM inscripciones", conn)
conn.close()

# You may want predicted probs; if not available, use raw abandono mean per colonia (last rows)
merged = panel.merge(students[["student_id","colonia_residencia"]], on="student_id", how="left")
risk_by_col = merged.groupby("colonia_residencia")["abandono"].mean().reset_index()
risk_by_col["key"] = risk_by_col["colonia_residencia"].map(norm)

col_name = [c for c in gdf_col.columns if c.lower()=="colonia"]
if not col_name:
    col_name = [c for c in gdf_col.columns if c.lower() in ("nomgeo","nombre")]
col_name = col_name[0]

gdf_col["key"] = gdf_col[col_name].map(norm)
gdf_col = gdf_col.merge(risk_by_col[["key","abandono"]], on="key", how="left")
gdf_col["abandono"] = gdf_col["abandono"].fillna(0.0)

fig, ax = plt.subplots(figsize=(10,10))
gdf_col.plot(column="abandono", cmap="Reds", legend=True, ax=ax,
             legend_kwds={"label":"Abandono observado", "orientation":"vertical"})
ax.set_title("Abandono observado por colonia")
ax.axis("off")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR,"map_colonias_abandono.png"))
plt.close()

print("✅ Saved:", os.path.join(OUT_DIR,"map_colonias_abandono.png"))
