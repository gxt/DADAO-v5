# m15-testcases-015: 剩余 tiny bootrom 资产集中到 `tests/ee-tiny/`

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m15-testcases-011`/`014`（ee-tiny 已建立；本任务补齐遗漏）
**可并行分片**：否（跨目录引用）
**预估**：1.5–2 h
**档位**：中改
**状态**：待开始

## 背景（用户 2026-11-18）

`tests/shared/bootrom/` 仍残留 tiny 资产未被 011 的清单覆盖。按「tiny 的 bootrom/lds/脚本集中到 `tests/ee-tiny/`」口径补齐。

## 目标（迁移清单，共 11 个文件）

**k0 固件目录（7）**

1. `tests/shared/bootrom/k0/README.md`
2. `tests/shared/bootrom/k0/hmon.S`
3. `tests/shared/bootrom/k0/hmon.lds`
4. `tests/shared/bootrom/k0/smon.S`
5. `tests/shared/bootrom/k0/smon.lds`
6. `tests/shared/bootrom/k0/probe_kernel.S`
7. `tests/shared/bootrom/k0/probe_kernel.lds`

**BootROM 杂项（4）**

8. `tests/shared/bootrom/bootrom.lds`
9. `tests/shared/bootrom/tiny_crt.S`
10. `tests/shared/bootrom/tiny_smoke.S`
11. `tests/shared/bootrom/semihost_msg.inc`

**不移动**：`tests/shared/bootrom/` 下若有其它多机型文件（迁移后复查）；`tests/ee-vast/**`、`tests/ee-user/**`、`tests/inst/**`、`tests/arch/**`。

## 引用更新（全量 grep）

- `tools/linux/check_k1.py`、`tools/qemu/k0_boot_probe.py`、`tools/linux/semihost_pa_probe.{S,lds}`、`tools/linux/semihost_readc_probe.S`、`tools/linux/check_k0.py` 等（`bootrom/k0` 路径）。
- `tests/ee-tiny/semihost_smoke.S`、`tests/ee-tiny/run_semihosting_smoke.py`（`semihost_msg.inc`）。
- `Makefile`（`build-bootrom` 的 `k0`/`bootrom.lds` 路径）。
- `tests/README.md`、`tests/INVENTORY.md`、`tests/shared/README.md`。
- 迁移后 `k0/hmon.S` 的 `OPEN_SUPV_ALL`/`K2_TIME_PERM` 引用与 `m14-testcases-006` 的 md5 记录保持一致（**不改内容**，只改路径）。

## 验收（逐条贴真实 rc）

1. `git mv` 后旧路径 0、新路径 11 文件齐；内容逐字节一致（md5 对账；`k0/hmon.S` 与 `m14-testcases-006` 的 bootrom md5 `b662183a` 构建结果一致）。
2. `make build-bootrom` rc=0（K0/K1 镜像 md5 不变）；`check-linux-k0`（119/119）、`check-linux-k1`（112/112）rc=0。
3. `check-tests-index`、`check-dirs`、`check-no-residue`、`check-interface` 全 rc=0。
4. 1 路注入：引用改回旧路径 ⇒ 构建/门控红；`cp`+md5 还原回绿。
5. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树。
2. 只动：11 文件 + 调用方/文档 + 本任务书；**不动**测试集内容、`spec/`、`.tao/contracts/`、组件补丁。
3. **不改版本号**；不提交 git；`cp`+md5 还原。
4. 迁移用 `git mv`。

## 待裁定

（无）

## 审阅记录

（待填）
