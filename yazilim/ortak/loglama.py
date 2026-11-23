"""Her uçuş için dosya + konsol loglaması kurar, kod sürümü ve ayar özetini kaydeder."""

from __future__ import annotations

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from yazilim.ortak.ayarlar import PROJE_KOKU, Ayarlar


def _git_surumu_al() -> str:
    """Mevcut git commit özetini döndürür; git deposu yoksa 'bilinmiyor' döner."""
    try:
        cikti = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(PROJE_KOKU),
            stderr=subprocess.DEVNULL,
            text=True,
        )
        return cikti.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        return "git-yok"


def loglama_kur(
    iha_id: int,
    ayarlar: Ayarlar,
    kayit_dizini: Path | None = None,
    seviye: int = logging.INFO,
) -> logging.Logger:
    """İHA özelinde loglayıcı oluşturur ve uçuş başlangıcında ayar özetini yazar."""
    dizin = kayit_dizini or (PROJE_KOKU / "kayitlar")
    dizin.mkdir(parents=True, exist_ok=True)

    zaman = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dosyasi = dizin / f"ucus_{zaman}_iha{iha_id}.log"

    kok_logger = logging.getLogger(f"suru.iha{iha_id}")
    kok_logger.setLevel(seviye)
    kok_logger.handlers.clear()
    kok_logger.propagate = False

    bicim = logging.Formatter(
        fmt="%(asctime)s.%(msecs)03d [%(levelname)s] [IHA-%(iha_id)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    class _IhaFiltresi(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            record.iha_id = iha_id  # type: ignore[attr-defined]
            return True

    filtre = _IhaFiltresi()

    dosya_isleyici = logging.FileHandler(log_dosyasi, encoding="utf-8")
    dosya_isleyici.setFormatter(bicim)
    dosya_isleyici.addFilter(filtre)

    konsol_isleyici = logging.StreamHandler()
    konsol_isleyici.setFormatter(bicim)
    konsol_isleyici.addFilter(filtre)

    kok_logger.addHandler(dosya_isleyici)
    kok_logger.addHandler(konsol_isleyici)

    # Her uçuşta kod sürümü ve ayar özetini kaydetmek kuraldır
    ozet_dosyasi = dizin / f"ayar_ozeti_{zaman}_iha{iha_id}.json"
    ozet: dict[str, Any] = {
        "zaman": zaman,
        "iha_id": iha_id,
        "kod_surumu": _git_surumu_al(),
        "ayarlar": ayarlar.ozet_sozluk(),
    }
    with ozet_dosyasi.open("w", encoding="utf-8") as f:
        json.dump(ozet, f, ensure_ascii=False, indent=2)

    kok_logger.info("Log başlatıldı: %s (sürüm=%s)", log_dosyasi.name, ozet["kod_surumu"])
    return kok_logger
