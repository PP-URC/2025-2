import sqlite3
import pandas as pd
import numpy as np
import geopandas as gpd
from faker import Faker
import random
import os
import requests, os

url = "https://datos.cdmx.gob.mx/dataset/04a1900a-0c2f-41ed-94dc-3d2d5bad4065/resource/f1408eeb-4e97-4548-bc69-61ff83838b1d/download/coloniascdmx.geojson"
out_file = "/content/2025-2/catlogo-de-colonias.json"

if not os.path.exists(out_file):
    r = requests.get(url)
    if r.status_code == 200:
        with open(out_file, "wb") as f:
            f.write(r.content)
        print(f"✅ Saved colonias catalog to {out_file}")
    else:
        print("⚠️ Download failed:", r.status_code)
else:
    print("Already exists:", out_file)

DB_PATH = "unrc.db"
COLONIAS_FILE = "catlogo-de-colonias.json"
N_STUDENTS = 1000
SEMESTRES_MAX = 8

fake = Faker("es_MX")

# --- Load colonias file ---
print("📥 Loading colonias catalog...")
gdf_colonias = gpd.read_file(COLONIAS_FILE)
print("Columns:", gdf_colonias.columns.tolist())

# Use correct columns: colonia + alc
colonias = gdf_colonias[["colonia", "alc"]].drop_duplicates()
colonias = colonias.rename(columns={"colonia": "colonia_residencia",
                                    "alc": "alcaldia"})

# --- Generate synthetic students ---
print(f"👩‍🎓 Generating {N_STUDENTS} students...")
students = pd.DataFrame({
    "student_id": range(1, N_STUDENTS+1),
    "sexo": np.random.choice(["M","F"], size=N_STUDENTS),
    "fecha_nacimiento": [fake.date_of_birth(minimum_age=17, maximum_age=30) for _ in range(N_STUDENTS)],
    "colonia_residencia": np.random.choice(colonias["colonia_residencia"], size=N_STUDENTS),
    "alcaldia": np.random.choice(colonias["alcaldia"], size=N_STUDENTS),
    "ingreso_familiar": np.random.choice([3000,6000,9000,12000,15000], size=N_STUDENTS),
    "personas_hogar": np.random.randint(1,6, size=N_STUDENTS),
    "horas_trabajo": np.random.choice([0,10,20,30,40], size=N_STUDENTS, p=[0.5,0.2,0.15,0.1,0.05]),
    "traslado_min": np.random.choice([15,30,45,60,90], size=N_STUDENTS, p=[0.1,0.3,0.3,0.2,0.1]),
    "dispositivo_propio": np.random.choice([0,1], size=N_STUDENTS, p=[0.2,0.8]),
    "internet_casa": np.random.choice([0,1], size=N_STUDENTS, p=[0.1,0.9])
})

# --- Generate inscripciones (semesters) ---
rows = []
for sid, row in students.iterrows():
    n_sem = np.random.randint(1, SEMESTRES_MAX+1)  # how many semesters completed
    for sem in range(1, n_sem+1):
        promedio   = np.clip(np.random.normal(8, 1), 5, 10)
        asistencia = np.clip(np.random.normal(85, 10), 40, 100)
        materias   = np.random.randint(4,7)
        aprobadas  = np.random.binomial(materias, 0.8)
        reprobadas = materias - aprobadas
        beca       = np.random.choice([0,1], p=[0.7,0.3])
        tutoria    = np.random.choice([0,1], p=[0.8,0.2])

        # 2) dropout logit with strong, interpretable weights
        #    higher in early semesters; lower promedio & asistencia, high work/commute raise risk
        #    NOTE: these weights are chosen to give a wide spread of probabilities (for “cool” demo)
        sem_effect = {1: 0.8, 2: 0.6, 3: 0.3, 4: 0.1, 5: -0.1, 6: -0.3, 7: -0.5, 8: -0.7}.get(sem, -0.5)

        z = (
      -1.1                  # intercept -> ~25–30% baseline before effects
      + sem_effect          # early semesters riskier
      - 0.9*(promedio - 8)  # each point above/below 8 shifts risk a lot
      - 0.03*(asistencia - 85)
      + 0.04*(row["horas_trabajo"])     # 0..40h -> up to +1.6 in log-odds
      + 0.02*(row["traslado_min"] - 45) # 15..90 -> ~(-0.6..+0.9)
            )

        p_dropout = 1.0/(1.0 + np.exp(-z))

        # Only the last observed semester can realize dropout
        abandono = np.random.binomial(1, p_dropout) if sem == n_sem else 0

       

        rows.append({
            "id": len(rows)+1,
            "student_id": row["student_id"],
            "semestre": sem,
            "promedio": promedio,
            "materias_inscritas": materias,
            "materias_aprobadas": aprobadas,
            "materias_reprobadas": reprobadas,
            "asistencia_pct": asistencia,
            "beca": beca,
            "apoyo_tutoria": tutoria,
            "abandono": abandono
        })

inscripciones = pd.DataFrame(rows)

# --- Save to SQLite ---
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
students.to_sql("students_raw", conn, index=False)
inscripciones.to_sql("inscripciones", conn, index=False)
conn.close()

print(f"✅ Created {DB_PATH} with {len(students)} students and {len(inscripciones)} inscripciones")
print("Columns in students_raw:", students.columns.tolist())
print("Sample abandono rates by semestre:")
print(inscripciones.groupby("semestre")["abandono"].mean())
