"""Ağ mesaj güvenlik süzgeci ve dağıtık senkronizasyon (susan komşu kilitlemez) testleri."""

from __future__ import annotations

import numpy as np

from yazilim.ag.mesaj import MesajKodlayici
from yazilim.suru.senkron import DagitimSenkron


def test_mesaj_dogrulama_bayat_ve_yanlis_anahtar() -> None:
    gonderici = MesajKodlayici(protokol_surumu=1, takim_anahtari="sir_123", maks_mesaj_yasi_s=2.0)
    alici = MesajKodlayici(protokol_surumu=1, takim_anahtari="sir_123", maks_mesaj_yasi_s=2.0)
    yabanci = MesajKodlayici(protokol_surumu=1, takim_anahtari="baska", maks_mesaj_yasi_s=2.0)

    paket = gonderici.paketle("DURUM", gonderen=1, veri={"adim": 1}, simdi=1000.0)

    # Geçerli paket kabul edilir
    cozulen = alici.coz(paket, simdi=1000.5)
    assert cozulen is not None
    assert cozulen.gonderen == 1
    assert cozulen.veri["adim"] == 1

    # Aynı sıra no tekrarlanırsa reddedilir (anti-replay)
    assert alici.coz(paket, simdi=1000.6) is None

    # Yanlış takım anahtarı reddedilir
    assert yabanci.coz(paket, simdi=1000.5) is None

    # Bayat paket reddedilir
    paket2 = gonderici.paketle("DURUM", gonderen=1, veri={"adim": 2}, simdi=1000.0)
    assert alici.coz(paket2, simdi=1005.0) is None

    # Bozuk JSON reddedilir
    assert alici.coz(b"{bozuk", simdi=1000.5) is None


def test_senkron_susan_komsuyu_bekleyip_kilitlenmez() -> None:
    senkron = DagitimSenkron(kendi_id=1, tum_iha_idleri=[1, 2, 3], komsu_zaman_asimi_s=2.0)
    senkron.yeni_adima_gec(1)
    senkron.kendi_adimini_bitir()

    # İHA-2 bitirdi, İHA-3 henüz bitirmedi (t=10.0)
    senkron.komsu_guncelle(
        2, {"konum_ned": [0, 0, -15], "adim": 1, "adim_bitti": True, "ayrilmis": False}, simdi=10.0
    )
    senkron.komsu_guncelle(
        3, {"konum_ned": [5, 0, -15], "adim": 1, "adim_bitti": False, "ayrilmis": False}, simdi=10.0
    )
    assert senkron.herkes_adimi_bitirdi_mi(simdi=10.5) is False

    # İHA-3 sustu/düştü (t=13.0 -> 2 sn zaman aşımı geçti); İHA-2 hâlâ canlı
    senkron.komsu_guncelle(
        2, {"konum_ned": [0, 0, -15], "adim": 1, "adim_bitti": True, "ayrilmis": False}, simdi=12.5
    )
    assert senkron.herkes_adimi_bitirdi_mi(simdi=13.0) is True
    assert senkron.aktif_iha_sayisi(simdi=13.0) == 2


def test_senkron_ayrilan_komsuyu_beklemez() -> None:
    senkron = DagitimSenkron(kendi_id=1, tum_iha_idleri=[1, 2, 3], komsu_zaman_asimi_s=2.0)
    senkron.yeni_adima_gec(2)
    senkron.kendi_adimini_bitir()

    senkron.komsu_guncelle(
        2, {"konum_ned": [0, 0, -15], "adim": 2, "adim_bitti": False, "ayrilmis": True}, simdi=20.0
    )
    senkron.komsu_guncelle(
        3, {"konum_ned": [5, 0, -15], "adim": 2, "adim_bitti": True, "ayrilmis": False}, simdi=20.0
    )
    assert senkron.herkes_adimi_bitirdi_mi(simdi=20.1) is True
