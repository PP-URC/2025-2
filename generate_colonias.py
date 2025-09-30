# generate_colonias.py
import os, sqlite3, random, requests
import numpy as np
import pandas as pd
import geopandas as gpd
from faker import Faker

# -------------------------
# Config
# -------------------------
random.seed(42)
np.random.seed(42)
fake = Faker("es_MX")

N_STUDENTS     = 1000
SEMESTRES_MAX  = 8
DB_PATH        = "unrc.db"

COLONIAS_FILE  = "catlogo-de-colonias.json"
COLONIAS_URL   = "https://datos.cdmx.gob.mx/dataset/02c6ce99-dbd8-47d8-aee1-ae885a12bb2f/resource/026b42d3-a609-44c7-a83d-22b2150caffc/download/catlogo-de-colonias.json"

# -------------------------
# Download + load GeoJSON (always use GeoPandas)
# -------------------------
if not os.path.exists(COLONIAS_FILE):
    print(f"⬇️ Downloading {COLONIAS_FILE}")
    r = requests.get(COLONIAS_URL, timeout=90)
    r.raise_for_status()
    with open(COLONIAS_FILE, "wb") as f:
        f.write(r.content)
    print(f"✅ Saved {COLONIAS_FILE}")
else:
    print(f"Already have {COLONIAS_FILE}")

# Always rea

with open(COLONIAS_FILE, "rb") as f:
    print(f.read(200))



gdf_colonias = gpd.read_file(COLONIAS_FILE)
# Expected columns typically include: ['cve_ent','entidad','cve_alc','alc','cve_col','colonia','clasif','geometry']
cols = gdf_colonias.columns.str.lower().tolist()

def pick_col(name_candidates):
    for c in name_candidates:
        if c in cols:
            return c
    return None

col_colonia = pick_col(["colonia", "nomgeo", "nombre"])
col_alc     = pick_col(["alc", "alcaldia", "municipio", "delegacion"])
if col_colonia is None:
    raise RuntimeError("Could not find the 'colonia' name column in GeoJSON.")
if col_alc is None:
    raise RuntimeError("Could not find the 'alcaldia' column in GeoJSON.")

colonias_catalog = gdf_colonias[[col_colonia, col_alc]].drop_duplicates().rename(
    columns={col_colonia: "colonia_residencia", col_alc: "alcaldia"}
).reset_index(drop=True)

# Assign a synthetic marginación index per colonia (-2 very low … +2 very high)
marginacion_levels = [-2,-1,0,1,2]
marginacion_probs  =  [0.22,0.28,0.26,0.16,0.08]  # skew to lower-middle, but with tail
colonias_catalog["marginacion_index"] = np.random.choice(
    marginacion_levels, size=len(colonias_catalog), p=marginacion_probs
)

print(f"Catálogo de colonias: {len(colonias_catalog)} únicas.")

# -------------------------
# Generate students
# -------------------------
students = pd.DataFrame({
    "student_id": range(1, N_STUDENTS+1),
    "sexo": np.random.choice(["M","F"], size=N_STUDENTS),
    "fecha_nacimiento": [fake.date_of_birth(minimum_age=17, maximum_age=30) for _ in range(N_STUDENTS)],
    "colonia_residencia": np.random.choice(colonias_catalog["colonia_residencia"], size=N_STUDENTS),
    "alcaldia": np.random.choice(colonias_catalog["alcaldia"], size=N_STUDENTS),
    "ingreso_familiar": np.random.choice([3000,6000,9000,12000,15000,20000], size=N_STUDENTS, p=[0.10,0.20,0.28,0.22,0.15,0.05]),
    "personas_hogar": np.random.randint(1,7, size=N_STUDENTS),
    "horas_trabajo": np.random.choice([0,10,20,30,40], size=N_STUDENTS, p=[0.48,0.20,0.17,0.10,0.05]),
    "traslado_min": np.random.choice([15,30,45,60,75,90], size=N_STUDENTS, p=[0.10,0.25,0.28,0.20,0.10,0.07]),
    "dispositivo_propio": np.random.choice([0,1], size=N_STUDENTS, p=[0.18,0.82]),
    "internet_casa": np.random.choice([0,1], size=N_STUDENTS, p=[0.12,0.88]),
})

students = students.merge(
    colonias_catalog[["colonia_residencia","marginacion_index"]],
    on="colonia_residencia", how="left"
)

# -------------------------
# Generate semesters with realistic dropout (can happen any term; stop after dropout)
# -------------------------
rows = []
for _, st in students.iterrows():
    dropped = False
    for sem in range(1, SEMESTRES_MAX+1):
        if dropped:
            break

        promedio   = float(np.clip(np.random.normal(8.0, 0.9), 5.0, 10.0))
        asistencia = float(np.clip(np.random.normal(86.0, 9.5), 40.0, 100.0))
        materias   = int(np.random.randint(4, 7))
        aprobadas  = int(np.random.binomial(materias, 0.80))
        reprobadas = materias - aprobadas
        beca       = int(np.random.choice([0,1], p=[0.70,0.30]))
        tutoria    = int(np.random.choice([0,1], p=[0.78,0.22]))

        # stronger early-semester risk; later safer
        sem_effect = {1:0.85, 2:0.60, 3:0.30, 4:0.10, 5:-0.10, 6:-0.30, 7:-0.55, 8:-0.80}.get(sem, -0.40)

        # Logit score (tuned for ~8–10% global dropout; varied student risks)
        z = (
            -1.90                      # intercept baseline
            + sem_effect               # early semesters riskier
            - 0.95*(promedio - 8.0)    # strong protection by GPA
            - 0.025*(asistencia - 86)  # modest protection by attendance
            + 0.045*(st["horas_trabajo"])
            + 0.020*(st["traslado_min"] - 45)
            + 0.40*st["marginacion_index"]
            - 0.40*beca                # supports reduce risk
            - 0.30*tutoria
        )

        p_dropout = 1.0/(1.0 + np.exp(-z))
        abandono  = int(np.random.binomial(1, p_dropout))

        rows.append({
            "id": len(rows)+1,
            "student_id": int(st["student_id"]),
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

        if abandono == 1:
            dropped = True

inscripciones = pd.DataFrame(rows)

# -------------------------
# Save DB
# -------------------------
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
students.to_sql("students_raw", conn, index=False)
inscripciones.to_sql("inscripciones", conn, index=False)
conn.close()

print(f"✅ Created {DB_PATH} with {len(students)} students and {len(inscripciones)} inscripciones")
print("Abandono por semestre (observado):")
print(inscripciones.groupby("semestre")["abandono"].mean().round(3))
