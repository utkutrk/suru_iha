#!/usr/bin/env python3
"""YKİ 'Başlat' betiği: Görev 1 için sürüye yalnız tek bir BASLAT komutu gönderir ve çıkar [5.1]."""

from __future__ import annotations

import argparse
import os
import socket
import sys
from pathlib import Path

PROJE_KOKU = Path(__file__).resolve().parents[1]
if str(PROJE_KOKU) not in sys.path:
    sys.path.insert(0, str(PROJE_KOKU))

from yazilim.ag.mesaj import MesajKodlayici
from yazilim.ortak.ayarlar import ayarlari_yukle


def main() -> None:
    parser = argparse.ArgumentParser(description="YKİ tek seferlik BASLAT komutu gönderici")
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
    paket = kodlayici.paketle(tip="BASLAT", gonderen=0, veri={"kaynak": "yki"})

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        for i in range(1, iha_sayisi + 1):
            sock.sendto(paket, (hedef_ip, taban_port + i))
        print(f"BASLAT komutu {iha_sayisi} İHA'ya gönderildi. YKİ bağlantısı kesilebilir.")
    finally:
        sock.close()


if __name__ == "__main__":
    main()
