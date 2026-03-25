# Changing Alert Thresholds

How to adjust when alerts fire -- making them more or less sensitive based on your environment.

---

## When to Change a Threshold

- An alert fires too often for conditions that are normal for your environment (false positives)
- An alert never fires despite genuine issues (too insensitive)
- A server role has different performance baselines than the defaults (e.g., SQL servers normally use 90%+ memory)

---

## Understanding Alert Thresholds

Each alert has two key settings:

1. **Threshold**: The value that triggers the alert (e.g., CPU > 90%)
2. **For duration**: How long the condition must persist before the alert fires (e.g., 30 minutes)

Both can be adjusted. See `docs/THRESHOLD_GUIDE.md` for the complete list of default thresholds.

---

## How to Request a Change

If you are a sysadmin without access to the git repository:

1. Identify the alert name (from the Teams notification or Grafana Alerting page)
2. Note the current threshold and what you think it should be
3. Provide justification (e.g., "WindowsMemoryHighWarning fires daily on SQL servers because they legitimately use 90% memory")
4. Send the request to the platform engineering team

The engineer will review, apply, and validate the change.

---

## How to Apply a Change (Engineers)

### Alert Rule Thresholds

Alert rules are defined in YAML files under `alerts/prometheus/`.

**Example**: Change WindowsCpuHighWarning from 90% to 92%.

1. Open `alerts/prometheus/windows_alerts.yml`
2. Find the rule:
   ```yaml
   - alert: WindowsCpuHighWarning
     expr: instance:windows_cpu_utilization:ratio > 0.90
     for: 30m
   ```
3. Change the threshold:
   ```yaml
     expr: instance:windows_cpu_utilization:ratio > 0.92
   ```
4. Reload Prometheus (no restart needed):
   ```bash
   curl -X POST http://localhost:9090/-/reload
   ```
5. Verify the change took effect: open `http://localhost:9090/rules` and find the updated rule

### For Duration Changes

To make an alert fire faster or slower:

```yaml
# Fire after 15 minutes instead of 30
- alert: WindowsCpuHighWarning
  expr: instance:windows_cpu_utilization:ratio > 0.90
  for: 15m
```

### Dashboard Color Thresholds

Dashboard panels use color thresholds (green/yellow/red) that are separate from alert rules. To change dashboard colors:

1. Open the dashboard JSON in `dashboards/`
2. Find the panel's `thresholds` block:
   ```json
   "thresholds": {
     "steps": [
       {"color": "green", "value": null},
       {"color": "yellow", "value": 80},
       {"color": "red", "value": 90}
     ]
   }
   ```
3. Adjust the values
4. Grafana auto-reloads dashboard JSON every 30 seconds -- no restart needed

Or use the Grafana UI: Edit panel > Field > Thresholds. Note that UI changes are overwritten on container restart since dashboards are provisioned from files.

---

## Commit the Change

After validating the threshold change works:

```bash
git add alerts/prometheus/<file>.yml
git commit -m "fix: tune <AlertName> threshold from X to Y"
git push
```

This ensures the change is tracked and survives stack rebuilds.

---

## Current Defaults

See `docs/THRESHOLD_GUIDE.md` for the complete table of thresholds for all server types, roles, and infrastructure components.

See `docs/ALERT_CATALOG.md` for fleet-scale noise risk assessment and tuning recommendations per alert.
