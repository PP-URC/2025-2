#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
UNRC SQLite Generator (raw only, dropout to be derived later)

Creates unrc.db with:
- students_raw (one row per student; includes sociodemographics)
- inscripciones (one row per student-semester actually enrolled)
No reinscrito_next, no abandono; absence of t+1 row indicates non-enrollment.
Implements time-varying hazard (higher early, lower late) with modifiers.
"""

import sqlite3, os, random, json
from datetime import datetime
import numpy as np
import pandas as pd

ALCALDIAS = ["Azcapotzalco","Coyoacán","GAM","Magdalena Contreras","Iztapalapa","Benito Juárez","Tlalpan","Iztacalco","Álvaro Obregón","Cuauhtémoc"]
PLANTELES = ["Azcapotzalco","Coyoacán","GAM","Magdalena Contreras"]

COMMUTE_BASELINE = {("Azcapotzalco","Azcapotzalco"):(18,30),("Azcapotzalco","Coyoacán"):(55,80),("Azcapotzalco","GAM"):(25,45),("Azcapotzalco","Magdalena Contreras"):(65,95),
("Coyoacán","Azcapotzalco"):(60,90),("Coyoacán","Coyoacán"):(18,30),("Coyoacán","GAM"):(55,80),("Coyoacán","Magdalena Contreras"):(30,50),
("GAM","Azcapotzalco"):(25,45),("GAM","Coyoacán"):(55,80),("GAM","GAM"):(18,30),("GAM","Magdalena Contreras"):(65,95),
("Magdalena Contreras","Azcapotzalco"):(65,95),("Magdalena Contreras","Coyoacán"):(35,55),("Magdalena Contreras","GAM"):(65,95),("Magdalena Contreras","Magdalena Contreras"):(18,30),
("Iztapalapa","Azcapotzalco"):(70,100),("Iztapalapa","Coyoacán"):(40,65),("Iztapalapa","GAM"):(55,85),("Iztapalapa","Magdalena Contreras"):(60,90),
("Benito Juárez","Azcapotzalco"):(45,70),("Benito Juárez","Coyoacán"):(18,35),("Benito Juárez","GAM"):(35,55),("Benito Juárez","Magdalena Contreras"):(40,60),
("Tlalpan","Azcapotzalco"):(75,110),("Tlalpan","Coyoacán"):(35,60),("Tlalpan","GAM"):(65,95),("Tlalpan","Magdalena Contreras"):(45,70),
("Iztacalco","Azcapotzalco"):(55,80),("Iztacalco","Coyoacán"):(35,60),("Iztacalco","GAM"):(45,70),("Iztacalco","Magdalena Contreras"):(55,85),
("Álvaro Obregón","Azcapotzalco"):(55,85),("Álvaro Obregón","Coyoacán"):(40,65),("Álvaro Obregón","GAM"):(60,90),("Álvaro Obregón","Magdalena Contreras"):(22,40),
("Cuauhtémoc","Azcapotzalco"):(35,60),("Cuauhtémoc","Coyoacán"):(35,60),("Cuauhtémoc","GAM"):(25,45),("Cuauhtémoc","Magdalena Contreras"):(45,70)}

def commute_minutes(home, campus):
    lo, hi = COMMUTE_BASELINE.get((home, campus), (40,70))
    return int(np.random.uniform(lo, hi))

def random_birthdate(min_age=18, max_age=30, cohort=datetime(2024,8,1)):
    age = np.random.randint(min_age, max_age+1)
    year = cohort.year - age
    month = np.random.randint(1, 13)
    day = np.random.randint(1, 28)
    return f"{year:04d}-{month:02d}-{day:02d}"

def main(students=1000, semesters=8, seed=7, out_db="unrc.db"):
    np.random.seed(seed); random.seed(seed)
    if os.path.exists(out_db):
        os.remove(out_db)
    conn = sqlite3.connect(out_db)
    cur = conn.cursor()

    # Schema
    cur.executescript("""
    PRAGMA journal_mode = WAL;
    CREATE TABLE students_raw (
      id_estudiante INTEGER PRIMARY KEY,
      sexo TEXT,
      fecha_nacimiento DATE,
      alcaldia_residencia TEXT,
      plantel TEXT,
      ingreso_familiar INTEGER,
      personas_hogar INTEGER,
      trabaja_horas INTEGER,
      dispositivo_propio INTEGER,
      internet_casa INTEGER
    );
    CREATE TABLE inscripciones (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      id_estudiante INTEGER,
      semestre INTEGER,
      promedio_semestre REAL,
      materias_inscritas INTEGER,
      materias_aprobadas INTEGER,
      materias_reprobadas INTEGER,
      beca INTEGER,
      apoyo_tutoria INTEGER,
      asistencia_pct REAL
    );
    """)

    # Students
    alcaldia_p = [0.07,0.10,0.12,0.06,0.18,0.08,0.10,0.08,0.10,0.11]
    plantel_p  = [0.25,0.30,0.30,0.15]

    students_rows = []
    for sid in range(1, students+1):
        sexo = np.random.choice(["M","F"], p=[0.45,0.55])
        dob = random_birthdate()
        home = np.random.choice(ALCALDIAS, p=alcaldia_p)
        campus = np.random.choice(PLANTELES, p=plantel_p)
        ingreso = int(np.random.choice([3500,6000,9000,14000,22000,32000,45000],
                                   p=[0.10,0.18,0.22,0.22,0.16,0.08,0.04]))
        hogar = int(np.random.randint(2,7))
        work_mu = 26 if ingreso<=6000 else (18 if ingreso<=9000 else 10)
        trabajo_h = max(0, int(np.random.normal(work_mu, 6)))
        laptop = 1 if np.random.rand()<0.78 else 0
        internet = 1 if np.random.rand()<0.85 else 0
        students_rows.append((sid, sexo, dob, home, campus, ingreso, hogar, trabajo_h, laptop, internet))

    cur.executemany("""
        INSERT INTO students_raw
        (id_estudiante,sexo,fecha_nacimiento,alcaldia_residencia,plantel,ingreso_familiar,personas_hogar,trabaja_horas,dispositivo_propio,internet_casa)
        VALUES (?,?,?,?,?,?,?,?,?,?);
    """, students_rows)
    conn.commit()

    # Hazard by semester (front-loaded)
    base_retention_by_sem = {1:0.88, 2:0.92, 3:0.94, 4:0.94, 5:0.96, 6:0.96, 7:0.98, 8:0.99}

    # Generate inscripciones per student until they stop appearing (drop out) or finish
    df_students = pd.read_sql_query("SELECT * FROM students_raw", conn)
    ins_rows = []
    for _, s in df_students.iterrows():
        enrolled = True
        for sem in range(1, semesters+1):
            if not enrolled: break
            commute = commute_minutes(s["alcaldia_residencia"], s["plantel"])

            grade_mu = 8.2
            if s["ingreso_familiar"]<=6000: grade_mu -= 0.35
            if s["trabaja_horas"]>=20:      grade_mu -= 0.25
            if commute>=90:                 grade_mu -= 0.20
            promedio = float(np.clip(np.random.normal(grade_mu, 0.9), 6.0, 10.0))

            materias = 5
            repro_p = 0.15 if promedio>=8 else (0.3 if promedio>=7 else 0.5)
            reprobadas = int(np.random.binomial(materias, repro_p))
            aprobadas = materias - reprobadas

            if s["ingreso_familiar"]<=6000:   beca = 1 if np.random.rand()<0.55 else 0
            elif s["ingreso_familiar"]<=9000: beca = 1 if np.random.rand()<0.35 else 0
            elif s["ingreso_familiar"]<=14000:beca = 1 if np.random.rand()<0.20 else 0
            else:                               beca = 1 if np.random.rand()<0.07 else 0
            tutoria = 1 if np.random.rand()<0.25 else 0

            base_att = 0.92
            if commute>=90:         base_att -= 0.08
            if s["trabaja_horas"]>=20: base_att -= 0.07
            if promedio<7.0:        base_att -= 0.06
            asistencia_pct = float(np.clip(np.random.normal(base_att, 0.08), 0.45, 0.99))*100.0

            ins_rows.append((int(s["id_estudiante"]), sem, promedio, materias, aprobadas, reprobadas, beca, tutoria, asistencia_pct))

            # Decide enrollment to next semester (not stored; affects whether we add next row)
            p = base_retention_by_sem.get(sem, 0.95)
            if s["ingreso_familiar"]<=6000: p -= 0.10
            elif s["ingreso_familiar"]<=9000: p -= 0.06
            if s["trabaja_horas"]>=20: p -= 0.06
            if commute>=90:         p -= 0.05
            if promedio<7.0:        p -= 0.20
            elif promedio<8.0:      p -= 0.08
            if asistencia_pct<70:   p -= 0.12
            if beca==1:             p += 0.10
            p = max(0.03, min(0.99, p))

            enrolled = (np.random.rand() < p)

    cur.executemany("""
        INSERT INTO inscripciones
        (id_estudiante,semestre,promedio_semestre,materias_inscritas,materias_aprobadas,materias_reprobadas,beca,apoyo_tutoria,asistencia_pct)
        VALUES (?,?,?,?,?,?,?,?,?);
    """, ins_rows)
    conn.commit()
    conn.close()
    print(f"Created {out_db} with {len(students_rows)} students and {len(ins_rows)} semester-rows.")

if __name__ == "__main__":
    # defaults; override via CLI if you run locally
    main(students=1000, semesters=8, seed=7, out_db="unrc.db")
