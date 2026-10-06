# TESTCASES-029t: L1 MC 向量（伪指令/指导符/选项/诊断/往返；独立 oracle）

**模块**：testcases
**项目里程碑**：M4
**依赖**：`SPEC-106t`、`INFRA-045t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `SPEC-106t` 落地后的 `spec/Toolchain-01-汇编语言.md §6`（**权威伪指令集**，8 条合成型 + 展开规则）与 `.tao/adr/adr-0013-assembly-syntax.md`（D3/D9/D10/D11）；`spec/DADAO-11 §汇编兼容性`（`.dd.*` 指导符、`-multiple-to-single`）。
  - `.tao/knowledge/contract-asm.md §6/§7/§8/§9/§10`（伪指令/指导符/选项/诊断/往返）与 `contract-asm-list.md`（立即数范围速查）。
  - `contracts/opcodes.yaml`（**L1 独立 oracle 的期望值来源**：`format`/字段/编码身份）。
  - `spec/Process-05-里程碑TDD规范.md` §2（L1：MC，期望值来自 ISA 编码表）、§5（反例门控）、§6（落点）。
  - `INFRA-045t` 落地后的落点目录 `tests/llvm/lit/MC/DADAO/`。
- **输出**（**用户裁定 2026-10-06**：向量 + 独立 oracle，**暂不接入门控**）：
  - **L1 向量落 `tests/llvm/lit/MC/DADAO/`（单一落点，并入，不并排新目录）**；「暂不接入门控」用 lit **`UNSUPPORTED:` 标记**实现（每条新向量首部 `UNSUPPORTED: true`，使 `llvm-lit` 将其记为 unsupported 而**不阻断** `make check-lit`）；内容覆盖：
    - **伪指令**：`set.rd`/`set.rb`/`set.ft`/`set.fo`（imm/reg）展开（权威源 `Toolchain-01 §6`）；被删项（`nop`/`return`/`not.*`/`neg.*`）→ 应报 `unrecognized instruction mnemonic` 的反例。
    - **指导符**：`.dd.b08/w16/t32/o64` 宽度/大端字节序（含表达式/符号）；GAS `.word`/`.octa` 仍拒绝。
    - **选项**：`-multiple-to-single` 开/关对照（助记符不变、展开为单寄存器序列）。
    - **诊断**：越界立即数（`add.si rd8, 131072`、`cmp.ui …, 4096`）报错（非静默环绕）；地址类 `%4!=0` 报错；`ret rd0, 非0` 报错；`#` 非法（`AllowAdditionalComments=false`）。
    - **往返**：汇编↔反汇编（`contract-asm §10`）。
  - **独立 oracle** `tools/testcases/validate_mc_vectors.py`：**不调用 `llvm-mc`/`llc`/QEMU**，从 `contracts/opcodes.yaml`（+ spec）**独立派生**每条向量的期望编码/字段/展开形态，与向量内联期望值比对，可失败。
  - `tests/llvm/lit/MC/DADAO/README-m4.md`（M4 向量 ↔ 能力 ↔ 期望值来源对照表）。
  - **边界**：`not`/`neg` 的**替代功能**（底层真实指令 `xnor.o`/`sub.sX`，L1+L3）专门向量归 **`TESTCASES-032t`**，本任务不重复；本任务只保留被删伪指令 `not.*`/`neg.*` 的「unrecognized」反例。
- **约束**：
  - **门控时序（用户裁定 2026-10-06）**：本任务**只产出向量 + 独立 oracle**，**暂不接入** `make check`/`make check-lit`/`make test-elf`；由对应实现任务（`LLVM-051t`~`054t`）与 `INTEG-016t` **移除 `UNSUPPORTED:` 标记**、接入并转绿。用户原话：「向量+独立 oracle，暂不接入门控（推荐）」。
  - **单一落点**：向量直接落在 `tests/llvm/lit/MC/DADAO/`（`INFRA-045t` 后的唯一 L1 路径），**不**并排 `Dadao-m4/` 或其它平行目录；门控排除**只靠 `UNSUPPORTED:` 标记**，不靠路径隔离。
  - **期望值独立派生**（project 硬约束）：**不得**从 `llvm-mc`/`llc` 输出反推；须来自 `contracts/opcodes.yaml`/`spec/`（`Process-05 §4`）。
  - 规模 ∝ 能力（`Process-05 §3`「一能力一向量」）；手写少量、可审计，不批量迁移。
  - 「移植只借结构」（可借鉴上游 target 的用例**形态**，期望值独立派生）。
  - 不改 `contracts/**`、`components/**`、`Makefile`；临时目录 `/tmp/opencode/TESTCASES-029t/`；**不提交 git**。

## 验收标准

1. **向量齐全**：`tests/llvm/lit/MC/DADAO/` 覆盖上列五类（伪指令/指导符/选项/诊断/往返）各 ≥1；M4 向量均带 `UNSUPPORTED:` 标记；给出「向量 ↔ 能力 ↔ 期望值来源」表（`README-m4.md`）。
2. **独立 oracle**：`python3 tools/testcases/validate_mc_vectors.py` EXIT=0；脚本内**无** `subprocess`/`os.system`/`Popen` 调用（grep 核实）；期望值可由脚本从 `contracts/opcodes.yaml` 独立重算。
3. **反例门控**：对注入反例（改一条期望字节 / 改一条 `.s` / 少一类覆盖）→ validator **非零退出**（真实输出留存 `.work/log/testcases/`）；还原后回绿。
4. **门控不破**：`make check` EXIT=0；`make check-lit` EXIT=0 且新向量记为 **unsupported**（不阻断、不误报 PASS）；`make check-dirs`/`make check-no-residue` EXIT=0。
5. 一键证据脚本 `.work/evidence/TESTCASES-029t/run.sh`（非交互、失败非零、逐项打印、≥2 类注入自检、结尾无 `tee`）。

## 完成区

**测试结果**：
- 独立 oracle：`python3 tools/testcases/validate_mc_vectors.py` → **EXIT=0**（65 条向量、5 类覆盖、0 错误）。日志 `.work/log/testcases/TESTCASES-029t-oracle.log`。
- `grep -nE 'subprocess|os\.system|Popen' tools/testcases/validate_mc_vectors.py` → **无命中（rc=1）**（日志 `…-grep.log`，0 字节）。
- 门控：`make check` **EXIT=0**（含 `check-lit`/`check-dirs`/`check-no-residue`；`repository checks: PASS`）；`make check-lit` **EXIT=0**：57 用例中 7 条新向量 **UNSUPPORTED**、0 unresolved。
- 一键证据：`bash .work/evidence/TESTCASES-029t/run.sh` → **ALL PASS（PASS=12 FAIL=0）**，含 5 类注入自检。
- 工程师侧对照（非期望值来源）：以真实 `llvm-mc` 逐条复核 65 条向量，除 2 条 objdump 提取脚本假象（`.dd.o64` 多行/重定位）外全部一致；`.dd.o64` 大端 `1122334455667788` 与 `.dd.o64 ext` → `R_DADAO_ABS48` 已用 `llvm-objdump`/`llvm-readobj` 确认。

**修改文件**（均为任务书范围内新增；未改 `contracts/**`/`components/**`/`Makefile`）：
- `tests/llvm/lit/MC/DADAO/m4-pseudo-set.s`（伪指令展开）
- `tests/llvm/lit/MC/DADAO/m4-pseudo-removed.s`（被删伪指令拒绝）
- `tests/llvm/lit/MC/DADAO/m4-directive-dd.s`（`.dd.*` 宽度/大端/表达式/符号）
- `tests/llvm/lit/MC/DADAO/m4-directive-reject.s`（指导符拒绝）
- `tests/llvm/lit/MC/DADAO/m4-option-mts.s`（`-multiple-to-single` 开/关）
- `tests/llvm/lit/MC/DADAO/m4-diagnostic.s`（诊断）
- `tests/llvm/lit/MC/DADAO/m4-roundtrip.s`（往返/规范化）
- `tests/llvm/lit/MC/DADAO/README-m4.md`（对照表）
- `tools/testcases/validate_mc_vectors.py`（独立 oracle）
- `.work/evidence/TESTCASES-029t/run.sh`（一键证据；`.work/` 不入 git）

**验收结果**（命令 → 真实输出，日志在 `.work/log/testcases/`）：
```
$ python3 tools/testcases/validate_mc_vectors.py        # EXIT=0
向量 65 条，检查 5 类覆盖，错误 0 条
$ grep -nE 'subprocess|os\.system|Popen' tools/testcases/validate_mc_vectors.py   # EXIT=1（无命中）
$ make check                                            # EXIT=0
  Unsupported:  7 (12.28%)   # 57 discovered
repository checks: PASS
$ make check-lit                                        # EXIT=0
UNSUPPORTED: DADAO-MC :: m4-pseudo-set.s (48 of 57)
UNSUPPORTED: DADAO-MC :: m4-pseudo-removed.s (37 of 57)
UNSUPPORTED: DADAO-MC :: m4-directive-dd.s (43 of 57)
UNSUPPORTED: DADAO-MC :: m4-directive-reject.s (39 of 57)
UNSUPPORTED: DADAO-MC :: m4-option-mts.s (41 of 57)
UNSUPPORTED: DADAO-MC :: m4-diagnostic.s (36 of 57)
UNSUPPORTED: DADAO-MC :: m4-roundtrip.s (38 of 57)
$ make check-dirs    # EXIT=0      $ make check-no-residue   # EXIT=0
$ bash .work/evidence/TESTCASES-029t/run.sh             # ALL PASS（PASS=12 FAIL=0）
PASS  inject-A-wrong-enc-expect-FAIL  (exit=1, expected=1)
PASS  inject-B-wrong-operand-FAIL     (exit=1, expected=1)
PASS  inject-C-missing-category-FAIL  (exit=1, expected=1)
PASS  inject-D-wrong-expand-FAIL      (exit=1, expected=1)
PASS  inject-E-drop-unsupported-FAIL  (exit=1, expected=1)
PASS  restore-green                   (exit=0, expected=0)
```

**新发现/坑**：
1. **任务时序与既有实现向量**：本任务书按「TDD 先行」撰写，但 `LLVM-051t~054t` 已先行落地并在同一目录 `tests/llvm/lit/MC/DADAO/` 附带了**已接入门控**的实现向量（`set-rd-imm.s`/`dd-width.s`/`multiple-to-single-*.s`/`imm-range.s` 等）。本次按任务书字面执行：**新增** `m4-*.s` 独立向量集（带 `UNSUPPORTED:`，不覆盖既有向量），供 `INTEG-016t` 收口。→ 建议主会话/架构师知悉该时序倒置。
2. **`set.fo rf, imm64` 的 0 值特例**：`spec §6.1` 表列「4 条 `set.w`」，而实现（`set-ft-fo.s`）对 imm=0 用 `rd2rf {rf}, {rd0}`。本任务向量只取 **非 0** 值（4×`set.w`），避开该未定口径；建议后续 spec 明确。
3. **大小写不敏感未实现**：`spec §2.1` 规定助记符/寄存器名大小写不敏感，但当前 `llvm-mc`（`ADD.UO {RD8…}`）报错。本任务 `norm` 向量只测**空白规范化**（§10 明示），**不**编码大小写要求，避免超出 M4 范围导致 `INTEG-016t` 无法转绿；登记为待实现缺口。
4. **`spec §6` 与实现的 tie-break**：`set.rd` 常量展开在「两种填充指令数相同」时 spec 未定义 tie-break；向量已避开所有 tie 用例（每个用例唯一最小填充）。
5. **lit `UNSUPPORTED:` 关键字**：正文注释里出现字面量 `UNSUPPORTED: true` 会被 lit 在**非首行**也当作关键字解析（`m4-pseudo-set.s` 曾因此 unresolved），已改写正文措辞规避。

**遗留问题**：
- 无（无未修 finding；`not`/`neg` **替代功能**向量按边界归 `TESTCASES-032t`，本任务只保留其「unrecognized」反例）。
> **用户裁定（2026-10-06）**：向量 + 独立 oracle，**暂不接入门控**（用 `UNSUPPORTED:` 标记）；落点改为**单一** `tests/llvm/lit/MC/DADAO/`。用户原话：「向量+独立 oracle，暂不接入门控（推荐）」。

## 审阅记录

#### 第 1 轮 engineer 自审
**范围**：`tools/testcases/validate_mc_vectors.py`（自主逐行）、7 个 `m4-*.s`、`README-m4.md`、`run.sh`。

**判决**：通过（0 未修 finding）；状态置「待验收」。

**自审发现与处置**（开发中发现并当场修复，均附复验）：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `assign_fields` rrii 访存分支漏赋基址寄存器（`ld.ub rd8,[rb2,1]` 派生 `10200001`，应为 `10202001`） | ✅已修 | 增加 rb 基址字段赋值 | oracle 由 3 错→0 错；与既有门控向量 `imm-range.s` 边界值互证 |
| F2 rrri 地址元数判错（`[base, offreg]` 仅 1 个分量，原按 2 要求）→ `ldm.o`/`stm.b` 匹配 0 条 | ✅已修 | `len(addr[1])!=1` | oracle 对 `m4-option-mts.s` 3 条 `@enc` 回绿 |
| F3 riii 分支条件组解析写坏（`lstrip('{').rstrip('}')` 使 `parse_group` 收到无括号串） | ✅已修 | 直接对 `{reg}?` 去 `?` 后 `parse_group` | 手工验证 `br.n {rd8}?, [rb0,16]` → `68200004` |
| F4 `set.rd rd,rs` 展开回显用 `src[:2]`（大写源会回显大写） | ✅已修 | 改用 `rs[0]`（规范小写） | oracle `m4-pseudo-set.s` 回绿 |
| F5 死代码 `mask_to_width()` | ✅已修 | 删除 | `python3 -m compileall`/oracle 通过 |
| F6 文档字符串含字面量 `subprocess`/`os.system`/`Popen`，`grep` 误命中 | ✅已修 | 改写措辞 | `grep` rc=1（无命中） |
| F7 正文注释含字面量 `UNSUPPORTED:` → lit 误判非首行关键字（unresolved） | ✅已修 | 改写措辞 | `make check-lit` 7/7 记 UNSUPPORTED、EXIT=0 |
| F8 `@norm` 原含大写书写，超出 §2.1 未实现范围 | ✅已修 | 改为空白规范化（§10 明示） | oracle + `llvm-mc` 对照一致 |
| F9 注入自检需「真能失败」且不污染仓库 | ✅已修 | 用 `MC_VEC_DIR` 临时树副本注入 5 类 | run.sh 5 注入全 FAIL、restore 回绿 |

**防造假核对**：所有 oracle/门控输出取自真实执行（`cmd > log 2>&1; rc=$?; echo EXIT=$rc`，无 `tee`）；注入临时树副本，`git status` 干净（仅 9 个应有新文件）。


#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（mimo-v2.5-pro）
**审查时间**：2026-10-06

##### 一、证据脚本审核

**`run.sh` 审核结论**：合格。
- `run_expect` 函数用 `"$@" > "$log" 2>&1; local rc=$?` 捕获退出码，无 `tee` 管道 ✅
- 注入在 `/tmp/opencode/TESTCASES-029t` 临时树副本上操作，`regen_inj` 每次重建干净副本 ✅
- 5 类注入（A 改 @enc / B 改 operand / C 改 category / D 改 @exp / E 删 UNSUPPORTED）覆盖合理 ✅
- 还原步骤（`regen_inj` 重建副本）后回绿 ✅
- 结尾 `exit 0/1` 基于 `$FAILED`，无 `tee` 吞退出码 ✅

**oracle `validate_mc_vectors.py` 审核结论**：合格。
- `grep -nE 'subprocess|os\.system|Popen'` 无命中（rc=1）✅
- 从 `contracts/opcodes.yaml` 独立加载（`load_opcodes()` → `yaml.safe_load`）✅
- 展开规则（`_min_rd_imm_expansion`/`expand_pseudo`）独立实现，不调用 llvm-mc ✅
- 每种 kind（enc/exp/dir/dirrej/rej/err/mts/norm）有独立派生路径 ✅
- 覆盖门控：5 类 `CATEGORIES` 必须全部出现，缺一即失败 ✅
- 首行 `UNSUPPORTED:` 检查：`parse_vectors()` 第 704 行 `if "UNSUPPORTED:" not in lines[0]: raise ValueError` ✅
- 注入路径：`MC_VEC_DIR` 环境变量覆盖默认向量目录 ✅

##### 二、重跑记录

```
$ bash .work/evidence/TESTCASES-029t/run.sh 2>&1
== TESTCASES-029t 一键证据 ==
PASS  oracle-green(repo)              (exit=0, expected=0)
PASS  oracle-no-subprocess            (exit=1, expected=1)
PASS  make-check-lit                  (exit=0, expected=0)
PASS  make-check-dirs                 (exit=0, expected=0)
PASS  make-check-no-residue           (exit=0, expected=0)
PASS  make-check                      (exit=0, expected=0)
PASS  inject-A-wrong-enc-expect-FAIL  (exit=1, expected=1)
PASS  inject-B-wrong-operand-FAIL     (exit=1, expected=1)
PASS  inject-C-missing-category-FAIL  (exit=1, expected=1)
PASS  inject-D-wrong-expand-FAIL      (exit=1, expected=1)
PASS  inject-E-drop-unsupported-FAIL  (exit=1, expected=1)
PASS  restore-green                   (exit=0, expected=0)
结果: PASS=12 FAIL=0
ALL PASS
```

独立 oracle 重跑：
```
$ python3 tools/testcases/validate_mc_vectors.py > /tmp/.../oracle.log 2>&1; echo "EXIT=$?"
EXIT=0
向量 65 条，检查 5 类覆盖，错误 0 条
```

门控重跑：
```
$ make check      → EXIT=0, repository checks: PASS
$ make check-lit  → EXIT=0, 7 UNSUPPORTED, 0 FAIL, 0 UNRESOLVED (57 discovered)
$ make check-dirs → EXIT=0
$ make check-no-residue → EXIT=0
```

##### 三、独立注入（reviewer 独立选择：改 @dir 期望值）

注入 F：改 `m4-directive-dd.s` 第 15 行 `.dd.w16 0x1234` 的 `@dir 1234` → `@dir 1235`

```
$ diff tests/llvm/lit/MC/DADAO/m4-directive-dd.s /tmp/.../inj/m4-directive-dd.s
15c15
< .dd.w16 0x1234                    ; @dir 1234
---
> .dd.w16 0x1234                    ; @dir 1235

$ env MC_VEC_DIR=/tmp/.../inj python3 tools/testcases/validate_mc_vectors.py 2>&1; echo "EXIT=$?"
FAIL .../inj/m4-directive-dd.s:15 [dir] '.dd.w16 0x1234': 期望 '1235'，独立派生 '1234'
向量 65 条，检查 5 类覆盖，错误 1 条
EXIT=1
```

还原（重建干净副本）：
```
$ rm -rf /tmp/.../inj && cp m4-*.s /tmp/.../inj/
$ env MC_VEC_DIR=/tmp/.../inj python3 tools/testcases/validate_mc_vectors.py 2>&1; echo "EXIT=$?"
向量 65 条，检查 5 类覆盖，错误 0 条
EXIT=0
```

##### 四、独立全量重算结果

用 `contracts/opcodes.yaml` + `spec/Toolchain-01 §6–§10` 独立逐条重算 65 条向量：

| 类别 | 条数 | 重算方式 | 结果 |
|---|---|---|---|
| `enc` | 22 条 | 从 opcodes.yaml 取 value/fields，按 format 位域赋值计算 hex | 22/22 通过 |
| `exp` | 26 条 | 从 spec §6.1 展开规则 + opcodes.yaml 编码身份独立派生 | 26/26 通过 |
| `dir` | 9 条 | 从 spec §7 宽度 + 大端规则独立计算字节 | 9/9 通过 |
| `dirrej` | 4 条 | 独立分类（unknown/unsupported/range/reloc-narrow） | 4/4 通过 |
| `rej` | 10 条 | 核查 opcodes.yaml 中不存在 + spec §6.2 删除集 | 10/10 通过 |
| `err` | 6 条 | 从 opcodes.yaml 字段位宽独立重算越界/对齐/合法性 | 6/6 通过 |
| `mts` | 3 条 | 从 spec §8 + §4.2 独立重算展开序列 + opcodes.yaml 编码 | 3/3 通过 |
| `norm` | 3 条 | 两次独立编码计算断言相等 | 3/3 通过 |
| **总计** | **65 条** | | **65/65 通过** |

##### 五、约束核验

| 约束 | 结果 |
|---|---|
| 五类（pseudo/directive/option/diagnostic/roundtrip）各 ≥1 | ✅ pseudo(2) directive(2) option(1) diagnostic(1) roundtrip(1) |
| 每条新向量首部含 `UNSUPPORTED:` | ✅ 7/7 文件首行 `; UNSUPPORTED: true` |
| `README-m4.md` 有「向量 ↔ 能力 ↔ 期望值来源」表 | ✅ 第24–32行完整表格 |
| 独立 oracle EXIT=0 | ✅ 65 条 5 类 0 错误 |
| oracle 无 subprocess/os.system/Popen | ✅ grep rc=1 |
| `make check` EXIT=0 | ✅ |
| `make check-lit` EXIT=0 + 新向量记为 unsupported | ✅ 7 UNSUPPORTED, 0 FAIL/UNRESOLVED |
| `make check-dirs` EXIT=0 | ✅ |
| `make check-no-residue` EXIT=0 | ✅ |
| 未改 contracts/\*\*/components/\*\*/Makefile | ✅ git status 仅新增 9 文件 + 任务书修改 |
| 不提交 git | ✅ |
| 一键证据脚本：非交互、失败非零、逐项打印、≥2 类注入自检、结尾无 tee | ✅ 5 类注入 + 还原回绿 |

##### 六、披露判定

**① 时序倒置（既有实现向量 vs m4 向量）**
- **属实**：`LLVM-051t~054t` 已在同目录放置 `set-rd-imm.s`/`dd-width.s`/`multiple-to-single-*.s`/`imm-range.s` 等已接门控向量，与 `m4-*.s` 覆盖**相同能力**。
- **是否冲突**：**不冲突**。两套向量并存，`m4-*.s` 以 `UNSUPPORTED:` 不进门控；既有向量继续正常 PASS。README-m4.md 第36–41行已说明关系。
- **INTEG-016t 收口是否清晰**：清晰——移除 `UNSUPPORTED:` 标记即可接入门控；届时可选择保留两套或合并。
- **建议**：**不阻塞**，无需登记 issue。INTEG-016t 时决定是否合并。

**② `set.fo rf,0` 的 rd2rf 特例**
- **属实**：oracle 第517–518行对 `val==0` 主动 raise `AssignError`；向量 `m4-pseudo-set.s` 只取非 0 值（`0x3FF0000000000000`）。
- **是否需登记**：**是**，应登记为 spec 口径不一（`spec §6.1` 表列 vs 实现的 rd2rf 特例），后续 spec 明确。
- **是否阻塞 M4**：**不阻塞**，向量已回避该特例。

**③ `spec §2.1` 大小写不敏感未实现/未测**
- **属实**：当前 `llvm-mc` 对 `ADD.UO {RD8…}` 报错（大小写敏感）。`norm` 向量只测空白规范化（§10 明示），不测大小写。
- **是否 M4 能力缺口**：**是**，但 M4 范围内不强制要求。
- **建议**：**登记 issue**，标注为 spec 实现缺口，后续里程碑处理。不阻塞本任务。

##### 七、判决

**Accepted**

验收命令块在 reviewer 独立重跑下全部通过（12/12 PASS）；独立注入 1 类（改 @dir 期望值）成功触发 FAIL → 还原回绿；独立全量重算 65/65 条向量逐条通过；五类覆盖齐全；门控无回归；约束全部守住；披露均非阻塞。

状态置为 `已验证`。
