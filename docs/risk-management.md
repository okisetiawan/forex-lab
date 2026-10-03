# Risk Management

Strategi menentukan kapan masuk. Risk management menentukan apakah kamu masih punya akun setelah 50 transaksi. Halaman ini adalah aturan main yang dijalankan sebelum strategi apa pun.

## 1. Risiko per posisi: maksimal 1%

Setiap posisi hanya boleh merugikan **1% dari modal** kalau stop loss kena. Batas kerasnya 2%; kalkulator di repo ini menolak angka di atas itu.

Kenapa sekecil itu? Karena kalah beruntun itu pasti terjadi, bahkan dengan strategi yang bagus. Ini yang tersisa dari modal setelah **10 kali kalah berturut-turut**:

| Risiko per posisi | Modal tersisa | Turun |
| --- | --- | --- |
| 1% | 90,4% | 9,6% |
| 2% | 81,7% | 18,3% |
| 5% | 59,9% | 40,1% |
| 10% | 34,9% | 65,1% |

Dengan 1%, sepuluh kekalahan beruntun cuma luka kecil. Dengan 10%, akun praktis habis.

## 2. Stop loss dulu, baru lot

Urutannya selalu:

1. Tentukan stop loss dari **chart**: di titik mana analisismu terbukti salah (di bawah support, di atas swing high, dan sebagainya).
2. Tambahkan spread ke jarak stop loss. Contoh: stop loss 18 pip + spread 2 pip = 20 pip.
3. Baru hitung lot supaya jarak itu tetap = 1% modal.

Yang salah: menentukan lot dulu ("pakai 0.1 saja"), lalu menaruh stop loss di jarak yang "terasa pas". Itu membuat risiko berubah-ubah tanpa disadari.

## 3. Menghitung ukuran lot

```
Lot = (Modal × Risiko%) ÷ (Jarak SL dalam pip × Nilai pip per lot)
```

**Nilai pip per lot** (1 lot standar = 100.000 unit):

| Kondisi | Nilai pip per lot |
| --- | --- |
| Mata uang belakang pair = mata uang akun (EURUSD, akun USD) | 10 USD |
| Mata uang depan pair = mata uang akun (USDJPY, akun USD) | 1.000 JPY ÷ harga. Di harga 150 = 6,67 USD |
| Pair silang (EURGBP, akun USD) | 10 GBP × kurs GBPUSD. Di kurs 1,27 = 12,70 USD |

Pair JPY memakai pip 0,01; pair lain 0,0001.

**Contoh:** modal 1.000 USD, risiko 1% = 10 USD, EURUSD, stop loss 20 pip.
Lot = 10 ÷ (20 × 10) = **0,05 lot**.

Hasil selalu **dibulatkan ke bawah** ke kelipatan lot broker. Kalau stop loss 30 pip, hitungannya 0,0333, jadi 0,03 lot. Membulatkan ke atas berarti diam-diam melanggar batas 1%.

Kalau lot minimum broker (biasanya 0,01) sudah melebihi 1% modal, **lewati setup itu**. Jangan perkecil stop loss supaya muat.

Pakai kalkulatornya:

```
python -m forexlab.lot --balance 1000 --pair EURUSD --sl 20
python -m forexlab.lot --balance 1000 --pair USDJPY --sl 30 --price 150
python -m forexlab.lot --balance 1000 --pair EURGBP --sl 20 --rate 1.27
```

Hitung ulang lot dari **modal saat ini** setiap kali, bukan dari modal awal. Setelah rugi, posisi otomatis mengecil; setelah untung, membesar pelan-pelan.

## 4. Leverage bukan risiko, tapi godaan

Leverage 1:500 hanya membuat margin yang dikunci broker lebih kecil. Risiko sebenarnya tetap ditentukan oleh **lot × jarak stop loss**. Bahayanya: leverage tinggi membuat posisi kebesaran terasa "bisa", dan di situlah akun biasanya habis. Kalau aturan lot di atas dipatuhi, besar leverage tidak mengubah risikomu.

## 5. Risk:reward dan expectancy

**Risk:reward (R:R)** = jarak take profit dibanding jarak stop loss. Stop loss 20 pip dan take profit 40 pip = 1:2.

R:R menentukan win rate minimal agar tidak rugi:

| R:R | Win rate minimal untuk impas |
| --- | --- |
| 1:1 | 50% |
| 1:1,5 | 40% |
| 1:2 | 33,3% |
| 1:3 | 25% |

**Expectancy** = rata-rata hasil per transaksi, dalam satuan R (1R = jumlah yang dirisikokan):

```
Expectancy = (Win rate × Rata-rata untung dalam R) − (Loss rate × Rata-rata rugi dalam R)
```

- Win rate 40%, R:R 1:2 → 0,4 × 2 − 0,6 × 1 = **+0,2R**. Dengan risiko 10 USD, rata-rata +2 USD per transaksi.
- Win rate 60%, tapi untung rata-rata cuma 0,5R → 0,6 × 0,5 − 0,4 × 1 = **−0,1R**. Sering menang, tapi tetap rugi.

Win rate tinggi tidak berarti profit. Yang menentukan adalah expectancy, dan itu yang nanti diukur oleh backtester.

## 6. Drawdown: turun gampang, naik susah

| Modal turun | Butuh naik untuk balik modal |
| --- | --- |
| 10% | 11,1% |
| 20% | 25% |
| 30% | 42,9% |
| 50% | 100% |
| 75% | 300% |

Makin dalam lubangnya, makin mustahil keluar. Itulah alasan semua batas di halaman ini dibuat ketat.

## 7. Batas kerugian dan aturan emosi

- **Rugi 2 kali berturut-turut dalam sehari → berhenti hari itu.**
- **Rugi 5% dalam seminggu → berhenti sampai minggu depan.**
- Stop loss tidak boleh digeser menjauh. Boleh digeser mendekat untuk mengunci untung.
- Tidak menambah posisi yang sedang rugi (averaging down).
- Kalau muncul keinginan "balas" kekalahan, tutup platform. Itu tanda emosi, bukan analisis.
- Setiap posisi dicatat di jurnal: alasan masuk, kondisi emosi, hasil.

## 8. Checklist sebelum entry

- [ ] Setup sesuai aturan strategi, bukan firasat
- [ ] Stop loss ditentukan dari chart, sudah termasuk spread
- [ ] Lot dihitung kalkulator dari modal saat ini, risiko ≤ 1%
- [ ] R:R minimal 1:1,5
- [ ] Belum kena batas harian atau mingguan
- [ ] Kondisi tenang, tidak sedang mengejar kerugian
