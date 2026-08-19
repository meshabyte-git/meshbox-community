# MeshBox Community — Gen 1

A fully self-hosted Linux telemetry agent, optional local status page and clean multi-server dashboard. The downloadable software communicates only with systems configured by its operator. It has no registration, cloud relay, analytics or phone-home service.

## Included

- `agent/` — dependency-light Python 3 Linux telemetry agent.
- `status-page/` — the optional read-only page is built into the agent.
- `dashboard/` — server-wall dashboard: no sidebar, light/dark mode, refresh selector and settings cog.
- `bootstrap/` — terminal bootstrap generator.
- `community-site/` — source for `community.meshbox.co.uk`, including browser Agent Builder and demo pages.
- `scripts/` — community-site and live-demo deployment helpers.
- `docs/` and `examples/` — configuration/security guidance.

## Telemetry choices

Every group is independently switchable and disabled groups are omitted from API responses:

- CPU
- Memory
- Storage
- Uptime
- Network Speed (RX/TX)
- Operating System
- IP Address
- Tailscale IP

## Dashboard server connections

The settings cog allows Local IP/hostname, Tailscale IP, or Direct IP/public address, with a user-selected agent port and HTTP/HTTPS protocol. Settings are stored in the browser running the dashboard; `servers.json` provides defaults.

## Community website paths

- `/` — welcome page
- `/builder/` — browser-based agent bootstrap builder
- `/demo/status/` — wrapper for the VM's live local status page
- `/demo/dashboard/` — real dashboard UI using the VM as a live demo server
- `/docs/` — quick start
- `/download/` — release/download area

The demo agent binds only to localhost and its public demo config disables IP Address and Tailscale IP telemetry.

## Licence

Apache License 2.0. See `LICENSE` and `NOTICE`.
