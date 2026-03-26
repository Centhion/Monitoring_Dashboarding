# SquaredUp Dashboard Reference

Screenshots captured 2026-03-25 from production SquaredUp instance (vm-den-scom1).
Used as reference for Grafana SCOM dashboard design -- not a copy target.

## Navigation Structure

- **Overview**: Active Alerts, Groups, Servers, Alert History
- **Resorts**: Per-site views (Deer Valley, Steamboat, Solitude, etc.)
- **Teams**: Per-role views (Active Directory, Exchange, SQL Server, Network, etc.)
- **IKON**: Business-unit specific (IKON Servers, Infrastructure, SQL, Disk Performance)
- **Citrix**: Denver Citrix, Steamboat Citrix
- **Inntopia, Network**: Additional business-unit views

## Key Observations

- Ops navigates by **resort first** (where), then role (what)
- **Health state** (healthy/warning/critical donuts) is the entry point, not performance charts
- **Alerts are front and center** on every view
- Per-resort view shows: health donut, alerts marquee, full server table with IP and CPU sparklines
- SQL cluster views show AG node tiles with memory/CPU bars and service monitor rollups
- Alert History shows daily average, top alerted objects, most common alerts by management pack

## Connection Details (from Connections page)

- Management Server: localhost (SquaredUp runs on vm-den-scom1)
- Data Warehouse: Data Source=vm-den-sql11;Initial Catalog=OperationsManagerDW;Integrated Security=True
- Auth: Windows Integrated Security (machine/service account on domain-joined host)

## Active Providers

- generic (API), DigiCert (API), Pingdom (API), Mammoth Palo Alto (API), Data Warehouse (SCOM DW)

## Screenshot Index

- IMG_1761: Active Alerts (full view)
- IMG_1762: Active Alerts (scrolled)
- IMG_1763: Resorts dropdown (site list)
- IMG_1764: Teams dropdown (role list)
- IMG_1765: IKON dropdown (business unit)
- IMG_1766: Citrix dropdown
- IMG_1767: Groups overview (health donuts + group grid)
- IMG_1768: Servers overview (Windows/Linux health donuts + critical grids)
- IMG_1769: Alert History (daily average, timeline, top objects, common alerts)
- IMG_1770: Deer Valley Servers (per-site: health donut, server table with sparklines)
- IMG_1771: DV SQL Nodes (cluster tiles, memory/CPU bars, service monitors)
- IMG_1772: Connections page (SCOM DW connection string)
- IMG_1773: Integrations page (active providers)
