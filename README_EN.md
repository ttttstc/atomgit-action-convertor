# GitHub Actions → AtomGit Actions Converter

[中文](README.md)

A tool for converting GitHub Actions source repositories into AtomGit Actions plugin repositories.

## Features

- **Environment Variable Conversion** — `GITHUB_*` → `ATOMGIT_*`
- **Context Expression Conversion** — `${{ github.* }}` → `${{ atomgit.* }}` (inside `${{ }}` blocks only)
- **Compatibility Scanning** — Auto-detects patterns that cannot be auto-converted (Octokit calls, GitHub API, etc.)
- **Pre-conversion Evaluation** — Output feasibility report before executing conversion

## Supported Action Types

| Type | Status |
|------|--------|
| Node.js (`node12`, `node16`, `node20`) | ✅ Supported |
| Docker (`runs.using: docker`) | ❌ Not supported |
| Composite (`runs.using: composite`) | ❌ Not supported |

## Compatibility Ratings

| Rating | Meaning |
|--------|---------|
| 🟢 GREEN | Fully auto-convertible, no GitHub API dependencies |
| 🟡 YELLOW | Contains @actions/* dependencies, requires manual adaptation |
| 🔴 RED | Contains Octokit/GitHub API calls, requires reimplementation |

## Quick Start

### Basic Usage

```bash
# Pre-conversion evaluation (recommended)
python convert.py --input <source-repo> --evaluate-only

# Execute conversion
python convert.py --input <source-repo> --output <output-repo>

# Dry-run (analyze only, no file changes)
python convert.py --input <source-repo> --output <output-repo> --dry-run
```

### Full Conversion Workflow

```bash
# 1. Pre-conversion evaluation
python convert.py --input ./my-action --evaluate-only

# 2. Execute conversion
python convert.py --input ./my-action --output ./my-action-atomgit

# 3. Handle @actions/* dependencies (manual)
# Replace with AtomGit platform equivalents

# 4. Rebuild (required)
cd my-action-atomgit
npm install
npm run build

# 5. Test
npm test

# 6. Commit and push
git init && git add . && git commit -m "Convert to AtomGit"
```

## Conversion Rules

### Environment Variables (Whitelist Only)

Only these variables are converted:

```
GITHUB_ACTION          → ATOMGIT_ACTION
GITHUB_ACTOR           → ATOMGIT_ACTOR
GITHUB_SHA             → ATOMGIT_SHA
GITHUB_REF             → ATOMGIT_REF
GITHUB_REF_NAME        → ATOMGIT_REF_NAME
GITHUB_REPOSITORY      → ATOMGIT_REPOSITORY
GITHUB_TOKEN           → ATOMGIT_TOKEN
GITHUB_WORKSPACE       → ATOMGIT_WORKSPACE
GITHUB_RUN_ID          → ATOMGIT_RUN_ID
GITHUB_SERVER_URL      → ATOMGIT_SERVER_URL
... (50+ variables, see convert.py)
```

### What Is NOT Converted

- ❌ URLs like `github.com`, `raw.githubusercontent.com`
- ❌ `@actions/*` dependency packages (must be manually replaced with AtomGit equivalents)
- ❌ User-defined `GITHUB_*` variables

### Examples

| Original | Converted |
|----------|-----------|
| `${{ github.token }}` | `${{ atomgit.token }}` |
| `process.env.GITHUB_SHA` | `process.env.ATOMGIT_SHA` |
| `echo $GITHUB_OUTPUT` | `echo $ATOMGIT_OUTPUT` |

## ⚠️ Important Reminders

- **Rebuild Required**: After converting source code, you MUST run `npm run build`,
  otherwise the published plugin will still use the old dist/ bundle
- **@actions/* Dependencies**: AtomGit does not provide `@atomgit/*` toolkit packages.
  Users must handle these manually.

## Conversion Report

After conversion, `CONVERSION_REPORT.md` is generated with:

- Compatibility rating
- List of modified files
- All replacement details
- Build/test status
- ⚠️ Rebuild reminder

## Project Structure

```
.
├── convert.py              # Main conversion script
├── SKILL.md                # Full conversion workflow documentation
├── CONVERSION_REPORT.md    # Sample conversion report
└── CLAUDE.md               # Claude Code development guide
```

## License

MIT
