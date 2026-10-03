import contextlib
import io
import math
import tempfile
import unittest
from pathlib import Path

from forexlab.backtest import Trade, main, run_backtest, summarize
from forexlab.data import Bar, load_csv
from forexlab.strategy import atr, ma_crossover, sma


def bar(o, h, l, c, t="t"):
    return Bar(time=t, open=o, high=h, low=l, close=c)


FLAT = bar(1.1000, 1.1005, 1.0995, 1.1000)


def run(bars, signals, stop=0.0010, **kwargs):
    kwargs.setdefault("balance", 1000)
    kwargs.setdefault("pair", "EURUSD")
    return run_backtest(bars, signals, [stop] * len(bars), **kwargs)


class LongTradeTests(unittest.TestCase):
    def test_take_profit(self):
        bars = [FLAT, FLAT, bar(1.1000, 1.1025, 1.1000, 1.1020)]
        trades, _ = run(bars, [1, 0, 0])
        t = trades[0]
        self.assertAlmostEqual(t.entry_price, 1.1001)
        self.assertEqual(t.lots, 0.1)
        self.assertAlmostEqual(t.r_multiple, 2.0)
        self.assertAlmostEqual(t.profit, 20.0)
        self.assertEqual(t.exit_reason, "take profit")

    def test_stop_wins_when_both_hit_in_one_bar(self):
        bars = [FLAT, FLAT, bar(1.1000, 1.1025, 1.0985, 1.1000)]
        t = run(bars, [1, 0, 0])[0][0]
        self.assertAlmostEqual(t.r_multiple, -1.0)
        self.assertAlmostEqual(t.profit, -10.0)

    def test_gap_through_stop_exits_at_open(self):
        bars = [FLAT, FLAT, bar(1.0980, 1.0985, 1.0970, 1.0975)]
        t = run(bars, [1, 0, 0])[0][0]
        self.assertAlmostEqual(t.exit_price, 1.0980)
        self.assertAlmostEqual(t.r_multiple, -2.1)

    def test_open_position_closes_when_data_ends(self):
        trades, _ = run([FLAT, FLAT, FLAT], [1, 0, 0])
        self.assertEqual(trades[0].exit_reason, "data habis")


class ShortTradeTests(unittest.TestCase):
    def test_take_profit_uses_ask(self):
        bars = [FLAT, FLAT, bar(1.1000, 1.1000, 1.0978, 1.0980)]
        t = run(bars, [-1, 0, 0])[0][0]
        self.assertAlmostEqual(t.r_multiple, 2.0)

    def test_spread_can_trigger_stop(self):
        bars = [FLAT, FLAT, bar(1.1000, 1.1009, 1.0995, 1.1000)]
        t = run(bars, [-1, 0, 0])[0][0]
        self.assertEqual(t.exit_reason, "stop loss")


class EngineRuleTests(unittest.TestCase):
    def test_no_trade_on_signal_at_last_bar(self):
        trades, _ = run([FLAT, FLAT], [0, 1])
        self.assertEqual(trades, [])

    def test_one_position_at_a_time(self):
        bars = [FLAT, FLAT, FLAT, bar(1.1000, 1.1025, 1.1000, 1.1020), FLAT]
        trades, _ = run(bars, [1, 1, 1, 0, 0])
        self.assertEqual(len(trades), 1)

    def test_trade_too_small_is_skipped(self):
        trades, skipped = run([FLAT, FLAT, FLAT], [1, 0, 0], stop=0.0050, balance=100)
        self.assertEqual((trades, skipped), ([], 1))

    def test_balance_compounds(self):
        win = bar(1.1000, 1.1025, 1.1000, 1.1020)
        trades, _ = run([FLAT, FLAT, win, FLAT, win], [1, 0, 1, 0, 0])
        self.assertAlmostEqual(trades[0].balance_after, 1020.0)
        self.assertEqual(trades[1].lots, 0.1)
        self.assertAlmostEqual(trades[1].balance_after, 1040.0)

    def test_usdjpy_profit_converted_to_usd(self):
        flat = bar(150.00, 150.05, 149.95, 150.00)
        win = bar(150.00, 150.70, 150.00, 150.60)
        t = run([flat, flat, win], [1, 0, 0], stop=0.30, pair="USDJPY")[0][0]
        self.assertEqual(t.lots, 0.05)
        self.assertAlmostEqual(t.profit, 0.60 * 0.05 * 100000 / 150.61)

    def test_unsupported_account_currency(self):
        with self.assertRaises(ValueError):
            run([FLAT, FLAT], [1, 0], pair="EURGBP")


class SummaryTests(unittest.TestCase):
    def trade(self, profit, balance_after, r):
        return Trade(1, "a", "b", 1.0, 1.0, 0.1, r, profit, balance_after, "")

    def test_stats(self):
        trades = [
            self.trade(20, 1020, 2.0),
            self.trade(-10, 1010, -1.0),
            self.trade(-10, 1000, -1.0),
            self.trade(20, 1020, 2.0),
        ]
        s = summarize(trades, 1000)
        self.assertEqual(s.win_rate, 50.0)
        self.assertAlmostEqual(s.expectancy_r, 0.5)
        self.assertAlmostEqual(s.profit_factor, 2.0)
        self.assertAlmostEqual(s.max_drawdown_percent, 20 / 1020 * 100)
        self.assertEqual(s.max_losing_streak, 2)
        self.assertAlmostEqual(s.return_percent, 2.0)

    def test_empty(self):
        s = summarize([], 1000)
        self.assertEqual((s.trades, s.profit_factor, s.net_profit), (0, None, 0))


class IndicatorTests(unittest.TestCase):
    def test_sma(self):
        self.assertEqual(sma([1, 2, 3, 4], 2), [None, 1.5, 2.5, 3.5])

    def test_atr_uses_previous_close(self):
        bars = [bar(1, 2, 1, 2), bar(4, 5, 4, 4)]
        self.assertEqual(atr(bars, 2), [None, 2.0])

    def test_crossover(self):
        closes = [5, 4, 3, 2, 1, 2, 3, 4, 5, 6, 5, 4, 3, 2]
        signals = ma_crossover([bar(c, c, c, c) for c in closes], 2, 4)
        self.assertIn(1, signals)
        self.assertIn(-1, signals)
        self.assertLess(signals.index(1), signals.index(-1))


class CsvAndCliTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def write(self, name, text):
        path = Path(self.dir.name) / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_mt5_export(self):
        path = self.write("mt5.csv", "<DATE>\t<TIME>\t<OPEN>\t<HIGH>\t<LOW>\t<CLOSE>\t<TICKVOL>\n"
                                     "2024.01.02\t00:00:00\t1.1\t1.2\t1.0\t1.15\t100\n")
        self.assertEqual(load_csv(path), [Bar("2024.01.02 00:00:00", 1.1, 1.2, 1.0, 1.15)])

    def test_plain_csv(self):
        path = self.write("plain.csv", "Date,Open,High,Low,Close\n2024-01-02,1.1,1.2,1.0,1.15\n")
        self.assertEqual(load_csv(path)[0].close, 1.15)

    def test_missing_columns(self):
        path = self.write("bad.csv", "Date,Price\n2024-01-02,1.1\n")
        with self.assertRaises(ValueError):
            load_csv(path)

    def test_cli_end_to_end(self):
        lines = ["Date,Open,High,Low,Close"]
        for i in range(400):
            price = 1.10 + 0.02 * math.sin(i / 15)
            lines.append(f"d{i},{price:.5f},{price + 0.002:.5f},{price - 0.002:.5f},{price:.5f}")
        path = self.write("wave.csv", "\n".join(lines))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = main(["--csv", str(path), "--pair", "EURUSD", "--trades"])
        self.assertEqual(code, 0)
        self.assertIn("Expectancy", out.getvalue())
        self.assertIn("BUY", out.getvalue())

    def test_cli_rejects_high_risk(self):
        path = self.write("p.csv", "Date,Open,High,Low,Close\n" + "\n".join(
            f"d{i},1.1,1.101,1.099,1.1" for i in range(60)))
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(["--csv", str(path), "--pair", "EURUSD", "--risk", "5"]), 2)


if __name__ == "__main__":
    unittest.main()
