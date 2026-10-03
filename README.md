# forex-lab

Lab pribadi untuk belajar forex dengan cara sistematis: aturan risiko dijadikan kode, strategi diuji dengan data sebelum memakai uang.

| Tahap | Isi | Status |
| --- | --- | --- |
| 1 | Halaman risk management + kalkulator lot | Selesai |
| 2 | Jurnal trading (Supabase) | Belum |
| 3 | Backtester strategi dengan data historis | Selesai (strategi MA crossover) |
| 4 | Laporan: win rate, expectancy, max drawdown, profit factor | Selesai, jadi bagian backtester |

Butuh Python 3.10 ke atas, tanpa library tambahan. Semua perintah dijalankan dari folder ini.

## Kalkulator lot

```
python -m forexlab.lot --balance 1000 --pair EURUSD --sl 20
```

Risiko default 1% per posisi. Risiko di atas 2%, posisi tanpa stop loss, dan posisi yang lot minimumnya melebihi batas risiko selalu ditolak. Penjelasan lengkapnya ada di [docs/risk-management.md](docs/risk-management.md).

## Backtester

### 1. Ambil data dari MetaTrader 5

1. Buka MT5, tekan `Ctrl+U` (View → Symbols).
2. Pilih tab **Bars**, pilih pair (misalnya EURUSD) dan timeframe (H4 atau D1).
3. Isi rentang tanggal sepanjang mungkin, minimal 3–5 tahun, lalu klik **Request**.
4. Klik **Export Bars** dan simpan file CSV-nya ke folder `data/` di repo ini.

File CSV biasa dengan kolom `Date,Open,High,Low,Close` juga bisa dibaca.

### 2. Jalankan

```
python -m forexlab.backtest --csv data/EURUSD_H4.csv --pair EURUSD
```

Pengaturan yang bisa diubah: `--fast` dan `--slow` (periode MA, default 20 dan 50), `--atr-mult` (stop loss = ATR × angka ini, default 1.5), `--rr` (take profit = stop loss × angka ini, default 2), `--spread` (pip, default 1; samakan dengan spread broker-mu), `--risk` (persen, maks 2), `--balance`. Tambah `--trades` untuk melihat semua transaksi.

### 3. Cara membaca hasil

- **Expectancy** adalah angka terpenting. Negatif berarti strategi itu rugi dalam jangka panjang, berapa pun win rate-nya.
- **Max drawdown** menunjukkan penurunan terdalam yang harus kamu tahan secara mental.
- **Kalah beruntun** menunjukkan berapa kali kalah berturut-turut yang wajar terjadi. Kalau itu terjadi di akun sungguhan, itu bukan tanda strateginya rusak.

Sebagai pembanding, di data acak strategi bawaan menghasilkan expectancy sekitar −0,11R: rugi tipis karena spread. Strategi yang layak dicoba di akun demo harus konsisten positif di beberapa pair dan rentang waktu, bukan cuma di satu periode.

### Aturan simulasi

Dibuat konservatif supaya hasilnya tidak terlihat lebih bagus dari kenyataan:

- Sinyal dihitung dari harga penutupan bar, posisi dibuka di harga pembukaan bar berikutnya. Tidak ada data masa depan yang dipakai.
- Harga di file dianggap harga bid. Buy masuk di ask (bid + spread), sell keluar di ask.
- Kalau stop loss dan take profit sama-sama tersentuh dalam satu bar, dianggap stop loss yang kena.
- Kalau harga gap melewati stop loss, posisi ditutup di harga pembukaan yang lebih buruk.
- Satu posisi dalam satu waktu. Lot dihitung ulang dari modal terakhir dengan aturan yang sama seperti kalkulator lot.
- Akun harus memakai salah satu mata uang di pair (misalnya akun USD untuk EURUSD atau USDJPY).

## Tes

```
python -m unittest discover -s tests -t .
```
