import argparse
import sys

from forexlab.risk import RiskRuleViolation, pip_value_per_lot, position_size


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m forexlab.lot",
        description="Hitung ukuran lot dari modal, risiko, dan jarak stop loss. Risiko di atas 2% selalu ditolak.",
    )
    parser.add_argument("--balance", type=float, required=True, help="Modal di akun, misalnya 1000")
    parser.add_argument("--pair", required=True, help="Pair, misalnya EURUSD")
    parser.add_argument("--sl", type=float, required=True, help="Jarak stop loss dalam pip, sudah termasuk spread")
    parser.add_argument("--risk", type=float, default=1.0, help="Risiko per posisi dalam persen (default 1)")
    parser.add_argument("--account", default="USD", help="Mata uang akun (default USD)")
    parser.add_argument("--price", type=float, help="Harga pair saat ini, kalau mata uang akun = mata uang depan pair")
    parser.add_argument("--rate", type=float, help="Kurs 1 unit mata uang belakang pair dalam mata uang akun")
    parser.add_argument("--lot-step", type=float, default=0.01, help="Kelipatan lot di broker (default 0.01)")
    parser.add_argument("--min-lot", type=float, default=0.01, help="Lot minimum di broker (default 0.01)")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    account = args.account.upper()
    try:
        pip_value = pip_value_per_lot(args.pair, account, price=args.price, quote_to_account_rate=args.rate)
        result = position_size(
            balance=args.balance,
            risk_percent=args.risk,
            stop_loss_pips=args.sl,
            pip_value=pip_value,
            lot_step=args.lot_step,
            min_lot=args.min_lot,
        )
    except RiskRuleViolation as err:
        print(f"DITOLAK: {err}", file=sys.stderr)
        return 2
    except ValueError as err:
        print(f"Input salah: {err}", file=sys.stderr)
        return 1

    print(f"Pair             : {args.pair.upper()}")
    print(f"Nilai pip / lot  : {pip_value:,.2f} {account}")
    print(f"Batas risiko     : {result.risk_budget:,.2f} {account} ({args.risk}% dari {args.balance:,.2f})")
    print(f"Ukuran lot       : {result.lots:.2f}")
    print(f"Risiko sebenarnya: {result.actual_risk:,.2f} {account} ({result.actual_risk_percent:.2f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
