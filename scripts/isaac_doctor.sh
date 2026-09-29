#!/usr/bin/env bash
set -euo pipefail

fail=0
for command_name in docker git; do
  if ! command -v "${command_name}" >/dev/null; then
    echo "缺少命令: ${command_name}" >&2
    fail=1
  fi
done

if ! command -v nvidia-smi >/dev/null; then
  echo "未检测到nvidia-smi" >&2
  fail=1
else
  nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
fi

if command -v docker >/dev/null && ! docker info >/dev/null 2>&1; then
  echo "当前用户不能访问Docker daemon" >&2
  fail=1
fi

if [[ "${fail}" -ne 0 ]]; then exit 1; fi
echo "ISAAC_DOCTOR_OK"
