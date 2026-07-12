#!/usr/bin/env python3
"""Collect normalized query events from the Pi-hole v6 API."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Set

from pihole_common import PiHoleAPI, collector_lock, emit, emit_error, iso_utc, load_checkpoint, load_config, save_checkpoint


BLOCKED_STATUSES = {
    "GRAVITY",
    "REGEX",
    "DENYLIST",
    "GRAVITY_CNAME",
    "REGEX_CNAME",
    "DENYLIST_CNAME",
    "EXTERNAL_BLOCKED_IP",
    "EXTERNAL_BLOCKED_NULL",
    "EXTERNAL_BLOCKED_NXRA",
    "EXTERNAL_BLOCKED_EDE15",
}


def normalize(row: Dict[str, Any], node: str) -> Dict[str, Any]:
    status = str(row.get("status") or "UNKNOWN").upper()
    client = row.get("client") if isinstance(row.get("client"), dict) else {}
    reply = row.get("reply") if isinstance(row.get("reply"), dict) else {}
    ede = row.get("ede") if isinstance(row.get("ede"), dict) else {}
    upstream = row.get("upstream")
    query_time = float(row.get("time") or time.time())

    blocked = status in BLOCKED_STATUSES
    cached = status in {"CACHE", "CACHE_STALE", "SPECIAL_DOMAIN"}
    forwarded = status in {"FORWARDED", "RETRIED", "RETRIED_DNSSEC"}
    allowed = cached or forwarded
    action = "blocked" if blocked else "allowed" if allowed else "unknown"

    return {
        "time": query_time,
        "event_time": iso_utc(query_time),
        "event_type": "dns_query",
        "vendor": "Pi-hole",
        "vendor_product": "Pi-hole FTL",
        "pihole_node": node,
        "query_id": row.get("id"),
        "src": client.get("ip"),
        "src_ip": client.get("ip"),
        "src_name": client.get("name"),
        "query": row.get("domain"),
        "domain": row.get("domain"),
        "query_type": row.get("type"),
        "record_type": row.get("type"),
        "status": status,
        "action": action,
        "blocked": blocked,
        "cached": cached,
        "forwarded": forwarded,
        "dest": upstream,
        "upstream": upstream,
        "reply_code": reply.get("type"),
        "reply_time_ms": reply.get("time"),
        "dnssec": row.get("dnssec"),
        "list_id": row.get("list_id"),
        "cname": row.get("cname"),
        "ede_code": ede.get("code"),
        "ede_text": ede.get("text"),
    }


def fetch_all(
    api: PiHoleAPI,
    since: float,
    until: float,
    batch_size: int,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    start = 0
    cursor = None

    while True:
        params: Dict[str, Any] = {
            "from": since,
            "until": until,
            "length": batch_size,
            "start": start,
        }
        if cursor is not None:
            params["cursor"] = cursor

        response = api.get("/api/queries", params=params)
        page = response.get("queries", [])
        if not isinstance(page, list):
            raise RuntimeError("Pi-hole /api/queries response did not contain a query list")

        rows.extend(item for item in page if isinstance(item, dict))
        if cursor is None:
            cursor = response.get("cursor")

        if len(page) < batch_size:
            break
        start += batch_size
        if start >= int(response.get("recordsFiltered") or response.get("recordsTotal") or 0):
            break

    return rows


def collect() -> int:
    config = load_config()
    node = str(config["node"])
    checkpoint = load_checkpoint(
        "queries",
        {"last_time": time.time() - 300, "recent_keys": []},
    )

    try:
        api = PiHoleAPI(config)
        api.authenticate()

        last_time = float(checkpoint.get("last_time", time.time() - 300))
        overlap = float(config["overlap_seconds"])
        until = time.time() + 1
        since = max(0.0, last_time - overlap)
        rows = fetch_all(api, since, until, int(config["batch_size"]))

        recent_keys: Set[str] = {str(x) for x in checkpoint.get("recent_keys", [])}
        emitted_keys: List[str] = []
        max_time = last_time

        rows.sort(key=lambda item: (float(item.get("time") or 0), int(item.get("id") or 0)))
        for row in rows:
            query_time = float(row.get("time") or 0)
            query_id = str(row.get("id") or "")
            event_key = f"{query_id}:{query_time:.6f}"
            duplicate = event_key in recent_keys
            too_old = query_time < last_time - overlap
            if duplicate or too_old:
                continue

            emit(normalize(row, node))
            emitted_keys.append(event_key)
            max_time = max(max_time, query_time)

        combined = list(dict.fromkeys(list(checkpoint.get("recent_keys", [])) + emitted_keys))
        save_checkpoint(
            "queries",
            {
                "last_time": max_time,
                "recent_keys": combined[-20000:],
                "updated_at": time.time(),
            },
        )
        return 0
    except Exception as exc:
        emit_error(node, "pihole_queries", exc)
        return 1


def main() -> int:
    config = load_config()
    node = str(config["node"])
    try:
        with collector_lock("queries"):
            return collect()
    except Exception as exc:
        emit_error(node, "pihole_queries", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
