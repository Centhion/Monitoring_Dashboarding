# SCOM Data Warehouse Schema Reference

Discovered from production OperationsManagerDW (2026-03-26/27).
Used for building Grafana SCOM dashboard queries.

## Tables Used in Dashboards

### Performance Data
| View | Granularity | Retention | Rows (production) |
|------|-------------|-----------|-------------------|
| Perf.vPerfRaw | ~5 minutes | ~13 days | 51,714,835 |
| Perf.vPerfHourly | 1 hour | ~400 days | -- |
| Perf.vPerfDaily | 1 day | ~400 days | -- |

Columns: DateTime, PerformanceRuleInstanceRowId, ManagedEntityRowId, SampleCount, AverageValue, MinValue, MaxValue, StandardDeviation

### Counter Lookup (two-table JOIN)
- vPerformanceRuleInstance: PerformanceRuleInstanceRowId, RuleRowId, InstanceName, LastReceivedDateTime
- vPerformanceRule: RuleRowId, ObjectName, CounterName, MultiInstanceId, LastReceivedDateTime

### State Data
| View | Granularity |
|------|-------------|
| State.vStateRaw | Per state change |
| State.vStateHourly | Hourly snapshot |
| State.vStateDaily | Daily snapshot |

Columns: DateTime, ManagedEntityRowId, MonitorRowId, OldHealthState, NewHealthState, InMaintenanceMode

### Alert Data
- Alert.vAlert: AlertGuid, AlertName, AlertDescription, Severity, Priority, ResolutionState, RaisedDateTime, ResolvedDateTime, ManagedEntityRowId
- Alert.vAlertDetail: (many nullable fields, date/time metadata)
- Alert.vAlertParameter: (alert context parameters)
- Alert.vAlertResolutionState: AlertGuid, ResolutionState, TimeInStateSeconds, TimeFromRaisedSeconds, StateSetDateTime, StateSetByUserId, DWCreatedDateTime

### Event Data
- Event.vEvent: EventOriginId, DateTime, EventPublisherRowId, EventChannelRowId, EventCategoryRowId, EventLevelId, LoggingComputerRowId, EventNumber, EventDisplayNumber, UserNameRowId, RawDescription, EventDataHash
- Event.vEventDetail: (extended event data)
- Event.vEventParameter: (event parameters)
- Event.vEventRule: (which SCOM rule collected the event)

### Event Lookup Tables
- dbo.vEventPublisher: publisher name lookup
- dbo.vEventChannel: channel name lookup (Application, System, Security, etc.)
- dbo.vEventLevel: level name lookup (Error, Warning, Information, etc.)
- dbo.vEventLoggingComputer: computer name lookup
- dbo.vEventCategory: category lookup
- dbo.vEventUserName: user name lookup

### Entity Data
- vManagedEntity: ManagedEntityRowId, ManagedEntityTypeRowId, Path, Name, DisplayName, FullName
- vManagedEntityType: ManagedEntityTypeRowId, ManagedEntityTypeSystemName
- vManagedEntityMonitor: ManagedEntityMonitorRowId, ManagedEntityRowId, MonitorRowId, DWCreatedDateTime
- vManagedEntityProperty: ManagedEntityPropertyRowId, ManagedEntityRowId, PropertyXml, DeltaXml, FromDateTime, ToDateTime
- vRelationship: RelationshipRowId, SourceManagedEntityRowId, TargetManagedEntityRowId

### Monitor Lookup
- dbo.vMonitor: monitor definitions (name, type, configuration)

### Maintenance Mode
- dbo.vMaintenanceMode: MaintenanceModeRowId, ManagedEntityRowId, StartDateTime, EndDateTime, PlannedMaintenanceInd, DWLastModifiedDateTime
- dbo.vMaintenanceModeHistory: MaintenanceModeHistoryRowId, MaintenanceModeRowId, ScheduledEndDateTime, PlannedMaintenanceInd, ReasonCode, Comment, UserId

### Health State
- dbo.vHealthState: current health state per entity
- dbo.vHealthServiceOutage: SCOM agent outage history

### Entity Type: Microsoft.Windows.Computer (ManagedEntityTypeRowId = 1)
### Hostname Pattern: VM-<SITE>-<ROLE><NUM>
