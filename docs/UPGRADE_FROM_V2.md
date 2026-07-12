# Upgrade from the original app

The original repository can remain installed while v3 is tested, but its
dashboard searches should not be used to validate v3 counts because they read
the raw `pihole` sourcetype.

Recommended migration:

1. Install the v3 apps under their new app IDs.
2. Create the dedicated `pihole` index.
3. Start `pihole:query:json` and `pihole:metric:json` collection.
4. Validate at least one hour of data.
5. Update any external searches to use the `pihole_queries` macro.
6. Disable the original `/var/log/pihole.log` monitor to avoid duplicate raw
   input and retire the old app after dashboard validation.

The v3 app does not reuse the original `sourcetype=pihole`; this prevents field
and dashboard collisions.
