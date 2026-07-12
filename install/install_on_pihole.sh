#!/usr/bin/env bash
set -euo pipefail

SPLUNK_HOME="${SPLUNK_HOME:-/opt/splunkforwarder}"
PACKAGE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ ! -x "${SPLUNK_HOME}/bin/splunk" ]]; then
  echo "Splunk Universal Forwarder was not found at ${SPLUNK_HOME}" >&2
  echo "Set SPLUNK_HOME and run this script again." >&2
  exit 1
fi

install_app() {
  local app="$1"
  rm -rf "${SPLUNK_HOME}/etc/apps/${app}"
  cp -a "${PACKAGE_ROOT}/apps/${app}" "${SPLUNK_HOME}/etc/apps/${app}"
}

install_app "TA-pihole"
install_app "pihole_forwarder_inputs"

chmod 0755 "${SPLUNK_HOME}/etc/apps/TA-pihole/bin/"*.py

echo "Installed TA-pihole and pihole_forwarder_inputs."
echo "Add PIHOLE_API_PASSWORD to the forwarder systemd service, grant log ACLs,"
echo "then restart the Universal Forwarder."
