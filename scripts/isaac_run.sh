#!/usr/bin/env bash
set -euo pipefail

mode="${1:-smoke}"
docker run --rm --gpus all --network host \
  -e ACCEPT_EULA=Y -e PRIVACY_CONSENT=Y \
  -v "${HOME}/docker/embodied-book-labs/cache:/root/.cache:rw" \
  -v "${HOME}/docker/embodied-book-labs/logs:/root/.nvidia-omniverse/logs:rw" \
  -v "${HOME}/docker/embodied-book-labs/unitree-assets/assets:/opt/unitree_sim_isaaclab/assets:ro" \
  embodied-book-labs-isaac:5.0 "${mode}"
