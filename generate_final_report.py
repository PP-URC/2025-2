"""
generate_final_report.py
------------------------
1. Load DB (unrc.db)
2. Aggregate dropout rates
3. Logistic regression
4. Save figures (PNG) into ./out_pipeline
5. Save regression coefficients
6. Calculate dropout probabilities
7. Save student risk CSV ordered by probability
8. Plot Top 10 students at risk
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

# Derive abandono: dropout if student doesn't appear in next semester
panel = panel.sort_values(["student_id","semestre"])
panel["abandono"] = 0
for sid, group in panel.groupby("student_id"):
    max_sem = group["semestre"].max()
    if max_sem < 8:
        panel.loc[(panel["student_id"]==sid) & (panel["semestre"]==max_sem),"abandono"] = 1

# --- Aggregate dropout rates ---
agg_sem = panel.groupby("semestre")["abandono"].mean().reset_index()
agg_sem.rename(columns={"abandono":"abandono_rate"}, inplace=True)

# --- Logistic regression ---
merged = panel.merge(students[["student_id","horas_trabajo","traslado_min"]],
                     on="student_id", how="left")

predictors = ["promedio","asistencia_pct","horas_trabajo","traslado_min"]
X = merged[predictors].copy()
X = add_constant(X, has_constant="add")
y = merged["abandono"]

logit = Logit(y, X).fit(disp=False)
print("\n📊 Logistic regression summary:")
print(logit.summary())

# --- Save coefficients ---
logit.params.to_csv(os.path.join(OUT_DIR,"logit_params.csv"))
print("✅ Saved regression coefficients at out_pipeline/logit_params.csv")

# --- Predict dropout probabilities ---
log_odds = X @ logit.params
merged["abandono_prob"] = 1 / (1 + np.exp(-log_odds))

student_risk = merged.groupby("student_id")["abandono_prob"].max().reset_index()
student_risk = student_risk.sort_values("abandono_prob", ascending=False)
student_risk.to_csv(os.path.join(OUT_DIR,"student_dropout_risk.csv"), index=False)

# --- Figure 1: Dropout by semester ---
plt.plot(agg_sem["semestre"], agg_sem["abandono_rate"], marker="o")
plt.title("Tasa de abandono por semestre")
plt.xlabel("Semestre")
plt.ylabel("Proporción de abandono")
plt.grid(True)
plt.savefig(os.path.join(OUT_DIR, "figura1_abandono_por_semestre.png"))
plt.close()

# --- Figure 2: Logistic regression coefficients ---
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

# --- Figure 3: ROC curve ---
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

# --- Figure 4: Top 10 students at risk ---
top10 = student_risk.head(10)
top10_details = top10.merge(students, on="student_id", how="left")
top10_details = top10_details.merge(
    panel.groupby("student_id")[["promedio","asistencia_pct"]].mean().reset_index(),
    on="student_id", how="left"
)
top10_details.to_csv(os.path.join(OUT_DIR,"top10_details.csv"), index=False)

# Render as image
fig, ax = plt.subplots(figsize=(10,3))
ax.axis("off")
tbl = ax.table(
    cellText=top10_details[["student_id","abandono_prob","promedio","asistencia_pct","horas_trabajo","traslado_min"]].round(2).values,
    colLabels=["ID","Prob.","Prom.","Asist.","Horas trabajo","Traslado min"],
    loc="center"
)
tbl.auto_set_font_size(False)
tbl.set_fontsize(8)
tbl.scale(1.2,1.2)
plt.savefig(os.path.join(OUT_DIR,"figura5_top10_table.png"), dpi=200)
plt.close()

# Save sample tables
students.head(10).to_csv(os.path.join(OUT_DIR,"sample_students.csv"), index=False)
agg_sem.head(10).to_csv(os.path.join(OUT_DIR,"sample_agg_sem.csv"), index=False)

print(f"\n✅ Analysis complete. Figures + risk CSV saved in {OUT_DIR}")
