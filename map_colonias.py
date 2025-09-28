# map_colonias.py
"""
import os, sqlite3, requests, unicodedata
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from generate_colonias import COLONIAS_FILE, COLONIAS_URL, DB_PATH 
from generate_final_report import OUT_DIR

os.makedirs(OUT_DIR, exist_ok=True)


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
"""


# map_colonias.py
import os, sqlite3, requests, unicodedata
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from generate_colonias import COLONIAS_FILE, COLONIAS_URL, OUT_DIR, DB_PATH


os.makedirs(OUT_DIR, exist_ok=True)


# Download colonias file if missing
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

# --- Load DB + compute risk by colonia ---
conn = sqlite3.connect(DB_PATH)
students = pd.read_sql("SELECT * FROM students_raw", conn)
panel    = pd.read_sql("SELECT * FROM inscripciones", conn)
conn.close()

merged = panel.merge(students[["student_id","colonia_residencia"]],
                     on="student_id", how="left")
risk_by_col = merged.groupby("colonia_residencia")["abandono"].mean().reset_index()
risk_by_col["key"] = risk_by_col["colonia_residencia"].map(norm)

# Match colonias column name
col_name = [c for c in gdf_col.columns if c.lower()=="colonia"]
if not col_name:
    col_name = [c for c in gdf_col.columns if c.lower() in ("nomgeo","nombre")]
col_name = col_name[0]

gdf_col["key"] = gdf_col[col_name].map(norm)
gdf_col = gdf_col.merge(risk_by_col[["key","abandono"]], on="key", how="left")
gdf_col["abandono"] = gdf_col["abandono"].fillna(0.0)

# --- Define planteles (URC campuses) ---
planteles = pd.DataFrame({
    "nombre": ["URC Norte","URC Centro","URC Sur"],
    "lon": [-99.14,-99.10,-99.16],
    "lat": [19.50,19.43,19.29],
    "color": ["blue","green","purple"]
})

# --- Plot map ---
fig, ax = plt.subplots(figsize=(12,12))

# Choropleth of colonias
gdf_col.plot(column="abandono", cmap="Reds", legend=True, ax=ax,
             legend_kwds={"label":"Tasa de abandono", "orientation":"vertical"},
             linewidth=0.1, edgecolor="gray")

# Overlay planteles
for _, row in planteles.iterrows():
    ax.scatter(row["lon"], row["lat"], c=row["color"], s=80, marker="o", edgecolor="black")
    ax.text(row["lon"], row["lat"]+0.01, row["nombre"],
            fontsize=9, ha="center", va="bottom",
            bbox=dict(boxstyle="round,pad=0.2", fc="white", alpha=0.7))

ax.set_title("Abandono observado por colonia y planteles URC en CDMX", fontsize=14)
ax.axis("off")

plt.tight_layout()
outpath = os.path.join(OUT_DIR,"map_colonias_abandono_planteles.png")
plt.savefig(outpath, dpi=150)
plt.close()

print("✅ Saved:", outpath)

