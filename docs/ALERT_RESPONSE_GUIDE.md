# Alert Response Guide

A step-by-step guide for sysadmins responding to monitoring alerts. No PromQL or code knowledge required.

---

## When You Receive an Alert

Alerts arrive in two places:

1. **Microsoft Teams** -- a card in the monitoring channel showing the alert name, severity, affected site, and affected host(s)
2. **Email** -- sent to your site's distribution list for critical and warning alerts

Every alert card includes:
- **Severity** (Critical / Warning / Info)
- **Alert name** (e.g., WindowsCpuHighWarning)
- **Datacenter** (which site is affected)
- **Host(s)** (which server(s) triggered the alert)
- **Summary** (one-line description of the problem)
- **Description** (additional context and current value)

---

## Step-by-Step Response

### Step 1: Read the Alert

Note the **severity**, **alert name**, and **hostname**. The severity tells you how urgently to respond:

| Severity | Response Time | What It Means |
|----------|---------------|---------------|
| **Critical** | Within 15 minutes | Something is down or about to fail. Users may be affected. |
| **Warning** | Within 4 hours | Something is degraded. Not urgent, but needs attention today. |
| **Info** | Weekly review | Something changed. No action needed now. |

See `ALERT_SEVERITY_CONTRACT.md` for the full definitions.

### Step 2: Open the Dashboard

1. Open Grafana in your browser
2. Navigate to the appropriate dashboard:
   - **NOC Overview** -- see all sites at a glance. Start here if the alert is site-wide.
   - **Site Overview** -- drill into a specific site. Use the datacenter dropdown to select your site.
   - **Windows Server** or **Linux Server** -- drill into a specific host. Use the hostname dropdown.
   - **Role dashboards** (SQL, IIS, AD/DC, File Server) -- if the alert is role-specific
3. Set the time range to the last 1-6 hours to see the trend leading up to the alert

If the Teams card has an "Open in Grafana" button, click it to go directly to the relevant dashboard.

### Step 3: Look Up the Runbook

1. Open `docs/ALERT_RUNBOOKS.md`
2. Find the alert name (use Ctrl+F to search)
3. Follow the **Investigate** steps to diagnose the root cause
4. Follow the **Remediate** steps to fix the problem

Every alert in the system has a runbook entry. If you find one that doesn't, report it to the platform team.

### Step 4: Take Action

Based on the runbook:
- **Fix the problem** if you can (restart a service, free disk space, replace a cable)
- **Escalate** if you cannot fix it within the expected response time
- **Silence the alert** if the issue is known and being worked on (see "How to Silence Alerts" below)

### Step 5: Verify Resolution

After fixing the problem:
1. Go back to the Grafana dashboard and confirm the metric has returned to normal
2. Wait for the "Resolved" notification in Teams (this confirms the alert condition has cleared)
3. If the alert does not resolve within 15-30 minutes after your fix, investigate further

---

## How to Silence Alerts

Use silences during planned maintenance or when you are actively working on an issue and don't need repeated notifications.

### Quick Silence (Grafana UI)

1. Go to **Alerting** > **Silences** in Grafana
2. Click **New Silence**
3. Add a matcher: `hostname = <the-server-name>`
4. Set the duration (e.g., 2 hours)
5. Add a comment explaining why (e.g., "Patching srv-web-01, ETA 1 hour")
6. Click **Submit**

### Site-Wide Silence (Script)

For patching an entire site:

```bash
python3 scripts/maintenance_window.py create \
    --name "DV patching" \
    --duration 4h
```

See `docs/MAINTENANCE_WINDOWS.md` for full instructions.

### Removing a Silence

Go to **Alerting** > **Silences**, find the active silence, and click **Expire**.

---

## How Alerts Are Grouped

The platform groups alerts by **alert type** and **site**. This means:

- If 10 servers at the same site all have high CPU, you get **1 Teams notification** listing all 10 servers -- not 10 separate notifications
- If 3 different sites each have a server with high CPU, you get **3 notifications** (one per site)
- If a site goes down (multiple servers unreachable), you get **1 outage alert** instead of individual alerts for each server

This grouping is intentional. It prevents the notification flood that caused alert fatigue in the previous monitoring system.

---

## Alert Escalation

If you cannot resolve an alert within the expected response time:

1. Post in the Teams monitoring channel: what the alert is, what you've tried, and where you're stuck
2. Tag the platform engineering team
3. For hardware issues: open a support ticket with the vendor (serial number, error details from BMC)
4. For network issues: escalate to the network team with the affected device/interface details

---

## Common Scenarios

### "I keep getting the same alert every hour"

The alert is repeating because the underlying issue is not resolved. Options:
- Fix the root cause
- If you're actively working on it: create a silence for the expected resolution time
- If the threshold is wrong: request a threshold change (see below)

### "The alert resolved on its own"

Some conditions are transient (CPU spike during backups, memory spike during patching). If the alert fires and resolves within one cycle, it may not need action. Check the dashboard to confirm normal operation. If the alert fires repeatedly and self-resolves, investigate the underlying pattern.

### "I don't understand what this alert means"

Look up the alert name in `docs/ALERT_RUNBOOKS.md`. Every alert has a runbook entry explaining what it means, why it fires, what to check, and how to fix it. If the runbook is unclear, provide feedback to the platform team so it can be improved.

### "Alerts are firing but the server seems fine"

Check if the alert threshold is appropriate for this server's workload. Some servers legitimately run at high resource utilization (SQL servers, build servers, file servers under heavy use). If the threshold is wrong, request a change.

---

## Requesting a Threshold Change

If an alert is too sensitive (fires too often for non-issues) or not sensitive enough (misses real problems):

1. **Note the alert name and current threshold** (visible in the Teams notification or the alert rule)
2. **Propose a new threshold** with justification (e.g., "WindowsMemoryHighWarning fires daily on SQL servers because they legitimately use 90% memory. Propose raising to 93% for SQL role servers.")
3. **Send the request** to the platform engineering team via email or Teams
4. **Engineering reviews** the request to ensure it won't mask real issues
5. **Change is applied** via a config update and pushed to git
6. **Validation** -- the team monitors for 1 week to confirm the change works as intended

No threshold change requires downtime. Changes take effect within minutes of being applied.

---

## Severity Quick Reference

| If you see... | It means... | Do this... |
|---------------|-------------|------------|
| `WindowsServerDown` / `LinuxServerDown` | Server is unreachable | Check if the server is powered on and network-connected |
| `*CpuHighCritical` | CPU is pegged at 95%+ | Find and kill the offending process |
| `*DiskSpaceLowCritical` | Disk is nearly full | Free space immediately (logs, temp files, old backups) |
| `*ServiceDown` / `*CriticalServiceDown` | A critical service stopped | Restart the service, check event logs |
| `SiteMajorOutage` | Most of a site is down | Network or power event. Contact the site team. |
| `TLSCertExpiring7Days` | Certificate expires this week | Install the renewed certificate now |
| `RedfishHealthCritical` | Hardware failure detected | Check BMC, open vendor support ticket |

---

## Where to Find More Information

| Document | What It Contains |
|----------|-----------------|
| `docs/ALERT_RUNBOOKS.md` | Per-alert investigation and remediation steps |
| `docs/ALERT_SEVERITY_CONTRACT.md` | What each severity level means and expected response times |
| `docs/ALERT_CATALOG.md` | Complete inventory of all 100 alert rules with noise risk assessment |
| `docs/MAINTENANCE_WINDOWS.md` | How to silence alerts during maintenance |
| `docs/ALERT_DEDUP.md` | How mass-outage detection and alert suppression works (for engineers) |
