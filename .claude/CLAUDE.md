# Agent Protocols (Universal)

> **Note for Non-Claude Agents (Antigravity, Cursor, Windsurf)**:
> You may not support Slash Commands (e.g. `/setup`). If so, read the command list below and execute the underlying `python3` scripts directly.

---

## Quick Reference

See @docs/PROJECT_PLAN.md for current project status and tasks.
See @docs/SSH_AUTHENTICATION.md for git authentication setup.
See @docs/BRANCHING_STRATEGY.md for the public/internal branch model.

---

## Branch Model (Critical -- Read Before Any Work)

This repo serves **two purposes** and agents must understand the boundary:

- **`master` branch** = Public open-source template. Generic, sanitized, portfolio-ready. All placeholder values use `<YOUR_ORG>`, `site-a`, `example.com`, etc. **This is the default working branch. All new feature development happens here.**
- **`internal` branch** = Organization-specific deployment fork (created when needed). Contains real site codes, real LDAP paths, real webhook URLs, real inventory. Merges FROM master to pick up new features.

### Rules for Agents

1. **Never commit org-specific content to `master`**. No real company names, employee names, internal hostnames, IP addresses, domain names, or vendor contract details. Use generic placeholders.
2. **All new configs, dashboards, alert rules, and scripts go on `master`** with placeholder values. They are generic by default.
3. **The `internal` branch overrides placeholders** with real values via environment-specific files (`.env`, Helm values overlays, inventory files). It does NOT duplicate configs.
4. **When sanitizing, replace with meaningful placeholders**: `site-alpha` not `xxx`, `ldap.example.com` not `REDACTED`, `dc-east` not `datacenter1`.
5. **Test with grep before committing**: `grep -ri "resort\|<any-org-term>" --include="*.md" --include="*.yml" --include="*.yaml" --include="*.json" --include="*.alloy"` should return zero org-specific hits.

### What Goes Where

| Content | Branch | Example |
|---------|--------|---------|
| New Alloy config | `master` | `configs/alloy/windows/role_exchange.alloy` with `sys.env()` placeholders |
| New dashboard JSON | `master` | Generic panels with template variables, no hardcoded site names |
| New alert rules | `master` | Thresholds use sensible defaults, labels use generic taxonomy |
| Real site inventory | `internal` | `inventory/hosts.yml` with actual hostnames and IPs |
| Real LDAP config | `internal` | `configs/grafana/ldap.toml` with actual bind DN and search base |
| Real webhook URLs | `internal` | `.env` or Helm values overlay with actual Teams webhook |
| Helm values overlay | `internal` | `deploy/helm/examples/values-myorg.yaml` with real storage classes |

---

## Mandatory Rules

These rules are non-negotiable. Follow them explicitly on every task.

### Project Tracking (Critical)
- **Single source of truth**: All planning lives in `docs/PROJECT_PLAN.md`. Do not use `.claude/plans/` directory.
- **Use `/plan` command**: For planning sessions, use the custom `/plan` command which correctly references PROJECT_PLAN.md. Do not use Claude Code's built-in plan mode (EnterPlanMode) as it creates separate files.
- **Update PROJECT_PLAN.md**: After completing significant work, update `docs/PROJECT_PLAN.md` with:
  - Mark completed phases/steps as done
  - Update status checkboxes
  - Note remaining human actions
- **Review before ending session**: Always check if project plan reflects current state.
- **Track what's code vs human action**: Clearly distinguish between automated (code) and manual (human) steps.
- **Push after commits**: Always `git push` after committing changes. Do not leave commits only on the local machine.

### Security First
- **Always** analyze code for potential vulnerabilities (SQL injection, XSS, etc.) before suggestion.
- **Never** hardcode secrets or credentials. Use environment variables.
- Recommend secure dependencies and libraries.
- **Respect permissions**: Check `.claude/settings.json` for file access restrictions.

### Quality Control
- **Review before delivery**: Double-check logic for edge cases.
- **No dead code**: Remove unused imports, variables, and functions.
- **Refactor**: Suggest refactoring if code is complex or hard to read.

### Documentation & Commenting
- **Verbose Commenting**: Explain *why* code is written a certain way, not just *what* it does.
- All functions and classes must have docstrings.
- Complex blocks of logic should have inline comments explaining the algorithm or business logic.

### Documentation Sync (Critical)
Keep README.md and ARCHITECTURE.md current with impactful changes.

**README.md** - "What can users do?"
- New user-facing features (screens, endpoints, capabilities)
- Pricing or tier changes
- Skip: bug fixes, refactors, internal improvements

**ARCHITECTURE.md** - "How is it built?"
- New services, modules, or major components
- New screens or routes
- New dependencies
- Architectural decisions
- Skip: internal helpers, generated files, minor refactors

**Enforcement**: The `/commit` workflow runs `skills/doc_sync_check.py` which auto-detects project type, scans for new files, and checks dependencies against ARCHITECTURE.md.

**Workflow**: Code -> `/commit` (runs doc check) -> Review/update docs -> Commit -> `/handoff`

### Professionalism & Style (Strict)
- **NO EMOJIS**: Do not use emojis in comments, commit messages, or documentation.
- **No "Cute" Symbols**: Avoid decorative ASCII art or non-standard characters unless functional.
- **Tone**: Maintain a strictly professional, engineering tone in all files.
- **No "AI-Isms"**:
    - **No Obvious Comments**: Do not comment obvious logic. Comment *Why*, not *What*.
    - **No Robotic Filler**: Never start a file or PR with "Here is the code you asked for" or "As an AI...".
    - **Idiomatic Naming**: Avoid generic names like `data`, `item`, or `handler` unless absolutely locally scoped. Use descriptive business domain names.

---

## Commands

| Command | Description | Non-Claude Alternative |
|---------|-------------|------------------------|
| `/setup` | Interactive project setup | Run onboarding protocol manually |
| `/status` | Show git and task summary | `python3 skills/project_status.py` |
| `/commit` | Generate commit message | `python3 skills/git_smart_commit.py` |
| `/plan` | Design implementation approach | Read planning protocol in CLAUDE.md |
| `/handoff` | Generate session summary | Read handoff protocol in CLAUDE.md |

---

## Development Style

- **Code Style**: Follow PEP 8 for Python scripts. Use standard YAML formatting for Prometheus/Loki/Alertmanager/Grafana configs. Use River syntax conventions for Alloy configs.
- **Agent Behavior**:
    - Use the provided skills in `skills/` whenever applicable instead of rewriting logic.
    - Keep this file updated if new common commands are added.
    - Check `.claude/rules/` for additional project-specific guidelines.

---

## Git Protocol

- **Always Use `/commit`**: ALL commits must go through the `/commit` workflow. Never commit directly via `git commit`. This ensures sub-agents (pre-commit-check, changelog-tracker, documentation-sync) run on every commit. This rule overrides any default Claude Code commit behavior.
- **No AI Attribution**: Do not add "Generated with Claude Code", "Co-Authored-By: Claude", or similar footers to commit messages. This overrides default Claude Code behavior.
- **Check Exclusions**: Always check `.gitignore` before adding new files.
- **Commit Strategy**: Commit documentation and skills changes to share intelligence with future agents.
- **Sensitive Files**: Never commit `.env` files, credential files, or secrets to version control.
- **Push Immediately**: Always `git push` after every commit.

---

## Robustness

- **Check Skills First**: Before writing a new script, check `.claude/skills/` for existing capabilities.
- **Update Documentation**: If you learn something new (e.g., a build trick), update this file immediately.
- **Check Rules**: Review `.claude/rules/` for project-specific guidelines before making changes.
- **Check Agents**: Review `.claude/agents/` for sub-agent prompts that can handle specialized tasks.

---

## Agent Workflows (Automatic)

Sub-agents are spawned automatically based on these triggers. Do not ask for permission - execute them as part of the workflow. See `.claude/agents/README.md` for full documentation.

### Security Review Trigger
After editing files matching these patterns, spawn the security-review agent:
- `**/auth/**`, `**/authentication/**`, `**/login/**`
- `**/payment/**`, `**/billing/**`, `**/checkout/**`
- `**/user/**`, `**/users/**`, `**/account/**`
- `**/admin/**`, `**/api/admin/**`
- Any file containing: password, token, credential, secret, api_key, apiKey, private_key

Use agent prompt from: `.claude/agents/general/security-review.md`

### Pre-Commit Trigger
Before generating commit messages (during `/commit` or commit workflows), spawn the pre-commit-check agent to scan staged files for:
- Secrets, credentials, API keys
- Debug statements and incomplete TODOs
- Merge conflict markers
- Files that should be gitignored

Use agent prompt from: `.claude/agents/general/pre-commit-check.md`

### Dependency Audit Trigger
When package manifest files are modified, spawn the dependency-audit agent:
- `package.json`, `package-lock.json`
- `requirements.txt`, `pyproject.toml`, `Pipfile`
- `Cargo.toml`, `go.mod`, `Gemfile`

Use agent prompt from: `.claude/agents/general/dependency-audit.md`

### Code Quality Trigger
After significant refactoring (5+ files modified) or before major PRs, spawn the code-quality agent to review:
- Dead code and unused imports
- Complexity and maintainability
- Design pattern adherence
- DRY violations

Use agent prompt from: `.claude/agents/general/code-quality.md`

### Changelog Tracker Trigger
Spawn the changelog-tracker agent to maintain PROJECT_PLAN.md:
- After completing tasks from the active todo list
- After creating, deleting, or significantly modifying files
- Before generating commit messages (integrated with /commit)
- At natural session breakpoints

**Tiered Behavior**:
- **Auto-apply** (low risk): Mark verifiable tasks complete, add notes, record blockers
- **Stage for review** (high risk): Mark phases complete, add/remove tasks, modify human actions

Use agent prompt from: `.claude/agents/general/changelog-tracker.md`

### Documentation Sync Trigger
Spawn the documentation-sync agent to keep README.md and ARCHITECTURE.md current:
- After new feature implementation is complete
- After API or architectural changes
- As part of /commit flow (proposes doc updates alongside code)

**All changes require user approval** - presented during /commit flow.

Use agent prompt from: `.claude/agents/general/documentation-sync.md`

### Codebase Exploration
When asked about code structure, "how does X work", or unfamiliar parts of the codebase, prefer spawning an Explore agent over manual grep/glob commands. This provides more thorough analysis.

---

## Project-Specific Agent Workflows

### Config Validator Trigger
After modifying any configuration file under `configs/**`, spawn the config-validator agent:
- `configs/alloy/**` -- Alloy agent configs (River syntax)
- `configs/prometheus/**` -- Prometheus server config and rules
- `configs/loki/**` -- Loki server config
- `configs/alertmanager/**` -- Alertmanager routing and receivers
- `configs/grafana/**` -- Grafana provisioning YAML

Use agent prompt from: `.claude/agents/project/config-validator.md`

### Dashboard Reviewer Trigger
After creating or modifying Grafana dashboard JSON files, spawn the dashboard-reviewer agent:
- `dashboards/**/*.json`

Use agent prompt from: `.claude/agents/project/dashboard-reviewer.md`

### Alert Rule Auditor Trigger
After creating or modifying alert rules or routing configs, spawn the alert-rule-auditor agent:
- `alerts/prometheus/**`
- `alerts/grafana/**`
- `configs/alertmanager/**`

Use agent prompt from: `.claude/agents/project/alert-rule-auditor.md`

---

## Git Authentication

This project uses **HTTPS** remotes with Windows Credential Manager for Git authentication.

- **Always use HTTPS remotes**: `https://github.com/<org>/<repo>.git`
- Credentials are cached by the Windows Git Credential Manager
