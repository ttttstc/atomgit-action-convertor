---
name: github-to-codearts-action
description: >
  Convert GitHub Actions plugins to CodeArts Actions (AtomGit) plugins by transforming
  environment variable prefixes, context expressions, process file references, and
  @actions/* toolkit dependencies to their @atomgit/* equivalents. Use this skill whenever
  the user wants to: migrate a GitHub Action to CodeArts/AtomGit, convert action.yml or
  plugin source code from GITHUB_ to ATOMGIT_ conventions, adapt Node-based GitHub Actions
  (node12/node16/node20) for the CodeArts pipeline platform, or analyze a GitHub Action's
  compatibility with CodeArts. Also trigger when the user mentions "插件转换", "插件迁移",
  "CodeArts插件","CodeArts兼容", "AtomGit插件", or asks about converting between GitHub Actions and
  CodeArts Actions ecosystems.
---

# GitHub Actions → Atomgit  Actions 源码仓转换

This skill converts a **GitHub Actions source code repository** into a **complete
AtomGit (CodeArts Actions) plugin repository**. The input is the full source repo
of a GitHub Action (containing `action.yml`, `package.json`, `src/`, etc.), and the
output is a structurally identical but fully converted AtomGit plugin repo that can
be directly pushed and published.

The two plugin systems share the same structural definition (action.yml schema),
differing only in runtime naming conventions. This skill handles the full repo-level
conversion pipeline: repository analysis, source code transformation, dependency
migration, rebuild, and verification.

## Scope

**Supported**: Node-based actions (`runs.using: node12 | node16 | node20`)

**Not supported this version**:
- Docker-based actions (`runs.using: docker`)
- Composite actions (`runs.using: composite`)

**Partial support (convert with warnings)**:
- Actions that depend on `@actions/github` — the `@actions/github` import is
  preserved as-is since it wraps Octokit/GitHub API. Everything else in the repo
  is still converted. The user is responsible for adapting `@actions/github`
  related code post-conversion.

## Conversion Pipeline

Execute these steps in order. If any step fails, stop and report the failure with context.

### Step 1 — Repository Analysis & Initialization

Given a GitHub Actions source code repository as input:

1. **Locate entry definition**: Find `action.yml` or `action.yaml` in the repo root
   (support both names). If neither exists, report error and stop.
2. **Validate plugin type**: Read `runs.using` — must be `node12`, `node16`, or `node20`.
   If it's `docker` or `composite`, report as unsupported in this version and stop.
3. **Record entry points**: Extract `runs.main`, `runs.pre` (optional), `runs.post`
   (optional) — these are the build targets for Step 5.
4. **Validate source structure**: Verify `package.json` exists. Verify source code
   directory exists (`src/`, `lib/`, or `.ts`/`.js` files in root).
5. **Initialize output repo**: Copy the entire source repository to the output
   directory, excluding `node_modules/`, `.git/`, and `dist/` (dist will be rebuilt).
6. **Scan for non-convertible patterns**: Read `references/incompatible-patterns.md`
   and scan the source tree. This is a **non-blocking** scan — the conversion proceeds
   regardless, but all detected issues are recorded in the final conversion report
   (`CONVERSION_REPORT.md`) with file paths, line numbers, and severity ratings:
   - **GREEN**: Fully auto-convertible, no GitHub API dependencies
   - **YELLOW**: Contains `@actions/github` usage — converted with the import
     preserved, user must adapt manually
   - **RED**: Contains Octokit/GitHub REST/GraphQL calls — converted as-is,
     clearly flagged in the report for user attention

### Step 2 — action.yml Transformation

Read `references/variable-mapping.md` for the complete variable whitelist.

**Expression replacement rules (inside `${{ }}` blocks only):**
1. Extract all `${{ ... }}` expression blocks from the YAML
2. Inside each block, tokenize to distinguish identifiers from string literals
3. Replace `github.` prefix on identifier paths → `atomgit.` (first segment only)
   - `github.event.pull_request.head.sha` → `atomgit.event.pull_request.head.sha`
   - `github.token` → `atomgit.token`
4. Do NOT replace `github` inside string literals (e.g., `'https://github.com'` stays)
5. Do NOT replace `github` outside `${{ }}` blocks

**Environment variable replacement (in `env:`, `with:`, `defaults:` blocks):**
- Replace only whitelist-matched `GITHUB_*` variables → `ATOMGIT_*`
- Do NOT use blind `s/GITHUB_/ATOMGIT_/g` — always match against the whitelist

**Input defaults:**
- `${{ github.token }}` → `${{ atomgit.token }}` (covered by expression rule above)

### Step 3 — package.json Transformation

1. In `dependencies` and `devDependencies`, replace `@actions/*` → `@atomgit/*`
   - Exception: `@actions/github` — leave as-is (already flagged in Step 1)
   - Preserve version numbers (API-compatible guarantee)
2. Delete `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml` if present
3. Replaceable packages include but are not limited to:
   `@actions/core`, `@actions/exec`, `@actions/io`, `@actions/tool-cache`,
   `@actions/http-client`, `@actions/glob`, `@actions/cache` (if applicable),
   `@actions/artifact` (if applicable)

### Step 4 — Source Code Transformation

Scan all `.ts` and `.js` files under `src/` (and project root if no `src/` exists).
Read `references/variable-mapping.md` for the full whitelist.

**Rule 4a — Import/Require paths:**
```
require('@actions/core')        → require('@atomgit/core')
import * as X from '@actions/Y' → import * as X from '@atomgit/Y'
import { A } from '@actions/Y'  → import { A } from '@atomgit/Y'
```
Exception: `@actions/github` — leave unchanged.

**Rule 4b — process.env direct access (whitelist-only):**
```
process.env.GITHUB_TOKEN       → process.env.ATOMGIT_TOKEN
process.env['GITHUB_SHA']      → process.env['ATOMGIT_SHA']
process.env["GITHUB_REF"]      → process.env["ATOMGIT_REF"]
```

**Rule 4c — process.env destructuring (whitelist-only):**
```
const { GITHUB_TOKEN, GITHUB_SHA } = process.env
→ const { ATOMGIT_TOKEN, ATOMGIT_SHA } = process.env
```

**Rule 4d — Shell strings with variable references (whitelist-only):**
```
`echo $GITHUB_SHA`             → `echo $ATOMGIT_SHA`
`cat $GITHUB_EVENT_PATH`       → `cat $ATOMGIT_EVENT_PATH`
```

**Global exclusion — URL patterns must NEVER be replaced:**
- `github.com`, `github.io`, `raw.githubusercontent.com`
- Any `https://...github...` URL pattern
- The string `@actions/github` (import left as-is per exception rule)

Run the conversion script: `scripts/convert.py` — see script documentation for usage.
After the script completes, do a manual review of the diff to catch edge cases.

### Step 5 — Rebuild

1. Determine Node version from `runs.using` field:
   - `node12` → use Node 12.x, `node16` → use Node 16.x, `node20` → use Node 20.x
2. Run `npm install` (or `yarn install` if `yarn.lock` existed before deletion)
3. Identify build command:
   - If `package.json` has `scripts.build` → run it
   - If `package.json` has `scripts.package` → run it
   - Otherwise → run `npx @vercel/ncc build <entry> -o dist --source-map --license licenses.txt`
     for each entry point (main, pre, post)
4. Verify build exits with code 0. If not, report the error and stop.

### Step 6 — Verification

1. **Build artifact check**: Verify each entry point file exists in `dist/`
2. **Dependency leak check**: Search `dist/` output for any remaining `@actions/` or
   `GITHUB_` references (excluding URL patterns). Report any leaks as warnings.
3. **Test execution**: If `package.json` has `scripts.test`, run `npm test`.
   Report pass/fail. Test failures should be reported but do not block the conversion
   (tests may fail due to missing runtime environment).
4. **Generate conversion report** — output a summary listing:
   - Files modified (with change count per file)
   - Variables replaced (grouped by category)
   - Incompatible items detected (if any)
   - Build status
   - Test status

### Output Structure

The converted plugin is output as a complete directory, ready to be pushed as a
standalone repository:

```
<plugin-name>-atomgit/
├── action.yml              # Transformed
├── package.json            # Dependencies migrated
├── src/                    # Source code transformed
│   └── *.ts / *.js
├── dist/                   # Rebuilt artifacts
│   ├── index.js            # main entry
│   ├── setup.js            # pre entry (if exists)
│   └── cleanup.js          # post entry (if exists)
├── LICENSE                 # Preserved from original
├── README.md               # Preserved (optionally updated)
└── CONVERSION_REPORT.md    # Generated conversion report
```

## Important Conversion Principles

1. **Whitelist, not wildcard**: Every GITHUB_ → ATOMGIT_ replacement is validated against
   the official variable whitelist. User-defined variables starting with GITHUB_ are
   never touched.

2. **Source-level rebuild**: Always work from source code, not the pre-built `dist/`
   bundle. The dist/ bundle has all dependencies inlined and cannot be reliably patched.

3. **Preserve semantics**: This is a naming convention migration, not a logic rewrite.
   If any transformation would alter program behavior beyond variable naming, flag it
   for human review instead of auto-converting.

4. **Fail loudly**: If the conversion script encounters an ambiguous pattern it cannot
   confidently classify, it should log a WARNING and include the location in the
   conversion report, rather than silently guessing.

## Reference Files

- `references/variable-mapping.md` — Complete whitelist of GITHUB_* → ATOMGIT_*
  variable mappings and context expression mappings. Read this BEFORE starting any
  conversion. This is the single source of truth for what gets replaced.

- `references/incompatible-patterns.md` — Patterns that indicate a plugin cannot be
  auto-converted (GitHub API calls, Octokit usage, etc.). Read during Step 1.

- `references/expression-parser.md` — Rules and examples for safely parsing and
  transforming `${{ }}` GitHub Actions expressions without corrupting string literals
  or URL patterns.

## Scripts

- `scripts/convert.py` — Main conversion script. Handles Steps 2-4 programmatically.
  Run with: `python scripts/convert.py --input <source-dir> --output <output-dir>`
  The script reads the variable whitelist from `references/variable-mapping.md` at
  runtime — keep them co-located.
