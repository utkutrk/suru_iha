# Sürü İHA — TEKNOFEST

Amaç: en az 3 dronluk, **dağıtık** bir sürüyü iki görevde uçurmak (Görev 1: QR ile dinamik sürü, Görev 2: tek kumandayla yarı otonom sürü).
Kodlama ajanı için kurallar ve amaç: **`AGENTS.md`**. Ana kaynak: `sartname/`.

## Takım kuralları
1. Sayılar koda gömülmez; `ayarlar/` içinde durur.
2. Yeni formasyon veya komut tek yerde eklenir (formasyonlar tek dosyada, komutlar tek dosyada).
3. Simülasyonda çalışmayan kod gerçek drona gitmez.

## Okuma sırası
`AGENTS.md` → `sartname/ozet.md` → `sartname/puan_ve_ceza.md` → `notlar/dosya_haritasi.md` → `notlar/acik_sorular.md`

## Klasörler
```
suru_iha/
├── AGENTS.md  README.md  .gitignore
├── sartname/     şartname özeti, puan ve cezalar (şartname PDF'i de buraya konur)
├── ayarlar/      tüm sayılar (şartname.json hazır)
├── yazilim/      kod (iç yapıyı kodlama ajanı belirler)
├── yki/          yer istasyonu (şimdilik QGroundControl; kendi YKİ'miz ileride)
├── simulasyon/   Gazebo dünyası ve modeller
├── senaryolar/   uçuş ve arıza senaryoları
├── test/         testler
├── betikler/     başlatma ve yardımcı betikler
├── kayitlar/     uçuş logları (git'e girmez)
└── notlar/       açık sorular, kararlar
```
Donanım, saha ve teslim (rapor/video) klasörleri gerektiğinde açılır.
