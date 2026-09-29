#!/usr/bin/env bash
set -euo pipefail

export ACCEPT_EULA="${ACCEPT_EULA:-Y}"
export PRIVACY_CONSENT="${PRIVACY_CONSENT:-Y}"

case "${1:-smoke}" in
  smoke)
    exec /isaac-sim/python.sh -c "from isaacsim import SimulationApp; app=SimulationApp({'headless': True}); print('ISAAC_SIM_READY'); app.close()"
    ;;
  g1)
    shift
    exec /isaac-sim/python.sh sim_main.py \
      --device cpu --enable_cameras \
      --task Isaac-PickPlace-Cylinder-G129-Dex1-Joint \
      --enable_dex1_dds --robot_type g129 --no_render "$@"
    ;;
  g1-gui)
    shift
    exec /isaac-sim/python.sh sim_main.py \
      --device cpu --enable_cameras \
      --task Isaac-PickPlace-Cylinder-G129-Dex1-Joint \
      --enable_dex1_dds --robot_type g129 "$@"
    ;;
  assets)
    asset_root="/assets-cache"
    if [[ -d "${asset_root}/assets" ]]; then
      echo "UNITREE_ASSETS_READY"
      exit 0
    fi
    mkdir -p "${asset_root}"
    git clone https://huggingface.co/datasets/unitreerobotics/unitree_sim_isaaclab_usds "${asset_root}/download"
    test "$(stat -c%s "${asset_root}/download/assets.zip")" -gt 1073741824
    unzip -q "${asset_root}/download/assets.zip" -d "${asset_root}"
    echo "UNITREE_ASSETS_READY"
    ;;
  shell)
    exec bash
    ;;
  *)
    exec "$@"
    ;;
esac
