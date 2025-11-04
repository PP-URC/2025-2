

from faker import Faker
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os


fake = Faker('es_MX')
np.random.seed(42)
fake.seed_instance(42)

def generate_attendance(n_students, n_sessions, base_attendance=0.75, variability=0.15):

    # Individual attendance rates centered around base_attendance
    student_rates = np.random.normal(base_attendance, variability, n_students)
    student_rates = np.clip(student_rates, 0.1, 0.98)
    attendance = np.zeros((n_students, n_sessions))

    for i, rate in enumerate(student_rates):
        attendance[i] = np.random.binomial(1, rate, n_sessions)

    return attendance.astype(int)


def generate_evals(n_students, n_assignments, min_score=5, max_score=10):


    scores_range = list(range(min_score, max_score + 1))
    probabilities = [0.02, 0.05, 0.08, 0.15, 0.30, 0.40]

    scores = np.random.choice(scores_range,
                             size=(n_students, n_assignments),
                             p=probabilities)

    return scores


print("*" * 200)

def data_to_excel_pd(directory, group, names, evaluation_data, attendance_data):

    filename = f"{group}.xlsx"
    filepath = os.path.join(directory, filename)
    evaluation_df = pd.DataFrame(evaluation_data)
    evaluation_df.insert(0, 'Nombre', names)
    attendance_df = pd.DataFrame(attendance_data)
    attendance_df.insert(0, 'Nombre', names)
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        # Save evaluations to second sheet
        evaluation_df.to_excel(writer, sheet_name='Evaluaciones', index=False)
        # Save attendance to first sheet
        attendance_df.to_excel(writer, sheet_name='Asistencia', index=False)



    print(f"✅ Saved {len(names)} students to {filename}")


def generate_names(num_students):

    fake = Faker('es_MX')

    names = []
    for _ in range(num_students):
        name = f"{fake.first_name()} {fake.last_name()} {fake.last_name()}"
        names.append(name)

    return names

def create_groups(n_groups, n_lessons=17, n_evals=10, min_students=10, max_students=25):

    groups = [f"Grupo_{n}" for n in range(1, n_groups + 1)]
    # Create directory
    directory_name = 'asistencia_calificaciones'
    os.makedirs(directory_name, exist_ok=True)

    print("🎓 GENERANDO DATOS DE ESTUDIANTES POR GRUPO")
    print("=" * 60)

    for group in groups:
        print(f"\n📚 Creando {group}")

        n_students = np.random.randint(min_students, max_students+1)
        names = generate_names(n_students)
        attendance_data = generate_attendance(n_students, n_lessons)
        evaluation_data = generate_evals(n_students, n_evals)
        data_to_excel_pd(directory_name, group, names, evaluation_data, attendance_data)

