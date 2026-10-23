"""Testes de integridade da etapa 2 (rode depois de `python src/build_survival_v2.py`)."""

import json
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PROC = ROOT / "data" / "processed" / "survival_v2"
ANA = ROOT / "analysis" / "survival_v2"


class SurvivalV2Tests(unittest.TestCase):
    def test_raw_api_files_exist(self):
        for name in ["oecd_survival_api.csv", "oecd_tax_api.csv", "worldbank_factors_api.csv"]:
            self.assertTrue((ROOT / "data" / "raw" / "api" / name).exists(), name)

    def test_survival_rates_in_range(self):
        df = pd.read_csv(PROC / "fact_survival_oecd_api.csv")
        valid = df[df["valid"]]
        self.assertTrue(valid["survival_rate_pct"].between(0, 100, inclusive="right").all())

    def test_one_row_per_country_in_cross_sections(self):
        for name in ["analytic_A1_cohort2017_s3.csv", "analytic_A2_cohorts2014_2016_s3.csv", "analytic_B_cohort2017_s2.csv"]:
            df = pd.read_csv(PROC / name)
            self.assertFalse(df["country_code"].duplicated().any(), name)
            self.assertGreaterEqual(len(df), 20, name)

    def test_brazil_in_a1_and_b(self):
        a1 = pd.read_csv(PROC / "analytic_A1_cohort2017_s3.csv").set_index("country_code")
        b = pd.read_csv(PROC / "analytic_B_cohort2017_s2.csv").set_index("country_code")
        self.assertAlmostEqual(a1.loc["BRA", "survival_rate_pct"], 49.4)
        self.assertIn("BRA", b.index)

    def test_factors_precede_cohort_in_panel(self):
        panel = pd.read_csv(PROC / "panel_country_cohort_s3.csv")
        self.assertTrue((panel["reference_year"] - panel["cohort_year"]).eq(3).all())
        self.assertGreaterEqual(panel["country_code"].nunique(), 25)

    def test_correlations_have_min_n_and_bh(self):
        corr = pd.read_csv(ANA / "correlations_by_design.csv")
        computed = corr.dropna(subset=["pearson_r"])
        self.assertTrue((computed["n"] >= 15).all())
        self.assertTrue((computed["pearson_q_bh"] >= computed["pearson_p"] - 1e-12).all())

    def test_validation_file(self):
        v = json.loads((ANA / "validation.json").read_text(encoding="utf-8"))
        self.assertEqual(v["factors"], 22)
        self.assertIn("A1", v["positions"])


if __name__ == "__main__":
    unittest.main()
