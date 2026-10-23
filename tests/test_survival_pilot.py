import json
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


class SurvivalPilotTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = pd.read_csv(ROOT / "data" / "processed" / "survival" / "cross_section_2017_2020.csv")
        cls.fact = pd.read_csv(ROOT / "data" / "processed" / "survival" / "fact_survival.csv")
        cls.corr = pd.read_csv(ROOT / "analysis" / "survival" / "correlations_pilot.csv")
        cls.payload = json.loads((ROOT / "dashboard" / "assets" / "data.json").read_text(encoding="utf-8"))

    def test_common_cross_section(self):
        self.assertEqual(len(self.base), 26)
        self.assertEqual(self.base["country_code"].nunique(), 26)
        self.assertTrue(self.base["cohort_year"].eq(2017).all())
        self.assertTrue(self.base["reference_year"].eq(2020).all())
        self.assertTrue(self.base["survival_age_years"].eq(3).all())

    def test_brazil_value_and_rank(self):
        brazil = self.base.loc[self.base["country_code"].eq("BRA")].iloc[0]
        self.assertAlmostEqual(brazil["survival_rate_pct"], 49.4)
        self.assertEqual(brazil["rank"], 18)

    def test_method_break_is_separate(self):
        legacy = self.fact.loc[self.fact["series_id"].eq("IBGE_ALL_ENTERPRISES_PRE2022")]
        self.assertEqual(len(legacy), 1)
        self.assertTrue(legacy["comparability_tier"].eq("C").all())

    def test_correlation_guardrails(self):
        self.assertEqual(len(self.corr), 10)
        self.assertTrue((self.corr["n"] >= 15).all())
        self.assertTrue((self.corr["pearson_q_bh"] >= self.corr["pearson_p"] - 1e-12).all())
        self.assertTrue((self.corr["pearson_q_bh"] > 0.05).all())

    def test_dashboard_payload(self):
        self.assertEqual(self.payload["summary"]["countries"], 26)
        self.assertEqual(len(self.payload["common_cross_section"]), 26)
        self.assertEqual(len(self.payload["correlations"]), 10)


if __name__ == "__main__":
    unittest.main()
