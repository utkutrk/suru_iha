"""Her dronun konumunu, PX4'e giden hedefi ve ideal slotunu CSV'ye yazar (prova raporu bu dosyadan çıkar)."""

from __future__ import annotations

import csv
import time
from datetime import datetime
from pathlib import Path
from typing import IO, TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:  # yalnız tip denetimi için; çalışma anında alt katmana bağımlılık yok
    from yazilim.dron.mavsdk_dron import DronTelemetri

# Raporun hangi anlarda hangi kuralı uygulayacağını bilmesi için uçuş fazları (tek yerde tanımlı)
FAZ_YERDE = "yerde"
FAZ_KALKIS = "kalkis"
FAZ_UCUS = "ucus"
FAZ_AYRILMA = "ayrilma"
FAZ_INIS = "inis"

BASLIKLAR = [
    "t_epoch_s", "adim", "faz", "aciklama",
    "kuzey_m", "dogu_m", "asagi_m", "yaw_deg",
    "hiz_kuzey_m_s", "hiz_dogu_m_s", "hiz_asagi_m_s",
    "hedef_kuzey_m", "hedef_dogu_m", "hedef_asagi_m",
    "slot_kuzey_m", "slot_dogu_m", "slot_asagi_m",
    "havada", "arm", "gps_saglikli",
]


class KonumKaydi:
    """Tek dronun konum kaydı; her satır ortak NED çerçevesindedir (K, D, A)."""

    def __init__(self, iha_id: int, dizin: Path, aralik_s: float) -> None:
        dizin.mkdir(parents=True, exist_ok=True)
        zaman = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.yol = dizin / f"konum_{zaman}_iha{iha_id}.csv"
        self._aralik_s = aralik_s
        self._son_yazim_s = -1e9
        self._dosya: IO[str] | None = self.yol.open("w", newline="", encoding="utf-8")
        self._yazici = csv.writer(self._dosya)
        self._yazici.writerow(BASLIKLAR)

    def yaz(
        self,
        telemetri: "DronTelemetri",
        hedef_ned: np.ndarray,
        slot_ned: np.ndarray | None,
        adim: int,
        faz: str,
        aciklama: str,
    ) -> None:
        """Aralık dolduysa bir satır yazar. slot_ned yoksa (ayrılmış dron) slot sütunları boş kalır."""
        simdi = time.monotonic()
        if self._dosya is None or simdi - self._son_yazim_s < 0.9 * self._aralik_s:  # zamanlayıcı sapmasında satır atlamasın
            return
        self._son_yazim_s = simdi

        k = telemetri.konum_ned
        h = telemetri.hiz_ned
        slot = ["", "", ""] if slot_ned is None else [f"{c:.3f}" for c in slot_ned]
        self._yazici.writerow([
            f"{time.time():.3f}", adim, faz, aciklama,
            f"{k[0]:.3f}", f"{k[1]:.3f}", f"{k[2]:.3f}", f"{telemetri.yaw_deg:.1f}",
            f"{h[0]:.3f}", f"{h[1]:.3f}", f"{h[2]:.3f}",
            f"{hedef_ned[0]:.3f}", f"{hedef_ned[1]:.3f}", f"{hedef_ned[2]:.3f}",
            *slot,
            int(telemetri.havada), int(telemetri.arm_durumu), int(telemetri.gps_saglikli),
        ])

    def kapat(self) -> None:
        if self._dosya is not None:
            self._dosya.close()
            self._dosya = None
