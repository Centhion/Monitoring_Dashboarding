-- =============================================================================
-- SCOM Data Warehouse Simulator -- Schema and Seed Data
-- =============================================================================
-- Creates a minimal replica of the SCOM DW schema with synthetic data
-- so Grafana SCOM dashboards can be reviewed without production access.
--
-- Tables/views created:
--   vManagedEntity, vManagedEntityType, vPerformanceRuleInstance,
--   vRelationship, Perf.vPerfHourly, State.vStateHourly, Alert.vAlert
-- =============================================================================

USE master;
GO

IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'OperationsManagerDW')
    CREATE DATABASE OperationsManagerDW;
GO

USE OperationsManagerDW;
GO

-- Create svc-omread login
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

-- Managed Entity Types
CREATE TABLE vManagedEntityType (
    ManagedEntityTypeRowId INT PRIMARY KEY IDENTITY(1,1),
    ManagedEntityTypeSystemName NVARCHAR(256)
);

INSERT INTO vManagedEntityType (ManagedEntityTypeSystemName) VALUES
('Microsoft.Windows.Computer'),
('Microsoft.Windows.Server.Computer'),
('System.Group'),
('Microsoft.SQLServer.DBEngine'),
('Microsoft.Windows.InternetInformationServices.ApplicationPool');

-- Managed Entities (servers and groups)
CREATE TABLE vManagedEntity (
    ManagedEntityRowId INT PRIMARY KEY IDENTITY(1,1),
    ManagedEntityTypeRowId INT,
    Path NVARCHAR(512),
    Name NVARCHAR(256),
    DisplayName NVARCHAR(256),
    FullName NVARCHAR(512)
);

-- Groups (sites)
INSERT INTO vManagedEntity (ManagedEntityTypeRowId, Path, Name, DisplayName, FullName) VALUES
(3, 'Steamboat Servers', 'Steamboat Servers', 'Steamboat Servers', 'Steamboat Servers'),
(3, 'Deer Valley Monitors', 'Deer Valley Monitors', 'Deer Valley Monitors', 'Deer Valley Monitors'),
(3, 'Solitude Servers', 'Solitude Servers', 'Solitude Servers', 'Solitude Servers'),
(3, 'Snowshoe Servers', 'Snowshoe Servers', 'Snowshoe Servers', 'Snowshoe Servers'),
(3, 'Stratton Servers', 'Stratton Servers', 'Stratton Servers', 'Stratton Servers'),
(3, 'Sugarbush Servers', 'Sugarbush Servers', 'Sugarbush Servers', 'Sugarbush Servers'),
(3, 'Tremblant Servers', 'Tremblant Servers', 'Tremblant Servers', 'Tremblant Servers'),
(3, 'CMH Servers', 'CMH Servers', 'CMH Servers', 'CMH Servers'),
(3, 'DEV Servers', 'DEV Servers', 'DEV Servers', 'DEV Servers'),
(3, 'UAT Servers', 'UAT Servers', 'UAT Servers', 'UAT Servers');

-- Servers (sample per site)
DECLARE @sites TABLE (site_name NVARCHAR(50), site_abbrev NVARCHAR(10));
INSERT INTO @sites VALUES
('Steamboat', 'SBT'), ('Deer Valley', 'DV'), ('Solitude', 'SOL'),
('Snowshoe', 'SNO'), ('Stratton', 'STR'), ('Sugarbush', 'SGB'),
('Tremblant', 'TMB'), ('CMH', 'CMH');

DECLARE @roles TABLE (role_name NVARCHAR(20), role_abbrev NVARCHAR(10));
INSERT INTO @roles VALUES
('DC', 'DC'), ('SQL', 'SQL'), ('IIS', 'IIS'),
('FS', 'FS'), ('APP', 'APP'), ('DHCP', 'DHCP');

DECLARE @site_name NVARCHAR(50), @site_abbrev NVARCHAR(10);
DECLARE @role_name NVARCHAR(20), @role_abbrev NVARCHAR(10);
DECLARE @server_num INT;

DECLARE site_cursor CURSOR FOR SELECT site_name, site_abbrev FROM @sites;
OPEN site_cursor;
FETCH NEXT FROM site_cursor INTO @site_name, @site_abbrev;

WHILE @@FETCH_STATUS = 0
BEGIN
    DECLARE role_cursor CURSOR FOR SELECT role_name, role_abbrev FROM @roles;
    OPEN role_cursor;
    FETCH NEXT FROM role_cursor INTO @role_name, @role_abbrev;
    SET @server_num = 1;

    WHILE @@FETCH_STATUS = 0
    BEGIN
        DECLARE @hostname NVARCHAR(256) = 'SRV-' + @role_abbrev + '-' + RIGHT('0' + CAST(@server_num AS VARCHAR), 2) + '.' + @site_abbrev + '.alterra.com';
        INSERT INTO vManagedEntity (ManagedEntityTypeRowId, Path, Name, DisplayName, FullName)
        VALUES (2, @hostname, @hostname, @hostname, @hostname);

        SET @server_num = @server_num + 1;
        FETCH NEXT FROM role_cursor INTO @role_name, @role_abbrev;
    END
    CLOSE role_cursor;
    DEALLOCATE role_cursor;

    FETCH NEXT FROM site_cursor INTO @site_name, @site_abbrev;
END
CLOSE site_cursor;
DEALLOCATE site_cursor;

-- Relationships (group membership)
CREATE TABLE vRelationship (
    RelationshipRowId INT PRIMARY KEY IDENTITY(1,1),
    SourceManagedEntityRowId INT,
    TargetManagedEntityRowId INT
);

-- Map servers to their site groups
INSERT INTO vRelationship (SourceManagedEntityRowId, TargetManagedEntityRowId)
SELECT g.ManagedEntityRowId, s.ManagedEntityRowId
FROM vManagedEntity s
CROSS JOIN vManagedEntity g
WHERE s.ManagedEntityTypeRowId = 2
AND g.ManagedEntityTypeRowId = 3
AND s.Path LIKE '%' +
    CASE g.DisplayName
        WHEN 'Steamboat Servers' THEN '.SBT.'
        WHEN 'Deer Valley Monitors' THEN '.DV.'
        WHEN 'Solitude Servers' THEN '.SOL.'
        WHEN 'Snowshoe Servers' THEN '.SNO.'
        WHEN 'Stratton Servers' THEN '.STR.'
        WHEN 'Sugarbush Servers' THEN '.SGB.'
        WHEN 'Tremblant Servers' THEN '.TMB.'
        WHEN 'CMH Servers' THEN '.CMH.'
    END + '%';

-- Performance Rule Instances (counter definitions)
CREATE TABLE vPerformanceRuleInstance (
    PerformanceRuleInstanceRowId INT PRIMARY KEY IDENTITY(1,1),
    ObjectName NVARCHAR(256),
    CounterName NVARCHAR(256),
    InstanceName NVARCHAR(256)
);

INSERT INTO vPerformanceRuleInstance (ObjectName, CounterName, InstanceName) VALUES
('Processor', '% Processor Time', '_Total'),
('Memory', 'Available MBytes', ''),
('Memory', '% Committed Bytes In Use', ''),
('LogicalDisk', '% Free Space', 'C:'),
('LogicalDisk', '% Free Space', 'D:'),
('LogicalDisk', '% Free Space', 'E:'),
('LogicalDisk', 'Avg. Disk sec/Read', 'C:'),
('LogicalDisk', 'Avg. Disk sec/Write', 'C:'),
('LogicalDisk', 'Avg. Disk sec/Read', 'D:'),
('LogicalDisk', 'Avg. Disk sec/Write', 'D:'),
('LogicalDisk', 'Disk Bytes/sec', 'C:'),
('LogicalDisk', 'Disk Bytes/sec', 'D:'),
('Network Interface', 'Bytes Total/sec', 'Ethernet0'),
('System', 'Processor Queue Length', ''),
('Paging File', '% Usage', '_Total');
GO

-- =============================================================================
-- Performance Data (Perf schema)
-- =============================================================================

CREATE SCHEMA Perf;
GO

CREATE TABLE Perf.vPerfHourly (
    DateTime DATETIME,
    ManagedEntityRowId INT,
    PerformanceRuleInstanceRowId INT,
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

-- Populate with 7 days of hourly data for all servers and counters
DECLARE @hour INT = 0;
WHILE @hour < 168  -- 7 days * 24 hours
BEGIN
    DECLARE @dt DATETIME = DATEADD(hour, -@hour, GETUTCDATE());

    INSERT INTO Perf.vPerfHourly (DateTime, ManagedEntityRowId, PerformanceRuleInstanceRowId, SampleCount, AverageValue, MinValue, MaxValue, StandardDeviation)
    SELECT
        @dt,
        me.ManagedEntityRowId,
        pri.PerformanceRuleInstanceRowId,
        12,  -- 12 samples per hour (5 min intervals)
        CASE pri.CounterName
            WHEN '% Processor Time' THEN 20.0 + (ABS(CHECKSUM(NEWID())) % 60)
            WHEN 'Available MBytes' THEN 2048.0 + (ABS(CHECKSUM(NEWID())) % 8192)
            WHEN '% Committed Bytes In Use' THEN 30.0 + (ABS(CHECKSUM(NEWID())) % 50)
            WHEN '% Free Space' THEN 15.0 + (ABS(CHECKSUM(NEWID())) % 70)
            WHEN 'Avg. Disk sec/Read' THEN 0.001 + (ABS(CHECKSUM(NEWID())) % 20) * 0.001
            WHEN 'Avg. Disk sec/Write' THEN 0.002 + (ABS(CHECKSUM(NEWID())) % 25) * 0.001
            WHEN 'Disk Bytes/sec' THEN 1000000.0 + (ABS(CHECKSUM(NEWID())) % 50000000)
            WHEN 'Bytes Total/sec' THEN 500000.0 + (ABS(CHECKSUM(NEWID())) % 20000000)
            WHEN 'Processor Queue Length' THEN (ABS(CHECKSUM(NEWID())) % 5)
            WHEN '% Usage' THEN 5.0 + (ABS(CHECKSUM(NEWID())) % 30)
            ELSE 0
        END,
        CASE pri.CounterName
            WHEN '% Processor Time' THEN 5.0 + (ABS(CHECKSUM(NEWID())) % 30)
            ELSE 0
        END,
        CASE pri.CounterName
            WHEN '% Processor Time' THEN 50.0 + (ABS(CHECKSUM(NEWID())) % 50)
            ELSE 0
        END,
        1.0
    FROM vManagedEntity me
    CROSS JOIN vPerformanceRuleInstance pri
    WHERE me.ManagedEntityTypeRowId = 2;  -- Only servers, not groups

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

-- Populate: most servers healthy, a few in warning
INSERT INTO State.vStateHourly (DateTime, ManagedEntityRowId, MonitorRowId, OldHealthState, NewHealthState, InMaintenanceMode)
SELECT
    DATEADD(hour, -ABS(CHECKSUM(NEWID())) % 24, GETUTCDATE()),
    me.ManagedEntityRowId,
    1,
    1,
    CASE WHEN ABS(CHECKSUM(NEWID())) % 20 = 0 THEN 2  -- 5% warning
         WHEN ABS(CHECKSUM(NEWID())) % 50 = 0 THEN 3  -- 2% critical
         ELSE 1 END,  -- healthy
    CASE WHEN ABS(CHECKSUM(NEWID())) % 30 = 0 THEN 1 ELSE 0 END  -- ~3% in maintenance
FROM vManagedEntity me
WHERE me.ManagedEntityTypeRowId = 2;
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
    Severity INT,  -- 0=Info, 1=Warning, 2=Critical
    Priority INT,
    ResolutionState INT,  -- 0=New, 255=Closed
    RaisedDateTime DATETIME,
    ResolvedDateTime DATETIME NULL,
    ManagedEntityRowId INT
);

-- Active alerts (not closed)
INSERT INTO Alert.vAlert (AlertName, AlertDescription, Severity, Priority, ResolutionState, RaisedDateTime, ManagedEntityRowId)
SELECT TOP 15
    CASE ABS(CHECKSUM(NEWID())) % 5
        WHEN 0 THEN 'Logical Disk Free Space is low'
        WHEN 1 THEN 'Windows Service Stopped'
        WHEN 2 THEN 'Processor Utilization exceeded threshold'
        WHEN 3 THEN 'Memory Pages/sec exceeded threshold'
        WHEN 4 THEN 'DNS Resolution Failure Rate High'
    END,
    'Threshold exceeded on ' + me.Path,
    CASE WHEN ABS(CHECKSUM(NEWID())) % 3 = 0 THEN 2 ELSE 1 END,  -- Mix of critical and warning
    1,
    0,  -- New (active)
    DATEADD(hour, -(ABS(CHECKSUM(NEWID())) % 72), GETUTCDATE()),
    me.ManagedEntityRowId
FROM vManagedEntity me
WHERE me.ManagedEntityTypeRowId = 2
ORDER BY NEWID();

-- Resolved alerts (last 7 days)
INSERT INTO Alert.vAlert (AlertName, AlertDescription, Severity, Priority, ResolutionState, RaisedDateTime, ResolvedDateTime, ManagedEntityRowId)
SELECT TOP 50
    CASE ABS(CHECKSUM(NEWID())) % 5
        WHEN 0 THEN 'Logical Disk Free Space is low'
        WHEN 1 THEN 'Windows Service Stopped'
        WHEN 2 THEN 'Processor Utilization exceeded threshold'
        WHEN 3 THEN 'Memory Pages/sec exceeded threshold'
        WHEN 4 THEN 'Health Service Heartbeat Failure'
    END,
    'Resolved alert on ' + me.Path,
    CASE WHEN ABS(CHECKSUM(NEWID())) % 4 = 0 THEN 2 ELSE 1 END,
    1,
    255,  -- Closed
    DATEADD(hour, -(ABS(CHECKSUM(NEWID())) % 168), GETUTCDATE()),
    DATEADD(minute, (ABS(CHECKSUM(NEWID())) % 240), DATEADD(hour, -(ABS(CHECKSUM(NEWID())) % 168), GETUTCDATE())),
    me.ManagedEntityRowId
FROM vManagedEntity me
WHERE me.ManagedEntityTypeRowId = 2
ORDER BY NEWID();
GO

PRINT 'SCOM DW Simulator seeded successfully';
GO
