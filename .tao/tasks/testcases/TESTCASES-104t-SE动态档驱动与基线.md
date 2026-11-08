# TESTCASES-104t: gem5 SE 动态档驱动与 QEMU 动态基线

**模块**：testcases
**项目里程碑**：M11
**依赖**：`GEM5-027t`（装载器 + auxv）、`GEM5-028t`（文件映射 + ldso）、`INTEG-058t`（转换编码迁移后的 QEMU 基线）
**状态**：待开始

## 背景与事实

- 现有 `tools/testcases/lib/gem5_se_engine.py` 的 `static_gate()` 对 `ET_DYN`/`PT_INTERP` 一律判 BLOCKED；三个 tset 驱动的 `--engine gem5-se` 只跑过 static
- `GEM5-027t` 放行 `ET_EXEC + PT_INTERP`，`GEM5-028t` 让 ldso 映射 DSO；驱动需支持 `--interp-dir`/`--redirect` 透传与 `--engine gem5-se --link-mode dynamic` 组合
- 仓库里 `.work/tests/authoritative/libc-*.json` 仍是 2026-10-19（LLVM-117t 之前）的旧数据，**不可作动态验收基线**；须重跑 QEMU dynamic 全量
- `ADR-0048 D4`：SE 最终覆盖完整 tset（static 先行、dynamic 后补但不得降级）

## 目标

1. **驱动**：`gem5_se_engine.py` 的 `static_gate()` 改为「`ET_EXEC`（含 `PT_INTERP`）放行、`ET_DYN` 主程序仍 BLOCKED」；透传 `--interp-dir`/`--redirect`；三个 tset 驱动支持 `--engine gem5-se --link-mode dynamic`。
2. **QEMU 动态基线刷新**：用当前工具链/QEMU 重跑 `libc-test` / `llvm-ts` / `embench` 的 dynamic 全量，落新 JSON（非易失），作为 gem5 对照基线。
3. **gem5 SE 动态全量**：`GEM5-028t` 合并后，跑三套件 dynamic 全量，与 QEMU 基线逐 case 对照；产出报告（`qemu_only_fail` 逐条列名、`gem5_only_fail` 逐条归因、超时单列）。
4. 不改测试用例与期望；不改 gem5/QEMU 实现。

## 范围 / 非范围

**在范围内**：`tools/testcases/lib/gem5_se_engine.py`、`tools/testcases/tset/{libc-test,llvm-ts,embench}/*.py`（仅 engine/参数）、`.tao/knowledge/refs/TESTCASES-104t-*`（报告）、本任务书、`milestones.md`。

**不在范围**：gem5 SE 实现（前序任务）、`mprotect` 真权限、主程序 PIE、测试用例与期望、`tests/parity/matrix-M11.md`（`INTEG-059t` 统一重生成）。

## 执行方式：按套件跨机分片（用户 2026-11-09 同意）

- **分片维度 = 套件**（不按用例切）：三套件互不依赖，天然可并行。
- 建议分配：`server208` 跑 `llvm-ts` + `embench`，主控机跑 `libc-test`（208 当前空闲；207 只用于 chipyard）。
- **三条前提**（缺一不可）：两机 `git rev-parse HEAD` 一致、组件源树 **tree hash** 一致（不比 commit id）、gem5/QEMU 二进制 md5 或 build-id 一致。
- **汇总与判据**：主控机收两机 JSON，校验「分片不重叠、不遗漏（并集 = 全集）」「engine_banner/二进制一致」；任一条不满足 ⇒ 结果作废重跑。
- **禁止的是「进程生命周期重叠」**：基线运行时段内，该机器不得有构建/编译/Verilator/sbt/大拷贝等 CPU 或 IO 密集进程；构建结束后再跑基线不受限。原因：用例 runtime 贴预算边界（`Quicksort` 128.9 s 对 120 s），负载会把「通过」推成 `timeout` 并误记为能力缺口。
- 若驱动需加参数（如 `--suites` 组合已够用则不加；确需 `--shard i/N` 再加），在任务书完成区说明。

## 验收标准

1. 三套件 × dynamic 在 gem5 SE 上跑完（预算按 `TESTCASES-103t`）；报告存在且可复算。
2. `qemu_only_fail` 逐条列名（须为 0 或给出 QEMU 侧任务）；`gem5_only_fail` 逐条归因；`timeout` 单列不计 PASS。
3. QEMU dynamic 新基线 JSON 覆盖三套件，计数与 `matrix-M11` 的 dynamic 行口径一致。
4. `make check`（L1）、`make check-modules`（L2）rc=0；驱动 `--self-test`（如有）rc=0。
5. 反例：把 `ET_EXEC+PT_INTERP` 改回 BLOCKED ⇒ 动态用例回 blocked；`cp`+`md5sum -c` 还原回绿。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 该任务只改**测试驱动/基线**，不改实现；gem5 侧能力缺口按 BLOCKED 记录并回给实现任务，不得在驱动里绕过。
- 动态档 gem5 慢 5–20×，预算与并发（`JOBS=32`）须按套件设置，避免把超时误判为能力失败。
