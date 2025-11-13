from faker import Faker
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys



fake = Faker('es_MX')
np.random.seed(42)
fake.seed_instance(42)



def generate_attendance(n_students, n_sessions, base_attendance=0.8, variability=0.15):

    # Individual attendance rates centered around base_attendance
    student_rates = np.random.normal(base_attendance, variability, n_students)
    student_rates = np.clip(student_rates, 0.1, 0.98)
    attendance = np.zeros((n_students, n_sessions))

    for i, rate in enumerate(student_rates):
        attendance[i] = np.random.binomial(1, rate, n_sessions)

    return attendance.astype(int)

def generate_evals(n_students, n_assignments, min_score=5, max_score=10):
    """
    Generar evaluaciones con diferencias realistas entre estudiantes
    """
    scores_range = list(range(min_score, max_score + 1))
    
    # Crear diferentes perfiles de estudiantes
    scores = np.zeros((n_students, n_assignments))
    
    for i in range(n_students):
        # Asignar perfil de rendimiento basado en posición
        if i % 5 == 0:  # 20% - Rendimiento crítico
            base_prob = [0.3, 0.25, 0.2, 0.15, 0.08, 0.02]  # Sesgado hacia 5-7
            variability = 1.5  # Alta variabilidad
        elif i % 5 == 1:  # 20% - Rendimiento bajo
            base_prob = [0.15, 0.2, 0.25, 0.2, 0.15, 0.05]  # Sesgado hacia 6-8
            variability = 1.2
        elif i % 5 == 2:  # 20% - Rendimiento inconsistente
            base_prob = [0.1, 0.15, 0.2, 0.2, 0.2, 0.15]  # Distribución plana
            variability = 2.0  # Muy alta variabilidad
        elif i % 5 == 3:  # 20% - Rendimiento promedio
            base_prob = [0.05, 0.1, 0.15, 0.25, 0.3, 0.15]  # Sesgado hacia 8-9
            variability = 0.8
        else:  # 20% - Rendimiento excelente
            base_prob = [0.02, 0.03, 0.05, 0.1, 0.3, 0.5]  # Sesgado hacia 9-10
            variability = 0.5  # Baja variabilidad
        
        # Aplicar variabilidad a las probabilidades
        varied_probs = np.array(base_prob) + np.random.normal(0, 0.05, 6)
        varied_probs = np.clip(varied_probs, 0.01, 0.99)
        varied_probs = varied_probs / varied_probs.sum()  # Normalizar
        
        # Generar scores para este estudiante
        student_scores = np.random.choice(scores_range, 
                                        size=n_assignments, 
                                        p=varied_probs)
        
        # Agregar variabilidad adicional
        noise = np.random.normal(0, variability, n_assignments)
        student_scores = np.clip(student_scores + noise, min_score, max_score).astype(int)
        
        scores[i] = student_scores
    
    return scores




def data_to_excel_pd(directory, group, matriculas, names, evaluation_data, attendance_data):

    filename = f"{group}.xlsx"
    filepath = os.path.join(directory, filename)
    evaluation_df = pd.DataFrame(evaluation_data)
    evaluation_df.insert(0, 'Matricula', matriculas)
    evaluation_df.insert(1, 'Nombre', names)
    attendance_df = pd.DataFrame(attendance_data)
    attendance_df.insert(0, 'Matricula', matriculas)
    attendance_df.insert(1, 'Nombre', names)
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        # Save evaluations to second sheet
        evaluation_df.to_excel(writer, sheet_name='Evaluaciones', index=False)
        # Save attendance to first sheet
        attendance_df.to_excel(writer, sheet_name='Asistencia', index=False)



    print(f"✅  {len(names)} students to {filename}")



def generate_matriculas(num_students, start=264_421_500):
    matriculas = list(range(start, start + num_students))
    np.random.shuffle(matriculas)
    return matriculas

def generate_names(num_students):

    fake = Faker('es_MX')

    names, matriculas = [], []
    for _ in range(num_students):
        name = f"{fake.first_name()} {fake.last_name()} {fake.last_name()}"
        names.append(name)
    return names

def create_groups(n_groups, n_lessons=17, n_evals=10, min_students=10, max_students=25):

    groups = [f"Grupo_{n}" for n in range(1, n_groups + 1)]
    populations = np.random.randint(min_students, max_students, 6)
    total_students = sum(populations)
    matriculas = generate_matriculas(total_students)
    # Create directory
    directory_name = 'asistencia_calificaciones'
    os.makedirs(directory_name, exist_ok=True)

    print("🎓 GENERANDO DATOS DE ESTUDIANTES POR GRUPO")

    for group, population in zip(groups, populations):
        count = 0
        names = generate_names(population)
        matriculas_group = matriculas[count:population]
        count += population
        attendance_data = generate_attendance(population, n_lessons)
        evaluation_data = generate_evals(population, n_evals)
        data_to_excel_pd(directory_name, group, matriculas_group, names, evaluation_data, attendance_data)

