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


# ---------------------------------------------------------------- rotasyon adımları (yay üzerinde dönüş)

from yazilim.ortak.koordinat import yaw_ara_adimlari


def test_yaw_ara_adimlari_hedefle_biter_ve_adim_asmaz() -> None:
    adimlar = yaw_ara_adimlari(53.1, 160.0, 15.0)
    assert adimlar[-1] == pytest.approx(160.0)
    onceki = 53.1
    for a in adimlar:
        assert abs(a - onceki) <= 15.0 + 1e-9
        onceki = a


def test_yaw_ara_adimlari_en_kisa_yonden_doner() -> None:
    # 170° -> -170° en kısa yol +20° (artı yönde, 180'i geçerek); 340° dönmemeli
    adimlar = yaw_ara_adimlari(170.0, -170.0, 15.0)
    assert len(adimlar) == 2
    assert adimlar[-1] == pytest.approx(-170.0)


def test_yaw_ara_adimlari_fark_sifirsa_tek_adim() -> None:
    assert yaw_ara_adimlari(45.0, 45.0, 15.0) == [pytest.approx(45.0)]


def _slotlar(yaw: float, n: int = 3, aralik: float = 6.0) -> np.ndarray:
    yapi = SanalYapi(n, np.array([0.0, 0.0, -18.0]), "ok_basi", aralik, yaw_deg=yaw, pitch_deg=10.0)
    return np.array([yapi.slot_hedefi_ned(i) for i in range(1, n + 1)])


def _en_kucuk_komsu_mesafesi(yawlar: list[float], adim_sayisi: int = 100) -> float:
    """Slotlar ardışık yaw'lar arasında düz çizgiyle yer değiştirirken komşular arası en küçük mesafe."""
    en_kucuk = float("inf")
    for y0, y1 in zip(yawlar[:-1], yawlar[1:]):
        a, b = _slotlar(y0), _slotlar(y1)
        for t in np.linspace(0.0, 1.0, adim_sayisi):
            p = a * (1 - t) + b * t
            for i in range(len(p)):
                for j in range(i + 1, len(p)):
                    en_kucuk = min(en_kucuk, float(np.linalg.norm(p[i] - p[j])))
    return en_kucuk


def test_rotasyon_kucuk_adimlarla_komsu_mesafesi_korunur() -> None:
    """Provadaki 53°->160° rotasyonu: tek hamle komşuları yaklaştırır, 15°'lik adımlar yaklaştırmaz."""
    tek_hamle = _en_kucuk_komsu_mesafesi([53.1, 160.0])
    adimli = _en_kucuk_komsu_mesafesi([53.1, *yaw_ara_adimlari(53.1, 160.0, 15.0)])
    assert tek_hamle < 4.0  # 6 m aralık düz çizgide yaklaşık 3.6 m'ye iner
    assert adimli > 5.5  # yay üzerinde aralık neredeyse korunur


# ---------------------------------------------------------------- geri katılımda yukarıdan yaklaşma

from yazilim.ortak.koordinat import yukaridan_yaklasma_noktalari


def _yol_en_yakin_mesafe(noktalar: list[np.ndarray], diger: np.ndarray, adim: int = 400) -> float:
    """Kırık çizgi yolun bir noktaya 3B en yakın uzaklığı."""
    en_kucuk = float("inf")
    for a, b in zip(noktalar[:-1], noktalar[1:]):
        for t in np.linspace(0.0, 1.0, adim):
            en_kucuk = min(en_kucuk, float(np.linalg.norm(a * (1 - t) + b * t - diger)))
    return en_kucuk


def test_yaklasma_noktalari_once_yuksel_sonra_slotun_ustune_gider() -> None:
    mevcut = np.array([39.3, -0.9, -17.4])
    hedef = np.array([63.0, -21.7, -17.5])
    yuksel, ust = yukaridan_yaklasma_noktalari(mevcut, hedef, 4.0)
    np.testing.assert_allclose(yuksel, [39.3, -0.9, -21.5])  # yerinde 4 m üstüne (NED'de z azalır)
    np.testing.assert_allclose(ust, [63.0, -21.7, -21.5])


def test_yaklasma_zaten_yuksekteyse_alcalmaz() -> None:
    yuksel, _ = yukaridan_yaklasma_noktalari(np.array([0.0, 0.0, -30.0]), np.array([10.0, 0.0, -15.0]), 4.0)
    assert yuksel[2] == -30.0


def test_yukaridan_yaklasma_formasyonun_icinden_gecerken_dikey_ayrim_saglar() -> None:
    """14:01 provasındaki geri katılış: ölçülen iz komşulara < 3 m yaklaşır, üstten yaklaşma ≥ 3 m uzak tutar.

    Ölçülen iz İHA-2'nin gerçek konum kaydından (yaklaşık 1,5 sn aralıkla) alındı; komşular o anki yerlerinde
    (İHA-1 ve İHA-3) sabit kabul edildi, bu yüzden gerçek en küçük mesafe (1,94 m) bu durağan hesaptan da küçüktür.
    """
    olculen_iz = [np.array(p) for p in [
        (39.3, -0.9, -17.4), (47.0, -7.7, -17.5), (53.8, -13.6, -17.5), (57.2, -16.6, -17.5),
        (59.1, -20.3, -17.5), (61.7, -23.4, -17.5), (63.9, -22.1, -17.4),
    ]]
    slot = np.array([63.0, -21.7, -17.5])
    komsular = [np.array([57.0, -21.7, -18.5]), np.array([60.0, -16.5, -18.5])]  # İHA-1 ve İHA-3
    ustten = [olculen_iz[0], *yukaridan_yaklasma_noktalari(olculen_iz[0], slot, 4.0)]
    for komsu in komsular:
        assert _yol_en_yakin_mesafe(olculen_iz, komsu) < 3.0
        assert _yol_en_yakin_mesafe(ustten, komsu) >= 3.0
