# generator_sqlite_unrc.py
# Generador sintético con riesgo de abandono realista (URC)

import sqlite3
import pandas as pd
import numpy as np
import os
from faker import Faker
from datetime import datetime

np.random.seed(42)
faker = Faker("es_MX")

DB_PATH = "unrc.db"
if os.path.exists(DB_PATH):
    os.remove(DB_PATH)
conn = sqlite3.connect(DB_PATH)

# -----------------------------------
# Parámetros
# -----------------------------------
n_students = 1000
alcaldias = [
    "Álvaro Obregón","Azcapotzalco","Benito Juárez","Coyoacán",
    "Cuajimalpa","Cuauhtémoc","Gustavo A. Madero","Iztacalco",
    "Iztapalapa","La Magdalena Contreras","Miguel Hidalgo","Milpa Alta",
    "Tláhuac","Tlalpan","Venustiano Carranza","Xochimilco"
]
planteles = ["Cuautepec","San Lorenzo Tezonco","Justo Sierra"]

# Mapa simplificado de traslado (minutos)
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
default_commute = (70,110)

# -----------------------------------
# Generar estudiantes
# -----------------------------------
students = []
for sid in range(1, n_students+1):
    sexo = np.random.choice(["M","F"])
    birthdate = faker.date_of_birth(minimum_age=18, maximum_age=30)
    edad = datetime.today().year - birthdate.year

    alc = np.random.choice(alcaldias)
    plantel = np.random.choice(planteles)

    # Tiempo de traslado
    if plantel in commute_map and alc in commute_map[plantel]:
        tmin, tmax = commute_map[plantel][alc]
    else:
        tmin, tmax = default_commute
    traslado_min = np.random.randint(tmin, tmax+1)

    ingreso = np.random.choice([5000, 8000, 12000, 20000, 30000],
                               p=[.2,.3,.3,.15,.05])
    personas = np.random.randint(2,6)
    horas_trabajo = np.random.choice([0,10,20,30,40], p=[.5,.2,.15,.1,.05])
    dispositivo = np.random.choice([0,1], p=[.2,.8])
    internet = np.random.choice([0,1], p=[.15,.85])

    students.append([
        sid, sexo, birthdate.isoformat(), edad, alc, plantel,
        ingreso, personas, horas_trabajo, dispositivo, internet, traslado_min
    ])

students_df = pd.DataFrame(students, columns=[
    "student_id","sexo","fecha_nacimiento","edad","alcaldia_residencia","plantel",
    "ingreso_familiar","personas_hogar","horas_trabajo",
    "dispositivo_propio","internet_casa","traslado_min"
])
students_df.to_sql("students_raw", conn, index=False)

# -----------------------------------
# Generar inscripciones con abandono
# -----------------------------------
semesters = []
for _, st in students_df.iterrows():
    sid = st["student_id"]
    abandonado = False

    for sem in range(1,9):  # máx. 8 semestres
        if abandonado:
            break

        promedio = np.clip(np.random.normal(8, 1), 5, 10)
        materias = 5
        aprobadas = np.random.binomial(materias, p=min(0.9, promedio/10))
        reprobadas = materias - aprobadas
        beca = np.random.choice([0,1], p=[0.7,0.3])
        tutoria = np.random.choice([0,1], p=[0.6,0.4])
        asistencia = np.clip(np.random.normal(85, 10), 50, 100)

        # --- Riesgo de abandono ---
        risk = 0.05  # base
        # Académico
        if promedio < 7: risk += 0.20
        elif promedio < 8: risk += 0.10
        if asistencia < 70: risk += 0.15
        if reprobadas >= 2: risk += 0.10
        if tutoria == 0: risk += 0.05
        if beca == 1: risk -= 0.05
        # Socioeconómico
        if st["ingreso_familiar"] < 8000: risk += 0.10
        if st["personas_hogar"] > 5: risk += 0.05
        if st["internet_casa"] == 0: risk += 0.05
        if st["dispositivo_propio"] == 0: risk += 0.05
        # Laboral
        if st["horas_trabajo"] > 20: risk += 0.10
        elif st["horas_trabajo"] >= 10: risk += 0.05
        # Geográfico
        if st["traslado_min"] > 60: risk += 0.10
        # Demográfico
        if st["edad"] > 24: risk += 0.05
        if st["sexo"] == "M": risk += 0.02
        # Temporal (semestre)
        if sem == 1: risk *= 1.8
        elif sem == 2: risk *= 1.5
        elif sem in [3,4,5]: risk *= 1.0
        elif sem == 6: risk *= 0.7
        elif sem == 7: risk *= 0.5
        elif sem == 8: risk *= 0.3

        risk = min(max(risk, 0.01), 0.95)
        abandono = np.random.rand() < risk

        semesters.append([
            None, sid, sem, promedio, materias, aprobadas, reprobadas,
            beca, tutoria, asistencia, 1 if abandono else 0
        ])

        if abandono:
            abandonado = True

inscripciones_df = pd.DataFrame(semesters, columns=[
    "id","student_id","semestre","promedio","materias_inscritas",
    "materias_aprobadas","materias_reprobadas","beca","apoyo_tutoria",
    "asistencia_pct","abandono"
])
inscripciones_df.to_sql("inscripciones", conn, index=False)

print(f"✅ Created {DB_PATH} with {len(students_df)} students and {len(inscripciones_df)} semester-rows.")
conn.close()
