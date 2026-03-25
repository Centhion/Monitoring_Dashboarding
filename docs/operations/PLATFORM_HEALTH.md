# Checking Platform Health

How to verify the monitoring stack is healthy and what to do when a component is down.

---

## Quick Health Check

Run from the monitoring server:

```bash
python3 scripts/stack_manage.py --status
```

This checks all four components and reports their status. A healthy stack looks like:

```
Checking prerequisites...
  Docker: OK
  Docker Compose: OK

Checking service health...
  Prometheus: OK (http://localhost:9090)
  Loki: OK (http://localhost:3100)
  Alertmanager: OK (http://localhost:9093)
  Grafana: OK (http://localhost:3000)

All services healthy.
```

---

## Manual Health Check URLs

If you can't run the script, check each component directly in your browser:

| Component | Health URL | Healthy Response |
|-----------|-----------|-----------------|
| Grafana | `http://<host>:3000/api/health` | `{"database":"ok"}` |
| Prometheus | `http://<host>:9090/-/healthy` | "Prometheus Server is Healthy" |
| Loki | `http://<host>:3100/ready` | "ready" |
| Alertmanager | `http://<host>:9093/-/healthy` | "OK" |

---

## What to Do When a Component Is Down

### Grafana Down

**Impact**: Users cannot view dashboards. Alerts continue to fire and deliver via Alertmanager (Grafana is the UI, not the alerting engine for Prometheus alerts).

**Fix**:
1. Check the container: `docker compose ps grafana`
2. Check logs: `docker compose logs --tail=50 grafana`
3. Restart: `docker compose restart grafana`
4. If it won't start, check disk space and the Grafana database file

### Prometheus Down

**Impact**: No new metrics are collected. Existing data is retained on disk. Alert rules stop evaluating. Dashboards show stale data.

**Fix**:
1. Check the container: `docker compose ps prometheus`
2. Check logs: `docker compose logs --tail=50 prometheus`
3. Common cause: disk full (Prometheus stores data locally). Check `docker exec mon-prometheus df -h`
4. Restart: `docker compose restart prometheus`
5. After restart, verify targets are being scraped: `http://<host>:9090/targets`

### Loki Down

**Impact**: No new logs are ingested. Existing logs are retained. Log Explorer dashboard shows no new entries. Metrics and alerts are not affected.

**Fix**:
1. Check the container: `docker compose ps loki`
2. Check logs: `docker compose logs --tail=50 loki`
3. Common cause: ingestion rate limit exceeded (log storm). Check for `rate_limited` in Loki logs.
4. Restart: `docker compose restart loki`

### Alertmanager Down

**Impact**: Alert rules still evaluate in Prometheus, but notifications are not delivered. Teams and email alerts stop until Alertmanager recovers. Alerts queue in Prometheus and deliver when Alertmanager comes back.

**Fix**:
1. Check the container: `docker compose ps alertmanager`
2. Check logs: `docker compose logs --tail=50 alertmanager`
3. Restart: `docker compose restart alertmanager`
4. After restart, check `http://<host>:9093/#/alerts` to see queued alerts

### Everything Down

If all components are down:
1. Check Docker: `docker info` (is the Docker daemon running?)
2. Check the host: disk space (`df -h`), memory (`free -m`), CPU (`top`)
3. Restart the full stack: `python3 scripts/stack_manage.py`
4. If the Docker host itself is down, it needs to be restarted by the infrastructure team

---

## Monitoring the Monitoring

The platform monitors itself. These alerts fire when components are unhealthy:

| Alert | What It Means |
|-------|--------------|
| `PrometheusTargetDown` | Prometheus cannot reach a monitored target |
| `PrometheusNotificationsFailing` | Prometheus cannot deliver alerts to Alertmanager |
| `PrometheusStorageNearFull` | Prometheus disk usage above 80% |
| `AlertmanagerNotificationsFailing` | Alertmanager cannot deliver to Teams/email |
| `LokiRequestErrors` | Loki is returning errors |
| `LokiIngestionRateHigh` | Log ingestion rate is above normal |

If the monitoring stack itself is fully down, these self-monitoring alerts obviously cannot fire. This is why an **external healthcheck** (a cron job on a separate server that curls the health endpoints) is recommended for production deployments. See Phase 14 in the project plan.
