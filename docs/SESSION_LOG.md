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

## Session: 2026-03-20

### Completed

- **Renamed poc_setup.py to stack_manage.py**: The "PoC" name was misleading for a production-ready tool. Updated all references across README, QUICKSTART, SESSION_LOG, PROJECT_PLAN, deploy_configure.py, site_config.example.yml.

- **Fixed linux_load_normalized recording rule**: Production bug where `node_load1 / count(node_cpu_seconds_total)` failed due to `os` label mismatch. Added `on()` clause to explicitly match on shared labels. Would have broken with real agents too.

- **Built-in snappy compression fallback**: Demo data generator no longer requires `python-snappy` package. Implements minimal snappy block format (literal-only encoding) in pure Python. System Python works out of the box -- no venv or pip install needed.

- **Deploy wrapper UX fixes**:
  - Removed network segment prompt (unused documentation field, confused users)
  - Removed environment from site prompts (environment belongs on agent via ALLOY_ENV, not on the site definition)
  - Fixed prompt() function bug where optional fields with blank default looped as required

- **Comprehensive instance audit**: Ran full review against fresh instance with user's real site data. 54/54 raw metrics present, 52/58 recording rules computing (6 correctly empty for healthy state), all SLA metrics working (126 series, 100% availability), all dashboard panels with data.

- **Documentation updates**: README, QUICKSTART, ARCHITECTURE updated with new dashboard structure (3 folders, 19 dashboards), deployment wrapper workflow, python-snappy dependency, deploy_configure.py and demo_data_generator.py in scripts list.

- **requirements.txt**: Added python-snappy>=0.7 (optional but recommended for better compression performance).

### In Progress

- **User testing deployment workflow**: User is running through the deploy_configure.py -> stack_manage.py -> --demo-data workflow on local machine to practice before work deployment. Stack is running with user's site data.

### Blockers

- None for current work.
- Lansweeper 7D.3-7D.4 still blocked on API credentials.

### Decisions

- **stack_manage.py** (not poc_setup.py): Production-appropriate name since the stack is no longer a PoC.
- **No network segment in prompts**: It was unused documentation. IPs appear automatically from agent metrics and SNMP polling.
- **No environment on sites**: Sites are physical locations. Environment (prod/uat/dev) belongs on the server via ALLOY_ENV. A single site can have both prod and UAT servers.
- **Built-in snappy over pip dependency**: Demo should work with zero pip installs on any machine with Python 3.10+. The fallback produces valid (unoptimized) snappy output.
- **Demo data with real site names**: Use real Alterra site codes in the demo. Data is tagged `environment=demo` so it's clearly synthetic. Less confusing during stakeholder presentations than fake names.
- **Demo data runs indefinitely**: Generator pushes every 30s until killed. No Docker container needed -- just a background process. If it dies, restart with `python3 scripts/stack_manage.py --demo-data`.

### Next Session

1. **User visual review feedback**: User is testing the full workflow. May report layout/readability issues on dashboards that automated audit can't catch.
2. **Work machine deployment**: User plans to deploy at work after practicing locally. Same 4-step workflow with real site codes.
3. **Stakeholder demo preparation**: May need additional polish based on user's review findings.
4. **Lansweeper 7D.3-7D.4**: Asset inventory dashboard and webhook sync (when API credentials available).

### Context

- Stack is running on user's machine at localhost:3000 with demo data flowing
- System Python works -- no venv needed. Snappy fallback handles compression.
- Workflow: `python3 scripts/deploy_configure.py` -> `python3 scripts/stack_manage.py --demo-data`
- To reset: `python3 scripts/stack_manage.py --reset`
- User's org is Alterra Mountain Company (resort/hospitality). Sites are physical resort locations with on-site datacenters.
- macOS requires `python3` not `python`
- 3 commits this continuation: 642ed59, ac640cb, and handoff
- Total across both sessions (3/19-3/20): 8 commits

---

## Session: 2026-03-20 (continued)

### Completed

- **Dashboard operational completeness audit**: Scenario-based review (SQL slow, File Server I/O, AD replication, Network down, Cert expiry, Hardware thermal) -- all 6 pass. Found 24 missing panels across role dashboards.

- **Server Health row on all role dashboards**: Added CPU, Memory, Disk Free, Network, Uptime, Services Down (or Load Average for Linux) gauges/stats to SQL, DC, IIS, DHCP, CA, File Server, Docker dashboards. Moved to top of every dashboard (operator looks at OS health first).

- **SQL dashboard overhaul**: Added Storage row (per-volume disk free, throughput, I/O utilization). Rebuilt layout to fix overlapping panels. 6 SQL stats now fit cleanly in one row at w=4 each.

- **IIS recording rules fix (production bug)**: Added `hostname`, `environment`, `role` to all `by` clauses in `iis_recording_rules.yml`. Without this, IIS dashboard showed "No data" when filtering by individual host because recording rules dropped the hostname label during aggregation.

- **Enterprise NOC PromQL fix (production bug)**: Fixed malformed PromQL in Site Health Grid where filter was placed outside aggregation parentheses: `min by (...) (metric){filter}` -> `min by (...) (metric{filter})`. Same fix in Site Overview.

- **SLA dashboard datacenter filter (production bug)**: Added `{datacenter=~"$datacenter"}` to all 10 SLA queries. Was ignoring site selection and showing all sites regardless.

- **48 threshold assignments**: Every stat/gauge panel now has color coding. Health metrics (CPU, memory, disk) use green/yellow/red. Informational metrics (total counts, rates) use blue. Documented in `docs/THRESHOLD_GUIDE.md`.

- **30 drill-down data links**: Clickable stat panels on hub dashboards (NOC, Infrastructure, Site Overview, Network, Physical Servers, Certificates, SLA, Probing) navigate to detail views.

- **Infrastructure Overview network panel**: Added Fleet Network Throughput (Windows + Linux split) to the fleet trends row.

- **Docker dashboard layout fix**: Fixed Host Memory stat overlapping with Container States timeseries.

- **Demo data improvements**: Role-based disk volumes (SQL 5 drives, FileServer 4, IIS 3). Fixed SNMP error counters to use monotonic counters.

- **User practiced deployment workflow**: User ran through deploy_configure.py -> stack_manage.py --demo-data on local machine with real Alterra site codes (7 sites). Stack running with demo data.

### In Progress

- **Visual review by user**: User is clicking through dashboards finding layout and data issues. Core functionality works but polish continues.

### Blockers

- None for current work. Lansweeper 7D.3-7D.4 still blocked on API credentials.

### Decisions

- **Server Health at top**: First row on every role dashboard. Operators check OS health before role-specific metrics.
- **Disk volumes are dynamic**: Dashboards query all volumes/disks that exist. Demo data uses role-based counts (SQL=5) but production agents auto-discover. Nothing hardcoded.
- **Thresholds documented separately**: `docs/THRESHOLD_GUIDE.md` is the single reference for all threshold values. Team reviews and adjusts before production. Changes go in dashboard JSON `thresholds.steps`.
- **Drill-downs from hub dashboards only**: Stat panels on NOC/Infrastructure/Site Overview are clickable. Role-specific dashboards (SQL, DC, etc.) are endpoints -- their stats don't drill down further.
- **No environment on site definitions**: Sites are physical locations. Environment (prod/uat) is set per-agent via ALLOY_ENV.
- **IIS recording rules must preserve hostname**: All `sum by` clauses include `hostname, environment, role` so per-host filtering works on dashboards.

### Next Session

1. **Continue visual dashboard review**: User may find more layout/readability issues
2. **Work machine deployment**: Same workflow with real site codes at work
3. **Stakeholder demo**: Stack is demo-ready with 7 Alterra sites
4. **Lansweeper 7D.3-7D.4**: When API credentials available

### Context

- Stack running on user's machine with 7 Alterra sites: dv, ent, sbt, sno, sol, schw, mm
- Demo data generator runs as background process, pushes every 30s
- Workflow: `python3 scripts/deploy_configure.py` -> `python3 scripts/stack_manage.py --demo-data`
- Data generator has built-in snappy fallback -- works with system Python, no pip install needed
- macOS requires `python3` not `python`
- IIS recording rules now preserve hostname -- this was a production bug that would also affect real agents
- 4 commits this continuation: 642ed59, ac640cb, f563ee3, 1a9d0cc
- Total across all sessions (3/19-3/20): 12 commits

---

## Session: 2026-03-20 (final)

### Completed

- **Phase 12 tasks 1-19 complete**: All original 17 tasks plus 2 additional (detail tables, comprehensive click audit)
- **Dashboard rebuilds**: CA (per-template), DC (replication/LDAP/SAM), DHCP (per-scope utilization)
- **Demo data expanded**: DC 16 new metrics, DHCP 24 per-scope metrics, CA 25 per-template metrics, SLA downtime simulation, audit trail Loki logs
- **Click-to-filter**: All actionable stat/gauge panels have click links, 7 dashboards got Stopped Services and Disk Space detail tables
- **Color fixes**: NOC High CPU, SLA red names, cert expiry standardized, probing thresholds
- **Comprehensive audit**: 36 remaining click links identified that need detail panel wiring (Phase 12B)

### In Progress

- **Phase 12B**: 16 click-to-filter detail wiring tasks planned (8 Category A = simple URL fixes, 8 Category B = new detail panels needed)

### Decisions

- **Click-to-filter pattern**: Every clickable stat must navigate to a visible, relevant detail panel showing filtered specifics. Not just reload the same dashboard.
- **Category A vs B**: Stats where a detail panel already exists on the dashboard just need correct anchor URLs. Stats without a matching detail panel need new collapsed-row tables added.
- **Docker per-container**: Requires cAdvisor (separate dependency). Dashboard stays daemon-level for now. Don't promise per-container drill-down in demo.
- **DHCP scopes**: Per-scope metrics available from Windows exporter. 4 demo scopes: Servers, Workstations, Printers, VoIP.
- **CA per-template**: 5 templates in demo: Machine, WebServer, User, DomainController, SubCA. No CRL metrics from Windows exporter.

### Next Session

1. **Phase 12B Category A** (tasks 20-27): Fix 8 click links to anchor to existing detail panels -- quick wins
2. **Phase 12B Category B** (tasks 28-35): Add 8 new detail panels for stats that lack them
3. **Visual review**: User continues clicking through dashboards
4. **Demo prep**: Finalize for stakeholder presentation

### Context

- Stack running with 7 Alterra sites, demo data generator in background
- 36 click links identified as incomplete -- planned in PROJECT_PLAN.md Phase 12B
- DHCP now has per-scope metrics (addresses_in_use, addresses_free, scope_state)
- CA now has per-template metrics (windows_adcs_requests_total by cert_template)
- DC now has replication bytes, LDAP sessions, SAM password changes, tombstone tracking
- Demo data simulates ~2% downtime on generic hosts for SLA dashboards
- Audit trail logs being pushed to Loki (login, dashboard views, failed logins)

---

## Session: 2026-03-20 (session 3)

### Completed

- **Phase 12B complete**: All 16 click-to-filter detail wiring tasks (20-35) done
- **Category A** (8 tasks): Fixed click links to anchor to existing detail panels (Certificate Inventory, Interface Status Table, Server Health Inventory, Top 10 tables, log streams, SMB panels, probe grid, SLA tables)
- **Category B** (8 tasks): Added new detail panels where missing (SQL Lock Wait + User Connections, Windows Stopped Services, Audit Trail Failed Login log filter, DC/Docker/IIS/File Server anchors)
- **Collapsed row fix**: Uncollapsed all detail rows -- Grafana viewPanel parameter doesn't work with panels inside collapsed rows
- **Panel ID assignment**: Assigned IDs to all panels across 9 dashboards that had missing IDs (stripped during earlier layout rebuilds)
- **47 click links verified**: Final audit shows 0 incomplete click-to-filter links

### Blockers

- None. Phase 12 fully complete.

### Decisions

- **No collapsed rows for detail panels**: viewPanel only works with top-level panels. Detail tables are regular (uncollapsed) rows at the bottom of each dashboard.
- **viewPanel for drill-down**: Clicking a stat opens the target panel in Grafana's focused panel view. This is the standard Grafana approach for same-dashboard drill-downs.

### Next Session

1. User continues visual dashboard review
2. Demo prep for stakeholder presentation
3. Lansweeper 7D.3-7D.4 when API credentials available

### Context

- Stack running with 7 Alterra sites, demo data flowing
- All 19 dashboards have complete click-to-filter coverage
- "out of order sample" warnings in demo data generator are harmless (clock sync)
- 5 commits this session: 1d107c1, abe6910, 87fa483, e880bd3, af13719

---
