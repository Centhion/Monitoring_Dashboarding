# RBAC and Access Control Guide

## Overview

Grafana's folder-based RBAC controls dashboard visibility per site and team. LDAP/AD integration enables SSO and group-based access, while per-site dashboard isolation ensures operations teams only see dashboards relevant to their site. This is a Phase 8 feature that requires configuration during deployment.

Key design decisions:

- Single Grafana organization with multi-tenancy achieved through folders and teams (not separate orgs).
- LDAP group membership drives automatic team assignment and permission inheritance.
- Dashboard-level isolation only -- Grafana OSS does not support row-level or data-source-level security.

---

## Architecture

### Access Control Model

The access control model consists of four layers:

1. **Grafana Organizations** -- Single org. Multi-tenancy is implemented via folders rather than separate organizations, which simplifies administration and dashboard sharing.
2. **Grafana Folders** -- One folder per dashboard category (Windows, Linux, Infrastructure, Network, Hardware, Certificates). Folders are the permission boundary.
3. **Grafana Teams** -- One team per site (e.g., Team-SiteAlpha, Team-SiteBeta). Teams are granted permissions on folders.
4. **LDAP Groups** -- Active Directory security groups map to Grafana Teams, automating user-to-team assignment on login and periodic sync.

### Why Folder-Based (Not Data-Source Level)

Grafana OSS does not support row-level security or data-source permissions per user. All users query the same Prometheus and Loki backends. Access control operates at the dashboard level: which dashboards a user can see is determined by folder permissions.

Users with direct Explore access can query any data in Prometheus or Loki regardless of folder permissions. For true data isolation, use Grafana Enterprise with its RBAC capabilities, or deploy separate Grafana instances per site.

---

## LDAP/AD Integration

### Prerequisites

- Active Directory domain with user accounts and security groups.
- LDAP service account with read-only bind access to user and group OUs.
- Network access from the Grafana server to the domain controller (LDAPS port 636 recommended).

### Security Group Convention

Create AD security groups following this naming pattern:

```
SG-Monitoring-Admins       -- Grafana Admin role (full access)
SG-Monitoring-SiteAlpha    -- Site Alpha ops team (Viewer/Editor on site dashboards)
SG-Monitoring-SiteBeta     -- Site Beta ops team
SG-Monitoring-NOC          -- NOC/operations center (Viewer on all dashboards)
SG-Monitoring-Readonly     -- Read-only stakeholders (management/reporting)
```

Each site added to the monitoring platform should have a corresponding `SG-Monitoring-<SiteCode>` security group.

### LDAP Configuration

Create `configs/grafana/ldap.toml`:

```toml
[[servers]]
host = "dc01.corp.example.com"
port = 636
use_ssl = true
start_tls = false
ssl_skip_verify = false
# Mount your internal CA cert for LDAPS verification
root_ca_cert = "/etc/grafana/ldap-ca.crt"

bind_dn = "CN=svc-grafana-ldap,OU=Service Accounts,DC=corp,DC=example,DC=com"
bind_password = "${LDAP_BIND_PASSWORD}"

search_filter = "(sAMAccountName=%s)"
search_base_dns = ["OU=Users,DC=corp,DC=example,DC=com"]

[servers.attributes]
name = "displayName"
surname = "sn"
username = "sAMAccountName"
member_of = "memberOf"
email = "mail"

# Map AD groups to Grafana org roles
[[servers.group_mappings]]
group_dn = "CN=SG-Monitoring-Admins,OU=Security Groups,DC=corp,DC=example,DC=com"
org_role = "Admin"

[[servers.group_mappings]]
group_dn = "CN=SG-Monitoring-NOC,OU=Security Groups,DC=corp,DC=example,DC=com"
org_role = "Viewer"

[[servers.group_mappings]]
group_dn = "CN=SG-Monitoring-SiteAlpha,OU=Security Groups,DC=corp,DC=example,DC=com"
org_role = "Editor"
grafana_admin = false

[[servers.group_mappings]]
group_dn = "CN=SG-Monitoring-SiteBeta,OU=Security Groups,DC=corp,DC=example,DC=com"
org_role = "Editor"
grafana_admin = false

# Catch-all: users in AD but no monitoring group get Viewer (or deny)
[[servers.group_mappings]]
group_dn = "*"
org_role = "Viewer"
```

### Grafana Configuration

Add to `configs/grafana/grafana.ini` or set as environment variables:

```ini
[auth.ldap]
enabled = true
config_file = /etc/grafana/ldap.toml
allow_sign_up = true         # Auto-create Grafana user on first login
sync_cron = "0 */15 * * *"   # Sync group membership every 15 minutes
active_sync_enabled = true

[auth]
disable_login_form = false   # Keep local admin login as fallback
```

### Environment Variables (Helm)

```yaml
grafana:
  env:
    GF_AUTH_LDAP_ENABLED: "true"
    GF_AUTH_LDAP_CONFIG_FILE: "/etc/grafana/ldap.toml"
    GF_AUTH_LDAP_ALLOW_SIGN_UP: "true"
```

---

## Folder and Team Provisioning

### Dashboard Folder Structure

```
Infrastructure/          -- Enterprise NOC, Site Overview, SLA, Probing, Audit
  ├── enterprise_noc.json
  ├── site_overview.json
  ├── infrastructure_overview.json
  ├── sla_availability.json
  ├── probing_overview.json
  ├── audit_trail.json
  └── log_explorer.json
Windows Servers/         -- Windows and IIS dashboards
  ├── windows_overview.json
  └── iis_overview.json
Linux Servers/           -- Linux dashboard
  └── linux_overview.json
Network/                 -- Network infrastructure
  └── network_overview.json
Hardware/                -- Hardware health
  └── hardware_overview.json
Certificates/            -- Certificate monitoring
  └── certificate_overview.json
```

### Team Configuration

Teams control which folders (and thus dashboards) members can access:

| Team | Folders | Permission | Members |
|------|---------|------------|---------|
| Admins | All | Admin | SG-Monitoring-Admins |
| NOC | Infrastructure, Network | Viewer | SG-Monitoring-NOC |
| Site-Alpha | All (filtered by datacenter variable) | Editor | SG-Monitoring-SiteAlpha |
| Site-Beta | All (filtered by datacenter variable) | Editor | SG-Monitoring-SiteBeta |
| Readonly | Infrastructure | Viewer | SG-Monitoring-Readonly |

### Folder Permission Assignment

Assign folder permissions via the Grafana API:

```bash
# Grant Team "Site-Alpha" Editor access to the Windows Servers folder
curl -X POST http://grafana:3000/api/folders/<folder-uid>/permissions \
  -H "Content-Type: application/json" \
  -d '{"items": [{"teamId": <team-id>, "permission": 2}]}'
```

Permission levels: `1` = Viewer, `2` = Editor, `4` = Admin.

### Provisioning via Config (Planned)

`configs/grafana/provisioning/teams/` and `configs/grafana/provisioning/dashboards/` support declarative team and folder permission setup. This is a deployment-time configuration task.

---

## Implementation Checklist

### Active Directory Setup (Human Actions)

- [ ] Create `SG-Monitoring-*` security groups in AD
- [ ] Add appropriate users to each group
- [ ] Create LDAP service account (read-only bind)
- [ ] Document LDAP server hostname, port, bind DN, and search bases

### Grafana Configuration

- [ ] Create `ldap.toml` with correct group DNs
- [ ] Mount `ldap.toml` into the Grafana container or pod
- [ ] Mount internal CA certificate for LDAPS verification
- [ ] Set `LDAP_BIND_PASSWORD` as an environment variable or Kubernetes Secret
- [ ] Enable LDAP auth in Grafana config
- [ ] Test login with an AD user account

### Post-Login Setup

- [ ] Create Grafana Teams matching AD group structure
- [ ] Assign folder permissions to teams
- [ ] Verify dashboard visibility per team
- [ ] Test with a user from each group to confirm isolation

---

## User Onboarding and Offboarding

### Onboarding a New User

1. Add the user to the appropriate AD security group (`SG-Monitoring-*`).
2. The user logs into Grafana with their AD credentials.
3. Grafana auto-creates the account and assigns an org role based on the LDAP group mapping.
4. Team membership syncs automatically (within 15 minutes or on next login).
5. The user sees only dashboards in folders their team has access to.

### Offboarding a User

1. Remove the user from the AD security group.
2. On the next LDAP sync (every 15 minutes), Grafana updates permissions.
3. Optionally disable the user in Grafana Admin > Users to prevent any access.
4. The user's saved preferences and starred dashboards are retained and can be deleted manually if needed.

### Adding a New Site

1. Create an AD security group: `SG-Monitoring-<SiteCode>`.
2. Create a Grafana Team: `Team-<SiteCode>`.
3. Map the AD group to the Team in `ldap.toml` (or via the Grafana API).
4. Assign folder permissions to the new Team.
5. Add team members to the AD group.

---

## Security Considerations

### LDAPS vs LDAP

Always use LDAPS (port 636). Standard LDAP (port 389) sends credentials in cleartext over the network. Mount the internal CA certificate for proper TLS verification and never set `ssl_skip_verify = true` in production.

### Service Account Security

- The LDAP bind account should have minimal permissions (read-only access to user and group OUs only).
- Store the bind password in a Kubernetes Secret or HashiCorp Vault, not in plaintext configuration files.
- Rotate the service account password on a regular schedule.

### Local Admin Account

Keep one local admin account as an emergency fallback in case the LDAP server is unavailable. Store the credentials in a password manager, not in documentation or configuration files. Audit local admin usage via the Audit Trail dashboard.

### Data Access Limitations

Folder permissions control dashboard visibility only. Users with Explore access can still query any data in Prometheus or Loki directly using PromQL or LogQL. For strict data isolation, consider deploying separate Grafana instances per site or using Grafana Enterprise with its built-in RBAC data source permissions.

---

## Troubleshooting

### User Cannot Log In

1. Verify the AD account is not locked: `Get-ADUser <username> -Properties LockedOut`
2. Verify the user is in at least one `SG-Monitoring-*` group.
3. Check Grafana server logs: `grep "ldap" /var/log/grafana/grafana.log`
4. Test LDAP connectivity from the Grafana host:
   ```bash
   ldapsearch -H ldaps://dc01:636 -D "CN=svc-grafana-ldap,..." -W -b "OU=Users,..."
   ```
5. Verify the bind DN and password in `ldap.toml`.

### User Sees Wrong Dashboards

1. Check team membership in Grafana Admin > Teams.
2. Verify AD group membership: `Get-ADGroupMember "SG-Monitoring-SiteAlpha"`
3. Force LDAP sync by restarting Grafana or waiting for the `sync_cron` cycle.
4. Check folder permissions in the Grafana UI under the folder's Permissions tab.

### LDAP Sync Not Working

1. Check Grafana logs for LDAP-related errors.
2. Verify network connectivity to the domain controller on port 636.
3. Verify the service account has not expired or been locked out.
4. Test with the `ldapsearch` CLI tool from the Grafana host to isolate whether the issue is Grafana-specific or network/AD-related.

---

## Related Documentation

- [Backend Deployment](BACKEND_DEPLOYMENT.md) -- Grafana deployment configuration
- [Audit Logging](AUDIT_LOGGING.md) -- Tracking user activity and access
- [Alloy Deployment](ALLOY_DEPLOYMENT.md) -- Agent deployment and fleet onboarding
- [Architecture](../ARCHITECTURE.md) -- Overall system design
