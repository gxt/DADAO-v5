# m19-spec-002: Tiny 硬件几何与启动 ABI（8K ROM / 8K hmon / 256K SRAM）

**模块**：spec
**项目里程碑**：M19
**依赖**：无
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：待开始

## 背景

用户 2026-11-27 定稿 Tiny 的硬件几何与软件布局；本任务把地址、尺寸、启动 ABI 写入 spec/契约，作为 QEMU/gem5/chipyard/testcases 的共同真源。

```
BOOT_ROM_BASE  = 0xFFFF_FFFF_0000  SIZE = 0x2000（8 KiB）
  power      0x0000–0x07FF（≤2 KiB）
  hmon 源    0x0800–0x13FF（≤3 KiB）
  table      0x1F00–0x1F2F（48 B）

HMON_SRAM_BASE = 0x0FFF_0000_0000  SIZE = 0x2000（8 KiB）
  code       0x0000–0x0BFF（≤3 KiB）
  data       0x0C00–0x0CFF（256 B）
  stack      0x0D00–0x1FFF（SP = 0x2000）

MAIN_SRAM_BASE = 0xFFFF_FF00_0000  SIZE = 0x40000（256 KiB）
  0x0000  VERSION（=1，loader 写）
  0x0020  MAILBOX（8 B）
  0x0030  EXIT_BLOCK（16 B；code 在 +0x38）
  0x0800  DUMP_BASE，DUMP_SIZE = 0x800（pt_regs 顺序）
  0x1000  SIGNATURE，0x800
  0x2000  ENTRY / raw 镜像基址
  0x38000 guard_lo
  0x39000 STACK，24 KiB，SP = 0x3F000
  0x3F000 MemRAS，4 KiB，MRPTR = 0x40000
```

- `DUMP_BASE` 四段：`rd[64]`@+0x000（rd0=status）、`rb[64]`@+0x200（rb0=ip）、`ra[64]`@+0x400、`rf[64]`@+0x600，总计 0x800。
- `image_window = 0x2_0000`（128 KiB）；`kernel_base = MAIN_SRAM_BASE+0x2000`、`kernel_reserved = 0`。
- MemRAS 与 Stack 之间**不设 guard_hi**（用户 2026-11-27 接受 4 KiB MemRAS 预算）；guard_lo 只挡栈溢出。
- `VERSION=1` 由 loader 写；power 必须同时检查 VERSION 与 MAILBOX magic 才放核。

## 目标

1. `spec/Kaiwu §1.1/§6/§6.2` 写入上表与启动/装载 ABI；删除 64 KiB BootROM、8 MiB SRAM、64 KiB hmon 的旧口径。
2. `contracts/machine.yaml` 的 `tiny.bootrom.size=0x2000`、`tiny.ram.size=0x40000`。
3. 明确 hmon 4 KiB→8 KiB、Boot ROM 布局、DUMP/signature/EXIT/MAILBOX 的角色与大小。
4. 版本号升级（spec/contracts）**待用户确认**；未确认前只落内容、不升号。

## 验收（逐条贴真实 rc）

1. `check-spec-refs` / `check-spec-numbering` / `check-contract-*` 真实 rc=0（基线红给逐行对照）。
2. 新表中所有地址/大小可 grep；`DUMP_BASE+0x800`、`SIGNATURE+0x800`、`ENTRY=0x2000` 与 `pt_regs` 偏移一致。
3. **可达 FAIL ≥2 路**：① 把 `BOOT_ROM_SIZE` 写回 64 KiB ⇒ 契约/派生检查红；② 把 `ENTRY` 写成 `0x100` ⇒ 交叉核对红。
4. 不改 QEMU/gem5/chipyard/testcases 源码；不升版本号（除非用户当轮确认）。

## 约束

独立 `git worktree`；**不提交 git**；只动 `spec/Kaiwu*`、`contracts/machine.yaml` 与必要索引；完成区不写具体 `.work/**` 路径。
