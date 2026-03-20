# Lansweeper Integration Guide

> **Status: In Progress** -- The API client and field mapping are implemented (Phase 7D.1-7D.2). Asset inventory dashboard (7D.3) and webhook-driven sync (7D.4) are not yet complete. Requires a Lansweeper Cloud PAT and site ID for live testing.

This guide covers the Lansweeper-to-monitoring-stack integration, which synchronizes asset inventory data from Lansweeper Cloud into the monitoring platform's host inventory and exposes asset metadata as Prometheus metrics.

## Overview

The integration bridges two systems with distinct responsibilities:

- **Lansweeper**: Asset discovery, hardware inventory, software inventory, warranty tracking
- **Monitoring Stack**: Infrastructure health monitoring (metrics, logs, alerts, dashboards)

The integration pulls asset data from Lansweeper into the monitoring stack, enabling automated inventory management, hardware enrichment in dashboards, and warranty expiry alerting.

## Prerequisites

- Lansweeper Cloud or Hybrid deployment (on-prem sites synced to cloud)
- A Lansweeper API client with a Personal Access Token (PAT)
- Python 3.10+ with PyYAML installed

**On-prem only deployments**: The Lansweeper GraphQL API is only available through the cloud platform. On-prem installations must enable cloud sync (hybrid mode) to use this integration. Direct SQL queries against the on-prem database are not supported by this tooling.

## Setup

### 1. Create a Lansweeper API Client

1. Log into Lansweeper Cloud at `app.lansweeper.com`
2. Navigate to **Site Settings** > **Developer Tools**
3. Click **Add new API client**
4. Select **Personal Access Token**
5. Name the client (e.g., `monitoring-stack-sync`)
6. Click **Refresh token** to generate the PAT
7. Copy the token immediately -- it is not stored by Lansweeper

### 2. Find Your Site ID

Run the `list-sites` command to discover your site ID:

```bash
export LANSWEEPER_PAT="your-token-here"
python3 scripts/lansweeper_sync.py list-sites
```

Output:

```
Authorized Sites (1):
------------------------------------------------------------
  ID:   xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  Name: My Organization
```

### 3. Configure Environment Variables

Add the following to your `.env` file (see `.env.example` for the template):

```bash
LANSWEEPER_API_URL=https://api.lansweeper.com/api/v2/graphql
LANSWEEPER_SITE_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
LANSWEEPER_PAT=your-personal-access-token-here
```

### 4. Configure Field Mapping

Edit `inventory/lansweeper_field_map.yml` to map Lansweeper asset attributes to monitoring roles and sites. This file controls:

- **Asset type filtering**: Which Lansweeper asset types to sync (default: Windows, Linux)
- **Role mapping**: Rules that assign monitoring roles based on hostname patterns, asset type, or description
- **Site mapping**: Rules that assign monitoring sites based on location, IP range, FQDN suffix, or network regex
- **OS mapping**: Translation from Lansweeper asset types to monitoring OS values

**Role rules** are evaluated in order; the first match wins. Assets that match no rules are assigned `default_role` (default: `generic`).

**Site rules** work the same way. Assets that match no rules are assigned `default_site` (default: `unknown`). You must configure site rules for your environment -- they are commented out by default because they are organization-specific.

#### Example: Mapping by IP Range

```yaml
site_rules:
  - site: site-alpha
    match:
      ip_prefix: "10.0."
    description: "East coast datacenter"

  - site: site-beta
    match:
      ip_prefix: "10.1."
    description: "West coast datacenter"
```

#### Example: Mapping by Lansweeper Location Field

```yaml
site_rules:
  - site: site-alpha
    match:
      location: "Building A"
    description: "Matched by Lansweeper location field"
```

#### Example: Mapping by FQDN Suffix

```yaml
site_rules:
  - site: site-alpha
    match:
      fqdn_suffix: ".east.corp.example.com"
    description: "Matched by DNS domain"
```

## Usage

### Dry Run (Preview Changes)

Always run a dry run first to verify the mapping:

```bash
python3 scripts/lansweeper_sync.py sync --dry-run
```

Output shows what would change without writing to `hosts.yml`:

```
=== DRY RUN === (no changes will be written)
Syncing from Lansweeper site: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

  Querying Lansweeper assets (page 1)...
  Total assets: 150 | Fetched: 150

Received 150 assets from Lansweeper
Mapped 142 assets to host entries (8 skipped)

============================================================
  Sync Summary
============================================================

  NEW (42):
    + srv-web-01  [windows] [iis] [site-alpha]
    + srv-sql-01  [windows] [sql] [site-alpha]
    ...

  UPDATED (98):
    ~ srv-dc-01
    ~ srv-dc-02
    ...

  SKIPPED (manually managed) (2):
    - custom-monitor-01

  DRY RUN: 140 change(s) would be applied.
  Run without --dry-run to apply.
```

### Apply Sync

```bash
python3 scripts/lansweeper_sync.py sync
```

After syncing, validate the inventory:

```bash
python3 scripts/fleet_inventory.py validate
```

### List Authorized Sites

```bash
python3 scripts/lansweeper_sync.py list-sites
```

## Merge Strategy

The sync uses a conservative merge strategy to prevent data loss:

| Scenario | Behavior |
|----------|----------|
| New host from Lansweeper | Added to `hosts.yml` with `source: lansweeper` tag |
| Existing host with `source: lansweeper` | Updated with fresh Lansweeper data |
| Existing host without `source` tag (manually added) | Never overwritten -- skipped with a warning |
| Host in `hosts.yml` with `source: lansweeper` but missing from Lansweeper | Flagged as "stale" in output (not removed) |

The `source: lansweeper` tag is the key differentiator. Manually added hosts will never be touched by the sync process. If you want a manually added host to be managed by the sync, add `source: lansweeper` to its entry.

## Rate Limiting

The Lansweeper API uses an aggressive rate limiter with a lockout-style cooldown:

1. When the rate limit is hit, all requests are blocked for **one full minute**
2. Any request made during that cooldown **resets the timer** back to one minute
3. The sync script handles this automatically with exponential backoff (65-second base wait)
4. Maximum 3 retries before failing

For typical deployments (under 5,000 assets), a full sync completes in a single paginated pass without hitting rate limits.

## Scheduling

For automated inventory sync, add a cron job or scheduled task:

```bash
# Sync every 6 hours (sufficient for asset metadata which changes slowly)
0 */6 * * * cd /path/to/repo && source .env && python3 scripts/lansweeper_sync.py sync >> /var/log/lansweeper-sync.log 2>&1
```

## Troubleshooting

### "No data returned for site"

Verify your site ID with `list-sites`. The PAT must have access to the specified site.

### "Missing required environment variables"

Ensure `LANSWEEPER_SITE_ID` and `LANSWEEPER_PAT` are exported in your shell or loaded from `.env`.

### "HTTP 401/403"

The PAT may be expired or revoked. Generate a new token in Lansweeper Developer Tools.

### Rate limit errors persisting

If you see repeated rate limit messages, another process or user may be querying the same API simultaneously. The cooldown timer resets on any request from any client using the same credentials. Coordinate sync schedules if multiple integrations share the same PAT.

### Assets synced but validation fails

Check `inventory/lansweeper_field_map.yml`:
- Ensure `site_rules` map to valid site codes defined in `inventory/sites.yml`
- Ensure `os_map` values match `valid_os` in `sites.yml`
- Ensure `default_role` and role rule outputs match `valid_roles` in `sites.yml`
