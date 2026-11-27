# m19-testcases-002: ee-tiny 链接与布局迁移（entry 0x2000、256K SRAM、signature 0x1000、DUMP 0x800）

**模块**：testcases
**项目里程碑**：M19
**依赖**：`m19-spec-002`
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：待开始

## 背景

Tiny 新几何（`m19-spec-002`）改动所有测试的入口与运行布局。本任务只迁 `tests/ee-tiny` 侧资产，不改 QEMU/gem5/chipyard 源码。

```
MAIN_SRAM_BASE = 0xFFFF_FF00_0000  SIZE = 0x40000
  0x0000 VERSION（=1）
  0x0020 MAILBOX
  0x0030 EXIT_BLOCK（16 B）
  0x0800 DUMP_BASE，0x800（pt_regs）
  0x1000 SIGNATURE，0x800
  0x2000 ENTRY / raw 基址
  0x38000 guard_lo
  0x39000 STACK（24 KiB，SP=0x3F000）
  0x3F000 MemRAS（4 KiB，MRPTR=0x40000）
image_window = 0x2_0000（128 KiB）
```

## 目标

1. `tests/ee-tiny/runtime.yaml`：`entry=0x2000`、`sp=0x3F000`、`image_window=0x2_0000`、`kernel_base=0x2000`、`kernel_reserved=0`、`exit_block=0x30`、`dump_base=0x800`（新增 `dump_size=0x800`、`signature_base=0x1000` 若 schema 需要）。
2. 再生成 `tests/shared/asm/machine-tiny.inc`；更新全部 `.lds`：`tests_inst_tiny.lds`、`tests_freestanding_tiny.lds`、picolibc tiny lds、`mcmodel_far.lds` 等。
3. `tests/inst` 布局：entry 0x2000；`.faultpad` +0x4000、`.faulttab` +0x4300、`.testdata` +0x5000；`TEST_BUF=0x1000`（固定签名区，0x800）；`TEST_EXITB` 改为全局 `EXIT_BLOCK=0x30`，释放 `ENTRY+0x7800`。
4. `crt0_tiny_freestanding.S` / `crt0_tiny_picolibc.S`：SP=0x3F000、EXIT_BLOCK=0x30；按需要设置 `ra0` 的 `MRPTR=0x40000`（MemRAS 4 KiB）。
5. `tests_inst` 的 `SIG_BEGIN/SIGUPD/SIG_DUMP` 使用固定 0x1000；检查 `TEST_DATA=ENTRY+0x5800` 与签名区不重叠。
6. 更新依赖旧地址的期望值：CFXMEM 边界、fault `cause_info`、`check_tests_index` 假布局、`mcmodel_far`；embench/ansibench 的链接脚本与 image_window 选择。
7. 保持 `tests/ee-tiny` 之外（QEMU/gem5/chipyard）不动。

## 验收（逐条贴真实 rc）

1. 所有 `tests/inst` 代表例可构建并在 QEMU 跑通；`.testdata`/`TEST_BUF`/`EXIT_BLOCK` 地址与 `runtime.yaml` 一致。
2. 签名区在 `0x1000–0x1800`，entry 在 `0x2000`；`TEST_DATA`、faultpad/faulttab 不越界。
3. 栈/guard/MemRAS：`SP=0x3F000`，guard_lo 0x38000–0x39000；若启用 MemRAS，`MRPTR=0x40000`。
4. **可达 FAIL ≥2 路**：① 把 entry 写回 0x10100 ⇒ 构建/装载红；② 把签名区写回 `ENTRY+0x7000` ⇒ 地址断言红。
5. `check-inst-asm` / `check-tests-index` 真实 rc=0（或基线红逐行对照）。

## 约束

独立 `git worktree`；**不提交 git**；只动 `tests/ee-tiny`、`tests/inst` 布局/macros、`tests/shared/asm/machine-tiny.inc` 与链接脚本；不改 QEMU/gem5/chipyard；不接板；完成区不写具体 `.work/**` 路径。
