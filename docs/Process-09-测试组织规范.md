# 测试组织规范（inst / arch / unit / tset）

> **状态**：**草案（2026-10-26 重写；待用户确认）**。确认前不据此移动任何文件。
> **上位依据**：`docs/Process-07`（门控分层）、`docs/Process-08`（运行产物与日志）、`ADR-0016 D6`（测试产物根 `.dadao/tests`）。
> **关键词**：**必须**（MUST）／**应当**（SHOULD）／**可以**（MAY）。
> **前册**：`TESTCASES-067t`（2026-10-26）的盘点与主流调研；本册按用户 2026-10-26 的四分法重写。

---

## 1. 目标与范围

把现有混合布局的 `tests/` 与分散的 runner/门控，整理为**四个固定 scope**：

| scope | 测什么 | 平台 |
|---|---|---|
| **inst** | **每条指令/短序列**在平台上的执行语义 | **`system`（`qemu-system-dadao`）**；`user` 后置（`platforms` 字段预留） |
| **arch** | **cfx 资源管理与权限控制**：trap/escape/cfx2rd/cfx2rc、inner/global/switch/instruction 掩码、异常 cause、per-hart/per-system、TIMER/IPI/UART/power | 仅 `system` |
| **unit** | **各模块自身功能**：LLVM（MC/CodeGen）、lld、QEMU、picolibc（仅 picolibc 下跑）、仓库工具 | host / toolchain |
| **tset** | **外部套件**（third-party test suites）在成品系统上的运行：libc-test、llvm-test-suite、Embench | `user`（成品系统） |

- **boot**（Linux/busybox）**预留**：整系统启动到用户态；下一里程碑再建，本册不排。现有 `tests/e2e/` 是**旧目录名**，拆到 inst/arch/unit，不构成 `boot` scope。
- 判据：**上游/组件自己的测试套件 → `unit/<组件>`**；**跑在成品系统上的外部套件 → `tset`**。
- 本册只定**组织与门控**；运行目录/日志细节仍按 `Process-08`。

---

## 2. 现状事实（2026-10-26 盘点）

> **2026-10-27 更新（`TESTCASES-072t`，P2）**：inst 向量已由 `tests/vectors/*` 迁至
> `tests/inst/<ext>/`（`isa` → `base`），inst harness 已由 `tests/scripts/` 迁至
> `tools/testcases/{lib,inst}/`（旧入口留薄 wrapper + 别名门控 `check-qemu-{smoke,semantics}`）；
> 因此下文「`tests/vectors/`」「`tests/scripts/`」的计数是**迁移前快照**。

- `tests/`：341 文件 / 13 个顶层项；`llvm`(216)、`e2e`(45)、`scripts`(30)、`vectors`(25)、`atomics/clmul/fma/minmax/roundint`、`qemu`(1)。
- `.dadao/tests/`：**19,967 文件 / 1.13 GB**，18 个子目录；含任务专属目录（如 `llvm-ts-user-050t`）、无 `clean` 目标、约 210 MB 不可重生成。
- 向量：1,456 例 / 193 个 opcode 身份 / 22 个 YAML；ledger 1,956 条；lit 154。
- 现行门控：`check`（L1）、`check-modules`（L2）、`check-full`（L3）、`check-milestone`；**无夜跑层**。
- 工具分散：`tests/scripts/`（inst harness）、`tools/testcases/`（生成器/oracle/套件驱动）、`tools/integ/`（集成驱动），有重复（embench runtime、两套 runner）。
- 平台：宿主 Linux x86-64；guest `qemu-system-dadao` / `qemu-dadao`；**无硬件在环**。

---

## 3. 源码目录（迁移完成后）

```text
tests/
  inst/                     # 指令用例（无 isa 子层）
    base/ atomics/ clmul/ fma/ minmax/ roundint/ rev/ bitcnt/ ...
  arch/                     # cfx/权限
    umon/ jmon/ smon/ hmon/ ptw/ tlb/ cache/ hart/ llc/ pmem/ time/ uart/ power/
  unit/                     # 模块自身
    llvm/ lld/ qemu/ picolibc/ infra/
  tset/                     # 外部套件（套件独有 glue 就近）
    libc-test/ llvm-ts/ embench/
  shared/                   # 共享测试基础设施（非用例）
    bootrom/ linker/ crt0/ macros/ expected/
  inst.yaml arch.yaml unit.yaml tset.yaml   # 根级 case 清单（见 §5）
  case-ledger.tsv           # 身份清单（生成物，L1 门控）
  README.md
```

- **禁止** `inst/isa` 子层、`unit/tools`、`tests/index/`、`tests/manifest/`。
- `tests/qemu/` 占位删除（内容并入 `arch/` 或 `tools/testcases`）。

---

## 4. 生成物（`.dadao/tests/`，scope 名固定）

```text
.dadao/tests/
  inst/<YYYYMMDDTHHMMSSZ>-<suite>-<mode>/   # Process-08 三件套
  arch/<...>/
  unit/<module>/<...>/
  tset/<suite>/<...>/
  night/<YYYY-MM-DD>/manifest.tsv           # 夜跑汇总（只读报告）
```

- **scope 名固定**为 `inst|arch|unit|tset`；**禁止**任务专属目录（如 `llvm-ts-user-050t`）。
- 运行目录形状、`run.json`/`run.log`/`meta.json`、权威跑，按 `Process-08`。
- **日志**不进生成物：仍落 `.work/log/<模块>/<任务号>-*.log`。
- `make clean-tests SCOPE=inst|arch|unit|tset|night|all`。
- **确定性**：只对**构建产物**（ELF/对象/反汇编等）要求逐字节可重生成；运行记录含时间戳/宿主信息，**不要求**。`make test-repro SCOPE=...` 跑两次比 md5；`case-ledger.tsv` 已实测 byte-identical；`.lit_test_times.txt` 等运行脚手架排除。
- **记录保留**：authoritative/夜跑 + **失败必留**（`run.json`/`meta.json`/日志）；普通 smoke 可落 `/tmp` 或跑后清理。

---

## 5. 根级索引（`tests/*.yaml`）

每 scope 一份，直接放 `tests/` 根（**不用** `index/` 或 `manifest/`）：

```yaml
# tests/inst.yaml
- id: inst-base-001
  file: inst/base/add.yaml
  platforms: [system, user]      # inst 必填
  level: smoke                   # smoke | full
  requires: []                   # 如 [user-mode]
```

- **ID**：`inst-<ext>-nnn` / `arch-<cfx>-nnn` / `unit-<module>-nnn` / `tset-<suite>-nnn`。
- **独立 oracle**：期望值来自 spec/契约/参考模型，不从 QEMU 输出反推（承接 `Process-05 §4`）。
- `check-*-index`（L1）：ID 唯一、文件存在、字段合法、scope/平台合法、计数现场派生。

---

## 6. 工具与 runner（先分解，再整理）

目标：**runner/driver/generator 全部收拢到 `tools/testcases/`**，`tests/` 只放用例与 `shared/`：

```text
tools/testcases/
  lib/          # 共享 harness：构建、运行 qemu、超时/信号、run.json、md5
  inst/         # ISA 向量构建/运行（原 tests/scripts 主体）
  arch/         # bootrom/min-ROM/CFX 场景（原 min_rom_probe）
  unit/         # lit 驱动、codegen/elf/ir-lli、picolibc
  tset/         # libc-test / llvm-ts / embench 驱动
  gen/          # 向量/oracle 生成器（ISA/rev/bitcnt/atomics/...）
```

- `tests/scripts/`：迁移后删除；harness → `tools/testcases/lib`，bootrom/lds/crt0/宏 → `tests/shared/`。
- `tools/integ/`：集成驱动并入 `tools/testcases/{unit,tset}`；`tools/integ` 目录删除。
- `tests/scripts/embench_*` 与 `tools/testcases/run_embench_user_suite.py` 合并为 `tools/testcases/tset/embench` 一份。
- `tests/shared/` 只放**非用例**数据（bootrom、linker、crt0、宏、公共期望）。
- **glue（测试胶水）**：把上游套件/被测程序接到 DADAO 的**非用例**代码与数据，分三类：
  1. **链接/布局**：`dadao.lds`、`dadao-dyn.lds`、`bootrom.lds`（基址、段、对齐）；
  2. **启动/运行时**：`crt0`（`codegen_crt0.s`）、bootrom（`bootrom.S`/`bootrom_app.S`）、trampoline（`gen_trampoline.py`）、`embench_runtime.c`/`embench_user_boardsupport.c`、`picolibc_test_crt0.s`；
  3. **接口桩**：syscall/semihosting stub、`SYS_EXIT`/console 适配、公共宏/头（`embench_include/`）。
  - **不是 patch**：patch 只用于**改上游组件源码**（`components/<name>/patches/**`，如 picolibc `semihost-dadao.S`、embench `boardsupport.c`、musl `arch/dadao`）；测试胶水**不改上游**，是我们自己的文件。
  - **不只是链接脚本**：链接脚本只是第 1 类。
  - **落点**：**共享**（被 ≥2 scope/套件复用，或基础 harness）→ `tests/shared/`；**套件独有** → `tests/tset/<suite>/`；扩展独有 → `tests/inst/<ext>/`；cfx 独有 → `tests/arch/<cfx>/`；Python harness → `tools/testcases/lib`；**必须改上游源码** → `components/<name>/patches/`。

---

## 7. 平台

- **宿主**：Linux x86-64（当前）；Python + clang/lld/llvm-*。
- **guest**：`qemu-system-dadao`（system）与 `qemu-dadao`（user）；**无硬件在环**。
- `inst` 首期**只 `system`**；`platforms` 字段预留 `user`/`hw`，runner 只在交集上跑。
- 将来硬件在环：`platforms` 增 `hw`，不改用例 ID。

---

## 8. 门控分层（一个检查只在一层）

- **任务级（Task）**：任务书 `## 验证` 必须写 `scope`、`level`（targeted/smoke）、`cmd`；reviewer 重跑同一命令。**≤2 min**，如 `make check-inst-smoke CASE=...`、`make check-arch-smoke CFX=...`、`make check-unit-llvm`、`make check-tset-libc-smoke`。
- **L1（静态）**：`tests/*.yaml` 索引、ID/文件/字段、`case-ledger`、生成器 `--check`、链接/引用；**不跑 guest**。
- **L2（模块代表集）**：四 scope 的 **smoke** 集，进 `make check-modules`。
- **L3（全量语义）**：`check-inst`（全 ISA）、`check-arch`（全 cfx）、`check-unit`、`check-tset`（smoke），进 `make check-full`。
- **里程碑（Milestone）**：`check-milestone` = 归档/任务号/`check-tasks` + **L3 结果** + **夜跑报告存在性**；**不内联跑长套件**。
- **夜跑（Night）**：`make check-night` = `tset` full（libc-test/llvm-ts/Embench）+ 长 arch；`setsid nohup` + `[exit marker] rc=N`；汇总 `.dadao/tests/night/<date>/manifest.tsv`；次日由里程碑门控消费。

---

## 9. 任务如何 check

任务书固定段（示例）：

```yaml
scope: inst/base
level: smoke
cmd: make check-inst-smoke CASE=base/add
```

- 任务只跑**自己 scope 的 smoke/targeted**；全量/夜跑不进任务。
- reviewer 独立重跑同一 `cmd`；不一致即 `Needs Revision`。
- 后续可加 `tools/testcases/check_task.py --task <ID>` 读该段执行；首期用约定 + Make 目标即可。

---

## 10. 参考体系

- **inst**：RISC-V `riscv-tests`（按扩展、自检 asm）+ `riscv-arch-test`（签名/合规）。
- **arch**：`kvm-unit-tests`（特权/系统）+ QEMU `tests/qtest`（系统/设备）。
- **unit**：LLVM `lit`/FileCheck（`llvm/test`、`clang/test`）+ QEMU `tests/unit`。
- **tset**：libc-test、llvm-test-suite、Embench、picolibc 各自上游套件。
- **整体骨架**：QEMU `tests/{unit,qtest,tcg,functional}` 最接近「unit / 系统 / guest 指令 / 端到端」四分。
- **框架**：**暂不引入 pytest**（新增依赖 + 两套入口，收益有限）；`unit/infra` 若需标准化，优先 stdlib **`unittest`**；**cocotb 不适用**（RTL 仿真），除非将来做 RTL 验证。

---

## 11. 迁移分期（先分解，再搬家）

- **P0 分解**：本册 §12 的映射表 + 缺口清单（不移动文件）。
- **P1 骨架**：建 `inst/arch/unit/tset/shared`、根级 `*.yaml`；旧目录不动。
- **P2 inst**（**已完成：`TESTCASES-072t`**）：`vectors/isa` + 探针 → `inst/`；harness → `tools/testcases/lib+inst`；smoke 绿后进 L2（`check-inst-smoke` / `check-inst`）。
- **P3 arch**：`llvm/codegen/m5` + `min_rom_probe_*` + bootrom → `arch/`；smoke 绿后进 L2。
- **P4 unit**：`lit/MC|CodeGen`、`codegen/m3/m4/m6`、`ir-lli`、`picolibc` → `unit/`。
- **P5 tset**：libc-test/llvm-ts/Embench 驱动 → `tools/testcases/tset`；smoke 绿。
- **P6 收口**：删 `tests/scripts`/`tests/qemu`/`tools/integ` 旧入口；重写 Makefile 门控；`clean-tests`/`test-repro`；`check-night`。

### §12 资产 → scope 映射（P0）

- `tests/vectors/isa/*` + `atomics/clmul/fma/minmax/roundint` 探针 → **inst**
- `tests/llvm/lit/MC`、`lit/CodeGen`、`llvm/codegen/m3/m4/m6`、`llvm/ir-lli` → **unit/llvm**
- `tests/llvm/codegen/m5`（semihosting/CFX 权限）+ `tools/qemu/min_rom_probe_*` → **arch**
- `tests/e2e/lit`：semihosting → **arch**；FP/clmul 等指令性 → **inst**；weak/CM 等链接/ABI → **unit**
- `tests/scripts`（bootrom/lds/crt0/harness）→ **shared** + **tools/testcases/lib**；其中 `embench_runtime.c`/`embench_user_boardsupport.c`/`embench_include/` → **tests/tset/embench/**
- libc-test / llvm-ts / Embench → **tset**（ansibench 不保留：源码集合，非门控套件）
- picolibc 自测（仅 picolibc 下跑）→ **unit/picolibc**
- `case-ledger.tsv` → 根级（身份清单）

---

## 13. 待确认

已定：`inst` 只 `system`；pytest 不引入；ansibench 不保留；`e2e` 改名 **`boot`**（仅整系统启动，**下一里程碑**）；确定性只要求构建产物；记录保留 authoritative/夜跑 + 失败；glue 共享→`shared`、套件独有→`tset/<suite>`、上游改动→patch。

待确认：无（若有新增，另起条目）。

## 14. 验收（本册生效时）

- 四 scope 目录/根级 `*.yaml`/生成物固定名落盘；旧目录有明确迁移去向。
- L1 索引门控、L2 smoke、L3 full、night 四层各就位；一个检查只在一层。
- `make clean-tests`/`test-repro` 可跑；`case-ledger` 仍 byte-identical。
- 每个 scope 至少 1 个 smoke 用例端到端绿（inst/arch/unit/tset）。
