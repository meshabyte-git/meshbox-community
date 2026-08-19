# Telemetry

The agent can expose CPU utilisation/model/core count, memory usage, mounted storage usage, uptime, current network RX/TX throughput, Linux OS/architecture, local IP address and Tailscale IPv4 address. Every telemetry family is independently switchable. Disabled telemetry is not included in `/api/status` and is not rendered on `/status`.
