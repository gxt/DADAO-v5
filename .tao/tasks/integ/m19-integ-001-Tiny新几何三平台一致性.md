# m19-integ-001: Tiny 新几何的三平台一致性（QEMU/gem5/chipyard）

**模块**：integ
**项目里程碑**：M19
**依赖**：`m19-qemu-001`、`m19-gem5-002`、`m19-chipyard-004`、`m19-testcases-002`、`m19-testcases-003`、`m19-testcases-005`、`m19-testcases-006`
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：待开始

## 背景

Tiny 的 ROM/SRAM/hmon/entry/DUMP/signature/stack/MemRAS 全部改了。各模块单独通过后，必须用**同一份**镜像和**同一套**签名/退出判据跑 QEMU、gem5、chipyard，确认三平台逐字节一致，否则 M19 的 FPGA 对照没有基线。

## 目标

0. **先对齐 BootROM 资产**：`m19-chipyard-004` 签入的 `bootrom.tiny.hex` 由旧固件（power 292 B / hmon 48 B）打包；`m19-testcases-005` 换了新固件（power 360 B / hmon 1344 B）后必须用 `m19-testcases-003` 的构建器重新生成并做入库 hex ↔ 镜像双向对账，否则 chipyard 腿跑的是旧固件。
1. 用新几何跑 `tests/inst` 代表例（≥10）、ansibench 四件、embench（至少 O0/O2 代表集）；记录签名/退出码/周期来源。
2. 三平台比对：签名流逐字节；退出码一致；地址类 `cause_info`（CFXMEM 边界）一致。
3. 检查 `entry=0x2000`、signature 0x1000、EXIT 0x30、DUMP 0x800、SP=0x3F000、MemRAS 0x3F000–0x40000 在三平台的实际值一致。
4. 更新 `tests/inst`/`tests/arch` 中因地址变化需要改的期望值；只改证据/期望，不改被测语义。
5. 输出一份三平台差异清单；不能一致的项登记为 issue，不静默跳过。

## 验收（逐条贴真实 rc）

1. 三平台跑同一镜像；签名/退出码逐字节一致（不一致项附最小反例）。
2. DUMP 0x800 的 `pt_regs` 顺序、`rd0/status`、`rb0/ip` 三平台一致。
3. **可达 FAIL ≥2 路**：① 故意改一个期望槽 ⇒ 比对红；② 把某一平台 entry 改回 0x10100 ⇒ 装载/比对红。
4. 门控：`check-inst-asm`、`check-tests-index`、`check-knowledge-refs` 真实 rc；基线红逐行对照。
5. 不改 QEMU/gem5/chipyard/testcases 的语义实现；只做验证/期望修正。

## 约束

独立 `git worktree`；**不提交 git**；不接 FPGA 板；长跑落 PID/日志/`*_EXIT`；完成区不写具体 `.work/**` 路径。
