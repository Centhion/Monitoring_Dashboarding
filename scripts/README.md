# Scripts

## Active (used in current deployment)

| Script | Purpose |
|--------|---------|
| `stack_manage.py` | Stack startup, health checks, shutdown. |
| `validate_dashboards.py` | Validates Grafana dashboard JSON structure and datasource references. |
| `validate_all.py` | Orchestrates all validators and produces a unified report. |
| `validate_on_save.py` | Lightweight post-save hook for YAML/JSON syntax checks. |
| `validate_alloy.py` | Validates Alloy agent configuration files. |
| `validate_prometheus.py` | Validates Prometheus and Alertmanager configuration files. |

## Future Phases (not yet deployed)

These scripts are built and tested but depend on infrastructure not yet in place
(Alloy agents, LDAP, Lansweeper API, etc.).

| Script | Phase | Depends On |
|--------|-------|------------|
| `deploy_configure.py` | Phase 10 | Site inventory, SMTP relay, Teams webhook |
| `demo_data_generator.py` | Phase 10 | Prometheus + Loki running with Alloy agents |
| `configure_rbac.py` | Phase 8 | LDAP/AD integration, Grafana API key |
| `validate_rbac.py` | Phase 8 | LDAP/AD integration, live Grafana instance |
| `fleet_inventory.py` | Phase 5.7 | Host inventory CSV, Ansible control node |
| `validate_fleet_tags.py` | Phase 5.7 | Live Prometheus with Alloy agent data |
| `lansweeper_sync.py` | Phase 7D | Lansweeper Cloud API access (PAT token) |
| `maintenance_window.py` | Phase 13 | Grafana API key, alert rules deployed |
