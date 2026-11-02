"""Offline checks for cohort validation and rate denominators."""
import unittest
import numpy as np
import pandas as pd
from analyze import ROOT, calculate_metrics


class MetricTests(unittest.TestCase):
    def setUp(self):
        self.raw = pd.DataFrame({
            'team': [f'T{i}' for i in range(32)], 'season': 2024,
            'situation': '5on5', 'iceTime': 7200,
            'unblockedShotAttemptsFor': 100, 'xGoalsFor': 5.0})

    def test_rates_and_identity(self):
        result = calculate_metrics(self.raw)
        self.assertTrue(result.attempts_per_60.eq(50).all())
        self.assertTrue(result.xg_per_attempt.eq(.05).all())
        self.assertTrue(result.xg_per_60.eq(2.5).all())
        self.assertNotIn('xg_per_60', self.raw)

    def test_other_situations_are_excluded(self):
        extra = self.raw.copy().assign(situation='all')
        self.assertEqual(len(calculate_metrics(pd.concat([self.raw, extra]))), 32)

    def test_duplicate_and_missing_team(self):
        with self.assertRaises(ValueError):
            calculate_metrics(self.raw.iloc[:-1])
        self.raw.loc[1, 'team'] = 'T0'
        with self.assertRaises(ValueError):
            calculate_metrics(self.raw)

    def test_invalid_numeric_values(self):
        for column, value in [('iceTime', 0), ('iceTime', np.inf),
                              ('unblockedShotAttemptsFor', -1),
                              ('xGoalsFor', 101), ('xGoalsFor', np.nan),
                              ('season', 2023)]:
            with self.subTest(column=column, value=value):
                raw = self.raw.copy()
                raw[column] = raw[column].astype(float)
                raw.loc[0, column] = value
                with self.assertRaises(ValueError):
                    calculate_metrics(raw)

    def test_required_columns(self):
        with self.assertRaisesRegex(ValueError, 'columns'):
            calculate_metrics(self.raw.drop(columns='iceTime'))

    def test_published_snapshot(self):
        result = calculate_metrics(pd.read_csv(ROOT / 'data/teams_2024.csv'))
        self.assertEqual(len(result), 32)
        self.assertAlmostEqual(result.attempts_per_60.corr(result.xg_per_attempt), -.0299, places=4)


if __name__ == '__main__':
    unittest.main()
