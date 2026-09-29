#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"${ROOT_DIR}/scripts/isaac_doctor.sh"
docker build \
  -f "${ROOT_DIR}/docker/isaac/Dockerfile" \
  -t embodied-book-labs-isaac:5.0 \
  "${ROOT_DIR}"
mkdir -p "${HOME}/docker/embodied-book-labs/unitree-assets"
docker run --rm \
  -v "${HOME}/docker/embodied-book-labs/unitree-assets:/assets-cache:rw" \
  embodied-book-labs-isaac:5.0 assets
echo "ISAAC_SETUP_OK"
