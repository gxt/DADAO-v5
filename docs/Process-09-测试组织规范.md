# 测试组织规范（inst / arch / unit / tset）

> **状态**：**生效（2026-10-27，P6 定稿）**。P1–P6 六期已全部落地（`TESTCASES-071t`…`TESTCASES-076t`）；
> 本册现行口径 = 下文正文（§2/§6 里标注「迁移前快照」的历史段落只作沿革）。
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

- **boot**（Linux/busybox）**预留**：整系统启动到用户态；下一里程碑再建，本册不排。原顶层 `e2e/` 已归 **unit**（`tests/unit/llvm/e2e/`，工具链编译/链接/运行用例），不构成 `boot` scope。
- 判据：**上游/组件自己的测试套件 → `unit/<组件>`**；**跑在成品系统上的外部套件 → `tset`**。
- 本册只定**组织与门控**；运行目录/日志细节仍按 `Process-08`。

---

## 2. 现状事实（2026-10-26 盘点）

> **2026-10-27 更新（`TESTCASES-072t`，P2）**：inst 向量已由 `tests/vectors/*` 迁至
> `tests/inst/<ext>/`（`isa` → `base`），inst harness 已由 `tests/scripts/` 迁至
> `tools/testcases/{lib,inst}/`（旧入口留薄 wrapper + 别名门控 `check-qemu-{smoke,semantics}`）；
> 因此下文「`tests/vectors/`」「`tests/scripts/`」的计数是**迁移前快照**。
>
> **2026-10-27 更新（`TESTCASES-073t`，P3）**：旧 `llvm/` 的 `codegen/m5/` → `tests/arch/umon/`
> （cfx_umon）；min-ROM 探针 `min_rom_probe_*` → `tools/testcases/arch/`、端到端驱动
> `run_m5_e2e.py` → `tools/testcases/arch/`（旧路径留薄 wrapper）；bootrom 三件
> （`bootrom.S`/`bootrom_app.S`/`bootrom.lds`）→ `tests/shared/bootrom/`
> （迁移期的 `tests/scripts/` 符号链接已由 P6 删除）。门控：`check-arch-smoke`（L2）/ `check-arch`（L3），旧名 `test-semihost`
> 为别名。下文 §12「`min_rom_probe_*` → arch」的**落点**以 §6 为准（驱动进
> `tools/testcases/arch/`，`tests/arch/` 只放用例资产）。

> **2026-10-27 更新（`TESTCASES-075t`，P5）**：三个 user-mode 上游套件驱动 →
> `tools/testcases/tset/{libc-test,llvm-ts,embench}/`（旧扁平路径留薄 wrapper，命令行
> 等价）；套件独有 glue（`embench_runtime.c`/`embench_user_boardsupport.c`/
> `embench_include/`）→ `tests/tset/embench/`（`tests/scripts/` 留符号链接，P6 已删除）。门控
> `check-tset-{libc,llvm,embench}-smoke`（L2，代表集机械派生；embench 为全量
> benchmark）。**运行目录名仍按 `Process-08`**（`<test-artifacts>/<suite>-user/…`），
> 不改 `tset/<suite>/` 形状（收口见 P6）。

> **2026-10-27 更新（`TESTCASES-074t`，P4）**：旧 `llvm/` 的 `lit/{MC,CodeGen}`、
> `codegen/{M3,m4,m6}`、`ir-lli` → `tests/unit/llvm/`（迁移期
> 符号链接已由 084t 删除）；picolibc 自测入口 → `tests/unit/picolibc/`（仍只在 picolibc
> 构建下跑）。门控 `check-unit`（L2）= `check-lit` + `test-codegen` + `test-elf` +
> ir-lli 值级差分 + `check-picolibc-tests` fast；旧目标名保留、可单独调用。下文
> 旧 `llvm/` 的计数是**迁移前快照**。

> **2026-10-27 更新（`TESTCASES-076t`，P6 收口）**：`tests/scripts/`、`tests/qemu/`、
> `tools/integ/` **已删除**；共享 glue → `tests/shared/{crt0,linker,runtime}/`；
> 旧 Make 目标名（`check-qemu-{smoke,semantics}` / `test-semihost` /
> `check-{libc-test,llvm-ts,embench}-smoke`）已删。下文 §2 的计数是**迁移前快照**。

> **2026-10-28 更新（`TESTCASES-084t`）**：顶层 `e2e/` → **`tests/unit/llvm/e2e/`**
> （工具链 E2E 属 unit/lit，`check-lit` 同跑）；旧 `llvm/` 迁移期符号链接与
> 旧 `min_rom_probe_*` 薄 wrapper 已删除，`tools/llvm` 默认路径、`spec/README`
> 与 README/INVENTORY 已同步。下文提及这两条旧路径处为迁移前快照。

- `tests/`：341 文件 / 13 个顶层项；`llvm`(216)、`e2e`(45)、`scripts`(30)、`vectors`(25)、`atomics/clmul/fma/minmax/roundint`、`qemu`(1)。
- `.dadao/tests/`：**19,967 文件 / 1.13 GB**，18 个子目录；含任务专属目录（如 `llvm-ts-user-050t`）、无 `clean` 目标、约 210 MB 不可重生成。
- 向量：1,456 例 / 193 个 opcode 身份 / 22 个 YAML；ledger 1,956 条；lit 154。
- 现行门控（2026-10-27，`TESTCASES-076t`）：`check`（L1）、`check-modules`（L2）、`check-full`（L3）、`check-night`（夜跑）、`check-milestone`；tset full 只在夜跑。
- 工具分散（迁移前快照，P6 后已删除）：`tests/scripts/`（inst harness）、`tools/testcases/`（生成器/oracle/套件驱动）、`tools/integ/`（集成驱动），有重复（embench runtime、两套 runner）。
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
    bootrom/ linker/ crt0/ runtime/ macros/ expected/
  inst.yaml arch.yaml unit.yaml tset.yaml   # 根级 case 清单（见 §5）
  case-ledger.tsv           # 身份清单（生成物，L1 门控）
  README.md
```

- **禁止** `inst/isa` 子层、`unit/tools`、`tests/index/`、`tests/manifest/`。
- `tests/qemu/`（占位 README）**已删除**（`TESTCASES-076t`）；QEMU 组件测试将来落
  `tests/unit/qemu/`（现在为空，不建空目录）。
- 工具链 E2E：`tests/unit/llvm/e2e/`（`check-lit` 跑其 `lit/`）。原顶层 `e2e/`
  已由 `TESTCASES-084t` 归入 **unit**——它测的是工具链编译/链接/运行整链，
  不是整系统启动（`boot` scope 仍预留）。

---

## 4. 生成物（`.dadao/tests/`）

```text
.dadao/tests/
  <scope 目录>/<YYYYMMDDTHHMMSSZ>-<suite>-<mode>/   # Process-08 三件套
  night/<YYYY-MM-DD>/manifest.tsv                   # 夜跑汇总（只读报告）
  l3/<YYYYMMDDTHHMMSSZ>/manifest.tsv                # L3 汇总（只读报告）
```

- **生成物根** = `manifests/install-dirs.lock.toml` 的 `test_artifacts_dir`（当前
  `.dadao/tests`），经 `tools/infra/paths.py` 解析，禁硬编码。
- **scope → 目录的映射表**（单一真源 = `tools/testcases/manage_tests.py::SCOPE_MAP`；
  文档与门控都指它，不另列清单）。**现状（P6）**仍沿用历史目录名 —— 统一改名到
  `{inst,arch,unit,tset}/` 需先定 `e2e`/`boot` 归属，**留到 `boot` 立项时一次性做**：

  | scope | 生成物目录（`.dadao/tests/` 下） |
  |---|---|
  | `inst` | `harness/`、`smoke/` |
  | `arch` | `arch/`、`m5-e2e/`、`probes/` |
  | `unit` | `codegen-e2e/`、`codegen-m6/`、`elf-e2e/`、`elf-m6/`、`ir-lli-diff/`、`lit-output/` |
  | `tset` | `libc-test-user/`、`llvm-ts-user/`、`llvm-ts-user-050t/`、`embench-user/`、`m6-embench/`、`libc-argv-static/`、`libc-argv-dynamic/` |
  | `night` | `night/` |
  | `l3` | `l3/` |

- **未归属即红**：`.dadao/tests/` 顶层出现映射表与 `UNSCOPED`（= 构建产物 `bootrom/`）之外
  的目录 ⇒ `clean-tests`/`test-repro` **FAIL**（防新产物目录悄悄长出而清理/复现漏掉）。
  **禁止**任务专属运行目录（如 `llvm-ts-user-050t` 这类历史孤儿已在表内，新任务不得再建）。
- 运行目录形状、`run.json`/`run.log`/`meta.json`、权威跑，按 `Process-08`。
- **日志**不进生成物：仍落 `.work/log/<模块>/<任务号>-*.log`（门控自身 `check-<name>.log`）。
- `make clean-tests SCOPE=inst|arch|unit|tset|night|all [DRY_RUN=1]`：按映射表删目录；
  未知 scope / 未归属目录 ⇒ 非零退出。`SCOPE=all` 连 `bootrom/` 一起删（并打印清单）。
- **确定性**：只对**构建产物**要求逐字节可重生成；运行记录含时间戳/宿主信息，**不要求**。
  `make test-repro SCOPE=...` 的口径 = **清 → 跑 producer → 快照 → 清 → 再跑 → 快照 →
  逐文件 md5 比**；比较面 = 构建产物后缀白名单（`.o/.bin/.s/.elf/.ll/.mir/.yaml/.a/.so/.d`），
  运行记录（`run.json`/`meta.json`/`*.log`/`.lit_test_times.txt`）天然排除。
  **产物数 == 0 ⇒ FAIL**（比较不能是空的）；`SCOPE=night` **显式拒绝**（报告不可逐字节复现）。
  `--inject CMD` 在两次生产之间执行一次注入，用于证明比较可达 FAIL（证据脚本用）。
- **夜跑报告**（`Process-09 §8` Night 层）落 `night/<YYYY-MM-DD>/`，三件：
  `manifest.tsv`（表头 `scope<TAB>suite<TAB>rc<TAB>log`，逐成员一行）、
  `meta.json`（`command`/`started_utc`/`finished_utc`）、`run.log`（汇总）。
  同日不覆盖（重跑须换日期或显式 `NIGHT_ALLOW_OVERWRITE=1`）。
- **L3 报告**（`Process-09 §8` L3 层，`TESTCASES-083t`）落 `l3/<YYYYMMDDTHHMMSSZ>/`，三件
  同格式：`manifest.tsv`（逐成员 `scope<TAB>suite<TAB>rc<TAB>log`）、`meta.json`
  （`command`/`started_utc`/`finished_utc`/`commit`/`toolchain` 摘要）、`run.log`（汇总 +
  `[exit marker] rc=N`）。由 `make check-full` → `tools/testcases/l3_run.py` 写；同戳不覆盖。
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
  inst/         # ISA 向量构建/运行（原薄 wrapper 区主体）
  arch/         # bootrom/min-ROM/CFX 场景（原 min_rom_probe）
  unit/         # codegen/elf 端到端驱动（原集成驱动目录）、lit/codegen/ir-lli 校验、picolibc
  tset/         # 外部套件驱动（TESTCASES-075t 已落）
    libc-test/  # run_libc_test_user_suite.py + run_smoke.py（L2 代表集）
    llvm-ts/    # run_llvm_ts_user.py + run_smoke.py
    embench/    # run_embench_user_suite.py（L2 跑全量 benchmark）
  gen/          # 向量/oracle 生成器（ISA/rev/bitcnt/atomics/...）
  manage_tests.py       # make clean-tests / test-repro 的实现（scope→目录映射单一真源）
  night_run.py          # make check-night 的实现（tset full×3 + 长 arch → 报告）
  check_night_report.py # 夜跑报告存在性/结构/结果门控（里程碑层）
  l3_run.py             # make check-full 的实现（L3 逐成员执行 → l3/<UTC>/ 报告）
  check_l3_report.py    # L3 报告存在性/结构/覆盖/结果门控（里程碑层）
  report_io.py          # night/l3 报告 manifest/meta 格式单一真源
```

- 仓库级**静态**一致性检查（`check_interface_alignment.py`）归 `tools/infra/`，不属测试驱动。

- `tests/scripts/`：**已删除**（`TESTCASES-076t`，P6）。去向：Python harness →
  `tools/testcases/{lib,inst}/`；共享 glue → `tests/shared/{bootrom,linker,crt0,runtime}/`；
  套件独有 glue → `tests/tset/<suite>/`。
- `tools/integ/`：**已删除**（`TESTCASES-076t`）。去向：codegen/elf 端到端驱动 →
  `tools/testcases/unit/`；embench 系统态端到端驱动 → `tools/testcases/tset/embench/`；
  跨模块接口一致性检查 `check_interface_alignment.py` → `tools/infra/`（静态检查，归 L1）。
- 旧 `tests/scripts/embench_*`（P6 已删除）与旧 `tools/testcases/run_embench_user_suite.py` 已合并为
  `tools/testcases/tset/embench` 一份（`TESTCASES-075t`）；套件独有 glue →
  `tests/tset/embench/`，共享运行时 → `tests/shared/runtime/dadao_mem_runtime.ll`。
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

- **任务级（Task）**：任务书 `## 验证` 必须写 `scope`、`level`（targeted/smoke）、`cmd`；reviewer 重跑同一命令。**≤2 min**，如 `make check-inst-smoke CASE=...`、`make check-arch-smoke CFX=...`、`make check-unit`、`make check-tset-libc-smoke`。
- **L1（静态）**：`tests/*.yaml` 索引、ID/文件/字段、`case-ledger`、生成器 `--check`、链接/引用、**跨模块接口一致性**（`check-interface`）、**代码跨度自检**（`check-code-range`）；**不跑 guest**。
- **L2（四 scope smoke）**：`check-inst-smoke`、`check-arch-smoke`、`check-unit`、`check-tset-{libc,llvm,embench}-smoke` ⇒ `make check-modules`。**不含 FP 探针**（2026-10-27 用户裁定「L2 只保留四 scope smoke」）。
- **L3（全量）**：`check-inst`（全 ISA）、`check-arch`（全 cfx）、**`check-unit-full`**（= `check-unit` + `check-lit-full`）、**4 个 FP 探针**（`fp` 身份无向量 ⇒ 探针是其唯一语义覆盖，只在 L3 跑）、`test-m6`（全量 lit + ir-lli + Embench E2E）⇒ `make check-full`；运行时逐成员落 `.dadao/tests/l3/<UTC>/` 报告（`l3_run.py`），由里程碑层 `check-l3-report` 消费。
  - **一层一列**：`check-unit` 只在 L2 直接列出；L3 用 `check-unit-full`，它在 L3 只是
    **前置依赖**（`Process-07 §4` 明文允许「被上层前置依赖而间接跑到不算重复」）。
    **不设例外**（2026-10-27 用户裁定严格化）。
  - **tset 不在 L3 直接列出**（`TESTCASES-082t`，2026-10-27）：`check-tset-{libc,llvm,embench}-smoke`
    只在 **L2**；tset **full** 只在**夜跑**；`test-m6` 的 Embench E2E 属集成步骤，不构成 tset smoke 重复。
- **里程碑（Milestone）**：`check-milestone` = 归档结构/内容 sha + 同步不可屏蔽 + knowledge 白名单 + `m` 册/任务号 + **夜跑报告存在性/结构/结果**（`check-night-report`）+ **L3 报告存在性/结构/四 scope 覆盖/结果**（`check-l3-report`）；**不内联跑长套件**。报告缺失 ⇒ **明确 FAIL**（不是 SKIP）。
- **夜跑（Night）**：`make check-night` = `tset` full ×3（libc-test / llvm-ts / Embench，各 static+dynamic）+ 长 arch；由**主会话** `setsid nohup` 启动 + `[exit marker] rc=N`；报告落 `.dadao/tests/night/<date>/`（`manifest.tsv`/`meta.json`/`run.log`），次日由里程碑门控消费。

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
- **P3 arch**（**已完成：`TESTCASES-073t`**）：`llvm/codegen/m5` + `min_rom_probe_*` + bootrom
  → `arch/`；smoke 绿后进 L2（`check-arch-smoke` / `check-arch`）。
- **P4 unit**（**已完成：`TESTCASES-074t`**）：`lit/MC|CodeGen`、`codegen`（M3/m4/m6）、`ir-lli`、`picolibc` → `unit/`；smoke 绿后进 L2（`check-unit`）。
- **P5 tset**（**已完成：`TESTCASES-075t`**）：libc-test/llvm-ts/Embench 驱动 → `tools/testcases/tset`；套件独有 glue → `tests/tset/<suite>/`；`check-tset-{libc,llvm,embench}-smoke`（L2）绿。
- **P6 收口**（**已完成：`TESTCASES-076t`**）：删旧入口（三个目录 + 旧目标名）；共享 glue →
  `tests/shared/`；门控重写（L2 = 四 scope 代表集、L3 = 四 scope 全量 + `test-m6`；tset
  smoke 后由 `TESTCASES-082t` 收口为「只 L2」、full 只夜跑）；新增
  `make check-night` / `check-night-report` / `clean-tests` / `test-repro`。

### §12 资产 → scope 映射（P0）

- `tests/vectors/isa/*` + `atomics/clmul/fma/minmax/roundint` 探针 → **inst**
- 旧 `llvm/` 的 `lit/MC`、`lit/CodeGen`、`codegen/m3/m4/m6`、`ir-lli` → **unit/llvm**
- 旧 `llvm/` 的 `codegen/m5`（semihosting/CFX 权限）+ min-ROM 探针 → **arch**
- 工具链 E2E（原顶层 `e2e/lit`，现 `tests/unit/llvm/e2e/`）→ **unit/llvm**（`TESTCASES-084t` 落定）
- 旧薄 wrapper 区（bootrom/lds/crt0/harness）→ **`tests/shared/`** + **`tools/testcases/lib`**；其中 `embench_runtime.c`/`embench_user_boardsupport.c`/`embench_include/` → **`tests/tset/embench/`**；集成驱动 → **`tools/testcases/{unit,tset}`** + **`tools/infra/`**（P6 已完成）
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
- **P6 验收（2026-10-27）**：旧入口零残留（`grep` 无悬空引用，除历史归档/组件 changelog/
  锁定 `spec/README.md`）；`make check` / `check-modules` 绿；`clean-tests` / `test-repro`
  可跑且**可失败**；`check-night-report` 在无报告时**明确 FAIL**。
