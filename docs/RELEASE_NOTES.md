# Release notes

## 3.0.1

- Fixed dashboards returning no results when `pihole_node` was absent from indexed payload fields.
- Dashboard node selectors and filters now use Splunk's indexed `host` metadata.
- Added a search-time calculated field, `pihole_node=coalesce(pihole_node,host)`, for backward compatibility with existing SPL and historical data.
- Updated saved searches to group on `host` and retain `pihole_node` as the display name.

## 3.0.0

- Initial Pi-hole v6 API and raw-log analytics release.
