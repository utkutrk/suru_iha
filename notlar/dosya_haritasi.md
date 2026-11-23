# Ne nereye kodlanır (kabataslak, öneri)

Bağlayıcı değil; iç düzeni kodlama ajanı değiştirebilir. Ortak ilke: **her dosya tek iş yapar**, en üstüne bir satır "bu dosya ne yapar" yorumu yazılır. Sayılar koda yazılmaz, `ayarlar/`'dan okunur.

## yazilim/ (asıl kod; başta az dosya, büyüdükçe bölünür)
| Parça | İçine ne kodlanır | İçinde OLMAYANLAR |
|---|---|---|
| ana program | Her dronda çalışan giriş dosyası; aşağıdaki parçaları birbirine bağlar | iş mantığı |
| dron | **Tek dronla konuşan tek yer.** MAVSDK'ya yalnız buradan dokunulur: bağlan, arm, kalkış, setpoint gönder, konum/GPS sağlığı oku, iniş | sürü, formasyon, ağ |
| ag | Dronlar arası mesajlaşma: gönder/al, mesaj biçimi (sürüm, gönderen, sıra no, zaman, anahtar), bozuk/bayat mesajı atma | sürü mantığı |
| guvenlik | **Dronlara giden her hedefin geçtiği son kapı:** 10 m tabanı, hız/alan sınırı, çarpışma önleme, kayıp komşu, RC kopma | MAVSDK çağrıları dışında dron detayı |
| suru | Sürünün beyni: `formasyonlar` (tek dosya: ok_basi, v, cizgi), `komutlar` (tek dosya: formasyon_kur, ayril, irtifa...), sanal yapı ve slot hedefi hesabı, adım adım senkron | MAVSDK, kamera, QR |
| gorus | Kamera arayüzü (sim ve gerçek aynı arayüz), renkli alan bulma; QR okuma sonra | uçuş kararı |
| gorevler | Görev 1: komut kaynağı arayüzü + senaryo okuyucu (QR sonra aynı yere takılır). Görev 2: kumanda girdisi → sürü komutu | düşük seviye uçuş |
| ortak | Ayar okuma ve doğrulama, log kurulumu, konum CSV kaydı | başka hiçbir şey |
| analiz | Kayıtlardan prova raporu (en küçük mesafe, irtifa, slot hatası, iniş doğruluğu) | uçuş kararı, MAVSDK |

Katman kuralı: alttakiler üsttekileri çağırmaz. Sıra: dron, ag → guvenlik, suru, gorus → gorevler.

## Diğer klasörler
- **ayarlar/**: yalnız JSON. `sartname.json` (hazır), `ucus.json` (hız sınırı, zaman aşımı, formasyon aralığı, eşikler), `saha.json` (sahada ölçülenler). Her değerin yanında birim, açıklama ve etiket: `[Ş]` şartname, `[K]` doğrulandı, `[Y]` tahmin.
- **yki/**: şimdilik boş, QGroundControl kullanılıyor. İleride kendi YKİ'miz.
- **simulasyon/**: **yalnız Gazebo ortamı**: dünya dosyası (zemin, renkli alanlar, ileride QR panoları) ve modeller. Uçuş veya sürü kodu yok.
- **senaryolar/**: yalnız JSON: Görev 1 komut dizileri, Görev 2 direktifleri, arıza senaryoları. Kod yok. Test ve simülasyon aynı dosyaları okur.
- **test/**: `birim` = PX4 gerektirmeyen saf hesap testleri; `simulasyon` = Gazebo'da tam prova. Sahte PX4 veya sahte dron yok.
- **betikler/**: tek komutla çalışan yardımcılar (SITL'leri başlat, dron programlarını başlat, testleri çalıştır). Mantık içermez, yalnız çağırır.
- **kayitlar/**: uçuş logları, kod sürümü ve ayar özeti. Git'e girmez.
- **notlar/**: açık sorular, kararlar, bu harita, `rapor_ozgunlukler.md` (TEKNOFEST raporu için özgün çözümler ve ölçümler; yeni çözüm eklenince güncellenir).
