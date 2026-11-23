"""Formasyon geometrisi, N-dron jenerikliği, pitch/roll eğimi ve rotasyon birim testleri."""

from __future__ import annotations

import numpy as np
import pytest

from yazilim.suru.formasyonlar import formasyon_ofsetleri
from yazilim.suru.sanal_yapi import SanalYapi


@pytest.mark.parametrize("formasyon", ["ok_basi", "ok", "v", "cizgi", "l"])
@pytest.mark.parametrize("n", [3, 4, 5])
def test_formasyonlar_n_dron_icin_merkezli(formasyon: str, n: int) -> None:
    ofsetler = formasyon_ofsetleri(formasyon, n, aralik_m=6.0)
    assert ofsetler.shape == (n, 3)
    np.testing.assert_allclose(np.mean(ofsetler, axis=0), [0.0, 0.0, 0.0], atol=1e-9)


def test_pitch_eksi_15_ondeki_alcalir_arkadakiler_yukselir() -> None:
    """Şartname 5.1.2 örneği: -15° pitch okbaşında öndeki alçalır, arkadaki ikisi yükselir."""
    yapi = SanalYapi(
        toplam_iha=3,
        merkez_ned=np.array([0.0, 0.0, -15.0]),
        formasyon_adi="ok_basi",
        aralik_m=6.0,
        pitch_deg=-15.0,
    )
    h1 = yapi.slot_hedefi_ned(1)  # öndeki dron
    h2 = yapi.slot_hedefi_ned(2)  # arka sol
    h3 = yapi.slot_hedefi_ned(3)  # arka sağ

    # NED'de z aşağı olduğu için: -z = irtifa
    assert -h1[2] < 15.0
    assert -h2[2] > 15.0
    assert -h3[2] > 15.0
    # Sürü merkezi sabit kalmalı
    np.testing.assert_allclose((h1 + h2 + h3) / 3.0, [0.0, 0.0, -15.0], atol=1e-9)


def test_formasyon_rotasyonu_goreli_mesafeleri_korur() -> None:
    yapi = SanalYapi(
        toplam_iha=3,
        merkez_ned=np.array([20.0, 10.0, -15.0]),
        formasyon_adi="ok_basi",
        aralik_m=6.0,
        yaw_deg=0.0,
    )
    d12_once = yapi.beklenen_komsu_mesafesi_m(1, 2)
    d23_once = yapi.beklenen_komsu_mesafesi_m(2, 3)

    yapi.yaw_deg = 127.0
    assert yapi.beklenen_komsu_mesafesi_m(1, 2) == pytest.approx(d12_once, abs=1e-9)
    assert yapi.beklenen_komsu_mesafesi_m(2, 3) == pytest.approx(d23_once, abs=1e-9)


def test_ayrilan_dron_kalanlarin_slotunu_degistirmez() -> None:
    """Şartname 5.1: birey ayrılınca kalan sürü formasyonu düzeltmez."""
    yapi = SanalYapi(
        toplam_iha=3,
        merkez_ned=np.array([0.0, 0.0, -15.0]),
        formasyon_adi="cizgi",
        aralik_m=5.0,
    )
    h1_once = yapi.slot_hedefi_ned(1).copy()
    h3_once = yapi.slot_hedefi_ned(3).copy()

    yapi.ayrilan_idleri.add(2)
    np.testing.assert_allclose(yapi.slot_hedefi_ned(1), h1_once)
    np.testing.assert_allclose(yapi.slot_hedefi_ned(3), h3_once)


def test_egimde_taban_koruma_10m_altina_indirmez() -> None:
    yapi = SanalYapi(
        toplam_iha=3,
        merkez_ned=np.array([0.0, 0.0, -10.2]),
        formasyon_adi="ok_basi",
        aralik_m=6.0,
        pitch_deg=-20.0,
    )
    assert yapi.en_alcak_slot_irtifasi_m() < 10.0
    yapi.egim_icin_taban_koru(10.0)
    assert yapi.en_alcak_slot_irtifasi_m() >= 10.0 - 1e-9
