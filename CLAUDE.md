# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **GitHub Actions → AtomGit Actions** converter. It transforms GitHub Actions source repositories into AtomGit plugin repositories by replacing:
- System env vars: `GITHUB_*` → `ATOMGIT_*`
- Context expressions: `github.*` → `atomgit.*` (inside `${{ }}` blocks only)

**Note**: This converter does NOT replace `@actions/*` packages. Users must maintain their own AtomGit-compatible toolkit packages.

## Commands

```bash
# Pre-conversion evaluation (recommended first step)
python convert.py --input <source-repo> --evaluate-only

# Convert a GitHub Actions repo to AtomGit
python convert.py --input <source-repo> --output <output-repo>

# Dry-run (analyze without modifying files)
python convert.py --input <source-repo> --output <output-repo> --dry-run
```

## Architecture

The converter runs a 5-step pipeline (`convert.py`):

1. **Repository Analysis** — Validates `action.yml`, extracts entry points, scans for compatibility issues
2. **action.yml Transformation** — Replaces `${{ github.* }}` → `${{ atomgit.* }}` and whitelist-matched `GITHUB_*` → `ATOMGIT_*`
3. **Source Code Transformation** — Transforms `process.env` access, destructuring, and shell variables
4. **Rebuild** — Runs `npm install` and builds with `ncc` or `package.json` scripts
5. **Verification** — Checks for leaked `GITHUB_*` refs in dist/

### Severity Ratings
- **GREEN**: Fully auto-convertible
- **YELLOW**: Contains `@actions/*` dependencies — NOT replaced, requires manual adaptation
- **RED**: Contains Octokit/GitHub API calls — requires reimplementation

### Important Exclusion Rules
- URLs (`github.com`, `raw.githubusercontent.com`, etc.) are **never** replaced
- `@actions/*` packages are **NOT** replaced (no `@atomgit/*` toolkit exists)
- Only whitelisted variables in `GITHUB_SYSTEM_VARS` are replaced

### Supported Action Types
- Node-based actions: `node12`, `node16`, `node20`
- Not supported: Docker-based actions, composite actions

## Key Files

| File | Purpose |
|------|---------|
| `convert.py` | Main conversion script (single-file, no external dependencies) |
| `SKILL.md` | Full conversion workflow documentation |
| `CONVERSION_REPORT.md` | Sample output report |
