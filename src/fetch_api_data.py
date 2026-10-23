"""Extração das APIs oficiais (OCDE SDMX e Banco Mundial v2) para o estudo de sobrevivência.

Gera os três arquivos de `data/raw/api/` usados por `src/build_survival_v2.py`:

- oecd_survival_api.csv      Sobrevivência de empresas empregadoras (OCDE, SDBS)
- oecd_tax_api.csv           Receita tributária (% PIB) e alíquota estatutária do IRPJ (OCDE)
- worldbank_factors_api.csv  Indicadores macro, financeiros, institucionais, tecnológicos e
                             de complexidade tributária (Banco Mundial: WDI, WGI e Doing Business)

Nenhuma API exige chave. Execute de uma máquina com acesso à internet:

    python src/fetch_api_data.py
"""

from __future__ import annotations

import io
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "api"

# Brasil + países da OCDE presentes na demografia empresarial + referências usuais
COUNTRIES = [
    "BRA", "AUT", "BEL", "COL", "CZE", "DNK", "EST", "FIN", "FRA", "DEU", "GRC", "HUN", "ISL",
    "IRL", "ISR", "ITA", "KOR", "LVA", "LTU", "LUX", "NLD", "NZL", "NOR", "POL", "PRT", "SVK",
    "SVN", "ESP", "SWE", "CHE", "TUR", "GBR", "AUS", "CAN", "USA", "JPN", "MEX", "CRI", "CHL",
]

OECD_SDMX = "https://sdmx.oecd.org/public/rest/data"
SURVIVAL_FLOW = "OECD.SDD.TPS,DSD_SDBSBD_ISIC4@DF_BD_EMP_S,1.0"
# Dimensões: FREQ.REF_AREA.MEASURE.ACTIVITY.SIZE_CLASS.AGE.ENT_TYPE.BUSINESS_STAGE.UNIT_MEASURE
SURVIVAL_ACTIVITIES = "BTNX642+BTN+_T+B+C+D+E+F+G+H+I+J+L+M+N"
SURVIVAL_KEY = f"A..ENT.{SURVIVAL_ACTIVITIES}..Y1+Y2+Y3.ENT_EMP.ACTIVE.PT_ENT_B"

REVENUE_FLOW = "OECD.CTP.TPS,DSD_REV_COMP_GLOBAL@DF_RSGLOBAL,"
CIT_FLOW = "OECD.CTP.TPS,DSD_TAX_CIT@DF_CIT,"

WORLD_BANK = "https://api.worldbank.org/v2"
# (fonte, indicador). Fonte 2 = WDI, 3 = WGI, 1 = Doing Business
WB_INDICATORS = [
    ("2", "NY.GDP.MKTP.KD.ZG"), ("2", "FP.CPI.TOTL.ZG"), ("2", "NY.GDP.PCAP.PP.KD"),
    ("2", "SL.UEM.TOTL.ZS"), ("2", "FS.AST.PRVT.GD.ZS"), ("2", "FR.INR.RINR"), ("2", "FR.INR.LNDP"),
    ("3", "GOV_WGI_RQ.EST"), ("3", "GOV_WGI_RL.EST"), ("3", "GOV_WGI_GE.EST"),
    ("2", "IT.NET.USER.ZS"), ("2", "GB.XPD.RSDV.GD.ZS"), ("2", "GC.TAX.TOTL.GD.ZS"),
    ("1", "PAY.TAX.TOT.TAX.RT.ZS"), ("1", "PAY.TAX.TM"), ("1", "PAY.TAX.PYMT.FREQ.NO"),
    ("1", "PAY.TAX.PRFT.CP.ZS"), ("1", "PAY.TAX.LABR.TAX.CONTR.ZS"), ("1", "IC.REG.DURS.MA.DY"),
    ("1", "RESLV.ISV.RCOV.RT"), ("2", "IC.BUS.NDNS.ZS"),
]


def get(url: str, **kwargs) -> requests.Response:
    for attempt in range(4):
        response = requests.get(url, timeout=180, **kwargs)
        if response.status_code == 200:
            return response
        time.sleep(2 * (attempt + 1))
    response.raise_for_status()
    return response


def sdmx_csv(flow: str, key: str, start: int, end: int | None = None) -> pd.DataFrame:
    params = {"startPeriod": start, "dimensionAtObservation": "AllDimensions", "format": "csvfile"}
    if end:
        params["endPeriod"] = end
    return pd.read_csv(io.StringIO(get(f"{OECD_SDMX}/{flow}/{key}", params=params).text))


def fetch_survival() -> pd.DataFrame:
    raw = sdmx_csv(SURVIVAL_FLOW, SURVIVAL_KEY, 2008)
    return pd.DataFrame(
        {
            "ref_area": raw["REF_AREA"],
            "activity": raw["ACTIVITY"],
            "size_class": raw["SIZE_CLASS"],
            "age_years": raw["AGE"].str[1:].astype(int),
            "reference_year": raw["TIME_PERIOD"].astype(int),
            "survival_rate_pct": raw["OBS_VALUE"].round(2),
            "obs_status": raw["OBS_STATUS"],
        }
    )


def fetch_tax() -> pd.DataFrame:
    areas = "+".join(COUNTRIES)
    frames = []
    total = sdmx_csv(REVENUE_FLOW, f"{areas}.TAX_REV.S13._T._T.PT_B1GQ.A", 2010, 2021)
    parts = sdmx_csv(REVENUE_FLOW, f"{areas}.TAX_REV.S13.T_1000+T_1200+T_2000+T_5000._T.PT_B1GQ.A", 2010, 2021)
    for df in (total, parts):
        frames.append(pd.DataFrame({
            "indicator": "tax_rev_pct_gdp:" + df["STANDARD_REVENUE"],
            "country_code": df["REF_AREA"], "year": df["TIME_PERIOD"], "value": df["OBS_VALUE"],
        }))
    cit = sdmx_csv(CIT_FLOW, f"{areas}.A.CIT_C.ST.PT_INC_TAX.S13._Z._Z._Z", 2010, 2021)
    frames.append(pd.DataFrame({
        "indicator": "cit_combined_statutory_rate",
        "country_code": cit["REF_AREA"], "year": cit["TIME_PERIOD"], "value": cit["OBS_VALUE"],
    }))
    return pd.concat(frames, ignore_index=True)


def fetch_world_bank() -> pd.DataFrame:
    rows = []
    areas = ";".join(COUNTRIES)
    for source, indicator in WB_INDICATORS:
        url = f"{WORLD_BANK}/country/{areas}/indicator/{indicator}"
        meta, data = get(url, params={"source": source, "format": "json", "date": "2010:2021", "per_page": 2000}).json()
        for item in data or []:
            if item["value"] is None:
                continue
            rows.append({
                "indicator": indicator,
                "country_code": item.get("countryiso3code") or item["country"]["id"],
                "year": int(item["date"]),
                "value": float(item["value"]),
                "source_lastupdated": meta.get("lastupdated"),
            })
    return pd.DataFrame(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    fetch_survival().to_csv(OUT / "oecd_survival_api.csv", index=False)
    fetch_tax().to_csv(OUT / "oecd_tax_api.csv", index=False)
    fetch_world_bank().to_csv(OUT / "worldbank_factors_api.csv", index=False)
    print(f"Arquivos gravados em {OUT}")


if __name__ == "__main__":
    main()
