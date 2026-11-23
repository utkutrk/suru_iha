# AGENTS.md

Proje: TEKNOFEST 2026 Sürü İHA Yarışması. Ana kaynak şartnamedir (`sartname/`). Çelişki olursa şartname kazanır; net olmayan bir yeri tahmin etme, `notlar/acik_sorular.md`'ye yaz.
Ekip konuları sıfırdan öğreniyor: Türkçe, sade, kısa dosyalar, neden yaptığını anlatan kısa yorumlar.

## Amaç
En az 3 dronluk, **dağıtık** (lider ve merkez yok) bir sürü.
- **Görev 1 — Dinamik Sürü (250 puan):** sürü QR kodlarından görev okur (formasyon, pitch/roll eğimi, irtifa, birey çıkarma/ekleme, sonraki QR), formasyon rotasyonuyla QR noktalarına gider, ayrılan dron renkli alana inip geri katılır. Yer istasyonu yalnız "başlat" der.
- **Görev 2 — Yarı Otonom (150 puan):** tek kumanda ile tüm sürü yönetilir (hareket modu, manevra modu, formasyon değişimi, kalkış/iniş).
Ayrıntı: `sartname/ozet.md`, puan ve cezalar: `sartname/puan_ve_ceza.md`, şartname sayıları: `ayarlar/sartname.json`.

## Takım kuralları (değişmez)
1. **Sayılar koda gömülmez.** Hız, irtifa, mesafe, süre, eşik, katsayı, port, koordinat, renk aralığı `ayarlar/` altındaki config dosyalarında durur. Her değerin yanında birim, açıklama ve kaynak etiketi olur: `[Ş]` şartname, `[K]` doğrulandı, `[Y]` tahmin.
2. **Yeni formasyon veya yeni komut tek yerde eklenir.** Tüm formasyonlar (ok başı, V, çizgi...) tek dosyada, tüm komutlar (formasyon kur, ayrıl, irtifa...) tek dosyada durur; her biri küçük bir fonksiyon veya tablo satırıdır. Yeni birini eklemek için başka dosya değiştirmek gerekmez. Ad → fonksiyon eşlemesi bir tabloyla yapılır, `if/elif` zinciri yazılmaz.
3. **Simülasyonda çalışmayan kod gerçek drona gitmez.**

## Şartnamenin zorunlu kıldıkları (bozma)
- **Dağıtık algoritma** [5.3]: her dronda aynı program; lider ve merkezi karar yok.
- **YKİ yalnız "başlat" der** [5.1]; sonrasında komut göndermez (iptal, iniş, kill, görev yükleme yok). Hakem bağlantıyı keser; sürü görevi sürdürür. Çözülen QR içeriği YKİ'de gösterilir.
- **Alt irtifa 10 m** [5.1] (eğimli formasyonda en alçak dron dahil). **Çarpışma ve düşme yok.**
- Algoritma **N dron** için çalışır, en az 3 [5, 5.3].
- Birey ayrılınca kalan sürü formasyonu düzeltmez [5.1]; ayrılan dron renkli alana (merkezden 2.5 m içine) iner, tekrar kalkar, en geç sonraki QR'da sürüye katılır.
- Formasyon rotasyonu yeni formasyon değil: merkez sabit, göreli konumlar korunur, her dronun yönü de döner [5.1]. Pitch/roll manevrasında merkez sabit, eğim sonraki komuta kadar korunur.
- RC kopunca **5 sn sonra Land** failsafe'i [5.4]. **GPS güvenilmez olabilir** [5.4]. Kamera FOV ≤ 90° [5.1].
- QR yalnız kendi takım ID'mize ait görevi uygular; yanlış görev = o QR başarısız [5.1].

## Teknoloji
Python 3.10+, asyncio, PX4 (SITL + Gazebo), MAVSDK-Python, NumPy, OpenCV. ROS yok. Dronlar arası haberleşme UDP + JSON. Paket sürümleri sabitlenir (MAVSDK'nın ana sürümleri arasında API değişebilir; hafızadan yazma, kurulu sürümü doğrula).

PX4 tuzakları (hatalar dronu yere indirir):
- NED: x Kuzey, y Doğu, **z AŞAĞI** (12 m irtifa = z −12). Yaw derece, Kuzey'den saat yönünde.
- Offboard'a geçmeden **önce** bir setpoint gönder; sonra akış kesintisiz sürsün (kesilirse PX4 offboard'dan çıkar).
- Havada disarm yok. GPS/home hazır olmadan arm yok. Her dron için ayrı MAVLink ve MAVSDK sunucu portu.
- Her dronun yerel orijini kendi kalkış noktasıdır; sürü ortak bir koordinat çerçevesinde çalışmalı.

## Şimdilik kapsam dışı
- **QR okuma ve QR içeriğini YKİ'de gösterme** şimdilik yapılmaz. Görev komutları (formasyon, irtifa, ayrıl, sonraki nokta...) şimdilik `senaryolar/` altındaki senaryo dosyasından gelir, sanki QR'dan okunmuş gibi. Komut kaynağı tek bir arayüzün arkasında olmalı ki sonradan QR okuyucu aynı yere takılabilsin; QR gelince YKİ'de gösterme de eklenir (şartname bunu zorunlu kılar, ceza −20).
- Kendi YKİ'mizi yazmak: sonra.

## Serbestlik
Klasörlerin iç yapısı, dosya adları, algoritma ve mimari seçimleri sana ait; yukarıdaki kurallar ve şartname sınırları içinde özgün çözüm üretmen beklenir. Aşağıdakiler **öneridir, bağlayıcı değil**; daha iyisini bulursan kullan, gerekçeni kısa bir notla yaz.

## Tasarım fikirleri (öneri)
- **Sanal yapı:** sürüyü görünmez katı cisim gibi düşün (merkez, yaw, pitch/roll, formasyon, aralık); her dron kendi slotuna gider: `hedef = merkez + R(yaw, pitch, roll) · ofset`. Slot = dron numarası; ayrılan dronun slotu boş kalır. Her ajan aynı yapıyı kendi içinde hesaplar. (Bunun hakemce "dağıtık" sayılıp sayılmayacağı açık soru.)
- **Senkron:** adım adım ilerle; aktif herkes adımı bitirmeden sonrakine geçme; **susan komşuyu kayıp say ve bekleme**. Her beklemenin zaman aşımı olsun; bir dronun düşmesi sürüyü kilitlememeli.
- **Haberleşme:** taşıyıcıyı soyutla (simülasyonda UDP, sahada telsiz); mesajlar alan adlı JSON, sürüm, gönderen, sıra no, zaman damgası ve takım anahtarı taşısın; yanlış anahtarlı, bozuk veya bayat mesaj yok sayılsın.
- **Güvenlik:** dronlara giden her hedef tek bir "son kapı"dan geçsin (10 m tabanı, hız/ivme sınırı, alan sınırı). Çarpışma önleme için mesafe izleme + yatay itme + farklı irtifa katmanları.
- **GPS:** (1) PX4'ün kendi GPS sağlık bilgisi, (2) formasyonda beklerken komşuların GPS'inden hesaplanan mesafeyi beklenen formasyon mesafesiyle karşılaştıran tutarlılık kontrolü (ilk sürümde uyarı + log; geçiş sırasında kontrol etme), (3) gerekirse GPS'ten bağımsız ölçüm (optik akış, dronlar arası mesafe sensörü). Sınır: GPS'i GPS ile doğrulamak bağımsız değildir; ortak kaymayı yakalayamaz. QR konumları sahada yeniden kaydedilebilir [5.1].
- **Görüntü:** simülasyon ve gerçek kamera aynı arayüzle; **Gazebo kamerasından Python'a görüntü alma ilk denenecek risktir.** QR için modül başına piksel hesabı (irtifa, FOV, çözünürlük); tespitte ardışık N kare şartı; kırmızı HSV'de iki aralık.
- **YKİ:** şimdilik QGroundControl kullanılır (dron konumu ve durumu için); `yki/` klasörü ileride kendi YKİ'mizi yazmak için ayrıdır. QR içeriğini gösteren arayüz **şimdilik yok** (aşağıdaki kapsam notuna bak). "Başlat" şartnamedeki sınıra uymalı; QGC'nin standart komutları yetmezse küçük bir başlat betiği yazılır.

## Çalışma biçimi
- Küçük adımlar, ama **sahte/taklit PX4 veya sahte dron yazma**: dron davranışı doğrudan PX4 SITL + Gazebo'da denenir (önce tek dron, sonra çok dron). Yalnız PX4 gerektirmeyen saf hesaplar (formasyon matematiği, mesaj ayrıştırma, config doğrulama) küçük birim testle denenir.
- **Gerçek drona geçmeden önce** (kapı): Gazebo'da Görev 1 ve Görev 2 ardışık en az 3 temiz prova (çarpışma, düşme, 10 m ihlali yok); arıza provaları (YKİ kesildi, bir dron öldürüldü, kumanda koptu, QR okunamadı, GPS bozuk); RC kopma failsafe'i doğrulandı; kodda gömülü sayı kalmadı; yarışmada her dron için ayrı pilot ve RC var, güvenlik pilotu ile YKİ operatörü aynı kişi değil [2, 5.1]. Geçiş aşamalıdır: yerde → tek dron elle → tek dron otonom → çok dron.
- `logging` kullan, hatayı yutma, dışarıdan gelen veriyi (ağ, QR, config) doğrula. Her uçuşta kod sürümünü ve ayar özetini kaydet; dronda otomatik güncelleme yok.
- Gizli değer (takım anahtarı) repoya düz yazılmaz.
- Başkasının kod veya raporunu kopyalama; şartname bunu diskalifiye sebebi sayar [10.3]. Fikir aldıysan kaynağını kısa not et.
- Önemli kararları kısa notla `notlar/` altına yaz (ne, neden, hangi şartname maddesi).
