---
name: skill-hot-loading
date: 2026-05-11
version: 1.0.0
scope:
  files:
    read:
      - "agents/**/*.py"
      - "dashboard/**/*.py"
      - "config/*.yaml"
      - "docs/**/*.md"
    write:
      - "agents/dispatcher/skills/*.md"
      - "agents/dispatcher/skills/loader.py"
      - "agents/dispatcher/nodes.py"
      - "config/permission_policies.yaml"
    create:
      - "agents/dispatcher/skills/*.md"
  commands:
    allowed:
      - "python"
      - "pytest"
      - "git status"
      - "git diff"
      - "git log"
    blocked:
      - "git push --force"
      - "rm -rf /*"
      - "npm install"
      - "pip install"
constraints:
  - "Skills must be defined as markdown files with YAML frontmatter"
  - "Skills hot-reload on file modification (mtime-based)"
  - "No direct database writes - use API"
  - "All API keys via environment variables"
---

# Skill Hot-Loading System

## Overview

Skills (tools) for the dispatcher agent are defined as markdown files and hot-loaded at runtime. This allows adding/updating skills without code changes or restarts.

## File Format

```markdown
---
name: lookup_portfolio
description: Look up current portfolio positions
category: portfolio
---

```python
async def skill_fn():
    # implementation
    return result
```
```

## Components

| Component | File | Purpose |
|-----------|------|---------|
| Skill Loader | `agents/dispatcher/skills/loader.py` | Parses markdown, extracts code, creates tools |
| Skills Dir | `agents/dispatcher/skills/` | Contains skill .md files |
| Integration | `agents/dispatcher/nodes.py` | Uses `get_skill_loader().get_tools()` instead of hardcoded |

## Existing Skills

1. `lookup_portfolio.md` - Query portfolio positions
2. `get_live_price.md` - Fetch market prices
3. `submit_decision.md` - Submit trading decisions
4. `lookup_pending_decisions.md` - List pending decisions
5. `parse_research_and_submit.md` - Parse research results

## Implementation Notes

- Skills use `@tool` decorator via LangChain
- Hot-reload uses `mtime` file monitoring
- Skills can be added by creating new `.md` files
