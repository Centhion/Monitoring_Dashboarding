# Platform Administration Guide

How to maintain the monitoring platform: backups, upgrades, capacity planning, and user management.

---

## Backup and Recovery

### What to Back Up

| Item | Location | How to Back Up | Why |
|------|----------|---------------|-----|
| Git repository | This repo | `git push` (already version-controlled) | All configs, dashboards, alert rules, and scripts |
| Grafana database | Docker volume `grafana-data` | `docker cp mon-grafana:/var/lib/grafana/grafana.db ./backup/` | User accounts, API keys, annotations, silences, non-provisioned settings |
| `.env` file | Repository root | Manual copy to secure location | Passwords, webhook URLs, SMTP credentials |

### What NOT to Back Up

- **Prometheus data**: Metrics are transient (30-day retention). Losing them means losing historical charts, not operational capability. Re-collected automatically when agents reconnect.
- **Loki data**: Same as Prometheus. Logs have 30-day retention and are re-collected from agents.
- **Alertmanager data**: Alert state is transient. Active alerts regenerate from Prometheus rule evaluation.

### Backup Script (Recommended)

Create a daily cron job on the Docker host:

```bash
#!/bin/bash
# backup_grafana.sh -- run daily via cron
BACKUP_DIR="/opt/monitoring/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

# Copy Grafana database from container
docker cp mon-grafana:/var/lib/grafana/grafana.db "$BACKUP_DIR/grafana_${TIMESTAMP}.db"

# Keep only the last 7 backups
ls -t "$BACKUP_DIR"/grafana_*.db | tail -n +8 | xargs rm -f 2>/dev/null

echo "Backup complete: $BACKUP_DIR/grafana_${TIMESTAMP}.db"
```

Add to crontab: `0 2 * * * /opt/monitoring/backup_grafana.sh`

### Recovery from Scratch

If the Docker host is lost:

1. Provision a new Docker host with Docker and Docker Compose installed
2. Clone the git repository
3. Copy the `.env` file from your secure backup location
4. Run `python3 scripts/stack_manage.py` to start the stack
5. Restore the Grafana database: `docker cp grafana_backup.db mon-grafana:/var/lib/grafana/grafana.db && docker compose restart grafana`
6. All dashboards, alert rules, and configs are provisioned from the git repo automatically
7. Agents will reconnect and begin pushing data within minutes

**Recovery time**: 15-30 minutes for a full rebuild. Historical metrics and logs are lost (30-day window restarts), but operational monitoring resumes immediately.

---

## Upgrading Components

### Before You Upgrade

1. Back up the Grafana database (see above)
2. Read the release notes for the new version
3. Check for breaking changes (especially Grafana and Prometheus major versions)
4. Plan for 5-10 minutes of downtime per component

### Upgrading a Single Component

Edit `deploy/docker/docker-compose.yml` and change the image tag:

```yaml
# Before
grafana:
  image: grafana/grafana:11.0.0

# After
grafana:
  image: grafana/grafana:11.1.0
```

Then pull and restart:

```bash
docker compose pull grafana
docker compose up -d grafana
```

Verify health after restart:
```bash
python3 scripts/stack_manage.py --status
```

### Upgrading All Components

```bash
# Pull all new images
docker compose pull

# Restart with new versions
docker compose up -d
```

### Component-Specific Notes

**Grafana**: Major version upgrades (e.g., 10.x to 11.x) may require database migration. Grafana runs migrations automatically on startup, but always back up the database first.

**Prometheus**: Check for deprecated config options in the changelog. Prometheus is generally backward-compatible between minor versions.

**Loki**: Schema versions are important. If upgrading across schema versions, read the Loki migration guide. Existing data remains readable, but new data uses the new schema.

**Alertmanager**: Configuration syntax changes are rare. Check the changelog for routing tree changes.

**Alloy**: Agent upgrades are independent of the stack. Deploy new Alloy versions to servers using your existing deployment method (SCCM, Ansible, manual). Agents are backward-compatible with the central stack.

### Rollback

If an upgrade causes issues:

```bash
# Revert the image tag in docker-compose.yml, then:
docker compose pull <component>
docker compose up -d <component>
```

Restore the Grafana database from backup if needed.

---

## Capacity Planning

### Current Resource Usage (Single Docker Host)

Typical resource consumption for a monitoring stack serving 100-500 servers:

| Component | CPU | Memory | Disk |
|-----------|-----|--------|------|
| Prometheus | 1-2 cores | 2-4 GB | 10-30 GB (depends on cardinality and retention) |
| Loki | 0.5-1 core | 1-2 GB | 5-15 GB (depends on log volume) |
| Alertmanager | < 0.1 core | 128 MB | Negligible |
| Grafana | 0.5-1 core | 512 MB - 1 GB | 100 MB (database) |
| **Total** | **2-4 cores** | **4-8 GB** | **15-50 GB** |

### Scaling Projections

| Fleet Size | Prometheus Disk (30d) | Prometheus Memory | Loki Disk (30d) | Recommendation |
|------------|----------------------|-------------------|-----------------|---------------|
| 100 servers | 10-15 GB | 2 GB | 5 GB | Single Docker host, 8 GB RAM, 50 GB disk |
| 500 servers | 30-50 GB | 4 GB | 15 GB | Single Docker host, 16 GB RAM, 100 GB disk |
| 1,000 servers | 60-100 GB | 8 GB | 30 GB | Single Docker host, 32 GB RAM, 200 GB disk |
| 1,500 servers | 90-150 GB | 12 GB | 45 GB | Consider Mimir migration for metrics, 32+ GB RAM, 300 GB disk |

### When to Expand

Monitor these metrics in the Infrastructure Overview dashboard:

| Metric | Warning Threshold | Action |
|--------|-------------------|--------|
| Prometheus disk usage | > 80% of allocated storage | Expand volume or reduce retention |
| Prometheus memory | > 75% of available RAM | Add memory to the host |
| Loki ingestion rate | Sustained > 10 MB/s | Review log volume, add log filtering, or expand Loki resources |
| Query response time | Dashboard panels taking > 5 seconds | Add recording rules for slow queries, or add CPU |

### Reducing Disk Usage

If disk is the bottleneck:

1. **Reduce retention**: Edit `configs/prometheus/prometheus.yml`, change `--storage.tsdb.retention.time` from `30d` to `15d`
2. **Add recording rules**: Pre-aggregate high-cardinality metrics to reduce storage
3. **Filter at the agent**: Drop unnecessary metrics at the Alloy level before they reach Prometheus
4. **Migrate to Mimir**: For long-term storage, Mimir uses object storage (S3/Azure Blob) which is cheaper than local disk

---

## User Management

### Local Accounts (Demo/Small Deployments)

Create users in Grafana UI:

1. Log in as admin
2. Go to **Administration** > **Users**
3. Click **New user**
4. Set username, email, password
5. Assign a role:
   - **Viewer**: Can view dashboards and create silences. Cannot edit dashboards or alert rules.
   - **Editor**: Can edit dashboards (changes are overwritten on restart since dashboards are provisioned from files). Can manage alert silences.
   - **Admin**: Full access including user management, datasource configuration, and system settings.

For most sysadmins, **Viewer** is sufficient. They can view all dashboards, use filters, create silences for maintenance, and access the log explorer.

### LDAP/AD Integration (Production)

LDAP integration maps Active Directory groups to Grafana teams and roles automatically.

**Setup**: See `docs/RBAC_GUIDE.md` for full LDAP configuration instructions.

**Quick summary**:
1. Create AD security groups: `SG-Monitoring-Admins`, `SG-Monitoring-<SiteCode>`, `SG-Monitoring-NOC`
2. Configure `configs/grafana/ldap.toml` with your domain controller, bind account, and group mappings
3. Enable LDAP in Grafana's environment variables
4. Users log in with their AD credentials -- group membership determines their Grafana role and team

### RBAC Folder Permissions

Dashboard visibility can be restricted per team:

1. Run `python3 scripts/configure_rbac.py` to set up teams and folder permissions
2. Each team sees only dashboards in their permitted folders
3. The Enterprise NOC and Infrastructure folders are typically visible to all teams

See `docs/RBAC_GUIDE.md` for the complete permission model.

### API Keys

For automated integrations (CI/CD, scripts, external tools):

1. Go to **Administration** > **Service accounts** in Grafana
2. Create a service account with the appropriate role
3. Generate a token
4. Store the token securely (never commit to git)

The `maintenance_window.py` script uses an API key for creating silences programmatically.
