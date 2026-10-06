# TESTCASES-030t: L3 执行向量（多 TU/多段/ELF 链路；独立 oracle）

**模块**：testcases
**项目里程碑**：M4
**依赖**：`SPEC-105t`、`INFRA-045t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `SPEC-105t` 落地后的 `.tao/knowledge/contract-elf.md §2–§4`（RELA、4 类 reloc、`ABS48` 3 片、无 −4、溢出 link-time error）与 `.tao/adr/adr-0019`（Accepted）；`.tao/adr/adr-0004`（`SPEC-107t` 调整后的加载约定）。
  - `spec/Process-05` §2（**L3：IR → 代码 → 运行 → 结果比对；独立 oracle**）、§3/§4/§5/§6（L3 落点 + `tools/integ/`/`tools/testcases/`）。
  - M3 既有 `tests/llvm/codegen/`（`INFRA-045t` 迁移后：`.ll` + `expected.yaml`，由 `make test-codegen` 的 `run_codegen_e2e.py` 消费，**本任务不得破坏**）。
- **输出**（**用户裁定 2026-10-06**：向量 + 独立 oracle，**暂不接入门控**）：
  - **M4 L3 向量落 `tests/llvm/codegen/m4/`（并入 M3 落点，不另起 `tests/codegen-elf/`）**：
    - **单一 m4 清单（M3 驱动不读）**：`tests/llvm/codegen/m4/expected.yaml` 为 M4 向量的**独立清单**；`tools/integ/run_codegen_e2e.py` 默认只读 `tests/llvm/codegen/expected.yaml`，**不读也不递归** `m4/`，故 M4 向量天然不进门控；由 `INTEG-016t` 接入时合并/显式指定。
    - **多 TU**：每个程序含 **≥2 个 `.ll`**（跨 TU 直接调用、跨 TU 全局符号），由清单声明如何链接。
    - **多段**：`.text`/`.rodata`/`.data`/`.bss` 均被覆盖；含全局数据初值与运行时读写。
    - **reloc 场景**：跨段/外部符号 `ABS48` 地址构造、跨 TU `REL26` call、条件分支 `REL20`/`REL14`（溢出负例另见 `INTEG-016t`）。
    - **文件**：`tests/llvm/codegen/m4/*.ll` + 清单 `tests/llvm/codegen/m4/expected.yaml`（`programs: [{name, category, sources:[…], expected_exit_code, derivation}]`）+ `tests/llvm/codegen/m4/README.md`（程序 ↔ 覆盖点 ↔ 推导依据）。
  - **独立 oracle** `tools/testcases/validate_elf_vectors.py`：**不调用 `llc`/QEMU**，按 IR/spec 语义（宿主侧 Python，大端 + 64 位补码）**独立派生**每个程序的期望退出码，与 `m4/expected.yaml` 比对；校验 schema/覆盖/多 TU 形态，可失败。
- **约束**：
  - **门控时序（用户裁定 2026-10-06）**：本任务**只产出向量 + 独立 oracle**，**暂不接入** `make test-elf`/`make check`；由 `INTEG-016t` 接入并转绿。排除方式 = **独立 m4 清单（驱动不读）**，**不**改动/不写入 M3 `tests/llvm/codegen/expected.yaml`，也不放 `tests/llvm/codegen/*.ll`（只放 `m4/`）。
  - **落点唯一**：**并入** `tests/llvm/codegen/`（`INFRA-045t` 后的 M3 L3 落点），**不另起** `tests/codegen-elf/` 等平行目录。
  - **Independent oracle**（project 硬约束）：期望值**不得**由 `llc`/QEMU 生成；须宿主侧按 IR/spec 语义独立派生（或手算并写明推导）。size/sign 敏感项（指针差、补码、`ABS48` 分片）须逐条重算。
  - 规模 ∝ 能力（`Process-05 §3`）；手写少量、可审计（`§4`），不批量迁移。
  - 退出通道：返回值应落在 `ADR-0004 D3` 的 `0x00–0x7F`（避免与机器 fault 段 `0x80–0xFF` 歧义，吸取 `INTEG-012t` 遗留 1 的教训）。
  - 不改 `tests/llvm/codegen/**`（M3 部分）、`contracts/**`、`components/**`、`Makefile`；临时目录 `/tmp/opencode/TESTCASES-030t/`；**不提交 git**。

## 验收标准

1. **向量齐全**：`tests/llvm/codegen/m4/` 含 ≥1 多 TU（≥2 `.ll`）、≥1 多段（`.data`+`.rodata`）、≥1 跨 TU `call`、≥1 `ABS48` 地址构造；`README` 给出「程序 ↔ 覆盖点 ↔ 推导依据」表。
2. **独立 oracle**：`python3 tools/testcases/validate_elf_vectors.py` EXIT=0（覆盖/schema/期望值全部 PASS）；脚本无外部工具调用（grep 核实）；给出宿主独立重算输出。
3. **size/sign 敏感逐条重算**：多 TU 求和/指针差/`ABS48` 分片等逐条独立复算与 `m4/expected.yaml` 一致（含负值时高 8 位补码）。
4. **反例门控**：对注入反例（改期望值 / 改 IR 形态 / 少一个多 TU 用例）→ validator **非零退出**（真实输出留存 `.work/log/testcases/`）；还原回绿。
5. **不破 M3**：`make test-codegen`（M3 15/15）EXIT=0（M4 清单不在其默认读取路径内）；`make check` EXIT=0；`make check-dirs`/`check-no-residue` EXIT=0。
6. 一键证据脚本 `.work/evidence/TESTCASES-030t/run.sh`（非交互、失败非零、逐项打印、≥2 类注入自检、结尾无 `tee`）。

## 完成区

**测试结果**：
- **独立 oracle**：`python3 tools/testcases/validate_elf_vectors.py` → **EXIT=0，36/36 checks PASS**（schema / 多 TU 形态 / 结构覆盖 / 期望值全绿）。
- **一键证据脚本**：`.work/evidence/TESTCASES-030t/run.sh`（默认）→ **25/25 PASS，EXIT=0**；`run.sh --gates` → **29/29 PASS，EXIT=0**。
- **反例注入 3 类**（改期望值 / 改 IR 形态 / 少一个多 TU）：validator 均**非零退出**，还原后回绿（md5 前后一致，逐轮对账）。
- **不破 M3**：`make test-codegen` **EXIT=0（15/15）**；`make check` **EXIT=0**；`make check-dirs` **EXIT=0**；`make check-no-residue` **EXIT=0**。
- **附带**（非门控、非 oracle）：三程序经真实 M4 ELF 链（`llc` 逐 TU → `ld.lld -T dadao.lds` → `qemu -kernel prog.elf`）跑出 **42 / 30 / 126**，与独立期望一致（`.work/log/testcases/TESTCASES-030t-e2e-bonus.log`）。
- 失败原因：无。

**修改文件**：
- 新增 `tests/llvm/codegen/m4/`：`expected.yaml`（独立 m4 清单，`schema: codegen-elf-vectors-v1`）、`README.md`（程序 ↔ 覆盖点 ↔ 推导依据）、6 个 `.ll`（3 程序 × ≥2 TU：`m4_call_lib/main`、`m4_section_data/main`、`m4_pdiff_data/main`）。
- 新增 `tools/testcases/validate_elf_vectors.py`（宿主侧 IR 解释器 oracle + schema/覆盖/多 TU 校验；无外部工具调用）。
- 非入库（`.work/` 已被 gitignore）：`.work/evidence/TESTCASES-030t/run.sh`、`.work/log/testcases/TESTCASES-030t-*.log`。
- **未动**：M3 部分 `tests/llvm/codegen/**`（仅新增 `m4/` 子目录）、`contracts/**`、`components/**`、`Makefile`、M3 `expected.yaml`。
- `git status --untracked-files=all` 仅上列 9 个新文件（8 × m4 + 1 × validator）。

**验收结果**（真实输出，`cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`，无 `tee`；日志见 `.work/log/testcases/`）：

**验收 1 — 向量齐全**：`tests/llvm/codegen/m4/` 含 6 个 `.ll`（`find` 见下），3 个程序**每个 ≥2 TU**；全覆盖多 TU / 多段 / 跨 TU `call` / `ABS48`。
```
$ ls tests/llvm/codegen/m4/
README.md  expected.yaml
m4_call_lib.ll   m4_call_main.ll
m4_pdiff_data.ll m4_pdiff_main.ll
m4_section_data.ll m4_section_main.ll
```
`llvm-readobj -r` 证 reloc 场景真实（`.work/log/testcases/TESTCASES-030t-reloc-section-evidence.log`）：
- 跨 TU `REL26`：`m4_call_main.o`→`R_DADAO_REL26 lib_mix`；`m4_section_main.o`→`R_DADAO_REL26 get_ro`；`m4_pdiff_main.o`→`R_DADAO_REL26 pdiff`。
- `ABS48`（每个全局地址 3 片）：`m4_call_main.o`→3×`acc`；`m4_section_main.o`→`bss_cnt`/`rw_acc` 各 3 片；`m4_pdiff_main.o`→3×`buf`；`m4_call_lib.o`→`seed`/`acc`；`m4_section_data.o`→`ro_tbl`。
- 多段：`m4_section_data.o` 有 `.rodata`(PROGBITS,align8) + `.data`(PROGBITS,align8) + `.bss`(NOBITS,align8)；`m4_call_lib.o` 有 `.rodata`+`.bss`；`m4_pdiff_data.o` 有 `.bss`。
- `README.md` 给出「程序 ↔ 覆盖点 ↔ 推导依据」表（并注明 REL20/REL14 为同 TU 分支、汇编期就地解析）。

**验收 2 — 独立 oracle**：`validator` EXIT=0（36 checks）；脚本**无外部工具调用**：
```
$ grep -nE 'subprocess\.|os\.system\(|os\.popen|Popen\(|check_output|shutil\.which|run\(\[|os\.exec' tools/testcases/validate_elf_vectors.py
(无输出) grep EXIT=1
$ grep -nE '^\s*(import|from)\s' tools/testcases/validate_elf_vectors.py
from __future__ import annotations / import re / import sys / from pathlib import Path / import yaml
```
宿主独立重算输出（validator `oracle[...]`/`hand-vs-oracle[...]` 全 PASS）。

**验收 3 — size/sign 敏感逐条重算**（宿主 Python，大端 + 64 位补码；与 `m4/expected.yaml` 一致）：

| 程序 | 独立重算 | 结果 | expected |
|------|----------|------|----------|
| `multi_tu_call` | `lib_mix(20,11)=20+11+11`；读回 `acc=42`；`42==42`→ | **42** | 42 |
| `multi_section_loop` | `acc=2+(3+5+7+9)=26`；`26+4` | **30** | 30 |
| `cross_tu_pdiff` | `d=10−3=7`；`e=3−10=−7=0xFFFF_FFFF_FFFF_FFF9`；`e & 127=0x79=121`；`7^121=0x7E` | **126** | 126 |

（含负值高 8 位补码逐条重算；`ABS48` 分片 = 每地址 3 片 wyde，见验收 1 的 readobj 计数。）

**验收 4 — 反例门控**（`.work/log/testcases/TESTCASES-030t-evidence-run3.log`，EXIT=0）：
```
[PASS] inject-expected-value: injection effective (md5 187829d… -> b6f462b8…) → validator FAILED as expected (EXIT=1) → restored → green again
[PASS] inject-ir-shape:      injection effective (md5 74db7548… -> da017c5f…) → validator FAILED as expected (EXIT=1) → restored → green again
[PASS] inject-missing-tu:    injection effective (md5 187829d… -> 37022151…) → validator FAILED as expected (EXIT=1) → restored → green again
```

**验收 5 — 不破 M3**：`make test-codegen` EXIT=0（`Results: 15/15 passed, 0 failed`）；`make check` EXIT=0（`repository checks: PASS`）；`make check-dirs`/`check-no-residue` EXIT=0。M4 清单**未**被 M3 驱动读取：
```
$ grep -n 'm4' tools/integ/run_codegen_e2e.py   → 无输出，EXIT=1
$ grep -n 'm4/' tests/llvm/codegen/expected.yaml → 无输出，EXIT=1
```

**验收 6 — 一键证据脚本**：`.work/evidence/TESTCASES-030t/run.sh`（非交互、失败非零、逐项打印、3 类注入自检、结尾无 `tee`）；默认 25/25 PASS、`--gates` 29/29 PASS。

**新发现/坑**：
1. **后端缺口：`TargetInstrInfo::insertBranch` 未实现**（M4 DADAO backend）。触发形态 = **循环之后的等值守卫**（`cond → done → {br.eq/br.ne} → ret`）：`llc` 在 Control Flow Optimizer 崩溃（`Target didn't implement TargetInstrInfo::insertBranch!`，`exit=134`）；同样 CFG 去掉循环（`v_c`）或去掉等值守卫（`t2`）均可编译。规避：`multi_section_loop` 只保留 signed loop（REL20），REL14 由 `multi_tu_call` 覆盖。**建议**由 LLVM 模块评估补 `insertBranch`（本任务超范围未修）。
2. **`ABS48`「恒发、不就地解析」被实测再次确认**：任一全局地址材料化（含**同 TU 跨 section**，如 `@seed`/`@acc`）均发 3 片 `R_DADAO_ABS48`；与 `LLVM-055t` 结论一致。
3. **REL20/REL14 在同 TU 内是汇编期就地解析，不是链接期 reloc**：L3 向量只能保证对应**指令形态**被端到端执行；其**重定位发射**由 L1（`TESTCASES-029t`）与 `INTEG-016t` 覆盖。已在 `m4/README.md` 显式声明（避免过度断言）。
4. **section 结构判据 = LLVM 标准映射**（`constant`→`.rodata`、非零 init→`.data`、zeroinit→`.bss`）；`llvm-readobj -S` 实测与之一致。
5. 建议沉淀：M4 L3 向量落点与「独立 m4 清单 + M3 驱动不递归」的隔离做法；`insertBranch` CFG 崩溃形态；REL20/REL14 的 L3↔L1 分工。

**遗留问题**：
- ⏸ **M4 向量暂不接入门控**（用户 2026-10-06 裁定）——由 `INTEG-016t` 接入（合并/显式指定 `m4/expected.yaml`）。
- ⏸ **后端 `insertBranch` 缺口**（坑 1）：本任务超范围未修，建议由 LLVM 模块评估；本任务以向量形态规避。
- ❌ 无其它未完成项；无未修 finding。

> **用户裁定（2026-10-06）**：向量 + 独立 oracle，**暂不接入门控**（**单独 m4 清单，M3 驱动不读**）；落点改为 **`tests/llvm/codegen/m4/`**（并入，不另起 `tests/codegen-elf/`）。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查方式**：全局 `subagent_depth=1`，engineer 自主逐行审查（无嵌套子代理）——通读 `validate_elf_vectors.py` 全文（IR 解析器 + 宿主解释器 + 校验器）、6 个 `.ll`、`expected.yaml`、`README.md`、证据脚本；对照任务书验收 1–6 与硬约束逐条核验。

**判决**：实现完成，验收 1–6 均有真实输出支撑；所有 finding 已处置（见下），无未修阻断项 → 状态置 `待验收`。

**逐行审查要点**：
- **独立 oracle 真实性**：`validate_elf_vectors.py` 用**宿主侧 IR 解释器**执行每个程序的所有 TU（`@main`），取返回值；六类构造（整数运算/`icmp`/`load`/`store`/`getelementptr`/`ptrtoint`/`zext`/`sext`/`trunc`/直接 `call`/`br`/`ret`）逐条有实现；**越界构造抛 `IrError`**（fail-closed，不静默建模错），如 `alloca`/`phi`/未知指令。脚本**不含** `subprocess`/`os.system`/`Popen`（grep 证）。
- **双来源交叉**：`expected_exit_code` 同时与「解释器结果」及文件内 `HAND_DERIVED`（手算）比对（`oracle-vs-expected` + `hand-vs-oracle`），三者一致。
- **覆盖从 IR 结构派生**（不信任清单声明）：多 TU（每程序 ≥2 TU）、跨 TU `call`、跨 TU 全局、`ABS48`（全局地址材料化）、`REL26`（未定义符号调用）、`REL20`（signed 条件分支形态）、`REL14`（eq/ne 条件分支形态）、`.text`/`.rodata`/`.data`/`.bss`、全局运行时读/写；`files-match` 保证清单与磁盘 `.ll` 一致（无缺失/无孤儿/无跨程序复用）。
- **隔离**：M3 驱动 `run_codegen_e2e.py` 默认只读 `tests/llvm/codegen/expected.yaml`（非递归），`grep m4` 无命中；M3 `validate_codegen_vectors.py` 的 `glob("*.ll")` 非递归，`m4/` 不入选。
- **防造假**：全部 `cmd > log 2>&1; rc=$?`，无 `tee`；注入逐轮 md5 对账（注入有效→非基线；还原→回基线）。
- **边界/未测输入**：源文件被删 → 校验器**优雅 FAIL（EXIT=1，无 traceback）**（实测）；异常 IR（EOF 截断）→ `IrError`（已加守卫）。
- **范围**：仅新增 `tests/llvm/codegen/m4/**` 与 `tools/testcases/validate_elf_vectors.py`；未改 M3/`contracts`/`components`/`Makefile`；未提交 git；临时文件仅在 `/tmp/opencode/TESTCASES-030t/`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `multi_section_loop` 原 IR（循环 + 后置等值守卫）使 `llc` 崩溃（`insertBranch` 未实现，exit=134） | ✅已修 | 去掉后置等值守卫，改为 `return acc+4`；REL14 交由 `multi_tu_call` 覆盖（并登记后端缺口） | 6 个 `.ll` `llc` 全 EXIT=0；`make check` EXIT=0；validator 36/36 |
| F2 校验器把 `coverage` 列为**必填**，与任务书给定的 5 字段 schema 不符 | ✅已修 | `coverage` 改为**可选**字段（存在时校验词表）；覆盖改由 IR 结构派生为主判据 | validator EXIT=0（36 checks）；`expected.yaml` 仍带 coverage 且词表校验通过 |
| F3 输入缺失/畸形时校验器可能抛未捕获异常（`FileNotFoundError`/`IndexError`） | ✅已修 | `derive_coverage`/`check_programs` 缺失源文件守卫；全局/函数头累积循环加 EOF 守卫（抛 `IrError`） | 删源文件模拟 → EXIT=1、输出 4 条 `[FAIL]`、**无 traceback**；还原后 EXIT=0 |
| F4 docstring 含 `subprocess`/`Popen` 字样，朴素 grep 会命中 | ❌不修 | — | 仅散文、无调用；证据脚本按**调用形态** grep（`subprocess.`/`Popen(`/`os.system(`）→ 无命中（EXIT=1）；`import` 仅 `re/sys/pathlib/yaml` |
| F5 REL20/REL14 在同 TU 内不会成为链接期 reloc（与任务书「reloc 场景」措辞的张力） | ❌不修（披露） | README 显式声明其 L3 只覆盖**指令形态**，reloc 发射归 L1/`INTEG-016t` | `README.md`「Relocation coverage」注记；readobj 证 ABS48/REL26 真实存在 |

**自验命令退出码**：`validate_elf_vectors.py` EXIT=0（36）；`run.sh` EXIT=0（25/25）；`run.sh --gates` EXIT=0（29/29）；`make test-codegen` EXIT=0（15/15）；`make check` EXIT=0；`make check-dirs` EXIT=0；`make check-no-residue` EXIT=0。

#### 第 1 轮 reviewer 验收

**审查者**: reviewer subagent
**审查方式**: 独立重跑全部验收命令 + 独立注入 + 独立全量期望重算 + 后端缺口复现

---

**一、证据脚本审计 (`run.sh`)**

| 检查项 | 结果 |
|--------|------|
| FAIL 路径存在（每条注入有 `fail` 调用） | ✅ `inject_case` 函数在注入失败/md5 不变/validator 未失败/还原失败 时均 `fail(...)` |
| 注入非空且可还原 | ✅ md5 前后对账：注入→变、还原→回基线 |
| 结尾无 `tee` | ✅ 全脚本无 `tee`；用 `> log 2>&1; rc=$?` 捕获退出码 |
| 无恒真断言 | ✅ `if [ "$rc" -eq 0 ] && pass ... || fail ...` 每条有双向分支 |

**二、oracle 审计 (`validate_elf_vectors.py`)**

| 检查项 | 结果 |
|--------|------|
| 无 `subprocess`/`os.system`/`Popen` | ✅ `grep -nE 'subprocess\.|os\.system\(|os\.popen|Popen\('` EXIT=1（无命中） |
| import 仅 `re/sys/pathlib/yaml` | ✅ `from __future__ / import re / import sys / from pathlib / import yaml` |
| 不调用 `llc`/QEMU | ✅ 无外部进程调用 |
| 期望值宿主侧独立派生 | ✅ `Interp` 类解析 IR 并执行；`HAND_DERIVED` 字典独立手算 |

**三、重跑记录**

| 命令 | 输出摘要 | EXIT |
|------|----------|------|
| `bash run.sh`（默认） | 25/25 PASS，3 注入均 effective→FAIL→restore→green | **0** |
| `python3 validate_elf_vectors.py` | 36/36 PASS（14 schema +14 coverage +6 oracle +2 hand） | **0** |
| `grep subprocess` validator | 无命中 | **1** |
| `grep m4 run_codegen_e2e.py` | 无命中 | **1** |
| `grep m4/ M3 expected.yaml` | 无命中 | **1** |
| `make test-codegen` | 15/15 passed, 0 failed | **0** |
| `make check` | repository checks: PASS | **0** |
| `make check-dirs` | PASS | **0** |
| `make check-no-residue` | PASS | **0** |

**四、独立注入（第 4 类，与 engineer 的 3 类不同）**

| 操作 | md5 | 结果 |
|------|-----|------|
| 注入：`@seed = constant i64 11` → `12`（`m4_call_lib.ll`） | `ad1b23d...` → `54a8421...` | ✅ 有效 |
| validator 运行 | EXIT=1；`oracle-vs-expected[multi_tu_call] expected=42 oracle=43`；`hand-vs-oracle[multi_tu_call] hand=42 oracle=43` | ✅ FAIL 如预期 |
| 还原：cp 备份回原文件 | `54a8421...` → `ad1b23d...` | ✅ md5 回基线 |
| validator 运行 | EXIT=0，36/36 PASS | ✅ 回绿 |
| `git diff --name-only -- tests/llvm/codegen/m4/` | 无输出 | ✅ 无残留 |

**五、全量期望重算（独立推导，宿主侧，大端 + 64 位补码）**

| 程序 | IR 推导过程 | 结果 | expected.yaml | HAND_DERIVED | 一致 |
|------|-----------|------|---------------|-------------|------|
| `multi_tu_call` | TU A: `lib_mix(a,b)=a+b+seed`, seed=11; TU B: `r=lib_mix(20,11)=20+11+11=42`, `v=load(@acc)=42`, `r==v→return r=42` | **42** | 42 | 42 | ✅ |
| `multi_section_loop` | TU A: `ro_tbl=[3,5,7,9]`, `rw_acc=2`, `bss_cnt=0`; TU B: loop `i=0..3`: `acc=2+3+5+7+9=26`; return `26+4=30` | **30** | 30 | 30 | ✅ |
| `cross_tu_pdiff` | TU A: `pdiff(a,b)=ptrtoint(a)-ptrtoint(b)`; TU B: `p=&buf[10]`, `q=&buf[3]`; `d=pdiff(p,q)=10-3=7`; `e=pdiff(q,p)=3-10=-7=0xFFFFFFFFFFFFFFF9`; `m=e&127=0x79=121`; `r=d^m=0x07^0x79=0x7E=126` | **126** | 126 | 126 | ✅ |

**六、后端缺口复现（`insertBranch` 未实现）**

| 测试 | IR 形态 | llc 结果 |
|------|---------|----------|
| `min_insertbranch_crash2.ll` | loop（body 含跨 TU `call @get_ro`）+ 后置 `icmp eq` + `br.eq` | **EXIT=134**（SIGABRT）：`Target didn't implement TargetInstrInfo::insertBranch!` at `Control Flow Optimizer` |
| `min_no_crash.ll` | 同上但**去掉**后置 `icmp eq` 守卫 | **EXIT=0**（编译成功） |
| `min_insertbranch_crash3.ll` | 简单 loop + eq guard（**无**外部调用） | **EXIT=0**（编译成功） |

**判定**: **真实后端缺口**。触发条件 = CFG 含循环体基本块（尤其含调用指令）+ 后置等值守卫 → `Control Flow Optimizer` 调用 `ReplaceTailWithBranchTo` → 未实现 `insertBranch`。简单 loop+eq（无调用）不触发。M4 向量已正确规避此模式（`multi_section_loop` 只有 signed loop 无 eq guard；`multi_tu_call` 有 eq guard 无 loop）。**建议**：需立 LLVM 任务补 `DADAOInstrInfo::insertBranch`，否则 `INTEG-016t` 等需要 loop+eq guard 组合的 ELF 端到端测试将受阻。

**七、REL20/REL14 L3↔L1 分工判定**

engineer 声称「REL20/REL14 在同 TU 内汇编期就地解析、L3 只覆盖指令形态、reloc 发射归 L1/`INTEG-016t`」——**属实**。理由：
1. 条件分支目标在同 TU 的 `.text` 内，汇编器可计算偏移并就地 patch，不需要链接期 reloc。
2. README 已显式声明此分工，未过度断言。
3. `llvm-readobj` 证据确认 ABS48/REL26 是真实的链接期 reloc，而 REL20/REL14 形态由指令编码覆盖。

**八、约束核验**

| 约束 | 状态 |
|------|------|
| ≥1 多 TU（≥2 `.ll`） | ✅ 3 程序 × 2 TU = 6 `.ll` |
| ≥1 多段（`.data`+`.rodata`） | ✅ `multi_section_loop` 覆盖 `.text`+`.rodata`+`.data`+`.bss` |
| ≥1 跨 TU `call` | ✅ `lib_mix`/`get_ro`/`pdiff` 均跨 TU |
| ≥1 `ABS48` | ✅ 所有全局地址材料化（`@seed`/`@acc`/`@ro_tbl`/`@rw_acc`/`@bss_cnt`/`@buf`） |
| `README` 覆盖表 | ✅ 程序↔覆盖点↔推导依据表 + Relocation coverage 注记 |
| 退出码落 `0x00–0x7F` | ✅ 42, 30, 126 均在范围内 |
| `tools/integ/run_codegen_e2e.py` 不读 `m4/` | ✅ grep EXIT=1 |
| `make test-codegen` 15/15 EXIT=0 | ✅ |
| M3 `expected.yaml`/`*.ll` 未被改 | ✅ git status 仅 m4/ 子目录新增 |
| `make check`/`check-dirs`/`check-no-residue` EXIT=0 | ✅ |
| 未改 `contracts/**`/`components/**`/`Makefile` | ✅ |
| 一键证据脚本（非交互、失败非零、逐项打印、注入自检、结尾无 `tee`） | ✅ |

**判决：Accepted**

全部验收标准通过。engineer 产出质量高：
- 独立 oracle 无外部工具调用，期望值宿主侧独立派生，三者一致（oracle/hand/expected）。
- 覆盖齐全，README 文档完善。
- 后端缺口正确识别并规避，REL20/REL14 L3↔L1 分工声明准确。
- 注入自检3类 + reviewer 独立第4类，均可失败且可还原。

**建议跟进**：为 `insertBranch` 后端缺口立 LLVM 模块任务（补 `DADAOInstrInfo::insertBranch`），以解除 `INTEG-016t` 等需 loop+eq guard 组合的测试限制。
