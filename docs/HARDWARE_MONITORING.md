# Hardware Health Monitoring (Redfish BMC)

## Overview

This document covers out-of-band hardware health monitoring using the Redfish API,
the DMTF standard REST/JSON interface that supersedes legacy IPMI.

- **Target devices**: Server BMCs -- HPE iLO, Dell iDRAC, OpenBMC-based controllers
- **Protocol**: Redfish (HTTPS/JSON) via an external exporter sidecar
- **Scrape interval**: 120 seconds (hardware state changes slowly; aggressive polling
  risks overloading BMC firmware with limited resources)
- **Coverage**: System health, thermal sensors, power draw, drives, memory DIMMs, processors

### Why Redfish Over IPMI

<!-- IPMI has known security weaknesses (cipher zero, unauthenticated commands) and
     limited structured data. Redfish provides authenticated HTTPS, typed JSON payloads,
     and a standardized schema across vendors -- making it the preferred approach for
     modern infrastructure monitoring. -->

IPMI (via `ipmitool`) was the traditional method for out-of-band hardware monitoring,
but it carries well-documented security weaknesses (cipher zero vulnerabilities,
unauthenticated LAN commands) and returns flat, unstructured sensor data. Redfish
provides authenticated HTTPS transport, vendor-standardized JSON schemas, and
richer component metadata. It is the correct protocol choice for any greenfield
monitoring deployment.

---

## Architecture

```
+-------------------+          +-------------------+          +-------------------+
|   BMC (iLO/iDRAC) | <-----  | Redfish Exporter  | <-----  | Alloy Site Gateway|
|   per server       | Redfish | (port 9220)       | scrape  | (per site)        |
|   mgmt network     | API     | sidecar container | 120s    |                   |
+-------------------+ (HTTPS) +-------------------+         +--------+----------+
                                                                      |
                                                              remote_write
                                                                      |
                                                              +-------v--------+
                                                              |   Prometheus   |
                                                              +----------------+
```

### Key Design Decisions

<!-- One gateway per site keeps BMC network access scoped to a single egress point
     per physical location. The multi-target pattern avoids deploying an exporter
     per BMC, which would be operationally expensive at scale. -->

- **One gateway per site**: Each site has a single Alloy gateway responsible for
  scraping all BMCs in that site. This limits the number of systems that need
  network access to the BMC management VLAN.
- **Multi-target pattern**: The Alloy gateway sends `?target=<BMC_IP>` as a query
  parameter to a single exporter instance. The exporter then queries the specified
  BMC on demand. This avoids running N exporter processes for N servers.
- **Sidecar deployment**: The exporter runs as a sidecar container alongside the
  Alloy gateway pod. This keeps BMC network access contained to the gateway pod's
  network namespace rather than exposing management VLAN routes broadly.

---

## Prerequisites

### BMC Access

Each monitored server must have a BMC with Redfish API enabled:

| Vendor | Minimum | Recommended | Notes |
|--------|---------|-------------|-------|
| HPE    | iLO 4   | iLO 5+      | iLO 4 has limited Redfish schema coverage |
| Dell   | iDRAC 8 | iDRAC 9+    | iDRAC 8 Redfish may require firmware update |

Network access from the monitoring stack to the BMC management network is required.
BMC management interfaces are often on a separate VLAN -- verify routing and
firewall rules before deployment.

### Service Accounts

<!-- Redfish API endpoints include destructive operations (power cycle, BIOS config,
     firmware update). A monitoring system must never hold write privileges to
     production hardware. Read-only accounts enforce this boundary at the BMC level,
     preventing accidental or malicious misuse even if credentials are compromised. -->

Create dedicated **read-only** service accounts on each BMC for monitoring purposes.

- **DO NOT use admin accounts** -- principle of least privilege is non-negotiable here.
  The Redfish API exposes endpoints that can power cycle servers, modify BIOS settings,
  and update firmware. A monitoring service account must never have access to these
  capabilities.
- **Recommended naming**: `svc-monitoring` or `redfish-monitor`
- **HPE iLO**: Assign minimum privilege "Login" only (no Configure, no Virtual Media,
  no Remote Console, no Virtual Power and Reset)
- **Dell iDRAC**: Assign the "ReadOnly" role

### Credential Management

<!-- Hardcoded credentials in config files end up in version control, CI logs, and
     container images. Environment variables or secret stores keep credentials out
     of the artifact pipeline entirely. -->

- Store BMC credentials in environment variables or Kubernetes Secrets
- **Never hardcode credentials in configuration files** -- they will inevitably
  leak into version control or container images
- For environments with many BMCs, consider HashiCorp Vault or the
  `external-secrets` operator for automated credential rotation
- Per-target credentials are supported for mixed-vendor environments where
  different BMC groups use different service accounts

---

## Adding Servers

### Step 1: Verify Redfish Access

Before adding a BMC to the monitoring configuration, confirm that the Redfish API
is reachable and credentials are valid:

```bash
# Test Redfish service root endpoint
# -s: silent mode (suppress progress bar)
# -k: skip TLS verification (BMCs typically use self-signed certs)
curl -sk https://<BMC_IP>/redfish/v1/ -u svc-monitoring:password
```

**Expected result**: JSON response containing the Redfish service root with links
to available resource collections (`Systems`, `Chassis`, `Managers`).

**Troubleshooting**:
- **HTTP 401**: Credentials are incorrect or the service account is locked/disabled
- **Connection refused**: Redfish may not be enabled in BMC settings -- check the
  BMC web UI under Network Services or Remote Access settings
- **Timeout**: Network routing issue between monitoring stack and BMC management VLAN

### Step 2: Add Target to Site Gateway

Edit `configs/alloy/gateway/site_gateway.alloy` and add a target block within the
appropriate `prometheus.scrape` component:

```river
target {
    // __address__ points to the local exporter sidecar, not the BMC directly
    "__address__"    = "localhost:9220"
    // __param_target tells the exporter which BMC to query (multi-target pattern)
    "__param_target" = "10.0.1.50"
    // instance label used in all metrics and alert routing
    "instance"       = "10.0.1.50"
    // Human-readable name displayed in dashboards and alert notifications
    "device_name"    = "ESXi Host 01 iLO"
    // Vendor tag enables dashboard filtering (hpe, dell, openbmc)
    "vendor"         = "hpe"
    // Device type distinguishes BMC targets from other scrape targets
    "device_type"    = "server_bmc"
}
```

**Label conventions**:
- `vendor`: Use `"hpe"` for iLO, `"dell"` for iDRAC, `"openbmc"` for OpenBMC.
  This label drives vendor-specific dashboard panels and alert grouping.
- `device_name`: A human-readable identifier that appears in alert notifications
  and dashboard tooltips. Use a name that operations staff can map to a physical
  server (e.g., rack location, hostname, or asset tag).

### Step 3: Configure Exporter Credentials

The Redfish exporter reads credentials from its configuration file or environment
variables. For single-credential environments:

```bash
export REDFISH_USER=svc-monitoring
export REDFISH_PASSWORD=<password>
```

For mixed-vendor environments requiring per-target credentials, configure the
exporter's target-credential mapping file (refer to the specific exporter's
documentation for the exact format).

### Step 4: Verify Data Collection

After deploying the updated configuration:

1. **Check Alloy scrape status**: Open the Alloy UI at `http://gateway:12345` and
   verify the new target shows as `UP` in the scrape targets list.

2. **Query key metrics** in Prometheus or Grafana Explore:

```promql
# BMC reachability -- should return 1
redfish_up{instance="10.0.1.50"}

# Overall system health -- should return 0 (OK)
redfish_health{instance="10.0.1.50"}
```

3. **Check scrape duration**: Verify `scrape_duration_seconds` is under 30 seconds.
   Redfish API calls are slower than typical metric endpoints due to HTTPS overhead
   and BMC firmware processing time.

---

## Metrics Collected

### System Health

| Metric | Values | Meaning |
|--------|--------|---------|
| `redfish_up` | 0 / 1 | Whether the exporter can reach the BMC via Redfish API |
| `redfish_power_state` | 0 / 1 | Server chassis power state (0 = off, 1 = on) |
| `redfish_health` | 0 / 1 / 2 | Overall system health: 0 = OK, 1 = Warning, 2 = Critical |

### Thermal

| Metric | Description |
|--------|-------------|
| `redfish_temperature_celsius` | Per-sensor temperature readings with `sensor` label (CPU, inlet, exhaust, ambient) |
| `redfish_fan_health` | Fan subsystem health state (0 = OK) |

### Power

| Metric | Description |
|--------|-------------|
| `redfish_power_consumed_watts` | Real-time power draw per power supply unit, labeled by PSU index |

### Components

| Metric | Description |
|--------|-------------|
| `redfish_drive_health` | Per-drive health status (0 = OK, non-zero = degraded or failed) |
| `redfish_memory_health` | Per-DIMM health status (detects correctable ECC errors) |
| `redfish_processor_health` | Per-CPU health status |

---

## Recording Rules

<!-- Recording rules pre-compute aggregations that would be expensive to calculate
     at query time across many servers. They also provide stable metric names for
     alerts and dashboards, decoupling presentation from raw metric structure. -->

### Server-Level Aggregations

These rules aggregate per-sensor metrics to a single value per server:

| Rule | Description | Use Case |
|------|-------------|----------|
| `server:temperature_max:celsius` | Hottest sensor reading per server | Threshold alerting -- alert on the worst case, not individual sensors |
| `server:power_consumed:watts` | Total server power (sum of all PSUs) | Capacity planning and per-server power tracking |

### Site-Level Aggregations

These rules provide site-wide operational summaries:

| Rule | Description | Use Case |
|------|-------------|----------|
| `site:hardware_monitored:count` | Total BMCs responding to scrapes | Fleet coverage visibility |
| `site:hardware_unreachable:count` | BMCs failing scrape (`redfish_up == 0`) | Connectivity issue detection |
| `site:hardware_healthy:count` | Servers with `health == 0` (OK) | NOC dashboard green/red counts |
| `site:hardware_warning:count` | Servers with `health == 1` (degraded) | NOC dashboard amber count |
| `site:hardware_critical:count` | Servers with `health == 2` (critical) | NOC dashboard red count |
| `site:power_consumed:watts` | Total power consumption across site | Facility power capacity tracking |
| `site:temperature_max:celsius` | Hottest component reading across entire site | HVAC and environmental alerting |

---

## Alert Rules

### BMC Connectivity

| Alert | Condition | For Duration | Severity | Notes |
|-------|-----------|--------------|----------|-------|
| `RedfishBMCUnreachable` | `redfish_up == 0` | 10m | WARNING | 10m hold avoids alerting on transient BMC reboots or brief network blips |

### System Health

| Alert | Condition | For Duration | Severity | Action |
|-------|-----------|--------------|----------|--------|
| `RedfishHealthWarning` | `redfish_health == 1` | 5m | WARNING | Investigate which subsystem is degraded (thermal, storage, memory) |
| `RedfishHealthCritical` | `redfish_health == 2` | 2m | CRITICAL | Immediate physical inspection required -- component failure likely |

### Thermal

<!-- Temperature thresholds are set conservatively below vendor thermal shutdown
     limits (typically 95-105C). The WARNING at 75C gives operators time to
     investigate airflow or HVAC issues before reaching critical territory. -->

| Alert | Condition | For Duration | Severity | Action |
|-------|-----------|--------------|----------|--------|
| `RedfishTemperatureHigh` | `> 75C` | 10m | WARNING | Check airflow obstructions, HVAC status, fan health |
| `RedfishTemperatureCritical` | `> 85C` | 5m | CRITICAL | Risk of thermal shutdown -- immediate environmental investigation |

### Power

| Alert | Condition | For Duration | Severity | Action |
|-------|-----------|--------------|----------|--------|
| `RedfishServerPoweredOff` | `power_state == 0 AND redfish_up == 1` | 5m | CRITICAL | Server is off but BMC is reachable -- indicates unexpected shutdown (not network issue) |

### Components

| Alert | Condition | For Duration | Severity | Action |
|-------|-----------|--------------|----------|--------|
| `RedfishDriveUnhealthy` | `drive_health != 0` | 5m | WARNING | Predictive drive failure -- check RAID status, schedule replacement |
| `RedfishMemoryUnhealthy` | `memory_health != 0` | 5m | WARNING | Likely correctable ECC errors accumulating -- plan DIMM replacement |

---

## Redfish Exporter Selection

### Options

| Exporter | Language | Strengths | Considerations |
|----------|----------|-----------|----------------|
| `prometheus-redfish-exporter` | Go | Most widely deployed, strong HPE/Dell support, low resource usage | Less flexible for custom metrics |
| `redfish_exporter` | Python | Easier to extend for custom BMC vendors, more readable codebase | Higher memory footprint, slower cold start |
| Custom exporter | Varies | Full control for unsupported BMC vendors | Maintenance burden, must implement Redfish client |

### Deployment Model

<!-- The sidecar pattern keeps BMC network access scoped to the gateway pod.
     Without this, every pod in the namespace (or node) would need routes to
     the management VLAN, expanding the attack surface significantly. -->

- Runs as a **sidecar container** alongside the Alloy gateway
- Listens on port **9220** (configurable via environment variable or flag)
- Uses the **multi-target pattern**: a single exporter instance serves all BMCs.
  The gateway sends `?target=<BMC_IP>` as a query parameter, and the exporter
  queries the specified BMC on each scrape.

---

## Deployment

### Docker Compose

```yaml
redfish-exporter:
  image: <exporter-image>
  ports:
    - "9220:9220"
  environment:
    # Credentials injected via environment -- never baked into the image
    - REDFISH_USER=${REDFISH_USER}
    - REDFISH_PASSWORD=${REDFISH_PASSWORD}
  networks:
    - monitoring
  # Restart policy ensures exporter recovers from transient failures
  restart: unless-stopped
```

### Kubernetes (Helm)

- Deploy as a **sidecar container** in the Alloy gateway pod spec
- Mount credentials from a Kubernetes Secret (or use `external-secrets` operator
  for Vault-backed rotation)
- Apply a **NetworkPolicy** allowing HTTPS (port 443) outbound only to the BMC
  management VLAN CIDR -- deny all other egress from the exporter container

### Network Requirements

| Direction | Protocol | Port | Source | Destination | Purpose |
|-----------|----------|------|--------|-------------|---------|
| Outbound | HTTPS | 443 | Redfish exporter | BMC management IPs | Redfish API calls |
| Inbound | HTTP | 9220 | Alloy gateway | Redfish exporter (localhost) | Metric scraping |

BMC management networks are typically isolated VLANs. Firewall rules or network
policies must explicitly permit monitoring traffic between the monitoring stack
and the management VLAN.

---

## Security Considerations

### Credential Rotation

<!-- BMC credentials that never rotate become a persistent risk vector. If
     credentials leak (e.g., via a backup, old container image, or log), the
     exposure window is unbounded without rotation. -->

- BMC passwords should be rotated on a defined schedule (quarterly at minimum)
- Use centralized secret management (HashiCorp Vault, Kubernetes `external-secrets`
  operator) to automate rotation
- Verify that the exporter supports credential reload without full restart -- some
  exporters watch their config file for changes, others require a SIGHUP or restart

### Network Isolation

- BMC management networks carry sensitive capabilities: power control, remote
  console (KVM), BIOS configuration, firmware updates
- Monitoring traffic should be **read-only and minimally privileged** at both the
  credential and network level
- Consider dedicated monitoring VLAN peering to the management VLAN with ACLs
  restricting traffic to HTTPS (port 443) only

### TLS Verification

<!-- Most BMCs ship with self-signed certificates because enterprise PKI deployment
     to BMC firmware is operationally complex. Disabling TLS verification is a
     pragmatic tradeoff, but should be revisited if the organization deploys PKI
     to its BMC fleet. -->

- Most BMCs use **self-signed certificates** generated during initial setup
- The exporter is typically configured with `insecure_skip_verify: true` for
  self-signed environments
- If the organization deploys enterprise PKI certificates to BMC firmware, enable
  full TLS verification in the exporter configuration to detect certificate
  tampering or MITM attacks

---

## Dashboard Integration

### Hardware Health Dashboard (`hardware-overview`)

The primary hardware monitoring dashboard provides:

- **System health grid**: Color-coded matrix of all monitored servers (green/amber/red)
- **Temperature gauges**: Per-server hottest sensor with threshold markers
- **Power tracking**: Per-server and site-total power consumption over time
- **Component status**: Drive, memory, and processor health per server

### Enterprise NOC Dashboard

The NOC overview includes site-level hardware health summary panels:

- Total monitored servers
- Count of healthy / warning / critical systems
- Unreachable BMC count

### Cross-Navigation

Dashboards support drill-down navigation:

```
Enterprise NOC  -->  Site Overview  -->  Hardware Health (per server detail)
```

Clicking a site's hardware health count in the NOC dashboard navigates to the
site-specific hardware overview with pre-filtered variables.

---

## Troubleshooting

### BMC Not Responding

1. **Verify network connectivity**:
   ```bash
   curl -sk https://<BMC_IP>/redfish/v1/
   ```
   If this times out, the issue is network routing or firewall rules, not
   the monitoring stack.

2. **Check credentials**: Ensure the service account is not locked. Some BMCs
   lock accounts after repeated failed authentication attempts.

3. **Verify Redfish is enabled**: Check the BMC web UI under Network Services
   or Remote Access Configuration. Redfish may be disabled by default on
   older firmware versions.

4. **Check BMC firmware version**: Older firmware may have Redfish implementation
   bugs. Consult the vendor's firmware release notes for known issues and
   update if feasible.

5. **Check concurrent session limits**: BMCs typically allow 4-8 concurrent
   Redfish sessions. If other tools (vendor management consoles, other monitoring
   systems) consume available sessions, the exporter will receive connection
   rejections.

### Stale Data

<!-- BMC sensor polling is handled by the BMC's internal firmware on its own
     schedule, independent of external API queries. Querying more frequently
     than the BMC updates its sensors provides no additional data freshness
     and wastes BMC resources. -->

- BMC sensors update on their own internal schedule, typically every 30-60 seconds
- The 120-second scrape interval is chosen to stay well above the BMC's internal
  refresh rate while avoiding excessive API load
- If data appears stale, check the BMC's own web UI to confirm whether sensor
  values are updating -- the issue may be in the BMC firmware itself, not the
  monitoring pipeline

### High Scrape Duration

- Redfish API calls are inherently slower than SNMP (JSON over HTTPS with TLS
  handshake vs. UDP) -- scrape durations of 5-15 seconds are normal
- The 120-second interval provides ample headroom for slow BMC responses
- If scrape duration exceeds 30 seconds:
  - Reduce the metric scope by limiting which Redfish resource paths the
    exporter queries
  - Increase the exporter's per-request timeout
  - Check if the BMC is under high load from other management tools

---

## Related Documentation

- `docs/ALERT_RUNBOOKS.md` -- Alert investigation and remediation procedures
- `ARCHITECTURE.md` -- Overall system architecture and component relationships
- `docs/BACKEND_DEPLOYMENT.md` -- Prometheus server setup and recording rules configuration
- `docs/SNMP_TRAPS.md` -- SNMP-based monitoring (complementary to Redfish for network devices)
