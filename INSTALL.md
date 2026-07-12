# Installation

Assumptions used by the site-specific examples:

- Pi-hole: `10.0.0.223`
- Splunk all-in-one / receiving indexer: `robot2`, `10.0.0.230`
- Splunk receiving port: `9997`
- Splunk management port: `8089`
- Splunk index: `pihole`

## 1. Pi-hole prerequisites

Confirm Pi-hole v6 query logging:

```bash
sudo pihole-FTL --config dns.queryLogging true
sudo pihole-FTL --config misc.extraLogging false
sudo pihole-FTL --config misc.privacylevel 0
```

`extraLogging` is intentionally left disabled; the API already returns stable,
fully correlated query records.

Create a dedicated Pi-hole application password from the Pi-hole web interface
or API. Keep the plaintext value only in the forwarder's systemd environment.

## 2. Splunk receiver

On `robot2`, enable TCP receiving on `9997` if it is not already enabled:

```bash
$SPLUNK_HOME/bin/splunk enable listen 9997 -auth admin:YOUR_PASSWORD
```

Copy these apps into `$SPLUNK_HOME/etc/apps/`:

```text
pihole_indexes
TA-pihole
SA-pihole
```

Restart Splunk:

```bash
$SPLUNK_HOME/bin/splunk restart
```

## 3. Universal Forwarder on the Pi-hole

Install the ARM64 Splunk Universal Forwarder that matches the Pi-hole operating
system and architecture.

Copy these apps into `$SPLUNK_HOME/etc/apps/` on the Pi-hole:

```text
TA-pihole
pihole_forwarder_inputs
```

The site app already targets `10.0.0.230:9997`.

## 4. Grant the forwarder read access

Determine the service account:

```bash
ps -eo user,comm,args | grep '[s]plunkd'
```

Replace `splunkfwd` below if the process runs under another account:

```bash
sudo setfacl -m u:splunkfwd:rx /var/log/pihole
sudo setfacl -m u:splunkfwd:r /var/log/pihole/pihole.log
sudo setfacl -m u:splunkfwd:r /var/log/pihole/FTL.log
sudo setfacl -m u:splunkfwd:r /var/log/pihole/webserver.log
sudo setfacl -d -m u:splunkfwd:r /var/log/pihole
```

Verify:

```bash
sudo -u splunkfwd head -n 1 /var/log/pihole/pihole.log
```

## 5. Store the API password securely

Find the forwarder service:

```bash
systemctl list-units --type=service | grep -i splunk
```

Create a systemd override, replacing `SplunkForwarder.service` if necessary:

```bash
sudo systemctl edit SplunkForwarder.service
```

Add:

```ini
[Service]
Environment="PIHOLE_API_PASSWORD=REPLACE_WITH_APP_PASSWORD"
Environment="PIHOLE_API_BASE_URL=http://127.0.0.1"
Environment="PIHOLE_NODE=pihole-10.0.0.223"
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart SplunkForwarder.service
```

The app password is not stored in `inputs.conf`, Git, or indexed events.

## 6. Verify forwarding

On the Pi-hole:

```bash
$SPLUNK_HOME/bin/splunk list forward-server
$SPLUNK_HOME/bin/splunk btool inputs list --debug | grep -A8 pihole
```

On `robot2`:

```spl
index=pihole earliest=-15m
| stats count min(_time) as first_seen max(_time) as last_seen by host sourcetype
| convert ctime(first_seen) ctime(last_seen)
```

## 7. Troubleshooting

Collector errors are emitted as JSON with `event_type=collector_error` into the
same API sourcetype. Search:

```spl
index=pihole event_type=collector_error
| table _time pihole_node collector error
```

Check the forwarder internal log:

```spl
index=_internal host=<PIHOLE_HOST> source=*splunkd.log*
(component=ExecProcessor OR component=TailReader)
| table _time log_level component message
```

The checkpoint is stored beneath:

```text
$SPLUNK_HOME/var/lib/splunk/modinputs/pihole_api/
```

Removing the checkpoint causes an overlap re-read. Query IDs are used to
suppress duplicate events.
