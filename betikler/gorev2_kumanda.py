#!/usr/bin/env python3
"""Görev 2 tek kumanda (klavye) kontrolcüsü: tüm dronlara UDP üzerinden senkron girdi yollar."""

from __future__ import annotations

import argparse
import os
import select
import socket
import sys
import termios
import tty
from pathlib import Path

PROJE_KOKU = Path(__file__).resolve().parents[1]
if str(PROJE_KOKU) not in sys.path:
    sys.path.insert(0, str(PROJE_KOKU))

from yazilim.ag.mesaj import MesajKodlayici
from yazilim.ortak.ayarlar import ayarlari_yukle


YARDIM = """
=== Görev 2 — Tek Kumanda Kontrolü ===
  t : Kalkış (tüm sürü)
  l : İniş (tüm sürü)
  w/s : İleri / Geri (Hareket Modu) veya Pitch Eğim (Manevra Modu)
  a/d : Sol / Sağ (Hareket Modu) veya Roll Eğim (Manevra Modu)
  r/f : Yüksel / Alçal (Throttle)
  q/e : Sola / Sağa Yaw (Formasyon Rotasyonu)
  m   : Mod değiştir (hareket <-> manevra)
  1   : Ok başı formasyonu
  2   : V formasyonu
  3   : Çizgi formasyonu
  Ctrl+C : Çıkış
"""


def _gonder(
    sock: socket.socket,
    kodlayici: MesajKodlayici,
    hedef_ip: str,
    taban_port: int,
    iha_sayisi: int,
    veri: dict[str, object],
) -> None:
    paket = kodlayici.paketle(tip="KUMANDA", gonderen=0, veri=veri)
    for i in range(1, iha_sayisi + 1):
        sock.sendto(paket, (hedef_ip, taban_port + i))


def main() -> None:
    parser = argparse.ArgumentParser(description="Görev 2 klavye kumanda arayüzü")
    parser.add_argument("--iha-sayisi", type=int, default=None, help="Sürüdeki İHA sayısı")
    args = parser.parse_args()

    if not os.environ.get("SURU_TAKIM_ANAHTARI") and not (
        PROJE_KOKU / "ayarlar" / "gizli.local.json"
    ).exists():
        os.environ["SURU_TAKIM_ANAHTARI"] = "gelistirme_anahtari_degistir"

    ayarlar = ayarlari_yukle()
    iha_sayisi = args.iha_sayisi or int(ayarlar.ag["varsayilan_iha_sayisi"])
    hedef_ip = str(ayarlar.ag["hedef_adresi"])
    taban_port = int(ayarlar.ag["udp_taban_portu"])

    kodlayici = MesajKodlayici(
        protokol_surumu=int(ayarlar.ag["protokol_surumu"]),
        takim_anahtari=ayarlar.takim_anahtari,
        maks_mesaj_yasi_s=float(ayarlar.ag["maks_mesaj_yasi_s"]),
    )
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    mod = "hareket"

    print(YARDIM)
    fd = sys.stdin.fileno()
    eski_ayar = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        while True:
            hazir, _, _ = select.select([sys.stdin], [], [], 0.1)
            if not hazir:
                continue
            tus = sys.stdin.read(1).lower()
            if tus == "\x03":
                break
            elif tus == "t":
                _gonder(sock, kodlayici, hedef_ip, taban_port, iha_sayisi, {"eylem": "kalkis"})
                print("[KUMANDA] Kalkış gönderildi")
            elif tus == "l":
                _gonder(sock, kodlayici, hedef_ip, taban_port, iha_sayisi, {"eylem": "inis"})
                print("[KUMANDA] İniş gönderildi")
            elif tus == "m":
                mod = "manevra" if mod == "hareket" else "hareket"
                _gonder(
                    sock, kodlayici, hedef_ip, taban_port, iha_sayisi,
                    {"eylem": "mod", "deger": mod},
                )
                print(f"[KUMANDA] Mod -> {mod}")
            elif tus in ("1", "2", "3"):
                frm_harita = {"1": "ok_basi", "2": "v", "3": "cizgi"}
                _gonder(
                    sock, kodlayici, hedef_ip, taban_port, iha_sayisi,
                    {"eylem": "formasyon", "deger": frm_harita[tus]},
                )
                print(f"[KUMANDA] Formasyon -> {frm_harita[tus]}")
            else:
                cubuk_harita = {
                    "w": {"ileri": 1.0},
                    "s": {"ileri": -1.0},
                    "d": {"sag": 1.0},
                    "a": {"sag": -1.0},
                    "r": {"yukari": 1.0},
                    "f": {"yukari": -1.0},
                    "e": {"yaw": 1.0},
                    "q": {"yaw": -1.0},
                }
                if tus in cubuk_harita:
                    veri: dict[str, object] = {"eylem": "cubuk", **cubuk_harita[tus]}
                    _gonder(sock, kodlayici, hedef_ip, taban_port, iha_sayisi, veri)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, eski_ayar)
        sock.close()


if __name__ == "__main__":
    main()
