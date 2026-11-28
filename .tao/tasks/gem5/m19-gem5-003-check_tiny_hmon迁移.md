# m19-gem5-003: `check_tiny_hmon` 迁移到 Tiny 新几何与 hmon 数据区

**模块**：gem5
**项目里程碑**：M19
**依赖**：`m19-gem5-002`、`m19-testcases-002`、`m19-testcases-003`、`m19-testcases-005`
**可并行分片**：否
**预估**：2–4 h
**档位**：小改
**状态**：待开始

## 背景

`tests/unit/gem5/check_tiny_hmon.py` 及其资产（`tiny_hmon.S`、`expected.yaml`、`tiny_hmon_layout.inc`）仍按旧 Tiny 几何与被测固件约定写：

- 旧 64 KiB BootROM、8 MiB SRAM、入口 `0x10100`、表偏移 `0xE000`、`0x30001` 表头；
- hmon 数据槽 `0xD8/0xE0/0xE8/0xF0/0xF8`（spec 新数据区为 `0x0C00–0x0CFF`）。

`m19-gem5-002` 已把 gem5 Tiny profile 迁到新几何；`m19-testcases-002` 已改 `tiny_hmon.lds`；`m19-testcases-003` 已改 BootROM 构建器（表 `0x1F00`）；`m19-testcases-005` 定义 hmon 数据区子偏移。本任务把该 harness 与资产迁齐，使 `make check-tiny-hmon` 在新几何下真实跑通。

## 目标

1. `check_tiny_hmon.py`：BootROM 大小/表偏移/表头、SRAM 大小、入口 `0x2000`、DUMP `0x800`、image_window 128 KiB 全部按 profile/构建器现场取值，删除硬编码旧值。
2. hmon 数据区按 `m19-testcases-005` 定稿的 `0x0C00–0x0CFF` 子偏移；`tiny_hmon_layout.inc` / `expected.yaml` / `tiny_hmon.S` 与之逐项一致。
3. `tiny_hmon.S` 的 `escape` 语法漂移（LLVM 下无法汇编）如仍存在，按现行语法修好，或在本任务内明确记为依赖项（不得静默跳过）。
4. 运行：`make check-tiny-hmon`（或等价）在 gem5 新 profile 下 rc=0；`power → hmon → 应用` 与 CFXESC 帧两条路径都覆盖。

## 验收（逐条贴真实 rc）

1. `make build-gem5` rc=0；`make check-tiny-hmon` rc=0。
2. 镜像恰 8192 B；表项 `offset=0x800`、`size ≤ 0x0C00`；入口/DUMP/签名/EXIT 地址与 spec 一致。
3. hmon 数据槽读回：cause_id / cause_ip / cause_info / 返回地址 / 保存的 scratch 原值。
4. **可达 FAIL ≥2 路**：① 表偏移写回 `0xE000` ⇒ 红；② hmon 数据槽写回 `0xD8` ⇒ 红；均 `cp`+md5 还原回绿。
5. `check-tests-index` / `check-patch-tree`（gem5 段）真实 rc；基线红逐行对照。
6. 不改 QEMU/chipyard/testcases 固件；版本号未升。

## 约束

独立 `git worktree`；**不提交 git**；只动 `tests/unit/gem5/**` 与必要索引；不接板；完成区不写具体 `.work/**` 路径。
