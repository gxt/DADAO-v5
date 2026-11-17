# m14-testcases-008: user 执行环境资产集中到 `tests/ee-user/`

**模块**：testcases
**项目里程碑**：M14
**依赖**：无（纯目录/路径迁移；测试集内容不变）
**可并行分片**：否（跨目录引用唯一）
**预估**：2–3 h
**档位**：中改（迁移 + 引用更新 + 门控回绿）
**状态**：待开始

## 背景（用户 2026-11-17）

`tests/` 下执行环境资产统一用 `ee-` 前缀：`tests/ee-tiny/`（已立 `m14-testcases-007`）、**`tests/ee-user/`**（本任务）、`tests/ee-vast/`（后续）。本任务把 qemu-user / gem5-se 的**脚本、crt、lds、runtime** 集中到 `tests/ee-user/`；**平铺、不建子目录**；测试集目录不移动。

## 目标（迁移清单，共 17 个文件）

**脚本（12）**

1. `tools/testcases/tset/embench/run_embench_user_suite.py`
2. `tools/testcases/tset/libc-test/run_libc_test_user_suite.py`
3. `tools/testcases/tset/libc-test/run_smoke.py`
4. `tools/testcases/tset/llvm-ts/run_llvm_ts_user.py`
5. `tools/testcases/tset/llvm-ts/run_smoke.py`
6. `tools/testcases/tset/llvm-ts/ref_split.py`
7. `tools/testcases/tset/gem5-se-baseline/run_gem5_se_baseline.py`
8. `tools/testcases/tset/gem5-se-baseline/sample_insts.py`
9. `tools/testcases/tset/gem5-se-baseline/make_blocked_case_lists.py`
10. `tools/testcases/tset/gem5-se-baseline/run_engine_ratio.py`
11. `tools/testcases/tset/gem5-se-baseline/run_pool.py`
12. `tools/testcases/parity/se_tset_matrix.py`

**crt / lds / runtime（5）**

13. `tests/shared/crt0/minimal_crt0.s`
14. `tests/shared/runtime/dadao_mem_runtime.ll`
15. `tests/shared/runtime/dadao_user_dyn_probe.c`
16. `tests/shared/linker/dadao-common.lds`
17. `tests/shared/linker/dadao-dyn.lds`

**不移动**：`tests/tset/{embench,libc-test,llvm-ts}/**`（测试集源码/patches）；`tools/testcases/parity/three_platform_matrix.py`、`qemu_gem5_shim.py`（跨 tiny/vast 的三平台差分/桥接）；`tests/arch/**`；`tests/inst/**`；`tests/ee-tiny/**`。

## 引用更新（必须全量 grep）

- `tools/testcases/tset/*/run_smoke.py` 与 suite 驱动自身的 `--help`/默认路径。
- `Makefile` 的 `check-libc-test*`/`check-llvm-ts*`/`check-embench*`/`check-unit`（若引用这些脚本）。
- `tests/README.md`、`tests/INVENTORY.md` 的路径。
- `tools/testcases/check_tests_index.py` 等门控的扫描面。
- 迁移后的脚本要能 `--help` 运行（相对导入/`ROOT` 解析按新位置修正）。

## 验收（逐条贴真实 rc）

1. `git mv` 后旧路径不存在、新路径存在；17 文件 md5 一致。
2. `check-tests-index`、`check-dirs`、`check-no-residue`、`check-run-artifacts` 全 rc=0。
3. 迁移后的 12 个脚本各自 `--help`（或等价轻量入口）可运行；至少 1 个 suite 冒烟（如 `run_smoke.py`）能跑或给出环境 BLOCKED 理由。
4. 1 路注入：引用改回旧路径 ⇒ 门控/脚本红；`cp`+md5 还原 ⇒ 回绿。
5. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树。
2. 只动：上述 17 文件、调用方（`Makefile`/`tools/`/文档/门控扫描面）、本任务书。**不动**测试集内容、`spec/`、`.tao/contracts/`、组件补丁。
3. **不改版本号**；不提交 git；`cp`+md5 还原。
4. 迁移用 `git mv`。

## 待裁定

（无）

## 审阅记录

（待填）
