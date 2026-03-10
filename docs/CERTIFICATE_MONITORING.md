# SSL/TLS Certificate Monitoring

## Overview

This document describes the SSL/TLS certificate monitoring capabilities of the Enterprise Monitoring and Dashboarding Platform. Certificate monitoring provides proactive visibility into certificate expiry across both internal PKI infrastructure and public-facing services.

Key capabilities:

- Monitors certificate expiry for internal PKI and public certificates.
- Uses Alloy's embedded blackbox exporter for TLS probing.
- Supports HTTPS endpoints, raw TLS services (LDAPS, SMTP/TLS, SQL Server), and TCP services.
- Configurable alert thresholds: 90d (info), 30d (warning), 7d (critical), expired (critical).

---

## Architecture

Alloy's embedded blackbox exporter performs a TLS handshake against each target endpoint, extracts the certificate chain, and reports the earliest expiry timestamp as a Prometheus metric. Recording rules convert the raw Unix timestamp into a days-remaining gauge for human-readable alerting and dashboard display.

Each site runs one certificate monitor instance, typically deployed on the site gateway or a dedicated monitoring role. This keeps TLS probing local to the network segment where the monitored services reside, avoiding cross-site firewall complexity.

```
[Alloy Gateway]
    |
    +-- blackbox exporter (embedded)
    |       |
    |       +-- TLS handshake --> target endpoint
    |       |
    |       +-- probe_ssl_earliest_cert_expiry metric
    |
    +-- recording rules --> instance:cert_days_remaining:gauge
    |
    +-- alert rules --> TLSCertExpiring*, TLSCertExpired, TLSCertProbeFailure
```

---

## Probe Modules

### https_cert_check

For public-facing HTTPS endpoints with valid CA-signed certificates. Performs full TLS chain validation and will fail if the chain is broken or untrusted.

**Best for:** Public websites, customer portals, APIs with publicly trusted certificates.

### https_cert_check_internal

For internal HTTPS services using private PKI (enterprise CA). By default, uses `insecure_skip_verify: true` to bypass chain validation against the system trust store. Alternatively, mount the internal CA bundle for full validation.

**Best for:** Internal admin portals, monitoring UIs, internal APIs behind enterprise CA.

### tcp_tls_cert_check

For non-HTTP TLS services. Opens a raw TCP connection, performs a TLS handshake, and extracts certificate data without sending any HTTP protocol frames.

**Best for:**

| Service        | Typical Port |
|----------------|--------------|
| LDAPS          | 636          |
| SMTP/TLS       | 465, 587     |
| SQL Server     | 1433         |
| Kafka          | 9093         |
| PostgreSQL     | 5432         |
| RDP            | 3389         |

### Reachability Probes (Non-Certificate)

These modules do not extract certificate data but are included in the same probing framework for convenience:

| Module              | Purpose                                   |
|---------------------|-------------------------------------------|
| `icmp_check`        | ICMP ping for host reachability           |
| `tcp_check`         | TCP port connectivity (no TLS)            |
| `udp_dns_check`     | DNS resolution validation                 |
| `http_synthetic`    | HTTP GET with status code validation      |
| `http_post_synthetic` | HTTP POST with JSON body                |

---

## Adding Endpoints to Monitor

### Step 1: Choose the Right Module

| Endpoint Type      | Protocol | Certificate Type | Module                       |
|--------------------|----------|------------------|------------------------------|
| Public website     | HTTPS    | CA-signed        | `https_cert_check`           |
| Internal portal    | HTTPS    | Private PKI      | `https_cert_check_internal`  |
| Domain controller  | LDAPS    | Private PKI      | `tcp_tls_cert_check`         |
| Mail server        | SMTP/TLS | CA-signed        | `tcp_tls_cert_check`         |
| Database           | TLS      | Private PKI      | `tcp_tls_cert_check`         |

### Step 2: Add Target

Edit `configs/alloy/roles/role_cert_monitor.alloy` or `configs/alloy/certs/endpoints.yml`.

For HTTPS endpoints:

```
target {
  name    = "portal-prod"
  address = "https://portal.example.com"
  module  = "https_cert_check"
  labels  = {
    datacenter  = "site-alpha"
    environment = "prod"
    cert_type   = "public"
    service     = "Customer Portal"
    owner       = "web-team"
  }
}
```

For TCP/TLS services (use `host:port` format with no protocol prefix):

```
target {
  name    = "ldaps-dc01"
  address = "dc01.corp.example.com:636"
  module  = "tcp_tls_cert_check"
  labels  = {
    datacenter  = "site-alpha"
    environment = "prod"
    cert_type   = "pki"
    service     = "LDAPS (DC01)"
    owner       = "ad-team"
  }
}
```

### Step 3: Label Best Practices

- **cert_type**: `"public"` or `"pki"` -- enables filtering by certificate authority type and controls alert routing.
- **owner**: Team responsible for certificate renewal -- used in Alertmanager routing to direct notifications to the correct channel.
- **service**: Human-readable service name displayed in dashboards and alert notifications.

### Step 4: Verify Monitoring

After adding a target, verify it is being scraped and producing metrics:

1. **Probe success:** `probe_success{job="cert_monitor", instance="portal.example.com"}` should return `1`.
2. **Certificate expiry:** `probe_ssl_earliest_cert_expiry{instance="portal.example.com"}` should return a future Unix timestamp.
3. **Dashboard:** Check the Certificate Overview dashboard for the new endpoint entry.

---

## Recording Rules

| Metric                              | Description                                              |
|-------------------------------------|----------------------------------------------------------|
| `instance:cert_days_remaining:gauge` | Days until earliest cert in chain expires (negative if expired) |
| `site:certs_monitored:count`        | Total monitored endpoints per site                       |
| `site:certs_expiring_30d:count`     | Certificates expiring within 30 days                     |
| `site:certs_expiring_7d:count`      | Certificates expiring within 7 days (critical)           |
| `site:certs_expired:count`          | Already-expired certificates per site                    |
| `site:cert_probe_failures:count`    | Unreachable endpoints per site                           |

---

## Alert Rules

| Alert                  | Condition                  | Duration | Severity  | Action                              |
|------------------------|----------------------------|----------|-----------|-------------------------------------|
| TLSCertExpiring90Days  | 30d <= remaining < 90d     | 1h       | INFO      | Plan renewal, create ticket         |
| TLSCertExpiring30Days  | 7d <= remaining < 30d      | 30m      | WARNING   | Begin renewal process               |
| TLSCertExpiring7Days   | 0 < remaining < 7d         | 10m      | CRITICAL  | Emergency renewal                   |
| TLSCertExpired         | remaining <= 0             | 5m       | CRITICAL  | Service impacted, renew immediately |
| TLSCertProbeFailure    | probe_success == 0          | 15m      | WARNING   | Endpoint unreachable or TLS error   |

### Chain Expiry Behavior

`probe_ssl_earliest_cert_expiry` reports the **earliest** expiry timestamp across the entire certificate chain. If an intermediate CA certificate expires before the leaf certificate, the alert fires on the intermediate's expiry date. This is correct behavior: an expired intermediate breaks the entire chain even if the leaf certificate is still valid.

---

## Internal PKI vs Public Certificates

### Public Certificates (Let's Encrypt, DigiCert, etc.)

- Use the `https_cert_check` module for full chain validation.
- Typically auto-renewed via ACME/certbot.
- The 30-day warning alert provides sufficient lead time to investigate failed auto-renewal.

### Internal PKI (Active Directory Certificate Services, etc.)

- Use `https_cert_check_internal` or `tcp_tls_cert_check`.
- Renewal is usually a manual process requiring longer lead times.
- The 90-day info alert serves as a planning horizon for manual renewal workflows.
- Root CA and intermediate CA certificates should also be monitored as separate targets.
- Mount the internal CA bundle to enable full chain validation instead of relying on `skip_verify`.

### DigiCert CertCentral Integration

This template monitors certificates via TLS handshake (black-box probing), not via certificate inventory APIs (white-box). API-based cert inventory through DigiCert CertCentral is possible but not included in this template. To add API-based monitoring, extend with a custom Alloy component or external script that queries the CertCentral API and exposes results as Prometheus metrics.

---

## Deployment

### Scrape Configuration

| Parameter | Value   | Rationale                                                        |
|-----------|---------|------------------------------------------------------------------|
| Interval  | 5m      | Certificate expiry changes slowly; one check per 5 minutes is sufficient |
| Timeout   | 15s     | Generous timeout for slow TLS handshakes and internal PKI OCSP checks    |
| Job name  | `cert_monitor` | Consistent job label across all cert probing targets             |

### Docker Compose

- Mount the blackbox modules file to the gateway container.
- Mount the endpoints file containing the target inventory.
- No additional containers are needed; the blackbox exporter is embedded in Alloy.

### Kubernetes (Helm)

- Create a ConfigMap for `blackbox_modules.yml` and `endpoints.yml`.
- The site gateway pod includes cert monitoring (no separate deployment required).
- Network policy: allow HTTPS outbound from the gateway pod to all monitored endpoints.

### Network Requirements

Alloy must be able to reach every monitored endpoint on its TLS port. Ensure the following ports are accessible from the monitoring VLAN or network segment:

| Service   | Port(s)     |
|-----------|-------------|
| HTTPS     | 443 (or custom) |
| LDAPS     | 636         |
| SMTP/TLS  | 465, 587    |

Internal endpoints may require firewall rules to permit connections from the monitoring infrastructure.

---

## Dashboard Integration

- **Certificate Overview** (`cert-overview`): Endpoint inventory, expiry timeline, and probe health status.
- **Enterprise NOC**: Site-level certificate health aggregation panel.
- **Probing Overview**: Includes certificate probes alongside ICMP, TCP, and HTTP probes.

---

## Troubleshooting

### Probe Failure (probe_success == 0)

1. Verify endpoint reachability from the monitoring host:
   ```bash
   curl -sv https://<endpoint> 2>&1 | grep "SSL certificate"
   ```
2. Check DNS resolution from the monitoring host.
3. For internal PKI: ensure the CA bundle is mounted if not using `skip_verify`.
4. Check firewall rules between the monitoring network and the target endpoint.

### Certificate Shows Wrong Expiry

`probe_ssl_earliest_cert_expiry` reports the earliest certificate in the chain. If the displayed expiry does not match the leaf certificate:

1. Inspect the full chain:
   ```bash
   openssl s_client -connect <host>:443 -showcerts
   ```
2. Check intermediate CA expiry dates -- if an intermediate expires before the leaf, that is the correct alert target.

### Missing Endpoints in Dashboard

1. Verify the target is defined in `endpoints.yml` or `role_cert_monitor.alloy`.
2. Check Alloy logs for scrape errors.
3. Query `probe_ssl_earliest_cert_expiry` directly to confirm the metric exists.
4. Ensure the `job` label matches the dashboard variable filter (`cert_monitor`).

---

## Related Documentation

- [Alert Runbooks](ALERT_RUNBOOKS.md) -- Alert investigation procedures.
- [SNMP Monitoring](SNMP_TRAPS.md) -- Network device monitoring (uses similar gateway pattern).
- [Architecture](../ARCHITECTURE.md) -- Overall system design.
