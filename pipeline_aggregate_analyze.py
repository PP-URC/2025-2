#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline: derive dropout & stop-outs from raw SQLite DB, aggregate, analyze.
- Input: unrc.db with students_raw, inscripciones
- Output: CSVs with derived labels and aggregates; simple logistic regression
"""
import sqlite3, os
import pandas as pd
import numpy as np
import statsmodels.api as sm
import matplotlib.pyplot as plt


DB_PATH = "unrc.db"
OUT_DIR = "./out_pipeline"

os.makedirs(OUT_DIR, exist_ok=True)
conn = sqlite3.connect(DB_PATH)

# 1) Load raw
stu = pd.read_sql_query("SELECT * FROM students_raw", conn)
ins = pd.read_sql_query("SELECT * FROM inscripciones", conn)

# 2) Derive commute (minutes) via baseline matrix
commute_map = {("Azcapotzalco","Azcapotzalco"):(18,30),("Azcapotzalco","Coyoacán"):(55,80),("Azcapotzalco","GAM"):(25,45),("Azcapotzalco","Magdalena Contreras"):(65,95),
("Coyoacán","Azcapotzalco"):(60,90),("Coyoacán","Coyoacán"):(18,30),("Coyoacán","GAM"):(55,80),("Coyoacán","Magdalena Contreras"):(30,50),
("GAM","Azcapotzalco"):(25,45),("GAM","Coyoacán"):(55,80),("GAM","GAM"):(18,30),("GAM","Magdalena Contreras"):(65,95),
("Magdalena Contreras","Azcapotzalco"):(65,95),("Magdalena Contreras","Coyoacán"):(35,55),("Magdalena Contreras","GAM"):(65,95),("Magdalena Contreras","Magdalena Contreras"):(18,30),
("Iztapalapa","Azcapotzalco"):(70,100),("Iztapalapa","Coyoacán"):(40,65),("Iztapalapa","GAM"):(55,85),("Iztapalapa","Magdalena Contreras"):(60,90),
("Benito Juárez","Azcapotzalco"):(45,70),("Benito Juárez","Coyoacán"):(18,35),("Benito Juárez","GAM"):(35,55),("Benito Juárez","Magdalena Contreras"):(40,60),
("Tlalpan","Azcapotzalco"):(75,110),("Tlalpan","Coyoacán"):(35,60),("Tlalpan","GAM"):(65,95),("Tlalpan","Magdalena Contreras"):(45,70),
("Iztacalco","Azcapotzalco"):(55,80),("Iztacalco","Coyoacán"):(35,60),("Iztacalco","GAM"):(45,70),("Iztacalco","Magdalena Contreras"):(55,85),
("Álvaro Obregón","Azcapotzalco"):(55,85),("Álvaro Obregón","Coyoacán"):(40,65),("Álvaro Obregón","GAM"):(60,90),("Álvaro Obregón","Magdalena Contreras"):(22,40),
("Cuauhtémoc","Azcapotzalco"):(35,60),("Cuauhtémoc","Coyoacán"):(35,60),("Cuauhtémoc","GAM"):(25,45),("Cuauhtémoc","Magdalena Contreras"):(45,70)}
def commute_sample(row):
    lo, hi = commute_map.get((row["alcaldia_residencia"], row["plantel"]), (40,70))
    return np.random.uniform(lo, hi)
stu["traslado_minutos"] = stu.apply(commute_sample, axis=1)

# 3) Build full student×semester panel (only for observed semesters)
panel = ins.merge(stu[["id_estudiante","sexo","fecha_nacimiento","alcaldia_residencia","plantel","ingreso_familiar","personas_hogar","trabaja_horas","dispositivo_propio","internet_casa","traslado_minutos"]],
                  on="id_estudiante", how="left")
panel.to_csv(os.path.join(OUT_DIR, "panel_raw.csv"), index=False)

# 4) Derive dropout & stop-out
# For each student-semester t, dropout_event=1 if no record at t+1 AND student never reappears later (no record > t+1).
# stopout_event=1 if no record at t+1 BUT reappears later.
max_sem_by_student = panel.groupby("id_estudiante")["semestre"].max().rename("max_sem")
panel = panel.merge(max_sem_by_student, on="id_estudiante", how="left")

panel["semestre_next"] = panel["semestre"] + 1
# next_active flag: does (id_estudiante, semestre+1) exist?
next_key = panel[["id_estudiante","semestre"]].copy()
next_key["semestre_next"] = next_key["semestre"] + 1
key_df = panel[["id_estudiante","semestre"]].drop_duplicates()
key_df["exists"] = 1

panel = panel.merge(key_df.rename(columns={"semestre":"semestre_next", "exists":"next_exists"}),
                    left_on=["id_estudiante","semestre_next"], right_on=["id_estudiante","semestre_next"], how="left")
panel["next_exists"] = panel["next_exists"].fillna(0).astype(int)

# reappears_later: any record at a semester > t+1
reappear = panel.groupby("id_estudiante")["semestre"].apply(lambda s: set(s.tolist())).to_dict()
def reappears(id_est, t):
    sems = reappear.get(id_est, set())
    return 1 if any(ss > t+1 for ss in sems) else 0
panel["reappears_later"] = panel.apply(lambda r: reappears(r["id_estudiante"], r["semestre"]), axis=1)

# Graduation: if max_sem == target max (assume 8), mark as graduated; they are not dropouts at last semester
TARGET_MAX = int(panel["semestre"].max())  # if generator used 8, this will be 8
panel["graduated"] = (panel["max_sem"] >= TARGET_MAX).astype(int)

# Events
panel["stopout_event"] = ((panel["next_exists"]==0) & (panel["reappears_later"]==1)).astype(int)
panel["dropout_event"] = ((panel["next_exists"]==0) & (panel["reappears_later"]==0) & (panel["graduated"]==0)).astype(int)

panel.to_csv(os.path.join(OUT_DIR, "panel_with_events.csv"), index=False)

# 5) Aggregates
agg_sem = panel.groupby("semestre").agg(
    abandono_sem=("dropout_event","mean"),
    stopout_sem=("stopout_event","mean"),
    promedio_sem=("promedio_semestre","mean"),
    asistencia_sem=("asistencia_pct","mean")
).reset_index()
agg_sem.to_csv(os.path.join(OUT_DIR, "agg_per_semester.csv"), index=False)

# 6) Simple logistic regression (dropout_event) on semester records
model_df = panel.copy()
X = model_df[["promedio_semestre","asistencia_pct","ingreso_familiar","traslado_minutos","beca","trabaja_horas"]].copy()
X = sm.add_constant(X)
y = model_df["dropout_event"].astype(int)
logit = sm.Logit(y, X).fit(disp=False)
with open(os.path.join(OUT_DIR, "logit_summary.txt"), "w") as f:
    f.write(logit.summary2().as_text())

# 7) Export a small README
cum_dropout = panel.groupby("id_estudiante")["dropout_event"].max().mean()
per_sem = panel.groupby("semestre")["dropout_event"].mean().round(3).to_dict()
with open(os.path.join(OUT_DIR, "README.txt"), "w") as f:
    f.write(f"Cumulative dropout (derived): {cum_dropout:.2%}\nPer-semester dropout: {per_sem}\nStop-out share per semester also in agg_per_semester.csv\n")


plt.figure()
agg_sem.plot(x="semestre", y="abandono_sem", marker="o", legend=False)
plt.title("Tasa de abandono por semestre")
plt.ylabel("Proporción de abandono")
plt.xlabel("Semestre")
plt.grid(True)
plt.savefig(os.path.join(OUT_DIR, "figura1_abandono_por_semestre.png"))
plt.close()

# --- Figura 2: Tasa de stop-out por semestre ---
plt.figure()
agg_sem.plot(x="semestre", y="stopout_sem", marker="o", color="orange", legend=False)
plt.title("Tasa de reingreso temporal (stop-out) por semestre")
plt.ylabel("Proporción de stop-out")
plt.xlabel("Semestre")
plt.grid(True)
plt.savefig(os.path.join(OUT_DIR, "figura2_stopout_por_semestre.png"))
plt.close()

# --- Figura 3: Coeficientes de la regresión logística ---
coefs = pd.DataFrame({
    "var": X.columns,
    "coef": logit.params,
    "pval": logit.pvalues
})
coefs = coefs[coefs["var"] != "const"].sort_values("coef")

plt.figure(figsize=(6,4))
plt.barh(coefs["var"], coefs["coef"], color="steelblue")
plt.title("Coeficientes de la regresión logística para abandono")
plt.xlabel("Efecto en log-odds de abandono")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "figura3_coef_logistica.png"))
plt.close()

# --- Figura 4: Diagrama de la regla t+1 ---
import matplotlib.patches as mpatches

fig, ax = plt.subplots(figsize=(8,2))
semestres = ["Sem 1", "Sem 2", "Sem 3", "Sem 4"]
for i, sem in enumerate(semestres):
    ax.text(i*2, 0, sem, ha="center", va="center", fontsize=12, bbox=dict(boxstyle="round", facecolor="lightblue"))
    if i < len(semestres)-1:
        ax.annotate("", xy=(i*2+1.2, 0), xytext=(i*2+0.8, 0),
                    arrowprops=dict(arrowstyle="->", lw=1.5))

ax.text(8, 0.3, "Si no reaparece = Abandono", fontsize=10, color="red")
ax.text(8, -0.1, "Si reaparece más tarde = Stop-out", fontsize=10, color="orange")
ax.text(8, -0.5, "Si llega a Sem 8 = Graduación", fontsize=10, color="green")

ax.axis("off")
plt.title("Ejemplo de la regla t+1 para identificar abandono y stop-out", fontsize=12)
plt.savefig(os.path.join(OUT_DIR, "figura4_regla_tmas1.png"), bbox_inches="tight")
plt.close()

print("Pipeline finished. Outputs in", OUT_DIR)
