# 测试组织规范（I / S / E / U 四层）

> **状态**：**方案（草案）**——供用户决策；**未生效**。生效前不据此移动任何文件。
> **任务**：`TESTCASES-067t`（2026-10-26）。现状事实见 `tests/INVENTORY.md`（同册产出）。
> **上位依据**：待定。若采纳「A 案（生成物改落 `.work/build/tests/`）」⇒ 与 `ADR-0016 D6`（测试产物根 = `.dadao/tests/`，用户锁定）+ `docs/Process-05 §6`（2026-10-06 用户裁定）**冲突**，须按 `docs/Process-03` 走 ADR 修订并**逐条**与用户确认；B 案不触动 ADR。
> **关键词**：**必须**（MUST）／**应当**（SHOULD）／**可以**（MAY）。
> **编号说明**：任务书原写 `docs/Process-08-测试组织规范.md`，但 `docs/Process-08-测试运行产物与日志组织规范.md` 已占用 08（2026-10-19 生效）。本册取 **09**，不改既有 08；若用户要求改号，仅需改名 + 更新 `docs/README.md` 索引。
> **前册衔接**：同名前册 `TESTCASES-067t-QEMU测试向量盘点与ISE组织.md`（已在工作树删除，内容见 `git show HEAD:…`）曾冻结 I/S/E 三层的**部分**口径（I=`tests/vectors/isa`、S=`tests/vectors/system/<cfx>` + `check-qemu-system`、E=Linux/busybox）。本册在其上补 U 层并把「程序级端到端」纳入 E；两处差异见 §7.9。
> **索引**：`docs/README.md` 的 `Process-0x` 表**尚未**收录本册（本册任务约束只允许新增 3 份文档）；采纳后由收尾/后续任务补一行。
> **分工**：门控**层归属**见 `docs/Process-07`；**运行产物与日志形状**见 `docs/Process-08`；**测试向量分层与独立 oracle 原则**见 `docs/Process-05 §2–§5`。本规范只定**测试资产如何组织、索引、判定与迁移**，不重复上述三册。

---

## 1. 问题（事实，来自 `tests/INVENTORY.md`）

1. **找不到**：没有「列出全部用例 / 按 ID 跑一个」的入口；入口 = 21 个 make 目标（`INVENTORY §5.2`）+ 若干 README 手工命令（`tests/scripts/README.md`、`tests/llvm/codegen/m6/README.md`）。
2. **看不到覆盖**：覆盖信息分散在 `tests/vectors/inventory.md`（M1 156 行）、`tools/llvm/llvm-isa-backend-matrix.tsv`（266 行）、各 probe 日志与 lit 用例里；`fp` 66 个身份**无向量**，`m1` cfx 4 个身份 deferred，`rev/bitcnt` 476 例不在门控。
3. **分不清**：顶层 `atomics/`、`clmul/` 是探针源，`vectors/atomics/`、`vectors/clmul/` 是向量；`llvm/codegen`（跑）与 `llvm/lit/CodeGen`（只看结构）同名异物。
4. **跑不到**：8 个 m6 执行程序、5 个 atomics 探针、9 个 e2e 源、4 个单测脚本**无任何自动入口**（清单见 `INVENTORY §5.3`）。
5. **清不掉**：`.dadao/tests/` 1.2 G 无清理目标（`clean-work` 只删 `.work/`），其中约 210 M 不可重生成（生成脚本已不在仓库，全仓 grep 零命中）。

下文第 2 节看主流怎么做，第 3 节给 DADAO 方案，第 4–6 节给生成物/确定性/迁移，第 7 节列待决策项。

---

## 2. 主流调研（8 个套件 / 6 个来源族，每项四要素）

> 覆盖任务要求的 6 族：RISC-V（2.1–2.2）· ARM（2.3、2.4、2.5 的 arm64）· x86（2.4、2.5 的 x86）· QEMU（2.7）· LLVM（2.8）· Linux（2.5、2.6）。

> 每条只写「**源码 vs 生成物**｜**层级**｜**oracle**｜**门控**」。来源为项目仓库/官方文档名称（未逐字引用）。

### 2.1 RISC-V `riscv-tests`（`riscv-software-src/riscv-tests`）

- **源码/生成物**：源 = `isa/<isa>/<name>.S` + `env/`（`riscv_test.h`、链接脚本、`p`/`v` 环境）；生成物 = 构建目录里的 `*.elf`/`*.dump`，**不入库**。
- **层级**：指令级（`isa/`，按 `rv64ui`/`rv64um`… 分册）+ benchmark；不含 OS/系统调用。
- **oracle**：**测试内自检**——期望值以汇编宏硬编码在用例里，`TEST_PASS`/`TEST_FAIL` 写 `tohost`，运行器只看 `tohost`/退出码。没有外部参考模型 ⇒ 期望值须人工从手册推导。
- **门控**：`make` + `run-tests`，按 ISA 子集选择；失败非零。

### 2.2 RISC-V `riscv-arch-test` + RISCOF（`riscv-non-isa/riscv-arch-test`；RISCOF 规范）

- **源码/生成物**：源 = `riscv-test-suite/rv64i_m/<ext>/src/*.S`；期望 = 同目录 `references/*.reference_output`（参考模型签名）；运行产物 = `riscof_work/`（生成目录，忽略）。
- **层级**：架构合规层（逐扩展/逐特权模式；指令级 + 机器模式 CSR/异常）。
- **oracle**：**参考模型签名**——同一测试在参考模型（Spike/Sail）上跑出 signature，DUT 的 signature 与之**逐字节**比较。这是最接近「独立 oracle」的主流做法。
- **门控**：RISCOF 插件 + 覆盖率报告；按 suite/扩展跑，签名不等即失败。

### 2.3 Arm `arm-arch-test`（Arm Architecture Tests，Arm 官方架构合规套件）

- **源码/生成物**：源 = `test_pool/<arch>/<feature>/`（汇编 + `VAL`/`END` 宏）；工具生成 ELF；运行产物（签名/寄存器转储/日志）在运行目录，不入库。
- **层级**：**系统/架构级**——覆盖 EL1/EL2/EL3、SVE/SME、RME 等，在 FVP/硬件上跑（不是单一指令编码测试）。
- **oracle**：用例内期望值 + 参考模型（Arm Fast Model/FVP）对照；覆盖报告按 feature 汇总。
- **门控**：`make` + 运行脚本，按 feature/suite 选择；失败非零，覆盖率另表。

### 2.4 `kvm-unit-tests`（`kvm-unit-tests/kvm-unit-tests`；x86 + arm + s390x）

- **源码/生成物**：源 = `x86/*.c`、`arm/*.c`、`lib/{x86,arm,s390x}/`；配置 = `x86/unittests.cfg`；产物（`*.flat`/`*.elf`）在构建目录。
- **层级**：**系统级**——guest 内核态：页表/中断/异常/定时器/设备/hypercall；可在 KVM 或 `qemu-system-*`（TCG）下跑。
- **oracle**：测试内断言 + TAP13 输出（`ok`/`not ok`/`SKIP`）；`unittests.cfg` 可对输出做 `check`/`fatal` 正则匹配。
- **门控**：`run_tests.sh`（`-g` 分组、`-t` 单选），退出码判定；`make standalone` 供单测。

### 2.5 Linux `kselftest`（`tools/testing/selftests/`；含 `x86/`、`arm64/`）

- **源码/生成物**：源 = 每子系统一目录 + `Makefile`（`TEST_PROGS`/`TEST_GEN_PROGS`/`TEST_FILES` 声明）；编译产物在源码树旁但被 `.gitignore` 覆盖。
- **层级**：**系统级**（内核 ABI/行为）；`x86/` 提供架构相关测试（vdso、sigreturn、FSGSBASE…）。
- **oracle**：测试内断言 + `ksft` 库输出 TAP；无外部模型。
- **门控**：`make -C tools/testing/selftests` + `run_kselftest.sh`，解析 TAP；失败非零。

### 2.6 Linux `KUnit`（`Documentation/dev-tools/kunit/`）

- **源码/生成物**：测试与内核源码同树（`lib/kunit/kunit-test.c` 等）；`kunitconfig` 描述配置；构建/日志在 `.kunit/`（生成物）。
- **层级**：内核**单元/子系统**测试（函数级）。
- **oracle**：`KUNIT_EXPECT_*` / `KUNIT_ASSERT_*` 断言（测试内）。
- **门控**：`tools/testing/kunit/kunit.py run`（UML 或 QEMU），输出 TAP，`--filter` 选 suite；失败非零。

### 2.7 QEMU（`docs/devel/testing/`：unit / qtest / tcg / functional）

- **源码/生成物**：源 = `tests/unit/*.c`（GLib `g_test`）、`tests/qtest/*.c`（`libqtest`）、`tests/tcg/<target>/`（guest 裸机）、`tests/functional/*.py`（`QemuSystemTest`）；产物全在**构建目录**；VM 镜像走 `asset` 缓存（`QEMU_TEST_ALLOW_LARGE_STORAGE` 才允许大资产）。
- **层级**：**四档并列**——host 单测（unit）/ 设备协议（qtest）/ guest 执行（tcg）/ 整机功能（functional）。这是「按被测边界分层」最清晰的样本。
- **oracle**：unit/qtest 用测试内断言；tcg 用 guest 退出码/输出；functional 用 Python 断言（可对称/差分）。无统一参考模型。
- **门控**：`make check`（unit+qtest）、`make check-tcg`、`make check-functional`（opt-in，需镜像）；meson/lit 退出码判定，逐例日志落构建目录。

### 2.8 LLVM（`llvm/test` + lit/FileCheck；`llvm-test-suite`）

- **源码/生成物**：源 = `llvm/test/{MC,CodeGen,Transforms}/<target>/*.ll|*.s`（`RUN:` + `CHECK:`）；`test_exec_root` 指向**构建树**，源树只读；`llvm-test-suite` 源 = `MultiSource/`、`SingleSource/`、`Bitcode/`，参考输出 `.reference_output`，结果 `test(results).json`。
- **层级**：lit 属**工具结构断言**（编码/isel/帧）；`llvm-test-suite` 属**执行/性能**层。官方明确前者锁回归、**不证语义**（与 `Process-05 §2` 的 L2 同义）。
- **oracle**：lit 用手写 `CHECK:`（结构快照）；test-suite 用 `.reference_output`（参考输出）。
- **门控**：`ninja check-llvm` / `llvm-lit`（`--filter`、`-j`）；test-suite 用 CMake+Ninja+lit；失败非零。

### 2.9 对本项目的 6 条结论

1. **源与产物必须分树**：所有调研对象都把「测试源/期望」入库、把「运行产物」放构建目录或缓存（QEMU/LLVM 最彻底）。
2. **层级按「被测边界」切，不按「工具」切**：QEMU 的 unit/qtest/tcg/functional 与 Arm 的架构级分层都说明这一点。
3. **oracle 分两级**：测试内断言（kselftest/KUnit/riscv-tests）与**参考模型签名/输出**（RISCOF、llvm-test-suite）；后者才配叫独立 oracle。
4. **门控 = 可执行入口 + 退出码**，且**按组选择**（`-g`/`--filter`/suite）；没有「按 ID 跑单例」能力的套件都会退化成手工。
5. **索引是必需品**：`unittests.cfg`、`TEST_PROGS`、lit 的发现规则、RISCOF 的 suite 清单——主流都用**机器可读清单**代替 README 表格。
6. **生成物需要清理与复现判据**：LLVM/QEMU 用构建目录天然可清；riscv-arch-test 用 `reference_output` 做逐字节复现判据。

---

## 3. DADAO 方案

### 3.1 四层定义（按「被测边界」，MUST）

| 层 | 名称 | 判定对象 | 判据 | 典型载体 |
|---|---|---|---|---|
| **I** | 指令级 Instruction | 单条指令 / 短序列的**编码、合法性、语义** | 编码字与 `contracts/opcodes.yaml` 一致；语义由独立 oracle 派生 | 向量 YAML、lit MC（汇编器编码） |
| **S** | 系统级 System | 机器/特权/异常/设备/OS 接口（跨指令、单次启动） | 陷入原因、CSR/权限、bootrom 交接、SYS_EXIT、服务表 | m5 semihost、bootrom、min-ROM 探针、syscall ABI |
| **E** | 端到端 End-to-end | 源程序/IR → 编译/链接 → 运行（或结构快照） | 程序可见结果（退出码/输出）或结构 `CHECK` | CodeGen lit（结构）、m3/m4/m6 e2e、Embench、libc-test、llvm-test-suite、ir-lli 差分 |
| **U** | 工具单测 Unit | **测试基础设施自身**（harness、校验器、oracle 模型、生成器） | 自测/注入用例；不判定 ISA 语义 | `test_harness_exit_path.py`、`test_encoding_oracle.py`、各 `check_* --self-test` |

**归属判据（机械，按顺序问）**：

1. 判的是**工具/脚本自身**对不对？⇒ **U**。
2. 判的是**单条指令/短序列**（含编码往返、单指令语义）？⇒ **I**。
3. 需要**机器/特权/设备/OS 接口**才成立（bootrom、semihosting、异常/陷阱、syscall）？⇒ **S**。
4. 其余（从源/IR 到运行，或 IR→汇编结构）⇒ **E**；E 内用 `judgement: structural | execution` 区分「只看结构」与「真跑」（对应 `Process-05` 的 L2/L3）。

> **混合载体按「判据」归层，不按语言**：`tests/atomics/*.c` 是 C 程序，但断言是 `lr/sc`/`fence` 的单指令语义 ⇒ **I**；`tests/llvm/codegen/m6/*.ll` 断言是程序退出码 ⇒ **E**。

> **E 层边界（待用户裁定，§7.9）**：前册把 E 定义为「Linux/busybox 级整机端到端」并推到下一里程碑；本册把现行的 CodeGen/ELF/Embench/libc-test 等「**程序级**端到端」也放进 E。若用户要求严格区分，建议拆 **E1（程序级）** / **E2（整机级）**，届时目录为 `E/program/**` 与 `E/system/**`。

### 3.2 目录树（迁移完成后；`←` 表示来源）

```
tests/
├── README.md                  # 索引 + 怎么跑 + 产物去哪 + 覆盖矩阵指针
├── INVENTORY.md               # 迁移期保留；迁完可降级为「迁移对照表」或删除
├── manifest/
│   ├── schema.md              # 索引 schema（§3.4）
│   ├── I.yaml  S.yaml  E.yaml  U.yaml
│   └── coverage.yaml          # 由 I.yaml + contracts/opcodes.yaml 派生（不手写）
├── I/                         # 指令级源
│   ├── isa/*.yaml             # ← tests/vectors/isa/
│   ├── ext/{rol,atomics,clmul,rev,bitcnt}/*.yaml       # ← tests/vectors/{rol,atomics,clmul,rev,bitcnt}/
│   ├── asm/mc/*.s             # ← tests/llvm/lit/MC/DADAO/
│   ├── asm/mc-gen/*.s         # ← tests/llvm/lit/MC/DADAO-gen/
│   └── probe/{atomics,clmul,fma,minmax,roundint}/*.c   # ← tests/{atomics,clmul,fma,minmax,roundint}/
├── S/                         # 系统级源
│   ├── boot/{bootrom.S,bootrom_app.S,*.lds}            # ← tests/scripts/
│   ├── semihost/{*.s,expected.yaml}                    # ← tests/llvm/codegen/m5/
│   ├── system/<cfx>/*.yaml                             # 规划落点：cfx 场景向量（前册冻结口径，§7.9）
│   └── minrom/*.py                                     # ← tools/qemu/min_rom_probe_*.py（若按「测试源」归位）
├── E/                         # 端到端源
│   ├── codegen/{m3,m4,m6}/                             # ← tests/llvm/codegen{,/m4,/m6}
│   ├── struct/*.ll|*.mir                               # ← tests/llvm/lit/CodeGen/DADAO/
│   ├── lit/*.test                                      # ← tests/e2e/lit/
│   └── suites/{ir-lli,embench,libc-test,llvm-ts}/      # ← tests/llvm/ir-lli/、驱动清单
├── U/                         # 工具单测源
│   ├── harness/test_harness_exit_path.py               # ← tests/scripts/
│   ├── validate/{test_encoding_oracle,test_m1_asm,test_anti_forgery}.py
│   └── dump/verify_harness_dump.py                     # ← tests/scripts/
├── harness/                   # 共享 harness（构建/运行/聚合；非层）  ← tests/scripts/*.py
├── fixtures/                  # 二进制夹具：trampoline.bin、crt0、lds    ← tests/scripts/
└── (无 .dadao/：生成物另树，见 §4)
```

**留位规则**：

- **工具与模型不进 `tests/`**：生成器、driver、独立 oracle 模型（`tools/testcases/generate_*.py`、`oracle_*.py`、`run_*_probe.py`）留在 `tools/`；`tests/` 只放**源与期望**（与 LLVM「test 在源树、harness 在工具」一致）。
- **`fixtures/` 与 `harness/` 不参与层级**，是横切资产；`manifest` 用 `requires:` 引用。
- **组件优先例外**：若决策保留 `tests/llvm/`（§7 第 2 项），则 `I/asm`、`E/struct`、`E/codegen` 三处不迁，其余照上表。

### 3.3 ID 规则（MUST）

```
单元 ID  = {层}-{族}-{名}
    层 ∈ I|S|E|U
    族 ∈ isa|asm|probe|boot|semi|minrom|cg|struct|lit|suite|harness|oracle|validate|dump
    名 = 稳定标识：opcode id（向量册）、文件名 stem（lit/程序）、suite 名
用例 ID  = {单元 ID}#{册内序号}      # 1-based；= 该用例在册内的位置（与 case-ledger 的 ordinal 列含义不同：后者是同内容出现序号）
```

- 示例：`I-isa-reg-arith`（册级；覆盖的身份写进 `covers`）、`I-asm-rrrr`、`S-semi-m5_semi_exit`、`E-cg-m6_multi_return`、`E-struct-fp-codegen`、`E-suite-embench`、`U-harness-exit-path`。
- **唯一性**：跨 manifest 全局唯一（`check-tests-manifest` 断言）；**永不复用**已删除的 ID。
- **稳定性**：ID 不含层内序号、不含路径、不含里程碑号 ⇒ 文件搬家不改 ID（这是「索引先行」的前提）。
- **可反查**：ID 必须能反查到 `source` + `selector` + 覆盖的 opcode 身份。

### 3.4 索引 schema（`tests/manifest/<layer>.yaml`，MUST）

一个 manifest = 一层；`entries` 是**单元**（不是逐用例——1,456 条用例不复制进清单，靠 `source` + `selector` 定位）。

```yaml
schema: dadao-tests-v1
layer: I
entries:
  - id: I-isa-reg-arith
    title: 整数加减（含 64→128 双目的）
    kind: vector                      # vector|lit|program|driver|unit
    source: tests/I/isa/reg-arith.yaml
    selector: {ids: [add.uo_rrrr_rd, sub.uo_rrrr_rd]}   # 可空 = 整册
    judgement: semantic               # encoding|legality|structural|semantic|system|exit-code
    covers: [add.uo_rrrr_rd, sub.uo_rrrr_rd]            # opcode 身份（⊆ opcodes.yaml）
    oracle: {kind: independent, ref: tools/testcases/generate_isa_vectors.py}
    run: {target: check-qemu-semantics, layer: L3, args: {vectors: <source>}}
    tier: [L2, L3]                    # 出现在哪些门控层
    status: active                    # active|deferred|manual|orphan
    # status: deferred 时必填 deferred_reason: "..."
    migrated_from: tests/vectors/isa/reg-arith.yaml
```

| 字段 | 必填 | 机械断言 |
|---|---|---|
| `id` | ✔ | 匹配 §3.3 正则；全局唯一；不复用 |
| `title` | ✔ | 非空，≤60 字符 |
| `kind` | ✔ | 枚举内 |
| `source` | ✔ | 路径存在；**且恰好被一个 entry 引用**（双向闭包） |
| `selector` | ✘ | 引用的 `ids` 必须在 `source` 内出现 |
| `judgement` | ✔ | 枚举内；`structural` 不得声明 `execution` 专属字段 |
| `covers` | ✘ | ⊆ `contracts/opcodes.yaml::id`；**覆盖率投影的唯一来源** |
| `oracle` | ✔ | `kind: independent` 时 `ref` 存在且**不 import** 组件产物（源码级 grep） |
| `run.target` | ✘ | 出现在 `Makefile` 目标表；`status: active` 且非 manual 时必填 |
| `run.layer` | ✘ | ∈ L1/L2/L3；层归属以 `Makefile`/`Process-07` 为准（`tier` 可含多层） |
| `tier` | ✔ | 非空子集；`manual` ⇒ 允许空 |
| `status` | ✔ | 枚举内；`deferred` ⇒ `deferred_reason` 非空 |
| `migrated_from` | ✘ | 迁移期必填（旧路径），迁完删除 |

**闭包断言（反腐烂核心，`lessons §2.21`）**：

- `tests/**` 下每个「测试源」文件**恰好**被一个 entry 的 `source` 覆盖；
- 反向：每个 `source` 指向真实文件；
- `covers` 的并集 = 覆盖矩阵行；未覆盖身份**显式列出**（`allow_uncovered:` 带理由），不得静默缺席。

### 3.5 独立 oracle 规则（MUST，承接 `Process-05 §4`）

- 期望值只从 `spec/` + `contracts/` 派生；**不得**由 `llc`/`qemu`/参考实现输出生成（差分工具如 `diff_ir_lli` 只作**参照**，不作判据真源）。
- 模型脚本放 `tools/testcases/oracle_*.py`，**不 import** 任何组件产物（源码级断言，`check-tests-manifest` 可查）。
- 生成物期望带 `generated_by`（脚本 + 版本）与 `spec_cite`；生成器必须提供 `--check`（重派生后逐字节比对），**并接入门控**（现状反例：`rev.yaml` 漂移未被发现，§5.3）。
- 生成器与产物**同仓同 PR**（AGENTS.md「生成器随产物保留」）。

### 3.6 门控分层（MUST）

| 层 | 新增/保留目标 | 内容 |
|---|---|---|
| **L1** | `check-tests-manifest`（新）、`validate-vectors`、`check-case-ledger`、`check-run-artifacts`、**U 层单测** | 结构闭包 / ID 唯一 / source 存在 / target 存在 / 覆盖投影一致 / harness 自测；**不跑被测语义** |
| **L2** | `check-qemu-smoke`（I 代表集）、`check-qemu-system`（S 场景，前册规划）、`check-lit`、`test-codegen`、`test-elf`、`test-semihost`、4 个 `check-*-probe` | 各层**机械派生**的代表集（禁手挑，`Process-07 §3`） |
| **L3** | `check-qemu-semantics`（I 全量）、`check-lit-full`、`test-m6`、`check-testcases-suites{,-full}` | 全量/大套件 |
| 按需 | m6 codegen/ELF、atomics probe、min-ROM 探针 | 升层或标 `manual`（§7 第 7 项） |

- **U 层必须进 L1**：它是「门控的门控」，成本秒级；现状 4 个单测脚本不在任何门控（`INVENTORY §5.3`）属缺陷。
- **层间不重复**（`Process-07 §4`）：同一 entry 可声明多个 `tier`，但同一目标只在**一层**直接列出。
- 每个目标必须**可达 FAIL**（`Process-07 §5`）；索引门控的注入 = 删一个 entry / 改一个 `source` / 加一个未覆盖身份。

### 3.7 runner（`tools/testcases/run_tests.py`，建议接口）

```sh
python3 tools/testcases/run_tests.py list [--layer I|S|E|U] [--status active]
python3 tools/testcases/run_tests.py run  <id>[#n] [--json-out FILE] [--jobs N]
python3 tools/testcases/run_tests.py run  --tier L2 [--filter <regex>]
```

- `run` 只**解释** manifest 的 `run.target/args` 并调用既有 make 目标或 driver，**不重写判定逻辑**（单一真源在 driver）；
- 输出统一走 `Process-08` 的运行目录三件套；
- 子集跑**不得**写 `authoritative/`（`Process-08 §1.2`）。

---

## 4. 生成物落点：A / B 两案（不替用户决定）

### 4.1 A 案：`.work/build/tests/<layer>/<id>/`

| 维度 | 内容 |
|---|---|
| 形状 | `<repo>/.work/build/tests/{I,S,E,U}/<unit-id>/…`；运行目录仍按 `Process-08` 的 `<UTC>-<suite>-<档>/` |
| 优点 | ① 与 `.work/build/` 同域，语义就是「构建产物」；② `make clean-work` **天然清理**（无需新目标）；③ `.work/` 已整体忽略，无入库风险；④ 与 LLVM/QEMU 的「产物在构建树」一致 |
| 代价 | 改 `manifests/install-dirs.lock.toml` 的 `test_artifacts_dir` 语义或新增键；改 `tools/infra/paths.py`；改 `Makefile` 约 15 处变量（`CODEGEN_E2E_WORK`、`CODEGEN_ELF_WORK`、`SEMIHOST_E2E_WORK`、`IR_LLI_WORK`、`EMBENCH_E2E_WORK`、`QEMU_SEM_WORK`、`QEMU_SMOKE_WORK`、`BOOTROM_DIR`、`TEST_ARTIFACTS_DIR`…）；改 4 个 lit `lit.cfg.py` 的 `test_exec_root`；改 8 个 driver 的 `DEFAULT_WORK_DIR`；改 `check-run-artifacts` A2 扫描面；改 `docs/Process-05 §6`、`docs/Process-08 §1.1`、`ADR-0016 D6` |
| 风险 | ① **与已 Accepted 的 `ADR-0016 D6` + 用户 2026-10-06 裁定冲突**，须 ADR 修订（逐条确认）；② `clean-work` 会连「可检视证据」（运行目录、lit 输出）一起删，跨任务追溯变难；③ `.work/tests/authoritative/`（权威跑）已在 `.work/` 下，A 案会把「一次性构建」与「权威证据」混在一棵会被清的树里；④ 若 `.work` 被清，`check-run-artifacts` 的存量豁免基线也需重建 |

### 4.2 B 案：保留 `.dadao/tests/` + manifest / clean / 确定性

| 维度 | 内容 |
|---|---|
| 形状 | 不变（`test_artifacts_dir = .dadao/tests`）；新增 `.dadao/tests/artifacts.tsv`（生成物清单：路径 / 生成目标 / 可否重生成 / 保留策略；与 `tests/manifest/` 的**用例索引**不是一回事）与 `make clean-tests`（按清单删，白名单保留 `authoritative/`） |
| 优点 | ① **零架构改动**，与 ADR-0016 D6、`Process-05 §6`、`Process-08` 全部一致；② 证据留存（运行目录、lit 输出）在仓库旁，便于人工检视；③ `check-run-artifacts` 不动 |
| 代价 | 新增 `clean-tests` 目标 + 清单生成器（`tools/testcases/artifacts_manifest.py`）+ 文档说明「`.dadao` 不在 `clean-work` 内」；需处理 210 M 不可重生成孤儿 |
| 风险 | ① 1.2 G 长期驻留、易再膨胀（清单若漂移则清理失效，需门控反向断言）；② `.dadao/` 与 `.work/` 的「可删/不可删」边界易被误解（现状已如此）；③ 「产物不入库」靠 `.gitignore` 而非目录语义，误 `git add -f` 的风险仍在 |

### 4.3 对比与硬约束

| 判据 | A | B |
|---|---|---|
| 是否符合现行 ADR/裁定 | **否**（需改 D6） | **是** |
| 清理成本 | 零（沿用 `clean-work`） | 新增 `clean-tests`（一次性） |
| 证据留存 | 差（会被 `clean-work` 删） | 好 |
| 改动面 | 大（路径单一真源 + 8 个消费者 + 3 份文档） | 小（新增 1 目标 + 1 清单） |
| 与主流一致度 | 高（构建树） | 中（独立产物根） |
| 迁移风险 | 中（易漏改硬编码） | 低 |

> **推断（非事实）**：若用户目标是「长期把测试当构建产物、允许随时丢弃」，A 更干净；若目标是「保留可检视证据 + 不动 ADR」，B 代价更低。本册**不选**，见 §7 第 1 项。
> **混合案（B 的变体，供参考）**：构建中间物（`*.o`/`*.elf`/`*.bin`/lit 临时）落 `.work/build/tests/`，运行目录与摘要（`run.json`/`meta.json`）留 `.dadao/tests/`。代价居中，但需两套路径规则。

---

## 5. 确定性（逐字节可重生成）

### 5.1 条件（生成器/驱动 MUST 满足）

1. **顺序固定**：遍历 `sorted()`；不得依赖 `dict`/`set` 迭代序（必要时 `PYTHONHASHSEED=0`）。
2. **无时间戳**：产物内不得出现 `time.time()`/`datetime.now()`/主机名/用户名；`SOURCE_DATE_EPOCH` 若被工具读取，必须显式设定并记录。
3. **相对路径**：产物只含仓库相对路径（`tests/...`），不含绝对路径（`/mnt/...`/`/tmp/...`）。
4. **随机固定**：随机用例必须**固定种子并写入产物头**（如 `generate_clmul_vectors.py` 的 `SEED`）。
5. **格式固定**：LF 行尾、YAML `allow_unicode=True, width=120` 一类参数冻结、无 locale 依赖排序。
6. **工具链固定**：生成/编译用的工具来自安装根且版本由 `manifests/` 锁定；同一输入同一工具 ⇒ 同字节。
7. **ELF 无易变字段**：不写 `--build-id=random`、不嵌时间戳；DWARF 的 producer 串须固定（实测见 5.3）。
8. **运行脚手架排除**：lit 的 `.lit_test_times.txt`、运行目录的 `meta.json`（含 UTC 起止）**按定义**不可逐字节复现 ⇒ 确定性判据只覆盖**入库的生成物**。

### 5.2 `make test-repro` 判据（MUST）

```
对 manifest 中每个 reproducible: true 的条目：
  1) 在 $TMP/repro/<unit-id>/ 用文档化命令重生成（--out/--check 优先）
  2) cmp -s <重生成> <入库>  ⇒ 逐项打印 "PASS/FAIL  <id>  expected=byte-identical actual=..."
  3) 任一 FAIL ⇒ 目标 rc≠0（fail-closed；禁 tee 吞码，用 ; rc=$?）
  4) 跑完断言 git status --porcelain -- tests 为空（证明重生成没有改写源树）
```

- `--inject` 自检：临时副本改 1 字节 ⇒ 必须 FAIL；还原 ⇒ 回绿（`cp` + md5，禁 `git checkout/restore/stash`）。
- **计数现场派生**：条目数 = manifest 中 `reproducible: true` 的条数，不写死。

### 5.3 已实测事实（本册现场）

| 对象 | 命令 | 结果 |
|---|---|---|
| `tests/case-ledger.tsv` | `check_case_ledger.py --write --ledger /tmp/…/regen.tsv` + `cmp` | **byte-identical**（双方 md5 `ffb154cdfbaa0d2b25e5b4493a76d392`） |
| `rol/rol.yaml` | `generate_rol_vectors.py --check` | **PASS**（64 例，byte-identical） |
| `atomics/*.yaml` | `generate_atomics_vectors.py --check` | **PASS**（108 LR/SC + 19 fence，byte-identical） |
| `clmul/clmul.yaml` | `generate_clmul_vectors.py --check` | **PASS**（81 例，byte-identical） |
| `bitcnt/bitcnt.yaml` | `generate_bitcnt_vectors.py --check` | **PASS**（414 例，byte-identical） |
| `rev/rev.yaml` | `generate_rev_vectors.py --check` | **FAIL**：62/62 例 `spec_cite` 由 `SimRISC-04: Bit manipulating：位操作指令` 漂为 `SimRISC-04: rev.o`；其余字段全等 ⇒ **生成器确定，入库文件陈旧**（因 `rev` 不在门控，无人发现） |
| `trampoline.bin` | 重新执行 `generate_trampoline()` 比对 16 B | **一致**（`4e0500ff 4a06fc00 4e0afc00 71080000`） |
| `llvm-mc` 两次同输入 | `rrrr.s → .o` ×2 | **byte-identical**（md5 `b23de33a77fb2f04f04526d15b5d2e38`） |
| `ld.lld` 两次同输入 | `crt0.o + main.o → .elf` ×2 | **byte-identical**（md5 `0bf125937df64ca9d3414a552aacbf0f`） |

**未测（如实标注）**：除上表 5 个带 `--check` 的生成器外，另有 5 个可执行生成器**无 `--check`**（`generate_{mem,ctrl_br,ctrl_jump_call_ret,misc}_vectors.py`、`generate_lit_vectors.py`，就地写盘）；`generate_isa_vectors.py` 无 `__main__`（库）。这些均未验证；全部 lit 输出、全部运行目录产物、`.dadao/tests/**` 的重生成确定性均**未测**；`Werror`/`-g` 下的对象确定性未测。

**结论**：确定性的瓶颈**不是随机性**，而是「**生成器有 `--check` 却不在门控**」（`rev` 反例）与「**生成器只能就地写盘**」（无 `--out`/`--check` 的 5 个）。

---

## 6. 迁移分期（先索引，后搬家）

| 期 | 内容 | 交付 | 每期门控 | 回滚 |
|---|---|---|---|---|
| **P0 索引 + runner**（不动文件） | 写 `tests/manifest/{I,S,E,U}.yaml` + `schema.md`；`tools/testcases/run_tests.py`（list/run）；`check-tests-manifest`（L1，闭包/唯一/覆盖投影）；`tests/README.md` | 索引覆盖 `tests/**` 100%（含 `manual`/`orphan` 状态）；现有 21 目标行为不变 | `make check`（含新门控）+ 受影响 L2 抽跑 + `git status` 干净 | 删 3 个新文件即可（无文件移动） |
| **P1 I 层** | 迁 `vectors/**`、`lit/MC/**`、5 组探针源到 `tests/I/**`；同步 6 处路径（Makefile、生成器 `OUT`、`inventory.md` 表、driver 默认值、`check-case-ledger` 扫描面、文档） | I 层文件到位；`case-ledger` 行数不变（1,956） | L1 `check-tests-manifest`+`validate-vectors`+`check-case-ledger`；L2 smoke；L3 semantics 数量不变 | 单 commit revert（源全在 git） |
| **P2 S 层** | 迁 m5/bootrom 夹具到 `tests/S/**`；把 `min_rom_probe_044/045/047/049` 与 atomics probe **接线或标 `manual`** | S 层有明确 runner 或显式 `manual` | L2 `test-semihost` + probe 目标 | revert |
| **P3 E 层** | 迁 `llvm/codegen/**`、`lit/CodeGen/**`、`e2e/lit/**`、`ir-lli` 清单到 `tests/E/**`；m6 codegen 接线；9 个死源处置（§7 第 6 项） | E 层全自动或标 `manual`；覆盖矩阵单一入口 | L2 `test-codegen`/`test-elf`/`check-lit`；L3 `test-m6` | revert |
| **P4 清理** | 删 9 个 `.pyc`；处置孤儿产物（§7 第 5 项）；`clean-tests`（若 B 案）；发布 `manifest/coverage.yaml` | 目录与 §3.2 一致；`INVENTORY` 降级 | `make check` + `check-run-artifacts` + 体积报告 | 逐项 revert |

**分期硬规则**：

- 每期**只做一层**；跨期共享文件（`Makefile`、`case-ledger.tsv`、`check_case_ledger.py` 扫描面）**串行**改。
- 每期结束必须重算 `INVENTORY` 锚点（本册证据脚本即模板）。
- 迁移**不改判定语义**：期望值/用例数/门控通过集在迁移前后必须相同（用 `case-ledger` 行数 + 门控日志比对）。

---

## 7. 待用户决策清单

> 每项只列选项与影响，**不预设答案**。第 1–4 项为任务书点名项；第 5–8 项为本册新增（不打勾不影响 P0）。

### 7.1 生成物落点（A / B / 混合）

- **A** `.work/build/tests/<layer>/<id>/`：需改 `ADR-0016 D6` + `Process-05 §6`（用户 2026-10-06 裁定），`clean-work` 会自动清；证据不留存。
- **B** 保留 `.dadao/tests/`：零 ADR 改动；需新增 `clean-tests` + 生成物清单；1.2 G 长期驻留。
- **混合**：中间物进 `.work/build/tests/`，运行目录留 `.dadao/tests/`；两套路径规则。
- **影响面**：`tools/infra/paths.py`、`Makefile`（约 15 处）、4 个 lit cfg、8 个 driver 默认值、`check-run-artifacts` A2、3 份文档。

### 7.2 `tests/llvm/` 归属

- **保留组件优先**（现状 `tests/llvm/{lit,codegen}`）：改动最小；但与 I/E 分层交叉（同一目录跨两层）。
- **按层拆分**（`tests/I/asm`、`tests/E/{struct,codegen}`）：层次清晰；迁移面最大（216 文件 + 5 处路径 + `ir-lli` `corpus_roots`）。
- **折中**：保留目录、在 manifest 用 `layer` 字段标注跨层，物理不搬。

### 7.3 `case-ledger.tsv` 是否继续作提交物

- **继续入库**：L1 可做「删用例哨兵」（现状）；缺点是 1,956 行生成物入库、每次加用例要重生成。
- **改为派生**：入库只留「身份集合摘要」（如排序后的 id+hash），门控现场重算比对；体积小，但失去逐行定位。
- **移入 manifest**：由 `I.yaml` 的 `selector` 反推；与索引合一，但需重写 `check_case_ledger.py` 判据。

### 7.4 确定性严格度

- **严格**：所有入库生成物（ledger + 5 组向量 + lit-gen + trampoline）全部 `--check`，接 L1；需先给 5 个「只能就地写」的生成器补 `--out`/`--check`。
- **仅产物**：只覆盖 `tests/**` 入库文件，不含运行目录/lit 输出（本册 §5.1 第 8 条口径）。
- **报告级**：`make test-repro` 只打印不判红（不作为门控）。
- **附带子问题**：`rev.yaml` 现漂移（62 例 `spec_cite`）——**修生成器输出**还是**回填旧 cite**？

### 7.5 孤儿生成物处置（`.dadao/tests/`，约 210 M 不可重生成）

- `llvm-ts-user-050t/`（209 M，`TESTCASES-048t` 历史一次性）、`libc-argv-{static,dynamic}/`（1.2 M）、`smoke/`（48 K，旧默认落点）。
- 选项：**删除**（不可复现，仅历史）/ **归档到仓库外备份**（需体积评估）/ **保留**（继续占 210 M）。

### 7.6 9 个无 runner 的 e2e 源

- `fp_codegen.c`、`fp_hfa.c`、`i1_load_e2e.c`、`large_const_cmp_e2e.c`、`mulhi_e2e.c`、`selectcc_e2e.c`、`setcc_e2e.c`、`smulhi_e2e.c`、`switch_jt_e2e.c`。
- 选项：**删除**（能力已由 lit/其他 e2e 覆盖，需逐条确认）/ **接回 `check-lit`**（补 `.test`）/ **标 `manual` 留档**。

### 7.7 手工资产是否升层

- `tests/atomics/*.c`（711/711 手工）、`tests/llvm/codegen/m6/*`（8 程序手工）、`min_rom_probe_044/045/047/049/061/070/071/072/074`。
- 选项：**升 L2/L3**（需先测成本）/ **保持按需但登记 `manual`**（manifest 可见）/ **归档**。

### 7.8 文档编号

- 本册取 `Process-09`（因 `Process-08` 已被《测试运行产物与日志组织规范》占用）。
- 选项：**接受 09** / **改号并调整 `docs/README.md`**（仅改名，无内容影响）。

### 7.9 E 层边界（与前册口径的差异）

- **前册**（`TESTCASES-067t-QEMU测试向量盘点与ISE组织.md`，已删）冻结：I=`tests/vectors/isa`、S=`tests/vectors/system/<cfx>` + `check-qemu-system`(L2)、**E=Linux/busybox（下一里程碑）**。
- **本册**：E 含现行「程序级端到端」（CodeGen/ELF/Embench/libc-test/llvm-test-suite/ir-lli）。
- 选项：**保持本册**（E=程序级+整机级，简单但粒度粗）/ **拆 E1/E2**（程序级 / 整机级，目录与门控各一套）/ **回到前册**（E 仅整机级，现行 CodeGen 等归入 I/S 或另立层）。
- **影响**：E1/E2 拆分会影响 `manifest/E.yaml` 的 `id` 族、L2/L3 归属与迁移分期的 P3。

---

## 8. 与其它规范的关系

- `Process-05`（里程碑 TDD）：本册 §3.5 承接其「独立 oracle」与「L1/L2/L3 向量」口径；E 层的 `structural` 对应其 L2，`execution` 对应 L3。
- `Process-07`（门控分层）：本册 §3.6 只给**成员归属**，分层判据与触发点以 07 为准。
- `Process-08`（运行产物/日志）：本册不重复三件套/命名/权威跑规则；§5.1 第 8 条的「排除运行脚手架」是对其 §1.1 的补充口径。
- `ADR-0016 D6`：生成物根的唯一真源；A 案须先修订。
- `AGENTS.md`：`Spec-first`、`Independent oracle`、`验证脚本反例门控` 在本册 §3.5/§5.2 落地。
