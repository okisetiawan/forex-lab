from forexlab.data import Bar


def sma(values: list[float], period: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    running = 0.0
    for i, value in enumerate(values):
        running += value
        if i >= period:
            running -= values[i - period]
        if i >= period - 1:
            out[i] = running / period
    return out


def atr(bars: list[Bar], period: int = 14) -> list[float | None]:
    """Average true range as a simple moving average of true range."""
    true_ranges = []
    for i, bar in enumerate(bars):
        if i == 0:
            true_ranges.append(bar.high - bar.low)
        else:
            prev_close = bars[i - 1].close
            true_ranges.append(max(bar.high - bar.low, abs(bar.high - prev_close), abs(bar.low - prev_close)))
    return sma(true_ranges, period)


def ma_crossover(bars: list[Bar], fast: int, slow: int) -> list[int]:
    """+1 on the close where the fast SMA crosses above the slow one, -1 where it crosses below, else 0."""
    if fast >= slow:
        raise ValueError("Periode MA cepat harus lebih kecil dari MA lambat.")
    closes = [b.close for b in bars]
    fast_ma, slow_ma = sma(closes, fast), sma(closes, slow)
    signals = [0] * len(bars)
    for i in range(1, len(bars)):
        if None in (fast_ma[i - 1], slow_ma[i - 1], fast_ma[i], slow_ma[i]):
            continue
        before = fast_ma[i - 1] - slow_ma[i - 1]
        now = fast_ma[i] - slow_ma[i]
        if before <= 0 < now:
            signals[i] = 1
        elif before >= 0 > now:
            signals[i] = -1
    return signals
