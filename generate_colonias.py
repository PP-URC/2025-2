# generator_sqlite_unrc_colonias.py
# Genera base sintética de estudiantes con colonia_residencia real (CDMX)

import sqlite3
import pandas as pd
import numpy as np
import os
import requests
import geopandas as gpd

DB_PATH = "unrc.db"

# --- Descargar catálogo de colonias ---
COLONIAS_FILE = "coloniascdmx.geojson"
if not os.path.exists(COLONIAS_FILE):
    url = "https://datos.cdmx.gob.mx/dataset/02c6ce99-dbd8-47d8-aee1-ae885a12bb2f/resource/265d519b-8949-46c0-8caa-5eaca7e690ec/download/catlogo-de-colonias.json"
    print("⬇️ Descargando catálogo de colonias...")
    r = requests.get(url)
    r.raise_for_status()
    with open(COLONIAS_FILE, "wb") as f:
        f.write(r.content)

gdf_colonias = gpd.read_file(COLONIAS_FILE)

# Confirmar campos disponibles
print("Campos en colonias:", gdf_colonias.columns)

# Normalizar nombres
col_names = [c.lower() for c in gdf_colonias.columns]
if "nom_col" in col_names:
    col_field = gdf_colonias.columns[col_names.index("nom_col")]
elif "colonia" in col_names:
    col_field = gdf_colonias.columns[col_names.index("colonia")]
else:
    raise KeyError(f"No se encontró campo de nombre de colonia. Campos: {gdf_colonias.columns}")

if "nom_deleg" in col_names:
    alc_field = gdf_colonias.columns[col_names.index("nom_deleg")]
else:
    alc_field = None

colonias = gdf_colonias[[col_field] + ([alc_field] if alc_field else [])].drop_duplicates()
colonias = colonias.rename(columns={col_field: "colonia", alc_field: "alcaldia"} if alc_field else {"colonia": "colonia"})

print("Ejemplo de colonias:\n", colonias.head())

# --- Generar estudiantes sintéticos ---
np.random.seed(42)
N = 1000

students = pd.DataFrame({
    "student_id": range(1, N+1),
    "sexo": np.random.choice(["M","F"], size=N),
    "fecha_nacimiento": pd.to_datetime(
        np.random.randint(pd.Timestamp("1995-01-01").value, pd.Timestamp("2005-12-31").value, size=N)
    ),
    "colonia_residencia": np.random.choice(colonias["colonia"], size=N),
    "ingreso_familiar": np.random.choice([2000,5000,10000,15000], size=N, p=[0.3,0.4,0.2,0.1]),
    "personas_hogar": np.random.randint(2,7,size=N),
    "trabaja_horas": np.random.choice([0,10,20,30,40], size=N, p=[0.5,0.2,0.15,0.1,0.05]),
    "dispositivo_propio": np.random.choice([0,1], size=N, p=[0.2,0.8]),
    "internet_casa": np.random.choice([0,1], size=N, p=[0.15,0.85])
})

# --- Inscripciones ---
rows = []
for sid in students["student_id"]:
    semestres = np.random.randint(1, 9)  # hasta 8 semestres
    for sem in range(1, semestres+1):
        promedio = np.clip(np.random.normal(80,10), 50, 100)
        materias = 5
        aprobadas = np.random.binomial(materias, promedio/100)
        reprobadas = materias - aprobadas
        asistencia = np.clip(np.random.normal(0.85,0.1), 0, 1)
        beca = np.random.choice([0,1], p=[0.7,0.3])
        tutoria = np.random.choice([0,1], p=[0.8,0.2])
        rows.append([sid, sem, promedio, materias, aprobadas, reprobadas, beca, tutoria, asistencia])

inscripciones = pd.DataFrame(rows, columns=[
    "student_id","semestre","promedio","materias_inscritas",
    "materias_aprobadas","materias_reprobadas","beca","apoyo_tutoria","asistencia_pct"
])

# --- Guardar en SQLite ---
conn = sqlite3.connect(DB_PATH)
students.to_sql("students_raw", conn, if_exists="replace", index=False)
inscripciones.to_sql("inscripciones", conn, if_exists="replace", index=False)
conn.close()

print(f"✅ Created {DB_PATH} with {len(students)} students and {len(inscripciones)} inscripciones")
