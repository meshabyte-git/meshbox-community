#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/generated-bootstrap"
rm -rf "$OUT"; mkdir -p "$OUT"

yesno(){ local prompt="$1" default="${2:-y}" ans; local hint='[y/N]'; [[ "$default" == y ]] && hint='[Y/n]'; read -r -p "$prompt $hint " ans; ans="${ans:-$default}"; [[ "$ans" =~ ^[Yy]$ ]]; }
read -r -p "Agent port [9876]: " PORT; PORT="${PORT:-9876}"
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || ((PORT<1 || PORT>65535)); then echo "Invalid port." >&2; exit 1; fi
read -r -p "Bind address [0.0.0.0]: " BIND; BIND="${BIND:-0.0.0.0}"
CPU=false; MEMORY=false; STORAGE=false; UPTIME=false; NETWORK=false; OSINFO=false; IP=false; TSIP=false
if yesno "Enable CPU telemetry?" y; then CPU=true; fi
if yesno "Enable memory telemetry?" y; then MEMORY=true; fi
if yesno "Enable storage telemetry?" y; then STORAGE=true; fi
if yesno "Enable uptime telemetry?" y; then UPTIME=true; fi
if yesno "Enable network speed telemetry?" y; then NETWORK=true; fi
if yesno "Enable operating system telemetry?" y; then OSINFO=true; fi
if yesno "Enable local IP telemetry?" y; then IP=true; fi
if yesno "Enable Tailscale IP telemetry?" n; then TSIP=true; fi
STATUS=false; MOTD=false; INSTALL_TS=false
if yesno "Enable the standard local status page?" n; then STATUS=true; fi
if yesno "Install graphical MOTD?" n; then MOTD=true; fi
if yesno "Install Tailscale if it is not already present?" n; then INSTALL_TS=true; fi
cat > "$OUT/config.json" <<JSON
{
  "agent": {"bind": "$BIND", "port": $PORT, "status_page": $STATUS, "cors_origins": ["*"]},
  "telemetry": {"cpu": $CPU, "memory": $MEMORY, "storage": $STORAGE, "uptime": $UPTIME, "network_speed": $NETWORK, "operating_system": $OSINFO, "ip_address": $IP, "tailscale_ip": $TSIP}
}
JSON
cp "$ROOT/agent/dashboard-agent.py" "$OUT/"
cp "$ROOT/agent/community-dashboard-agent.service" "$OUT/"
cat > "$OUT/install-agent.sh" <<BASH2
#!/usr/bin/env bash
set -euo pipefail
[[ \${EUID:-\$(id -u)} -eq 0 ]] || { echo "Run as root: sudo ./install-agent.sh" >&2; exit 1; }
HERE="\$(cd "\$(dirname "\${BASH_SOURCE[0]}")" && pwd)"
install -d -m 0755 /opt/community-dashboard-agent /etc/community-dashboard-agent
install -m 0755 "\$HERE/dashboard-agent.py" /opt/community-dashboard-agent/dashboard-agent.py
install -m 0644 "\$HERE/config.json" /etc/community-dashboard-agent/config.json
install -m 0644 "\$HERE/community-dashboard-agent.service" /etc/systemd/system/community-dashboard-agent.service
if $INSTALL_TS && ! command -v tailscale >/dev/null 2>&1; then
  echo "Installing Tailscale from the official Tailscale installer..."
  if command -v curl >/dev/null 2>&1; then curl -fsSL https://tailscale.com/install.sh | sh; else echo "curl is required for automatic Tailscale installation." >&2; exit 1; fi
fi
if $MOTD; then
cat >/etc/profile.d/community-dashboard-motd.sh <<'MOTD'
#!/usr/bin/env bash
[[ -t 1 ]] || return 0
CFG=/etc/community-dashboard-agent/config.json
PORT=\$(python3 -c 'import json;print(json.load(open("'\$CFG'"))["agent"]["port"])' 2>/dev/null || echo 9876)
HOST=\$(hostname)
IP=\$(hostname -I 2>/dev/null | awk '{print \$1}')
printf '\n\033[1;36m%s\033[0m  \033[1;32m● ONLINE\033[0m\n' "\$HOST"
printf 'Dashboard Agent: http://%s:%s/api/status\n\n' "\${IP:-localhost}" "\$PORT"
MOTD
chmod 0755 /etc/profile.d/community-dashboard-motd.sh
fi
systemctl daemon-reload
systemctl enable --now community-dashboard-agent.service
echo
echo "Agent installed."
echo "API:    http://<server-ip>:$PORT/api/status"
if $STATUS; then echo "Status: http://<server-ip>:$PORT/status"; fi
echo "Health: http://<server-ip>:$PORT/health"
BASH2
chmod +x "$OUT/install-agent.sh"
cat > "$OUT/uninstall-agent.sh" <<'BASH3'
#!/usr/bin/env bash
set -euo pipefail
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "Run as root." >&2; exit 1; }
systemctl disable --now community-dashboard-agent.service 2>/dev/null || true
rm -f /etc/systemd/system/community-dashboard-agent.service /etc/profile.d/community-dashboard-motd.sh
rm -rf /opt/community-dashboard-agent /etc/community-dashboard-agent
systemctl daemon-reload
echo "Community Dashboard Agent removed. Tailscale is intentionally left untouched."
BASH3
chmod +x "$OUT/uninstall-agent.sh"
cat > "$OUT/README.txt" <<EOF
Generated Community Dashboard Agent bootstrap
Port: $PORT
Bind: $BIND
Status page: $STATUS
Graphical MOTD: $MOTD
Tailscale install: $INSTALL_TS

Run: sudo ./install-agent.sh
Edit later: /etc/community-dashboard-agent/config.json
Restart after changes: sudo systemctl restart community-dashboard-agent
EOF
printf '\nGenerated: %s\n' "$OUT"
printf 'Copy this folder to the target Linux server and run: sudo ./install-agent.sh\n'
