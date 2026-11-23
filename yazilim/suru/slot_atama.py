"""Karışık dizilimde dron -> slot eşlemesi: toplam yolu en kısa yapan bire bir atama (lidersiz, herkes aynı hesabı yapar).

Neden: slot = dron numarası olursa, hakemlerin karışık dizdiği dronlar kendi slotuna giderken birbirinin yolunu
keser. Toplam uzaklığı en aza indiren eşleşmede düz çizgi yolları düzlemde kesişmez.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import numpy as np

from yazilim.ag.mesaj import AgMesaji
from yazilim.ag.udp_tasiyici import Tasiyici


def _macar_yontemi(maliyet: list[list[float]]) -> list[int]:
    """Kare maliyet matrisinde toplam maliyeti en küçük bire bir eşleşmeyi (satır -> sütun) bulur (O(n^3))."""
    n = len(maliyet)
    sonsuz = float("inf")
    u = [0.0] * (n + 1)
    v = [0.0] * (n + 1)
    p = [0] * (n + 1)
    yol = [0] * (n + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [sonsuz] * (n + 1)
        kullanildi = [False] * (n + 1)
        while True:
            kullanildi[j0] = True
            i0, delta, j1 = p[j0], sonsuz, 0
            for j in range(1, n + 1):
                if not kullanildi[j]:
                    mevcut = maliyet[i0 - 1][j - 1] - u[i0] - v[j]
                    if mevcut < minv[j]:
                        minv[j], yol[j] = mevcut, j0
                    if minv[j] < delta:
                        delta, j1 = minv[j], j
            for j in range(n + 1):
                if kullanildi[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = yol[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    sonuc = [0] * n
    for j in range(1, n + 1):
        sonuc[p[j] - 1] = j - 1
    return sonuc


def en_kisa_toplam_yol_atamasi(
    dron_konumlari: dict[int, np.ndarray],
    slot_konumlari: dict[int, np.ndarray],
    yuvarlama_m: float,
    kimlik_tercihi_m: float,
) -> dict[int, int]:
    """Her dronu (iha_id) bir slota (slot_no) eşler; yalnız yatay uzaklık sayılır.

    - Konumlar yuvarlama_m ızgarasına yuvarlanır: dronların GPS'indeki santimetrelik fark kararı değiştirmesin.
    - Kimlik tercihi: slot_no == iha_id eşleşmesi kimlik_tercihi_m kadar "bedava" sayılır; gerçek eşitlikte
      (veya çok az kazançta) numara = slot korunur, kararlı ve tahmin edilebilir kalır.
    """
    idler = sorted(dron_konumlari)
    slotlar = sorted(slot_konumlari)
    if len(idler) != len(slotlar):
        raise ValueError(f"Dron sayısı ({len(idler)}) slot sayısına ({len(slotlar)}) eşit olmalıdır")
    if yuvarlama_m <= 0:
        raise ValueError("yuvarlama_m pozitif olmalıdır")

    def yuvarla(nokta: np.ndarray) -> np.ndarray:
        return np.round(np.asarray(nokta, dtype=float)[:2] / yuvarlama_m) * yuvarlama_m

    maliyet = [
        [
            float(np.linalg.norm(yuvarla(dron_konumlari[i]) - yuvarla(slot_konumlari[s])))
            - (kimlik_tercihi_m if i == s else 0.0)
            for s in slotlar
        ]
        for i in idler
    ]
    sutunlar = _macar_yontemi(maliyet)
    return {idler[satir]: slotlar[sutun] for satir, sutun in enumerate(sutunlar)}


class SlotAtamaUzlasmasi:
    """Herkesin aynı eşleşmeyi hesapladığını UDP ile doğrular; uyuşmazsa numara = slot'a döner (güvenli yol)."""

    def __init__(
        self,
        iha_id: int,
        toplam_iha: int,
        tasiyici: Tasiyici,
        logger: logging.Logger,
        yayin_araligi_s: float,
        zaman_asimi_s: float,
    ) -> None:
        self._iha_id = iha_id
        self._toplam_iha = toplam_iha
        self._tasiyici = tasiyici
        self._logger = logger
        self._yayin_araligi_s = yayin_araligi_s
        self._zaman_asimi_s = zaman_asimi_s
        self._oneriler: dict[int, dict[int, int]] = {}
        tasiyici.mesaj_dinleyici_ekle(self._mesaj_isle)

    def _mesaj_isle(self, mesaj: AgMesaji) -> None:
        if mesaj.tip != "ATAMA":
            return
        oneri = self._atamayi_dogrula(mesaj.veri.get("atama"))
        if oneri is None:
            self._logger.warning("İHA-%d'den geçersiz ATAMA mesajı atıldı.", mesaj.gonderen)
            return
        self._oneriler[mesaj.gonderen] = oneri

    def _atamayi_dogrula(self, ham: Any) -> dict[int, int] | None:
        """Dışarıdan gelen eşleşmenin 1..N için bire bir olduğunu doğrular."""
        if not isinstance(ham, dict):
            return None
        try:
            atama = {int(k): int(v) for k, v in ham.items()}
        except (TypeError, ValueError):
            return None
        aralik = set(range(1, self._toplam_iha + 1))
        if set(atama) != aralik or set(atama.values()) != aralik:
            return None
        return atama

    async def belirle(
        self,
        dron_konumlari: dict[int, np.ndarray],
        slot_konumlari: dict[int, np.ndarray],
        yuvarlama_m: float,
        kimlik_tercihi_m: float,
    ) -> dict[int, int]:
        """Eşleşmeyi hesaplar, komşularla doğrular; başarısızsa kimlik eşleşmesini (i -> i) döndürür."""
        kimlik = {i: i for i in range(1, self._toplam_iha + 1)}
        eksik = set(kimlik) - set(dron_konumlari)
        if eksik:
            self._logger.warning("Konumu bilinmeyen İHA'lar %s; slot = numara kullanılıyor.", sorted(eksik))
            return kimlik

        oneri = en_kisa_toplam_yol_atamasi(dron_konumlari, slot_konumlari, yuvarlama_m, kimlik_tercihi_m)
        if not await self._uzlas(oneri):
            return kimlik

        def toplam(atama: dict[int, int]) -> float:
            return sum(
                float(np.linalg.norm(np.asarray(dron_konumlari[i])[:2] - np.asarray(slot_konumlari[s])[:2]))
                for i, s in atama.items()
            )

        self._logger.info(
            "Slot ataması (İHA->slot) %s: toplam yol %.1f m (numara=slot olsaydı %.1f m)",
            oneri, toplam(oneri), toplam(kimlik),
        )
        return oneri

    async def _uzlas(self, oneri: dict[int, int]) -> bool:
        """Tüm komşular aynı öneriyi yayınladıysa True. Eksik veya farklı öneri varsa False."""
        komsular = set(range(1, self._toplam_iha + 1)) - {self._iha_id}
        paket = {"atama": {str(k): v for k, v in oneri.items()}}
        bitis = time.monotonic() + self._zaman_asimi_s
        while True:
            # UDP kayıp olabilir: bitene kadar tekrar tekrar yayınla
            self._tasiyici.yayinla("ATAMA", paket)
            if komsular <= self._oneriler.keys():
                break
            if time.monotonic() >= bitis:
                self._logger.warning(
                    "ATAMA önerisi gelmeyen İHA'lar %s; slot = numara kullanılıyor.",
                    sorted(komsular - self._oneriler.keys()),
                )
                return False
            await asyncio.sleep(self._yayin_araligi_s)

        farkli = sorted(i for i in komsular if self._oneriler[i] != oneri)
        if farkli:
            self._logger.warning("İHA'lar %s farklı slot ataması önerdi; slot = numara kullanılıyor.", farkli)
            return False
        return True
