# TESTCASES-105t: 回归运行（原「夜跑」）加 gem5 SE + FS 成员

**模块**：testcases
**项目里程碑**：M11
**依赖**：`INTEG-059t`（gem5 SE 完整 tset 驱动）；gem5 FS 的 inst/arch 驱动已有
**状态**：待开始

## 背景

用户 2026-11-08 裁定：「夜跑应该加 gem5，包括 se 和 fs；夜跑这个词有歧义，你不要误解」。

**口径澄清**：本仓库的「夜跑」= **全量回归成员集**（`tools/testcases/night_run.py` 的 `DEFAULT_MEMBERS`），不是「只在夜里跑」；触发时间不限。

现状（实测）：`DEFAULT_MEMBERS` 4 个成员全部走 QEMU——`tset:libc-test` / `tset:llvm-ts` / `tset:embench` / `arch:cfx`；gem5 没有任何长期回归成员，只在 `INTEG-059t` 里做一次性对照。

## 目标

1. **gem5 SE 成员**：把 `INTEG-059t` 的 gem5 SE tset 驱动固化为 Make 目标（`check-tset-*-gem5-se` 或等价），按 `static` + `dynamic` 两档全量跑 libc-test / llvm-ts / embench；结果 JSON 落 `TSET_GATE_JSON_DIR` 同构位置。
2. **gem5 FS 成员**：把 gem5 FS 的 `inst` + `arch`（裸机 E2E）驱动固化为成员；与 QEMU system 同一 case 集、比架构结果/退出码，不比时序。
3. **`DEFAULT_MEMBERS` 追加**：`tset:gem5-se-libc`、`tset:gem5-se-llvm`、`tset:gem5-se-embench`、`arch:gem5-fs`（命名可调整，须自解释）。
4. **报告**：`check_night_report.py` 的成员结构性检查同时覆盖新成员（缺成员/空结果/构建失败必须 FAIL，禁 vacuous）。
5. **预算**：给每个新成员独立超时；任一成员超时单列 `timeout`，不吞并成「失败」。

## 验收标准

1. `make night-run` 的 dry-run 列表含 gem5 SE 与 gem5 FS 成员（逐条打印，名称自解释）。
2. **复用 `103t`/`104t` 的落盘结果作为「成员可用」证据**，不重复全量跑：把其 JSON 路径登记进成员定义/文档，并说明「该成员跑什么、产物在哪」。
3. **只跑一个最快成员**（建议 `embench`，实测秒级）做端到端接入验证：rc=0、结果 JSON 落盘、报告能识别。
4. `check-night-report` 对新报告 rc=0；人为删一个成员结果 ⇒ rc=1（可达 FAIL）。
5. 不改变 QEMU 四个成员的既有语义与预算。
6. 完成区 ≤30 行、无运行期路径。

## 说明

- **不阻塞 M11 收口**（用户 2026-11-08）：收口判据是「已知功能实现 + 已知 bug 解决 + 该做的验证做完」。
- **不重复全量**（用户 2026-11-09）：`103t`/`104t` 已跑过全量，本任务只做成员登记与报告接入；全量由常驻成员平时跑。
- gem5 SE 全量比 QEMU 慢一个量级，若单次回归跑不完，在报告中如实记录耗时，不缩减 case 集（除非用户另定）。
- 不改 `INTEG-059t` 的对照逻辑；本任务只做「固化为常驻成员 + 报告接入」。
