"""HSV renkli iniş alanı tespiti (kırmızı iki aralıkta) ve ardışık N kare doğrulaması."""

from __future__ import annotations

import math
from dataclasses import dataclass
import cv2
import numpy as np

from yazilim.ortak.ayarlar import Ayarlar


@dataclass(frozen=True)
class RenkTespiti:
    """Onaylanmış renkli alan tespiti ve tahmin edilen yer NED konumu."""

    renk: str
    merkez_px: tuple[float, float]
    alan_px: float
    yer_konum_ned: np.ndarray


class RenkAlgilayici:
    """Aşağı bakan kameradan kırmızı ve mavi iniş alanlarını tespit eder."""

    def __init__(self, ayarlar: Ayarlar) -> None:
        kam = ayarlar.saha["kamera"]
        self._fov_deg = float(kam["fov_deg"])
        self._ardisik_esik = int(kam["ardisik_tespit_kare"])
        self._min_alan = float(kam["min_kontur_alani_px"])
        self._hsv_araliklari: dict[str, list[list[list[int]]]] = ayarlar.saha[
            "renk_hsv_araliklari"
        ]
        self._ardisik_sayac: dict[str, int] = {r: 0 for r in self._hsv_araliklari}

    def kare_isle(
        self,
        bgr_kare: np.ndarray,
        dron_konum_ned: np.ndarray,
        dron_yaw_deg: float,
    ) -> list[RenkTespiti]:
        """Karede renkli alan arar; ardışık N kare şartını geçenleri ortak NED'e yansıtır."""
        hsv = cv2.cvtColor(bgr_kare, cv2.COLOR_BGR2HSV)
        yukseklik, genislik = bgr_kare.shape[:2]
        irtifa_m = max(0.5, float(-dron_konum_ned[2]))

        tespitler: list[RenkTespiti] = []
        for renk, araliklar in self._hsv_araliklari.items():
            maske = np.zeros((yukseklik, genislik), dtype=np.uint8)
            for alt, ust in araliklar:
                parca = cv2.inRange(
                    hsv,
                    np.array(alt, dtype=np.uint8),
                    np.array(ust, dtype=np.uint8),
                )
                maske = cv2.bitwise_or(maske, parca)

            konturlar, _ = cv2.findContours(maske, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            en_buyuk = max(konturlar, key=cv2.contourArea) if konturlar else None
            if en_buyuk is None or cv2.contourArea(en_buyuk) < self._min_alan:
                self._ardisik_sayac[renk] = 0
                continue

            self._ardisik_sayac[renk] += 1
            if self._ardisik_sayac[renk] < self._ardisik_esik:
                continue

            m = cv2.moments(en_buyuk)
            if m["m00"] <= 0:
                continue
            cx = m["m10"] / m["m00"]
            cy = m["m01"] / m["m00"]

            yer_ned = self._pikselden_ned_hesapla(
                cx, cy, genislik, yukseklik, irtifa_m, dron_konum_ned, dron_yaw_deg
            )
            tespitler.append(
                RenkTespiti(
                    renk=renk,
                    merkez_px=(cx, cy),
                    alan_px=float(cv2.contourArea(en_buyuk)),
                    yer_konum_ned=yer_ned,
                )
            )
        return tespitler

    def _pikselden_ned_hesapla(
        self,
        cx: float,
        cy: float,
        genislik: int,
        yukseklik: int,
        irtifa_m: float,
        dron_konum_ned: np.ndarray,
        dron_yaw_deg: float,
    ) -> np.ndarray:
        """İğne deliği kamera modeliyle piksel merkezini düz zemin NED konumuna yansıtır."""
        odak_px = (genislik / 2.0) / math.tan(math.radians(self._fov_deg / 2.0))
        # Görüntü yukarı (-y_px) = dron ileri (+x_govde); görüntü sağ (+x_px) = dron sağ (+y_govde)
        ileri_m = ((yukseklik / 2.0) - cy) * (irtifa_m / odak_px)
        sag_m = (cx - (genislik / 2.0)) * (irtifa_m / odak_px)

        psi = math.radians(dron_yaw_deg)
        d_kuzey = ileri_m * math.cos(psi) - sag_m * math.sin(psi)
        d_dogu = ileri_m * math.sin(psi) + sag_m * math.cos(psi)
        return np.array(
            [float(dron_konum_ned[0]) + d_kuzey, float(dron_konum_ned[1]) + d_dogu, 0.0],
            dtype=float,
        )
