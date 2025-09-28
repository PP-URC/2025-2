# generator_sqlite_unrc_colonias.py
# Generate synthetic UNRC student + enrollment data with colonias of CDMX

import sqlite3
import pandas as pd
import numpy as np
import geopandas as gpd
import json
from shapely.geometry import shape

DB_PATH = "unrc.db"
COLONIAS_FILE = "catlogo-de-colonias.json"

# --- Load colonias robustly ---
with open(COLONIAS_FILE, "r", encoding="utf-8") as f:
    raw = json.load(f)

features = raw["features"]
rows = []
for ft in features:
    props = ft["properties"]
    props["geometry"] = shape(ft["geometry"])
    rows.append(props)

gdf_colonias = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:4326")

# Keep only colonia + alcaldía names
colonias = gdf_colonias[["nom_col", "nom_alc"]].drop_duplicates()
colonias = colonias.rename(columns={"nom_col":"colonia", "nom_alc":"alcaldia"})

# --- Generate students ---
np.random.seed(42)
N = 1000

students = pd.DataFrame({
    "student_id": range(1, N+1),
    "sexo": np.random.choice(["M","F"], size=N),
    "fecha_nacimiento": pd.to_datetime(
        np.random.randint(pd.Timestamp("1995-01-01").value,
                          pd.Timestamp("2005-12-31").value, size=N)
    ),
    "colonia_residencia": np.random.choice(colonias["colonia"], size=N),
    "ingreso_familiar": np.random.choice([2000,5000,10000,15000],
                                         size=N, p=[0.3,0.4,0.2,0.1]),
    "personas_hogar": np.random.randint(2,7,size=N),
    "horas_trabajo": np.random.choice([0,10,20,30,40],
                                      size=N, p=[0.5,0.2,0.15,0.1,0.05]),
    "traslado_min": np.random.choice([15,30,45,60,90],
                                     size=N, p=[0.1,0.3,0.3,0.2,0.1]),
    "dispositivo_propio": np.random.choice([0,1], size=N, p=[0.2,0.8]),
    "internet_casa": np.random.choice([0,1], size=N, p=[0.15,0.85])
})

# --- Generate enrollments (inscripciones) ---
rows = []
for sid in students["student_id"]:
    semestres = np.random.randint(1, 9)  # up to 8 semesters
    for sem in range(1, semestres+1):
        promedio = np.clip(np.random.normal(80,10), 50, 100)
        materias = 5
        aprobadas = np.random.binomial(materias, promedio/100)
        reprobadas = materias - aprobadas
        asistencia = np.clip(np.random.normal(0.85,0.1), 0, 1)
        beca = np.random.choice([0,1], p=[0.7,0.3])
        tutoria = np.random.choice([0,1], p=[0.8,0.2])
        rows.append([sid, sem, promedio, materias, aprobadas,
                     reprobadas, beca, tutoria, asistencia])

inscripciones = pd.DataFrame(rows, columns=[
    "student_id","semestre","promedio","materias_inscritas",
    "materias_aprobadas","materias_reprobadas",
    "beca","apoyo_tutoria","asistencia_pct"
])

# --- Save to SQLite ---
conn = sqlite3.connect(DB_PATH)
students.to_sql("students_raw", conn, if_exists="replace", index=False)
inscripciones.to_sql("inscripciones", conn, if_exists="replace", index=False)
conn.close()

print(f"✅ Created {DB_PATH} with {len(students)} students and {len(inscripciones)} inscripciones")
