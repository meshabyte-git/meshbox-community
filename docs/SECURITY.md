# Security

The agent exposes read-only HTTP endpoints only: `/health`, `/api/status`, and optional `/status`. It has no command, configuration, shell or write endpoint.

Do not expose a plain agent directly to the public Internet unless you have deliberately placed suitable access control/TLS/firewalling in front of it. Local IP or private Tailscale connectivity is preferred.

The community live demo agent binds to `127.0.0.1` and disables IP Address and Tailscale IP telemetry before nginx proxies the demo endpoints.
