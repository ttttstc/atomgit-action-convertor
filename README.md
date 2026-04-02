# GitHub Actions → Atomgit Actions 转换器

[English](README_EN.md)

将 GitHub Actions 源码仓库转换为 Atomgit Actions  插件仓库的工具。

## 功能特性

- **环境变量转换** — `GITHUB_*` → `ATOMGIT_*`
- **上下文表达式转换** — `${{ github.* }}` → `${{ atomgit.* }}`（仅限 `${{ }}` 块内）
- **依赖包转换** — `@actions/*` → `@atomgit/*`
- **兼容性扫描** — 自动识别无法自动转换的模式（Octokit 调用、GitHub API 等）

## 支持的 Action 类型

| 类型 | 状态 |
|------|------|
| Node.js (`node12`, `node16`, `node20`) | ✅ 支持 |
| Docker (`runs.using: docker`) | ❌ 暂不支持 |
| Composite (`runs.using: composite`) | ❌ 暂不支持 |

## 兼容性等级

| 等级 | 含义 |
|------|------|
| 🟢 GREEN | 完全可自动转换，无 GitHub API 依赖 |
| 🟡 YELLOW | 含 `@actions/github` — 已转换，需手动适配 |
| 🔴 RED | 含 Octokit/GitHub API 调用 — 已转换，需人工审查 |

## 快速开始

### 安装依赖

无外部依赖，直接运行：

```bash
python convert.py --help
```

### 基本用法

```bash
# 转换仓库
python convert.py --input <源仓库路径> --output <输出路径>

# 预览模式（仅分析，不修改文件）
python convert.py --input <源仓库路径> --output <输出路径> --dry-run
```

### 完整转换流程

```bash
# 1. 转换
python convert.py --input ./my-action --output ./my-action-atomgit

# 2. 安装依赖
cd my-action-atomgit
npm install

# 3. 构建
npm run build
# 或
npx @vercel/ncc build src/index.ts -o dist

# 4. 测试
npm test

# 5. 查看转换报告
cat CONVERSION_REPORT.md

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
...（共 50+ 变量，见 convert.py 第 35 行）
```

### 不会被转换的内容

- ❌ `github.com`、`raw.githubusercontent.com` 等 URL
- ❌ `@actions/github` 导入（保留原样，需手动适配）
- ❌ 用户自定义的 `GITHUB_*` 变量

### 示例

| 原内容 | 转换后 |
|--------|--------|
| `${{ github.token }}` | `${{ atomgit.token }}` |
| `process.env.GITHUB_SHA` | `process.env.ATOMGIT_SHA` |
| `import * as core from '@actions/core'` | `import * as core from '@atomgit/core'` |
| `echo $GITHUB_OUTPUT` | `echo $ATOMGIT_OUTPUT` |

## 转换报告

转换完成后会生成 `CONVERSION_REPORT.md`，包含：

- 兼容性等级
- 修改的文件列表
- 所有替换详情
- 构建/测试状态

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
