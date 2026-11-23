"""Görev 2 — Yarı Otonom Sürü Kontrolü (tek kumandadan hareket, manevra ve formasyon)."""

from __future__ import annotations

import asyncio
import logging
import math
import time
import numpy as np

from yazilim.ag.mesaj import AgMesaji
from yazilim.ag.udp_tasiyici import Tasiyici
from yazilim.dron.mavsdk_dron import MavsdkDron
from yazilim.guvenlik.son_kapi import GuvenlikKapisi
from yazilim.ortak.ayarlar import Ayarlar
from yazilim.ortak.konum_kaydi import FAZ_INIS, FAZ_KALKIS, FAZ_UCUS, FAZ_YERDE, KonumKaydi
from yazilim.ortak.koordinat import aci_normalize_deg
from yazilim.suru.formasyonlar import kanonik_formasyon_adi
from yazilim.suru.sanal_yapi import SanalYapi
from yazilim.suru.senkron import DagitimSenkron
from yazilim.suru.slot_atama import SlotAtamaUzlasmasi


class Gorev2YariOtonom:
    """Tek joystick/klavye girdisini tüm dronlarda senkron uygulayan dağıtık Görev 2 yürütücüsü."""

    def __init__(
        self,
        iha_id: int,
        toplam_iha: int,
        ayarlar: Ayarlar,
        dron: MavsdkDron,
        tasiyici: Tasiyici,
        guvenlik: GuvenlikKapisi,
        senkron: DagitimSenkron,
        logger: logging.Logger,
        konum_kaydi: KonumKaydi | None = None,
    ) -> None:
        self._konum_kaydi = konum_kaydi
        self._faz = FAZ_YERDE
        self._iha_id = iha_id
        self._ayarlar = ayarlar
        self._dron = dron
        self._tasiyici = tasiyici
        self._guvenlik = guvenlik
        self._senkron = senkron
        self._logger = logger

        home = np.asarray(ayarlar.saha["home_merkezi_ned"], dtype=float)
        kalkis_irtifa = float(ayarlar.ucus["kalkis_irtifasi_m"])
        self._yapi = SanalYapi(
            toplam_iha=toplam_iha,
            merkez_ned=np.array([home[0], home[1], -kalkis_irtifa], dtype=float),
            formasyon_adi=str(ayarlar.ucus["varsayilan_formasyon"]),
            aralik_m=float(ayarlar.ucus["varsayilan_aralik_m"]),
        )

        self._toplam_iha = toplam_iha
        self._atama_uzlasmasi = SlotAtamaUzlasmasi(
            iha_id=iha_id,
            toplam_iha=toplam_iha,
            tasiyici=tasiyici,
            logger=logger,
            yayin_araligi_s=float(ayarlar.ucus["durum_yayin_araligi_s"]),
            zaman_asimi_s=float(ayarlar.ucus["slot_atama_uzlasma_zaman_asimi_s"]),
        )

        self._mod = "hareket"  # "hareket" (Sürü Hareket Modu) veya "manevra" (Manevra Modu)
        self._ileri = 0.0
        self._sag = 0.0
        self._yukari = 0.0
        self._yaw = 0.0
        self._son_kumanda_s = 0.0

        self._kalkis_istendi = asyncio.Event()
        self._inis_istendi = asyncio.Event()
        self._calisiyor = False

        self._tasiyici.mesaj_dinleyici_ekle(self._mesaj_isle)

    def _mesaj_isle(self, mesaj: AgMesaji) -> None:
        if mesaj.tip == "DURUM":
            self._senkron.komsu_guncelle(mesaj.gonderen, mesaj.veri)
            return
        if mesaj.tip != "KUMANDA":
            return

        veri = mesaj.veri
        self._son_kumanda_s = time.monotonic()

        eylem = str(veri.get("eylem", "cubuk")).lower()
        if eylem == "kalkis":
            self._kalkis_istendi.set()
        elif eylem == "inis":
            self._inis_istendi.set()
        elif eylem == "mod":
            yeni_mod = str(veri.get("deger", "hareket")).lower()
            if yeni_mod in ("hareket", "manevra"):
                self._mod = yeni_mod
                self._logger.info("Görev 2 modu değişti -> %s", self._mod)
        elif eylem == "formasyon":
            try:
                yeni_frm = kanonik_formasyon_adi(str(veri.get("deger", "")))
                self._yapi.formasyon_adi = yeni_frm
                self._yapi.pitch_deg = 0.0
                self._yapi.roll_deg = 0.0
                self._logger.info("Görev 2 formasyon -> %s", yeni_frm)
            except ValueError as hata:
                self._logger.warning("Geçersiz formasyon komutu: %s", hata)
        elif eylem == "cubuk":
            self._ileri = max(-1.0, min(1.0, float(veri.get("ileri", 0.0))))
            self._sag = max(-1.0, min(1.0, float(veri.get("sag", 0.0))))
            self._yukari = max(-1.0, min(1.0, float(veri.get("yukari", 0.0))))
            self._yaw = max(-1.0, min(1.0, float(veri.get("yaw", 0.0))))

    async def calistir(self) -> None:
        """Kumandadan kalkış bekler, hareket/manevra döngüsünü çalıştırır, inişle bitirir."""
        self._calisiyor = True
        yayin_gorevi = asyncio.create_task(self._durum_yayin_dongusu())
        try:
            self._logger.info("Görev 2 hazır. Kumandadan 'kalkis' komutu bekleniyor...")
            await self._kalkis_istendi.wait()

            # Karışık dizilimde dronlar yerdeki konumlarına en uygun slota atanır (kalkıştan önce)
            if bool(self._ayarlar.ucus["slot_atama_acik"]):
                konumlar = {self._iha_id: self._dron.telemetri_al().konum_ned, **self._senkron.komsu_konumlari()}
                slotlar = {n: self._yapi.slot_no_hedefi_ned(n) for n in range(1, self._toplam_iha + 1)}
                self._yapi.atama_ayarla(
                    await self._atama_uzlasmasi.belirle(
                        konumlar,
                        slotlar,
                        float(self._ayarlar.ucus["slot_atama_konum_yuvarlama_m"]),
                        float(self._ayarlar.ucus["slot_atama_kimlik_tercihi_m"]),
                    )
                )
                self._logger.info("Bu dronun slotu: %d", self._yapi.slot_no(self._iha_id))

            tel = self._dron.telemetri_al()
            self._guvenlik.sifirla(tel.konum_ned, tel.yaw_deg)
            self._dron.hedef_guncelle(tel.konum_ned, tel.yaw_deg)
            await self._dron.arm_ve_offboard_baslat()
            self._faz = FAZ_KALKIS

            # İlk kalkış (10 m tabanına ulaşana kadar)
            aralik = 1.0 / float(self._ayarlar.ucus["setpoint_frekansi_hz"])
            min_irtifa = float(self._ayarlar.sartname["min_irtifa_m"])
            maks_irtifa = float(self._ayarlar.ucus["maks_irtifa_m"])
            maks_egim = float(self._ayarlar.ucus["maks_egim_acisi_deg"])
            hareket_hizi = float(self._ayarlar.ucus["gorev2_hareket_hizi_m_s"])
            irtifa_hizi = float(self._ayarlar.ucus["gorev2_irtifa_hizi_m_s"])
            yaw_hizi = float(self._ayarlar.ucus["gorev2_yaw_hizi_deg_s"])
            egim_hizi = float(self._ayarlar.ucus["gorev2_egim_hizi_deg_s"])
            kumanda_zaman_asimi = float(self._ayarlar.ucus["gorev2_kumanda_zaman_asimi_s"])

            taban_ulasildi = False
            while not self._inis_istendi.is_set():
                tel = self._dron.telemetri_al()
                if -tel.konum_ned[2] >= min_irtifa:
                    taban_ulasildi = True
                    self._faz = FAZ_UCUS

                # Kumanda paketi kesilirse çubuk girdilerini sıfırla (havada sabit kal)
                if (time.monotonic() - self._son_kumanda_s) > kumanda_zaman_asimi:
                    ileri, sag, yukari, yaw_girdi = 0.0, 0.0, 0.0, 0.0
                else:
                    ileri, sag, yukari, yaw_girdi = (
                        self._ileri, self._sag, self._yukari, self._yaw
                    )

                # Her iki modda da throttle (yukarı/aşağı) ve yaw (merkez sabit rotasyon) çalışır
                self._yapi.merkez_ned[2] -= yukari * irtifa_hizi * aralik
                self._yapi.merkez_ned[2] = max(
                    -maks_irtifa, min(-min_irtifa, float(self._yapi.merkez_ned[2]))
                )
                self._yapi.yaw_deg = aci_normalize_deg(
                    self._yapi.yaw_deg + yaw_girdi * yaw_hizi * aralik
                )

                if self._mod == "hareket":
                    # Sürü Hareket Modu: formasyonu koruyarak gövde yönünde ileri/geri ve sağ/sol
                    psi = math.radians(self._yapi.yaw_deg)
                    d_kuzey = (ileri * math.cos(psi) - sag * math.sin(psi)) * hareket_hizi * aralik
                    d_dogu = (ileri * math.sin(psi) + sag * math.cos(psi)) * hareket_hizi * aralik
                    self._yapi.merkez_ned[0] += d_kuzey
                    self._yapi.merkez_ned[1] += d_dogu
                else:
                    # Manevra Modu: merkez sabit, topluca pitch ve roll eğimi [5.2.2]
                    # İleri pitch girdisi burnu aşağı eğer (-pitch)
                    self._yapi.pitch_deg = max(
                        -maks_egim,
                        min(maks_egim, self._yapi.pitch_deg - ileri * egim_hizi * aralik),
                    )
                    self._yapi.roll_deg = max(
                        -maks_egim,
                        min(maks_egim, self._yapi.roll_deg + sag * egim_hizi * aralik),
                    )
                    self._yapi.egim_icin_taban_koru(min_irtifa)

                hedef = self._yapi.slot_hedefi_ned(self._iha_id)
                guvenli, g_yaw = self._guvenlik.hedefi_suz(
                    hedef, self._yapi.yaw_deg, tel.konum_ned,
                    self._senkron.komsu_konumlari(), aralik,
                    taban_aktif=taban_ulasildi,
                )
                self._dron.hedef_guncelle(guvenli, g_yaw)
                await asyncio.sleep(aralik)

            self._logger.info("Kumandadan iniş komutu alındı; güvenli iniş başlıyor...")
            self._faz = FAZ_INIS
            await self._dron.inis_yap_ve_bekle()
            self._faz = FAZ_YERDE
            self._logger.info("Görev 2 başarıyla tamamlandı.")
        finally:
            self._calisiyor = False
            yayin_gorevi.cancel()
            await asyncio.gather(yayin_gorevi, return_exceptions=True)

    async def _durum_yayin_dongusu(self) -> None:
        aralik = float(self._ayarlar.ucus["durum_yayin_araligi_s"])
        while self._calisiyor:
            tel = self._dron.telemetri_al()
            paket = self._senkron.durum_paketi_olustur(tel.konum_ned, tel.gps_saglikli)
            self._tasiyici.yayinla("DURUM", paket)
            if self._konum_kaydi is not None:
                self._konum_kaydi.yaz(
                    tel, self._dron.hedef_ortak_ned, self._yapi.slot_hedefi_ned(self._iha_id),
                    0, self._faz, f"mod={self._mod}",
                )
            await asyncio.sleep(aralik)
