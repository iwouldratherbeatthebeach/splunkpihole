# Architecture

## Why both raw logs and the API?

A dnsmasq text log records query, forwarding, and reply messages on separate
lines. Correlating those messages reliably requires serial IDs or transaction
state and becomes fragile across log rotation and format changes.

Pi-hole v6 `/api/queries` returns one complete record containing:

- stable query ID and timestamp
- client IP and resolved client name
- queried domain and RR type
- final status and blocking mechanism
- upstream destination
- reply type and response time
- DNSSEC result
- list ID and CNAME-blocking target
- Extended DNS Error code and text

The API feed therefore powers dashboards and detections. Raw logs are retained
for service troubleshooting, immediate visibility, and forensic context.

## App placement

| Component | Pi-hole UF | Search head | Indexer |
|---|---:|---:|---:|
| `TA-pihole` | Yes | Yes | Yes |
| `pihole_forwarder_inputs` | Yes | No | No |
| `SA-pihole` | No | Yes | Optional |
| `pihole_indexes` | No | No | Yes |

For an all-in-one Splunk instance, install `TA-pihole`, `SA-pihole`, and
`pihole_indexes` on that instance.

## Data ownership

- `pihole:query:json` is the analytics source of truth.
- `pihole:metric:json` provides point-in-time service and performance state.
- Raw log sourcetypes are not counted as DNS transactions to avoid double
  counting.
- The `pihole` index defaults to 10 GB and 90-day retention; adjust locally.

## Security model

- The Pi-hole app password is supplied to the forwarder through systemd.
- It is not stored in Git, Splunk configuration, or event payloads.
- The API collector performs read-only GET requests after authentication.
- `webserver.api.app_sudo` is not required.
- The package never changes Pi-hole blocking or configuration.
