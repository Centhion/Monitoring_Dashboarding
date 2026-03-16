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
