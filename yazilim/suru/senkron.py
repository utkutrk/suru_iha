"""Dağıtık komşu takibi ve adım adım bariyer senkronizasyonu (susan komşu sürüyü kilitlemez)."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
import numpy as np


@dataclass
class KomsuDurumu:
    """Bir komşu dronun son alınan durum özeti."""

    iha_id: int
    konum_ned: np.ndarray
    adim: int
    adim_bitti: bool
    ayrilmis: bool
    son_gorulme_s: float
    gps_saglikli: bool = True
    kesfedilen_renkler: dict[str, list[float]] = field(default_factory=dict)


class DagitimSenkron:
    """Lidersiz adım bariyeri ve kayıp komşu tespiti."""

    def __init__(
        self,
        kendi_id: int,
        tum_iha_idleri: list[int],
        komsu_zaman_asimi_s: float,
    ) -> None:
        self._kendi_id = kendi_id
        self._tum_idleri = list(tum_iha_idleri)
        self._zaman_asimi = komsu_zaman_asimi_s
        self._komsular: dict[int, KomsuDurumu] = {}
        self._mevcut_adim = 0
        self._kendi_adim_bitti = False
        self._kendi_ayrilmis = False
        self._bilinen_renkli_alanlar: dict[str, np.ndarray] = {}

    @property
    def mevcut_adim(self) -> int:
        return self._mevcut_adim

    def yeni_adima_gec(self, adim: int) -> None:
        self._mevcut_adim = adim
        self._kendi_adim_bitti = False

    def kendi_adimini_bitir(self) -> None:
        self._kendi_adim_bitti = True

    def kendi_ayrilma_durumu_ayarla(self, ayrilmis: bool) -> None:
        self._kendi_ayrilmis = ayrilmis

    def renkli_alan_kaydet(self, renk: str, konum_ned: np.ndarray) -> None:
        """Rota üzerinde keşfedilen renkli alanın konumunu kaydeder (diğer dronlarla paylaşılır)."""
        self._bilinen_renkli_alanlar[renk.lower()] = np.asarray(konum_ned, dtype=float).copy()

    def renkli_alan_al(self, renk: str) -> np.ndarray | None:
        konum = self._bilinen_renkli_alanlar.get(renk.lower())
        return None if konum is None else konum.copy()

    def bilinen_renkli_alanlar_sozluk(self) -> dict[str, list[float]]:
        return {k: v.tolist() for k, v in self._bilinen_renkli_alanlar.items()}

    def durum_paketi_olustur(self, konum_ned: np.ndarray, gps_saglikli: bool) -> dict[str, object]:
        """Diğer dronlara UDP ile yayınlanacak durum sözlüğünü hazırlar."""
        return {
            "konum_ned": [round(float(c), 3) for c in konum_ned],
            "adim": self._mevcut_adim,
            "adim_bitti": self._kendi_adim_bitti,
            "ayrilmis": self._kendi_ayrilmis,
            "gps_saglikli": gps_saglikli,
            "renkler": self.bilinen_renkli_alanlar_sozluk(),
        }

    def komsu_guncelle(
        self,
        gonderen_id: int,
        veri: dict[str, object],
        simdi: float | None = None,
    ) -> None:
        """Gelen DURUM mesajıyla komşu tablosunu ve paylaşılan renkli alanları günceller."""
        if gonderen_id == self._kendi_id:
            return
        ts = time.monotonic() if simdi is None else simdi
        konum = np.asarray(veri.get("konum_ned", [0.0, 0.0, 0.0]), dtype=float)
        if konum.shape != (3,):
            return

        renkler = veri.get("renkler", {})
        if isinstance(renkler, dict):
            for renk, k in renkler.items():
                if isinstance(k, list) and len(k) == 3 and renk not in self._bilinen_renkli_alanlar:
                    self._bilinen_renkli_alanlar[str(renk).lower()] = np.asarray(k, dtype=float)

        self._komsular[gonderen_id] = KomsuDurumu(
            iha_id=gonderen_id,
            konum_ned=konum,
            adim=int(veri.get("adim", 0)),  # type: ignore[arg-type]
            adim_bitti=bool(veri.get("adim_bitti", False)),
            ayrilmis=bool(veri.get("ayrilmis", False)),
            son_gorulme_s=ts,
            gps_saglikli=bool(veri.get("gps_saglikli", True)),
        )

    def canli_komsular(self, simdi: float | None = None) -> dict[int, KomsuDurumu]:
        """Zaman aşımına uğramamış (hayatta) komşuları döndürür."""
        ts = time.monotonic() if simdi is None else simdi
        return {
            cid: durum
            for cid, durum in self._komsular.items()
            if (ts - durum.son_gorulme_s) <= self._zaman_asimi
        }

    def komsu_konumlari(self, simdi: float | None = None) -> dict[int, np.ndarray]:
        """Çarpışma önleme için canlı komşuların son NED konumlarını döndürür."""
        return {cid: d.konum_ned.copy() for cid, d in self.canli_komsular(simdi).items()}

    def aktif_iha_sayisi(self, simdi: float | None = None) -> int:
        """Kendisi + canlı komşuların toplam sayısı (Tablo 7 minimum İHA takibi için)."""
        return 1 + len(self.canli_komsular(simdi))

    def herkes_adimi_bitirdi_mi(self, simdi: float | None = None) -> bool:
        """Aktif (canlı ve ayrılmamış) tüm komşular mevcut adımı bitirdiyse True döner.

        Susan/düşen komşu canlı listeden düştüğü için sürüyü asla kilitlemez.
        """
        if not self._kendi_adim_bitti:
            return False
        for durum in self.canli_komsular(simdi).values():
            if durum.ayrilmis:
                continue
            # Komşu ya mevcut adımı bitirmiş ya da bir sonraki adıma geçmiş olmalı
            if durum.adim < self._mevcut_adim:
                return False
            if durum.adim == self._mevcut_adim and not durum.adim_bitti:
                return False
        return True
