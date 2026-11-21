# `tests/` 索引

> **本页给「要跑/要找用例的人」**：目录地图、常用命令、产物落点、覆盖矩阵指针。
> **现状盘点**（每个目录的文件数/门控/手工-自动/已知问题）：[`INVENTORY.md`](INVENTORY.md)。
> **组织规范（**生效**，P6 定稿）**：[`../docs/Process-09-测试组织规范.md`](../docs/Process-09-测试组织规范.md)。
> **分层口径**：门控层 L1/L2/L3 见 `docs/Process-07`；向量层 L1/L2/L3（编码/结构/执行）见 `docs/Process-05`；本页的 **I/S/E/U** 是**资产组织层**（指令级/系统级/端到端/工具单测），定义见 `Process-09 §3.1`。

---

## 0. 四 scope 骨架（P1–P6 全部落地；`tests/scripts`/`tests/qemu`/`tools/integ` 已删）

`Process-09` 的四分法骨架（P1，`TESTCASES-071t`）与六期迁移已**全部落地**：

- **P2 inst**（`TESTCASES-072t`）：`tests/vectors/*` + 顶层
  `atomics/clmul/fma/minmax/roundint` 探针 → `tests/inst/<ext>/`；inst harness →
  `tools/testcases/{lib,inst}/`。
- **P3 arch**（`TESTCASES-073t`）：`tests/unit/llvm/codegen/m5` → `tests/arch/umon/`；
  min-ROM 探针 `min_rom_probe_*` → `tools/testcases/arch/`；bootrom 三件 →
  `tests/shared/bootrom/`。
- **P4 unit**（`TESTCASES-074t`）：`tests/unit/llvm/{lit,codegen,ir-lli}`；picolibc 自测入口 →
  `tests/unit/picolibc/`（仍只在 picolibc 构建下跑）；门控 `check-unit`。
- **P5 tset**（`TESTCASES-075t`）：三个 user-mode 套件驱动 →
  `tools/testcases/tset/{libc-test,llvm-ts,embench}/`；Embench 套件独有 glue →
  `tests/tset/embench/`；门控 `check-tset-{libc,llvm,embench}-smoke`。
- **P6 收口**（`TESTCASES-076t`）：删旧入口三目录与旧 Make 目标名；共享 glue →
  `tests/shared/{crt0,linker,runtime}/`；集成驱动 → `tools/testcases/{unit,tset}/` +
  `tools/infra/`；门控重写（L2/L3）+ `night-run` / `clean-tests` / `test-repro`。
  原顶层 `e2e/` 于 P6 未动；`TESTCASES-084t` 已归 `tests/unit/llvm/e2e/`（工具链 E2E 属 unit）。
- **执行环境资产（2026-11-17）**：按执行环境重新归口——Tiny 专属脚本/固件/lds →
  `tests/ee-tiny/`（`m15-testcases-011`）；qemu-user / gem5 SE 的脚本、crt0、runtime、
  lds → `tests/ee-user/`（`m15-testcases-012`）；Vast 的 step5 BootROM 固件与
  `kaiwu-vast.lds` → `tests/ee-vast/`（`m15-testcases-013`，平铺不建子目录）。测试集目录（`tset/`、
  `inst/`、`unit/`、`arch/`）不动。

| scope | 测什么 | `platforms` 允许值 | 目录 |
|---|---|---|---|
| `inst` | 单指令/短序列执行语义（system 上跑） | `system`（`user`/`hw` 预留） | `tests/inst/` |
| `arch` | cfx/权限：trap/escape/掩码/TIMER/IPI/UART/power | `system`（`hw` 预留） | `tests/arch/` |
| `unit` | 各模块自身：LLVM/lld/QEMU/picolibc/仓库工具 | `host`、`toolchain` | `tests/unit/` |
| `tset` | 外部套件在成品系统上跑：libc-test/llvm-ts/Embench | `user`（`hw` 预留） | `tests/tset/` |

> `tests/data/` **不是 scope**：只放被代码消费的入库数据（语义矩阵、长尾基线 summary、
> 冻结的三平台报告），不成册、无 `*.yaml` 索引（`m15-infra-004`）。

- **`platforms` 语义**：`system` = **qemu-system 运行模式**（相对 `user` 用户态），**不**代表 Vast
  机型；Vast 已明确**不做 ISA 级执行覆盖**（`m13-testcases-043`，用户 2026-11-14 裁定）。`.S` 载体的
  索引条目一律 `platforms: [system]`。
- 共享**非用例**资产（bootrom/lds/crt0/宏）→ `tests/shared/`；`boot`（整系统启动）下一里程碑再建。
- 根级清单 `tests/{inst,arch,unit,tset}.yaml`：每条目**恰好**五项 `id` / `file` / `platforms` / `level`（`smoke|full`）/ `requires`；**空列表 `[]` 合法**。
- `id` = `<scope>-<name>[-<name>...]-<nnn>`，四份索引内**全局唯一**；`file` 必须位于对应 `tests/<scope>/` 且存在。
- 门控：`make check-tests-index`（L1，静态、不跑 guest；`tools/testcases/check_tests_index.py --self-test` 含注入反例）。
- 生成物：`.dadao/tests/`；scope→目录映射表见 `Process-09 §4`（单一真源 `tools/testcases/manage_tests.py::SCOPE_MAP`），清理/复现走 `make clean-tests` / `make test-repro`（见下文 §3）。

---

## 1. 目录地图（P6 收口后）

| 路径 | 层 | 是什么 | 自动入口 |
|---|---|---|---|
| `inst/<册>/*.S` | I | 指令执行向量（**唯一**载体模型；一行一用例、期望内联；原 YAML 载体已全退役） | `make check-inst-asm`（**L2**，`.S` 全量、单平台 QEMU） |
| `inst/00-isa-design/undi_reserved.S` | I | 保留编码（QFC 空白格）⇒ UNDI；**非 id 载体**（逐文件登记） | 同上（`check-inst-asm` 执行；`validate-vectors`/`check-tests-index` 显式登记） |
| `inst/{inventory.md,schema.md,README.md}` | — | 覆盖矩阵（M1 156 行）、inst scope 说明、迁移台账（`schema.md` 的 YAML 字段规范为**历史**） | `make validate-vectors`（L1） |
| `unit/llvm/lit/MC/{DADAO,DADAO-gen}/` | U | 汇编器编码 lit 用例（77 + 12；原 `llvm/lit/MC/`，旧路径为符号链接） | `make check-lit` / `make check-lit-full`；`check-unit` |
| `unit/llvm/lit/CodeGen/DADAO/` | U | IR→汇编/MIR **结构**断言（63） | `make check-lit`；`check-unit` |
| `unit/llvm/codegen/`（M3） | U | IR→运行（15 程序） | `make test-codegen`；`check-unit` |
| `unit/llvm/codegen/m4/` | U | 多 TU/多段 ELF（5 程序） | `make test-elf`；`check-unit` |
| `arch/umon/` | S | cfx_umon：semihosting/CFX 权限执行向量（10 程序 + 清单；原 `llvm/codegen/m5/`，旧路径为符号链接） | `make check-arch-smoke`（L2）/ `check-arch`（L3） |
| `unit/llvm/codegen/m6/` | U | M6 调用约定/大帧/FP（8 程序） | **手工**（见 `unit/llvm/codegen/m6/README.md`） |
| `unit/llvm/ir-lli/` | U | host `lli` vs DADAO 值级差分（19 include / 72 exclude） | `make check-unit`（L2）/ `make test-m6`（L3） |
| `unit/picolibc/` | U | picolibc 上游自测入口（仍只在 picolibc 构建下跑） | `make check-picolibc-tests`（L2；`check-unit` 成员） |
| `tset/libc-test/` | T | libc-test 套件说明 + L2 代表集规则（语料在 `.work/source/`） | `make check-tset-libc-smoke` |
| `tset/llvm-ts/` | T | llvm-test-suite 套件说明 + L2 代表集规则（语料在 `.work/source/`） | `make check-tset-llvm-smoke` |
| `tset/embench/` | T | Embench 套件说明 + 套件独有 glue（runtime/boardsupport/头） | `make check-tset-embench-smoke` |
| `unit/llvm/e2e/lit/*.test` | U | 工具链端到端 smoke/FP/clmul/weak/CM（14）；`TESTCASES-084t` 由顶层 `e2e/` 归入 | `make check-lit` |
| `unit/llvm/e2e/*.c|*.s|*.lds` | U | 上述 `.test` 的源（9 个已无 runner，见 `INVENTORY §7.4`） | 经 `.test` |
| `ee-tiny/` | S 载体 | Kaiwu-Tiny 执行环境资产（平铺，`m15-testcases-011`；`m15-testcases-015` 补齐）：3 个驱动（`run_inst_tiny.py` / `run_picolibc_tiny.py` / `run_embench_tiny.py`）+ Tiny bootrom/lds/公共宏（`cfx_power_tiny/cfx_hmon_tiny.{S,lds}`、`tests_embench_crt0.S`、`app_tiny.lds`） | `make build-bootrom`；`check-inst-asm` / `check-picolibc-tests` / `test-m6` |
| `ee-user/` | T 执行环境 | qemu-user / gem5 SE 资产平铺（`m15-testcases-012`）：12 个脚本（三套件全量驱动 + 代表集 + gem5 SE 基线/池 + `tset_matrix_user`）与 `crt0_user.s`/`mem_runtime_user.ll`/`dyn_probe_user.c`/`dyn_user.lds` | `make check-tset-{libc,llvm,embench}-{smoke,full}`、`test-codegen`/`test-elf`/lit/e2e、`test-m6` |
| `ee-vast/` | S 载体 | Vast 执行环境资产平铺（`m15-testcases-013`；`m15-testcases-015` 补 K1 boot 链）：step5 BootROM 固件 7 件（`power_vast/hmon_vast/smon_vast.{S,lds}` + `README.md`）+ `kernel_vast.lds` + K1 boot 链固件（`hmon_k0_vast`/`smon_k0_vast`/`probe_kernel_k0_vast` 的 `.S`/`.lds`） | `make build-bootrom` → `check-arch{,-smoke}`；`check-interface` / `run_parity`（vast）；`check-linux-k0{,-k1}` / `k0_boot_probe`（K1 链） |
| `case-ledger.tsv` | — | 逐条身份清单（1,962 行含表头；生成物） | `make check-case-ledger`（L1） |

---

## 2. 怎么跑

### 2.1 按门控层

```sh
make check            # L1：仓库完整性（不跑被测语义）
make check-modules    # L2：四 scope smoke（inst/arch/unit + tset×3；不含 FP 探针）
make check-full       # L3：check-arch + check-unit-full + test-m6（慢；inst 由 L2 check-inst-asm 全量跑、tset smoke 仅在 L2、tset full 仅在回归运行）；逐成员报告落 .dadao/tests/l3/<UTC>/
make night-run        # 回归运行（tset full×3 + 长 arch；独立 night.lock；主会话 setsid nohup 启动；小时级）
make check-night-report  # 按需诊断：回归运行报告存在性/结构/结果（未跑 ⇒ 明确 FAIL；观测，不阻断收口）
make check-l3-report  # 里程碑层：L3 报告存在性/结构/四 scope 覆盖/全绿（未跑 ⇒ 明确 FAIL）

make check-unit       # unit 代表集（仅 L2：lit + codegen/elf + ir-lli + picolibc fast）
make check-unit-full  # unit 全量（仅 L3：check-unit + lit 全量档）
make check-inst-smoke # inst 代表集（L2）
make check-inst       # inst 全量（L3）
make check-arch-smoke # arch 代表集（L2：SEE/semihosting + cfx 权限 + 25 服务）
make check-arch       # arch 全 cfx（L3：arch-smoke + cfx min-ROM 探针 044/045/049）
make check-tset-libc-smoke / check-tset-llvm-smoke / check-tset-embench-smoke   # tset 代表集（仅 L2；全量在回归运行）
```

生成物管理：

```sh
make clean-tests SCOPE=inst DRY_RUN=1     # 列出将删的目录（不动盘）
make clean-tests SCOPE=unit               # 真删（按 Process-09 §4 的 scope→目录映射表）
make clean-tests SCOPE=l3                 # 删 L3 报告目录（SCOPE=night 删回归运行报告）
make test-repro  SCOPE=unit               # 两次生产 + 构建产物逐字节比（运行记录排除）
```

（旧目标名 `check-qemu-{smoke,semantics}` / `test-semihost` / `check-{libc-test,llvm-ts,embench}-smoke`
已在 P6 删除。）

**L3 报告**（`TESTCASES-083t`）：`make check-full` 逐成员执行并写只读报告
`.dadao/tests/l3/<YYYYMMDDTHHMMSSZ>/`——`manifest.tsv`（`scope<TAB>suite<TAB>rc<TAB>log`，
逐成员一行）、`meta.json`（command / 起止 UTC / commit / 工具链摘要）、`run.log`
（汇总 + `[exit marker] rc=N`），与回归运行报告同格式（`tools/testcases/report_io.py`）。
同戳不覆盖；**里程碑收尾**由 `make check-l3-report` 机检（缺报告 ⇒ 明确 FAIL）。

### 2.2 单个向量文件 / 单个用例（手工）

```sh
# 单个 `.S` 载体（= 一个 id；链例比结果字节流、故障例比 monitor 退出码）
python3 tests/ee-tiny/run_inst_tiny.py --id add.si_riii_rd --platforms qemu

# 一册（目录）
python3 tests/ee-tiny/run_inst_tiny.py --vectors tests/inst/04-arith-logic-octa \
    --platforms qemu

# 全部册（= L2 `check-inst-asm` 的同一命令）
python3 tests/ee-tiny/run_inst_tiny.py --books-root tests/inst --platforms qemu

# 只做现场统计（不建镜像、不跑）：点数 / 点号连续性 / ≤127
python3 tests/ee-tiny/run_inst_tiny.py --books-root tests/inst --scan-only
```

前置：`make install-host`（`qemu-system-dadao` 取自安装根，见 `tools/testcases/lib/README.md`）。

arch（`tests/arch/`）单跑：

```sh
make build-bootrom                                   # SEE bootrom（源在 tests/ee-tiny/ + tests/ee-vast/）
python3 tools/testcases/arch/run_m5_e2e.py --only m5_semi_exit
python3 tools/testcases/arch/run_m5_e2e.py --inject   # 反例自检（FAIL ⇒ 还原 ⇒ 回绿）
python3 tools/testcases/arch/min_rom_probe_044t.py --list   # cfx min-ROM 场景探针
```

### 2.3 lit（汇编器/CodeGen/E2E）

```sh
make check-lit                      # MC + CodeGen + E2E 三套
make check-lit-full                 # 生成档全量（L3）
# 单文件（lit 可执行在安装根）
.dadao/cross-toolchain/bin/llvm-lit tests/unit/llvm/lit/MC/DADAO/rrrr.s -v
```

### 2.4 探针（**已全部退役**）

> 四类 C/IR 探针目标 `check-{rnd,minmax,fma,clmul}-probe` **已全部退役**，仓库内无任何
> 探针目录/驱动/oracle：
> - `rnd`/`minmax`/`fma`：`m13-testcases-044`（能力由 `tests/unit/llvm` 的 lit/e2e +
>   picolibc 承担，缺口已按抽样规则补进对应 `.S`）；
> - `atomics`（五探针）：`m13-testcases-050`（用户裁定 A）——编译器语义层改由
>   `tests/unit/llvm/e2e/atomics_e2e.c`（`make check-lit`，QEMU 真跑）承担；争用/内存序记 GAP；
> - `clmul`（C/IR 四文件 + 驱动/oracle）：`m15-testcases-008`——ISA 语义由
>   `inst/04-arith-logic-octa/clmul.o_rrrr_rd.S`（`check-inst-asm`）承担，编译器侧由
>   `tests/unit/llvm/lit/CodeGen/DADAO/clmul.ll` + `unit/llvm/e2e/lit/clmul_builtin.test`
>   （`make check-lit`）承担；**丢掉**的运行期覆盖：i128 composite、GHASH、CRC-32C
>   （见 `INVENTORY.md §6`）。

### 2.5 上游套件（opt-in，慢）

```sh
make check-tset-libc-smoke         # libc-test user-mode 代表集（L2：每顶层类别 1 例）
make check-tset-llvm-smoke         # llvm-test-suite user-mode 代表集（L2：每棵树 1 例）
make check-tset-embench-smoke      # Embench 全量 benchmark × -O0/-O2（L2）
make check-picolibc-tests          # picolibc 自测代表集（fast）
make check-picolibc-tests-full     # 全量（235，最近 1 fail / 3 blocked）
```

---

## 3. 生成物去哪

**现状**：全部落 `.dadao/tests/`（`manifests/install-dirs.lock.toml` 的 `test_artifacts_dir`，经 `tools/infra/paths.py` 解析；**禁硬编码**）。

| 产物 | 目录 |
|---|---|
| `test-codegen` / `test-elf` / `check-arch-smoke` | `codegen-e2e/` / `elf-e2e/` / `arch/m5-e2e/` |
| `test-m6` | `ir-lli-diff/` / `m6-embench/` |
| `check-inst-smoke` / `check-inst` | `harness/smoke/` / `harness/gate/` |
| lit | `lit-output/{DADAO-MC,DADAO-CodeGen,DADAO-E2E,DADAO-MC-gen}/` |
| 上游套件运行目录 | `libc-test-user/<UTC>-…/`、`llvm-ts-user/<UTC>-…/`、`embench-user/<UTC>-…/`（三件套 `run.json`/`run.log`/`meta.json`，见 `docs/Process-08`） |
| bootrom / m6 手工 | `bootrom/` / `codegen-m6/`、`elf-m6/` |

- **日志**在 `.work/log/`（`check-<name>.log` 或 `<任务号>-<用途>.log`）。
- **清理**：`make clean-work` **只删 `.work/`**；`.dadao/tests/` 走 `make clean-tests SCOPE=...`
  （`DRY_RUN=1` 先看清单；未知 scope / 未归属目录 ⇒ 非零退出）。逐目录来源与可重生成性见 `INVENTORY §4`。
- **重生成确定性**：`make test-repro SCOPE=...` = 清 → 跑 → 快照 → 清 → 再跑 → 构建产物逐字节比
  （运行记录排除；产物数 0 ⇒ FAIL）。`case-ledger.tsv` 已实测 byte-identical；其
  `asm` 行 = `.S` 载体逐用例身份（删任一用例行 ⇒ `check-case-ledger` 红）。

> **已定（B 形状）**：生成物保留在 `.dadao/tests/`（`ADR-0016 D6`），由 `make clean-tests` 管理；
> 统一改名到 `{inst,arch,unit,tset}/` 留到 `boot` 立项时一次性做（`Process-09 §4`）。

---

## 4. 覆盖矩阵指针（现状：多处并存，尚未合一）

| 想知道 | 看哪里 |
|---|---|
| M1 每个身份有没有向量、哪一册、deferred 原因 | `tests/inst/inventory.md`（156 行；`make validate-vectors` 守护） |
| 每个身份在 LLVM 后端到哪一步（td/isel/编码/汇编） | `tools/llvm/llvm-isa-backend-matrix.tsv`（266 行；`make check-isa-coverage` 守护） |
| 有没有「被删掉的用例/pattern」 | `tests/case-ledger.tsv`（1,958 条；`make check-case-ledger` 守护） |
| IR 差分语料的准入/排除理由 | `tests/unit/llvm/ir-lli/manifest.yaml`（19 include / 72 exclude，按类登记） |
| 哪些册进 L2/L3 | `tests/inst/inventory.md` 末尾「门控覆盖」表 |

**已知缺口**（详见 `INVENTORY §6`）：`fp` 66 个身份无向量（语义靠 lit + 4 个 probe）；`m1` 4 个 cfx 身份 deferred；`rev`/`bitcnt` 476 例不在门控。

> `TESTCASES-072t` 只搬家/接线：向量、探针、harness 内容未改（生成器 `ctrl-jump/call/ret`、`ctrl-br`、`mem`、`isa`、`misc`、`bitcnt`、`rev` 的 `--check` 逐字节一致，由 `make check-generator-sync`（L2）与 `make check-rev-vectors`（L1）守护；`case-ledger` 仅路径前缀变化）。

---

## 5. 相关文档

- `docs/Process-05-里程碑TDD规范.md`：向量三层（编码/结构/执行）、独立 oracle、落点。
- `docs/Process-07-门控分层规范.md`：L1/L2/L3 成员、触发点、新检查归属。
- `docs/Process-08-测试运行产物与日志组织规范.md`：运行目录三件套、权威跑、日志命名。
- `docs/Process-09-测试组织规范.md`：四个 scope、ID、索引 schema、生成物映射表、`clean-tests`/`test-repro`、回归运行、迁移分期（P6 定稿）。
- `tests/INVENTORY.md`：现状盘点与已知问题清单。
