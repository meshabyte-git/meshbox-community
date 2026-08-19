# Configuration

Agent configuration lives at `/etc/community-dashboard-agent/config.json`. Each telemetry key is a boolean. Restart the service after edits with `sudo systemctl restart community-dashboard-agent`.

Dashboard defaults live in `dashboard/servers.json`. Runtime changes made through the settings cog are saved in that browser's local storage.
