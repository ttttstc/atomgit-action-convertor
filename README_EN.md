# GitHub Actions → CodeArts Actions Converter

[中文](README.md)

A tool for converting GitHub Actions source repositories into CodeArts Actions (AtomGit) plugin repositories.

## Features

- **Environment Variable Conversion** — `GITHUB_*` → `ATOMGIT_*`
- **Context Expression Conversion** — `${{ github.* }}` → `${{ atomgit.* }}` (inside `${{ }}` blocks only)
- **Dependency Conversion** — `@actions/*` → `@atomgit/*`
- **Compatibility Scanning** — Auto-detects patterns that cannot be auto-converted (Octokit calls, GitHub API, etc.)

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
| 🟡 YELLOW | Contains `@actions/github` — converted, requires manual adaptation |
| 🔴 RED | Contains Octokit/GitHub API calls — converted, requires human review |

## Quick Start

### Install Dependencies

No external dependencies required. Run directly:

```bash
python convert.py --help
```

### Basic Usage

```bash
# Convert a repository
python convert.py --input <source-repo> --output <output-repo>

# Dry-run (analyze only, no file changes)
python convert.py --input <source-repo> --output <output-repo> --dry-run
```

### Full Conversion Workflow

```bash
# 1. Convert
python convert.py --input ./my-action --output ./my-action-atomgit

# 2. Install dependencies
cd my-action-atomgit
npm install

# 3. Build
npm run build
# or
npx @vercel/ncc build src/index.ts -o dist

# 4. Test
npm test

# 5. Review conversion report
cat CONVERSION_REPORT.md

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
... (50+ variables, see line 35 in convert.py)
```

### What Is NOT Converted

- ❌ URLs like `github.com`, `raw.githubusercontent.com`
- ❌ `@actions/github` imports (preserved as-is, manual adaptation required)
- ❌ User-defined `GITHUB_*` variables

### Examples

| Original | Converted |
|----------|-----------|
| `${{ github.token }}` | `${{ atomgit.token }}` |
| `process.env.GITHUB_SHA` | `process.env.ATOMGIT_SHA` |
| `import * as core from '@actions/core'` | `import * as core from '@atomgit/core'` |
| `echo $GITHUB_OUTPUT` | `echo $ATOMGIT_OUTPUT` |

## Conversion Report

After conversion, `CONVERSION_REPORT.md` is generated with:

- Compatibility rating
- List of modified files
- All replacement details
- Build/test status

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
