# Production Deployment Notes

## Docker Host Environment

- Location: Denver DC
- Traefik reverse proxy running at `/opt/docker-host/traefik/`
- App containers in `/opt/docker-apps/`
- External Docker network: `Frontend` (used by Traefik for auto-discovery)

## Traefik Configuration

Traefik auto-discovers containers via Docker labels on the `Frontend` network.

- Entrypoints: HTTP (:80), HTTPS (:443), Dashboard (:8080)
- Docker provider: watches `Frontend` network, `exposedByDefault: false`
- File provider: `/dynamic` directory for static routes
- Certificates: `/opt/docker-host/traefik/certificates/`

## Grafana Integration with Traefik

To expose Grafana through Traefik:

1. Join the `Frontend` external network
2. Add Traefik labels for routing
3. Remove direct port mapping (Traefik handles it)

Required additions to our docker-compose.yml Grafana service:

```yaml
# Add to grafana service:
networks:
  - Frontend      # Traefik discovery
  - monitoring    # Internal stack communication
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.grafana.rule=Host(`<monitoring-hostname>`)"
  - "traefik.http.routers.grafana.entrypoints=https"
  - "traefik.http.routers.grafana.tls=true"
  - "traefik.http.services.grafana.loadbalancer.server.port=3000"
```

```yaml
# Add to networks section:
networks:
  Frontend:
    external: true
  monitoring:
    driver: bridge
```

## SCOM DW Connection

- SQL Server: set `SCOM_DW_HOST` in `.env`
- Auth: SQL login (Docker host is not domain-joined)
- Login name: create dedicated login (e.g., `grafana-scom-ro`) with `db_datareader`
- Encrypt: set to `"true"` for production (currently `"disable"` for simulator)

## Pre-Deployment Checklist

- [ ] Confirm Docker host access and directory for our app
- [ ] Create SQL login on SCOM DW server with db_datareader
- [ ] Verify network path: Docker host -> SCOM DW SQL Server port 1433
- [ ] Get monitoring hostname for Traefik routing (e.g., monitoring.example.com)
- [ ] Add TLS certificate for monitoring hostname to Traefik
- [ ] Update `.env` with production SCOM DW connection details
- [ ] Update `encrypt` in scom_dw.yml from "disable" to "true" for production
- [ ] Clone repo to `/opt/docker-apps/monitoring` (or appropriate directory)
- [ ] Run `python3 scripts/stack_manage.py`
