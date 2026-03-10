# SNMP Network Device Monitoring

## Overview

This document covers the end-to-end SNMP monitoring pipeline in the Enterprise Monitoring and Dashboarding Platform. The platform uses a **two-tier approach** to capture both structured metrics and event-driven data from network infrastructure:

1. **SNMP Polling (Metrics)** -- The Alloy site gateway embeds an `snmp_exporter` component that actively polls devices on UDP 161 at regular intervals. This produces time-series metrics (interface counters, device health, resource utilization) that flow into Prometheus for alerting and dashboarding.

2. **SNMP Trap Ingestion (Events/Logs)** -- A `snmptrapd` sidecar listens for asynchronous trap notifications on UDP 162. Traps are reformatted as structured syslog messages and forwarded through Alloy into Loki, where they serve as an event log for link state changes, device reboots, authentication failures, and vendor-specific notifications.

The two tiers are complementary. Polling provides continuous visibility into device state and performance trends, while traps provide immediate notification of discrete events that occur between polling intervals.

---

## Architecture

### Metrics Path (SNMP Polling)

```
+------------------+        UDP 161 (poll)        +---------------------+       remote_write       +----------------+
|  Network Device  | <--------------------------- |  Alloy Site Gateway | ---------------------> |   Prometheus   |
|  (switch, FW,    |  SNMP GET/WALK responses  -> |  (snmp_exporter)    |                        |   (central)    |
|   AP, UPS, NAS)  |                               +---------------------+                        +----------------+
+------------------+
```

The gateway initiates outbound SNMP requests to each device. Devices never need to reach the gateway for this path -- the gateway drives all communication. This is important because it means SNMP polling works through NAT boundaries as long as the gateway can reach the device management interface.

### Event Path (SNMP Traps)

```
+------------------+    UDP 162 (trap)    +-------------+   syslog UDP 1514   +---------------------+    push    +--------+
|  Network Device  | ------------------> |  snmptrapd   | ------------------> |  Alloy Site Gateway | ---------> |  Loki  |
+------------------+                      +-------------+                      |  (syslog receiver)  |            +--------+
                                                                               +---------------------+
```

Traps are asynchronous -- the device pushes them when an event occurs. The `snmptrapd` daemon receives them, translates OIDs (if MIBs are available), and emits a structured syslog line that Alloy parses and ships to Loki.

### Deployment Topology

- **One gateway per site or datacenter.** Keeping SNMP traffic local avoids polling over WAN links, which introduces latency, packet loss, and unreliable counter deltas. Each site gateway handles its own device fleet and forwards aggregated metrics/logs to the central stack.
- **Gateway runs as a container** in either Docker Compose (for smaller sites) or as a Kubernetes pod (for sites with existing K8s infrastructure).

---

## Supported Device Types

The following device types are supported out of the box. Each maps to one or more SNMP exporter modules that define which OIDs to collect.

| Device Type      | Examples                     | SNMP Modules Used                  | Notes                                                        |
|------------------|------------------------------|------------------------------------|--------------------------------------------------------------|
| Switches         | Cisco Catalyst, Aruba CX     | `system`, `if_mib`                 | Core use case -- interface counters and link status           |
| Firewalls        | Palo Alto PA-series           | `system`, `if_mib`, `paloalto`     | Enterprise MIB provides session/threat metrics                |
| Access Points    | Ubiquiti UniFi                | `system`, `if_mib`, `ubiquiti_unifi` | Client counts and RF quality metrics                        |
| UPS              | APC Smart-UPS                 | `system`, `apcups`                 | Battery health, load, and runtime remaining                  |
| NAS              | Synology, QNAP               | `system`, `if_mib`                 | Standard MIBs; vendor MIBs can be added for disk/volume stats |

---

## Adding SNMP Devices

### Step 1: Verify SNMP Access

Before adding a device to the monitoring config, confirm that the gateway host can reach the device over SNMP. This catches network-level issues (firewall rules, ACLs, wrong community strings) before they become silent collection failures.

**SNMPv2c:**

```bash
snmpwalk -v2c -c <community> <device_ip> sysDescr
```

**SNMPv3:**

```bash
snmpwalk -v3 -l authPriv -u <user> -a SHA -A <authpass> -x AES -X <privpass> <device_ip> sysDescr
```

A successful response returns the device description string. If the command hangs or returns "Timeout", the issue is network connectivity or credentials -- resolve this before proceeding.

### Step 2: Configure Authentication

Edit `configs/alloy/gateway/snmp_auths.yml` to define the authentication profile the gateway will use when polling the device.

**SNMPv2c example (legacy devices only):**

```yaml
# SNMPv2c uses a "community string" as a shared secret. It is transmitted
# in cleartext on every request, which is why v3 is strongly preferred.
community_v2:
  version: 2
  community: "monitoring-ro"
```

**SNMPv3 example (recommended for production):**

```yaml
# SNMPv3 provides authentication (verifies identity via HMAC) and privacy
# (encrypts the payload via AES). This prevents credential sniffing and
# protects device data in transit -- both required by most compliance
# frameworks (PCI-DSS, HIPAA, SOC2).
secure_v3:
  version: 3
  security_level: "authPriv"
  username: "monitor_user"
  auth_protocol: "SHA"
  auth_passphrase: "${SNMP_AUTH_PASS}"
  priv_protocol: "AES"
  priv_passphrase: "${SNMP_PRIV_PASS}"
```

SNMPv3 is recommended for all production environments. SNMPv2c community strings are sent in cleartext with every packet, making them trivially interceptable on shared network segments. SNMPv3 provides both authentication (SHA/SHA256 HMAC) and encryption (AES128/AES256), ensuring that credentials cannot be sniffed and device data cannot be read in transit.

### Step 3: Add Targets to Site Gateway

Edit `configs/alloy/gateway/site_gateway.alloy` to add the device as a scrape target. Each target block defines the device address, the SNMP modules to poll, and metadata labels used for filtering in dashboards and alerts.

```alloy
targets = [
  {
    "__address__"     = "snmp_exporter:9116",
    "__param_target"  = "10.1.50.10",
    "module"          = "system,if_mib",
    "auth"            = "secure_v3",

    // Labels attached to every metric from this device. These drive
    // dashboard filtering and alert routing -- use consistent values.
    "device_type"     = "switch",
    "vendor"          = "cisco",
    "device_name"     = "core-sw-01",
    "site"            = "dc-east",
  },
]
```

**Label definitions:**

| Label         | Purpose                                                                 |
|---------------|-------------------------------------------------------------------------|
| `__address__` | The SNMP exporter endpoint (usually the embedded exporter in Alloy)      |
| `__param_target` | The management IP of the network device being polled                |
| `module`      | Comma-separated list of SNMP modules defining which OID trees to walk   |
| `auth`        | Name of the authentication profile from `snmp_auths.yml`                |
| `device_type` | Classification: `switch`, `firewall`, `ap`, `ups`, `nas`                |
| `vendor`      | Manufacturer name for vendor-specific dashboard filtering               |
| `device_name` | Human-readable hostname used in alert notifications and dashboards      |
| `site`        | Site/datacenter identifier for geographic aggregation                   |

### Step 4: Verify Collection

After reloading the gateway configuration:

1. **Check Alloy UI** at `http://gateway:12345` -- the SNMP component should show the new target in a healthy state with recent scrape timestamps.

2. **Verify target is up** in Prometheus:

   ```promql
   up{job="snmp", instance="<device_ip>"}
   ```

   A value of `1` confirms successful SNMP communication.

3. **Confirm data flow** with a basic metric query:

   ```promql
   sysUpTime{instance="<device_ip>"}
   ```

   This returns the device uptime in hundredths of a second. If the value is present and increasing, the full pipeline is operational.

---

## SNMP Modules Reference

### system Module

The `system` module polls the SNMPv2-MIB system group, which is implemented by virtually every SNMP-capable device regardless of vendor.

| OID Object    | Metric / Label   | Use Case                                                      |
|---------------|------------------|---------------------------------------------------------------|
| `sysUpTime`   | `sysUpTime`      | Device uptime; resets indicate reboots                        |
| `sysName`     | label            | Hostname as configured on the device                          |
| `sysDescr`    | label            | Software version and hardware model string                    |
| `sysLocation` | label            | Physical location (if configured on device)                   |
| `sysContact`  | label            | Administrative contact (if configured on device)              |

This module serves two purposes: device inventory (populating dashboards with device metadata) and reboot detection (alerting when `sysUpTime` resets to a low value).

### if_mib Module

The `if_mib` module polls the IF-MIB interface table. This is the primary source of network traffic metrics.

| OID Object        | Metric                | Description                                                                                   |
|-------------------|-----------------------|-----------------------------------------------------------------------------------------------|
| `ifHCInOctets`    | `ifHCInOctets`        | Total bytes received on the interface (64-bit counter)                                        |
| `ifHCOutOctets`   | `ifHCOutOctets`       | Total bytes transmitted on the interface (64-bit counter)                                     |
| `ifOperStatus`    | `ifOperStatus`        | Current operational state: 1=up, 2=down, 3=testing                                           |
| `ifAdminStatus`   | `ifAdminStatus`       | Configured administrative state: 1=up, 2=down                                                |
| `ifInErrors`      | `ifInErrors`          | Count of inbound packets with errors (CRC, framing, etc.)                                    |
| `ifOutErrors`     | `ifOutErrors`         | Count of outbound packets with errors                                                        |
| `ifInDiscards`    | `ifInDiscards`        | Count of inbound packets discarded (buffer overflows, QoS drops)                              |
| `ifOutDiscards`   | `ifOutDiscards`       | Count of outbound packets discarded                                                           |
| `ifSpeed`         | `ifSpeed`             | Interface speed in bits per second (used for utilization calculation)                         |

**Why HC (High Capacity) counters:** The standard 32-bit counters (`ifInOctets`, `ifOutOctets`) wrap at approximately 4.3 GB. On a 10 Gbps link running at full capacity, a 32-bit counter wraps every 3.4 seconds, making rate calculations meaningless. The 64-bit HC counters (`ifHCInOctets`, `ifHCOutOctets`) do not wrap under any realistic traffic volume, so they are the only reliable source for traffic rate calculations on modern networks.

### paloalto Module

The `paloalto` module polls the PAN-COMMON-MIB and PAN-TRAPS-MIB enterprise OID trees specific to Palo Alto Networks firewalls.

| Metric Category         | Examples                                          | Use Case                                         |
|-------------------------|---------------------------------------------------|--------------------------------------------------|
| Session counts          | Active sessions, session utilization percentage   | Capacity planning and session table exhaustion    |
| Throughput              | Firewall throughput in bytes/sec                  | Verifying hardware is not bottlenecking traffic   |
| Threat detection        | Threat count by severity, virus/spyware detections | Security operations correlation                  |

### ubiquiti_unifi Module

The `ubiquiti_unifi` module polls UniFi-specific OIDs from Ubiquiti access points.

| Metric Category         | Examples                                          | Use Case                                         |
|-------------------------|---------------------------------------------------|--------------------------------------------------|
| Client counts           | Connected clients per radio band                  | Capacity planning and load balancing              |
| Channel utilization     | Percentage of airtime consumed                    | RF environment health                             |
| Signal quality          | Average client RSSI, noise floor                  | Coverage gap identification                       |

### apcups Module

The `apcups` module polls the PowerNet-MIB from APC/Schneider Electric UPS devices.

| Metric Category         | Examples                                          | Use Case                                          |
|-------------------------|---------------------------------------------------|---------------------------------------------------|
| Battery status          | Battery charge %, estimated runtime remaining     | Alerting before battery depletion during outage    |
| Input/output voltage    | Line voltage, output voltage                      | Power quality monitoring                           |
| Load                    | Output load percentage                            | Capacity planning; overloaded UPS risks shutdown   |
| Temperature             | Internal UPS temperature                          | Environmental monitoring                           |

---

## Recording Rules

Recording rules pre-compute frequently used expressions to reduce query latency and enable efficient aggregation across large device fleets.

### Interface-Level (snmp_interface_rules)

| Recording Rule Metric                    | Description                                                    | Source Counters                        |
|------------------------------------------|----------------------------------------------------------------|----------------------------------------|
| `snmp:interface:traffic_in_bps`          | Inbound traffic rate in bits per second                        | `rate(ifHCInOctets[5m]) * 8`           |
| `snmp:interface:traffic_out_bps`         | Outbound traffic rate in bits per second                       | `rate(ifHCOutOctets[5m]) * 8`          |
| `snmp:interface:utilization_in_pct`      | Inbound utilization as percentage of link speed                | `traffic_in_bps / ifSpeed * 100`       |
| `snmp:interface:utilization_out_pct`     | Outbound utilization as percentage of link speed               | `traffic_out_bps / ifSpeed * 100`      |
| `snmp:interface:errors_in_rate`          | Inbound error rate per second                                  | `rate(ifInErrors[5m])`                 |
| `snmp:interface:errors_out_rate`         | Outbound error rate per second                                 | `rate(ifOutErrors[5m])`                |
| `snmp:interface:discards_in_rate`        | Inbound discard rate per second                                | `rate(ifInDiscards[5m])`               |
| `snmp:interface:discards_out_rate`       | Outbound discard rate per second                               | `rate(ifOutDiscards[5m])`              |

### Site-Level Aggregations (snmp_site_rules)

| Recording Rule Metric                        | Description                                                    | Aggregation                                              |
|----------------------------------------------|----------------------------------------------------------------|----------------------------------------------------------|
| `snmp:site:device_count`                     | Total number of SNMP-monitored devices per site                | `count by (site) (up{job="snmp"})`                       |
| `snmp:site:device_down_count`                | Number of unreachable devices per site                         | `count by (site) (up{job="snmp"} == 0)`                  |
| `snmp:site:interface_high_utilization_count` | Interfaces exceeding 85% utilization per site                  | `count by (site) (utilization > 85)`                     |
| `snmp:site:interface_error_count`            | Interfaces with active errors per site                         | `count by (site) (error_rate > 0)`                       |

---

## Alert Rules

### Device Health Alerts

| Alert Name              | Condition                             | Duration | Severity   | Description                                                         |
|-------------------------|---------------------------------------|----------|------------|---------------------------------------------------------------------|
| `SNMPDeviceUnreachable` | `up{job="snmp"} == 0`                 | 5m       | CRITICAL   | Device has not responded to SNMP polls for 5 minutes. Indicates device failure, network partition, or credential misconfiguration. |
| `SNMPDeviceReboot`      | `sysUpTime` reset detected within 10m | 10m      | WARNING    | Device uptime counter reset, indicating an unexpected reboot. Correlate with change management records. |

### Interface Health Alerts

| Alert Name                       | Condition                                                    | Duration | Severity   | Description                                                                                          |
|----------------------------------|--------------------------------------------------------------|----------|------------|------------------------------------------------------------------------------------------------------|
| `SNMPInterfaceDown`              | `ifOperStatus == 2 AND ifAdminStatus == 1`                   | 5m       | WARNING    | Interface is operationally down but administratively enabled.                                        |
| `SNMPInterfaceHighUtilization`   | `snmp:interface:utilization > 85%`                           | 15m      | WARNING    | Interface sustained above 85% utilization. Indicates capacity pressure.                              |
| `SNMPInterfaceSaturated`         | `snmp:interface:utilization > 95%`                           | 5m       | CRITICAL   | Interface near wire-rate. Packet loss is likely occurring.                                           |
| `SNMPInterfaceErrors`            | `snmp:interface:errors_rate > 1`                             | 10m      | WARNING    | Interface experiencing sustained errors. Possible cable fault, duplex mismatch, or failing hardware. |

**Why the `ifAdminStatus == 1` filter matters for `SNMPInterfaceDown`:** Without this filter, every intentionally shutdown port on every switch would fire an alert. Network operators routinely disable unused ports as a security practice. The admin-enabled filter ensures alerts only fire for ports that *should* be up but are not -- the actual operational concern.

---

## SNMPv3 Configuration

### Why SNMPv3

SNMPv2c relies on a "community string" that functions as a password, but it is transmitted in cleartext with every SNMP packet. Any host on the same network segment (or any device in the path) can capture these strings with a packet sniffer. In many environments, the community string also grants write access, making interception a direct security risk.

SNMPv3 addresses this with two mechanisms:

- **Authentication (auth):** Uses HMAC with SHA or SHA-256 to verify that requests come from a legitimate management station. Prevents spoofing and replay attacks.
- **Privacy (priv):** Uses AES-128 or AES-256 to encrypt the SNMP payload. Prevents eavesdropping on device configuration and performance data.

Most security compliance frameworks (PCI-DSS, HIPAA, SOC 2, NIST 800-53) either require or strongly recommend SNMPv3 with `authPriv` level for network device monitoring.

### Authentication Profiles

The `configs/alloy/gateway/snmp_auths.yml` file defines named authentication profiles that targets reference by name. This decouples credentials from target definitions, allowing credential rotation without editing every target block.

```yaml
# Legacy profile for devices that do not support SNMPv3.
# Schedule these devices for firmware upgrade to enable v3 support.
community_v2:
  version: 2
  community: "${SNMP_COMMUNITY}"

# Production profile for all SNMPv3-capable devices.
# Uses authPriv: both authentication and encryption are active.
secure_v3:
  version: 3
  security_level: "authPriv"
  username: "monitor_user"
  auth_protocol: "SHA"
  auth_passphrase: "${SNMP_AUTH_PASS}"
  priv_protocol: "AES"
  priv_passphrase: "${SNMP_PRIV_PASS}"
```

**Per-device auth override:** If a specific device uses different credentials (common during migration from v2c to v3), define an additional profile and reference it in that device's target block via the `auth` label. This avoids the need for a single set of credentials across all devices.

### Device-Side Configuration

SNMPv3 must be configured on both the monitoring platform (above) and on each network device. The following are abbreviated examples -- consult vendor documentation for complete syntax.

**Cisco IOS / IOS-XE:**

```
snmp-server group MONITOR v3 priv
snmp-server user monitor_user MONITOR v3 auth sha <authpass> priv aes 128 <privpass>
snmp-server view MONITOR-VIEW iso included
```

**Palo Alto PAN-OS:**

Navigate to Device > Setup > Operations > SNMP Setup. Configure an SNMPv3 user with Auth (SHA) and Privacy (AES) settings matching the `snmp_auths.yml` profile.

**Generic devices:**

Consult vendor documentation for SNMPv3 user, group, and view configuration. The key parameters to match are: username, authentication protocol (SHA), authentication passphrase, privacy protocol (AES), and privacy passphrase.

---

## SNMP Trap Ingestion

### Architecture

The trap ingestion pipeline converts asynchronous device notifications into searchable log entries:

1. **snmptrapd** listens on UDP 162 (the IANA-assigned SNMP trap port). It receives trap PDUs from network devices and formats each trap as a single structured syslog line containing the source IP, trap OID, variable bindings, and timestamp.

2. **Alloy syslog receiver** listens on UDP 1514 (a non-privileged port to avoid running Alloy as root). It parses the syslog messages, extracts labels (source device, trap type, severity), and pushes the entries to Loki.

3. **Loki** stores trap logs with the label `job="snmp_traps"`, making them queryable via LogQL in Grafana dashboards and alert rules.

### Trap Types Classified

The following are the standard SNMP trap types defined in RFC 3418. Devices may also send enterprise-specific traps (type 6) with vendor-defined OIDs.

| Trap Type | Generic Trap ID | Description                                                          | Typical Use                                   |
|-----------|-----------------|----------------------------------------------------------------------|-----------------------------------------------|
| coldStart | 0               | Device completed a cold boot (full reinitialization)                 | Unexpected reboot detection                   |
| warmStart | 1               | Device completed a warm restart (software reload only)               | Planned restart confirmation                  |
| linkDown  | 2               | An interface transitioned to operationally down                      | Cable pulls, port failures, upstream outages  |
| linkUp    | 3               | An interface transitioned to operationally up                        | Recovery confirmation                         |
| authenticationFailure | 4  | SNMP request received with invalid credentials                      | Security monitoring, brute-force detection    |
| egpNeighborLoss | 5        | EGP neighbor relationship lost (legacy, rarely seen)                 | BGP/routing issues on older devices           |
| enterpriseSpecific | 6     | Vendor-defined trap with enterprise OID                              | Vendor-specific events (fan failure, etc.)    |

### Configuring Devices to Send Traps

On each network device, configure the following:

1. **Trap destination:** Set the gateway IP address and port 162 as the trap receiver (often called "trap host" or "notification receiver" in device configuration).

2. **Community string:** Configure the trap community string to match the value in the `snmptrapd.conf` file on the gateway. For SNMPv3, configure an SNMP notify target with matching credentials.

3. **Trap types:** Enable the specific trap types relevant to your monitoring needs. The most operationally useful traps are:
   - `linkDown` / `linkUp` -- immediate notification of interface state changes
   - `authenticationFailure` -- security monitoring for unauthorized SNMP access attempts
   - `coldStart` -- unexpected device reboots

### Grafana Alert Rules on Traps

Trap-based alerts use LogQL queries against Loki rather than PromQL against Prometheus. These alerts are configured in Grafana's alerting system.

| Alert Name                  | LogQL Query Pattern                                                        | Severity | Description                                                        |
|-----------------------------|----------------------------------------------------------------------------|----------|--------------------------------------------------------------------|
| SNMP Link Down              | `{job="snmp_traps"} \| json \| trap_type="linkDown"`                      | WARNING  | Interface went down on a monitored device                          |
| SNMP Auth Failure Burst     | `count_over_time({job="snmp_traps"} \| json \| trap_type="authenticationFailure" [5m]) > 5` | WARNING | Repeated authentication failures may indicate brute-force attempts |
| SNMP Cold Start             | `{job="snmp_traps"} \| json \| trap_type="coldStart"`                     | WARNING  | Device rebooted unexpectedly                                       |
| SNMP Trap Storm             | `count_over_time({job="snmp_traps"} [10m]) > 50`                          | WARNING  | High trap volume indicates network instability or flapping         |

### MIB Files (Optional)

MIB files provide the mapping between numeric OIDs and human-readable names:

- **Without MIBs:** Trap OIDs appear as numeric strings (e.g., `1.3.6.1.6.3.1.1.5.3`). The trap is still captured and searchable, but operators must look up OIDs manually.
- **With MIBs:** OIDs are translated to descriptive names (e.g., `IF-MIB::linkDown`). This significantly improves readability in dashboards and log searches.

To enable MIB translation, mount vendor MIB files into the snmptrapd container at `/usr/share/snmp/mibs/`. The `snmptrapd` process loads MIBs at startup and uses them to translate OIDs in trap output.

---

## Custom Vendor MIBs

### Adding Custom Modules

When the built-in modules do not cover a device's vendor-specific OIDs, you can generate custom snmp_exporter modules:

1. **Obtain MIB files** from the device vendor. These are typically downloadable from the vendor's support portal or included in the device firmware package.

2. **Generate the snmp_exporter module** using the `snmp_exporter` generator tool:

   ```bash
   # The generator reads MIB files and produces a module definition
   # that tells the exporter which OIDs to walk and how to map them to metrics.
   ./generator generate --module-name=custom_vendor --mibs=/path/to/vendor-mibs/
   ```

3. **Add the generated module** to the SNMP exporter configuration in `site_gateway.alloy`. The module defines the OID tree walk targets and metric type mappings.

4. **Reference the module** in the target's `module` label list (e.g., `"module" = "system,if_mib,custom_vendor"`).

### Common Vendor MIB Sources

| Vendor         | MIB Source                                                          |
|----------------|---------------------------------------------------------------------|
| Cisco          | cisco.com/public/sw-center/netmgmt/cmtk/mibs.shtml                 |
| HP / Aruba     | support.hpe.com (search for "MIB files" under networking)           |
| Palo Alto      | PAN-MIB included in PAN-OS documentation and support portal         |

---

## Deployment

### Docker Compose

The site gateway and snmptrapd run as services in a Docker Compose stack. This is the recommended deployment model for sites without Kubernetes infrastructure.

Key configuration points:

- **SNMP exporter configuration** is mounted from the host into the gateway container.
- **snmptrapd** runs as a sidecar service in the same Docker network, sharing the network namespace with the gateway for syslog forwarding.
- **Port mappings:**
  - `161/udp` -- Outbound SNMP polling. The gateway initiates connections to devices on this port. Not technically a published port (the gateway connects outward), but firewall rules must allow outbound UDP 161 from the gateway host.
  - `162/udp` -- Inbound trap reception. This port must be published and reachable from managed devices.

### Kubernetes (Helm)

For sites with Kubernetes infrastructure, the gateway deploys as a pod with snmptrapd as a sidecar container:

- **Pod structure:** Single pod with two containers (Alloy gateway + snmptrapd sidecar). They share the pod network and communicate via localhost on UDP 1514.
- **ConfigMap:** Contains `snmptrapd.conf` and `snmp_auths.yml`. Sensitive values (passphrases) should be stored in a Secret resource and referenced via environment variables.
- **Service:** A UDP Service exposes port 162 for trap ingestion. Use `NodePort` or `LoadBalancer` type depending on network topology. Standard ClusterIP services do not support UDP well in many CNI implementations -- test thoroughly.
- **NetworkPolicy:** Allow outbound UDP 161 from the gateway pod to the device management VLAN CIDR. Restrict inbound UDP 162 to known device management subnets to prevent unauthorized trap injection.

### Network Requirements

| Direction          | Protocol | Port    | From                  | To                       | Purpose                                |
|--------------------|----------|---------|-----------------------|--------------------------|-----------------------------------------|
| Outbound           | UDP      | 161     | Monitoring gateway    | Device management IPs    | SNMP polling (GET/WALK requests)        |
| Inbound            | UDP      | 162     | Device management IPs | Monitoring gateway       | SNMP trap reception                     |
| Internal           | UDP      | 1514    | snmptrapd             | Alloy syslog receiver    | Trap-to-syslog forwarding (pod-local)   |

In most enterprise networks, the monitoring stack and device management interfaces reside on separate VLANs. Firewall rules or ACLs must explicitly permit the traffic described above. The monitoring VLAN typically needs a route to the management VLAN, and the management VLAN needs a return route for trap delivery.

---

## Dashboard Integration

SNMP metrics and trap logs integrate into the following Grafana dashboards:

- **Network Infrastructure dashboard (`network-overview`):** Provides per-device and per-interface visibility. Includes an interface status grid (color-coded by operational state), traffic rate charts (in/out bps), utilization heatmaps (highlighting hotspots across the device fleet), and error/discard trend panels.

- **Enterprise NOC dashboard:** Aggregates device health at the site level using the `snmp_site_rules` recording rules. Shows device counts, down device counts, and high-utilization interface counts per site. Designed for wall-mounted NOC displays.

- **Network dashboard SNMP Trap Log row:** Embedded within the network dashboard, this row contains a trap event viewer (log panel querying `{job="snmp_traps"}`) and a trap volume chart (rate of traps over time). The event viewer supports filtering by device, trap type, and time range.

---

## Troubleshooting

### Device Not Appearing

If a device is configured but no metrics appear in Prometheus:

1. **Verify SNMP access from the gateway host.** SSH into the gateway host (or exec into the container) and run `snmpwalk` against the device. If this fails, the issue is network-level or credential-related, not a monitoring platform issue.

   ```bash
   snmpwalk -v2c -c <community> <device_ip> sysDescr
   ```

2. **Check community string or SNMPv3 credentials.** A common failure mode is a typo in the community string or a passphrase mismatch between the monitoring config and the device config. SNMPv3 failures are silent -- the device simply does not respond.

3. **Verify network path.** Check firewall rules, ACLs, and routing between the monitoring gateway and the device management interface. SNMP uses UDP, so there are no connection-level errors -- packets are silently dropped if blocked.

4. **Check Alloy logs for scrape errors.** The Alloy gateway logs include scrape results for each target. Look for timeout or authentication error messages:

   ```bash
   docker logs alloy-gateway 2>&1 | grep -i "snmp"
   ```

### No Trap Data

If traps are not appearing in Loki:

1. **Verify snmptrapd is running and listening.** Confirm the process is active and bound to UDP 162:

   ```bash
   ss -ulnp | grep 162
   ```

2. **Send a test trap** from the gateway host to confirm the pipeline end-to-end:

   ```bash
   snmptrap -v2c -c public localhost "" .1.3.6.1.6.3.1.1.5.3
   ```

   This sends a linkDown trap to localhost. If it appears in Loki, the pipeline is functional and the issue is device-to-gateway connectivity.

3. **Check Alloy syslog receiver logs.** Verify that Alloy is receiving syslog messages from snmptrapd on UDP 1514.

4. **Query Loki directly** to confirm trap data is being stored:

   ```logql
   {job="snmp_traps"} | limit 10
   ```

### High Scrape Duration

If SNMP scrapes are taking longer than expected or timing out:

- **SNMP walks over WAN links are inherently slow.** Each SNMP GETNEXT request is a separate UDP round-trip. A walk of 1000 OIDs over a 100ms latency link takes at minimum 100 seconds. This is the primary reason for deploying a gateway per site -- keeping SNMP traffic on the local LAN.

- **Reduce module scope.** Do not walk all available OIDs on every device. If a device only needs interface monitoring, use `module = "system,if_mib"` rather than including vendor-specific modules that walk large OID trees.

- **Increase scrape_timeout if needed.** Some devices with large interface tables (e.g., chassis switches with 400+ ports) require longer scrape windows. A maximum of 30 seconds is recommended -- beyond that, the device is likely overloaded or the network path is too slow for reliable monitoring.

- **Consider dedicated gateways per site** to keep SNMP traffic on local network segments. This eliminates WAN latency from the scrape path and reduces the blast radius of gateway failures.

---

## Related Documentation

- [docs/SNMP_TRAPS.md](SNMP_TRAPS.md) -- Detailed trap pipeline setup and snmptrapd configuration
- [docs/ALERT_RUNBOOKS.md](ALERT_RUNBOOKS.md) -- Alert investigation procedures for SNMP and other alert types
- [ARCHITECTURE.md](../ARCHITECTURE.md) -- Overall system design and component relationships
