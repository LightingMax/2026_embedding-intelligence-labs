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
  shell)
    exec bash
    ;;
  *)
    exec "$@"
    ;;
esac
