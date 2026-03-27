-- =============================================================================
-- SCOM Data Warehouse Discovery Queries
-- =============================================================================
-- Run these against your production SCOM DW (OperationsManagerDW)
-- to discover entity types, counter names, groups, and management packs.
--
-- Results are used to validate/adjust Grafana dashboard queries before deployment.
-- Requires: db_datareader role on OperationsManagerDW
-- =============================================================================

USE OperationsManagerDW;
GO

-- =============================================================================
-- 1. Entity Types
-- What kinds of objects does SCOM monitor? Need the exact SystemName for
-- Computer entities (used in WHERE clauses throughout all dashboards).
-- Expected: Microsoft.Windows.Server.Computer or Microsoft.Windows.Computer
-- =============================================================================
SELECT
    met.ManagedEntityTypeSystemName,
    COUNT(*) AS entity_count
FROM vManagedEntity me
INNER JOIN vManagedEntityType met
    ON me.ManagedEntityTypeRowId = met.ManagedEntityTypeRowId
GROUP BY met.ManagedEntityTypeSystemName
ORDER BY entity_count DESC;
GO

-- =============================================================================
-- 2. Performance Counters (last 24 hours)
-- What ObjectName/CounterName pairs exist? These must match the dashboard
-- SQL queries exactly. Grouped by object to show which Management Packs
-- are collecting data.
--
-- Key counters we need:
--   Windows OS:     Processor / % Processor Time
--                   Memory / % Committed Bytes In Use, Available MBytes
--                   LogicalDisk / % Free Space, Avg. Disk sec/Read, sec/Write
--   SQL Server MP:  SQLServer:Buffer Manager / Buffer cache hit ratio
--                   SQLServer:SQL Statistics / Batch Requests/sec
--   IIS MP:         Web Service / Current Connections, Total Method Requests/sec
--   AD MP:          NTDS / LDAP Searches/sec, Kerberos Authentications
--   DNS:            DNS / Total Query Received/sec
-- =============================================================================
SELECT
    pri.ObjectName,
    pri.CounterName,
    COUNT(DISTINCT ph.ManagedEntityRowId) AS server_count,
    COUNT(*) AS sample_count_24h
FROM Perf.vPerfHourly ph
INNER JOIN vPerformanceRuleInstance pri
    ON ph.PerformanceRuleInstanceRowId = pri.PerformanceRuleInstanceRowId
WHERE ph.DateTime >= DATEADD(day, -1, GETUTCDATE())
GROUP BY pri.ObjectName, pri.CounterName
ORDER BY pri.ObjectName, pri.CounterName;
GO

-- =============================================================================
-- 3. SCOM Groups
-- What groups exist? These are used for site-level filtering in dashboards.
-- The site_group variable queries System.Group entities.
-- Need: group display names, member counts, naming pattern.
-- =============================================================================
SELECT
    me.DisplayName,
    me.Path,
    (SELECT COUNT(*)
     FROM vRelationship r
     WHERE r.SourceManagedEntityRowId = me.ManagedEntityRowId) AS member_count
FROM vManagedEntity me
INNER JOIN vManagedEntityType met
    ON me.ManagedEntityTypeRowId = met.ManagedEntityTypeRowId
WHERE met.ManagedEntityTypeSystemName = 'System.Group'
ORDER BY me.DisplayName;
GO

-- =============================================================================
-- 4. Server Hostname Patterns (sample)
-- What naming convention do servers follow? Needed to validate server
-- variable filter queries (e.g., WHERE Path LIKE 'SRV-SQL%').
-- =============================================================================
SELECT TOP 100
    me.Path,
    me.DisplayName
FROM vManagedEntity me
INNER JOIN vManagedEntityType met
    ON me.ManagedEntityTypeRowId = met.ManagedEntityTypeRowId
WHERE met.ManagedEntityTypeSystemName LIKE '%Computer%'
ORDER BY me.Path;
GO

-- =============================================================================
-- 5. Role-Specific Counter Names
-- Confirms which Management Packs are installed and collecting data.
-- If any of these return zero rows, that MP may not be installed or
-- the counter names differ from our dashboard queries.
-- =============================================================================

-- SQL Server Management Pack counters
SELECT DISTINCT pri.ObjectName, pri.CounterName
FROM vPerformanceRuleInstance pri
WHERE pri.ObjectName LIKE 'SQL%'
ORDER BY pri.ObjectName, pri.CounterName;
GO

-- IIS Management Pack counters
SELECT DISTINCT pri.ObjectName, pri.CounterName
FROM vPerformanceRuleInstance pri
WHERE pri.ObjectName IN ('Web Service', 'ASP.NET', 'ASP.NET Applications')
ORDER BY pri.ObjectName, pri.CounterName;
GO

-- Active Directory Management Pack counters
SELECT DISTINCT pri.ObjectName, pri.CounterName
FROM vPerformanceRuleInstance pri
WHERE pri.ObjectName IN ('NTDS', 'DNS')
ORDER BY pri.ObjectName, pri.CounterName;
GO

-- =============================================================================
-- 6. State Data Check
-- Verify health state monitoring is active and how many entities have state.
-- =============================================================================
SELECT
    COUNT(*) AS total_state_rows,
    COUNT(DISTINCT ManagedEntityRowId) AS entities_with_state,
    MIN(DateTime) AS earliest,
    MAX(DateTime) AS latest
FROM State.vStateHourly;
GO

-- =============================================================================
-- 7. Alert Volume
-- How many active alerts exist? Helps set expectations for dashboard.
-- =============================================================================
SELECT
    CASE a.Severity WHEN 0 THEN 'Info' WHEN 1 THEN 'Warning' WHEN 2 THEN 'Critical' END AS Severity,
    CASE WHEN a.ResolutionState = 255 THEN 'Closed' ELSE 'Active' END AS Status,
    COUNT(*) AS alert_count
FROM Alert.vAlert a
GROUP BY a.Severity, CASE WHEN a.ResolutionState = 255 THEN 'Closed' ELSE 'Active' END
ORDER BY a.Severity DESC, Status;
GO
