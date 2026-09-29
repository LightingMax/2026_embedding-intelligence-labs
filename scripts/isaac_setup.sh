#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
"${ROOT_DIR}/scripts/isaac_doctor.sh"

DEPS_DIR="${ROOT_DIR}/external/isaac-deps"
mkdir -p "${DEPS_DIR}"

download_archive() {
  local filename="$1"
  local url="$2"
  local target="${DEPS_DIR}/${filename}"
  local partial="${target}.part"
  if [[ -f "${target}" ]] && tar -tzf "${target}" >/dev/null 2>&1; then
    echo "依赖归档已缓存: ${filename}"
    return
  fi
  echo "下载依赖归档: ${filename}"
  curl -fL --retry 20 --retry-all-errors --retry-delay 5 \
    --connect-timeout 20 --speed-time 60 --speed-limit 1024 \
    -C - -o "${partial}" "${url}"
  tar -tzf "${partial}" >/dev/null
  mv "${partial}" "${target}"
}

download_archive isaaclab.tar.gz \
  https://codeload.github.com/isaac-sim/IsaacLab/tar.gz/46dff135f44683f031edf346e544fcfd8456b2bb
download_archive cyclonedds.tar.gz \
  https://codeload.github.com/eclipse-cyclonedds/cyclonedds/tar.gz/5041f3560c088c99e5088b2b8520b69169621196
download_archive unitree-sdk.tar.gz \
  https://codeload.github.com/unitreerobotics/unitree_sdk2_python/tar.gz/814556d15970dd2ecf1c9984e845ca02ab07e206
download_archive unitree-sim.tar.gz \
  https://codeload.github.com/unitreerobotics/unitree_sim_isaaclab/tar.gz/e30c25b1dffdf92ada1d6c8c1fe9a47bdde0fecc
download_archive teleimager.tar.gz \
  https://codeload.github.com/unitreerobotics/teleimager/tar.gz/b81de448bca9c696d7ce145f4af71c66146d0b69

RUNTIME_WHEELS="${DEPS_DIR}/runtime-wheels"
mkdir -p "${RUNTIME_WHEELS}"
if ! compgen -G "${RUNTIME_WHEELS}/pin-2.7.0-*.whl" >/dev/null \
  || ! compgen -G "${RUNTIME_WHEELS}/gymnasium-1.2.0-*.whl" >/dev/null \
  || ! compgen -G "${RUNTIME_WHEELS}/flatdict-4.0.1.*" >/dev/null; then
  echo "缓存 Isaac Lab 核心运行依赖"
  docker run --rm \
    -v "${RUNTIME_WHEELS}:/wheels" \
    --entrypoint /isaac-sim/python.sh \
    nvcr.io/nvidia/isaac-sim:5.0.0 \
    -m pip download --no-build-isolation --dest /wheels \
    "flatdict==4.0.1" "gymnasium==1.2.0" "prettytable==3.3.0" "pin==2.7.0"
fi

docker build \
  -f "${ROOT_DIR}/docker/isaac/Dockerfile" \
  -t embodied-book-labs-isaac:5.0 \
  "${ROOT_DIR}"
mkdir -p "${HOME}/docker/embodied-book-labs/unitree-assets"
docker run --rm \
  -v "${HOME}/docker/embodied-book-labs/unitree-assets:/assets-cache:rw" \
  embodied-book-labs-isaac:5.0 assets
echo "ISAAC_SETUP_OK"
