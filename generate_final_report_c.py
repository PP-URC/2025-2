# generate_final_report_c.py
import sqlite3
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
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

# Derive abandono again (last semester < 8 → dropout)
panel = panel.sort_values(["student_id","semestre"])
panel["abandono_flag"] = 0
for sid, group in panel.groupby("student_id"):
    max_sem = group["semestre"].max()
    if max_sem < 8:
        panel.loc[(panel["student_id"]==sid) & (panel["semestre"]==max_sem),"abandono_flag"] = 1

# --- Aggregate dropout rates ---
agg_sem = panel.groupby("semestre")["abandono_flag"].mean().reset_index()

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

# --- Save coefficients ---
coefs = pd.DataFrame({"var": X.columns, "coef": logit.params})
coefs.to_csv(os.path.join(OUT_DIR, "logit_params.csv"), index=False)

# --- Figures ---
# 1. Dropout by semester
plt.plot(agg_sem["semestre"], agg_sem["abandono_flag"], marker="o")
plt.title("Tasa de abandono por semestre")
plt.xlabel("Semestre")
plt.ylabel("Proporción de abandono")
plt.grid(True)
plt.savefig(os.path.join(OUT_DIR, "figura1_abandono_por_semestre.png"))
plt.close()

# 2. Logistic regression coefficients
coefs_plot = coefs[coefs["var"]!="const"].sort_values("coef")
plt.barh(coefs_plot["var"], coefs_plot["coef"], color="steelblue")
plt.title("Coeficientes de la regresión logística")
plt.xlabel("Efecto en log-odds de abandono")
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "figura2_coef_logistica.png"))
plt.close()

# 3. ROC curve
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

print(f"\n✅ Analysis complete. Figures saved in {OUT_DIR}")
