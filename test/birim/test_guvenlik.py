"""Güvenlik son kapısı: 10 m taban, geofence, hız rampası, çarpışma itmesi ve GPS tutarlılığı."""

from __future__ import annotations

import logging
import numpy as np

from yazilim.guvenlik.son_kapi import GuvenlikKapisi
from yazilim.ortak.ayarlar import ayarlari_yukle


def _kapi_kur() -> GuvenlikKapisi:
    ayarlar = ayarlari_yukle(takim_anahtari_gecersiz_kilsin="test")
    return GuvenlikKapisi(iha_id=1, ayarlar=ayarlar, logger=logging.getLogger("test.guvenlik"))


def test_10m_taban_korunur() -> None:
    kapi = _kapi_kur()
    kapi.sifirla(np.array([0.0, 0.0, -10.5]), 0.0)
    guvenli, _ = kapi.hedefi_suz(
        ham_hedef_ned=np.array([0.0, 0.0, -4.0]),
        ham_yaw_deg=0.0,
        mevcut_ned=np.array([0.0, 0.0, -10.5]),
        komsu_konumlari={},
        dt_s=1.0,
        taban_aktif=True,
    )
    assert guvenli[2] <= -10.0


def test_carpisma_itmesi_yakin_komsudan_uzaklastirir() -> None:
    kapi = _kapi_kur()
    mevcut = np.array([0.0, 0.0, -15.0])
    kapi.sifirla(mevcut, 0.0)
    # Komşu 1 m kuzeyde (+x); itme güneye (-x) olmalı
    guvenli, _ = kapi.hedefi_suz(
        ham_hedef_ned=mevcut,
        ham_yaw_deg=0.0,
        mevcut_ned=mevcut,
        komsu_konumlari={2: np.array([1.0, 0.0, -15.0])},
        dt_s=0.1,
    )
    assert guvenli[0] < 0.0


def test_geofence_sinirlari_korunur() -> None:
    kapi = _kapi_kur()
    kapi.sifirla(np.array([119.0, 0.0, -15.0]), 0.0)
    guvenli, _ = kapi.hedefi_suz(
        ham_hedef_ned=np.array([500.0, 0.0, -15.0]),
        ham_yaw_deg=0.0,
        mevcut_ned=np.array([119.0, 0.0, -15.0]),
        komsu_konumlari={},
        dt_s=1.0,
    )
    assert guvenli[0] <= 120.0


def test_gps_tutarlilik_sapmada_uyari_verir() -> None:
    kapi = _kapi_kur()
    uyarilar = kapi.gps_tutarlilik_kontrolu(
        mevcut_ned=np.array([0.0, 0.0, -15.0]),
        komsu_konumlari={2: np.array([12.0, 0.0, -15.0])},
        beklenen_mesafeler={2: 5.0},
    )
    assert len(uyarilar) == 1


def test_kritik_yakinlik_logu_sinirlanir(caplog) -> None:
    """Aynı komşu için 'Kritik yakınlık' uyarısı her döngüde değil, aralıkla yazılır."""
    kapi = _kapi_kur()
    mevcut = np.array([0.0, 0.0, -15.0])
    kapi.sifirla(mevcut, 0.0)
    with caplog.at_level(logging.WARNING, logger="test.guvenlik"):
        for _ in range(50):
            kapi.hedefi_suz(
                ham_hedef_ned=mevcut, ham_yaw_deg=0.0, mevcut_ned=mevcut,
                komsu_konumlari={2: np.array([1.0, 0.0, -15.0])}, dt_s=0.05,
            )
    kritikler = [k for k in caplog.records if "Kritik yakınlık" in k.getMessage()]
    assert len(kritikler) == 1
