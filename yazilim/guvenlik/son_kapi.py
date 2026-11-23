"""Dronlara giden her hedefin geçtiği son güvenlik kapısı."""

from __future__ import annotations

import logging
import math
import time
import numpy as np

from yazilim.ortak.ayarlar import Ayarlar
from yazilim.ortak.koordinat import aci_normalize_deg, en_kisa_aci_farki_deg


class GuvenlikKapisi:
    """Tüm setpoint hedeflerini uçuş öncesi sınırlar ve çarpışma önleme uygular."""

    def __init__(self, iha_id: int, ayarlar: Ayarlar, logger: logging.Logger) -> None:
        self._iha_id = iha_id
        self._logger = logger

        self._min_irtifa = float(ayarlar.sartname["min_irtifa_m"])
        self._maks_irtifa = float(ayarlar.ucus["maks_irtifa_m"])
        self._maks_yatay_hiz = float(ayarlar.ucus["maks_yatay_hiz_m_s"])
        self._maks_dusey_hiz = float(ayarlar.ucus["maks_dusey_hiz_m_s"])
        self._maks_yaw_hizi = float(ayarlar.ucus["maks_yaw_hizi_deg_s"])

        self._kacinma_mesafesi = float(ayarlar.ucus["carpismadan_kacinma_mesafesi_m"])
        self._kritik_mesafe = float(ayarlar.ucus["kritik_carpisma_mesafesi_m"])
        self._itme_kazanci = float(ayarlar.ucus["kacinma_itme_kazanci"])
        self._gecis_katmani = float(ayarlar.ucus["gecis_irtifa_katmani_m"])
        self._gps_tutarlilik_esigi = float(ayarlar.ucus["gps_tutarlilik_esigi_m"])
        self._kritik_log_araligi = float(ayarlar.ucus["kritik_log_araligi_s"])
        # Aynı komşu için uyarıyı her döngüde değil, belirli aralıkla yazmak için son log zamanı
        self._son_kritik_log_s: dict[int, float] = {}

        sinir = ayarlar.saha["alan_sinirlari_ned"]
        self._min_kuzey = float(sinir["min_kuzey_m"])
        self._maks_kuzey = float(sinir["maks_kuzey_m"])
        self._min_dogu = float(sinir["min_dogu_m"])
        self._maks_dogu = float(sinir["maks_dogu_m"])

        self._son_hedef_ned: np.ndarray | None = None
        self._son_yaw_deg: float | None = None

    def sifirla(self, mevcut_ned: np.ndarray, mevcut_yaw_deg: float) -> None:
        """Hız rampasının başlangıç noktasını dronun anlık konumuna eşitler."""
        self._son_hedef_ned = np.asarray(mevcut_ned, dtype=float).copy()
        self._son_yaw_deg = aci_normalize_deg(mevcut_yaw_deg)

    def gecis_irtifa_ofseti_m(self, gecis_aktif: bool) -> float:
        """Formasyon değişimi sırasında slot bazlı geçici irtifa ayrımı üretir (yukarı = negatif z)."""
        if not gecis_aktif:
            return 0.0
        # Her dron kendi slotu kadar katman yukarıda geçiş yapar (taban 10 m'yi asla delmez)
        return -(self._iha_id - 1) * self._gecis_katmani

    def hedefi_suz(
        self,
        ham_hedef_ned: np.ndarray,
        ham_yaw_deg: float,
        mevcut_ned: np.ndarray,
        komsu_konumlari: dict[int, np.ndarray],
        dt_s: float,
        taban_aktif: bool = True,
        gecis_aktif: bool = False,
    ) -> tuple[np.ndarray, float]:
        """Hedefi sırasıyla katman, çarpışma itmesi, hız rampası, geofence ve irtifa tabanından geçirir."""
        hedef = np.asarray(ham_hedef_ned, dtype=float).copy()
        mevcut = np.asarray(mevcut_ned, dtype=float)

        # 1. Geçiş sırasında farklı irtifa katmanı (çapraz geçişte çarpışmayı önler)
        hedef[2] += self.gecis_irtifa_ofseti_m(gecis_aktif)

        # 2. Hız rampası (ani sıçrama ve PID osilasyonunu önler)
        if self._son_hedef_ned is None:
            self._son_hedef_ned = mevcut.copy()
        if self._son_yaw_deg is None:
            self._son_yaw_deg = aci_normalize_deg(ham_yaw_deg)

        dt = max(dt_s, 1e-3)
        fark = hedef - self._son_hedef_ned
        yatay_mesafe = float(math.hypot(fark[0], fark[1]))
        maks_yatay_adim = self._maks_yatay_hiz * dt
        if yatay_mesafe > maks_yatay_adim and yatay_mesafe > 1e-9:
            olcek = maks_yatay_adim / yatay_mesafe
            fark[0] *= olcek
            fark[1] *= olcek

        maks_dusey_adim = self._maks_dusey_hiz * dt
        fark[2] = max(-maks_dusey_adim, min(maks_dusey_adim, float(fark[2])))

        guvenli = self._son_hedef_ned + fark

        # 3. Çarpışma önleme: yakın komşulardan yatay itme vektörü ekle
        itme_xy = self._carpisma_itmesi_hesapla(mevcut, komsu_konumlari)
        guvenli[0] += itme_xy[0]
        guvenli[1] += itme_xy[1]

        # 4. Alan (geofence) sınırları
        guvenli[0] = max(self._min_kuzey, min(self._maks_kuzey, float(guvenli[0])))
        guvenli[1] = max(self._min_dogu, min(self._maks_dogu, float(guvenli[1])))

        # 5. İrtifa tabanı (>= 10 m [Ş]) ve tavanı (NED'de z AŞAĞI pozitiftir!)
        en_yuksek_z = -self._min_irtifa  # örn. -10.0 m
        en_alcak_z = -self._maks_irtifa  # örn. -35.0 m
        if taban_aktif and guvenli[2] > en_yuksek_z:
            self._logger.warning(
                "Alt irtifa sınırı korundu: istenen=%.2f m -> %.2f m",
                -guvenli[2],
                self._min_irtifa,
            )
            guvenli[2] = en_yuksek_z
        if guvenli[2] < en_alcak_z:
            guvenli[2] = en_alcak_z

        # 6. Yumuşak yaw hız sınırı
        yaw_fark = en_kisa_aci_farki_deg(ham_yaw_deg, self._son_yaw_deg)
        maks_yaw_adim = self._maks_yaw_hizi * dt
        yaw_adim = max(-maks_yaw_adim, min(maks_yaw_adim, yaw_fark))
        guvenli_yaw = aci_normalize_deg(self._son_yaw_deg + yaw_adim)

        self._son_hedef_ned = guvenli.copy()
        self._son_yaw_deg = guvenli_yaw
        return guvenli, guvenli_yaw

    def _carpisma_itmesi_hesapla(
        self,
        mevcut_ned: np.ndarray,
        komsu_konumlari: dict[int, np.ndarray],
    ) -> np.ndarray:
        """Komşular güvenli mesafeden yakınsa uzaklaştırıcı yatay itme vektörü (m) üretir."""
        toplam_itme = np.zeros(2, dtype=float)
        for komsu_id, komsu_ned in komsu_konumlari.items():
            if komsu_id == self._iha_id:
                continue
            fark_3b = mevcut_ned - komsu_ned
            mesafe_3b = float(np.linalg.norm(fark_3b))
            if mesafe_3b >= self._kacinma_mesafesi:
                continue

            yatay = fark_3b[:2]
            yatay_norm = float(np.linalg.norm(yatay))
            if yatay_norm < 1e-4:
                # Tam üst üste denk gelinirse deterministik yön seç (ID farkına göre)
                aci = float(self._iha_id) * 2.0943951  # 120° adımlı ayrışma
                yon = np.array([math.cos(aci), math.sin(aci)], dtype=float)
            else:
                yon = yatay / yatay_norm

            siddet = (self._kacinma_mesafesi - mesafe_3b) * self._itme_kazanci
            if mesafe_3b < self._kritik_mesafe:
                siddet *= 2.0
                simdi = time.monotonic()
                if simdi - self._son_kritik_log_s.get(komsu_id, -1e9) >= self._kritik_log_araligi:
                    self._son_kritik_log_s[komsu_id] = simdi
                    self._logger.warning(
                        "Kritik yakınlık! İHA-%d ile mesafe=%.2f m", komsu_id, mesafe_3b
                    )
            toplam_itme += yon * siddet
        return toplam_itme

    def gps_tutarlilik_kontrolu(
        self,
        mevcut_ned: np.ndarray,
        komsu_konumlari: dict[int, np.ndarray],
        beklenen_mesafeler: dict[int, float],
    ) -> list[str]:
        """Formasyonda beklerken komşu GPS mesafelerini beklenen formasyon mesafesiyle karşılaştırır."""
        uyarilar: list[str] = []
        for komsu_id, komsu_ned in komsu_konumlari.items():
            beklenen = beklenen_mesafeler.get(komsu_id)
            if beklenen is None:
                continue
            olculen = float(np.linalg.norm(mevcut_ned - komsu_ned))
            sapma = abs(olculen - beklenen)
            if sapma > self._gps_tutarlilik_esigi:
                mesaj = (
                    f"GPS tutarlılık uyarısı (İHA-{komsu_id}): "
                    f"ölçülen={olculen:.2f} m, beklenen={beklenen:.2f} m, sapma={sapma:.2f} m"
                )
                self._logger.warning(mesaj)
                uyarilar.append(mesaj)
        return uyarilar
