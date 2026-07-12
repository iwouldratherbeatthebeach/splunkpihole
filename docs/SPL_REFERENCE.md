# SPL reference

## Overall service level

```spl
`pihole_queries`
| stats count as total
        count(eval(action="blocked")) as blocked
        count(eval(forwarded=true())) as forwarded
        count(eval(cached=true())) as cached
        dc(src) as clients
        dc(query) as domains
        avg(eval(if(reply_time_ms>=0,reply_time_ms,null()))) as avg_reply_ms
        perc95(eval(if(reply_time_ms>=0,reply_time_ms,null()))) as p95_reply_ms
| eval block_rate=round(100*blocked/total,2),
       cache_rate=round(100*cached/total,2)
```

## Noisiest clients

```spl
`pihole_queries`
| stats count as queries
        count(eval(action="blocked")) as blocked
        dc(query) as unique_domains
        values(src_name) as names
  by src
| eval block_rate=round(100*blocked/queries,2)
| sort - queries
```

## Client-domain matrix

```spl
`pihole_queries`
| chart count over src by query limit=20
```

## Slow upstreams

```spl
`pihole_queries` forwarded=true reply_time_ms>=0
| stats count as queries
        avg(reply_time_ms) as avg_ms
        perc95(reply_time_ms) as p95_ms
        max(reply_time_ms) as max_ms
  by upstream
| where queries>=10
| sort - p95_ms
```

## Newly observed domains

```spl
`pihole_queries` earliest=-30d
| stats min(_time) as first_seen
        max(_time) as last_seen
        count
        dc(src) as clients
  by query
| where first_seen>=relative_time(now(),"-24h")
| convert ctime(first_seen) ctime(last_seen)
| sort - first_seen
```

## Query-volume anomaly by client

```spl
`pihole_queries` earliest=-24h
| bin _time span=5m
| stats count as queries by _time src
| eventstats avg(queries) as baseline stdev(queries) as deviation by src
| eval zscore=if(deviation>0,(queries-baseline)/deviation,0)
| where _time>=relative_time(now(),"-10m") AND zscore>=4 AND queries>=100
| sort - zscore
```

## Block list contribution

```spl
`pihole_queries` action=blocked
| stats count as blocks dc(query) as domains dc(src) as clients by list_id status
| sort - blocks
```

## DNSSEC and EDE failures

```spl
`pihole_queries`
| where dnssec="BOGUS" OR ede_code>0
| stats count values(ede_text) as ede_text values(reply_code) as replies
  by src query dnssec ede_code
| sort - count
```
