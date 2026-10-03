import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Bar:
    time: str
    open: float
    high: float
    low: float
    close: float


def _normalize(name: str) -> str:
    return name.strip().strip("<>").lower()


def load_csv(path: str | Path) -> list[Bar]:
    """Load OHLC bars from an MT5 export (tab separated, <DATE> <TIME> ...) or a plain Date,Open,High,Low,Close CSV."""
    text = Path(path).read_text(encoding="utf-8-sig")
    first_line = text.splitlines()[0] if text else ""
    delimiter = "\t" if "\t" in first_line else ("," if "," in first_line else ";")
    rows = list(csv.reader(text.splitlines(), delimiter=delimiter))
    if len(rows) < 2:
        raise ValueError(f"{path}: file kosong atau tanpa data.")

    header = [_normalize(h) for h in rows[0]]
    try:
        cols = {key: header.index(key) for key in ("date", "open", "high", "low", "close")}
    except ValueError:
        raise ValueError(f"{path}: kolom wajib date, open, high, low, close. Ditemukan: {rows[0]}") from None
    time_col = header.index("time") if "time" in header else None

    bars = []
    for line_no, row in enumerate(rows[1:], start=2):
        if not row or not any(cell.strip() for cell in row):
            continue
        stamp = row[cols["date"]].strip()
        if time_col is not None:
            stamp = f"{stamp} {row[time_col].strip()}"
        try:
            bar = Bar(
                time=stamp,
                open=float(row[cols["open"]]),
                high=float(row[cols["high"]]),
                low=float(row[cols["low"]]),
                close=float(row[cols["close"]]),
            )
        except (ValueError, IndexError):
            raise ValueError(f"{path}: baris {line_no} tidak bisa dibaca: {row}") from None
        bars.append(bar)
    return bars
