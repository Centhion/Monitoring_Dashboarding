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
    # Disk latency read/write -- Server Overview Disk Latency panel
    ("LogicalDisk", "Avg. Disk sec/Read", "C:", None),
    ("LogicalDisk", "Avg. Disk sec/Read", "D:", None),
    ("LogicalDisk", "Avg. Disk sec/Write", "C:", None),
    ("LogicalDisk", "Avg. Disk sec/Write", "D:", None),
    # DRA replication sub-counters -- AD/DC DRA Replication Detail panels
    ("DirectoryServices", "DRA Inbound Bytes Compressed (Between Sites, After Compression)/sec", "", "DC"),
    ("DirectoryServices", "DRA Inbound Bytes Not Compressed (Within Site)/sec", "", "DC"),
    ("DirectoryServices", "DRA Outbound Bytes Compressed (Between Sites, After Compression)/sec", "", "DC"),
    ("DirectoryServices", "DRA Outbound Bytes Not Compressed (Within Site)/sec", "", "DC"),
    # DHCP Scope counters -- DHCP Scope Address Usage panel
    ("Scopes", "IPV4Scope-AddressesInUse", "10.1.0.0/24", "DHCP"),
    ("Scopes", "IPV4Scope-AddressesAvailable", "10.1.0.0/24", "DHCP"),
    ("Scopes", "IPV4Scope-AddressesInUse", "10.2.0.0/24", "DHCP"),
    ("Scopes", "IPV4Scope-AddressesAvailable", "10.2.0.0/24", "DHCP"),
    ("Scopes", "IPV4Scope-AddressesInUse", "192.168.1.0/24", "DHCP"),
    ("Scopes", "IPV4Scope-AddressesAvailable", "192.168.1.0/24", "DHCP"),
    # Exchange Server counters -- Exchange dashboard
    ("Exchange Server", "Messages Received/sec", "", "SQL"),
    ("Exchange Server", "Messages Sent/Sec", "", "SQL"),
    ("Exchange Server", "Queue Length", "", "SQL"),
    ("Exchange Server", "Client Connections Count", "", "SQL"),
    ("Exchange Server", "Avg. RPC Latency (ms)", "", "SQL"),
    # Exchange Mailbox Database counters
    ("Exchange Mailbox Database", "I/O Database Reads Average Latency (ms)", "", "SQL"),
    ("Exchange Mailbox Database", "I/O Database Writes Average Latency (ms)", "", "SQL"),
    ("Exchange Mailbox Database", "Database Size (MB)", "", "SQL"),
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
        # Disk latency read/write
        "Avg. Disk sec/Read": lambda: 0.001 + random.random() * 0.015,
        "Avg. Disk sec/Write": lambda: 0.002 + random.random() * 0.025,
        # DRA replication sub-counters
        "DRA Inbound Bytes Compressed (Between Sites, After Compression)/sec": lambda: 5000 + random.random() * 95000,
        "DRA Inbound Bytes Not Compressed (Within Site)/sec": lambda: 5000 + random.random() * 95000,
        "DRA Outbound Bytes Compressed (Between Sites, After Compression)/sec": lambda: 5000 + random.random() * 95000,
        "DRA Outbound Bytes Not Compressed (Within Site)/sec": lambda: 5000 + random.random() * 95000,
        # DHCP Scope counters
        "IPV4Scope-AddressesInUse": lambda: 20 + random.randint(0, 200),
        "IPV4Scope-AddressesAvailable": lambda: 10 + random.randint(0, 40),
        # Exchange counters
        "Messages Received/sec": lambda: 5 + random.random() * 95,
        "Messages Sent/Sec": lambda: 3 + random.random() * 80,
        "Queue Length": lambda: random.randint(0, 15),
        "Client Connections Count": lambda: 20 + random.random() * 480,
        "Avg. RPC Latency (ms)": lambda: 1 + random.random() * 25,
        "I/O Database Reads Average Latency (ms)": lambda: 5 + random.random() * 45,
        "I/O Database Writes Average Latency (ms)": lambda: 10 + random.random() * 90,
        "Database Size (MB)": lambda: 5000 + random.random() * 45000,
    }
    return generators.get(counter_name, lambda: random.random() * 100)()


def bulk_insert(cursor, conn, sql_prefix, rows, chunk_size=200):
    """
    Insert rows using multi-row VALUES clauses instead of executemany.
    pymssql's executemany sends one INSERT per row over the wire, which is
    extremely slow for large datasets. This builds a single INSERT with up to
    chunk_size value tuples, reducing round-trips by orders of magnitude.

    sql_prefix: e.g. "INSERT INTO Perf.vPerfHourly (col1, col2) VALUES"
    rows: list of tuples
    conn: database connection (for intermediate commits on large batches)
    chunk_size: rows per INSERT statement (200 balances speed vs SQL Server limits)
    """
    if not rows:
        return
    for i in range(0, len(rows), chunk_size):
        chunk = rows[i:i + chunk_size]
        # Build value tuples as SQL-safe strings
        value_strings = []
        for row in chunk:
            formatted = []
            for val in row:
                if val is None:
                    formatted.append("NULL")
                elif isinstance(val, str):
                    # Escape single quotes for SQL safety
                    formatted.append("'" + val.replace("'", "''") + "'")
                elif isinstance(val, (int, float)):
                    formatted.append(str(val))
                else:
                    formatted.append("'" + str(val).replace("'", "''") + "'")
            value_strings.append("(" + ",".join(formatted) + ")")
        sql = sql_prefix + " " + ",".join(value_strings)
        cursor.execute(sql)
        # Commit every 10k rows to avoid connection timeouts on constrained hosts
        if (i // chunk_size) % 50 == 49:
            conn.commit()


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
    PERF_PREFIX = "INSERT INTO Perf.vPerfHourly (DateTime, PerformanceRuleInstanceRowId, ManagedEntityRowId, SampleCount, AverageValue, MinValue, MaxValue, StandardDeviation) VALUES"

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

        # Flush every hour to avoid overwhelming the SQL connection
        bulk_insert(cursor, conn, PERF_PREFIX, batch)
        batch = []
        conn.commit()

        if (hour + 1) % 24 == 0:
            print(f"    Day {(hour+1)//24}/7 complete ({total_rows:,} rows)")

    conn.commit()
    print(f"  Perf data: {total_rows:,} rows")

    # =========================================================================
    # Seed state data (every 4 hours for 7 days)
    # =========================================================================
    # Production SCOM DW has one row per (entity, monitor, hour). We seed two
    # monitor types per entity:
    #   MonitorRowId=1 (System.Health.AvailabilityState) -- aggregate rollup
    #   A role-appropriate unit monitor -- the actionable root cause
    # The unit monitor IDs match the dbo.vMonitor seed below:
    #   7 = FreeSpaceMonitor, 8 = MemoryUsageMonitor,
    #   9 = CPUUsageMonitor,  10 = ServiceMonitor
    ROLE_UNIT_MONITOR = {
        "DC":   7,   # domain controller -- SYSVOL disk space
        "SQL":  8,   # SQL server -- memory pressure
        "IIS":  10,  # IIS server -- W3SVC service state
        "FS":   7,   # file server -- disk free space
        "APP":  9,   # app server -- CPU utilization
        "DHCP": 10,  # DHCP server -- DHCP service state
    }
    print("  Seeding health state data...")
    batch = []
    for hour in range(0, 168, 4):
        dt = now - timedelta(hours=hour)
        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        for sid, name in all_servers:
            r = random.random()
            # ~5% critical, ~12% warning for realistic fleet monitoring visibility
            health = 3 if r < 0.05 else (2 if r < 0.17 else 1)
            maint = 1 if random.random() < 0.04 else 0
            # Aggregate monitor (always present -- rollup of all unit monitors)
            batch.append((dt_str, sid, 1, 1, health, maint))
            # Unit monitor row -- only seed when degraded so the table shows
            # actionable failures rather than noise from healthy unit checks
            if health > 1:
                parts = name.split("-")
                role_str = "".join(c for c in parts[2] if not c.isdigit()) if len(parts) >= 3 else "DC"
                unit_mid = ROLE_UNIT_MONITOR.get(role_str, 7)
                batch.append((dt_str, sid, unit_mid, 1, health, maint))

    bulk_insert(cursor, conn,
        "INSERT INTO State.vStateHourly (DateTime, ManagedEntityRowId, MonitorRowId, OldHealthState, NewHealthState, InMaintenanceMode) VALUES",
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

    # Active alerts -- ensure broad coverage so every server drill-down
    # demonstrates alert panels. Target ~60% of servers with active alerts.
    servers_for_alerts = random.sample(all_servers, min(45, len(all_servers)))
    for sid, name in servers_for_alerts:
        # 1-3 alerts per server for realistic density
        num_alerts = random.choices([1, 2, 3], weights=[50, 35, 15])[0]
        for _ in range(num_alerts):
            alert = random.choice(alert_names)
            sev = random.choice([1, 1, 1, 2, 2])
            hours_ago = random.randint(1, 120)
            dt = (now - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO Alert.vAlert (AlertName, AlertDescription, Severity, Priority, ResolutionState, RaisedDateTime, ManagedEntityRowId) VALUES (%s, %s, %s, 1, 0, %s, %s)",
                (alert, f"Threshold exceeded on {name}", sev, dt, sid)
            )

    # Resolved alerts -- every server should have alert history to demonstrate
    # the Alert History panel on drill-down
    for sid, name in all_servers:
        num_resolved = random.randint(2, 6)
        for _ in range(num_resolved):
            alert = random.choice(alert_names)
            sev = random.choice([1, 1, 2])
            hours_ago = random.randint(1, 168)
            duration = random.randint(10, 480)
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
        print("  Seeding Perf.vPerfRaw (5-min granularity, 3 days)...")
        batch = []
        raw_total = 0
        # Seed 3 days at 5-min intervals for key counters.
        # Include CPU, memory, disk (free space + latency), network, and queue
        # so the Server Overview "Recent Performance" section is fully populated.
        raw_counter_names = [
            "% Processor Time", "PercentMemoryUsed", "% Free Space",
            "Avg. Disk sec/Read", "Avg. Disk sec/Write",
            "Bytes Total/sec", "Processor Queue Length", "Disk Bytes/sec",
        ]
        raw_instances = [(k, v) for k, v in instance_map.items() if k[1] in raw_counter_names]
        RAW_PREFIX = "INSERT INTO Perf.vPerfRaw (DateTime, PerformanceRuleInstanceRowId, ManagedEntityRowId, SampleCount, AverageValue, MinValue, MaxValue, StandardDeviation) VALUES"
        intervals_per_day = 288  # 24h * 60min / 5min
        # Flush every 12 intervals (1 hour of 5-min data) to stay within
        # Azure SQL Edge connection limits
        for interval in range(864):
            dt = (now - timedelta(minutes=interval * 5)).strftime("%Y-%m-%d %H:%M:%S")
            for (obj, ctr, inst), pri_id in raw_instances:
                for sid, _ in all_servers:
                    val = gen_value(ctr)
                    batch.append((dt, pri_id, sid, 1, val, val * 0.8, val * 1.2, 1.0))
                    raw_total += 1
            # Flush every hour (12 x 5-min intervals)
            if (interval + 1) % 12 == 0:
                bulk_insert(cursor, conn, RAW_PREFIX, batch)
                batch = []
                conn.commit()
            if (interval + 1) % intervals_per_day == 0:
                print(f"    Raw Day {(interval+1)//intervals_per_day}/3 complete ({raw_total:,} rows)")
        if batch:
            bulk_insert(cursor, conn, RAW_PREFIX, batch)
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
        EVT_PREFIX = "INSERT INTO Event.vEvent (DateTime, EventPublisherRowId, EventChannelRowId, EventLevelId, LoggingComputerRowId, EventNumber, EventDisplayNumber, RawDescription) VALUES"
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
            # Flush every hour
            bulk_insert(cursor, conn, EVT_PREFIX, batch)
            batch = []
            conn.commit()
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

    # =========================================================================
    # Seed additional tables (Alert Detail, Health Monitors, Agent Outages,
    # Daily Perf, State Raw, Exchange Mailbox)
    # =========================================================================

    # --- Alert.vAlertDetail (repeat counts and context) ---
    try:
        cursor.execute("""IF OBJECT_ID('Alert.vAlertDetail') IS NULL CREATE TABLE Alert.vAlertDetail (
            AlertGuid UNIQUEIDENTIFIER,
            RepeatCount INT DEFAULT 0,
            DBLastModifiedDateTime DATETIME DEFAULT GETUTCDATE(),
            DWCreatedDateTime DATETIME DEFAULT GETUTCDATE()
        )""")
    except Exception:
        pass

    cursor.execute("SELECT COUNT(*) FROM Alert.vAlertDetail")
    if cursor.fetchone()[0] == 0:
        print("  Seeding alert details...")
        cursor.execute("SELECT AlertGuid FROM Alert.vAlert")
        for (guid,) in cursor.fetchall():
            cursor.execute(
                "INSERT INTO Alert.vAlertDetail (AlertGuid, RepeatCount) VALUES (%s, %s)",
                (guid, random.randint(0, 25))
            )
        conn.commit()

    # --- dbo.vMonitor (monitor definitions) ---
    try:
        cursor.execute("""IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'vMonitor' AND schema_id = SCHEMA_ID('dbo'))
            CREATE TABLE dbo.vMonitor (
                MonitorRowId INT PRIMARY KEY IDENTITY(1,1),
                MonitorDefaultName NVARCHAR(256),
                MonitorSystemName NVARCHAR(256)
            )""")
    except Exception:
        pass

    cursor.execute("SELECT COUNT(*) FROM dbo.vMonitor")
    if cursor.fetchone()[0] == 0:
        print("  Seeding monitors...")
        monitors = [
            "System.Health.AvailabilityState", "System.Health.PerformanceState",
            "System.Health.ConfigurationState", "System.Health.SecurityState",
            "Microsoft.Windows.Server.Computer.PerformanceRollup",
            "Microsoft.Windows.Server.Computer.AvailabilityRollup",
            "Microsoft.Windows.LogicalDisk.FreeSpaceMonitor",
            "Microsoft.Windows.Server.MemoryUsageMonitor",
            "Microsoft.Windows.Server.CPUUsageMonitor",
            "Microsoft.Windows.DNSServer.ServiceMonitor",
        ]
        for m in monitors:
            name = m.split('.')[-1]
            cursor.execute("INSERT INTO dbo.vMonitor (MonitorDefaultName, MonitorSystemName) VALUES (%s, %s)", (name, m))
        conn.commit()

    # --- vManagedEntityMonitor (which monitors are on which entities) ---
    try:
        cursor.execute("""IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'vManagedEntityMonitor')
            CREATE TABLE dbo.vManagedEntityMonitor (
                ManagedEntityMonitorRowId INT PRIMARY KEY IDENTITY(1,1),
                ManagedEntityRowId INT,
                MonitorRowId INT,
                DWCreatedDateTime DATETIME DEFAULT GETUTCDATE()
            )""")
    except Exception:
        pass

    cursor.execute("SELECT COUNT(*) FROM dbo.vManagedEntityMonitor")
    if cursor.fetchone()[0] == 0:
        print("  Seeding entity-monitor mappings...")
        cursor.execute("SELECT MonitorRowId FROM dbo.vMonitor")
        monitor_ids = [r[0] for r in cursor.fetchall()]
        for sid, _ in all_servers:
            for mid in monitor_ids:
                cursor.execute("INSERT INTO dbo.vManagedEntityMonitor (ManagedEntityRowId, MonitorRowId) VALUES (%s, %s)", (sid, mid))
        conn.commit()

    # --- dbo.vHealthServiceOutage (agent outages) ---
    try:
        cursor.execute("""IF OBJECT_ID('dbo.vHealthServiceOutage') IS NULL CREATE TABLE dbo.vHealthServiceOutage (
            HealthServiceOutageRowId INT PRIMARY KEY IDENTITY(1,1),
            ManagedEntityRowId INT,
            OutageStartDateTime DATETIME,
            OutageEndDateTime DATETIME
        )""")
    except Exception:
        pass

    cursor.execute("SELECT COUNT(*) FROM dbo.vHealthServiceOutage")
    if cursor.fetchone()[0] == 0:
        print("  Seeding agent outages...")
        for _ in range(15):
            sid, name = random.choice(all_servers)
            days_ago = random.randint(1, 14)
            duration_min = random.randint(5, 180)
            start = now - timedelta(days=days_ago)
            end = start + timedelta(minutes=duration_min)
            cursor.execute(
                "INSERT INTO dbo.vHealthServiceOutage (ManagedEntityRowId, OutageStartDateTime, OutageEndDateTime) VALUES (%s, %s, %s)",
                (sid, start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S"))
            )
        conn.commit()

    # --- Perf.vPerfDaily (daily aggregation for long-term trends) ---
    try:
        cursor.execute("""IF OBJECT_ID('Perf.vPerfDaily') IS NULL CREATE TABLE Perf.vPerfDaily (
            DateTime DATETIME, PerformanceRuleInstanceRowId INT, ManagedEntityRowId INT,
            SampleCount INT, AverageValue FLOAT, MinValue FLOAT, MaxValue FLOAT, StandardDeviation FLOAT
        )""")
    except Exception:
        pass

    cursor.execute("SELECT COUNT(*) FROM Perf.vPerfDaily")
    if cursor.fetchone()[0] == 0:
        print("  Seeding Perf.vPerfDaily (30 days)...")
        batch = []
        daily_total = 0
        DAILY_PREFIX = "INSERT INTO Perf.vPerfDaily (DateTime, PerformanceRuleInstanceRowId, ManagedEntityRowId, SampleCount, AverageValue, MinValue, MaxValue, StandardDeviation) VALUES"
        key_instances = list(instance_map.items())[:4]  # CPU, memory only
        for day in range(30):
            dt = (now - timedelta(days=day)).strftime("%Y-%m-%d 00:00:00")
            for (obj, ctr, inst), pri_id in key_instances:
                for sid, _ in all_servers:
                    val = gen_value(ctr)
                    batch.append((dt, pri_id, sid, 288, val, val * 0.5, val * 1.5, 2.0))
                    daily_total += 1
        bulk_insert(cursor, conn, DAILY_PREFIX, batch)
        conn.commit()
        print(f"  Perf.vPerfDaily: {daily_total:,} rows")

    # --- State.vStateRaw (precise state changes) ---
    try:
        cursor.execute("""IF OBJECT_ID('State.vStateRaw') IS NULL CREATE TABLE State.vStateRaw (
            DateTime DATETIME, ManagedEntityRowId INT, MonitorRowId INT,
            OldHealthState INT, NewHealthState INT, InMaintenanceMode BIT
        )""")
    except Exception:
        pass

    cursor.execute("SELECT COUNT(*) FROM State.vStateRaw")
    if cursor.fetchone()[0] == 0:
        print("  Seeding State.vStateRaw...")
        batch = []
        for sid, name in all_servers:
            parts = name.split("-")
            role_str = "".join(c for c in parts[2] if not c.isdigit()) if len(parts) >= 3 else "DC"
            unit_mid = ROLE_UNIT_MONITOR.get(role_str, 7)
            # Generate 5-15 state changes per server over 7 days
            for _ in range(random.randint(5, 15)):
                dt = (now - timedelta(hours=random.randint(1, 168))).strftime("%Y-%m-%d %H:%M:%S")
                old_state = random.choice([1, 1, 1, 2])
                new_state = random.choice([1, 1, 1, 2, 3]) if old_state == 1 else 1
                # Aggregate row
                batch.append((dt, sid, 1, old_state, new_state, 0))
                # Unit monitor row when degraded -- provides the root-cause detail
                # that production SCOM DW stores per-monitor
                if new_state > 1:
                    batch.append((dt, sid, unit_mid, 1, new_state, 0))
        bulk_insert(cursor, conn,
            "INSERT INTO State.vStateRaw (DateTime, ManagedEntityRowId, MonitorRowId, OldHealthState, NewHealthState, InMaintenanceMode) VALUES",
            batch)
        conn.commit()
        print(f"  State.vStateRaw: {len(batch)} rows")

    # --- Exchange2013.vMailboxDatabase ---
    try:
        cursor.execute("IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'Exchange2013') EXEC('CREATE SCHEMA Exchange2013')")
    except Exception:
        pass
    try:
        cursor.execute("""IF OBJECT_ID('Exchange2013.vMailboxDatabase') IS NULL CREATE TABLE Exchange2013.vMailboxDatabase (
            DatabaseName NVARCHAR(256),
            DatabaseSizeMB FLOAT,
            AvailableSpaceMB FLOAT,
            MailboxCount INT
        )""")
    except Exception:
        pass

    cursor.execute("SELECT COUNT(*) FROM Exchange2013.vMailboxDatabase")
    if cursor.fetchone()[0] == 0:
        print("  Seeding Exchange mailbox databases...")
        for db_name in ["DB01", "DB02", "DB03"]:
            cursor.execute(
                "INSERT INTO Exchange2013.vMailboxDatabase VALUES (%s, %s, %s, %s)",
                (db_name, random.uniform(5000, 50000), random.uniform(1000, 10000), random.randint(50, 500))
            )
        conn.commit()

    # Final counts
    print("\n  Final counts:")
    for tbl in ["vManagedEntity", "vPerformanceRule", "vPerformanceRuleInstance",
                "Perf.vPerfHourly", "Perf.vPerfRaw", "Perf.vPerfDaily",
                "State.vStateHourly", "State.vStateRaw",
                "Alert.vAlert", "Alert.vAlertDetail", "Alert.vAlertResolutionState",
                "Event.vEvent", "dbo.vMaintenanceMode", "dbo.vHealthServiceOutage",
                "dbo.vMonitor", "dbo.vManagedEntityMonitor",
                "Exchange2013.vMailboxDatabase"]:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
            print(f"    {tbl}: {cursor.fetchone()[0]:,}")
        except Exception:
            print(f"    {tbl}: (not created)")

    conn.close()
    print("\nSCOM DW Simulator seeded successfully (production-aligned schema)!")


if __name__ == "__main__":
    main()
