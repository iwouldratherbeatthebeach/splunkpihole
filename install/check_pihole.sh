#!/usr/bin/env bash
set -u

SPLUNK_HOME="${SPLUNK_HOME:-/opt/splunkforwarder}"
failed=0

check() {
  local label="$1"
  shift
  if "$@" >/dev/null 2>&1; then
    printf '[OK]   %s\n' "$label"
  else
    printf '[FAIL] %s\n' "$label"
    failed=1
  fi
}

check "Pi-hole API is reachable" curl -fsS http://127.0.0.1/api/auth
check "dnsmasq log exists" test -r /var/log/pihole/pihole.log
check "FTL log exists" test -r /var/log/pihole/FTL.log
check "webserver log exists" test -r /var/log/pihole/webserver.log
check "Splunk forwarder exists" test -x "${SPLUNK_HOME}/bin/splunk"

if [[ -x "${SPLUNK_HOME}/bin/splunk" ]]; then
  "${SPLUNK_HOME}/bin/splunk" list forward-server || true
  "${SPLUNK_HOME}/bin/splunk" btool inputs list --debug | grep -A8 -E 'pihole|TA-pihole' || true
fi

exit "$failed"
