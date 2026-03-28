#!/usr/bin/env python3
"""
Seeds the SCOM DW Simulator (Azure SQL Edge) with production-aligned schema.
Run after the scom-dw-sim container is healthy.

Schema matches production OperationsManagerDW (discovered 2026-03-25):
  - vPerformanceRule (separate table for ObjectName/CounterName)
  - vPerformanceRuleInstance (RuleRowId reference)
  - Entity type: Microsoft.Windows.Computer
  - Hostname pattern: VM-<SITE>-<ROLE><NUM>

Usage:
    python scripts/scom_dw_seed_runner.py
"""

import os
import sys
import time
import random
from datetime import datetime, timezone, timedelta

try:
    import pymssql
except ImportError:
    print("ERROR: pymssql required. Install: pip install pymssql")
    sys.exit(1)

# Connection settings from environment (for Docker) or defaults (for local)
HOST = os.environ.get("SCOM_DW_HOST", "localhost")
PORT = int(os.environ.get("SCOM_DW_PORT", "1433"))
USER = os.environ.get("SCOM_DW_SA_USER", "sa")
PASSWORD = os.environ.get("SCOM_DW_SA_PASSWORD", "ScomDemo123!")
DB = "OperationsManagerDW"
MAX_WAIT = int(os.environ.get("SCOM_DW_WAIT_SECONDS", "120"))

# Generic site codes for simulator (production sites populate dynamically from SCOM DW)
SITES = ["ALPHA", "BRAVO", "CHARLIE", "DELTA", "ECHO", "FOXTROT", "GOLF", "HOTEL", "JULIET"]

# Server roles per site
ROLES = ["DC", "SQL", "IIS", "FS", "APP", "DHCP"]

# Counter names matching standard SCOM Management Pack conventions
# Format: (ObjectName, CounterName, InstanceName, role_filter)
# role_filter: None = all servers, "DC" = DC only, "IIS" = IIS only, etc.
COUNTERS = [
    # Windows OS -- all servers
    ("Processor Information", "% Processor Time", "_Total", None),
    ("Memory", "PercentMemoryUsed", "", None),
    ("Memory", "Available MBytes", "", None),
    ("Memory", "Pages/sec", "", None),
    ("LogicalDisk", "% Free Space", "C:", None),
    ("LogicalDisk", "% Free Space", "D:", None),
    ("LogicalDisk", "Free Megabytes", "C:", None),
    ("LogicalDisk", "Free Megabytes", "D:", None),
    ("LogicalDisk", "% Idle Time", "C:", None),
    ("LogicalDisk", "Avg. Disk sec/Transfer", "C:", None),
    ("LogicalDisk", "Avg. Disk sec/Transfer", "D:", None),
    ("LogicalDisk", "Current Disk Queue Length", "C:", None),
    ("Network Adapter", "Bytes Total/sec", "Ethernet0", None),
    ("Network Adapter", "Current Bandwidth", "Ethernet0", None),
    ("Network Adapter", "PercentBandwidthUsedTotal", "Ethernet0", None),
    ("System", "Processor Queue Length", "", None),
    ("System", "System Up Time", "", None),
    # AD/DC -- DirectoryServices (production ObjectName, not NTDS)
    ("DirectoryServices", "LDAP Searches/sec", "", "DC"),
    ("DirectoryServices", "LDAP Client Sessions", "", "DC"),
    ("DirectoryServices", "LDAP Writes/sec", "", "DC"),
    ("DirectoryServices", "DRA Inbound Bytes Total/sec", "", "DC"),
    ("DirectoryServices", "DRA Outbound Bytes Total/sec", "", "DC"),
    ("DirectoryServices", "DS Search sub-operations/sec", "", "DC"),
    ("Security System-Wide Statistics", "Kerberos Authentications", "", "DC"),
    ("Security System-Wide Statistics", "NTLM Authentications", "", "DC"),
    ("Security System-Wide Statistics", "KDC AS Requests", "", "DC"),
    ("Security System-Wide Statistics", "KDC TGS Requests", "", "DC"),
    # DNS -- DC servers
    ("DNS", "Total Query Received/sec", "", "DC"),
    ("DNS", "Recursive Queries/sec", "", "DC"),
    ("DNS", "Dynamic Update Received/sec", "", "DC"),
    # IIS -- Web Service counters
    ("Web Service", "Current Connections", "_Total", "IIS"),
    ("Web Service", "Total Method Requests/sec", "_Total", "IIS"),
    ("Web Service", "Bytes Total/sec", "_Total", "IIS"),
    ("Web Service", "Bytes Received/sec", "_Total", "IIS"),
    ("Web Service", "Bytes Sent/sec", "_Total", "IIS"),
    ("Web Service", "Connection Attempts/sec", "_Total", "IIS"),
    # DHCP
    ("DHCP Server", "Acks/sec", "", "DHCP"),
    ("DHCP Server", "Requests/sec", "", "DHCP"),
    ("DHCP Server", "Discovers/sec", "", "DHCP"),
    ("DHCP Server", "Active Queue Length", "", "DHCP"),
    ("DHCP Server", "Packets Received/sec", "", "DHCP"),
    # AD Storage -- DC servers
    ("AD Storage", "Database Size", "", "DC"),
    ("AD Storage", "Database Drive Free Space", "", "DC"),
    ("AD Storage", "Log File Drive Free Space", "", "DC"),
    # DFS -- DC and FS servers
    ("DFS Replicated Folders", "Staging Space In Use", "", "DC,FS"),
    ("DFS Replicated Folders", "Conflict Space In Use", "", "DC,FS"),
    ("DFS Replication Connections", "Bandwidth Savings Using DFS Replication", "", "DC,FS"),
    # Kernel memory and connections -- all servers
    ("Memory", "Pool Nonpaged Bytes", "", None),
    ("Memory", "Pool Paged Bytes", "", None),
    ("Memory", "Free System Page Table Entries", "", None),
    ("TCPv4", "Connections Established", "_Total", None),
    ("TCPv6", "Connections Established", "_Total", None),
    ("Server", "Server Sessions", "", None),
    ("LogicalDisk", "Disk Bytes/sec", "C:", None),
    # AD/DC additional -- FSMO, replication queue, GC
    ("AD Replication", "AD Replication Queue", "", "DC"),
    ("General Response", "Global Catalog Search Time", "", "DC"),
    ("General Response", "Active Directory Last Bind", "", "DC"),
    ("DirectoryServices", "LDAP Successful Binds/sec", "", "DC"),
    ("PDC Op Master", "Op Master PDC Last Bind", "", "DC"),
    ("RID Op Master", "Op Master RID Last Bind", "", "DC"),
    ("Infrastructure Op Master", "Op Master Infrastructure Last Bind", "", "DC"),
    ("Schema Op Master", "Op Master Schema Last Bind", "", "DC"),
    ("Domain Naming Op Master", "Op Master Domain Naming Last Bind", "", "DC"),
    # DHCP additional -- response lifecycle and errors
    ("DHCP Server", "Offers/sec", "", "DHCP"),
    ("DHCP Server", "Nacks/sec", "", "DHCP"),
    ("DHCP Server", "Declines/sec", "", "DHCP"),
    ("DHCP Server", "Duplicates Dropped/sec", "", "DHCP"),
    ("DHCP Server", "Packets Expired/sec", "", "DHCP"),
    ("DHCP Server", "Milliseconds per packet (Avg).", "", "DHCP"),
    # IIS additional -- ASP.NET and errors
    ("Web Service", "Not Found Errors/sec", "_Total", "IIS"),
    ("ASP.NET Applications", "Requests/Sec", "__Total__", "IIS"),
    ("ASP.NET Applications", "Request Execution Time", "__Total__", "IIS"),
    ("ASP.NET", "Application Restarts", "", "IIS"),
]


def gen_value(counter_name):
    """Generate a realistic random value for a given counter."""
    generators = {
        "% Processor Time": lambda: 15.0 + random.random() * 70,
        "PercentMemoryUsed": lambda: 30.0 + random.random() * 50,
        "Available MBytes": lambda: 1024.0 + random.random() * 12288,
        "Pages/sec": lambda: random.random() * 100,
        "% Free Space": lambda: 10.0 + random.random() * 75,
        "Free Megabytes": lambda: 5000.0 + random.random() * 50000,
        "% Idle Time": lambda: 40.0 + random.random() * 60,
        "Avg. Disk sec/Transfer": lambda: 0.001 + random.random() * 0.02,
        "Current Disk Queue Length": lambda: random.randint(0, 3),
        "Bytes Total/sec": lambda: 100000.0 + random.random() * 20000000,
        "Current Bandwidth": lambda: 1000000000,
        "PercentBandwidthUsedTotal": lambda: 1.0 + random.random() * 30,
        "Processor Queue Length": lambda: random.randint(0, 5),
        "System Up Time": lambda: 86400.0 + random.random() * 8640000,
        "LDAP Searches/sec": lambda: 50.0 + random.random() * 450,
        "LDAP Client Sessions": lambda: 10.0 + random.random() * 200,
        "LDAP Writes/sec": lambda: 5.0 + random.random() * 50,
        "DRA Inbound Bytes Total/sec": lambda: 10000.0 + random.random() * 190000,
        "DRA Outbound Bytes Total/sec": lambda: 10000.0 + random.random() * 190000,
        "DS Search sub-operations/sec": lambda: 20.0 + random.random() * 200,
        "Kerberos Authentications": lambda: 20.0 + random.random() * 280,
        "NTLM Authentications": lambda: 5.0 + random.random() * 45,
        "KDC AS Requests": lambda: 10.0 + random.random() * 100,
        "KDC TGS Requests": lambda: 20.0 + random.random() * 200,
        "Total Query Received/sec": lambda: 100.0 + random.random() * 900,
        "Recursive Queries/sec": lambda: 10.0 + random.random() * 190,
        "Dynamic Update Received/sec": lambda: random.random() * 20,
        "Current Connections": lambda: 5.0 + random.random() * 195,
        "Total Method Requests/sec": lambda: 10.0 + random.random() * 290,
        "Bytes Received/sec": lambda: 20000.0 + random.random() * 200000,
        "Bytes Sent/sec": lambda: 30000.0 + random.random() * 300000,
        "Connection Attempts/sec": lambda: 5.0 + random.random() * 100,
        "Acks/sec": lambda: 1.0 + random.random() * 50,
        "Requests/sec": lambda: 2.0 + random.random() * 60,
        "Discovers/sec": lambda: 1.0 + random.random() * 30,
        "Active Queue Length": lambda: random.randint(0, 5),
        "Packets Received/sec": lambda: 5.0 + random.random() * 100,
        "Database Size": lambda: 500.0 + random.random() * 2000,
        "Database Drive Free Space": lambda: 10000.0 + random.random() * 40000,
        "Log File Drive Free Space": lambda: 5000.0 + random.random() * 20000,
        "Staging Space In Use": lambda: 100.0 + random.random() * 5000,
        "Conflict Space In Use": lambda: random.random() * 500,
        "Bandwidth Savings Using DFS Replication": lambda: 1000.0 + random.random() * 100000,
        "Pool Nonpaged Bytes": lambda: 50000000 + random.random() * 150000000,
        "Pool Paged Bytes": lambda: 100000000 + random.random() * 300000000,
        "Free System Page Table Entries": lambda: 10000 + random.random() * 50000,
        "Connections Established": lambda: 50 + random.random() * 500,
        "Server Sessions": lambda: 5 + random.random() * 100,
        "Disk Bytes/sec": lambda: 1000000 + random.random() * 50000000,
        "AD Replication Queue": lambda: random.randint(0, 3),
        "Global Catalog Search Time": lambda: 5 + random.random() * 50,
        "Active Directory Last Bind": lambda: 1 + random.random() * 20,
        "LDAP Successful Binds/sec": lambda: 10 + random.random() * 90,
        "Op Master PDC Last Bind": lambda: 1 + random.random() * 10,
        "Op Master RID Last Bind": lambda: 1 + random.random() * 10,
        "Op Master Infrastructure Last Bind": lambda: 1 + random.random() * 10,
        "Op Master Schema Last Bind": lambda: 1 + random.random() * 15,
        "Op Master Domain Naming Last Bind": lambda: 1 + random.random() * 15,
        "Offers/sec": lambda: 1 + random.random() * 40,
        "Nacks/sec": lambda: random.random() * 3,
        "Declines/sec": lambda: random.random() * 2,
        "Duplicates Dropped/sec": lambda: random.random() * 5,
        "Packets Expired/sec": lambda: random.random() * 3,
        "Milliseconds per packet (Avg).": lambda: 1 + random.random() * 15,
        "Not Found Errors/sec": lambda: random.random() * 5,
        "Request Execution Time": lambda: 10 + random.random() * 490,
        "Application Restarts": lambda: random.random() * 2,
    }
    return generators.get(counter_name, lambda: random.random() * 100)()


def wait_for_sql():
    """Wait for SQL Server to accept connections."""
    print(f"Waiting for SQL Server at {HOST}:{PORT} (max {MAX_WAIT}s)...")
    start = time.time()
    while time.time() - start < MAX_WAIT:
        try:
            conn = pymssql.connect(server=HOST, port=PORT, user=USER, password=PASSWORD)
            conn.close()
            print("  SQL Server is ready")
            return True
        except Exception:
            time.sleep(3)
    print("  TIMEOUT: SQL Server not available")
    return False


def main():
    if not wait_for_sql():
        sys.exit(1)

    print("Seeding SCOM DW Simulator...")

    # Create database
    conn = pymssql.connect(server=HOST, port=PORT, user=USER, password=PASSWORD, autocommit=True)
    cursor = conn.cursor()
    cursor.execute(f"IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{DB}') CREATE DATABASE [{DB}]")
    conn.close()

    # Connect to DW database
    conn = pymssql.connect(server=HOST, port=PORT, user=USER, password=PASSWORD, database=DB, autocommit=True)
    cursor = conn.cursor()

    # Create login/user
    for sql in [
        "IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = 'svc-omread') CREATE LOGIN [svc-omread] WITH PASSWORD = 'ScomDemo123!'",
        "IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'svc-omread') CREATE USER [svc-omread] FOR LOGIN [svc-omread]",
        "ALTER ROLE db_datareader ADD MEMBER [svc-omread]",
    ]:
        try:
            cursor.execute(sql)
        except Exception:
            pass
    print("  Login created")

    # Create schemas
    for schema in ["Perf", "State", "Alert"]:
        try:
            cursor.execute(f"IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = '{schema}') EXEC('CREATE SCHEMA [{schema}]')")
        except Exception:
            pass

    # Create tables
    tables = {
        "vManagedEntityType": """
            CREATE TABLE vManagedEntityType (
                ManagedEntityTypeRowId INT PRIMARY KEY IDENTITY(1,1),
                ManagedEntityTypeSystemName NVARCHAR(256)
            )""",
        "vManagedEntity": """
            CREATE TABLE vManagedEntity (
                ManagedEntityRowId INT PRIMARY KEY IDENTITY(1,1),
                ManagedEntityTypeRowId INT,
                Path NVARCHAR(512),
                Name NVARCHAR(256),
                DisplayName NVARCHAR(256),
                FullName NVARCHAR(512)
            )""",
        "vRelationship": """
            CREATE TABLE vRelationship (
                RelationshipRowId INT PRIMARY KEY IDENTITY(1,1),
                SourceManagedEntityRowId INT,
                TargetManagedEntityRowId INT
            )""",
        "vPerformanceRule": """
            CREATE TABLE vPerformanceRule (
                RuleRowId INT PRIMARY KEY IDENTITY(1,1),
                ObjectName NVARCHAR(256),
                CounterName NVARCHAR(256),
                MultiInstanceId INT DEFAULT 0,
                LastReceivedDateTime DATETIME DEFAULT GETUTCDATE()
            )""",
        "vPerformanceRuleInstance": """
            CREATE TABLE vPerformanceRuleInstance (
                PerformanceRuleInstanceRowId INT PRIMARY KEY IDENTITY(1,1),
                RuleRowId INT,
                InstanceName NVARCHAR(256),
                LastReceivedDateTime DATETIME DEFAULT GETUTCDATE()
            )""",
    }
    for name, ddl in tables.items():
        try:
            cursor.execute(f"IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = '{name}') {ddl}")
        except Exception as e:
            print(f"  Table {name}: {e}")

    # Schema-qualified tables
    schema_tables = {
        "Perf.vPerfHourly": """
            CREATE TABLE Perf.vPerfHourly (
                DateTime DATETIME,
                PerformanceRuleInstanceRowId INT,
                ManagedEntityRowId INT,
                SampleCount INT,
                AverageValue FLOAT,
                MinValue FLOAT,
                MaxValue FLOAT,
                StandardDeviation FLOAT
            )""",
        "State.vStateHourly": """
            CREATE TABLE State.vStateHourly (
                DateTime DATETIME,
                ManagedEntityRowId INT,
                MonitorRowId INT,
                OldHealthState INT,
                NewHealthState INT,
                InMaintenanceMode BIT
            )""",
        "Alert.vAlert": """
            CREATE TABLE Alert.vAlert (
                AlertGuid UNIQUEIDENTIFIER DEFAULT NEWID(),
                AlertName NVARCHAR(256),
                AlertDescription NVARCHAR(MAX),
                Severity INT,
                Priority INT,
                ResolutionState INT,
                RaisedDateTime DATETIME,
                ResolvedDateTime DATETIME NULL,
                ManagedEntityRowId INT
            )""",
    }
    for name, ddl in schema_tables.items():
        tbl = name.split(".")[1]
        try:
            cursor.execute(f"IF OBJECT_ID('{name}') IS NULL {ddl}")
        except Exception as e:
            print(f"  Table {name}: {e}")

    # Indexes
    for idx_sql in [
        "IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_PerfH_DT') CREATE INDEX IX_PerfH_DT ON Perf.vPerfHourly (DateTime)",
        "IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_PerfH_ME') CREATE INDEX IX_PerfH_ME ON Perf.vPerfHourly (ManagedEntityRowId)",
        "IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_PerfH_RI') CREATE INDEX IX_PerfH_RI ON Perf.vPerfHourly (PerformanceRuleInstanceRowId)",
    ]:
        try:
            cursor.execute(idx_sql)
        except Exception:
            pass

    print("  Tables created")

    # Check if already seeded
    cursor.execute("SELECT COUNT(*) FROM vManagedEntity")
    if cursor.fetchone()[0] > 0:
        print("  Already seeded -- showing counts:")
        for tbl in ["vManagedEntity", "vPerformanceRule", "vPerformanceRuleInstance", "Perf.vPerfHourly", "State.vStateHourly", "Alert.vAlert"]:
            cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
            print(f"    {tbl}: {cursor.fetchone()[0]}")
        conn.close()
        return

    # =========================================================================
    # Seed entity types
    # =========================================================================
    cursor.execute("""
        INSERT INTO vManagedEntityType (ManagedEntityTypeSystemName) VALUES
        ('Microsoft.Windows.Computer'),
        ('System.Group')
    """)

    # =========================================================================
    # Seed servers: VM-<SITE>-<ROLE><NUM>
    # =========================================================================
    servers = []  # (ManagedEntityRowId will be assigned, track hostname and role)
    for site in SITES:
        for role in ROLES:
            hostname = f"VM-{site}-{role}1"
            cursor.execute(
                "INSERT INTO vManagedEntity (ManagedEntityTypeRowId, Path, Name, DisplayName, FullName) VALUES (1, %s, %s, %s, %s)",
                (hostname, hostname, hostname, hostname)
            )
        # Second DC and SQL per site
        for extra_role in ["DC", "SQL"]:
            hostname = f"VM-{site}-{extra_role}2"
            cursor.execute(
                "INSERT INTO vManagedEntity (ManagedEntityTypeRowId, Path, Name, DisplayName, FullName) VALUES (1, %s, %s, %s, %s)",
                (hostname, hostname, hostname, hostname)
            )
    conn.commit()

    # Get all server IDs with their hostnames
    cursor.execute("SELECT ManagedEntityRowId, DisplayName FROM vManagedEntity WHERE ManagedEntityTypeRowId = 1")
    all_servers = cursor.fetchall()
    print(f"  Seeded {len(all_servers)} servers across {len(SITES)} sites")

    # Build server lookup by role
    def servers_for_role(role_filter):
        """Get server IDs matching a role filter (e.g., 'DC', 'IIS', 'DC,FS')."""
        if role_filter is None:
            return all_servers
        roles = [r.strip() for r in role_filter.split(",")]
        return [(sid, name) for sid, name in all_servers if any(f"-{r}" in name for r in roles)]

    # Seed groups (role-based, matching production)
    groups = [
        "AD Domain Controller Group (Windows Server 2016)",
        "IIS 10.0 Web Server Group",
        "DHCP Server Group",
        "All Windows Computers",
    ]
    for g in groups:
        cursor.execute(
            "INSERT INTO vManagedEntity (ManagedEntityTypeRowId, Path, Name, DisplayName, FullName) VALUES (2, %s, %s, %s, %s)",
            (g, g, g, g)
        )
    conn.commit()
    print("  Groups seeded")

    # Seed relationships
    cursor.execute("SELECT ManagedEntityRowId, DisplayName FROM vManagedEntity WHERE ManagedEntityTypeRowId = 2")
    group_rows = cursor.fetchall()
    for gid, gname in group_rows:
        if "Domain Controller" in gname:
            matched = servers_for_role("DC")
        elif "IIS" in gname:
            matched = servers_for_role("IIS")
        elif "DHCP" in gname:
            matched = servers_for_role("DHCP")
        elif "All Windows" in gname:
            matched = all_servers
        else:
            matched = []
        for sid, _ in matched:
            cursor.execute("INSERT INTO vRelationship (SourceManagedEntityRowId, TargetManagedEntityRowId) VALUES (%s, %s)", (gid, sid))
    conn.commit()
    print("  Relationships seeded")

    # =========================================================================
    # Seed performance rules (counter definitions)
    # =========================================================================
    # Deduplicate: same ObjectName+CounterName can have multiple instances
    rule_map = {}  # (ObjectName, CounterName) -> RuleRowId
    for obj, ctr, inst, role_filter in COUNTERS:
        key = (obj, ctr)
        if key not in rule_map:
            cursor.execute(
                "INSERT INTO vPerformanceRule (ObjectName, CounterName) VALUES (%s, %s)",
                (obj, ctr)
            )
            cursor.execute("SELECT SCOPE_IDENTITY()")
            rule_map[key] = int(cursor.fetchone()[0])
    conn.commit()
    print(f"  Seeded {len(rule_map)} performance rules")

    # Seed performance rule instances (rule + instance name)
    instance_map = {}  # (ObjectName, CounterName, InstanceName) -> PerformanceRuleInstanceRowId
    for obj, ctr, inst, role_filter in COUNTERS:
        key = (obj, ctr, inst)
        if key not in instance_map:
            rule_id = rule_map[(obj, ctr)]
            cursor.execute(
                "INSERT INTO vPerformanceRuleInstance (RuleRowId, InstanceName) VALUES (%s, %s)",
                (rule_id, inst)
            )
            cursor.execute("SELECT SCOPE_IDENTITY()")
            instance_map[key] = int(cursor.fetchone()[0])
    conn.commit()
    print(f"  Seeded {len(instance_map)} performance rule instances")

    # =========================================================================
    # Seed performance data (7 days hourly)
    # =========================================================================
    print("  Seeding 7 days of hourly performance data...")
    now = datetime.now(timezone.utc)
    batch = []
    total_rows = 0

    for hour in range(168):
        dt = now - timedelta(hours=hour)
        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")

        for obj, ctr, inst, role_filter in COUNTERS:
            pri_id = instance_map[(obj, ctr, inst)]
            target_servers = servers_for_role(role_filter)

            for sid, _ in target_servers:
                val = gen_value(ctr)
                batch.append((dt_str, pri_id, sid, 12, val, val * 0.7, val * 1.3, 1.0))
                total_rows += 1

                if len(batch) >= 1000:
                    cursor.executemany(
                        "INSERT INTO Perf.vPerfHourly (DateTime, PerformanceRuleInstanceRowId, ManagedEntityRowId, SampleCount, AverageValue, MinValue, MaxValue, StandardDeviation) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        batch
                    )
                    conn.commit()
                    batch = []

        if (hour + 1) % 24 == 0:
            print(f"    Day {(hour+1)//24}/7 complete ({total_rows:,} rows)")

    if batch:
        cursor.executemany(
            "INSERT INTO Perf.vPerfHourly (DateTime, PerformanceRuleInstanceRowId, ManagedEntityRowId, SampleCount, AverageValue, MinValue, MaxValue, StandardDeviation) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            batch
        )
        conn.commit()
    print(f"  Perf data: {total_rows:,} rows")

    # =========================================================================
    # Seed state data (every 4 hours for 7 days)
    # =========================================================================
    print("  Seeding health state data...")
    batch = []
    for hour in range(0, 168, 4):
        dt = now - timedelta(hours=hour)
        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        for sid, _ in all_servers:
            r = random.random()
            health = 3 if r < 0.02 else (2 if r < 0.07 else 1)
            maint = 1 if random.random() < 0.03 else 0
            batch.append((dt_str, sid, 1, 1, health, maint))

    cursor.executemany(
        "INSERT INTO State.vStateHourly (DateTime, ManagedEntityRowId, MonitorRowId, OldHealthState, NewHealthState, InMaintenanceMode) VALUES (%s, %s, %s, %s, %s, %s)",
        batch
    )
    conn.commit()
    print(f"  State data: {len(batch)} rows")

    # =========================================================================
    # Seed alerts
    # =========================================================================
    print("  Seeding alerts...")
    alert_names = [
        "Logical Disk Free Space is low",
        "Windows Service Stopped",
        "Processor Utilization exceeded threshold",
        "Memory Pages/sec exceeded threshold",
        "DNS Resolution Failure Rate High",
        "Health Service Heartbeat Failure",
    ]

    # Active alerts
    for sid, name in random.sample(all_servers, min(15, len(all_servers))):
        alert = random.choice(alert_names)
        sev = random.choice([1, 1, 2])
        hours_ago = random.randint(1, 72)
        dt = (now - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute(
            "INSERT INTO Alert.vAlert (AlertName, AlertDescription, Severity, Priority, ResolutionState, RaisedDateTime, ManagedEntityRowId) VALUES (%s, %s, %s, 1, 0, %s, %s)",
            (alert, f"Threshold exceeded on {name}", sev, dt, sid)
        )

    # Resolved alerts
    for sid, name in random.sample(all_servers, min(50, len(all_servers))):
        alert = random.choice(alert_names)
        sev = random.choice([1, 1, 2])
        hours_ago = random.randint(1, 168)
        duration = random.randint(10, 240)
        raised = now - timedelta(hours=hours_ago)
        resolved = raised + timedelta(minutes=duration)
        cursor.execute(
            "INSERT INTO Alert.vAlert (AlertName, AlertDescription, Severity, Priority, ResolutionState, RaisedDateTime, ResolvedDateTime, ManagedEntityRowId) VALUES (%s, %s, %s, 1, 255, %s, %s, %s)",
            (alert, f"Resolved on {name}", sev, raised.strftime("%Y-%m-%d %H:%M:%S"), resolved.strftime("%Y-%m-%d %H:%M:%S"), sid)
        )
    conn.commit()

    # =========================================================================
    # Seed troubleshooting tables (Phase 15I)
    # =========================================================================

    # --- Perf.vPerfRaw (5-minute granularity, last 7 days) ---
    # Same schema as vPerfHourly but higher resolution
    try:
        cursor.execute("IF OBJECT_ID('Perf.vPerfRaw') IS NULL CREATE TABLE Perf.vPerfRaw (DateTime DATETIME, PerformanceRuleInstanceRowId INT, ManagedEntityRowId INT, SampleCount INT, AverageValue FLOAT, MinValue FLOAT, MaxValue FLOAT, StandardDeviation FLOAT)")
        cursor.execute("IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_PerfRaw_DT') CREATE INDEX IX_PerfRaw_DT ON Perf.vPerfRaw (DateTime)")
    except Exception:
        pass

    cursor.execute("SELECT COUNT(*) FROM Perf.vPerfRaw")
    if cursor.fetchone()[0] == 0:
        print("  Seeding Perf.vPerfRaw (5-min granularity)...")
        batch = []
        raw_total = 0
        # Seed 3 days at 5-min intervals (864 intervals) for key counters only
        # Using a subset of counters to keep row count manageable
        key_instances = list(instance_map.items())[:8]  # CPU, memory, disk, network
        for interval in range(864):
            dt = (now - timedelta(minutes=interval * 5)).strftime("%Y-%m-%d %H:%M:%S")
            for (obj, ctr, inst), pri_id in key_instances:
                for sid, _ in random.sample(all_servers, min(20, len(all_servers))):
                    val = gen_value(ctr)
                    batch.append((dt, pri_id, sid, 1, val, val * 0.8, val * 1.2, 1.0))
                    raw_total += 1
                    if len(batch) >= 2000:
                        cursor.executemany(
                            "INSERT INTO Perf.vPerfRaw (DateTime, PerformanceRuleInstanceRowId, ManagedEntityRowId, SampleCount, AverageValue, MinValue, MaxValue, StandardDeviation) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                            batch
                        )
                        conn.commit()
                        batch = []
        if batch:
            cursor.executemany(
                "INSERT INTO Perf.vPerfRaw (DateTime, PerformanceRuleInstanceRowId, ManagedEntityRowId, SampleCount, AverageValue, MinValue, MaxValue, StandardDeviation) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                batch
            )
            conn.commit()
        print(f"  Perf.vPerfRaw: {raw_total:,} rows")

    # --- Event tables ---
    try:
        cursor.execute("IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'Event') EXEC('CREATE SCHEMA Event')")
    except Exception:
        pass

    event_tables = {
        "EventPublisher": "CREATE TABLE dbo.EventPublisher (EventPublisherRowId INT PRIMARY KEY IDENTITY(1,1), EventPublisherName NVARCHAR(256))",
        "EventChannel": "CREATE TABLE dbo.EventChannel (EventChannelRowId INT PRIMARY KEY IDENTITY(1,1), EventChannelName NVARCHAR(256))",
        "EventLevel": "CREATE TABLE dbo.EventLevel (EventLevelId INT PRIMARY KEY, EventLevelName NVARCHAR(50))",
        "EventLoggingComputer": "CREATE TABLE dbo.EventLoggingComputer (LoggingComputerRowId INT PRIMARY KEY IDENTITY(1,1), LoggingComputerName NVARCHAR(256))",
        "vEventPublisher": "CREATE VIEW dbo.vEventPublisher AS SELECT * FROM dbo.EventPublisher",
        "vEventChannel": "CREATE VIEW dbo.vEventChannel AS SELECT * FROM dbo.EventChannel",
        "vEventLevel": "CREATE VIEW dbo.vEventLevel AS SELECT * FROM dbo.EventLevel",
        "vEventLoggingComputer": "CREATE VIEW dbo.vEventLoggingComputer AS SELECT * FROM dbo.EventLoggingComputer",
    }
    for name, ddl in event_tables.items():
        try:
            if "VIEW" in ddl:
                cursor.execute(f"IF OBJECT_ID('dbo.{name}') IS NULL EXEC('{ddl.replace(chr(39), chr(39)+chr(39))}')")
            else:
                cursor.execute(f"IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = '{name}') {ddl}")
        except Exception:
            pass

    try:
        cursor.execute("""IF OBJECT_ID('Event.vEvent') IS NULL CREATE TABLE Event.vEvent (
            EventOriginId UNIQUEIDENTIFIER DEFAULT NEWID(),
            DateTime DATETIME,
            EventPublisherRowId INT,
            EventChannelRowId INT,
            EventCategoryRowId INT DEFAULT 1,
            EventLevelId INT,
            LoggingComputerRowId INT,
            EventNumber INT,
            EventDisplayNumber INT,
            UserNameRowId INT DEFAULT 1,
            RawDescription NVARCHAR(MAX),
            EventDataHash UNIQUEIDENTIFIER DEFAULT NEWID()
        )""")
    except Exception:
        pass

    # Seed event lookup data
    cursor.execute("SELECT COUNT(*) FROM dbo.EventPublisher")
    if cursor.fetchone()[0] == 0:
        print("  Seeding event lookup tables...")
        publishers = ["Microsoft-Windows-Security-Auditing", "Service Control Manager",
                      "Microsoft-Windows-DNS-Server-Service", "MSSQLSERVER",
                      "Application Error", "Windows Error Reporting", "NTFS",
                      "Microsoft-Windows-DistributedCOM", "Microsoft-Windows-GroupPolicy"]
        for p in publishers:
            cursor.execute("INSERT INTO dbo.EventPublisher (EventPublisherName) VALUES (%s)", (p,))

        channels = ["Application", "System", "Security", "Setup"]
        for c in channels:
            cursor.execute("INSERT INTO dbo.EventChannel (EventChannelName) VALUES (%s)", (c,))

        levels = [(1, "Error"), (2, "Warning"), (3, "Information"), (4, "Verbose")]
        for lid, lname in levels:
            try:
                cursor.execute("INSERT INTO dbo.EventLevel (EventLevelId, EventLevelName) VALUES (%s, %s)", (lid, lname))
            except Exception:
                pass

        # Create logging computer entries matching our servers
        for sid, name in all_servers:
            cursor.execute("INSERT INTO dbo.EventLoggingComputer (LoggingComputerName) VALUES (%s)", (name,))
        conn.commit()

    # Seed events (7 days)
    cursor.execute("SELECT COUNT(*) FROM Event.vEvent")
    if cursor.fetchone()[0] == 0:
        print("  Seeding events...")
        cursor.execute("SELECT LoggingComputerRowId, LoggingComputerName FROM dbo.EventLoggingComputer")
        computers = cursor.fetchall()

        event_descriptions = [
            "The service was stopped.",
            "The service was started successfully.",
            "The driver detected a controller error.",
            "The previous system shutdown was unexpected.",
            "The certificate received from the remote server has expired.",
            "The server was unable to allocate from the system nonpaged pool.",
            "A timeout was reached while waiting for a transaction response.",
            "Login failed for user. Reason: password expired.",
            "Disk space is critically low on volume C:.",
            "The DNS server timed out attempting a recursive query.",
        ]

        batch = []
        evt_total = 0
        for hour in range(168):
            dt_base = now - timedelta(hours=hour)
            # Generate 2-10 events per hour per subset of servers
            for comp_id, comp_name in random.sample(computers, min(15, len(computers))):
                num_events = random.randint(1, 5)
                for _ in range(num_events):
                    dt = (dt_base + timedelta(minutes=random.randint(0, 59))).strftime("%Y-%m-%d %H:%M:%S")
                    level = random.choices([1, 2, 3], weights=[10, 20, 70])[0]
                    pub_id = random.randint(1, 9)
                    chan_id = random.choice([1, 2])  # Application or System
                    evt_num = random.choice([7036, 7045, 1014, 6008, 36882, 2004, 5014, 18456, 2013, 4015])
                    desc = random.choice(event_descriptions)
                    batch.append((dt, pub_id, chan_id, level, comp_id, evt_num, evt_num, desc))
                    evt_total += 1
                    if len(batch) >= 2000:
                        cursor.executemany(
                            "INSERT INTO Event.vEvent (DateTime, EventPublisherRowId, EventChannelRowId, EventLevelId, LoggingComputerRowId, EventNumber, EventDisplayNumber, RawDescription) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                            batch
                        )
                        conn.commit()
                        batch = []
        if batch:
            cursor.executemany(
                "INSERT INTO Event.vEvent (DateTime, EventPublisherRowId, EventChannelRowId, EventLevelId, LoggingComputerRowId, EventNumber, EventDisplayNumber, RawDescription) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                batch
            )
            conn.commit()
        print(f"  Events: {evt_total:,} rows")

    # --- Alert Resolution State ---
    try:
        cursor.execute("""IF OBJECT_ID('Alert.vAlertResolutionState') IS NULL CREATE TABLE Alert.vAlertResolutionState (
            AlertGuid UNIQUEIDENTIFIER,
            ResolutionState INT,
            TimeInStateSeconds INT,
            TimeFromRaisedSeconds INT,
            StateSetDateTime DATETIME,
            StateSetByUserId NVARCHAR(256),
            DWCreatedDateTime DATETIME DEFAULT GETUTCDATE()
        )""")
    except Exception:
        pass

    cursor.execute("SELECT COUNT(*) FROM Alert.vAlertResolutionState")
    if cursor.fetchone()[0] == 0:
        print("  Seeding alert resolution states...")
        cursor.execute("SELECT AlertGuid, RaisedDateTime, ResolutionState FROM Alert.vAlert")
        alerts = cursor.fetchall()
        users = ["System", "svc-scom", "admin_user1", "admin_user2", "noc_operator"]
        for guid, raised, res_state in alerts:
            # Initial state (New)
            cursor.execute(
                "INSERT INTO Alert.vAlertResolutionState (AlertGuid, ResolutionState, TimeInStateSeconds, TimeFromRaisedSeconds, StateSetDateTime, StateSetByUserId) VALUES (%s, 0, %s, 0, %s, 'System')",
                (guid, random.randint(60, 86400), raised.strftime("%Y-%m-%d %H:%M:%S"))
            )
            # If resolved, add closed state
            if res_state == 255:
                closed_dt = raised + timedelta(minutes=random.randint(10, 480))
                cursor.execute(
                    "INSERT INTO Alert.vAlertResolutionState (AlertGuid, ResolutionState, TimeInStateSeconds, TimeFromRaisedSeconds, StateSetDateTime, StateSetByUserId) VALUES (%s, 255, 0, %s, %s, %s)",
                    (guid, int((closed_dt - raised).total_seconds()), closed_dt.strftime("%Y-%m-%d %H:%M:%S"), random.choice(users))
                )
        conn.commit()

    # --- Maintenance Mode ---
    try:
        cursor.execute("""IF OBJECT_ID('dbo.vMaintenanceMode') IS NULL CREATE TABLE dbo.vMaintenanceMode (
            MaintenanceModeRowId INT PRIMARY KEY IDENTITY(1,1),
            ManagedEntityRowId INT,
            StartDateTime DATETIME,
            EndDateTime DATETIME,
            PlannedMaintenanceInd BIT,
            DWLastModifiedDateTime DATETIME DEFAULT GETUTCDATE()
        )""")
        cursor.execute("""IF OBJECT_ID('dbo.vMaintenanceModeHistory') IS NULL CREATE TABLE dbo.vMaintenanceModeHistory (
            MaintenanceModeHistoryRowId INT PRIMARY KEY IDENTITY(1,1),
            MaintenanceModeRowId INT,
            ScheduledEndDateTime DATETIME,
            PlannedMaintenanceInd BIT,
            ReasonCode INT,
            Comment NVARCHAR(MAX),
            UserId NVARCHAR(256),
            DBLastModifiedDateTime DATETIME DEFAULT GETUTCDATE(),
            DWCreatedDateTime DATETIME DEFAULT GETUTCDATE()
        )""")
    except Exception:
        pass

    cursor.execute("SELECT COUNT(*) FROM dbo.vMaintenanceMode")
    if cursor.fetchone()[0] == 0:
        print("  Seeding maintenance mode history...")
        maint_reasons = [
            "Disabling alerts for Windows updates",
            "Planned hardware maintenance",
            "Application deployment in progress",
            "Monthly patching cycle",
            "Network maintenance window",
        ]
        maint_users = ["admin_user1", "admin_user2", "svc-scom", "noc_operator"]
        for _ in range(25):
            sid, name = random.choice(all_servers)
            days_ago = random.randint(1, 30)
            duration_hours = random.choice([1, 2, 4, 8])
            start = now - timedelta(days=days_ago)
            end = start + timedelta(hours=duration_hours)
            planned = random.choice([0, 1, 1, 1])
            cursor.execute(
                "INSERT INTO dbo.vMaintenanceMode (ManagedEntityRowId, StartDateTime, EndDateTime, PlannedMaintenanceInd) VALUES (%s, %s, %s, %s)",
                (sid, start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S"), planned)
            )
            cursor.execute("SELECT SCOPE_IDENTITY()")
            mm_id = int(cursor.fetchone()[0])
            cursor.execute(
                "INSERT INTO dbo.vMaintenanceModeHistory (MaintenanceModeRowId, ScheduledEndDateTime, PlannedMaintenanceInd, ReasonCode, Comment, UserId) VALUES (%s, %s, %s, %s, %s, %s)",
                (mm_id, end.strftime("%Y-%m-%d %H:%M:%S"), planned, random.randint(1, 10), random.choice(maint_reasons), random.choice(maint_users))
            )
        conn.commit()

    # Final counts
    print("\n  Final counts:")
    for tbl in ["vManagedEntity", "vPerformanceRule", "vPerformanceRuleInstance",
                "Perf.vPerfHourly", "Perf.vPerfRaw", "State.vStateHourly",
                "Alert.vAlert", "Alert.vAlertResolutionState",
                "Event.vEvent", "dbo.vMaintenanceMode"]:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
            print(f"    {tbl}: {cursor.fetchone()[0]:,}")
        except Exception:
            print(f"    {tbl}: (not created)")

    conn.close()
    print("\nSCOM DW Simulator seeded successfully (production-aligned schema)!")


if __name__ == "__main__":
    main()
