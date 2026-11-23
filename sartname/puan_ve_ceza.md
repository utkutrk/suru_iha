# Puan ve Ceza (Şartname V1.2, sayfa 23, Tablo 4-7)

Kaynak: şartname sayfa 23 görseli, elle okundu. Hepsi [Ş] (doğrulandı), yalnız "yorum" yazanlar [Y].

## Tablo 4 — Genel
| Kalem | Puan |
|---|---|
| Görev 1: Dinamik Sürü Kabiliyeti | 250 |
| Görev 2: Yarı Otonom Sürü Kontrolü | 150 |
| KTR puanı | (10 × KTR puanı) / 100 |
| Uçuş Kanıt Videosu puanı | (10 × video puanı) / 100 |

Her görev için en fazla 3 hak; en yüksek puan geçerli [8.4].
Dikkat: Metin 8.3 "rapor ve video %20, görev %80" diyor. Tabloya göre KTR ve video en fazla 10'ar puan, görevler toplam 400. İkisi birbirini tutmuyor; Soru-Cevap'ta sorulacak. Hesapta tabloyu esas alıyoruz.

## Tablo 5 — Görev 1 (Dinamik Sürü)
| Puan kalemi | Puan | Ceza | Puan |
|---|---|---|---|
| Formasyon | 15 × görev adeti | Çarpışma | −20 |
| Formasyon rotasyonu | 5 × görev adeti | Görev sırasında İHA düşmesi | −20 |
| Navigasyon | 5 × görev adeti | Osilasyon gözlemlenmesi | −(1–15) |
| Manevra | 15 × görev adeti | Formasyon bütünlüğünün bozulması | −(1–15) |
| İrtifa değişimi | 5 × görev adeti | YKİ bağlantısının kesilememesi | −50 |
| Sürüden birey çıkarma | 30 | QR mesajının YKİ'de en az 1 kez görülememesi | −20 |
| Sürüye birey ekleme | 20 | İrtifa sınırının ihlali | −20 |

Yorum [Y]: "görev adeti" = senaryoda o komuttan kaç tane varsa (ör. 3 formasyon komutu = 45 puan). 250 üst sınır gibi görünüyor.

## Tablo 6 — Görev 2 (Yarı Otonom)
| Puan kalemi | Puan | Ceza | Puan |
|---|---|---|---|
| Yarı otonom kalkış | 10 | Çarpışma | −20 |
| Formasyon değişimi | 30 | Görev sırasında İHA düşmesi | −20 |
| Sürü hareket modu | 40 | Osilasyon gözlemlenmesi | −(1–15) |
| Sürü manevra modu | 60 | Formasyon bütünlüğünün bozulması | −(1–15) |
| Yarı otonom iniş | 10 | | |

Toplam 150. En değerli tek kalem manevra modu (60).

## Tablo 7 — Görev bazlı minimum aktif İHA
| Görev | Min. İHA |
|---|---|
| Formasyon | 3 |
| Manevra | 3 |
| Rotasyon | 3 |
| Navigasyon | 2 |
| Birey ekleme/çıkarma | 2 |
| İrtifa değişimi | 2 |

Anlamı: 2 İHA'ya düşsek bile navigasyon, irtifa ve birey ekleme/çıkarmadan puan almaya devam ederiz; formasyon, manevra ve rotasyondan alamayız [8.4].

## Bunlardan çıkan sonuçlar
- Ödül için en az 200 görev puanı ve iki görevden de puan gerekir [12.1]. Örnek yol: Görev 2'den 150 + Görev 1'den en az 50.
- Bir çarpışma ya da düşme (−20) bir formasyon komutunun puanından (15) büyüktür. Güvenlik puandan önce gelir.
- Birey çıkarma + ekleme = 50 puan; yalnız 2 dron gerektirir.
- Osilasyon ve formasyon bütünlüğü cezaları 1–15 arası, hakem takdiri. PID salınımı ve GPS gürültüsü doğrudan bunu etkiler.
- YKİ −50: Hakem bağlantıyı keser. Sürü YKİ'ye bağımlı olmamalı ve bağlantı gerçekten kesilebilir olmalı.

## Ceza → önlem fikri
| Ceza | Önlem fikri |
|---|---|
| Çarpışma −20 | Komşu mesafesi izleme, geçişte farklı irtifa katmanları, yakınlıkta yavaşlama |
| İHA düşmesi −20 | Havada disarm yok, offboard akışı kesilmez, failsafe |
| Osilasyon −(1–15) | Yumuşak hız profili, filtre, ayarlı kazançlar |
| Formasyon bütünlüğü −(1–15) | Senkron adım geçişi, sabit slotlar, hızlı geri katılma |
| YKİ kesilememesi −50 | Sürü YKİ'ye bağımlı değil; YKİ yalnız başlatır |
| QR YKİ'de görülmedi −20 | Çözülen QR içeriğini YKİ'ye gönder |
| İrtifa sınırı ihlali −20 | 10 m tabanı, eğimde en alçak dron dahil |
