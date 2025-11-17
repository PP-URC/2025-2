import glob
import os
import pandas as pd
from schemas import REPORT_DBNAME


def preview_xl_data(path='asistencia_calificaciones'):
    """preview_excel_data(path) -> None
    prints first 3 rows of all sheets"""
  
    excel_files = glob.glob(os.path.join(path, "*.xlsx"))
    for file_path in excel_files:
        filename = os.path.basename(file_path)
        print(f"📊 PREVIEW: {filename}")
        print("=" * 60)
        try:
            excel_file = pd.ExcelFile(file_path)
            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                print(f"\n📋 Sheet: {sheet_name} ({df.shape[0]} rows × {df.shape[1]} columns)")

                # Show first few rows
                display(df.head(3))
                print(f"... and {len(df) - 3} more rows")
                print("-" * 40)

        except Exception as e:
            print(f"❌ Error reading {filename}: {e}")

def analyze_problems(path='asistencia_calificaciones'):
    """analyze_academic_issues(path): -> Tuple[List, List]
    returns tuple of 2 lists with group and student problems
    Analyze *.xlsx files
    """
    print("🎓 ANÁLISIS ACADÉMICO - REPORTE DE PROBLEMAS")
    print("=" * 60)

    excel_files = glob.glob(os.path.join(directory, "*.xlsx"))

    if not excel_files:
        print("No se encontraron archivos Excel")
        return

    problems_groups = []
    problems_students = []
    for excel_filename in excel_files:
        filename = os.path.basename(excel_filename)
        *subject_l, group  = filename.replace('.xlsx', '').split("_")
        subject = " ".join(subject_l)
        df_attendance = pd.read_excel(excel_filename, sheet_name='Asistencia')
        df_scores = pd.read_excel(excel_filename, sheet_name='Evaluaciones')
        matriculas = df_attendance.iloc[:, 0].tolist()
        attendance = df_attendance.iloc[:, 2:].values
        scores = df_scores.iloc[:, 2:].values
        attendance_avg = np.mean(attendance)
        score_avg = np.mean(scores)
        problems = []
        if attendance_avg < 0.8:
            problems.append(f"Asistencia baja ({attendance_avg:.1%})")
        if score_avg < 7.5:
            problems.append(f"Rendimiento bajo ({score_avg:.1f}/10)")
            if problems:
                problems_groups.append({
                    'group': group,
                    'subject': subject,
                    'problems': problems
                })

        for i, matricula in enumerate(matriculas):
            if i >= len(attendance) or i >= len(scores):
                continue
            attendance_student = np.mean(attendance[i])
            score_student = np.mean(scores[i])
            problems = []
            if attendance_student < 0.7:
                problems.append(f"asistencia crítica ({attendance_student:.1%})")
            if score_student < 6:
                problems.append(f"rendimiento crítico ({score_student:.1f}/10)")
            if problems:
                problems_students.append({
                    'group': group,
                    'subject': subject,
                    'matricula': matricula,
                    'problems': problems,
                    'attendance': attendance_student,
                    'score': score_student
                })
    return problems_groups, problems_students

def print_report(problems_group, problems_student):
    """
    Print report per group and student
    """
    print(f"\n{'='*80}")
    print("📊 PROBLEMAS IDENTIFICADOS")
    print(f"{'='*80}")

    # Problemas de grupos
    if problems_group:
        print("\nPROBLEMAS POR GRUPO:")
        for problem in problems_group:
            print(f"   • {problem['group']}: {problem['problem']}")

    # Problemas de estudiantes
    if problems_student:
        print(f"\nESTUDIANTES QUE NECESITAN ATENCIÓN ({len(problems_group)} estudiantes):")

        # Agrupar por grupo
        groups = set(st['group'] for st in problems_group)

        for group in groups:
            students_group = [est for est in problems_student if est['group'] == group]
            print(f"\n   {group}:")

            for st in students_group:
                print(f"      {staticmethod['student']}")
                print(f"         Asistencia: {st['asistencia']:.1%} | Rendimiento: {st['rendimiento']:.1f}/10")
                for problema in st['problemas']:
                    print(f"         {problema}")

def generate_report_sql(problems_group, problems_students, conn, db=REPORT_DBNAME):
    pass

