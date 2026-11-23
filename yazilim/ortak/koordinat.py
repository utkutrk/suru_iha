"""GPS <-> ortak NED dönüşümleri, açı normalizasyonu ve 3B NED dönüş matrisi hesapları."""

from __future__ import annotations

import math
import numpy as np

# WGS-84 ortalama dünya yarıçapı (evrensel fiziksel sabit, metre)
DUNYA_YARICAPI_M = 6378137.0


def aci_normalize_deg(aci_deg: float) -> float:
    """Açıyı [-180, 180) aralığına indirger."""
    return ((aci_deg + 180.0) % 360.0) - 180.0


def en_kisa_aci_farki_deg(hedef_deg: float, mevcut_deg: float) -> float:
    """mevcut_deg -> hedef_deg arasındaki en kısa işaretli açı farkını döndürür."""
    return aci_normalize_deg(hedef_deg - mevcut_deg)


def yaw_ara_adimlari(mevcut_deg: float, hedef_deg: float, adim_deg: float) -> list[float]:
    """mevcut_deg -> hedef_deg dönüşünü en kısa yönden adim_deg'lik yaw değerlerine böler.

    Neden: formasyon tek hamlede döndürülürse slotlar düz çizgiyle yer değiştirir ve komşu
    slotların yolları kesişir. Küçük yaw adımlarıyla slotlar yay üzerinde kalır.
    Dönen liste her zaman tam hedef açıyla biter; fark sıfırsa yalnız [hedef] döner.
    """
    if adim_deg <= 0:
        raise ValueError("adim_deg pozitif olmalıdır")
    fark = en_kisa_aci_farki_deg(hedef_deg, mevcut_deg)
    adim_sayisi = max(1, math.ceil(abs(fark) / adim_deg - 1e-9))
    return [
        aci_normalize_deg(mevcut_deg + fark * (k / adim_sayisi))
        for k in range(1, adim_sayisi + 1)
    ]


def yukaridan_yaklasma_noktalari(
    mevcut_ned: np.ndarray, hedef_ned: np.ndarray, yukseklik_m: float
) -> list[np.ndarray]:
    """Hedefe formasyonun üstünden yaklaşmak için ara noktaları verir: önce yerinde yüksel, sonra hedefin üstüne git.

    Üçüncü adım (hedefe alçalma) çağıranın normal hedef hareketidir, listede yoktur.
    NED'de yukarı = z azalır; dron zaten daha yüksekteyse alçalmaz.
    """
    if yukseklik_m <= 0:
        raise ValueError("yukseklik_m pozitif olmalıdır")
    mevcut = np.asarray(mevcut_ned, dtype=float)
    hedef = np.asarray(hedef_ned, dtype=float)
    ust_z = min(float(hedef[2]) - yukseklik_m, float(mevcut[2]))
    yerinde_yuksel = np.array([mevcut[0], mevcut[1], ust_z], dtype=float)
    hedefin_ustu = np.array([hedef[0], hedef[1], float(hedef[2]) - yukseklik_m], dtype=float)
    return [yerinde_yuksel, hedefin_ustu]


def gps_to_ned(
    enlem_deg: float,
    boylam_deg: float,
    irtifa_m: float,
    orijin_enlem_deg: float,
    orijin_boylam_deg: float,
    orijin_irtifa_m: float,
) -> np.ndarray:
    """GPS (enlem, boylam, irtifa) konumunu ortak NED (Kuzey, Doğu, Aşağı) vektörüne çevirir."""
    d_lat = math.radians(enlem_deg - orijin_enlem_deg)
    d_lon = math.radians(boylam_deg - orijin_boylam_deg)
    lat0_rad = math.radians(orijin_enlem_deg)

    kuzey_m = d_lat * DUNYA_YARICAPI_M
    dogu_m = d_lon * DUNYA_YARICAPI_M * math.cos(lat0_rad)
    # NED sisteminde z AŞAĞI pozitiftir; yükseldikçe z negatif olur
    asagi_m = -(irtifa_m - orijin_irtifa_m)
    return np.array([kuzey_m, dogu_m, asagi_m], dtype=float)


def ned_to_gps(
    ned: np.ndarray,
    orijin_enlem_deg: float,
    orijin_boylam_deg: float,
    orijin_irtifa_m: float,
) -> tuple[float, float, float]:
    """Ortak NED vektörünü GPS (enlem, boylam, irtifa) üçlüsüne çevirir."""
    lat0_rad = math.radians(orijin_enlem_deg)
    enlem = orijin_enlem_deg + math.degrees(float(ned[0]) / DUNYA_YARICAPI_M)
    boylam = orijin_boylam_deg + math.degrees(
        float(ned[1]) / (DUNYA_YARICAPI_M * math.cos(lat0_rad))
    )
    irtifa = orijin_irtifa_m - float(ned[2])
    return enlem, boylam, irtifa


def hedef_yonelim_deg(baslangic_ned: np.ndarray, hedef_ned: np.ndarray) -> float:
    """NED yatay düzleminde başlangıçtan hedefe olan pusula açısını (Kuzey=0, saat yönü +) verir."""
    d_kuzey = float(hedef_ned[0] - baslangic_ned[0])
    d_dogu = float(hedef_ned[1] - baslangic_ned[1])
    if abs(d_kuzey) < 1e-6 and abs(d_dogu) < 1e-6:
        return 0.0
    return aci_normalize_deg(math.degrees(math.atan2(d_dogu, d_kuzey)))


def donus_matrisi_ned(yaw_deg: float, pitch_deg: float, roll_deg: float) -> np.ndarray:
    """Z-Y-X (yaw -> pitch -> roll) sırasıyla gövdeden ortak NED'e dönüş matrisi üretir.

    NED gövde eksenleri: x ileri, y sağ, z aşağı.
    - Pozitif yaw: sağa (saat yönü) dönüş.
    - Pozitif pitch: burun yukarı (+x yukarı yani z negatif -> -sin(pitch)).
      Böylece -15° pitch (burun aşağı) verildiğinde öndeki dron alçalır, arkadaki yükselir (şartname 5.1.2).
    - Pozitif roll: sağ kanat aşağı (+y aşağı yani z pozitif -> +sin(roll)).
    """
    psi = math.radians(yaw_deg)
    theta = math.radians(pitch_deg)
    phi = math.radians(roll_deg)

    c_psi, s_psi = math.cos(psi), math.sin(psi)
    c_th, s_th = math.cos(theta), math.sin(theta)
    c_phi, s_phi = math.cos(phi), math.sin(phi)

    r_z = np.array(
        [
            [c_psi, -s_psi, 0.0],
            [s_psi, c_psi, 0.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=float,
    )
    r_y = np.array(
        [
            [c_th, 0.0, s_th],
            [0.0, 1.0, 0.0],
            [-s_th, 0.0, c_th],
        ],
        dtype=float,
    )
    r_x = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, c_phi, -s_phi],
            [0.0, s_phi, c_phi],
        ],
        dtype=float,
    )
    return r_z @ r_y @ r_x
