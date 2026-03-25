# Adding a New Site/Datacenter

How to add a new site to the monitoring platform so it appears in the NOC dashboard, receives site-specific alert routing, and has its own email distribution list.

**Time required**: 10-15 minutes (config generation), plus server deployment time.

---

## Before You Start

You need:
- The new site's **code** (short identifier, e.g., `par` for Paris, `nyc` for New York)
- The new site's **display name** (e.g., "Paris Datacenter")
- The site team's **email distribution list** (e.g., `par-ops@example.com`)
- The **Teams webhook URL** for alert notifications (can use the shared channel)

---

## Step 1: Run the Configuration Generator

The `deploy_configure.py` script generates all necessary config files for a new site.

From the repository root:

```bash
python3 scripts/deploy_configure.py
```

The script runs interactively. When prompted, add the new site to the site list. It will generate updated versions of:
- `configs/alertmanager/alertmanager.yml` -- new receivers and routes for the site
- `configs/grafana/notifiers/notifiers.yml` -- new contact points for the site
- `inventory/sites.yml` -- site metadata

If you already have a `deploy/site_config.yml`, edit it to add the new site entry, then re-run in non-interactive mode:

```bash
python3 scripts/deploy_configure.py --config deploy/site_config.yml
```

---

## Step 2: Restart the Stack

Apply the updated configurations:

```bash
python3 scripts/stack_manage.py --stop
python3 scripts/stack_manage.py
```

Or if the stack is running on a remote Docker host, restart the Alertmanager and Grafana containers:

```bash
docker compose restart alertmanager grafana
```

---

## Step 3: Verify the Site Appears

1. Open Grafana and navigate to **Enterprise > Enterprise NOC**
2. The new site should appear in the NOC grid (it will show "No Data" until servers are deployed)
3. Open **Infrastructure > Site Overview** and select the new site from the **datacenter** dropdown
4. Verify that **Alerting > Notification Policies** shows the new site's routing rules

---

## Step 4: Deploy Agents to Servers at the New Site

Follow the "Adding a New Server to Monitoring" guide for each server at the new site. Set `ALLOY_DATACENTER` to the new site code on every server.

As servers report in, the NOC dashboard will populate automatically.

---

## Step 5: Commit the Configuration

After verifying the new site works:

```bash
git add configs/alertmanager/alertmanager.yml configs/grafana/notifiers/notifiers.yml inventory/sites.yml
git commit -m "feat: add site <code> to monitoring"
git push
```

This ensures the configuration is version-controlled and can be regenerated if needed.
