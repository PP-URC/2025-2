import glob
import os
import pandas as pd
import numpy as np
from schemas import REPORT_DBNAME


def preview_xl_data(path='asistencia_calificaciones'):
    """preview_excel_data(path) -> None
    prints first 3 rows of all sheets"""
  
    excel_files = glob.glob(os.path.join(path, "*.xlsx"))
    for file_path in excel_files[:1]:
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
    print(f"🎓 ANÁLISIS ACADÉMICO - REPORTE DE PROBLEMAS\nEN EL DIRECTORIO {path}")

    excel_files = glob.glob(os.path.join(path, "*.xlsx"))

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
    #return problems_groups, problems_students

def analyze_problems(path='asistencia_calificaciones'):
    """Analyze academic issues with new Excel structure"""
    print(f"🎓 ANÁLISIS ACADÉMICO - NUEVA ESTRUCTURA\nDIRECTORIO: {path}")

    excel_files = glob.glob(os.path.join(path, "*.xlsx"))
    
    if not excel_files:
        print("No se encontraron archivos Excel")
        return [], []

    problems_groups = []
    problems_students = []

    for excel_filename in excel_files:
        subject = os.path.basename(excel_filename).replace('.xlsx', '')
        print(f"\n📖 Materia: {subject}")
        
        excel_file = pd.ExcelFile(excel_filename)
        
        # Process each evaluation sheet (find corresponding attendance sheet)
        for sheet_name in excel_file.sheet_names:
            if sheet_name.startswith('Evaluaciones_'):
                group = sheet_name.replace('Evaluaciones_', '')
                att_sheet = f'Asistencia_{group}'
                
                if att_sheet not in excel_file.sheet_names:
                    continue
                
                # Analyze this group
                group_problems, student_problems = analyze_group(
                    excel_filename, subject, group, sheet_name, att_sheet
                )
                
                if group_problems:
                    problems_groups.append(group_problems)
                
                problems_students.extend(student_problems)
    
    return problems_groups, problems_students

def analyze_group(excel_file, subject, group, eval_sheet, att_sheet):
    """Analyze a specific group within a subject"""
    try:
        df_scores = pd.read_excel(excel_file, sheet_name=eval_sheet)
        df_attendance = pd.read_excel(excel_file, sheet_name=att_sheet)
        
        matriculas = df_attendance.iloc[:, 0].tolist()
        attendance_data = df_attendance.iloc[:, 2:].values
        scores_data = df_scores.iloc[:, 2:].values
        
        # Group analysis
        attendance_avg = np.mean(attendance_data)
        score_avg = np.mean(scores_data)
        
        group_problems = []
        if attendance_avg < 0.75:
            group_problems.append(f"Asistencia baja ({attendance_avg:.1%})")
        if score_avg < 7:
            group_problems.append(f"Rendimiento bajo ({score_avg:.1f}/10)")
        
        group_result = {
            'group': group,
            'subject': subject,
            'problems': group_problems if group_problems else None,
            'attendance_avg': attendance_avg,
            'score_avg': score_avg
        } 
        
        # Student analysis
        students_problems = list()
        for i, matricula in enumerate(matriculas):
            if i >= len(attendance_data) or i >= len(scores_data):
                continue
                
            att_student = np.mean(attendance_data[i])
            score_student = np.mean(scores_data[i])
            
            problems_student = []
            if att_student < 0.7:
                problems_student.append(f"asistencia crítica ({att_student:.1%})")
            if score_student < 6:
                problems_student.append(f"rendimiento crítico ({score_student:.1f}/10)")
            
            if problems_student:
                students_problems.append({
                    'group': group,
                    'subject': subject,
                    'matricula': matricula,
                    'problems': problems_student,
                    'attendance': att_student,
                    'score': score_student
                })
                group_result.setdefault('students', list()).append([matricula, *problems_student])
        
        # Print summary for this group
        status = "⚠️" if group_problems else "✅"
        #student_status = f", {len(student_problems)} estudiantes problemáticos" if student_problems else ""
        #print(f"   {status} {group}: {len(group_problems)} problemas grupales{student_status}")
        print(f"{status} {group} {group_result['problems'] if group_result['problems'] else ''}")
        for student in students_problems:
            print(f"{student['matricula']}: {student['problems']}")
        
        return group_result, students_problems
        
    except Exception as e:
        print(f"❌ Error en {group}: {e}")
        return None, []


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
            print(f"   • {problem['group']}: {problem['problems']}")

    # Problemas de estudiantes
    if problems_student:
        print(f"\nESTUDIANTES QUE NECESITAN ATENCIÓN ({len(problems_student)} estudiantes):")

        # Agrupar por grupo
        groups = set(st['group'] for st in problems_student)

        for group in groups:
            students_group = [st for st in problems_student if st['group'] == group]
            print(f"\n   {group}:")

            for st in students_group:
                print(f"      {st['matricula']}")
                print(f"         Asistencia: {st['attendance']:.1%} | Rendimiento: {st['score']:.1f}/10")
                for problema in st['problems']:
                    print(f"         {problema}")

def generate_report_sql(problems_group, problems_students, conn, db=REPORT_DBNAME):
    pass

