# Conversion Report: test-action

**Compatibility Rating**: YELLOW
**Build Status**: pending
**Test Status**: pending

## Entry Points

- **using**: `node20`
- **main**: `dist/index.js`
- **post**: `dist/cleanup.js`

## Compatibility Issues

- 🟡 **YELLOW** `package.json:0` — Incompatible dependency: @actions/github
  ```
  @actions/github: ^6.0.0
  ```

## Files Modified

**Total replacements**: 18

- `action.yml`: 2 change(s)
- `package.json`: 3 change(s)
- `src/cleanup.ts`: 3 change(s)
- `src/index.ts`: 10 change(s)

## Replacement Details

### `action.yml:6` (action.yml expression/env)
```diff
- default: ${{ github.token }}
+ default: ${{ atomgit.token }}
```

### `action.yml:9` (action.yml expression/env)
```diff
- default: ${{ github.repository }}
+ default: ${{ atomgit.repository }}
```

### `package.json:0` (dependencies replacement)
```diff
- @actions/core: ^1.10.0
+ @atomgit/core: ^1.10.0
```

### `package.json:0` (dependencies replacement)
```diff
- @actions/exec: ^1.1.1
+ @atomgit/exec: ^1.1.1
```

### `package.json:0` (dependencies replacement)
```diff
- @actions/io: ^1.1.3
+ @atomgit/io: ^1.1.3
```

### `src/index.ts:1` (source code)
```diff
- import * as core from '@actions/core';
+ import * as core from '@atomgit/core';
```

### `src/index.ts:2` (source code)
```diff
- import * as exec from '@actions/exec';
+ import * as exec from '@atomgit/exec';
```

### `src/index.ts:6` (source code)
```diff
- const token = process.env.GITHUB_TOKEN;
+ const token = process.env.ATOMGIT_TOKEN;
```

### `src/index.ts:7` (source code)
```diff
- const workspace = process.env['GITHUB_WORKSPACE'];
+ const workspace = process.env['ATOMGIT_WORKSPACE'];
```

### `src/index.ts:8` (source code)
```diff
- const { GITHUB_SHA, GITHUB_REF } = process.env;
+ const { ATOMGIT_SHA, ATOMGIT_REF } = process.env;
```

### `src/index.ts:10` (source code)
```diff
- core.info(`SHA: ${GITHUB_SHA}`);
+ core.info(`SHA: ${ATOMGIT_SHA}`);
```

### `src/index.ts:11` (source code)
```diff
- core.info(`Ref: ${process.env.GITHUB_REF_NAME}`);
+ core.info(`Ref: ${process.env.ATOMGIT_REF_NAME}`);
```

### `src/index.ts:15` (source code)
```diff
- await exec.exec('bash', ['-c', `echo "result=success" >> $GITHUB_OUTPUT`]);
+ await exec.exec('bash', ['-c', `echo "result=success" >> $ATOMGIT_OUTPUT`]);
```

### `src/index.ts:16` (source code)
```diff
- await exec.exec('bash', ['-c', `echo "DEPLOY=true" >> $GITHUB_ENV`]);
+ await exec.exec('bash', ['-c', `echo "DEPLOY=true" >> $ATOMGIT_ENV`]);
```

### `src/index.ts:18` (source code)
```diff
- const repoUrl = `${process.env.GITHUB_SERVER_URL}/${process.env.GITHUB_REPOSITORY}`;
+ const repoUrl = `${process.env.ATOMGIT_SERVER_URL}/${process.env.ATOMGIT_REPOSITORY}`;
```

### `src/cleanup.ts:1` (source code)
```diff
- import * as core from '@actions/core';
+ import * as core from '@atomgit/core';
```

### `src/cleanup.ts:4` (source code)
```diff
- core.info(`Cleaning up in ${process.env.GITHUB_WORKSPACE}`);
+ core.info(`Cleaning up in ${process.env.ATOMGIT_WORKSPACE}`);
```

### `src/cleanup.ts:5` (source code)
```diff
- core.info(`Run ID: ${process.env["GITHUB_RUN_ID"]}`);
+ core.info(`Run ID: ${process.env["ATOMGIT_RUN_ID"]}`);
```
