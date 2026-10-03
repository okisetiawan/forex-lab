import argparse
import sys
from dataclasses import dataclass

from forexlab.data import Bar, load_csv
from forexlab.risk import (
    DEFAULT_MAX_RISK_PERCENT,
    STANDARD_LOT_UNITS,
    RiskRuleViolation,
    pip_size,
    pip_value_per_lot,
    position_size,
    split_pair,
)
from forexlab.strategy import atr, ma_crossover


@dataclass(frozen=True)
class Trade:
    direction: int
    entry_time: str
    exit_time: str
    entry_price: float
    exit_price: float
    lots: float
    r_multiple: float
    profit: float
    balance_after: float
    exit_reason: str


@dataclass(frozen=True)
class Stats:
    trades: int
    skipped: int
    win_rate: float
    avg_win_r: float
    avg_loss_r: float
    expectancy_r: float
    profit_factor: float | None
    net_profit: float
    return_percent: float
    max_drawdown_percent: float
    max_losing_streak: int


def _to_account(amount_in_quote: float, quote: str, account: str, price: float) -> float:
    return amount_in_quote if quote == account else amount_in_quote / price


def run_backtest(
    bars: list[Bar],
    signals: list[int],
    stop_distances: list[float | None],
    pair: str,
    balance: float,
    risk_percent: float = 1.0,
    reward_ratio: float = 2.0,
    spread_pips: float = 1.0,
    account_currency: str = "USD",
    lot_step: float = 0.01,
    min_lot: float = 0.01,
) -> tuple[list[Trade], int]:
    """Bars are bid prices. A signal on bar i is entered at the open of bar i+1, one position at a time.

    When stop loss and take profit both fall inside one bar the stop loss is assumed to hit first,
    and a gap through the stop loss exits at the worse open price.
    """
    if not 0 < risk_percent <= DEFAULT_MAX_RISK_PERCENT:
        raise RiskRuleViolation(
            f"Risiko {risk_percent}% di luar batas 0–{DEFAULT_MAX_RISK_PERCENT}% per posisi."
        )
    base, quote = split_pair(pair)
    account = account_currency.upper()
    if account not in (base, quote):
        raise ValueError(f"Backtest {pair} butuh akun {base} atau {quote}; akun {account} belum didukung.")
    pip = pip_size(pair)
    spread = spread_pips * pip

    trades: list[Trade] = []
    skipped = 0
    i = 1
    while i < len(bars):
        signal, stop_distance = signals[i - 1], stop_distances[i - 1]
        if signal == 0 or not stop_distance:
            i += 1
            continue

        entry_bar = bars[i]
        entry = entry_bar.open + spread if signal == 1 else entry_bar.open
        stop = entry - signal * stop_distance
        target = entry + signal * stop_distance * reward_ratio
        try:
            size = position_size(
                balance,
                risk_percent,
                stop_distance / pip,
                pip_value_per_lot(pair, account, price=entry),
                lot_step=lot_step,
                min_lot=min_lot,
            )
        except RiskRuleViolation:
            skipped += 1
            i += 1
            continue

        exit_price, exit_reason, j = None, "", i
        while j < len(bars):
            bar = bars[j]
            # Shorts close at the ask, so their stops and targets see bid + spread.
            low, high, opening = (bar.low, bar.high, bar.open) if signal == 1 else (
                bar.low + spread, bar.high + spread, bar.open + spread)
            stop_hit = low <= stop if signal == 1 else high >= stop
            target_hit = high >= target if signal == 1 else low <= target
            if stop_hit:
                gapped = j > i and (opening <= stop if signal == 1 else opening >= stop)
                exit_price, exit_reason = (opening if gapped else stop), "stop loss"
                break
            if target_hit:
                exit_price, exit_reason = target, "take profit"
                break
            j += 1
        if exit_price is None:
            j = len(bars) - 1
            last = bars[j]
            exit_price, exit_reason = (last.close if signal == 1 else last.close + spread), "data habis"

        move = (exit_price - entry) * signal
        profit = _to_account(move * size.lots * STANDARD_LOT_UNITS, quote, account, exit_price)
        balance += profit
        trades.append(Trade(
            direction=signal,
            entry_time=entry_bar.time,
            exit_time=bars[j].time,
            entry_price=entry,
            exit_price=exit_price,
            lots=size.lots,
            r_multiple=move / stop_distance,
            profit=profit,
            balance_after=balance,
            exit_reason=exit_reason,
        ))
        i = j + 1
    return trades, skipped


def summarize(trades: list[Trade], starting_balance: float, skipped: int = 0) -> Stats:
    wins = [t for t in trades if t.profit > 0]
    losses = [t for t in trades if t.profit <= 0]
    gross_win = sum(t.profit for t in wins)
    gross_loss = -sum(t.profit for t in losses)

    peak, max_drawdown = starting_balance, 0.0
    streak = longest_streak = 0
    for t in trades:
        peak = max(peak, t.balance_after)
        max_drawdown = max(max_drawdown, (peak - t.balance_after) / peak * 100)
        streak = streak + 1 if t.profit <= 0 else 0
        longest_streak = max(longest_streak, streak)

    final = trades[-1].balance_after if trades else starting_balance
    count = len(trades)
    return Stats(
        trades=count,
        skipped=skipped,
        win_rate=len(wins) / count * 100 if count else 0.0,
        avg_win_r=sum(t.r_multiple for t in wins) / len(wins) if wins else 0.0,
        avg_loss_r=sum(t.r_multiple for t in losses) / len(losses) if losses else 0.0,
        expectancy_r=sum(t.r_multiple for t in trades) / count if count else 0.0,
        profit_factor=gross_win / gross_loss if gross_loss else None,
        net_profit=final - starting_balance,
        return_percent=(final - starting_balance) / starting_balance * 100,
        max_drawdown_percent=max_drawdown,
        max_losing_streak=longest_streak,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m forexlab.backtest",
        description="Backtest strategi moving average crossover dengan stop loss berbasis ATR.",
    )
    parser.add_argument("--csv", required=True, help="File harga dari MT5 (Export Bars) atau CSV Date,Open,High,Low,Close")
    parser.add_argument("--pair", required=True, help="Pair, misalnya EURUSD")
    parser.add_argument("--balance", type=float, default=1000, help="Modal awal (default 1000)")
    parser.add_argument("--account", default="USD", help="Mata uang akun (default USD)")
    parser.add_argument("--risk", type=float, default=1.0, help="Risiko per posisi dalam persen (default 1, maks 2)")
    parser.add_argument("--fast", type=int, default=20, help="Periode MA cepat (default 20)")
    parser.add_argument("--slow", type=int, default=50, help="Periode MA lambat (default 50)")
    parser.add_argument("--atr", type=int, default=14, help="Periode ATR (default 14)")
    parser.add_argument("--atr-mult", type=float, default=1.5, help="Stop loss = ATR x angka ini (default 1.5)")
    parser.add_argument("--rr", type=float, default=2.0, help="Take profit = stop loss x angka ini (default 2)")
    parser.add_argument("--spread", type=float, default=1.0, help="Spread dalam pip (default 1)")
    parser.add_argument("--trades", action="store_true", help="Tampilkan daftar semua transaksi")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        bars = load_csv(args.csv)
        signals = ma_crossover(bars, args.fast, args.slow)
        stops = [a * args.atr_mult if a else None for a in atr(bars, args.atr)]
        trades, skipped = run_backtest(
            bars, signals, stops, args.pair, args.balance,
            risk_percent=args.risk, reward_ratio=args.rr,
            spread_pips=args.spread, account_currency=args.account,
        )
    except RiskRuleViolation as err:
        print(f"DITOLAK: {err}", file=sys.stderr)
        return 2
    except (ValueError, OSError) as err:
        print(f"Input salah: {err}", file=sys.stderr)
        return 1

    stats = summarize(trades, args.balance, skipped)
    account = args.account.upper()
    if args.trades:
        for t in trades:
            side = "BUY " if t.direction == 1 else "SELL"
            print(f"{t.entry_time} -> {t.exit_time}  {side} {t.lots:.2f} lot  "
                  f"{t.r_multiple:+.2f}R  {t.profit:+,.2f} {account}  ({t.exit_reason})")
        print()

    pf = f"{stats.profit_factor:.2f}" if stats.profit_factor is not None else "-"
    print(f"Data             : {len(bars)} bar, {bars[0].time} s/d {bars[-1].time}")
    print(f"Strategi         : MA {args.fast}/{args.slow}, SL = ATR{args.atr} x {args.atr_mult}, R:R 1:{args.rr}, spread {args.spread} pip")
    print(f"Transaksi        : {stats.trades} (dilewati karena risiko: {stats.skipped})")
    print(f"Win rate         : {stats.win_rate:.1f}%")
    print(f"Rata-rata menang : {stats.avg_win_r:+.2f}R   Rata-rata kalah: {stats.avg_loss_r:+.2f}R")
    print(f"Expectancy       : {stats.expectancy_r:+.3f}R per transaksi")
    print(f"Profit factor    : {pf}")
    print(f"Hasil bersih     : {stats.net_profit:+,.2f} {account} ({stats.return_percent:+.1f}%)")
    print(f"Max drawdown     : {stats.max_drawdown_percent:.1f}%")
    print(f"Kalah beruntun   : {stats.max_losing_streak} kali")
    return 0


if __name__ == "__main__":
    sys.exit(main())
