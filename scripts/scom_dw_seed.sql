-- =============================================================================
-- SCOM Data Warehouse Simulator -- Schema and Seed Data
-- =============================================================================
-- Creates a minimal replica of the SCOM DW schema with synthetic data
-- so Grafana SCOM dashboards can be reviewed without production access.
--
-- Schema matches production OperationsManagerDW (discovered 2026-03-25):
--   - vPerformanceRule (separate table for ObjectName/CounterName)
--   - vPerformanceRuleInstance (RuleRowId reference, not embedded counter names)
--   - Entity type: Microsoft.Windows.Computer (not .Server.Computer)
--   - Hostname pattern: VM-<SITE>-<ROLE><NUM> (matches production convention)
--
-- Tables/views created:
--   vManagedEntityType, vManagedEntity, vRelationship,
--   vPerformanceRule, vPerformanceRuleInstance,
--   Perf.vPerfHourly, State.vStateHourly, Alert.vAlert
-- =============================================================================

USE master;
GO

IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'OperationsManagerDW')
    CREATE DATABASE OperationsManagerDW;
GO

USE OperationsManagerDW;
GO

-- Create read-only login for Grafana
IF NOT EXISTS (SELECT * FROM sys.server_principals WHERE name = 'svc-omread')
    CREATE LOGIN [svc-omread] WITH PASSWORD = 'ScomDemo123!';
GO

IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'svc-omread')
    CREATE USER [svc-omread] FOR LOGIN [svc-omread];
GO

ALTER ROLE db_datareader ADD MEMBER [svc-omread];
GO

-- =============================================================================
-- Dimensional Tables
-- =============================================================================

CREATE TABLE vManagedEntityType (
    ManagedEntityTypeRowId INT PRIMARY KEY IDENTITY(1,1),
    ManagedEntityTypeSystemName NVARCHAR(256)
);

-- Entity types matching production
INSERT INTO vManagedEntityType (ManagedEntityTypeSystemName) VALUES
('Microsoft.Windows.Computer'),                                       -- RowId 1
('System.Group'),                                                      -- RowId 2
('Microsoft.Windows.InternetInformationServices.10.0.ApplicationPool'),-- RowId 3
('Microsoft.Windows.DNSServer.2016.Zone'),                            -- RowId 4
('Microsoft.Windows.Cluster.Group');                                   -- RowId 5

-- Managed Entities (servers and groups)
CREATE TABLE vManagedEntity (
    ManagedEntityRowId INT PRIMARY KEY IDENTITY(1,1),
    ManagedEntityTypeRowId INT,
    Path NVARCHAR(512),
    Name NVARCHAR(256),
    DisplayName NVARCHAR(256),
    FullName NVARCHAR(512)
);

-- =============================================================================
-- Sites and Servers
-- Using production hostname pattern: VM-<SITE>-<ROLE><NUM>
-- Site codes from production: DEN, DV, SBT, SNO, SOL, STR, SUG, TRM, WP
-- Roles: DC, SQL, IIS, FS, APP, DHCP, EXC (Exchange)
-- =============================================================================

DECLARE @sites TABLE (site_code NVARCHAR(10));
INSERT INTO @sites VALUES
('DEN'), ('DV'), ('SBT'), ('SNO'), ('SOL'), ('STR'), ('SUG'), ('TRM'), ('WP');

DECLARE @roles TABLE (role_prefix NVARCHAR(10), role_num_start INT);
INSERT INTO @roles VALUES
('DC', 1), ('SQL', 1), ('IIS', 1), ('FS', 1), ('APP', 1), ('DHCP', 1);

DECLARE @site NVARCHAR(10), @role NVARCHAR(10), @num INT;
DECLARE @hostname NVARCHAR(256);

-- Generate servers per site per role
DECLARE site_cur CURSOR FOR SELECT site_code FROM @sites;
OPEN site_cur;
FETCH NEXT FROM site_cur INTO @site;

WHILE @@FETCH_STATUS = 0
BEGIN
    DECLARE role_cur CURSOR FOR SELECT role_prefix, role_num_start FROM @roles;
    OPEN role_cur;
    FETCH NEXT FROM role_cur INTO @role, @num;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        SET @hostname = 'VM-' + @site + '-' + @role + CAST(@num AS VARCHAR);
        INSERT INTO vManagedEntity (ManagedEntityTypeRowId, Path, Name, DisplayName, FullName)
        VALUES (1, @hostname, @hostname, @hostname, @hostname);

        FETCH NEXT FROM role_cur INTO @role, @num;
    END
    CLOSE role_cur;
    DEALLOCATE role_cur;

    FETCH NEXT FROM site_cur INTO @site;
END
CLOSE site_cur;
DEALLOCATE site_cur;

-- Add a second DC and SQL per site for realism (larger sites)
INSERT INTO vManagedEntity (ManagedEntityTypeRowId, Path, Name, DisplayName, FullName)
SELECT 1,
    'VM-' + s.site_code + '-DC2',
    'VM-' + s.site_code + '-DC2',
    'VM-' + s.site_code + '-DC2',
    'VM-' + s.site_code + '-DC2'
FROM @sites s;

INSERT INTO vManagedEntity (ManagedEntityTypeRowId, Path, Name, DisplayName, FullName)
SELECT 1,
    'VM-' + s.site_code + '-SQL2',
    'VM-' + s.site_code + '-SQL2',
    'VM-' + s.site_code + '-SQL2',
    'VM-' + s.site_code + '-SQL2'
FROM @sites s;

-- Groups (no site groups in production -- use role groups like production)
INSERT INTO vManagedEntity (ManagedEntityTypeRowId, Path, Name, DisplayName, FullName) VALUES
(2, 'AD Domain Controller Group', 'AD Domain Controller Group', 'AD Domain Controller Group (Windows Server 2016)', 'AD Domain Controller Group'),
(2, 'IIS Web Server Group', 'IIS Web Server Group', 'IIS 10.0 Web Server Group', 'IIS Web Server Group'),
(2, 'DHCP Server Group', 'DHCP Server Group', 'DHCP Server Group', 'DHCP Server Group'),
(2, 'All Windows Computers', 'All Windows Computers', 'All Windows Computers', 'All Windows Computers');

-- Relationships (group membership)
CREATE TABLE vRelationship (
    RelationshipRowId INT PRIMARY KEY IDENTITY(1,1),
    SourceManagedEntityRowId INT,
    TargetManagedEntityRowId INT
);

-- Map DCs to DC group
INSERT INTO vRelationship (SourceManagedEntityRowId, TargetManagedEntityRowId)
SELECT g.ManagedEntityRowId, s.ManagedEntityRowId
FROM vManagedEntity s, vManagedEntity g
WHERE s.ManagedEntityTypeRowId = 1 AND s.DisplayName LIKE '%-DC%'
AND g.DisplayName LIKE 'AD Domain Controller Group%';

-- Map IIS to IIS group
INSERT INTO vRelationship (SourceManagedEntityRowId, TargetManagedEntityRowId)
SELECT g.ManagedEntityRowId, s.ManagedEntityRowId
FROM vManagedEntity s, vManagedEntity g
WHERE s.ManagedEntityTypeRowId = 1 AND s.DisplayName LIKE '%-IIS%'
AND g.DisplayName LIKE 'IIS%';

-- Map DHCP to DHCP group
INSERT INTO vRelationship (SourceManagedEntityRowId, TargetManagedEntityRowId)
SELECT g.ManagedEntityRowId, s.ManagedEntityRowId
FROM vManagedEntity s, vManagedEntity g
WHERE s.ManagedEntityTypeRowId = 1 AND s.DisplayName LIKE '%-DHCP%'
AND g.DisplayName LIKE 'DHCP%';

-- Map all servers to All Windows Computers
INSERT INTO vRelationship (SourceManagedEntityRowId, TargetManagedEntityRowId)
SELECT g.ManagedEntityRowId, s.ManagedEntityRowId
FROM vManagedEntity s, vManagedEntity g
WHERE s.ManagedEntityTypeRowId = 1
AND g.DisplayName = 'All Windows Computers';

-- =============================================================================
-- Performance Rules (counter definitions -- separate table in production)
-- =============================================================================

CREATE TABLE vPerformanceRule (
    RuleRowId INT PRIMARY KEY IDENTITY(1,1),
    ObjectName NVARCHAR(256),
    CounterName NVARCHAR(256),
    MultiInstanceId INT DEFAULT 0,
    LastReceivedDateTime DATETIME DEFAULT GETUTCDATE()
);

-- Counter names matching production discovery (2026-03-25)
INSERT INTO vPerformanceRule (ObjectName, CounterName) VALUES
-- Windows OS (collected on all servers)
('Processor Information', '% Processor Time'),                        -- 1
('Memory', 'PercentMemoryUsed'),                                      -- 2
('Memory', 'Available MBytes'),                                       -- 3
('Memory', 'Pages/sec'),                                              -- 4
('LogicalDisk', '% Free Space'),                                      -- 5
('LogicalDisk', 'Free Megabytes'),                                    -- 6
('LogicalDisk', '% Idle Time'),                                       -- 7
('LogicalDisk', 'Avg. Disk sec/Transfer'),                            -- 8
('LogicalDisk', 'Current Disk Queue Length'),                         -- 9
('Network Adapter', 'Bytes Total/sec'),                               -- 10
('Network Adapter', 'Current Bandwidth'),                             -- 11
('Network Adapter', 'PercentBandwidthUsedTotal'),                     -- 12
('System', 'Processor Queue Length'),                                  -- 13
('System', 'System Up Time'),                                         -- 14
-- AD/DC (DirectoryServices, not NTDS)
('DirectoryServices', 'LDAP Searches/sec'),                           -- 15
('DirectoryServices', 'LDAP Client Sessions'),                        -- 16
('DirectoryServices', 'LDAP Writes/sec'),                             -- 17
('DirectoryServices', 'DRA Inbound Bytes Total/sec'),                 -- 18
('DirectoryServices', 'DRA Outbound Bytes Total/sec'),                -- 19
('DirectoryServices', 'DS Search sub-operations/sec'),                -- 20
('Security System-Wide Statistics', 'Kerberos Authentications'),      -- 21
('Security System-Wide Statistics', 'NTLM Authentications'),          -- 22
('Security System-Wide Statistics', 'KDC AS Requests'),               -- 23
('Security System-Wide Statistics', 'KDC TGS Requests'),              -- 24
-- DNS
('DNS', 'Total Query Received/sec'),                                   -- 25
('DNS', 'Recursive Queries/sec'),                                      -- 26
('DNS', 'Dynamic Update Received/sec'),                                -- 27
-- IIS / Web Service
('Web Service', 'Current Connections'),                                -- 28
('Web Service', 'Total Method Requests/sec'),                          -- 29
('Web Service', 'Bytes Total/sec'),                                    -- 30
('Web Service', 'Bytes Received/sec'),                                 -- 31
('Web Service', 'Bytes Sent/sec'),                                     -- 32
('Web Service', 'Connection Attempts/sec'),                            -- 33
-- DHCP
('DHCP Server', 'Acks/sec'),                                           -- 34
('DHCP Server', 'Requests/sec'),                                       -- 35
('DHCP Server', 'Discovers/sec'),                                      -- 36
('DHCP Server', 'Active Queue Length'),                                -- 37
('DHCP Server', 'Packets Received/sec'),                               -- 38
-- AD Storage
('AD Storage', 'Database Size'),                                       -- 39
('AD Storage', 'Database Drive Free Space'),                           -- 40
('AD Storage', 'Log File Drive Free Space'),                           -- 41
-- DFS Replication
('DFS Replicated Folders', 'Staging Space In Use'),                    -- 42
('DFS Replicated Folders', 'Conflict Space In Use'),                   -- 43
('DFS Replication Connections', 'Bandwidth Savings Using DFS Replication'); -- 44

-- Performance Rule Instances (links rules to specific instances)
-- Production schema: RuleRowId + InstanceName, no ObjectName/CounterName
CREATE TABLE vPerformanceRuleInstance (
    PerformanceRuleInstanceRowId INT PRIMARY KEY IDENTITY(1,1),
    RuleRowId INT,
    InstanceName NVARCHAR(256),
    LastReceivedDateTime DATETIME DEFAULT GETUTCDATE()
);

-- Create instances for each rule
-- OS counters: _Total or per-instance
INSERT INTO vPerformanceRuleInstance (RuleRowId, InstanceName) VALUES
(1, '_Total'),       -- Processor Information / % Processor Time
(2, ''),             -- Memory / PercentMemoryUsed
(3, ''),             -- Memory / Available MBytes
(4, ''),             -- Memory / Pages/sec
(5, 'C:'),           -- LogicalDisk / % Free Space (C:)
(5, 'D:'),           -- LogicalDisk / % Free Space (D:)
(6, 'C:'),           -- LogicalDisk / Free Megabytes (C:)
(6, 'D:'),           -- LogicalDisk / Free Megabytes (D:)
(7, 'C:'),           -- LogicalDisk / % Idle Time
(8, 'C:'),           -- LogicalDisk / Avg. Disk sec/Transfer
(8, 'D:'),           -- LogicalDisk / Avg. Disk sec/Transfer
(9, 'C:'),           -- LogicalDisk / Current Disk Queue Length
(10, 'Ethernet0'),   -- Network Adapter / Bytes Total/sec
(11, 'Ethernet0'),   -- Network Adapter / Current Bandwidth
(12, 'Ethernet0'),   -- Network Adapter / PercentBandwidthUsedTotal
(13, ''),            -- System / Processor Queue Length
(14, ''),            -- System / System Up Time
-- AD/DC counters (one instance each)
(15, ''), (16, ''), (17, ''), (18, ''), (19, ''), (20, ''),
(21, ''), (22, ''), (23, ''), (24, ''),
-- DNS
(25, ''), (26, ''), (27, ''),
-- IIS (per _Total site)
(28, '_Total'), (29, '_Total'), (30, '_Total'),
(31, '_Total'), (32, '_Total'), (33, '_Total'),
-- DHCP
(34, ''), (35, ''), (36, ''), (37, ''), (38, ''),
-- AD Storage
(39, ''), (40, ''), (41, ''),
-- DFS
(42, ''), (43, ''), (44, '');
GO

-- =============================================================================
-- Performance Data (Perf schema)
-- =============================================================================

CREATE SCHEMA Perf;
GO

CREATE TABLE Perf.vPerfHourly (
    DateTime DATETIME,
    PerformanceRuleInstanceRowId INT,
    ManagedEntityRowId INT,
    SampleCount INT,
    AverageValue FLOAT,
    MinValue FLOAT,
    MaxValue FLOAT,
    StandardDeviation FLOAT
);

CREATE INDEX IX_PerfHourly_DateTime ON Perf.vPerfHourly (DateTime);
CREATE INDEX IX_PerfHourly_Entity ON Perf.vPerfHourly (ManagedEntityRowId);
CREATE INDEX IX_PerfHourly_Rule ON Perf.vPerfHourly (PerformanceRuleInstanceRowId);
GO

-- Populate 7 days of hourly data
-- OS counters (RuleRowId 1-14, InstanceRowId 1-17) go to ALL servers
-- AD counters (RuleRowId 15-24) go to DC servers only
-- DNS counters (RuleRowId 25-27) go to DC servers only
-- IIS counters (RuleRowId 28-33) go to IIS servers only
-- DHCP counters (RuleRowId 34-38) go to DHCP servers only
-- AD Storage (RuleRowId 39-41) go to DC servers only
-- DFS (RuleRowId 42-44) go to DC and FS servers

DECLARE @hour INT = 0;
WHILE @hour < 168
BEGIN
    DECLARE @dt DATETIME = DATEADD(hour, -@hour, GETUTCDATE());

    -- OS counters for ALL servers (PerformanceRuleInstanceRowId 1-17)
    INSERT INTO Perf.vPerfHourly (DateTime, PerformanceRuleInstanceRowId, ManagedEntityRowId, SampleCount, AverageValue, MinValue, MaxValue, StandardDeviation)
    SELECT @dt, pri.PerformanceRuleInstanceRowId, me.ManagedEntityRowId, 12,
        CASE pr.CounterName
            WHEN '% Processor Time' THEN 15.0 + (ABS(CHECKSUM(NEWID())) % 70)
            WHEN 'PercentMemoryUsed' THEN 30.0 + (ABS(CHECKSUM(NEWID())) % 50)
            WHEN 'Available MBytes' THEN 1024.0 + (ABS(CHECKSUM(NEWID())) % 12288)
            WHEN 'Pages/sec' THEN (ABS(CHECKSUM(NEWID())) % 100)
            WHEN '% Free Space' THEN 10.0 + (ABS(CHECKSUM(NEWID())) % 75)
            WHEN 'Free Megabytes' THEN 5000.0 + (ABS(CHECKSUM(NEWID())) % 50000)
            WHEN '% Idle Time' THEN 40.0 + (ABS(CHECKSUM(NEWID())) % 60)
            WHEN 'Avg. Disk sec/Transfer' THEN 0.001 + (ABS(CHECKSUM(NEWID())) % 20) * 0.001
            WHEN 'Current Disk Queue Length' THEN (ABS(CHECKSUM(NEWID())) % 3)
            WHEN 'Bytes Total/sec' THEN 100000.0 + (ABS(CHECKSUM(NEWID())) % 20000000)
            WHEN 'Current Bandwidth' THEN 1000000000
            WHEN 'PercentBandwidthUsedTotal' THEN 1.0 + (ABS(CHECKSUM(NEWID())) % 30)
            WHEN 'Processor Queue Length' THEN (ABS(CHECKSUM(NEWID())) % 5)
            WHEN 'System Up Time' THEN 86400.0 + (ABS(CHECKSUM(NEWID())) % 8640000)
            ELSE 0
        END,
        0, 0, 1.0
    FROM vManagedEntity me
    CROSS JOIN vPerformanceRuleInstance pri
    INNER JOIN vPerformanceRule pr ON pri.RuleRowId = pr.RuleRowId
    WHERE me.ManagedEntityTypeRowId = 1
    AND pri.PerformanceRuleInstanceRowId BETWEEN 1 AND 17;

    -- AD/DC counters for DC servers only (PerformanceRuleInstanceRowId 18-27)
    INSERT INTO Perf.vPerfHourly (DateTime, PerformanceRuleInstanceRowId, ManagedEntityRowId, SampleCount, AverageValue, MinValue, MaxValue, StandardDeviation)
    SELECT @dt, pri.PerformanceRuleInstanceRowId, me.ManagedEntityRowId, 12,
        CASE pr.CounterName
            WHEN 'LDAP Searches/sec' THEN 50.0 + (ABS(CHECKSUM(NEWID())) % 450)
            WHEN 'LDAP Client Sessions' THEN 10.0 + (ABS(CHECKSUM(NEWID())) % 200)
            WHEN 'LDAP Writes/sec' THEN 5.0 + (ABS(CHECKSUM(NEWID())) % 50)
            WHEN 'DRA Inbound Bytes Total/sec' THEN 10000.0 + (ABS(CHECKSUM(NEWID())) % 190000)
            WHEN 'DRA Outbound Bytes Total/sec' THEN 10000.0 + (ABS(CHECKSUM(NEWID())) % 190000)
            WHEN 'DS Search sub-operations/sec' THEN 20.0 + (ABS(CHECKSUM(NEWID())) % 200)
            WHEN 'Kerberos Authentications' THEN 20.0 + (ABS(CHECKSUM(NEWID())) % 280)
            WHEN 'NTLM Authentications' THEN 5.0 + (ABS(CHECKSUM(NEWID())) % 45)
            WHEN 'KDC AS Requests' THEN 10.0 + (ABS(CHECKSUM(NEWID())) % 100)
            WHEN 'KDC TGS Requests' THEN 20.0 + (ABS(CHECKSUM(NEWID())) % 200)
            ELSE 0
        END,
        0, 0, 1.0
    FROM vManagedEntity me
    CROSS JOIN vPerformanceRuleInstance pri
    INNER JOIN vPerformanceRule pr ON pri.RuleRowId = pr.RuleRowId
    WHERE me.ManagedEntityTypeRowId = 1 AND me.DisplayName LIKE '%-DC%'
    AND pri.PerformanceRuleInstanceRowId BETWEEN 18 AND 27;

    -- DNS counters for DC servers (PerformanceRuleInstanceRowId 28-30)
    INSERT INTO Perf.vPerfHourly (DateTime, PerformanceRuleInstanceRowId, ManagedEntityRowId, SampleCount, AverageValue, MinValue, MaxValue, StandardDeviation)
    SELECT @dt, pri.PerformanceRuleInstanceRowId, me.ManagedEntityRowId, 12,
        CASE pr.CounterName
            WHEN 'Total Query Received/sec' THEN 100.0 + (ABS(CHECKSUM(NEWID())) % 900)
            WHEN 'Recursive Queries/sec' THEN 10.0 + (ABS(CHECKSUM(NEWID())) % 190)
            WHEN 'Dynamic Update Received/sec' THEN (ABS(CHECKSUM(NEWID())) % 20)
            ELSE 0
        END,
        0, 0, 1.0
    FROM vManagedEntity me
    CROSS JOIN vPerformanceRuleInstance pri
    INNER JOIN vPerformanceRule pr ON pri.RuleRowId = pr.RuleRowId
    WHERE me.ManagedEntityTypeRowId = 1 AND me.DisplayName LIKE '%-DC%'
    AND pri.PerformanceRuleInstanceRowId BETWEEN 28 AND 30;

    -- IIS counters for IIS servers (PerformanceRuleInstanceRowId 31-36)
    INSERT INTO Perf.vPerfHourly (DateTime, PerformanceRuleInstanceRowId, ManagedEntityRowId, SampleCount, AverageValue, MinValue, MaxValue, StandardDeviation)
    SELECT @dt, pri.PerformanceRuleInstanceRowId, me.ManagedEntityRowId, 12,
        CASE pr.CounterName
            WHEN 'Current Connections' THEN 5.0 + (ABS(CHECKSUM(NEWID())) % 195)
            WHEN 'Total Method Requests/sec' THEN 10.0 + (ABS(CHECKSUM(NEWID())) % 290)
            WHEN 'Bytes Total/sec' THEN 50000.0 + (ABS(CHECKSUM(NEWID())) % 450000)
            WHEN 'Bytes Received/sec' THEN 20000.0 + (ABS(CHECKSUM(NEWID())) % 200000)
            WHEN 'Bytes Sent/sec' THEN 30000.0 + (ABS(CHECKSUM(NEWID())) % 300000)
            WHEN 'Connection Attempts/sec' THEN 5.0 + (ABS(CHECKSUM(NEWID())) % 100)
            ELSE 0
        END,
        0, 0, 1.0
    FROM vManagedEntity me
    CROSS JOIN vPerformanceRuleInstance pri
    INNER JOIN vPerformanceRule pr ON pri.RuleRowId = pr.RuleRowId
    WHERE me.ManagedEntityTypeRowId = 1 AND me.DisplayName LIKE '%-IIS%'
    AND pri.PerformanceRuleInstanceRowId BETWEEN 31 AND 36;

    -- DHCP counters for DHCP servers (PerformanceRuleInstanceRowId 37-41)
    INSERT INTO Perf.vPerfHourly (DateTime, PerformanceRuleInstanceRowId, ManagedEntityRowId, SampleCount, AverageValue, MinValue, MaxValue, StandardDeviation)
    SELECT @dt, pri.PerformanceRuleInstanceRowId, me.ManagedEntityRowId, 12,
        CASE pr.CounterName
            WHEN 'Acks/sec' THEN 1.0 + (ABS(CHECKSUM(NEWID())) % 50)
            WHEN 'Requests/sec' THEN 2.0 + (ABS(CHECKSUM(NEWID())) % 60)
            WHEN 'Discovers/sec' THEN 1.0 + (ABS(CHECKSUM(NEWID())) % 30)
            WHEN 'Active Queue Length' THEN (ABS(CHECKSUM(NEWID())) % 5)
            WHEN 'Packets Received/sec' THEN 5.0 + (ABS(CHECKSUM(NEWID())) % 100)
            ELSE 0
        END,
        0, 0, 1.0
    FROM vManagedEntity me
    CROSS JOIN vPerformanceRuleInstance pri
    INNER JOIN vPerformanceRule pr ON pri.RuleRowId = pr.RuleRowId
    WHERE me.ManagedEntityTypeRowId = 1 AND me.DisplayName LIKE '%-DHCP%'
    AND pri.PerformanceRuleInstanceRowId BETWEEN 37 AND 41;

    -- AD Storage for DC servers (PerformanceRuleInstanceRowId 42-44)
    INSERT INTO Perf.vPerfHourly (DateTime, PerformanceRuleInstanceRowId, ManagedEntityRowId, SampleCount, AverageValue, MinValue, MaxValue, StandardDeviation)
    SELECT @dt, pri.PerformanceRuleInstanceRowId, me.ManagedEntityRowId, 12,
        CASE pr.CounterName
            WHEN 'Database Size' THEN 500.0 + (ABS(CHECKSUM(NEWID())) % 2000)
            WHEN 'Database Drive Free Space' THEN 10000.0 + (ABS(CHECKSUM(NEWID())) % 40000)
            WHEN 'Log File Drive Free Space' THEN 5000.0 + (ABS(CHECKSUM(NEWID())) % 20000)
            ELSE 0
        END,
        0, 0, 1.0
    FROM vManagedEntity me
    CROSS JOIN vPerformanceRuleInstance pri
    INNER JOIN vPerformanceRule pr ON pri.RuleRowId = pr.RuleRowId
    WHERE me.ManagedEntityTypeRowId = 1 AND me.DisplayName LIKE '%-DC%'
    AND pri.PerformanceRuleInstanceRowId BETWEEN 42 AND 44;

    -- DFS for DC and FS servers (PerformanceRuleInstanceRowId 45-47)
    INSERT INTO Perf.vPerfHourly (DateTime, PerformanceRuleInstanceRowId, ManagedEntityRowId, SampleCount, AverageValue, MinValue, MaxValue, StandardDeviation)
    SELECT @dt, pri.PerformanceRuleInstanceRowId, me.ManagedEntityRowId, 12,
        CASE pr.CounterName
            WHEN 'Staging Space In Use' THEN 100.0 + (ABS(CHECKSUM(NEWID())) % 5000)
            WHEN 'Conflict Space In Use' THEN (ABS(CHECKSUM(NEWID())) % 500)
            WHEN 'Bandwidth Savings Using DFS Replication' THEN 1000.0 + (ABS(CHECKSUM(NEWID())) % 100000)
            ELSE 0
        END,
        0, 0, 1.0
    FROM vManagedEntity me
    CROSS JOIN vPerformanceRuleInstance pri
    INNER JOIN vPerformanceRule pr ON pri.RuleRowId = pr.RuleRowId
    WHERE me.ManagedEntityTypeRowId = 1 AND (me.DisplayName LIKE '%-DC%' OR me.DisplayName LIKE '%-FS%')
    AND pri.PerformanceRuleInstanceRowId BETWEEN 45 AND 47;

    SET @hour = @hour + 1;
END
GO

-- =============================================================================
-- State Data (State schema)
-- =============================================================================

CREATE SCHEMA State;
GO

CREATE TABLE State.vStateHourly (
    DateTime DATETIME,
    ManagedEntityRowId INT,
    MonitorRowId INT,
    OldHealthState INT,
    NewHealthState INT,
    InMaintenanceMode BIT
);

-- Populate 7 days of state snapshots (every 4 hours)
DECLARE @sh INT = 0;
WHILE @sh < 168
BEGIN
    INSERT INTO State.vStateHourly (DateTime, ManagedEntityRowId, MonitorRowId, OldHealthState, NewHealthState, InMaintenanceMode)
    SELECT
        DATEADD(hour, -@sh, GETUTCDATE()),
        me.ManagedEntityRowId,
        1,
        1,
        CASE WHEN ABS(CHECKSUM(NEWID())) % 20 = 0 THEN 2
             WHEN ABS(CHECKSUM(NEWID())) % 50 = 0 THEN 3
             ELSE 1 END,
        CASE WHEN ABS(CHECKSUM(NEWID())) % 30 = 0 THEN 1 ELSE 0 END
    FROM vManagedEntity me
    WHERE me.ManagedEntityTypeRowId = 1;

    SET @sh = @sh + 4;
END
GO

-- =============================================================================
-- Alert Data (Alert schema)
-- =============================================================================

CREATE SCHEMA Alert;
GO

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
);

-- Active alerts
INSERT INTO Alert.vAlert (AlertName, AlertDescription, Severity, Priority, ResolutionState, RaisedDateTime, ManagedEntityRowId)
SELECT TOP 15
    CASE ABS(CHECKSUM(NEWID())) % 6
        WHEN 0 THEN 'Logical Disk Free Space is low'
        WHEN 1 THEN 'Windows Service Stopped'
        WHEN 2 THEN 'Processor Utilization exceeded threshold'
        WHEN 3 THEN 'Memory Pages/sec exceeded threshold'
        WHEN 4 THEN 'DNS Resolution Failure Rate High'
        WHEN 5 THEN 'Health Service Heartbeat Failure'
    END,
    'Threshold exceeded on ' + me.DisplayName,
    CASE WHEN ABS(CHECKSUM(NEWID())) % 3 = 0 THEN 2 ELSE 1 END,
    1,
    0,
    DATEADD(hour, -(ABS(CHECKSUM(NEWID())) % 72), GETUTCDATE()),
    me.ManagedEntityRowId
FROM vManagedEntity me
WHERE me.ManagedEntityTypeRowId = 1
ORDER BY NEWID();

-- Resolved alerts
INSERT INTO Alert.vAlert (AlertName, AlertDescription, Severity, Priority, ResolutionState, RaisedDateTime, ResolvedDateTime, ManagedEntityRowId)
SELECT TOP 50
    CASE ABS(CHECKSUM(NEWID())) % 6
        WHEN 0 THEN 'Logical Disk Free Space is low'
        WHEN 1 THEN 'Windows Service Stopped'
        WHEN 2 THEN 'Processor Utilization exceeded threshold'
        WHEN 3 THEN 'Memory Pages/sec exceeded threshold'
        WHEN 4 THEN 'DNS Resolution Failure Rate High'
        WHEN 5 THEN 'Health Service Heartbeat Failure'
    END,
    'Resolved alert on ' + me.DisplayName,
    CASE WHEN ABS(CHECKSUM(NEWID())) % 4 = 0 THEN 2 ELSE 1 END,
    1,
    255,
    DATEADD(hour, -(ABS(CHECKSUM(NEWID())) % 168), GETUTCDATE()),
    DATEADD(minute, (ABS(CHECKSUM(NEWID())) % 240), DATEADD(hour, -(ABS(CHECKSUM(NEWID())) % 168), GETUTCDATE())),
    me.ManagedEntityRowId
FROM vManagedEntity me
WHERE me.ManagedEntityTypeRowId = 1
ORDER BY NEWID();
GO

PRINT 'SCOM DW Simulator seeded successfully (production-aligned schema)';
GO
