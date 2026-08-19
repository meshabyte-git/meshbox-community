#!/usr/bin/env bash
set -euo pipefail
[[ ${EUID:-$(id -u)} -eq 0 ]] || { echo "Run as root: sudo ./scripts/install-community-site.sh" >&2; exit 1; }
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
command -v nginx >/dev/null 2>&1 || { echo "nginx is required. Install it first (e.g. apt install nginx)." >&2; exit 1; }
install -d -m 0755 /opt/meshbox-community
rm -rf /opt/meshbox-community/community-site
cp -a "$ROOT/community-site" /opt/meshbox-community/community-site
install -m 0644 "$ROOT/community-site/nginx/community.meshbox.co.uk.conf" /etc/nginx/sites-available/community.meshbox.co.uk
ln -sfn /etc/nginx/sites-available/community.meshbox.co.uk /etc/nginx/sites-enabled/community.meshbox.co.uk
nginx -t
systemctl reload nginx
echo "Community site installed. Local origin: http://127.0.0.1:8080 (via nginx listener on 8080)."
echo "Point your tunnel at http://127.0.0.1:8080."
