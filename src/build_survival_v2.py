"""Etapa 2 do estudo de sobrevivência: dados das APIs, fatores anteriores às coortes e robustez.

Entradas (geradas por `src/fetch_api_data.py`):
    data/raw/api/oecd_survival_api.csv
    data/raw/api/oecd_tax_api.csv
    data/raw/api/worldbank_factors_api.csv
    data/raw/survival/ibge_employer_survival_brazil.csv   (Brasil, 3 anos — IBGE)

Saídas:
    data/processed/survival_v2/   fatos harmonizados e bases analíticas
    analysis/survival_v2/         correlações, modelos, validação e relatório

Desenhos analíticos
    A1  Coorte 2017, sobrevivência em 3 anos (obs. 2020), fatores = média 2014–2016. Inclui o
        Brasil pelo IBGE. É o corte do piloto, agora com fatores anteriores à coorte.
    A2  Pré-pandemia: média das coortes 2014–2016 (obs. 2017–2019), fatores = média 2011–2013.
    B   Coorte 2017, sobrevivência em 2 anos (obs. 2019), fonte única OCDE inclusive para o Brasil.
    P   Painel país × coorte (coortes 2011–2017, 3 anos): fator = média dos 3 anos anteriores ao
        nascimento da coorte; efeitos fixos de coorte; erros-padrão agrupados por país.
    S   Índices ajustados por composição setorial e por porte (efeitos fixos), obs. 2017–2019.
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

warnings.filterwarnings("ignore", category=RuntimeWarning)

ROOT = Path(__file__).resolve().parents[1]
RAW_API = ROOT / "data" / "raw" / "api"
RAW_SURVIVAL = ROOT / "data" / "raw" / "survival"
PROCESSED = ROOT / "data" / "processed" / "survival_v2"
ANALYSIS = ROOT / "analysis" / "survival_v2"

OECD_MEMBERS = {
    "AUS", "AUT", "BEL", "CAN", "CHL", "COL", "CRI", "CZE", "DNK", "EST", "FIN", "FRA", "DEU",
    "GRC", "HUN", "ISL", "IRL", "ISR", "ITA", "JPN", "KOR", "LVA", "LTU", "LUX", "MEX", "NLD",
    "NZL", "NOR", "POL", "PRT", "SVK", "SVN", "ESP", "SWE", "CHE", "TUR", "GBR", "USA",
}

COUNTRY_PT = {
    "AUS": "Austrália", "AUT": "Áustria", "BEL": "Bélgica", "BRA": "Brasil", "CAN": "Canadá",
    "CHE": "Suíça", "CHL": "Chile", "COL": "Colômbia", "CRI": "Costa Rica", "CZE": "Tchéquia",
    "DEU": "Alemanha", "DNK": "Dinamarca", "ESP": "Espanha", "EST": "Estônia", "FIN": "Finlândia",
    "FRA": "França", "GBR": "Reino Unido", "GRC": "Grécia", "HUN": "Hungria", "IRL": "Irlanda",
    "ISL": "Islândia", "ISR": "Israel", "ITA": "Itália", "JPN": "Japão", "KOR": "Coreia do Sul",
    "LTU": "Lituânia", "LUX": "Luxemburgo", "LVA": "Letônia", "MEX": "México", "NLD": "Países Baixos",
    "NOR": "Noruega", "NZL": "Nova Zelândia", "POL": "Polônia", "PRT": "Portugal", "SVK": "Eslováquia",
    "SVN": "Eslovênia", "SWE": "Suécia", "TUR": "Turquia", "USA": "Estados Unidos",
}

# Agregado de atividade preferido para cada país (mesmo conceito ao longo do tempo)
ACTIVITY_PREFERENCE = ["BTNX642", "BTN", "_T"]
ACTIVITY_LABEL = {
    "BTNX642": "Indústria, construção e serviços de mercado (exc. holdings)",
    "BTN": "Indústria, construção e serviços de mercado",
    "_T": "Total das atividades",
}
SECTORS = list("BCDEFGHIJLMN")
SIZES = ["S1T4", "S5T9", "S_GE10"]

SRC_WDI = "Banco Mundial — World Development Indicators (API v2)"
SRC_WGI = "Banco Mundial — Worldwide Governance Indicators (API v2)"
SRC_DB = "Banco Mundial — Doing Business (API v2, fonte 1)"
SRC_REV = "OCDE — Global Revenue Statistics (SDMX)"
SRC_CIT = "OCDE — Corporate Tax Statistics (SDMX)"

# code: (indicador bruto, nome, dimensão, unidade, fonte, transformação, sinal esperado)
FACTORS = {
    "gdp_growth": ("NY.GDP.MKTP.KD.ZG", "Crescimento do PIB", "Macroeconômico", "% a.a.", SRC_WDI, None, "+"),
    "inflation": ("FP.CPI.TOTL.ZG", "Inflação (IPC)", "Macroeconômico", "% a.a.", SRC_WDI, None, "−"),
    "log_gdp_pc": ("NY.GDP.PCAP.PP.KD", "PIB per capita (PPC, log)", "Macroeconômico", "log US$ PPC", SRC_WDI, "log", "+"),
    "unemployment": ("SL.UEM.TOTL.ZS", "Desemprego", "Macroeconômico", "% força de trabalho", SRC_WDI, None, "−"),
    "private_credit": ("FS.AST.PRVT.GD.ZS", "Crédito doméstico ao setor privado", "Financeiro", "% PIB", SRC_WDI, None, "+"),
    "real_interest": ("FR.INR.RINR", "Taxa real de juros", "Financeiro", "%", SRC_WDI, None, "−"),
    "insolvency_recovery": ("RESLV.ISV.RCOV.RT", "Taxa de recuperação na insolvência", "Financeiro", "centavos por dólar", SRC_DB, None, "+"),
    "regulatory_quality": ("GOV_WGI_RQ.EST", "Qualidade regulatória", "Institucional", "escore (−2,5 a 2,5)", SRC_WGI, None, "+"),
    "rule_of_law": ("GOV_WGI_RL.EST", "Estado de direito", "Institucional", "escore (−2,5 a 2,5)", SRC_WGI, None, "+"),
    "gov_effectiveness": ("GOV_WGI_GE.EST", "Efetividade do governo", "Institucional", "escore (−2,5 a 2,5)", SRC_WGI, None, "+"),
    "log_days_start": ("IC.REG.DURS.MA.DY", "Tempo para abrir empresa (log)", "Institucional", "log dias", SRC_DB, "log", "?"),
    "internet_users": ("IT.NET.USER.ZS", "Usuários de internet", "Tecnológico", "% população", SRC_WDI, None, "+"),
    "rd_expenditure": ("GB.XPD.RSDV.GD.ZS", "Gasto em P&D", "Tecnológico", "% PIB", SRC_WDI, None, "+"),
    "tax_to_gdp": ("tax_rev_pct_gdp:_T", "Carga tributária total", "Tributário", "% PIB", SRC_REV, None, "?"),
    "income_tax_share": ("share:T_1000", "Tributos sobre renda e lucro", "Tributário", "% da receita tributária", SRC_REV, None, "?"),
    "ssc_share": ("share:T_2000", "Contribuições sociais", "Tributário", "% da receita tributária", SRC_REV, None, "?"),
    "consumption_tax_share": ("share:T_5000", "Tributos sobre bens e serviços", "Tributário", "% da receita tributária", SRC_REV, None, "?"),
    "cit_revenue": ("tax_rev_pct_gdp:T_1200", "Receita de IRPJ", "Tributário", "% PIB", SRC_REV, None, "?"),
    "cit_rate": ("cit_combined_statutory_rate", "Alíquota estatutária do IRPJ", "Tributário", "%", SRC_CIT, None, "−"),
    "total_tax_rate": ("PAY.TAX.TOT.TAX.RT.ZS", "Carga total sobre o lucro (Doing Business)", "Tributário", "% do lucro", SRC_DB, None, "−"),
    "log_tax_hours": ("PAY.TAX.TM", "Horas para cumprir obrigações tributárias (log)", "Tributário", "log horas/ano", SRC_DB, "log", "−"),
    "log_tax_payments": ("PAY.TAX.PYMT.FREQ.NO", "Número de pagamentos de tributos (log)", "Tributário", "log pagamentos/ano", SRC_DB, "log", "−"),
}
# Um fator pré-definido por dimensão para o modelo multivariado do painel
MULTIVARIATE_SET = ["gdp_growth", "inflation", "private_credit", "regulatory_quality", "internet_users", "tax_to_gdp", "log_tax_hours"]

DESIGNS = {
    "A1": "Coorte 2017 · 3 anos (obs. 2020) · fatores 2014–2016 · Brasil pelo IBGE",
    "A2": "Coortes 2014–2016 · 3 anos (obs. 2017–2019) · fatores 2011–2013 · pré-pandemia",
    "B": "Coorte 2017 · 2 anos (obs. 2019) · fatores 2014–2016 · OCDE para todos, inclusive Brasil",
    "S_sector": "Índice ajustado por setor · 3 anos (obs. 2017–2019) · fatores 2012–2015",
    "S_size": "Índice ajustado por porte · 3 anos (obs. 2017–2019) · fatores 2012–2015",
}
MIN_N = 15


# ----------------------------------------------------------------------------- utilidades

def bh_adjust(p: pd.Series) -> pd.Series:
    p = p.astype(float)
    valid = p.dropna().sort_values()
    m = len(valid)
    if m == 0:
        return p * np.nan
    ranked = valid * m / np.arange(1, m + 1)
    adjusted = np.minimum.accumulate(ranked[::-1])[::-1].clip(upper=1)
    return pd.Series(adjusted, index=valid.index).reindex(p.index)


def name_pt(code: str) -> str:
    return COUNTRY_PT.get(code, code)


# ----------------------------------------------------------------------------- desfecho

def load_survival() -> tuple[pd.DataFrame, pd.DataFrame]:
    raw = pd.read_csv(RAW_API / "oecd_survival_api.csv")
    raw = raw[raw["ref_area"].isin(OECD_MEMBERS | {"BRA"})].copy()
    raw["cohort_year"] = raw["reference_year"] - raw["age_years"]
    raw["valid"] = raw["survival_rate_pct"].between(0, 100, inclusive="right")

    aggregate = raw[raw["activity"].isin(ACTIVITY_PREFERENCE) & raw["size_class"].eq("_T")]
    # Por país, o agregado com maior cobertura válida; empate resolvido pela ordem de preferência
    cover = (
        aggregate[aggregate["survival_rate_pct"].between(0, 100, inclusive="right")]
        .groupby(["ref_area", "activity"]).size().rename("cells").reset_index()
    )
    cover["pref"] = cover["activity"].map({a: i for i, a in enumerate(ACTIVITY_PREFERENCE)})
    chosen = (
        cover.sort_values(["ref_area", "cells", "pref"], ascending=[True, False, True])
        .groupby("ref_area")["activity"].first()
    )
    headline = aggregate[aggregate["activity"].eq(aggregate["ref_area"].map(chosen))].copy()

    # Consistência de coorte: S1 >= S2 >= S3 (tolerância de 1 p.p.)
    wide = headline[headline["valid"]].pivot_table(
        index=["ref_area", "cohort_year"], columns="age_years", values="survival_rate_pct"
    )
    bad = pd.Series(False, index=wide.index)
    for a, b in [(1, 2), (2, 3), (1, 3)]:
        if a in wide and b in wide:
            bad |= (wide[b] > wide[a] + 1).fillna(False)
    bad_cohorts = set(bad[bad].index)
    headline["cohort_inconsistent"] = [
        (r, c) in bad_cohorts for r, c in zip(headline["ref_area"], headline["cohort_year"])
    ]
    headline["activity_label"] = headline["activity"].map(ACTIVITY_LABEL)
    headline["country_name_pt"] = headline["ref_area"].map(name_pt)
    headline["source"] = "OCDE — Employer business demography (SDMX, DF_BD_EMP_S)"
    return raw, headline.rename(columns={"ref_area": "country_code"})


def load_ibge() -> pd.DataFrame:
    ibge = pd.read_csv(RAW_SURVIVAL / "ibge_employer_survival_brazil.csv")
    ibge = ibge[ibge["series_id"].eq("IBGE_EMPLOYER_2022")].copy()
    return ibge


# ----------------------------------------------------------------------------- fatores

def load_factors() -> pd.DataFrame:
    wb = pd.read_csv(RAW_API / "worldbank_factors_api.csv")[["indicator", "country_code", "year", "value"]]
    tax = pd.read_csv(RAW_API / "oecd_tax_api.csv")
    total = tax[tax["indicator"].eq("tax_rev_pct_gdp:_T")].set_index(["country_code", "year"])["value"]
    shares = []
    for part in ["T_1000", "T_2000", "T_5000"]:
        s = tax[tax["indicator"].eq(f"tax_rev_pct_gdp:{part}")].set_index(["country_code", "year"])["value"]
        share = (s / total * 100).dropna().rename("value").reset_index()
        share["indicator"] = f"share:{part}"
        shares.append(share)
    raw = pd.concat([wb, tax, *shares], ignore_index=True)

    rows = []
    for code, (indicator, name, dim, unit, source, transform, sign) in FACTORS.items():
        part = raw[raw["indicator"].eq(indicator)].copy()
        if transform == "log":
            part = part[part["value"] > 0]
            part["value"] = np.log(part["value"])
        part["factor_code"] = code
        rows.append(part[["country_code", "year", "factor_code", "value"]])
    long = pd.concat(rows, ignore_index=True)
    long = long[long["country_code"].isin(OECD_MEMBERS | {"BRA"})]
    return long


def factor_window(factors: pd.DataFrame, start: int, end: int) -> pd.DataFrame:
    sub = factors[factors["year"].between(start, end)]
    return sub.groupby(["country_code", "factor_code"])["value"].mean().unstack()


# ----------------------------------------------------------------------------- análises

def correlate(outcome: pd.Series, wide_factors: pd.DataFrame, design: str) -> pd.DataFrame:
    rows = []
    for code in FACTORS:
        if code not in wide_factors:
            continue
        df = pd.concat([outcome.rename("y"), wide_factors[code].rename("x")], axis=1, join="inner").dropna()
        n = len(df)
        if n < MIN_N or df["x"].std() == 0:
            rows.append({"design": design, "factor_code": code, "n": n})
            continue
        pr = stats.pearsonr(df["x"], df["y"])
        sr = stats.spearmanr(df["x"], df["y"])
        loo = [stats.pearsonr(df.drop(i)["x"], df.drop(i)["y"]).statistic for i in df.index]
        slope = np.polyfit(df["x"], df["y"], 1)[0]
        rows.append({
            "design": design, "factor_code": code, "n": n,
            "pearson_r": pr.statistic, "pearson_p": pr.pvalue,
            "spearman_rho": sr.statistic, "spearman_p": sr.pvalue,
            "slope_pp_per_unit": slope, "slope_pp_per_sd": slope * df["x"].std(),
            "loo_pearson_min": min(loo), "loo_pearson_max": max(loo),
            "includes_brazil": "BRA" in df.index,
        })
    out = pd.DataFrame(rows)
    if "pearson_p" in out:
        out["pearson_q_bh"] = bh_adjust(out["pearson_p"])
        out["spearman_q_bh"] = bh_adjust(out["spearman_p"])
    return out


def panel_dataset(headline: pd.DataFrame, factors: pd.DataFrame) -> pd.DataFrame:
    s3 = headline[headline["age_years"].eq(3) & headline["valid"] & headline["cohort_year"].between(2011, 2017)]
    s3 = s3[s3["country_code"].isin(OECD_MEMBERS)]
    panel = s3[["country_code", "cohort_year", "reference_year", "survival_rate_pct", "cohort_inconsistent"]].copy()
    fwide = factors.pivot_table(index=["country_code", "year"], columns="factor_code", values="value")
    for code in FACTORS:
        if code not in fwide:
            continue
        series = fwide[code]
        vals = []
        for c, k in zip(panel["country_code"], panel["cohort_year"]):
            window = [series.get((c, y), np.nan) for y in (k - 3, k - 2, k - 1)]
            vals.append(np.nanmean(window) if np.isfinite(window).any() else np.nan)
        panel[code] = vals
    return panel


def panel_models(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for code in FACTORS:
        df = panel[["country_code", "cohort_year", "survival_rate_pct", code]].dropna()
        if df["country_code"].nunique() < MIN_N:
            rows.append({"factor_code": code, "n_obs": len(df), "n_countries": df["country_code"].nunique()})
            continue
        df = df.assign(z=(df[code] - df[code].mean()) / df[code].std())
        pooled = smf.ols("survival_rate_pct ~ z + C(cohort_year)", data=df).fit(
            cov_type="cluster", cov_kwds={"groups": pd.factorize(df["country_code"])[0]}
        )
        within = smf.ols("survival_rate_pct ~ z + C(cohort_year) + C(country_code)", data=df).fit(
            cov_type="cluster", cov_kwds={"groups": pd.factorize(df["country_code"])[0]}
        )
        clean = df[~panel.loc[df.index, "cohort_inconsistent"]]
        pooled_clean = smf.ols("survival_rate_pct ~ z + C(cohort_year)", data=clean).fit(
            cov_type="cluster", cov_kwds={"groups": pd.factorize(clean["country_code"])[0]}
        )
        rows.append({
            "factor_code": code, "n_obs": len(df), "n_countries": df["country_code"].nunique(),
            "pooled_beta_pp_per_sd": pooled.params["z"], "pooled_p": pooled.pvalues["z"],
            "pooled_ci_low": pooled.conf_int().loc["z", 0], "pooled_ci_high": pooled.conf_int().loc["z", 1],
            "pooled_clean_beta": pooled_clean.params["z"], "pooled_clean_p": pooled_clean.pvalues["z"],
            "within_beta_pp_per_sd": within.params["z"], "within_p": within.pvalues["z"],
        })
    out = pd.DataFrame(rows)
    out["pooled_q_bh"] = bh_adjust(out["pooled_p"])
    out["within_q_bh"] = bh_adjust(out["within_p"])
    return out


def panel_multivariate(panel: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    df = panel[["country_code", "cohort_year", "survival_rate_pct", *MULTIVARIATE_SET]].dropna().copy()
    for code in MULTIVARIATE_SET:
        df[code] = (df[code] - df[code].mean()) / df[code].std()
    formula = "survival_rate_pct ~ " + " + ".join(MULTIVARIATE_SET) + " + C(cohort_year)"
    fit = smf.ols(formula, data=df).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(df["country_code"])[0]})
    ci = fit.conf_int()
    table = pd.DataFrame({
        "factor_code": MULTIVARIATE_SET,
        "beta_pp_per_sd": [fit.params[c] for c in MULTIVARIATE_SET],
        "ci_low": [ci.loc[c, 0] for c in MULTIVARIATE_SET],
        "ci_high": [ci.loc[c, 1] for c in MULTIVARIATE_SET],
        "p_value": [fit.pvalues[c] for c in MULTIVARIATE_SET],
    })
    vif = {}
    X = df[MULTIVARIATE_SET].values
    for i, code in enumerate(MULTIVARIATE_SET):
        others = np.delete(X, i, axis=1)
        others = np.column_stack([np.ones(len(X)), others])
        beta, *_ = np.linalg.lstsq(others, X[:, i], rcond=None)
        resid = X[:, i] - others @ beta
        r2 = 1 - resid.var() / X[:, i].var()
        vif[code] = 1 / (1 - r2)
    table["vif"] = table["factor_code"].map(vif)
    info = {"n_obs": int(fit.nobs), "n_countries": int(df["country_code"].nunique()), "r2": float(fit.rsquared)}
    return table, info


def composition_index(raw: pd.DataFrame, dim: str) -> pd.Series:
    """Efeito-país de uma regressão com efeitos fixos de setor (ou porte) e de ano (3 anos, obs. 2017–2019)."""
    base = raw[raw["valid"] & raw["age_years"].eq(3) & raw["reference_year"].between(2017, 2019)]
    base = base[base["ref_area"].isin(OECD_MEMBERS)]
    if dim == "sector":
        df = base[base["activity"].isin(SECTORS) & base["size_class"].eq("_T")].rename(columns={"activity": "cell"})
    else:
        agg = base[base["activity"].isin(ACTIVITY_PREFERENCE) & base["size_class"].isin(SIZES)]
        pref = agg.assign(p=agg["activity"].map({a: i for i, a in enumerate(ACTIVITY_PREFERENCE)}))
        keep = pref.groupby("ref_area")["p"].transform("min").eq(pref["p"])
        df = pref[keep].rename(columns={"size_class": "cell"})
    counts = df.groupby("ref_area")["cell"].nunique()
    min_cells = 8 if dim == "sector" else 3
    df = df[df["ref_area"].isin(counts[counts >= min_cells].index)]
    fit = smf.ols("survival_rate_pct ~ C(ref_area, Sum) + C(cell) + C(reference_year)", data=df).fit()
    countries = sorted(df["ref_area"].unique())
    effects = {}
    for i, c in enumerate(countries[:-1]):
        effects[c] = fit.params[f"C(ref_area, Sum)[S.{c}]"]
    effects[countries[-1]] = -sum(effects.values())
    grand = df["survival_rate_pct"].mean()
    return pd.Series({c: grand + e for c, e in effects.items()})


# ----------------------------------------------------------------------------- principal

def main() -> None:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    ANALYSIS.mkdir(parents=True, exist_ok=True)

    raw, headline = load_survival()
    ibge = load_ibge()
    factors = load_factors()

    valid = headline[headline["valid"]]
    s = valid.set_index(["country_code", "age_years", "reference_year"])["survival_rate_pct"]

    # A1 — coorte 2017, 3 anos
    a1 = s.xs((3, 2020), level=("age_years", "reference_year"))
    a1 = a1[a1.index.isin(OECD_MEMBERS)]
    brazil_s3 = float(ibge.loc[ibge["survival_age_years"].eq(3), "survival_rate_pct"].iloc[0])
    a1 = pd.concat([a1, pd.Series({"BRA": brazil_s3})])

    # A2 — média coortes 2014–2016
    a2_base = valid[valid["age_years"].eq(3) & valid["reference_year"].between(2017, 2019) & valid["country_code"].isin(OECD_MEMBERS)]
    a2_counts = a2_base.groupby("country_code").size()
    a2 = a2_base.groupby("country_code")["survival_rate_pct"].mean()[a2_counts >= 2]

    # B — coorte 2017, 2 anos, OCDE para todos
    b = s.xs((2, 2019), level=("age_years", "reference_year"))
    b = b[b.index.isin(OECD_MEMBERS | {"BRA"})]

    sector_idx = composition_index(raw, "sector")
    size_idx = composition_index(raw, "size")

    f_1416 = factor_window(factors, 2014, 2016)
    f_1113 = factor_window(factors, 2011, 2013)
    f_1215 = factor_window(factors, 2012, 2015)

    corr = pd.concat([
        correlate(a1, f_1416, "A1"),
        correlate(a2, f_1113, "A2"),
        correlate(b, f_1416, "B"),
        correlate(sector_idx, f_1215, "S_sector"),
        correlate(size_idx, f_1215, "S_size"),
    ], ignore_index=True)

    panel = panel_dataset(headline, factors)
    pmodels = panel_models(panel)
    multi, multi_info = panel_multivariate(panel)

    # Síntese de robustez por fator
    meta = pd.DataFrame(
        [(c, v[1], v[2], v[3], v[4], v[6]) for c, v in FACTORS.items()],
        columns=["factor_code", "factor_name", "dimension", "unit", "source", "expected_sign"],
    )
    piv_r = corr.pivot(index="factor_code", columns="design", values="pearson_r")
    piv_p = corr.pivot(index="factor_code", columns="design", values="pearson_p")
    piv_q = corr.pivot(index="factor_code", columns="design", values="pearson_q_bh")
    summary = meta.set_index("factor_code").copy()
    for d in DESIGNS:
        summary[f"r_{d}"] = piv_r.get(d)
        summary[f"p_{d}"] = piv_p.get(d)
        summary[f"q_{d}"] = piv_q.get(d)
    pm = pmodels.set_index("factor_code")
    summary["panel_beta"] = pm["pooled_beta_pp_per_sd"]
    summary["panel_p"] = pm["pooled_p"]
    summary["panel_q"] = pm["pooled_q_bh"]
    summary["panel_within_beta"] = pm["within_beta_pp_per_sd"]
    summary["panel_within_p"] = pm["within_p"]

    def classify(row: pd.Series) -> str:
        signs = [np.sign(row.get(f"r_{d}")) for d in DESIGNS if pd.notna(row.get(f"r_{d}"))]
        signs.append(np.sign(row["panel_beta"]) if pd.notna(row["panel_beta"]) else np.nan)
        signs = [x for x in signs if pd.notna(x)]
        consistent = len(signs) >= 4 and (all(x > 0 for x in signs) or all(x < 0 for x in signs))
        sig_designs = sum(
            1 for d in DESIGNS if pd.notna(row.get(f"p_{d}")) and row[f"p_{d}"] < 0.05
        ) + int(pd.notna(row["panel_p"]) and row["panel_p"] < 0.05)
        survives_fdr = (pd.notna(row["panel_q"]) and row["panel_q"] < 0.10) or (
            pd.notna(row.get("q_A1")) and row["q_A1"] < 0.10
        )
        if consistent and sig_designs >= 3 and survives_fdr:
            return "Robusta"
        if consistent and sig_designs >= 2:
            return "Sugestiva"
        if consistent:
            return "Mesmo sinal, sem significância"
        return "Inconsistente"

    summary["evidence"] = summary.apply(classify, axis=1)
    summary = summary.reset_index()

    # Divergência IBGE × OCDE para o Brasil (coorte 2017)
    bra_oecd = valid[valid["country_code"].eq("BRA") & valid["cohort_year"].eq(2017)].set_index("age_years")["survival_rate_pct"]
    divergence = ibge[["survival_age_years", "survival_rate_pct"]].rename(
        columns={"survival_age_years": "age_years", "survival_rate_pct": "ibge_pct"}
    )
    divergence["oecd_pct"] = divergence["age_years"].map(bra_oecd)
    divergence["diff_pp"] = divergence["oecd_pct"] - divergence["ibge_pct"]

    # Rankings / posição do Brasil
    def position(series: pd.Series) -> dict:
        ordered = series.sort_values(ascending=False)
        out = {"n": int(len(ordered)), "oecd_median": float(ordered.drop("BRA", errors="ignore").median())}
        if "BRA" in ordered.index:
            out["brazil"] = float(ordered["BRA"])
            out["brazil_rank"] = int(list(ordered.index).index("BRA") + 1)
        return out

    positions = {"A1": position(a1), "A2": position(a2), "B": position(b)}

    # ---------------------------------------------------------------- gravação
    headline.to_csv(PROCESSED / "fact_survival_oecd_api.csv", index=False)
    f_out = factors.merge(meta, on="factor_code", how="left")
    f_out["country_name_pt"] = f_out["country_code"].map(name_pt)
    f_out.to_csv(PROCESSED / "fact_factors_api.csv", index=False)

    def outcome_frame(series: pd.Series, design: str, wide: pd.DataFrame) -> pd.DataFrame:
        df = series.rename("survival_rate_pct").to_frame()
        df.index.name = "country_code"
        df = df.join(wide, how="left").reset_index()
        df.insert(1, "country_name_pt", df["country_code"].map(name_pt))
        df.insert(2, "design", design)
        return df.sort_values("survival_rate_pct", ascending=False)

    outcome_frame(a1, "A1", f_1416).to_csv(PROCESSED / "analytic_A1_cohort2017_s3.csv", index=False)
    outcome_frame(a2, "A2", f_1113).to_csv(PROCESSED / "analytic_A2_cohorts2014_2016_s3.csv", index=False)
    outcome_frame(b, "B", f_1416).to_csv(PROCESSED / "analytic_B_cohort2017_s2.csv", index=False)
    outcome_frame(sector_idx, "S_sector", f_1215).to_csv(PROCESSED / "analytic_S_sector_index.csv", index=False)
    outcome_frame(size_idx, "S_size", f_1215).to_csv(PROCESSED / "analytic_S_size_index.csv", index=False)
    panel.to_csv(PROCESSED / "panel_country_cohort_s3.csv", index=False)

    coverage = f_1416.notna().astype(int)
    coverage = coverage.reindex(sorted(set(a1.index) | set(b.index)))
    coverage.insert(0, "country_name_pt", [name_pt(c) for c in coverage.index])
    coverage["factors_available"] = coverage[list(FACTORS)].sum(axis=1)
    coverage.to_csv(PROCESSED / "coverage_factors_2014_2016.csv")

    corr = corr.merge(meta[["factor_code", "factor_name", "dimension"]], on="factor_code", how="left")
    corr.to_csv(ANALYSIS / "correlations_by_design.csv", index=False)
    pmodels.merge(meta[["factor_code", "factor_name", "dimension"]], on="factor_code").to_csv(ANALYSIS / "panel_models.csv", index=False)
    multi.merge(meta[["factor_code", "factor_name"]], on="factor_code").to_csv(ANALYSIS / "panel_multivariate.csv", index=False)
    summary.to_csv(ANALYSIS / "evidence_summary.csv", index=False)
    divergence.to_csv(ANALYSIS / "brazil_ibge_vs_oecd.csv", index=False)

    validation = {
        "oecd_rows_total": int(len(raw)),
        "oecd_rows_invalid_value": int((~raw["valid"]).sum()),
        "headline_cohorts_inconsistent": int(headline.loc[headline["valid"], ["country_code", "cohort_year"]][headline.loc[headline["valid"], "cohort_inconsistent"]].drop_duplicates().shape[0]),
        "activity_used": headline.groupby("country_code")["activity"].first().to_dict(),
        "designs": {d: DESIGNS[d] for d in DESIGNS},
        "positions": positions,
        "panel": {"n_obs": int(len(panel)), "n_countries": int(panel["country_code"].nunique()),
                  "cohorts": sorted(int(x) for x in panel["cohort_year"].unique())},
        "multivariate": multi_info,
        "factors": len(FACTORS),
        "min_n": MIN_N,
    }
    (ANALYSIS / "validation.json").write_text(json.dumps(validation, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(validation["positions"], indent=1))


if __name__ == "__main__":
    main()
