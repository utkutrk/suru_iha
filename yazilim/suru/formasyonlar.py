"""Tüm formasyon geometrileri tek dosyada, tablo tabanlı ve N dron için jenerik."""

from __future__ import annotations

import math
from typing import Callable
import numpy as np


def _merkezle(noktalar: np.ndarray) -> np.ndarray:
    """Formasyon ofsetlerinin ağırlık merkezini (0, 0, 0) noktasına taşır."""
    if len(noktalar) == 0:
        return noktalar
    return noktalar - np.mean(noktalar, axis=0)


def _ok_basi(n: int, aralik_m: float) -> np.ndarray:
    """Ok başı formasyonu (Şekil 3a): slot 1 önde, diğerleri arkaya doğru iki kolda."""
    # 60° yarım açı ile eşkenar üçgen düzeni (komşular arası mesafe = aralik_m)
    dx = aralik_m * math.cos(math.radians(30.0))
    dy = aralik_m * math.sin(math.radians(30.0))
    ofsetler = [[0.0, 0.0, 0.0]]
    for i in range(1, n):
        kademe = (i + 1) // 2
        taraf = -1.0 if (i % 2 == 1) else 1.0  # tekler sol (-y), çiftler sağ (+y)
        ofsetler.append([-kademe * dx, taraf * kademe * dy, 0.0])
    return _merkezle(np.array(ofsetler, dtype=float))


def _v_formasyonu(n: int, aralik_m: float) -> np.ndarray:
    """V formasyonu (Şekil 3b): slot 1 arkada merkezde, kanatlar öne doğru açılır."""
    dx = aralik_m * math.cos(math.radians(30.0))
    dy = aralik_m * math.sin(math.radians(30.0))
    ofsetler = [[0.0, 0.0, 0.0]]
    for i in range(1, n):
        kademe = (i + 1) // 2
        taraf = -1.0 if (i % 2 == 1) else 1.0
        ofsetler.append([kademe * dx, taraf * kademe * dy, 0.0])
    return _merkezle(np.array(ofsetler, dtype=float))


def _cizgi(n: int, aralik_m: float) -> np.ndarray:
    """Çizgi formasyonu (Şekil 3c): Y ekseni boyunca (soldan sağa) yan yana dizilim."""
    ofsetler = [[0.0, i * aralik_m, 0.0] for i in range(n)]
    return _merkezle(np.array(ofsetler, dtype=float))


# Yeni formasyon eklemek için yalnız yukarıya fonksiyon yazıp bu tabloya eklemek yeterlidir
FormasyonFn = Callable[[int, float], np.ndarray]

FORMASYONLAR: dict[str, FormasyonFn] = {
    "ok_basi": _ok_basi,
    "ok": _ok_basi,
    "v": _v_formasyonu,
    "cizgi": _cizgi,
    "l": _cizgi,
}

# Şartname / QR kısa adlarını standart kanonik ada çeviren tablo
FORMASYON_KANONIK: dict[str, str] = {
    "ok_basi": "ok_basi",
    "ok": "ok_basi",
    "v": "v",
    "cizgi": "cizgi",
    "l": "cizgi",
}


def formasyon_ofsetleri(ad: str, iha_sayisi: int, aralik_m: float) -> np.ndarray:
    """Verilen formasyon adı, N dron ve aralık için gövde çerçevesinde (N, 3) ofset döner."""
    anahtar = ad.strip().lower()
    fn = FORMASYONLAR.get(anahtar)
    if fn is None:
        gecerli = ", ".join(sorted(set(FORMASYON_KANONIK.values())))
        raise ValueError(f"Bilinmeyen formasyon: '{ad}'. Geçerliler: {gecerli}")
    if iha_sayisi < 1:
        raise ValueError("iha_sayisi en az 1 olmalıdır")
    if aralik_m <= 0:
        raise ValueError("aralik_m pozitif olmalıdır")
    return fn(iha_sayisi, aralik_m)


def kanonik_formasyon_adi(ad: str) -> str:
    """Kısa adları ('ok', 'l') standart ada ('ok_basi', 'cizgi') dönüştürür."""
    anahtar = ad.strip().lower()
    if anahtar not in FORMASYON_KANONIK:
        raise ValueError(f"Bilinmeyen formasyon: '{ad}'")
    return FORMASYON_KANONIK[anahtar]
