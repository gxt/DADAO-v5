# m19-gem5-002: gem5 Tiny 新几何与装载（8K ROM / 8K hmon / 256K SRAM）

**模块**：gem5
**项目里程碑**：M19
**依赖**：`m19-spec-002`
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：待开始

## 背景

gem5 的 Tiny profile 仍按 64 KiB BootROM / 8 MiB SRAM / 64 KiB hmon。Tiny 新几何（`m19-spec-002`）为：ROM 8 KiB、SRAM 256 KiB、hmon 8 KiB、entry `MAIN_SRAM_BASE+0x2000`、raw 基址 `0x2000`、DUMP 0x800（pt_regs）、SIGNATURE 0x1000、EXIT 0x30、MAILBOX 0x20、STACK 0x39000–0x3F000、MemRAS 0x3F000–0x40000。

## 目标

1. `configs/dadao/fs.py --profile tiny`：BootROM 8 KiB、RAM 256 KiB、hmon 8 KiB、reset/entry/raw 基址按新几何。
2. 装载：BootROM 镜像 8 KiB；应用 ELF/raw 只落 `0x2000` 起 SRAM；`e_entry=0x2000`；禁止写 header/BootROM/hmon。
3. 头区与 DUMP：`VERSION/MAILBOX/EXIT` 地址；DUMP 0x800 四组 `rd/rb/ra/rf` 按 `pt_regs` 顺序，`rd0=status`、`rb0=ip`。
4. 同步 gem5 侧探针/配置中的旧地址；不改 QEMU/chipyard。
5. 不影响既有 `m19-gem5-001`（swym）范围。

## 验收（逐条贴真实 rc）

1. `make build-gem5` rc=0；`check-gem5-decode` / `check-wuming-cycles` 真实 rc（基线红逐行对照）。
2. gem5 FS Tiny 跑通 power→hmon→应用；`tests/inst` 代表例通过，地址类期望按新几何。
3. DUMP 0x800 读回四组，`rd0/status`、`rb0/ip` 正确。
4. **可达 FAIL ≥2 路**：① RAM 写回 8 MiB ⇒ 边界/尺寸用例红；② entry 写回 0x10100 ⇒ 装载用例红。
5. 不改 QEMU/chipyard；不接板。

## 约束

独立 `git worktree`；**不提交 git**；只动 gem5 组件/补丁与 profile；完成区不写具体 `.work/**` 路径。
