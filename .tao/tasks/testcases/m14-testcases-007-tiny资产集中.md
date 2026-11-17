# m14-testcases-007: tiny 资产集中到 `tests/ee-tiny/`（脚本 + bootrom + lds）

**模块**：testcases
**项目里程碑**：M14
**依赖**：无（纯目录/路径迁移；测试集内容不变）
**可并行分片**：否（跨目录引用唯一）
**预估**：2–3 h
**档位**：中改（迁移 + 引用更新 + 门控回绿）
**状态**：待开始

## 背景（用户 2026-11-17 指示）

把 kaiwu-tiny 专属的**脚本、bootrom、lds** 集中到 `tests/ee-tiny/`；**不建子目录**（平铺，文件名说明用途）；**测试集不移动**（`tests/inst`、`tests/tset`、`tests/unit` 原地不动）。

## 目标（迁移清单，共 17 个文件）

**脚本（4）**

1. `tools/testcases/inst/run_asm_suite.py`
2. `tools/testcases/picolibc_tests.py`
3. `tools/testcases/tset/embench/run_embench_e2e.py`
4. `tools/linux/run_semihosting_smoke.py`

**BootROM（10）**

5. `tests/shared/bootrom/tiny/power.S`
6. `tests/shared/bootrom/tiny/hmon.S`
7. `tests/shared/bootrom/tiny/tiny_common.inc`
8. `tests/shared/bootrom/tiny/power.lds`
9. `tests/shared/bootrom/tiny/hmon.lds`
10. `tests/shared/bootrom/bootrom.S`
11. `tests/shared/bootrom/bootrom_app.S`
12. `tests/shared/bootrom/semihost_smoke.S`
13. `tests/shared/bootrom/tiny_smoke.lds`
14. `tests/shared/bootrom/semihost_smoke.lds`

**LDS（3）**

15. `tests/shared/linker/kaiwu-tiny.lds`
16. `tests/shared/linker/kaiwu-tiny-app.lds`
17. `tests/shared/linker/picolibc-tiny.ld`

**不移动**：`tests/inst/linker/inst-tiny.lds`（属 inst 测试集布局，测试集不动）；`tests/shared/bootrom/step5/**`（Vast）；`tests/shared/linker/dadao-*.lds`、`kaiwu-vast.lds`（多机型/其它）；`tests/unit/picolibc/**`、`tests/tset/**`、`tests/inst/**`。

**迁移后目录**：`tests/ee-tiny/` 平铺上述 13 个 bootrom/lds 文件（脚本 4 个也放 `tests/ee-tiny/`，按用户指示）。

## 引用更新（必须全量 grep，不得漏）

- `Makefile`：`build-bootrom` 目标与 `BOOTROM_*` 变量、`build-picolibc`、相关门控的路径。
- `tools/`：`check_tests_index.py`、`check_inst_*`/`check_asm_*`、`picolibc_tests.py`、`run_asm_suite.py`、`run_embench_e2e.py`、`run_semihosting_smoke.py` 自身及调用方。
- `tests/README.md`、`tests/INVENTORY.md`、`tests/inst/README.md` 等文档中的路径。
- 门控扫描面（`check-dirs`、`check-no-residue`、`check-inst-macro-scope`、`check-run-artifacts` 等）若按目录枚举，需同步。

## 验收（逐条贴真实 rc）

1. `git mv` 后旧路径不存在、新路径存在；17 个文件内容逐字节不变（md5 对账）。
2. `make build-bootrom` rc=0；tiny bootrom md5 与迁移前一致。
3. `check-inst-asm` **272/272**（测试集未动）；`check-tests-index`、`check-case-ledger`、`check-inst-macro-scope`、`check-dirs`、`check-no-residue` 全 rc=0。
4. `python3 tests/ee-tiny/run_asm_suite.py --help`、`python3 tests/ee-tiny/picolibc_tests.py --list`（或等价轻量路径）可运行；`run_embench_e2e.py --help`、`run_semihosting_smoke.py --help` 可运行。
5. 1 路注入：把引用改回旧路径 ⇒ 对应门控/构建红；`cp`+md5 还原 ⇒ 回绿。
6. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树。
2. 只动：上述 17 文件、调用方（`Makefile`/`tools/`/文档/门控扫描面）、本任务书。**不动**测试集内容、`spec/`、`.tao/contracts/`、组件补丁。
3. **不改版本号**；不提交 git；`cp`+md5 还原。
4. 迁移用 `git mv`（保留历史）。

## 待裁定

（无）

## 审阅记录

（待填）
