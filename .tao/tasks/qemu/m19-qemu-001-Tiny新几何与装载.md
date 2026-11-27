# m19-qemu-001: QEMU Tiny 新几何与装载（8K ROM / 8K hmon / 256K SRAM）

**模块**：qemu
**项目里程碑**：M19
**依赖**：`m19-spec-002`
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：待开始

## 背景

QEMU 的 `kaiwu-tiny` 仍按 64 KiB BootROM / 8 MiB SRAM / 64 KiB hmon 建模。Tiny 新硬件几何（`m19-spec-002`）为：ROM 8 KiB、SRAM 256 KiB、hmon 8 KiB、entry `MAIN_SRAM_BASE+0x2000`、raw 基址 `0x2000`、DUMP 0x800（pt_regs）、SIGNATURE 0x1000、EXIT 0x30、MAILBOX 0x20、STACK 0x39000–0x3F000、MemRAS 0x3F000–0x40000。

## 目标

1. `-M kaiwu-tiny`：bootrom 8 KiB、RAM 256 KiB、hmon 8 KiB；reset PC 仍 `0xFFFF_FFFF_0000`。
2. `bootrom-image` / legacy `-bios`：镜像恰好 8 KiB；QEMU 原样装入，不按应用 `e_entry` 改写。
3. `-kernel`（raw/ELF）：只接受 `0x2000` 起的 SRAM 段；raw 基址 `0x2000`、`e_entry=0x2000`；禁止 PT_LOAD 到 header/BootROM/hmon。
4. 头区：`VERSION=0x0000`、`MAILBOX=0x0020`、`EXIT_BLOCK=0x0030`；按新地址建模。
5. DUMP：`DUMP_BASE=0x0800`、`DUMP_SIZE=0x800`，四组 `rd/rb/ra/rf` 顺序与 `pt_regs` 一致；`rd[0]=status`、`rb[0]=ip`。
6. 更新 QEMU 侧探针/驱动中的旧地址；不改 gem5/chipyard。

## 验收（逐条贴真实 rc）

1. QEMU 跑通 `power → hmon → 应用`；`tests/inst` 代表例与旧基线语义一致（地址类期望按新几何更新）。
2. 镜像/入口校验：错误 `bootrom` 大小、`e_entry≠0x2000`、PT_LOAD 越界均显式失败，不静默。
3. DUMP 0x800：按 `pt_regs` 偏移读回四组；`rd0/status`、`rb0/ip` 正确。
4. **可达 FAIL ≥2 路**：① 把 RAM 改回 8 MiB ⇒ 尺寸/边界用例红；② 把 entry 改回 0x10100 ⇒ 装载校验红。
5. `make check-qemu-semantics` / `check-interface` 真实 rc（基线红逐行对照）。

## 约束

独立 `git worktree`；**不提交 git**；只动 QEMU 组件/补丁与 QEMU 侧工具；不改 gem5/chipyard；不接板；完成区不写具体 `.work/**` 路径。
