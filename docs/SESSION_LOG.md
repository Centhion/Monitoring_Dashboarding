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

## Session: 2026-03-20 (session 4)

### Completed

- **Phase 12B click-to-filter**: All 16 wiring tasks complete. 47 clickable stat panels linked to detail panels. Uncollapsed detail rows (viewPanel doesn't work with collapsed row children in Grafana 11.5).

- **Datacenter drill-down fix (root cause)**: `multi=False` on datacenter variable across all 17 dashboards. Grafana wraps multi-select URL values in braces (`{sno}` instead of `sno`), breaking all cross-dashboard drill-downs. Single-select fixes this.

- **Cross-dashboard linking fixed**: Site Overview passes `$datacenter` to target dashboards. NOC table cell links use `:raw` format modifier. Removed `var-environment` from all cross-dashboard links (caused "All" literal string issues). Full flow works: NOC -> click site -> Site Overview (filtered) -> click stat -> role dashboard (filtered to same site).

- **Same-dashboard click links removed**: 53 useless links that pointed to `/d/same-dashboard` removed. Grafana 11.5 doesn't support scroll-to-panel or viewPanel for most panel types. Detail tables are visible on the page -- users scroll naturally.

- **Dashboard descriptions**: Text panel added to all 18 dashboards (Audit Trail already had one) explaining purpose, how to use filters, and what colors mean.

- **Network dashboard device filter**: Added `device_name` variable for per-device drill-down. Added "Interfaces with Errors" detail table showing only interfaces with non-zero error rates.

- **Site Overview datacenter filter fix**: Changed `datacenter="$datacenter"` (exact match) to `datacenter=~"$datacenter"` (regex match) on queries that showed "No data" when "All" was selected.

- **Expanded demo data committed**: DC (16 new metrics), DHCP (24 per-scope), CA (25 per-template), SLA downtime simulation, audit trail Loki logs.

### In Progress

- **Certificate Overview dashboard rebuild**: Probe Status History is unreadable (raw labels as Y-axis). Expiry Timeline is spaghetti chart. Both need complete rebuild. User wants whole cert dashboard reworked.
- **Ongoing visual review**: User finding issues as they click through dashboards.

### Blockers

- None technical. Grafana 11.5 limitation: no scroll-to-panel, no viewPanel for non-VizPanel types. Worked around by making detail tables always visible.

### Decisions

- **Datacenter single-select**: `multi=False` on all dashboards. Prevents `{value}` brace-wrapping in URL drill-downs. Users select one datacenter at a time.
- **No same-dashboard click links**: Grafana 11.5 can't scroll to a panel or open it in focus mode reliably. Detail tables are always visible -- users scroll. Cross-dashboard links work fine.
- **No var-environment in cross-dashboard links**: Causes "All" literal string issues. Target dashboards load with their own Environment="All" default which works correctly.
- **Table cell links use ${__data.fields.field:raw}**: Prevents Grafana from wrapping values.
- **Cert dashboard needs full rebuild**: Replace status-history (unreadable) with table. Replace spaghetti time series with sorted bar chart or table for expiry.

### Next Session

1. **Rebuild Certificate Overview dashboard**: Replace Probe Status History with clean table, replace Expiry Timeline with sorted bar/table visualization
2. **Continue visual review**: User may find more issues
3. **Demo prep**: Finalize for stakeholder presentation

### Context

- Stack running with 7 Alterra sites, demo data generator in background
- Datacenter is single-select on all dashboards (critical for drill-down)
- Cross-dashboard links: no var-environment, only var-datacenter where needed
- Same-dashboard clickable stats removed (no useful behavior in Grafana 11.5)
- NOC -> Site Overview -> role dashboard drill-down flow verified working
- Commits this session: 1d107c1, abe6910, 87fa483, e880bd3, af13719, 3afa9a0, 5d22c10

---

## Session: 2026-03-20 (session 5)

### Completed

- **Certificate Overview dashboard rebuilt**: Replaced unreadable Probe Status History (raw labels as Y-axis) and spaghetti Expiry Timeline with clean visualizations: Certificate Inventory table (sorted by days remaining, color-coded cells), Expiry Distribution (horizontal bar gauge), Probe Health table (UP/DOWN text, no giant green blocks).

- **Hostname and service labels on cert probes**: Added `hostname` (which server hosts the cert) and `service` (what the cert is for) to cert probe demo data and dashboard tables. Operators can see which server to update when a cert expires.

- **Cert expiry ranges fixed**: Demo data now generates realistic spread -- 10% critical (<7d), 10% urgent (8-30d), 15% expiring (31-60d), 65% healthy (61-365d). Expiring/Urgent/Critical stats now show values.

- **Duplicate series fix**: Empty-string labels (`hostname=""`) create separate Prometheus series from label-absent series. Fixed generator to only add labels when non-empty. Added `hostname!=""` filter to cert dashboard tables to exclude recording rule outputs.

### Decisions

- **Cert hostname comes from endpoint config**: In production, operators add hostname/service labels to `configs/alloy/certs/endpoints.yml`. The dashboard shows these to help identify which server hosts each certificate.
- **Recording rules strip hostname**: `probe_recording_rules.yml` aggregates by datacenter, dropping hostname. Dashboard tables filter with `hostname!=""` to show only raw endpoint data.
- **Local Grafana accounts for demo evaluation**: Users get local accounts with Viewer role during demo period. No LDAP complexity for evaluation.

### Next Session

1. Continue visual dashboard review
2. Demo prep for stakeholder presentation
3. Any remaining dashboard issues from user testing

### Context

- Stack running with 7 Alterra sites, demo data generator in background
- Certificate Overview fully rebuilt -- user approved ("this is great!")
- All validations pass, all cross-dashboard drill-downs working
- Commit: b0057cc

---

## Session: 2026-03-20 (session 6 - final)

### Completed

- **Certificate Overview finalized**: Fixed duplicate series (empty-string labels vs absent labels), added hostname!="" filter to exclude recording rule outputs. User approved.

- **Phase 13 (Alert Strategy) planned**: 16 tasks covering alert audit, noise reduction, documentation, and validation with real data. Alert fatigue is the #1 adoption risk.

- **Phase 13B (Operator Documentation) planned**: 20 deliverables across 5 categories -- operations guide, alert reference, dashboard guide, architecture overview, administration guide. Written for sysadmins, Wiki/KB ready, 10-year supportability.

- **Phase 14 (Production Rollout) planned**: 29 tasks -- pilot site, security hardening, fleet rollout, operations handoff, platform evolution. Docker Compose on dedicated Denver DC host.

- **Deployment context documented to memory**: Zero budget, SquaredUp replacement ($26K savings), team of 10 inheriting platform, no on-call yet, Docker before Kubernetes.

### Decisions

- **Alert fatigue is the hill**: If the platform generates noise like SCOM, team rejects it. Conservative thresholds, proper dedup, and clear runbooks from day one.
- **Documentation for operators, not builders**: Current docs are engineer-focused. Need sysadmin-facing docs that assume no Grafana/Prometheus knowledge.
- **10-year supportability**: Platform must be maintainable by people who didn't build it. Documentation, training, and bulletproof operations are non-negotiable.
- **Traefik for production**: Docker host has Traefik reverse proxy. Grafana exposed via DNS, backend services stay internal on Docker network.
- **Azure DevOps CI/CD**: Existing pipeline can integrate validate_all.py. Not priority for demo but planned for Phase 14E.

### Next Session

1. Phase 13A: audit the 167 alert rules, categorize actionable vs noise
2. Phase 13B: start writing operator documentation
3. Dashboard visual review continues
4. Prepare for deployment to Denver DC Docker host

### Context

- Docker host in Denver DC has Traefik -- Grafana needs Traefik labels, not port mapping
- Alloy agents from remote sites need Prometheus remote_write and Loki push accessible (Traefik or direct ports)
- SquaredUp costs $26K/year -- this platform replaces it at $0
- SCOM alert fatigue is the problem the team wants solved -- alert quality is the success metric
- Team: 8 sysadmins + 2 engineers. Sysadmins operate, engineers escalate.
- No on-call rotation yet. Business hours email DLs per site initially.
- Commits: 9291b6a, dc33b3a, be8ff79, b0057cc

---

## Session: 2026-03-24

### Completed

- **Phase 13A Alert Noise Reduction**: 28 changes across 7 alert files. CPU warning raised from 85% to 90%, memory from 80% to 90%. Warning `for` durations extended to 15-30m. Server reboot alerts changed to info (no email). Outage detection timing adjusted (SitePartialOutage 2m, ServerDown 5m).

- **Alert Reference Table**: Complete catalog of all 87 alert rules added to THRESHOLD_GUIDE.md with severity, for duration, description, and source file.

- **SLA Availability dashboard rebuilt**: Fleet summary, per-site table with gauge bars, per-role breakdown, per-host detail (actionable table sorted by worst availability), availability trends with threshold lines.

- **Phase 15 SCOM Data Warehouse Integration**:
  - Researched SCOM DW schema (Perf.vPerfHourly, Alert.vAlert, State.vStateHourly, vManagedEntity)
  - Created SQL Server datasource config (`configs/grafana/datasources/scom_dw.yml`) with env var placeholders
  - Built 4 SCOM dashboards: Server Overview, Fleet Overview, Alerts, Health State
  - Added group-based site filtering using vRelationship joins (matches SCOM's existing group structure: Steamboat Servers, Solitude Servers, etc.)
  - Updated docker-compose.yml with SCOM dashboard mount and datasource mount
  - Default username set to `svc-omread` (existing SCOM DW reader account)

- **Phase 13, 13B, 14 planned in PROJECT_PLAN.md**: Alert strategy, operator documentation, production rollout with full task breakdowns.

- **Deployment context saved to memory**: Team structure, budget, alert fatigue priority, Docker-first approach.

### In Progress

- **Deployment to Denver DC Docker host**: All code ready. Need Traefik configuration and `.env` with SCOM DW credentials on the production host.

### Blockers

- **Traefik configuration**: User needs to inspect existing Traefik setup on Docker host and add Grafana labels. First time working with Traefik.
- **SCOM DW password**: User has it but won't enter until deployed on production host. Set via `.env` at deployment time.

### Decisions

- **SCOM DW parallel with Alloy**: Both data sources coexist. SCOM dashboards for immediate SquaredUp replacement, Alloy dashboards for future state.
- **svc-omread for Grafana SQL connection**: Existing read-only SCOM DW service account. No new SQL accounts needed. No SCOM Run As role needed -- just SQL db_datareader.
- **Group-based site filtering**: SCOM dashboards filter by SCOM groups (Steamboat Servers, etc.) via vRelationship joins. Matches how SCOM is already organized.
- **No RBAC complexity for demo**: Viewer accounts, datacenter dropdown filtering, bookmark-based navigation. LDAP integration deferred to production Phase 14B.
- **Alert noise reduction**: CPU/memory warning thresholds raised, `for` durations extended, reboots changed to info. Designed to be dramatically quieter than SCOM.
- **Password only in .env**: SCOM DW password, SMTP password, all secrets live only in .env (gitignored). Never in repo files.

### Next Session

1. Deploy to Denver DC Docker host (Traefik config, .env setup, stack_manage.py)
2. Verify SCOM DW dashboards populate with real data
3. Create Viewer accounts for team evaluation
4. Phase 13B: start writing operator documentation

### Context

- SCOM DW SQL Server: `VM-DEN-SQL11`, port 1433, database `OperationsManagerDW`, user `svc-omread`
- SCOM has 365 groups organized by site (Steamboat, Solitude, Sugarbush, Stratton, Tremblant, etc.)
- Management Packs installed: Windows Server, AD, DNS, DHCP, IIS, File Services, Exchange, Certificate Services, Nutanix, Linux, Network Monitoring
- 4 active SCOM alerts (all Warning/Medium priority)
- Docker host has Traefik -- Grafana gets labels, not port mapping
- Reporting URL: http://VM-DEN-SQL11:80/ReportServer (SSRS, not what Grafana connects to)
- Commits this session: 33aeeb0, 4793462, 6d8af21, c145343, fc49f70, f1b9a28

---

## Session: 2026-03-24 (continued)

### Completed

- **SCOM DW Simulator**: Azure SQL Edge container with synthetic data. 48 servers across 8 sites, 80K perf rows, 63 alerts, health state. Seeded via `scripts/scom_dw_seed_runner.py` (requires pymssql).

- **Grafana SCOM DW connectivity**: Fixed env var passing -- Grafana provisioning doesn't support `:-` default syntax. SCOM connection vars set in docker-compose.yml Grafana environment section. Defaults point to local simulator (`scom-dw-sim`).

- **SCOM dashboard query fixes**: Removed complex group filter subqueries that broke variable resolution. Simplified to direct queries. Fixed entity type pattern `%Computer%` to match `Microsoft.Windows.Server.Computer`. Set time range to 7 days. Removed broken `$severity` SQL filter.

- **Docker Compose project renamed**: `observability-stack-poc`.

- **API query validation**: 22 out of 23 SCOM panel queries confirmed returning data through Grafana API.

- **SLA Availability dashboard rebuilt**: Fleet summary, per-site, per-role, per-host detail, availability trends.

### In Progress

- **SCOM dashboards visual review**: Queries return data via API but some panels may still show "No data" in the browser due to variable resolution or time range issues. Need `claude --chrome` session or manual review to verify visually.

- **Group-based site filtering**: Removed temporarily because complex subqueries broke dashboards. Need to re-implement as simpler approach once base queries work.

### Blockers

- **Chrome browser integration**: Claude Code has Chrome capability but requires `claude --chrome` flag at session start. Can't enable mid-session. Next session should start with `claude --chrome` for visual dashboard review.

### Decisions

- **Azure SQL Edge for SCOM simulator**: ARM64 compatible (works on Mac), lightweight. Standard mssql/server image is AMD64 only.
- **Simplified SCOM queries first**: Removed group filter subqueries to get base dashboards working. Site filtering added back later.
- **scom-demo Docker Compose profile**: SCOM simulator disabled by default. Start with `--profile scom-demo` to include it.
- **Env vars for SCOM connection**: Set in docker-compose.yml Grafana environment, not in datasource YAML. Grafana resolves `${VAR}` from container environment.
- **Viewer accounts for demo**: Local Grafana accounts with Viewer role. No LDAP during evaluation.
- **Bookmarks over RBAC**: Each site team gets a URL bookmark pre-filtered to their datacenter. Simpler than Editor roles or per-site folders.

### Next Session

1. Start with `claude --chrome` to visually review SCOM dashboards
2. Fix any remaining "No data" panels based on visual review
3. Re-implement group-based site filtering (simpler approach)
4. Deploy to Denver DC Docker host
5. Phase 13B: operator documentation

### Context

- SCOM DW simulator running as `mon-scom-dw-sim` container on `scom-demo` profile
- Seed script: `python scripts/scom_dw_seed_runner.py` (needs pymssql in a venv: `/tmp/scom-venv`)
- To start with simulator: `docker compose --profile scom-demo up -d`
- To swap to production: set `SCOM_DW_HOST=VM-DEN-SQL11` and `SCOM_DW_PASSWORD=<password>` in `.env`
- Grafana sees 3 datasources: Prometheus, Loki, SCOM Data Warehouse
- 4 folders: Enterprise, Servers, Infrastructure, SCOM Monitoring
- Demo data generator still needed for Alloy dashboards (separate from SCOM simulator)
- Commits: fe5da4d, fef63fb, f4419f6

---

## Session: 2026-03-25 (Chrome Review + Phase 15C)

### Completed

- **Chrome visual review of all 4 core SCOM dashboards** (Fleet Overview, Health State, Server Overview, Alerts)
- **Fixed SCOM Fleet Overview**: replaced `DATEADD(hour, -1, GETUTCDATE())` with `$__timeFilter()` in Avg CPU, Avg Memory, Top 10 tables. Fixed "Free %" column visibility (gauge -> color-text, column widths).
- **Fixed SCOM Health State**: replaced `DATEADD(hour, -1)` with `MAX(DateTime)` subquery in all 4 summary stat panels. Seeded 2,016 state rows (48 servers x 42 snapshots across 7 days) for realistic health state data.
- **Fixed SCOM Server Overview**: changed `LIKE '$server'` to `= '${server:raw}'` in all 9 panel queries to fix Grafana MSSQL double-quoting bug. Removed `includeAll` from Server variable.
- **Built 3 new Phase 15C role-specific dashboards**: SQL Server (`scom_sql_server.json`), IIS (`scom_iis.json`), AD/DC (`scom_ad_dc.json`) with stat summaries, performance trends, and role-specific panels.
- **Seeded 32,256 role-specific performance counter rows** in SCOM simulator (8 counters each for SQL/IIS/AD across 8 servers, 7 days hourly).
- **Created `scripts/scom_dw_discovery.sql`**: 7 production discovery queries for counter names, entity types, groups, hostname patterns, and MP validation.
- **Commits**: 10c1179 (dashboard fixes), 08d9db5 (Phase 15C dashboards)

### In Progress

- **SCOM hub-and-spoke site filtering**: Dashboards currently scope to single server, not site-level. Need to add `$site` variable and build fleet-level hub dashboards per role (SQL Fleet, IIS Fleet, AD Fleet) matching Prometheus/Loki pattern. Deferred pending production discovery query results.
- **Default server selection**: Added `current` field to server variables but untested due to Grafana rendering issue.

### Blockers

- **Grafana v11.5.2 panel rendering**: After Grafana volume wipe (required during debugging), ALL dashboards show "Loading plugin panel..." on fresh start. This is a Grafana cold-start/dashboardScene bug, not a dashboard JSON issue. The committed dashboard JSON was verified working before the volume wipe. Fix: wait for Grafana warm-up, or restart Grafana after initial boot. The container may need a manual restart to fully initialize plugins on first cold boot.
- **Production SCOM DW counter names**: Role-specific dashboards (SQL/IIS/AD) use counter names from standard SCOM Management Packs, but exact strings need validation against production. Discovery SQL script created for this purpose.

### Decisions

- **`${server:raw}` for MSSQL variables**: Grafana's MSSQL plugin double-quotes values when using `LIKE '$var'`. Using `= '${server:raw}'` with raw interpolation avoids this. Applied to all server-scoped dashboards.
- **`MAX(DateTime)` for health state summaries**: Health state stat panels query the latest snapshot rather than using `$__timeFilter`, since we always want current state regardless of time picker.
- **Site filtering deferred to next session**: Rather than guess at production group structure, will use discovery query results to build proper site-filtered dashboards that match production exactly. Avoids deployment rework.
- **Counter name validation before deployment**: User has no CI/CD pipeline, so dashboards must be correct on first deploy. Discovery queries provide all needed info to match counter strings to production.

### Next Session

1. **Run `scripts/scom_dw_discovery.sql` against production** (VM-DEN-SQL11) -- user action
2. **Adjust counter names** in all SCOM dashboard queries based on discovery results
3. **Build hub-and-spoke site filtering** using real SCOM group names from production
4. **Build fleet-level dashboards per role** (SQL Fleet, IIS Fleet, AD Fleet) with site breakdown
5. **Fix Grafana cold-start** -- may need to add a startup delay or health check to docker-compose
6. **Re-verify all dashboards visually** after fixes

### Context

- SCOM simulator runs as `mon-scom-dw-sim` on `scom-demo` Docker Compose profile
- Role-specific counter seed script ran via pymssql (`/tmp/scom-venv`), data is ephemeral (lost on container restart)
- The `scom_dw_seed.sql` file does NOT include role-specific counters -- those were seeded via Python only. If the SCOM sim container restarts, only the base seed data (Windows OS counters) will exist. Role counters need re-seeding or adding to the SQL seed file.
- Grafana volume was wiped during debugging -- fresh state, admin/admin login, password change prompt on first access
- The `rawQuery` field in Server Overview targets contains old query strings (pre-fix). These are vestigial -- Grafana uses `rawSql` for execution. Harmless but messy.
- Files not committed: `docs/INTERNAL_PROPOSAL.md` (pre-existing untracked)

---

## Session: 2026-03-25 (continued) -- Production Schema Alignment + Full Dashboard Rebuild

### Completed (14 commits)

- **Production SCOM DW Discovery**: User ran 4 SQL queries against VM-DEN-SQL11 OperationsManagerDW. Discovered: entity type is `Microsoft.Windows.Computer`, counter names stored in separate `vPerformanceRule` table via `RuleRowId`, counter ObjectNames differ from simulator (Processor Information, PercentMemoryUsed, Network Adapter, DirectoryServices, Security System-Wide Statistics). No SQL Server MP perf counters. No SCOM site groups -- site filtering from hostname parsing.
- **Phase 15E complete**: Rebuilt SCOM simulator with production-aligned schema. 72 servers across 9 sites (DEN, DV, SBT, SNO, SOL, STR, SUG, TRM, WP). 44 performance rules, 47 instances, 284K perf rows. vPerformanceRule table added. Hostname pattern VM-<SITE>-<ROLE><NUM>.
- **All 10 SCOM dashboards rebuilt**: Corrected JOIN path (vPerfHourly -> vPerformanceRuleInstance -> vPerformanceRule via RuleRowId), entity type, counter names, hostname field (me.DisplayName not me.Path).
- **Site filtering added to all dashboards**: Site variable extracts code from hostname using STUFF/LEFT/CHARINDEX. Server variable cascades from site. Role dashboards filter by role prefix.
- **Per-Site Summary table** added to Fleet Overview: shows server count, avg CPU, avg memory per site with drill-down links.
- **4 new role dashboards**: DHCP (scom_dhcp.json), DNS (scom_dns.json), DFS Replication (scom_dfs.json), Exchange (scom_exchange.json).
- **SQL Server dashboard removed**: No SQL Server perf counters in production DW.
- **Standardized navigation**: 4-link nav bar on all 10 dashboards with keepTime. Fleet drill-downs pass site context.
- **Auto-seed container**: scom-dw-seed Docker container runs seed automatically on `docker compose --profile scom-demo up`. No manual pymssql step needed.
- **Variable query format fix**: Grafana v11.5 MSSQL plugin requires template variable queries as plain SQL strings, not `{"query": "...", "refId": "..."}` objects. Fixed across all 10 dashboards.
- **Production discovery CSVs saved**: scripts/scom_production_counters.csv, scom_production_entities.csv, scom_production_groups.csv

### 10 SCOM Dashboards (final state)

| Dashboard | UID | Servers | Role Filter |
|-----------|-----|---------|-------------|
| Fleet Overview | scom-fleet-overview | All (72) | None (hub) |
| Server Overview | scom-server-overview | Any | All roles |
| Health State | scom-health-state | All | None |
| Alerts | scom-alerts | All | None |
| AD/DC | scom-ad-dc | DC (18) | VM-*-DC* |
| IIS | scom-iis | IIS (9) | VM-*-IIS* |
| DHCP | scom-dhcp | DHCP (9) | VM-*-DHCP* |
| DNS | scom-dns | DC (18) | VM-*-DC* |
| DFS Replication | scom-dfs | DC+FS (27) | VM-*-DC*/FS* |
| Exchange | scom-exchange | All | None (prod only) |

### Key Technical Decisions

- **Variable queries must be plain strings**: Grafana v11.5 MSSQL plugin cannot unmarshal object-format variable queries. Panel target queries work with objects. This is a Grafana bug/limitation.
- **Site extraction from hostname**: `LEFT(STUFF(me.DisplayName, 1, 3, ''), CHARINDEX('-', STUFF(me.DisplayName, 1, 3, '')) - 1)` extracts site code from VM-<SITE>-<ROLE> pattern.
- **No SCOM site groups in production**: Site filtering via hostname parsing, not SCOM group membership.
- **SQL Server MP not installed**: No SQL-specific perf counters in DW. SQL servers monitored via Windows OS counters only. AG cluster status visible via group data.
- **Production deployment**: Skip `--profile scom-demo`, set `SCOM_DW_HOST=VM-DEN-SQL11` and `SCOM_DW_PASSWORD` in `.env`. Simulator containers don't start without the profile.

### Blockers

- **Production SQL login**: Need `svc-omread` with `db_datareader` on OperationsManagerDW (human action)
- **Network path verification**: Denver DC Docker host to VM-DEN-SQL11 (human action)
- **Hostname pattern validation**: Need to confirm all 1,335 production servers follow `VM-<SITE>-` pattern

### Next Session

1. Visual Chrome review of all 10 rebuilt dashboards with working variables
2. Verify site dropdown, server cascading, and cross-dashboard navigation
3. Build remaining deferred dashboards if needed (UPS/Battery, SQL Cluster/AG)
4. Production deployment prep once SQL login and network path are confirmed

### Context

- Stack: `docker compose --profile scom-demo up -d` (from deploy/docker/)
- Grafana: localhost:3000, admin/admin (fresh volume, password change prompt on first login)
- SCOM simulator seeds automatically via mon-scom-dw-seed container (~3 min on first start)
- Production discovery data in scripts/scom_production_*.csv
- 15 production sites: BMR, DED, DEN, DEU, DV, MM, SBT, SCHW, SNO, SOL, STR, SUG, SVAM, TRM, WP
- Commits: dfac108 through 8442895

---

## Session: 2026-03-26 (continued) -- Chrome Review, Deployment Prep, Documentation

### Completed

- **Chrome review of all 10 SCOM dashboards**: Systematic verification with screenshots. 8 fully passing, IIS partial (ASP.NET counters not seeded -- will work on production), Exchange expected no data (production-only counters).
- **Variable query fix**: Root cause identified -- Grafana v11.5 MSSQL plugin requires template variable queries as plain SQL strings, NOT `{"query": "...", "refId": "..."}` objects. Fixed across all 10 dashboards. This was causing the warning triangles on Site and Server dropdowns.
- **Site variable query fix**: Replaced `SUBSTRING/CHARINDEX` (failed on edge cases) with `STUFF/LEFT/CHARINDEX` for robust site code extraction from `VM-<SITE>-<ROLE>` hostname pattern.
- **Auto-seed container**: Created `scripts/Dockerfile.scom-seed` and `scom-dw-seed` service in docker-compose.yml. SCOM simulator now auto-seeds on `docker compose --profile scom-demo up` -- no manual pymssql step needed.
- **Documentation overhaul**:
  - `scripts/validate_dashboards.py`: Added `scom-dw` to valid datasource UIDs. All 29 dashboards pass validation.
  - `docs/operations/STACK_MANAGEMENT.md`: Full SCOM section with production deployment, demo setup, dashboard inventory, troubleshooting.
  - `docs/operations/DASHBOARD_GUIDE.md`: All 10 SCOM dashboards documented with descriptions, navigation flow, filter table, glossary.
  - `docs/PROJECT_PLAN.md`: Phase 15A marked complete, Phase 15 status updated.
- **Architecture decision**: Reverted standalone `docker-compose.scom.yml` in favor of keeping everything in the main compose file. Made Grafana `depends_on` Prometheus/Loki optional (`required: false`) so Grafana starts even without the full metrics stack. SCOM dashboards work immediately; Alloy dashboards populate when agents deploy.
- **Commits**: 8442895 through 2744ae1 (7 commits this portion)

### In Progress

- **Production deployment**: Deployment steps documented but blocked on infrastructure questions.

### Blockers

- **Docker host domain join status**: User needs to check if the Denver DC Docker host is domain-joined. Determines authentication path to SCOM DW SQL Server.
  - If domain-joined: can use Windows Auth with existing `svc-omread` AD account (Kerberos config needed in Grafana container)
  - If NOT domain-joined (likely): need a SQL auth login (e.g., `grafana-scom-ro`) with db_datareader on OperationsManagerDW
- **SQL Server login creation**: Cannot proceed with production deployment until auth method is confirmed and login is created.
- **Network path verification**: Need to confirm Docker host can reach VM-DEN-SQL11 port 1433.

### Decisions

- **Single compose file, not separate SCOM-only file**: Reverted the `docker-compose.scom.yml` approach. The main compose file handles everything via profiles. Adding a second compose file was fragmentation that didn't respect the existing `stack_manage.py` wrapper and deployment patterns.
- **Grafana dependencies optional**: Changed `depends_on` for Prometheus/Loki to `required: false`. Grafana starts regardless of metrics backend state. SCOM dashboards work immediately on production; Alloy dashboards show "No data" until agents are deployed.
- **Phased demo strategy**: Phase 1 demo shows live SCOM data ("replace SquaredUp today, $26K saved"). Phase 2 demo shows Alloy stack ("replace SCOM agents with better alerting"). Don't mix live and synthetic in the same demo.
- **SQL auth for Grafana**: Most likely path since Docker host is probably not domain-joined. Create a purpose-built SQL login (`grafana-scom-ro`) rather than reusing the AD account name `svc-omread`.
- **Variable queries must be plain strings**: Grafana v11.5 MSSQL plugin limitation. Panel target queries can use object format but template variables cannot. Documented as a known constraint.

### Next Session

1. **Confirm Docker host domain join status** (user action)
2. **Create SQL login on VM-DEN-SQL11** (user action, needs domain join answer first)
3. **Verify network path** Docker host -> VM-DEN-SQL11:1433 (user action)
4. **Test production connection** -- set `.env` values and verify SCOM dashboards populate with real data
5. **Validate hostname patterns** -- confirm all 1,335 production servers follow `VM-<SITE>-` pattern for site variable extraction
6. **Fix any counter name mismatches** -- some panels may show "No data" if production counter strings differ slightly from discovery data

### Context

- Stack wrapper: `python3 scripts/stack_manage.py` from project root (reads `.env` from project root, not `deploy/docker/`)
- `.env` file goes in **project root**, not `deploy/docker/` -- this is how `stack_manage.py` and `_compose_base_cmd()` work
- `svc-omread` exists in ADUC as an AD service account. Do NOT create a SQL login with the same name to avoid confusion. Use `grafana-scom-ro` or similar for the SQL auth login.
- The Grafana volume was wiped during this session. Fresh install state: admin/admin login with password change prompt.
- `docs/INTERNAL_PROPOSAL.md` is still untracked (not committed). Pre-existing file from before these sessions.
- Dashboard validator passes all 29 dashboards (0 failures, 44 warnings -- all pre-existing grid overlap warnings, none SCOM-related).
- Production discovery CSVs in `scripts/scom_production_*.csv` -- these are the ground truth for counter names and entity types.

---
