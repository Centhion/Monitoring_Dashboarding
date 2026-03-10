# Branching Strategy

This repository serves as both a **public open-source template** and the basis for an **internal production deployment**. This document defines the boundary between the two.

---

## Branch Model

```
master (public template)
  |
  +-- All new feature development happens here
  |   Generic placeholders, sanitized content
  |
  +-- internal (org-specific deployment fork)
      |
      +-- Merges FROM master to pick up new features
      +-- Overrides placeholders with real values
      +-- Contains real inventory, credentials config, site-specific overrides
```

### master (default)

The public-facing open-source template. Published to GitHub as a portfolio project and community resource.

**Contains:**
- All Alloy agent configs with `sys.env()` placeholders
- All Grafana dashboards with template variables (no hardcoded sites)
- All Prometheus alert rules and recording rules with sensible default thresholds
- Helm chart with generic `storageClass: ""` and commented examples
- Docker Compose PoC environment
- Validation scripts, test suite, CI tooling
- Documentation (architecture, deployment guide, runbooks, project plan)
- Session logs and requirements response (sanitized)

**Does NOT contain:**
- Real company names, employee names, team member names
- Real hostnames, IP addresses, or internal domain names
- Real LDAP bind DNs, search bases, or AD group names
- Real webhook URLs, SMTP relay addresses, or API keys
- Real site codes that could identify the organization
- Vendor contract details or licensing specifics

**Placeholder conventions:**
| Pattern | Meaning |
|---------|---------|
| `<YOUR_ORG>` | Organization name |
| `site-a`, `site-b`, `site-alpha` | Datacenter/site names |
| `dc-east`, `dc-west`, `cloud-us` | Generic datacenter codes |
| `example.com`, `corp.example.com` | Domain names |
| `ldap.example.com` | LDAP server |
| `smtp.example.com` | SMTP relay |
| `YOUR_WEBHOOK_URL_HERE` | Teams/Slack webhook |
| `changeme` | Default passwords |

### internal (deployment fork)

Created when ready to deploy to production. Branches from master and adds org-specific configuration.

**Contains (in addition to master):**
- Real site inventory (`inventory/hosts.yml`, `inventory/sites.yml`)
- Real LDAP configuration (`configs/grafana/ldap.toml` with actual bind DN)
- Real Alertmanager receivers (actual email addresses, webhook URLs)
- Real Helm values overlay (`deploy/helm/examples/values-production-myorg.yaml`)
- Real `.env` file (gitignored, but deployment docs reference actual values)
- Any org-specific Alloy role configs not suitable for the public template

**Workflow:**
```bash
# Pick up new features from master
git checkout internal
git merge master

# Resolve any placeholder conflicts (master resets, internal keeps real values)
# Push internal
git push origin internal
```

---

## Sanitization Checklist

Before merging to master or committing on master, run:

```bash
# Check for org-specific terms (add your own terms to the pattern)
grep -ri "TERM1\|TERM2\|TERM3" \
  --include="*.md" --include="*.yml" --include="*.yaml" \
  --include="*.json" --include="*.alloy" --include="*.py" \
  --include="*.toml" --include="*.tmpl"
```

Known safe terms that look org-specific but are not:
- `PSU` in hardware alerts = Power Supply Unit (hardware component)
- `LogicMonitor`, `Datadog` in REQUIREMENTS_RESPONSE.md = generic vendor comparison (no contract details)
- `Nutanix NKP` in architecture docs = platform choice (public knowledge)

---

## For AI Agents

If you are a Claude Code agent, Cursor, Windsurf, or similar:

1. **Check which branch you are on** before making changes: `git branch --show-current`
2. **All new feature work goes on `master`** with generic placeholders
3. **Never put real org data on `master`** -- if you are unsure, ask the user
4. **The `internal` branch does not exist yet** -- it will be created when production deployment begins
5. See `.claude/CLAUDE.md` "Branch Model" section for the full rules

---

*Document Version: 1.0*
*Created: 2026-03-09*
