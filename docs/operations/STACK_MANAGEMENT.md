# Stack Management

How to start, stop, restart, and manage the monitoring stack using `stack_manage.py`.

---

## Commands

Run all commands from the repository root on the Docker host.

### Start the Stack (Production)

```bash
python3 scripts/stack_manage.py
```

This starts the core stack (Grafana, Prometheus, Loki, Alertmanager), waits for health checks, and verifies everything is operational. SCOM dashboards connect to the production DW configured in `.env`. Prometheus/Loki dashboards populate when Alloy agents are deployed.

### Start the Stack (SCOM Demo)

```bash
python3 scripts/stack_manage.py --scom-demo
```

Starts the core stack plus the SCOM DW simulator (Azure SQL Edge) and auto-seed container. All SCOM dashboards render synthetic data immediately -- no production access needed. The seed takes ~8 minutes on first run to populate 411K rows across 9 sites.

### Check Status

```bash
python3 scripts/stack_manage.py --status
```

Reports the health of each component without starting or stopping anything.

### Stop the Stack (Preserve Data)

```bash
python3 scripts/stack_manage.py --stop
```

Stops all containers. **Data is preserved** -- Prometheus metrics, Loki logs, and Grafana settings remain on disk. The next `stack_manage.py` start will resume where you left off.

Use this for:
- Planned maintenance on the Docker host
- Configuration changes that require a restart
- Temporary shutdowns

### Reset the Stack (Delete All Data)

```bash
python3 scripts/stack_manage.py --reset
```

Stops all containers **and deletes all data volumes**. This removes:
- All collected metrics (Prometheus)
- All collected logs (Loki)
- Grafana database (dashboards are reprovisioned from files, but any UI-created silences, annotations, or API keys are lost)

Use this only for:
- Starting fresh after testing
- Recovering from a corrupted database
- Rebuilding the stack from scratch

**This is destructive and irreversible.** Back up the Grafana database first if you have important non-provisioned settings.

---

## SCOM Data Warehouse Connection

The stack reads from the SCOM Data Warehouse via a SQL Server datasource. This replaces SquaredUp by connecting Grafana directly to the existing SCOM DW.

### Production Deployment

Set these variables in your `.env` file (in `deploy/docker/`):

```env
SCOM_DW_HOST=<your-scom-dw-sql-server>
SCOM_DW_PORT=1433
SCOM_DW_DATABASE=OperationsManagerDW
SCOM_DW_USER=<your-sql-login>
SCOM_DW_PASSWORD=<your-password>
```

Prerequisites:
- SQL login `svc-omread` with `db_datareader` role on `OperationsManagerDW`
- Network path from the Docker host to the SCOM DW SQL Server (port 1433)

Then start the stack normally:

```bash
cd deploy/docker
docker compose up -d
```

The SCOM dashboards (in the "SCOM Monitoring" folder) will connect to production data immediately. Prometheus/Loki dashboards will show "No data" until Alloy agents are deployed -- this is expected.

### Demo/Development (Simulator)

For local testing without production access, use the `scom-demo` profile which starts an Azure SQL Edge simulator and auto-seeds it with synthetic data matching the production schema:

```bash
cd deploy/docker
docker compose --profile scom-demo up -d
```

The seed container (`mon-scom-dw-seed`) waits for SQL Edge to be ready, then populates 72 servers across 9 sites with 7 days of hourly performance data. No manual seeding step required.

### SCOM Dashboards (10 total)

| Dashboard | Description | Data Source |
|-----------|-------------|-------------|
| Fleet Overview | Per-site summary, top problem servers, CPU trend | All servers |
| Server Overview | Single server CPU, memory, disk, network detail | Selected server |
| Health State | Healthy/warning/critical counts, state history | State.vStateHourly |
| Alerts | Active/resolved alerts, severity breakdown, trend | Alert.vAlert |
| AD/DC | LDAP, Kerberos, NTLM, DRA replication | Domain Controllers |
| IIS | Connections, requests, bandwidth, errors | IIS servers |
| DHCP | Requests, acks, queue length, packets | DHCP servers |
| DNS | Query volume, recursive queries, dynamic updates | Domain Controllers |
| DFS Replication | Staging space, conflict space, bandwidth savings | DC + File Servers |
| Exchange | Mail flow, queue, DB latency (production only) | Exchange servers |

All dashboards include a **Site** dropdown for filtering by datacenter and a **Server** dropdown that cascades from the selected site.

### Troubleshooting

**"No data" on all SCOM panels**: Check `.env` has correct `SCOM_DW_HOST` and `SCOM_DW_PASSWORD`. Verify network connectivity: `telnet <your-scom-dw-host> 1433`.

**Site dropdown empty**: The site variable extracts site codes from hostnames matching `VM-<SITE>-` pattern. If production servers use a different naming convention, the variable query needs adjustment.

**Exchange dashboard empty**: Expected in the simulator (Exchange counters not seeded). Will populate on production if the Exchange Management Pack is installed.

---

## Removing a Server from Monitoring

To stop monitoring a server:

1. **Uninstall Alloy** from the server:
   - Windows: Uninstall via Programs and Features, or `msiexec /x <product-code>`
   - Linux: `sudo apt remove grafana-alloy` or `sudo yum remove grafana-alloy`

2. **No cleanup needed on the monitoring stack.** The server's metrics and logs will age out automatically based on retention settings:
   - Prometheus: 30 days
   - Loki: 30 days (720 hours)

3. The server will disappear from dashboard dropdowns within 5 minutes of the last metric being received.

4. If the server had alert silences, they will expire naturally. No manual cleanup needed.

---

## Configuration Changes

After editing any configuration file, restart the affected component:

| Changed File | Restart Command |
|-------------|-----------------|
| `configs/prometheus/prometheus.yml` | `docker compose restart prometheus` |
| `configs/prometheus/recording_rules.yml` | `curl -X POST http://localhost:9090/-/reload` |
| `alerts/prometheus/*.yml` | `curl -X POST http://localhost:9090/-/reload` |
| `configs/loki/loki.yml` | `docker compose restart loki` |
| `configs/alertmanager/alertmanager.yml` | `docker compose restart alertmanager` |
| `configs/grafana/datasources/*.yml` | `docker compose restart grafana` |
| `configs/grafana/notifiers/*.yml` | `docker compose restart grafana` |
| `dashboards/**/*.json` | Automatic (Grafana polls every 30s) |

**Prometheus hot reload**: Alert rules and recording rules can be reloaded without restarting Prometheus. Send a POST to the reload endpoint:

```bash
curl -X POST http://localhost:9090/-/reload
```

This is the preferred method for alert threshold changes -- no downtime, no data loss.
