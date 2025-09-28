# generate_colonias.py
import sqlite3
import pandas as pd
import numpy as np
import json
from faker import Faker
import random
import os
import requests

DB_PATH = "unrc.db"
COLONIAS_FILE = "catlogo-de-colonias.json"
N_STUDENTS = 1000
SEMESTRES_MAX = 8

fake = Faker("es_MX")

# --- Download colonias catalog ---
url = "https://datos.cdmx.gob.mx/dataset/04a1900a-0c2f-41ed-94dc-3d2d5bad4065/resource/f1408eeb-4e97-4548-bc69-61ff83838b1d/download/coloniascdmx.geojson"
if not os.path.exists(COLONIAS_FILE):
    print("⬇️ Downloading colonias catalog...")
    r = requests.get(url)
    r.raise_for_status()
    with open(COLONIAS_FILE, "wb") as f:
        f.write(r.content)
    print(f"✅ Saved {COLONIAS_FILE}")
else:
    print("Already have", COLONIAS_FILE)

# --- Load colonias catalog ---
print("📥 Loading colonias catalog...")
gdf_colonias = pd.read_json(COLONIAS_FILE) if COLONIAS_FILE.endswith(".json") else None
if gdf_colonias is None or "features" in gdf_colonias.columns or "features" in gdf_colonias.to_dict():
    with open(COLONIAS_FILE, "r", encoding="utf-8") as f:
        raw = json.load(f)
    gdf_colonias = pd.DataFrame([ft["properties"] for ft in raw["features"]])

# Normalize names
colonias = gdf_colonias.rename(columns={
    "colonia": "colonia_residencia",
    "alc": "alcaldia"
})
colonias = colonias[["colonia_residencia", "alcaldia"]].drop_duplicates()

print("✅ Loaded", len(colonias), "colonias")

# --- Synthetic marginación index ---
marginacion_levels = [-2, -1, 0, 1, 2]   # -2=very low, +2=very high
marginacion_probs  = [0.35, 0.30, 0.20, 0.10, 0.05]

colonias["marginacion_index"] = np.random.choice(marginacion_levels,
                                                 size=len(colonias),
                                                 p=marginacion_probs)

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

students = students.merge(colonias[["colonia_residencia","marginacion_index"]],
                          on="colonia_residencia", how="left")

# --- Generate inscripciones ---
rows = []
for sid, row in students.iterrows():
    n_sem = np.random.randint(1, SEMESTRES_MAX+1)
    for sem in range(1, n_sem+1):
        promedio   = np.clip(np.random.normal(8, 1), 5, 10)
        asistencia = np.clip(np.random.normal(85, 10), 40, 100)
        materias   = np.random.randint(4,7)
        aprobadas  = np.random.binomial(materias, 0.8)
        reprobadas = materias - aprobadas
        beca       = np.random.choice([0,1], p=[0.7,0.3])
        tutoria    = np.random.choice([0,1], p=[0.8,0.2])

        sem_effect = {1: 1.2, 2: 0.8, 3: 0.4, 4: 0.0,
                      5: -0.4, 6: -0.8, 7: -1.2, 8: -1.6}.get(sem, -0.5)

        z = (
            -1.3
            + sem_effect
            - 1.0*(promedio - 8)
            - 0.05*(asistencia - 85)
            + 0.05*(row["horas_trabajo"])
            + 0.03*(row["traslado_min"] - 45)
            + 0.7 * row["marginacion_index"]
        )

        p_dropout = 1.0/(1.0 + np.exp(-z))
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
            "abandono": abandono,
            "p_abandono": p_dropout
        })

inscripciones = pd.DataFrame(rows)

# --- Save ---
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
conn = sqlite3.connect(DB_PATH)
students.to_sql("students_raw", conn, index=False)
inscripciones.to_sql("inscripciones", conn, index=False)
conn.close()

print(f"✅ Created {DB_PATH} with {len(students)} students and {len(inscripciones)} inscripciones")
print("Sample abandono rates by semestre:")
print(inscripciones.groupby("semestre")["abandono"].mean())
