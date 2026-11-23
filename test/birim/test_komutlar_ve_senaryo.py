"""QR JSON ayrıştırma (Şekil 2) ve tablo tabanlı komut uygulama birim testleri."""

from __future__ import annotations

import asyncio
import numpy as np
import pytest

from yazilim.gorevler.komut_kaynagi import SenaryoKomutKaynagi, qr_json_ayristir
from yazilim.ortak.ayarlar import PROJE_KOKU
from yazilim.suru.komutlar import komut_uygula
from yazilim.suru.sanal_yapi import SanalYapi


def test_sekil2_qr_ayristirma_yalniz_kendi_takim_id() -> None:
    ham = {
        "qr": 1,
        "w": 4,
        "mis": [
            [["frm", "ok", 6], ["mnv", -10, 0], ["alt", 20]],
            [["frm", "v", 8], ["mnv", 0, 10], ["alt", 25]],
        ],
        "team": {"1": [1, 4], "2": [2, 5]},
    }
    p1 = qr_json_ayristir(ham, takim_id="1", varsayilan_bekleme_s=3.0)
    assert p1.qr_no == 1
    assert p1.bekleme_s == 4.0
    assert p1.sonraki_qr == 4
    assert p1.komutlar[0] == ["frm", "ok", 6]

    p2 = qr_json_ayristir(ham, takim_id="2", varsayilan_bekleme_s=3.0)
    assert p2.sonraki_qr == 5
    assert p2.komutlar[0] == ["frm", "v", 8]


def test_komut_tablosu_sirali_uygulama() -> None:
    yapi = SanalYapi(
        toplam_iha=3,
        merkez_ned=np.array([0.0, 0.0, -15.0]),
        formasyon_adi="ok_basi",
        aralik_m=5.0,
    )
    sinirlar = {"min_irtifa_m": 10.0, "maks_irtifa_m": 35.0, "maks_egim_acisi_deg": 25.0}

    e1 = komut_uygula(["frm", "v", 7], yapi, sinirlar)
    assert e1.formasyon_degisti is True
    assert yapi.formasyon_adi == "v"
    assert yapi.aralik_m == 7.0

    komut_uygula(["mnv", -10, 5], yapi, sinirlar)
    assert yapi.pitch_deg == -10.0
    assert yapi.roll_deg == 5.0

    # Alt irtifa sınırı 10 m zorunlu [5.1]
    komut_uygula(["alt", 5], yapi, sinirlar)
    assert yapi.en_alcak_slot_irtifasi_m() >= 10.0 - 1e-9

    e4 = komut_uygula(["cikar", 2, "kirmizi"], yapi, sinirlar)
    assert e4.ayrilacak_iha_id == 2
    assert e4.inis_rengi == "kirmizi"
    assert 2 in yapi.ayrilan_idleri


def test_ornek_senaryo_dosyasi_okunur() -> None:
    kaynak = SenaryoKomutKaynagi(
        senaryo_yolu=PROJE_KOKU / "senaryolar" / "gorev1_ornek.json",
        takim_id="1",
        varsayilan_bekleme_s=4.0,
    )
    qr = kaynak.baslangic_qr_no()
    ziyaret = []
    while qr != 0:
        paket = asyncio.run(kaynak.qr_gorevini_oku(qr))
        ziyaret.append(paket.qr_no)
        qr = paket.sonraki_qr
    assert ziyaret == [1, 4, 2, 3, 5]
