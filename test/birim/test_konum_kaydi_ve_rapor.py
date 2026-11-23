"""Konum CSV kaydı ve prova raporu hesapları (PX4 gerektirmez)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from yazilim.analiz.prova_raporu import en_dusuk_irtifa, en_yakin_mesafe, inis_sapmasi, kayit_oku, slot_hatasi
from yazilim.ortak.konum_kaydi import FAZ_AYRILMA, FAZ_KALKIS, FAZ_UCUS, KonumKaydi


@dataclass
class _Tel:
    konum_ned: np.ndarray
    hiz_ned: np.ndarray
    yaw_deg: float = 0.0
    havada: bool = True
    arm_durumu: bool = True
    gps_saglikli: bool = True


def _csv_yaz(
    dizin: Path,
    iha_id: int,
    satirlar: list[tuple[str, np.ndarray, np.ndarray | None, bool]],
    adimlar: list[int] | None = None,
):
    """(faz, konum, slot, havada) satırlarını 10 Hz zaman damgasıyla yazıp Kayit olarak geri okur."""
    kayit = KonumKaydi(iha_id, dizin, aralik_s=0.0)
    for sira, (faz, konum, slot, havada) in enumerate(satirlar):
        adim = adimlar[sira] if adimlar else 1
        kayit.yaz(_Tel(konum, np.zeros(3), havada=havada), konum, slot, adim, faz, "test adımı")
    kayit.kapat()
    return kayit_oku(kayit.yol, iha_id)


def test_csv_yazilir_ve_geri_okunur(tmp_path: Path) -> None:
    k = _csv_yaz(tmp_path, 1, [(FAZ_UCUS, np.array([1.0, 2.0, -15.0]), np.array([1.0, 2.0, -15.5]), True)])
    assert k.konum.shape == (1, 3)
    np.testing.assert_allclose(k.konum[0], [1.0, 2.0, -15.0])
    assert k.faz[0] == FAZ_UCUS


def test_slotu_olmayan_satir_nan_olur(tmp_path: Path) -> None:
    k = _csv_yaz(tmp_path, 2, [(FAZ_AYRILMA, np.array([0.0, 0.0, -12.0]), None, True)])
    assert np.isnan(k.slot[0, 0])


def test_en_dusuk_irtifa_yalniz_ucus_fazinda_sayilir(tmp_path: Path) -> None:
    k = _csv_yaz(tmp_path, 1, [
        (FAZ_KALKIS, np.array([0.0, 0.0, -2.0]), None, True),   # kalkış sırasında alçak olması normal
        (FAZ_UCUS, np.array([0.0, 0.0, -14.0]), None, True),
        (FAZ_UCUS, np.array([0.0, 0.0, -11.0]), None, True),
        (FAZ_AYRILMA, np.array([0.0, 0.0, -1.0]), None, True),  # renkli alana iniş muaf
    ])
    irtifa, _ = en_dusuk_irtifa(k)
    assert irtifa == 11.0


def test_en_yakin_mesafe_zamanda_eslestirir(tmp_path: Path) -> None:
    a = _csv_yaz(tmp_path, 1, [(FAZ_UCUS, np.array([0.0, 0.0, -15.0]), None, True)] * 3)
    b = _csv_yaz(tmp_path, 2, [(FAZ_UCUS, np.array([3.0, 4.0, -15.0]), None, True)] * 3)
    mesafe, _, _ = en_yakin_mesafe(a, b, pencere_s=5.0)
    assert abs(mesafe - 5.0) < 1e-9


def test_slot_hatasi_adim_sonu_ornegini_kullanir(tmp_path: Path) -> None:
    """Hareket sırasındaki büyük sapma sayılmaz; her adımın sondan ikinci örneği (kararlı hâl) sayılır."""
    slot = np.array([0.0, 0.0, -15.0])
    k = _csv_yaz(
        tmp_path, 1,
        [(FAZ_UCUS, np.array([50.0, 0.0, -15.0]), slot, True),   # adım 1: hareket (sayılmaz)
         (FAZ_UCUS, np.array([20.0, 0.0, -15.0]), slot, True),
         (FAZ_UCUS, np.array([1.0, 0.0, -15.0]), slot, True),    # adım 1 sondan ikinci: 1 m
         (FAZ_UCUS, np.array([1.0, 0.0, -15.0]), slot, True),
         (FAZ_UCUS, np.array([9.0, 0.0, -15.0]), slot, True),
         (FAZ_UCUS, np.array([2.0, 0.0, -15.0]), slot, True),    # adım 2 sondan ikinci: 2 m
         (FAZ_UCUS, np.array([2.0, 0.0, -15.0]), slot, True)],
        adimlar=[1, 1, 1, 1, 2, 2, 2],
    )
    # adım 2'de 3 örnek var: sondan ikinci 2 m. Adım 1'de 4 örnek: sondan ikinci 1 m.
    ortalama, _, en_buyuk = slot_hatasi(k)
    assert abs(ortalama - 1.5) < 1e-9 and abs(en_buyuk - 2.0) < 1e-9


def test_inis_sapmasi(tmp_path: Path) -> None:
    k = _csv_yaz(tmp_path, 2, [
        (FAZ_UCUS, np.array([1.0, 0.0, -15.0]), np.array([0.0, 0.0, -15.0]), True),
        (FAZ_AYRILMA, np.array([41.0, 1.0, 0.0]), None, False),  # yerde: alan merkezi (40, 0)
    ])
    renk, sapma = inis_sapmasi(k, {"kirmizi": np.array([40.0, 0.0, 0.0])})
    assert renk == "kirmizi"
    assert abs(sapma - 2 ** 0.5) < 1e-9
