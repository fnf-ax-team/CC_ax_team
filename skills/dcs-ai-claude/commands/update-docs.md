---
description: Sync documentation from source-of-truth files
---

# Update Documentation

**⚡ Action Required**: Use the `Task` tool to spawn the `doc-updater` sub-agent.

```
Task({
  subagent_type: "doc-updater",
  prompt: "Sync documentation from source-of-truth files (package.json, .env.example). Generate CONTRIB.md and RUNBOOK.md.",
  description: "Documentation update"
})
```

## Context for the Agent

The doc-updater agent will:

1. Read `package.json` scripts section
   - Generate scripts reference table
   - Include descriptions from comments

2. Read `.env.example`
   - Extract all environment variables
   - Document purpose and format

3. Generate `docs/CONTRIB.md` with:
   - Development workflow
   - Available scripts
   - Environment setup
   - Testing procedures

4. Generate `docs/RUNBOOK.md` with:
   - Deployment procedures
   - Monitoring and alerts
   - Common issues and fixes
   - Rollback procedures

5. Identify obsolete documentation:
   - Find docs not modified in 90+ days
   - List for manual review

6. Show diff summary

## Source of Truth

- `package.json` - Scripts and dependencies
- `.env.example` - Environment variables
- `CLAUDE.md` - Architecture decisions

Always sync docs from these files, never the other way around.
