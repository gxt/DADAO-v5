# M6 阶段已关闭 Issue（≤ 2026-10-11）

> **来源**：`INTEG-026m`（2026-10-11）从 `.tao/knowledge/issues.yaml` 提取——**M6 阶段已 `closed` 的 issue**（判据 = 字段 `resolved_by` 指向 M6 任务）。
>
> **判据**：M6 达成 = **2026-10-11**（`milestones.md` 项目里程碑 M6 置「达成」）。各 `resolved_by` 对应任务均属 M6（`INFRA-052m`/`SPEC-125m`/`LLVM-067m`/`QEMU-054m`/`TESTCASES-040m` 关联任务；提交落于 M6 期 2026-10-08 ~ 2026-10-11）。
>
> **未提取（活动台账保留）**：M1 阶段（≤ 2026-09-22）的 8 条见 `.tao/archive/M1/issues-closed.md`；M2（2026-09-23 ~ 2026-10-04）41 条见 `.tao/archive/M2/issues-closed.md`；M3（≤ 2026-10-05）56 条见 `.tao/archive/M3/issues-closed.md`；M4（2026-10-06 ~ 2026-10-07）12 条见 `.tao/archive/M4/issues-closed.md`；M5（2026-10-07 ~ 2026-10-08）5 条见 `.tao/archive/M5/issues-closed.md`。本次提取后活台账 `.tao/knowledge/issues.yaml` 仅保留 open 项。
>
> **注**：`ISS-183`/`ISS-184` 为「子代理执行异常·已处置」类登记项（`LLVM-071t`/`LLVM-072t`，`Too Many Requests` 重试 1 次成功），随其父任务提交一并关闭、计入 M6。

**共 18 条**（按原 `issues.yaml` 顺序）。

| id | title | scope | resolved_by |
| --- | --- | --- | --- |
| `ISS-161` | LLVM-052t 遗留：REL12（load/store 相对寻址）未添加；FK_Data_1/2/4 数据符号引用静默出 0 | [llvm] | LLVM-065t |
| `ISS-151` | LLVM-054t 遗留：访存符号偏移 ld.st …,[rb1,sym] 的 reloc 类型落 REL20（emitter 默认分支，既有） | [llvm] | LLVM-065t |
| `ISS-154` | contract-elf.md §2/§3 ABS48 未含数据 8 字节字段表示（与 ADR-0019 §D2 澄清漂移） | [spec] | LLVM-065t |
| `ISS-172` | `install-host` 幂等性缺陷：`cp` 间歇 `File exists`，污染 `test-elf`/`test-semihost` 门控（首跑 rc=2、重跑 rc=0） | [infra] | INFRA-053t |
| `ISS-173` | DADAO 后端缺整数 `setcc` / `select_cc` lowering：把比较结果当值使用即 ISel 崩溃（阻塞真实 C / Embench） | [llvm] | LLVM-069t |
| `ISS-174` | clang 内置头（resource-dir `include/`）未随 `install-host` 安装：`#include <stddef.h>` 即 `file not found` | [infra] | INFRA-054t |
| `ISS-175` | 大常量比较超 12 位立即数：`select/setcc`/branch 比较常量 >12 位即显式失败（`llc` rc=134 / `clang` rc=1） | [llvm] | LLVM-071t |
| `ISS-176` | 128 位乘高半 `umul_lohi` / `mulhu` 不可 select（`Cannot select: ... mulhu` rc=134） | [llvm] | LLVM-073t |
| `ISS-177` | `br_jt`（跳转表 / `switch` 密集分发）不可 select：`-O0` 即触发（`Cannot select: ... br_jt`） | [llvm] | LLVM-072t |
| `ISS-178` | 尾调用 `LowerCall` 断言 `LowerCall emitted a return value for a tail call!`（仅 `-O2`） | [llvm] | LLVM-070t |
| `ISS-179` | 分支 / 跳转目标超 12 位 PC 相对范围：`error: branch/jump target out of range for a 12-bit PC-relative immediate` | [llvm] | LLVM-071t |
| `ISS-180` | 【缺陷·静默错码】`-O2` 运行期误编译致死循环：编译成功但 QEMU 执行 hang（`GUEST_EXIT=124`），`-O0`/`-O1` 正常 | [llvm] | LLVM-070t |
| `ISS-181` | 数据指示符口径待裁决：禁 `.word/.long/.quad`、规范名 `.dd.*`、删 `.align` 只留 `.p2align` | [llvm] | SPEC-130t + LLVM-078t |
| `ISS-182` | 【缺陷】`.p2align`（可执行段）使 `llvm-mc` 崩溃：`MCAssembler.cpp:588 The stream should advance by fragment size` | [llvm] | LLVM-075t |
| `ISS-183` | 【子代理执行异常·已处置】`LLVM-071t` reviewer 首次下发返回 `Too Many Requests`、产出未落盘；重试 1 次成功（未触发任务拆分） | [llvm] | LLVM-071t |
| `ISS-184` | 【子代理执行异常·已处置】`LLVM-072t` reviewer 首轮返回 `Too Many Requests`、产出未落盘；重试 1 次成功（未触发任务拆分） | [llvm] | LLVM-072t |
| `ISS-185` | 有符号乘高半 `MULHS` / `SMUL_LOHI` 缺失（`Cannot select: ... mulhs` rc=134） | [llvm] | LLVM-076t |
| `ISS-186` | `aha-mont64 -O2` 阻塞于 `Cannot select: ... load<..., zext from i1>`（后端缺口，它类） | [llvm] | LLVM-077t |

## 判定表（逐条：`resolved_by` → 提交属 M6，提交日 ≤ 2026-10-11）

| id | resolved_by（提交） | 提交日（`git log --grep`） | 判定 |
| --- | --- | --- | --- |
| `ISS-151` | LLVM-065t | 2026-10-09 | ✅ 提取 |
| `ISS-154` | LLVM-065t | 2026-10-09 | ✅ 提取 |
| `ISS-161` | LLVM-065t | 2026-10-09 | ✅ 提取 |
| `ISS-172` | INFRA-053t | 2026-10-09 | ✅ 提取 |
| `ISS-173` | LLVM-069t | 2026-10-10 | ✅ 提取 |
| `ISS-174` | INFRA-054t | 2026-10-10 | ✅ 提取 |
| `ISS-175` | LLVM-071t | 2026-10-10 | ✅ 提取 |
| `ISS-176` | LLVM-073t | 2026-10-10 | ✅ 提取 |
| `ISS-177` | LLVM-072t | 2026-10-10 | ✅ 提取 |
| `ISS-178` | LLVM-070t | 2026-10-10 | ✅ 提取 |
| `ISS-179` | LLVM-071t | 2026-10-10 | ✅ 提取 |
| `ISS-180` | LLVM-070t | 2026-10-10 | ✅ 提取 |
| `ISS-181` | SPEC-130t + LLVM-078t | 2026-10-10 ~ 10-11 | ✅ 提取 |
| `ISS-182` | LLVM-075t | 2026-10-10 | ✅ 提取 |
| `ISS-183` | LLVM-071t | 2026-10-10 | ✅ 提取（子代理异常·已处置） |
| `ISS-184` | LLVM-072t | 2026-10-10 | ✅ 提取（子代理异常·已处置） |
| `ISS-185` | LLVM-076t | 2026-10-10 | ✅ 提取 |
| `ISS-186` | LLVM-077t | 2026-10-10 | ✅ 提取 |

> **待收敛（未提取，暂留活动台账 open）**：`ISS-043`/`ISS-045`/`ISS-138`/`ISS-148`/`ISS-156`/`ISS-159`/`ISS-162` 七条由 M6 任务（`LLVM-062t`〔043/045/148/159/162〕、`LLVM-064t`〔138〕、`SPEC-123t`〔156〕）在完成区**声称已修/已收口**，但 `issues.yaml` 中 `resolved_by` 仍为 `null`、`status` 仍为 `open`（父任务提交未回填台账）。按 `Process-04 §3` 步骤 1「关闭已消解项」**本应在归档前回填 `resolved_by` + `closed`**；`INTEG-026m` **未擅自处置**（`INTEG-024t` 已将裁决动作显式留待 `§3`），**如实登记提请**：建议 M7 归档前置 `§3` 梳理时一并回填/关闭（或经用户裁定）。

> **已收敛（`INTEG-028t`，2026-10-11）**：`ISS-043`/`ISS-045`/`ISS-138`/`ISS-148`/`ISS-156`/`ISS-159`/`ISS-162` **7 条**已逐条独立核实为「已修（可关）」（证据 `.work/log/integ/ISS-reconcile.md`），并在 `issues.yaml` 回填 `resolved_by`（`LLVM-062t`〔043/045/148/159/162〕、`LLVM-064t`〔138〕、`SPEC-123t`〔156〕）+ 置 `closed`（活台账 17 open / 7 closed，`check_issues` rc=0）。**如实示证、只追加**，不改上段历史。
