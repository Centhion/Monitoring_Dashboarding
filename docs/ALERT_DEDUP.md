# Alert Deduplication Architecture

## Overview

The monitoring platform uses mass-outage detection to automatically suppress per-host alert noise during large-scale failures. This approach requires zero manual topology maintenance -- it relies on statistical thresholds across the existing `datacenter` and `role` label taxonomy.

## How It Works

### Mass-Outage Detection Pipeline

1. **Recording rules** (`configs/prometheus/outage_recording_rules.yml`) continuously compute:
   - `site:hosts_up:count` -- number of hosts reporting `up == 1` per datacenter
   - `site:hosts_total:count` -- total hosts per datacenter (including down)
   - `site:hosts_up_ratio:current` -- percentage of hosts up per datacenter
   - Equivalent metrics per role: `role:hosts_up_ratio:current`

2. **Outage alert rules** (`alerts/prometheus/outage_alerts.yml`) fire when:
   - `SitePartialOutage` -- less than 70% of a site's hosts are up (warning)
   - `SiteMajorOutage` -- less than 30% of a site's hosts are up (critical)
   - `RolePartialOutage` -- less than 70% of a role's hosts are up at a site (warning)
   - All rules require a minimum host count (5+) to prevent false positives on small sites

3. **Alertmanager inhibition rules** (`configs/alertmanager/alertmanager.yml`) suppress noise:
   - `SiteMajorOutage` suppresses ALL per-host critical and warning alerts for that datacenter
   - `SitePartialOutage` suppresses per-host warning alerts (critical still fires)
   - `RolePartialOutage` suppresses per-role warning alerts
   - Matching uses `equal: [datacenter]` to scope suppression to the affected site

### Why This Design

| Approach | Maintenance | Accuracy | Complexity |
|----------|-------------|----------|------------|
| Full topology mapping (upstream_device labels) | High -- must maintain per-host dependency tree | High -- knows exact blast radius | High |
| Statistical mass-outage detection | Zero -- uses existing labels | Good -- catches 80%+ of real outages | Low |
| Manual grouping rules | Medium -- must update when fleet changes | Medium | Medium |

The statistical approach was chosen because:
- The fleet uses a consistent label taxonomy (`datacenter`, `role`) that naturally groups hosts
- Most mass outages are site-level (network/power) or role-level (shared dependency)
- Zero maintenance means it scales as the fleet grows without config changes
- Per-host topology mapping is available as an optional enhancement (see below)

## Inhibition Rule Hierarchy

```
SiteMajorOutage (critical)
  └── Suppresses: ALL per-host alerts (critical + warning) at that site
      └── Rationale: If <30% of a site is up, the problem is infrastructure-level

SitePartialOutage (warning)
  └── Suppresses: per-host WARNING alerts at that site
      └── Rationale: If <70% is up, individual warnings are noise
      └── Per-host CRITICAL alerts still fire (may indicate separate issues)

RolePartialOutage (warning)
  └── Suppresses: per-role WARNING alerts
      └── Rationale: If most SQL servers are down, individual SQL alerts are noise
```

### Self-Inhibition Prevention

The outage alerts use an `outage_scope: site` label to differentiate themselves from per-host alerts. The inhibition rules match `outage_scope != "site"` on the target side, preventing outage alerts from suppressing each other.

## Optional: Per-Host Topology Mapping

For environments that want precise dependency-based suppression, the `upstream_device` label pattern is available as an enhancement:

1. Add `upstream_device` label to Alloy agent configs identifying each host's network dependency
2. Create inhibition rules that suppress host alerts when `upstream_device` is down
3. This provides exact blast radius awareness but requires maintaining the topology map

This is not implemented in the template because it requires site-specific knowledge that varies per deployment.

## Configuration Files

| File | Purpose |
|------|---------|
| `configs/prometheus/outage_recording_rules.yml` | Computes host-up ratios per site and role |
| `alerts/prometheus/outage_alerts.yml` | Fires site/role outage alerts |
| `configs/alertmanager/alertmanager.yml` | Inhibition rules for alert suppression |

## Testing

To validate the deduplication pipeline:

1. Start the Docker Compose stack
2. Stop multiple Alloy agents simultaneously (simulates outage)
3. Verify outage alerts fire after the threshold is crossed
4. Verify per-host alerts are suppressed by Alertmanager
5. Check Alertmanager UI for inhibited alerts (shown with "inhibited" status)
