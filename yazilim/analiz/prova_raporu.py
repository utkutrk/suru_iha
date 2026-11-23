"""Konum CSV'lerinden ve uçuş loglarından prova raporu üretir (çarpışma, 10 m, formasyon, iniş doğruluğu)."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from yazilim.ortak.ayarlar import Ayarlar
from yazilim.ortak.konum_kaydi import FAZ_AYRILMA, FAZ_UCUS


@dataclass
class Kayit:
    """Bir dronun konum CSV'sinin sütunlara ayrılmış hali."""

    iha_id: int
    t: np.ndarray
    adim: np.ndarray
    faz: np.ndarray
    aciklama: np.ndarray
    konum: np.ndarray  # (N, 3) ortak NED
    slot: np.ndarray  # (N, 3), slot yoksa NaN
    havada: np.ndarray


def kayit_oku(yol: Path, iha_id: int) -> Kayit:
    """Konum CSV dosyasını okur; boş slot hücreleri NaN olur."""
    with yol.open("r", encoding="utf-8", newline="") as f:
        satirlar = list(csv.DictReader(f))

    def sayi(anahtar: str) -> np.ndarray:
        return np.array([float(s[anahtar]) if s[anahtar] != "" else np.nan for s in satirlar])

    return Kayit(
        iha_id=iha_id,
        t=sayi("t_epoch_s"),
        adim=sayi("adim").astype(int) if satirlar else np.array([], dtype=int),
        faz=np.array([s["faz"] for s in satirlar]),
        aciklama=np.array([s["aciklama"] for s in satirlar]),
        konum=np.column_stack([sayi("kuzey_m"), sayi("dogu_m"), sayi("asagi_m")]) if satirlar else np.zeros((0, 3)),
        slot=np.column_stack([sayi("slot_kuzey_m"), sayi("slot_dogu_m"), sayi("slot_asagi_m")]) if satirlar else np.zeros((0, 3)),
        havada=sayi("havada").astype(bool) if satirlar else np.array([], dtype=bool),
    )


def en_yakin_mesafe(a: Kayit, b: Kayit, pencere_s: float) -> tuple[float, float, str]:
    """İki dronun CSV satırlarını pencere_s içinde eşleştirip havadayken birbirine en çok yaklaştığı 3B mesafe, zamanı ve o anki adım açıklaması."""
    if len(a.t) == 0 or len(b.t) == 0:
        return float("inf"), float("nan"), ""
    sira = np.searchsorted(b.t, a.t)
    sira = np.clip(sira, 1, len(b.t) - 1)
    onceki_yakin = np.abs(b.t[sira - 1] - a.t) <= np.abs(b.t[sira] - a.t)
    j = np.where(onceki_yakin, sira - 1, sira)
    gecerli = (np.abs(b.t[j] - a.t) <= pencere_s) & a.havada & b.havada[j]
    if not np.any(gecerli):
        return float("inf"), float("nan"), ""
    mesafe = np.linalg.norm(a.konum - b.konum[j], axis=1)
    mesafe = np.where(gecerli, mesafe, np.inf)
    i = int(np.argmin(mesafe))
    return float(mesafe[i]), float(a.t[i]), str(a.aciklama[i])


def en_dusuk_irtifa(k: Kayit) -> tuple[float, str]:
    """Yalnız 'ucus' fazındaki en düşük irtifa (kalkış, ayrılma ve iniş fazları 10 m kuralının dışındadır)."""
    maske = (k.faz == FAZ_UCUS) & k.havada
    if not np.any(maske):
        return float("inf"), ""
    irtifa = -k.konum[:, 2]
    irtifa = np.where(maske, irtifa, np.inf)
    i = int(np.argmin(irtifa))
    return float(irtifa[i]), str(k.aciklama[i])


def slot_hatasi(k: Kayit) -> tuple[float, float, float] | None:
    """Adım sonu slot hatasının (ortalama, %95, en büyük) değeri: her 'ucus' adımının sondan ikinci örneği.

    Neden adım sonu: hareket sırasında slot hedefi ileri atladığı için anlık sapma yüzlerce metreye çıkar
    ve formasyon bütünlüğünü göstermez; adım bitiminde dronun slotuna ne kadar yakın durduğu anlamlıdır.
    """
    hatalar = []
    for adim in np.unique(k.adim):
        idx = np.where((k.adim == adim) & (k.faz == FAZ_UCUS) & k.havada & ~np.isnan(k.slot[:, 0]))[0]
        if len(idx) > 2:
            j = idx[-2]
            hatalar.append(float(np.linalg.norm(k.konum[j] - k.slot[j])))
    if not hatalar:
        return None
    hata = np.array(hatalar)
    return float(np.mean(hata)), float(np.percentile(hata, 95)), float(np.max(hata))


def inis_sapmasi(k: Kayit, alanlar: dict[str, np.ndarray]) -> tuple[str, float] | None:
    """Ayrılma fazında yerde kalınan konumun en yakın renkli alan merkezine yatay uzaklığı."""
    maske = (k.faz == FAZ_AYRILMA) & ~k.havada
    if not np.any(maske):
        return None
    yer = np.median(k.konum[maske][:, :2], axis=0)
    renk, alan = min(alanlar.items(), key=lambda kv: float(np.linalg.norm(yer - kv[1][:2])))
    return renk, float(np.linalg.norm(yer - alan[:2]))


def _en_yeniler(dizin: Path, desen: str, oturum: str | None) -> dict[int, Path]:
    """Her dron için en yeni dosyayı seçer (isteğe bağlı olarak zaman damgası öneki verilir)."""
    sonuc: dict[int, Path] = {}
    for yol in sorted(dizin.glob(desen)):
        eslesme = re.search(r"_(\d{8}_\d{6})_iha(\d+)\.", yol.name)
        if eslesme is None or (oturum and not eslesme.group(1).startswith(oturum)):
            continue
        sonuc[int(eslesme.group(2))] = yol
    return sonuc


def log_sayaclari(yol: Path) -> dict[str, object]:
    """Uçuş logundaki önemli olay sayıları."""
    metin = yol.read_text(encoding="utf-8")
    return {
        "tamamlandi": int("başarıyla tamamlandı" in metin),
        "senkron_zaman_asimi": metin.count("senkron zaman aşımı"),
        "varis_zaman_asimi": metin.count("Hedefe varış zaman aşımı"),
        "kritik_yakinlik": metin.count("Kritik yakınlık"),
        "gps_uyarisi": metin.count("GPS tutarlılık uyarısı"),
        "gecersiz_inis": metin.count("GEÇERSİZ"),
        "slot_atamasi": (re.findall(r"Slot ataması \(İHA->slot\) (\{[^}]*\}): toplam yol ([0-9.]+) m \(numara=slot olsaydı ([0-9.]+) m\)", metin) or [None])[0],
        "slot_atamasi_geri_donus": int("slot = numara kullanılıyor" in metin),
        "katilim_sureleri_s": [float(x) for x in re.findall(r"katılım adımı: ([0-9.]+) s", metin)],
    }


def rapor_uret(dizin: Path, ayarlar: Ayarlar, oturum: str | None = None) -> tuple[str, bool]:
    """Raporu metin olarak ve 'temiz mi' bilgisiyle döndürür."""
    csvler = _en_yeniler(dizin, "konum_*_iha*.csv", oturum)
    loglar = _en_yeniler(dizin, "ucus_*_iha*.log", oturum)
    if not csvler:
        return "Konum CSV'si bulunamadı (kayitlar/konum_*.csv). konum_kaydi_acik=true ile uçuş yapın.", False

    kayitlar = {i: kayit_oku(y, i) for i, y in csvler.items()}
    min_irtifa = float(ayarlar.sartname["min_irtifa_m"])
    irtifa_tol = float(ayarlar.ucus["rapor_irtifa_toleransi_m"])
    pencere_s = float(ayarlar.ucus["rapor_eslestirme_penceresi_s"])
    carpisma_m = float(ayarlar.ucus["rapor_carpisma_mesafesi_m"])
    kritik_m = float(ayarlar.ucus["kritik_carpisma_mesafesi_m"])
    inis_tol = float(ayarlar.sartname["inis_tolerans_m"])
    alanlar = {
        str(k): np.asarray(v, dtype=float)
        for k, v in ayarlar.saha.get("simulasyon_renkli_alanlar_ned", {}).items()
    }

    temiz = True
    satirlar = ["=== PROVA RAPORU ===", f"Dronlar: {sorted(kayitlar)}"]

    # 1. Görev tamamlandı mı, log olayları
    satirlar.append("\n[Log olayları]")
    for iha_id, yol in sorted(loglar.items()):
        s = log_sayaclari(yol)
        satirlar.append(
            f"  İHA-{iha_id}: tamamlandı={'evet' if s['tamamlandi'] else 'HAYIR'}, "
            f"senkron_zaman_aşımı={s['senkron_zaman_asimi']}, varış_zaman_aşımı={s['varis_zaman_asimi']}, "
            f"kritik_yakınlık_uyarısı={s['kritik_yakinlik']}, gps_uyarısı={s['gps_uyarisi']}"
        )
        if s["slot_atamasi"]:
            atama, yol, kimlik_yol = s["slot_atamasi"]
            satirlar.append(f"           slot ataması {atama}: toplam yol {yol} m (numara=slot olsaydı {kimlik_yol} m)")
        if s["slot_atamasi_geri_donus"]:
            satirlar.append("           UYARI: slot ataması uzlaşılamadı, slot = numara kullanıldı")
        if s["katilim_sureleri_s"]:
            satirlar.append(f"           ayrılan dron katılım adımı süresi: {s['katilim_sureleri_s']} s")
        if not s["tamamlandi"] or s["gecersiz_inis"]:
            temiz = False
        if s["senkron_zaman_asimi"] or s["varis_zaman_asimi"]:
            temiz = False

    # 2. Dronlar arası en küçük mesafe
    satirlar.append(f"\n[Dronlar arası en küçük mesafe] (çarpışma sayılan: < {carpisma_m} m, kritik: < {kritik_m} m)")
    ids = sorted(kayitlar)
    for x in range(len(ids)):
        for y in range(x + 1, len(ids)):
            m, t, aciklama = en_yakin_mesafe(kayitlar[ids[x]], kayitlar[ids[y]], pencere_s)
            isaret = "ÇARPIŞMA" if m < carpisma_m else ("kritik" if m < kritik_m else "ok")
            satirlar.append(f"  İHA-{ids[x]}↔İHA-{ids[y]}: {m:.2f} m  [{isaret}]  adım: {aciklama}")
            if m < carpisma_m:
                temiz = False

    # 3. İrtifa tabanı
    satirlar.append(f"\n[En düşük irtifa, 'uçuş' fazında] (sınır {min_irtifa} m, tolerans {irtifa_tol} m)")
    for i in ids:
        irt, aciklama = en_dusuk_irtifa(kayitlar[i])
        ihlal = irt < min_irtifa - irtifa_tol
        satirlar.append(f"  İHA-{i}: {irt:.2f} m  [{'İHLAL' if ihlal else 'ok'}]  adım: {aciklama}")
        if ihlal:
            temiz = False

    # 4. Formasyon bütünlüğü
    satirlar.append("\n[Adım sonu slot hatası (ölçülen konum - ideal slot)]  ortalama / %95 / en büyük")
    for i in ids:
        h = slot_hatasi(kayitlar[i])
        satirlar.append("  İHA-%d: yeterli veri yok" % i if h is None else f"  İHA-{i}: {h[0]:.2f} / {h[1]:.2f} / {h[2]:.2f} m")

    # 5. Renkli alana iniş doğruluğu
    satirlar.append(f"\n[Renkli alana iniş] (sınır {inis_tol} m)")
    inis_var = False
    for i in ids:
        r = inis_sapmasi(kayitlar[i], alanlar) if alanlar else None
        if r is not None:
            inis_var = True
            gecerli = r[1] <= inis_tol
            satirlar.append(f"  İHA-{i}: {r[0]} alan merkezinden {r[1]:.2f} m  [{'geçerli' if gecerli else 'GEÇERSİZ'}]")
            if not gecerli:
                temiz = False
    if not inis_var:
        satirlar.append("  (bu provada birey ayrılması görülmedi)")

    satirlar.append(f"\nSONUÇ: {'TEMİZ' if temiz else 'TEMİZ DEĞİL — yukarıdaki satırlara bak'}")
    return "\n".join(satirlar), temiz
