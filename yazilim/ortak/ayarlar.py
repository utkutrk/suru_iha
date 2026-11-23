"""Ayar dosyalarını (sartname, ucus, ag, saha) yükler, doğrular ve tek arayüzle sunar."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Proje kök dizini (yazilim/ortak/ayarlar.py -> 2 üst klasör)
PROJE_KOKU = Path(__file__).resolve().parents[2]
AYARLAR_DIZINI = PROJE_KOKU / "ayarlar"


class AyarHatasi(ValueError):
    """Eksik, bozuk veya şartnameye aykırı ayar tespit edildiğinde fırlatılır."""


def _json_oku(yol: Path) -> dict[str, Any]:
    if not yol.exists():
        raise AyarHatasi(f"Ayar dosyası bulunamadı: {yol}")
    try:
        with yol.open("r", encoding="utf-8") as f:
            veri = json.load(f)
    except json.JSONDecodeError as hata:
        raise AyarHatasi(f"Ayar dosyası geçersiz JSON ({yol}): {hata}") from hata
    if not isinstance(veri, dict):
        raise AyarHatasi(f"Ayar dosyası sözlük (object) olmalıdır: {yol}")
    return veri


def _degerleri_cikar(ham: dict[str, Any], dosya_adi: str) -> dict[str, Any]:
    """Meta anahtarları ('_' ile başlayan) atlar ve her kaydın 'deger' alanını çıkarır."""
    sonuc: dict[str, Any] = {}
    for anahtar, kayit in ham.items():
        if anahtar.startswith("_"):
            continue
        if not isinstance(kayit, dict) or "deger" not in kayit:
            raise AyarHatasi(f"{dosya_adi}: '{anahtar}' kaydında 'deger' alanı yok")
        sonuc[anahtar] = kayit["deger"]
    return sonuc


@dataclass(frozen=True)
class Ayarlar:
    """Tüm JSON ayar dosyalarının doğrulanmış anlık görüntüsü."""

    sartname: dict[str, Any]
    ucus: dict[str, Any]
    ag: dict[str, Any]
    saha: dict[str, Any]
    takim_anahtari: str

    def ozet_sozluk(self) -> dict[str, Any]:
        """Uçuş kaydına yazılacak güvenli ayar özeti (gizli anahtar hariç)."""
        return {
            "sartname": self.sartname,
            "ucus": self.ucus,
            "ag": self.ag,
            "saha": self.saha,
        }


def _takim_anahtarini_bul(ag: dict[str, Any], kok: Path) -> str:
    """Takım anahtarını ortam değişkeninden veya git'e girmeyen yerel dosyadan okur."""
    env_adi = str(ag["takim_anahtari_env"])
    env_deger = os.environ.get(env_adi, "").strip()
    if env_deger:
        return env_deger

    yerel_yol = kok / str(ag["yerel_gizli_dosya"])
    if yerel_yol.exists():
        veri = _json_oku(yerel_yol)
        anahtar = str(veri.get("takim_anahtari", "")).strip()
        if anahtar:
            return anahtar

    raise AyarHatasi(
        f"Takım anahtarı bulunamadı. '{env_adi}' ortam değişkenini ayarlayın "
        f"veya '{yerel_yol}' dosyasına {{\"takim_anahtari\": \"...\"}} yazın."
    )


def _sartnameyi_dogrula(
    sartname: dict[str, Any],
    ucus: dict[str, Any],
    ag: dict[str, Any],
    saha: dict[str, Any],
) -> None:
    """Şartnamenin değişmez kurallarına aykırı ayarları daha uçuş başlamadan engeller."""
    min_irtifa = float(sartname["min_irtifa_m"])
    if float(ucus["kalkis_irtifasi_m"]) < min_irtifa:
        raise AyarHatasi(
            f"kalkis_irtifasi_m ({ucus['kalkis_irtifasi_m']}) "
            f"şartname alt sınırı {min_irtifa} m'den küçük olamaz [5.1]"
        )
    if float(ucus["maks_irtifa_m"]) <= min_irtifa:
        raise AyarHatasi("maks_irtifa_m, min_irtifa_m'den büyük olmalıdır")

    if int(ag["varsayilan_iha_sayisi"]) < int(sartname["min_iha_sayisi"]):
        raise AyarHatasi(
            f"varsayilan_iha_sayisi en az {sartname['min_iha_sayisi']} olmalıdır [5]"
        )

    fov = float(saha["kamera"]["fov_deg"])
    maks_fov = float(sartname["kamera_maks_fov_deg"])
    if fov > maks_fov:
        raise AyarHatasi(f"Kamera FOV ({fov}°) şartname sınırı {maks_fov}°'yi aşamaz [5.1]")

    if float(ucus["setpoint_frekansi_hz"]) <= 0:
        raise AyarHatasi("setpoint_frekansi_hz pozitif olmalıdır")


def ayarlari_yukle(
    ayarlar_dizini: Path | None = None,
    takim_anahtari_gecersiz_kilsin: str | None = None,
) -> Ayarlar:
    """Tüm ayar dosyalarını yükler ve şartname uyumluluğunu doğrular."""
    dizin = ayarlar_dizini or AYARLAR_DIZINI
    kok = dizin.parent

    sartname = _degerleri_cikar(_json_oku(dizin / "sartname.json"), "sartname.json")
    ucus = _degerleri_cikar(_json_oku(dizin / "ucus.json"), "ucus.json")
    ag = _degerleri_cikar(_json_oku(dizin / "ag.json"), "ag.json")
    saha = _degerleri_cikar(_json_oku(dizin / "saha.json"), "saha.json")

    _sartnameyi_dogrula(sartname, ucus, ag, saha)

    if takim_anahtari_gecersiz_kilsin is not None:
        anahtar = takim_anahtari_gecersiz_kilsin
    else:
        anahtar = _takim_anahtarini_bul(ag, kok)

    return Ayarlar(
        sartname=sartname,
        ucus=ucus,
        ag=ag,
        saha=saha,
        takim_anahtari=anahtar,
    )
