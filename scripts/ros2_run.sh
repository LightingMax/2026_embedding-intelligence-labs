#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fault="${1:-none}"
case "${fault}" in
  none|path_blocked|grasp_failed|user_cancel) ;;
  *) echo "ROS 2教学后端不支持故障: ${fault}" >&2; exit 2 ;;
esac

cd "${ROOT_DIR}"
BOOK_ROS_FAULT="${fault}" docker compose --profile ros2 run --rm ros2
