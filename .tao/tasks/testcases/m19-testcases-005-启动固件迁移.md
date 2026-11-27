# m19-testcases-005: 启动固件 power/hmon 迁移（8 KiB ROM 可启动）

**模块**：testcases
**项目里程碑**：M19
**依赖**：`m19-spec-002`、`m19-testcases-002`、`m19-testcases-003`、`m19-qemu-001`
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：待开始

## 背景

`m19-testcases-003` 已把 BootROM **构建器**改成 8 KiB 布局，但 `tests/ee-tiny/cfx_power_tiny.S` / `cfx_hmon_tiny.S` 仍是旧固件：

- power 读表 `0xE000`、复制 hmon 源 `0x2000`、跳 `0x10100`；
- hmon 数据槽 `0xD8–0xF8`，与 spec 新 `0xC00–0xCFF` 不一致；且 `rb0 + signed imms12` 到不了 `0xC00`（hmon 仅 `rd63` 一个 scratch）。

结果：新 8 KiB 镜像**结构合法但不可启动**。本任务把固件迁到新布局，并用新 QEMU/gem5/chipyard 验证 `power → hmon → 应用`。

## 目标

1. `cfx_power_tiny.S`：表偏移 `0x1F00`、hmon 源 `0x800`、复制目标 `HMON_SRAM_BASE`、跳 `ENTRY=0x2000`；校验/复制长度/边界按 8 KiB。
2. `cfx_hmon_tiny.S`：数据槽布局定案（`0x0C00` 可行方案 / `0x7C0` / 追加 RB scratch / 收回 spec 分区）；若需改 spec 分区，写入「待裁定」并说明影响。
3. `cfx_power_tiny.lds` / `cfx_hmon_tiny.lds` 与新 BootROM 布局一致；`build_tiny_bootrom.py` 的断言/表项同步。
4. 新 QEMU（qemu-001）、gem5（gem5-002）、chipyard（chipyard-004）跑通同一 8 KiB 镜像：`power → hmon → 应用`，`SYS_EXIT`/签名一致。
5. 不接板；不改 picolibc/arch（归其它任务）。

## 验收（逐条贴真实 rc）

1. 8 KiB BootROM 镜像在新 QEMU 下启动到应用；`power` 的复制/表校验/跳转均有真实日志或探针。
2. hmon 数据槽读写正确；若采用 `0xC00` 之外方案，给出 spec/任务书待裁定与理由。
3. **可达 FAIL ≥2 路**：① 表偏移写回 `0xE000` ⇒ 启动失败；② 跳转写回 `0x10100` ⇒ 启动失败；均需还原回绿。
4. gem5/chipyard 同一镜像跑通；签名/退出码一致（或记录跨任务阻塞）。
5. `check-inst-asm`/`check-tests-index` 真实 rc；基线红逐行对照。

## 约束

独立 `git worktree`；**不提交 git**；只动 `tests/ee-tiny/cfx_power_tiny.*`/`cfx_hmon_tiny.*` 与 `build_tiny_bootrom.py` 必要断言；不改 QEMU/gem5/chipyard 源码；不接板；完成区不写具体 `.work/**` 路径。
