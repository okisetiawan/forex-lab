from dataclasses import dataclass
from decimal import ROUND_DOWN, Decimal

STANDARD_LOT_UNITS = 100_000
DEFAULT_MAX_RISK_PERCENT = 2.0
METALS = {"XAU", "XAG", "XPT", "XPD"}


class RiskRuleViolation(ValueError):
    pass


@dataclass(frozen=True)
class PositionSize:
    lots: float
    risk_budget: float
    actual_risk: float
    actual_risk_percent: float


def split_pair(pair: str) -> tuple[str, str]:
    code = pair.replace("/", "").strip().upper()
    if len(code) != 6 or not code.isalpha():
        raise ValueError(f"Pair tidak dikenali: {pair!r}. Contoh format: EURUSD atau EUR/USD.")
    base, quote = code[:3], code[3:]
    if base in METALS or quote in METALS:
        raise ValueError(
            f"{code} adalah logam mulia; ukuran kontrak dan pip-nya beda per broker, belum didukung."
        )
    return base, quote


def pip_size(pair: str) -> float:
    _, quote = split_pair(pair)
    return 0.01 if quote == "JPY" else 0.0001


def pip_value_per_lot(
    pair: str,
    account_currency: str,
    price: float | None = None,
    quote_to_account_rate: float | None = None,
) -> float:
    """Pip value of one standard lot, in the account currency."""
    base, quote = split_pair(pair)
    account = account_currency.strip().upper()
    value_in_quote = pip_size(pair) * STANDARD_LOT_UNITS

    if quote == account:
        return value_in_quote
    if base == account:
        if not price or price <= 0:
            raise ValueError(f"Untuk {base}{quote} dengan akun {account}, isi harga pair saat ini (--price).")
        return value_in_quote / price
    if not quote_to_account_rate or quote_to_account_rate <= 0:
        raise ValueError(
            f"Untuk {base}{quote} dengan akun {account}, isi kurs 1 {quote} = berapa {account} (--rate)."
        )
    return value_in_quote * quote_to_account_rate


def _floor_to_step(value: float, step: float) -> float:
    steps = (Decimal(str(value)) / Decimal(str(step))).to_integral_value(rounding=ROUND_DOWN)
    return float(steps * Decimal(str(step)))


def position_size(
    balance: float,
    risk_percent: float,
    stop_loss_pips: float,
    pip_value: float,
    lot_step: float = 0.01,
    min_lot: float = 0.01,
    max_risk_percent: float = DEFAULT_MAX_RISK_PERCENT,
) -> PositionSize:
    if balance <= 0:
        raise ValueError("Modal harus lebih dari 0.")
    if stop_loss_pips <= 0:
        raise RiskRuleViolation("Wajib pakai stop loss. Jarak stop loss harus lebih dari 0 pip.")
    if pip_value <= 0:
        raise ValueError("Nilai pip harus lebih dari 0.")
    if risk_percent <= 0:
        raise ValueError("Risiko per posisi harus lebih dari 0%.")
    if risk_percent > max_risk_percent:
        raise RiskRuleViolation(
            f"Risiko {risk_percent}% melewati batas maksimal {max_risk_percent}% per posisi."
        )

    risk_budget = balance * risk_percent / 100
    # Round down, never up: the position must not risk more than the budget.
    lots = _floor_to_step(risk_budget / (stop_loss_pips * pip_value), lot_step)
    if lots < min_lot:
        raise RiskRuleViolation(
            f"Lot minimum {min_lot} dengan stop loss {stop_loss_pips} pip sudah melebihi "
            f"batas risiko {risk_budget:.2f}. Lewati setup ini atau cari stop loss yang lebih dekat."
        )

    actual_risk = lots * stop_loss_pips * pip_value
    return PositionSize(
        lots=lots,
        risk_budget=risk_budget,
        actual_risk=actual_risk,
        actual_risk_percent=actual_risk / balance * 100,
    )
