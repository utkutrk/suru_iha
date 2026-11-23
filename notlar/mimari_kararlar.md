# Mimari Kararlar ve Gazebo Çalıştırma Rehberi

## Mimari Kararlar
1. **Dağıtık (lidersiz) yapı [5.3]:** Her dronda aynı `yazilim/ana.py` çalışır. Her dron kendi içinde aynı `SanalYapi` modelini hesaplar ve UDP üzerinden `DURUM` paketleriyle adım bariyerini senkronize eder.
2. **Ortak koordinat çerçevesi:** PX4'te her dronun yerel NED orijini kendi kalkış noktasıdır. `yazilim/dron/mavsdk_dron.py`, GPS + `ayarlar/saha.json` ortak orijiniyle her dronun yerel ofsetini başlangıçta kalibre eder; böylece tüm sürü tek ortak NED çerçevesinde uçar.
3. **Tek son güvenlik kapısı [5.1, Tablo 5-6]:** PX4'e giden her hedef `yazilim/guvenlik/son_kapi.py` içinden geçer (10 m alt irtifa tabanı, tavan, geofence, yumuşak hız rampası, yatay çarpışma itmesi, geçişte irtifa katmanları, GPS tutarlılık kontrolü).
4. **Tek yerden genişletme:** Formasyonlar yalnız `yazilim/suru/formasyonlar.py` tablosunda, komutlar yalnız `yazilim/suru/komutlar.py` tablosunda tanımlıdır; `if/elif` zinciri yoktur.
5. **Komut kaynağı soyutlaması:** Görev 1 komutları `KomutKaynagi` arayüzünden gelir; şimdilik `SenaryoKomutKaynagi` (Şekil 2 QR JSON biçimi) takılıdır. İleride QR okuyucu aynı arayüze takılacaktır.
6. **Gazebo koordinat dönüşümü:** Gazebo Harmonic ENU `(Doğu, Kuzey, Yukarı)`, PX4 ise NED `(Kuzey, Doğu, Aşağı)` kullanır. `simulasyon/dunyalar/teknofest_alani.sdf` ve `betikler/sitl_baslat.sh` dönüşümü otomatik yapar.

## Gazebo'da 3 İHA ile Çalıştırma

### 1. Terminal — Gazebo + 3 PX4 SITL başlat
```bash
PX4_DIR=~/PX4-Autopilot ./betikler/sitl_baslat.sh 3
```

### 2. Terminal — 3 dağıtık sürü ajanını başlat
Görev 1 (Dinamik Sürü):
```bash
./betikler/suru_baslat.sh gorev1 3
```
veya Görev 2 (Yarı Otonom):
```bash
./betikler/suru_baslat.sh gorev2 3
```

### 3. Terminal — Başlatma / Kumanda
- **Görev 1:** Tek seferlik YKİ başlat komutu gönderir ve çıkar (YKİ bağlantısı kesilse de sürü görevi tamamlar):
  ```bash
  ./venv/bin/python betikler/baslat_komutu.py
  ```
- **Görev 2:** Tek kumanda (klavye) ile tüm sürüyü yönetir (`t` kalkış, `w/a/s/d` hareket veya eğim, `q/e` yaw, `r/f` irtifa, `m` mod değiştir, `1/2/3` formasyon, `l` iniş):
  ```bash
  ./venv/bin/python betikler/gorev2_kumanda.py
  ```
