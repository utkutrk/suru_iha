# Açık Sorular

Cevaplanınca "KAPANDI" diye işaretle, cevabı yaz. Cevap gelene kadar tahmini değer config'te `[Y]` etiketiyle durur.

1. **Hedef yarışma yılı.** Mevcut şartname V1.2 (2026); takvimi geçti. Yeni şartname çıkınca `sartname/` güncellenir.
2. **Donanım.** Gövde, uçuş kontrolcüsü, kamera (çözünürlük, FOV ≤ 90°), telsiz, ek sensörler. Simülasyon kapısından sonra.
3. **GPS.** Sahada GPS kalitesi ölçülüp GPS'ten bağımsız ölçüm gerekip gerekmediğine karar verilecek.
4. **Dağıtık algoritma yorumu** [5.3]. Ortak sanal yapı + senkron adım yaklaşımı hakemce "dağıtık" sayılır mı? Soru-Cevap toplantısında sorulacak.
5. **KAPANDI — QR içerik biçimi** (Şekil 2, PDF sayfa 12): Görselden okundu: `{"qr": 1, "w": 4, "mis": [[["frm", "ok", 6], ["mnv", -10, 0], ["alt", 20]], ...], "team": {"1": [1, 4], ...}}`. `team[id] = [1-tabanlı görev indeksi, sonraki QR no]`. Birey çıkarma komutunun kısa kodu (`cikar` / `rem`) hakem brifinginde teyit edilecek `[Y]`.
6. **Tutarsızlık.** Metin 8.3 "rapor+video %20, görev %80" diyor; Tablo 4'e göre KTR ve video en fazla 10'ar puan, görevler toplam 400.
7. **Formasyon aralığı sınırları.** Şartname örnek veriyor (5 m, 6 m); izin verilen alt/üst sınır belirtilmiyor. Hakem brifinginde doğrulanacak.
8. **QR okunurluğu.** 10 m sınırında, seçilecek kamerayla 150 cm QR yeterli piksele sahip mi? Kamera seçilince hesaplanacak.
9. **Gazebo kamera akışı.** Simülasyon kamerasından Python'a görüntü alma yöntemi doğrulanmadı; ilk denenecek risk.
10. **"Görev adeti"** [Tablo 5]. Puan "görev adeti" ile çarpılıyor; senaryoda o komuttan kaç tane varsa mı demek? Hakem brifinginde teyit edilecek.
11. **Renkli alana iniş doğruluğu.** 2.5 m tolerans var; yalnız GPS yeterli mi, görüntü işleme gerekir mi? Simülasyonda ve sahada ölçülecek.
12. **Ertelendi: QR içeriğini YKİ'de gösterme.** Şimdilik QGroundControl kullanılıyor ve QR okuma kapsam dışı. QR eklenince gösterme yolu (örn. STATUSTEXT) ve "başlat" komutunun şartnameye uygun biçimi doğrulanacak.
