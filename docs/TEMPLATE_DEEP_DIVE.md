# Golden Template: Deep Dive and Philosophy

> "AI Agents need structure, not just prompts."

This document explains the **Why** and **How** behind the architecture of this template. It is intended for developers who want to understand, extend, or fork this system.

---

## 1. The Core Philosophy

Most AI coding fails because the AI lacks:

1. **Context**: "What are we building?"
2. **Memory**: "What did we do yesterday?"
3. **Tools**: "How do I verify my work?"

This template solves these problems by treating the **Filesystem as the Agent's Brain**. Configuration is not ephemeral; it is grounded in persistent files that follow Anthropic's recommended hierarchy.

---

## 2. Anatomy of the Template

### The Brain: `.claude/`

The `.claude/` directory is the agent's "Operating System":

| Component | Purpose |
|-----------|---------|
| `CLAUDE.md` | Main instructions, rules, and protocols |
| `settings.json` | Permissions, hooks, and security settings |
| `rules/*.md` | Modular guidelines (security, style, testing) |
| `commands/*.md` | Slash command definitions |

**Why `.claude/` instead of root-level `CLAUDE.md`?**
- Follows Anthropic's official configuration hierarchy
- Cleaner separation of agent config from project files
- Enables modular rules with path-specific scoping

### The Hands: `skills/`

Agents differ from chatbots because they can *do* things.

| Skill | Purpose |
|-------|---------|
| `project_status.py` | Situational awareness - reads Git status and task list |
| `git_smart_commit.py` | Version control - generates conventional commit messages |

Skills are **universal Python scripts** that work across all agent types (Claude Code, Antigravity, Cursor, Windsurf).

### The Memory: `docs/`

| File | Purpose |
|------|---------|
| `PROJECT_PLAN.md` | Task tracking, phase status, human actions required |
| `DECISIONS.md` | Architectural decision log with rationale |

The agent updates these files after completing significant work, ensuring continuity across sessions.

### The Connections: `.mcp.json` (Optional)

MCP (Model Context Protocol) enables agents to connect to external tools:

- Databases (Postgres, MySQL)
- APIs (GitHub, Linear, Stripe)
- Development tools (linters, test runners)

The `.mcp.json` file at project root configures these connections with environment variable expansion for security. This file is configured during `/setup` if you indicate you need external tool integration.

---

## 3. Configuration Hierarchy

Claude Code loads configuration in this order (highest precedence first):

```
1. Enterprise policy (system-level, IT-managed)
2. Command-line arguments (session overrides)
3. .claude/settings.local.json (personal, gitignored)
4. .claude/settings.json (team, committed)
5. .claude/CLAUDE.md (team, committed)
6. .claude/rules/*.md (team, committed)
7. CLAUDE.local.md (personal, gitignored)
```

This hierarchy allows:
- Teams to share consistent configuration
- Individuals to override for personal preferences
- Enterprises to enforce security policies

---

## 4. Extending the Template

### Adding a New Skill

1. Write a standalone Python script in `skills/`:
   ```python
   # skills/deploy.py
   def main():
       # Implementation
       pass

   if __name__ == "__main__":
       main()
   ```

2. Test manually: `python3 skills/deploy.py`

3. Register in `.claude/CLAUDE.md` under Commands, or create a slash command:
   ```markdown
   <!-- .claude/commands/deploy.md -->
   Run the deployment script: python3 skills/deploy.py
   ```

### Adding a New Rule

1. Create a markdown file in `.claude/rules/`:
   ```markdown
   <!-- .claude/rules/security.md -->
   # Security Rules

   - Never log sensitive data
   - Validate all user input
   - Use parameterized queries
   ```

2. Optionally scope to specific paths with YAML frontmatter:
   ```markdown
   ---
   paths: src/api/**/*.ts
   ---

   # API Security Rules
   ...
   ```

### Adding a Permission

Edit `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": ["Bash(npm run test)"],
    "deny": ["Read(./.env)"]
  }
}
```

---

## 5. Universal Compatibility

While designed for Claude Code, this template works across agents:

| Feature | Claude Code | Antigravity/Cursor/Windsurf |
|---------|-------------|----------------------------|
| Slash Commands | Native support | Run scripts directly |
| Settings | `.claude/settings.json` | Read `.claude/CLAUDE.md` |
| Skills | Works | Works |
| Rules | Auto-loaded | Read manually |

For non-Claude agents, the Python scripts in `skills/` provide equivalent functionality.

---

## 6. Security Considerations

### Files Protected by Default

The template configures `.claude/settings.json` to deny access to:
- `.env` and `.env.*` files
- `secrets/` directory
- Files containing "secret" or "credential" in name
- Ansible vault files (`vault.yml`)

### Personal Overrides (Gitignored)

| File | Purpose |
|------|---------|
| `CLAUDE.local.md` | Personal notes, not shared |
| `.claude/settings.local.json` | Personal permission overrides |

These files are automatically excluded from version control.

---

*Keep this document in your repository to onboard future team members to the "Agentic Way of Working".*
