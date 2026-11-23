# Rapor İçin Özgün Çözümler ve Geliştirmeler

**Bu dosya ne işe yarar?** TEKNOFEST raporu (KTR) ve yazılım mimarisi videosu yazılırken jürinin dikkatini çekebilecek mühendislik kararlarını, çözümleri ve ölçülmüş sonuçları tek yerde toplar. Her başlık aynı kalıbı izler: **Problem → Çözüm (sade anlatım) → Teknik ayrıntı → Kanıt/ölçüm → Şartname bağı → Sınır**. "Sade anlatım" kısımları rapora neredeyse olduğu gibi konabilir.

**Yeni bir çözüm ekleyince** bu dosyaya da bir başlık ekleyin (tarih ve ölçüm sonucuyla). Ölçülmemiş şeyi "ölçüldü" diye yazmayın; ölçüm bekleyenler **[ölçüm bekliyor]** diye işaretli.

**Kanıt etiketleri:** `[Gazebo]` PX4 SITL + Gazebo uçuş provasında ölçüldü · `[Birim test]` PX4 gerektirmeyen saf hesap testiyle doğrulandı · `[Hesap]` hesapla gösterildi, uçuşta henüz ölçülmedi.

Tarih: 2026-11-23 (bu tarihe kadar yapılanlar).

---

## 1. Bir bakışta: özgün katkılar

| # | Katkı | Tek cümlede | Şartname bağı | Kanıt |
|---|---|---|---|---|
| 1 | Lidersiz "sanal yapı" mimarisi | Her dron aynı programı çalıştırır, formasyonu kendi içinde hesaplar; lider ve merkez yok | 5.3 (dağıtık) | [Gazebo] |
| 2 | Susan komşuya dayanıklı adım senkronu | Bir dron düşse/susarsa sürü kilitlenmez | 5.3, 5.1 (2 İHA'ya düşme) | [Birim test] [Gazebo] |
| 3 | GPS tabanlı ortak koordinat çerçevesi | Her dronun kendi "sıfır noktası" farklı olsa da sürü tek haritada uçar | 5.1 | [Gazebo] |
| 4 | Tek "son güvenlik kapısı" | Dronlara giden her hedef tek yerden geçer: 10 m tabanı, hız, alan, çarpışma | 5.1 (irtifa, çarpışma) | [Birim test] [Gazebo] |
| 5 | Yay üzerinde formasyon rotasyonu | Formasyon küçük açı adımlarıyla döner, dronların yolları kesişmez | 5.1 (rotasyon) | [Birim test] [Hesap] |
| 6 | "Mantıksal adım" ile ayrılan dronu sürüyle senkron tutma | İnen dron havada olmasa da görev akışını sürüyle izler; sayaç kaymaz | 5.1 (birey çıkarma) | [Gazebo] |
| 7 | Katılım adımı (ayrılan dronu QR'da bekleme) | Sürü, ayrılan dron slotuna dönene kadar QR'ı okumaz; komutlar 3 dronla uygulanır | 5.1, Tablo 7 | [Gazebo] |
| 8 | Karışık dizilimde konuma göre slot ataması | Dronlar yerdeki konumlarına en uygun slota gider; yollar kesişmez | 5.1 ("karışık dizer") | [Birim test] [Gazebo] |
| 9 | İmzalı ve doğrulamalı dronlar arası mesajlaşma | HMAC imzası, sıra no, bayatlık süzgeci | 5.3, güvenlik | [Birim test] |
| 10 | Tablo tabanlı, ayar dosyalı genişletilebilirlik | Yeni formasyon/komut tek satır; sayılar kodda değil ayarda | Takım kuralları | [Birim test] |
| 11 | Otomatik prova raporu (konum CSV + analiz) | Çarpışma, 10 m, formasyon bütünlüğü ve iniş doğruluğu sayıyla ölçülür | 5.1 (cezalar) | [Gazebo] |
| 12 | QR için hazır komut kaynağı soyutlaması | Komutlar bugün senaryo dosyasından gelir, QR okuyucu aynı arayüze takılır | 5.1 (QR) | [Birim test] |

---

## 2. Ayrıntılı anlatım

### 2.1 Lidersiz "sanal yapı" mimarisi

**Problem.** Şartname merkezi algoritmayı eksik puanla cezalandırıyor [5.3]. Dronların birbirini takip etmesi (lider-takipçi) tek noktada arıza demek.

**Çözüm (sade).** Sürüyü, kendi başına dönebilen, eğilebilen "görünmez bir çerçeve" gibi düşünüyoruz. Çerçevenin bir merkezi, yönü ve eğimi var; her dronun çerçevenin içinde bir **slotu** (durak noktası) var. Her dron aynı programı çalıştırıyor ve çerçeveyi kendi içinde hesaplıyor; kimse kimseye "şuraya git" demiyor. Dronlar yalnızca "ben şu adımı bitirdim" bilgisini birbirine söylüyor.

**Teknik.** `hedef = merkez + R(yaw, pitch, roll) · ofset` (dönüş matrisi Z-Y-X sırasıyla, NED eksen takımında). Pitch/roll eğiminde merkez sabit kalır, ofsetler döner; böylece "−15° pitch'te öndeki alçalır, arkadaki ikisi yükselir" örneği formülden kendiliğinden çıkar (birim testi var). Aynı kod N dron için çalışır (formasyon fonksiyonları N'e göre jenerik, 3–5 dron testli).

**Kaynak notu.** "Sanal yapı" (virtual structure) fikri çok robotlu sistemlerde bilinen bir kavramdır (ör. Lewis & Tan, 1997). Bizim katkımız: bunu dağıtık senkron adım bariyeriyle, ayrılma/katılma akışıyla ve şartnamenin her kuralına bağlı şekilde bütünleştirmemiz.

**Sınır / açık soru.** Ortak sanal yapı + senkron adım yaklaşımının hakemce "dağıtık" sayılıp sayılmayacağı Soru-Cevap toplantısında sorulacak (`acik_sorular.md` madde 4).

---

### 2.2 Susan komşuya dayanıklı adım senkronu

**Problem.** Dronlar adım adım ilerlerken bir dron düşerse ya da telsizden kaybolursa, diğerleri onu sonsuza kadar bekleyip kilitlenebilir. Şartname "2 İHA'ya düşse bile tamamlanan kısma kadar puan" diyor.

**Çözüm (sade).** Her dron 10 Hz'de "şu adımdayım, bitirdim mi" bilgisini yayınlar. Bir komşudan 2,5 sn haber gelmezse o dron "kayıp" sayılır ve beklenmez. Her beklemenin ayrıca bir zaman aşımı vardır.

**Teknik.** `DagitimSenkron`: komşu tablosu, canlılık süresi, `aktif_komsular_adimi_bitirdi_mi()` (komşu ya o adımı bitirmiş ya da sonraki adıma geçmiş olmalı). Birim testlerle susan komşunun kilitlemediği doğrulandı.

**Kanıt.** `[Birim test]` susan komşu, geride kalan komşu, ayrılmış komşu senaryoları.

---

### 2.3 GPS tabanlı ortak koordinat çerçevesi

**Problem.** PX4'te her dron kendi kalkış noktasını (0, 0) kabul eder. Üç dron aynı anda "ben (0, 0)'dayım" der; ortak formasyon kurulamaz.

**Çözüm (sade).** Her dron açılışta kendi GPS'ini bilinen ortak bir referans noktasına göre metreye çevirir ve "benim yerel sıfırım ortak haritada nerede" farkını (ofset) bir kez hesaplar. Bundan sonra her dron kendi yerel konumuna bu farkı ekleyerek ortak haritada konuşur.

**Teknik.** `gps_to_ned()` ile enlem/boylam → Kuzey/Doğu metre; yatay ofset GPS'ten, düşey ofset zemin referansından (barometre kaymasından kaçınmak için). PX4 setpoint'i gönderirken ofset geri çıkarılır.

**Kanıt.** `[Gazebo]` Hesaplanan ofsetler spawn noktalarıyla 1–2 cm uyuştu (ör. İHA-1: 2,49 m / 2,5 m). Dronlar önceki uçuşun iniş noktalarından (kasıtsız bir "karışık dizilim") kalkınca da ofsetler değişmedi ve sürü doğru çalıştı: çerçeve, başlangıç yerinden bağımsız.

**Sınır (dürüst yazılacak).** Ofset bir kez hesaplanıyor; havada GPS kayarsa güncellenmiyor ve tüm dronlar aynı yöne kayarsa fark edilmez. GPS'ten bağımsız ölçüm (optik akış, dronlar arası mesafe) sahada karar verilecek (`acik_sorular.md` madde 3).

---

### 2.4 Tek "son güvenlik kapısı"

**Problem.** Çarpışma (−20), irtifa ihlali (−20) ve düşme (−20) tek bir hatayla puanı sıfırlayabilir. Güvenlik kontrolü kodun her yerine dağılırsa bir yerde unutulur.

**Çözüm (sade).** Dronlara giden **her** hedef konum, tek bir fonksiyondan geçer. O fonksiyon hedefi güvenli hâle getirir. Hiçbir görev kodu doğrudan PX4'e hedef gönderemez.

**Teknik.** `GuvenlikKapisi.hedefi_suz()`; sırayla: (1) geçişte slot bazlı irtifa katmanı, (2) yatay/düşey hız rampası (osilasyonu azaltır), (3) yakın komşudan uzaklaştıran yatay itme (2,5 m'de başlar, 1,5 m'de iki katı), (4) alan sınırı (geofence), (5) irtifa tabanı (10 m) ve tavanı, (6) yaw hız sınırı. Eğimli formasyonda en alçak dron da 10 m tabanını aşmasın diye merkez otomatik yukarı çekilir. Tüm eşikler `ayarlar/ucus.json` içindedir.

**Kanıt.** `[Birim test]` 10 m tabanı, geofence, itme yönü. `[Gazebo]` Üç provada 10 m ihlali ve çarpışma yok; en düşük uçuş irtifası 14,4 m.

---

### 2.5 Yay üzerinde formasyon rotasyonu

**Problem.** Rotasyonda formasyon, merkez sabit kalarak yeni yöne dönmeli [5.1]. İlk uygulamada yeni slot hedefi tek hamlede verildi; dronlar eski noktadan yeni noktaya **düz çizgiyle** gitti. Büyük dönüşlerde (örn. 107°) komşu slotların yolları kesişti ve dronlar birbirine yaklaştı.

**Çözüm (sade).** Dönüşü 15°'lik küçük adımlara böldük. Her adımda slotlar biraz döner ve dronlar senkronlanır. Böylece her dron gerçek bir daire yayı üzerinde ilerler, yollar birbirini kesmez.

**Teknik.** `yaw_ara_adimlari()` (en kısa yönden böler, hedef açıyla biter); `rotasyon_adim_deg`, ara adım toleransları ayarlanabilir. Ara adımlarda gevşek tolerans kullanılarak dur-kalk hareketi (osilasyon cezası) önlendi.

**Kanıt.**
- `[Birim test]` 6 m aralıkla 53° → 160° dönüşünde komşu slotlar arası en küçük mesafe: **tek hamlede ≈ 3,6 m, 15° adımlarla > 5,5 m**.
- `[Gazebo]` Rotasyon adımlarında hiç "kritik yakınlık" uyarısı çıkmadı; 107° dönüş yaklaşık 4–5 sn sürdü.

---

### 2.6 "Mantıksal adım": ayrılan dronu sürüyle senkron tutma

**Problem.** Birey çıkarmada bir dron renkli alana inip tekrar kalkar (~45 sn). İlk uygulamada dönen dron, sürü ilerlediği hâlde komutları baştan kendi başına tekrar uçuyordu. Adım sayacı da kayıyordu (ayrılan dron bir adım geride kalıyordu); sürü onu **50 sn bekledi**, ayrıca İHA-2 diğerlerinden önce rotasyona başladığı için dronlar 1,21 m'ye kadar yaklaştı.

**Çözüm (sade).** Ayrılan dron havada olmasa da görev akışını sürüyle birlikte "kafasında" izler: komutları uygular, adım sayısını sürüyle aynı tutar, ama uçmaz. Uçuşunu (iniş, bekleme, kalkış) ayrı bir arka plan görevi yürütür. Hazır olunca doğrudan güncel duruma katılır; yeniden tekrar etmez.

**Teknik.** Adım numarası tüm dronlarda aynı olayları aynı sırayla sayar. Ayrık dron `_mantiksal_adim()` ile komşuların adımı bitirmesini bekler (uçuşsuz). Uçuş `_ayrilma_ucusu()` ayrı bir `asyncio` görevidir.

**Kanıt (üç prova karşılaştırması, `[Gazebo]`).**

| Ölçüt | Düzeltme öncesi | Düzeltme sonrası |
|---|---|---|
| Senkron zaman aşımı (boşuna bekleme) | 1 (≈ 50 sn) | **0** |
| Adım sayacı | İHA-2 bir geride | **Üçü de aynı** |
| Toplam süre | 367 sn | **267 sn** |
| Dronlar arası en küçük mesafe | 1,21 m | **2,90 m** |
| Yanlış GPS uyarıları | 9 | **0** |

---

### 2.7 Katılım adımı: ayrılan dronu QR'da bekleme

**Problem.** Şartname, ayrılan dronun **en geç sonraki QR noktasında** sürüye katılmasını ister [5.1]. Ayrıca Tablo 7'ye göre formasyon, manevra ve rotasyon puanı için **en az 3 aktif İHA** gerekir. Sürü ayrılan dronu beklemeden QR komutlarını uygularsa, bu komutlar 2 dronla uygulanır ve puan getirmez.

**Çözüm (sade).** Sürü sonraki QR'a gider ve orada ayrılan dron slotuna oturana kadar bekler; ancak ondan sonra QR'ın içeriğini okur. Böylece o QR'ın formasyon ve manevra komutları hep 3 dronla yapılır.

**Teknik.** Herkes aynı numaralı "katılım adımını" yapar (kimin ayrıldığı bilgisi tüm dronlarda aynıdır, dron erken dönse bile sayaç kaymaz). Bariyer bu adımda ayrılmış komşuyu da bekler (`ayrilmislari_bekle`). Ayrılan dron düşer/susarsa komşu canlı listeden düşer ve sürü beklemeyi bırakır; ayrıca 120 sn üst sınır vardır (kilitlenme yok).

**Kanıt.** `[Gazebo]` Katılım adımı ≈ 30 sn sürdü; İHA-2 slotuna 0,6 m hassasiyetle oturdu; QR-2'nin komutları üç dronla uygulandı. Katılırken komşularla en az 5,6 m mesafe korundu. `[Birim test]` ayrılmış komşunun yalnız katılım adımında beklenmesi.

**Yukarıdan katılma (geri katılış yolu).** Ayrılan dron slotuna düz çizgiyle dönerse formasyonun içinden geçebilir (karışık dizilim provasında 1,94 m'ye yaklaştı). Bu yüzden slot aynı kalır, yalnız yaklaşma yolu değişir: dron önce bulunduğu yerde slotunun 4 m üstüne çıkar, o irtifada slotunun üstüne gider, sonra alçalıp yerine oturur. Dikey ayrım sayesinde formasyonun üstünden geçse bile komşulara en az dikey fark kadar uzak kalır. Yükseklik tek bir ayardır (`katilim_yaklasma_yuksekligi_m`) ve çarpışma kaçınma mesafesinden büyük olması başlangıçta doğrulanır. Adım sayısı değişmez (aynı katılım adımının içinde yapılır), bedeli birkaç saniyedir.
`[Birim test]` Ölçülen gerçek iz komşulara < 3 m yaklaşırken üstten yaklaşma yolu ≥ 3 m (3,6–5,0 m) uzak kalıyor; ayar doğrulaması testli. `[Gazebo]` (14:28 provası, karışık dizilim) Geri katılış adımında dronlar arası en küçük mesafe **1,94 m → 4,0 m** (İHA-1 ile 4,89 m, İHA-3 ile 4,0 m); dron slotunun 4,0 m üstünden yaklaşıp alçaldı, adım sonunda slot hatası 0,76 m. Katılım adımı 34,4 sn'den 37,4 sn'ye uzadı (beklenen ≈ +3 sn); toplam süre 295 sn.

**Seçenek notu.** Alternatif olarak ayrılma noktasında beklemek rotasyonu da 3 dronla yapar ama yaklaşık 25–30 sn daha yavaştır; seçilmedi (`acik_sorular.md` madde 13).

---

### 2.8 Karışık dizilimde konuma göre slot ataması

**Problem.** Hakemler dronları yerde karışık dizer [5.1]. Slot = dron numarası olursa, dronlar kendi slotuna giderken birbirinin önünden geçer. Provada, önceki uçuşun iniş konumları tesadüfen karışık bir dizilim oluşturdu ve ilk formasyonda dronlar 2,0 m'ye kadar yaklaştı (hazır dizilimde bu mesafe 5,0 m idi).

**Çözüm (sade).** Kalkıştan hemen önce, dronlar yerdeki konumlarını paylaşır ve her biri aynı hesabı yapar: "hangi dron hangi slota giderse toplam yol en kısa olur?" Sonuçta her slot tam bir dron alır ve dronların düz yolları birbirini kesmez. Dronlar hesapları birbirine doğrulatır; uyuşmazlık olursa herkes eski kurala (numara = slot) döner.

**Teknik.**
- En kısa toplam yatay yolu veren bire bir eşleşme; Macar yöntemi (Kuhn–Munkres), O(n³), N dron için jenerik, harici kütüphane gerektirmez.
- Toplam uzaklığı en aza indiren eşleşmede düz yollar düzlemde kesişmez (üçgen eşitsizliğine dayanan bilinen özellik); birim testte 25 rastgele senaryoda doğrulandı.
- Dağıtık tutarlılık için konumlar 0,5 m ızgaraya yuvarlanır, eşitlikte numara = slot korunur; her dron önerisini yayınlar, herkes aynı öneriyi bildirmezse (veya komşu susarsa) güvenli yola döner.
- Slot sahibi görev boyunca sabittir; ayrılan dron geri dönünce aynı slota oturur.

**Kanıt.**
- `[Birim test]` Provadaki gerçek konumlar için eşleşme İHA-1→2, İHA-2→3, İHA-3→1; kaba kuvvet aramayla aynı optimum (25 senaryo); uzlaşma protokolü (aynı görüş, farklı öneri, susan komşu).
- `[Hesap]` Aynı konumlarda toplam yol **16,1 m → 3,7 m**; düz yollarda komşular arası en küçük mesafe **1,9 m → 4,9 m**.
- `[Gazebo]` Hazır dizilimde (13:50 provası): üç dron BASLAT'tan 0,1 sn sonra aynı atamayı buldu ve doğruladı, kimlik tercihi sayesinde gereksiz yer değiştirme yapılmadı; kalkışta gecikme yok.
- `[Gazebo]` Karışık dizilimde (`SPAWN_SIRASI=2,3,1`, 14:01 provası): üç dron BASLAT'tan 0,1 sn sonra aynı atamayı buldu (`{1:2, 2:3, 3:1}`, beklenen sonuç); toplam yol **2,5 m** (numara = slot olsaydı 15,7 m). İlk formasyonda dronlar arası en küçük mesafe **4,95 m** (atamasız karışık dizilimde 2,01 m idi, hazır dizilimde 4,98 m). Kalkıştan ilk formasyonun sonuna kadar hiçbir çiftte 4,9 m'nin altına inilmedi.

**Nasıl test ediyoruz (karışık dizilim provası).** Şartname hakemlerin dronları yerde karışık dizeceğini söylüyor [5.1]; bunu simülasyonda tekrarlanabilir biçimde denemek için Gazebo başlatma betiğine `SPAWN_SIRASI` seçeneği eklendi. Örneğin `SPAWN_SIRASI=2,3,1` ile İHA-1, İHA-2'nin normal başlangıç noktasında, İHA-2 İHA-3'ünkinde, İHA-3 İHA-1'inkinde doğar. Seçenek verilmezse davranış eskisi gibidir. Böylece "önceki uçuşun iniş noktası" gibi tesadüflere bağlı kalmadan aynı karışık başlangıç istenildiği kadar tekrar üretilebilir.

Prova şu soruları cevaplar:
1. **Uzlaşma çalışıyor mu?** Üç dronun logunda da aynı atama (beklenen `{1:2, 2:3, 3:1}`) çıkmalı ve "slot = numara kullanılıyor" uyarısı çıkmamalı.
2. **Atama gerçekten işe yarıyor mu?** İlk formasyon adımında dronlar arası en küçük mesafe, atamasız durumdaki 2,01 m'den belirgin biçimde yukarı çıkmalı (hazır dizilimdeki 4,98 m'ye yakın); toplam yol logdaki hesapla (≈ 3,7 m, numara = slot olsaydı ≈ 16,1 m) uyumlu olmalı.
3. **Geri kalan görev bozulmuyor mu?** Adım sayacı üç dronda aynı bitmeli, senkron zaman aşımı olmamalı; ayrılan dron geri dönerken kendi (atanmış) slotuna oturmalı, çarpışma ve 10 m ihlali olmamalı.

**Sonuç (14:01 provası).**
1. Uzlaşma çalıştı: üç logda aynı atama, geri dönüş uyarısı yok.
2. Atama işe yaradı: ilk formasyon en küçük mesafesi 2,01 m → 4,95 m; toplam yol 15,7 m → 2,5 m.
3. Görev bozulmadı: adım sayacı üç dronda 72'de bitti, zaman aşımı ve kritik yakınlık yok, 10 m ihlali yok, ayrılan dron renkli alana 1,14 m ile indi ve atanmış slotuna (slot 3) oturdu. **Bir istisna:** ayrılan dronun sürüye geri katılırken en küçük mesafe 1,94 m'ye indi (bkz. Sınır).

**Sınır (ölçümden çıkan).** Slot ataması geri katılımın yolunu da değiştiriyor: karışık dizilim provasında ayrılan İHA-2'nin slotu formasyonun uzak tarafına (slot 3) düştü, renkli alandan düz çizgiyle gelirken diğer iki dronun arasından geçti ve en küçük mesafe **1,94 m / 2,01 m** oldu (hazır dizilimde aynı adımda 5,6 m idi). Çarpışma kaçınma devreye girdi, kritik eşiğe (1,5 m) inilmedi, ama bu marj dar; bu yüzden geri katılımda formasyonun üstünden yaklaşma eklendi (2.7'ye bakın); Gazebo'da doğrulandı (en küçük mesafe 1,94 m → 4,0 m).

**Sınır.** Hakemin formasyonda dron sırasına bakıp bakmadığı bilinmiyor (`acik_sorular.md` madde 15); gerekirse tek ayarla kapatılır. Telsiz kaybı durumunda uzlaşma için kesin karar mesajı ileride eklenecek (madde 16).

---

### 2.9 İmzalı ve doğrulamalı dronlar arası mesajlaşma

**Problem.** Dronlar arası mesajlar bozuk, eski veya yabancı bir kaynaktan gelirse sürü yanlış karar verebilir.

**Çözüm (sade).** Her mesaj takım anahtarıyla imzalanır; yanlış imzalı, bozuk, bayat veya tekrarlanmış mesaj atılır. Anahtar kodda ve repoda düz yazılı durmaz.

**Teknik.** HMAC-SHA256 imza (zamanlama saldırısına dayanıklı karşılaştırma), mesaj sürümü, gönderen kimliği, sıra numarası (tekrar saldırısına karşı), zaman damgası ve azami yaş süzgeci. Taşıyıcı soyuttur: simülasyonda UDP, sahada telsiz aynı arayüze takılır. Dışarıdan gelen her alan (ATAMA gibi) doğrulanır.

**Kanıt.** `[Birim test]` geçerli, bayat, yanlış anahtarlı, bozuk JSON ve tekrarlı paket senaryoları.

---

### 2.10 Tablo tabanlı, ayar dosyalı genişletilebilirlik

**Problem.** Yarışmada yeni formasyon veya komut istenebilir; kodun birçok yerinde `if/elif` zinciri varsa değişiklik hata getirir.

**Çözüm (sade).** Her formasyon tek bir küçük fonksiyon, her komut tek bir küçük fonksiyondur; ad → fonksiyon eşlemesi bir tablodadır. Yeni formasyon eklemek için başka dosya değiştirmek gerekmez. Hız, mesafe, irtifa, eşik gibi tüm sayılar `ayarlar/` altındadır ve her birinin yanında birim, açıklama ve kaynak etiketi (`[Ş]` şartname, `[K]` doğrulandı, `[Y]` tahmin) bulunur.

**Teknik.** `formasyonlar.py` ve `komutlar.py` tablo tabanlıdır; ayar yükleyici şartname kurallarını başlangıçta doğrular (örn. kalkış irtifası 10 m'nin altındaysa program başlamaz, kamera FOV'u 90°'yi aşarsa reddedilir).

**Kanıt.** `[Birim test]` N=3,4,5 için tüm formasyonlar; ayar doğrulama testleri.

---

### 2.11 Otomatik prova raporu

**Problem.** "Çarpışma yok, 10 m ihlali yok" iddiasını sadece gözle izlemek yetersiz; ilk analizimizde uyarı sayılarına bakıyorduk ama gerçek mesafeyi ve irtifayı ölçemiyorduk.

**Çözüm (sade).** Her dron uçuş boyunca konumunu, hedefini ve ideal slotunu 10 Hz CSV'ye yazar. Bir betik bu kayıtlardan raporu otomatik üretir.

**Raporun ölçtükleri.** Dronlar arası en küçük mesafe, uçuş fazındaki gerçek en düşük irtifa, adım sonu slot hatası (formasyon bütünlüğü göstergesi), renkli alana iniş sapması, senkron/varış zaman aşımları, atama ve katılım süreleri. Sonuç "TEMİZ" veya "TEMİZ DEĞİL" olarak çıkar (çıkış kodu 0/1).

**Neden önemli.** Gerçek drona geçiş kapısı "ardışık 3 temiz prova"dır; bu rapor o kapıyı sayıya çevirir. Şartnamenin cezalarını (çarpışma, irtifa, formasyon bütünlüğü, osilasyon) ölçülebilir hâle getirir.

**Kanıt.** `[Gazebo]` Son prova ölçümleri: ortalama adım sonu slot hatası 0,6–1,0 m; bekleme anlarında konum sapması 1–2,6 cm (osilasyon göstergesi); renkli alana iniş 1,14–1,19 m (sınır 2,5 m).

**Raporda kullanılabilecek grafikler (CSV'den çizilebilir).** Dronlar arası mesafe zaman çizgisi; irtifa zaman çizgisi ve 10 m çizgisi; üstten yörünge görünümü (formasyon + QR rotası); adım sonu slot hatası dağılımı.

---

### 2.12 QR için hazır komut kaynağı soyutlaması

**Problem.** QR okuma şimdilik kapsam dışı, ama sonradan eklenince sistemin geri kalanı değişmemeli.

**Çözüm (sade).** Görev komutları tek bir arayüzün ("komut kaynağı") arkasından gelir. Bugün kaynak bir senaryo dosyasıdır ve QR'dan okunmuş gibi davranır; QR okuyucu yazılınca aynı yere takılır. Şartnamedeki QR JSON biçimi (Şekil 2) için ayrıştırıcı hazırdır ve yalnız kendi takım kimliğimizin görevini uygular.

**Kanıt.** `[Birim test]` QR biçimi ayrıştırma, takım kimliği süzgeci, geçersiz içerik reddi.

---

## 3. Küçük ama değerli tasarım ayrıntıları

- **YKİ'ye bağımlılık yok [5.1].** YKİ yalnız "başlat" gönderir. Bir drona ulaşan BASLAT mesajı diğerlerine yayılır; hakem bağlantıyı kessin ya da bir drona ulaşılamasın, sürü görevi sürdürür.
- **Havada disarm yok ve offboard akışı kesilmez.** Setpoint akışı arka planda sürekli sürer (kesilirse PX4 offboard'dan çıkar).
- **Ayrılan dronun iniş doğruluğu ölçülüp loglanır** (alan merkezine uzaklık ve 2,5 m sınırına göre geçerli/geçersiz).
- **GPS tutarlılık kontrolü.** Formasyonda beklerken komşu GPS mesafesi beklenen formasyon mesafesiyle karşılaştırılır; sapma uyarı olarak loglanır. Ayrılmış komşular hariç tutulur. (Sınır: GPS'i GPS ile doğrulamak ortak kaymayı yakalayamaz.)
- **Her uçuşta kod sürümü ve ayar özeti kaydedilir** (`kayitlar/ayar_ozeti_*.json`), böylece her sonuç hangi kodla ve hangi ayarla alındığına bağlanabilir.
- **Gerçek drona geçmeden önce "simülasyonda çalışmayan kod gerçek drona gitmez" kuralı.** PX4'ü taklit eden sahte simülatör yazmadık; davranış doğrudan PX4 SITL + Gazebo'da denendi. Yalnız PX4 gerektirmeyen saf hesaplar (geometri, mesaj ayrıştırma, atama, senkron mantığı) birim testle denendi.

---

## 4. Mühendislik süreci: ölçüm → kök neden → düzeltme

Jüriye "sistemi nasıl geliştirdiniz" sorusunun cevabı olarak anlatılabilir. Bu projede loglardan ve kayıtlardan ilerledik:

1. **İlk tam prova.** Görev tamamlandı ama loglarda 50 sn'lik senkron bekleme ve 1,3 m'ye varan yakınlaşma gördük.
2. **Kök neden analizi.** Adım numaralarının dronlar arasında kaydığı ve ayrılan dronun sürüyle aynı anda rotasyona başlamadığı ortaya çıktı. İlk hipotezimiz rotasyonun düz çizgi geometrisiydi; hesapla doğrulayınca geometrinin tek başına yakınlaşmayı açıklamadığını (yalnız ≈ 3,6 m'ye indirdiğini) gördük ve asıl nedenin sayaç kayması olduğunu belirledik. **Her ikisini de düzelttik.**
3. **Ölçümü sayıya çevirmek.** "Uyarı yok" yerine gerçek mesafeyi/irtifayı ölçen otomatik rapor yazdık.
4. **Şartnamedeki ince kuralı yakalamak.** "En geç sonraki QR'da katıl" + Tablo 7'nin "en az 3 İHA" kuralı birlikte okunarak katılım adımı tasarlandı.
5. **Kazayla bulunan senaryo.** Provayı tekrar başlatınca dronlar önceki uçuşun iniş noktalarından kalktı; bu kasıtsız "karışık dizilim", slot ataması ihtiyacını gösterdi.

Bu akış, loglamaya ve ölçüme dayalı, tekrarlanabilir bir geliştirme yöntemini göstermesi bakımından rapora konabilir.

---

## 5. Dürüst sınırlar ve yapılacaklar

Rapora "tamamlandı" diye yazılmaması gerekenler:

- **QR okuma ve QR içeriğinin YKİ'de gösterilmesi** henüz yok (kapsam dışı bırakıldı; QR gelince ceza −20 riski kapatılacak).
- **Birey ekleme (20 puan) ve yedek dron** henüz yok.
- **Renkli alanı kamerayla bulma** henüz yok; simülasyonda alanın yakınından geçilince "keşfedildi" sayılıyor. Gazebo kamerasından Python'a görüntü alma ilk denenecek risk.
- **RC kopma failsafe'i (5 sn sonra Land) ve YKİ kesilme senaryosu** doğrulanmadı; arıza provaları (dron öldürme, GPS bozma, kumanda koparma) yapılmadı.
- **Görev 2** (yarı otonom) yazıldı ama bu belgedeki ölçümler Görev 1 provalarından; Görev 2 için ayrı prova raporu yok.
- **Formasyon değişimlerinde yakınlık:** çizgi ↔ ok başı ↔ V geçişlerinde (katmanlı geçiş) dronlar arası en küçük mesafe 2,8–3,1 m'ye iniyor (kaçınma eşiği 2,5 m, kritik 1,5 m); marj yeterli ama iyileştirme adayı.
- **GPS güvenilmezliği** için GPS'ten bağımsız ölçüm sahada karar verilecek.
- Tüm sonuçlar **simülasyon (PX4 SITL + Gazebo)** sonuçlarıdır; gerçek donanımda ölçülmedi.
- Hakem brifinginde teyit edilecek yorumlar: `notlar/acik_sorular.md` (özellikle madde 4, 10, 13, 15).

---

## 6. Provalar ve ölçüm özeti

| Prova | Süre | Dronlar arası en küçük mesafe | Senkron zaman aşımı | Not |
|---|---|---|---|---|
| 1 (11:37, düzeltme öncesi) | 367 sn | 1,21 m | 1 (≈ 50 sn) | Adım sayacı kaymıştı |
| 2 (12:57, rotasyon + sayaç düzeltmesi) | 267 sn | 2,90 m | 0 | Ayrılan dron sürüyü izleyerek geri katıldı |
| 3 (13:17, katılım adımı eklendi, karışık başlangıç) | 290 sn | 2,01 m (ilk formasyon, karışık dizilim), 2,87 m (diğer) | 0 | Katılım 30 sn; slot ataması bu provadan sonra eklendi |
| 4 (13:50, slot ataması açık, hazır dizilim) | 288 sn | 2,91 m (en küçük), ilk formasyonda 4,98 m | 0 | Üç dron aynı atamayı buldu (`{1:1, 2:2, 3:3}`), uzlaşma 0,1 sn sürdü; sonuçlar prova 2–3 ile uyumlu |
| 5 (14:01, karışık dizilim, `SPAWN_SIRASI=2,3,1`) | 292 sn | 1,94 m (en küçük, geri katılım adımı), ilk formasyonda **4,95 m** | 0 | Atama `{1:2, 2:3, 3:1}`, toplam yol 2,5 m (numara = slot olsaydı 15,7 m); geri katılırken İHA-2 formasyonun içinden geçti (1,94 / 2,01 m), katılım adımı 34,4 sn |
| 6 (14:28, karışık dizilim + yukarıdan katılma) | 295 sn | 2,80 m (en küçük, V geçişi); geri katılım adımında **4,0 m**; ilk formasyonda 4,74 m | 0 | Atama `{1:2, 2:3, 3:1}` (2,5 m / 15,7 m); geri katılırken İHA-2 slotunun 4 m üstünden yaklaştı, katılım adımı 37,4 sn |

Her altı provada: çarpışma yok, 10 m ihlali yok (en düşük uçuş irtifası ≈ 14,4 m), görev tamamlandı.

Test durumu: **112 birim testi geçiyor** (başlangıçta 32).

---

## 7. Kaynak ve fikir notları

AGENTS.md kuralı gereği ödünç alınan fikirler belirtilir. Kodun tamamı bu projede yazılmıştır.

- Sanal yapı ile formasyon kontrolü: Lewis, M. A. & Tan, K.-H., "High precision formation control of mobile robots using virtual structures", Autonomous Robots, 1997 (kavram kaynağı; uygulama bize aittir).
- Atama problemi için Macar yöntemi: Kuhn (1955) ve Munkres (1957) (klasik algoritma; uygulama bize aittir).
- Mesaj imzası: HMAC (RFC 2104), SHA-256 (standart kütüphaneler).
- Yarışma kuralları: TEKNOFEST 2026 Sürü İHA Yarışması Şartnamesi V1.2.

---

## 8. Güncelleme günlüğü

| Tarih | Eklenen |
|---|---|
| 2026-11-23 | İlk sürüm: 1–12 numaralı katkılar, prova özeti, sınırlar |
| 2026-11-23 | Prova 4 (hazır dizilim, slot ataması açık) sonucu eklendi; karışık dizilim provası (prova 5) için satır açıldı |
| 2026-11-23 | 2.8'e "Nasıl test ediyoruz" eklendi: `SPAWN_SIRASI` karışık dizilim senaryosu ve provanın cevaplayacağı üç soru |
| 2026-11-23 | 2.7'ye "yukarıdan katılma" eklendi (geri katılışta formasyonun üstünden yaklaşma); Gazebo ölçümü bekliyor |
| 2026-11-23 | Prova 6 (14:28) sonucu: yukarıdan katılma doğrulandı (geri katılım en küçük mesafe 1,94 → 4,0 m); formasyon geçişleri 2,8–3,1 m yeni iyileştirme adayı olarak sınırlara yazıldı |
| 2026-11-23 | Prova 5 (karışık dizilim) sonuçları eklendi: atama doğrulandı (ilk formasyon 2,01 → 4,95 m); geri katılışta 1,94 m'lik yakınlaşma sınır olarak not edildi |
