#!/usr/bin/env bash
set -euo pipefail

SPLUNK_HOME="${SPLUNK_HOME:-/opt/splunk}"
PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -x "${SPLUNK_HOME}/bin/splunk" ]]; then
  echo "Splunk was not found at ${SPLUNK_HOME}" >&2
  echo "Set SPLUNK_HOME and run this script again." >&2
  exit 1
fi

install_app() {
  local app="$1"
  rm -rf "${SPLUNK_HOME}/etc/apps/${app}"
  cp -a "${PACKAGE_ROOT}/apps/${app}" "${SPLUNK_HOME}/etc/apps/${app}"
}

install_app "pihole_indexes"
install_app "TA-pihole"
install_app "SA-pihole"

echo "Installed pihole_indexes, TA-pihole, and SA-pihole."
echo "Enable TCP 9997 if needed, then restart Splunk."
