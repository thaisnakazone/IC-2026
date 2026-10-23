#!/usr/bin/env python3
"""Build the survival-of-firms pilot and the data bundle used by the dashboard.

The pilot deliberately keeps the outcome comparison and the exploratory factor
correlations in separate products.  The former is aligned (2017 cohort, 2020
observation, three-year employer-enterprise survival); the latter uses the OECD
2020-2023 ecosystem scores and is therefore labelled as temporally misaligned.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "survival"
PROCESSED = ROOT / "data" / "processed" / "survival"
ANALYSIS = ROOT / "analysis" / "survival"
# Etapa 2: o dashboard principal é gerado por src/build_dashboard_v2.py.
# Os dados do piloto ficam arquivados em dashboard/piloto_assets/ para não sobrescrever a versão atual.
DASHBOARD_ASSETS = ROOT / "dashboard" / "piloto_assets"

SOURCE_OECD_SURVIVAL = (
    "https://www.oecd.org/en/publications/entrepreneurial-ecosystem-diagnostics_7096961f-en/"
    "full-report/key-data-for-selected-entrepreneurship-indicators_1c1f628c.html"
)
SOURCE_OECD_FACTORS = (
    "https://www.oecd.org/en/publications/entrepreneurial-ecosystem-diagnostics_7096961f-en/"
    "full-report/cross-country-diagnostic-results_aa27755d.html"
)
SOURCE_IBGE = "https://biblioteca.ibge.gov.br/index.php/biblioteca-catalogo?id=2102142&view=detalhes"
SOURCE_IBGE_LEGACY = (
    "https://agenciadenoticias.ibge.gov.br/agencia-noticias/2012-agencia-de-noticias/noticias/"
    "29212-com-taxa-de-sobrevivencia-de-84-1-pais-tem-saldo-negativo-de-empresas-em-2018"
)

COUNTRY_PT = {
    "AUS": "Austrália", "AUT": "Áustria", "BEL": "Bélgica", "BRA": "Brasil",
    "CAN": "Canadá", "CHE": "Suíça", "CHL": "Chile", "COL": "Colômbia",
    "CRI": "Costa Rica", "CZE": "Tchéquia", "DEU": "Alemanha", "DNK": "Dinamarca",
    "ESP": "Espanha", "EST": "Estônia", "FIN": "Finlândia", "FRA": "França",
    "GBR": "Reino Unido", "GRC": "Grécia", "HUN": "Hungria", "IRL": "Irlanda",
    "ISL": "Islândia", "ISR": "Israel", "ITA": "Itália", "JPN": "Japão",
    "KOR": "Coreia do Sul", "LTU": "Lituânia", "LUX": "Luxemburgo", "LVA": "Letônia",
    "MEX": "México", "NLD": "Países Baixos", "NOR": "Noruega", "NZL": "Nova Zelândia",
    "POL": "Polônia", "PRT": "Portugal", "SVK": "Eslováquia", "SVN": "Eslovênia",
    "SWE": "Suécia", "TUR": "Turquia", "USA": "Estados Unidos",
}

FACTOR_LABELS = {
    "institution": "Instituições",
    "culture": "Cultura empreendedora",
    "networks": "Redes",
    "infrastructure": "Infraestrutura",
    "markets": "Mercados",
    "finance": "Financiamento",
    "knowledge": "Conhecimento",
    "talent": "Talento",
    "leadership": "Liderança",
    "intermediate_services": "Serviços intermediários",
}

CONTEXT_LABELS = {
    "tax_to_gdp_pct": ("Carga tributária / PIB", "% do PIB", "Tributação"),
    "gdp_per_capita_ppp_constant": ("PIB per capita PPC", "US$ internacionais constantes", "Macroeconomia"),
    "gdp_growth_pct": ("Crescimento do PIB", "% a.a.", "Macroeconomia"),
    "inflation_pct": ("Inflação", "% a.a.", "Macroeconomia"),
    "unemployment_pct": ("Desemprego", "% da força de trabalho", "Mercado de trabalho"),
    "new_business_density": ("Densidade de novos negócios", "por mil adultos", "Dinamismo empresarial"),
}


def bh_adjust(pvalues: pd.Series) -> pd.Series:
    """Benjamini-Hochberg adjusted p-values, preserving the original index."""
    p = pvalues.astype(float)
    order = np.argsort(p.to_numpy())
    ranked = p.to_numpy()[order]
    adjusted = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    adjusted = np.clip(adjusted, 0, 1)
    out = np.empty(len(p))
    out[order] = adjusted
    return pd.Series(out, index=p.index)


def build_survival_fact() -> pd.DataFrame:
    oecd = pd.read_csv(RAW / "oecd_employer_survival_latest.csv")
    oecd = oecd.assign(
        country_name_pt=oecd["country_code"].map(COUNTRY_PT),
        series_id="OECD_EMPLOYER_SURVIVAL_3Y",
        source="OCDE",
        population_definition="Empresas empregadoras",
        activity="Total — indústria, construção e serviços de mercado",
        size_class="Total",
        source_url=SOURCE_OECD_SURVIVAL,
        comparability_tier=np.where(oecd["reference_year"].eq(2020), "A", "B"),
        comparability_note=np.where(
            oecd["reference_year"].eq(2020),
            "Mesma coorte, horizonte, população e ano do corte principal",
            "Conceito alinhado, mas ano de referência diferente do corte principal",
        ),
    )

    ibge = pd.read_csv(RAW / "ibge_employer_survival_brazil.csv")
    legacy = ibge["series_id"].eq("IBGE_ALL_ENTERPRISES_PRE2022")
    exact = (~legacy) & ibge["survival_age_years"].eq(3) & ibge["reference_year"].eq(2020)
    ibge = ibge.assign(
        country_name_pt="Brasil",
        source="IBGE",
        activity="Total das atividades cobertas pela Demografia das Empresas",
        size_class="Total",
        source_url=np.where(legacy, SOURCE_IBGE_LEGACY, SOURCE_IBGE),
        comparability_tier=np.select([legacy, exact], ["C", "A"], default="B"),
        comparability_note=np.select(
            [legacy, exact],
            [
                "Série antiga de empresas ativas; não encadear com empresas empregadoras",
                "Mesma coorte, horizonte, população e ano do corte principal",
            ],
            default="Empresas empregadoras comparáveis conceitualmente, mas outro horizonte",
        ),
    )
    columns = [
        "country_code", "country_name_pt", "country_en", "reference_year", "cohort_year",
        "survival_age_years", "survival_rate_pct", "series_id", "source",
        "population_definition", "activity", "size_class", "comparability_tier",
        "comparability_note", "source_url", "source_note",
    ]
    return pd.concat([oecd[columns], ibge[columns]], ignore_index=True).sort_values(
        ["country_code", "series_id", "survival_age_years"]
    )


def build_factor_fact() -> tuple[pd.DataFrame, pd.DataFrame]:
    ecosystem = pd.read_csv(RAW / "oecd_ecosystem_scores_2020_2023.csv")
    ecosystem["country_name_pt"] = ecosystem["country_code"].map(COUNTRY_PT)
    long = ecosystem.melt(
        id_vars=["country_code", "country_name_pt", "country_en"],
        value_vars=list(FACTOR_LABELS),
        var_name="factor_code",
        value_name="value",
    )
    long = long.assign(
        factor_name=long["factor_code"].map(FACTOR_LABELS),
        dimension="Ecossistema empreendedor",
        period_start=2020,
        period_end=2023,
        unit="Escore normalizado (0–100)",
        source="OCDE — Entrepreneurial Ecosystem Diagnostics 2025",
        source_url=SOURCE_OECD_FACTORS,
        timing_role="Posterior/concomitante ao desfecho de 2020",
        analysis_status="Exploratório — desalinhamento temporal",
    )

    panel_path = ROOT / "data" / "processed" / "painel_principal_2013_2024.csv"
    context = pd.DataFrame()
    if panel_path.exists():
        panel = pd.read_csv(panel_path)
        context = panel.loc[panel["year"].eq(2017), ["country_code", "country_name", *CONTEXT_LABELS]].copy()
        context = context.melt(
            id_vars=["country_code", "country_name"],
            value_vars=list(CONTEXT_LABELS),
            var_name="factor_code",
            value_name="value",
        )
        context["country_name_pt"] = context["country_code"].map(COUNTRY_PT).fillna(context["country_name"])
        context["country_en"] = context["country_code"]
        context["factor_name"] = context["factor_code"].map(lambda x: CONTEXT_LABELS[x][0])
        context["unit"] = context["factor_code"].map(lambda x: CONTEXT_LABELS[x][1])
        context["dimension"] = context["factor_code"].map(lambda x: CONTEXT_LABELS[x][2])
        context = context.assign(
            period_start=2017,
            period_end=2017,
            source="Banco Mundial/OCDE — painel anterior da pesquisa",
            source_url="",
            timing_role="Prévio/contemporâneo à coorte de 2017",
            analysis_status="Cobertura insuficiente no corte comum para correlação",
        )
        context = context[long.columns]

    return long, context


def calculate_correlations(cross_section: pd.DataFrame, ecosystem_long: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict] = []
    for code, group in ecosystem_long.groupby("factor_code", sort=False):
        merged = cross_section[["country_code", "survival_rate_pct"]].merge(
            group[["country_code", "value"]], on="country_code", how="inner"
        ).dropna()
        n = len(merged)
        pearson = stats.pearsonr(merged["value"], merged["survival_rate_pct"])
        spearman = stats.spearmanr(merged["value"], merged["survival_rate_pct"])
        slope, intercept = np.polyfit(merged["value"], merged["survival_rate_pct"], 1)
        loo = []
        for i in range(n):
            reduced = merged.drop(merged.index[i])
            loo.append(stats.pearsonr(reduced["value"], reduced["survival_rate_pct"]).statistic)
        rows.append(
            {
                "factor_code": code,
                "factor_name": FACTOR_LABELS[code],
                "n": n,
                "pearson_r": pearson.statistic,
                "pearson_p": pearson.pvalue,
                "spearman_rho": spearman.statistic,
                "spearman_p": spearman.pvalue,
                "r_squared": pearson.statistic ** 2,
                "slope": slope,
                "intercept": intercept,
                "loo_pearson_min": min(loo),
                "loo_pearson_max": max(loo),
                "timing_warning": "Desfecho em 2020; fatores compostos no período 2020–2023",
                "interpretation": "Associação exploratória; não interpretar como efeito causal",
            }
        )
    result = pd.DataFrame(rows)
    result["pearson_q_bh"] = bh_adjust(result["pearson_p"])
    result["spearman_q_bh"] = bh_adjust(result["spearman_p"])
    return result.sort_values("pearson_r", key=lambda s: s.abs(), ascending=False).reset_index(drop=True)


def serialise_records(df: pd.DataFrame) -> list[dict]:
    clean = df.replace({np.nan: None})
    return clean.to_dict(orient="records")


def build_standalone_dashboard() -> None:
    """Create a single-file edition that opens without a local web server."""
    dashboard = ROOT / "dashboard"
    html = (dashboard / "index.html").read_text(encoding="utf-8")
    css = (DASHBOARD_ASSETS / "styles.css").read_text(encoding="utf-8")
    data_js = (DASHBOARD_ASSETS / "data.js").read_text(encoding="utf-8")
    app_js = (DASHBOARD_ASSETS / "app.js").read_text(encoding="utf-8")
    csv_bytes = (DASHBOARD_ASSETS / "cross_section_2017_2020.csv").read_bytes()
    csv_uri = "data:text/csv;base64," + base64.b64encode(csv_bytes).decode("ascii")
    html = html.replace('<link rel="stylesheet" href="assets/styles.css">', f"<style>\n{css}\n</style>")
    html = html.replace('href="assets/cross_section_2017_2020.csv"', f'href="{csv_uri}"')
    html = html.replace('<script src="assets/data.js"></script>', f"<script>\n{data_js}\n</script>")
    html = html.replace('<script src="assets/app.js"></script>', f"<script>\n{app_js}\n</script>")
    (dashboard / "sobrevivencia_dashboard_piloto.html").write_text(html, encoding="utf-8")


def write_report(cross: pd.DataFrame, corr: pd.DataFrame, context_long: pd.DataFrame) -> None:
    brazil = float(cross.loc[cross["country_code"].eq("BRA"), "survival_rate_pct"].iloc[0])
    oecd = cross.loc[cross["country_code"].ne("BRA"), "survival_rate_pct"]
    rank = int(cross.sort_values("survival_rate_pct", ascending=False).reset_index(drop=True).index[
        cross.sort_values("survival_rate_pct", ascending=False).reset_index(drop=True)["country_code"].eq("BRA")
    ][0] + 1)
    strongest = corr.iloc[0]
    lines = [
        "# Piloto — sobrevivência empresarial e ecossistema empreendedor",
        "",
        "## Resultado comparável",
        "",
        f"O corte principal reúne **{len(cross)} países** (Brasil + {len(oecd)} países da OCDE), ",
        "todos com empresas empregadoras nascidas em 2017 e sobrevivência após três anos, observada em 2020.",
        f"O Brasil registra **{brazil:.1f}%**, contra mediana de **{oecd.median():.1f}%** nos países da OCDE ",
        f"e ocupa a posição **{rank} de {len(cross)}** no ranking do piloto.",
        "",
        "## Correlações do protótipo",
        "",
        f"A maior correlação linear em módulo é **{strongest.factor_name}** ",
        f"(r = {strongest.pearson_r:.2f}; n = {int(strongest.n)}; p = {strongest.pearson_p:.3f}; ",
        f"q-BH = {strongest.pearson_q_bh:.3f}). Mesmo essa associação é apenas exploratória.",
        "Os escores de ecossistema cobrem 2020–2023 e, portanto, não antecedem de forma limpa a coorte de 2017.",
        "",
        "## Regra de interpretação",
        "",
        "- O ranking de sobrevivência do corte 2017→2020 é a parte substantivamente comparável do piloto.",
        "- As correlações com os dez pilares da OCDE testam a arquitetura visual e estatística, não causalidade.",
        "- O dashboard exibe Pearson, Spearman, p-valor, correção de múltiplos testes e intervalo leave-one-out.",
        f"- Os indicadores tributários e macroeconômicos de 2017 têm somente {context_long['country_code'].nunique()} países ",
        "na base anterior e cobertura ainda menor no corte comum; ficam visíveis na matriz de cobertura, mas não são correlacionados.",
        "",
        "## Próxima extração necessária",
        "",
        "Extrair séries anuais/coortes da OCDE e indicadores explicativos anteriores a 2017 ",
        "(preferencialmente médias 2014–2016 ou valores de 2016), ampliando o número de países. ",
        "Só então as correlações devem entrar como resultado acadêmico.",
    ]
    (ANALYSIS / "relatorio_piloto.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    for directory in (PROCESSED, ANALYSIS, DASHBOARD_ASSETS):
        directory.mkdir(parents=True, exist_ok=True)

    survival = build_survival_fact()
    ecosystem_long, context_long = build_factor_fact()
    factors = pd.concat([ecosystem_long, context_long], ignore_index=True)

    cross = survival.loc[
        survival["reference_year"].eq(2020)
        & survival["cohort_year"].eq(2017)
        & survival["survival_age_years"].eq(3)
        & survival["population_definition"].str.contains("empregadoras|Employer", case=False, regex=True)
    ].copy()
    cross = cross.sort_values("survival_rate_pct", ascending=False).reset_index(drop=True)
    cross["rank"] = np.arange(1, len(cross) + 1)
    cross["group"] = np.where(cross["country_code"].eq("BRA"), "Brasil", "OCDE")

    ecosystem_wide = ecosystem_long.pivot(index="country_code", columns="factor_code", values="value").reset_index()
    analytical = cross.merge(ecosystem_wide, on="country_code", how="left")
    correlations = calculate_correlations(cross.loc[cross["country_code"].ne("BRA")], ecosystem_long)

    coverage = cross[["country_code", "country_name_pt", "survival_rate_pct", "group"]].copy()
    for code in FACTOR_LABELS:
        coverage[code] = coverage["country_code"].map(ecosystem_wide.set_index("country_code")[code])
    context_common = context_long.pivot_table(index="country_code", columns="factor_code", values="value", aggfunc="first")
    for code in CONTEXT_LABELS:
        coverage[code] = coverage["country_code"].map(context_common[code] if code in context_common else pd.Series(dtype=float))
    coverage["ecosystem_factors_available"] = coverage[list(FACTOR_LABELS)].notna().sum(axis=1)
    coverage["context_factors_available"] = coverage[list(CONTEXT_LABELS)].notna().sum(axis=1)

    survival.to_csv(PROCESSED / "fact_survival.csv", index=False)
    factors.to_csv(PROCESSED / "fact_factors.csv", index=False)
    cross.to_csv(PROCESSED / "cross_section_2017_2020.csv", index=False)
    cross.to_csv(DASHBOARD_ASSETS / "cross_section_2017_2020.csv", index=False)
    analytical.to_csv(PROCESSED / "panel_survival_ecosystem_pilot.csv", index=False)
    coverage.to_csv(PROCESSED / "coverage_matrix.csv", index=False)
    correlations.to_csv(ANALYSIS / "correlations_pilot.csv", index=False)

    brazil_curve = survival.loc[
        survival["country_code"].eq("BRA")
        & survival["series_id"].eq("IBGE_EMPLOYER_2022")
    ].sort_values("survival_age_years")
    latest = survival.loc[
        survival["survival_age_years"].eq(3)
        & ~survival["series_id"].eq("IBGE_ALL_ENTERPRISES_PRE2022")
    ].sort_values("survival_rate_pct", ascending=False)
    payload = {
        "meta": {
            "title": "Sobreviver para crescer",
            "subtitle": "Piloto internacional de sobrevivência empresarial",
            "common_cut": "Coorte 2017 · sobrevivência em 3 anos · observação 2020",
            "factor_period": "Escores OCDE 2020–2023",
            "updated": "2026-08-21",
            "method_warning": "Correlações exploratórias: fatores 2020–2023 não antecedem integralmente o desfecho de 2020.",
        },
        "summary": {
            "countries": int(len(cross)),
            "oecd_countries": int(cross["country_code"].ne("BRA").sum()),
            "brazil_rate": float(cross.loc[cross["country_code"].eq("BRA"), "survival_rate_pct"].iloc[0]),
            "oecd_median": float(cross.loc[cross["country_code"].ne("BRA"), "survival_rate_pct"].median()),
            "oecd_mean": float(cross.loc[cross["country_code"].ne("BRA"), "survival_rate_pct"].mean()),
            "brazil_rank": int(cross.loc[cross["country_code"].eq("BRA"), "rank"].iloc[0]),
        },
        "common_cross_section": serialise_records(cross),
        "latest_survival": serialise_records(latest),
        "brazil_curve": serialise_records(brazil_curve),
        "ecosystem_factors": serialise_records(ecosystem_long),
        "context_factors": serialise_records(context_long),
        "correlations": serialise_records(correlations),
        "coverage": serialise_records(coverage),
        "factor_labels": FACTOR_LABELS,
        "context_labels": {k: v[0] for k, v in CONTEXT_LABELS.items()},
        "sources": json.loads((ROOT / "config" / "survival_sources.json").read_text(encoding="utf-8")),
    }
    json_text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    (DASHBOARD_ASSETS / "data.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    (DASHBOARD_ASSETS / "data.js").write_text(f"window.DASHBOARD_DATA={json_text};\n", encoding="utf-8")
    # build_standalone_dashboard()  # desativado: dashboard/sobrevivencia_dashboard_piloto.html fica como arquivo histórico
    write_report(cross, correlations, context_long)

    validation = {
        "status": "ok",
        "common_cross_section_rows": int(len(cross)),
        "common_cross_section_oecd": int(cross["country_code"].ne("BRA").sum()),
        "brazil_rate": float(cross.loc[cross["country_code"].eq("BRA"), "survival_rate_pct"].iloc[0]),
        "duplicate_country_rows": int(cross.duplicated("country_code").sum()),
        "correlation_factors": int(len(correlations)),
        "minimum_correlation_n": int(correlations["n"].min()),
        "legacy_series_separated": bool(
            survival.loc[survival["series_id"].eq("IBGE_ALL_ENTERPRISES_PRE2022"), "comparability_tier"].eq("C").all()
        ),
    }
    (ANALYSIS / "validation.json").write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(validation, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
