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
13. **Karar verildi (hakem brifinginde teyit edilecek) — "en geç sonraki QR'da katıl"** [5.1]: Sürü sonraki QR'a varınca ayrılan dron slotuna oturana kadar QR'ı okumadan bekler (katılım adımı); böylece o QR'ın formasyon/manevra komutları 3 dronla uygulanır (Tablo 7). Ayrılan dron susarsa komşular onu canlı listeden düşürür, en çok `ayrilma_tamamlama_zaman_asimi_s` beklenir. Alternatif (ayrılma noktasında beklemek, rotasyon da 3 dronla yapılsın) ~25–30 sn daha yavaş; seçilmedi.
14. **Şartname 5.1: iniş sonrası dron kalkış beklemesi.** Ayrılan dronun yerde bekleme süresi (`ayrilma_yerde_bekleme_s`) şartnamede verilmiyor, `[Y]` tahmin.
15. **Formasyonda hangi dron hangi slotta durmalı?** [5.1] Şimdilik dronlar yerdeki konumlarına göre en kısa toplam yolla slota atanıyor (karışık dizilimde yol kesişmesin diye); slot numarası dron numarasına bağlı değil. Şartname formasyonda dron sırasını (1. dron öndeki mi?) net söylemiyor, Şekil 3 numarasız çizilmiş görünüyor. Hakem brifinginde sırası önemli mi diye sorulacak; önemliyse `slot_atama_acik=false` yapılır (tek ayar).
16. **ATAMA mesajı kaybı:** Slot ataması uzlaşması UDP üzerinden önerileri tekrar tekrar yayınlayarak çalışır; simülasyonda kayıp yok. Sahada telsiz bir komşunun önerisini kaçırırsa yalnız o dron slot = numaraya dönüp diğerleri farklı atamayı kullanabilir. Sahada telsiz güvenilirliği ölçülünce bu risk için kesin karar mesajı eklenecek.
