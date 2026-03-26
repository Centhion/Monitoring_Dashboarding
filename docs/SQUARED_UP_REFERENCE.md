# SquaredUp Dashboard Reference

Screenshots captured from production SquaredUp instance.
Used as reference for Grafana SCOM dashboard design -- not a copy target.

## Navigation Structure

- **Overview**: Active Alerts, Groups, Servers, Alert History
- **Sites**: Per-site views (one tab per datacenter/location)
- **Teams**: Per-role views (Active Directory, Exchange, SQL Server, Network, etc.)
- **Business Units**: Business-unit specific views (servers, infrastructure, SQL, disk performance)
- **Application-specific**: Citrix, line-of-business application views

## Key Observations

- Ops navigates by **resort first** (where), then role (what)
- **Health state** (healthy/warning/critical donuts) is the entry point, not performance charts
- **Alerts are front and center** on every view
- Per-resort view shows: health donut, alerts marquee, full server table with IP and CPU sparklines
- SQL cluster views show AG node tiles with memory/CPU bars and service monitor rollups
- Alert History shows daily average, top alerted objects, most common alerts by management pack

## Connection Details (from Connections page)

- Management Server: localhost (SquaredUp runs on the SCOM management server)
- Data Warehouse: SQL Server connection with Integrated Security
- Auth: Windows Integrated Security (machine/service account on domain-joined host)

## Active Providers

- generic (API), certificate management (API), synthetic monitoring (API), firewall (API), Data Warehouse (SCOM DW)

## Screenshot Index

- Active Alerts (full view, scrolled)
- Site dropdown (site list)
- Teams dropdown (role list)
- Business unit dropdown
- Application-specific dropdown
- Groups overview (health donuts + group grid)
- Servers overview (Windows/Linux health donuts + critical grids)
- Alert History (daily average, timeline, top objects, common alerts)
- Per-site server view (health donut, server table with sparklines)
- SQL cluster nodes (cluster tiles, memory/CPU bars, service monitors)
- Connections page (SCOM DW connection string)
- Integrations page (active providers)
