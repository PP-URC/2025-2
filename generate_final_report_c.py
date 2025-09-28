# generate_final_report_c.py
"""
Pipeline:
1. Load DB (unrc.db)
2. Use 'abandono' from generator (no overwrite)
3. Logistic regression
4. Save plots, top 10 risk list, and CSVs into ./out_pipeline
"""

import sqlite3
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from statsmodels.discrete.discrete_model import Logit
from statsmodels.tools import add_constant
from sklearn.metrics import roc_curve, auc

DB_PATH = "unrc.db"
OUT_DIR = "./out_pipeline"
os.makedirs(OUT_DIR, exist_ok=True)

# --- Load data ---
conn = sqlite3.connect(DB_PATH)
students = pd.read_sql("SELECT * FROM students_raw", conn)
panel = pd.read_sql("SELECT * FROM inscripciones", conn)
conn.close()

# ✅ Keep generator's dropout
panel["abandono_flag"] = panel["abandono"]

# --- Aggregate dropout rates ---
agg_sem = panel.groupby("semestre")["abandono_flag"].mean().reset_index()
agg_sem.rename(columns={"abandono_flag":"abandono_rate"}, inplace=True)

# --- Logistic regression ---
merged = panel.merge(students[["student_id","horas_trabajo","traslado_min"]],
                     on="student_id", how="left")

predictors = ["promedio","asistencia_pct","horas_trabajo","traslado_min"]
X = merged[predictors].copy()
X = add_constant(X, has_constant="add")
y = merged["abandono_flag"]

logit = Logit(y, X).fit(disp=False)

print("\n📊 Logistic regression summary:")
print(logit.summary())

# --- Save Figures ---

# Figure 1: Dropout by semester
plt.plot(agg_sem["semestre"], agg_sem["abandono_rate"], marker="o")
plt.title("Tasa de abandono por semestre")
plt.xlabel("Semestre")
plt.ylabel("Proporción de abandono")
plt.grid(True)
plt.savefig(os.path.join(OUT_DIR, "figura1_abandono_por_semestre.png"))
plt.close()

# Figure 2: Logistic regression coefficients
coefs = pd.DataFrame({
    "var": X.columns,
    "coef": logit.params
})
coefs = coefs[coefs["var"]!="const"].sort_values("coef")

plt.barh(coefs["var"], coefs["coef"], color="steelblue")
plt.title("Coeficientes de la regresión logística")
plt.xlabel("Efecto en log-odds de abandono")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "figura2_coef_logistica.png"))
plt.close()

# Figure 3: ROC curve
y_pred = logit.predict(X)
fpr, tpr, _ = roc_curve(y, y_pred)
roc_auc = auc(fpr, tpr)

plt.plot(fpr, tpr, color="darkorange", lw=2, label=f"ROC curve (área = {roc_auc:.2f})")
plt.plot([0,1],[0,1], color="navy", lw=2, linestyle="--")
plt.xlabel("Tasa de falsos positivos")
plt.ylabel("Tasa de verdaderos positivos")
plt.title("Curva ROC del modelo logístico")
plt.legend(loc="lower right")
plt.savefig(os.path.join(OUT_DIR, "figura3_roc.png"))
plt.close()

# --- Top 10 risk students ---
merged["abandono_prob"] = logit.predict(X)

risk = merged.groupby("student_id")["abandono_prob"].mean().reset_index()
risk = risk.merge(students[["student_id","sexo","colonia_residencia","alcaldia"]],
                  on="student_id", how="left")

top10 = risk.sort_values("abandono_prob", ascending=False).head(10)

# Save as CSV
top10.to_csv(os.path.join(OUT_DIR, "top10_risk_students.csv"), index=False)

# Save as image
fig, ax = plt.subplots(figsize=(8,4))
ax.barh(top10["student_id"].astype(str), top10["abandono_prob"]*100, color="salmon")
ax.set_xlabel("Probabilidad de abandono (%)")
ax.set_ylabel("ID Estudiante")
ax.set_title("Top 10 estudiantes con mayor riesgo de abandono")
plt.gca().invert_yaxis()
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR,"figura4_top10_risk.png"))
plt.close()

print(f"\n✅ Analysis complete. Outputs saved in {OUT_DIR}")
