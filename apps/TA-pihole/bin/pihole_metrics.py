#!/usr/bin/env python3
"""Collect Pi-hole v6 service, health, and summary metrics."""

from __future__ import annotations

import time
from typing import Dict

from pihole_common import PiHoleAPI, collector_lock, emit, emit_error, iso_utc, load_config


ENDPOINTS: Dict[str, str] = {
    "summary": "/api/stats/summary",
    "upstreams": "/api/stats/upstreams",
    "blocking": "/api/dns/blocking",
    "system": "/api/info/system",
    "ftl": "/api/info/ftl",
    "version": "/api/info/version",
    "database": "/api/info/database",
    "messages": "/api/info/messages/count",
    "sensors": "/api/info/sensors",
}


def collect() -> int:
    config = load_config()
    node = str(config["node"])
    collected_at = time.time()

    try:
        api = PiHoleAPI(config)
        api.authenticate()

        errors = 0
        for metric_name, endpoint in ENDPOINTS.items():
            try:
                payload = api.get(endpoint)
                payload.pop("took", None)
                emit(
                    {
                        "collected_at": collected_at,
                        "event_time": iso_utc(collected_at),
                        "event_type": "pihole_metric",
                        "metric_name": metric_name,
                        "endpoint": endpoint,
                        "pihole_node": node,
                        "vendor_product": "Pi-hole",
                        "data": payload,
                    }
                )
            except Exception as exc:
                errors += 1
                emit_error(node, f"pihole_metrics:{metric_name}", exc)
        return 1 if errors == len(ENDPOINTS) else 0
    except Exception as exc:
        emit_error(node, "pihole_metrics", exc)
        return 1


def main() -> int:
    config = load_config()
    node = str(config["node"])
    try:
        with collector_lock("metrics"):
            return collect()
    except Exception as exc:
        emit_error(node, "pihole_metrics", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
