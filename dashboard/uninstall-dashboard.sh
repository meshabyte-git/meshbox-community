#!/usr/bin/env bash
set -euo pipefail
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "Run as root." >&2; exit 1; }
systemctl disable --now community-server-dashboard.service 2>/dev/null || true
rm -f /etc/systemd/system/community-server-dashboard.service
rm -rf /opt/community-server-dashboard
systemctl daemon-reload
echo "Dashboard removed."
