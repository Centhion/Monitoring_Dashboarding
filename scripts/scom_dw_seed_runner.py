#!/usr/bin/env python3
"""
Seeds the SCOM DW Simulator (Azure SQL Edge) with schema and demo data.
Run after the scom-dw-sim container is healthy.

Usage:
    python scripts/scom_dw_seed_runner.py
"""

import sys
import time
import random

try:
    import pymssql
except ImportError:
    print("ERROR: pymssql required. Install: pip install pymssql")
    sys.exit(1)

HOST = "localhost"
PORT = 1433
USER = "sa"
PASSWORD = "ScomDemo123!"
DB = "OperationsManagerDW"

def execute(conn, sql, ignore_errors=False):
    """Execute SQL statement."""
    cursor = conn.cursor()
    try:
        cursor.execute(sql)
        conn.commit()
        return True
    except Exception as e:
        if not ignore_errors:
            print(f"  ERROR: {str(e)[:120]}")
        return False

def main():
    print("Connecting to SCOM DW Simulator...")

    # Step 1: Create database
    conn = pymssql.connect(server=HOST, port=PORT, user=USER, password=PASSWORD, autocommit=True)
    print("  Connected to SQL Server")

    execute(conn, f"IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{DB}') CREATE DATABASE [{DB}]")
    print("  Database created")
    conn.close()

    # Step 2: Connect to the new database
    conn = pymssql.connect(server=HOST, port=PORT, user=USER, password=PASSWORD, database=DB, autocommit=True)

    # Create login and user
    execute(conn, "IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = 'svc-omread') CREATE LOGIN [svc-omread] WITH PASSWORD = 'ScomDemo123!'", ignore_errors=True)
    execute(conn, "IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'svc-omread') CREATE USER [svc-omread] FOR LOGIN [svc-omread]", ignore_errors=True)
    execute(conn, "ALTER ROLE db_datareader ADD MEMBER [svc-omread]", ignore_errors=True)
    print("  User svc-omread created")

    # Create schemas
    for schema in ["Perf", "State", "Alert"]:
        execute(conn, f"IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = '{schema}') EXEC('CREATE SCHEMA [{schema}]')")
    print("  Schemas created")

    # Create tables
    execute(conn, """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'vManagedEntityType')
        CREATE TABLE vManagedEntityType (
            ManagedEntityTypeRowId INT PRIMARY KEY IDENTITY(1,1),
            ManagedEntityTypeSystemName NVARCHAR(256)
        )
    """)

    execute(conn, """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'vManagedEntity')
        CREATE TABLE vManagedEntity (
            ManagedEntityRowId INT PRIMARY KEY IDENTITY(1,1),
            ManagedEntityTypeRowId INT,
            Path NVARCHAR(512),
            Name NVARCHAR(256),
            DisplayName NVARCHAR(256),
            FullName NVARCHAR(512)
        )
    """)

    execute(conn, """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'vRelationship')
        CREATE TABLE vRelationship (
            RelationshipRowId INT PRIMARY KEY IDENTITY(1,1),
            SourceManagedEntityRowId INT,
            TargetManagedEntityRowId INT
        )
    """)

    execute(conn, """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'vPerformanceRuleInstance')
        CREATE TABLE vPerformanceRuleInstance (
            PerformanceRuleInstanceRowId INT PRIMARY KEY IDENTITY(1,1),
            ObjectName NVARCHAR(256),
            CounterName NVARCHAR(256),
            InstanceName NVARCHAR(256)
        )
    """)

    execute(conn, """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'vPerfHourly' AND SCHEMA_ID('Perf') IS NOT NULL)
        CREATE TABLE Perf.vPerfHourly (
            DateTime DATETIME,
            ManagedEntityRowId INT,
            PerformanceRuleInstanceRowId INT,
            SampleCount INT,
            AverageValue FLOAT,
            MinValue FLOAT,
            MaxValue FLOAT,
            StandardDeviation FLOAT
        )
    """)

    execute(conn, """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'vStateHourly' AND SCHEMA_ID('State') IS NOT NULL)
        CREATE TABLE State.vStateHourly (
            DateTime DATETIME,
            ManagedEntityRowId INT,
            MonitorRowId INT,
            OldHealthState INT,
            NewHealthState INT,
            InMaintenanceMode BIT
        )
    """)

    execute(conn, """
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'vAlert' AND SCHEMA_ID('Alert') IS NOT NULL)
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
        )
    """)
    print("  Tables created")

    # Check if already seeded
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM vManagedEntity")
    if cursor.fetchone()[0] > 0:
        print("  Already seeded -- skipping data insert")
        cursor.execute("SELECT COUNT(*) FROM vManagedEntity")
        print(f"  Entities: {cursor.fetchone()[0]}")
        cursor.execute("SELECT COUNT(*) FROM Perf.vPerfHourly")
        print(f"  Perf rows: {cursor.fetchone()[0]}")
        cursor.execute("SELECT COUNT(*) FROM Alert.vAlert")
        print(f"  Alerts: {cursor.fetchone()[0]}")
        conn.close()
        return

    # Seed entity types
    execute(conn, """
        INSERT INTO vManagedEntityType (ManagedEntityTypeSystemName) VALUES
        ('Microsoft.Windows.Computer'),
        ('Microsoft.Windows.Server.Computer'),
        ('System.Group'),
        ('Microsoft.SQLServer.DBEngine'),
        ('Microsoft.Windows.InternetInformationServices.ApplicationPool')
    """)

    # Seed groups
    groups = [
        "Steamboat Servers", "Deer Valley Monitors", "Solitude Servers",
        "Snowshoe Servers", "Stratton Servers", "Sugarbush Servers",
        "Tremblant Servers", "CMH Servers", "DEV Servers", "UAT Servers",
    ]
    for g in groups:
        execute(conn, f"INSERT INTO vManagedEntity (ManagedEntityTypeRowId, Path, Name, DisplayName, FullName) VALUES (3, '{g}', '{g}', '{g}', '{g}')")

    # Seed servers
    sites = {
        "Steamboat Servers": "SBT", "Deer Valley Monitors": "DV", "Solitude Servers": "SOL",
        "Snowshoe Servers": "SNO", "Stratton Servers": "STR", "Sugarbush Servers": "SGB",
        "Tremblant Servers": "TMB", "CMH Servers": "CMH",
    }
    roles = ["DC", "SQL", "IIS", "FS", "APP", "DHCP"]

    for site_name, site_abbrev in sites.items():
        for i, role in enumerate(roles):
            hostname = f"SRV-{role}-{i+1:02d}.{site_abbrev}.alterra.com"
            execute(conn, f"INSERT INTO vManagedEntity (ManagedEntityTypeRowId, Path, Name, DisplayName, FullName) VALUES (2, '{hostname}', '{hostname}', '{hostname}', '{hostname}')")

    print(f"  Seeded {len(sites) * len(roles)} servers across {len(sites)} sites")

    # Seed relationships (group membership)
    for group_name, abbrev in sites.items():
        execute(conn, f"""
            INSERT INTO vRelationship (SourceManagedEntityRowId, TargetManagedEntityRowId)
            SELECT g.ManagedEntityRowId, s.ManagedEntityRowId
            FROM vManagedEntity s, vManagedEntity g
            WHERE s.ManagedEntityTypeRowId = 2 AND g.DisplayName = '{group_name}'
            AND s.Path LIKE '%.{abbrev}.%'
        """)
    print("  Relationships seeded")

    # Seed performance counters
    counters = [
        ("Processor", "% Processor Time", "_Total"),
        ("Memory", "Available MBytes", ""),
        ("Memory", "% Committed Bytes In Use", ""),
        ("LogicalDisk", "% Free Space", "C:"),
        ("LogicalDisk", "% Free Space", "D:"),
        ("LogicalDisk", "Avg. Disk sec/Read", "C:"),
        ("LogicalDisk", "Avg. Disk sec/Write", "C:"),
        ("LogicalDisk", "Disk Bytes/sec", "C:"),
        ("Network Interface", "Bytes Total/sec", "Ethernet0"),
        ("System", "Processor Queue Length", ""),
    ]
    for obj, counter, inst in counters:
        execute(conn, f"INSERT INTO vPerformanceRuleInstance (ObjectName, CounterName, InstanceName) VALUES ('{obj}', '{counter}', '{inst}')")
    print("  Counters seeded")

    # Seed performance data (7 days hourly)
    print("  Seeding 7 days of hourly performance data...")
    cursor = conn.cursor()
    cursor.execute("SELECT ManagedEntityRowId FROM vManagedEntity WHERE ManagedEntityTypeRowId = 2")
    server_ids = [r[0] for r in cursor.fetchall()]

    cursor.execute("SELECT PerformanceRuleInstanceRowId, CounterName FROM vPerformanceRuleInstance")
    counter_rows = cursor.fetchall()

    batch_size = 500
    values = []

    for hour in range(168):
        for server_id in server_ids:
            for counter_id, counter_name in counter_rows:
                if counter_name == "% Processor Time":
                    avg_val = 20 + random.random() * 60
                elif counter_name == "Available MBytes":
                    avg_val = 2048 + random.random() * 8192
                elif counter_name == "% Committed Bytes In Use":
                    avg_val = 30 + random.random() * 50
                elif counter_name == "% Free Space":
                    avg_val = 15 + random.random() * 70
                elif "Disk sec" in counter_name:
                    avg_val = 0.001 + random.random() * 0.02
                elif counter_name == "Disk Bytes/sec":
                    avg_val = 1e6 + random.random() * 5e7
                elif counter_name == "Bytes Total/sec":
                    avg_val = 5e5 + random.random() * 2e7
                elif counter_name == "Processor Queue Length":
                    avg_val = random.randint(0, 5)
                else:
                    avg_val = random.random() * 100

                values.append(f"(DATEADD(hour, -{hour}, GETUTCDATE()), {server_id}, {counter_id}, 12, {avg_val:.4f}, {avg_val*0.5:.4f}, {avg_val*1.5:.4f}, 1.0)")

                if len(values) >= batch_size:
                    sql = f"INSERT INTO Perf.vPerfHourly (DateTime, ManagedEntityRowId, PerformanceRuleInstanceRowId, SampleCount, AverageValue, MinValue, MaxValue, StandardDeviation) VALUES {','.join(values)}"
                    execute(conn, sql)
                    values = []

        if (hour + 1) % 24 == 0:
            print(f"    Day {(hour+1)//24}/7 complete")

    if values:
        sql = f"INSERT INTO Perf.vPerfHourly (DateTime, ManagedEntityRowId, PerformanceRuleInstanceRowId, SampleCount, AverageValue, MinValue, MaxValue, StandardDeviation) VALUES {','.join(values)}"
        execute(conn, sql)

    # Seed state data
    print("  Seeding health state data...")
    for server_id in server_ids:
        health = random.choices([1, 2, 3], weights=[90, 8, 2])[0]
        maint = 1 if random.random() < 0.03 else 0
        execute(conn, f"INSERT INTO State.vStateHourly VALUES (GETUTCDATE(), {server_id}, 1, 1, {health}, {maint})")

    # Seed alerts
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
    sample_servers = random.sample(server_ids, min(15, len(server_ids)))
    for sid in sample_servers:
        alert = random.choice(alert_names)
        sev = random.choice([1, 1, 2])
        hours_ago = random.randint(1, 72)
        execute(conn, f"INSERT INTO Alert.vAlert (AlertName, AlertDescription, Severity, Priority, ResolutionState, RaisedDateTime, ManagedEntityRowId) VALUES ('{alert}', 'Threshold exceeded', {sev}, 1, 0, DATEADD(hour, -{hours_ago}, GETUTCDATE()), {sid})")

    # Resolved alerts
    sample_servers2 = random.sample(server_ids, min(50, len(server_ids)))
    for sid in sample_servers2:
        alert = random.choice(alert_names)
        sev = random.choice([1, 1, 2])
        hours_ago = random.randint(1, 168)
        duration = random.randint(10, 240)
        execute(conn, f"INSERT INTO Alert.vAlert (AlertName, AlertDescription, Severity, Priority, ResolutionState, RaisedDateTime, ResolvedDateTime, ManagedEntityRowId) VALUES ('{alert}', 'Resolved', {sev}, 1, 255, DATEADD(hour, -{hours_ago}, GETUTCDATE()), DATEADD(minute, {duration}, DATEADD(hour, -{hours_ago}, GETUTCDATE())), {sid})")

    # Final counts
    cursor.execute("SELECT COUNT(*) FROM vManagedEntity")
    print(f"\n  Entities: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM Perf.vPerfHourly")
    print(f"  Perf rows: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM Alert.vAlert")
    print(f"  Alerts: {cursor.fetchone()[0]}")
    cursor.execute("SELECT COUNT(*) FROM State.vStateHourly")
    print(f"  State rows: {cursor.fetchone()[0]}")

    conn.close()
    print("\nSCOM DW Simulator seeded successfully!")

if __name__ == "__main__":
    main()
