#!/usr/bin/env bash
set -euo pipefail
[[ \${EUID:-$(id -u)} -eq 0 ]] || { echo "Run as root: sudo ./install-dashboard.sh" >&2; exit 1; }
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
install -d -m 0755 /opt/community-server-dashboard
cp "$HERE/index.html" "$HERE/servers.json" "$HERE/serve-dashboard.py" /opt/community-server-dashboard/
chmod 0755 /opt/community-server-dashboard/serve-dashboard.py
cat >/etc/systemd/system/community-server-dashboard.service <<'EOF'
[Unit]
Description=Community Server Dashboard
After=network-online.target
Wants=network-online.target
[Service]
Type=simple
WorkingDirectory=/opt/community-server-dashboard
ExecStart=/usr/bin/python3 /opt/community-server-dashboard/serve-dashboard.py --port 8080 --bind 127.0.0.1
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now community-server-dashboard.service
echo "Dashboard installed at http://127.0.0.1:8080"
echo "Use a reverse proxy, tunnel, or change the service bind if LAN access is required."
