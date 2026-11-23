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


def test_aktif_komsular_adimi_bitirdi_mi_ayrilmis_komsuyu_beklemez() -> None:
    """Ayrık dron uçuşsuz adım atarken komşuların adımı bitirmesini izler; ayrılmış komşuyu beklemez."""
    senkron = DagitimSenkron(kendi_id=2, tum_iha_idleri=[1, 2, 3], komsu_zaman_asimi_s=2.0)
    senkron.komsu_guncelle(
        1, {"konum_ned": [0, 0, -15], "adim": 5, "adim_bitti": False, "ayrilmis": False}, simdi=10.0
    )
    senkron.komsu_guncelle(
        3, {"konum_ned": [5, 0, -15], "adim": 6, "adim_bitti": False, "ayrilmis": False}, simdi=10.0
    )
    # İHA-1 5. adımı henüz bitirmedi
    assert senkron.aktif_komsular_adimi_bitirdi_mi(5, simdi=10.1) is False
    # İHA-1 bitirdi; İHA-3 zaten 6. adıma geçmiş (5'i bitirmiş sayılır)
    senkron.komsu_guncelle(
        1, {"konum_ned": [0, 0, -15], "adim": 5, "adim_bitti": True, "ayrilmis": False}, simdi=10.2
    )
    assert senkron.aktif_komsular_adimi_bitirdi_mi(5, simdi=10.3) is True
    # Geride kalan komşu varsa beklenir (adım sayacı kayması böyle sürüyü bekletmişti)
    senkron.komsu_guncelle(
        3, {"konum_ned": [5, 0, -15], "adim": 4, "adim_bitti": True, "ayrilmis": False}, simdi=10.4
    )
    assert senkron.aktif_komsular_adimi_bitirdi_mi(5, simdi=10.5) is False
    # Ayrılmış komşu beklenmez
    senkron.komsu_guncelle(
        3, {"konum_ned": [5, 0, -15], "adim": 4, "adim_bitti": False, "ayrilmis": True}, simdi=10.6
    )
    assert senkron.aktif_komsular_adimi_bitirdi_mi(5, simdi=10.7) is True


def test_katilim_adiminda_ayrilmis_komsu_beklenir() -> None:
    """Katılım adımında ayrılmış komşu da adımı bitirene kadar beklenir; susarsa canlı listeden düşer."""
    senkron = DagitimSenkron(kendi_id=1, tum_iha_idleri=[1, 2, 3], komsu_zaman_asimi_s=2.0)
    senkron.yeni_adima_gec(7)
    senkron.kendi_adimini_bitir()
    senkron.komsu_guncelle(
        3, {"konum_ned": [5, 0, -15], "adim": 7, "adim_bitti": True, "ayrilmis": False}, simdi=10.0
    )
    # İHA-2 ayrılmış ve hâlâ 6. adımda (uçuşunu bitirmeye çalışıyor)
    senkron.komsu_guncelle(
        2, {"konum_ned": [40, 0, 0], "adim": 6, "adim_bitti": True, "ayrilmis": True}, simdi=10.0
    )
    assert senkron.herkes_adimi_bitirdi_mi(simdi=10.5) is True  # normal adımda ayrılmış beklenmez
    assert senkron.herkes_adimi_bitirdi_mi(simdi=10.5, ayrilmislari_bekle=True) is False
    # İHA-2 slotuna oturup 7. adımı bitirdi
    senkron.komsu_guncelle(
        2, {"konum_ned": [0, 0, -15], "adim": 7, "adim_bitti": True, "ayrilmis": False}, simdi=11.0
    )
    assert senkron.herkes_adimi_bitirdi_mi(simdi=11.1, ayrilmislari_bekle=True) is True
    # İHA-2 sustu: 2.5 sn sonra canlı listeden düşer, sürü kilitlenmez
    senkron.komsu_guncelle(
        3, {"konum_ned": [5, 0, -15], "adim": 7, "adim_bitti": True, "ayrilmis": False}, simdi=15.0
    )
    senkron.komsu_guncelle(
        2, {"konum_ned": [40, 0, 0], "adim": 6, "adim_bitti": True, "ayrilmis": True}, simdi=11.0
    )
    assert senkron.herkes_adimi_bitirdi_mi(simdi=15.1, ayrilmislari_bekle=True) is True
