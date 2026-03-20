# Cloud Infrastructure Monitoring

> **Status: Stub Only** -- These are placeholder configurations. No cloud resources are currently monitored. The stub configs document the integration approach for when cloud adoption begins. Disabled by default.

## Overview

The monitoring platform includes stub configurations for extending monitoring to cloud infrastructure (AWS and Azure). These configs are disabled by default and activated when cloud resources are deployed.

## Supported Providers

### AWS CloudWatch

Alloy's `prometheus.exporter.cloudwatch` component can scrape CloudWatch metrics and convert them to Prometheus format.

**Stub config**: `configs/alloy/cloud/aws_cloudwatch.alloy.example`

**Supported services**:
- EC2 instances (CPU, network, disk, status checks)
- RDS databases (connections, IOPS, replication lag)
- ELB/ALB load balancers (request count, latency, 5xx errors)
- S3 buckets (request count, data transfer)
- Lambda functions (invocations, duration, errors)

**Prerequisites**:
- IAM role with `cloudwatch:GetMetricData` and `cloudwatch:ListMetrics` permissions
- AWS credentials available to Alloy (instance profile, env vars, or credential file)
- Network access from Alloy to AWS CloudWatch API endpoints

### Azure Monitor

Alloy's `prometheus.exporter.azure` component scrapes Azure Monitor metrics.

**Stub config**: `configs/alloy/cloud/azure_monitor.alloy.example`

**Supported services**:
- Azure VMs (CPU, memory, disk, network)
- Azure SQL Database (DTU, connections, deadlocks)
- Azure App Service (requests, response time, errors)
- Azure Kubernetes Service (node/pod metrics)
- Azure Storage (transactions, latency, capacity)

**Prerequisites**:
- Azure service principal with `Monitoring Reader` role
- Tenant ID, client ID, and client secret
- Network access from Alloy to Azure Monitor API endpoints

## Activation Workflow

1. Copy the `.example` file to remove the `.example` extension
2. Configure credentials via environment variables
3. Uncomment the desired service sections
4. Add the config to Alloy's config directory
5. Restart Alloy

## Helm Values

Cloud monitoring can be enabled in the Helm chart values:

```yaml
cloud:
  aws:
    enabled: false
    # region: us-east-1
    # roleArn: arn:aws:iam::123456789:role/monitoring
  azure:
    enabled: false
    # tenantId: ""
    # clientId: ""
    # subscriptionId: ""
```

## Configuration Files

| File | Purpose |
|------|---------|
| `configs/alloy/cloud/aws_cloudwatch.alloy.example` | AWS CloudWatch stub config |
| `configs/alloy/cloud/azure_monitor.alloy.example` | Azure Monitor stub config |
