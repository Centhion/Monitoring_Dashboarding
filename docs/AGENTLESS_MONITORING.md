# Agentless Monitoring Guide

## Overview

Some devices cannot run a local Alloy agent. Embedded firmware, vendor restrictions, and locked-down appliances all prevent agent installation. Agentless monitoring uses external probing from the site gateway to collect metrics and events from these targets.

Supported methods:

- **SNMP polling** -- periodic metric collection over UDP 161
- **SNMP traps** -- event-driven notifications pushed to the gateway on UDP 162
- **Redfish API** -- hardware health via HTTPS from server BMCs
- **Blackbox probing** -- reachability checks using ICMP, TCP, HTTP, and DNS
- **WMI remoting** -- Windows performance counters over DCOM (advanced, not included in template)
- **SSH-based collection** -- Linux command output parsed into metrics (advanced, not included in template)

This guide covers architecture, use cases, and configuration for each method.

---

## When to Use Agentless Monitoring

### Agent Not Possible

| Device Category | Reason | Recommended Method |
|-----------------|--------|--------------------|
| Network switches, routers, firewalls | No agent support on network OS | SNMP |
| UPS, PDU, environmental sensors | Embedded firmware with no user-space runtime | SNMP |
| Server BMCs (iLO, iDRAC) | Out-of-band management interface, not a general-purpose OS | Redfish |
| Legacy appliances | Vendor does not support custom software installation | SNMP or blackbox probes |
| IoT/OT devices | Limited OS, no agent runtime available | SNMP (if supported) or blackbox probes |

### Agent Not Preferred

| Scenario | Reason | Recommended Method |
|----------|--------|--------------------|
| Third-party managed servers | Contractual restrictions on installing software | Blackbox probes, WMI remoting |
| DMZ hosts | Security policy prohibits additional services | Blackbox probes |
| Short-lived VMs | Agent deployment overhead exceeds VM lifetime | Blackbox probes |
| Read-only infrastructure | Immutable images that cannot be modified | Blackbox probes |

---

## Agentless Collection Methods

### 1. SNMP Polling (Network Devices)

- **Protocol**: UDP 161 (polling from gateway to device)
- **Data type**: Metrics (counters, gauges, status)
- **Best for**: Switches, routers, firewalls, APs, UPS, NAS
- **Alloy component**: `prometheus.exporter.snmp`
- **Detail**: See [docs/SNMP_MONITORING.md](SNMP_MONITORING.md)

### 2. SNMP Trap Reception (Event-Driven)

- **Protocol**: UDP 162 (device pushes to gateway)
- **Data type**: Events/logs (stored in Loki)
- **Best for**: Link-down events, auth failures, device reboots
- **Component**: snmptrapd sidecar + Alloy syslog receiver
- **Detail**: See [docs/SNMP_TRAPS.md](SNMP_TRAPS.md)

### 3. Redfish API (Server Hardware)

- **Protocol**: HTTPS 443 (polling from gateway to BMC)
- **Data type**: Metrics (health, temperature, power, components)
- **Best for**: HPE iLO, Dell iDRAC, Lenovo XClarity, OpenBMC
- **Component**: External Redfish exporter sidecar
- **Detail**: See [docs/HARDWARE_MONITORING.md](HARDWARE_MONITORING.md)

### 4. Blackbox Probing (Reachability)

- **Protocol**: ICMP, TCP, HTTP/HTTPS, UDP/DNS
- **Data type**: Metrics (success/failure, latency)
- **Best for**: Any device with a network interface or service port
- **Component**: Alloy embedded blackbox exporter
- **Detail**: See [docs/CERTIFICATE_MONITORING.md](CERTIFICATE_MONITORING.md) (TLS probes) and `configs/alloy/certs/blackbox_modules.yml`

### 5. WMI Remoting (Windows -- Advanced)

- **Protocol**: DCOM/WMI (TCP 135 + dynamic ports)
- **Data type**: Metrics (performance counters, service status)
- **Best for**: Windows servers where agent cannot be installed but WinRM/WMI is available
- **Status**: Not included in template (requires custom exporter like wmi_exporter in proxy mode)
- **Alternative**: Consider deploying Alloy agent instead -- it uses far less overhead than WMI remoting

### 6. SSH-Based Collection (Linux -- Advanced)

- **Protocol**: SSH (TCP 22)
- **Data type**: Metrics (parsed from command output)
- **Best for**: Linux hosts where agent installation is restricted
- **Status**: Not included in template (requires custom script or node_exporter textfile collector via SSH)
- **Alternative**: Deploy Alloy agent -- it is a single static binary with minimal dependencies

---

## Architecture

### Proxy Collection Pattern

```
Target Device (no agent)
    |
    v (SNMP/Redfish/ICMP/HTTP)
Site Gateway (Alloy + sidecars)
    |
    v (remote_write / loki push)
Central Backend (Prometheus + Loki)
    |
    v
Grafana Dashboards
```

The site gateway acts as a proxy collector:

- Polls targets using the appropriate protocol
- Enriches metrics with standard labels (`datacenter`, `environment`)
- Pushes to central Prometheus and Loki

### Why Gateway-Based

- Keeps protocol complexity at the gateway, not at every target
- Single point for credential management (SNMP communities, Redfish passwords)
- Network access from one gateway host, not from the entire monitoring stack
- Easy to add/remove targets by editing gateway config

---

## Blackbox Probe Configuration

### Available Modules

| Module | Protocol | Use Case |
|--------|----------|----------|
| `icmp_check` | ICMP | Host reachability (ping) |
| `tcp_check` | TCP | Port connectivity |
| `udp_dns_check` | UDP | DNS resolver validation |
| `http_synthetic` | HTTP GET | Web service availability |
| `http_post_synthetic` | HTTP POST | API endpoint validation |
| `https_cert_check` | HTTPS | Certificate + availability |
| `tcp_tls_cert_check` | TCP+TLS | TLS service certificate |

### Adding a Probe Target

Edit `configs/alloy/certs/endpoints.yml` or `role_cert_monitor.alloy`:

```
// ICMP ping probe for a network appliance
target {
  name    = "fw-perimeter"
  address = "10.0.0.1"
  module  = "icmp_check"
  labels  = {
    datacenter  = "site-alpha"
    environment = "prod"
    device_type = "firewall"
    service     = "Perimeter Firewall"
  }
}

// HTTP probe for an appliance web interface
target {
  name    = "nas-webui"
  address = "https://nas01.corp.example.com"
  module  = "http_synthetic"
  labels  = {
    datacenter  = "site-alpha"
    environment = "prod"
    device_type = "nas"
    service     = "NAS Web Interface"
  }
}
```

### Probe Metrics

| Metric | Description |
|--------|-------------|
| `probe_success` | 1=reachable, 0=unreachable |
| `probe_duration_seconds` | Round-trip latency |
| `probe_dns_lookup_time_seconds` | DNS resolution time (HTTP probes) |
| `probe_ssl_earliest_cert_expiry` | Certificate expiry (TLS probes) |

---

## Combining Methods for Full Coverage

For a device that cannot run an agent, layer multiple agentless methods:

| Device Type | Metrics (SNMP) | Hardware (Redfish) | Reachability (Probe) | Events (Traps) |
|------------|---------------|-------------------|---------------------|----------------|
| Network switch | Yes | -- | Yes (ICMP) | Yes |
| Firewall | Yes | -- | Yes (ICMP/HTTP) | Yes |
| Server (no agent) | -- | Yes (if BMC) | Yes (ICMP/TCP) | -- |
| UPS | Yes | -- | Yes (ICMP) | Yes |
| Web appliance | -- | -- | Yes (HTTP/HTTPS) | -- |
| IoT sensor | Yes (if SNMP) | -- | Yes (ICMP) | Optional |

---

## Limitations

### Compared to Agent-Based Monitoring

- **Less granularity**: SNMP/Redfish provide device-level metrics, not process-level
- **Higher latency**: External polling has network round-trip overhead
- **No log collection**: Cannot read local logs without agent (except syslog/traps)
- **Credential management**: Each target needs credentials stored centrally
- **Network dependency**: If network path to target fails, monitoring fails

### Recommendation

Deploy Alloy agents where possible. Agentless monitoring is a complement for devices that genuinely cannot run agents, not a replacement for agent-based collection on servers.

---

## Security Considerations

### Credential Storage

- SNMP community strings and Redfish passwords are stored in gateway config
- Use Kubernetes Secrets or Vault for production deployments
- Rotate credentials periodically
- Use SNMPv3 over v2c where supported

### Network Access

- Gateway needs network path to all target management interfaces
- This may cross VLAN boundaries (management, OOB, IoT networks)
- Implement firewall rules to allow only required protocols and ports
- Document all cross-VLAN access in network security policy

### Probe Impact

- ICMP and TCP probes have negligible impact on targets
- SNMP walks can be CPU-intensive on low-power devices -- use targeted OIDs
- Redfish API calls are heavier -- 120s interval prevents BMC overload
- HTTP probes should not trigger WAF/IDS alerts -- whitelist gateway IP

---

## Troubleshooting

### Target Not Responding to Probes

1. Verify network connectivity from gateway: `ping <target_ip>`
2. Check firewall rules for required protocol/port
3. For SNMP: verify community string or v3 credentials
4. For Redfish: verify BMC is reachable on HTTPS and credentials work
5. Check Alloy logs on gateway for scrape errors

### Intermittent Probe Failures

- Network instability between gateway and target
- Target under heavy load (slow SNMP responses)
- Increase scrape timeout (but not beyond 30s)
- Check for packet loss: `mtr` or `traceroute` from gateway to target

### Missing Data After Gateway Restart

- WAL (Write-Ahead Log) in Alloy preserves unsent data across restarts
- If WAL is full, oldest data is dropped -- check WAL directory size
- Verify remote_write endpoint is healthy after restart

---

## Related Documentation

- [docs/SNMP_MONITORING.md](SNMP_MONITORING.md) -- SNMP device monitoring in detail
- [docs/SNMP_TRAPS.md](SNMP_TRAPS.md) -- Trap ingestion pipeline
- [docs/HARDWARE_MONITORING.md](HARDWARE_MONITORING.md) -- Redfish BMC monitoring
- [docs/CERTIFICATE_MONITORING.md](CERTIFICATE_MONITORING.md) -- TLS certificate probing
- [docs/FLEET_ONBOARDING.md](FLEET_ONBOARDING.md) -- Adding servers with agents
- [ARCHITECTURE.md](../ARCHITECTURE.md) -- Overall system design
