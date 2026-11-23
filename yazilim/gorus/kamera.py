"""Simülasyon ve gerçek kamera için ortak kamera arayüzü."""

from __future__ import annotations

from abc import ABC, abstractmethod
import cv2
import numpy as np


class KameraArayuzu(ABC):
    """Tüm kamera kaynaklarının uyduğu tek arayüz."""

    @abstractmethod
    def kare_oku(self) -> np.ndarray | None:
        """BGR biçiminde bir görüntü karesi döndürür; kare yoksa None."""

    @abstractmethod
    def kapat(self) -> None:
        """Kamera kaynağını serbest bırakır."""


class BosKamera(KameraArayuzu):
    """Kamera akışı olmadan simülasyon testleri için boş kamera."""

    def kare_oku(self) -> np.ndarray | None:
        return None

    def kapat(self) -> None:
        return None


class OpenCvKamera(KameraArayuzu):
    """V4L2, RTSP veya GStreamer (Gazebo) kaynağından OpenCV ile kare okur."""

    def __init__(self, kaynak: int | str) -> None:
        self._yakalayici = cv2.VideoCapture(kaynak)

    def kare_oku(self) -> np.ndarray | None:
        if not self._yakalayici.isOpened():
            return None
        basarili, kare = self._yakalayici.read()
        return kare if basarili else None

    def kapat(self) -> None:
        if self._yakalayici.isOpened():
            self._yakalayici.release()
