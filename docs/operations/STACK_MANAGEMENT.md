# Stack Management

How to start, stop, restart, and manage the monitoring stack using `stack_manage.py`.

---

## Commands

Run all commands from the repository root on the Docker host.

### Start the Stack

```bash
python3 scripts/stack_manage.py
```

This starts all containers, waits for health checks, and verifies the full stack is operational. Output shows each component's status as it comes up.

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

## Starting with SCOM Simulator

To include the SCOM Data Warehouse simulator (for demo environments):

```bash
docker compose --profile scom-demo -f deploy/docker/docker-compose.yml up -d
```

Then seed the demo data:

```bash
python3 scripts/scom_dw_seed_runner.py
```

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
