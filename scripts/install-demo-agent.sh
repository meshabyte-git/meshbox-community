#!/usr/bin/env bash
set -euo pipefail
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "Run as root." >&2; exit 1; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
install -d -m 0755 /opt/community-dashboard-agent /etc/community-dashboard-agent
install -m 0755 "$ROOT/agent/dashboard-agent.py" /opt/community-dashboard-agent/dashboard-agent.py
install -m 0644 "$ROOT/community-site/demo-agent-config.json" /etc/community-dashboard-agent/config.json
install -m 0644 "$ROOT/agent/community-dashboard-agent.service" /etc/systemd/system/community-dashboard-agent.service
# Force the supplied service/config path; bind/port come from the demo config.
systemctl daemon-reload
systemctl enable --now community-dashboard-agent.service
echo "Live demo agent installed on 127.0.0.1:9876; IP telemetry is disabled."
