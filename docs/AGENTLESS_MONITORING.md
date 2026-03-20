# Agentless Monitoring Guide

## Overview

Some devices cannot run a local Alloy agent. Embedded firmware, vendor restrictions, and locked-down appliances all prevent agent installation. Agentless monitoring uses external probing from the site gateway to collect metrics and events from these targets.

## Collection Methods

| Method | Protocol | Best For | Detail |
|--------|----------|----------|--------|
| SNMP polling | UDP 161 | Switches, routers, firewalls, APs, UPS, NAS | [SNMP_MONITORING.md](SNMP_MONITORING.md) |
| SNMP traps | UDP 162 | Link-down events, auth failures, device reboots | [SNMP_TRAPS.md](SNMP_TRAPS.md) |
| Redfish API | HTTPS 443 | HPE iLO, Dell iDRAC, Lenovo XClarity, OpenBMC | [HARDWARE_MONITORING.md](HARDWARE_MONITORING.md) |
| Blackbox probing | ICMP/TCP/HTTP/DNS | Any device with a network interface or service port | [CERTIFICATE_MONITORING.md](CERTIFICATE_MONITORING.md) |
| WMI remoting | DCOM (TCP 135+) | Windows servers where agent cannot be installed | Not included in template |
| SSH collection | TCP 22 | Linux hosts where agent is restricted | Not included in template |

## Architecture

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

The site gateway acts as a proxy collector: polls targets using the appropriate protocol, enriches metrics with standard labels (`datacenter`, `environment`), and pushes to central Prometheus and Loki. This keeps protocol complexity at the gateway, centralizes credential management, and requires network access from only one host.

## Combining Methods for Full Coverage

| Device Type | Metrics (SNMP) | Hardware (Redfish) | Reachability (Probe) | Events (Traps) |
|------------|---------------|-------------------|---------------------|----------------|
| Network switch | Yes | -- | Yes (ICMP) | Yes |
| Firewall | Yes | -- | Yes (ICMP/HTTP) | Yes |
| Server (no agent) | -- | Yes (if BMC) | Yes (ICMP/TCP) | -- |
| UPS | Yes | -- | Yes (ICMP) | Yes |
| Web appliance | -- | -- | Yes (HTTP/HTTPS) | -- |

## Recommendation

Deploy Alloy agents where possible. Agentless monitoring is a complement for devices that genuinely cannot run agents, not a replacement for agent-based collection on servers.

## Related Documentation

- [SNMP_MONITORING.md](SNMP_MONITORING.md) -- SNMP device polling
- [SNMP_TRAPS.md](SNMP_TRAPS.md) -- Trap ingestion pipeline
- [HARDWARE_MONITORING.md](HARDWARE_MONITORING.md) -- Redfish BMC monitoring
- [CERTIFICATE_MONITORING.md](CERTIFICATE_MONITORING.md) -- TLS certificate probing
- [ALLOY_DEPLOYMENT.md](ALLOY_DEPLOYMENT.md) -- Agent-based alternative
