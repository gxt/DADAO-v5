# `tests/` 索引

> **本页给「要跑/要找用例的人」**：目录地图、常用命令、产物落点、覆盖矩阵指针。
> **现状盘点**（每个目录的文件数/门控/手工-自动/已知问题）：[`INVENTORY.md`](INVENTORY.md)。
> **组织规范（草案；下方 §0 的 P1 骨架已按此落盘）**：[`../docs/Process-09-测试组织规范.md`](../docs/Process-09-测试组织规范.md)。
> **分层口径**：门控层 L1/L2/L3 见 `docs/Process-07`；向量层 L1/L2/L3（编码/结构/执行）见 `docs/Process-05`；本页的 **I/S/E/U** 是**资产组织层**（指令级/系统级/端到端/工具单测），定义见 `Process-09 §3.1`。

---

## 0. 四 scope 骨架（P1 已落；P2 = inst 已迁）

`Process-09` 的四分法骨架已落盘（P1，`TESTCASES-071t`）。
**P2（`TESTCASES-072t`，2026-10-27）已完成 inst 迁移**：`tests/vectors/*` 与顶层
`atomics/clmul/fma/minmax/roundint` 探针 → `tests/inst/<ext>/`；inst harness →
`tools/testcases/{lib,inst}/`（`tests/scripts/` 留薄 wrapper，旧命令行等价可用）。
其余 scope（arch/unit/tset）仍待 `TESTCASES-073t`~`075t`，旧目录暂按原样保留。

| scope | 测什么 | `platforms` 允许值 | 目录 |
|---|---|---|---|
| `inst` | 单指令/短序列执行语义（system 上跑） | `system`（`user`/`hw` 预留） | `tests/inst/` |
| `arch` | cfx/权限：trap/escape/掩码/TIMER/IPI/UART/power | `system`（`hw` 预留） | `tests/arch/` |
| `unit` | 各模块自身：LLVM/lld/QEMU/picolibc/仓库工具 | `host`、`toolchain` | `tests/unit/` |
| `tset` | 外部套件在成品系统上跑：libc-test/llvm-ts/Embench | `user`（`hw` 预留） | `tests/tset/` |

- 共享**非用例**资产（bootrom/lds/crt0/宏）→ `tests/shared/`；`boot`（整系统启动）下一里程碑再建。
- 根级清单 `tests/{inst,arch,unit,tset}.yaml`：每条目**恰好**五项 `id` / `file` / `platforms` / `level`（`smoke|full`）/ `requires`；**空列表 `[]` 合法**。
- `id` = `<scope>-<name>[-<name>...]-<nnn>`，四份索引内**全局唯一**；`file` 必须位于对应 `tests/<scope>/` 且存在。
- 门控：`make check-tests-index`（L1，静态、不跑 guest；`tools/testcases/check_tests_index.py --self-test` 含注入反例）。
- 生成物：目标形状 `.dadao/tests/{inst,arch,unit,tset}/`（`Process-09 §4`）；本册**不改** `.dadao/tests/` 现状（见下文 §3）。

---

## 1. 目录地图（P2 = inst 迁移后；其余 scope 仍为迁移前状态）

| 路径 | 层 | 是什么 | 自动入口 |
|---|---|---|---|
| `inst/base/*.yaml` | I | M1 指令向量（16 册 / 708 例；原 `vectors/isa/`） | `make check-inst`（L3）、`make check-inst-smoke`（L2 代表集） |
| `inst/{rol,atomics,clmul,rev,bitcnt}/*.yaml` | I | 非 M1 向量（`rev`/`bitcnt` 未入门控） | 同上（仅 `rol`/`atomics`/`clmul`） |
| `inst/{inventory.md,schema.md,README.md}` | — | 覆盖矩阵（M1 156 行）、向量字段规范、inst scope 说明 | `make validate-vectors`（L1） |
| `inst/{atomics,clmul,fma,minmax,roundint}/*.[ch]|*.ll` | I | 指令语义探针源（C/IR；原 `tests/<ext>/`） | `make check-{rnd,minmax,fma,clmul}-probe`（L2；atomics 手工） |
| `llvm/lit/MC/{DADAO,DADAO-gen}/` | I | 汇编器编码 lit 用例（76 + 12） | `make check-lit` / `make check-lit-full` |
| `llvm/lit/CodeGen/DADAO/` | E | IR→汇编/MIR **结构**断言（63） | `make check-lit` |
| `llvm/codegen/`（M3） | E | IR→运行（15 程序） | `make test-codegen` |
| `llvm/codegen/m4/` | E | 多 TU/多段 ELF（5 程序） | `make test-elf` |
| `llvm/codegen/m5/` | S | semihosting/CFX 权限（10 程序） | `make test-semihost` |
| `llvm/codegen/m6/` | E | M6 调用约定/大帧/FP（8 程序） | **手工**（见 `llvm/codegen/m6/README.md`） |
| `llvm/ir-lli/` | E | host `lli` vs DADAO 值级差分（19 include / 72 exclude） | `make test-m6` |
| `e2e/lit/*.test` | E | 端到端 smoke/FP/clmul/weak/CM（14） | `make check-lit` |
| `e2e/*.c|*.s|*.lds` | E | 上述 `.test` 的源（9 个已无 runner，见 `INVENTORY §7.4`） | 经 `.test` |
| `scripts/` | U 载体 | **迁移后只剩薄 wrapper**（6 个 inst harness 入口）+ bootrom/crt0/lds/embench 胶水（P3/P5 再迁） | 旧命令行转发到 `tools/testcases/{lib,inst}/` |
| `qemu/` | — | 占位（QEMU 组件测试落点） | — |
| `case-ledger.tsv` | — | 逐条身份清单（1,962 行含表头；生成物） | `make check-case-ledger`（L1） |

---

## 2. 怎么跑

### 2.1 按门控层

```sh
make check            # L1：仓库完整性（不跑被测语义）
make check-modules    # L2：模块代表集（lit 子集 + inst 冒烟 + codegen/elf/semihost + 4 个 probe）
make check-full       # L3：inst 全量（check-inst）+ test-m6（慢）

make check-inst-smoke # inst 代表集（L2；旧名 check-qemu-smoke = 别名）
make check-inst       # inst 全量（L3；旧名 check-qemu-semantics = 别名）
```

### 2.2 单个向量文件 / 单个用例（手工）

```sh
# 整册（新路径）
python3 tools/testcases/lib/run_qemu_test.py tests/inst/base/reg-arith.yaml

# 旧入口/旧路径仍等价可用（薄 wrapper + 路径兼容层）
python3 tests/scripts/run_qemu_test.py tests/vectors/isa/reg-arith.yaml

# 单个 case（0-based）
python3 tools/testcases/lib/run_qemu_test.py tests/inst/base/reg-arith.yaml --case 1

# 整目录批跑
python3 tools/testcases/lib/run_qemu_test.py tests/inst/base/ --batch --jobs 8
```

前置：`make install-host`（`qemu-system-dadao` 取自安装根，见 `tools/testcases/lib/README.md` 或 `tests/scripts/README.md`）。

### 2.3 lit（汇编器/CodeGen/E2E）

```sh
make check-lit                      # MC + CodeGen + E2E 三套
make check-lit-full                 # 生成档全量（L3）
# 单文件（lit 可执行在安装根）
.dadao/cross-toolchain/bin/llvm-lit tests/llvm/lit/MC/DADAO/rrrr.s -v
```

### 2.4 探针

```sh
make check-rnd-probe       # ftrnd/fornd   785 例 × O0/O2
make check-minmax-probe    # ftmin/ftmax   3,102 例 × O0/O2
make check-fma-probe       # ftfma/fofma   626 例 × O0/O2
make check-clmul-probe     # clmul/GHASH/CRC-32C  627 例 × O0/O2
# atomics（无 make 目标，手工）：
python3 tools/testcases/run_atomics_probe.py --link-mode static --json-out /tmp/opencode/atomics-static.json
```

### 2.5 上游套件（opt-in，慢）

```sh
make check-testcases-suites        # libc-test + llvm-test-suite fast 子集
make check-testcases-suites-full   # 两套件全量可枚举 C 用例
make check-picolibc-tests          # picolibc 自测代表集（fast）
make check-picolibc-tests-full     # 全量（235，最近 1 fail / 3 blocked）
```

---

## 3. 生成物去哪

**现状**：全部落 `.dadao/tests/`（`manifests/install-dirs.lock.toml` 的 `test_artifacts_dir`，经 `tools/infra/paths.py` 解析；**禁硬编码**）。

| 产物 | 目录 |
|---|---|
| `test-codegen` / `test-elf` / `test-semihost` | `codegen-e2e/` / `elf-e2e/` / `m5-e2e/` |
| `test-m6` | `ir-lli-diff/` / `m6-embench/` |
| `check-inst-smoke` / `check-inst`（旧名 `check-qemu-{smoke,semantics}`） | `harness/smoke/` / `harness/gate/` |
| lit | `lit-output/{DADAO-MC,DADAO-CodeGen,DADAO-E2E,DADAO-MC-gen}/` |
| 上游套件运行目录 | `libc-test-user/<UTC>-…/`、`llvm-ts-user/<UTC>-…/`、`embench-user/<UTC>-…/`（三件套 `run.json`/`run.log`/`meta.json`，见 `docs/Process-08`） |
| bootrom / m6 手工 | `bootrom/` / `codegen-m6/`、`elf-m6/` |

- **日志**在 `.work/log/`（`check-<name>.log` 或 `<任务号>-<用途>.log`）。
- **清理**：`make clean-work` **只删 `.work/`**；`.dadao/tests/` 目前**没有**清理目标（1.2 G），逐目录来源与可重生成性见 `INVENTORY §4`。
- **重生成确定性**：已测事实与条件见 `Process-09 §5`（`case-ledger` 逐字节一致；`rev.yaml` 已漂移）。

> **待决策（A/B）**：`Process-09 §4/§7.1` 提出两案——**A** 改落 `.work/build/tests/<layer>/<id>/`（需改 `ADR-0016 D6`），**B** 保留 `.dadao/tests/` + 生成物清单 + `make clean-tests`。**本页在决策前按现状（B 形状）描述**；决策后本节替换为单一口径。

---

## 4. 覆盖矩阵指针（现状：多处并存，尚未合一）

| 想知道 | 看哪里 |
|---|---|
| M1 每个身份有没有向量、哪一册、deferred 原因 | `tests/inst/inventory.md`（156 行；`make validate-vectors` 守护） |
| 每个身份在 LLVM 后端到哪一步（td/isel/编码/汇编） | `tools/llvm/llvm-isa-backend-matrix.tsv`（266 行；`make check-isa-coverage` 守护） |
| 有没有「被删掉的用例/pattern」 | `tests/case-ledger.tsv`（1,956 条；`make check-case-ledger` 守护） |
| IR 差分语料的准入/排除理由 | `tests/llvm/ir-lli/manifest.yaml`（19 include / 72 exclude，按类登记） |
| 哪些册进 L2/L3 | `tests/inst/inventory.md` 末尾「门控覆盖」表 |

**已知缺口**（详见 `INVENTORY §6`）：`fp` 66 个身份无向量（语义靠 lit + 4 个 probe）；`m1` 4 个 cfx 身份 deferred；`rev`/`bitcnt` 476 例不在门控。

> `TESTCASES-072t` 只搬家/接线：向量、探针、harness 内容未改（生成器 `--check` 全部 byte-identical；`case-ledger` 仅路径前缀变化）。

---

## 5. 相关文档

- `docs/Process-05-里程碑TDD规范.md`：向量三层（编码/结构/执行）、独立 oracle、落点。
- `docs/Process-07-门控分层规范.md`：L1/L2/L3 成员、触发点、新检查归属。
- `docs/Process-08-测试运行产物与日志组织规范.md`：运行目录三件套、权威跑、日志命名。
- `docs/Process-09-测试组织规范.md`：I/S/E/U、ID、manifest schema、生成物 A/B、确定性、迁移分期。
- `tests/INVENTORY.md`：现状盘点与已知问题清单。
