"""Gera os dados do dashboard (etapa 2) e a edição em arquivo único.

Rode depois de `src/build_survival_v2.py`:

    python src/build_dashboard_v2.py

Saídas:
    dashboard/assets/data.js                         dados consumidos por assets/app.js
    dashboard/assets/*.csv                           bases para download
    dashboard/sobrevivencia_dashboard.html           edição standalone (abre sem servidor)
"""

from __future__ import annotations

import base64
import json
import shutil
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

import build_survival_v2 as v2

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed" / "survival_v2"
ANA = ROOT / "analysis" / "survival_v2"
DASH = ROOT / "dashboard"
ASSETS = DASH / "assets"

DESIGN_META = {
    "A1": {"label": "3 anos · coorte 2017", "short": "A1", "age": 3, "window": "2014_2016",
           "outcome": "Sobrevivência em 3 anos (%) · coorte 2017, obs. 2020",
           "note": "Brasil pelo IBGE; demais países pela OCDE. É o corte do piloto.",
           "file": "analytic_A1_cohort2017_s3.csv"},
    "B": {"label": "2 anos · fonte única OCDE", "short": "B", "age": 2, "window": "2014_2016",
          "outcome": "Sobrevivência em 2 anos (%) · coorte 2017, obs. 2019",
          "note": "Todos os países, inclusive o Brasil, pela mesma fonte (OCDE).",
          "file": "analytic_B_cohort2017_s2.csv"},
    "A2": {"label": "3 anos · pré-pandemia", "short": "A2", "age": 3, "window": "2011_2013",
           "outcome": "Sobrevivência média em 3 anos (%) · coortes 2014–2016, obs. 2017–2019",
           "note": "Sem o Brasil: a OCDE não publica 3 anos para o país e o IBGE só cobre a coorte 2017.",
           "file": "analytic_A2_cohorts2014_2016_s3.csv"},
    "S_sector": {"label": "Ajustado por setor", "short": "Setor", "age": 3, "window": "2012_2015",
                 "outcome": "Índice de sobrevivência em 3 anos ajustado por composição setorial (%)",
                 "note": "Efeito-país de regressão com efeitos fixos de setor e de ano (obs. 2017–2019).",
                 "file": "analytic_S_sector_index.csv"},
    "S_size": {"label": "Ajustado por porte", "short": "Porte", "age": 3, "window": "2012_2015",
               "outcome": "Índice de sobrevivência em 3 anos ajustado por porte (%)",
               "note": "Efeito-país de regressão com efeitos fixos de faixa de pessoal e de ano (obs. 2017–2019).",
               "file": "analytic_S_size_index.csv"},
}
WINDOWS = {"2014_2016": (2014, 2016), "2011_2013": (2011, 2013), "2012_2015": (2012, 2015)}

SOURCES = [
    ("OCDE — Employer business demography: enterprise survival (SDMX)",
     "https://data-explorer.oecd.org/vis?df[ds]=dsDisseminateFinalDMZ&df[id]=DSD_SDBSBD_ISIC4%40DF_BD_EMP_S&df[ag]=OECD.SDD.TPS"),
    ("IBGE — Demografia das Empresas 2022",
     "https://biblioteca.ibge.gov.br/index.php/biblioteca-catalogo?id=2102142&view=detalhes"),
    ("IBGE — Release: sobrevivência da coorte 2017",
     "https://agenciadenoticias.ibge.gov.br/agencia-noticias/2012-agencia-de-noticias/noticias/42109-taxa-de-nascimento-de-empresas-empregadoras-chega-a-15-3-e-e-a-maior-desde-2017"),
    ("Banco Mundial — API de indicadores (WDI, WGI, Doing Business)", "https://datahelpdesk.worldbank.org/knowledgebase/articles/889392"),
    ("OCDE — Global Revenue Statistics", "https://www.oecd.org/en/data/datasets/global-revenue-statistics-database.html"),
    ("OCDE — Corporate Tax Statistics", "https://www.oecd.org/en/data/datasets/corporate-tax-statistics-database.html"),
]

DOWNLOADS = {
    "corte_A1_coorte2017_3anos.csv": PROC / "analytic_A1_cohort2017_s3.csv",
    "corte_B_coorte2017_2anos.csv": PROC / "analytic_B_cohort2017_s2.csv",
    "painel_pais_coorte.csv": PROC / "panel_country_cohort_s3.csv",
    "sintese_evidencia.csv": ANA / "evidence_summary.csv",
}


def clean(value):
    if isinstance(value, (float, np.floating)):
        return None if not np.isfinite(value) else round(float(value), 4)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def records(df: pd.DataFrame) -> list[dict]:
    return [{k: clean(v) for k, v in row.items()} for row in df.to_dict(orient="records")]


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    validation = json.loads((ANA / "validation.json").read_text(encoding="utf-8"))
    factors_long = v2.load_factors()
    meta = [
        {"code": c, "name": f[1], "dimension": f[2], "unit": f[3], "source": f[4],
         "transform": f[5], "expected": f[6]}
        for c, f in v2.FACTORS.items()
    ]

    windows = {}
    for key, (start, end) in WINDOWS.items():
        wide = v2.factor_window(factors_long, start, end)
        windows[key] = {code: {c: clean(v) for c, v in wide[code].dropna().items()} for code in wide.columns}

    designs = {}
    for key, m in DESIGN_META.items():
        df = pd.read_csv(PROC / m["file"])[["country_code", "country_name_pt", "survival_rate_pct"]]
        df = df.sort_values("survival_rate_pct", ascending=False).reset_index(drop=True)
        df["rank"] = np.arange(1, len(df) + 1)
        oecd = df[df["country_code"].ne("BRA")]["survival_rate_pct"]
        entry = {**m, "rows": records(df), "n": int(len(df)), "oecd_median": clean(oecd.median()),
                 "min": clean(df["survival_rate_pct"].min()), "max": clean(df["survival_rate_pct"].max())}
        if "BRA" in set(df["country_code"]):
            row = df[df["country_code"].eq("BRA")].iloc[0]
            entry["brazil"] = clean(row["survival_rate_pct"])
            entry["brazil_rank"] = int(row["rank"])
        entry.pop("file")
        designs[key] = entry

    corr = pd.read_csv(ANA / "correlations_by_design.csv")
    panel = pd.read_csv(ANA / "panel_models.csv")
    multi = pd.read_csv(ANA / "panel_multivariate.csv")
    evidence = pd.read_csv(ANA / "evidence_summary.csv")

    # Brasil: IBGE (curva) e OCDE (1 e 2 anos por ano de referência)
    ibge = v2.load_ibge()[["survival_age_years", "survival_rate_pct"]]
    fact = pd.read_csv(PROC / "fact_survival_oecd_api.csv")
    bra = fact[fact["country_code"].eq("BRA") & fact["valid"]][["age_years", "reference_year", "cohort_year", "survival_rate_pct"]]
    oecd_median_by_year = (
        fact[fact["valid"] & fact["country_code"].isin(v2.OECD_MEMBERS)]
        .groupby(["age_years", "reference_year"])["survival_rate_pct"].median().rename("oecd_median").reset_index()
    )
    divergence = pd.read_csv(ANA / "brazil_ibge_vs_oecd.csv")

    coverage = pd.read_csv(PROC / "coverage_factors_2014_2016.csv")
    coverage = coverage.rename(columns={coverage.columns[0]: "country_code"})

    n_tested = int(corr.dropna(subset=["pearson_r"])["factor_code"].nunique())
    payload = {
        "meta": {
            "title": "Sobreviver para crescer",
            "updated": date.today().isoformat(),
            "stage": "Etapa 2 · dados das APIs",
            "factors_total": len(meta),
            "factors_tested": n_tested,
            "panel": validation["panel"],
            "multivariate": validation["multivariate"],
            "invalid_rows": validation["oecd_rows_invalid_value"],
            "oecd_rows": validation["oecd_rows_total"],
        },
        "designs": designs,
        "design_order": ["A1", "B", "A2", "S_sector", "S_size"],
        "factors": meta,
        "factor_windows": windows,
        "correlations": records(corr.drop(columns=["factor_name", "dimension"], errors="ignore")),
        "panel_models": records(panel.drop(columns=["factor_name", "dimension"], errors="ignore")),
        "panel_multivariate": records(multi.drop(columns=["factor_name"], errors="ignore")),
        "evidence": records(evidence[["factor_code", "evidence"]]),
        "brazil": {
            "ibge_curve": records(ibge),
            "oecd_series": records(bra),
            "oecd_median_by_year": records(oecd_median_by_year),
            "divergence": records(divergence),
        },
        "coverage": records(coverage),
        "sources": [{"label": a, "url": b} for a, b in SOURCES],
        "downloads": list(DOWNLOADS),
    }

    (ASSETS / "data.js").write_text(
        "window.DASHBOARD_DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    for name, src in DOWNLOADS.items():
        shutil.copyfile(src, ASSETS / name)

    # Edição em arquivo único
    html = (DASH / "index.html").read_text(encoding="utf-8")
    css = (ASSETS / "styles.css").read_text(encoding="utf-8")
    html = html.replace('<link rel="stylesheet" href="assets/styles.css">', f"<style>\n{css}\n</style>")
    html = html.replace('<script src="assets/data.js"></script>', "<script>\n" + (ASSETS / "data.js").read_text(encoding="utf-8") + "</script>")
    html = html.replace('<script src="assets/app.js"></script>', "<script>\n" + (ASSETS / "app.js").read_text(encoding="utf-8") + "</script>")
    for name in DOWNLOADS:
        uri = "data:text/csv;charset=utf-8;base64," + base64.b64encode((ASSETS / name).read_bytes()).decode("ascii")
        html = html.replace(f'href="assets/{name}"', f'href="{uri}"')
    (DASH / "sobrevivencia_dashboard.html").write_text(html, encoding="utf-8")
    print(f"data.js: {(ASSETS / 'data.js').stat().st_size / 1024:.0f} KB · standalone gerado")


if __name__ == "__main__":
    main()
