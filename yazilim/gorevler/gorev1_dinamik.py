"""Görev 1 — Dinamik Sürü Kabiliyeti dağıtık durum makinesi."""

from __future__ import annotations

import asyncio
import logging
import time
import numpy as np

from yazilim.ag.mesaj import AgMesaji
from yazilim.ag.udp_tasiyici import Tasiyici
from yazilim.dron.mavsdk_dron import MavsdkDron
from yazilim.gorevler.komut_kaynagi import KomutKaynagi
from yazilim.gorus.kamera import KameraArayuzu
from yazilim.gorus.renk_algilama import RenkAlgilayici
from yazilim.guvenlik.son_kapi import GuvenlikKapisi
from yazilim.ortak.ayarlar import Ayarlar
from yazilim.ortak.koordinat import en_kisa_aci_farki_deg, hedef_yonelim_deg
from yazilim.suru.komutlar import komut_uygula
from yazilim.suru.sanal_yapi import SanalYapi
from yazilim.suru.senkron import DagitimSenkron


class Gorev1DinamikSuru:
    """Her dronda aynı biçimde çalışan lidersiz Görev 1 yürütücüsü."""

    def __init__(
        self,
        iha_id: int,
        toplam_iha: int,
        ayarlar: Ayarlar,
        dron: MavsdkDron,
        tasiyici: Tasiyici,
        guvenlik: GuvenlikKapisi,
        senkron: DagitimSenkron,
        komut_kaynagi: KomutKaynagi,
        kamera: KameraArayuzu,
        logger: logging.Logger,
        hemen_basla: bool = False,
    ) -> None:
        self._iha_id = iha_id
        self._toplam_iha = toplam_iha
        self._ayarlar = ayarlar
        self._dron = dron
        self._tasiyici = tasiyici
        self._guvenlik = guvenlik
        self._senkron = senkron
        self._komut_kaynagi = komut_kaynagi
        self._kamera = kamera
        self._renk_algilayici = RenkAlgilayici(ayarlar)
        self._logger = logger

        self._baslat_olayi = asyncio.Event()
        if hemen_basla:
            self._baslat_olayi.set()

        self._home_merkezi = np.asarray(ayarlar.saha["home_merkezi_ned"], dtype=float)
        self._qr_konumlari = {
            int(k): np.asarray(v, dtype=float)
            for k, v in ayarlar.saha["qr_konumlari_ned"].items()
        }
        self._sim_renkli_alanlar = {
            str(k).lower(): np.asarray(v, dtype=float)
            for k, v in ayarlar.saha.get("simulasyon_renkli_alanlar_ned", {}).items()
        }

        kalkis_irtifa = float(ayarlar.ucus["kalkis_irtifasi_m"])
        self._yapi = SanalYapi(
            toplam_iha=toplam_iha,
            merkez_ned=np.array(
                [self._home_merkezi[0], self._home_merkezi[1], -kalkis_irtifa], dtype=float
            ),
            formasyon_adi=str(ayarlar.ucus["varsayilan_formasyon"]),
            aralik_m=float(ayarlar.ucus["varsayilan_aralik_m"]),
        )
        self._komut_sinirlari = {
            "min_irtifa_m": float(ayarlar.sartname["min_irtifa_m"]),
            "maks_irtifa_m": float(ayarlar.ucus["maks_irtifa_m"]),
            "maks_egim_acisi_deg": float(ayarlar.ucus["maks_egim_acisi_deg"]),
        }
        self._calisiyor = False
        self._adim_sayaci = 0

        self._tasiyici.mesaj_dinleyici_ekle(self._mesaj_isle)

    def _mesaj_isle(self, mesaj: AgMesaji) -> None:
        if mesaj.tip == "DURUM":
            self._senkron.komsu_guncelle(mesaj.gonderen, mesaj.veri)
        elif mesaj.tip == "BASLAT":
            if not self._baslat_olayi.is_set():
                self._logger.info("YKİ/komşudan BASLAT komutu alındı.")
                self._baslat_olayi.set()
                # YKİ yalnız tek bir drona ulaşsa bile diğerlerine yay (dağıtık güvence)
                self._tasiyici.yayinla("BASLAT", {"kaynak": self._iha_id})

    async def calistir(self) -> None:
        """Görev 1 yaşam döngüsünü uçtan uca yürütür."""
        self._calisiyor = True
        yayin_gorevi = asyncio.create_task(self._durum_yayin_dongusu())
        try:
            self._logger.info("Görev 1 hazır. YKİ 'BASLAT' komutu bekleniyor...")
            await self._baslat_olayi.wait()

            # 1. Eş zamanlı kalkış ve başlangıç formasyonu
            tel = self._dron.telemetri_al()
            self._guvenlik.sifirla(tel.konum_ned, tel.yaw_deg)
            kalkis_hedef = np.array(
                [tel.konum_ned[0], tel.konum_ned[1], -float(self._ayarlar.ucus["kalkis_irtifasi_m"])],
                dtype=float,
            )
            self._dron.hedef_guncelle(tel.konum_ned, tel.yaw_deg)
            await self._dron.arm_ve_offboard_baslat()

            self._logger.info("Eş zamanlı kalkış başlıyor...")
            await self._hedefe_git_ve_senkron_ol(
                kalkis_hedef, tel.yaw_deg, taban_aktif=False, aciklama="Kalkış"
            )
            await self._slotuna_git_ve_senkron_ol(gecis_aktif=True, aciklama="İlk formasyon")

            # 2. QR rotası döngüsü
            qr_no = self._komut_kaynagi.baslangic_qr_no()
            while qr_no != 0:
                qr_hedef = self._qr_konumlari[qr_no]
                hedef_merkez = np.array(
                    [qr_hedef[0], qr_hedef[1], float(self._yapi.merkez_ned[2])], dtype=float
                )

                # Formasyon rotasyonu (merkez sabit, yönelim hedef QR'a döner [5.1])
                yeni_yaw = hedef_yonelim_deg(self._yapi.merkez_ned, hedef_merkez)
                self._yapi.yaw_deg = yeni_yaw
                await self._slotuna_git_ve_senkron_ol(
                    aciklama=f"QR-{qr_no} formasyon rotasyonu (yaw={yeni_yaw:.1f}°)"
                )

                # Hedef QR noktasına sürüyü taşı
                self._yapi.merkez_ned = hedef_merkez
                await self._slotuna_git_ve_senkron_ol(aciklama=f"QR-{qr_no} navigasyonu")

                # Ayrılmış dron bu QR'da sürüye tekrar katılır [5.1]
                if self._iha_id in self._yapi.ayrilan_idleri:
                    self._yapi.ayrilan_idleri.discard(self._iha_id)
                    self._senkron.kendi_ayrilma_durumu_ayarla(False)

                # QR görevini oku (yalnız kendi takım ID'miz)
                paket = await self._komut_kaynagi.qr_gorevini_oku(qr_no)
                self._logger.info(
                    "QR-%d görevi alındı: %d komut, bekleme=%.1f s, sonraki_qr=%d",
                    paket.qr_no,
                    len(paket.komutlar),
                    paket.bekleme_s,
                    paket.sonraki_qr,
                )

                # Komutları sırayla uygula
                for komut_satiri in paket.komutlar:
                    etki = komut_uygula(komut_satiri, self._yapi, self._komut_sinirlari)
                    self._logger.info("QR-%d komutu: %s", qr_no, etki.aciklama)

                    if etki.ayrilacak_iha_id is not None and etki.inis_rengi is not None:
                        if etki.ayrilacak_iha_id == self._iha_id:
                            await self._birey_ayril_ve_katil(etki.inis_rengi)
                        else:
                            # Kalan sürü formasyonu düzeltmez, yerini korur [5.1]
                            await self._slotuna_git_ve_senkron_ol(
                                aciklama=f"İHA-{etki.ayrilacak_iha_id} ayrılırken formasyonu koru"
                            )
                    else:
                        await self._slotuna_git_ve_senkron_ol(
                            gecis_aktif=etki.formasyon_degisti,
                            aciklama=etki.aciklama,
                        )

                    # Bekleme süresi (formasyonda beklerken GPS tutarlılık kontrolü)
                    bekleme = (
                        etki.ek_bekleme_s if etki.ek_bekleme_s is not None else paket.bekleme_s
                    )
                    if bekleme > 0:
                        self._gps_tutarliligi_kontrol_et()
                        await self._yerinde_bekle(bekleme)

                qr_no = paket.sonraki_qr

            # 3. Sonraki QR = 0 -> Home'a dön ve formasyonu bozmadan in [5.1]
            self._yapi.pitch_deg = 0.0
            self._yapi.roll_deg = 0.0
            home_hedef = np.array(
                [self._home_merkezi[0], self._home_merkezi[1], float(self._yapi.merkez_ned[2])],
                dtype=float,
            )
            self._yapi.yaw_deg = hedef_yonelim_deg(self._yapi.merkez_ned, home_hedef)
            await self._slotuna_git_ve_senkron_ol(aciklama="Home formasyon rotasyonu")

            self._yapi.merkez_ned = home_hedef
            await self._slotuna_git_ve_senkron_ol(aciklama="Home dönüşü")

            self._logger.info("Formasyon korunarak güvenli iniş başlıyor...")
            await self._dron.inis_yap_ve_bekle()
            self._logger.info("Görev 1 başarıyla tamamlandı.")
        finally:
            self._calisiyor = False
            yayin_gorevi.cancel()
            await asyncio.gather(yayin_gorevi, return_exceptions=True)

    async def _birey_ayril_ve_katil(self, renk: str) -> None:
        """Ayrılan dronun renkli alana inip disarm olması, kalkıp sürüye geri katılması [5.1]."""
        self._senkron.kendi_ayrilma_durumu_ayarla(True)
        alan_ned = self._senkron.renkli_alan_al(renk)
        if alan_ned is None:
            alan_ned = self._sim_renkli_alanlar.get(renk)
        if alan_ned is None:
            self._logger.error("'%s' renkli alan konumu bilinmiyor; ayrılma iptal.", renk)
            self._senkron.kendi_ayrilma_durumu_ayarla(False)
            self._yapi.ayrilan_idleri.discard(self._iha_id)
            return

        self._logger.info("Ayrılma başladı -> %s alan [%.1f, %.1f]", renk, alan_ned[0], alan_ned[1])
        ust_hedef = np.array(
            [alan_ned[0], alan_ned[1], -float(self._ayarlar.sartname["min_irtifa_m"])],
            dtype=float,
        )
        await self._tekil_hedefe_git(ust_hedef, self._yapi.yaw_deg, taban_aktif=True)

        # Renkli alana in ve disarm ol
        await self._dron.inis_yap_ve_bekle()
        await asyncio.sleep(float(self._ayarlar.ucus["ayrilma_yerde_bekleme_s"]))

        # Tekrar arm ol, kalk ve sürüye katıl
        tel = self._dron.telemetri_al()
        self._guvenlik.sifirla(tel.konum_ned, tel.yaw_deg)
        self._dron.hedef_guncelle(tel.konum_ned, tel.yaw_deg)
        await self._dron.arm_ve_offboard_baslat()

        kalkis_hedef = np.array(
            [tel.konum_ned[0], tel.konum_ned[1], float(self._yapi.merkez_ned[2])],
            dtype=float,
        )
        await self._tekil_hedefe_git(kalkis_hedef, self._yapi.yaw_deg, taban_aktif=False)

        self._yapi.ayrilan_idleri.discard(self._iha_id)
        self._senkron.kendi_ayrilma_durumu_ayarla(False)
        self._logger.info("Renkli alandan kalkış tamamlandı, sürüye katılınıyor.")

    async def _slotuna_git_ve_senkron_ol(
        self, gecis_aktif: bool = False, aciklama: str = ""
    ) -> None:
        hedef = self._yapi.slot_hedefi_ned(self._iha_id)
        if gecis_aktif:
            # Önce kendi irtifa katmanında yatay yerleş, sonra hedef irtifaya in
            await self._hedefe_git_ve_senkron_ol(
                hedef, self._yapi.yaw_deg, taban_aktif=True, gecis_aktif=True,
                aciklama=f"{aciklama} (katmanlı geçiş)",
            )
        await self._hedefe_git_ve_senkron_ol(
            hedef, self._yapi.yaw_deg, taban_aktif=True, gecis_aktif=False, aciklama=aciklama
        )

    async def _hedefe_git_ve_senkron_ol(
        self,
        hedef_ned: np.ndarray,
        hedef_yaw_deg: float,
        taban_aktif: bool = True,
        gecis_aktif: bool = False,
        aciklama: str = "",
    ) -> None:
        self._adim_sayaci += 1
        self._senkron.yeni_adima_gec(self._adim_sayaci)
        self._logger.info("Adım %d başladı: %s", self._adim_sayaci, aciklama)

        await self._tekil_hedefe_git(hedef_ned, hedef_yaw_deg, taban_aktif, gecis_aktif)
        self._senkron.kendi_adimini_bitir()

        # Aktif komşuların bu adımı bitirmesini bekle (zaman aşımıyla kilitlenmeyi önle)
        aralik = 1.0 / float(self._ayarlar.ucus["setpoint_frekansi_hz"])
        zaman_asimi = float(self._ayarlar.ucus["adim_zaman_asimi_s"])
        baslangic = time.monotonic()
        while not self._senkron.herkes_adimi_bitirdi_mi():
            if (time.monotonic() - baslangic) > zaman_asimi:
                self._logger.warning("Adım %d senkron zaman aşımı; devam ediliyor.", self._adim_sayaci)
                break
            tel = self._dron.telemetri_al()
            guvenli, g_yaw = self._guvenlik.hedefi_suz(
                hedef_ned, hedef_yaw_deg, tel.konum_ned,
                self._senkron.komsu_konumlari(), aralik,
                taban_aktif=taban_aktif, gecis_aktif=gecis_aktif,
            )
            self._dron.hedef_guncelle(guvenli, g_yaw)
            await asyncio.sleep(aralik)

    async def _tekil_hedefe_git(
        self,
        hedef_ned: np.ndarray,
        hedef_yaw_deg: float,
        taban_aktif: bool = True,
        gecis_aktif: bool = False,
    ) -> None:
        aralik = 1.0 / float(self._ayarlar.ucus["setpoint_frekansi_hz"])
        konum_tol = float(self._ayarlar.ucus["konum_varis_toleransi_m"])
        yaw_tol = float(self._ayarlar.ucus["yaw_varis_toleransi_deg"])
        zaman_asimi = float(self._ayarlar.ucus["adim_zaman_asimi_s"])
        baslangic = time.monotonic()

        while True:
            tel = self._dron.telemetri_al()
            self._rota_renk_tara(tel.konum_ned, tel.yaw_deg)

            guvenli, g_yaw = self._guvenlik.hedefi_suz(
                hedef_ned, hedef_yaw_deg, tel.konum_ned,
                self._senkron.komsu_konumlari(), aralik,
                taban_aktif=taban_aktif, gecis_aktif=gecis_aktif,
            )
            self._dron.hedef_guncelle(guvenli, g_yaw)

            # Katmanlı geçişte gerçek hedef katman ofsetini içerir
            beklenen = hedef_ned.copy()
            beklenen[2] += self._guvenlik.gecis_irtifa_ofseti_m(gecis_aktif)
            mesafe = float(np.linalg.norm(tel.konum_ned - beklenen))
            yaw_fark = abs(en_kisa_aci_farki_deg(hedef_yaw_deg, tel.yaw_deg))

            if mesafe <= konum_tol and yaw_fark <= yaw_tol:
                break
            if (time.monotonic() - baslangic) > zaman_asimi:
                self._logger.warning("Hedefe varış zaman aşımı (kalan=%.2f m)", mesafe)
                break
            await asyncio.sleep(aralik)

    async def _yerinde_bekle(self, sure_s: float) -> None:
        aralik = 1.0 / float(self._ayarlar.ucus["setpoint_frekansi_hz"])
        bitis = time.monotonic() + sure_s
        hedef = self._yapi.slot_hedefi_ned(self._iha_id)
        while time.monotonic() < bitis:
            tel = self._dron.telemetri_al()
            guvenli, g_yaw = self._guvenlik.hedefi_suz(
                hedef, self._yapi.yaw_deg, tel.konum_ned,
                self._senkron.komsu_konumlari(), aralik, taban_aktif=True,
            )
            self._dron.hedef_guncelle(guvenli, g_yaw)
            await asyncio.sleep(aralik)

    def _rota_renk_tara(self, konum_ned: np.ndarray, yaw_deg: float) -> None:
        """Rota üzerinde kameradan (veya simülasyon yakınlığından) renkli alanları kaydeder."""
        kare = self._kamera.kare_oku()
        if kare is not None:
            for tespit in self._renk_algilayici.kare_isle(kare, konum_ned, yaw_deg):
                if self._senkron.renkli_alan_al(tespit.renk) is None:
                    self._senkron.renkli_alan_kaydet(tespit.renk, tespit.yer_konum_ned)
                    self._logger.info(
                        "Kamerayla '%s' alan keşfedildi: [%.1f, %.1f]",
                        tespit.renk, tespit.yer_konum_ned[0], tespit.yer_konum_ned[1],
                    )
            return

        # Kamera akışı yoksa simülasyonda alanın yakınından geçildiğinde keşfedilmiş say
        for renk, alan_ned in self._sim_renkli_alanlar.items():
            if self._senkron.renkli_alan_al(renk) is None:
                yatay = float(np.linalg.norm(konum_ned[:2] - alan_ned[:2]))
                if yatay <= float(-konum_ned[2]):
                    self._senkron.renkli_alan_kaydet(renk, alan_ned)
                    self._logger.info("Rota üzerinde '%s' alan kaydedildi.", renk)

    def _gps_tutarliligi_kontrol_et(self) -> None:
        tel = self._dron.telemetri_al()
        komsular = self._senkron.komsu_konumlari()
        beklenenler = {
            cid: self._yapi.beklenen_komsu_mesafesi_m(self._iha_id, cid)
            for cid in komsular
        }
        self._guvenlik.gps_tutarlilik_kontrolu(tel.konum_ned, komsular, beklenenler)

    async def _durum_yayin_dongusu(self) -> None:
        aralik = float(self._ayarlar.ucus["durum_yayin_araligi_s"])
        while self._calisiyor:
            tel = self._dron.telemetri_al()
            paket = self._senkron.durum_paketi_olustur(tel.konum_ned, tel.gps_saglikli)
            self._tasiyici.yayinla("DURUM", paket)
            await asyncio.sleep(aralik)
