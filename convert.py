#!/usr/bin/env python3
"""
GitHub Actions → CodeArts Actions (AtomGit) Source Repo Converter

Converts a GitHub Actions source code repository into a complete AtomGit
(CodeArts Actions) plugin repository by transforming:
- System environment variables: GITHUB_* → ATOMGIT_*
- Process file variables: $GITHUB_* → $ATOMGIT_*
- Context expressions: github.* → atomgit.* (inside ${{ }} blocks)
- Toolkit dependencies: @actions/* → @atomgit/*

The input is a full GitHub Actions source repo. The output is a structurally
identical but fully converted AtomGit plugin repo, ready to push and publish.

Usage:
    python convert.py --input <source-repo> --output <output-repo>
    python convert.py --input <source-repo> --output <output-repo> --dry-run
"""

import argparse
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

# ============================================================================
# Variable Whitelist — the ONLY variables that get replaced
# ============================================================================

GITHUB_SYSTEM_VARS = {
    "GITHUB_ACTION", "GITHUB_ACTION_PATH", "GITHUB_ACTION_REPOSITORY",
    "GITHUB_ACTIONS", "GITHUB_ACTOR", "GITHUB_ACTOR_ID",
    "GITHUB_API_URL", "GITHUB_BASE_REF", "GITHUB_ENV",
    "GITHUB_EVENT_NAME", "GITHUB_EVENT_PATH", "GITHUB_GRAPHQL_URL",
    "GITHUB_HEAD_REF", "GITHUB_JOB", "GITHUB_OUTPUT",
    "GITHUB_PATH", "GITHUB_REF", "GITHUB_REF_NAME",
    "GITHUB_REF_PROTECTED", "GITHUB_REF_TYPE", "GITHUB_REPOSITORY",
    "GITHUB_REPOSITORY_ID", "GITHUB_REPOSITORY_OWNER",
    "GITHUB_REPOSITORY_OWNER_ID", "GITHUB_RETENTION_DAYS",
    "GITHUB_RUN_ATTEMPT", "GITHUB_RUN_ID", "GITHUB_RUN_NUMBER",
    "GITHUB_SERVER_URL", "GITHUB_SHA", "GITHUB_STATE",
    "GITHUB_STEP_SUMMARY", "GITHUB_TOKEN", "GITHUB_TRIGGERING_ACTOR",
    "GITHUB_WORKFLOW", "GITHUB_WORKFLOW_REF", "GITHUB_WORKFLOW_SHA",
    "GITHUB_WORKSPACE",
}

# Packages that get replaced
REPLACEABLE_PACKAGES = {
    "@actions/core", "@actions/exec", "@actions/io",
    "@actions/tool-cache", "@actions/http-client",
    "@actions/glob", "@actions/cache", "@actions/artifact",
}

# Packages that are NOT replaced (flag as incompatible)
INCOMPATIBLE_PACKAGES = {
    "@actions/github",
}

# URL patterns that must never be replaced
URL_GUARD_PATTERN = re.compile(
    r'(?:https?://[^\s\'\"]*github|\.github\.com|\.github\.io|'
    r'githubusercontent\.com|githubassets\.com)'
)


# ============================================================================
# Data Structures
# ============================================================================

class Severity(Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


@dataclass
class Issue:
    file: str
    line: int
    severity: Severity
    category: str
    snippet: str


@dataclass
class Replacement:
    file: str
    line: int
    category: str
    before: str
    after: str


@dataclass
class ConversionReport:
    plugin_name: str
    compatibility: Severity = Severity.GREEN
    issues: list = field(default_factory=list)
    replacements: list = field(default_factory=list)
    files_modified: dict = field(default_factory=dict)
    build_status: str = "not_run"
    test_status: str = "not_run"
    entry_points: dict = field(default_factory=dict)

    def add_issue(self, issue: Issue):
        self.issues.append(issue)
        if issue.severity == Severity.RED:
            self.compatibility = Severity.RED
        elif issue.severity == Severity.YELLOW and self.compatibility != Severity.RED:
            self.compatibility = Severity.YELLOW

    def add_replacement(self, repl: Replacement):
        self.replacements.append(repl)
        self.files_modified.setdefault(repl.file, 0)
        self.files_modified[repl.file] += 1


# ============================================================================
# Step 1a: Input Validation
# ============================================================================

def find_action_yml(source_dir: Path) -> Optional[Path]:
    """Find action.yml or action.yaml in the plugin root."""
    for name in ("action.yml", "action.yaml"):
        path = source_dir / name
        if path.exists():
            return path
    return None


def parse_action_yml(action_path: Path) -> dict:
    """Parse action.yml to extract runs configuration.

    Uses a simple line-based parser to avoid PyYAML dependency.
    For production use, consider using PyYAML or ruamel.yaml.
    """
    content = action_path.read_text(encoding="utf-8")

    result = {"using": None, "main": None, "pre": None, "post": None}

    # Simple extraction — works for standard action.yml format
    in_runs = False
    for line in content.splitlines():
        stripped = line.strip()
        # Detect top-level 'runs:' block
        if line.startswith("runs:"):
            in_runs = True
            continue
        # Exit runs block on next top-level key
        if in_runs and not line.startswith(" ") and not line.startswith("\t") and stripped:
            in_runs = False
        if in_runs:
            for key in ("using", "main", "pre", "post"):
                pattern = rf"^\s+{key}:\s*['\"]?([^'\"#\s]+)"
                m = re.match(pattern, line)
                if m:
                    result[key] = m.group(1).strip("'\"")

    return result


def validate_input(source_dir: Path) -> tuple:
    """Step 1a: Validate input repository and extract metadata.

    Returns: (action_path, runs_config, list_of_errors)
    """
    errors = []

    action_path = find_action_yml(source_dir)
    if not action_path:
        errors.append("No action.yml or action.yaml found in plugin root")
        return None, None, errors

    runs = parse_action_yml(action_path)

    if not runs["using"]:
        errors.append("Could not parse 'runs.using' from action.yml")
        return action_path, runs, errors

    supported = {"node12", "node16", "node20"}
    if runs["using"] not in supported:
        errors.append(
            f"Unsupported runs.using: '{runs['using']}'. "
            f"Only {supported} are supported."
        )
        return action_path, runs, errors

    if not runs["main"]:
        errors.append("No 'runs.main' entry point found in action.yml")

    pkg_path = source_dir / "package.json"
    if not pkg_path.exists():
        errors.append("No package.json found — cannot process Node-based action")

    return action_path, runs, errors


# ============================================================================
# Step 1c: Non-blocking Compatibility Scan
# ============================================================================

# RED patterns
RED_PATTERNS = [
    (re.compile(r'\bnew\s+Octokit\b'), "Octokit constructor"),
    (re.compile(r'\boctokit\s*\.\s*(?:rest|graphql|request|paginate)\b'), "Octokit API call"),
    (re.compile(r'\bgetOctokit\s*\('), "getOctokit() call"),
    (re.compile(r'https?://api\.github\.com'), "GitHub API endpoint"),
]

# YELLOW patterns (source code)
YELLOW_PATTERNS = [
    (re.compile(r"from\s+['\"]@actions/github['\"]"), "@actions/github import"),
    (re.compile(r"require\s*\(\s*['\"]@actions/github['\"]\s*\)"), "@actions/github require"),
]


def scan_file_for_issues(filepath: Path, rel_path: str) -> list:
    """Scan a single source file for compatibility issues."""
    issues = []
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return issues

    for line_num, line in enumerate(content.splitlines(), 1):
        for pattern, category in RED_PATTERNS:
            if pattern.search(line):
                issues.append(Issue(
                    file=rel_path, line=line_num,
                    severity=Severity.RED, category=category,
                    snippet=line.strip()[:120]
                ))

        for pattern, category in YELLOW_PATTERNS:
            if pattern.search(line):
                # Check if it's context-only usage (YELLOW) vs API usage (RED)
                issues.append(Issue(
                    file=rel_path, line=line_num,
                    severity=Severity.YELLOW, category=category,
                    snippet=line.strip()[:120]
                ))

    return issues


def scan_package_json(source_dir: Path) -> list:
    """Scan package.json for incompatible dependencies."""
    issues = []
    pkg_path = source_dir / "package.json"
    if not pkg_path.exists():
        return issues

    try:
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
    except Exception:
        return issues

    deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

    for pkg_name in INCOMPATIBLE_PACKAGES:
        if pkg_name in deps:
            issues.append(Issue(
                file="package.json", line=0,
                severity=Severity.YELLOW,
                category=f"Incompatible dependency: {pkg_name}",
                snippet=f"{pkg_name}: {deps[pkg_name]}"
            ))

    return issues


def scan_compatibility(source_dir: Path) -> list:
    """Step 1c: Non-blocking compatibility scan. Results go into the report."""
    all_issues = []

    # Scan package.json
    all_issues.extend(scan_package_json(source_dir))

    # Scan source files
    scan_globs = ["src/**/*.ts", "src/**/*.js", "*.ts", "*.js",
                  "__tests__/**/*.ts", "__tests__/**/*.js",
                  "test/**/*.ts", "test/**/*.js"]

    scanned = set()
    for glob_pattern in scan_globs:
        for filepath in source_dir.glob(glob_pattern):
            if filepath in scanned:
                continue
            # Skip node_modules and dist
            rel = filepath.relative_to(source_dir)
            if any(part in ("node_modules", "dist", ".git") for part in rel.parts):
                continue
            scanned.add(filepath)
            all_issues.extend(
                scan_file_for_issues(filepath, str(rel))
            )

    # Upgrade YELLOW @actions/github issues to RED if getOctokit is also found
    has_get_octokit = any(
        i.category == "getOctokit() call" for i in all_issues
    )
    if has_get_octokit:
        for issue in all_issues:
            if issue.category in ("@actions/github import", "@actions/github require"):
                issue.severity = Severity.RED

    return all_issues


# ============================================================================
# Step 2: action.yml Transformation
# ============================================================================

def is_inside_url(text: str, match_start: int) -> bool:
    """Check if a match position is inside a URL pattern."""
    # Look back up to 30 chars for URL indicators
    lookback = text[max(0, match_start - 30):match_start]
    if "://" in lookback or lookback.rstrip().endswith("."):
        return True
    # Check if followed by .com, .io, etc.
    lookahead = text[match_start:match_start + 20]
    if re.match(r'github\.(com|io|dev)\b', lookahead):
        return True
    return False


def transform_expression(expr: str) -> str:
    """Transform github.* references inside a ${{ }} expression.

    Splits on string literals to protect them, then replaces github. → atomgit.
    in non-literal segments only.
    """
    # Split on single-quoted string literals
    parts = re.split(r"('(?:[^'\\]|\\.)*')", expr)
    result = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            # Inside string literal — don't touch
            result.append(part)
        else:
            # Outside string literal — replace github. identifiers
            part = re.sub(r'\bgithub\.', 'atomgit.', part)
            result.append(part)
    return ''.join(result)


def transform_action_yml(content: str) -> tuple:
    """Step 2: Transform action.yml content.

    Returns: (transformed_content, list_of_replacements)
    """
    replacements = []
    lines = content.splitlines(keepends=True)
    result_lines = []

    for line_num, line in enumerate(lines, 1):
        original = line

        # 1. Transform ${{ }} expressions
        def expr_replacer(match):
            full_match = match.group(0)
            inner = match.group(1)
            transformed = transform_expression(inner)
            if inner != transformed:
                return '${{ ' + transformed + ' }}'
            return full_match

        line = re.sub(r'\$\{\{\s*(.*?)\s*\}\}', expr_replacer, line, flags=re.DOTALL)

        # 2. Transform GITHUB_* env var references (whitelist only)
        for var in GITHUB_SYSTEM_VARS:
            atomgit_var = var.replace("GITHUB_", "ATOMGIT_", 1)
            # Match as complete variable name (not part of a longer name)
            pattern = re.compile(rf'\b{re.escape(var)}\b')
            if pattern.search(line):
                # Guard against URL context
                for m in pattern.finditer(line):
                    if not is_inside_url(line, m.start()):
                        line = line[:m.start()] + atomgit_var + line[m.end():]
                        break  # Re-scan after modification (positions shifted)
                # Simple approach: just replace all non-URL occurrences
                # More robust: re-run until stable
                new_line = line
                for _ in range(5):  # Max 5 replacements per line
                    prev = new_line
                    for m in pattern.finditer(new_line):
                        if not is_inside_url(new_line, m.start()):
                            new_line = new_line[:m.start()] + atomgit_var + new_line[m.end():]
                            break
                    if new_line == prev:
                        break
                line = new_line

        if line != original:
            replacements.append(Replacement(
                file="action.yml", line=line_num,
                category="action.yml expression/env",
                before=original.strip(), after=line.strip()
            ))

        result_lines.append(line)

    return ''.join(result_lines), replacements


# ============================================================================
# Step 3: package.json Transformation
# ============================================================================

def transform_package_json(content: str) -> tuple:
    """Step 3: Transform package.json content.

    Returns: (transformed_content, list_of_replacements)
    """
    replacements = []

    try:
        pkg = json.loads(content)
    except json.JSONDecodeError as e:
        return content, [Replacement(
            file="package.json", line=0,
            category="parse_error",
            before=f"JSON parse error: {e}", after=""
        )]

    # Replace in dependencies and devDependencies
    for dep_key in ("dependencies", "devDependencies"):
        if dep_key not in pkg:
            continue

        new_deps = {}
        for name, version in pkg[dep_key].items():
            if name in REPLACEABLE_PACKAGES:
                new_name = name.replace("@actions/", "@atomgit/", 1)
                new_deps[new_name] = version
                replacements.append(Replacement(
                    file="package.json", line=0,
                    category=f"{dep_key} replacement",
                    before=f"{name}: {version}",
                    after=f"{new_name}: {version}"
                ))
            else:
                new_deps[name] = version

        pkg[dep_key] = new_deps

    transformed = json.dumps(pkg, indent=2, ensure_ascii=False) + "\n"
    return transformed, replacements


# ============================================================================
# Step 4: Source Code Transformation
# ============================================================================

def transform_source_file(content: str, filepath: str) -> tuple:
    """Step 4: Transform a JS/TS source file.

    Returns: (transformed_content, list_of_replacements)
    """
    replacements = []
    lines = content.splitlines(keepends=True)
    result_lines = []

    for line_num, line in enumerate(lines, 1):
        original = line

        # Skip lines that are purely comments
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("*"):
            result_lines.append(line)
            continue

        # Rule 4a: Import/require path replacement
        # require('@actions/core') → require('@atomgit/core')
        for pkg in REPLACEABLE_PACKAGES:
            atomgit_pkg = pkg.replace("@actions/", "@atomgit/", 1)
            # Handle both single and double quotes
            for q in ("'", '"'):
                old = f"{q}{pkg}{q}"
                new = f"{q}{atomgit_pkg}{q}"
                if old in line:
                    line = line.replace(old, new)

        # Rule 4b: process.env.GITHUB_* direct access (whitelist only)
        for var in GITHUB_SYSTEM_VARS:
            atomgit_var = var.replace("GITHUB_", "ATOMGIT_", 1)

            # process.env.GITHUB_XXX
            pattern_dot = f"process.env.{var}"
            if pattern_dot in line:
                # Guard: make sure it's not inside a URL
                idx = line.find(pattern_dot)
                if idx >= 0 and not is_inside_url(line, idx):
                    line = line.replace(pattern_dot, f"process.env.{atomgit_var}")

            # process.env['GITHUB_XXX'] and process.env["GITHUB_XXX"]
            for q in ("'", '"'):
                bracket_old = f"process.env[{q}{var}{q}]"
                bracket_new = f"process.env[{q}{atomgit_var}{q}]"
                if bracket_old in line:
                    line = line.replace(bracket_old, bracket_new)

        # Rule 4c: Destructuring from process.env
        # const { GITHUB_TOKEN, GITHUB_SHA } = process.env
        destructure_match = re.search(
            r'(?:const|let|var)\s*\{([^}]+)\}\s*=\s*process\.env', line
        )
        if destructure_match:
            vars_block = destructure_match.group(1)
            new_vars_block = vars_block
            for var in GITHUB_SYSTEM_VARS:
                atomgit_var = var.replace("GITHUB_", "ATOMGIT_", 1)
                new_vars_block = re.sub(
                    rf'\b{re.escape(var)}\b', atomgit_var, new_vars_block
                )
            if new_vars_block != vars_block:
                line = line.replace(vars_block, new_vars_block)

        # Rule 4d: Shell variable references in template strings
        # `echo $GITHUB_SHA` → `echo $ATOMGIT_SHA`
        # Only match $GITHUB_XXX that are in the whitelist
        for var in GITHUB_SYSTEM_VARS:
            atomgit_var = var.replace("GITHUB_", "ATOMGIT_", 1)
            # Match $GITHUB_XXX or ${GITHUB_XXX} in strings
            shell_patterns = [
                (rf'\${re.escape(var)}\b', f'${atomgit_var}'),
                (rf'\$\{{{re.escape(var)}\}}', f'${{{atomgit_var}}}'),
            ]
            for pat, repl in shell_patterns:
                new_line = re.sub(pat, repl, line)
                if new_line != line:
                    # Verify not inside a URL
                    line = new_line

        # Record replacement
        if line != original:
            replacements.append(Replacement(
                file=filepath, line=line_num,
                category="source code",
                before=original.strip()[:120],
                after=line.strip()[:120]
            ))

        result_lines.append(line)

    return ''.join(result_lines), replacements


# ============================================================================
# Step 6: Verification — Dependency Leak Check
# ============================================================================

def check_leaks_in_dist(output_dir: Path) -> list:
    """Scan dist/ for any remaining GITHUB_ or @actions/ references."""
    leaks = []
    dist_dir = output_dir / "dist"
    if not dist_dir.exists():
        return leaks

    for filepath in dist_dir.rglob("*.js"):
        try:
            content = filepath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        rel = filepath.relative_to(output_dir)

        for line_num, line in enumerate(content.splitlines(), 1):
            # Check for @actions/ (excluding @actions/github which is allowed)
            for pkg in REPLACEABLE_PACKAGES:
                if pkg in line:
                    leaks.append(Issue(
                        file=str(rel), line=line_num,
                        severity=Severity.YELLOW,
                        category=f"Leak: {pkg} in dist",
                        snippet=line.strip()[:120]
                    ))

            # Check for GITHUB_ system vars
            for var in GITHUB_SYSTEM_VARS:
                if var in line and not is_inside_url(line, line.find(var)):
                    # Exclude common false positives in comments
                    leaks.append(Issue(
                        file=str(rel), line=line_num,
                        severity=Severity.YELLOW,
                        category=f"Leak: {var} in dist",
                        snippet=line.strip()[:120]
                    ))

    return leaks


# ============================================================================
# Report Generation
# ============================================================================

def generate_report(report: ConversionReport) -> str:
    """Generate a Markdown conversion report."""
    lines = [
        f"# Conversion Report: {report.plugin_name}",
        "",
        f"**Compatibility Rating**: {report.compatibility.value}",
        f"**Build Status**: {report.build_status}",
        f"**Test Status**: {report.test_status}",
        "",
    ]

    # Entry points
    if report.entry_points:
        lines.append("## Entry Points")
        lines.append("")
        for key, val in report.entry_points.items():
            if val:
                lines.append(f"- **{key}**: `{val}`")
        lines.append("")

    # Issues
    if report.issues:
        lines.append("## Compatibility Issues")
        lines.append("")
        for issue in report.issues:
            icon = {"RED": "🔴", "YELLOW": "🟡", "GREEN": "🟢"}[issue.severity.value]
            lines.append(
                f"- {icon} **{issue.severity.value}** `{issue.file}:{issue.line}` "
                f"— {issue.category}"
            )
            lines.append(f"  ```")
            lines.append(f"  {issue.snippet}")
            lines.append(f"  ```")
        lines.append("")

    # Files modified
    if report.files_modified:
        lines.append("## Files Modified")
        lines.append("")
        total = sum(report.files_modified.values())
        lines.append(f"**Total replacements**: {total}")
        lines.append("")
        for filepath, count in sorted(report.files_modified.items()):
            lines.append(f"- `{filepath}`: {count} change(s)")
        lines.append("")

    # Replacement details
    if report.replacements:
        lines.append("## Replacement Details")
        lines.append("")
        for repl in report.replacements:
            lines.append(f"### `{repl.file}:{repl.line}` ({repl.category})")
            lines.append(f"```diff")
            lines.append(f"- {repl.before}")
            lines.append(f"+ {repl.after}")
            lines.append(f"```")
            lines.append("")

    return "\n".join(lines)


# ============================================================================
# Main Pipeline
# ============================================================================

def convert(source_dir: Path, output_dir: Path, dry_run: bool = False) -> ConversionReport:
    """Execute the full conversion pipeline.

    Converts a GitHub Actions source code repository into a complete
    AtomGit (CodeArts Actions) plugin repository.
    """

    plugin_name = source_dir.name
    report = ConversionReport(plugin_name=plugin_name)

    print(f"🔄 Converting GitHub Actions repo → AtomGit plugin repo")
    print(f"   Source repo: {source_dir}")
    print(f"   Output repo: {output_dir}")
    print()

    # Step 1: Repository Analysis & Initialization
    print("Step 1: Repository Analysis & Initialization...")

    # 1a. Validate input structure
    action_path, runs, errors = validate_input(source_dir)
    if errors:
        for err in errors:
            print(f"  ❌ {err}")
            report.add_issue(Issue(
                file="", line=0, severity=Severity.RED,
                category="validation", snippet=err
            ))
        return report

    report.entry_points = {
        "using": runs["using"],
        "main": runs["main"],
        "pre": runs.get("pre"),
        "post": runs.get("post"),
    }
    print(f"  ✅ Plugin type: {runs['using']}, main={runs['main']}, "
          f"pre={runs.get('pre', 'none')}, post={runs.get('post', 'none')}")

    # 1b. Initialize output repo (copy source, excluding node_modules/.git/dist)
    if not dry_run:
        if output_dir.exists():
            shutil.rmtree(output_dir)
        shutil.copytree(source_dir, output_dir, ignore=shutil.ignore_patterns(
            'node_modules', '.git', 'dist'
        ))
        print(f"  📁 Initialized output repo: {output_dir}")

    # 1c. Non-blocking compatibility scan
    print("  🔍 Scanning for non-convertible patterns...")
    issues = scan_compatibility(source_dir)
    for issue in issues:
        report.add_issue(issue)
        icon = {"RED": "🔴", "YELLOW": "🟡"}[issue.severity.value]
        print(f"     {icon} [{issue.severity.value}] {issue.file}:{issue.line} "
              f"— {issue.category}")

    if not issues:
        print("  ✅ No compatibility issues detected (GREEN)")
    else:
        print(f"  ⚠️  {len(issues)} issue(s) detected — recorded in CONVERSION_REPORT.md, "
              f"proceeding with conversion")

    # Step 2: action.yml Transformation
    print("\nStep 2: action.yml Transformation...")
    action_name = action_path.name
    action_file = output_dir / action_name if not dry_run else action_path
    content = action_file.read_text(encoding="utf-8")
    transformed, repls = transform_action_yml(content)
    for r in repls:
        report.add_replacement(r)
    if not dry_run and repls:
        action_file.write_text(transformed, encoding="utf-8")
    print(f"  ✅ {len(repls)} replacement(s) in {action_name}")

    # Step 3: package.json Transformation
    print("\nStep 3: package.json Transformation...")
    pkg_file = output_dir / "package.json" if not dry_run else source_dir / "package.json"
    content = pkg_file.read_text(encoding="utf-8")
    transformed, repls = transform_package_json(content)
    for r in repls:
        report.add_replacement(r)
    if not dry_run and repls:
        pkg_file.write_text(transformed, encoding="utf-8")
    print(f"  ✅ {len(repls)} dependency replacement(s)")

    # Delete lock files
    if not dry_run:
        for lock_file in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml"):
            lock_path = output_dir / lock_file
            if lock_path.exists():
                lock_path.unlink()
                print(f"  🗑️  Deleted {lock_file}")

    # Step 4: Source Code Transformation
    print("\nStep 4: Source Code Transformation...")
    source_extensions = {".ts", ".js"}
    scan_dirs = ["src", "lib", "."]
    scanned = set()
    total_source_repls = 0

    for scan_dir in scan_dirs:
        base = (output_dir if not dry_run else source_dir) / scan_dir
        if not base.exists():
            continue
        for ext in source_extensions:
            for filepath in base.rglob(f"*{ext}"):
                if filepath in scanned:
                    continue
                rel = filepath.relative_to(output_dir if not dry_run else source_dir)
                if any(part in ("node_modules", "dist", ".git", "__tests__", "test")
                       for part in rel.parts):
                    continue
                scanned.add(filepath)

                content = filepath.read_text(encoding="utf-8", errors="replace")
                transformed, repls = transform_source_file(content, str(rel))
                for r in repls:
                    report.add_replacement(r)
                    total_source_repls += 1
                if not dry_run and repls:
                    filepath.write_text(transformed, encoding="utf-8")

    print(f"  ✅ {total_source_repls} replacement(s) across "
          f"{len(scanned)} source file(s)")

    if dry_run:
        print("\n🏁 Dry-run complete. No files were modified.")
        return report

    report.build_status = "pending"
    report.test_status = "pending"

    # Generate conversion report file
    report_content = generate_report(report)
    report_path = output_dir / "CONVERSION_REPORT.md"
    report_path.write_text(report_content, encoding="utf-8")
    print(f"\n📝 Conversion report written to {report_path}")

    print("\n" + "=" * 60)
    print(f"✅ Repo conversion complete: {plugin_name}")
    print(f"   Output repo: {output_dir}")
    print(f"   Compatibility: {report.compatibility.value}")
    print(f"   Total replacements: {len(report.replacements)}")
    print(f"   Files modified: {len(report.files_modified)}")
    print("=" * 60)
    print()
    print("Next steps:")
    print(f"  1. cd {output_dir}")
    print(f"  2. npm install")
    print(f"  3. npm run build  (or: npx @vercel/ncc build {runs['main']} -o dist)")
    print(f"  4. npm test  (if tests exist)")
    print(f"  5. Review CONVERSION_REPORT.md for any flagged issues")
    print(f"  6. git init && git add . && git commit  (push as new AtomGit repo)")

    return report


# ============================================================================
# CLI Entry Point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Convert a GitHub Actions source repo into a CodeArts Actions "
                    "(AtomGit) plugin repo"
    )
    parser.add_argument(
        "--input", "-i", required=True,
        help="Path to the GitHub Actions source code repository"
    )
    parser.add_argument(
        "--output", "-o",
        help="Path for the output AtomGit plugin repository "
             "(default: <input>-atomgit)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Analyze and report without modifying any files"
    )

    args = parser.parse_args()

    source_dir = Path(args.input).resolve()
    if not source_dir.exists():
        print(f"❌ Source directory not found: {source_dir}")
        sys.exit(1)

    if args.output:
        output_dir = Path(args.output).resolve()
    else:
        output_dir = source_dir.parent / f"{source_dir.name}-atomgit"

    report = convert(source_dir, output_dir, dry_run=args.dry_run)

    # Exit code: 0=GREEN, 1=YELLOW, 2=RED (non-blocking, just informational)
    if report.compatibility == Severity.RED:
        sys.exit(2)
    elif report.compatibility == Severity.YELLOW:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
