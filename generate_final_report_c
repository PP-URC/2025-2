"""
generate_final_report.py
-------------------
1. Load DB (unrc.db)
2. Use abandono from generator (don't overwrite)
3. Logistic regression
4. Save figures (PNG) into ./out_pipeline
5. Save Top-10 risk list
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

# Make sure it's sorted
panel = panel.sort_values(["student_id","semestre"])

# --- Aggregate dropout rates ---
agg_sem = panel.groupby("semestre")["abandono"].mean().reset_index()
agg_sem.rename(columns={"abandono":"abandono_rate"}, inplace=True)

# --- Logistic regression ---
merged = panel.merge(
    students[["student_id","horas_trabajo","traslado_min"]],
    on="student_id", how="left"
)

predictors = ["promedio","asistencia_pct","horas_trabajo","traslado_min"]
X = add_constant(merged[predictors], has_constant="add")
y = merged["abandono"]

logit = Logit(y, X).fit(disp=False)

print("\n📊 Logistic regression summary:")
print(logit.summary())

# --- Save figures ---

# Figure 1: Dropout by semester
plt.plot(agg_sem["semestre"], agg_sem["abandono_rate"], marker="o")
plt.title("Tasa de abandono por semestre")
plt.xlabel("Semestre")
plt.ylabel("Proporción de abandono")
plt.grid(True)
plt.savefig(os.path.join(OUT_DIR, "figura1_abandono_por_semestre.png"))
plt.close()

# Figure 2: Logistic regression coefficients
coefs = pd.DataFrame({"var": X.columns, "coef": logit.params})
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

plt.plot(fpr, tpr, color="darkorange", lw=2, label=f"ROC (área = {roc_auc:.2f})")
plt.plot([0,1],[0,1], color="navy", lw=2, linestyle="--")
plt.xlabel("Tasa de falsos positivos")
plt.ylabel("Tasa de verdaderos positivos")
plt.title("Curva ROC")
plt.legend(loc="lower right")
plt.savefig(os.path.join(OUT_DIR, "figura3_roc.png"))
plt.close()

# --- Risk scoring (last semester only) ---
idx_last = merged.groupby("student_id")["semestre"].idxmax()
risk_df = merged.loc[idx_last, ["student_id","semestre"]].copy()
risk_df["prob_abandono"] = logit.predict(add_constant(
    merged.loc[idx_last, predictors], has_constant="add"
))

risk_df = risk_df.merge(
    students[["student_id","sexo","colonia_residencia","horas_trabajo","traslado_min"]],
    on="student_id", how="left"
)

risk_top10 = risk_df.sort_values("prob_abandono", ascending=False).head(10)
risk_df.sort_values("prob_abandono", ascending=False).to_csv(
    os.path.join(OUT_DIR, "risk_by_student.csv"), index=False
)

print("\n✅ Analysis complete. Figures + risk CSV saved in", OUT_DIR)
print("\nTop 10 students at risk:")
print(risk_top10)
