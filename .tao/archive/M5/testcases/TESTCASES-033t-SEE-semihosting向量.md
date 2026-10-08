# TESTCASES-033t: SEE/HEE + semihosting 向量（L1 MC + L3 执行；独立 oracle）

**模块**：testcases
**项目里程碑**：M5
**依赖**：`SPEC-114t`、`SPEC-115t`、`LLVM-060t`、`INFRA-048t`、`QEMU-044t`、`QEMU-045t`、`QEMU-046t`、`QEMU-047t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `SPEC-114t`（SEE/semihosting 正文）+ `SPEC-115t`（`trap`/`escape`/`cfx2rc`/`cfx2rd` re-scope + `contracts/opcodes.yaml`）+ `.tao/adr/adr-0020-see-semihosting.md`（`Accepted`）。
  - `LLVM-060t`（MC 编码支持；**L1 MC 向量依赖它**）+ `INFRA-048t`（落点 `.dadao/tests/`）+ `QEMU-047t`（**新 bootrom**：生成物 `.dadao/tests/bootrom/bootrom.bin` + `-bios` 加载路径；**L3 执行向量的启动器/模式·向量配置来源**）。
  - `spec/Process-05-里程碑TDD规范.md`（§2 L1/L2/L3；§3「一能力一向量」；§4 期望值**独立派生**；§5 反例门控；§6 落点）；`contracts/opcodes.yaml`（L1 期望编码来源）。
  - `spec/SimRISC-11-其它.md`（4 条形式）、`spec/DADAO-12 §5`（异常进入/退出）、`spec/DADAO-22 §1/§3`（调用约定/初始化）、`.tao/knowledge/contract-abi.md §4.1/§4.4`（传参/返回）。
  - 既有 `tests/llvm/lit/MC/DADAO/`（`validate_mc_vectors.py` oracle）与 `tests/llvm/codegen/`（L3 驱动模式）；既有驱动 `tools/integ/run_codegen_e2e.py`/`run_elf_e2e.py`（**`run_m5_e2e.py` 复用其结构**：清单 → 自有工具链编 bin → `-bios`+`qemu` 跑 → 逐例比对 → `--inject` 反例自检）。
- **输出**：
  - **L1 MC 向量**：落 `tests/llvm/lit/MC/DADAO/`（如 `m5-trap-escape-cfx2.s`）——`trap`/`escape`/`cfx2rd`/`cfx2rc` 编码与往返；**分阶段**：`LLVM-060t` 就绪前以 lit **`UNSUPPORTED:`** 标记暂缓（`Process-05`；`LLVM-060t` 完成后**去除**标记）。期望编码**独立派生自 `contracts/opcodes.yaml`**（**禁**从 `llvm-mc` 反推）。
  - **L3 执行向量**：落 `tests/llvm/codegen/m5/`（独立 m5 清单 + `expected.yaml`）——**承载形态 = bin**（`llc`/`llvm-mc` → `objcopy -O binary` → `qemu`；**不经 `ld.lld` 多 TU ELF**——用户 2026-10-08 M5 范围简化裁定，见下「承载形态裁定」）跑通：① **semihosting 服务**（≥ console `WRITEC/WRITE0/WRITE` + `EXIT`/`EXIT_EXTENDED`；`READC` 可 host 输入桩）；② **权限反例（cfx 级可观测；M5 无 PTBR 权限层）**（reserved cfxha / mask 禁止 ⇒ `ILLI`〔含 reserved〕；未实现 cfx / 不存在或超数量寄存器组合 ⇒ `CFXREG`；**`NUPERM/NJPERM/NSPERM/NHPERM` 属 `DADAO-12 §2.2` PTBR 权限层、不在 M5**〔`ADR-0020 D9`〕）；③ **一条一般 trap 进入向量 + escape 返回**。**期望值独立派生自 spec/契约**（**禁**从 QEMU 反填）。
  - **L3 运行方式（与 M5 门槛口径一致；用户 2026-10-08 裁定）**：`qemu-system-dadao -M dadao-m1 -bios <bootrom.bin> -kernel <vec.bin> -semihosting-config enable=on,target=<native|gdb>`；`<bootrom.bin>` = `QEMU-047t` 产物 `.dadao/tests/bootrom/bootrom.bin`（**经 `tools/infra/paths.py::test_artifacts_dir()`/`BOOTROM_DIR` 解析，禁硬编码**），`<vec.bin>` 由**自有工具链**（`llvm-mc`/`llc` → `llvm-objcopy -O binary`）产生。**L3 全部用例均经 `-bios` bootrom**（bootrom = 唯一应用入口/启动器：复位 PC=`0xffff_ffff_0000`，须由 bootrom 完成模式/向量/栈初始化后 hypv→user 跳应用——**无 `-bios` 则应用无入口、不执行**）；若认为某例无需 bootrom，**须写出依据**（该例如何获得入口/模式配置）**供裁定，不得静默采用**（依据见「审阅记录 · 下发前预检修订」）。
  - **m5 L3 驱动**：**新建 `tools/integ/run_m5_e2e.py`**（复用既有 runner 结构：读 m5 清单 → 自有工具链编 bin → `qemu -bios <bootrom> -kernel <bin> -semihosting-config …` → 逐例比对期望退出码/故障码 → `--inject` 反例自检；对 `run_codegen_e2e.py`/`run_elf_e2e.py` **只复用结构、不改其 M3/M4 门控**）；本任务内**直接 `python3` 调用**（`Makefile`/`make test-semihost` 接线归 `INTEG-020t`，本任务**不改 `Makefile`**）。
  - **独立 oracle**：扩展 `tools/testcases/validate_mc_vectors.py` / 新增 `validate_elf_vectors.py` 派生（复用 `029t`/`030t` 共享 validator，`Process-05 §6`）；**不调用** `llvm-mc`/`llc`/QEMU 作为期望来源。
  - `tests/llvm/lit/MC/DADAO/README-m5.md`（向量 ↔ 能力 ↔ 期望值来源对照）。
- **门控时序（`Process-05` TDD）**：向量**先立**；L1 暂缓用 `UNSUPPORTED:`（**不接门控**），由 `LLVM-060t` 完成后（或 `INTEG-020t` 收口时）去除标记接入 `check-lit`；L3 落 m5 独立清单（`make test-codegen`/`test-elf` 的 M3/M4 驱动**不读**，避免误接）。
- **约束（硬）**：
  - **期望值独立派生**（`AGENTS.md`「Independent oracle」；`Process-05 §4`）；**不得**从 LLVM/QEMU 反填。
  - **规模 ∝ 能力**（「一能力一向量」），手写少量、可审计；**禁**批量迁移。
  - **向量须能对反例失败**（`Process-05 §5`）：每条向量有可达 FAIL 路径（**逐条**核对，避免恒真/两支同值）。
  - **允许改动文件集（越界须披露）**：`tests/llvm/lit/MC/DADAO/**`、`tests/llvm/codegen/m5/**`、`tools/testcases/validate_*.py`、`tools/integ/run_m5_e2e.py`、**本任务书**；`.work/evidence/TESTCASES-033t/**`（gitignored、非入库）。
  - 不改 `contracts/**`/`components/**`/`Makefile`/`spec/**`；临时目录 `/tmp/opencode/TESTCASES-033t/`；**不提交 git**；复杂命令输出留存 `.work/log/testcases/`（**禁 `tee`**）。
  - **重建成本申报**：L3 需 `build-mc`/`build-lld`/`build-qemu`（增量，`build-qemu` 5–20 分钟）；开工前说明。

## 验收标准

1. **L1 向量**：`tests/llvm/lit/MC/DADAO/` 含 4 条指令编码/往返向量（`LLVM-060t` 就绪前带 `UNSUPPORTED:`）；`make check-lit` EXIT=0 且新向量被正确处理（unsupported 或 PASS）。
2. **L3 向量**：`tests/llvm/codegen/m5/` 含 semihosting 服务（≥3 类）/权限反例（**cfx 级可观测**：`ILLI`〔含 mask 禁止/reserved〕/`CFXREG`〔未实现 cfx / 不存在或超数量寄存器组合〕，≥3 类）/一般 trap+escape 各 ≥1；给出「向量 ↔ 能力 ↔ 期望值来源」表。
3. **独立 oracle**：`python3 tools/testcases/validate_*.py` EXIT=0；oracle **无** `subprocess`/`os.system`/`Popen`（`grep` 核实）；期望值可独立重算。
4. **L3 执行**：经 m5 驱动（`python3 tools/integ/run_m5_e2e.py …`）跑通，逐例「名字/期望/实际/退出码」；**逐例给出实际 qemu 命令行（含 `-bios`）**，并核**复位 PC/bootrom 生效**（`-d cpu` 首块 `PC=0xffff_ffff_0000` 或等价，含「模式/向量配置生效」观测）；给真实输出（`.work/log/testcases/`）。
5. **反例门控**：对注入反例（改一条期望字节 / 改一条服务号 / 改一条**权限期望**〔cfx 级：改 `ILLI`/`CFXREG` 期望码〕）⇒ oracle/驱动器**非零退出**；还原后回绿（真实输出）。
6. **门控**：`make check`/`make check-lit` EXIT=0；`make check-no-residue` EXIT=0。
7. **一键证据脚本**：`.work/evidence/TESTCASES-033t/run.sh`——非交互、失败非零、逐项打印、≥2 类注入自检、结尾**禁 `tee`**。
8. **无残留**：`git status --untracked-files=all` 仅新增向量 + oracle + `tools/integ/run_m5_e2e.py` + README + 本任务书。

## 完成区

**测试结果**：**通过**。独立 oracle `tools/testcases/validate_m5_vectors.py` **PASS（141 checks）EXIT=0**（其余 `validate_{vectors,mc_vectors,codegen_vectors,elf_vectors}.py` 亦 EXIT=0；oracle **无**子进程导入，`grep` 0 命中）；M5 驱动 `tools/integ/run_m5_e2e.py` **10/10 PASS**（`run_m5_e2e: PASS`，EXIT=0）；L1 `make check-lit` **62/62 EXIT=0**；一键证据脚本 `.work/evidence/TESTCASES-033t/run.sh` **`EVIDENCE: PASS` / `SCRIPT_EXIT=0`**（4 类注入各自 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿）；`make check` **EXIT=0**（30s，含 `check-patch-tree: 2 component(s), 92 patches OK`、`check-qemu-semantics: PASS`、`check-no-residue: PASS`、lit 62/62）。

**修改文件**（与 `git status --untracked-files=all` 一致；`.work/**`、`.dadao/**` gitignored 不入库）：
- `tests/llvm/codegen/m5/m5_semi_writec.s`（新）— `SYS_WRITEC` 单字符
- `tests/llvm/codegen/m5/m5_semi_write0.s`（新）— `SYS_WRITE0` NUL 串
- `tests/llvm/codegen/m5/m5_semi_write.s`（新）— `SYS_OPEN`(mode 4) + `SYS_WRITE`
- `tests/llvm/codegen/m5/m5_semi_exit.s`（新）— `SYS_EXIT`
- `tests/llvm/codegen/m5/m5_semi_exit_extended.s`（新）— `SYS_EXIT_EXTENDED`
- `tests/llvm/codegen/m5/m5_perm_reserved_illi.s`（新）— reserved cfxha ⇒ `ILLI`
- `tests/llvm/codegen/m5/m5_perm_mask_illi.s`（新）— 指令类型 mask 禁止 ⇒ `ILLI`
- `tests/llvm/codegen/m5/m5_perm_unimpl_cfxreg.s`（新）— 未实现 cfx ⇒ `CFXREG`
- `tests/llvm/codegen/m5/m5_perm_badcombo_cfxreg.s`（新）— 超数量寄存器组合 ⇒ `CFXREG`
- `tests/llvm/codegen/m5/m5_trap_escape.s`（新）— 一般 trap 进向量 + `escape` 返回
- `tests/llvm/codegen/m5/expected.yaml`（新）— 独立 m5 清单（schema `m5-vectors-v1`）
- `tests/llvm/codegen/m5/README.md`（新）— m5 目录说明
- `tests/llvm/lit/MC/DADAO/README-m5.md`（新）— 向量 ↔ 能力 ↔ 期望值来源对照 + **L3 实际 qemu 命令行**
- `tools/integ/run_m5_e2e.py`（新，**随产物入库**）— M5 E2E 驱动（`-bios` bootrom + bin + semihosting）
- `tools/testcases/validate_m5_vectors.py`（新，**随产物入库**）— M5 独立 oracle
- `.work/evidence/TESTCASES-033t/run.sh`（gitignored，非入库）
- `.work/log/testcases/TESTCASES-033t-*.log`（gitignored，非入库）
- 生成物 `.dadao/tests/m5-e2e/**`（gitignored，非入库）
- 本任务书（完成区/自审/状态）
- **未改** `contracts/**`/`components/**`/`Makefile`/`spec/**`

**验收结果**（真实命令输出/rc，日志在 `.work/log/testcases/`）：
1. **L1 向量**：`tests/llvm/lit/MC/DADAO/cfx2-trap-escape.s`（+ `-err.s`）由前置 `LLVM-060t` 自带并已接入门控，覆盖 `trap`/`escape`/`cfx2rd`/`cfx2rc` 的**编码 + 往返**；`make check-lit` **EXIT=0**（`Total Discovered Tests: 62 / Passed: 62`）。本任务**复用**（不重复文件；见「新发现 1」）。
2. **L3 向量**：`tests/llvm/codegen/m5/` 含 **10 条**：semihosting 服务 **5 条**（`WRITEC`/`WRITE0`/`WRITE` + `EXIT`/`EXIT_EXTENDED`）、cfx 级权限反例 **4 类**（`ILLI`：reserved / mask；`CFXREG`：unimpl / badcombo）、一般 `trap`+`escape` **1 条**。对照表见 `README-m5.md §2`。
3. **独立 oracle**：`python3 tools/testcases/validate_m5_vectors.py` → `validate_m5_vectors: PASS (141 checks)` **EXIT=0**；`grep -nE '(^|[^A-Za-z_.])(import[[:space:]]+subprocess|from[[:space:]]+subprocess|os\.system\(|Popen\()' tools/testcases/validate_m5_vectors.py` **0 命中**（EXIT=1）；期望值由 contract-semihosting §3 服务表 + contract-see §3 规则 + 向量 `@m5` 输入**独立重算**。
4. **L3 执行**：`python3 tools/integ/run_m5_e2e.py` → **10/10 PASS**，逐例打印「名字/期望/实际/退出码」与**实际 qemu 命令行（含 `-bios`）**；逐例核 bootrom 生效：`[bootrom] reset PC ok; bootrom user vector set; app entered user mode`（`-d cpu` 首块 `PC: 0000ffffffff0000` + `CFX00 M0 ... VEC:0000ffffffff0200` + 应用 `MODE: 0`）。逐例结果：
   ```
   PASS m5_semi_writec expected=64 actual=64   PASS m5_perm_reserved_illi expected=80 actual=80 cause=ILLI
   PASS m5_semi_write0 expected=65 actual=65   PASS m5_perm_mask_illi     expected=81 actual=81 cause=ILLI
   PASS m5_semi_write  expected=66 actual=66   PASS m5_perm_unimpl_cfxreg expected=82 actual=82 cause=CFXREG
   PASS m5_semi_exit   expected=67 actual=67   PASS m5_perm_badcombo_cfxreg expected=83 actual=83 cause=CFXREG
   PASS m5_semi_exit_extended expected=68 actual=68   PASS m5_trap_escape expected=96 actual=96 cause=CFXTRAP
   Results: 10/10 passed, 0 failed
   ```
   逐例实际命令行（示例，全 10 条见 `.work/log/testcases/TESTCASES-033t-ev-run_m5_e2e_py_.log`）：
   ```
   .dadao/cross-toolchain/bin/qemu-system-dadao -M dadao-m1 \
     -bios .dadao/tests/bootrom/bootrom.bin \
     -kernel .dadao/tests/m5-e2e/m5_perm_reserved_illi.bin \
     -semihosting-config enable=on,target=native,chardev=semi \
     -chardev file,id=semi,path=.../m5_perm_reserved_illi.console \
     -display none -nographic -d cpu -D .../m5_perm_reserved_illi.cpu.log
   ```
5. **反例门控**：`.work/evidence/TESTCASES-033t/run.sh` 4 类注入（真实输出见日志）：A 改 `expected.yaml` 期望退出码（`0x40→0x41`）⇒ **驱动 EXIT=1**（`actual=64 != expected 65`）；B 改向量服务号（`0x03→0x06`）⇒ **oracle EXIT=1**（`m5_semi_writec:src-has-service-const`）；C 改权限期望码（`ILLI 0x0100→0x0004`）⇒ **oracle EXIT=1** 且 **驱动 EXIT=1**（`actual=225=0xE1`，即向量 fail 分支可达）；D 改 trap 期望码（`CFXTRAP 0x0001→0x0004`）⇒ **驱动 EXIT=1**（`actual=226=0xE2`）；每轮 `cp` 还原且 **md5 相等**（`e1d5942f…` / `71238c35…` / `63d2d490…` / `1de7e305…`）⇒ 回绿。全程**无 `tee`**（逐命令 `rc=$?` 直捕）。
6. **门控**：`make check` **EXIT=0**（30.6s；`.work/log/testcases/TESTCASES-033t-check.log`：`check-patch-tree: 2 component(s), 92 patches OK`、`check-qemu-semantics: PASS`、lit 62/62、`check-no-residue: PASS`、`repository checks: PASS`）；`make check-lit` **EXIT=0**；`make check-no-residue` **EXIT=0**。
7. **一键证据脚本**：`.work/evidence/TESTCASES-033t/run.sh` → **`EVIDENCE: PASS` / `SCRIPT_EXIT=0`**（`.work/log/testcases/TESTCASES-033t-evidence.log`）：非交互、失败非零、逐项打印、4 类注入自检、结尾 `rc=$?` 直判、**禁 `tee`**。
8. **无残留**：`git status --untracked-files=all` = 上列 15 个新文件（+ 本任务书）；无 `*_tmp*`/`*_gate*`/`*.orig`/`*.rej`/`*.preinject`；注入后工作树与注入前 md5 一致（`git status` 无残留改动）；生成物全在 `.dadao/tests/m5-e2e/`（gitignored）。

**新发现/坑**：
1. **L1 向量的落点归属**：`trap`/`escape`/`cfx2rd`/`cfx2rc` 的 L1 编码/往返向量由前置 `LLVM-060t` 自带（`cfx2-trap-escape.s` + `-err.s`），本任务**复用**而非重复（`spec/Process-05` 分阶段 + DRY）。M5 无新增 L1 向量。
2. **semihosting 控制台输出通道**：`target=native` **无 `chardev`** 时 `WRITEC`/`WRITE0` 输出到 **QEMU 进程 stderr**（不可与 QEMU 自身告警区分）；驱动据此加 `-chardev file,id=semi,path=…` + `chardev=semi` 落盘再比对。
3. **`.dadao/` 里没有 `BOOTROM_DIR`**：`tools/infra/paths.py` 只给 `test_artifacts_dir()`（=`.dadao/tests`）；bootrom 落点由 `build-bootrom` 决定 ⇒ 驱动用 `test_artifacts_dir() / "bootrom" / "bootrom.bin"`（**未硬编码**）。
4. **cfx cause id 取值（`-d cpu` / `cfx2rd` 回读）**：`CFXTRAP=1<<0`、`CFXREG=1<<2`、`ILLI=1<<8`（`DADAO-12 §4` monitor 异常原因表，一位）；M5 monitor（umon）`cause_nonmaskable=0x3f07` ⇒ 步骤 3–5 屏蔽对该三类 cause 不生效，异常必进入当前 mode monitor 向量（`QEMU-044t` 新发现 1）。
5. **应用可自读 `cfx_umon.cg5.rc2`（cause id）**：user 模式下 `cfxha==inner_cfx_code`（bootrom hypv→user 跳转后 `inner_cfx_code=0=umon`）⇒ 跳过 mask 检查，`cfx2rd cfx_umon, cg5, rc2` 可读 ⇒ 权限反例可在 guest 内自检、只暴露 host `$?`。
6. **`escape` 偏移 `4` 的返回 + bootrom 复用**：bootrom 的 umon user 向量（ROM+0x200）就是 `escape cfx_umon,[excp_cause_ip,4]`，一般 trap 与 ILLI/CFXREG 重定向都经它返回 ⇒ 反例向量无需自建 handler。
7. **`st.o` 的 wyde 位置易错**：`0x20026` 须 `set.zw rd8, wp1, 0x0002` + `or.w rd8, wp0, 0x0026`（**wp1**，非 wp2）；本次调试期因误用 `wp2` 一度致 `SYS_EXIT` 返回 1（`arg0 != ADP_Stopped_ApplicationExit`）。建议沉淀。

**遗留问题**：
- **`Makefile`/`make test-semihost` 接线归 `INTEG-020t`**（本任务按约束**不改 `Makefile`**）；本任务内以 `python3 tools/integ/run_m5_e2e.py` 直接驱动。⇒ `INTEG-020t` 复用本驱动（其输出 1 亦已按主会话判定改为复用 `run_m5_e2e.py`）。
- **oracle 的 `RULE_CAUSE`/`CAUSE_ID`/pass-token 表为带 contract 引用的硬编码（未从 `contract-see.md` 机械解析）**：服务表已从 `contract-semihosting §3` 机械解析（25 条）；权限规则/monitor cause 位为字面引用 + 硬编码，同 `validate_codegen_vectors.py`/`validate_elf_vectors.py` 的既有范式。
- **pass/fail token 为文档化约定**（`README-m5.md §2.3` + `PASS_TOKEN` 表）：退出码非契约派生语义，但语义主体（服务号↔名称、console 字节、cause id）为独立派生，且 token 与向量源常量双向核对。
- **无 PTBR 权限层**（`NUPERM/NJPERM/NSPERM/NHPERM`）不在 M5（`ADR-0020 D9`）；本任务权限反例一律 cfx 级（`ILLI`/`CFXREG`），已在 `README-m5.md`/`expected.yaml`/验收 2 标注。
- **不改 `spec/`**（本任务按预检结论 5）。
- 生成器随产物入库：`tools/integ/run_m5_e2e.py`、`tools/testcases/validate_m5_vectors.py` 均已入库；`.work/evidence/…/run.sh` 按任务书为 gitignored 非入库证据脚本。


## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**：逐行审查全部改动文件——10 条 `.s` 向量 + `expected.yaml` + `README.md` + `README-m5.md` + `tools/integ/run_m5_e2e.py` + `tools/testcases/validate_m5_vectors.py` + `.work/evidence/TESTCASES-033t/run.sh`；核对 Spec-first（`contract-see §3/§4`、`contract-semihosting §1–§5`、`Machine-01 §2`、`ADR-0020 D1/D3/D8/D9/D10/D14`、`ADR-0004 D2.3/R1/R3`、`DADAO-12 §2.1/§4/§5`）、边界（不改 `spec/`/`contracts/`/`components/`/`Makefile`）、防造假（真实执行、完成区逐条对齐、`run.sh` 无 `tee`、每条向量有可达 FAIL 分支）。

**结论**：逻辑正确、边界受控、证据真实；10 向量经 `-bios` bootrom E2E 全绿、4 类注入证明 oracle/驱动与向量 fail 分支均可失败。处置如下表（无未修 finding）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 L1 向量：`trap`/`escape`/`cfx2rd`/`cfx2rc` 编码/往返由 `LLVM-060t` 自带 | ⏸记录（复用，不重复；符合 `Process-05` 分阶段 + DRY；architect「重排落纸」已定归属） | 无（仅在 `README-m5.md §1` 登记对照表） | `make check-lit` 62/62 EXIT=0 |
| F2 `target=native` 无 `chardev` 时控制台落 QEMU stderr，与告警混淆 | ✅已修 | 驱动加 `-chardev file,id=semi,path=…` + `-semihosting-config …,chardev=semi` | `m5_semi_writec.console=41`、`m5_semi_write0.console=4f4b0a` 逐例比对 PASS |
| F3 oracle 的权限规则/monitor cause 位为硬编码（服务表已机械解析） | ⏸记录（带 contract 引用；同 `validate_codegen/elf_vectors.py` 范式） | 无（`RULE_CAUSE`/`CAUSE_ID` 注释标注 `contract-see §3`/`DADAO-12 §3/§4`/`DADAO-22 §3` 出处） | oracle 141 checks PASS；注入 B/C/D 均 FAIL |
| F4 `m5_trap_escape` 的 oracle 源文本检查（常量出现即过）对「两处同常量」不如驱动灵敏 | ⏸记录（oracle 事源文本一致性、驱动承担执行语义） | 无（在 `run.sh` 注入 D 注释注明该差异） | 注入 D 改 trap 期望码 ⇒ **驱动** EXIT=1（`actual=226=0xE2`），证 fail 分支可达 |
| F5 pass/fail token 为文档化约定（非契约派生语义） | ⏸记录（`README-m5.md §2.3` + oracle `PASS_TOKEN`；语义主体为独立派生） | 无 | oracle `exit-is-pass-token`/`manifest-exit==header`/`src-has-exit-const` 均 PASS；注入 A 改期望码 ⇒ 驱动 FAIL |
| F6 驱动硬编码 bootrom 用户向量串 `0000ffffffff0200`（QEMU-047t 专有） | ⏸记录（bootrom 生效观测的必要断言；README-m5 §2.1 注明 bootrom 来源） | 无 | 逐例 `[bootrom] reset PC ok; bootrom user vector set; app entered user mode` |
| F7 驱动逐例恒跑 `-d cpu -D <log>`（额外开销/磁盘） | ⏸记录（acceptance 4「复位 PC/bootrom 生效」观测必需；10 例 <1s/例） | 无 | 逐例 bootrom 检查 PASS；日志在 `.dadao/tests/m5-e2e/`（gitignored） |
| F8 断言可达 FAIL（逐向量） | ✅已证 | 10 向量 pass token 与 fail token 互异（`0x40..0x60` vs `0xE1`/`0xE2`）；`cmp.so`+`br.nz` 分支非恒真 | 注入 C（权限 `actual=225=0xE1`）/ D（trap `actual=226=0xE2`）证明分支真实可达 |

**边界核查**：仅新增任务范围内文件（`tests/llvm/codegen/m5/**`、`tests/llvm/lit/MC/DADAO/README-m5.md`、`tools/integ/run_m5_e2e.py`、`tools/testcases/validate_m5_vectors.py`、本任务书）；**`spec/` 交集空**；**未改 `contracts/**`/`components/**`/`Makefile`**；`.work/**`/`.dadao/**` 未入库。**状态**：无未修 finding ⇒ 置「待验收」，返回主会话 `/complete`。

#### 第 1 轮 reviewer 验收

**审查者独立验证**：证据脚本审核 + 重跑 + **独立注入一次反例** + oracle 独立性复核 + L3 实跑 + L1 复用 + 门控 + 边界 + 判决。

##### 1. 证据脚本 `.work/evidence/TESTCASES-033t/run.sh` 审核

**结论：合格。**

逐条核可达 FAIL 路径：
- **Injection A**（改 `expected.yaml` 期望退出码 `0x40→0x41`）：regex 匹配 `name: m5_semi_writec` 块的 `expected_exit_code: )0x40`，替换为 `0x41`。目标字符串存在于 `expected.yaml` 第47行（`expected_exit_code: 0x40`）。assert `s2 != s` 保证注入非空。还原用 `cp` + md5 校验。
- **Injection B**（改 `m5_semi_writec.s` 服务号 `0x0003→0x0006`）：目标 `set.zw\trd16, wp0, 0x0003` 存在于向量第35行。assert 保证非空。还原用 `cp` + md5。
- **Injection C**（改 `m5_perm_reserved_illi.s` 权限期望码 `0x0100→0x0004`）：目标 `set.zw\trd12, wp0, 0x0100` 存在于向量第31行。assert 保证非空。还原用 `cp` + md5。
- **Injection D**（改 `m5_trap_escape.s` trap 期望码 `0x0001→0x0004`）：目标存在2处（第30、36行），`s.replace(..., 1)` 只改第1处。脚本注释明确说明：oracle（源文本检查）可能仍 PASS（因第2处未改），但**驱动**必 FAIL（向量走 fail 分支）。还原用 `cp` + md5。

4 类注入均非空且可还原（`cp` 备份 + md5 对账；无 `git checkout`/`git show`）。结尾 `rc=$?` 直判（无 `tee`）。`run_check`/`run_expect_fail` 函数均用 `"$@" > "$log" 2>&1; local rc=$?` 捕获真实退出码。

##### 2. 重跑证据脚本

```
EVIDENCE: PASS
SCRIPT_EXIT=0
```

全部19项检查 PASS：4 oracle PASS、grep 无子进程导入、驱动10/10 PASS、`--inject` 自检 PASS、4类注入各自 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿、`make check-lit` 62/62 PASS、`make check-no-residue` PASS。

##### 3. 独立注入（reviewer 自行执行）

**注入**：改 `expected.yaml` 中 `m5_perm_reserved_illi` 的 `expected_cause: ILLI` → `expected_cause: CFXREG`。

```
ORIGINAL md5=e1d5942f9ec2bd2ef6a76581b1a90005
INJECTED md5=ad1eb437feffd7186c7c9d747412be8e
```

oracle 输出：
```
[FAIL] m5_perm_reserved_illi:manifest-cause manifest cause 'CFXREG' != derived 'ILLI'
validate_m5_vectors: FAIL (1 failed, 140 passed)
ORACLE_EXIT=1
```

**还原**：`cp` 备份还原 + md5 校验：
```
RESTORED md5=e1d5942f9ec2bd2ef6a76581b1a90005  (与 ORIGINAL 一致)
```

回绿：
```
validate_m5_vectors: PASS (141 checks)
ORACLE_EXIT=0
```

**注入有效**：`git diff --name-only` 非空（注入期间文件确实被改动），还原后 `git status` 干净。

##### 4. Oracle 独立性复核

- **无子进程导入**：`grep -nE '(import subprocess|from subprocess|os\.system|Popen)' validate_m5_vectors.py` → **0 命中**（EXIT=1）。仅导入 `re`、`sys`、`pathlib`、`yaml`。
- **服务表机械解析**：`load_service_table()` 用 regex `SVC_ROW_RE` 从 `contract-semihosting.md` §3 解析 `0xNN | NAME |` 格式行。实测该文件**恰好25条**服务条目（`grep -c` 命中25），与 oracle `ck.check("contract-service-table", len(services) == 25)` 断言一致。
- **权限规则来源**：`RULE_CAUSE` 字典（4条规则 → ILLI/CFXREG）带注释引用 `contract-see.md §3`、`DADAO-12 §5`、`DADAO-22 §3`。reviewer 独立核对 `contract-see.md` 第35-39行确有对应规则文本。
- **Cause ID 来源**：`CAUSE_ID` 字典 `{CFXTRAP: 1<<0, CFXREG: 1<<2, ILLI: 1<<8}` 带注释引用 `DADAO-12 §4`。reviewer 独立核对 `spec/DADAO-12*.md` 第405-408行确有对应定义。
- **抽查2条**：① `m5_semi_writec` 服务号0x03 → oracle 从 contract-semihosting §3 解析得 `SYS_WRITEC`，与向量 `@m5 service_name=SYS_WRITEC` 交叉核对 PASS；② `m5_perm_reserved_illi` 规则 `reserved_cfxha` → oracle 从 `RULE_CAUSE` 派生 `ILLI`，与向量 `@m5 cause=ILLI` + manifest `expected_cause: ILLI` 三方交叉核对 PASS。

**结论**：oracle 期望值确由 contract 文件独立重算（服务表25条机械解析、cause 位/权限规则带 contract 引用的硬编码），不从 llvm-mc/llc/QEMU 反推。

##### 5. L3 实跑

```
run_m5_e2e: 10 programs, bootrom .../bootrom.bin
PASS  m5_semi_writec           expected=64 actual=64
PASS  m5_semi_write0           expected=65 actual=65
PASS  m5_semi_write            expected=66 actual=66
PASS  m5_semi_exit             expected=67 actual=67
PASS  m5_semi_exit_extended    expected=68 actual=68
PASS  m5_perm_reserved_illi    expected=80 actual=80 cause=ILLI
PASS  m5_perm_mask_illi        expected=81 actual=81 cause=ILLI
PASS  m5_perm_unimpl_cfxreg   expected=82 actual=82 cause=CFXREG
PASS  m5_perm_badcombo_cfxreg expected=83 actual=83 cause=CFXREG
PASS  m5_trap_escape           expected=96 actual=96 cause=CFXTRAP
Results: 10/10 passed, 0 failed
run_m5_e2e: PASS
EXIT=0
```

逐例含实际 qemu 命令行（均含 `-bios .../bootrom.bin`）+ bootrom 生效证据（`[bootrom] reset PC ok; bootrom user vector set; app entered user mode`）。分类：semihosting 5 / cfx 级权限反例 4 / trap+escape 1，与任务书一致。

##### 6. L1 复用

`cfx2-trap-escape.s` 覆盖 `trap`（14处）/ `escape`（16处）/ `cfx2rd`（17处）/ `cfx2rc`（9处）的编码与往返（含9个 `; OBJ:` 标记）。`README-m5.md §1` 对照表列出2条（`.s` + `-err.s`），覆盖4条指令。`make check-lit` **62/62 PASS**，无 `UNSUPPORTED:` 遗留。

##### 7. 门控

```
make check:       EXIT=0  (62/62 lit, check-patch-tree OK, check-no-residue PASS)
make check-lit:   EXIT=0  (62/62)
make check-no-residue: EXIT=0
```

##### 8. 未越界

`git diff --name-only f23bcc4..HEAD` = **17 文件**（与声明一致，含 `INTEG-019k` 加注）。`spec/` 交集为空。`.dadao/**`、`.work/**` 未入库。未触 `contracts/**`/`components/**`/`Makefile`。

##### 9. 两处披露判定

- **① 驱动追加 `chardev=semi` + `-chardev file,…`**：**合理必要**。`target=native` 无 `chardev` 时 `WRITEC`/`WRITE0` 输出到 QEMU 进程 stderr，与 QEMU 自身告警不可区分，无法可靠比对控制台内容。追加 `-chardev file,id=semi,path=…` + `chardev=semi` 是标准 semihosting 控制台捕获方式，不改变被测语义。
- **② oracle 权限规则/cause 位/token 为带 contract 引用的硬编码**：**可接受**。与既有 `validate_codegen_vectors.py`/`validate_elf_vectors.py` 范式一致。服务表已从 `contract-semihosting §3` 机械解析（25条）；权限规则/monitor cause 位为字面引用 + 硬编码，注释标注了 `contract-see §3`/`DADAO-12 §3/§4`/`DADAO-22 §3` 出处。pass/fail token 为文档化约定（`README-m5.md §2.3`），与向量源常量双向核对。

##### 判决

**Accepted**。

验收命令块全部在 reviewer 独立重跑下通过（oracle 141 checks PASS / 驱动10/10 PASS / check-lit 62/62 / check-no-residue PASS / 4类注入 FAIL+还原+回绿）；独立注入（改 manifest cause）确认 oracle 可失败；oracle 独立性经 grep + 抽查2条 contract 来源实证；边界无越界；两处披露合理。无阻断问题。

#### architect 重排落纸（2026-10-07，用户裁定 1）
**用户原话**：「**A 重排：先 LLVM-060t 再 SPEC-115t（推荐）**」（经主会话转达；见 `lessons §7.3`）。

**对本任务的影响（lit 归属裁定）**：本任务的 L1 MC 向量落点 `tests/llvm/lit/MC/DADAO/` 现由**前置的 `LLVM-060t` 先行自带**（含 `crrr`/`ciii` 的 `; OBJ:`），本任务**复用/扩展**（不再需要「`LLVM-060t` 就绪前以 `UNSUPPORTED:` 暂缓」，因其已就绪）。`tests/vectors/inventory.md` 的 4 行由 `SPEC-115t` 承接（`validate_vectors` 要求行集 == `scope==m1` 集，原子强制）。完整归属理由见 `SPEC-115t` 审阅记录「第 2 轮 architect 重排落纸」。

#### architect 承载形态裁定（2026-10-08，用户裁定）

**用户原话（逐字落盘；完整原话见 `INTEG-019k` §第 8 轮）**：

> 「……用bios的时候，直接接bin，也就是objdump后的测试程序；而用elf的时候，则不需要bootrom，只需要semihosting即可……只做bootrom+bin的情况；elf加载放在M6……」

**对本任务的影响**：

1. **L3 执行向量承载形态改 = bin**（`llc`/`llvm-mc` → `objcopy -O binary` → `qemu`）；**不经 `ld.lld` 多 TU ELF**（已同步接口规范「L3 执行向量」条）。
2. **原「单/多 TU ELF」正向用例移 M6**（ELF 加载/链接态随 M6，与「`-bios`+ELF 组合语义」一并；登记 `ISS-168`）。本任务保留的 L3 用例 = semihosting 服务 / 权限反例 / 一般 trap+escape（**bin 形态即可承载**，不依赖多 TU ELF）。
3. **L1 MC 向量不变**（`trap`/`escape`/`cfx2rd`/`cfx2rc` 编码/往返；`LLVM-060t` 已自带，本任务复用/扩展）。

**未改范围**：本轮**未动 `spec/`**。

#### 下发前预检修订（architect，2026-10-08，只追加）

**背景**：主会话对本任务书作「**下发前预检**」，发现 2 处缺口（F1 运行方式未写明致前置缺口；F2「m5 驱动」无落点）。本轮据**用户裁定口径**（M5 门槛正向 = **bootrom（`-bios`）+ bin 应用**经 `-semihosting`；`INTEG-019k` §第 8 轮）修订本任务书；**未触 `spec/`**、**未改任务范围**（L1/L3 与交付物不变）。

**F1（L3 运行方式未写明 ⇒ 前置缺口）**

- **事实**：门槛口径含 **bootrom（`-bios`）**，但原任务书未提 `bootrom`/`-bios`/`QEMU-047t`，依赖段亦无 `QEMU-047t`。而 L3 的权限反例（reserved cfxha / 未实现 cfx / scratch rc≥N / RO 写）与「一般 `trap` 进向量 + `escape`」需**模式/掩码/向量配置**，且 bin 应用**无独立入口** ⇒ 需 bootrom。
- **改法**：① **依赖段 += `QEMU-047t`**（**已验证**；bootrom 产物 `.dadao/tests/bootrom/bootrom.bin` + `-bios` 路径）；② 「输入」补 `QEMU-047t` 说明；③ 「输出」L3 新增**运行方式**条（`qemu-system-dadao -M dadao-m1 -bios <bootrom> -kernel <bin> -semihosting-config …`；bin 由**自有工具链** `llvm-mc`/`llc` → `llvm-objcopy -O binary` 产生；bootrom 路径经 `tools/infra/paths.py` 解析、禁硬编码）；④ **验收 4** 补「逐例给出**实际 qemu 命令行（含 `-bios`）** + 核**复位 PC/bootrom 生效**」。
- **「L3 是否某些用例无需 bootrom」——architect 依据（**供裁定**；本轮按「**全部经 bootrom**」写）**：
  1. **门槛口径**（用户 2026-10-08 裁定）明示 L3 载体 = bootrom（`-bios`）+ bin ⇒ 一律经 bootrom；
  2. **bootrom 是唯一应用入口/启动器**：`-kernel <bin>` 的 flat bin 落**旧 RAM 基址**，**复位 PC = ROM 基址 `0xffff_ffff_0000`**，须由 bootrom 完成模式/向量/栈初始化后 **hypv→user 跳应用**（`QEMU-047t`：栈置 RAM@0）——**无 `-bios` 则应用无入口、不执行**；
  3. semihosting 服务例虽在**译码层短路**（`QEMU-046t`，不进入向量），**仍需 bootrom 把应用启动/进入 user**；
  4. ⇒ **结论：L3 全部用例均经 bootrom，无例外**。若 engineer 认为某例可省，**须给依据供裁定**（该例如何获得入口/模式配置），**不得静默采用**。

**F2（「m5 驱动」无落点）**

- **事实**：`tests/llvm/codegen/m5/` 不存在；`tools/integ/` 仅 `run_codegen_e2e.py`/`run_elf_e2e.py` ⇒ 验收 4「经 m5 驱动跑通」**无实现落点**，且「新建驱动」未入输出/允许文件集。
- **改法（择 ①，理由见下）**：**新建 `tools/integ/run_m5_e2e.py`**，已写入「输出」并加入**允许改动文件集**（含验收 8「无残留」清单）。本任务内**直接 `python3` 调用**；`Makefile`/`make test-semihost` 接线归 `INTEG-020t`（本任务**不改 `Makefile`**）。
- **择 ①（新建）而非 ②（扩 `run_codegen_e2e.py` 加 `--list m5`）的理由**：① M5 管线与 M3 门控**实质不同**（`-bios` bootrom vs `trampoline.bin`、`-semihosting-config`、期望含**故障码**），且 m5 源码形态偏 `.s`（`trap`/`escape`/`cfx2*`/semihosting）；② 沿用本项目**每里程碑一个 runner** 的既有范式（M3 `run_codegen_e2e.py`、M4 `run_elf_e2e.py` ⇒ M5 `run_m5_e2e.py`）；③ **不触碰** M3 门控脚本，零回归风险。DRY 通过**复用 runner 结构**（清单加载 / 构建管线 / qemu 调用 / `--inject` 自检）达成。

**供裁定（本轮未改主文，仅登记）**

1. **L3 执行还直接依赖 `QEMU-044t`/`045t`/`046t`（+ `QEMU-049t`）**：semihosting 例需 `QEMU-046t`、一般 `trap`/`escape` 例需 `QEMU-045t`、cfx/权限反例需 `QEMU-044t`、RAM@0 需 `QEMU-049t`。本轮按指令**只 += `QEMU-047t`**（其自身依赖 `QEMU-044t`/`QEMU-049t`）；**是否将 `QEMU-045t`/`046t` 等一并列入依赖段，供裁定**（均**已验证**）。
2. **「未授权模式 ⇒ `NUPERM/NJPERM/NSPERM/NHPERM`」的 M5 可观测性**：`NUPERM` 等属 `DADAO-12 §2.2` **PTBR 权限层**，**不在 M5**（`ADR-0020 D9`；`QEMU-044t` 遗留明示）。M5 机器可观测的**权限反例 = cfx 级**（reserved cfxha ⇒ `ILLI`；未实现 cfx ⇒ `CFXREG`；scratch rc≥N ⇒ `CFXREG`；RO 写 ⇒ `CFXREG`，见 `QEMU-044t` 完成区）。**建议 L3 权限反例按 cfx 级（`ILLI`/`CFXREG`）表述**；本轮**未改主文**（「输出 ②」「验收 2」沿用原文），**供裁定**。
3. **`INTEG-020t` 的 `tools/integ/` 驱动复用**：`INTEG-020t` 输出 1 举 `run_semihost_e2e.py` 为例；为避免与 `run_m5_e2e.py` 重复，**建议 `INTEG-020t` 复用 `run_m5_e2e.py`**（其负责 `make test-semihost` 接线 + console stdio 捕获）。**供主会话协调**（本轮未改 `INTEG-020t`）。

**台账同步（最小）**：`INTEG-019k` §任务分解表 `TESTCASES-033t` 行依赖 += `QEMU-047t`；Wave 4 依赖链同步。`milestones.md` 未列本任务依赖 ⇒ **无需改**。

**边界**：本轮仅改**本任务书** + `INTEG-019k` 台账（1 行 + Wave 4）；**`spec/` 交集为空**；未改 `contracts/**`/`components/**`/`Makefile`；未新增/删除任务。

#### 主会话判定落纸（architect，2026-10-08，只追加）

**背景**：上「下发前预检修订」末「**供裁定**」登记 3 项（依赖补齐 / 权限反例 M5 可观测性 / `INTEG-020t` 驱动复用），**均待主会话裁定**。主会话本轮**逐项判定**，且明示**属事实对齐/去重、非新增范围**。以下按判定落纸；**未改任务范围**（L1/L3 交付物不变）、**未触 `spec/`**。

**判定 1（依赖补齐）— 已落纸**

- **判定**：依赖段 **+= `QEMU-044t`、`QEMU-045t`、`QEMU-046t`**（L3 执行跑在 QEMU 上；**均 `已验证`**）。
- **依据**：L3 执行向量三类用例分别落在 `QEMU-044t`（cfx/权限反例）、`QEMU-045t`（一般 `trap`/`escape`）、`QEMU-046t`（semihosting 服务）；`QEMU-047t`（bootrom）已在前轮计入。原依赖段仅列 `SPEC-114t`/`SPEC-115t`/`LLVM-060t`/`INFRA-048t`/`QEMU-047t`，缺上述三项 ⇒ 补齐。
- **改法**：依赖段（文件头）→ `SPEC-114t`、`SPEC-115t`、`LLVM-060t`、`INFRA-048t`、`QEMU-044t`、`QEMU-045t`、`QEMU-046t`、`QEMU-047t`。同步 `INTEG-019k` §任务分解表 `TESTCASES-033t` 行 + Wave 4。

**判定 2（权限反例口径）— 已落纸**

- **判定**：M5 **无 PTBR 权限层** ⇒ 「未授权模式 ⇒ `NUPERM/NJPERM/NSPERM/NHPERM`」**改为 cfx 级可观测**：`ILLI`（含 mask 禁止 / reserved）/ `CFXREG`（未实现 cfx / 不存在或超数量寄存器组合）；`NUPERM…` **明确标注属 `DADAO-12 §2.2` PTBR 层、不在 M5**（`ADR-0020 D9`）。
- **依据**：`ADR-0020 D9`；`QEMU-044t` 完成区遗留明示「`NUPERM` 等属 PTBR 权限层、不在 M5」；M5 机器可观测的权限反例 = cfx 级。
- **改法（3 处，已在主文改）**：① 「输出 · L3 执行向量」的 ② 权限反例；② 「验收 2」权限反例（≥3 类，明确 cfx 级）；③ 「验收 5」注入反例的「权限期望」明确为 cfx 级（改 `ILLI`/`CFXREG` 期望码）。

**判定 3（`INTEG-020t` 驱动去重）— 落 `INTEG-020t`**

- **判定**：`INTEG-020t` 输出 1 若举 `run_semihost_e2e.py` ⇒ **改为复用 `tools/integ/run_m5_e2e.py`**（**只追加/最小改**）。
- **落纸**：见 `INTEG-020t` 审阅记录「主会话判定落纸（architect，2026-10-08）」（本文件不改，去重落点在 `INTEG-020t`）。

**台账同步（最小）**：`INTEG-019k` §任务分解表 `TESTCASES-033t` 行依赖 += `QEMU-044t`/`045t`/`046t`；Wave 4 依赖链同步。`milestones.md` 未列本任务依赖 ⇒ **无需改**。

**边界**：本轮仅改**本任务书** + `INTEG-019k` 台账（1 行 + Wave 4）；**`spec/` 交集为空**；未改 `contracts/**`/`components/**`/`Makefile`；未新增/删除任务。

#### 第 1 轮 architect 提交（WIP）

**档位**：**`WIP:`**（reviewer 未验收、本任务 `状态` = `待验收` ⇒ 非「正常提交」）——**只本地 `commit`，未 `push`**。提交信息 = `WIP: TESTCASES-033t SEE/semihosting 向量（L1 复用 + L3 m5 bin 10 例 + run_m5_e2e + 独立 oracle）（待 reviewer 验收）`（**不写死 SHA**：后续 `/complete` 收尾会 squash/amend，SHA 会变）。

**文件集对账**（显式 staging、逐个路径；**未用 `git add -A`**）：

- 入库 **17** 条 = engineer 声明 **16 条**（15 新增 + 本任务书）+ **1 条** 台账文件 `.tao/tasks/integ/INTEG-019k-m5启动与分解.md`（本轮 architect「顺带加注」：§任务分解表 `QEMU-044t` 行权限口径注脚 + 其审阅记录只追加一条，**由主会话指令授权**）。
- **漏提 = 0**；**未授权多提 / 越界 = 0**；**`spec/` 交集 = 空**（`git status --porcelain -uall -- spec/` 无输出）；**`.dadao/**`、`.work/**` 未入库**（gitignored，`git check-ignore` 命中 `.gitignore`）；未触 `contracts/**`/`components/**`/`Makefile`；无并行会话改动卷入（提交时工作树仅本任务文件 + 上述台账）。
- `git diff --cached --stat` = **17 files changed, 1780 insertions(+), 5 deletions(-)**。

**注**：本留痕于**提交之后**追加（architect 标准流程：先提交、再留痕），**未随该 WIP 提交入库**，将由 `/complete` 收尾时一并纳入；本条与「第 1 轮 reviewer 验收」占位条并存（reviewer 尚未验收）。

#### 第 1 轮 architect 提交（正常）

**档位**：**正常提交**（reviewer 判 **`Accepted`** ⇒ 验收完成；`/complete` 收尾完成、本任务 `**状态**` 由 `待验收` 置 **`已验证`**）——**只本地 `commit`，未 `push`**。提交信息 = `TESTCASES-033t SEE/semihosting 向量（L1 复用 + L3 m5 bin 10 例 + run_m5_e2e + 独立 oracle）（reviewer Accepted）`（**不写死 SHA**：`push` 时由主会话将该任务本地提交 squash/amend 为单一「已验证」提交，SHA 会变）。

**本次纳入**：上轮 WIP 提交（`WIP: …`）**之后**追加的「第 1 轮 reviewer 验收」全文 + 上轮「architect 提交（WIP）」留痕（二者**均未随 WIP 提交入库**，本次一并纳入）；本任务书 `**状态**` `待验收`→`已验证`；`/complete` 知识沉淀 4 件（`lessons.md` §7.22/§8.16、`changelog.md` 1 行、`milestones.md` M5 段 `✅ TESTCASES-033t 落地`、`MEMORY.md` M5 摘要行）。

**文件集对账**（显式 staging、逐个路径；**未用 `git add -A`**）：

- 入库 = 本任务书 `.tao/tasks/testcases/TESTCASES-033t-SEE-semihosting向量.md` + **4** 个知识文件 `.tao/knowledge/{lessons.md,changelog.md,milestones.md,MEMORY.md}`（`git diff --cached --name-only` = 5 路径）。
- **漏提 = 0**（`git status --porcelain -uall` 仅这 5 个文件，全部 staged）；**多提 / 越界 = 0**；**`spec/` 交集 = 空**（`git diff --cached --name-only -- spec/` 无输出）；**`.dadao/**`、`.work/**` 未入库**（gitignored）；未触 `contracts/**`/`components/**`/`Makefile`；无并行会话改动卷入。

**交叉复核（architect，§2.5）**：reviewer 判决 **`Accepted`** 不过严/不过松；核其**独立注入**（改 `expected.yaml` 的 `expected_cause` `ILLI`→`CFXREG` ⇒ oracle `manifest-cause` FAIL ⇒ `cp`+md5 还原 ⇒ 141 checks 回绿）**有鉴别力**，且**未用** `git show <commit>:<path>` 读回（`lessons §7.20`；`.work/evidence/TESTCASES-033t/run.sh` 与 `.work/log/**` 均无 `git show/checkout/restore/stash`）。**独立**核：oracle `grep` 无 `subprocess`/`os.system`/`Popen`（0 命中）；服务表从 `contract-semihosting §3` 机械解析 **25** 条；L3 **10/10 PASS** 且逐例命令行含 `-bios`；L1 复用 `cfx2-trap-escape.s` 覆盖 `trap`/`escape`/`cfx2rd`/`cfx2rc` 且**无 `UNSUPPORTED:`**；`make check`/`check-lit`/`check-no-residue` EXIT=0（按硬约束**未重跑 `make`**，核证据日志 `.work/log/testcases/TESTCASES-033t-{check,check-lit-baseline,ev-make_check_lit_,ev-make_check_no_residue_}.log`）；**独立注入**（改 `expected_console` `"A"`→`"B"` ⇒ oracle `console-derived` FAIL ⇒ `cp`+md5 还原 ⇒ 141 checks 回绿）；`git diff f23bcc4..HEAD` **17 文件**、`spec/` 交集**空**、`.dadao/**`/`.work/**` **未入库**。补充发现 3 项（`Makefile`/`make test-semihost` 接线归 `INTEG-020t`；oracle 硬编码部分带 contract 引用且与既有 `validate_codegen/elf_vectors.py` 范式一致；驱动追加 `chardev` 披露）均**合理可接受**。**复核判决：通过（Accepted 维持）**。

#### 主会话统一验收报告（`/complete`，2026-10-08）

- **reviewer**：`Accepted`。证据脚本重跑 **`EVIDENCE: PASS`**（19 项；**4 类注入**各自 FAIL ⇒ `cp`+`md5` 还原 ⇒ 回绿）；**独立注入**（改 `expected.yaml` 的 `expected_cause` `ILLI→CFXREG`）⇒ oracle **EXIT=1** ⇒ 还原 ⇒ 回绿。
- **architect 交叉复核**：**通过**。独立核：**oracle 无子进程导入**（`grep` 0 命中）；**服务表 25 条机械解析**自 `contract-semihosting §3`；`RULE_CAUSE`/`CAUSE_ID` **带 contract 引用**；**L3 10/10**（逐例含 `-bios`）；**L1 无 `UNSUPPORTED:` 遗留**（复用 `LLVM-060t` 向量覆盖 4 条指令）；`check-lit` 62/62、`make check`/`check-no-residue` EXIT=0；`spec/` 交集空、`.dadao/**`/`.work/**` 未入库。**并核 reviewer 未用 `git show <commit>:<path>` 读回**（`lessons §7.20` 合规）。
- **交付**：**L3 m5 执行向量 10 条**（semihosting 5〔`WRITEC`/`WRITE0`/`WRITE`/`EXIT`/`EXIT_EXTENDED`〕+ **cfx 级权限反例 4**〔`ILLI` reserved/mask；`CFXREG` unimpl/badcombo〕+ `trap`+`escape` 1）**以 bin 形态**经 **`-bios <bootrom>`** 跑通；**新建驱动 `tools/integ/run_m5_e2e.py`**（`INTEG-020t` 复用，不另建 `run_semihost_e2e.py`）；**独立 oracle `tools/testcases/validate_m5_vectors.py`**（141 checks）；`README-m5.md` 对照表（含实际 qemu 命令行）；**L1 复用** `LLVM-060t` 向量（DRY）。
- **处置的其他事项**：本任务**不改 `Makefile`** ⇒ `make test-semihost` 接线归 `INTEG-020t`；oracle 硬编码部分（带 contract 引用）与既有 `validate_*_vectors.py` 范式一致（已披露）；驱动**追加 `chardev=file`**（否则控制台落 stderr 不可比对，已披露、判为必要）。
- **知识沉淀**：`lessons §7.22`（期望值「能机械解析则机械解析」+ 旁路通道显式重定向）+ **`§8.16`**。
- **最终判决**：**`Accepted`** ⇒ 任务书 `**状态**` 置 `已验证`。
