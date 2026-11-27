# M16 回顾（gem5 Timing / chipyard wuming 与 `tests/arch` 三方载体）

> **达成**：2026-11-27 ｜ **册数**：95（见 `README.md` §1）｜ **关闭 issue**：56（见 `issues-closed.md`）

## 1. 目标与范围

- **目标（用户 2026-11-19）**：对齐 `gem5` 的 `TimingSimpleCPU` 与 `chipyard-wuming`（RTL），覆盖 `tiny` 与 `vast` 两个机型。
- **定位（用户 2026-11-13）**：只做 **Timing**（`Minor`/`O3` 等 `wuqing`/`wuxing` RTL 出现后再开）；gem5 `TimingSimpleCPU` 保持原样，只加「每指令延迟」钩子（默认 0）。
- **范围扩展（用户 2026-11-16）**：ISA 语义对齐（`ADR-0056` 子原因编码、`DADAO-12 §5.2` 同步异常路由），编号沿用 `m16-<module>-NNN`，与时序模型口径分开统计。

## 2. 实际交付

- **gem5 侧（27 册）**：Timing 钩子与周期模型、Tiny/Vast 机型面、cfx 寄存器面与异常、PTW/TLB、pmem、power、time、异步 escape 出口帧与源接口（与 M18 对齐）。
- **chipyard / RTL 侧（31 册）**：`dadao-gewu` 独立 generator、cfx 面（cfx0/2/3/5/15/32/34/63）、PTW/TLB、D/I cache、pmem、power 写侧、RegRAS 环形缓冲（去掉搬移）、cfx15 挂死定位。
- **QEMU 侧（7 册）**：cfx 面与 pmem/power 对齐、`cg9`/`escape` 回归。
- **`tests/arch`（testcases 24 册）**：23 条用例（umon/ptw/cache/hart/pmem/time/power）+ 三平台承载（QEMU/gem5/RTL）、`expected-divergences.yaml`、`rtl-coverage.yaml`、`run_arch.py` 驱动与 `--self-test`。
- **spec/infra（5 册）**：`DADAO-12` 相关小节与契约同步、盘点矩阵与门控脚手架。

## 3. 关键裁定（最终口径）

| 主题 | 裁定 |
| --- | --- |
| 三方一致性 | 以 QEMU/gem5/RTL **逐槽签名一致**为准；差异必须由用户裁定并登记 `tests/arch/expected-divergences.yaml` |
| 仿真进不进常规门控 | 不进 L2/L3；`check-arch-smoke` 用 `cache-model=off`，cfx5 的 on 用例按需 |
| cfx 用例归属 | 写进各 RTL 补实现任务；同一 case 定义/期望只写一份，三平台复用载体 |
| ADWBFAIL | 不做用例（`DIV-14` 收口、`DIV-04` wont-fix） |
| `cg9 rc6` | 由 `m18-spec-006` 定为「RW、复位 2、进入取该值」，三实现按此对齐 |
| 环形 RegRAS | 四平台统一隐藏布局：物理槽 0 = `ra0` 元数据，`1..63` = 数据槽，`phys(i)=1+((base+i)%63)`；C1（`RACNT=0`）**不推进** base（与 QEMU 参考实现一致） |
| 三方差分收口 | **移交 M20**（用户 2026-11-27）：M18/M20 对 spec 改动多，差分与收口统一由 `m20-integ-001/002` 承担 |

## 4. 收尾状态（2026-11-27）

- **任务**：94 册 `已验证` + 本归档册；台账「待开始 / 进行中」为空。
- **issue**：`closed_in: M16` 共 56 条（快照见 `issues-closed.md`）；未解决的 1 条（`ISS-535`：`cfx_pmem` PA→SRAM DMA 直读未实现，P4 backlog）已移入 `issues-left.yaml`。
- **门控**：`make check-arch-smoke` PASS、`run_arch --self-test` PASS、`check-patch-tree` 的 chipyard/qemu/gem5/llvm 段 0 problem、`check-idl-full` 273/274（`DIV-18`）。
- **三方差分现场结果（移交 M20）**：qemu/gem5 各 20 PASS / 7 FAIL；`arch-power-001/002`、`arch-umon-012/013` 为回归挂死（此前有绿证据），`arch-cache-003/004` 为既有红；`arch-umon-011..013` 缺 gem5/RTL 承载；另有 4 处 `run_arch` 工具链缺口（详见 `discussing.md` N40）。

## 5. 经验与坑（供后续里程碑复用）

1. **组件补丁合入后必须「重放 + 重建 + `install-host`」**：M18 的 qemu 合入后源树/安装根未重放，导致 `arch-umon-*` 全红（`ISS-m16-013`）。判据：`check_patch_tree`（全量）能抓「源树 ≠ 补丁集」，`--source-state` 抓不出。
2. **「偶发挂死」先查预算**：`+max-cycles` 按 harness 时钟计数（= 2× core + 786 经验截距），`200000` 截断点落在签名 dump 内会被误读为挂死（`ISS-m16-011` 关闭为测量伪影）；判据应是「日志有无 `FAILED (timeout)`」而非「没跑完」。
3. **共享构建/安装根会随并发会话漂移**：`sim`/`gem5.opt`/`qemu` md5 只能在同时段内比较（`ISS-451`/`ISS-453`）；行为判据优先于 md5。
4. **基线对照要留改前产物**：逐字节一致的证明依赖改前输出/ELF，不能只重跑一次（本里程碑多次用改前 baseline TSV 复验）。
5. **任务书里的估算/槽数会随上游任务漂移**：派单前按现场刷新（如 hart 槽数从 89/40/40 → 124/38/38、pmem 55 → 48）。
6. **归档纪律**：`issues-*.yaml` 收尾必须清空（open → `issues-left`，closed → `issues-closed.md`）；任务书状态与台账同源，否则 `check-milestones-fresh` 会红（本轮补了 9 册残留状态）。

## 6. 遗留（不属 M16 收口阻断）

- `ISS-535`（P4 backlog）——`cfx_pmem` DMA 直读路径未实现，见 `issues-left.yaml`。
- 三方差分现场红项（power/umon 回归、cache-003/004 既有红）与 `run_arch` 工具链缺口——由 M20 登记与收口（`discussing.md` N40）。
