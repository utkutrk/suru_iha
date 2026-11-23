"""Her dronda aynı biçimde çalışan ana giriş programı (iş mantığı içermez, yalnız parçaları bağlar)."""

from __future__ import annotations

import argparse
import asyncio
import logging
import signal
from pathlib import Path

from yazilim.ag.mesaj import MesajKodlayici
from yazilim.ag.udp_tasiyici import UdpTasiyici
from yazilim.dron.mavsdk_dron import MavsdkDron
from yazilim.gorevler.gorev1_dinamik import Gorev1DinamikSuru
from yazilim.gorevler.gorev2_yari_otonom import Gorev2YariOtonom
from yazilim.gorevler.komut_kaynagi import SenaryoKomutKaynagi
from yazilim.gorus.kamera import BosKamera, OpenCvKamera
from yazilim.guvenlik.son_kapi import GuvenlikKapisi
from yazilim.ortak.ayarlar import PROJE_KOKU, ayarlari_yukle
from yazilim.ortak.loglama import loglama_kur
from yazilim.suru.senkron import DagitimSenkron


def _argumanlari_oku() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TEKNOFEST Sürü İHA dağıtık ajan programı")
    parser.add_argument("--iha-id", type=int, required=True, help="Bu dronun ID'si (1..N)")
    parser.add_argument("--iha-sayisi", type=int, default=None, help="Sürüdeki toplam İHA sayısı")
    parser.add_argument(
        "--gorev",
        choices=["gorev1", "gorev2"],
        default="gorev1",
        help="Çalıştırılacak görev (gorev1 veya gorev2)",
    )
    parser.add_argument(
        "--senaryo",
        type=Path,
        default=PROJE_KOKU / "senaryolar" / "gorev1_ornek.json",
        help="Görev 1 senaryo JSON yolu",
    )
    parser.add_argument("--takim-id", type=str, default=None, help="QR içindeki takım ID")
    parser.add_argument(
        "--hemen-basla",
        action="store_true",
        help="Görev 1 için YKİ 'BASLAT' beklemeden hemen kalk",
    )
    parser.add_argument(
        "--kamera",
        type=str,
        default="",
        help="İsteğe bağlı kamera kaynağı (cihaz indeksi veya GStreamer/RTSP adresi)",
    )
    parser.add_argument("--log-seviye", type=str, default="INFO", help="DEBUG/INFO/WARNING")
    return parser.parse_args()


async def _calistir(args: argparse.Namespace) -> None:
    ayarlar = ayarlari_yukle()
    iha_sayisi = args.iha_sayisi or int(ayarlar.ag["varsayilan_iha_sayisi"])
    takim_id = args.takim_id or str(ayarlar.ag["takim_id"])

    if not (1 <= args.iha_id <= iha_sayisi):
        raise ValueError(f"--iha-id 1..{iha_sayisi} aralığında olmalıdır")

    seviye = getattr(logging, args.log_seviye.upper(), logging.INFO)
    logger = loglama_kur(args.iha_id, ayarlar, seviye=seviye)

    tum_idleri = list(range(1, iha_sayisi + 1))
    kodlayici = MesajKodlayici(
        protokol_surumu=int(ayarlar.ag["protokol_surumu"]),
        takim_anahtari=ayarlar.takim_anahtari,
        maks_mesaj_yasi_s=float(ayarlar.ag["maks_mesaj_yasi_s"]),
    )
    tasiyici = UdpTasiyici(
        iha_id=args.iha_id,
        tum_iha_idleri=tum_idleri,
        dinleme_adresi=str(ayarlar.ag["dinleme_adresi"]),
        hedef_adresi=str(ayarlar.ag["hedef_adresi"]),
        udp_taban_portu=int(ayarlar.ag["udp_taban_portu"]),
        kodlayici=kodlayici,
        logger=logger.getChild("ag"),
    )
    dron = MavsdkDron(args.iha_id, ayarlar, logger.getChild("dron"))
    guvenlik = GuvenlikKapisi(args.iha_id, ayarlar, logger.getChild("guvenlik"))
    senkron = DagitimSenkron(
        kendi_id=args.iha_id,
        tum_iha_idleri=tum_idleri,
        komsu_zaman_asimi_s=float(ayarlar.ucus["komsu_zaman_asimi_s"]),
    )
    kamera = (
        OpenCvKamera(int(args.kamera) if args.kamera.isdigit() else args.kamera)
        if args.kamera
        else BosKamera()
    )

    await tasiyici.baslat()
    await dron.baglan()

    try:
        if args.gorev == "gorev1":
            komut_kaynagi = SenaryoKomutKaynagi(
                senaryo_yolu=args.senaryo,
                takim_id=takim_id,
                varsayilan_bekleme_s=float(ayarlar.ucus["varsayilan_gorev_bekleme_s"]),
            )
            gorev = Gorev1DinamikSuru(
                iha_id=args.iha_id,
                toplam_iha=iha_sayisi,
                ayarlar=ayarlar,
                dron=dron,
                tasiyici=tasiyici,
                guvenlik=guvenlik,
                senkron=senkron,
                komut_kaynagi=komut_kaynagi,
                kamera=kamera,
                logger=logger.getChild("gorev1"),
                hemen_basla=args.hemen_basla,
            )
            await gorev.calistir()
        else:
            gorev2 = Gorev2YariOtonom(
                iha_id=args.iha_id,
                toplam_iha=iha_sayisi,
                ayarlar=ayarlar,
                dron=dron,
                tasiyici=tasiyici,
                guvenlik=guvenlik,
                senkron=senkron,
                logger=logger.getChild("gorev2"),
            )
            await gorev2.calistir()
    finally:
        kamera.kapat()
        await dron.kapat()
        await tasiyici.kapat()


def main() -> None:
    args = _argumanlari_oku()
    dongu = asyncio.new_event_loop()
    asyncio.set_event_loop(dongu)

    ana_gorev = dongu.create_task(_calistir(args))
    for sig in (signal.SIGINT, signal.SIGTERM):
        dongu.add_signal_handler(sig, ana_gorev.cancel)

    try:
        dongu.run_until_complete(ana_gorev)
    except asyncio.CancelledError:
        pass
    finally:
        dongu.close()


if __name__ == "__main__":
    main()
