# Rakip Takımlar — Donanım İnceleme Notları

Bu dosya, incelenen saha ve atölye görsellerinden tespit edilen donanım bileşenlerini takım / araç bazlı olarak özetler. Yalnızca görsellerde doğrudan seçilebilen veya sınıfı net olarak görülen parçalar listelenmiştir; kadrajda olmayan / gövde içinde kalan parçalar açıkça belirtilmiştir.

---

## 1. Gamma İTÜ

**Genel Tasarım Yaklaşımı:** Kompakt (7–8 inç sınıfı), hafif, yüksek uçuş süreli (Li-Ion), harici yüksek güçlü çift antenli Wi-Fi adaptörlü ve dikey Raspberry Pi yerleşimli özgün sürü platformu.

| Bileşen | Görselde Tespit Edilen Parça / Model | Tespit Detayı & Notlar |
| :--- | :--- | :--- |
| **Gövde (Frame)** | 7–8" düz karbon fiber kollu X-Frame (özel CNC kesim üst/alt plaka) | Bir dronda açık gri/beyaz (G10/fiberglas), diğer ikisinde siyah karbon üst plaka. |
| **Motor** | 7" sınıfı FPV fırçasız motorlar (tahminen 2806.5 / 2807 ~1300KV, M5 şaftlı) | Siyah gövde, fiberli M5 somun. |
| **Pervane** | 7" 3 palli (*tri-blade*) siyah FPV pervaneler (tahminen 7040 sınıfı) | 3 dronda da aynı siyah 3 palli pervaneler. |
| **Uçuş Kontrolcüsü (FC) & ESC** | Gövde plakaları arasında kompakt 30.5×30.5 mm stack *(tam model görülmüyor)* | İki plaka arası dar olduğundan büyük kasa Pixhawk değil, kompakt FC + 4-in-1 ESC sınıfı. |
| **Pil** | Özel paketli silindirik **Li-Ion batarya** (mavi PVC makaron, sarı **XT60**) | Mavi makaron altında yatay dizilmiş 18650/21700 silindirik hücreler net seçiliyor (4S2P/6S2P sınıfı). |
| **Voltaj Regülatörü (BEC)** | Harici mavi klemensli **DC-DC Step-Down (Buck)** kartı (XL4015/LM2596 sınıfı) | Pilin önünde üst plakaya sabitlenmiş; 2 mavi vidalı klemens ve 2 gümüş SMD kondansatör görülüyor. |
| **Görev Bilgisayarı** | **Raspberry Pi** (4B / 3B+ / 5 sınıfı — 2 blok USB-A + Ethernet + 40-pin GPIO) | Pilin arkasına **dikey** monte edilerek küçük gövdede yer kazanılmış. |
| **İHA'lar Arası Haberleşme** | **ALFA Network** çift antenli USB Wi-Fi adaptörü (`AWUS036ACH` / `AWUS036ACM` sınıfı) + **3. uzun yan RP-SMA anten** | Siyah adaptörde **`ALFA`** yazısı okunuyor; 2 dikey anten arasına sabitleme + ID (`1`) için gri koli bandı çekilmiş. Üstten kolajda yana uzanan 3. bir uzun siyah RP-SMA anten (harici telemetri / ek RF hattı) daha görülüyor. |
| **Kamera** | **Raspberry Pi CSI Kamera Modülü** (yere bakan) | Pi'den çıkan turuncu/siyah FPC şerit kablo, alt plaka kenarındaki küçük yeşil kamera kartına gidiyor. |
| **GPS + Pusula** | Uzun karbon direk üstünde GNSS + Pusula (u-blox M8N/M9N/M10 tipi; üstten görünümde açık kare seramik patch antenli örnek) | Altında sarı/turuncu 3B baskı taban ve RF parazitine karşı **alüminyum folyo EMI kalkanı** sarılı. |
| **Diğer / Güvenlik** | Turuncu 3B baskı motor altı iniş ayakları, sağ yanda kırmızı koruma çerçeveli siyah basmalı/döner **güç/güvenlik anahtarı** | Üstten görünümde kırmızı koruma halkası içindeki siyah anahtar net doğrulanıyor. |
| **RC Kumanda / Alıcı / YKİ** | *Görsellerde seçilemiyor / kadrajda yok* | — |

---

## 2. ahiha.team

**Genel Tasarım Yaklaşımı:** Klasik, erişilebilir ve modüler **S500 + Pixhawk 2.4.8 + Raspberry Pi** tabanlı 10 inç sınıfı quadcopter sürüsü.

| Bileşen | Görselde Tespit Edilen Parça / Model | Tespit Detayı & Notlar |
| :--- | :--- | :--- |
| **Gövde (Frame)** | **S500 Quadcopter Gövdesi** (T-tipi karbon iniş takımı + kırmızı şeritli siyah sünger ayaklar) | Klasik S500 plastik/karbon destekli siyah kollar ve yüksek T-ayak iniş takımı 3 görselde de net görülüyor. |
| **Motor** | **2212 920KV** sınıfı fırçasız motorlar | S500 kitiyle uyumlu siyah/bakır sargılı klasik 2212 sınıfı motorlar. |
| **Pervane** | **1045 (10×4.5 inç) 2 palli** plastik pervaneler (yeşil + yön ayrımı için 1 kırmızı/turuncu) | Ön/arka yön ayrımı için bir kolda kırmızı pervane kullanılmış. |
| **Uçuş Kontrolcüsü (FC)** | **Pixhawk 2.4.8** (veya Pixhawk 1 serisi) | Merkezdeki parlak RGB LED ve siyah/beyaz klasik Pixhawk kasası + yan servo/telemetri pinleri net seçiliyor. |
| **GPS + Pusula** | **u-blox NEO-M8N** GPS + Pusula modülü (klasik Pixhawk kiti GPS'i) | Siyah yuvarlak kasa üzerindeki beyaz pusula/çip grafiği ve yanındaki kırmızı LED belirgin; düz siyah GPS direğine takılı. |
| **RC Alıcı** | **FlySky FS-iA10B** (10 Kanal, 2.4 GHz AFHDS 2A) | Yeşil etiket üzerinde **`FS-iA10B`** modeli doğrudan okunuyor; çift ince beyaz/gümüş anteni sola doğru uzanıyor (FlySky FS-i6 / FS-i6X kumanda ailesiyle kullanılır). |
| **Görev Bilgisayarı** | **Raspberry Pi** (resmî kırmızı-beyaz Raspberry Pi kasası içinde) | Monitörde doğrudan **Raspberry Pi OS ("Create User... to log in to your Raspberry Pi")** kurulum ekranı görülüyor; kırmızı-beyaz kutu gövdenin alt plakasına sabitlenmiş. |
| **Pil** | Gümüş/gri kaplamalı dikdörtgen **LiPo batarya** (3S veya 4S ~3300–5200 mAh sınıfı) | İniş takımlarının arasında gövde altına bağlı duruyor. |
| **Voltaj Regülatörü (BEC)** | Mavi PCB **DC-DC Step-Down (Buck)** kartı *(model net okunmuyor)* | Pixhawk'ın sağ yanında mavi PCB ve beyaz pin başlıkları görülüyor. |
| **İHA'lar Arası Haberleşme** | Harici büyük Wi-Fi anteni yok; **Raspberry Pi dahili Wi-Fi** (veya gövde içi küçük modül) | 3 dronun üzerinde harici büyük anten görünmüyor; Ubuntu YKİ bilgisayarından terminalle (SSH/ağ üzerinden) bağlanılıyor. |
| **YKİ Bilgisayarı** | **Ubuntu Linux** dizüstü bilgisayar | Sahada Ubuntu masaüstü ve çoklu terminal pencereleri açık (`.py` ve launch betikleri çalışıyor). |
| **ESC / Kamera / Optik Akış** | *Görsellerde net seçilemiyor* | — |

---

## 3. Drone 1 (İTÜ Ekibi — Çim Saha, TEKNOFEST Gaziantep)

**Genel Tasarım Yaklaşımı:** **S500 + Cube Orange + Raspberry Pi** tabanlı yüksek kararlılıklı otopilot kurulumu.

| Bileşen | Görselde Tespit Edilen Parça / Model | Tespit Detayı & Notlar |
| :--- | :--- | :--- |
| **Gövde (Frame)** | **S500** Quadcopter gövdesi (kırmızı şeritli sünger T-ayak iniş takımı) | Siyah karbon destekli S500 kollar. |
| **Uçuş Kontrolcüsü (FC)** | **CubePilot Cube Orange / Cube Orange+** | Gövde merkezindeki parlak turuncu küp ve taşıyıcı kartı net seçiliyor. |
| **Görev Bilgisayarı** | **Raspberry Pi** (4B / 5 sınıfı) | Cube Orange'ın hemen arkasında üst plakaya yatay monteli yeşil kart. |
| **GPS + Pusula** | Büyük yuvarlak siyah GNSS + Pusula (**Here 3 / Here 4** veya u-blox M9N/M10 sınıfı) | Uzun direk tepesinde yüksek montaj. |
| **Haberleşme** | Tek adet uzun siyah dikey **omni anten** | Sol kolda dikey sabitlenmiş (433/915 MHz telemetri veya Wi-Fi/RF). |
| **Güç / Güvenlik** | Alt gövdede batarya + sarı **XT60** + kırmızı silindirik **güç/güvenlik anahtarı** | — |
| **Motor / Pervane** | 2212 / 2216 sınıfı fırçasız motorlar *(pervaneler sökülü)* | — |
| **YKİ** | Dizüstü bilgisayar | Takım üyesinin dizinde sahada aktif. |

---

## 4. Drone 2 (Çim Saha — Siyah Pervaneli Quadcopter)

| Bileşen | Görselde Tespit Edilen Parça / Model | Tespit Detayı & Notlar |
| :--- | :--- | :--- |
| **Gövde (Frame)** | **F450 / S500** sınıfı siyah kollar + yüksek siyah iniş ayakları | Kablolar kırmızı bantla sabitlenmiş. |
| **Motor & Pervane** | 2212 / 2216 sınıfı siyah fırçasız motorlar + **1045 (2 palli) siyah pervaneler** | — |
| **Uçuş Kontrolcüsü (FC)** | Siyah kutulu FC (**Pixhawk 2.4.8** sınıfı) | Üst merkezde konumlu. |
| **GPS + Pusula** | Yuvarlak siyah **u-blox M8N/M9N/M10** GPS + Pusula | Merkezde siyah direk tepesinde. |
| **Pil** | Büyük gri/siyah **LiPo batarya** + sarı **XT60** | İniş ayaklarının arasına dikey/asılı konumlandırılmış. |
| **Güvenlik** | **Kırmızı acil güç kesme / güvenlik anahtarı** | Sağ alt/yan tarafta dışarı uzatılmış. |
| **Görev Bilgisayarı / Kamera** | *Bu açıdan net seçilemiyor* | — |

---

## 5. Drone 3 (TEKNOFEST Gaziantep Masası — Yakın Çekim S500)

| Bileşen | Görselde Tespit Edilen Parça / Model | Tespit Detayı & Notlar |
| :--- | :--- | :--- |
| **Gövde (Frame)** | **S500** Quadcopter gövdesi (kırmızı şeritli sünger T-ayak iniş takımı) | Siyah S500 kollar. |
| **Uçuş Kontrolcüsü (FC)** | **Pixhawk 2.4.8** | Kasasında ters açıdan **`Pixhawk`** yazısı doğrudan okunuyor. |
| **GPS + Pusula** | Yuvarlak siyah **u-blox** GPS + Pusula | Siyah direk tepesinde. |
| **Voltaj Regülatörü (BEC)** | **7-segment dijital voltmetre ekranlı (`8.8.8`) + mavi klemensli + toroid bobinli DC-DC Step-Down (Buck) regülatör** | XL4015 / LM2596 ekranlı versiyon; ön kısımda pilin üzerine kelepçelenmiş. |
| **Pil** | Siyah-beyaz etiketli **LiPo batarya** + sarı **XT60** | Ön/alt kısımda. |
| **Güvenlik Anahtarı** | Siyah **rocker (açma/kapama) güç anahtarı** | Pixhawk'ın sağ yanında pembe/kırmızı sünger yuva içinde. |
| **Motorlar** | 2212 920KV sınıfı fırçasız motorlar *(pervaneler sökülü)* | — |

---

## 6. Drone 5 (Çadır — Mavi Kollu F450)

| Bileşen | Görselde Tespit Edilen Parça / Model | Tespit Detayı & Notlar |
| :--- | :--- | :--- |
| **Gövde (Frame)** | **F450** Quadcopter gövdesi (mavi/siyah desenli kollar + açık yeşil 3B baskı iniş ayakları) | — |
| **Motor & Pervane** | 2212 920KV fırçasız motorlar + **1045 (2 palli) siyah pervaneler** | — |
| **Görev Bilgisayarı** | **Raspberry Pi 4 Model B** *(veya 3B+/5)* | Gövdenin tam üstünde açıkta; 2 blok USB-A + Ethernet portu + GPIO pinleri çok net. |
| **Uçuş Kontrolcüsü (FC)** | **Pixhawk 2.4.8** | Raspberry Pi'nin hemen üst/yanında siyah kasa. |
| **GPS + Pusula** | Büyük yuvarlak siyah GPS + Pusula modülü | Sol üstte. |
| **Haberleşme** | Beyaz/gri kutulu ve çift küçük siyah antenli RF/telemetri veya Wi-Fi modülü | Sol altta. |
| **Güç / Güvenlik** | Sarı **XT60** konnektör + kırmızı başlıklı **güç/güvenlik anahtarı** | Sağ kolda. |

---

## 7. Drone 6 (Kırmızı Tişörtlü Ekip — Kırmızı-Beyaz F450)

| Bileşen | Görselde Tespit Edilen Parça / Model | Tespit Detayı & Notlar |
| :--- | :--- | :--- |
| **Gövde (Frame)** | **F450** Quadcopter gövdesi (klasik 2 kırmızı + 2 beyaz kol + yüksek siyah iniş ayakları) | — |
| **Uçuş Kontrolcüsü (FC)** | **Pixhawk 2.4.8** | Üst merkezde beyaz pin etiketleriyle net seçiliyor. |
| **GPS + Pusula** | Kısa direk üstünde siyah yuvarlak **u-blox M8N/M9N** GPS + Pusula | — |
| **Görev Bilgisayarı** | **Raspberry Pi** | Pixhawk'ın hemen alt katmanında yeşil PCB. |
| **Alt Modül / Antenler** | Ön iki beyaz kol arasında öne/aşağı bakan küçük siyah modül + aşağı uzanan çift siyah anten | Kamera/sensör veya RC/telemetri antenleri. |
| **Motorlar & YKİ** | 2212 920KV fırçasız motorlar *(pervaneler sökülü)*; USB ile bağlı dizüstü YKİ | — |

---

## 8. Drone 7 (Masada Kırmızı-Beyaz Kollu İki F450)

| Bileşen | Görselde Tespit Edilen Parça / Model | Tespit Detayı & Notlar |
| :--- | :--- | :--- |
| **Gövde (Frame)** | **F450** (2 kırmızı + 2 beyaz kol, beyaz kollarda 3B baskı motor altı koruma/ayak + yüksek siyah kavisli iniş ayakları) | Arkada aynı konfigürasyondan 2. dron duruyor. |
| **Motor & Pervane** | 2212 / 2216 sınıfı siyah motorlar (kırmızı/siyah somun) + **1045 (2 palli) siyah pervaneler** | — |
| **Uçuş Kontrolcüsü (FC)** | **Pixhawk 2.4.8** | Üst katta önden PWM/servo pin sırası net görülüyor. |
| **Görev Bilgisayarı** | **Raspberry Pi 4 Model B** *(veya 3B+/5)* | Pixhawk'ın tam altındaki katta, önden Ethernet + 2× çift USB-A portları doğrudan görünüyor. |
| **GPS + Pusula** | Katlanabilir siyah direk tepesinde yuvarlak siyah GPS + Pusula | — |
| **ESC & Güç** | Kolların üstünde siyah tekil ESC'ler (30A/40A) + önde sarı **XT60** bağlantıları | — |
| **RC Kumanda** | Masada dronun altında siyah 2.4 GHz RC kumanda | — |

---

## 9. Drone 8 (Masada Montaj Aşamasındaki S500 — Etiketleri Okunanlar)

| Bileşen | Görselde Tespit Edilen Parça / Model | Tespit Detayı & Notlar |
| :--- | :--- | :--- |
| **Gövde (Frame)** | **S500** Quadcopter gövdesi (siyah S500 kollar + kırmızı şeritli sünger T-ayak iniş takımı) | — |
| **ESC** | **BLHeli 30A** (4 adet tekil ESC) | Sarı-kırmızı **`BLHeli 30A`** etiketi doğrudan okunuyor. |
| **Güç Modülü** | **Holybro PM07 Güç Modülü** | Sağ alt köşedeki **`KOMPENT`** poşet etiketinde **`Holybro PM07 Güç Modülü`** yazısı doğrudan okunuyor. |
| **Pil** | **5200 mAh 4S LiPo batarya** (sarı XT60) | Üstte masada duran siyah pil üzerinde **`5200 mAh`** okunuyor. |
| **Görev Bilgisayarı** | **Raspberry Pi** | Üst sağda masada çıplak yeşil kart (40-pin GPIO + USB/Ethernet). |
| **Haberleşme / RF Kartı** | Sarı taşıyıcı PCB üzerinde metal kalkanlı ve **çift altın SMA konnektörlü** RF/telemetri modülü | Merkez üstte konumlu. |
| **GPS + Pusula** | Yuvarlak siyah GPS + Pusula modülü | Merkezde. |
| **Motorlar** | 2212 920KV sınıfı siyah fırçasız motorlar (3.5 mm bullet konnektörlü) | — |

---

## 10. Tüm Rakip Takımlardan Çıkan Genel Özet

| Kriter | Sahadaki Baskın Eğilim (Çoğunluk) | Öne Çıkan İstisna / İleri Tercih |
| :--- | :--- | :--- |
| **Gövde** | **S500** ve **F450** (10 inç, 2212 920KV motor, 1045 2-palli pervane) | **Gamma İTÜ:** 7–8" kompakt FPV X-Frame (3-palli pervane) |
| **Uçuş Kontrolcüsü** | **Pixhawk 2.4.8** (ekonomik, yaygın) | **İTÜ (Drone 1):** **CubePilot Cube Orange**; **Gamma İTÜ:** Kompakt 30.5×30.5 stack |
| **Görev Bilgisayarı** | Neredeyse tamamında **Raspberry Pi (4B / 5)** | — |
| **Pil** | **4S 3300–5200 mAh LiPo** | **Gamma İTÜ:** Özel paketli silindirik **Li-Ion** |
| **Haberleşme** | RPi dahili Wi-Fi veya harici tekil RF/telemetri anteni | **Gamma İTÜ:** Harici **ALFA çift antenli USB Wi-Fi** + 3. RF anteni |
| **Güvenlik Detayları** | Harici kırmızı güç/acil durdurma anahtarı + mavi klemensli 5V Step-Down BEC | **Gamma İTÜ:** GPS altı **alüminyum folyo EMI kalkanı** |
