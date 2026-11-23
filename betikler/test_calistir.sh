#!/usr/bin/env bash
# Birim testlerini çalıştırır.
set -euo pipefail
PROJE_KOKU="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJE_KOKU}"
"${PROJE_KOKU}/venv/bin/python" -m pytest -v test/birim
