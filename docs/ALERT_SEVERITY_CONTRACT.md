# Alert Severity Contract

This document defines what each alert severity level means for the operations team. It governs how alerts are configured, routed, and responded to across the monitoring platform.

---

## Team Context

- **Team size**: 8 sysadmins + 2 engineers
- **On-call rotation**: None. Alerts are monitored during business hours only.
- **Notification channels**: Microsoft Teams (primary) + per-site email distribution lists
- **Business hours**: Monday-Friday, 07:00-17:00 local time per site
- **After-hours coverage**: Critical infrastructure alerts only, via email to site DLs. No pager, no phone escalation.

---

## Severity Definitions

### Critical -- Act Now

**Meaning**: A service, server, or infrastructure component is down or will be down imminently. Users or business operations are affected or will be within minutes.

**Expected response time**: Within 15 minutes during business hours. Next business day for after-hours alerts unless the affected system is business-critical (DC, SQL, IIS serving production traffic).

**Notification behavior**:
- Teams notification (immediate, grouped by site)
- Email to site-specific distribution list
- Repeats every **1 hour** until resolved or silenced

**Examples**:
- Server unreachable (WindowsServerDown, LinuxServerDown)
- Critical service stopped (AD, SQL, IIS, Docker daemon)
- Site or role outage detected (SiteMajorOutage, RolePartialOutage)
- Disk space below 10% (imminent data loss risk)
- TLS certificate expired or expiring within 7 days
- Hardware critical fault (Redfish health critical, temperature critical)

**Who acts**: Site sysadmin team. Escalate to engineers if root cause is unclear after 30 minutes.

**Expected volume**: 0-2 per site per day under normal operations. If higher, thresholds need tuning.

---

### Warning -- Investigate Soon

**Meaning**: A resource is degraded, trending toward failure, or outside normal operating parameters. No immediate user impact, but left unaddressed it will become critical.

**Expected response time**: Within 4 hours during business hours. Next business day for after-hours.

**Notification behavior**:
- Teams notification (grouped by site, batched with 60s wait)
- Email to site-specific distribution list
- Repeats every **4 hours** until resolved or silenced

**Examples**:
- CPU above 90% sustained (server overloaded but still responding)
- Memory above 85% (approaching OOM conditions)
- Disk space below 20% (weeks of runway, but needs attention)
- Windows service stopped (non-critical service)
- SQL buffer cache hit ratio low (performance degradation)
- Network interface utilization above 85%
- SNMP device rebooted unexpectedly
- Certificate expiring in 7-30 days

**Who acts**: Site sysadmin team during their next available window. No need to interrupt current work unless trending toward critical.

**Expected volume**: 3-10 per site per day. This is the "daily work queue" severity. If volume consistently exceeds 10/day per site, review thresholds.

---

### Info -- Awareness Only

**Meaning**: Something changed or a long-lead-time condition exists. No action required now. Used for planning, capacity management, and audit trails.

**Expected response time**: Review during weekly operations meeting or as time permits. No same-day response expected.

**Notification behavior**:
- Teams notification only (no email)
- Repeats every **12 hours** (essentially once per business day)
- Resolved notifications are suppressed (no "all clear" noise for info alerts)

**Examples**:
- Server rebooted (WindowsServerReboot, LinuxServerReboot) -- informational, not actionable unless unexpected
- Certificate expiring in 30-90 days -- planning window for renewal
- Warranty expiring in 60-90 days -- procurement planning
- Fleet trend thresholds (awareness of systemic patterns)

**Who acts**: No immediate action. Site lead reviews info alerts weekly for capacity planning and preventive maintenance scheduling.

**Expected volume**: 5-20 per site per day. These should never generate urgent attention. If sysadmins feel pressured to act on info alerts, the alert is miscategorized and should be promoted to warning or removed.

---

## Escalation Path

```
Alert fires
    |
    v
Site sysadmin team (via Teams + email DL)
    |
    | (30 min for critical, 4 hours for warning, no escalation for info)
    v
Engineers (platform team)
    |
    | (if infrastructure/platform issue, not server-level)
    v
Vendor support (if hardware or third-party software)
```

---

## Anti-Patterns -- What This Platform Must NOT Do

These behaviors caused alert fatigue in SCOM and must not be replicated:

1. **No per-host notification storms**: If 20 servers hit high CPU during a patching window, the team gets 1 notification per site listing all affected hosts -- not 20 separate notifications.

2. **No duplicate alerts for the same issue**: Inhibition rules suppress warning/info alerts when a server is already flagged as down. One root cause = one alert.

3. **No alerts without runbooks**: Every alert that fires must have a documented investigation and remediation path in `ALERT_RUNBOOKS.md`. If there's no runbook, the alert should not exist.

4. **No "acknowledge and ignore" culture**: If the team routinely ignores an alert, the alert is wrong. Either fix the threshold, reclassify the severity, or remove it. Alerts exist to drive action, not to be dismissed.

5. **No after-hours noise for non-critical issues**: Warning and info alerts during off-hours accumulate silently. The team reviews them at the start of the next business day.

---

## Threshold Change Process

Thresholds are not sacred. They are starting defaults that must be tuned based on real-world observation.

1. **Sysadmin identifies a noisy or missing alert** -- too many false positives, threshold too sensitive, or a condition that should alert but doesn't.
2. **Sysadmin submits a request** -- email to the platform team or a ticket in the tracking system. Include: alert name, current threshold, proposed threshold, and why.
3. **Engineer reviews** -- validates the change won't mask real issues or create gaps.
4. **Change is applied** -- engineer edits the relevant alert rule YAML in `alerts/prometheus/` or `alerts/grafana/`, commits to git, and restarts the stack.
5. **Validation** -- monitor for 1 week to confirm the change has the intended effect.

No threshold change requires downtime. Alert rule reloads are automatic on config change.

---

## Review Cadence

- **Weekly**: Site leads review info alert volume and warning trends. Are any warnings becoming chronic? Should they be escalated or silenced as known issues?
- **Monthly**: Platform team reviews alert volume per severity per site. Identify noisy rules, tune thresholds, update runbooks.
- **Quarterly**: Full alert audit. Are all rules still relevant? Are there gaps in coverage? Compare alert volume trends to SCOM baseline.
