"""Tüm görev komutları tek dosyada, tablo tabanlı (if/elif zinciri olmadan) tanımlanır."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from yazilim.suru.formasyonlar import kanonik_formasyon_adi
from yazilim.suru.sanal_yapi import SanalYapi


@dataclass(frozen=True)
class KomutEtkisi:
    """Bir komutun sanal yapı ve uçuş akışı üzerindeki yan etkisini tanımlar."""

    aciklama: str
    formasyon_degisti: bool = False
    ayrilacak_iha_id: int | None = None
    inis_rengi: str | None = None
    ek_bekleme_s: float | None = None


def _cmd_formasyon(yapi: SanalYapi, arglar: list[Any], sinirlar: dict[str, float]) -> KomutEtkisi:
    """Formasyon ve aralık değiştirir. Şartname 5.1: yeni formasyon önceki eğimi sıfırlar."""
    if len(arglar) < 2:
        raise ValueError(f"'frm' komutu 2 argüman bekler [tip, aralik_m], gelen: {arglar}")
    yeni_tip = kanonik_formasyon_adi(str(arglar[0]))
    yeni_aralik = float(arglar[1])
    if yeni_aralik <= 0:
        raise ValueError(f"Formasyon aralığı pozitif olmalıdır: {yeni_aralik}")
    yapi.formasyon_adi = yeni_tip
    yapi.aralik_m = yeni_aralik
    yapi.pitch_deg = 0.0
    yapi.roll_deg = 0.0
    return KomutEtkisi(
        aciklama=f"Formasyon -> {yeni_tip} ({yeni_aralik:.1f} m)",
        formasyon_degisti=True,
    )


def _cmd_manevra(yapi: SanalYapi, arglar: list[Any], sinirlar: dict[str, float]) -> KomutEtkisi:
    """Sürü merkezi sabit kalacak şekilde pitch/roll eğimi uygular."""
    if len(arglar) < 2:
        raise ValueError(f"'mnv' komutu 2 argüman bekler [pitch_deg, roll_deg], gelen: {arglar}")
    maks_egim = float(sinirlar["maks_egim_acisi_deg"])
    pitch = max(-maks_egim, min(maks_egim, float(arglar[0])))
    roll = max(-maks_egim, min(maks_egim, float(arglar[1])))
    yapi.pitch_deg = pitch
    yapi.roll_deg = roll
    # Eğimde en alçak dronun 10 m tabanını ihlal etmesini önle
    yapi.egim_icin_taban_koru(float(sinirlar["min_irtifa_m"]))
    return KomutEtkisi(aciklama=f"Manevra -> pitch={pitch:.1f}°, roll={roll:.1f}°")


def _cmd_irtifa(yapi: SanalYapi, arglar: list[Any], sinirlar: dict[str, float]) -> KomutEtkisi:
    """Sürünün merkez irtifasını değiştirir (alt ve üst sınırlar korunarak)."""
    if len(arglar) < 1:
        raise ValueError(f"'alt' komutu 1 argüman bekler [irtifa_m], gelen: {arglar}")
    min_irtifa = float(sinirlar["min_irtifa_m"])
    maks_irtifa = float(sinirlar["maks_irtifa_m"])
    hedef_irtifa = max(min_irtifa, min(maks_irtifa, float(arglar[0])))
    yapi.merkez_ned[2] = -hedef_irtifa
    yapi.egim_icin_taban_koru(min_irtifa)
    return KomutEtkisi(aciklama=f"İrtifa -> {hedef_irtifa:.1f} m")


def _cmd_birey_cikar(yapi: SanalYapi, arglar: list[Any], sinirlar: dict[str, float]) -> KomutEtkisi:
    """Belirtilen İHA'yı renkli alana inmek üzere sürüden ayırır; kalan sürü formasyonu bozmaz."""
    if len(arglar) < 2:
        raise ValueError(f"'cikar' komutu 2 argüman bekler [iha_id, renk], gelen: {arglar}")
    hedef_id = int(arglar[0])
    renk = str(arglar[1]).strip().lower()
    if not (1 <= hedef_id <= yapi.toplam_iha):
        raise ValueError(f"Geçersiz ayrılacak İHA ID: {hedef_id}")
    yapi.ayrilan_idleri.add(hedef_id)
    return KomutEtkisi(
        aciklama=f"Birey çıkarma -> İHA-{hedef_id} ({renk} alan)",
        ayrilacak_iha_id=hedef_id,
        inis_rengi=renk,
    )


def _cmd_bekle(yapi: SanalYapi, arglar: list[Any], sinirlar: dict[str, float]) -> KomutEtkisi:
    """İsteğe bağlı açık bekleme komutu."""
    sure = float(arglar[0]) if arglar else 0.0
    return KomutEtkisi(aciklama=f"Bekle -> {sure:.1f} s", ek_bekleme_s=max(0.0, sure))


# Yeni komut eklemek için yalnız yukarıya fonksiyon yazıp bu tabloya eklemek yeterlidir
KomutFn = Callable[[SanalYapi, list[Any], dict[str, float]], KomutEtkisi]

KOMUTLAR: dict[str, KomutFn] = {
    "frm": _cmd_formasyon,
    "formasyon": _cmd_formasyon,
    "mnv": _cmd_manevra,
    "manevra": _cmd_manevra,
    "alt": _cmd_irtifa,
    "irtifa": _cmd_irtifa,
    "cikar": _cmd_birey_cikar,
    "rem": _cmd_birey_cikar,
    "bekle": _cmd_bekle,
    "wait": _cmd_bekle,
}


def komut_uygula(
    komut_satiri: list[Any],
    yapi: SanalYapi,
    sinirlar: dict[str, float],
) -> KomutEtkisi:
    """QR/senaryo komut satırını (ör. ['frm', 'ok', 6]) tablodan bulup sanal yapıya uygular."""
    if not komut_satiri:
        raise ValueError("Boş komut satırı")
    ad = str(komut_satiri[0]).strip().lower()
    fn = KOMUTLAR.get(ad)
    if fn is None:
        raise ValueError(f"Bilinmeyen komut: '{ad}'. Desteklenenler: {sorted(KOMUTLAR.keys())}")
    return fn(yapi, list(komut_satiri[1:]), sinirlar)
