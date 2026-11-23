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
from yazilim.ortak.konum_kaydi import (
    FAZ_AYRILMA,
    FAZ_INIS,
    FAZ_KALKIS,
    FAZ_UCUS,
    FAZ_YERDE,
    KonumKaydi,
)
from yazilim.ortak.koordinat import (
    en_kisa_aci_farki_deg,
    hedef_yonelim_deg,
    yaw_ara_adimlari,
    yukaridan_yaklasma_noktalari,
)
from yazilim.suru.komutlar import komut_uygula
from yazilim.suru.sanal_yapi import SanalYapi
from yazilim.suru.senkron import DagitimSenkron
from yazilim.suru.slot_atama import SlotAtamaUzlasmasi


class Gorev1DinamikSuru:
    """Her dronda aynı biçimde çalışan lidersiz Görev 1 yürütücüsü.

    Adım numarası tüm dronlarda aynı olayları aynı sırayla sayar. Ayrılan dron havada olmasa
    da görev akışını "mantıksal" olarak (uçuşsuz) sürüyle birlikte izler; böylece geri
    döndüğünde sayacı ve sanal yapısı sürüyle aynıdır ve sürü onu beklemek zorunda kalmaz.
    """

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
        konum_kaydi: KonumKaydi | None = None,
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
        self._konum_kaydi = konum_kaydi

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
        self._atama_uzlasmasi = SlotAtamaUzlasmasi(
            iha_id=iha_id,
            toplam_iha=toplam_iha,
            tasiyici=tasiyici,
            logger=logger,
            yayin_araligi_s=float(ayarlar.ucus["durum_yayin_araligi_s"]),
            zaman_asimi_s=float(ayarlar.ucus["slot_atama_uzlasma_zaman_asimi_s"]),
        )

        # Birey ayrılma durumu: ayrık dron uçuşunu arka plan görevi yürütür, ana akış mantıksaldır
        self._ayrik = False
        self._ayrilma_gorevi: asyncio.Task[None] | None = None
        # Ayrılan dronlar (tüm dronlarca aynı bilinir). Sonraki QR'daki katılım adımı bu listeye bakar;
        # dron erken dönse bile liste değişmez, böylece herkes aynı sayıda adım sayar.
        self._katilim_beklenenleri: set[int] = set()

        # Konum kaydı için anlık faz ve adım açıklaması
        self._faz = FAZ_YERDE
        self._adim_aciklamasi = ""

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

            # Karışık dizilimde dronlar yerdeki konumlarına en uygun slota atanır (kalkıştan önce)
            await self._slot_atamasini_yap()

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
            self._faz = FAZ_KALKIS
            await self._hedefe_git_ve_senkron_ol(
                kalkis_hedef, tel.yaw_deg, taban_aktif=False, aciklama="Kalkış"
            )
            self._faz = FAZ_UCUS
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
                await self._formasyonu_dondur(yeni_yaw, f"QR-{qr_no} formasyon rotasyonu")

                # Hedef QR noktasına sürüyü taşı
                self._yapi.merkez_ned = hedef_merkez
                await self._slotuna_git_ve_senkron_ol(aciklama=f"QR-{qr_no} navigasyonu")

                # Ayrılan birey en geç bu QR'da sürüye katılır [5.1]. Sürü QR'ı okumadan önce bekler;
                # böylece formasyon ve manevra komutları tüm dronlarla uygulanır (Tablo 7: en az 3 İHA).
                await self._ayrilan_katilimini_sagla(f"QR-{qr_no}: ayrılan dronun katılımı")

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
                        self._katilim_beklenenleri.add(etki.ayrilacak_iha_id)
                        if etki.ayrilacak_iha_id == self._iha_id:
                            self._birey_ayrilmayi_baslat(etki.inis_rengi)
                        # Herkes aynı adımı sayar. Kalan sürü formasyonu düzeltmez, yerini korur [5.1];
                        # ayrılan dron ise bu adımı uçuşsuz (mantıksal) izler.
                        await self._slotuna_git_ve_senkron_ol(
                            aciklama=f"İHA-{etki.ayrilacak_iha_id} ayrılıyor, formasyon korunuyor"
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
                    if bekleme > 0 and not self._ayrik:
                        self._gps_tutarliligi_kontrol_et()
                        await self._yerinde_bekle(bekleme)

                qr_no = paket.sonraki_qr

            # 3. Sonraki QR = 0 -> Home'a dön ve formasyonu bozmadan in [5.1]
            await self._ayrilan_katilimini_sagla("Home öncesi: ayrılan dronun katılımı")
            self._yapi.pitch_deg = 0.0
            self._yapi.roll_deg = 0.0
            home_hedef = np.array(
                [self._home_merkezi[0], self._home_merkezi[1], float(self._yapi.merkez_ned[2])],
                dtype=float,
            )
            await self._formasyonu_dondur(
                hedef_yonelim_deg(self._yapi.merkez_ned, home_hedef), "Home formasyon rotasyonu"
            )

            self._yapi.merkez_ned = home_hedef
            await self._slotuna_git_ve_senkron_ol(aciklama="Home dönüşü")

            self._logger.info("Formasyon korunarak güvenli iniş başlıyor...")
            self._faz = FAZ_INIS
            self._adim_aciklamasi = "İniş"
            await self._dron.inis_yap_ve_bekle()
            self._faz = FAZ_YERDE
            self._logger.info("Görev 1 başarıyla tamamlandı.")
        finally:
            self._calisiyor = False
            yayin_gorevi.cancel()
            await asyncio.gather(yayin_gorevi, return_exceptions=True)

    async def _slot_atamasini_yap(self) -> None:
        """Yerdeki (hareketsiz) konumlara bakıp dron -> slot eşlemesini belirler; tüm dronlar aynı sonucu bulur."""
        if not bool(self._ayarlar.ucus["slot_atama_acik"]):
            return
        konumlar = {self._iha_id: self._dron.telemetri_al().konum_ned, **self._senkron.komsu_konumlari()}
        slotlar = {n: self._yapi.slot_no_hedefi_ned(n) for n in range(1, self._toplam_iha + 1)}
        atama = await self._atama_uzlasmasi.belirle(
            konumlar,
            slotlar,
            float(self._ayarlar.ucus["slot_atama_konum_yuvarlama_m"]),
            float(self._ayarlar.ucus["slot_atama_kimlik_tercihi_m"]),
        )
        self._yapi.atama_ayarla(atama)
        self._logger.info("Bu dronun slotu: %d", self._yapi.slot_no(self._iha_id))

    # ------------------------------------------------------------------ birey ayrılma / katılma

    def _birey_ayrilmayi_baslat(self, renk: str) -> None:
        """Bu dron ayrılacaksa renkli alana iniş ve tekrar kalkışı arka plan görevi olarak başlatır [5.1]."""
        alan_ned = self._senkron.renkli_alan_al(renk)
        if alan_ned is None:
            alan_ned = self._sim_renkli_alanlar.get(renk)
        if alan_ned is None:
            self._logger.error("'%s' renkli alan konumu bilinmiyor; ayrılma iptal.", renk)
            self._yapi.ayrilan_idleri.discard(self._iha_id)
            return

        self._ayrik = True
        self._senkron.kendi_ayrilma_durumu_ayarla(True)
        self._faz = FAZ_AYRILMA
        self._ayrilma_gorevi = asyncio.create_task(self._ayrilma_ucusu(renk, alan_ned))

    async def _ayrilma_ucusu(self, renk: str, alan_ned: np.ndarray) -> None:
        """Renkli alana in, disarm ol, bekle, tekrar arm ol ve sürü irtifasına kalk."""
        self._logger.info("Ayrılma başladı -> %s alan [%.1f, %.1f]", renk, alan_ned[0], alan_ned[1])
        ust_hedef = np.array(
            [alan_ned[0], alan_ned[1], -float(self._ayarlar.sartname["min_irtifa_m"])],
            dtype=float,
        )
        await self._tekil_hedefe_git(ust_hedef, self._yapi.yaw_deg, taban_aktif=True)

        # Renkli alana in ve disarm ol
        await self._dron.inis_yap_ve_bekle()

        # İniş doğruluğu: şartname alan merkezinden 2.5 m içini ister [5.1]
        konum = self._dron.telemetri_al().konum_ned
        sapma = float(np.linalg.norm(konum[:2] - alan_ned[:2]))
        tolerans = float(self._ayarlar.sartname["inis_tolerans_m"])
        if sapma <= tolerans:
            self._logger.info("Renkli alana iniş: merkezden %.2f m (sınır %.1f m) — geçerli", sapma, tolerans)
        else:
            self._logger.warning("Renkli alana iniş: merkezden %.2f m (sınır %.1f m) — GEÇERSİZ", sapma, tolerans)

        await asyncio.sleep(float(self._ayarlar.ucus["ayrilma_yerde_bekleme_s"]))

        # Tekrar arm ol, kalk; sürüye katılım ana akışta bir sonraki adım başında yapılır
        tel = self._dron.telemetri_al()
        self._guvenlik.sifirla(tel.konum_ned, tel.yaw_deg)
        self._dron.hedef_guncelle(tel.konum_ned, tel.yaw_deg)
        await self._dron.arm_ve_offboard_baslat()

        kalkis_hedef = np.array(
            [tel.konum_ned[0], tel.konum_ned[1], float(self._yapi.merkez_ned[2])],
            dtype=float,
        )
        await self._tekil_hedefe_git(kalkis_hedef, self._yapi.yaw_deg, taban_aktif=False)
        self._logger.info("Renkli alandan kalkış tamamlandı, sürüye katılmaya hazır.")

    def _katilima_hazir_mi(self) -> bool:
        """Ayrılma uçuşu bittiyse True döner; uçuş hata verdiyse hatayı yutmadan yukarı iletir."""
        if self._ayrilma_gorevi is None or not self._ayrilma_gorevi.done():
            return False
        self._ayrilma_gorevi.result()
        return True

    def _suruye_katil(self) -> None:
        """Ayrık dronu sürüye geri alır; bundan sonraki adımlar uçuşludur."""
        self._ayrik = False
        self._ayrilma_gorevi = None
        self._yapi.ayrilan_idleri.discard(self._iha_id)
        self._senkron.kendi_ayrilma_durumu_ayarla(False)
        self._faz = FAZ_UCUS
        self._logger.info("Sürüye katılıyor (adım %d'den itibaren uçuşlu).", self._adim_sayaci + 1)

    async def _ayrilan_katilimini_sagla(self, aciklama: str) -> None:
        """Bu QR'a kadar ayrılan birey varsa tüm dronlar katılım adımını birlikte yapar [5.1].

        Sürü slotlarında bekler; ayrılan dron uçuşunu bitirip slotuna oturunca adım biter.
        Ayrılan dron düşer/susarsa komşular onu canlı listeden düşürür ve beklemeyi bırakır;
        ayrıca en çok ayrilma_tamamlama_zaman_asimi_s kadar beklenir (kilitlenme önlemi).
        """
        if not self._katilim_beklenenleri:
            return
        zaman_asimi = float(self._ayarlar.ucus["ayrilma_tamamlama_zaman_asimi_s"])
        baslangic = time.monotonic()

        if self._ayrik and self._ayrilma_gorevi is not None:
            # Ayrılan dron: önce uçuşunu bitirir (sürü bu adımda onu bekliyor), sonra slotuna uçar
            await asyncio.wait({self._ayrilma_gorevi}, timeout=zaman_asimi)
            if not self._ayrilma_gorevi.done():
                self._logger.error("Ayrılma uçuşu %.0f s içinde bitmedi; iptal ediliyor.", zaman_asimi)
                self._ayrilma_gorevi.cancel()
                await asyncio.gather(self._ayrilma_gorevi, return_exceptions=True)
                self._ayrilma_gorevi = None

        await self._slotuna_git_ve_senkron_ol(
            aciklama=aciklama, ayrilmislari_bekle=True, bariyer_zaman_asimi_s=zaman_asimi
        )
        self._logger.info(
            "Ayrılan dron katılım adımı: %.1f s sürdü (ayrılanlar=%s).",
            time.monotonic() - baslangic, sorted(self._katilim_beklenenleri),
        )
        # Slot artık dolu: tüm dronlar aynı anda listeyi temizler
        self._yapi.ayrilan_idleri -= self._katilim_beklenenleri
        self._katilim_beklenenleri.clear()

    # ------------------------------------------------------------------ adım yürütme

    async def _formasyonu_dondur(self, hedef_yaw_deg: float, aciklama: str) -> None:
        """Formasyonu merkez sabit, küçük yaw adımlarıyla döndürür (slotlar yay üzerinde kalır [5.1])."""
        adim_deg = float(self._ayarlar.ucus["rotasyon_adim_deg"])
        yawlar = yaw_ara_adimlari(self._yapi.yaw_deg, hedef_yaw_deg, adim_deg)
        for sira, yaw in enumerate(yawlar, start=1):
            self._yapi.yaw_deg = yaw
            await self._slotuna_git_ve_senkron_ol(
                aciklama=f"{aciklama} ({sira}/{len(yawlar)}, yaw={yaw:.0f}°)",
                ara_adim=sira < len(yawlar),
            )

    async def _slotuna_git_ve_senkron_ol(
        self,
        gecis_aktif: bool = False,
        aciklama: str = "",
        ara_adim: bool = False,
        ayrilmislari_bekle: bool = False,
        bariyer_zaman_asimi_s: float | None = None,
    ) -> None:
        # Ayrık dron henüz dönmediyse bu adımı uçuşsuz izler; hazırsa bu adımda sürüye katılır.
        yukaridan_yaklas = False
        if self._ayrik:
            if self._katilima_hazir_mi():
                self._suruye_katil()
                yukaridan_yaklas = True  # formasyonun içinden geçmesin: üstten yaklaş
            else:
                # Katmanlı geçiş diğer dronlarda 2 adım sayıldığı için burada da 2 sayılır
                for _ in range(2 if gecis_aktif else 1):
                    await self._mantiksal_adim(aciklama)
                return

        hedef = self._yapi.slot_hedefi_ned(self._iha_id)
        if gecis_aktif:
            # Önce kendi irtifa katmanında yatay yerleş, sonra hedef irtifaya in
            await self._hedefe_git_ve_senkron_ol(
                hedef, self._yapi.yaw_deg, taban_aktif=True, gecis_aktif=True,
                aciklama=f"{aciklama} (katmanlı geçiş)", yukaridan_yaklas=yukaridan_yaklas,
            )
            yukaridan_yaklas = False
        await self._hedefe_git_ve_senkron_ol(
            hedef, self._yapi.yaw_deg, taban_aktif=True, gecis_aktif=False,
            aciklama=aciklama, ara_adim=ara_adim,
            ayrilmislari_bekle=ayrilmislari_bekle, bariyer_zaman_asimi_s=bariyer_zaman_asimi_s,
            yukaridan_yaklas=yukaridan_yaklas,
        )

    async def _mantiksal_adim(self, aciklama: str) -> None:
        """Uçuşsuz adım: sayacı sürüyle aynı tutar, komşular adımı bitirene kadar bekler."""
        self._adim_sayaci += 1
        self._adim_aciklamasi = aciklama
        self._senkron.yeni_adima_gec(self._adim_sayaci)
        self._logger.info("Adım %d (ayrık, uçuşsuz): %s", self._adim_sayaci, aciklama)

        aralik = 1.0 / float(self._ayarlar.ucus["setpoint_frekansi_hz"])
        zaman_asimi = float(self._ayarlar.ucus["adim_zaman_asimi_s"])
        baslangic = time.monotonic()
        while not self._senkron.aktif_komsular_adimi_bitirdi_mi(self._adim_sayaci):
            if self._katilima_hazir_mi():
                break  # hazırım: bir sonraki adımda sürüye katılacağım, beklemeyi bırak
            if (time.monotonic() - baslangic) > zaman_asimi:
                self._logger.warning("Ayrık adım %d zaman aşımı; devam ediliyor.", self._adim_sayaci)
                break
            await asyncio.sleep(aralik)
        self._senkron.kendi_adimini_bitir()

    async def _hedefe_git_ve_senkron_ol(
        self,
        hedef_ned: np.ndarray,
        hedef_yaw_deg: float,
        taban_aktif: bool = True,
        gecis_aktif: bool = False,
        aciklama: str = "",
        ara_adim: bool = False,
        ayrilmislari_bekle: bool = False,
        bariyer_zaman_asimi_s: float | None = None,
        yukaridan_yaklas: bool = False,
    ) -> None:
        self._adim_sayaci += 1
        self._adim_aciklamasi = aciklama
        self._senkron.yeni_adima_gec(self._adim_sayaci)
        self._logger.info("Adım %d başladı: %s", self._adim_sayaci, aciklama)

        if yukaridan_yaklas:
            await self._yukaridan_yaklas(hedef_ned, hedef_yaw_deg, taban_aktif, gecis_aktif)
        await self._tekil_hedefe_git(hedef_ned, hedef_yaw_deg, taban_aktif, gecis_aktif, ara_adim)
        self._senkron.kendi_adimini_bitir()

        # Aktif komşuların bu adımı bitirmesini bekle (zaman aşımıyla kilitlenmeyi önle)
        aralik = 1.0 / float(self._ayarlar.ucus["setpoint_frekansi_hz"])
        zaman_asimi = (
            bariyer_zaman_asimi_s
            if bariyer_zaman_asimi_s is not None
            else float(self._ayarlar.ucus["adim_zaman_asimi_s"])
        )
        baslangic = time.monotonic()
        while not self._senkron.herkes_adimi_bitirdi_mi(ayrilmislari_bekle=ayrilmislari_bekle):
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

    async def _yukaridan_yaklas(
        self, hedef_ned: np.ndarray, hedef_yaw_deg: float, taban_aktif: bool, gecis_aktif: bool
    ) -> None:
        """Geri katılan dron slotuna formasyonun üstünden yaklaşır; alçalma çağıranın normal hedef hareketidir."""
        yukseklik = float(self._ayarlar.ucus["katilim_yaklasma_yuksekligi_m"])
        mevcut = self._dron.telemetri_al().konum_ned
        self._logger.info("Sürüye yukarıdan katılma: slotun %.1f m üstünden yaklaşılıyor.", yukseklik)
        for nokta in yukaridan_yaklasma_noktalari(mevcut, hedef_ned, yukseklik):
            # Ara noktalarda gevşek tolerans: dur-kalk yapmadan bir sonraki noktaya geç
            await self._tekil_hedefe_git(nokta, hedef_yaw_deg, taban_aktif, gecis_aktif, ara_adim=True)

    async def _tekil_hedefe_git(
        self,
        hedef_ned: np.ndarray,
        hedef_yaw_deg: float,
        taban_aktif: bool = True,
        gecis_aktif: bool = False,
        ara_adim: bool = False,
    ) -> None:
        aralik = 1.0 / float(self._ayarlar.ucus["setpoint_frekansi_hz"])
        if ara_adim:
            # Rotasyonun ara adımı: dur-kalk yapmadan, gevşek toleransla bir sonraki yay noktasına geç
            konum_tol = float(self._ayarlar.ucus["rotasyon_ara_konum_toleransi_m"])
            yaw_tol = float(self._ayarlar.ucus["rotasyon_ara_yaw_toleransi_deg"])
        else:
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
        """Formasyondaki komşularla GPS mesafesini kontrol eder; ayrılmış komşular ve ayrık dron hariç."""
        if self._ayrik:
            return
        tel = self._dron.telemetri_al()
        komsular = {
            cid: durum.konum_ned
            for cid, durum in self._senkron.canli_komsular().items()
            if not durum.ayrilmis and cid not in self._yapi.ayrilan_idleri
        }
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
            if self._konum_kaydi is not None:
                # Ayrık dronun slotu boştur; kayıtta slot sütunları boş bırakılır
                slot = None if self._ayrik else self._yapi.slot_hedefi_ned(self._iha_id)
                self._konum_kaydi.yaz(
                    tel, self._dron.hedef_ortak_ned, slot,
                    self._adim_sayaci, self._faz, self._adim_aciklamasi,
                )
            await asyncio.sleep(aralik)
