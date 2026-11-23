# Sürü İHA — Hızlı Başlatma Komutları

Tüm komutlar proje ana klasöründe (`/home/utku/suru_iha`) çalıştırılır.

---

## 1. Simülasyonu Başlat (Terminal 1)
Gazebo dünyasını ve 3 adet PX4 SITL dronunu başlatır:
```bash
PX4_DIR=~/PX4-Autopilot ./betikler/sitl_baslat.sh 3
```
*(Gazebo açılınca kamera bir drona kilitlenirse serbest bırakmak için:)*
```bash
gz topic -t /gui/follow -m gz.msgs.StringMsg -p 'data: ""'
```

---

## 2. Görev 1 — Dinamik Sürü (Terminal 2 & 3)

**Terminal 2 — 3 dağıtık dron yazılımını başlat:**
```bash
./betikler/suru_baslat.sh gorev1 3
```

**Terminal 3 — YKİ "Başlat" komutunu gönder (tek seferliktir, sonra kapanır):**
```bash
./venv/bin/python betikler/baslat_komutu.py
```

---

## 3. Görev 2 — Yarı Otonom Sürü (Terminal 2 & 3)

**Terminal 2 — 3 dağıtık dron yazılımını başlat:**
```bash
./betikler/suru_baslat.sh gorev2 3
```

**Terminal 3 — Tek kumanda (klavye) ile sürüyü yönet:**
```bash
./venv/bin/python betikler/gorev2_kumanda.py
```
Klavye tuşları:
- `t` : Kalkış (tüm sürü)
- `l` : İniş (tüm sürü)
- `w / s` : İleri / Geri (Hareket Modu) veya Pitch Eğim (Manevra Modu)
- `a / d` : Sol / Sağ (Hareket Modu) veya Roll Eğim (Manevra Modu)
- `r / f` : Yüksel / Alçal
- `q / e` : Sola / Sağa Yaw (Formasyon Rotasyonu)
- `m` : Mod değiştir (`hareket` ↔ `manevra`)
- `1 / 2 / 3` : Formasyon seç (`1`: Ok başı, `2`: V, `3`: Çizgi)

---

## 4. Tek İHA'yı Elle Başlatmak (Gerekirse)
```bash
./venv/bin/python -m yazilim.ana --iha-id 1 --iha-sayisi 3 --gorev gorev1
```
- YKİ beklemeden hemen kalkması için sonuna `--hemen-basla` eklenebilir.

---

## 5. Birim Testlerini Çalıştır
```bash
./betikler/test_calistir.sh
```
