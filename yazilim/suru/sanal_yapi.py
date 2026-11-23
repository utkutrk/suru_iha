"""Sanal yapı modeli: merkez, yönelim, pitch/roll eğimi, formasyon ve slot hedefleri."""

from __future__ import annotations

from dataclasses import dataclass, field
import numpy as np

from yazilim.ortak.koordinat import aci_normalize_deg, donus_matrisi_ned
from yazilim.suru.formasyonlar import formasyon_ofsetleri, kanonik_formasyon_adi


@dataclass
class SanalYapi:
    """Her dronun kendi içinde aynı kurallarla hesapladığı görünmez katı cisim durumu.

    Ayrılan dronların slotları boş kalır; kalan sürü formasyonu düzeltmez (şartname 5.1).
    """

    toplam_iha: int
    merkez_ned: np.ndarray
    formasyon_adi: str
    aralik_m: float
    yaw_deg: float = 0.0
    pitch_deg: float = 0.0
    roll_deg: float = 0.0
    ayrilan_idleri: set[int] = field(default_factory=set)
    # İHA numarası -> slot numarası. Boşsa numara = slot (varsayılan). Karışık dizilimde slot_atama.py doldurur.
    slot_atamasi: dict[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.merkez_ned = np.asarray(self.merkez_ned, dtype=float).copy()
        self.formasyon_adi = kanonik_formasyon_adi(self.formasyon_adi)
        self.yaw_deg = aci_normalize_deg(self.yaw_deg)

    def atama_ayarla(self, atama: dict[int, int]) -> None:
        """İHA -> slot eşlemesini ayarlar; 1..N için bire bir olmalıdır."""
        aralik = set(range(1, self.toplam_iha + 1))
        if set(atama) != aralik or set(atama.values()) != aralik:
            raise ValueError(f"Slot ataması 1..{self.toplam_iha} için bire bir olmalıdır: {atama}")
        self.slot_atamasi = dict(atama)

    def slot_no(self, iha_id: int) -> int:
        """İHA'nın slot numarasını döndürür (atama yoksa kendi numarası)."""
        if not (1 <= iha_id <= self.toplam_iha):
            raise ValueError(f"Geçersiz İHA ID: {iha_id} (1..{self.toplam_iha})")
        return self.slot_atamasi.get(iha_id, iha_id)

    def slot_ofseti_govde(self, iha_id: int) -> np.ndarray:
        """İHA'nın slotuna karşılık gelen gövde çerçevesi ofsetini döndürür."""
        return self._ofset_slot_no(self.slot_no(iha_id))

    def _ofset_slot_no(self, slot_no: int) -> np.ndarray:
        ofsetler = formasyon_ofsetleri(self.formasyon_adi, self.toplam_iha, self.aralik_m)
        return ofsetler[slot_no - 1]

    def slot_no_hedefi_ned(self, slot_no: int) -> np.ndarray:
        """Slot numarasının (dron numarasından bağımsız) ortak NED hedefini hesaplar."""
        rot = donus_matrisi_ned(self.yaw_deg, self.pitch_deg, self.roll_deg)
        return self.merkez_ned + (rot @ self._ofset_slot_no(slot_no))

    def slot_hedefi_ned(self, iha_id: int) -> np.ndarray:
        """Verilen İHA'nın ortak NED çerçevesindeki 3B slot hedefini hesaplar."""
        return self.slot_no_hedefi_ned(self.slot_no(iha_id))

    def tum_slot_hedefleri_ned(self) -> dict[int, np.ndarray]:
        """Tüm slotlar (1..N) için ortak NED hedeflerini döndürür."""
        return {i: self.slot_hedefi_ned(i) for i in range(1, self.toplam_iha + 1)}

    def en_alcak_slot_irtifasi_m(self) -> float:
        """Eğimli formasyonda yere en yakın (en alçak) aktif dronun irtifasını metre cinsinden verir."""
        aktifler = [i for i in range(1, self.toplam_iha + 1) if i not in self.ayrilan_idleri]
        if not aktifler:
            return float(-self.merkez_ned[2])
        # NED'de z aşağı olduğu için en büyük z = en alçak irtifa
        en_buyuk_z = max(float(self.slot_hedefi_ned(i)[2]) for i in aktifler)
        return -en_buyuk_z

    def egim_icin_taban_koru(self, min_irtifa_m: float) -> None:
        """Eğimli formasyonda en alçak dron min_irtifa_m altına düşecekse merkezi yukarı çeker."""
        en_alcak = self.en_alcak_slot_irtifasi_m()
        if en_alcak < min_irtifa_m:
            fark = min_irtifa_m - en_alcak
            self.merkez_ned[2] -= fark  # NED'de yukarı = z azalır

    def beklenen_komsu_mesafesi_m(self, iha_a: int, iha_b: int) -> float:
        """GPS tutarlılık kontrolü için iki slot arasındaki beklenen 3B mesafeyi döndürür."""
        p_a = self.slot_hedefi_ned(iha_a)
        p_b = self.slot_hedefi_ned(iha_b)
        return float(np.linalg.norm(p_a - p_b))
