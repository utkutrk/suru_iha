"""JSON mesaj biçimi, takım anahtarı doğrulaması, bayatlık ve sıra no kontrolü."""

from __future__ import annotations

import hmac
import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AgMesaji:
    """Doğrulanmış ağ mesajı."""

    surum: int
    tip: str
    gonderen: int
    sira_no: int
    zaman_damgasi: float
    veri: dict[str, Any]


def _imza_hesapla(
    surum: int,
    tip: str,
    gonderen: int,
    sira_no: int,
    zaman_damgasi: float,
    veri: dict[str, Any],
    takim_anahtari: str,
) -> str:
    """Mesaj bütünlüğünü ve takım kimliğini doğrulamak için HMAC-SHA256 üretir."""
    govde = json.dumps(
        {
            "surum": surum,
            "tip": tip,
            "gonderen": gonderen,
            "sira_no": sira_no,
            "zaman_damgasi": round(zaman_damgasi, 3),
            "veri": veri,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hmac.new(takim_anahtari.encode("utf-8"), govde, hashlib.sha256).hexdigest()


class MesajKodlayici:
    """Mesajları paketler ve gelen paketleri güvenlik/bayatlık süzgecinden geçirir."""

    def __init__(
        self,
        protokol_surumu: int,
        takim_anahtari: str,
        maks_mesaj_yasi_s: float,
    ) -> None:
        self._surum = protokol_surumu
        self._anahtar = takim_anahtari
        self._maks_yas = maks_mesaj_yasi_s
        self._sira_no = 0
        self._son_sira_nolar: dict[tuple[int, str], int] = {}

    def paketle(
        self,
        tip: str,
        gonderen: int,
        veri: dict[str, Any],
        simdi: float | None = None,
    ) -> bytes:
        """Veriyi imzalı JSON bayt dizisine dönüştürür."""
        self._sira_no += 1
        ts = round(time.time() if simdi is None else simdi, 3)
        imza = _imza_hesapla(
            self._surum, tip, gonderen, self._sira_no, ts, veri, self._anahtar
        )
        zarf = {
            "surum": self._surum,
            "tip": tip,
            "gonderen": gonderen,
            "sira_no": self._sira_no,
            "zaman_damgasi": ts,
            "imza": imza,
            "veri": veri,
        }
        return json.dumps(zarf, ensure_ascii=False, separators=(",", ":")).encode("utf-8")

    def coz(self, ham_veri: bytes, simdi: float | None = None) -> AgMesaji | None:
        """Gelen baytları doğrular; bozuk, yanlış anahtarlı, bayat veya tekrarlıysa None döner."""
        try:
            zarf = json.loads(ham_veri.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

        if not isinstance(zarf, dict):
            return None

        gerekli = ("surum", "tip", "gonderen", "sira_no", "zaman_damgasi", "imza", "veri")
        if any(alan not in zarf for alan in gerekli):
            return None

        surum = zarf["surum"]
        tip = zarf["tip"]
        gonderen = zarf["gonderen"]
        sira_no = zarf["sira_no"]
        ts = zarf["zaman_damgasi"]
        imza = zarf["imza"]
        veri = zarf["veri"]

        if (
            surum != self._surum
            or not isinstance(tip, str)
            or not isinstance(gonderen, int)
            or not isinstance(sira_no, int)
            or not isinstance(ts, (int, float))
            or not isinstance(imza, str)
            or not isinstance(veri, dict)
        ):
            return None

        # Zaman damgası bayatlık kontrolü (eski veya gelecekten gelen sahte paketleri at)
        su_an = time.time() if simdi is None else simdi
        if abs(su_an - float(ts)) > self._maks_yas:
            return None

        # Takım anahtarı doğrulaması (zamanlama saldırısına dayanıklı karşılaştırma)
        beklenen = _imza_hesapla(surum, tip, gonderen, sira_no, float(ts), veri, self._anahtar)
        if not hmac.compare_digest(imza, beklenen):
            return None

        # Sıra numarası kontrolü (tekrarlı veya sıra dışı eski paketleri at)
        anahtar = (gonderen, tip)
        onceki = self._son_sira_nolar.get(anahtar, 0)
        if sira_no <= onceki:
            return None
        self._son_sira_nolar[anahtar] = sira_no

        return AgMesaji(
            surum=surum,
            tip=tip,
            gonderen=gonderen,
            sira_no=sira_no,
            zaman_damgasi=float(ts),
            veri=veri,
        )
