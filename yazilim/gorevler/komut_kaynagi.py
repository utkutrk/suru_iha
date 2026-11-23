"""Komut kaynağı arayüzü ve Şekil 2 QR JSON biçimini okuyan senaryo okuyucu."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class QrGorevPaketi:
    """Bir QR noktasından bizim takım ID'mize ait çözülmüş görev paketi."""

    qr_no: int
    bekleme_s: float
    komutlar: list[list[Any]]
    sonraki_qr: int


def qr_json_ayristir(
    ham_qr: dict[str, Any],
    takim_id: str,
    varsayilan_bekleme_s: float,
) -> QrGorevPaketi:
    """Şartname Şekil 2 QR JSON yapısını doğrular ve yalnız ilgili takımın görevini çıkarır."""
    if not isinstance(ham_qr, dict):
        raise ValueError("QR verisi sözlük (JSON object) olmalıdır")

    for zorunlu in ("qr", "mis", "team"):
        if zorunlu not in ham_qr:
            raise ValueError(f"QR verisinde zorunlu alan eksik: '{zorunlu}'")

    qr_no = int(ham_qr["qr"])
    bekleme_s = float(ham_qr.get("w", varsayilan_bekleme_s))
    gorev_listeleri = ham_qr["mis"]
    takimlar = ham_qr["team"]

    if not isinstance(gorev_listeleri, list) or not isinstance(takimlar, dict):
        raise ValueError("QR 'mis' liste, 'team' sözlük olmalıdır")

    takim_anahtar = str(takim_id)
    if takim_anahtar not in takimlar:
        raise ValueError(f"QR içinde takım ID '{takim_anahtar}' bulunamadı")

    eslesme = takimlar[takim_anahtar]
    if not isinstance(eslesme, list) or len(eslesme) != 2:
        raise ValueError(f"Takım '{takim_anahtar}' girdisi [gorev_indeks, sonraki_qr] olmalıdır")

    gorev_indeks_1tabanli = int(eslesme[0])
    sonraki_qr = int(eslesme[1])

    if not (1 <= gorev_indeks_1tabanli <= len(gorev_listeleri)):
        raise ValueError(
            f"Geçersiz görev indeksi {gorev_indeks_1tabanli} (toplam {len(gorev_listeleri)})"
        )

    komutlar = gorev_listeleri[gorev_indeks_1tabanli - 1]
    if not isinstance(komutlar, list):
        raise ValueError("Seçilen görev komut listesi değil")

    return QrGorevPaketi(
        qr_no=qr_no,
        bekleme_s=max(0.0, bekleme_s),
        komutlar=komutlar,
        sonraki_qr=sonraki_qr,
    )


class KomutKaynagi(ABC):
    """Görev 1 komut kaynağı arayüzü (şimdi senaryo dosyası, ileride QR okuyucu aynı yere takılır)."""

    @abstractmethod
    def baslangic_qr_no(self) -> int:
        """Sürünün ilk gideceği QR numarasını döndürür."""

    @abstractmethod
    async def qr_gorevini_oku(self, qr_no: int) -> QrGorevPaketi:
        """Verilen QR noktasındaki takım görevini döndürür."""


class SenaryoKomutKaynagi(KomutKaynagi):
    """senaryolar/*.json dosyasından sanki QR okunmuş gibi görev döndürür."""

    def __init__(
        self,
        senaryo_yolu: Path,
        takim_id: str,
        varsayilan_bekleme_s: float,
    ) -> None:
        if not senaryo_yolu.exists():
            raise FileNotFoundError(f"Senaryo dosyası bulunamadı: {senaryo_yolu}")
        with senaryo_yolu.open("r", encoding="utf-8") as f:
            self._veri = json.load(f)
        self._takim_id = str(takim_id)
        self._varsayilan_bekleme_s = varsayilan_bekleme_s

    def baslangic_qr_no(self) -> int:
        return int(self._veri.get("baslangic_qr", 1))

    async def qr_gorevini_oku(self, qr_no: int) -> QrGorevPaketi:
        qr_sozluk = self._veri.get("qr_verileri", {})
        anahtar = str(qr_no)
        if anahtar not in qr_sozluk:
            raise KeyError(f"Senaryoda QR-{qr_no} verisi bulunamadı")
        return qr_json_ayristir(
            ham_qr=qr_sozluk[anahtar],
            takim_id=self._takim_id,
            varsayilan_bekleme_s=self._varsayilan_bekleme_s,
        )
