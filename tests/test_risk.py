import unittest

from forexlab.lot import main
from forexlab.risk import (
    RiskRuleViolation,
    pip_size,
    pip_value_per_lot,
    position_size,
)


class PipTests(unittest.TestCase):
    def test_pip_size(self):
        self.assertEqual(pip_size("EURUSD"), 0.0001)
        self.assertEqual(pip_size("usd/jpy"), 0.01)

    def test_pip_value_quote_is_account(self):
        self.assertAlmostEqual(pip_value_per_lot("EURUSD", "USD"), 10.0)

    def test_pip_value_base_is_account(self):
        self.assertAlmostEqual(pip_value_per_lot("USDJPY", "USD", price=150.0), 1000 / 150)

    def test_pip_value_cross_needs_rate(self):
        self.assertAlmostEqual(pip_value_per_lot("EURGBP", "USD", quote_to_account_rate=1.27), 12.7)
        with self.assertRaises(ValueError):
            pip_value_per_lot("EURGBP", "USD")

    def test_idr_account(self):
        self.assertAlmostEqual(pip_value_per_lot("EURUSD", "IDR", quote_to_account_rate=16000), 160000)

    def test_metals_and_bad_pairs_rejected(self):
        for pair in ("XAUUSD", "EUR", "EURUSD1"):
            with self.assertRaises(ValueError):
                pip_size(pair)


class PositionSizeTests(unittest.TestCase):
    def test_basic_one_percent(self):
        result = position_size(1000, 1, 20, 10.0)
        self.assertEqual(result.lots, 0.05)
        self.assertAlmostEqual(result.actual_risk, 10.0)

    def test_rounds_down_never_over_budget(self):
        result = position_size(1000, 1, 30, 10.0)
        self.assertEqual(result.lots, 0.03)
        self.assertLessEqual(result.actual_risk, result.risk_budget)

    def test_risk_above_cap_is_refused(self):
        with self.assertRaises(RiskRuleViolation):
            position_size(1000, 5, 20, 10.0)

    def test_stop_loss_is_mandatory(self):
        with self.assertRaises(RiskRuleViolation):
            position_size(1000, 1, 0, 10.0)

    def test_below_min_lot_is_refused(self):
        with self.assertRaises(RiskRuleViolation):
            position_size(100, 1, 50, 10.0)


class CliTests(unittest.TestCase):
    def test_exit_codes(self):
        self.assertEqual(main(["--balance", "1000", "--pair", "EURUSD", "--sl", "20"]), 0)
        self.assertEqual(main(["--balance", "1000", "--pair", "EURUSD", "--sl", "20", "--risk", "5"]), 2)
        self.assertEqual(main(["--balance", "1000", "--pair", "EURGBP", "--sl", "20"]), 1)


if __name__ == "__main__":
    unittest.main()
