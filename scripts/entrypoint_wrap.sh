#!/bin/sh
set -eu

HOST="dashscope.aliyuncs.com"

# 如果已经写过就不重复写
if ! grep -qE "[[:space:]]${HOST}([[:space:]]|$)" /etc/hosts; then
  # 只取 IPv6（避开 IPv4 黑洞）
  IPV6="$(getent ahostsv6 "$HOST" 2>/dev/null | awk 'NR==1{print $1}')"
  if [ -n "${IPV6:-}" ]; then
    echo "$IPV6 $HOST" >> /etc/hosts
    echo "[entrypoint_wrap] pinned $HOST -> $IPV6" >&2
  else
    echo "[entrypoint_wrap] WARN: no IPv6 for $HOST (ahostsv6 empty)" >&2
  fi
fi

exec /app/scripts/backend_entrypoint.sh "$@"
