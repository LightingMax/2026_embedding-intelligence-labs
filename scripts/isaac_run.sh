#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mode="${1:-smoke}"
if [[ $# -gt 0 ]]; then shift; fi
display_args=()
if [[ "${mode}" == "g1-gui" ]]; then
  display_name="${DISPLAY:-:0}"
  xauthority_file="${XAUTHORITY:-/run/user/$(id -u)/gdm/Xauthority}"
  if [[ ! -S /tmp/.X11-unix/X0 || ! -r "${xauthority_file}" ]]; then
    echo "未找到Xorg :0或Xauthority，无法启动图形窗口" >&2
    exit 1
  fi
  display_args=(
    -e "DISPLAY=${display_name}"
    -e XAUTHORITY=/tmp/host-Xauthority
    -v /tmp/.X11-unix:/tmp/.X11-unix:rw
    -v "${xauthority_file}:/tmp/host-Xauthority:ro"
  )
fi

mkdir -p "${ROOT_DIR}/artifacts/isaac"

docker run --rm --gpus all --network host \
  -e ACCEPT_EULA=Y -e PRIVACY_CONSENT=Y -e PYTHONUNBUFFERED=1 \
  "${display_args[@]}" \
  -v "${HOME}/docker/embodied-book-labs/cache:/root/.cache:rw" \
  -v "${HOME}/docker/embodied-book-labs/logs:/root/.nvidia-omniverse/logs:rw" \
  -v "${HOME}/docker/embodied-book-labs/unitree-assets/assets:/opt/unitree_sim_isaaclab/assets:ro" \
  -v "${ROOT_DIR}/artifacts/isaac:/book-artifacts:rw" \
  embodied-book-labs-isaac:5.0 "${mode}" "$@"
