# TESTCASES-071t: 测试骨架与根级索引（P1，不动文件）

**模块**：testcases
**项目里程碑**：M10
**依赖**：Process-09（草案）
**状态**：已验证

## 目标（P1）
1. 建 `tests/{inst,arch,unit,tset,shared}/`（空目录可留 `.gitkeep`）。
2. 落根级索引 `tests/{inst,arch,unit,tset}.yaml`（字段：`id/file/platforms/level/requires`）+ `tests/README.md` 更新。
3. 新增 L1 门控 `check-tests-index`：ID 唯一、文件存在、字段/平台合法、计数现场派生；`--self-test` 注入→FAIL→还原→PASS。
4. **不移动任何现有文件**；旧门控全部保留。

## 验收
- `make check` rc=0；`check-tests-index` rc=0 且自检可达 FAIL。
- 目录/索引存在；`git status` 证明无测试文件移动。

## 约束
- 只改本任务范围内的 `tests/`、`tools/testcases/`、`Makefile`、索引/`case-ledger`、`milestones.md`；不改 spec/qemu/LLVM 语义。
- **旧路径/旧门控在本任务内保留**（薄 wrapper/别名）；删除旧入口只在 `TESTCASES-076t` 做。
- 不改测试期望、不放宽断言；只做“搬家 + 接线 + 兼容层”。
- 只跑 smoke/定向；全量 `check-full`/夜跑留到 `TESTCASES-076t` 或任务空档。
- 临时目录 `/tmp/opencode/<任务号>/`；不提交。

## 完成区

**测试结果**：证据脚本 9/9 PASS；`make check` rc=0；`make check-tests-index` rc=0；`--self-test` 13 类注入全部可达 FAIL。

**修改文件**：
- 新增 `tests/{inst,arch,unit,tset,shared}/.gitkeep`（5 个 scope 目录）
- 新增 `tests/{inst,arch,unit,tset}.yaml`（空列表 `[]`，含字段/平台注释）
- 新增 `tools/testcases/check_tests_index.py`（L1 门控 + `--self-test`）
- `Makefile`：新增 `check-tests-index`，仅接入 `_locked-check`（L2/L3 不重复）
- `tests/README.md`：新增 §0「四 scope 骨架」（scope/索引字段/生成物目标形状）
- `.tao/knowledge/milestones.md`：TESTCASES-071t 行状态 → `待验收`

**验收结果**（`.work/evidence/TESTCASES-071t/run.sh`，rc=0）：
```
[PASS] 四 scope + shared 目录 | 5 个目录全部存在
[PASS] 四个根级索引存在且为列表
[PASS] make check-tests-index | PASS + 现场计数（inst=0/arch=0/unit=0/tset=0/total=0）
[PASS] check_tests_index --self-test（注入 13 类）| rc=0
[PASS] 接线层（仅 L1）| L1=1 / L2|L3=0
[PASS] make check（L1）| rc=0 + repository checks (L1): PASS
[PASS] 旧测试文件未移动/改名 | status=0 行 / R-A-D=0
[PASS] 注入A 重复ID→FAIL(marker=重复)→cp+md5 还原一致→PASS
[PASS] 注入B file不存在→FAIL(marker=不存在)→cp+md5 还原一致→PASS
```

**新发现/坑**：`tests/` 根下任何 `*.yaml` 都必须是 scope 索引（防 `tests/index/`、`tests/manifest/` 旁路）；`file` 除存在外须为**文件**（指向目录会静默通过存在性检查）。

**遗留问题**：无（迁移/删旧入口/生成物目录落在 `TESTCASES-072t`~`076t`）。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `_check_entry` 返回未使用的 `platforms`、`_SCOPE_DIRS` 死变量 | ✅已修 | 返回值收窄为 `cid`；删除死变量 | `--self-test` rc=0 |
| `file` 指向目录时仅查 `exists()` 会误通过 | ✅已修 | 增 `is_file()` 分支 + 注入⑫ | self-test case14 marker=`不是文件` |
| 空文件索引路径未被基线覆盖 | ✅已修 | 干净基线①的 `inst.yaml` 用空文件 | self-test case1 rc=0 |
| 注入还原是否真回到原字节 | ✅已修 | 证据脚本 `cp` 备份 + 两次 md5 对账 | 注入 A/B 均 `md5=same` |

### 第 1 轮 reviewer 验收（2026-10-27）

**改动范围**：`git show --name-status 75f0b30f` 仅 A/M，无 R/D；`git status --porcelain -uall` 验收前后快照逐行一致（均 0 行），目标文件 md5 验收前后相等（inst=d2441f15 / arch=c940570a，与 commit 内容一致）。

**重跑（reviewer 自己执行）**：
- `make check` → rc=0，`repository checks (L1): PASS`。
- `make check-tests-index` → rc=0，现场计数 inst=0/arch=0/unit=0/tset=0/total=0，`结果: PASS`。
- `python3 tools/testcases/check_tests_index.py --self-test` → rc=0，case1~14 + case-dir 全 PASS，13 类注入各自 rc=1 且 marker 命中（可达 FAIL，非恒真）。
- `bash .work/evidence/TESTCASES-071t/run.sh` → rc=0，checks=9 fails=0，与完成区 9/9 逐条一致。

**独立反例（reviewer 自注入，非复用 engineer）**：
- A（跨条目重复 ID）：`tests/arch.yaml` 写两条 `arch-umon-001` → rc=1，`id=arch-umon-001 重复（已在第 1 条出现）`；`cp` 还原 + md5=same → rc=0 回绿。
- B（file 不存在）：`tests/inst.yaml` 指向 `inst/nonexistent/rev.yaml` → rc=1，`file 不存在`；`cp` 还原 + md5=same → rc=0 回绿。
- 还原全程用 `cp`+md5 对账，未用 git checkout/restore。

**约束核验**：① 未移动/改名现有测试文件（diff 无 R/D）✓；② 门控仅接 L1：`check-tests-index` 只出现在 `.PHONY`/`_locked-check: ...` 与目标定义，L2 `_locked-check-modules`、L3 `_locked-check-full` 均未列入 ✓；③ 旧门控全保留（`check-testcases-suites{,-full}`、`check-case-ledger` 等原样在）✓；④ 索引字段恰五项、scope/平台校验、空索引/空文件合法、计数现场派生（代码 + self-test 双向验证）✓；⑤ 越界：改动仅 `tests/`、`tools/testcases/`、`Makefile`、`tests/README.md`、`milestones.md`、本任务书 ✓；⑥ 临时产物落 `/tmp/opencode/TESTCASES-071t/` ✓。

**判决**：Accepted。

