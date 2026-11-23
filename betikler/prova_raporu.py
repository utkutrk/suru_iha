#!/usr/bin/env python3
"""Son provanın konum CSV'lerinden ve loglarından rapor üretir. Kullanım: python betikler/prova_raporu.py [--oturum 20261123_1137]"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJE_KOKU = Path(__file__).resolve().parents[1]
if str(PROJE_KOKU) not in sys.path:
    sys.path.insert(0, str(PROJE_KOKU))

from yazilim.analiz.prova_raporu import rapor_uret
from yazilim.ortak.ayarlar import ayarlari_yukle


def main() -> None:
    parser = argparse.ArgumentParser(description="Prova raporu")
    parser.add_argument("--dizin", type=Path, default=PROJE_KOKU / "kayitlar")
    parser.add_argument("--oturum", type=str, default=None, help="Dosya adındaki zaman damgası öneki (YYYYMMDD_HHMM)")
    args = parser.parse_args()

    # Rapor takım anahtarına ihtiyaç duymaz; ayar doğrulaması için geçici değer verilir
    ayarlar = ayarlari_yukle(takim_anahtari_gecersiz_kilsin="rapor")
    metin, temiz = rapor_uret(args.dizin, ayarlar, args.oturum)
    print(metin)
    sys.exit(0 if temiz else 1)


if __name__ == "__main__":
    main()
