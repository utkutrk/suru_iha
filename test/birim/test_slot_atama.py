"""Karışık dizilimde dron -> slot ataması: en kısa toplam yol, determinizm, yol kesişmemesi ve uzlaşma protokolü."""

from __future__ import annotations

import asyncio
import itertools
import logging
import random

import numpy as np
import pytest

from yazilim.ag.mesaj import AgMesaji
from yazilim.ag.udp_tasiyici import Tasiyici
from yazilim.suru.sanal_yapi import SanalYapi
from yazilim.suru.slot_atama import SlotAtamaUzlasmasi, en_kisa_toplam_yol_atamasi

# ok başı, 5 m, merkez (0,0), yaw 0 (kalkış öncesi slotlar)
SLOTLAR = {
    1: np.array([2.887, 0.0, -15.0]),
    2: np.array([-1.443, -2.5, -15.0]),
    3: np.array([-1.443, 2.5, -15.0]),
}


def _ata(dronlar: dict[int, tuple[float, float]], slotlar=SLOTLAR, yuvarlama=1e-6, tercih=0.0):
    konum = {i: np.array([x, y, 0.0]) for i, (x, y) in dronlar.items()}
    return en_kisa_toplam_yol_atamasi(konum, slotlar, yuvarlama, tercih)


def test_provadaki_gercek_konumlar_en_yakin_slotlara_gider() -> None:
    """13:17 provasında dronların yerdeki konumları: İHA-1->2, İHA-2->3, İHA-3->1 (toplam 3,7 m)."""
    atama = _ata({1: (-2.78, -2.81), 2: (-1.58, 1.99), 3: (1.98, -1.55)})
    assert atama == {1: 2, 2: 3, 3: 1}


def test_iki_dron_ayni_slotu_istediginde_cakisma_cozulur() -> None:
    """İHA-1 ve İHA-2 ikisi de slot 2'ye en yakın; slot 3 boş kalmamalı, hiçbir slot iki kez seçilmemeli."""
    atama = _ata({1: (-1.0, -1.0), 2: (-2.0, -3.5), 3: (3.0, 1.0)})
    assert sorted(atama.values()) == [1, 2, 3]
    assert atama == {1: 3, 2: 2, 3: 1}


def test_zaten_yerinde_olan_dronlar_numara_slot_kalir() -> None:
    atama = _ata({1: (2.887, 0.0), 2: (-1.443, -2.5), 3: (-1.443, 2.5)})
    assert atama == {1: 1, 2: 2, 3: 3}


def test_kimlik_tercihi_esitlikte_numarayi_korur() -> None:
    """Dron 2 ve 3'ün slot 2/3'e uzaklığı simetrik: eşitlikte numara = slot kalmalı."""
    atama = _ata({1: (2.887, 0.0), 2: (-1.443, 0.0), 3: (-1.443, 0.0)}, tercih=0.05)
    assert atama == {1: 1, 2: 2, 3: 3}


def _toplam(atama: dict[int, int], konum: dict[int, np.ndarray], slotlar: dict[int, np.ndarray]) -> float:
    return sum(float(np.linalg.norm(konum[i][:2] - slotlar[s][:2])) for i, s in atama.items())


@pytest.mark.parametrize("tohum", range(25))
def test_macar_yontemi_kaba_kuvvetle_ayni_toplami_verir(tohum: int) -> None:
    rng = random.Random(tohum)
    n = 6
    slotlar = {k: np.array([rng.uniform(-10, 10), rng.uniform(-10, 10), -15.0]) for k in range(1, n + 1)}
    konum = {i: np.array([rng.uniform(-10, 10), rng.uniform(-10, 10), 0.0]) for i in range(1, n + 1)}
    atama = en_kisa_toplam_yol_atamasi(konum, slotlar, 1e-9, 0.0)
    en_iyi = min(
        _toplam(dict(zip(range(1, n + 1), p)), konum, slotlar) for p in itertools.permutations(range(1, n + 1))
    )
    assert _toplam(atama, konum, slotlar) == pytest.approx(en_iyi, abs=1e-6)


def _kesisir(a1, a2, b1, b2) -> bool:
    """İki doğru parçasının (düzlemde) gerçekten kesişip kesişmediği."""
    def yon(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    return yon(a1, a2, b1) * yon(a1, a2, b2) < 0 and yon(b1, b2, a1) * yon(b1, b2, a2) < 0


@pytest.mark.parametrize("tohum", range(25))
def test_atamada_duz_yollar_kesismez(tohum: int) -> None:
    rng = random.Random(100 + tohum)
    n = 5
    slotlar = {k: np.array([rng.uniform(-10, 10), rng.uniform(-10, 10), -15.0]) for k in range(1, n + 1)}
    konum = {i: np.array([rng.uniform(-10, 10), rng.uniform(-10, 10), 0.0]) for i in range(1, n + 1)}
    atama = en_kisa_toplam_yol_atamasi(konum, slotlar, 1e-9, 0.0)
    for i, j in itertools.combinations(range(1, n + 1), 2):
        assert not _kesisir(konum[i], slotlar[atama[i]], konum[j], slotlar[atama[j]])


def test_sonuc_sozluk_siralamasindan_bagimsiz() -> None:
    """Her dron konumları kendi sırasıyla toplar; sonuç yine de aynı olmalı (dağıtık tutarlılık)."""
    dronlar = {1: (-2.78, -2.81), 2: (-1.58, 1.99), 3: (1.98, -1.55)}
    sonuclar = {
        tuple(sorted(_ata(dict(sira), yuvarlama=0.5, tercih=0.05).items()))
        for sira in itertools.permutations(dronlar.items())
    }
    assert len(sonuclar) == 1


def test_dron_ve_slot_sayisi_uyusmazsa_hata() -> None:
    with pytest.raises(ValueError):
        _ata({1: (0.0, 0.0), 2: (1.0, 1.0)}, slotlar=SLOTLAR)


# ------------------------------------------------------------------ SanalYapi slot eşlemesi

def _yapi(n: int = 3) -> SanalYapi:
    return SanalYapi(n, np.array([0.0, 0.0, -15.0]), "ok_basi", 5.0)


def test_sanal_yapi_atama_yoksa_numara_slot() -> None:
    yapi = _yapi()
    assert [yapi.slot_no(i) for i in (1, 2, 3)] == [1, 2, 3]


def test_sanal_yapi_atamaya_gore_hedef_verir() -> None:
    yapi = _yapi()
    yapi.atama_ayarla({1: 2, 2: 3, 3: 1})
    np.testing.assert_allclose(yapi.slot_hedefi_ned(1), yapi.slot_no_hedefi_ned(2))
    np.testing.assert_allclose(yapi.slot_hedefi_ned(3), yapi.slot_no_hedefi_ned(1))


def test_sanal_yapi_bire_bir_olmayan_atamayi_reddeder() -> None:
    with pytest.raises(ValueError):
        _yapi().atama_ayarla({1: 2, 2: 2, 3: 1})


# ------------------------------------------------------------------ uzlaşma protokolü (bellek içi ağ)

class _BellekAgi:
    """Test için bellek içi ağ: bir ajanın yayını diğerlerinin dinleyicilerine anında ulaşır."""

    def __init__(self) -> None:
        self.tasiyicilar: dict[int, "_BellekTasiyici"] = {}


class _BellekTasiyici(Tasiyici):
    def __init__(self, ag: _BellekAgi, iha_id: int) -> None:
        self._ag, self._id = ag, iha_id
        self._dinleyiciler = []
        self._sira = 0
        ag.tasiyicilar[iha_id] = self

    async def baslat(self) -> None: ...
    async def kapat(self) -> None: ...

    def yayinla(self, tip, veri) -> None:
        self._sira += 1
        mesaj = AgMesaji(1, tip, self._id, self._sira, 0.0, veri)
        for kimlik, t in self._ag.tasiyicilar.items():
            if kimlik != self._id:
                for d in t._dinleyiciler:
                    d(mesaj)

    def mesaj_dinleyici_ekle(self, geri_cagrim) -> None:
        self._dinleyiciler.append(geri_cagrim)


def _uzlasma_calistir(konumlar_per_dron: dict[int, dict[int, tuple[float, float]]], zaman_asimi=0.3):
    """Her dron kendi gördüğü konumlarla belirle() çalıştırır; sonuçları döndürür."""
    ag = _BellekAgi()
    n = 3
    nesneler = {
        i: SlotAtamaUzlasmasi(i, n, _BellekTasiyici(ag, i), logging.getLogger(f"test.uzlasma{i}"), 0.01, zaman_asimi)
        for i in konumlar_per_dron
    }

    async def calis():
        return await asyncio.gather(*[
            nesneler[i].belirle(
                {k: np.array([x, y, 0.0]) for k, (x, y) in konumlar_per_dron[i].items()}, SLOTLAR, 0.5, 0.05
            )
            for i in nesneler
        ])

    return dict(zip(nesneler, asyncio.run(calis())))


KONUMLAR = {1: (-2.78, -2.81), 2: (-1.58, 1.99), 3: (1.98, -1.55)}


def test_uzlasma_hepsi_ayni_konumu_gorurse_ayni_atamayi_kullanir() -> None:
    sonuc = _uzlasma_calistir({1: KONUMLAR, 2: KONUMLAR, 3: KONUMLAR})
    assert all(a == {1: 2, 2: 3, 3: 1} for a in sonuc.values())


def test_uzlasma_farkli_oneri_varsa_herkes_numara_slota_doner() -> None:
    """Bir dron komşusunu çok farklı yerde sanırsa öneriler ayrışır; güvenli yol: slot = numara."""
    sapmis = {**KONUMLAR, 3: (-1.5, 2.5)}  # İHA-3'ü kendi slotunda sanıyor
    sonuc = _uzlasma_calistir({1: KONUMLAR, 2: KONUMLAR, 3: sapmis})
    assert all(a == {1: 1, 2: 2, 3: 3} for a in sonuc.values())


def test_uzlasma_susan_komsuda_zaman_asimiyla_numara_slota_doner() -> None:
    """İHA-3 hiç öneri yayınlamazsa (ağda yok) diğerleri kilitlenmez, zaman aşımıyla numara = slot olur."""
    sonuc = _uzlasma_calistir({1: KONUMLAR, 2: KONUMLAR})
    assert all(a == {1: 1, 2: 2, 3: 3} for a in sonuc.values())


def test_uzlasma_konumu_bilinmeyen_dron_varsa_numara_slot() -> None:
    eksik = {1: KONUMLAR[1], 2: KONUMLAR[2]}
    sonuc = _uzlasma_calistir({1: eksik, 2: eksik, 3: eksik})
    assert all(a == {1: 1, 2: 2, 3: 3} for a in sonuc.values())
