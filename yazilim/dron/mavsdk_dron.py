"""Tek bir PX4 dronu ile MAVSDK üzerinden konuşan tek modül."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
import numpy as np

from mavsdk import System
from mavsdk.offboard import OffboardError, PositionNedYaw

from yazilim.ortak.ayarlar import Ayarlar
from yazilim.ortak.koordinat import gps_to_ned


@dataclass
class DronTelemetri:
    """Bir dronun anlık telemetri özeti (ortak NED çerçevesinde)."""

    konum_ned: np.ndarray
    hiz_ned: np.ndarray
    yaw_deg: float
    enlem_deg: float
    boylam_deg: float
    mutlak_irtifa_m: float
    goreli_irtifa_m: float
    gps_uydu: int
    gps_saglikli: bool
    arm_durumu: bool
    havada: bool
    ucus_modu: str


class MavsdkDron:
    """MAVSDK ile PX4 bağlantısı, sürekli offboard akışı ve ortak NED eşlemesi yönetir."""

    def __init__(self, iha_id: int, ayarlar: Ayarlar, logger: logging.Logger) -> None:
        self._iha_id = iha_id
        self._ayarlar = ayarlar
        self._logger = logger

        mavsdk_port = int(ayarlar.ag["mavsdk_sunucu_taban_portu"]) + iha_id
        self._mavlink_port = int(ayarlar.ag["mavlink_taban_portu"]) + (iha_id - 1)
        self._sistem = System(port=mavsdk_port)

        orijin = ayarlar.saha["ortak_orijin_gps"]
        self._orijin_enlem = float(orijin["enlem"])
        self._orijin_boylam = float(orijin["boylam"])
        self._orijin_irtifa = float(orijin["irtifa_m"])

        # PX4'ün yerel NED orijini her dronun kendi kalkış noktasıdır; ortak çerçeveye çevrilir
        self._yerel_orijin_ofset_ned = np.zeros(3, dtype=float)
        self._yerel_konum_ned = np.zeros(3, dtype=float)
        self._hiz_ned = np.zeros(3, dtype=float)
        self._yaw_deg = 0.0
        self._enlem_deg = self._orijin_enlem
        self._boylam_deg = self._orijin_boylam
        self._mutlak_irtifa_m = self._orijin_irtifa
        self._goreli_irtifa_m = 0.0
        self._gps_uydu = 0
        self._gps_saglikli = False
        self._arm_durumu = False
        self._havada = False
        self._ucus_modu = "UNKNOWN"

        self._hedef_ortak_ned = np.zeros(3, dtype=float)
        self._hedef_yaw_deg = 0.0
        self._offboard_aktif = False
        self._gorevler: list[asyncio.Task[None]] = []

    @property
    def iha_id(self) -> int:
        return self._iha_id

    @property
    def offboard_aktif(self) -> bool:
        return self._offboard_aktif

    @property
    def hedef_ortak_ned(self) -> np.ndarray:
        """PX4'e şu an gönderilen (güvenlik kapısından geçmiş) ortak NED hedefinin kopyası."""
        return self._hedef_ortak_ned.copy()

    def telemetri_al(self) -> DronTelemetri:
        """Ortak NED koordinat çerçevesindeki anlık telemetriyi döndürür."""
        ortak_konum = self._yerel_konum_ned + self._yerel_orijin_ofset_ned
        return DronTelemetri(
            konum_ned=ortak_konum.copy(),
            hiz_ned=self._hiz_ned.copy(),
            yaw_deg=self._yaw_deg,
            enlem_deg=self._enlem_deg,
            boylam_deg=self._boylam_deg,
            mutlak_irtifa_m=self._mutlak_irtifa_m,
            goreli_irtifa_m=self._goreli_irtifa_m,
            gps_uydu=self._gps_uydu,
            gps_saglikli=self._gps_saglikli,
            arm_durumu=self._arm_durumu,
            havada=self._havada,
            ucus_modu=self._ucus_modu,
        )

    async def baglan(self) -> None:
        """PX4'e bağlanır, GPS/home hazır olana kadar bekler ve telemetri akışlarını başlatır."""
        adres = f"udpin://0.0.0.0:{self._mavlink_port}"
        self._logger.info("PX4'e bağlanılıyor: %s", adres)
        await self._sistem.connect(system_address=adres)

        async for durum in self._sistem.core.connection_state():
            if durum.is_connected:
                self._logger.info("PX4 bağlantısı kuruldu.")
                break

        self._logger.info("GPS, home ve yerel konum sağlığı bekleniyor...")
        async for saglik in self._sistem.telemetry.health():
            if (
                saglik.is_global_position_ok
                and saglik.is_home_position_ok
                and saglik.is_local_position_ok
            ):
                self._gps_saglikli = True
                self._logger.info("GPS ve home konumu hazır.")
                break

        # Arka plan telemetri dinleyicilerini başlat
        self._gorevler.append(asyncio.create_task(self._izle_konum_hiz_ned()))
        self._gorevler.append(asyncio.create_task(self._izle_gps()))
        self._gorevler.append(asyncio.create_task(self._izle_euler()))
        self._gorevler.append(asyncio.create_task(self._izle_durum()))

        # İlk GPS ve yerel NED okumasını alıp ortak çerçeve ofsetini kalibre et
        await asyncio.sleep(0.5)
        self._ortak_orijin_kalibre_et()
        self._hedef_ortak_ned = self.telemetri_al().konum_ned.copy()
        self._hedef_yaw_deg = self._yaw_deg

    def _ortak_orijin_kalibre_et(self) -> None:
        """Dronun kendi yerel NED orijinini sürünün ortak NED orijinine eşler."""
        gps_ned = gps_to_ned(
            self._enlem_deg,
            self._boylam_deg,
            self._mutlak_irtifa_m,
            self._orijin_enlem,
            self._orijin_boylam,
            self._orijin_irtifa,
        )
        # Yatay ofset GPS'ten, düşey z=0 zemin referansından alınır (barometre kaymasını önler)
        self._yerel_orijin_ofset_ned = np.array(
            [
                gps_ned[0] - self._yerel_konum_ned[0],
                gps_ned[1] - self._yerel_konum_ned[1],
                0.0,
            ],
            dtype=float,
        )
        self._logger.info(
            "Ortak NED ofseti kalibre edildi: [K=%.2f, D=%.2f, A=%.2f] m",
            self._yerel_orijin_ofset_ned[0],
            self._yerel_orijin_ofset_ned[1],
            self._yerel_orijin_ofset_ned[2],
        )

    def hedef_guncelle(self, ortak_ned: np.ndarray, yaw_deg: float) -> None:
        """Arka plan setpoint akışının PX4'e göndereceği ortak NED hedefini günceller."""
        self._hedef_ortak_ned = np.asarray(ortak_ned, dtype=float).copy()
        self._hedef_yaw_deg = float(yaw_deg)

    async def arm_ve_offboard_baslat(self) -> None:
        """Dronu arm eder, başlangıç setpointlerini yollar ve offboard modunu başlatır."""
        if not self._gps_saglikli:
            raise RuntimeError("GPS/home hazır olmadan arm edilemez")

        self._logger.info("Arm ediliyor...")
        await self._sistem.action.arm()

        # PX4 kuralı: offboard.start() öncesi kesintisiz setpoint akışı başlamış olmalı
        paket_sayisi = int(self._ayarlar.ucus["baslangic_offboard_paket_sayisi"])
        aralik = 1.0 / float(self._ayarlar.ucus["setpoint_frekansi_hz"])
        for _ in range(paket_sayisi):
            await self._tek_setpoint_gonder()
            await asyncio.sleep(aralik)

        try:
            await self._sistem.offboard.start()
        except OffboardError as hata:
            self._logger.error("Offboard başlatılamadı: %s", hata)
            raise

        self._offboard_aktif = True
        self._gorevler.append(asyncio.create_task(self._offboard_akisi()))
        self._logger.info("Offboard modu aktif.")

    async def inis_yap_ve_bekle(self) -> None:
        """Güvenli iniş başlatır ve PX4 disarm olana kadar bekler (havada disarm yok!)."""
        self._logger.info("İniş başlatılıyor...")
        self._offboard_aktif = False
        try:
            await self._sistem.offboard.stop()
        except OffboardError:
            pass
        await self._sistem.action.land()

        # İniş ve otomatik disarm tamamlanana kadar bekle
        while self._havada or self._arm_durumu:
            await asyncio.sleep(0.25)
        self._logger.info("İniş ve disarm tamamlandı.")

    async def kapat(self) -> None:
        """Arka plan görevlerini temizce durdurur."""
        self._offboard_aktif = False
        for gorev in self._gorevler:
            gorev.cancel()
        if self._gorevler:
            await asyncio.gather(*self._gorevler, return_exceptions=True)
        self._gorevler.clear()

    async def _tek_setpoint_gonder(self) -> None:
        yerel = self._hedef_ortak_ned - self._yerel_orijin_ofset_ned
        await self._sistem.offboard.set_position_ned(
            PositionNedYaw(
                float(yerel[0]),
                float(yerel[1]),
                float(yerel[2]),
                float(self._hedef_yaw_deg),
            )
        )

    async def _offboard_akisi(self) -> None:
        aralik = 1.0 / float(self._ayarlar.ucus["setpoint_frekansi_hz"])
        while self._offboard_aktif:
            try:
                await self._tek_setpoint_gonder()
            except OffboardError as hata:
                self._logger.warning("Setpoint gönderim hatası: %s", hata)
            await asyncio.sleep(aralik)

    async def _izle_konum_hiz_ned(self) -> None:
        async for pv in self._sistem.telemetry.position_velocity_ned():
            self._yerel_konum_ned = np.array(
                [pv.position.north_m, pv.position.east_m, pv.position.down_m], dtype=float
            )
            self._hiz_ned = np.array(
                [pv.velocity.north_m_s, pv.velocity.east_m_s, pv.velocity.down_m_s], dtype=float
            )

    async def _izle_gps(self) -> None:
        async for pos in self._sistem.telemetry.position():
            self._enlem_deg = float(pos.latitude_deg)
            self._boylam_deg = float(pos.longitude_deg)
            self._mutlak_irtifa_m = float(pos.absolute_altitude_m)
            self._goreli_irtifa_m = float(pos.relative_altitude_m)

    async def _izle_euler(self) -> None:
        async for aci in self._sistem.telemetry.attitude_euler():
            self._yaw_deg = float(aci.yaw_deg)

    async def _izle_durum(self) -> None:
        async def _arm() -> None:
            async for a in self._sistem.telemetry.armed():
                self._arm_durumu = bool(a)

        async def _havada() -> None:
            async for h in self._sistem.telemetry.in_air():
                self._havada = bool(h)

        async def _mod() -> None:
            async for m in self._sistem.telemetry.flight_mode():
                self._ucus_modu = str(m)

        async def _gps_info() -> None:
            async for g in self._sistem.telemetry.gps_info():
                self._gps_uydu = int(g.num_satellites)

        await asyncio.gather(_arm(), _havada(), _mod(), _gps_info())
