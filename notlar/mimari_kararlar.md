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

## Rotasyon ve ayrılma düzeltmeleri (2026-11-23 prova analizinden)
7. **Rotasyon yay üzerinde [5.1]:** `gorev1_dinamik._formasyonu_dondur`, yaw'ı `rotasyon_adim_deg` (15°) adımlarına böler; her adım senkronlanır. Tek hamlede slotlar düz çizgiyle yer değiştirdiği için komşular arası mesafe 6 m'den ~3,6 m'ye iniyordu; adımlarla ~5,9 m kalır (birim testte doğrulanır). Neden: Çarpışma −20.
8. **Adım sayacı tüm dronlarda aynı olayları sayar:** Ayrılan dron havada olmasa da görev akışını "mantıksal adım" olarak (uçuşsuz) izler; sanal yapısı ve sayacı sürüyle aynı kalır. Eski davranışta dönen dron QR-2'yi tek başına tekrar uçuyor, sürü ~50 sn bekliyordu. Dönen dron hazır olunca bir sonraki adım başında uçuşlu katılır.
9. **Ayrılan slotu "boş" sayma:** Her dron bir sonraki QR navigasyonunda `ayrilan_idleri` listesini temizler (şartname: en geç o QR'da katılır). Eskiden diğer dronlar ayrılanı sonsuza kadar ayrılmış sayıyordu.
10. **Konum kaydı ve prova raporu:** Her dron `kayitlar/konum_*_ihaX.csv` yazar (10 Hz, ortak NED). `betikler/prova_raporu.py` bunlardan en küçük mesafe, gerçek en düşük irtifa, slot hatası ve renkli alana iniş sapmasını hesaplar. "3 temiz prova" kapısı bu rapora dayanır.
11. **Ayrılan dron için katılım adımı [5.1, Tablo 7]:** `cikar` uygulandıktan sonraki ilk QR navigasyonunun ardından (QR okunmadan önce) tüm dronlar "ayrılan dronun katılımı" adımını yapar. Sürü slotlarında bekler, ayrılan dron uçuşunu bitirip slotuna oturunca adım biter. Adımın yapılıp yapılmayacağı `_katilim_beklenenleri` listesine bakar (tüm dronlarca aynı); dron erken dönse bile sayaç kaymaz. Neden: şartname en geç sonraki QR'da katılımı istiyor ve formasyon/manevra puanı için en az 3 aktif İHA gerekiyor.
12. **Karışık dizilimde slot ataması [5.1, 5.3]:** `yazilim/suru/slot_atama.py`. BASLAT'tan sonra, kalkıştan önce her dron yerdeki (hareketsiz) konumları paylaşır ve aynı hesabı kendi içinde yapar: toplam yatay yolu en kısa yapan bire bir eşleşme (Macar yöntemi). Bu eşleşmede düz yollar kesişmez. Konumlar 0,5 m ızgaraya yuvarlanır, eşitlikte numara = slot korunur. Herkes önerisini yayınlar; öneriler uyuşmaz ya da komşu susarsa herkes numara = slot'a döner. Slot sahibi görev boyunca değişmez (ayrılan dron aynı slota döner). Neden: Provada karışık dizilimde slot = numara yolları kesiştirdi (2,0 m yakınlaşma, toplam yol 16,1 m vs 3,7 m).
13. **Geri katılışta yukarıdan yaklaşma [5.1]:** Ayrılan dron slotuna (sabit kalır) formasyonun `katilim_yaklasma_yuksekligi_m` (4 m) üstünden yaklaşır: yerinde yüksel → slotun üstüne git → alçal. Aynı katılım adımının içinde yapılır, adım sayısı değişmez. Neden: Karışık dizilim provasında (14:01) İHA-2'nin slotu formasyonun uzak tarafına düştü, düz çizgiyle gelirken komşulara 1,94 m yaklaştı. Ayar, kaçınma mesafesinden büyük olmak zorunda (ayar doğrulamasıyla zorlanır).
