# generate_final_report_c.py
import sqlite3, os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm
import geopandas as gpd
import requests
import json
import matplotlib as mpl

OUT_DIR = "out_pipeline"
os.makedirs(OUT_DIR, exist_ok=True)

DB_PATH = "unrc.db"

# --- Load data ---
conn = sqlite3.connect(DB_PATH)
students = pd.read_sql("SELECT * FROM students_raw", conn)
inscripciones = pd.read_sql("SELECT * FROM inscripciones", conn)
conn.close()

print(f"📊 Tasa global de abandono: {inscripciones['abandono'].mean()*100:.2f}%")

# Merge for modeling
merged = inscripciones.merge(
    students[["student_id","sexo","colonia_residencia","alcaldia",
              "horas_trabajo","traslado_min"]],
    on="student_id", how="left"
)

# --- Logistic regression ---
X = merged[["promedio","asistencia_pct","horas_trabajo","traslado_min"]]
X = sm.add_constant(X)
y = merged["abandono"]

logit = sm.Logit(y, X).fit(disp=False)
print(logit.summary())

params = pd.DataFrame(logit.params, columns=["coef"])
params.to_csv(os.path.join(OUT_DIR, "logit_params.csv"))

# --- Predicted probabilities ---
merged["abandono_prob"] = logit.predict(X)

# --- Plot: observed vs predicted by semestre ---
obs = merged.groupby("semestre")["abandono"].mean()
pred = merged.groupby("semestre")["abandono_prob"].mean()

plt.figure(figsize=(8,5))
plt.plot(obs.index, obs.values*100, "o-", label="Observado (%)")
plt.plot(pred.index, pred.values*100, "s--", label="Predicho (%)")
plt.xlabel("Semestre")
plt.ylabel("Tasa de abandono (%)")
plt.title("Abandono observado vs predicho por semestre")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR,"figura1_abandono_vs_predicho.png"))
plt.close()

# --- Top 10 risk students ---
cols_keep = ["student_id","sexo","colonia_residencia","alcaldia",
             "promedio","asistencia_pct","horas_trabajo","traslado_min","abandono_prob"]

top10 = merged.groupby("student_id").apply(
    lambda df: df[cols_keep].iloc[-1]  # last semester row
).reset_index(drop=True)

top10 = top10.sort_values("abandono_prob", ascending=False).head(10)
top10.to_csv(os.path.join(OUT_DIR, "top10_risk_students.csv"), index=False)

# Chart with annotations
fig, ax = plt.subplots(figsize=(10,6))
bars = ax.barh(top10["student_id"].astype(str), top10["abandono_prob"]*100, color="salmon")

ax.set_xlabel("Probabilidad de abandono (%)")
ax.set_ylabel("ID Estudiante")
ax.set_title("Top 10 estudiantes con mayor riesgo de abandono")
plt.gca().invert_yaxis()

for bar, (_, row) in zip(bars, top10.iterrows()):
    label = f"Prom:{row['promedio']:.1f}, Asist:{row['asistencia_pct']:.0f}%, Trab:{row['horas_trabajo']}h, Trasl:{row['traslado_min']}m"
    ax.text(bar.get_width()+1, bar.get_y()+bar.get_height()/2,
            label, va="center", fontsize=8)

plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR,"figura4_top10_risk.png"))
plt.close()

# --- Map of colonias with dropout risk ---
COLONIAS_FILE = "catlogo-de-colonias.json"
url_colonias = "https://datos.cdmx.gob.mx/dataset/02c6ce99-dbd8-47d8-aee1-ae885a12bb2f/resource/026b42d3-a609-44c7-a83d-22b2150caffc/download/catlogo-de-colonias.json"
if not os.path.exists(COLONIAS_FILE):
    r = requests.get(url_colonias)
    if r.status_code == 200:
        with open(COLONIAS_FILE,"wb") as f: f.write(r.content)

try:
    gdf_colonias = gpd.read_file(COLONIAS_FILE)
    risk_by_colonia = merged.groupby("colonia_residencia")["abandono_prob"].mean().reset_index()
    risk_by_colonia.columns = ["colonia","abandono_prob"]

    gdf_colonias = gdf_colonias.merge(risk_by_colonia, left_on="colonia", right_on="colonia", how="left")

    fig, ax = plt.subplots(figsize=(10,10))
    gdf_colonias.plot(column="abandono_prob", cmap="Reds", legend=True, ax=ax,
                      legend_kwds={'label': "Prob. abandono", 'orientation': "vertical"})
    ax.set_title("Riesgo promedio de abandono por colonia")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR,"figura5_colonias_riesgo.png"))
    plt.close()
except Exception as e:
    print("⚠️ Map colonias skipped:", e)

# --- Map with planteles (URC campuses) ---
url_alc = "https://datos.cdmx.gob.mx/dataset/bae265a8-d1f6-4614-b399-4184bc93e027/resource/deb5c583-84e2-4e07-a706-1b3a0dbc99b0/download/limite-de-las-alcaldas.json"
ALC_FILE = "limite-de-las-alcaldas.json"
if not os.path.exists(ALC_FILE):
    r = requests.get(url_alc)
    if r.status_code == 200:
        with open(ALC_FILE,"wb") as f: f.write(r.content)

try:
    gdf_alc = gpd.read_file(ALC_FILE)

    planteles = pd.DataFrame({
        "nombre": ["URC Norte","URC Centro","URC Sur"],
        "lon": [-99.14,-99.10,-99.16],
        "lat": [19.50,19.43,19.29],
        "color": ["red","blue","green"]
    })

    fig, ax = plt.subplots(figsize=(10,10))
    gdf_alc.plot(ax=ax, color="whitesmoke", edgecolor="gray")

    for _, row in planteles.iterrows():
        ax.scatter(row["lon"], row["lat"], c=row["color"], s=80, marker="o", label=row["nombre"])
        ax.text(row["lon"], row["lat"], row["nombre"], fontsize=8,
                ha="center", va="bottom",
                bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none"))

    ax.legend()
    ax.set_title("Planteles URC en CDMX")
    plt.axis("off")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR,"figura6_alcaldias.png"))
    plt.close()
except Exception as e:
    print("⚠️ Map planteles skipped:", e)

print(f"✅ Analysis complete. Outputs saved in {OUT_DIR}")
