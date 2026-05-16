#!/usr/bin/env bash
# Gurobi solver — Mac'te yerel çalıştırma (Docker lisans uyumsuzluğu için)
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -z "${GRB_LICENSE_FILE:-}" ]]; then
  if [[ -f "$HOME/gurobi.lic" ]]; then
    export GRB_LICENSE_FILE="$HOME/gurobi.lic"
  elif [[ -f "./gurobi.lic" ]]; then
    export GRB_LICENSE_FILE="./gurobi.lic"
  else
    echo "Hata: gurobi.lic bulunamadı. GRB_LICENSE_FILE ayarlayın." >&2
    exit 1
  fi
fi

if [[ ! -d .venv ]]; then
  python3.12 -m venv .venv
  .venv/bin/pip install -q -r solver/requirements.txt
fi

echo "Solver başlatılıyor: http://127.0.0.1:8001 (lisans: $GRB_LICENSE_FILE)"
exec .venv/bin/python -m uvicorn solver.main:app --host 0.0.0.0 --port 8001 --reload
