#!/usr/bin/env python3
"""
Deployment Configuration Wrapper

Generates all monitoring stack config files from a single site inventory.
Supports both interactive mode (prompts) and file mode (--config).

Usage:
    python scripts/deploy_configure.py                         # Interactive
    python scripts/deploy_configure.py --config deploy/site_config.yml  # From file
    python scripts/deploy_configure.py --config deploy/site_config.yml --dry-run

Generated files:
    .env                                    Stack-wide environment variables
    inventory/sites.yml                     Site registry (populated)
    inventory/hosts.yml                     Host inventory (demo entries if enabled)
    configs/alertmanager/alertmanager.yml   Per-site receivers and routes
    configs/grafana/notifiers/notifiers.yml Per-site Grafana contact points
"""

import argparse
import copy
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Default role mix for demo data generation
DEFAULT_HOST_PROFILE = {
    "dc": 2,
    "sql": 2,
    "iis": 3,
    "fileserver": 2,
    "docker": 2,
    "generic": 3,
}

VALID_ROLES = ["dc", "sql", "iis", "fileserver", "dhcp", "ca", "docker", "generic"]


# =============================================================================
# Interactive Prompt Helpers
# =============================================================================

def prompt(label: str, default: str = "", required: bool = True) -> str:
    """Prompt user for input with an optional default value."""
    if default:
        raw = input(f"  {label} [{default}]: ").strip()
        return raw if raw else default
    raw = input(f"  {label}: ").strip()
    if raw:
        return raw
    if not required:
        return ""
    while not raw:
        print("    (required)")
        raw = input(f"  {label}: ").strip()
    return raw


def prompt_yes_no(label: str, default: bool = True) -> bool:
    """Prompt user for a yes/no answer."""
    hint = "Y/n" if default else "y/N"
    raw = input(f"  {label} [{hint}]: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes")


def prompt_int(label: str, default: int) -> int:
    """Prompt user for an integer value."""
    raw = input(f"  {label} [{default}]: ").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        print(f"    Invalid number, using default: {default}")
        return default


# =============================================================================
# Interactive Configuration Builder
# =============================================================================

def collect_interactive() -> dict:
    """Walk user through all deployment settings via interactive prompts."""
    config = {"stack": {}, "notifications": {"smtp": {}}, "sites": [], "demo": {}}

    print()
    print("=" * 60)
    print("  Monitoring Stack -- Deployment Configuration")
    print("=" * 60)

    # -- Stack-wide settings --
    print()
    print("-- Stack Settings --")
    config["stack"]["cluster_name"] = prompt(
        "Cluster name (external label on all metrics)", "monitoring-prod"
    )
    config["stack"]["grafana_admin_user"] = prompt("Grafana admin username", "admin")
    config["stack"]["grafana_admin_password"] = prompt(
        "Grafana admin password", "admin"
    )
    config["stack"]["retention_time"] = prompt("Prometheus retention time", "15d")
    config["stack"]["retention_size"] = prompt("Prometheus retention size", "5GB")

    # -- Notification settings --
    print()
    print("-- Notification Settings --")
    config["notifications"]["teams_webhook_url"] = prompt(
        "Teams webhook URL (or press Enter for placeholder)",
        "https://example.com/webhook/placeholder",
    )

    print()
    print("  SMTP Configuration (for email alerts):")
    config["notifications"]["smtp"]["host"] = prompt(
        "    SMTP host", "smtp.example.com"
    )
    config["notifications"]["smtp"]["port"] = prompt_int("    SMTP port", 587)
    config["notifications"]["smtp"]["from_address"] = prompt(
        "    From address", "monitoring@example.com"
    )
    config["notifications"]["smtp"]["auth_username"] = prompt(
        "    Auth username", "monitoring@example.com"
    )
    config["notifications"]["smtp"]["auth_password"] = prompt(
        "    Auth password", "changeme"
    )
    config["notifications"]["smtp"]["require_tls"] = prompt_yes_no(
        "    Require TLS?", True
    )

    config["notifications"]["default_email"] = prompt(
        "Default catch-all ops email", "ops-team@example.com"
    )

    # -- Sites --
    print()
    print("-- Site Definitions --")
    print("  Enter site codes one at a time. Empty code to finish.")
    print()

    while True:
        code = input("  Site code (e.g., ENT, DV): ").strip().lower()
        if not code:
            if not config["sites"]:
                print("    At least one site is required.")
                continue
            break

        # Validate site code format
        if not re.match(r"^[a-z][a-z0-9_-]*$", code):
            print("    Invalid code. Use lowercase letters, numbers, hyphens, underscores.")
            continue

        site = {"code": code}
        site["display_name"] = prompt(f"    Display name for '{code}'")
        site["contact_email"] = prompt(
            f"    Ops email for '{code}'", f"{code}-ops@example.com"
        )
        site["timezone"] = prompt("    Timezone", "America/Denver")

        site["gateway"] = {}
        if prompt_yes_no("    Enable site gateway (SNMP/Redfish/certs)?", True):
            site["gateway"]["snmp"] = prompt_yes_no("      SNMP polling?", True)
            site["gateway"]["redfish"] = prompt_yes_no("      Redfish BMC?", True)
            site["gateway"]["certs"] = prompt_yes_no("      Certificate probing?", True)
        else:
            site["gateway"]["snmp"] = False
            site["gateway"]["redfish"] = False
            site["gateway"]["certs"] = False

        config["sites"].append(site)
        print(f"    Added site: {code} ({site['display_name']})")
        print()

    # -- Demo data --
    print()
    print("-- Demo Data --")
    config["demo"]["enabled"] = prompt_yes_no(
        "Generate demo data for showcasing dashboards?", True
    )
    if config["demo"]["enabled"]:
        print("  Host profile per site (how many simulated hosts per role):")
        profile = {}
        for role in VALID_ROLES:
            profile[role] = prompt_int(
                f"    {role}", DEFAULT_HOST_PROFILE.get(role, 2)
            )
        config["demo"]["host_profile"] = profile
        config["demo"]["backfill_minutes"] = prompt_int(
            "  Backfill minutes (for recording rules/SLA)", 30
        )
    else:
        config["demo"]["host_profile"] = DEFAULT_HOST_PROFILE
        config["demo"]["backfill_minutes"] = 30

    return config


# =============================================================================
# Config File Generators
# =============================================================================

def generate_env_file(config: dict) -> str:
    """Generate .env file content from deployment config."""
    notif = config["notifications"]
    smtp = notif["smtp"]
    stack = config["stack"]
    sites = config["sites"]

    lines = [
        "# Generated by deploy_configure.py -- do not commit to version control",
        "",
        "# -- Service URLs (Docker Compose internal) --",
        "PROMETHEUS_URL=http://prometheus:9090",
        "LOKI_URL=http://loki:3100",
        "GRAFANA_URL=http://grafana:3000",
        "ALERTMANAGER_URL=http://alertmanager:9093",
        "",
        "# -- Prometheus Retention --",
        f"PROMETHEUS_RETENTION_DAYS={stack.get('retention_time', '15d').rstrip('d')}",
        "",
        "# -- Microsoft Teams --",
        f"TEAMS_WEBHOOK_URL={notif['teams_webhook_url']}",
        "",
        "# -- SMTP --",
        f"SMTP_HOST={smtp['host']}",
        f"SMTP_PORT={smtp['port']}",
        f"SMTP_FROM={smtp['from_address']}",
        f"SMTP_AUTH_USERNAME={smtp['auth_username']}",
        f"SMTP_AUTH_PASSWORD={smtp['auth_password']}",
        "",
        "# -- Default Email --",
        f"ALERT_EMAIL_TO={notif['default_email']}",
        "",
        "# -- Per-Site Email Distribution Lists --",
    ]

    for site in sites:
        var_name = f"SITE_{site['code'].upper().replace('-', '_')}_EMAIL"
        lines.append(f"{var_name}={site['contact_email']}")

    lines.append("")
    return "\n".join(lines)


def generate_sites_yml(config: dict) -> str:
    """Generate inventory/sites.yml from deployment config."""
    data = {
        "valid_roles": VALID_ROLES,
        "valid_os": ["windows", "linux"],
        "sites": {},
    }

    for site in config["sites"]:
        entry = {
            "display_name": site["display_name"],
            "timezone": site.get("timezone", "America/Denver"),
            "environment": site.get("environment", "prod"),
            "contact_email": site["contact_email"],
        }
        if site.get("network_segment"):
            entry["network_segment"] = site["network_segment"]

        gw = site.get("gateway", {})
        entry["gateway"] = {
            "enabled": any(gw.values()),
            "snmp_targets": gw.get("snmp", False),
            "redfish_targets": gw.get("redfish", False),
            "cert_targets": gw.get("certs", False),
        }

        data["sites"][site["code"]] = entry

    # Use block style for readability
    header = (
        "# Site Registry -- Generated by deploy_configure.py\n"
        "# Re-run the wrapper to add or modify sites.\n"
        "#\n"
        "# Usage: python3 scripts/fleet_inventory.py validate\n\n"
    )
    return header + yaml.dump(data, default_flow_style=False, sort_keys=False)


def generate_hosts_yml(config: dict) -> str:
    """Generate inventory/hosts.yml with demo host entries if enabled."""
    header = (
        "# Host Inventory -- Generated by deploy_configure.py\n"
        "# Demo hosts are simulated entries for dashboard showcasing.\n\n"
    )

    hosts = {}
    demo = config.get("demo", {})

    if demo.get("enabled", False):
        profile = demo.get("host_profile", DEFAULT_HOST_PROFILE)

        for site in config["sites"]:
            code = site["code"]
            host_num = 1

            for role, count in profile.items():
                os_type = "linux" if role == "docker" else "windows"
                for i in range(count):
                    hostname = f"srv-{role}-{host_num:02d}.{code}"
                    hosts[hostname] = {
                        "site": code,
                        "roles": [role],
                        "os": os_type,
                        "ip": f"10.{hash(code) % 250}.{host_num // 255}.{host_num % 255}",
                        "source": "demo",
                    }
                    host_num += 1

    data = {"hosts": hosts if hosts else {}}
    return header + yaml.dump(data, default_flow_style=False, sort_keys=False)


def _site_receiver_block(site_code: str, email: str, webhook_url: str) -> list[dict]:
    """Generate critical + warning receiver entries for a single site."""
    safe_name = site_code.replace("-", "_")
    return [
        {
            "name": f"{safe_name}_critical",
            "webhook_configs": [
                {"url": webhook_url, "send_resolved": True}
            ],
            "email_configs": [
                {
                    "to": email,
                    "send_resolved": True,
                    "headers": {
                        "Subject": f"[CRITICAL] [{site_code}] "
                        "{{ .GroupLabels.alertname }} in {{ .GroupLabels.datacenter }} ({{ .Alerts | len }} host(s))"
                    },
                }
            ],
        },
        {
            "name": f"{safe_name}_warning",
            "webhook_configs": [
                {"url": webhook_url, "send_resolved": True}
            ],
            "email_configs": [
                {
                    "to": email,
                    "send_resolved": True,
                    "headers": {
                        "Subject": f"[WARNING] [{site_code}] "
                        "{{ .GroupLabels.alertname }} in {{ .GroupLabels.datacenter }} ({{ .Alerts | len }} host(s))"
                    },
                }
            ],
        },
    ]


def _site_route_entries(site_code: str) -> list[dict]:
    """Generate critical + warning route match entries for a single site."""
    safe_name = site_code.replace("-", "_")
    return [
        {
            "match": {"datacenter": site_code},
            "receiver": f"{safe_name}_critical",
            "continue": False,
        },
        {
            "match": {"datacenter": site_code},
            "receiver": f"{safe_name}_warning",
            "continue": False,
        },
    ]


def generate_alertmanager_yml(config: dict) -> str:
    """Generate full alertmanager.yml with per-site receivers and routes."""
    notif = config["notifications"]
    smtp = notif["smtp"]
    webhook = notif["teams_webhook_url"]
    default_email = notif["default_email"]
    sites = config["sites"]

    # Build critical routes (per-site match blocks)
    critical_routes = []
    for site in sites:
        safe_name = site["code"].replace("-", "_")
        critical_routes.append({
            "match": {"datacenter": site["code"]},
            "receiver": f"{safe_name}_critical",
            "continue": False,
        })
    # Fallback for unmapped datacenters
    critical_routes.append({"receiver": "teams_and_email"})

    # Build warning routes (per-site match blocks)
    warning_routes = []
    for site in sites:
        safe_name = site["code"].replace("-", "_")
        warning_routes.append({
            "match": {"datacenter": site["code"]},
            "receiver": f"{safe_name}_warning",
            "continue": False,
        })
    warning_routes.append({"receiver": "teams_default"})

    # Build receivers list
    receivers = [
        {
            "name": "teams_default",
            "webhook_configs": [{"url": webhook, "send_resolved": True}],
        },
        {
            "name": "teams_and_email",
            "webhook_configs": [{"url": webhook, "send_resolved": True}],
            "email_configs": [
                {
                    "to": default_email,
                    "send_resolved": True,
                    "headers": {
                        "Subject": "[CRITICAL] {{ .GroupLabels.alertname }} in "
                        "{{ .GroupLabels.datacenter }} ({{ .Alerts | len }} host(s))"
                    },
                }
            ],
        },
        {
            "name": "teams_info",
            "webhook_configs": [{"url": webhook, "send_resolved": False}],
        },
    ]

    # Per-site receivers (critical + warning for each site)
    for site in sites:
        receivers.extend(
            _site_receiver_block(site["code"], site["contact_email"], webhook)
        )

    # Assemble the full alertmanager config
    am_config = {
        "global": {
            "resolve_timeout": "5m",
            "smtp_smarthost": f"{smtp['host']}:{smtp['port']}",
            "smtp_from": smtp["from_address"],
            "smtp_require_tls": smtp.get("require_tls", True),
            "smtp_auth_username": smtp["auth_username"],
            "smtp_auth_password": smtp["auth_password"],
        },
        "templates": ["/etc/alertmanager/templates/*.tmpl"],
        "route": {
            "receiver": "teams_default",
            "group_by": ["alertname", "datacenter"],
            "group_wait": "60s",
            "group_interval": "5m",
            "repeat_interval": "4h",
            "routes": [
                {
                    "match": {"severity": "critical"},
                    "group_wait": "15s",
                    "repeat_interval": "1h",
                    "routes": critical_routes,
                    "continue": False,
                },
                {
                    "match": {"severity": "warning"},
                    "group_wait": "60s",
                    "repeat_interval": "4h",
                    "routes": warning_routes,
                    "continue": False,
                },
                {
                    "match": {"severity": "info"},
                    "receiver": "teams_info",
                    "repeat_interval": "12h",
                    "continue": False,
                },
            ],
        },
        "inhibit_rules": [
            # Server down suppresses per-host warnings
            {
                "source_matchers": [
                    'alertname =~ "WindowsServerDown|LinuxServerDown"'
                ],
                "target_matchers": ['severity =~ "warning|info"'],
                "equal": ["hostname"],
            },
            # Prometheus notification failures suppress fleet alerts
            {
                "source_matchers": [
                    'alertname = "PrometheusNotificationsFailing"'
                ],
                "target_matchers": ['alertname =~ "Fleet.*"'],
            },
            # Critical suppresses warning on same host to prevent duplicate
            # notifications when a warning escalates to critical
            {
                "source_matchers": ['severity = "critical"'],
                "target_matchers": ['severity = "warning"'],
                "equal": ["hostname", "datacenter"],
            },
            # Mass-outage: major outage suppresses all per-host alerts at site
            {
                "source_matchers": ['alertname = "SiteMajorOutage"'],
                "target_matchers": [
                    'severity =~ "critical|warning"',
                    'outage_scope != "site"',
                ],
                "equal": ["datacenter"],
            },
            # Partial outage suppresses per-host warnings at site
            {
                "source_matchers": ['alertname = "SitePartialOutage"'],
                "target_matchers": [
                    'severity = "warning"',
                    'outage_scope != "site"',
                ],
                "equal": ["datacenter"],
            },
            # Role outage suppresses per-host warnings for that role
            {
                "source_matchers": ['alertname = "RolePartialOutage"'],
                "target_matchers": [
                    'severity = "warning"',
                    'outage_scope != "role"',
                ],
                "equal": ["datacenter", "role"],
            },
        ],
        "receivers": receivers,
    }

    header = (
        "# =============================================================================\n"
        "# Alertmanager Configuration -- Generated by deploy_configure.py\n"
        "# =============================================================================\n"
        "# Re-run the wrapper to regenerate after adding sites.\n"
        f"# Sites configured: {', '.join(s['code'] for s in sites)}\n"
        "# =============================================================================\n\n"
    )

    return header + yaml.dump(
        am_config, default_flow_style=False, sort_keys=False, width=120
    )


def generate_notifiers_yml(config: dict) -> str:
    """Generate Grafana notifiers/notifiers.yml with per-site contact points."""
    sites = config["sites"]

    contact_points = [
        {
            "orgId": 1,
            "name": "Microsoft Teams",
            "receivers": [
                {
                    "uid": "teams-webhook",
                    "type": "teams",
                    "settings": {
                        "url": "${TEAMS_WEBHOOK_URL}",
                        "title": "[{{ .Status | toUpper }}] {{ .CommonLabels.alertname }}",
                        "sectiontitle": "{{ .CommonLabels.hostname }} ({{ .CommonLabels.environment }})",
                        "text": "{{ .CommonAnnotations.summary }}",
                    },
                    "disableResolveMessage": False,
                }
            ],
        },
        {
            "orgId": 1,
            "name": "Email Fallback",
            "receivers": [
                {
                    "uid": "email-fallback",
                    "type": "email",
                    "settings": {
                        "addresses": "${ALERT_EMAIL_TO:-ops-team@example.com}",
                        "singleEmail": True,
                    },
                    "disableResolveMessage": False,
                }
            ],
        },
    ]

    # Per-site email contact points
    for site in sites:
        code = site["code"]
        var_name = f"SITE_{code.upper().replace('-', '_')}_EMAIL"
        contact_points.append({
            "orgId": 1,
            "name": f"{code.upper()} Email",
            "receivers": [
                {
                    "uid": f"email-{code}",
                    "type": "email",
                    "settings": {
                        "addresses": f"${{{var_name}:-{site['contact_email']}}}",
                        "singleEmail": True,
                    },
                    "disableResolveMessage": False,
                }
            ],
        })

    # Build notification policy routes
    critical_site_routes = []
    warning_site_routes = []
    for site in sites:
        code = site["code"]
        critical_site_routes.append({
            "receiver": f"{code.upper()} Email",
            "matchers": [f"datacenter = {code}"],
            "continue": True,
        })
        warning_site_routes.append({
            "receiver": f"{code.upper()} Email",
            "matchers": [f"datacenter = {code}"],
            "continue": True,
        })

    policies = [
        {
            "orgId": 1,
            "receiver": "Microsoft Teams",
            "group_by": ["alertname", "datacenter"],
            "group_wait": "60s",
            "group_interval": "5m",
            "repeat_interval": "4h",
            "routes": [
                {
                    "receiver": "Email Fallback",
                    "matchers": ["severity = critical"],
                    "continue": True,
                    "group_wait": "15s",
                    "repeat_interval": "1h",
                    "routes": critical_site_routes,
                },
                {
                    "receiver": "Microsoft Teams",
                    "matchers": ["severity = warning"],
                    "continue": False,
                    "group_wait": "60s",
                    "repeat_interval": "4h",
                    "routes": warning_site_routes,
                },
                {
                    "receiver": "Microsoft Teams",
                    "matchers": ["severity = info"],
                    "continue": False,
                    "repeat_interval": "12h",
                },
            ],
        }
    ]

    data = {
        "apiVersion": 1,
        "contactPoints": contact_points,
        "policies": policies,
        "muteTimes": [],
    }

    header = (
        "# =============================================================================\n"
        "# Grafana Notification Provisioning -- Generated by deploy_configure.py\n"
        "# =============================================================================\n"
        f"# Sites configured: {', '.join(s['code'] for s in sites)}\n"
        "# =============================================================================\n\n"
    )

    return header + yaml.dump(
        data, default_flow_style=False, sort_keys=False, width=120
    )


# =============================================================================
# Validation
# =============================================================================

def validate_config(config: dict) -> list[str]:
    """Validate deployment config and return list of issues (empty = valid)."""
    issues = []

    if not config.get("sites"):
        issues.append("No sites defined")

    seen_codes = set()
    for site in config.get("sites", []):
        code = site.get("code", "")
        if not code:
            issues.append("Site missing 'code' field")
        elif not re.match(r"^[a-z][a-z0-9_-]*$", code):
            issues.append(
                f"Site code '{code}' invalid -- use lowercase, start with letter"
            )
        if code in seen_codes:
            issues.append(f"Duplicate site code: {code}")
        seen_codes.add(code)

        if not site.get("display_name"):
            issues.append(f"Site '{code}' missing display_name")
        if not site.get("contact_email"):
            issues.append(f"Site '{code}' missing contact_email")

    smtp = config.get("notifications", {}).get("smtp", {})
    if not smtp.get("host"):
        issues.append("SMTP host not configured")

    # Validate demo host profile roles
    demo = config.get("demo", {})
    if demo.get("enabled"):
        profile = demo.get("host_profile", {})
        for role in profile:
            if role not in VALID_ROLES:
                issues.append(f"Demo host_profile contains invalid role: '{role}'")

    return issues


# Role co-location conflict rules. Key = role, value = set of conflicting roles.
# DC already collects DHCP/DNS metrics; deploying both causes duplicate collection.
ROLE_CONFLICTS = {
    "dc": {"dhcp"},
    "dhcp": {"dc"},
}

# Role-to-config-to-dashboard mapping for operator reference
ROLE_REFERENCE = {
    "dc":         {"config": "role_dc.alloy",         "job": "windows_dc",         "dashboard": "Domain Controller Overview",  "os": "windows", "includes": "AD DS, DNS, DHCP (if co-located)"},
    "sql":        {"config": "role_sql.alloy",         "job": "windows_sql",        "dashboard": "SQL Server Overview",         "os": "windows", "includes": "MSSQL perf counters, SQL Agent"},
    "iis":        {"config": "role_iis.alloy",         "job": "windows_iis",        "dashboard": "IIS Web Server Overview",     "os": "windows", "includes": "Request rates, app pools, W3C logs"},
    "fileserver": {"config": "role_fileserver.alloy",  "job": "windows_fileserver", "dashboard": "File Server Overview",        "os": "windows", "includes": "SMB sessions, disk I/O, FSRM quotas"},
    "dhcp":       {"config": "role_dhcp.alloy",        "job": "windows_dhcp",       "dashboard": "DHCP Server Overview",        "os": "windows", "includes": "DHCP messages, scope stats"},
    "ca":         {"config": "role_ca.alloy",          "job": "windows_ca",         "dashboard": "Certificate Authority Overview", "os": "windows", "includes": "AD CS requests, issuance, CRL"},
    "docker":     {"config": "role_docker.alloy",      "job": "docker_daemon",      "dashboard": "Docker Host Overview",        "os": "linux",   "includes": "Container states, engine metrics"},
    "generic":    {"config": "(base.alloy only)",      "job": "windows_base/linux_base", "dashboard": "Windows/Linux Overview", "os": "both",    "includes": "OS-level metrics only"},
}


def check_role_conflicts(hosts_config: dict) -> list[str]:
    """Check for role co-location conflicts in host inventory."""
    warnings = []
    for hostname, host in hosts_config.items():
        roles = set(host.get("roles", []))
        for role in roles:
            conflicts = ROLE_CONFLICTS.get(role, set())
            overlaps = roles & conflicts
            if overlaps:
                warnings.append(
                    f"Host '{hostname}': role '{role}' conflicts with {overlaps} "
                    f"(duplicate metric collection). Use only one."
                )
    return warnings


# =============================================================================
# File Writer
# =============================================================================

def write_generated_files(config: dict, dry_run: bool = False) -> None:
    """Generate and write all config files from deployment config."""
    files = {
        PROJECT_ROOT / ".env": generate_env_file(config),
        PROJECT_ROOT / "inventory" / "sites.yml": generate_sites_yml(config),
        PROJECT_ROOT / "inventory" / "hosts.yml": generate_hosts_yml(config),
        PROJECT_ROOT / "configs" / "alertmanager" / "alertmanager.yml": generate_alertmanager_yml(config),
        PROJECT_ROOT / "configs" / "grafana" / "notifiers" / "notifiers.yml": generate_notifiers_yml(config),
    }

    # Save the site_config.yml for future re-runs
    config_out = PROJECT_ROOT / "deploy" / "site_config.yml"
    files[config_out] = (
        "# Deployment config -- generated by deploy_configure.py interactive mode\n"
        "# Re-run with: python scripts/deploy_configure.py --config deploy/site_config.yml\n\n"
        + yaml.dump(config, default_flow_style=False, sort_keys=False, width=120)
    )

    site_list = ", ".join(s["code"] for s in config["sites"])

    if dry_run:
        print()
        print("DRY RUN -- Files that would be generated:")
        print("-" * 60)
        for path, content in files.items():
            rel = path.relative_to(PROJECT_ROOT)
            line_count = content.count("\n")
            print(f"  {rel} ({line_count} lines)")
        print()
        print(f"Sites: {site_list}")
        print(f"Demo data: {'enabled' if config.get('demo', {}).get('enabled') else 'disabled'}")
        return

    print()
    print("Writing configuration files...")

    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        rel = path.relative_to(PROJECT_ROOT)
        print(f"  {rel}")

    print()
    print("=" * 60)
    print("  Configuration Complete")
    print("=" * 60)
    print(f"  Sites configured: {site_list}")
    print(f"  Demo data: {'enabled' if config.get('demo', {}).get('enabled') else 'disabled'}")
    print()
    print("  Next steps:")
    print("    1. Review generated files (especially .env)")
    print("    2. Start the stack:")
    print("       python scripts/stack_manage.py")
    if config.get("demo", {}).get("enabled"):
        print("    3. Start with demo data:")
        print("       python scripts/stack_manage.py --demo-data")
    print()
    print("  To reconfigure, re-run this script.")
    print("  To add sites, edit deploy/site_config.yml and re-run with --config.")


# =============================================================================
# Main
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate monitoring stack config files from site inventory"
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to site_config.yml (skip interactive prompts)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be generated without writing files",
    )
    args = parser.parse_args()

    if args.config:
        if not args.config.exists():
            print(f"ERROR: Config file not found: {args.config}")
            return 1
        with open(args.config) as f:
            config = yaml.safe_load(f)
    else:
        config = collect_interactive()

    # Validate
    issues = validate_config(config)
    if issues:
        print()
        print("Configuration errors:")
        for issue in issues:
            print(f"  - {issue}")
        return 1

    write_generated_files(config, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
