# TESTCASES-026t: CodeGen 独立测试向量

**模块**：testcases
**项目里程碑**：M3
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`SPEC-096k` §边界（M3 = 标量整数/指针）；`.tao/knowledge/contract-abi.md`（+ `SPEC-097t` 的 §4 正文）。
- **输出**：
  - `tests/codegen/*.ll`：M3 标量程序的源 IR（每程序一个文件），覆盖 **算术 / 访存 / 分支 / 调用** 四类，每类 ≥1，且**互不依赖外部符号/全局变量/变参/聚合**。
  - `tests/codegen/expected.yaml`（或等价）：每程序的**期望结果**（退出码/返回值），带**独立推导依据**（见约束）。
  - `tools/testcases/validate_codegen_vectors.py`：校验向量 schema/覆盖/期望值格式（可失败）。
- **约束**：
  - **Independent oracle**（project 硬约束）：期望值**不得**由 LLVM（`llc`）或 QEMU 生成，必须**独立派生**——在 host 侧用独立脚本/Python 按 IR 语义算出（或手算并写明推导）。
  - **程序形态**：IR 层可被 M3 后端编译（标量、无变参/聚合/sret/间接调用/全局变量/`.data`）；入口约定与 `INTEG-012t` 的 harness 对齐（程序把结果写入 exit port 或返回码，harness 读退出码比较；具体接口在 `INTEG-012t` 冻结，本任务与之对齐）。
  - **覆盖矩阵（对齐 §5 判定）**：算术（add/sub/常量材料化，含负常数与高位 wyde 序列 → C12）、访存（load/store + 偏移，含**大端窄访存** `ld.ub/uw/ut`/`ld.sb/sw/st` 的字节偏移/扩展 → C13/`ADR-0018（C13）`）、分支（有符号谓词 + 循环；`==`/`!=` 用 `br.eq/ne`、`p==NULL` 用 `br.z/nz {rb}`、`p==q` 用 `cmp.uo`（`dbb`）+`br.z` → C17）、调用（直接 call/ret + 返回值 + 多参数/栈参数至少一例；堆溢出按**全局声明序**、窄参数 caller 扩展 → C4/`ADR-0018（C4）`）；另含**指针参数/返回 bank**（指针落 GPRB/`rb31` → C1/C5）与**指针算术**各 ≥1：`add.o`（orrr，rb 目的，base+offset）、`cmp.uo`（orrr `dbb`）指针比较（→ C14/`ADR-0018（C14）`）、**`ptr−ptr` 指针差**（两指针相减，后端选出新增指令 `sub.o_orrr_dbb` = RB−RB→RD；语义见 `SPEC-100t`/`adr-0012 D9`；期望值 = 两地址整数差，**独立按 IR 语义推导**，不得从 `llc`/QEMU 反推）。给出「程序 ↔ 覆盖点」表。
  - **期望值**：每条给出最小/边界/负值样本（如算术含负操作数、访存含非零偏移与窄宽度大端字节序、分支覆盖 taken/not-taken、指针算术含非零偏移、**`ptr−ptr` 含负差（小地址 − 大地址）与正差各 ≥1**、调用含指针参数）。
  - **validator 能失败**：对注入的反例（改期望值 / 改 IR / 少一个覆盖类别）必须报 FAIL；完成区给出反例注入真实输出。
  - 不改 `contracts/**`、不改既有 `tests/vectors/**`（M3 codegen 向量独立目录）；不提交 git。

## 验收标准

1. `tests/codegen/` 含四类程序文件 + 期望值；`tools/testcases/validate_codegen_vectors.py` 退出 0，且**覆盖矩阵四类齐全**（≥1 算术/访存/分支/调用），且含**指针差 `ptr−ptr`** 用例 ≥1（期望值为两地址整数差，**独立派生**自 IR 语义）。
2. 每条期望值有**独立推导证据**（host 计算脚本输出或手算说明），**非**来自 `llc`/QEMU。
3. validator 反例门控：注入反例 → 非零退出（真实输出留存 `.work/log/testcases/`）；还原 → 回绿。
4. 不引入仓库残留（`make check-dirs`/`check-no-residue` 干净）。

## 完成区

**测试结果**：全绿。`python3 tools/testcases/validate_codegen_vectors.py` → **PASS (58 checks)**，EXIT=0；`.work/evidence/TESTCASES-026t/derive.py` 独立重算 → **PASS (15 programs)**，EXIT=0；一键证据 `.work/evidence/TESTCASES-026t/run.sh` → **EXIT=0**（含 3 类注入自检：改期望值 / 改 IR / 少覆盖类，均「改后 FAIL → 还原 sha256 一致 → 回绿」）；`llc -march=dadao` 对全部 15 个程序 EXIT=0（结构性 smoke，非期望值来源）；`make check` EXIT=0（lit 33/33）；`make check-dirs`/`make check-no-residue` EXIT=0。

**修改文件**（全部为本任务范围内新建；未改任何既有文件、未改 `contracts/**`、未改 `tests/vectors/**`、未改 `components/**`）：
- `tests/codegen/arith_add_sub_neg.ll`、`arith_const_hi_wyde.ll`（算术）
- `tests/codegen/mem_store_load_offset.ll`、`mem_narrow_be_bytes.ll`、`mem_narrow_be_wide.ll`（访存 / 大端窄访存）
- `tests/codegen/branch_loop_sum.ll`、`branch_eq_ne.ll`、`branch_ptr.ll`（分支）
- `tests/codegen/call_direct_ret.ll`、`call_multiarg_stack.ll`、`call_narrow_args.ll`、`call_ptr_bank.ll`（调用）
- `tests/codegen/ptr_add_offset.ll`、`ptr_diff_pos.ll`、`ptr_diff_neg.ll`（指针算术 / 指针差）
- `tests/codegen/expected.yaml`（期望值 + 独立推导依据 + 覆盖点）
- `tests/codegen/README.md`（约定 + **程序 ↔ 覆盖点表**）
- `tools/testcases/validate_codegen_vectors.py`（schema / 覆盖 / IR 形态 / 期望值 oracle 校验，可失败）
- 证据（gitignored）：`.work/evidence/TESTCASES-026t/{run.sh,derive.py}`；日志 `.work/log/testcases/TESTCASES-026t-{validate,evidence,make-check,llc-structural}.log`

**覆盖矩阵（4 类齐全；程序 ↔ 覆盖点见 `tests/codegen/README.md`）**：
- 算术（2+2）：C12 负常数材料化 + add/sub（`arith_add_sub_neg`，246）；C12 高位 wyde 全 4 wyde 常数（`arith_const_hi_wyde`，238）；`ptr−ptr` 正差（`ptr_diff_pos`，7）/负差（`ptr_diff_neg`，249 raw −7）。
- 访存（3+1）：load/store 非零元素偏移（`mem_store_load_offset`，77）；大端窄访存 `ld.ub`@0/7 + `ld.sb`@3（`mem_narrow_be_bytes`，41）；大端 `ld.uw`@0/6 + `ld.ut`@4 + `ld.sw`@2 + `ld.st`@0（`mem_narrow_be_wide`，236）；指针 base+运行时偏移（`ptr_add_offset`，171）。
- 分支（3）：有符号谓词循环 taken/not-taken（`branch_loop_sum`，45）；`==`/`!=`→`br.eq/ne`（`branch_eq_ne`，16）；`p==NULL`→`br.z/nz {rb}` + `p==q`→`cmp.uo`(dbb)+`br`（`branch_ptr`，25）。
- 调用（4）：直接 call/ret + 返回值（`call_direct_ret`，9）；18 参数 → 2 栈槽、按声明序（`call_multiarg_stack`，171）；窄参数 caller 扩展（`call_narrow_args`，137）；指针参数 `rb16` / 指针返回 `rb31`（`call_ptr_bank`，42）。

**验收结果**（真实命令 + 输出 + 退出码；制式 `cmd > log 2>&1; rc=$?`，无 `tee`）：

1. **四类程序 + 期望值 + validator + `ptr−ptr`**（验收 1）：
```
$ python3 tools/testcases/validate_codegen_vectors.py; echo "EXIT=$?"
...
validate_codegen_vectors: PASS (58 checks)
EXIT=0
```
含 `categories-known` / `category-coverage`（四类齐全）、`coverage-required`（C1/C4/C5/C12/C13/C14/C17 + `ptr.diff-pos`/`ptr.diff-neg`/… 均在）、`expected-vs-oracle[*]`（15 条期望值 = 宿主 oracle）、`ir-main-signature[*]`/`ir-m3-boundary[*]`。`ptr−ptr` 用例 `ptr_diff_pos.ll`（7）、`ptr_diff_neg.ll`（249 = raw −7 的低 8 位）。

2. **独立推导证据**（验收 2，**非** llc/QEMU）：
```
$ python3 .work/evidence/TESTCASES-026t/derive.py; echo "EXIT=$?"
[PASS] arith_add_sub_neg.ll: expected=246 derived=246
[PASS] arith_const_hi_wyde.ll: expected=238 derived=238
[PASS] mem_store_load_offset.ll: expected=77 derived=77
[PASS] mem_narrow_be_bytes.ll: expected=41 derived=41
[PASS] mem_narrow_be_wide.ll: expected=236 derived=236
[PASS] branch_loop_sum.ll: expected=45 derived=45
[PASS] branch_eq_ne.ll: expected=16 derived=16
[PASS] branch_ptr.ll: expected=25 derived=25
[PASS] call_direct_ret.ll: expected=9 derived=9
[PASS] call_multiarg_stack.ll: expected=171 derived=171
[PASS] call_narrow_args.ll: expected=137 derived=137
[PASS] call_ptr_bank.ll: expected=42 derived=42
[PASS] ptr_add_offset.ll: expected=171 derived=171
[PASS] ptr_diff_pos.ll: expected=7 derived=7
[PASS] ptr_diff_neg.ll: expected=249 derived=249
derive: PASS (15 programs)
EXIT=0
```
`expected.yaml` 每条附 `derivation`（按 IR 语义手算说明）；`validate_codegen_vectors.py` 内嵌**宿主 IR-语义 oracle**（大端内存 + 64 位补码）复算全部 15 条。

3. **validator 反例门控**（验收 3）：
```
$ bash .work/evidence/TESTCASES-026t/run.sh; echo "EXIT=$?"
...
[PASS] inject-expected-value | expected: file changed
[PASS] inject-expected-value -> validator FAIL | expected_rc!=0 actual_rc=1
[PASS] restore-expected-value | expected: sha256 unchanged
[PASS] restore-expected-value -> validator PASS | expected_rc=0 actual_rc=0
[PASS] inject-ir-shape | expected: file changed
[PASS] inject-ir-shape -> validator FAIL | expected_rc!=0 actual_rc=1
[PASS] restore-ir-shape | expected: sha256 unchanged
[PASS] restore-ir-shape -> validator PASS | expected_rc=0 actual_rc=0
[PASS] inject-missing-category | expected: file changed
[PASS] inject-missing-category -> validator FAIL | expected_rc!=0 actual_rc=1
[PASS] restore-missing-category | expected: sha256 unchanged
[PASS] restore-missing-category -> validator PASS | expected_rc=0 actual_rc=0
TESTCASES-026t evidence: PASS
EXIT=0
```
三类注入的真实 FAIL 原因（摘 `.work/log/testcases/TESTCASES-026t-evidence.log`）：
- 改期望值（`246→247`）：`[FAIL] expected-vs-oracle[arith_add_sub_neg.ll] expected=247 oracle=246`；
- 改 IR（`define i64 @main()`→`define void @main()`）：`[FAIL] ir-main-signature[branch_ptr.ll] missing 'define i64 @main()'`；
- 少覆盖类（`category: branch`→`misc`）：`[FAIL] categories-known` / `category-coverage`。

4. **无仓库残留**（验收 4）：
```
$ make check-dirs;        echo "EXIT=$?"   → check-dirs: PASS        EXIT=0
$ make check-no-residue;  echo "EXIT=$?"   → check-no-residue: PASS  EXIT=0
$ make check;             echo "EXIT=$?"   → repository checks: PASS; lit 33/33; EXIT=0
$ git status --untracked-files=all --short → 仅 17 个 tests/codegen/ 文件 + 1 个 tools/testcases/ 新文件（见「修改文件」）
```

5. **一键证据脚本**（下发要求 5）：`.work/evidence/TESTCASES-026t/run.sh` → EXIT=0；非交互、任一检查失败即非零退出、逐项打印「检查名 + 期望 + 实际 + rc」、内置 3 类注入自检、结尾显式 `exit` 且**无 `tee`**。

6. **结构性 smoke（附加，非期望值来源）**：`llc -march=dadao` 对 15 个程序全部 EXIT=0；MIR/汇编核对到目标指令（`.work/log/testcases/TESTCASES-026t-llc-structural.log`）：`ld.ub/sb/uw/sw/ut/st`、`cmp.uo`、`br.eq/ne`、`br.nz {rb}`、`sub.o`、`set.zw/ow`+`or.w/andn.w`、`call`/`ret` 均命中。

**新发现/坑**：
1. **LLVM IR 的 `0x…` 十六进制字面量是「浮点」**：`i64 0xFEDC…` 报 `error: floating point constant invalid for type`；整数十六进制须写 `u0x…`（或十进制）。已改 `u0x…`。
2. **`sext i8/i16/i32` 作用于「形参」→ Cannot select**：lower 成 `sign_extend_inreg`，M3 后端未选（`LLVM ERROR: Cannot select: … sign_extend_inreg`，abort 134）。故**有符号**窄参数的 caller 扩展无法用「callee 内 `sext`」观测；`call_narrow_args.ll` 改用**无符号**窄参数（`zext` = `and` 掩码，可编译）。这是后端能力缺口（→「遗留问题 1」）。
3. **`sext` 结果若最终 `& 255` 会被（正确）优化掉**：`SimplifyDemandedBits` 只要求低 8 位，sext 与 zext 低 8 位相同 → 优化掉，无法通过低字节掩码观测符号扩展。故窄访存向量改为「右移取符号位再 `& 255`」（`>>8`/`>>16`/`>>32`），使 `sext` 在 0..255 通道内可观测（汇编实测 `ld.sb`/`ld.sw`/`ld.st`）。
4. **C14 `add.o`（指针 base+offset 直接落 GPRB）后端尚未选出**：`ptr_add_offset.ll` 实测走 `rb2rd`→GPRD `add.uo`→`rd2rb`（与 `LLVM-036t` 遗留「C14 D1 未实现」一致）；该向量覆盖 C14 的**意图**，E2E 语义仍正确（→「遗留问题 2」）。
5. **指针比较需「指针形参」**：`cmp.uo`(dbb) / `br.z/nz {rb}` 只在 `isPointerBankValue`（GPRB `CopyFromReg`）成立时选出；alloca 派生的指针不被识别。故 `branch_ptr.ll` 把 `p==NULL`/`p==q` 放进「吃指针形参」的 helper。
6. **`i8* null` 常量可编译**（GPRB 物化 0，实测 `rd2rb rb17, rd34(=0)`）；无需 `inttoptr`。
7. **`volatile` + `noinline` 是必要的**：`llc` 默认 `-O2` 会把全常量程序折叠成一条 `ret`；用 volatile 栈槽作输入、helper 标 `noinline`，保证 add/sub/循环/调用/窄访存真实存在。`alloca [N x T]` 是本地内存（非「聚合传参/返回」），符合 M3 边界。

**遗留问题**：
1. **有符号窄参数/窄返回扩展（C4 侧 `sext` / C5 侧 callee `sext`）无法在当前 M3 后端编译**：根因 `sign_extend_inreg` 无 ISel（新发现 2）。本任务只覆盖**无符号**窄参数 caller 扩展；建议另立 LLVM 任务补窄 `sext` 支持（或在前端属性 fixed 后免重扩展）。**非本任务引入**。
2. **C14 D1「指针算术直接落 GPRB（单条 `add.o`）」后端未实现**（`LLVM-036t` 已披露）：`ptr_add_offset.ll` 记录了该覆盖意图，但当前 E2E 会看到 `rb2rd`/`rd2rb` 路径；`INTEG-012t` 的门槛「覆盖 `add.o`」在该能力落地前无法字面满足（语义正确）。
3. **端到端执行不在本任务**：按任务书「只产出 `.ll` + `expected.yaml` + validator，不建 harness」，guest 退出码 vs 期望值的比较由 `INTEG-012t` 承担；本任务未运行 QEMU。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**（逐行）：15 个 `.ll`、`expected.yaml`、`tools/testcases/validate_codegen_vectors.py`、`.work/evidence/TESTCASES-026t/{run.sh,derive.py}`、`tests/codegen/README.md`。

**审查要点**：
- **逻辑正确性**：逐条手算 + 独立脚本重算 15 个期望值（含 size/sign 敏感项——`ptr−ptr` 正/负差 = 两地址整数差、`ptrdiff=-7` 的全 64 位补码、`ld.sb/sw/st` 的符号扩展在高位可观测、`call_multiarg_stack` 按声明序 18 参数求和）；`expected.yaml` 的 `derivation` 与 IR 逐条对齐；宿主 oracle 与 `derive.py` 两套独立实现对 15 条结果一致（若任一算错，`expected-vs-oracle` 或 `derive` 必红）。
- **设计/惯用法**：入口统一 `i64 @main()`；`volatile`+`noinline` 防 `-O2` 折叠；指针比较放 GPRB 形参 helper（贴合 `isPointerBankValue`）；无符号窄参数取可编译路径；不引外部依赖、不改既有文件/签名。
- **防造假**：validator/derive/run.sh 输出均为真实运行 `cmd > log 2>&1; rc=$?` 捕获；run.sh 结尾显式 `exit`、无 `tee`；注入前后用 `cmp`+`sha256sum` 证明「确已改」与「确已还原」；`llc` 结构性证据留 `.work/log/testcases/`（并标注**非**期望值来源）。
- **边界/反例**：`llc` 对 15 程序全 EXIT=0；validator 三类注入各有可达 FAIL 路径且还原回绿；`make check` 不回归。
- **越界**：仅新建 `tests/codegen/**` 与 `tools/testcases/validate_codegen_vectors.py`；未改 `contracts/**`/`tests/vectors/**`/`components/**`/`Makefile`；`git status` 仅列本任务新文件。

**findings 与处置**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | `i64 0xFEDC…` 被解析为浮点常量（`arith_const_hi_wyde` 等 3 文件 EXIT=1） | ✅已修 | 3 处改为 `u0x…` | `llc` 15/15 EXIT=0；validator `expected-vs-oracle` 全 PASS |
| 2 | `call_narrow_args.ll` 用 `sext` 形参 → `sign_extend_inreg` Cannot select（EXIT=134） | ✅已修（设计回避，并披露为后端缺口） | 改为无符号窄参数 + `zext`（→`and` 掩码）；注释与完成区说明 | 该文件 `llc` EXIT=0（汇编含 `and.o` 掩码）；保守披露于「新发现 2 / 遗留 1」 |
| 3 | 窄访存的 `sext` 被最终 `& 255` 优化掉，符号扩展在 0..255 通道不可观测 | ✅已修 | `mem_narrow_be_bytes/wide` 改为「右移取符号位再 `& 255`」 | 汇编实测 `ld.sb`/`ld.sw`/`ld.st`；期望值 41/236 由独立重算确认 |
| 4 | 期望值若仅靠 validator 绿灯不足以证明语义；且「改期望值」须能触发 FAIL | ✅已修 | validator 内嵌宿主 IR-语义 oracle（非 llc/QEMU）与 `expected.yaml` 比对；另加独立 `derive.py` 第二实现 | 注入 `246→247` → `expected-vs-oracle` FAIL；两实现 15/15 一致 |
| 5 | 「改 IR」的注入路径 | ✅已修 | validator 校验 `define i64 @main()` + M3 边界（全局变量/变参/sret/byval/nest/invoke/callbr/间接调用/浮点） | 注入 `define void @main()` → `ir-main-signature[branch_ptr.ll]` FAIL |
| 6 | C14 `add.o` 未被后端选出（`ptr_add_offset.ll` 走 `rb2rd`/`rd2rb`） | ⏸延后（非本任务可修；后端能力缺口） | 不改代码；在注释/README/完成区显式说明为「覆盖意图」 | 汇编证据 `.work/log/testcases/TESTCASES-026t-llc-structural.log`；登记「新发现 4 / 遗留 2」 |
| 7 | 新增 `tests/codegen/README.md`（超出 §输出 三件套字面清单） | ✅已改（披露） | 用于承载任务要求的「程序 ↔ 覆盖点表」与约定 | 列于「修改文件」并说明理由；位于 `tests/codegen/` 新目录内 |

**自审判决**：finding #1–#5、#7 全部 ✅已修/已披露，finding #6 为后端能力缺口（非本任务范围）已显式登记；无未处置项。validator 58 项 / derive 15 项 / evidence 全绿、三类注入 FAIL→还原→回绿、`llc` 15/15、`make check` + `check-dirs` + `check-no-residue` 全绿。任务状态置 **待验收**，交 reviewer 独立验收。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理
**审查范围**：15 个 `.ll`、`expected.yaml`、`validate_codegen_vectors.py`、`derive.py`、`run.sh`、`README.md`；独立重算 15 条期望值；独立注入反例。

---

### 1. 证据脚本 + validator 审查

**`run.sh` 审查**（逐条）：
- 非交互 ✓（无 `read`/`stdin` 依赖）
- 任一检查失败即 `FAILS` 累加，最终 `$FAILS -ne 0` → `exit 1` ✓
- 逐项打印 `check name | expected | actual | rc` ✓
- 内置 3 类注入自检（改期望值 / 改 IR / 少覆盖类）✓
- 结尾显式 `exit 0`/`exit 1`，无 `tee` 吞退出码 ✓
- 注入前后用 `sha256sum` + `cmp` 验证「确已改」与「确已还原」✓
- 每条断言的 FAIL 路径可达（`expect_zero`/`expect_nonzero` 两支不同结果）✓

**`validate_codegen_vectors.py` 审查**：
- 内嵌 oracle 函数 `oracle(name)` 为纯 Python 算术（`u64`/`sext`/`be_bytes`），**无** `subprocess`/`os.system`/`Popen` 调用，**不调用** `llc`/QEMU ✓
- `grep -E 'subprocess|os\.system|os\.popen|Popen|llc|qemu|QEMU'` 仅命中注释行 ✓
- `check()` 方法两支结果不同（PASS → `passes+1`，FAIL → `fails.append`），非恒真 ✓
- 退出码：有 fails → `return 1`，全 PASS → `return 0` ✓

**`derive.py` 审查**：
- 纯 Python 算术实现，与 validator 内嵌 oracle 为**独立第二实现** ✓
- 无外部工具调用 ✓
- 退出码：有 mismatches → `return 1`，全 PASS → `return 0` ✓

**结论**：证据脚本与 validator 合格，无需返工。

---

### 2. 独立重跑记录

| 命令 | 真实输出（末行） | 退出码 |
|------|-----------------|--------|
| `python3 tools/testcases/validate_codegen_vectors.py` | `validate_codegen_vectors: PASS (58 checks)` | **EXIT=0** |
| `python3 .work/evidence/TESTCASES-026t/derive.py` | `derive: PASS (15 programs)` | **EXIT=0** |
| `bash .work/evidence/TESTCASES-026t/run.sh` | `TESTCASES-026t evidence: PASS` | **EXIT=0** |
| `make check-dirs` | `check-dirs: PASS` | **EXIT=0** |
| `make check-no-residue` | `check-no-residue: PASS` | **EXIT=0** |
| `make check` | `repository checks: PASS; lit 33/33` | **EXIT=0** |

全部与 engineer 完成区声称一致。

---

### 3. 全量独立重算比对表

reviewer 用 **JavaScript**（Code Mode）独立计算，未复用 `derive.py` 或 validator oracle，未用 `llc`/QEMU。size/sign 敏感项逐条标注。

| # | 用例 | reviewer 独立计算过程 | 计算值 | expected.yaml | 匹配 |
|---|------|---------------------|--------|---------------|------|
| 1 | `arith_add_sub_neg.ll` | a=-5,b=3 → c=add=-2,d=sub=8 → e=xor=0xFFFFFFFFFFFFFFF6 → r=e&255 | **246** | 246 | ✓ |
| 2 | `arith_const_hi_wyde.ll` | v=0xFEDC…3210 → hi=v>>56=254, lo=v&0xFF=16 → x=hi^lo=238 → r=x&255 | **238** | 238 | ✓ |
| 3 | `mem_store_load_offset.ll` | buf[0]=100, buf[1]=23 → r=100-23 | **77** | 77 | ✓ |
| 4 | `mem_narrow_be_bytes.ll` | BE bytes [01,02,03,04,05,06,07,08]; byte[3]=0xFE; b0=1,b7=8; s3=sext(0xFE)=-2; shi=(-2>>8)&0xFF=255; r=(10+800+255)&0xFF | **41** | 41 | ✓ |
| 5 | `mem_narrow_be_wide.ll` | h0=0x1122→a8=17; h6=0x7788→b=136; w4=0x55667788→c8=85; n=sext(-300,i16)→nhi=(-300>>16)&0xFF=255; s=sext(-70000,i32)→shi=(-70000>>32)&0xFF=255; r=(17+136+85+255+255)&0xFF=748&0xFF | **236** | 236 | ✓ |
| 6 | `branch_loop_sum.ll` | sum(0..9)=45; 45>40→r=45 | **45** | 45 | ✓ |
| 7 | `branch_eq_ne.ll` | 7==7→1; 3!=9→1+10=11; 11+5 | **16** | 16 | ✓ |
| 8 | `branch_ptr.ll` | checks(p,p)=6; checks(p,null)=10; checks(null,p)=9; 6+10+9 | **25** | 25 | ✓ |
| 9 | `call_direct_ret.ll` | add3(2,3,4)=9 | **9** | 9 | ✓ |
| 10 | `call_multiarg_stack.ll` | 18 args: base=1, x_i=1+i; sum=18×1+(0+…+17)=18+153 | **171** | 171 | ✓ |
| 11 | `call_narrow_args.ll` | zext(i8 -56)=200, zext(i16 300)=300, zext(i32 400)=400, w=5; 905&0xFF | **137** | 137 | ✓ |
| 12 | `call_ptr_bank.ll` | buf[3]=42; advance(buf,3); deref(q)=42 | **42** | 42 | ✓ |
| 13 | `ptr_add_offset.ll` | off=20; p=buf+20; store -85; zext(load)=0xAB | **171** | 171 | ✓ |
| 14 | `ptr_diff_pos.ll` | ptrtoint(&buf[10])-ptrtoint(&buf[3])=10-3 | **7** | 7 | ✓ |
| 15 | `ptr_diff_neg.ll` | ptrtoint(&buf[3])-ptrtoint(&buf[10])=3-10=-7; -7&0xFF=0xF9 | **249** | 249 | ✓ |

**size/sign 敏感项**：#1（64 位补码 xor）、#4（`sext` i8→i64 后右移 8 取符号位）、#5（`sext` i16/i32→i64 后右移 16/32 取符号位）、#11（窄类型 `zext` 后截断 8 位）、#15（负指针差 64 位补码 & 0xFF）——全部手工验证通过。

**结论**：15/15 全部匹配，无差异。

---

### 4. 独立注入反例

**注入点**：与 engineer 不同（engineer 注入 `246→247`，reviewer 注入 `9→10` 改 `call_direct_ret.ll` 期望值）。

| 步骤 | 命令 | 真实输出 | 退出码 |
|------|------|---------|--------|
| 备份 | `cp expected.yaml /tmp/…/expected.yaml.bak` | — | 0 |
| sha256 before | `sha256sum expected.yaml` | `e5d2494188eb…b2a6b96` | 0 |
| 注入 | `sed 's/expected_exit_code: 9$/expected_exit_code: 10/'` | file changed ✓ | 0 |
| 验证 FAIL | `python3 validate_codegen_vectors.py` | `[FAIL] expected-vs-oracle[call_direct_ret.ll] expected=10 oracle=9` / `FAIL (1 failed, 57 passed)` | **EXIT=1** |
| 还原 | `cp /tmp/…/expected.yaml.bak expected.yaml` | sha256 matches ✓ | 0 |
| 验证回绿 | `python3 validate_codegen_vectors.py` | `PASS (58 checks)` | **EXIT=0** |

**结论**：注入→FAIL→还原→回绿，全链路验证通过。

---

### 5. 覆盖矩阵独立复核

| 要求 | 状态 | 证据 |
|------|------|------|
| 四类齐全（算术/访存/分支/调用）≥1 each | ✓ | 算术: arith_add_sub_neg, arith_const_hi_wyde, ptr_diff_pos, ptr_diff_neg; 访存: mem_store_load_offset, mem_narrow_be_bytes, mem_narrow_be_wide, ptr_add_offset; 分支: branch_loop_sum, branch_eq_ne, branch_ptr; 调用: call_direct_ret, call_multiarg_stack, call_narrow_args, call_ptr_bank |
| 指针参数/返回 bank (C1/C5) ≥1 | ✓ | C1: branch_ptr (ptr_checks 指针形参), call_ptr_bank (advance 的 i8* %p); C5: call_ptr_bank (advance 返回 i8*) |
| 指针算术 `add.o` (C14) | ✓ | ptr_add_offset.ll（意图覆盖，后端走 rb2rd/rd2rb 路径） |
| `cmp.uo` (dbb) 指针比较 | ✓ | branch_ptr.ll 中 p==q → `cmp.uo` + `br` |
| `ptr−ptr` 正差 ≥1 | ✓ | ptr_diff_pos.ll: 10-3=7 |
| `ptr−ptr` 负差 ≥1 | ✓ | ptr_diff_neg.ll: 3-10=-7, &0xFF=249 |
| 大端窄访存字节偏移/扩展 | ✓ | mem_narrow_be_bytes (ld.ub@0/7 + ld.sb@3); mem_narrow_be_wide (ld.uw@0/6 + ld.ut@4 + ld.sw@2 + ld.st@0) |
| C4 栈参数 | ✓ | call_multiarg_stack: 18 参数，rd16..rd31 取前 16，x16/x17 栈溢出 |
| C12 常量材料化 | ✓ | arith_add_sub_neg (负常数 -5); arith_const_hi_wyde (全 4 wyde 0xFEDC…3210) |
| C17 分支 | ✓ | branch_loop_sum (有符号谓词循环); branch_eq_ne (==/!=); branch_ptr (p==NULL/p==q) |

README「程序 ↔ 覆盖点」表与实际 `.ll` 文件内容/expected.yaml 覆盖点**名实相符**。

---

### 6. 四条发现判定

**(1) 后端缺口 `sext` 形参 → `sign_extend_inreg` 无 ISel（abort 134）**

reviewer 独立复现确认：`sext i8 %x to i64` 作用于形参时，llc 确实产生 `sign_extend_inreg` 并 abort 134。`call_narrow_args.ll` 改用 `zext`（无符号窄参数）是**合理的设计回避**。此为后端能力缺口，**非阻塞本任务**（向量仍覆盖 C4 无符号窄参数扩展）。**建议另立 LLVM 任务补 `sign_extend_inreg` ISel 支持**（或在前端 fixed 属性后免重扩展）。

**(2) C14 `add.o` 未选出**

确认：`ptr_add_offset.ll` 走 `rb2rd`→`add.uo`→`rd2rb` 路径，非单条 `add.o`。这是已知的 `ISS-137`/`LLVM-036t` 遗留。向量**仍覆盖 C14 语义意图**（指针 base+offset 运算的 E2E 正确性）。`INTEG-012t` 的「覆盖 `add.o`」门槛在该能力落地前**无法字面满足**，建议 `INTEG-012t` 任务书中注明此为「意图覆盖」而非「指令级覆盖」。

**(3) `sext` 被 `& 255` 优化掉 → 改用右移取符号位**

reviewer 验证：`mem_narrow_be_bytes.ll` 中 `s3s = sext i8 %s3 to i64` → `shi = lshr s3s, 8` → `shi8 = and shi, 255`。对于 s3=-2 (0xFE), sext→0xFFFFFFFFFFFFFFFE, >>8→0xFFFFFFFFFFFFFF, &0xFF→0xFF=255。**正确**，符号扩展在高位可观测。`mem_narrow_be_wide.ll` 中 ld.sw/ld.st 同理（-300>>16=-1→0xFF; -70000>>32=-1→0xFF）。设计正确。

**(4) IR 十六进制须 `u0x…`**

reviewer 验证：grep `u0x` 在实际 IR 代码中命中 3 处（`arith_const_hi_wyde.ll`、`mem_narrow_be_bytes.ll`、`mem_narrow_be_wide.ll`），均为 `store volatile i64 u0x…` 形式。所有 `0x…`（无 `u` 前缀）仅出现在注释中。**确认真实**：LLVM IR 的 `0x…` 整数字面量确实被解析为浮点常量（这是 LLVM 的已知行为），整数须用 `u0x…` 前缀。

---

### 7. `derive.py` 落点判定

**事实**：
- `expected.yaml`（产物）已入 git（`tests/codegen/expected.yaml`）。
- `derive.py`（生成器/独立验证脚本）在 `.work/evidence/TESTCASES-026t/derive.py`（gitignored）。

**规则**：AGENTS.md「生成器/脚本随产物保留」——"凡产物被提交（入 git）的生成器或脚本，必须随产物保留在非易失位置——优先 `tools/<module>/`"。

**判定**：`.work/` 目录是仓库内非易失位置（非 `/tmp`），且 `derive.py` 的定位是**第二独立验证实现**（与 validator 内嵌 oracle 并列），而非 `expected.yaml` 的生成器（`expected.yaml` 是手写+手算推导的）。其存在价值是作为 validator 的交叉验证，不必随 `expected.yaml` 入库。**当前落点 `.work/evidence/TESTCASES-026t/` 可接受**，但若后续需复用（如 CI 中跑交叉验证），建议移入 `tools/testcases/`。

**结论**：当前落点**可接受**，非阻塞。

---

### 8. 退出通道核验

所有 15 个程序的 `expected_exit_code` 均在 **0..255** 范围内（validator 的 `exit-code-range` 检查确认）。程序返回值经 `& 255` 掩码截断后返回 `i64`，由 crt0 写入退出端口。跨用例无歧义，符合 `INTEG-012t` 接口。

---

### 9. 门控核验

| 门控 | 退出码 | 结果 |
|------|--------|------|
| `make check-dirs` | EXIT=0 | PASS |
| `make check-no-residue` | EXIT=0 | PASS |
| `make check` | EXIT=0 | lit 33/33 PASS |

未改 `contracts/**`、未改既有 `tests/vectors/**`、未改 `components/**`。`git status` 仅列本任务新建文件。

---

### 判决

**Accepted**

验收命令块在 reviewer 独立重跑下全部通过（EXIT=0）；15 条期望值全量独立重算匹配（JS 计算，未复用 derive.py/validator oracle）；独立注入反例（`call_direct_ret.ll` 期望值 9→10）→FAIL→还原→回绿全链路验证通过；覆盖矩阵四类齐全且各项覆盖点名实相符；4 条发现均已独立复现并给出明确判定；退出通道 0..255 无歧义；门控全绿。任务状态置 **已验证**。
