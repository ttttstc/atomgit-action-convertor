# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **GitHub Actions → CodeArts Actions (AtomGit)** converter. It transforms GitHub Actions source repositories into AtomGit plugin repositories by replacing:
- System env vars: `GITHUB_*` → `ATOMGIT_*`
- Context expressions: `github.*` → `atomgit.*` (inside `${{ }}` blocks only)
- Toolkit imports: `@actions/*` → `@atomgit/*`

## Commands

```bash
# Convert a GitHub Actions repo to AtomGit
python convert.py --input <source-repo> --output <output-repo>

# Dry-run (analyze without modifying files)
python convert.py --input <source-repo> --output <output-repo> --dry-run
```

## Architecture

The converter runs a 6-step pipeline (`convert.py`):

1. **Repository Analysis** — Validates `action.yml`, extracts entry points (`main`, `pre`, `post`), scans for compatibility issues
2. **action.yml Transformation** — Replaces `${{ github.* }}` → `${{ atomgit.* }}` and whitelist-matched `GITHUB_*` → `ATOMGIT_*`
3. **package.json Transformation** — Replaces `@actions/*` → `@atomgit/*` dependencies (except `@actions/github`)
4. **Source Code Transformation** — Transforms imports, `process.env` access, destructuring, and shell variables
5. **Rebuild** — Runs `npm install` and builds with `ncc` or `package.json` scripts
6. **Verification** — Checks for leaked `@actions/` or `GITHUB_*` refs in dist/

### Severity Ratings
- **GREEN**: Fully auto-convertible
- **YELLOW**: Contains `@actions/github` — converted but requires manual adaptation
- **RED**: Contains Octokit/GitHub API calls — converted as-is, flagged for review

### Important Exclusion Rules
- URLs (`github.com`, `raw.githubusercontent.com`, etc.) are **never** replaced
- `@actions/github` import is preserved as-is (not converted to `@atomgit/github`)
- Only whitelisted variables in `GITHUB_SYSTEM_VARS` (line 35 in `convert.py`) are replaced

### Supported Action Types
- Node-based actions: `node12`, `node16`, `node20`
- Not supported: Docker-based actions, composite actions

## Key Files

| File | Purpose |
|------|---------|
| `convert.py` | Main conversion script (single-file, no external dependencies) |
| `SKILL.md` | Full conversion workflow documentation |
| `CONVERSION_REPORT.md` | Sample output report showing what the conversion produces |
