"""Ayar yükleme ve şartname doğrulama birim testleri."""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from yazilim.ortak.ayarlar import AyarHatasi, ayarlari_yukle


def test_varsayilan_ayarlar_yuklenir() -> None:
    ayarlar = ayarlari_yukle(takim_anahtari_gecersiz_kilsin="test_anahtar")
    assert ayarlar.sartname["min_irtifa_m"] == 10
    assert ayarlar.sartname["min_iha_sayisi"] == 3
    assert ayarlar.ucus["kalkis_irtifasi_m"] >= 10
    assert ayarlar.saha["kamera"]["fov_deg"] <= 90


def test_sartname_alt_irtifa_ihlali_reddedilir(tmp_path: Path) -> None:
    ayarlar = ayarlari_yukle(takim_anahtari_gecersiz_kilsin="test_anahtar")
    ayar_dizini = tmp_path / "ayarlar"
    ayar_dizini.mkdir()

    for ad, veri in (
        ("sartname.json", ayarlar.sartname),
        ("ucus.json", {**ayarlar.ucus, "kalkis_irtifasi_m": 8.0}),
        ("ag.json", ayarlar.ag),
        ("saha.json", ayarlar.saha),
    ):
        sarili = {k: {"deger": v} for k, v in veri.items()}
        (ayar_dizini / ad).write_text(json.dumps(sarili), encoding="utf-8")

    with pytest.raises(AyarHatasi, match="alt sınırı"):
        ayarlari_yukle(ayarlar_dizini=ayar_dizini, takim_anahtari_gecersiz_kilsin="test")


def test_kamera_fov_90_ustunde_reddedilir(tmp_path: Path) -> None:
    ayarlar = ayarlari_yukle(takim_anahtari_gecersiz_kilsin="test_anahtar")
    ayar_dizini = tmp_path / "ayarlar"
    ayar_dizini.mkdir()

    bozuk_saha = {**ayarlar.saha, "kamera": {**ayarlar.saha["kamera"], "fov_deg": 110.0}}
    for ad, veri in (
        ("sartname.json", ayarlar.sartname),
        ("ucus.json", ayarlar.ucus),
        ("ag.json", ayarlar.ag),
        ("saha.json", bozuk_saha),
    ):
        sarili = {k: {"deger": v} for k, v in veri.items()}
        (ayar_dizini / ad).write_text(json.dumps(sarili), encoding="utf-8")

    with pytest.raises(AyarHatasi, match="FOV"):
        ayarlari_yukle(ayarlar_dizini=ayar_dizini, takim_anahtari_gecersiz_kilsin="test")
