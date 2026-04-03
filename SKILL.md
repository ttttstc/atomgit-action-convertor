---
name: github-to-codearts-action
description: >
  Convert GitHub Actions plugins to CodeArts Actions (AtomGit) plugins by transforming
  environment variable prefixes (GITHUB_* → ATOMGIT_*) and context expressions
  (github.* → atomgit.*). Use this skill whenever the user wants to: migrate a GitHub
  Action to CodeArts/AtomGit, convert action.yml or plugin source code from GITHUB_
  to ATOMGIT_ conventions, adapt Node-based GitHub Actions (node12/node16/node20) for
  the CodeArts pipeline platform, or analyze a GitHub Action's compatibility with
  CodeArts. Also trigger when the user mentions "插件转换", "插件迁移",
  "CodeArts插件","CodeArts兼容", "AtomGit插件", or asks about converting between
  GitHub Actions and CodeArts Actions ecosystems.

  NOTE: This converter does NOT replace @actions/* packages. Users must maintain
  their own AtomGit-compatible toolkit packages.
---

# GitHub Actions → AtomGit 插件转换

此 skill 将 **GitHub Actions 源码仓库** 转换为 **AtomGit (CodeArts Actions) 插件仓库**。
输入为包含 `action.yml`、`package.json`、`src/` 等的完整 GitHub Action 源码仓库，
输出为结构相同但已完成变量名转换的 AtomGit 插件仓库，可直接推送发布。

两个插件系统共享相同的结构定义（action.yml schema），仅运行时命名约定不同。
此 skill 处理完整的仓库级转换流程：兼容性评估、源码转换、重建、验证。

## 转换前评估（推荐先执行）

在真正转换之前，**强烈建议**先执行兼容性评估：

```bash
python convert.py --input <source-repo> --evaluate-only
```

这将输出转换可行性评估报告，明确告诉用户：
- ✅ **GREEN**: 可完全自动转换
- ⚠️ **YELLOW**: 可转换，但需手动适配（如 @actions/* 依赖）
- ❌ **RED**: 无法自动转换，需先处理问题

## 支持的 Action 类型

**支持**: Node-based actions (`runs.using: node12 | node16 | node20`)

**不支持**:
- Docker-based actions (`runs.using: docker`)
- Composite actions (`runs.using: composite`)

## 兼容性等级

| 等级 | 含义 |
|------|------|
| 🟢 GREEN | 可完全自动转换，无需人工介入 |
| 🟡 YELLOW | 含 @actions/* 依赖，转换后需手动替换为 AtomGit 方案 |
| 🔴 RED | 含 Octokit/GitHub API 调用，需重新实现相关逻辑 |

## 转换管道

按顺序执行以下步骤。任意步骤失败则停止并报告。

### Step 1 — 仓库分析与兼容性扫描

输入 GitHub Actions 源码仓库：

1. **定位入口定义**: 在仓库根目录查找 `action.yml` 或 `action.yaml`
2. **验证插件类型**: 读取 `runs.using` — 必须为 `node12`、`node16` 或 `node20`
3. **记录入口点**: 提取 `runs.main`、`runs.pre`（可选）、`runs.post`（可选）
4. **验证源码结构**: 确认 `package.json` 存在，确认源码目录存在
5. **初始化输出仓库**: 复制整个源码仓库（排除 `node_modules/`、`.git/`、`dist/`）
6. **扫描兼容性问题**: 扫描源码树，检测不可转换模式

### Step 2 — action.yml 转换

读取白名单中的变量映射。

**表达式替换规则（仅在 `${{ }}` 块内）:**
1. 提取所有 `${{ ... }}` 表达式块
2. 区分标识符和字符串字面量
3. 将标识符路径上的 `github.` 前缀 → `atomgit.`（仅第一段）
   - `github.event.pull_request.head.sha` → `atomgit.event.pull_request.head.sha`
   - `github.token` → `atomgit.token`
4. **不替换**字符串字面量中的 `github`（如 `'https://github.com'` 保持不变）
5. **不替换** `${{ }}` 块外的 `github`

**环境变量替换（`env:`、`with:`、`defaults:` 块中）:**
- 仅替换白名单中的 `GITHUB_*` → `ATOMGIT_*`
- 不使用盲替换 `s/GITHUB_/ATOMGIT_/g`，始终与白名单匹配

### Step 3 — 源码转换

扫描 `src/` 下的所有 `.ts` 和 `.js` 文件。

**Rule 3a — process.env 直接访问（仅白名单）:**
```
process.env.GITHUB_TOKEN       → process.env.ATOMGIT_TOKEN
process.env['GITHUB_SHA']      → process.env['ATOMGIT_SHA']
process.env["GITHUB_REF"]      → process.env["ATOMGIT_REF"]
```

**Rule 3b — process.env 解构（仅白名单）:**
```
const { GITHUB_TOKEN, GITHUB_SHA } = process.env
→ const { ATOMGIT_TOKEN, ATOMGIT_SHA } = process.env
```

**Rule 3c — 模板字符串中的 Shell 变量（仅白名单）:**
```
`echo $GITHUB_SHA`             → `echo $ATOMGIT_SHA`
`cat $GITHUB_EVENT_PATH`       → `cat $ATOMGIT_EVENT_PATH`
```

**全局排除 — URL 模式永不替换:**
- `github.com`、`github.io`、`raw.githubusercontent.com`
- 任何 `https://...github...` URL 模式

### Step 4 — 重建

⚠️ **必须重建**：转换源码后，必须重新构建 dist/ bundle

1. 根据 `runs.using` 确定 Node 版本
2. 运行 `npm install`
3. 识别构建命令：
   - 若 `package.json` 有 `scripts.build` → 执行它
   - 若 `package.json` 有 `scripts.package` → 执行它
   - 否则 → 对每个入口点执行 `npx @vercel/ncc build <entry> -o dist --source-map --license licenses.txt`
4. 验证构建成功（exit code 0）

### Step 5 — 验证

1. **构建产物检查**: 确认每个入口点文件存在于 `dist/`
2. **泄漏检查**: 在 `dist/` 中搜索残留的 `GITHUB_` 引用
3. **测试执行**: 若有 `scripts.test`，运行 `npm test`
4. **生成转换报告**: 输出包含文件修改列表、变量替换、兼容性问题的报告

## 输出结构

```
<plugin-name>-atomgit/
├── action.yml              # 已转换
├── package.json            # 保留原样（@actions/* 依赖需手动处理）
├── src/                    # 源码已转换
│   └── *.ts / *.js
├── dist/                   # 重新构建的产物
│   ├── index.js            # main 入口
│   ├── setup.js            # pre 入口（若存在）
│   └── cleanup.js          # post 入口（若存在）
├── LICENSE                 # 保留
├── README.md               # 保留
└── CONVERSION_REPORT.md    # 生成的转换报告
```

## 重要原则

1. **白名单机制**: 所有 GITHUB_ → ATOMGIT_ 替换都经过白名单验证，
   用户自定义的 GITHUB_* 变量不会被触碰。

2. **源码级重建**: 始终从源码工作，不从预构建的 `dist/` bundle 补丁。
   dist/ bundle 内联了所有依赖，无法可靠地打补丁。

3. **保留语义**: 这是命名约定的迁移，不是逻辑重写。
   如果任何转换会改变程序行为（超出变量命名范围），标记为需人工审查。

4. **失败上报**: 如果转换脚本遇到无法自信分类的歧义模式，
   记录 WARNING 并包含在转换报告中，而不是静默猜测。

## ⚠️ @actions/* 依赖处理

**AtomGit 不提供 `@atomgit/*` 工具包。**

转换后，用户必须：
1. 自行维护一套 `@atomgit/*` 包，或
2. 替换为 AtomGit 平台提供的等效方案

所有 `@actions/*` 依赖会在评估报告中标记为 YELLOW 项。

## 快速开始

```bash
# 1. 先评估（推荐）
python convert.py --input ./my-action --evaluate-only

# 2. 确认后执行转换
python convert.py --input ./my-action --output ./my-action-atomgit

# 3. 处理 @actions/* 依赖（手动）
# 编辑 package.json 和源码，替换为 AtomGit 方案

# 4. 重建（必须）
cd my-action-atomgit
npm install
npm run build

# 5. 测试并推送
npm test
git init && git add . && git commit -m "Convert to AtomGit"
```
