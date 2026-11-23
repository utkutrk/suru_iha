#!/usr/bin/env bash
# N adet dağıtık sürü ajanını (her biri ayrı süreç, aynı program) tek komutla başlatır.
# Kullanım: SURU_TAKIM_ANAHTARI=gizli ./betikler/suru_baslat.sh [gorev1|gorev2] [iha_sayisi]

set -euo pipefail

PROJE_KOKU="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${PROJE_KOKU}/venv/bin/python"
GOREV="${1:-gorev1}"
IHA_SAYISI="${2:-3}"

# Yerel geliştirme için anahtar verilmediyse gizli.local.json kontrolü yazilim/ortak/ayarlar.py'de yapılır
if [[ -z "${SURU_TAKIM_ANAHTARI:-}" && ! -f "${PROJE_KOKU}/ayarlar/gizli.local.json" ]]; then
  echo "UYARI: SURU_TAKIM_ANAHTARI tanımlı değil. Simülasyon için geçici anahtar atanıyor."
  export SURU_TAKIM_ANAHTARI="gelistirme_anahtari_degistir"
fi

PIDLER=()
temizle() {
  echo ""
  echo "Sürü ajanları kapatılıyor..."
  for pid in "${PIDLER[@]}"; do
    kill "${pid}" 2>/dev/null || true
  done
  wait 2>/dev/null || true
}
trap temizle EXIT INT TERM

cd "${PROJE_KOKU}"
for ((i = 1; i <= IHA_SAYISI; i++)); do
  echo "Dağıtık ajan başlatılıyor: İHA-${i} (görev=${GOREV})"
  "${PYTHON}" -m yazilim.ana --iha-id "${i}" --iha-sayisi "${IHA_SAYISI}" --gorev "${GOREV}" &
  PIDLER+=($!)
  sleep 0.4
done

echo ""
echo "${IHA_SAYISI} ajan hazır."
if [[ "${GOREV}" == "gorev1" ]]; then
  echo "Görevi başlatmak için başka terminalde: ./venv/bin/python betikler/baslat_komutu.py"
else
  echo "Sürüyü yönetmek için başka terminalde: ./venv/bin/python betikler/gorev2_kumanda.py"
fi
wait
