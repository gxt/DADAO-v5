# INTEG-059t: G3 完整 tset 双向一致性（static + dynamic）

**模块**：integ
**项目里程碑**：M11
**依赖**：`GEM5-023t`～`GEM5-028t`（SE 文件 I/O/时钟、信号、IPC/多进程、线程/TLS、动态装载器、文件映射）、`TESTCASES-103t`（预算）、`TESTCASES-104t`（动态驱动与 QEMU 动态基线）
**状态**：待开始

## 背景与目标

`ADR-0048 D4` 要求 SE 最终覆盖**完整 tset**，且 gem5 与 QEMU 同模式双向一致。前置能力补齐后，本任务做收口级一致性验证：

1. **完整 tset**：`libc-test` / `llvm-ts` / `embench`，**static 与 dynamic 两档**，在 gem5 SE 与 QEMU user 上逐 case 对照。
2. **一致性判据**（同 `ADR-0048 D2/D5`）：
   - 同 case 的 pass/fail、退出码、架构可见结果一致；
   - `gem5_only_fail` / `qemu_only_fail` / `diff` 逐条列名并归因；
   - `gem5 通过而 QEMU 未通过` 必须定位到 spec/实现/测试资产之一，不得直接接受。
3. **矩阵重生成**：`tests/parity/matrix-M11.md` 增加 SE 段（或新增 `matrix-M11-SE.md`），计数由脚本现场统计，不手改。
4. **预算口径**：复用 `TESTCASES-103t` 的按套件预算；`timeout` 单列，不计入 PASS/BLOCKED 能力项。
5. **收口证据**：完整报告（JSON + Markdown）落 `.tao/knowledge/refs/`；L1/L2/L3 + 夜跑观测记录。

## 范围 / 非范围

**在范围内**：`tools/testcases/tset/gem5-se-baseline/**`（扩展为完整 tset 双档）、`tools/testcases/parity/**`（SE 段）、`tests/parity/**`（矩阵快照）、`.tao/knowledge/refs/**`、本任务书、`milestones.md`。

**不在范围**：能力实现（前置任务）、spec/contracts、M11 `m` 册（收口任务另立）、`mprotect` 真权限与主程序 PIE（本轮登记为限制/backlog）。

## 验收标准

1. 三套件 × 两档 × 两引擎全量跑完，报告存在且可复算；计数现场统计。
2. `diff = 0`；`qemu_only_fail` 逐条列名（若有）；`gem5_only_fail` 逐条列名 + 归因；不存在「无归因的失败」。
3. `run_parity` 自检 rc=0；`node/arch` 269 例仍 0 diff；`check-inst`/`check-arch`/`check-gem5-decode`/`check_b6`/`check_b7` 绿。
4. 矩阵快照重生成且与报告逐列一致；`make check`（L1）、`make check-modules`（L2）rc=0。
5. 反例：把某 case 的期望状态改错 ⇒ 矩阵/对照报告 FAIL；`cp`+`md5sum -c` 还原回绿。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 本任务是 **G3 收口**，其完成是 M11 `m` 册的前置；不包含 `m` 册本身。
- 动态线依赖 `GEM5-027t`；若动态仍有 BLOCKED，须按 `ADR-0048 D4`「不得降级」明确列出并给关闭计划。
- 跑全量耗时长（小时级），按套件分批、落日志/EXIT，避免与构建并行。
