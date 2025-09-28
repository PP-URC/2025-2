# generator_sqlite_unrc.py

import sqlite3
import pandas as pd
import numpy as np
import os
from faker import Faker

np.random.seed(42)
faker = Faker("es_MX")

DB_PATH = "unrc.db"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
conn = sqlite3.connect(DB_PATH)

# -----------------------------------
# Parameters
# -----------------------------------
n_students = 1000
alcaldias = [
    "Álvaro Obregón","Azcapotzalco","Benito Juárez","Coyoacán",
    "Cuajimalpa","Cuauhtémoc","Gustavo A. Madero","Iztacalco",
    "Iztapalapa","La Magdalena Contreras","Miguel Hidalgo","Milpa Alta",
    "Tláhuac","Tlalpan","Venustiano Carranza","Xochimilco"
]
planteles = ["Cuautepec","San Lorenzo Tezonco","Justo Sierra"]

# Simple commute lookup (minutes range)
commute_map = {
    "Cuautepec": {
        "Gustavo A. Madero": (20,40),
        "Azcapotzalco": (30,50),
        "Cuauhtémoc": (45,70),
        "Benito Juárez": (60,90)
    },
    "San Lorenzo Tezonco": {
        "Iztapalapa": (20,40),
        "Tláhuac": (25,45),
        "Coyoacán": (50,70),
        "Álvaro Obregón": (70,100)
    },
    "Justo Sierra": {
        "Cuauhtémoc": (20,35),
        "Benito Juárez": (25,40),
        "Miguel Hidalgo": (35,55),
        "Iztacalco": (40,60)
    }
}
# Default commute range for "far" alcaldías
default_commute = (70,110)

# -----------------------------------
# Generate students_raw
# -----------------------------------
students = []
for sid in range(1, n_students+1):
    alc = np.random.choice(alcaldias)
    plantel = np.random.choice(planteles)
    # commute lookup
    if plantel in commute_map and alc in commute_map[plantel]:
        tmin, tmax = commute_map[plantel][alc]
    else:
        tmin, tmax = default_commute
    traslado_min = np.random.randint(tmin, tmax+1)

    students.append([
        sid,
        np.random.choice(["M","F"]),
        faker.date_of_birth(minimum_age=18, maximum_age=30).isoformat(),
        alc,
        plantel,
        np.random.choice([5000, 8000, 12000, 20000, 30000], p=[.2,.3,.3,.15,.05]),
        np.random.randint(2,6),
        np.random.choice([0,10,20,30,40], p=[.5,.2,.15,.1,.05]),
        np.random.choice([0,1], p=[.2,.8]),
        np.random.choice([0,1], p=[.15,.85]),
        traslado_min
    ])

students_df = pd.DataFrame(students, columns=[
    "student_id","sexo","fecha_nacimiento","alcaldia_residencia","plantel",
    "ingreso_familiar","personas_hogar","horas_trabajo","dispositivo_propio",
    "internet_casa","traslado_min"
])
students_df.to_sql("students_raw", conn, index=False)

# -----------------------------------
# Generate inscripciones (semesters)
# -----------------------------------
semesters = []
for sid in students_df["student_id"]:
    n_sem = np.random.choice([4,6,8], p=[0.2,0.5,0.3])
    for sem in range(1, n_sem+1):
        promedio = np.clip(np.random.normal(8, 1), 5, 10)
        materias = 5
        aprobadas = np.random.binomial(materias, p=min(0.9, promedio/10))
        reprobadas = materias - aprobadas
        beca = np.random.choice([0,1], p=[0.7,0.3])
        tutoria = np.random.choice([0,1], p=[0.6,0.4])
        asistencia = np.clip(np.random.normal(85, 10), 50, 100)
        semesters.append([
            None, sid, sem, promedio, materias, aprobadas, reprobadas, beca, tutoria, asistencia
        ])

inscripciones_df = pd.DataFrame(semesters, columns=[
    "id","student_id","semestre","promedio","materias_inscritas",
    "materias_aprobadas","materias_reprobadas","beca","apoyo_tutoria","asistencia_pct"
])
inscripciones_df.to_sql("inscripciones", conn, index=False)

print(f"✅ Created {DB_PATH} with {len(students_df)} students and {len(inscripciones_df)} semester-rows.")
conn.close()
