# Şartname Özeti (V1.2, 15.06.2026) — sade Türkçe

Köşeli parantez = şartname madde numarası. Anlam kaybı olursa PDF geçerlidir.

## 1. Genel kurallar
- Takım 3–10 kişi, en fazla 1 danışman [2]
- Güvenlik pilotu ile YKİ operatörü aynı kişi olamaz [2]
- Her İHA için ayrı pilot ve ayrı RC kumanda şart; hakem kill switch kullanabilir [5.1, 5.4, 5.5.1]
- İHA multicopter olmalı (sabit kanat ve VTOL yok), en fazla 10 kg, hazır alınabilir, farklı modeller olabilir [6, 6.1]
- Her dronun üzerinde ID (1., 2., 3.) yazmalı [6]
- LiPo pil çantası zorunlu [6.2]
- Pilotlar iha.shgm.gov.tr'den kayıt olmalı, İHA'lar da kayıtlı olmalı; onaysız uçuş yok [5.5.1]
- Yasaklı kod yok, açık kaynak serbest [5.3]
- Kumanda kopunca 5 sn sonra Land failsafe'i çalışmalı; çalışmayana uçuş izni yok [5.4]
- GPS güvenilmez olabilir, alternatif yöntem düşünülmeli [5.4]
- Sahada danışmanın bulunması veya dışarıdan sözlü/yazılı müdahale = görev başarısız [5.1, 5.2]

## 2. Algoritma kuralları [5.3]
- İstenen sayıda İHA'yı yönetebilmeli (jenerik)
- Formasyon kurma/değiştirme her an yapılabilmeli
- İHA'lar çarpışmamalı
- **Dağıtık algoritma şart; merkezi algoritma eksik puan**
- Yazılım ve arayüz kolay kullanılabilir olmalı

## 3. Görev 1 — Dinamik Sürü [5.1]
Akış:
1. Hakemler dronları yerde karışık dizer; araları X m (örn. 5 m).
2. Tek kalkış komutu: hepsi eş zamanlı, otonom kalkar, formasyonu koruyarak irtifaya (örn. 15 m) çıkar.
3. Sürü formasyon rotasyonu yapıp QR1'e gider.
4. En az bir İHA QR'ı kamerayla bulup çözer.
5. QR içeriğini sırayla uygular: formasyon → pitch/roll eğimi → irtifa → birey çıkarma/ekleme → sonraki QR; her görev arasında "wait" süresi bekler.
6. Sonraki QR = 0 ise o görevi yapar, home'a döner, formasyonu bozmadan iner; hepsi disarm olunca görev biter.

QR ve komutlar:
- QR içeriği takım ID'sine göre farklıdır; takım yalnız kendi ID'sinin görevini uygular. Yanlış görev = o QR başarısız.
- QR boyutu 150 x 150 cm; konumları (enlem, boylam) önceden verilir, sahada doğrulanabilir.
- Kamera: en az bir İHA'da şart, hepsinde olabilir; FOV en fazla 90°.
- Pitch/roll: sürü merkezi sabit kalıp topluca eğilir (örn. -15° pitch, okbaşında arkadaki ikisi yükselir, öndeki alçalır). Açı, yeni formasyon veya yeni manevra gelene kadar korunur.
- Formasyon rotasyonu: yol boyunca formasyon Z ekseninde hedefe döner, göreli konumlar bozulmaz, her İHA'nın heading'i de hedefe döner. Bu yeni formasyona geçiş değildir.

Birey çıkarma/ekleme:
- QR, ayrılacak dronun ID'sini ve renkli alan rengini (kırmızı/mavi) söyler.
- Renkli alanlar rotaya rastgele konur (100 cm yarıçaplı daire). Konumları önceden verilmez; ayrıca tarama yapılamaz. Sürü yol boyunca kamerayla bulup kaydeder.
- Ayrılan dron alanın merkezinden 2.5 m içine inmeli, disarm olur, bekler, tekrar arm olup kalkar ve en geç bir sonraki QR noktasında sürüye katılır. Yanlış renk veya alan dışı = bu kalemden puan yok.
- Kalan sürü formasyonu düzeltmez.
- 3'ten fazla dron varsa biri yerde yedek bekler; ayrılan dron inip disarm olunca yedek sürüye katılır.
- Görüntü işlemeyle iniş zorunlu değil.

Özel durumlar:
- QR çözülemezse: sürü alçalma, yükselme, ileri/geri manevralarla tekrar deneyebilir; 10 m altına inmek yasak.
- Hâlâ çözülemezse: sürü eve döner ve görevi baştan başlar; o ana kadarki kısımdan puan alınır.
- Bağlantı varken çözülen QR içeriği YKİ'de gösterilmeli (görüntü veya metin). Hiç gösterilmezse ceza.
- YKİ'den yalnız "başlat" gönderilir; başka müdahale = görev başarısız. Hakem istediği an YKİ bağlantısını keser.
- Uçuş sırasında 2 İHA'ya düşülürse, 3 İHA ile tamamlanan kısma kadar tam puan, sonrası eksik.

## 4. Görev 2 — Yarı Otonom Sürü Kontrolü [5.2]
- Tek joystick veya RC ile tüm sürü yönetilir; kalkış ve iniş de kumandadan, sürü halinde.
- **Sürü Hareket Modu:** formasyon korunarak ileri/geri (pitch), sağ/sol (roll), yaw (merkez sabit, topluca dönüş, her İHA heading'ini ayarlar), irtifa (throttle).
- **Manevra Modu:** merkez sabit, topluca pitch/roll eğimi ve yaw dönüşü.
- Formasyon değişimleri (ok başı, V, çizgi) kumandadan yapılır.
- Hakem direktifleri: kalkış, irtifa yükselt, formasyona geç, ileri pitch, sağ roll, ileri+sağ çapraz, yaw, manevra modu, throttle, sonra eve dönüş ve iniş.
- Uçuş süresi görev başında bildirilir.
- YKİ'den görev öncesi ayar yapılabilir; başladıktan sonra müdahale = görev başarısız.
- En az 3 İHA; 2'ye düşerse 3 İHA ile yapılan kısma kadar tam puan.

## 5. Puanlama ve teslimler [8, 12]
- Rapor ve video %20 (KTR %10, Uçuş Kanıt + Yazılım Mimarisi Videosu %10); görev puanı %80 [8.3]
- Her görev için en fazla 3 hak; en yüksek puan geçerli [8.4]
- Görev, Tablo 7'deki minimum aktif İHA sayısının altına düşerse o görevden puan alınmaz [8.4]
- Ödül için en az 200 görev puanı ve iki görevden de puan şart [12.1]
- Uçuş kanıt videosu: ~5 dk, en az 3 dk otonom, RC müdahalesi olmadığı görünmeli, air HUD zorunlu, en az 720p [8.2]
- Yazılım videosu: en fazla 10 dk, algoritma (çarpışma önleme, formasyon) ve mimari; kod HAVELSAN platformuna yüklenir [8.2]
- Final günü yazılım değişikliği beyan edilmeli [8.2]
