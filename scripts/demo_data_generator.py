#!/usr/bin/env python3
"""
Demo Data Generator for the Monitoring Stack

Pushes synthetic metrics into Prometheus and logs into Loki that match
real Alloy agent output. All dashboards (Windows, Linux, NOC, Site Overview,
Network, Hardware, Certs, SLA, IIS, Probing) populate with realistic data.

Architecture:
    1. Reads deploy/site_config.yml for site definitions and host profiles
    2. Generates time-series with correct metric names, label sets, and values
    3. Pushes to Prometheus via remote_write (/api/v1/write)
    4. Pushes log entries to Loki (/loki/api/v1/push)
    5. Runs continuously in background mode for live demos

Usage:
    python scripts/demo_data_generator.py                          # Default config
    python scripts/demo_data_generator.py --config deploy/site_config.yml
    python scripts/demo_data_generator.py --backfill 60            # 60 min history
    python scripts/demo_data_generator.py --once                   # Single push, no loop
"""

import argparse
import json
import math
import random
import struct
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)

try:
    import snappy
    HAS_SNAPPY = True
except ImportError:
    HAS_SNAPPY = False


def _snappy_compress_fallback(data: bytes) -> bytes:
    """Minimal snappy block compression for Prometheus remote_write.

    Implements the snappy block format (not streaming) which is what
    Prometheus expects. Only uses literal-only encoding (no copy ops)
    which is valid snappy but not optimally compressed. Good enough for
    demo data payloads.

    Format: varint(uncompressed_length) + chunks
    Each chunk: tag_byte(0x00 = literal) + length + data
    """
    result = _encode_varint_snappy(len(data))
    offset = 0
    while offset < len(data):
        # Max literal chunk is 65536 bytes
        chunk_size = min(len(data) - offset, 65536)
        chunk = data[offset : offset + chunk_size]

        if chunk_size <= 60:
            # Short literal: tag byte encodes length - 1 in upper 6 bits
            result += bytes([(chunk_size - 1) << 2])
        elif chunk_size <= 256:
            # 1-byte length literal
            result += bytes([0xF0, chunk_size - 1])
        else:
            # 2-byte length literal
            result += bytes([0xF4, (chunk_size - 1) & 0xFF, ((chunk_size - 1) >> 8) & 0xFF])

        result += chunk
        offset += chunk_size

    return result


def _encode_varint_snappy(value: int) -> bytes:
    """Encode varint for snappy framing."""
    result = []
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Prometheus remote_write and Loki push endpoints (Docker Compose defaults)
PROMETHEUS_URL = "http://localhost:9090/api/v1/write"
LOKI_URL = "http://localhost:3100/loki/api/v1/push"

# Scrape interval matches Alloy/Prometheus config
SCRAPE_INTERVAL = 30  # seconds

# Default host profile if not specified in config
DEFAULT_HOST_PROFILE = {
    "dc": 2,
    "sql": 2,
    "iis": 3,
    "fileserver": 2,
    "dhcp": 1,
    "ca": 1,
    "docker": 2,
    "generic": 3,
}


# =============================================================================
# Simulated Host Model
# =============================================================================

@dataclass
class SimulatedHost:
    """Represents a simulated server with persistent state for metric generation."""

    hostname: str
    site_code: str
    role: str
    os_type: str  # "windows" or "linux"
    ip: str
    instance: str = ""

    # Persistent metric state -- updated each tick to create realistic trends
    cpu_base: float = 0.0
    mem_base: float = 0.0
    disk_used_ratio: float = 0.0
    net_bytes_counter: float = 0.0
    uptime_start: float = 0.0
    services_stopped: int = 0
    iis_requests_counter: float = 0.0
    iis_connections: int = 0
    # CPU counters must be monotonically increasing (tracked per mode)
    cpu_counters: dict = field(default_factory=dict)

    def __post_init__(self):
        self.instance = f"{self.ip}:9182" if self.os_type == "windows" else f"{self.ip}:9100"
        # Randomize baselines so each host looks different
        self.cpu_base = random.uniform(0.10, 0.55)
        self.mem_base = random.uniform(0.35, 0.75)
        self.disk_used_ratio = random.uniform(0.30, 0.80)
        self.net_bytes_counter = random.uniform(1e9, 1e11)
        self.uptime_start = time.time() - random.uniform(86400, 86400 * 30)
        self.services_stopped = random.randint(0, 2) if self.os_type == "windows" else 0
        if self.role == "iis":
            self.iis_requests_counter = random.uniform(1e6, 1e8)
            self.iis_connections = random.randint(10, 200)


@dataclass
class SimulatedNetworkDevice:
    """Represents a simulated SNMP network device."""

    device_name: str
    device_type: str  # switch, firewall, ap, ups
    vendor: str
    site_code: str
    ip: str
    instance: str = ""
    interface_count: int = 4
    uptime_ticks: int = 0
    in_octets_counters: list = field(default_factory=list)
    out_octets_counters: list = field(default_factory=list)

    def __post_init__(self):
        self.instance = f"{self.ip}:161"
        self.uptime_ticks = random.randint(100000, 99999999)
        self.in_octets_counters = [
            random.uniform(1e9, 1e12) for _ in range(self.interface_count)
        ]
        self.out_octets_counters = [
            random.uniform(1e9, 1e12) for _ in range(self.interface_count)
        ]


@dataclass
class SimulatedBMC:
    """Represents a simulated Redfish BMC (iLO/iDRAC)."""

    device_name: str
    vendor: str  # HPE, Dell
    bmc_type: str  # iLO, iDRAC
    site_code: str
    ip: str
    instance: str = ""
    temperature: float = 0.0
    power_watts: float = 0.0

    def __post_init__(self):
        self.instance = f"{self.ip}:443"
        self.temperature = random.uniform(22.0, 38.0)
        self.power_watts = random.uniform(150.0, 450.0)


@dataclass
class SimulatedCertEndpoint:
    """Represents a simulated TLS certificate endpoint."""

    name: str
    address: str
    site_code: str
    cert_type: str  # public, pki
    days_until_expiry: int = 0

    def __post_init__(self):
        # Spread expiry across realistic ranges including urgent/critical
        weights = random.random()
        if weights < 0.1:
            self.days_until_expiry = random.randint(1, 7)      # Critical
        elif weights < 0.2:
            self.days_until_expiry = random.randint(8, 30)     # Urgent
        elif weights < 0.35:
            self.days_until_expiry = random.randint(31, 60)    # Expiring
        else:
            self.days_until_expiry = random.randint(61, 365)   # Healthy


# =============================================================================
# Inventory Builder
# =============================================================================

def build_inventory(config: dict) -> dict:
    """Build simulated inventory from site_config.yml."""
    sites = config.get("sites", [])
    demo = config.get("demo", {})
    profile = demo.get("host_profile", DEFAULT_HOST_PROFILE)

    hosts = []
    network_devices = []
    bmcs = []
    cert_endpoints = []

    for site in sites:
        code = site["code"]
        host_num = 1

        # Generate servers per role
        for role, count in profile.items():
            os_type = "linux" if role == "docker" else "windows"
            for i in range(count):
                ip = f"10.{hash(code) % 250}.{host_num // 255}.{(host_num % 255) + 1}"
                hosts.append(
                    SimulatedHost(
                        hostname=f"srv-{role}-{host_num:02d}.{code}",
                        site_code=code,
                        role=role,
                        os_type=os_type,
                        ip=ip,
                    )
                )
                host_num += 1

        # Generate network devices (2 switches, 1 firewall, 2 APs per site)
        gw = site.get("gateway", {})
        if gw.get("snmp", False):
            device_templates = [
                ("sw-core-01", "switch", "Cisco", 24),
                ("sw-access-01", "switch", "Cisco", 48),
                ("fw-perimeter-01", "firewall", "Palo Alto", 8),
                ("ap-floor1-01", "ap", "Ubiquiti", 2),
                ("ap-floor2-01", "ap", "Ubiquiti", 2),
            ]
            for name_base, dtype, vendor, intf_count in device_templates:
                ip = f"10.{hash(code) % 250}.254.{len(network_devices) % 255 + 1}"
                network_devices.append(
                    SimulatedNetworkDevice(
                        device_name=f"{name_base}.{code}",
                        device_type=dtype,
                        vendor=vendor,
                        site_code=code,
                        ip=ip,
                        interface_count=intf_count,
                    )
                )

        # Generate BMC endpoints (one per physical server at site)
        if gw.get("redfish", False):
            bmc_templates = [
                ("hv-node-01", "HPE", "iLO"),
                ("hv-node-02", "HPE", "iLO"),
                ("hv-node-03", "Dell", "iDRAC"),
            ]
            for name_base, vendor, bmc_type in bmc_templates:
                ip = f"10.{hash(code) % 250}.253.{len(bmcs) % 255 + 1}"
                bmcs.append(
                    SimulatedBMC(
                        device_name=f"{name_base}.{code}",
                        vendor=vendor,
                        bmc_type=bmc_type,
                        site_code=code,
                        ip=ip,
                    )
                )

        # Generate certificate endpoints
        if gw.get("certs", False):
            cert_templates = [
                (f"webmail.{code}.example.com", "public", f"srv-iis-05.{code}", "Exchange OWA"),
                (f"portal.{code}.example.com", "public", f"srv-iis-06.{code}", "Employee Portal"),
                (f"ldap.{code}.example.com", "pki", f"srv-dc-01.{code}", "LDAPS"),
                (f"vcenter.{code}.example.com", "pki", f"srv-generic-12.{code}", "vCenter"),
            ]
            for addr, ctype, hostname, service in cert_templates:
                ep = SimulatedCertEndpoint(
                    name=addr.split(".")[0],
                    address=f"https://{addr}",
                    site_code=code,
                    cert_type=ctype,
                )
                ep.hostname = hostname
                ep.service = service
                cert_endpoints.append(ep)

    return {
        "hosts": hosts,
        "network_devices": network_devices,
        "bmcs": bmcs,
        "cert_endpoints": cert_endpoints,
    }


# =============================================================================
# Metric Generation
# =============================================================================

def _jitter(base: float, amplitude: float = 0.05) -> float:
    """Add realistic noise to a metric value, clamped to [0, 1] for ratios."""
    return max(0.0, min(1.0, base + random.uniform(-amplitude, amplitude)))


def _counter_increment(current: float, rate_per_sec: float) -> float:
    """Increment a counter by a realistic amount for one scrape interval."""
    jittered_rate = rate_per_sec * random.uniform(0.7, 1.3)
    return current + (jittered_rate * SCRAPE_INTERVAL)


def generate_host_metrics(host: SimulatedHost, timestamp_ms: int) -> list[tuple]:
    """Generate all metrics for a single host at a given timestamp.

    Returns list of (metric_name, labels_dict, value) tuples.
    """
    metrics = []
    base_labels = {
        "hostname": host.hostname,
        "instance": host.instance,
        "environment": "demo",
        "datacenter": host.site_code,
        "role": host.role,
    }

    # Evolve state slightly each tick for realism
    host.cpu_base = _jitter(host.cpu_base, 0.03)
    host.mem_base = _jitter(host.mem_base, 0.02)
    host.net_bytes_counter = _counter_increment(host.net_bytes_counter, random.uniform(1e5, 5e6))

    if host.os_type == "windows":
        metrics.extend(_generate_windows_metrics(host, base_labels, timestamp_ms))
    else:
        metrics.extend(_generate_linux_metrics(host, base_labels, timestamp_ms))

    # Universal: up metric (simulate occasional downtime for SLA dashboards)
    # ~2% of generic hosts randomly go "down" for short periods to show non-100% SLA
    job = "windows_base" if host.os_type == "windows" else "linux_base"
    up_labels = {**base_labels, "job": job, "os": host.os_type}
    is_down = (host.role == "generic" and random.random() < 0.02)
    metrics.append(("up", up_labels, 0.0 if is_down else 1.0))

    return metrics


def _generate_windows_metrics(
    host: SimulatedHost, base_labels: dict, timestamp_ms: int
) -> list[tuple]:
    """Generate Windows-specific metrics."""
    metrics = []
    labels = {**base_labels, "os": "windows"}

    # CPU time counters (must be monotonically increasing)
    idle_ratio = 1.0 - host.cpu_base
    for mode, ratio in [("idle", idle_ratio), ("user", host.cpu_base * 0.7),
                         ("system", host.cpu_base * 0.2), ("interrupt", host.cpu_base * 0.1)]:
        cpu_labels = {**labels, "mode": mode}
        key = f"win_{mode}"
        increment = SCRAPE_INTERVAL * ratio * random.uniform(0.9, 1.1)
        host.cpu_counters[key] = host.cpu_counters.get(key, random.uniform(1e4, 1e6)) + increment
        metrics.append(("windows_cpu_time_total", cpu_labels, host.cpu_counters[key]))

    # Memory
    total_bytes = 17179869184.0  # 16 GB
    free_bytes = total_bytes * (1.0 - host.mem_base)
    metrics.append(("windows_memory_physical_total_bytes", labels, total_bytes))
    metrics.append(("windows_memory_physical_free_bytes", labels, free_bytes))

    # Disk volumes -- vary by role to reflect realistic server configurations
    role_volumes = {
        "sql": ["C:", "D:", "E:", "F:", "G:"],  # OS, Data, Logs, TempDB, Backup
        "fileserver": ["C:", "D:", "E:", "F:"],  # OS, Data1, Data2, Archive
        "iis": ["C:", "D:", "E:"],               # OS, Sites, Logs
        "dc": ["C:", "D:"],                      # OS, NTDS/SYSVOL
        "generic": ["C:", "D:"],
        "dhcp": ["C:", "D:"],
        "ca": ["C:", "D:"],
    }
    volumes = role_volumes.get(host.role, ["C:", "D:"])
    for volume in volumes:
        vol_labels = {**labels, "volume": volume}
        size = 536870912000.0 if volume == "C:" else 1099511627776.0  # 500GB / 1TB
        free = size * (1.0 - host.disk_used_ratio * random.uniform(0.9, 1.1))
        free = max(0, min(size, free))
        metrics.append(("windows_logical_disk_size_bytes", vol_labels, size))
        metrics.append(("windows_logical_disk_free_bytes", vol_labels, free))
        # Disk IO utilization (idle seconds counter)
        uptime = time.time() - host.uptime_start
        idle_pct = random.uniform(0.6, 0.95)
        metrics.append(("windows_logical_disk_idle_seconds_total", vol_labels, uptime * idle_pct))
        # Disk throughput counters (monotonically increasing)
        read_key = f"win_disk_read_{volume}"
        write_key = f"win_disk_write_{volume}"
        host.cpu_counters[read_key] = host.cpu_counters.get(read_key, random.uniform(1e9, 1e11)) + random.uniform(1e5, 5e7) * SCRAPE_INTERVAL
        host.cpu_counters[write_key] = host.cpu_counters.get(write_key, random.uniform(1e9, 1e11)) + random.uniform(1e5, 5e7) * SCRAPE_INTERVAL
        metrics.append(("windows_logical_disk_read_bytes_total", vol_labels, host.cpu_counters[read_key]))
        metrics.append(("windows_logical_disk_write_bytes_total", vol_labels, host.cpu_counters[write_key]))

    # Network
    nic_labels = {**labels, "nic": "Ethernet0"}
    metrics.append(("windows_net_bytes_total", nic_labels, host.net_bytes_counter))
    metrics.append(("windows_net_bytes_received_total", nic_labels, host.net_bytes_counter * 0.6))
    metrics.append(("windows_net_bytes_sent_total", nic_labels, host.net_bytes_counter * 0.4))

    # Services
    running_services = ["W32Time", "WinRM", "EventLog", "Dnscache", "LanmanServer"]
    for svc in running_services:
        svc_labels = {**labels, "name": svc, "state": "running"}
        metrics.append(("windows_service_state", svc_labels, 1.0))
    # Occasionally show a stopped service
    if host.services_stopped > 0:
        svc_labels = {**labels, "name": "Spooler", "state": "stopped"}
        metrics.append(("windows_service_state", svc_labels, 1.0))

    # Uptime
    metrics.append(("windows_time_current_timestamp_seconds", labels, time.time()))
    metrics.append(("windows_system_boot_time_timestamp", labels, host.uptime_start))

    # IIS metrics (only for iis role)
    if host.role == "iis":
        host.iis_requests_counter = _counter_increment(host.iis_requests_counter, random.uniform(50, 500))
        host.iis_connections = max(1, host.iis_connections + random.randint(-5, 5))

        for site_name in ["Default Web Site", "API"]:
            iis_labels = {**labels, "site_name": site_name}
            for status, weight in [("200", 0.85), ("301", 0.05), ("404", 0.06), ("500", 0.03), ("503", 0.01)]:
                req_labels = {**iis_labels, "status_code": status, "method": "GET"}
                metrics.append(("windows_iis_requests_total", req_labels, host.iis_requests_counter * weight))
            metrics.append(("windows_iis_current_connections", iis_labels, float(host.iis_connections)))
            metrics.append(("windows_iis_sent_bytes_total", iis_labels, host.net_bytes_counter * 0.3))
            metrics.append(("windows_iis_received_bytes_total", iis_labels, host.net_bytes_counter * 0.1))

    # SQL Server metrics (only for sql role)
    if host.role == "sql":
        sql_labels = {**labels, "job": "windows_sql"}
        metrics.append(("mssql_buffer_cache_hit_ratio", sql_labels, random.uniform(0.92, 0.99)))
        metrics.append(("mssql_buffer_manager_page_life_expectancy_seconds", sql_labels, random.uniform(200, 800)))
        metrics.append(("mssql_sql_statistics_batch_requests_per_sec", sql_labels, random.uniform(50, 500)))
        metrics.append(("mssql_sql_statistics_sql_compilations_per_sec", sql_labels, random.uniform(5, 50)))
        metrics.append(("mssql_sql_statistics_sql_recompilations_per_sec", sql_labels, random.uniform(0, 5)))
        metrics.append(("mssql_general_statistics_user_connections", sql_labels, float(random.randint(10, 100))))
        metrics.append(("mssql_general_statistics_processes_blocked", sql_labels, float(random.randint(0, 2))))
        metrics.append(("mssql_locks_lock_waits_per_sec", sql_labels, random.uniform(0, 10)))
        metrics.append(("mssql_locks_deadlocks_per_sec", sql_labels, random.uniform(0, 0.5)))
        metrics.append(("mssql_locks_average_wait_time_ms", sql_labels, random.uniform(0, 50)))
        metrics.append(("mssql_memory_manager_total_server_memory_bytes", sql_labels, random.uniform(4e9, 12e9)))
        metrics.append(("mssql_memory_manager_target_server_memory_bytes", sql_labels, 12884901888.0))
        metrics.append(("mssql_memory_manager_memory_grants_pending", sql_labels, 0.0))
        metrics.append(("mssql_access_methods_full_scans_per_sec", sql_labels, random.uniform(0, 20)))
        metrics.append(("mssql_access_methods_index_searches_per_sec", sql_labels, random.uniform(100, 2000)))
        metrics.append(("mssql_access_methods_page_splits_per_sec", sql_labels, random.uniform(0, 50)))
        # Per-database metrics
        for db in ["master", "AppDB", "ReportDB"]:
            db_labels = {**sql_labels, "database": db}
            metrics.append(("mssql_databases_data_file_size_bytes", db_labels, random.uniform(1e8, 5e10)))
            metrics.append(("mssql_databases_log_file_size_bytes", db_labels, random.uniform(1e7, 5e9)))
            metrics.append(("mssql_databases_active_transactions", db_labels, float(random.randint(0, 10))))
            metrics.append(("mssql_databases_log_flush_waits_per_sec", db_labels, random.uniform(0, 5)))
        # up for sql job
        metrics.append(("up", {**sql_labels}, 1.0))
        # SQL services
        for svc in ["MSSQLSERVER", "SQLSERVERAGENT", "SQLBrowser"]:
            metrics.append(("windows_service_state", {**labels, "name": svc, "state": "running"}, 1.0))

    # Domain Controller metrics (only for dc role)
    if host.role == "dc":
        dc_labels = {**labels, "job": "windows_dc"}
        # LDAP
        metrics.append(("windows_ad_ldap_searches_total", dc_labels, host.cpu_counters.get("ldap_search", random.uniform(1e5, 1e7))))
        host.cpu_counters["ldap_search"] = host.cpu_counters.get("ldap_search", random.uniform(1e5, 1e7)) + random.uniform(50, 500) * SCRAPE_INTERVAL
        metrics.append(("ad_ds_ldap_searches_per_sec", dc_labels, random.uniform(50, 500)))
        metrics.append(("ad_ds_ldap_binds_per_sec", dc_labels, random.uniform(10, 100)))
        metrics.append(("windows_ad_ldap_client_sessions", dc_labels, float(random.randint(20, 200))))
        # Replication
        metrics.append(("ad_ds_replication_objects_inbound", dc_labels, float(random.randint(100, 10000))))
        metrics.append(("ad_ds_replication_objects_outbound", dc_labels, float(random.randint(100, 10000))))
        metrics.append(("ad_ds_dra_inbound_sync_requests_per_sec", dc_labels, random.uniform(0, 5)))
        metrics.append(("ad_ds_dra_outbound_sync_requests_per_sec", dc_labels, random.uniform(0, 5)))
        metrics.append(("windows_ad_replication_data_intrasite_bytes_total", dc_labels,
                         host.cpu_counters.get("repl_intra", random.uniform(1e8, 1e10))))
        host.cpu_counters["repl_intra"] = host.cpu_counters.get("repl_intra", random.uniform(1e8, 1e10)) + random.uniform(1e3, 1e5) * SCRAPE_INTERVAL
        metrics.append(("windows_ad_replication_data_intersite_bytes_total", dc_labels,
                         host.cpu_counters.get("repl_inter", random.uniform(1e7, 1e9))))
        host.cpu_counters["repl_inter"] = host.cpu_counters.get("repl_inter", random.uniform(1e7, 1e9)) + random.uniform(1e2, 1e4) * SCRAPE_INTERVAL
        metrics.append(("windows_ad_replication_inbound_sync_objects_remaining", dc_labels, float(random.randint(0, 5))))
        # SAM and security
        metrics.append(("windows_ad_sam_password_changes_total", dc_labels,
                         host.cpu_counters.get("sam_pwd", random.uniform(1e3, 1e5))))
        host.cpu_counters["sam_pwd"] = host.cpu_counters.get("sam_pwd", random.uniform(1e3, 1e5)) + random.uniform(0, 2) * SCRAPE_INTERVAL
        metrics.append(("windows_ad_tombstoned_objects_visited_total", dc_labels, float(random.randint(0, 100))))
        # DNS
        metrics.append(("dns_queries_per_sec", dc_labels, random.uniform(100, 2000)))
        metrics.append(("dns_recursive_queries_per_sec", dc_labels, random.uniform(10, 200)))
        metrics.append(("dns_zone_transfer_requests_per_sec", dc_labels, random.uniform(0, 1)))
        metrics.append(("up", {**dc_labels}, 1.0))
        for svc in ["NTDS", "DNS", "Netlogon", "DFSR", "KDC", "ADWS"]:
            metrics.append(("windows_service_state", {**labels, "name": svc, "state": "running"}, 1.0))

    # DHCP Server metrics (only for dhcp role)
    if host.role == "dhcp":
        dhcp_labels = {**labels, "job": "windows_dhcp"}
        # Server-level message counters
        metrics.append(("windows_dhcp_discovers_total", dhcp_labels, host.cpu_counters.get("dhcp_disc", random.uniform(1e4, 1e6))))
        host.cpu_counters["dhcp_disc"] = host.cpu_counters.get("dhcp_disc", random.uniform(1e4, 1e6)) + random.uniform(1, 10) * SCRAPE_INTERVAL
        metrics.append(("windows_dhcp_offers_total", dhcp_labels, host.cpu_counters.get("dhcp_offer", random.uniform(1e4, 1e6))))
        host.cpu_counters["dhcp_offer"] = host.cpu_counters.get("dhcp_offer", random.uniform(1e4, 1e6)) + random.uniform(1, 10) * SCRAPE_INTERVAL
        metrics.append(("windows_dhcp_requests_total", dhcp_labels, host.cpu_counters.get("dhcp_req", random.uniform(1e4, 1e6))))
        host.cpu_counters["dhcp_req"] = host.cpu_counters.get("dhcp_req", random.uniform(1e4, 1e6)) + random.uniform(1, 10) * SCRAPE_INTERVAL
        metrics.append(("windows_dhcp_ack_total", dhcp_labels, host.cpu_counters.get("dhcp_ack", random.uniform(1e4, 1e6))))
        host.cpu_counters["dhcp_ack"] = host.cpu_counters.get("dhcp_ack", random.uniform(1e4, 1e6)) + random.uniform(1, 10) * SCRAPE_INTERVAL
        metrics.append(("windows_dhcp_nacks_total", dhcp_labels, host.cpu_counters.get("dhcp_nack", 0.0)))
        host.cpu_counters["dhcp_nack"] = host.cpu_counters.get("dhcp_nack", 0.0) + (random.uniform(0, 0.1) if random.random() < 0.05 else 0)
        # Legacy rate metrics (kept for backward compat with existing dashboard)
        metrics.append(("dhcp_ack_messages_per_sec", dhcp_labels, random.uniform(0, 10)))
        metrics.append(("dhcp_nak_messages_per_sec", dhcp_labels, random.uniform(0, 0.5)))
        metrics.append(("dhcp_discover_messages_per_sec", dhcp_labels, random.uniform(0, 10)))
        metrics.append(("dhcp_offer_messages_per_sec", dhcp_labels, random.uniform(0, 10)))
        metrics.append(("dhcp_request_messages_per_sec", dhcp_labels, random.uniform(0, 10)))
        # Per-scope metrics
        scopes = [
            ("10.0.1.0/24", "Servers", 254, random.randint(50, 200)),
            ("10.0.2.0/24", "Workstations", 254, random.randint(100, 240)),
            ("10.0.3.0/24", "Printers", 126, random.randint(10, 50)),
            ("10.0.10.0/24", "VoIP", 254, random.randint(30, 100)),
        ]
        for subnet, scope_name, total, in_use in scopes:
            scope_labels = {**dhcp_labels, "scope": subnet}
            free = max(0, total - in_use)
            metrics.append(("windows_dhcp_scope_addresses_in_use", scope_labels, float(in_use)))
            metrics.append(("windows_dhcp_scope_addresses_free", scope_labels, float(free)))
            metrics.append(("windows_dhcp_scope_pending_offers", scope_labels, float(random.randint(0, 3))))
            metrics.append(("windows_dhcp_scope_reserved_address", scope_labels, float(random.randint(5, 20))))
            metrics.append(("windows_dhcp_scope_state", {**scope_labels, "state": "active"}, 1.0))
            metrics.append(("windows_dhcp_scope_info", {**scope_labels, "name": scope_name}, 1.0))
        metrics.append(("up", {**dhcp_labels}, 1.0))
        metrics.append(("windows_service_state", {**labels, "name": "DHCPServer", "state": "running"}, 1.0))

    # Certificate Authority metrics (only for ca role)
    if host.role == "ca":
        ca_labels = {**labels, "job": "windows_ca"}
        # Per-template metrics (what the real ADCS collector exposes)
        templates = ["Machine", "WebServer", "User", "DomainController", "SubCA"]
        for tmpl in templates:
            tmpl_labels = {**ca_labels, "cert_template": tmpl}
            rate = random.uniform(0.1, 3.0) if tmpl in ("Machine", "User") else random.uniform(0, 0.5)
            host.cpu_counters[f"adcs_req_{tmpl}"] = host.cpu_counters.get(f"adcs_req_{tmpl}", random.uniform(100, 10000)) + rate * SCRAPE_INTERVAL
            host.cpu_counters[f"adcs_issued_{tmpl}"] = host.cpu_counters.get(f"adcs_issued_{tmpl}", random.uniform(100, 10000)) + rate * 0.95 * SCRAPE_INTERVAL
            host.cpu_counters[f"adcs_failed_{tmpl}"] = host.cpu_counters.get(f"adcs_failed_{tmpl}", 0) + (random.uniform(0, 0.05) if random.random() < 0.1 else 0)
            metrics.append(("windows_adcs_requests_total", tmpl_labels, host.cpu_counters[f"adcs_req_{tmpl}"]))
            metrics.append(("windows_adcs_issued_requests_total", tmpl_labels, host.cpu_counters[f"adcs_issued_{tmpl}"]))
            metrics.append(("windows_adcs_failed_requests_total", tmpl_labels, host.cpu_counters[f"adcs_failed_{tmpl}"]))
            metrics.append(("windows_adcs_pending_requests_total", tmpl_labels, float(random.randint(0, 2))))
            metrics.append(("windows_adcs_request_processing_time_seconds", tmpl_labels, random.uniform(0.01, 0.5)))
        # Legacy aggregate metrics (kept for backward compat)
        metrics.append(("adcs_requests_per_sec", ca_labels, random.uniform(0, 5)))
        metrics.append(("adcs_issued_per_sec", ca_labels, random.uniform(0, 5)))
        metrics.append(("adcs_failed_per_sec", ca_labels, random.uniform(0, 0.2)))
        metrics.append(("adcs_pending_requests", ca_labels, float(random.randint(0, 3))))
        metrics.append(("up", {**ca_labels}, 1.0))
        metrics.append(("windows_service_state", {**labels, "name": "CertSvc", "state": "running"}, 1.0))

    # File Server metrics (only for fileserver role)
    if host.role == "fileserver":
        fs_labels = {**labels, "job": "windows_fileserver"}
        metrics.append(("smb_server_sessions_active", fs_labels, float(random.randint(5, 50))))
        metrics.append(("smb_server_tree_connects_total", fs_labels, float(random.randint(10, 200))))
        metrics.append(("smb_server_bytes_read_per_sec", fs_labels, random.uniform(1e5, 5e7)))
        metrics.append(("smb_server_bytes_written_per_sec", fs_labels, random.uniform(1e5, 5e7)))
        metrics.append(("smb_server_requests_per_sec", fs_labels, random.uniform(10, 500)))
        for share in ["Data$", "Users$", "Apps$"]:
            share_labels = {**fs_labels, "share": share}
            metrics.append(("smb_server_open_files_per_share", share_labels, float(random.randint(0, 50))))
        # Physical disk I/O
        for disk in ["PhysicalDisk0", "PhysicalDisk1"]:
            disk_labels = {**fs_labels, "disk": disk}
            metrics.append(("physical_disk_read_bytes_per_sec", disk_labels, random.uniform(1e5, 5e7)))
            metrics.append(("physical_disk_write_bytes_per_sec", disk_labels, random.uniform(1e5, 5e7)))
            metrics.append(("physical_disk_reads_per_sec", disk_labels, random.uniform(10, 500)))
            metrics.append(("physical_disk_writes_per_sec", disk_labels, random.uniform(10, 500)))
            metrics.append(("physical_disk_avg_queue_depth", disk_labels, random.uniform(0, 5)))
            metrics.append(("physical_disk_avg_read_latency_ms", disk_labels, random.uniform(0.5, 15)))
            metrics.append(("physical_disk_avg_write_latency_ms", disk_labels, random.uniform(0.5, 20)))
        # FSRM quota metrics
        for quota_path in [r"C:\Shares\Data", r"C:\Shares\Users", r"C:\Shares\Apps"]:
            quota_labels = {**fs_labels, "path": quota_path}
            hard_limit = 1099511627776.0  # 1 TB
            usage = hard_limit * random.uniform(0.3, 0.85)
            metrics.append(("fsrm_quota_usage_bytes", quota_labels, usage))
            metrics.append(("fsrm_quota_hard_limit_bytes", quota_labels, hard_limit))
            metrics.append(("fsrm_quota_percent_used", quota_labels, (usage / hard_limit) * 100))
        metrics.append(("up", {**fs_labels}, 1.0))
        for svc in ["LanmanServer", "DFSR", "DFS", "SrmSvc"]:
            metrics.append(("windows_service_state", {**labels, "name": svc, "state": "running"}, 1.0))

    # IIS service state (for iis role)
    if host.role == "iis":
        for svc in ["W3SVC", "WAS", "IISADMIN"]:
            metrics.append(("windows_service_state", {**labels, "name": svc, "state": "running"}, 1.0))

    return metrics


def _generate_linux_metrics(
    host: SimulatedHost, base_labels: dict, timestamp_ms: int
) -> list[tuple]:
    """Generate Linux-specific metrics."""
    metrics = []
    labels = {**base_labels, "os": "linux"}

    # CPU seconds total (must be monotonically increasing)
    idle_ratio = 1.0 - host.cpu_base
    for mode, ratio in [("idle", idle_ratio), ("user", host.cpu_base * 0.6),
                         ("system", host.cpu_base * 0.25), ("iowait", host.cpu_base * 0.1),
                         ("irq", host.cpu_base * 0.05)]:
        cpu_labels = {**labels, "mode": mode, "cpu": "0"}
        key = f"linux_{mode}"
        increment = SCRAPE_INTERVAL * ratio * random.uniform(0.9, 1.1)
        host.cpu_counters[key] = host.cpu_counters.get(key, random.uniform(1e4, 1e6)) + increment
        metrics.append(("node_cpu_seconds_total", cpu_labels, host.cpu_counters[key]))

    # Memory (full breakdown for Linux dashboard)
    total_bytes = 17179869184.0  # 16 GB
    used_ratio = host.mem_base
    free_bytes = total_bytes * 0.05
    cached_bytes = total_bytes * (1.0 - used_ratio) * 0.6
    buffers_bytes = total_bytes * (1.0 - used_ratio) * 0.1
    avail_bytes = free_bytes + cached_bytes + buffers_bytes
    swap_total = 8589934592.0  # 8 GB
    swap_free = swap_total * random.uniform(0.8, 1.0)
    metrics.append(("node_memory_MemTotal_bytes", labels, total_bytes))
    metrics.append(("node_memory_MemAvailable_bytes", labels, avail_bytes))
    metrics.append(("node_memory_MemFree_bytes", labels, free_bytes))
    metrics.append(("node_memory_Cached_bytes", labels, cached_bytes))
    metrics.append(("node_memory_Buffers_bytes", labels, buffers_bytes))
    metrics.append(("node_memory_SwapTotal_bytes", labels, swap_total))
    metrics.append(("node_memory_SwapFree_bytes", labels, swap_free))

    # Filesystem
    for mp, dev, size in [("/", "/dev/sda1", 107374182400.0),
                           ("/var", "/dev/sda2", 53687091200.0)]:
        fs_labels = {**labels, "mountpoint": mp, "device": dev, "fstype": "ext4"}
        avail = size * (1.0 - host.disk_used_ratio * random.uniform(0.9, 1.1))
        avail = max(0, min(size, avail))
        metrics.append(("node_filesystem_size_bytes", fs_labels, size))
        metrics.append(("node_filesystem_avail_bytes", fs_labels, avail))

    # Disk IO (counters -- must be monotonically increasing)
    disk_labels = {**labels, "device": "sda"}
    uptime_secs = time.time() - host.uptime_start
    io_time = uptime_secs * random.uniform(0.05, 0.30)
    metrics.append(("node_disk_io_time_seconds_total", disk_labels, io_time))
    read_key = "linux_disk_read"
    write_key = "linux_disk_write"
    host.cpu_counters[read_key] = host.cpu_counters.get(read_key, random.uniform(1e9, 1e11)) + random.uniform(1e5, 5e7) * SCRAPE_INTERVAL
    host.cpu_counters[write_key] = host.cpu_counters.get(write_key, random.uniform(1e9, 1e11)) + random.uniform(1e5, 5e7) * SCRAPE_INTERVAL
    metrics.append(("node_disk_read_bytes_total", disk_labels, host.cpu_counters[read_key]))
    metrics.append(("node_disk_written_bytes_total", disk_labels, host.cpu_counters[write_key]))

    # Network
    net_labels = {**labels, "device": "eth0"}
    metrics.append(("node_network_receive_bytes_total", net_labels, host.net_bytes_counter * 0.6))
    metrics.append(("node_network_transmit_bytes_total", net_labels, host.net_bytes_counter * 0.4))

    # Load (1m, 5m, 15m)
    load_base = host.cpu_base * 4.0
    metrics.append(("node_load1", labels, load_base * random.uniform(0.8, 1.2)))
    metrics.append(("node_load5", labels, load_base * random.uniform(0.85, 1.15)))
    metrics.append(("node_load15", labels, load_base * random.uniform(0.9, 1.1)))

    # Systemd units
    for unit, state in [("docker.service", "active"), ("sshd.service", "active"),
                         ("chronyd.service", "active")]:
        unit_labels = {**labels, "name": unit, "state": state}
        metrics.append(("node_systemd_unit_state", unit_labels, 1.0))

    # Boot time
    metrics.append(("node_boot_time_seconds", labels, host.uptime_start))

    # Docker-specific metrics (only for docker role)
    if host.role == "docker":
        docker_labels = {**labels, "job": "docker_daemon"}
        running = random.randint(8, 25)
        stopped = random.randint(0, 3)
        metrics.append(("engine_daemon_container_states_containers", {**docker_labels, "state": "running"}, float(running)))
        metrics.append(("engine_daemon_container_states_containers", {**docker_labels, "state": "stopped"}, float(stopped)))
        metrics.append(("engine_daemon_container_states_containers", {**docker_labels, "state": "paused"}, 0.0))
        metrics.append(("engine_daemon_images_images", docker_labels, float(random.randint(10, 50))))
        metrics.append(("engine_daemon_engine_cpus", docker_labels, 4.0))
        metrics.append(("engine_daemon_engine_memory_bytes", docker_labels, 17179869184.0))
        metrics.append(("go_goroutines", docker_labels, float(random.randint(30, 100))))
        metrics.append(("go_memstats_heap_alloc_bytes", docker_labels, random.uniform(5e7, 3e8)))
        metrics.append(("up", {**docker_labels}, 1.0))

    return metrics


def generate_network_device_metrics(device: SimulatedNetworkDevice, timestamp_ms: int) -> list[tuple]:
    """Generate SNMP metrics for a network device."""
    metrics = []
    base_labels = {
        "device_name": device.device_name,
        "device_type": device.device_type,
        "vendor": device.vendor,
        "datacenter": device.site_code,
        "environment": "demo",
        "job": "snmp",
        "instance": device.instance,
    }

    # sysUpTime (in timeticks, 1/100th second)
    device.uptime_ticks += SCRAPE_INTERVAL * 100
    metrics.append(("sysUpTime", base_labels, float(device.uptime_ticks)))

    # up metric
    metrics.append(("up", {**base_labels}, 1.0))

    # Per-interface metrics
    for i in range(device.interface_count):
        if_name = f"GigabitEthernet0/{i}" if device.device_type != "ap" else f"wlan{i}"
        if_labels = {**base_labels, "ifName": if_name, "ifAlias": f"Port {i}"}

        # Increment counters
        in_rate = random.uniform(1e5, 5e7)
        out_rate = random.uniform(1e5, 5e7)
        device.in_octets_counters[i] += in_rate * SCRAPE_INTERVAL
        device.out_octets_counters[i] += out_rate * SCRAPE_INTERVAL

        metrics.append(("ifHCInOctets", if_labels, device.in_octets_counters[i]))
        metrics.append(("ifHCOutOctets", if_labels, device.out_octets_counters[i]))
        metrics.append(("ifSpeed", if_labels, 1e9))  # 1 Gbps
        # Error counters must be monotonically increasing (they are SNMP counters)
        # Most interfaces accumulate zero new errors; ~2% get a small increment per tick
        err_key = f"err_{device.device_name}_{i}"
        disc_key = f"disc_{device.device_name}_{i}"
        if err_key not in device.__dict__:
            device.__dict__[err_key] = 0.0
            device.__dict__[disc_key] = 0.0
        if random.random() < 0.02:
            device.__dict__[err_key] += random.randint(1, 3)
        if random.random() < 0.03:
            device.__dict__[disc_key] += random.randint(1, 2)
        metrics.append(("ifInErrors", if_labels, device.__dict__[err_key]))
        metrics.append(("ifOutErrors", if_labels, device.__dict__[err_key] * 0.5))
        metrics.append(("ifInDiscards", if_labels, device.__dict__[disc_key]))
        metrics.append(("ifOutDiscards", if_labels, device.__dict__[disc_key] * 0.3))
        metrics.append(("ifOperStatus", if_labels, 1.0))  # up
        metrics.append(("ifAdminStatus", if_labels, 1.0))  # up

    return metrics


def generate_bmc_metrics(bmc: SimulatedBMC, timestamp_ms: int) -> list[tuple]:
    """Generate Redfish hardware metrics for a BMC."""
    metrics = []
    base_labels = {
        "device_name": bmc.device_name,
        "vendor": bmc.vendor,
        "bmc_type": bmc.bmc_type,
        "device_type": "server",
        "datacenter": bmc.site_code,
        "environment": "demo",
        "job": "redfish",
        "instance": bmc.instance,
    }

    # Evolve temperature slightly
    bmc.temperature = max(18.0, min(45.0, bmc.temperature + random.uniform(-0.5, 0.5)))
    bmc.power_watts = max(100.0, min(600.0, bmc.power_watts + random.uniform(-10, 10)))

    metrics.append(("redfish_health", base_labels, 0.0))  # 0 = OK
    metrics.append(("redfish_power_state", base_labels, 1.0))  # 1 = on
    metrics.append(("redfish_up", base_labels, 1.0))
    metrics.append(("up", base_labels, 1.0))

    for sensor in ["Inlet Ambient", "CPU 1", "CPU 2"]:
        temp_labels = {**base_labels, "sensor_name": sensor}
        temp = bmc.temperature + (random.uniform(5, 20) if "CPU" in sensor else 0)
        metrics.append(("redfish_temperature_celsius", temp_labels, temp))

    for ps_id in ["PSU1", "PSU2"]:
        power_labels = {**base_labels, "power_supply_id": ps_id}
        metrics.append(("redfish_power_consumed_watts", power_labels, bmc.power_watts / 2))

    return metrics


def generate_probe_metrics(endpoint: SimulatedCertEndpoint, timestamp_ms: int) -> list[tuple]:
    """Generate blackbox probe and certificate metrics."""
    metrics = []
    base_labels = {
        "instance": endpoint.address,
        "datacenter": endpoint.site_code,
        "environment": "demo",
    }
    # Add hostname and service if present (avoids empty-string labels creating duplicate series)
    hostname = getattr(endpoint, "hostname", "")
    service = getattr(endpoint, "service", "")
    if hostname:
        base_labels["hostname"] = hostname
    if service:
        base_labels["service"] = service

    # Probe success (occasional failure for realism)
    success = 1.0 if random.random() > 0.02 else 0.0
    probe_labels = {**base_labels, "job": "cert_monitor", "probe_type": "http"}
    metrics.append(("probe_success", probe_labels, success))
    metrics.append(("probe_duration_seconds", probe_labels, random.uniform(0.01, 0.5)))
    metrics.append(("up", probe_labels, 1.0))

    # Certificate expiry
    cert_labels = {**base_labels, "job": "cert_monitor", "cert_type": endpoint.cert_type}
    expiry_timestamp = time.time() + (endpoint.days_until_expiry * 86400)
    metrics.append(("probe_ssl_earliest_cert_expiry", cert_labels, expiry_timestamp))

    # up for cert_monitor job
    metrics.append(("up", {**cert_labels}, 1.0))

    return metrics


def generate_stack_self_metrics(timestamp_ms: int) -> list[tuple]:
    """Generate up metrics for the stack components (Prometheus, Grafana, etc.)."""
    metrics = []
    for job, instance in [("prometheus", "localhost:9090"),
                           ("grafana", "localhost:3000"),
                           ("alertmanager", "alertmanager:9093"),
                           ("loki", "loki:3100")]:
        metrics.append(("up", {"job": job, "instance": instance}, 1.0))
    return metrics


# =============================================================================
# Prometheus Remote Write Protocol
# =============================================================================

def _encode_varint(value: int) -> bytes:
    """Encode an integer as a protobuf varint."""
    result = []
    while value > 0x7F:
        result.append((value & 0x7F) | 0x80)
        value >>= 7
    result.append(value & 0x7F)
    return bytes(result)


def _encode_string(field_num: int, value: str) -> bytes:
    """Encode a string field in protobuf format."""
    encoded = value.encode("utf-8")
    return _encode_varint((field_num << 3) | 2) + _encode_varint(len(encoded)) + encoded


def _encode_label(name: str, value: str) -> bytes:
    """Encode a Label message (name=1, value=2)."""
    payload = _encode_string(1, name) + _encode_string(2, value)
    return payload


def _encode_sample(value: float, timestamp_ms: int) -> bytes:
    """Encode a Sample message (value=1 double, timestamp=2 int64)."""
    # Field 1: double (wire type 1 = 64-bit)
    result = _encode_varint((1 << 3) | 1) + struct.pack("<d", value)
    # Field 2: int64 (wire type 0 = varint)
    result += _encode_varint(2 << 3) + _encode_varint(timestamp_ms)
    return result


def _encode_timeseries(name: str, labels: dict, value: float, timestamp_ms: int) -> bytes:
    """Encode a single TimeSeries message."""
    # Add __name__ label first, then sorted user labels
    all_labels = {"__name__": name, **labels}
    sorted_labels = sorted(all_labels.items())

    # Encode labels (field 1, repeated Label)
    labels_payload = b""
    for lname, lvalue in sorted_labels:
        label_bytes = _encode_label(lname, str(lvalue))
        labels_payload += _encode_varint((1 << 3) | 2) + _encode_varint(len(label_bytes)) + label_bytes

    # Encode sample (field 2, repeated Sample)
    sample_bytes = _encode_sample(value, timestamp_ms)
    samples_payload = _encode_varint((2 << 3) | 2) + _encode_varint(len(sample_bytes)) + sample_bytes

    return labels_payload + samples_payload


def encode_write_request(metrics: list[tuple], timestamp_ms: int) -> bytes:
    """Encode a list of (name, labels, value) tuples into a Prometheus WriteRequest.

    Uses protobuf binary encoding matching the prometheus remote write protocol.
    """
    payload = b""
    for name, labels, value in metrics:
        ts_bytes = _encode_timeseries(name, labels, value, timestamp_ms)
        # Field 1 of WriteRequest: repeated TimeSeries
        payload += _encode_varint((1 << 3) | 2) + _encode_varint(len(ts_bytes)) + ts_bytes

    return payload


def push_to_prometheus(metrics: list[tuple], timestamp_ms: int) -> bool:
    """Push metrics to Prometheus via remote_write endpoint.

    Sends raw protobuf (snappy compressed if available, uncompressed otherwise).
    """
    if not metrics:
        return True

    # Batch in chunks to avoid oversized requests
    batch_size = 500
    for i in range(0, len(metrics), batch_size):
        batch = metrics[i : i + batch_size]
        body = encode_write_request(batch, timestamp_ms)

        headers = {
            "Content-Type": "application/x-protobuf",
            "Content-Encoding": "snappy",
            "X-Prometheus-Remote-Write-Version": "0.1.0",
        }

        if HAS_SNAPPY:
            body = snappy.compress(body)
        else:
            body = _snappy_compress_fallback(body)

        req = urllib.request.Request(PROMETHEUS_URL, data=body, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status not in (200, 204):
                    print(f"  WARNING: Prometheus returned {resp.status}")
                    return False
        except urllib.error.HTTPError as exc:
            # Read error body for debugging
            error_body = exc.read().decode("utf-8", errors="replace")[:200]
            print(f"  ERROR pushing to Prometheus: {exc.code} -- {error_body}")
            return False
        except urllib.error.URLError as exc:
            print(f"  ERROR connecting to Prometheus: {exc.reason}")
            return False

    return True


# =============================================================================
# Loki Log Push
# =============================================================================

def generate_log_entries(hosts: list[SimulatedHost], timestamp_ns: int) -> list[dict]:
    """Generate synthetic log entries matching what Alloy would push."""
    streams = []

    # Only generate logs for a subset of hosts each tick to keep volume manageable
    sample_hosts = random.sample(hosts, min(5, len(hosts)))

    for host in sample_hosts:
        labels = {
            "hostname": host.hostname,
            "os": host.os_type,
            "environment": "demo",
            "datacenter": host.site_code,
        }

        if host.os_type == "windows":
            labels["source"] = "windows_eventlog"
            labels["job"] = "windows_eventlog"
            events = [
                {"level": "info", "event_id": "7036", "source": "Service Control Manager",
                 "message": f"The Windows Time service entered the running state."},
                {"level": "info", "event_id": "4624", "source": "Security",
                 "message": "An account was successfully logged on."},
                {"level": "warning", "event_id": "1014", "source": "DNS Client Events",
                 "message": "Name resolution timed out after none of the configured DNS servers responded."},
            ]
        else:
            labels["source"] = "journal"
            labels["job"] = "linux_journal"
            events = [
                {"level": "info", "message": "Started Session 42 of user admin."},
                {"level": "info", "message": "systemd[1]: Started Docker Application Container Engine."},
                {"level": "notice", "message": "sshd[12345]: Accepted publickey for admin from 10.0.0.1 port 22."},
            ]

        event = random.choice(events)
        log_line = json.dumps(event)

        streams.append({
            "stream": labels,
            "values": [[str(timestamp_ns), log_line]],
        })

    # Audit trail logs (Grafana activity simulation)
    audit_labels = {"job": "grafana_audit", "logger": "context"}
    audit_events = [
        {"level": "info", "method": "GET", "path": "/api/dashboards/uid/enterprise-noc",
         "status": 200, "user": "admin", "action": "dashboard_view"},
        {"level": "info", "method": "GET", "path": "/d/sql-overview",
         "status": 200, "user": "admin", "action": "dashboard_view"},
        {"level": "info", "method": "POST", "path": "/login",
         "status": 200, "user": "admin", "action": "login"},
        {"level": "info", "method": "GET", "path": "/api/search",
         "status": 200, "user": "jsmith", "action": "search"},
        {"level": "warn", "method": "POST", "path": "/login",
         "status": 401, "user": "unknown", "action": "login_failed"},
    ]
    audit_event = random.choice(audit_events)
    streams.append({
        "stream": {**audit_labels, "logger": "api" if audit_event.get("method") in ("POST", "PUT", "DELETE") else "context"},
        "values": [[str(timestamp_ns + 1000), json.dumps(audit_event)]],
    })

    return streams


def push_to_loki(streams: list[dict]) -> bool:
    """Push log entries to Loki via push API."""
    if not streams:
        return True

    body = json.dumps({"streams": streams}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    req = urllib.request.Request(LOKI_URL, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status not in (200, 204):
                print(f"  WARNING: Loki returned {resp.status}")
                return False
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")[:200]
        print(f"  ERROR pushing to Loki: {exc.code} -- {error_body}")
        return False
    except urllib.error.URLError as exc:
        print(f"  ERROR connecting to Loki: {exc.reason}")
        return False

    return True


# =============================================================================
# Main Loop
# =============================================================================

def run_single_tick(inventory: dict, timestamp_ms: int) -> tuple[int, int]:
    """Generate and push one scrape interval's worth of data.

    Returns (metrics_count, logs_count).
    """
    all_metrics = []

    # Server metrics
    for host in inventory["hosts"]:
        all_metrics.extend(generate_host_metrics(host, timestamp_ms))

    # Network device metrics
    for device in inventory["network_devices"]:
        all_metrics.extend(generate_network_device_metrics(device, timestamp_ms))

    # BMC metrics
    for bmc in inventory["bmcs"]:
        all_metrics.extend(generate_bmc_metrics(bmc, timestamp_ms))

    # Probe/cert metrics
    for endpoint in inventory["cert_endpoints"]:
        all_metrics.extend(generate_probe_metrics(endpoint, timestamp_ms))

    # Stack self-monitoring
    all_metrics.extend(generate_stack_self_metrics(timestamp_ms))

    # Push metrics
    push_ok = push_to_prometheus(all_metrics, timestamp_ms)

    # Push logs
    timestamp_ns = timestamp_ms * 1_000_000
    log_streams = generate_log_entries(inventory["hosts"], timestamp_ns)
    logs_ok = push_to_loki(log_streams)

    if not push_ok:
        print(f"  WARNING: Metrics push had errors at {timestamp_ms}")
    if not logs_ok:
        print(f"  WARNING: Logs push had errors at {timestamp_ms}")

    return len(all_metrics), len(log_streams)


def backfill(inventory: dict, minutes: int) -> None:
    """Seed initial data by pushing rapid ticks at current timestamps.

    Prometheus v2.x does not support out-of-order ingestion, so we cannot
    backfill with past timestamps. Instead, we push multiple ticks rapidly
    at the current time. This gives recording rules enough data points to
    begin computing (rate/avg_over_time need 2+ samples).
    """
    # Push enough ticks for rate() to compute (needs 2+ samples per series)
    # and for avg_over_time windows to populate. Push 10 ticks rapidly.
    total_ticks = min(10, max(2, (minutes * 60) // SCRAPE_INTERVAL))

    print(f"Seeding {total_ticks} data points (rapid push at current time)...")
    print("  Recording rules need 2+ samples to compute rate().")

    for i in range(total_ticks):
        ts_ms = int(time.time() * 1000)
        metric_count, log_count = run_single_tick(inventory, ts_ms)
        print(f"  [{i + 1}/{total_ticks}] {metric_count} metrics, {log_count} log streams")
        # Brief pause between ticks so timestamps differ
        if i < total_ticks - 1:
            time.sleep(2)

    print("Seeding complete. Recording rules will begin computing on next evaluation cycle (30s).")


def run_continuous(inventory: dict) -> None:
    """Push data every SCRAPE_INTERVAL seconds until interrupted."""
    print(f"Running continuous mode (every {SCRAPE_INTERVAL}s). Ctrl+C to stop.")

    while True:
        ts_ms = int(time.time() * 1000)
        metric_count, log_count = run_single_tick(inventory, ts_ms)
        print(f"  Pushed {metric_count} metrics, {log_count} log streams")
        time.sleep(SCRAPE_INTERVAL)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate demo data for monitoring stack dashboards"
    )
    parser.add_argument(
        "--config", type=Path, default=PROJECT_ROOT / "deploy" / "site_config.yml",
        help="Path to site_config.yml",
    )
    parser.add_argument(
        "--backfill", type=int, default=0,
        help="Minutes of historical data to backfill (default: from config or 30)",
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Push one tick of data and exit (no continuous loop)",
    )
    global PROMETHEUS_URL, LOKI_URL

    parser.add_argument(
        "--prometheus-url", default=PROMETHEUS_URL,
        help="Prometheus remote_write URL",
    )
    parser.add_argument(
        "--loki-url", default=LOKI_URL,
        help="Loki push URL",
    )
    args = parser.parse_args()

    PROMETHEUS_URL = args.prometheus_url
    LOKI_URL = args.loki_url

    # Load config
    if not args.config.exists():
        print(f"ERROR: Config not found: {args.config}")
        print("Run deploy_configure.py first to generate site_config.yml")
        return 1

    with open(args.config) as f:
        config = yaml.safe_load(f)

    # Build inventory
    inventory = build_inventory(config)
    host_count = len(inventory["hosts"])
    device_count = len(inventory["network_devices"])
    bmc_count = len(inventory["bmcs"])
    cert_count = len(inventory["cert_endpoints"])
    site_count = len(config.get("sites", []))

    print()
    print("=" * 60)
    print("  Demo Data Generator")
    print("=" * 60)
    print(f"  Sites:             {site_count}")
    print(f"  Servers:           {host_count}")
    print(f"  Network devices:   {device_count}")
    print(f"  BMC endpoints:     {bmc_count}")
    print(f"  Cert endpoints:    {cert_count}")
    print(f"  Prometheus:        {PROMETHEUS_URL}")
    print(f"  Loki:              {LOKI_URL}")
    print()

    # Determine backfill minutes
    backfill_min = args.backfill
    if backfill_min == 0:
        backfill_min = config.get("demo", {}).get("backfill_minutes", 30)

    # Backfill historical data
    if backfill_min > 0:
        backfill(inventory, backfill_min)

    if args.once:
        print("Single push complete.")
        return 0

    # Continuous mode
    try:
        run_continuous(inventory)
    except KeyboardInterrupt:
        print("\nStopped.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
