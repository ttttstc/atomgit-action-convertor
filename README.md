# GitHub Actions → AtomGit Actions 转换器

[English](README_EN.md)

将 GitHub Actions 源码仓库转换为 AtomGit Actions 插件仓库的工具。

## 功能特性

- **环境变量转换** — `GITHUB_*` → `ATOMGIT_*`
- **上下文表达式转换** — `${{ github.* }}` → `${{ atomgit.* }}`（仅限 `${{ }}` 块内）
- **兼容性扫描** — 自动识别无法自动转换的模式（Octokit 调用、GitHub API 等）
- **转换前评估** — 先输出可行性报告，用户确认后再执行转换

## 支持的 Action 类型

| 类型 | 状态 |
|------|------|
| Node.js (`node12`, `node16`, `node20`) | ✅ 支持 |
| Docker (`runs.using: docker`) | ❌ 不支持 |
| Composite (`runs.using: composite`) | ❌ 不支持 |

## 兼容性等级

| 等级 | 含义 |
|------|------|
| 🟢 GREEN | 可完全自动转换，无需人工介入 |
| 🟡 YELLOW | 含 @actions/* 依赖，需手动适配 |
| 🔴 RED | 含 Octokit/GitHub API 调用，需重新实现 |

## 快速开始

### 基本用法

```bash
# 转换前先评估（推荐）
python convert.py --input <源仓库> --evaluate-only

# 执行转换
python convert.py --input <源仓库> --output <输出路径>

# 预览模式（仅分析，不修改文件）
python convert.py --input <源仓库> --output <输出路径> --dry-run
```

### 完整转换流程

```bash
# 1. 转换前评估
python convert.py --input ./my-action --evaluate-only

# 2. 执行转换
python convert.py --input ./my-action --output ./my-action-atomgit

# 3. 处理 @actions/* 依赖（手动）
# 替换为 AtomGit 平台提供的等效方案

# 4. 重建（必须）
cd my-action-atomgit
npm install
npm run build

# 5. 测试
npm test

# 6. 提交推送
git init && git add . && git commit -m "Convert to AtomGit"
```

## 转换规则

### 环境变量（仅白名单）

以下变量会被转换：

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
...（50+ 变量，见 convert.py）
```

### 不会被转换的内容

- ❌ URL（如 `github.com`、`raw.githubusercontent.com`）
- ❌ `@actions/*` 依赖包（需用户手动替换为 AtomGit 方案）
- ❌ 用户自定义的 `GITHUB_*` 变量

### 示例

| 原内容 | 转换后 |
|--------|--------|
| `${{ github.token }}` | `${{ atomgit.token }}` |
| `process.env.GITHUB_SHA` | `process.env.ATOMGIT_SHA` |
| `echo $GITHUB_OUTPUT` | `echo $ATOMGIT_OUTPUT` |

## ⚠️ 重要提醒

- **必须重建**: 转换源码后必须 `npm run build`，否则发布的还是旧的 dist/ 产物
- **@actions/* 依赖**: AtomGit 不提供 `@atomgit/*` 工具包，需用户自行处理

## 转换报告

转换完成后生成 `CONVERSION_REPORT.md`，包含：

- 兼容性等级
- 修改的文件列表
- 所有替换详情
- 构建/测试状态
- ⚠️ 重建提醒

## 项目结构

```
.
├── convert.py              # 主转换脚本
├── SKILL.md                # 完整转换流程文档
├── CONVERSION_REPORT.md    # 示例转换报告
└── CLAUDE.md               # Claude Code 开发指引
```

## License

MIT
