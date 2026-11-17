# m15-testcases-013: vast 执行环境资产集中到 `tests/ee-vast/`

**模块**：testcases
**项目里程碑**：M15
**依赖**：无（纯目录/路径迁移；测试集内容不变）
**可并行分片**：否（跨目录引用唯一）
**预估**：1.5–2 h
**档位**：中改（迁移 + 引用更新 + 门控回绿）
**状态**：待开始

## 背景（用户 2026-11-18）

执行环境资产统一 `ee-` 前缀：`tests/ee-tiny/`（已收尾 `m15-testcases-011`）、`tests/ee-user/`（已收尾 `m15-testcases-012`）、**`tests/ee-vast/`**（本任务）。平铺、不建子目录；测试集目录不动。

## 目标（迁移清单，共 8 个文件）

**BootROM（7）**

1. `tests/shared/bootrom/step5/power.S`
2. `tests/shared/bootrom/step5/hmon.S`
3. `tests/shared/bootrom/step5/smon.S`
4. `tests/shared/bootrom/step5/power.lds`
5. `tests/shared/bootrom/step5/hmon.lds`
6. `tests/shared/bootrom/step5/smon.lds`
7. `tests/shared/bootrom/step5/README.md`

**LDS（1）**

8. `tests/shared/linker/kaiwu-vast.lds`

**不移动**：`tests/arch/**`（Vast 测试集与探针驱动）、`tests/inst/**`、`tests/tset/**`、`tests/unit/**`、`tests/shared/{asm,crt0,runtime,init}`、`tests/shared/bootrom/{bootrom.lds,tiny_crt.S,tiny_smoke.S,semihost_msg.inc}`（tiny 残留/共享）。

## 引用更新（全量 grep）

- `Makefile` 的 `build-bootrom`（step5 路径）、`check-arch` 相关。
- `tools/testcases/arch/node_probe_prelude.py`、`min_rom_probe_integ046t.py`、`run_m5_e2e.py`、`tools/testcases/parity/run_parity.py`、`tools/testcases/check_tests_index.py`（`power_lds` 路径）、`tools/infra/check_interface_alignment.py`。
- `tests/README.md`、`tests/INVENTORY.md`、`tests/arch/umon/expected.yaml`（若含路径）。
- 迁移后 `--help`/轻量入口可运行。

## 验收（逐条贴真实 rc）

1. `git mv` 后旧路径不存在、新路径 8 文件齐；内容逐字节一致（md5 对账）。
2. `make build-bootrom` rc=0；Vast bootrom 镜像 md5 与迁移前一致（记录）。
3. `check-tests-index`、`check-dirs`、`check-no-residue`、`check-arch-smoke`（或等价）rc=0。
4. 1 路注入：引用改回旧路径 ⇒ 构建/门控红；`cp`+md5 还原回绿。
5. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树。
2. 只动：上述 8 文件、调用方（`Makefile`/`tools/`/文档/门控扫描面）、本任务书。**不动**测试集内容、`spec/`、`.tao/contracts/`、组件补丁。
3. **不改版本号**；不提交 git；`cp`+md5 还原。
4. 迁移用 `git mv`。

## 待裁定

（无）

## 审阅记录

（待填）
