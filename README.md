# Splunk for Pi-hole v3

A production-oriented Pi-hole v6 integration for Splunk.

This project intentionally separates deployment responsibilities:

- `TA-pihole`: Pi-hole log parsing and Python API collectors
- `SA-pihole`: macros, CIM-style normalization, dashboards, and alerts
- `pihole_indexes`: dedicated index definition
- `pihole_forwarder_inputs`: site-specific forwarder inputs and output target
- `install/`: deployment helpers for the Pi-hole and Splunk server

## Architecture

```text
Pi-hole 10.0.0.223
  ├─ Universal Forwarder monitors:
  │    /var/log/pihole/pihole.log
  │    /var/log/pihole/FTL.log
  │    /var/log/pihole/webserver.log
  └─ Scripted inputs call Pi-hole v6 API:
       /api/queries
       /api/stats/summary
       /api/stats/upstreams
       /api/info/*
       /api/dns/blocking
             │
             ▼ TCP 9997
Splunk robot2 10.0.0.230
  ├─ index=pihole
  ├─ TA-pihole
  └─ SA-pihole dashboards and alerts
```

The API query feed is the authoritative analytics source because each event is a
complete DNS transaction with query ID, client, domain, status, reply, upstream,
latency, DNSSEC, list ID, and Extended DNS Error fields. Raw logs remain useful
for immediate troubleshooting and Pi-hole service diagnostics.

## Included dashboards

1. Overview
2. Clients
3. Domains
4. Upstreams and Performance
5. Security Analytics
6. Pi-hole Operations
7. Query Explorer

## Default sourcetypes

| Sourcetype | Purpose |
|---|---|
| `pihole:query:json` | One normalized event per DNS query |
| `pihole:metric:json` | Pi-hole API summary and health snapshots |
| `pihole:dns` | Raw dnsmasq query/reply log |
| `pihole:ftl` | FTL service log |
| `pihole:web` | Embedded web server log |

## Install

See [`INSTALL.md`](INSTALL.md). Do not commit the Pi-hole app password to Git.
The collector reads it from the `PIHOLE_API_PASSWORD` environment variable.

## Validation

After data starts arriving:

```spl
index=pihole
| stats count by sourcetype host
```

Validate normalized query fields:

```spl
`pihole_queries`
| table _time pihole_node src src_name query query_type action status
        reply_code reply_time_ms dest dnssec list_id
| head 100
```

Validate CIM-style DNS tagging:

```spl
tag=dns index=pihole
| stats count by action query_type reply_code
```
