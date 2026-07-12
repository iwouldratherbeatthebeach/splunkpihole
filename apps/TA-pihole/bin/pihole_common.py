#!/usr/bin/env python3
"""Shared helpers for Pi-hole v6 scripted inputs."""

from __future__ import annotations

import configparser
from datetime import datetime, timezone
import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from contextlib import contextmanager
from typing import Any, Dict, Iterator, Optional


APP_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = APP_ROOT / "default" / "pihole_api.conf"
LOCAL_CONFIG = APP_ROOT / "local" / "pihole_api.conf"


def load_config() -> Dict[str, Any]:
    parser = configparser.ConfigParser()
    parser.read([str(DEFAULT_CONFIG), str(LOCAL_CONFIG)])
    section = parser["pihole"] if parser.has_section("pihole") else {}

    def value(name: str, default: str) -> str:
        return os.environ.get(name, section.get(name.lower(), default)).strip()

    return {
        "base_url": value("PIHOLE_API_BASE_URL", "http://127.0.0.1").rstrip("/"),
        "password": value("PIHOLE_API_PASSWORD", ""),
        "node": value("PIHOLE_NODE", socket.gethostname()),
        "timeout": float(value("PIHOLE_API_TIMEOUT", "15")),
        "verify_tls": value("PIHOLE_VERIFY_TLS", "true").lower() in {"1", "true", "yes", "on"},
        "overlap_seconds": float(value("PIHOLE_OVERLAP_SECONDS", "120")),
        "batch_size": min(max(int(value("PIHOLE_API_BATCH_SIZE", "5000")), 1), 10000),
    }


def checkpoint_dir() -> Path:
    splunk_home = os.environ.get("SPLUNK_HOME")
    if splunk_home:
        path = Path(splunk_home) / "var" / "lib" / "splunk" / "modinputs" / "pihole_api"
    else:
        path = APP_ROOT / "local" / "checkpoints"
    path.mkdir(parents=True, exist_ok=True)
    return path



@contextmanager
def collector_lock(name: str) -> Iterator[None]:
    """Prevent overlapping scripted-input executions on Linux."""
    lock_path = checkpoint_dir() / f"{name}.lock"
    handle = lock_path.open("a+", encoding="utf-8")
    try:
        try:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError(f"Collector {name} is already running") from exc
        yield
    finally:
        try:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except Exception:
            pass
        handle.close()

def load_checkpoint(name: str, default: Dict[str, Any]) -> Dict[str, Any]:
    path = checkpoint_dir() / f"{name}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            merged = dict(default)
            merged.update(data)
            return merged
    except (OSError, ValueError, TypeError):
        pass
    return dict(default)


def save_checkpoint(name: str, data: Dict[str, Any]) -> None:
    path = checkpoint_dir() / f"{name}.json"
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
    os.replace(temp, path)


class PiHoleAPI:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.base_url = str(config["base_url"])
        self.password = str(config["password"])
        self.timeout = float(config["timeout"])
        self.verify_tls = bool(config.get("verify_tls", True))
        self.sid: Optional[str] = None
        self.ssl_context = ssl.create_default_context()
        if not self.verify_tls:
            self.ssl_context = ssl._create_unverified_context()

    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        payload: Optional[Dict[str, Any]] = None,
        authenticated: bool = True,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            url += "?" + urllib.parse.urlencode(clean)

        headers = {"Accept": "application/json", "User-Agent": "TA-pihole/3.0"}
        if authenticated and self.sid:
            headers["X-FTL-SID"] = self.sid

        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout, context=self.ssl_context) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Pi-hole API HTTP {exc.code} for {endpoint}: {detail[:500]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Pi-hole API connection failed for {endpoint}: {exc.reason}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Pi-hole API returned invalid JSON for {endpoint}") from exc

    def authenticate(self) -> None:
        status = self._request("GET", "/api/auth", authenticated=False)
        session = status.get("session", {})
        if session.get("valid"):
            self.sid = session.get("sid")
            return
        if not self.password:
            raise RuntimeError(
                "Pi-hole API authentication is required but PIHOLE_API_PASSWORD is not set"
            )
        result = self._request(
            "POST",
            "/api/auth",
            payload={"password": self.password},
            authenticated=False,
        )
        session = result.get("session", {})
        self.sid = session.get("sid")
        if not session.get("valid") or not self.sid:
            raise RuntimeError("Pi-hole API authentication failed")

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self.sid is None:
            self.authenticate()
        return self._request("GET", endpoint, params=params)



def iso_utc(timestamp: Optional[float] = None) -> str:
    value = time.time() if timestamp is None else float(timestamp)
    dt = datetime.fromtimestamp(value, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond:06d}Z"

def emit(event: Dict[str, Any]) -> None:
    print(json.dumps(event, separators=(",", ":"), ensure_ascii=False), flush=True)


def emit_error(node: str, collector: str, error: Exception) -> None:
    emit(
        {
            "collected_at": time.time(),
            "event_time": iso_utc(),
            "event_type": "collector_error",
            "pihole_node": node,
            "collector": collector,
            "error": str(error),
            "vendor_product": "Pi-hole",
        }
    )


def nested_get(data: Dict[str, Any], *path: str, default: Any = None) -> Any:
    value: Any = data
    for key in path:
        if not isinstance(value, dict):
            return default
        value = value.get(key)
    return default if value is None else value
