#!/usr/bin/env bash
# Gazebo Harmonic + N adet PX4 SITL (x500) dronunu tek komutla başlatır.
# Kullanım: PX4_DIR=/yol/PX4-Autopilot ./betikler/sitl_baslat.sh [iha_sayisi]
# Karışık dizilim denemesi (hakemler dronları karışık dizer [5.1]): SPAWN_SIRASI=2,3,1 verilirse
# İHA-1 saha.json'daki 2. başlangıç noktasında, İHA-2 3.'de, İHA-3 1.'de doğar. Verilmezse İHA-i, i. noktada doğar.

set -euo pipefail

PROJE_KOKU="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PROJE_KOKU}/venv/bin/python"
PX4_DIR="${PX4_DIR:-$HOME/PX4-Autopilot}"
IHA_SAYISI="${1:-3}"
SPAWN_SIRASI="${SPAWN_SIRASI:-}"
DUNYA_YOLU="${PROJE_KOKU}/simulasyon/dunyalar/teknofest_alani.sdf"

if [[ ! -d "${PX4_DIR}" ]]; then
  echo "HATA: PX4_DIR bulunamadı: ${PX4_DIR}"
  echo "Örnek: PX4_DIR=\$HOME/PX4-Autopilot ./betikler/sitl_baslat.sh ${IHA_SAYISI}"
  exit 1
fi

PX4_BIN="${PX4_DIR}/build/px4_sitl_default/bin/px4"
if [[ ! -x "${PX4_BIN}" ]]; then
  echo "HATA: PX4 SITL derlenmemiş: ${PX4_BIN}"
  echo "Önce PX4 klasöründe 'make px4_sitl gz_x500' çalıştırın."
  exit 1
fi

export GZ_SIM_RESOURCE_PATH="${PX4_DIR}/Tools/simulation/gz/models:${PX4_DIR}/Tools/simulation/gz/worlds:${PROJE_KOKU}/simulasyon/dunyalar:${GZ_SIM_RESOURCE_PATH:-}"

PIDLER=()
temizle() {
  echo ""
  echo "PX4 SITL ve Gazebo kapatılıyor..."
  for pid in "${PIDLER[@]}"; do
    kill "${pid}" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap temizle EXIT INT TERM

echo "Gazebo dünyası başlatılıyor: ${DUNYA_YOLU}"
gz sim -r "${DUNYA_YOLU}" &
PIDLER+=($!)
sleep 4

for ((i = 1; i <= IHA_SAYISI; i++)); do
  INST=$((i - 1))
  # Başlangıç konumunu ayarlar/saha.json'dan oku ve NED -> Gazebo ENU'ya çevir
  POSE="$("${PYTHON}" -c "
import json
with open('${PROJE_KOKU}/ayarlar/saha.json', encoding='utf-8') as f:
    konumlar = json.load(f)['baslangic_konumlari_ned']['deger']
sira = [int(x) for x in '${SPAWN_SIRASI}'.split(',') if x.strip()]
if sira and sorted(sira) != list(range(1, ${IHA_SAYISI} + 1)):
    raise SystemExit('HATA: SPAWN_SIRASI 1..${IHA_SAYISI} sayılarının bir sıralaması olmalı, örn. 2,3,1')
nokta = sira[${i} - 1] if sira else ${i}
kuzey, dogu, _ = konumlar.get(str(nokta), [0.0, (nokta - 1) * 4.0, 0.0])
print(f'{dogu},{kuzey},0.2,0,0,0')
")"

  PX4_CALISMA="${PROJE_KOKU}/kayitlar/px4_rootfs/iha${i}"
  mkdir -p "${PX4_CALISMA}"

  echo "PX4 SITL İHA-${i} başlatılıyor (instance=${INST}, ENU pose=${POSE}, MAVLink UDP=$((14540 + INST)))..."
  PX4_SYS_AUTOSTART=4001 \
  PX4_SIM_MODEL=gz_x500 \
  PX4_GZ_STANDALONE=1 \
  PX4_GZ_WORLD=teknofest_alani \
  PX4_GZ_MODEL_POSE="${POSE}" \
  PX4_GZ_NO_FOLLOW=1 \
  "${PX4_BIN}" -i "${INST}" -d "${PX4_DIR}/build/px4_sitl_default/etc" -w "${PX4_CALISMA}" \
    > "${PROJE_KOKU}/kayitlar/px4_sitl_iha${i}.log" 2>&1 &
  PIDLER+=($!)
  sleep 2
done

# PX4 başlangıç betiği kamerayı x500_0'a kilitlemişse serbest bırak (serbest gezinme için)
sleep 1
gz topic -t /gui/follow -m gz.msgs.StringMsg -p 'data: ""' 2>/dev/null || true

echo ""
echo "${IHA_SAYISI} adet PX4 SITL + Gazebo hazır. Durdurmak için Ctrl+C."
wait
