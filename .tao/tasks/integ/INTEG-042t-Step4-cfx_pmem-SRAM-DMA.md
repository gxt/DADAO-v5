# INTEG-042t: Step 4 落地（cfx_pmem SRAM + DMA）

**模块**：integ
**项目里程碑**：M10
**依赖**：ADR-0042（Accepted）、ADR-0044（fence）、`INTEG-040t`（Step 3）
**状态**：待开始

## 背景

ADR-0042 已改为简化模型：不设 `cfxin/cfxout`，不设 per-cfx DMA；只在 `cfx_pmem`（cfx17）内提供 64 KiB SRAM，DMA 只在 SRAM 与 physical memory 之间搬运；CPU 用 `ld/st` 访问 SRAM，其它 cfx 也由 CPU 直接访问。设备↔pmem 由 CPU 中转；当前单 hart。

## 目标

1. **spec/文档**
   - `cfx5=cache`（原 cfx6 迁入），`cfx6–14/19–61` reserved；同步索引/别名/README。
   - `cfx_pmem`：64 KiB SRAM，内部偏移 0；DMA 寄存器在 cg15：rc0 src、rc1 dst、rc2 size、rc3 ctrl、rc4 status。
   - 地址/长度：src/dst 64 位；方向位 1 位（0=CFX→PA，1=PA→CFX）；CFX 低42、PA低56，高位忽略；size 30 位，1..2^29（512 MiB）。
   - ctrl/status：START/DIR/IRQ_EN；BUSY/DONE/ERROR/ERR_CODE（16 位 one-hot），W1C；PMEM_DMA=1<<8，异步可屏蔽，单 hart 投递 cfx_pmem。
   - 删除 cfxin/cfxout 及旧 crii/64 字节/块选择描述；不新增 DMA ISA 指令。
2. **contracts**
   - cfx aliases/PMEM 寄存器/异常 cause 同步；生成物重算。
3. **QEMU**
   - 实现 cfx_pmem SRAM 窗口、cg15 访问、DMA SRAM↔PA、status/W1C、PMEM_DMA/pending；单 hart；不实现多 hart/设备 DMA。
   - 不实现 cfxin/cfxout 指令。
4. **测试**
   - CPU `ld/st` 访问 cfx_pmem SRAM；
   - DMA 两方向、地址/长度边界、size=0/>512MiB、高位忽略、busy/start 冲突；
   - DONE/ERROR/ERR_CODE/W1C；PMEM_DMA 屏蔽/pending；
   - cfx5 别名/cfx6 reserved；
   - 回归 Step1–3 探针。

## 验收

- `make check`、`make check-modules`、`make check-arch-smoke`、`make check-arch`、`make check-lit`、`check-spec-readonly`、`check-spec-changelog`、`check-patch-tree`、`check-source-state`、`check-cfx-aliases` 全 rc=0。
- 证据 `.work/evidence/<任务号>/run.sh`：注入→FAIL→cp+md5 还原→PASS。
- 不改 multi-hart/设备 DMA/cfx 访问权限；不跑 full/夜跑。
- 完成区 ≤30 行；任务书/里程碑置 `待验收`；临时 `/tmp/opencode/INTEG-042t/`。

## 约束

- 只做 ADR-0042 范围；`cfx_pmem` 是唯一 DMA，CPU 直访其它 cfx。
- 不提交、不 push；重建先申报；失败保留现场。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
