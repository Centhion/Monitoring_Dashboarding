# Maintenance Window Management

## Overview

The monitoring platform supports three methods for silencing alerts during planned maintenance:

1. **Ad hoc silences** via the Alertmanager UI (manual, immediate)
2. **Programmatic silences** via the `maintenance_window.py` script (API-driven, schedulable)
3. **Recurring mute timings** via Grafana notification policies (config-driven, repeating)

## Method 1: Ad Hoc Silences (Alertmanager UI)

Best for: Unplanned maintenance, quick one-off suppressions.

1. Open Alertmanager at `http://<alertmanager>:9093/#/silences`
2. Click "New Silence"
3. Set matchers to scope the silence:
   - `datacenter = site-a` -- silence all alerts for a site
   - `hostname = server01` -- silence alerts for a single host
   - `role = sql` -- silence all SQL server alerts
   - `alertname = WindowsCPUHigh` -- silence a specific alert type
4. Set start/end time and add a comment
5. Click "Create"

## Method 2: Programmatic Silences (API Script)

Best for: Pre-planned maintenance with known start/end times, automation integration.

### Create a Maintenance Window

```bash
# 4-hour window starting now
python3 scripts/maintenance_window.py create \
    --name "Site-A Patching" \
    --duration 4h \
    --grafana-url http://localhost:3000 \
    --api-key "$GRAFANA_API_KEY"

# Specific time range
python3 scripts/maintenance_window.py create \
    --name "SQL Upgrade" \
    --start "2026-03-15T02:00:00Z" \
    --end "2026-03-15T06:00:00Z" \
    --grafana-url http://localhost:3000 \
    --api-key "$GRAFANA_API_KEY"
```

### List Active Windows

```bash
python3 scripts/maintenance_window.py list \
    --grafana-url http://localhost:3000 \
    --api-key "$GRAFANA_API_KEY"
```

### Delete a Window

```bash
python3 scripts/maintenance_window.py delete \
    --name "Site-A Patching" \
    --grafana-url http://localhost:3000 \
    --api-key "$GRAFANA_API_KEY"
```

### Duration Formats

The `--duration` flag accepts human-readable formats:
- `30m` -- 30 minutes
- `4h` -- 4 hours
- `2h30m` -- 2 hours 30 minutes
- `1d` -- 1 day
- `1d4h` -- 1 day 4 hours

### Environment Variables

Instead of passing flags every time, set these environment variables:

| Variable | Description |
|----------|-------------|
| `GRAFANA_URL` | Grafana base URL (default: http://localhost:3000) |
| `GRAFANA_API_KEY` | API key with Editor or Admin role |
| `GRAFANA_USER` | Username (alternative to API key) |
| `GRAFANA_PASSWORD` | Password (alternative to API key) |

## Method 3: Recurring Mute Timings (Grafana Config)

Best for: Regular maintenance schedules (weekly patching, monthly upgrades).

Mute timings are defined in `configs/grafana/notifiers/notifiers.yml` under the `muteTimes` section:

```yaml
muteTimes:
  - orgId: 1
    name: "Tuesday Maintenance"
    time_intervals:
      - times:
          - start_time: "00:00"
            end_time: "06:00"
        weekdays: ["tuesday"]

  - orgId: 1
    name: "Monthly Patching"
    time_intervals:
      - times:
          - start_time: "00:00"
            end_time: "23:59"
        weekdays: ["saturday"]
        days_of_month: ["1:7"]
```

### Activating a Mute Timing

A mute timing must be referenced by a notification policy route to take effect:

1. Define the mute timing in `notifiers.yml`
2. Reference it in a route using `mute_time_intervals`:
   ```yaml
   routes:
     - receiver: "Microsoft Teams"
       mute_time_intervals:
         - "Tuesday Maintenance"
   ```
3. Or activate via the Grafana UI: Alerting > Notification Policies > Edit route > Mute timings

### Site-Specific Mute Timings

Combine mute timings with datacenter matchers to silence alerts only for a specific site:

```yaml
routes:
  - receiver: "Site-A Email"
    matchers:
      - datacenter = site-a
    mute_time_intervals:
      - "Site-A Maintenance"
```

## Choosing the Right Method

| Scenario | Method |
|----------|--------|
| Emergency maintenance, unknown duration | Ad hoc silence (Alertmanager UI) |
| Planned patching with known schedule | Programmatic silence (script) |
| Every Tuesday night, same window | Recurring mute timing (config) |
| Per-site maintenance at different times | Site-specific mute timing (config + matcher) |
| CI/CD pipeline integration | Programmatic silence (script) |

## Configuration Files

| File | Purpose |
|------|---------|
| `scripts/maintenance_window.py` | API helper for creating/listing/deleting mute timings |
| `configs/grafana/notifiers/notifiers.yml` | Recurring mute timing definitions |
| `configs/alertmanager/alertmanager.yml` | Alertmanager silence API (direct API access) |
