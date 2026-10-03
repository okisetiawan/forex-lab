# forex-lab

Lab pribadi untuk belajar forex dengan cara sistematis: aturan risiko dijadikan kode, strategi diuji dengan data sebelum memakai uang.

| Tahap | Isi | Status |
| --- | --- | --- |
| 1 | Halaman risk management + kalkulator lot | Selesai |
| 2 | Jurnal trading (Supabase) | Belum |
| 3 | Backtester strategi dengan data historis | Belum |
| 4 | Laporan: win rate, expectancy, max drawdown, profit factor | Belum |

## Kalkulator lot

Butuh Python 3.10 ke atas, tanpa library tambahan. Jalankan dari folder ini:

```
python -m forexlab.lot --balance 1000 --pair EURUSD --sl 20
```

Risiko default 1% per posisi. Risiko di atas 2%, posisi tanpa stop loss, dan posisi yang lot minimumnya melebihi batas risiko selalu ditolak. Penjelasan lengkapnya ada di [docs/risk-management.md](docs/risk-management.md).

## Tes

```
python -m unittest discover -s tests -t .
```
