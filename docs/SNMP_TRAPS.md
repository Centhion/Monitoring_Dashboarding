# SNMP Trap Pipeline

## Overview

The monitoring platform can receive SNMP traps from network devices and ingest them into Loki for log-based alerting and visualization. This complements the polling-based SNMP monitoring (Phase 7A) with event-driven trap data.

## Architecture

```
Network Device (switch, firewall, UPS)
  |-- Sends SNMP trap to snmptrapd (UDP 162)
  |
snmptrapd (sidecar container)
  |-- Authenticates trap (community string or SNMPv3)
  |-- Formats trap data as structured syslog message
  |-- Forwards to Alloy syslog receiver (UDP 1514)
  |
Alloy (role_snmp_traps.alloy)
  |-- Receives syslog via loki.source.syslog
  |-- Extracts labels: source_ip, trap_oid, trap_type
  |-- Adds static labels: datacenter, environment, log_type=snmp_trap
  |-- Forwards to Loki
  |
Loki
  |-- Stores trap log entries with labels
  |-- Grafana alerting rules query for critical trap patterns
  |
Grafana Alerting (snmp_trap_alerts.yml)
  |-- LogQL metric queries detect: linkDown, authFailure, coldStart
  |-- Routes through standard notification policies
```

## Deployment

### Docker Compose

Add the snmptrapd sidecar to the Docker Compose stack:

```yaml
snmptrapd:
  image: net-snmp/net-snmp:latest
  container_name: mon-snmptrapd
  restart: unless-stopped
  ports:
    - "162:162/udp"
  volumes:
    - ../../configs/snmptrapd/snmptrapd.conf:/etc/snmp/snmptrapd.conf:ro
  networks:
    - monitoring
```

### Kubernetes

In Kubernetes, snmptrapd runs as a sidecar container in the Alloy gateway pod:

```yaml
containers:
  - name: snmptrapd
    image: net-snmp/net-snmp:latest
    ports:
      - containerPort: 162
        protocol: UDP
    volumeMounts:
      - name: snmptrapd-config
        mountPath: /etc/snmp/snmptrapd.conf
        subPath: snmptrapd.conf
```

## Device Configuration

Each network device must be configured to send traps to the snmptrapd host:

### Cisco IOS
```
snmp-server host <monitoring-ip> version 2c <community> udp-port 162
snmp-server enable traps
```

### Palo Alto PAN-OS
```
set deviceconfig system snmp-setting snmp-system trap-server <name> server <monitoring-ip>
set deviceconfig system snmp-setting snmp-system trap-server <name> community <community>
```

### Generic SNMPv2c
Most devices have a "trap destination" or "SNMP manager" setting in their management UI. Configure:
- **Destination IP**: The host running snmptrapd
- **Port**: 162 (UDP)
- **Community**: Must match `snmptrapd.conf`
- **Trap types**: Enable all or select specific trap categories

## Alert Rules

Grafana alerting rules (`alerts/grafana/snmp_trap_alerts.yml`) fire on critical trap patterns:

| Alert | Trigger | Severity |
|-------|---------|----------|
| SNMP Trap: Link Down | `linkDown` trap received | Warning |
| SNMP Trap: Authentication Failure | `authenticationFailure` trap | Warning |
| SNMP Trap: Device Cold Start | `coldStart` trap (device rebooted) | Critical |
| SNMP Trap: High Volume | >50 traps from one device in 10 minutes | Warning |

## Common Trap OIDs

| OID | Name | Description |
|-----|------|-------------|
| 1.3.6.1.6.3.1.1.5.1 | coldStart | Device powered on or restarted |
| 1.3.6.1.6.3.1.1.5.2 | warmStart | Device software restarted |
| 1.3.6.1.6.3.1.1.5.3 | linkDown | Network interface went down |
| 1.3.6.1.6.3.1.1.5.4 | linkUp | Network interface came back up |
| 1.3.6.1.6.3.1.1.5.5 | authenticationFailure | Failed SNMP authentication |

## Adding Custom Trap Alerts

To alert on vendor-specific trap OIDs:

1. Identify the trap OID from the device vendor's MIB documentation
2. Add a new Grafana alert rule in `alerts/grafana/snmp_trap_alerts.yml`:
   ```yaml
   - uid: snmp-trap-custom
     title: "SNMP Trap: Custom Event"
     data:
       - refId: A
         datasourceUid: loki
         model:
           expr: 'count_over_time({job="snmp_traps", trap_oid="1.3.6.1.4.1.VENDOR.SPECIFIC.OID"} [5m])'
   ```
3. Deploy the updated alert rule via Grafana provisioning

## Troubleshooting

### No traps appearing in Loki
1. Verify snmptrapd is running: `docker logs mon-snmptrapd`
2. Test trap reception: `snmptrap -v2c -c public localhost '' .1.3.6.1.6.3.1.1.5.1`
3. Check Alloy syslog receiver is listening on UDP 1514
4. Verify network path from devices to snmptrapd (UDP 162)

### Traps received but no labels extracted
1. Check Alloy processing pipeline logs for regex parse errors
2. Verify the syslog message format matches the regex pattern in `role_snmp_traps.alloy`
3. Test with a known trap format using `snmptrap` CLI tool

## Configuration Files

| File | Purpose |
|------|---------|
| `configs/snmptrapd/snmptrapd.conf` | snmptrapd trap receiver configuration |
| `configs/alloy/gateway/role_snmp_traps.alloy` | Alloy syslog receiver and Loki forwarding |
| `alerts/grafana/snmp_trap_alerts.yml` | Grafana alerting rules for critical traps |
| `dashboards/network/network_overview.json` | Network dashboard with trap log panel |
