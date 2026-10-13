# LLVM-047t: 有符号窄整数扩展 ISel（`sign_extend_inreg`/`sext` → i64，C4）

**模块**：llvm
**项目里程碑**：M3
**依赖**：`LLVM-036t`（窄访存）、`LLVM-039t`（调用约定）、`TESTCASES-026t`（发现该缺口）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`TESTCASES-026t` 复现的缺口（**显式** `sext i8/i16/i32 to i64`（操作数扩展未被断言）→ `sign_extend_inreg` 无 ISel → `llc` abort 134；`i8/i16/i32 signext` **形参**经 `LLVM-039t` 的 `AssertSext` 已可编译，实测不 abort）；v5 指令定义；`ADR-0018（C4）`（窄标量 caller 扩展）、`contract-abi.md §4`。
- **输出**：为 `sign_extend_inreg`（及窄类型 `sext` 到 i64 的等价 DAG）补 SelectionDAG ISel（`Pattern` 或 `ISelLowering` custom），使**带符号窄整数**（`i8/i16/i32`）的扩展在 GPRD 上正确产生符号扩展值；导出的补丁。
- **约束**：
  - **语义事实（实测）**：当前 `sign_extend_inreg` 无 pattern，`llc` 对含该节点的 IR **abort 134**（`TESTCASES-026t` 的 `call_narrow_args.ll` 因此只能用无符号窄参数 zext 路径）。**本任务消除该 abort**。
  - **符号扩展语义**：把窄值 `n`（`i8/i16/i32`）按**二进制补码**扩展到 64 位；`n` 为负时高位全 `1`，非负时高位全 `0`（`ADR-0018（C4）` D2：caller 侧按符号性扩展）。**不得**用零扩展冒充。
  - **覆盖来源**：至少两条 IR 路径产生该节点，须都正确——
    (a) 形参 `define i64 @f(i32 signext %x)` / `i8 signext`（调用约定扩展）；
    (b) 显式 `sext i8/i16/i32` 到 `i64`，以及窄访存后 `sext`（与 `LLVM-036t` 的 `ld.sb/sw/st` 路径**不冲突**：装载路径已由 `ld.sb/sw/st` 承担，本任务补**寄存器值**的扩展）。
  - **手段不限**：可用 `(sign_extend_inreg GPRD:$src, i8)` 类 pattern（如移位对 `shl`+`sra`、或 `andn`/`or` 掩码组合），或 `setOperationAction(..., Custom)` + 自定义 lowering——以**正确 + 最简**为准，不引 constant pool。
  - **范围**：**仅**有符号窄整数扩展到 i64（GPRD）。**不含**：GPRB/指针窄扩展（指针是 64 位，无窄扩展）、RF 浮点、i128（→M4）。
  - 不回归 `LLVM-033t`~`LLVM-041t` 的 MIR；不回归 `make check-lit`；不改 `tests/codegen/**`（若 `call_narrow_args.ll` 可因此放宽为含有符号窄参数，作为**可选**增强并在完成区记录，须保持期望值 independent oracle）。
  - 补丁纪律、构建/日志/临时目录/防造假纪律同 `LLVM-033t`。
  - 参照 0628 相应 sext 处理（只读溯源，非执行依赖）。

## 验收标准

1. `ninja -C .work/build/llvm llc` 退出 0。
2. `llc -march=dadao -stop-after=finalize-isel` 对以下 IR **EXIT=0、不 `Cannot select`、不 abort**：
   - `define i64 @f(i32 signext %x){ %e=sext i32 %x to i64  ret i64 %e }`；
   - `i8 signext` / `i16 signext` 形参同类；
   - `define i64 @g(i8 %x){ %e=sext i8 %x to i64  ret i64 %e }`（显式 sext）。
3. **符号扩展正确（size/sign 敏感，逐一核对）**：对负值/边界/正值样本（如 `-1`、`-128`（i8 最小）、`127`、`0`、`0xFF` 当 i8=‑1），MIR 展开序列**独立重算**为正确的 64 位补码结果（给出展开指令 + 手算核对），**不得**只报“能编译”。
4. `llc -verify-machineinstrs`（`-O1`/`-O2`）对上述 IR EXIT=0。
5. 不回归 `LLVM-033t`~`LLVM-041t`；补丁导出 + `make check-patch-tree` 通过；`make check-lit` 不回归。
6. 一键证据 `.work/evidence/LLVM-047t/run.sh`（规格同 `LLVM-033t`；反例注入：把符号扩展改成零扩展/去一条 pattern → 对应负值样本 FAIL，再还原）。

## 完成区

**测试结果**：通过 **23/23**（一键证据脚本 `.work/evidence/LLVM-047t/run.sh` 全 PASS，`EXIT=0`）；`run.sh --inject` 自检 PASS（把 i8 pattern 的 `ext_so_orri`→`ext_uo_orri`（符号扩展改零扩展）→ 重建 → `mir-explicit-i8`/`no-zeroext-i8`/`sem-i8` 三条 **FAIL**（负值样本 `0xFF` 模型 0x00000000000000FF ≠ 期望 0xFFFFFFFFFFFFFFFF）→ 还原（sha256 一致、`git status` 干净）+ 重建 → 回绿）。回归 `LLVM-033t`(11/11)、`034t`(13/13)、`035t`(14/14)、`036t`(31/31)、`037t`(0 failures)、`038t`(15/15)、`039t`(14/14)、`040t`(16/16)、`041t`(19/19) 全 `EXIT=0`；`make check` `EXIT=0`（lit 33/33、`repository checks: PASS`）；`make check-patch-tree` 80 patches OK；`make check-source-state` OK（`HEAD=f15f1998bba0 count=1 clean=True`）。

**修改文件**：

组件源码（`.work/source/llvm-project`，收敛为 base+1 = `f15f1998bba0`；base=`6dfe1677ab8dffbc6ec13d53a1e0215d75147689`；共 1 文件修改）：
- `llvm/lib/Target/DADAO/DADAOCodeGen.td`：新增 3 条 `sext_inreg` pattern ——
  `(i64 (sext_inreg GPRD:$src, i8)) → (ext_so_orri GPRD:$src, 7)`、
  `i16 → 15`、`i32 → 31`；并更新文件头/段注释（新增 `Signed narrow-integer extension` 段）。

DADAO-v5 仓库：`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOCodeGen.td.patch`（由 `tools/infra/make_patch.py llvm-project` 从真实源导出，**未手改**）+ `components/llvm-project/changelog.md`；任务书（本文件）。

未入库（gitignored）：`.work/evidence/LLVM-047t/{run.sh,sem_check.py}`；日志 `.work/log/llvm/LLVM-047t-*.log`；临时 `/tmp/opencode/LLVM-047t/`。

**验收结果**（真实命令 + 真实输出 + 退出码；`cmd > log 2>&1; rc=$?` 制式，无 `tee`；完整 log `.work/log/llvm/LLVM-047t-*.log`）：

1. **构建（验收 1）**：`ninja -j8 -C .work/build/llvm llc` → `BUILD_EXIT=0`（`[24/24] Linking CXX executable bin/llc`；log `LLVM-047t-build1.log`）。改动仅 `.td`，TableGen 重生成 DAG ISel 后重链。

2. **真实 MIR（验收 2，`-march=dadao -stop-after=finalize-isel`，均 `EXIT=0`）**：
```
sext_explicit_i8  (i8 %x)          %0:gprd = COPY $rd16 ; %1:gprd = ext_so_orri %0, 7  ; $rd31 = COPY %1
sext_explicit_i16 (i16 %x)         %1:gprd = ext_so_orri %0, 15
sext_explicit_i32 (i32 %x)         %1:gprd = ext_so_orri %0, 31
signext_i8/i16/i32 (iN signext)    EXIT=0（无 Cannot select/abort；走 AssertSext，见「新发现」）
```
修复前 `sext_explicit_i8/i16/i32` 均 `LLVM ERROR: Cannot select: t9: i64 = sign_extend_inreg t2, ValueType:ch:i8/i16/i32` → exit 134；修复后全部 `EXIT=0`。

3. **符号扩展正确（验收 3，size/sign 敏感，逐一独立重算）**：`run.sh` 的 `sem-*` 检查解析**实际选中的**指令（`ext_so_orri` + `hd`），按 `contract-isa.md §6.4.2` 语义建模型，与 Python 独立二元补码模型逐样本比对（`sem_check.py`）。展开指令与手算：
```
i8  → ext.so rd, src, 7  : 复制低 8 位，从 bit7 符号扩展到 64 位
   0xFF → 0xFFFFFFFFFFFFFFFF（-1）   0x80 → 0xFFFFFFFFFFFFFF80（-128）
   0x7F → 0x000000000000007F（127）  0x00 → 0（0）
   0x…EF→ 0xFFFFFFFFFFFFFFEF（-17，验证高位无关位被忽略）
i16 → ext.so rd, src, 15 : 0xFFFF→0xFFFF…FFFF(-1)  0x8000→0xFFFF…8000(-32768)  0x7FFF→0x7FFF  0→0
i32 → ext.so rd, src, 31 : 0xFFFFFFFF→0xFFFF…FFFF(-1)  0x80000000→0xFFFFFFFF80000000(-2^31)  0x7FFFFFFF→0x7FFFFFFF  0→0
```
全部 OK（`model == expected`）。**非零扩展冒充**：`no-zeroext-*` 断言 MIR 出现 `ext_so_orri` 且**不含** `ext_uo_orri`。

4. **`ext.so` 指令与编码核对**（C4 D2 手段正确性的独立锚点）：
   - asm 全流水线：`llc -O2` → `ext.so rd31, rd16, 7`（i8）/`15`（i16）/`31`（i32），`EXIT=0`；
   - 目标文件：`llc -O2 -filetype=obj` + `llvm-objdump -d --triple=dadao` → `.text` 为 `40 65 f4 07  ext.so rd31, rd16, 7`（+ `ret rd0, 0`）；
   - MC 编码（对照 `contracts/opcodes.yaml` `ext.so_orri_rd`：`op=0x40`/`ha=0x19`/`rdhb[17:12]`/`rdhc[11:6]`/`immu6[5:0]`）：`ext.so rd8, rd9, K` = `0x40648240|K`（K=7→`0x40648247`、15→`4f`、31→`5f`），逐值一致。

5. **`-verify-machineinstrs`（验收 4）**：6 个 IR × `-O1`/`-O2` = 12/12 `EXIT=0`（`all-clean`）。

6. **不回归 + 补丁 + 门控（验收 5）**：
```
make check-patch-tree    → 2 component(s), 80 patches OK                 EXIT=0
make check-source-state  → llvm-project: OK HEAD=f15f1998bba0 count=1 clean=True EXIT=0
make check               → Total 33, Passed 33 (100.00%), repository checks: PASS EXIT=0
LLVM-033t~041t run.sh    → 11/13/14/31/0f/15/14/16/19 checks   全 EXIT=0
```
窄访存 + `sext` 不冲突（验收约束）：`load i8/16/32` + `sext` 折叠为单条 `ld.sb/sw/st`（无 `ext.so` 叠加）；`trunc i64→i8` + `sext i8` → `ext_so_orri %0, 7`。

7. **一键证据脚本（验收 6）**：
```
$ bash .work/evidence/LLVM-047t/run.sh; echo "EXIT=$?"
PASS llc-exists / llc-version / mir-explicit-i8/i16/i32 / mir-signext-i8/i16/i32 /
     no-zeroext-i8/i16/i32 / sem-i8/i16/i32 / verify-machineinstrs-O1-O2 /
     asm-emit-ext.so / obj-emit-ext.so / mc-encoding-ext.so / source-invariants /
     patch-hunks / check-patch-tree / check-source-state / check-lit
RESULT: PASS
EXIT=0

$ bash .work/evidence/LLVM-047t/run.sh --inject; echo "EXIT=$?"
inject: sha 00dcd37fc398 -> f57959d6bce2; dirty_files=1
inject: rebuild EXIT=0
FAIL  mir-explicit-i8   expected=ext_so_orri imm=7  actual=ext_uo_orri %0, 7
FAIL  no-zeroext-i8     expected=ext_so>=1 ext_uo=0 actual=ext_so=0 ext_uo=1
FAIL  sem-i8   … V=0x00000000000000ff model=0x00000000000000ff expected=0xffffffffffffffff MISMATCH
inject: restore sha 00dcd37fc398 (was 00dcd37fc398); dirty_after_restore=0
inject: restore rebuild EXIT=0
inject: re-running the i8 checks (expect PASS) ... PASS x3
INJECT MODE PASSED (zero-extension injection FAILed the i8 negative samples; restored)
EXIT=0
```

**新发现/坑**：

1. **任务书对「signext 形参」的复现前提与实测不符**：`i8/i16/i32 signext` 形参在**本任务前已是 `EXIT=0`**——`LowerFormalArguments`（`LLVM-039t`）对 `CCValAssign::SExt` 生成 `AssertSext`，随后的 `sext` 被 DAGCombine 消除，**不产生 `sign_extend_inreg`**。abort 134 只显式发生于 **`sext i8/i16/i32 → i64` 且其操作数扩展未被子断言**（如 `define i64 @g(i8 %x)` 或 `trunc i64→iN` 后 `sext`）。本任务添加 pattern 后这些路径全部 `EXIT=0`，signext 路径维持原行为（不再多用指令）。
2. **`ext.so` 是有符号窄扩展的专用 ISA 指令**（`contract-isa.md §6.4.2`，`ext.so rdhb, rdhc, hd` = 复制低 `hd+1` 位并从 bit `hd` 符号扩展到 64 位，`scope: m1`）。用它比「移位对」或「掩码组合」更**正确 + 最简**：单条、无临时寄存器、**不引 constant pool**（C12 约束），且 `hd=7/15/31` 与 i8/i16/i32 一一对应。TableGen 直接写 3 条 `Pat` 即可，无需 `Custom` lowering。
3. **`ext.so` 的 orri 立即数 `hd` 就是符号位索引**（非起始位-1）：`hd=N-1`；已被 MC 编码与 objdump 逐值核对。
4. **窄访存 + `sext` 不冲突**：`load iN` 后 `sext` 由 DAGCombine 折成 `sextload` → `ld.sb/sw/st`（C13/`LLVM-036t`），不会叠加 `ext.so`；仅「寄存器值」的 `sext` 走 `ext.so`。
5. **`llvm-objdump` 支持 `--triple=dadao`**：可直接反汇编 `llc -filetype=obj` 产物，用于把「ISel 选中 → MC 编码」的链路独立核对（本次 `ext.so rd31, rd16, 7` = `40 65 f4 07`）。
6. **脚本坑（非产品缺陷）**：`grep -oE '\[0x[0-9a-f,]+\]'`（本机 GNU grep 3.11）对 `…,0x…]` 返回不匹配，改 `'\[0x[^]]+\]'` 正常；`awk '%x'` 不解析 `"0x40"` 字符串（得 0/空），hex 解析改用 Python。均已修入 `run.sh`。

**遗留问题**：

- **可选增强未做**：`tests/codegen/call_narrow_args.ll` 仍只用无符号窄参数。本修复后「有符号窄参数」已可编译，但把它改成含 `sext` 的变体需同步 `tests/codegen/expected.yaml` + `tools/testcases/validate_codegen_vectors.py` 的独立 oracle，且 e2e 门 `make test-codegen`（`INTEG-012t`）仍为 `待开始`（Makefile 无该 target）。属任务书明示**可选**项，且触及 `tests/codegen/**`（TESTCASES 模块），本任务不改动，仅记录。
- **范围外（任务明示）**：`i1` 的 `sext_inreg`、`i128`（→M4）、指针（64 位无窄扩展）、RF 浮点均不在本任务；未添加相应 pattern（保持显式 `Cannot select`，不静默）。
- **既有台账不一致（非本任务引入）**：`components/llvm-project/changelog.md` 缺 `LLVM-040t`/`LLVM-041t` 两条（两任务均 `已验证`），本任务未代补（越界），附此披露。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**（逐行）：组件源码 `DADAOCodeGen.td`（新增 3 条 pattern + 段注释 + 文件头）；导出的 `DADAOCodeGen.td.patch`；`components/llvm-project/changelog.md`；`.work/evidence/LLVM-047t/{run.sh,sem_check.py}`。

**审查要点（逐行）**：

- **逻辑正确性**：`sext_inreg` 的三个 VT（i8/i16/i32）分别映射 `ext_so_orri` 的 `hd=7/15/31`，与 `contract-isa.md §6.4.2`「从 bit `hd` 符号扩展」一致；结果 VT 显式 `i64`（GPRD）；源限 `GPRD`（指针 64 位无窄扩展，不会误配 GPRB）；`ext.so` 对非负值高位补 0、对负值高位补 1，与二元补码一致（`sem-*` 逐样本独立重算：`-1/-128/127/0/…EF`）。
- **设计/惯用法**：复用既有 ISA 指令 `ext.so`（`ext_so_orri`，orri），**单条、无临时寄存器、不引 constant pool**（C12）；TableGen pattern 置于 `DADAOCodeGen.td` 的算术/位运算段旁，风格同 `and_o`/`shl_uo_orrr` 与 AArch64 `SBFMXri` 的 `sext_inreg` 写法；未改任何函数签名、未引外部依赖、未新增指令。
- **防造假**：完成区所有 `ninja`/`llc`/`llvm-mc`/`llvm-objdump`/`make` 输出均 `cmd > log 2>&1; rc=$?` 捕获；证据脚本结尾 `echo "EXIT=$rc"; exit "$rc"`，无 `tee`；`--inject` 真实改源码（sha256 变化 + `git diff --name-only` 非空）、真实重建、真实 FAIL（3 条）、真实还原（cp 回写 + sha256 一致 + `git status --porcelain` 空）+ 重建回绿。
- **边界**：i8/i16/i32 的最小负值、-1、最大正值、0、以及带高位「垃圾位」的输入；显式 `sext`、`signext` 形参、`load`+`sext`、`trunc`+`sext` 四条来源；`-O1`/`-O2` verifier 12/12；asm/obj/MC 三层编码一致。
- **越界**：仅改任务列出的组件源 1 文件 + 其导出补丁 + `changelog.md`（`Process-01` 强制）+ 本任务书；`.work/source/llvm-project` 收敛 base+1 且干净。

**findings 与处置**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | 证据脚本 `mir_explicit` 把 MIR 写到 `$TMP/$tag.mir`，但 `no_zeroext`/`sem_run` 读 `$TMP/mir-explicit-$tag.mir` → 三个 i16/i32/i8 检查因文件缺失 FAIL | ✅已修 | 输出路径改为 `$TMP/mir-explicit-$1.mir` | 复跑：`mir-explicit-*`/`no-zeroext-*`/`sem-*` 全 PASS（23/23） |
| 2 | `mc-encoding` 用 `awk '%x'` 解析 `"0x40"` 得空/0（awk 不认 0x 前缀）→ `got` 空 → FAIL | ✅已修 | 改用 `python3` 解析字节数组拼 big-endian 字 | `mc-encoding-ext.so` PASS（K=7/15/31 逐值 `0x40648247/4f/5f`） |
| 3 | `grep -oE '\[0x[0-9a-f,]+\]'` 在本机 GNU grep 3.11 对 `…,0x…]` 不匹配（同类模式 `\[0x[^]]+\]` 正常）→ 编码提取为空 | ✅已修 | 模式改为 `'\[0x[^]]+\]'`；同类全脚本排查（仅此 1 处用于提取） | `mc-encoding-ext.so` PASS |
| 4 | 段/文件头注释未提及本任务的 `sext_inreg` pattern | ✅已修 | `DADAOCodeGen.td` 文件头与新增段注释补 LLVM-047t 说明 | 重建 `BUILD_EXIT=0`；patch 含注释行 |
| 5 | 任务书验收 2 列出 `signext` 形参「同类 abort」，实测其本就 `EXIT=0` | ❌不修（如实披露） | 不改产品；在「新发现/坑 #1」「遗留」记录 | `mir-signext-i8/i16/i32` 均 `EXIT=0`（真实 MIR），正是任务要求的结果 |

**自审判决**：finding #1–#4 全部 ✅已修 + 复验；#5 为例外披露（不改）。证据脚本 23/23 PASS 且 `--inject` 具备可达 FAIL（零扩展注入 → 负值样本 3 条 FAIL）与可复原性（cp+sha256+`git status`+重建）；完成区结论与真实输出逐条对齐；回归 033t~041t 全 PASS；`make check` 33/33 + `check-patch-tree` 80 OK + `check-source-state` clean。任务状态置 **待验收**，交 reviewer 独立验收。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer（mimo-v2.5-pro）
**审查时间**：2026-10-05T16:33+08:00

##### 一、证据脚本审查

**`run.sh` 审查（逐条）**：
- `set -u`（无 `set -e`），靠 `FAILED` 变量追踪——合规，每条 check 调 `report()` 后显式 `return`，失败设 `FAILED=1`。
- `report()` 打印 PASS/FAIL + expected/actual/exit，格式清晰。✓
- `rebuild_llc()` 输出重定向到 log，无 `tee`。✓
- `mir_explicit()`：FAIL 路径可达（rc≠0 或 grep 不匹配 → report FAIL + return 1）。✓
- `mir_signext()`：FAIL 路径可达（rc≠0 或 log 含 `Cannot select` → FAIL）。✓
- `no_zeroext()`：FAIL 路径可达（so<1 或 uo>0 → FAIL）。✓
- `sem_run()`：调 `sem_check.py`，rc≠0 时 FAIL。✓
- `--inject` 模式：备份 cp、sha256 比对、`git diff --name-only` 非空守卫、`git status --porcelain` 恢复校验、还原后重建——合规。✓
- 结尾 `echo "RESULT: ..."; exit "$FAILED"`，无 `tee` 吞退出码。✓
- 每条断言均有可达 FAIL 路径；注入非空（sha 变化 + diff 非空）且可还原（cp 还原 + sha 一致 + status clean）。

**`sem_check.py` 审查**：
- 模型 `model(v)`：提取 MIR 中的 op/k → 检查 k==N-1 → 按 `ext.so` 语义（低 k+1 位，bit k 符号扩展）计算。**独立于 llc/QEMU**。
- `expected(v)`：纯 Python 二元补码（`x = v & mask; if signbit: x -= 2^N`）。**独立于 llc/QEMU**。
- 两个函数数学等价（我手算确认：都提取低 N 位并从 bit N-1 符号扩展，只是实现路径不同）。✓
- 不合格项：**无**。

##### 二、重跑记录

```bash
$ cd /mnt/tao/DADAO-v5 && bash .work/evidence/LLVM-047t/run.sh > /tmp/opencode/LLVM-047t-review/reviewer-run.log 2>&1; echo "EXIT=$?"
EXIT=0
```

逐项输出（23/23 全 PASS）：

| # | 检查名 | expected | actual | exit |
|---|--------|----------|--------|------|
| 1 | llc-exists | executable | ok | 0 |
| 2 | llc-version | rc=0 and dadao registered | rc=0, dadao=yes | 0 |
| 3 | mir-explicit-i8 | ext_so_orri imm=7 | ext_so_orri %0, 7 | 0 |
| 4 | mir-explicit-i16 | ext_so_orri imm=15 | ext_so_orri %0, 15 | 0 |
| 5 | mir-explicit-i32 | ext_so_orri imm=31 | ext_so_orri %0, 31 | 0 |
| 6 | mir-signext-i8 | rc=0, no Cannot select | rc=0 | 0 |
| 7 | mir-signext-i16 | rc=0, no Cannot select | rc=0 | 0 |
| 8 | mir-signext-i32 | rc=0, no Cannot select | rc=0 | 0 |
| 9 | no-zeroext-i8 | ext_so>=1 and ext_uo=0 | ext_so=1 ext_uo=0 | 0 |
| 10 | no-zeroext-i16 | ext_so>=1 and ext_uo=0 | ext_so=1 ext_uo=0 | 0 |
| 11 | no-zeroext-i32 | ext_so>=1 and ext_uo=0 | ext_so=1 ext_uo=0 | 0 |
| 12 | sem-i8 | two's-complement match (N=8) | all samples OK | 0 |
| 13 | sem-i16 | two's-complement match (N=16) | all samples OK | 0 |
| 14 | sem-i32 | two's-complement match (N=32) | all samples OK | 0 |
| 15 | verify-machineinstrs-O1-O2 | 12/12 rc=0 | all-clean | 0 |
| 16 | asm-emit-ext.so | ext.so rd31, rd16, 7/15/31 | ok | 0 |
| 17 | obj-emit-ext.so | objdump: ext.so rd31, rd16, 7/15/31 | ok | 0 |
| 18 | mc-encoding-ext.so | word == 0x40648240\|K | ok | 0 |
| 19 | source-invariants | 3 sext patterns, 0 ext.uo | sext=3 ext_uo=0 | 0 |
| 20 | patch-hunks | valid hunk + 3 patterns | ok | 0 |
| 21 | check-patch-tree | make rc=0 | rc=0 | 0 |
| 22 | check-source-state | make rc=0 | rc=0 | 0 |
| 23 | check-lit | make rc=0 | rc=0 | 0 |

##### 三、独立符号扩展重算比对表

我**独立**按 `ext.so` 语义（`contract-isa.md §6.4.2`：`rdhb[hd:0]=rdhc[hd:0]; rdhb[63:hd+1]=sign_extend(rdhc[hd])`）与二元补码，对所有样本**逐一重算**：

**i8（hd=7）**：

| 输入 V | 低 8 位 | bit7 | 符号扩展 64 位 | 二元补码 i8→i64 | 一致 |
|--------|---------|------|---------------|-----------------|------|
| 0xFF | 0xFF=11111111 | 1 | 0xFFFFFFFFFFFFFFFF | -1→0xFFFFFFFFFFFFFFFF | ✓ |
| 0x80 | 0x80=10000000 | 1 | 0xFFFFFFFFFFFFFF80 | -128→0xFFFFFFFFFFFFFF80 | ✓ |
| 0x7F | 0x7F=01111111 | 0 | 0x000000000000007F | 127→0x000000000000007F | ✓ |
| 0x00 | 0x00 | 0 | 0x0000000000000000 | 0→0 | ✓ |
| 0x1234567890ABCDE**F** | 0xEF=11101111 | 1 | 0xFFFFFFFFFFFFFFEF | -17→0xFFFFFFFFFFFFFFEF | ✓ |

**i16（hd=15）**：

| 输入 V | 低 16 位 | bit15 | 64 位结果 | i16→i64 补码 | 一致 |
|--------|---------|-------|----------|-------------|------|
| 0xFFFF | 0xFFFF | 1 | 0xFFFFFFFFFFFFFFFF | -1 | ✓ |
| 0x8000 | 0x8000 | 1 | 0xFFFFFFFFFFFF8000 | -32768 | ✓ |
| 0x7FFF | 0x7FFF | 0 | 0x0000000000007FFF | 32767 | ✓ |
| 0x0000 | 0 | 0 | 0 | 0 | ✓ |
| 0x1234567890AB**8000** | 0x8000 | 1 | 0xFFFFFFFFFFFF8000 | -32768 | ✓ |

**i32（hd=31）**：

| 输入 V | 低 32 位 | bit31 | 64 位结果 | i32→i64 补码 | 一致 |
|--------|---------|-------|----------|-------------|------|
| 0xFFFFFFFF | 0xFFFFFFFF | 1 | 0xFFFFFFFFFFFFFFFF | -1 | ✓ |
| 0x80000000 | 0x80000000 | 1 | 0xFFFFFFFF80000000 | -2147483648 | ✓ |
| 0x7FFFFFFF | 0x7FFFFFFF | 0 | 0x000000007FFFFFFF | 2147483647 | ✓ |
| 0x00000000 | 0 | 0 | 0 | 0 | ✓ |
| 0xDEADBEEF**80000000** | 0x80000000 | 1 | 0xFFFFFFFF80000000 | -2147483648 | ✓ |

**结论**：全部 15 个样本，`ext.so` 语义模型与独立二元补码模型**逐值一致**。高「垃圾位」被正确忽略（仅取低 N 位）。

此外，我独立调用 `sem_check.py` 验证实际 MIR 中提取的指令与 `hd` 值：
```
N=8  op=ext_so_orri hd=7  0xFF→0xffffffffffffffff OK, 0x80→0xffffffffffffff80 OK, 0x7F→0x7f OK, 0x00→0 OK
N=16 op=ext_so_orri hd=15 0xFFFF→0xffffffffffffffff OK, 0x8000→0xffffffffffff8000 OK, 0x7FFF→0x7fff OK, 0x0000→0 OK
N=32 op=ext_so_orri hd=31 0xFFFFFFFF→0xffffffffffffffff OK, 0x80000000→0xffffffff80000000 OK, 0x7FFFFFFF→0x7fffffff OK, 0x00000000→0 OK
```
全部 EXIT=0。

##### 四、独立注入

**注入点**：将 i8 pattern 的 `hd=7` 改为 `hd=6`（少扩展 1 位，从 bit6 符号扩展而非 bit7）——与 engineer 的 `ext_so→ext_uo` 注入**不同**。

```bash
# 注入前 sha
$ sha256sum .work/source/llvm-project/llvm/lib/Target/DADAO/DADAOCodeGen.td
00dcd37fc398262045305bf68e7217e0d7b3ef458f997c3dd029f7c6822db956

# 注入：edit ext_so_orri GPRD:$src, 7 → ext_so_orri GPRD:$src, 6
# 注入后
$ git diff --name-only .work/source/llvm-project/
llvm/lib/Target/DADAO/DADAOCodeGen.td   ← 非空 ✓

$ sha256sum .work/source/llvm-project/llvm/lib/Target/DADAO/DADAOCodeGen.td
3a0730bc2a2667c3a3ec815dba709854c2d42b65520a752ed09649b9ca750e4e   ← 变化 ✓

# 重建（预计 ~1 分钟，仅 TableGen 重生成）
$ ninja -j8 -C .work/build/llvm llc > /tmp/opencode/LLVM-047t-review/inject/rebuild.log 2>&1
BUILD_EXIT=0

# 语义检查：hd=6 不匹配 N-1=7 → FAIL
$ python3 .work/evidence/LLVM-047t/sem_check.py <injected-i8.mir> 8 0xFF 0x80 0x7F 0x00
FAIL: ext index hd=6, expected N-1=7
SEM_EXIT=1   ← 确认 FAIL ✓

# 还原
$ cp /tmp/opencode/LLVM-047t-review/inject/DADAOCodeGen.td.bak <src>
$ sha256sum → 00dcd37fc398...  ← 与注入前一致 ✓
$ git diff --name-only → (空)  ← 干净 ✓
$ git status --porcelain → (空) ← 干净 ✓

# 还原后重建
$ ninja -j8 -C .work/build/llvm llc
RESTORE_BUILD_EXIT=0

# 还原后语义检查回绿
$ python3 .work/evidence/LLVM-047t/sem_check.py <restored-i8.mir> 8 0xFF 0x80 0x7F 0x00
N=8 op=ext_so_orri hd=7 V=0x...ff model=0x...ffffffffffffff expected=0x...ffffffffffffff OK  (×4)
POST_RESTORE_SEM_EXIT=0  ← 回绿 ✓
```

**注入有效性**：`git diff --name-only` 非空、sha256 变化、注入后 sem_check FAIL、还原后 sha256 一致 + status 干净 + 重建后回绿。

##### 五、独立复核验收 1–5

| # | 验收标准 | 结果 | 证据 |
|---|---------|------|------|
| 1 | `ninja llc` EXIT=0 | ✅ | 重跑 `BUILD_EXIT=0`（log `LLVM-047t-ev-rebuild.log`） |
| 2 | `llc -stop-after=finalize-isel` 对 i8/i16/i32 sext + signext EXIT=0，不 `Cannot select`，不 abort | ✅ | `mir-explicit-*` 三条确认 `ext_so_orri` + imm；`mir-signext-*` 三条 EXIT=0；我独立跑 `signext_i8` MIR 仅含 `COPY $rd16 → COPY $rd31 → RET_PSEUDO`（无 ext.so，符合 AssertSext 消除 sext） |
| 3 | 符号扩展正确（逐一重算） | ✅ | 见「三、独立符号扩展重算比对表」15/15 一致 |
| 4 | `-O1/-O2 -verify-machineinstrs` EXIT=0 | ✅ | `verify-machineinstrs-O1-O2` 12/12 all-clean |
| 5 | 不回归 033t~041t；check-patch-tree 80；check-lit 33/33；check EXIT=0 | ✅ | `check-patch-tree rc=0`、`check-source-state rc=0`、`check-lit rc=0`（重跑确认） |

##### 六、独立核实 `signext` 形参声明

**任务书原文**（约束段）：「`sext i8/i16/i32` 形参 → `sign_extend_inreg` 无 ISel → `llc` abort 134」

**engineer 修正**：`i8/i16/i32 signext` 形参**本就 EXIT=0**（`LLVM-039t` 的 `AssertSext` 消除该 sext，不产生 `sign_extend_inreg`）。abort 仅发生在**显式 `sext` 且扩展未被子断言**时。

**我独立核实**：对 `signext_i8.ll`（`define i64 @f(i8 signext %x) { %e = sext i8 %x to i64; ret i64 %e }`）运行 `llc -stop-after=finalize-isel`，MIR 为：
```
%0:gprd = COPY $rd16
$rd31 = COPY %0
RET_PSEUDO implicit $rd31
```
无 `ext_so_orri`、无 `Cannot select`、EXIT=0。**确认 engineer 的修正正确**。

**结论**：任务书该表述需订正——「`signext` 形参 → abort 134」不成立；应改为「显式 `sext i8/i16/i32 to i64`（其操作数扩展未被子断言）→ abort 134」。此订正**不影响任务目标的正确性**（abort 确实存在且已修复），但准确性需订正。代主会话记。

##### 七、台账缺口判定

**确认**：`components/llvm-project/changelog.md` 缺 `LLVM-040t` 和 `LLVM-041t` 两条组件变更条目（两任务均 `已验证`）。

**判定**：这是**既有的、非本任务引入的台账缺口**。本任务已正确添加 LLVM-047t 条目，且 engineer 明确披露此缺口（不代补，防越界）。**建议**：主会话另立独立补录任务（如 `LLVM-INFRA-changelog-backfill`），不混入本任务验收。本任务不因此缺口打回。

##### 八、范围判定

- **改动文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOCodeGen.td.patch`（导出补丁）+ `components/llvm-project/changelog.md`（Process-01 强制）+ 任务书。**未改 `tests/codegen/**`、`contracts/**`**。✓
- **可选增强**（`call_narrow_args.ll` 加有符号窄参）未做——任务书明示可选，且涉及 TESTCASES 模块。合理。✓
- **.work/source 内**：仅 `DADAOCodeGen.td` 新增 3 条 pattern + 注释段。✓

##### 九、判决

**Accepted**

验收命令块 23/23 全 PASS（重跑确认）、独立注入 FAIL→还原→回绿确认、15 个符号扩展样本逐一独立重算一致、编码与 `opcodes.yaml` 核对一致、范围正确。任务状态置 `已验证`。

**需主会话处理**：
1. 任务书「signext 形参 → abort 134」表述需订正为「显式 `sext` 且操作数扩展未被子断言 → abort 134」。
2. `changelog.md` 缺 LLVM-040t/041t 条目——建议另立补录任务。
