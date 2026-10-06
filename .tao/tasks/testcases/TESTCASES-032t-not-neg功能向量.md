# TESTCASES-032t: `not`/`neg` 功能向量（L1 编码 + L3 执行；独立 oracle）

**模块**：testcases
**项目里程碑**：M4
**依赖**：`SPEC-106t`、`INFRA-045t`、`TESTCASES-029t`、`TESTCASES-030t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**（自包含）：
  - `.tao/adr/adr-0013-assembly-syntax.md` 的 **D11**（2026-10-06 用户逐条确认，`Accepted`）——**决策来源**。**用户裁定原话（原文引用）**：「**删除（不实现，10 条）**：`nop`（用 `swym 0`）、`return`（用 `ret rd0, 0`）、`not.{b,w,t,o}`（用 `xnor.o`/`xnor.X`）、`neg.{b,w,t,o}`（用 `sub.sX`）。」
  - `SPEC-106t` 落地后的 `spec/Toolchain-01-汇编语言.md §6`（权威伪指令集）与 `spec/SimRISC-00 §伪指令`（**功能说明 + 如何实现**：`not`→`xnor.o`、`neg`→`sub.sX`）。
  - **底层真实指令的语义来源**（**期望值独立派生基点**）：
    - `.tao/knowledge/contract-isa.md` §6.3（`xnor.o` 64 位逻辑：相同为一、相异为零；「无专门 not 指令；当 `rdhc` 或 `rdhd` 为 `rd0` 时，`xnor` 实现另一操作数取反」）、§6.6（`not.o rdhb, rdhc` → `xnor.o rdhb, rdhc, rd0`；`neg.o rdhb, rdhc` → `sub.so rd0, rdhb, rd0, rdhc`）、§10.6/§11.6/§12.6（`neg.b/w/t` → `sub.sb/sw/st rdhb, rd0, rdhc`）。
    - **已删窄位宽逻辑**：`xnor.b/w/t` 已于 `SPEC-069t` 删除（`contract-isa` §10.3/§11.3/§12.3 的 `SPEC-069t` 注），故 `not.b/w/t` **无对应底层指令**——本任务 `not` **仅测 64 位 `xnor.o`**。
    - `spec/SimRISC-04 §Logic operators：逻辑运算 / §not / §neg`、`spec/SimRISC-05/08/09/10 §加减操作`（只读溯源，内容非执行必需）。
  - `contracts/opcodes.yaml`（**L1 独立 oracle 的期望编码来源**）：`xnor.o_orrr_rd`（`format: orrr`，`op=0x40`/`ha=0x0B`/`value=0x402C0000`，`legal:` `rdhb != rd0`）、`sub.sb_orrr_rd`（`op=0x43`/`ha=0x29`）、`sub.sw_orrr_rd`（`op=0x42`/`ha=0x29`）、`sub.st_orrr_rd`（`op=0x41`/`ha=0x29`）、`sub.so_rrrr_rd`（`format: rrrr`，`op=0x53`，双目的 `rdha:rdhb = rdhc − rdhd`）。
  - `spec/Process-05-里程碑TDD规范.md` §2（L1 期望值来自 ISA 编码表；L3 独立 oracle）、§4（期望值独立派生）、§5（反例门控）、§6（落点）。
  - `INFRA-045t` 落地后的落点：`tests/llvm/lit/MC/DADAO/`（L1）、`tests/llvm/codegen/m4/`（L3）。
- **输出**（**用户裁定 2026-10-06**：向量 + 独立 oracle，**暂不接入门控**）：
  - **L1 编码/往返向量** 落 `tests/llvm/lit/MC/DADAO/`（并入，单一落点；每条首部带 `UNSUPPORTED: true`，使 `llvm-lit` 记为 unsupported 而**不阻断** `make check-lit`）：
    - **`not` 功能 → 仅 64 位 `xnor.o`**：`xnor.o rd, rc, rd0` 的编码（`; OBJ:` 字节独立派生自 `contracts/opcodes.yaml`）与反汇编往返；`.b/.w/.t` **不适用**（见上「已删窄位宽逻辑」）。
    - **`neg` 功能 → `sub.sb/sw/st/so`**：`sub.sb/sw/st rd, rd0, rc`（8/16/32 位符号扩展减法）与 `sub.so {rd0, rd}, rd0, rc`（64 位双目的）的编码/往返（`; OBJ:` 独立派生自 `contracts/opcodes.yaml`）。
  - **L3 执行向量** 落 `tests/llvm/codegen/m4/`（并入 `m4/` 落点，与 `TESTCASES-030t` 共用**独立 m4 清单** `expected.yaml`，M3 驱动不读）：
    - `*.ll`（IR 级程序）+ `tests/llvm/codegen/m4/expected.yaml` 条目：按位取反（`xor x, -1` 语义）与取负（`0 - x` 语义）的 IR 程序，覆盖 8/16/32/64 位有符号；宿主侧独立派生期望退出码（大端 + 64 位补码），**不调用** `llc`/QEMU。
    - 边界用例：`not 0` / `not -1`、`neg 0`、各宽度 `INT_MIN` 取负、符号扩展边界（如 8 位 `0x80`）。
  - **独立 oracle**（**扩展** `TESTCASES-029t`/`030t` 建立的共享 validator，不另造）：
    - L1：`tools/testcases/validate_mc_vectors.py`——**不调用** `llvm-mc`/`llc`/QEMU，从 `contracts/opcodes.yaml` 独立派生 `xnor.o`/`sub.sX` 的期望编码/字段，与向量内联期望值比对，可失败。
    - L3：`tools/testcases/validate_elf_vectors.py`——**不调用** `llc`/QEMU，按 IR/spec 语义独立派生每个程序的期望退出码，与 `m4/expected.yaml` 比对，可失败。
  - `tests/llvm/lit/MC/DADAO/README-m4.md`、`tests/llvm/codegen/m4/README.md` 补「`not`/`neg` 功能 ↔ 底层真实指令 ↔ 期望值来源」对照行。
  - **边界**：`set.*` 展开/指导符/选项/诊断归 `TESTCASES-029t`；多 TU/多段/ELF 链路归 `TESTCASES-030t`；被删伪指令 `not.*`/`neg.*` 的「unrecognized」反例归 `TESTCASES-029t`。本任务只做 `not`/`neg` 的**替代功能**（`xnor.o`/`sub.sX`，**底层真实指令**）正例向量，不重复。
- **约束**：
  - **门控时序（用户裁定 2026-10-06）**：本任务**只产出向量 + 独立 oracle**，**暂不接入** `make check`/`make check-lit`/`make test-elf`；L1 用 lit **`UNSUPPORTED:` 标记**、L3 用**独立 m4 清单**；由对应实现任务与 `INTEG-016t` 移除标记/接入并转绿。
  - **期望值独立派生**（project 硬约束）：**不得**从 `llvm-mc`/`llc`/QEMU 反推；L1 来自 `contracts/opcodes.yaml`，L3 来自 IR/spec 语义（`Process-05 §4`）。
  - **指令精确**：`not` → **仅** `xnor.o`；`neg` → `sub.sb/sw/st/so`；**不得**测试已删的 `xnor.b/w/t`。
  - **规模 ∝ 能力**（`Process-05 §3`）；手写少量、可审计。
  - **串行**：共享 `tests/llvm/lit/MC/DADAO/`、`tests/llvm/codegen/m4/` 与两个 validator，**串行于** `TESTCASES-029t`/`030t`（本任务在其后扩展脚本）。
  - 不改 `contracts/**`、`components/**`、`Makefile`；临时目录 `/tmp/opencode/TESTCASES-032t/`；**不提交 git**；复杂命令输出留存 `.work/log/testcases/`。

## 验收标准

1. **L1 向量齐全**：`tests/llvm/lit/MC/DADAO/` 含 `xnor.o`（`rd, rc, rd0`）与 `sub.sb/sw/st/so` 的编码/往返向量各 ≥1；`; OBJ:` 字节独立派生自 `contracts/opcodes.yaml`；均带 `UNSUPPORTED:` 标记；`README-m4.md` 给出「功能 ↔ 底层指令 ↔ 期望值来源」表。
2. **L3 向量齐全**：`tests/llvm/codegen/m4/` 含 `not`/`neg` 的 IR 程序 + `expected.yaml` 条目；覆盖 8/16/32/64 位有符号取负与 64 位取反；含 `0`/`-1`/各宽度 `INT_MIN` 边界；`README.md` 给出「程序 ↔ 覆盖点 ↔ 推导依据」。
3. **独立 oracle**：`python3 tools/testcases/validate_mc_vectors.py`、`python3 tools/testcases/validate_elf_vectors.py` 对新增向量 EXIT=0；脚本内**无** `subprocess`/`os.system`/`Popen`（grep 核实）；L1 期望可由脚本从 `contracts/opcodes.yaml` 独立重算。
4. **size/sign 逐条重算**：`sub.sb/sw/st` 的符号扩展与 64 位补码、各宽度 `INT_MIN` 取负逐条独立复算，与 `expected.yaml`/`; OBJ:` 一致（含负值高 8 位补码）。
5. **反例门控**：对注入反例（改一条 `; OBJ:` 期望字节 / 改一条 L3 期望退出码 / 少一类覆盖）→ validator **非零退出**（真实输出留存 `.work/log/testcases/`）；还原后回绿。
6. **门控不破**：`make check` EXIT=0；`make check-lit` EXIT=0 且新向量记为 **unsupported**（不阻断、不误报 PASS）；`make check-dirs`/`check-no-residue` EXIT=0。
7. 一键证据脚本 `.work/evidence/TESTCASES-032t/run.sh`（非交互、失败非零、逐项打印、≥2 类注入自检、结尾无 `tee`）。

## 完成区

**测试结果**：
- **独立 oracle**：L1 `python3 tools/testcases/validate_mc_vectors.py` → **EXIT=0**（73 条向量 / 5 类覆盖 / 0 错）；L3 `python3 tools/testcases/validate_elf_vectors.py` → **EXIT=0**（42 checks）。日志 `.work/log/testcases/TESTCASES-032t-{l1,l3}-oracle.log`。
- **无子进程调用**：L1 `grep -nE 'subprocess|os\.system|Popen'` → rc=1（无命中）；L3 按调用形态 grep → rc=1。
- **反例门控 5 类**（改 `; OBJ:` 字节 / 改 `@enc` / 改 L3 期望退出码 / 改 IR 形态 / 少一个 TU）：validator 均**非零退出**，还原后回绿（L1 在临时树副本；L3 备份 + md5 对账）。日志 `…-inj-*.log`。
- **门控不破**：`make check` **EXIT=0**（`repository checks: PASS`）；`make check-lit` **EXIT=0**（58 discovered，**8 UNSUPPORTED**，含 `m4-not-neg.s`）；`make check-dirs`/`check-no-residue` **EXIT=0**；`check_lit_bytes.py` **EXIT=0**（148 patterns OK）。
- **一键证据**：`bash .work/evidence/TESTCASES-032t/run.sh` → **FAIL=0（EXIT=0）**，38 项 PASS、5 类注入自检。日志 `.work/log/testcases/TESTCASES-032t-evidence-run.log`。
- **附带（非 oracle，仅差分交叉验证）**：真实 M4 ELF 链（`llc` 逐 TU → `ld.lld -T tests/scripts/dadao.lds` → `qemu -kernel prog.elf`）得 `notneg_not=108`、`notneg_neg=8`，与独立派生期望一致（`.work/log/testcases/TESTCASES-032t-e2e-bonus.log`）。
- 失败原因：无。

**修改文件**（均在任务书范围内；未改 `contracts/**`/`components/**`/`Makefile`）：
- 新增 `tests/llvm/lit/MC/DADAO/m4-not-neg.s`（`not`/`neg` 底层真实指令的编码/往返 L1 向量；首行 `UNSUPPORTED: true`；含 `; OBJ:` 字节行 + `@enc` + `@norm`）。
- 新增 `tests/llvm/codegen/m4/`：`m4_notneg_not_lib.ll`、`m4_notneg_not_main.ll`、`m4_notneg_neg_lib.ll`、`m4_notneg_neg_main.ll`（`not`/`neg` L3 执行向量，2 程序 × 2 TU）。
- 改 `tests/llvm/codegen/m4/expected.yaml`（新增 2 条 `notneg_not`/`notneg_neg` 条目，含 `expected_exit_code` + 推导）。
- 改 `tests/llvm/codegen/m4/README.md`（程序 ↔ 覆盖点 ↔ 推导依据表补 2 行 + `not`/`neg` 说明段）。
- 改 `tests/llvm/lit/MC/DADAO/README-m4.md`（对照表补 `m4-not-neg.s` 行 + `OBJ` 字节独立派生说明 + 反例门控第 5 条）。
- 改 `tools/testcases/validate_mc_vectors.py`（**扩展**：解析 `; OBJ:` 字节行，要求其等于同指令 `@enc` 的独立派生编码）。
- 改 `tools/testcases/validate_elf_vectors.py`（**扩展**：`HAND_DERIVED` 增 2 条手算期望，与宿主解释器交叉验证）。
- 非入库（`.work/` gitignored）：`.work/evidence/TESTCASES-032t/run.sh`、`.work/log/testcases/TESTCASES-032t-*.log`。
- `git status --untracked-files=all` 仅上列 5 个新文件 + 5 个已跟踪文件改动。

**验收结果**（命令 → 真实输出；`cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`，无 `tee`；日志 `.work/log/testcases/`）：
```
$ python3 tools/testcases/validate_mc_vectors.py                       # EXIT=0
  向量 73 条，检查 5 类覆盖，错误 0 条
$ python3 tools/testcases/validate_elf_vectors.py                      # EXIT=0
  validate_elf_vectors: PASS (42 checks)
$ grep -nE 'subprocess|os\.system|Popen' tools/testcases/validate_mc_vectors.py   # EXIT=1（无命中）
$ python3 tools/llvm/check_lit_bytes.py                                 # EXIT=0
  check_lit_bytes: 148 patterns OK
$ make check                                                            # EXIT=0
  repository checks: PASS        (58 discovered, 8 Unsupported)
$ make check-lit                                                        # EXIT=0
  UNSUPPORTED: DADAO-MC :: m4-not-neg.s (39 of 58)
$ make check-dirs     # EXIT=0         $ make check-no-residue   # EXIT=0
$ bash .work/evidence/TESTCASES-032t/run.sh                             # EXIT=0
  结果: FAIL=0 / TESTCASES-032t EVIDENCE: PASS
  [PASS] inject-L1-obj-byte: oracle FAILED as expected (EXIT=1)
  [PASS] inject-L1-enc-value: oracle FAILED as expected (EXIT=1)
  [PASS] inject-expected-value: oracle FAILED as expected (EXIT=1)
  [PASS] inject-ir-shape: oracle FAILED as expected (EXIT=1)
  [PASS] inject-missing-tu: oracle FAILED as expected (EXIT=1)
$ # 附带 e2e（非 oracle）：notneg_not=108/108, notneg_neg=8/8
```
**size/sign 逐条重算**（宿主侧 64 位补码；与 `expected.yaml` 及解释器一致）：

| 项 | 独立重算 | 值 |
|---|---|---|
| `notneg_not`：`~0`/`~(-1)`/`~0x0102030405060708` | `y=~0^~(-1)^~C=0x0102030405060708`；`(y*0x9E37…C15)>>57` | **0x6C=108** |
| `notneg_neg` 8 位 `INT_MIN`（wire `0x80`） | `sext8(0-0x80)=-128=0xFFFF…FF80` | — |
| `notneg_neg` 16 位 `INT_MIN` | `sext16(0-0x8000)=0xFFFF…8000` | — |
| `notneg_neg` 32 位 `INT_MIN` | `sext32(0-0x80000000)=0xFFFF…80000000` | — |
| `notneg_neg` 64 位 `INT_MIN` | `0-(-2^63)=0x8000…0000` | — |
| `notneg_neg` `neg 0` / 8 位符号扩展边界 `0x40→0xC0` | `0` / `sext8(0xC0)=0xFFFF…FFC0` | — |
| `notneg_neg` 折叠 | `x5=0x800000007FFF8040`；`(x5*0x9E37…C15)>>57` | **0x08=8** |

**新发现/坑**：
1. **`; OBJ:` 与 `@enc` 两套约定**：仓库内 lit 向量用 `; OBJ:`（FileCheck 字节模式，`check_lit_bytes.py` 校验），而 `029t` 建立的 m4 向量 oracle 用 `@enc`。本任务按任务书要求写 `; OBJ:`，并**扩展** `validate_mc_vectors.py` 使其同时校验 `; OBJ:` 字节（= 同指令的独立派生编码），使「改 `; OBJ:`」能令既定 L1 oracle 非零退出（否则仅 `check_lit_bytes.py` 会失败）。两套约定并存于 `m4-not-neg.s`（`; OBJ:` + `@enc` + `@norm`）。
2. **lit 关键字陷阱复现**：正文注释里出现字面量 `OBJ:`（含反引号包裹）会被 FileCheck 当作 check 行解析（`m4-not-neg.s` 首次运行 `OBJ` 检查失败）。已改写措辞为「`OBJ` 字节行」（去掉冒号）；同理 `check_lit_bytes.py` 的 `; OBJ:` 宽松计数也需规避非模式行。
3. **LLVM IR 不接受十六进制整数字面量**：`mul i64 %y, 0x9E3779B97F4A7C15` 报 `floating point constant invalid for type`（`0x` 被当浮点 HEX）。改用十进制 `11400714819323198485`（等价无符号位型）。解释器 `int(tok,0)` 同样接受。
4. **XOR 折叠对「取反」不变**：初版用 XOR-shift 折叠把 64 位压到 7 位，结果对「全 1 取反」不变（`fold(~x)==fold(x)`），导致 `xor -1`↔`xor 0` 的注入**检测不到**。改为乘法哈希 `(v * 0x9E3779B97F4A7C15) >> 57` 后，取反注入、各宽度 `INT_MIN`、符号扩展边界均可被 exit 码区分。
5. **M4 后端对 `not`/`neg` 的实际 lower（观察，非缺陷）**：`llc -march=dadao` 对 IR `xor i64 %x,-1` 生成 `set.ow` + `xor.o rd, rd, rd`（非 `xnor.o rd, rc, rd0`）；对 `sub iN 0,x` 生成 `sub.uo {rd0,rd},rd,rd` + `ext.so`（非 `sub.sb/sw/st`）。语义正确、e2e 值一致；`sub.sX`/`xnor.o` 的**编码**由 L1 `m4-not-neg.s` 覆盖。若期望后端择用 `xnor.o`/`sub.sX` 形态，属后续 LLVM 优化议题（本任务超范围）。
6. 建议沉淀：`; OBJ:`（lit/`check_lit_bytes`）与 `@enc`（m4 oracle）双约定及其消歧；lit 注释中 `OBJ:`/`UNSUPPORTED:` 字面量陷阱；LLVM IR 无 hex 整数字面量；XOR 折叠的取反不变性。

**遗留问题**：
- ⏸ **暂不接入门控**（用户 2026-10-06 裁定）：L1 以 `UNSUPPORTED:` 标记、L3 以独立 m4 清单隔离；由 `INTEG-016t` 移除标记/接入并转绿。
- ⏸ **L3 `not` 仅 64 位**：依验收 2「64 位取反」+ 指令精确（`xnor.b/w/t` 已删、`not`→仅 `xnor.o`），未覆盖窄位宽 `not`（无等宽底层指令）。
- ❌ 无其它未完成项；无未修 finding。
> **用户裁定（2026-10-06）**：`not`/`neg` 功能向量**单独一个 `TESTCASES`**（本任务），自 `SPEC-106t` 移出；测**底层真实指令**（`not`→`xnor.o`；`neg`→`sub.sb/sw/st/so`），L1 编码 + L3 执行，期望值**独立派生自 `spec/`/`contracts/`**；暂不接入门控（`UNSUPPORTED:` + 独立 m4 清单）。

## 审阅记录

#### 第 1 轮 engineer 自审

**方式**：全局 `subagent_depth=1`，engineer 自主逐行审查（无嵌套子代理）——通读 `m4-not-neg.s`、4 个 `.ll`、`expected.yaml`、两个 validator 的改动、两个 README、`run.sh`；对照验收 1–7 与硬约束逐条核验，并跑真实命令。

**判决**：通过（0 未修 finding）；状态置「待验收」。

**逐行审查要点**：
- **期望值独立派生**：L1 `; OBJ:`/`@enc` 的编码由 `validate_mc_vectors.py` 从 `contracts/opcodes.yaml`（`xnor.o_orrr_rd`/`sub.sb/sw/st_orrr_rd`/`sub.so_rrrr_rd` 位域）独立重算；L3 由 `validate_elf_vectors.py` 的宿主 IR 解释器 + `HAND_DERIVED` 手算双来源交叉。**未**调用 `llvm-mc`/`llc`/QEMU 反推（`llc`/QEMU 仅用于事后差分，见坑 5/e2e）。
- **指令精确**：L1 只含 `xnor.o`（`rd, rc, rd0`）与 `sub.sb/sw/st`/`sub.so`；**未**出现已删 `xnor.b/w/t`、`not.*`、`neg.*`。已 `grep` 核实。
- **可失败性**：新增 OBJ 交叉检查有独立 FAIL 路径（改 `; OBJ:` → `validate_mc_vectors` EXIT=1，实测）；L3 期望/形态/TU 注入均实测 FAIL。
- **边界/未测输入**：L3 覆盖 `not 0`/`not -1`、`neg 0`、8/16/32/64 位 `INT_MIN`、8 位符号扩展边界；L1 `norm` 覆盖空白规范化等价书写。
- **范围**：仅动任务书范围 7 个文件（5 改 + 5 新，见完成区）；未改 `contracts/**`/`components/**`/`Makefile`；临时文件仅在 `/tmp/opencode/TESTCASES-032t/` 与 `.work/`。
- **防造假**：全部 `cmd > log 2>&1; rc=$?`，无 `tee`；注入逐轮 md5/临时树对账；`git status` 仅应有改动。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 正文注释含字面量 `OBJ:`（反引号包裹）→ FileCheck 误当 check 行，`OBJ` 检查失败 | ✅已修 | 改为「`OBJ` 字节行」（去冒号） | 手动 `llvm-objdump -d \| FileCheck --check-prefix=OBJ` EXIT=0；`check_lit_bytes.py` 148 patterns OK |
| F2 IR 用 `0x9E3779B97F4A7C15` → `llc` 报 `floating point constant invalid for type` | ✅已修 | 改十进制 `11400714819323198485` | 4 个 `.ll` `llc -march=dadao` 全 EXIT=0 |
| F3 初版 XOR-shift 折叠对「取反」不变（`fold(~x)==fold(x)`）→ `xor -1`↔`xor 0` 注入**检测不到**（实测 inject-ir-shape 未 FAIL） | ✅已修 | 折叠改乘法哈希 `(v*0x9E3779B97F4A7C15)>>57`；同步更新 `expected.yaml`/`HAND_DERIVED`/README（not 8→108、neg 64→8） | L3 oracle 42 checks PASS；`inject-ir-shape` 现 FAIL（EXIT=1）；逐位敏感度核对（neg 无单比特碰撞） |
| F4 `run.sh` 消息串内反引号 `` `; OBJ:` `` → bash 命令替换语法错误（`syntax error near ';'`） | ✅已修 | 去掉消息内反引号 | `run.sh` 全跑 EXIT=0（FAIL=0） |
| F5 任务书用 `; OBJ:` 而 029t oracle 用 `@enc`（两约定） | ✅已修（兼容实现） | 向量同时写 `; OBJ:`+`@enc`+`@norm`；扩展 `validate_mc_vectors.py` 交叉校验 OBJ 字节 | 改 `; OBJ:` → L1 oracle EXIT=1（及 `check_lit_bytes` 可失败）；基线 EXIT=0 |

**自验命令退出码**：L1 oracle EXIT=0（73/5/0）；L3 oracle EXIT=0（42 checks）；`check_lit_bytes` EXIT=0（148）；`make check` EXIT=0；`make check-lit` EXIT=0；`check-dirs`/`check-no-residue` EXIT=0；`run.sh` EXIT=0；附带 e2e 108/8 一致。

#### 第 1 轮 reviewer 验收

**审查方式**：独立重跑所有验收命令 + 独立注入（不同于 engineer 的 5 类）+ 独立全量重算 L1 编码与 L3 期望退出码。

**判决**：**Accepted**（全部约束守住，0 项未修 finding）。

---

##### 1. 证据脚本审阅

**`run.sh` 审查**：
- `set -u`（未定义变量报错）✓
- 无 `tee`（grep 仅在注释中出现一次 "No `tee` anywhere"）✓
- 结尾 `exit 0`/`exit 1`（非 `tee` 吞退出码）✓
- L1 注入在临时树副本（`MC_VEC_DIR="$WORK/inj"`），不污染真实仓库 ✓
- L3 注入有 backup + md5 + 还原 + 还原后 oracle 回绿验证 ✓
- 5 类注入：L1（obj-byte, enc-value）+ L3（expected-value, ir-shape, missing-tu）✓
- FAIL 路径：每条注入均检查 oracle 非零退出，否则 fail ✓
- `grep -nE 'subprocess|os\.system|Popen'` 在两个 validator 上确认无命中 ✓

**Validator 扩展审查**：
- `validate_mc_vectors.py`：新增 `OBJ_RE` 正则解析 `; OBJ:` 字节行 + `pending_obj` 跟踪 + `enc/OBJ` 交叉校验（L774–L780）。逻辑正确：当 `obj_bytes` 不为 None 且与独立派生不等时报 FAIL。✓
- `validate_elf_vectors.py`：`HAND_DERIVED` 新增 `notneg_not: 0x6C`、`notneg_neg: 0x08` 两条手算期望，与解释器输出交叉。✓
- 两个脚本均无 `subprocess`/`os.system`/`Popen`（grep EXIT=1 确认）✓

##### 2. 重跑记录（逐项真实命令 + 退出码）

```
$ python3 tools/testcases/validate_mc_vectors.py > log 2>&1; echo "EXIT=$?"
EXIT=0
  向量 73 条，检查 5 类覆盖，错误 0 条

$ python3 tools/testcases/validate_elf_vectors.py > log 2>&1; echo "EXIT=$?"
EXIT=0
  validate_elf_vectors: PASS (42 checks)

$ grep -nE 'subprocess|os\.system|Popen' tools/testcases/validate_mc_vectors.py; echo "EXIT=$?"
EXIT=1（无命中）

$ grep -nE 'subprocess\.|os\.system\(|os\.popen|Popen\(|check_output|shutil\.which|run\(\[|os\.exec' tools/testcases/validate_elf_vectors.py; echo "EXIT=$?"
EXIT=1（无命中）

$ python3 tools/llvm/check_lit_bytes.py > log 2>&1; echo "EXIT=$?"
EXIT=0
  check_lit_bytes: 148 patterns OK

$ bash .work/evidence/TESTCASES-032t/run.sh > log 2>&1; echo "EXIT=$?"
EXIT=0
  结果: FAIL=0 / TESTCASES-032t EVIDENCE: PASS
  38 项全部 PASS（8 文件存在 + 2 oracle 基线 + 2 无外部调用 + 6 OBJ 覆盖 + 5 L1 注入 + 5 L3 注入 + 4 门控 + 2 最终基线）

$ make check > log 2>&1; echo "EXIT=$?"
EXIT=0

$ make check-lit > log 2>&1; echo "EXIT=$?"
EXIT=0
  8 UNSUPPORTED, m4-not-neg.s reported UNSUPPORTED

$ make check-dirs > log 2>&1; echo "EXIT=$?"
EXIT=0

$ make check-no-residue > log 2>&1; echo "EXIT=$?"
EXIT=0
```

##### 3. 约束核验（逐条）

| 约束 | 结果 |
|------|------|
| 不改 `contracts/**` | ✓（git diff 无 contracts 变动） |
| 不改 `components/**` | ✓ |
| 不改 `Makefile` | ✓ |
| L1 均带 `UNSUPPORTED:` | ✓（首行 `; UNSUPPORTED: true`） |
| L3 用独立 m4 清单 | ✓（`expected.yaml` 独立于 M3 清单） |
| 期望值独立派生（不从 llvm-mc/llc/QEMU 反推） | ✓（validator 无外部调用） |
| `not` → 仅 `xnor.o` | ✓（未出现 `xnor.b/w/t`） |
| `neg` → `sub.sb/sw/st/so` | ✓ |
| 临时目录 `/tmp/opencode/TESTCASES-032t/` | ✓ |
| 不提交 git | ✓（git status 仅未暂存改动 + untracked 新文件） |
| 一键证据脚本非交互、失败非零、逐项打印、≥2 类注入、结尾无 `tee` | ✓（38 项 PASS，5 类注入自检） |

##### 4. 独立注入（第 6 类，不同于 engineer 的 5 类）

**注入内容**：修改 `m4_notneg_neg_main.ll` 的 `%a = call i64 @neg8(i64 128)` → `i64 129`（改变 IR 参数值，属于 IR 语义注入，engineer 的 5 类未覆盖此类型）。

```
$ cp original → backup; sed 's/128/129/' → inject
$ md5 before: 3d990e628cccbf228ccaa531ec300d86
$ md5 after inject: fe8520edbeaddd09c7932bda7ead8ccf（不同 ✓）
$ git diff: non-empty（确认改动生效 ✓）

$ python3 tools/testcases/validate_elf_vectors.py > log 2>&1; echo "EXIT=$?"
EXIT=1
  [FAIL] oracle-vs-expected[notneg_neg] expected=8 oracle=40
  [FAIL] hand-vs-oracle[notneg_neg] hand=8 oracle=40

$ 还原（edit 129→128）→ md5: 3d990e628cccbf228ccaa531ec300d86（与原始一致 ✓）

$ python3 tools/testcases/validate_elf_vectors.py > log 2>&1; echo "EXIT=$?"
EXIT=0
  validate_elf_vectors: PASS (42 checks)
```

**结论**：注入有效（oracle 非零退出），还原成功（md5 一致 + oracle 回绿）。✓

##### 5. 独立全量重算

**L1 编码（从 `contracts/opcodes.yaml` 独立派生，逐条）**：

| 指令 | 操作数 | op | ha | 字段值 | 独立派生编码 | 向量 `@enc` | 向量 `; OBJ:` | 一致 |
|------|--------|----|----|--------|-------------|-------------|---------------|------|
| `xnor.o` | rd8,rd9,rd0 | 0x40 | 0x0B | hb=8,hc=9,hd=0 | `402c8240` | `402c8240` | `40 2c 82 40` | ✓ |
| `sub.sb` | rd8,rd0,rd9 | 0x43 | 0x29 | hb=8,hc=0,hd=9 | `43a48009` | `43a48009` | `43 a4 80 09` | ✓ |
| `sub.sw` | rd8,rd0,rd9 | 0x42 | 0x29 | hb=8,hc=0,hd=9 | `42a48009` | `42a48009` | `42 a4 80 09` | ✓ |
| `sub.st` | rd8,rd0,rd9 | 0x41 | 0x29 | hb=8,hc=0,hd=9 | `41a48009` | `41a48009` | `41 a4 80 09` | ✓ |
| `sub.so` | {rd0,rd8},rd0,rd9 | 0x53 | — | ha=0,hb=8,hc=0,hd=9 | `53008009` | `53008009` | `53 00 80 09` | ✓ |

**未出现已删 `xnor.b/w/t`**（仅注释中提及删除说明）✓

**L3 期望退出码（逐条独立推导，64 位补码 + 大端）**：

**`notneg_not` (期望=108)**：
- `a = bitnot64(0) = ~0 = 0xFFFFFFFFFFFFFFFF`
- `b = bitnot64(-1) = ~(-1) = 0x0000000000000000`
- `c = bitnot64(0x0102030405060708) = 0xFEFDFCFBFAF9F8F7`
- `y = a^b^c = 0xFFFFFFFFFFFFFFFF ^ 0 ^ 0xFEFDFCFBFAF9F8F7 = 0x0102030405060708`
- `fold(y) = (0x0102030405060708 * 0x9E3779B97F4A7C15) >> 57 = 108 = 0x6C` ✓

**`notneg_neg` (期望=8)**：
- `a = neg8(128)`: trunc→0x80; sub i8 0,0x80=0x80; sext8(0x80)=−128=`0xFFFFFFFFFFFFFF80`
- `b = neg16(32768)`: trunc→0x8000; sub i16→0x8000; sext16=−32768=`0xFFFFFFFFFFFF8000`
- `c = neg32(2147483648)`: trunc→0x80000000; sub i32→0x80000000; sext32=−2147483648=`0xFFFFFFFF80000000`
- `d = neg64(−2^63)`: sub i64 0,0x8000000000000000=0x8000000000000000（溢出，仍是 `0x8000000000000000`）
- `e = neg64(0) = 0`
- `g = neg8(64)`: trunc→0x40; sub i8→0xC0; sext8(0xC0)=−64=`0xFFFFFFFFFFFFFFC0`
- `x5 = a^b^c^d^e^g = 0x800000007FFF8040`
- `fold(x5) = (0x800000007FFF8040 * 0x9E3779B97F4A7C15) >> 57 = 8 = 0x08` ✓

**边界验证**：`neg 0`=0 ✓；`neg8(0x80)` = `0xFFFFFF...FF80`（符号扩展边界）✓；各宽度 `INT_MIN` 取负正确溢回自身 ✓。

##### 6. 披露判定

**① `; OBJ:` vs `@enc` 双约定**：**合理，无需 architect 裁定**。

理由：两套约定服务不同消费者——`; OBJ:` 是 lit FileCheck 模式（`check_lit_bytes.py` 校验），`@enc` 是 L1 oracle 期望值注解（`validate_mc_vectors.py` 校验）。engineer 同时写两者并用 `validate_mc_vectors.py` 交叉校验（改任一即失败），增加了注入覆盖面（改 `; OBJ:` 不仅 `check_lit_bytes` 失败，L1 oracle 也失败）。实现合理、范围不超。✓

**② 后端 lower 分歧**：**真实缺口，但本任务正确分层，建议登记 issue**。

事实：M4 后端对 IR `xor i64 %x,-1` 实际 lower 为 `set.ow`+`xor.o`（非 `xnor.o rd,rc,rd0`）；对 `sub iN 0,x` 实际 lower 为 `sub.uo`+`ext.so`（非 `sub.sb/sw/st`）。这意味着 `INTEG-016t` 移除 `UNSUPPORTED` 后，L3 实际执行的**不是** `xnor.o`/`sub.sX`——L1 仍覆盖其编码（独立验证），但 L3 的 e2e 不经过任务书所述的伪指令替代路径。

判定：
- **不削弱本任务前提**：任务书说"底层真实指令的编码由 L1 覆盖、功能由 L3 覆盖"，两者分工成立。L1 证明编码正确，L3 证明 IR 语义正确（不依赖具体指令选择）。
- **需登记 issue**：「M4 后端对 `not`/`neg` 功能的 lower 未走 `xnor.o`/`sub.sX` 路径——当 `INTEG-016t` 接入时，需确认是否需要后端 pass 将 `xor x,-1` → `xnor.o` 或验证当前 `xor.o`+常量路径同样正确」。此 issue 属 LLVM 后端优化议题，非 testcases 模块阻断。
- **不阻断验收**：L1/L3 分工正确，期望值独立派生正确，注入可失败。

##### 7. 其余披露判定

| 披露 | 判定 |
|------|------|
| XOR 折叠取反不变性（F3） | ✅ 已修：改乘法哈希，敏感度足够。✓ |
| IR 十进制（F2，hex 被当浮点） | ✅ 已修：改用十进制 `11400714819323198485`。✓ |
| lit 注释 `OBJ:` 关键字陷阱（F1） | ✅ 已修：去冒号写 `OBJ` 字节行。✓ |
| run.sh 消息反引号语法错误（F4） | ✅ 已修。✓ |

以上 4 项均属 engineer 自审阶段发现并修复的问题，修复正确，无遗留。

##### 8. 判决

**Accepted**。验收命令块在 reviewer 独立重跑下全部通过；全部硬约束守住；独立注入有效；独立全量重算一致；两处披露判定不阻断（①合理 ②需登记 issue）。

**issue 建议**：登记为 `LLVM` 模块 future issue——「M4 后端 lower `not`/`neg` 未走 `xnor.o`/`sub.sX` 伪指令替代路径；INTEG-016t 接入时需确认」。
