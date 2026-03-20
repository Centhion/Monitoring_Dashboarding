# Session Log

Chronological record of work sessions for context continuity.

---

## Session: 2026-03-16

### Completed

- **Phase 7D reinstated**: Lansweeper Integration moved from "Dropped" to "In Progress" with full 4-phase rolling implementation plan added to PROJECT_PLAN.md
- **7D.1 Tasks 1-5, 7 complete**: Core API client and inventory sync
  - `.env.example` updated with Lansweeper config vars (API URL, site ID, PAT, webhook secret)
  - `scripts/lansweeper_sync.py` created -- GraphQL client with PAT auth, cursor-based pagination, rate-limit backoff (65s cooldown), `sync` subcommand with `--dry-run`, `list-sites` subcommand
  - `inventory/lansweeper_field_map.yml` created -- configurable asset type filtering, role mapping (name regex, asset type, description), site mapping (location, IP prefix, FQDN suffix, network regex), OS mapping
  - Merge strategy: new hosts added, `source: lansweeper` hosts updated, manual hosts never overwritten, stale hosts flagged
  - `docs/LANSWEEPER_INTEGRATION.md` created -- full setup, auth, usage, merge strategy, rate limiting, scheduling, troubleshooting
- **7D.2 Tasks 1-5 complete**: Asset enrichment metrics
  - `export-metrics` subcommand added to `lansweeper_sync.py` -- generates Prometheus textfile collector output
  - Three metric families: `lansweeper_asset_info` (info gauge with hardware/OS/location labels), `lansweeper_warranty_expiry_timestamp_seconds`, `lansweeper_last_seen_timestamp_seconds`
  - `configs/alloy/roles/role_lansweeper_metrics.alloy` -- textfile collector config with disabled default collectors, 15m scrape interval
  - `configs/prometheus/lansweeper_recording_rules.yml` -- 7 recording rules (warranty days remaining, days since seen, fleet counts by type/manufacturer, warranty expiring/expired counts, stale asset count)
  - `alerts/prometheus/lansweeper_alerts.yml` -- 5 alert rules (warranty 90d/60d/30d/expired escalation, asset not seen 7d)
  - Prometheus config updated to load new rule files
  - `.gitignore` updated to exclude `metrics/lansweeper/` runtime artifacts
- **ARCHITECTURE.md** updated with new files (lansweeper_sync.py, lansweeper_field_map.yml, LANSWEEPER_INTEGRATION.md)
- **Memory file created** at `.claude/projects/.../memory/MEMORY.md` documenting that this repo is the private/internal project (not the public `monitoring-stack` repo)

### In Progress

- **7D.1 Task 6**: Integration test with live API -- cannot test without real Lansweeper PAT and site ID (human action required)
- **7D.2 Task 6**: Validate metrics flow end-to-end in Docker Compose PoC -- not yet attempted
- **7D.3**: Asset Inventory Dashboard -- not yet started
- **7D.4**: Webhook-driven real-time sync -- not yet started
- **Proposal document**: User wants to write an internal proposal justifying adoption of this stack over commercial alternatives. Research completed (Dynatrace, Datadog, New Relic, Splunk, Elastic, Zabbix, PRTG, Grafana Cloud compared), document not yet written

### Blockers

- **Lansweeper API credentials**: Need PAT and site ID from Lansweeper cloud console to test 7D.1 Task 6 live
- **Organizational buy-in**: User expressed frustration that the org is "still seeking" commercial replacements despite this enterprise-grade solution being built. The $26K annual SquaredUp budget is the only available spend, which eliminates all commercial SaaS options at 1,500+ hosts

### Decisions

- **Two-folder project structure** (not branch-based): `monitoring-stack` = public template, `Monitoring_Dashboarding-master` = private/internal org-specific. Not using the branching strategy described in CLAUDE.md
- **Lansweeper Cloud GraphQL API**: Selected over SQL direct access (requires cloud/hybrid, which user confirmed). PAT auth over OAuth (simpler for internal use)
- **Prometheus textfile collector pattern** for asset enrichment: Consistent with existing project patterns (Phase 9B file/process monitoring uses same approach). Cron-based schedule acceptable since asset metadata changes slowly
- **Conservative merge strategy**: Manual hosts never overwritten, `source: lansweeper` tag tracks which entries are API-managed
- **Timestamp-based metrics over days-remaining**: Store warranty expiry and last-seen as Unix timestamps, compute days-remaining in recording rules. More flexible for PromQL

### Next Session

1. **Write the internal proposal document** -- user's immediate priority. Structure: problem statement (SCOM+SquaredUp limitations), solution overview, feature comparison matrix, TCO analysis at 1,500+ hosts ($0 vs $550K+ Dynatrace / $700K+ Datadog), risk analysis, implementation status (91% requirements coverage, already built)
2. **7D.3: Asset Inventory Dashboard** -- create `dashboards/overview/asset_inventory.json` with warranty tracker, stale assets, unmanaged assets panels
3. **7D.2 Task 6**: Validate metrics flow in Docker Compose PoC (may require the dashboard work first for visual validation)
4. **7D.4: Webhook receiver** -- last phase of Lansweeper integration

### Context

- Fleet is 1,500+ VMs (Windows/Linux), network hardware (SNMP), physical HCI hosts (Nutanix with Redfish/BMC). Much larger than initially estimated in commercial comparisons
- SquaredUp annual cost is $26K -- this is the only budget available. No commercial SaaS monitoring platform covers 1,500 hosts at this price point
- User is the primary builder of this platform and is losing motivation due to organizational resistance to adopting what's already built
- The proposal document may be the most impactful deliverable right now -- more so than finishing 7D.3/7D.4
- Lansweeper rate limiter is aggressive: 1-minute lockout that resets on ANY request during cooldown. The sync script uses 65-second base backoff to handle this
- Requirements traceability matrix shows 91% coverage (70/77 requirements). Only gaps: Grafana Enterprise audit diffs (2 items) and some pending items that are actually completed (RBAC Phase 8, Fleet Phase 5.7 show as pending in the matrix but are marked complete in PROJECT_PLAN.md -- matrix needs updating)

---

## Session: 2026-03-19

### Completed

- **Documentation cleanup**: Merged 3 docs (FLEET_ONBOARDING into ALLOY_DEPLOYMENT, LOCAL_TESTING into QUICKSTART, slimmed AGENTLESS_MONITORING to index). Fixed stale REQUIREMENTS_TRACEABILITY entries (91% -> 96% coverage). Added status banners to LANSWEEPER_INTEGRATION and CLOUD_MONITORING.

- **Phase 10A: Deployment Wrapper** (`scripts/deploy_configure.py`): Interactive config generator that collects all deployment parameters and generates .env, inventory/sites.yml, inventory/hosts.yml, alertmanager.yml, notifiers.yml. Supports --config for file-based re-runs, --dry-run, role conflict detection (DC+DHCP).

- **Phase 10B: Demo Data Generator** (`scripts/demo_data_generator.py`): Pushes 2,800+ synthetic metrics per tick across 46+ metric names covering all dashboard categories. Continuous background mode for live demos. Snappy compression for Prometheus remote_write.

- **Phase 10C: Integration**: stack_manage.py --demo-data flag. site_config.example.yml with ENT/DV sites.

- **Phase 11: Dashboard Production Readiness** (all 19 tasks complete):
  - Restructured 19 dashboards into 3 folders: Enterprise (4), Servers (10), Infrastructure (5)
  - Removed all phase-* tags, replaced with functional taxonomy
  - Created 6 new role dashboards: SQL, DC, DHCP, CA, File Server, Docker
  - Created Alloy role configs: role_dhcp.alloy, role_ca.alloy
  - Fixed drill-down links, template variables, stat panel aggregation

- **82 dashboard bugs resolved**: prometheusVersion semver fix, recording rule reference fixes (site:* -> fleet:*, instance:iis_* -> iis:site_*), cert probe job label, SNMP column renames, ifDescr -> ifName legends, empty placeholder removal, FSRM quota table rebuild, systemd table organize, SNMP error counter fix (gauge -> monotonic counter), Grafana 11.x link/variable schema compliance.

- **Deep operational audit**: All recording rules healthy, data consistency verified, metric values realistic, all drill-down links resolve, no orphaned metrics.

### In Progress

- **Visual dashboard review**: Automated audit clean but visual quality (layout, sizing, readability) needs human review. User began reviewing.
- **SNMP error interface count**: Stabilizing with monotonic counter fix. Needs 5+ min to flush rate() window.

### Blockers

- None for Phase 10/11. Lansweeper 7D.3-7D.4 still blocked on API credentials.

### Decisions

- **Folder structure**: Enterprise / Servers / Infrastructure (not per-site). Industry standard.
- **Physical Servers** (not "Hardware"): Clearest name for BMC/Redfish monitoring.
- **DHCP co-location**: Dedicated servers use role_dhcp.alloy; DCs use role_dc.alloy (includes DHCP). Conflict detection in deploy_configure.py.
- **Demo data uses environment=demo**: Distinguishes from production.
- **Always use /commit skill**: Never raw git add/commit. Saved to memory.
- **Prometheus v2.53.4 no out-of-order ingestion**: Backfill uses rapid ticks at current time.

### Next Session

1. Visual dashboard review: NOC -> Site Overview -> each role dashboard flow
2. Enterprise NOC site health grid verification
3. Demo presentation prep (may need real Alterra site codes)
4. Lansweeper 7D.3-7D.4 (asset inventory dashboard, webhook sync)

### Context

- Stack running at localhost:3000 with demo data generator in background
- Demo venv at /tmp/demo-venv (pyyaml + python-snappy). Restart generator: `nohup /tmp/demo-venv/bin/python3 scripts/demo_data_generator.py --config deploy/site_config.yml --backfill 0 &`
- Grafana 11.5.2 quirks: prometheusVersion must be exact semver, variable queries as dict with refId, links need asDropdown/keepTime/tags
- 5 commits this session: d2a10c9, 5756cd0, 3aaaf8d, df0e6af, 634e95a
- This is the private/internal repo. Public template at /Users/et/Development/monitoring-stack

---
