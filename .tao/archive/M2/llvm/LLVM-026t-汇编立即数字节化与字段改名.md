# LLVM-026t: 汇编立即数字节化与字段改名

**模块**：llvm
**项目里程碑**：M2
**依赖**：无
**状态**：已验证

## 目标

落地 ADR-0013 D3（汇编地址立即数单位=字节、取消 `i` 后缀）与 D10（汇编层字段改名 `imms14/imms20/imms26`）的 LLVM 侧全部改动：修改 AsmParser 补丁（去 `i`、按字节解析、`%4` 校验、范围校验、编码 `>>2`）、MCInstPrinter 补丁（反汇编 `<<2`）、`gen_asm_list.py`（去 `i` 后缀、字段改名）；应用补丁 → 增量重建 llvm-mc → 烟探验证。

## 执行环境

**执行环境**：本地

## 范围

### 文件清单

| 文件 | 改动方式 | 说明 |
|---|---|---|
| `components/llvm-project/patches/…/DADAOAsmParser.cpp.patch` | **工作树改 → 导出** | 去 `i` 后缀解析；按字节解析地址立即数；`%4==0` 校验 + 范围校验；编码 `field = bytes >> 2` |
| `components/llvm-project/patches/…/DADAOMCInstPrinter.cpp.patch` | **工作树改 → 导出** | 反汇编 `bytes = field << 2`；不打印 `i` 后缀 |
| `tools/llvm/gen_asm_list.py` | 直接编辑 | 去 `i` 后缀渲染；地址字段改名；更新 `IMM_EXAMPLE`；更新范围表；escape 模板改名 |
| `docs/assembly-list.md` | 自动生成 | 由 gen_asm_list.py 重生成（15 处 `i` 后缀自动消除） |

### 补丁工作流（不得直接编辑 patch 文件）

1. `make prepare`（应用现有补丁到 `.work/source/llvm-project`）
2. 在 `.work/source/llvm-project/llvm/lib/Target/DADAO/` 中编辑 AsmParser.cpp 与 DADAOMCInstPrinter.cpp
3. 增量重建验证（见验收）
4. **导出（防呆）**：`git -C .work/source/llvm-project diff <base_commit> -- <单个源文件> > /tmp/opencode/LLVM-026t/<name>.patch`
   - ⚠️ **输出必须写到临时文件**；**严禁**把 `>` 指向 `.work/source` 下**任何**路径（2026-10-02 事故根因即此）
   - 一次只 diff **一个**文件，避免混淆
5. **替换前校验（全部满足才替换）**：`wc -l` 行数 **≥ 300**（原 `1090`/`397`）；`git apply --check` 通过；与 `.work/source` 实际内容一致（`check-patch-tree` 断言⑥）。**行数骤降/出现 `e69de29`（空 blob）立即停止报告**，不得替换。

### 约束

- ISA 编码语义不变（`Addr = rb0 + (imms << 2)`）；仅改汇编层换算
- **编码层名字保持 `imms12/18/24`**（`contracts/opcodes.yaml`、`contract-isa.md`、probes、vectors 不动）
- 重建 llvm-mc 预计 **5–15 分钟**（增量，`JOBS=8`）
- 串行说明：TESTCASES-021t 依赖本任务（需要新 llvm-mc）；SPEC-082t 依赖本任务（需要 gen_asm_list.py 更新后重生成嵌入表格）

### 详细改动

#### 1. DADAOAsmParser.cpp（工作树 `.work/source/llvm-project/`）

- **去掉 `i` 后缀解析**：删除 `AddrSuffix`/`hasSuffix` 等 `i` 后缀检测逻辑
- **按字节解析**：地址立即数直接以字节值解析（不再以指令字为单位）
- **`%4` 校验**：地址立即数（跳转/分支目标偏移、escape 偏移）必须 `%4==0`，否则报错
- **范围校验**：
  - `imms14`（原 `imms12` 的跳转/分支形式）：`[-8192, 8188]`，`%4==0`
  - `imms20`（原 `imms18` 的跳转/分支/escape 形式）：`[-524288, 524284]`，`%4==0`
  - `imms26`（原 `imms24` 的 iiii 跳转形式）：`[-33554432, 33554428]`，`%4==0`
- **编码换算**：装配时 `field = bytes >> 2` 写入 MCInst
- **（硬性）保留符号/重定位路径**：地址立即数若为**不可求值的符号表达式**（label/未定义符号），**必须**仍走 `createImmExpr`（`MCOperand::createExpr` + fixup），**严禁**被拍平成 `0`。本次改造**只改单位与校验**，**不得删除** `createImmExpr`/`evaluateAsAbsolute`/`isExpr` 机制（2026-10-02 首版即因此丢失符号支持）。
- **访存偏移不变**：`imms12`（`ld.*`/`st.*` 偏移）仍为字节，不 `%4`、不 `>>2`
- **`ret rd, imm` 不变**：`imms18`（返回值，非地址）不 `%4`、不 `>>2`

#### 2. DADAOMCInstPrinter.cpp（工作树）

- **反汇编换算**：`bytes = field << 2` 打印字节值
- **不打印 `i` 后缀**：删除所有 `<< "i"` 输出

#### 3. gen_asm_list.py（直接编辑）

- **`IM` lambda**（L272）：去掉 `f"{op['name']}i"` → `op['name']`
- **`IMM_EXAMPLE`**（L64）：地址立即数改为字节值 —— 新增 `"imms14": "8"`、`"imms20": "8"`、`"imms26": "8"`（或按各指令的实际示例值）；保留 `"imms12": "1"`（访存不变）、`"imms18": "1"`（ret 不变）
- **`new_form` 函数中的硬编码字段名**：
  - `escape` 行（L340）：`imms18i` → `imms20`
  - `br.*`/`jump`/`call` 行（L279–295）：模板中的跳转/分支字段名按上下文改名（`imms12→imms14`、`imms18→imms20`、`imms24→imms26`）
  - `ld.*`/`st.*` 行（L329）：`imms12` **保持不变**（访存）
- **立即数范围速查表**（L656–667）：新增 `imms14`/`imms20`/`imms26` 行（字节范围 + `%4==0` 说明）；保留 `imms12`/`imms18`（注明"仅访存 / ret"）
- **重新生成** `docs/assembly-list.md`（15 处 `i` 后缀自动消除）

#### 4. 增量重建与烟探验证

- `make build-mc`（增量，`JOBS=8`，预计 5–15 分钟）
- 烟探：`echo 'br.n {rd0}?, [rb0, 16]' | .work/build/llvm/bin/llvm-mc -triple=dadao -show-encoding 2>&1` 验证输出含 `encoding: [0x68,0x00,0x00,0x04]`（16>>2=4，与旧 `4i` 编码相同）

## 验收标准

1. **补丁完整性（防空补丁）**：`git apply --check` 两个补丁文件无错误，**且** 各自 `wc -l` **≥ 300**、内容**不含 `e69de29`（空 blob）**。⚠️ `git apply --check` **不能**兜住无效补丁（2026-10-02 事故；2026-10-03 经实测订正）：0 字节/仅头部（无 hunk）会被**拒绝**（rc≠0），但「**新建空文件**」补丁（`new file mode … index 0000000..e69de29`、无 hunk）会**静默通过**（rc=0）。故必须同时核对**行数下限**与**非空 blob**（并以 `check-patch-tree` 断言⑥兜底）。
2. **gen_asm_list.py 可运行并更新仓库产物**：`python3 tools/llvm/gen_asm_list.py --syntax new`（**默认写 `docs/assembly-list.md`**）无异常退出；随后 `grep -cE '[0-9]+i[][ ,;)]' docs/assembly-list.md` = **0**、`grep -cE 'imms14|imms20|imms26' docs/assembly-list.md` **> 0**（**必须落到仓库文件**，不得只写 `/tmp`）
3. **无 `i` 残留**：`grep -n 'imms12i\|imms18i\|imms24i\|[0-9]i\]' tools/llvm/gen_asm_list.py docs/assembly-list.md` 退出码 1
4. **字段改名**：`grep -c 'imms14\|imms20\|imms26' docs/assembly-list.md` 输出 > 0
5. **烟探验证**（重建后）：`echo 'br.n {rd0}?, [rb0, 16]' | .work/build/llvm/bin/llvm-mc -triple=dadao -show-encoding 2>&1` 输出含 `encoding: [0x68,0x00,0x00,0x04]`（反例：将 `16` 改为 `17`，应报错 `%4` 不对齐）
6. **反例门控**（重建后）：`echo 'br.n {rd0}?, [rb0, 17]' | .work/build/llvm/bin/llvm-mc -triple=dadao -show-encoding 2>&1` 退出码非 0（`17 % 4 != 0`，应报错）
7. **符号/重定位保留**（重建后，**关键回归门控**）：`echo 'jump [rb0, foo]' | .work/build/llvm/bin/llvm-mc -triple=dadao -show-encoding 2>&1` 输出须含 `fixup … value: foo, kind: DADAO_FK_PCRel_24`（**严禁**输出 `jump [rb0, 0]`）。另测 `br.n {rd0}?, [rb0, foo]` 与 `jump [rb3, rd0, foo]` 同样须保留 fixup。
8. **访存不回归**：`echo 'ld.ub rd8, [rb2, 3]' | … -show-encoding` 正常（不 `%4`、不 `>>2`）。

## 下发前预检

1. **任务书内部一致性**：✅ 目标/范围/约束/验收一致；D3（去 `i` + 字节）与 D10（字段改名）均覆盖；访存 `imms12` / `ret` `imms18` 明确排除；补丁工作流符合 `component-patching.md`
2. **依赖链实际可用性**：✅ 无前置任务依赖；`make prepare` + `make build-mc` 为仓库已有基础设施
3. **验收可执行性**：
   - 验收 1（`git apply --check`）：**现在可跑**
   - 验收 2–4（gen_asm_list.py）：**现在可跑**（Python + yaml，不需 LLVM 构建）
   - 验收 5–6（烟探 + 反例）：**BLOCKED**（需 `make build-mc` 完成，预计 5–15 分钟；替代证据：验收 2–4 的生成器输出已确认无 `i` 残留 + 字段改名正确）
4. **与 spec/vectors 一致**：✅ 不改 `contracts/opcodes.yaml`、不改 `tests/vectors/`；gen_asm_list.py 从 `opcodes.yaml` 读取，编码层不变

## 完成区

**测试结果**：MC lit 22/22 PASS；E2E 3/3 PASS（含 `smoke_jump.test`）；`check-lit` 25/25 PASS；`check-patch-tree` 67 patches OK

**修改文件**：
| 文件 | 改动 | 范围归属 |
|---|---|---|
| `components/llvm-project/patches/.../DADAOAsmParser.cpp.patch` | 1097 行：去 `i` 后缀；按字节解析；`%4` 校验 + 范围校验（字段域阈值）；编码 `>>2`；符号 fixup 保留（bypass matcher） | **本任务** |
| `components/llvm-project/patches/.../DADAOMCInstPrinter.cpp.patch` | 393 行：反汇编 `<<2`；去 `i` 后缀；`isImm()/isExpr()` 守卫 | **本任务** |
| `tools/llvm/gen_asm_list.py` | `_asm_imm_name` 字段改名；去 `i`；更新 `IMM_EXAMPLE`/范围表 | **本任务** |
| `docs/assembly-list.md` | 重生成（15 处 `i` 消除 + 字段改名） | **本任务** |
| `tests/e2e/smoke_jump.s` | `2i` → `8`（字节偏移） | **本任务**（E2E lit 必须绿） |
| `tests/lit/MC/Dadao/{e_flags,iiii_jump,riii_branch,rrii_branch}.s` | `Ni` → 字节偏移 | **TESTCASES-021t 范围重叠**（必要：否则 MC lit 4/22 FAIL） |
| `tools/llvm/test_encoding_oracle.py` | `1i→4`、`4i→16`、`2i→8`（汇编字符串同步） | **TESTCASES-021t 范围重叠**（必要：否则 10/61 FAIL） |
| `components/llvm-project/changelog.md` | 追加 LLVM-026t 条目 | **本任务** |

**范围重叠说明**：4 个 lit `.s` 文件与 `test_encoding_oracle.py` 属 TESTCASES-021t 预期范围，但 LLVM-026t 改变了汇编语法（去 `i` 后缀），不同步则 lit/oracle 立即 FAIL。改动仅替换汇编字符串，期望编码值不变。

**`test_encoding_oracle.py` 必要性说明**：该脚本是 lit 字节 CHECK 的独立端到端交叉验证（`check_lit_bytes.py` 只查 mask/value 结构；oracle 从汇编→编码全链路验证）。语法迁移后不同步则 10 条含地址立即数的用例因语法取消而 FAIL，丧失此验证能力。

**验收结果**：
| # | 验收项 | 真实输出 | RC |
|---|--------|----------|-----|
| 1 | 补丁完整性 | AsmParser 1097 行、Printer 393 行 ≥300 ✓；`check-patch-tree` 67 patches OK ✓ | 0 |
| 2 | gen_asm_list.py | 227 entries → `docs/assembly-list.md` | 0 |
| 3 | 无 i 残留 | `grep` 无匹配 | 1 |
| 4 | 字段改名 | `grep -c` = 18 > 0 | 0 |
| 5 | 烟探 | `br.n {rd0}?, [rb0, 16]` → `[0x68,0x00,0x00,0x04]` | 0 |
| 6 | 反例门控 | `br.n {rd0}?, [rb0, 17]` → `%4` error | 1 |
| 7a | 符号 fixup | `jump [rb0, foo]` → PCRel_24 | 0 |
| 7b | 符号 fixup | `br.n {rd0}?, [rb0, foo]` → PCRel_18 | 0 |
| 7c | 符号 fixup | `jump [rb3, rd0, foo]` → PCRel_12 | 0 |
| 8 | 访存不回归 | `ld.ub rd8, [rb2, 3]` → `[0x10,0x20,0x20,0x03]` | 0 |
| F2 | imms26 边界 | `33554432`✗ `33554428`✓ `-33554432`✓ `-33554436`✗ | 1/0/0/1 |
| — | check-lit | MC 22/22 + E2E 3/3 = **25/25** | 0 |
| — | check-patch-tree | 67 patches OK | 0 |

**新发现/坑**：
- Auto-generated matcher 的 `convertToMCInst` 会丢失 `DADAOOperand::ImmExpr` 指针（根因未完全确认，可能与 `MCParsedAsmOperand` 默认拷贝语义有关）。解决方案：对含 expr 的地址立即数 bypass `MatchInstructionImpl`，直接 `MCInst` + `MCOperand::createExpr` + `emitInstruction`。
- MCCodeEmitter 不应用 `>>2`，parser 必须做。
- `git diff --no-index /dev/null <file>` 导出补丁时，若之前已有同名补丁文件，shell 可能缓存旧输出。必须先 `rm` 再导出。

**遗留问题**：
- `escape` 指令汇编不可用（`excp_cause_ip` 基址当前 parser 不支持）——**既有缺口**，是否实现待用户裁定，本轮不实现。
- `isRegBankPrefix` 函数未使用（原有 warning）。
- `ImmExpr` 丢失根因未完全确认（bypass 方案有效但增加代码复杂度）。

## 审阅记录

#### 第 2 轮 engineer 自审（返工 F1-F4/F6 后）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1: Printer 补丁缺 isImm/isExpr 守卫 | ✅已修 | 重新导出补丁（先 `rm` 再 `git diff --no-index`） | `check-patch-tree` 67 OK ✓；注入验证 abort→fixup ✓ |
| F2: iiii 范围阈值差 4× | ✅已修 | `[-33554432,33554427]` → `[-8388608,8388607]` | `33554432`✗ `33554428`✓ `-33554432`✓ `-33554436`✗ |
| F3: lit E2E smoke_jump FAIL | ✅已修 | `smoke_jump.s` 中 `2i` → `8` | `check-lit` 25/25 ✓ |
| F4: escape 声明不实 | ✅已更正 | 完成区改为「既有缺口，本轮不实现」 | — |
| F6: 范围重叠未说明 | ✅已更正 | 完成区明示范围重叠 + 必要性说明 + changelog 条目 | `changelog.md` 已追加 |

**判决**：全部 findings 已修，可标「待验收」。

#### 第 1 轮 reviewer 验收（返工后）

**审查者**：reviewer 子代理｜**日期**：2026-10-02｜**判决**：**Needs Revision**
**审查方式**：独立重跑 8 项验收 + 2 次源码反例注入（含还原重建）+ 逐行审查补丁/源码 + 边界抽验。**未采信完成区任何结论**。

##### 一、验收标准逐条重跑（reviewer 本人命令/输出/退出码）

| # | 验收项 | reviewer 实际命令 | 真实输出 | RC | 结论 |
|---|---|---|---|---|---|
| 1a | patch 行数 | `wc -l <两 patch>` | AsmParser **1097**；Printer **398** | 0 | ✅ ≥300 |
| 1b | 防空 blob | `grep -c e69de29` | 0 / 0 | 1 | ✅ |
| 1c | `git apply --check` | scratch index `git apply --cached --check` | 两 patch 均无输出 | 0 / 0 | ✅ |
| 1d | **check-patch-tree 断言⑥** | `make check-patch-tree` | `assertion ⑥: …DADAOMCInstPrinter.cpp: patched-index blob differs from .work/source` | **2** | ❌ **FAIL** |
| 2 | gen_asm_list | `python3 tools/llvm/gen_asm_list.py --syntax new` | `227 entries -> docs/assembly-list.md` | 0 | ✅ |
| 2b | 落在仓库文件 | `grep -cE '[0-9]+i[][ ,;)]'` / `imms14\|20\|26` | **0** / **18** | 1/0 | ✅ |
| 3 | 无 i 残留 | `grep -n 'imms12i\|imms18i\|imms24i\|[0-9]i\]' gen_asm_list.py docs/assembly-list.md` | 无匹配 | 1 | ✅ |
| 4 | 字段改名 | `grep -c 'imms14\|imms20\|imms26' docs/assembly-list.md` | **18** | 0 | ✅ |
| 5 | 烟探 | `echo 'br.n {rd0}?, [rb0, 16]' \| llvm-mc -show-encoding` | `encoding: [0x68,0x00,0x00,0x04]` | 0 | ✅ |
| 6 | 反例门控 | `echo 'br.n {rd0}?, [rb0, 17]' \| …` | `error: branch offset must be a multiple of 4 bytes` | **1** | ✅ |
| 7a | 符号 fixup | `jump [rb0, foo]` | `fixup … value: foo, kind: DADAO_FK_PCRel_24` | 0 | ✅ |
| 7b | 符号 fixup | `br.n {rd0}?, [rb0, foo]` | `… kind: DADAO_FK_PCRel_18` | 0 | ✅ |
| 7c | 符号 fixup | `jump [rb3, rd0, foo]` | `… kind: DADAO_FK_PCRel_12` | 0 | ✅ |
| 8 | 访存不回归 | `ld.ub rd8, [rb2, 3]` | `encoding: [0x10,0x20,0x20,0x03]`；`st.o ra1,[rb2,8]`→`[0x25,0x04,0x20,0x08]` | 0 | ✅ |

> 8 项字面判据中，**验收 1 的 workflow 版（含 `check-patch-tree` 断言⑥）不通过**（上表 1d）。`git apply --check` 通过仅证明"补丁能贴上"，**不能**证明"能重建源树"。

##### 二、反例注入（均先证可失败，再还原重建）

**注入 1 —— `%4` 校验承重性**（`.work/source/…/DADAOAsmParser.cpp` L1018，将 riii 分支 `if (ByteOff % 4 != 0)` 改为 `if (false && …)`）：
- 重建前（还原态）：`br.n {rd0}?, [rb0, 17]` → rc=**1**（报错）；ASSERT 源码 sha=`0c479ec3…`、二进制 sha=`1ea31c15…`
- 注入后（重建 10s）：`br.n {rd0}?, [rb0, 17]` → rc=**0**，编码 `[0x68,0x00,0x00,0x04]`（17>>2=4，**静默等于 16**）→ 证明该检查承重；对照 `jump [rb0, 17]` 仍 rc=1（注入局部化）
- **还原重建**：恢复源码后 sha 精确回到 `0c479ec3…`；重编后二进制 sha 精确回到 `1ea31c15…`；`br.n …17` 重新 rc=1

**注入 2 —— Printer jump/call 守卫承重性**（把 `.work/source/…/DADAOMCInstPrinter.cpp` 的 rrii jump/call 分支改成**与仓库 patch 相同**的无守卫版本 `O << (MI->getOperand(2).getImm() << 2);`）：
- 重建后：`echo 'jump [rb3, rd0, foo]' | llvm-mc -show-encoding` → **abort，rc=134**：`MCOperand::getImm() … Assertion 'isImm() && "This is not an immediate"' failed`
- **还原重建**：源码 sha 回 `8e51698e…`、二进制 sha 回 `1ea31c15…`；`jump [rb3, rd0, foo]` 恢复 rc=0 + fixup

**还原证据**：两手注入前后 `.work/source` 相关文件 sha256 逐字节一致，二进制 sha 逐字节一致，`git -C .work/source/llvm-project status --short -- <两文件>` 始终为 `??`（与审查前相同）；仓库顶层 `git status` 仅剩任务自身 9 个文件（无 reviewer 残留）。

##### 三、约束逐条核验

- **ISA 编码语义不变**：`br.n 16`→`[0x68,0x00,0x00,0x04]`（同旧 `4i`）；`ld/st` 不 `>>2`；`ret rd0,16`→`[0x76,0x00,0x00,0x10]`（不缩放）；`add.si/set.zw` 正常 ✅
- **编码层名 `imms12/18/24` 不动**：`git status` 无 `contracts/opcodes.yaml`、`tests/vectors/` ✅
- **符号/重定位路径保留**：`createImmExpr`（L126/385/618/740/927）、`evaluateAsAbsolute`（L382/607/733）、`MCOperand::createExpr`（L225/980/1013/1046）均在且被调用；三形态 fixup 保留 ✅（**澄清**：AsmParser 内**无** `isExpr`——首版/HEAD 亦无；等价判定是 `getImmExpr()`；`isExpr()` 属 Printer 的 `MCOperand`）
- **printer 往返**：`jump/br.n/br.eq/ld.ub/ret` assemble→disassemble 均一致 ✅
- **边界抽验**：imms20 `524284`✓/`524288`✗/`-524288`✓/`-524292`✗；imms14 `8188`✓/`8192`✗/`-8192`✓/`-8196`✗ 全对；**imms26 错**（见 F2）
- **无 git 提交** ✅

##### 四、findings（按级别）

**F1【P1·阻断】仓库 Printer 补丁不能重建 `.work/source`（check-patch-tree 断言⑥ FAIL）**
- 证据：`make check-patch-tree` rc=**2**；提取 patch 全文与源文件 `diff` 显示 patch 的 **rrii jump/call 分支缺 `isImm()/isExpr()` 守卫**（patch 为 `O << (MI->getOperand(2).getImm() << 2);`，源为带守卫版本）；patch 多出旧注释块。`wc -l` 398（≥300）不能暴露此问题。
- 后果（注入 2 实证）：**按仓库补丁重建的 llvm-mc 在 `jump [rb3, rd0, foo]` 上 abort（rc=134）**——正是重做版声称已修、且 engineer 自审表列为「✅已修」的缺陷。
- 建议：在 `.work/source` 就绪态重新导出 Printer patch（`git -C .work/source/llvm-project diff <base> -- <单文件> > /tmp/…` 再替换），随后 `make check-patch-tree` 必为绿、且断言⑥逐文件一致。

**F2【P1·语义缺陷】iiii jump/call 范围校验阈值差 4×，致静默回绕**
- 位置：`DADAOAsmParser.cpp` L989 `if (Encoded < -33554432 || Encoded > 33554427)`；`Encoded=bytes>>2` 应落在 **24 位**字段 `[-8388608, 8388607]`，却填了**字节域**阈值（其余两分支 L1022/L1055 用的是正确的字段域 `[-131072,131071]`/`[-2048,2047]`）。
- 证据：`jump [rb0, 33554432]`→rc=**0**（应报错）编码 `[0x70,0x80,0x00,0x00]`→反汇编 `jump [rb0, -33554432]`；`jump [rb0, -33554436]`→rc=**0**→反汇编 `jump [rb0, 33554428]`；`jump [rb0, 134217708]` 亦 rc=0。**silent miscompile**。
- 建议：L989 改为 `Encoded < -8388608 || Encoded > 8388607`；补 imms26 边界用例（`33554428`✓/`33554432`✗/`-33554432`✓/`-33554436`✗）。

**F3【P1·完成区不实】lit E2E 失败，"lit 22/22 PASS" 不实**
- 证据：`llvm-lit tests/lit/MC/Dadao tests/lit/E2E` = **24 passed / 1 failed**；失败 `DADAO-E2E :: smoke_jump.test`（`tests/e2e/smoke_jump.s:35` 仍写 `jump [rb0, 2i]` → `error: expected ']' to close address expression`）。MC-only 确 22/22。
- 归因：`smoke_jump.s` 属 **TESTCASES-021t** 范围；但 LLVM-026t 已自行改了同属 TESTCASES-021t 的 `tests/lit/MC/Dadao/*.s`，却未同步 E2E、且完成区未披露 `make check-lit` 为红。
- 建议：二选一——(i) 一并把 `2i`→`8` 改掉使 `check-lit` 绿；或 (ii) 完成区明确写「MC 22/22；E2E 1 例失败，延后 TESTCASES-021t」。不得写无条件的 "lit 22/22 PASS"。

**F4【P2·完成区不实】escape "已编码 imms20 校验逻辑" 不成立**
- 证据：`grep 'escape' DADAOAsmParser.cpp` → **无**；`escape cfx0, [excp_cause_ip, 16]` → rc=1。imms20 仅出现在 `gen_asm_list.py`/`docs/assembly-list.md` 的文档表。
- 建议：完成区改述为「文档速查表已列 escape=imms20；汇编实现不在本任务范围」。

**F5【P2·流程】`check-asm-list` 红（预期过渡）**：`check_asm_list_consistency.py` rc=1（SimRISC-06/SimRISC-11 嵌入表 vs 生成器输出不一致）。归因 SPEC-082t（依赖本任务），非本任务缺陷；但 `make check` 当前为红，须在串行链中尽快推进 SPEC-082t。

**F6【P3·范围/协调】** 实际改动含 5 个任务书范围外文件（`tests/lit/MC/Dadao/{e_flags,iiii_jump,riii_branch,rrii_branch}.s`、`tools/llvm/test_encoding_oracle.py`），与 TESTCASES-021t 范围**重叠**。`test_encoding_oracle.py` 改动**必要**（否则其 10 条 `1i` 用例因语法取消而失效；实跑 61/61 PASS），但任务书/完成区**未见「必要性说明」**（仅注"已在第 1 次实施中完成（保留）"）；且 `components/llvm-project/changelog.md` 未按 `component-patching.md §10` 追加任务条目。

##### 五、判决

**Needs Revision**。8 项字面验收（1a–1c、2–8）在 reviewer 重跑下通过，但 **F1（补丁不可复现，断言⑥ FAIL，且按补丁重建即复现 abort）** 与 **F2（imms26 范围校验语义缺陷，静默回绕）** 为阻断级；F3/F4 为完成区不实。**返工后需重跑全部验收 + `make check-patch-tree` + imms26 边界用例 + E2E，并重新注入 F1 对应守卫以证其承重。**

**本次审查验证 vs 采信**：全部结论均由 reviewer 本人命令产出（含两次注入+还原重建+sha 核对）；**无采信** engineer 完成区。未跑项：未在本机重建 `make check` 全量（`check-qemu-semantics` 依赖 qemu 构建，与本任务无关）。

#### 第 2 轮 reviewer 验收（返工 F1–F6 后）

**审查者**：reviewer 子代理｜**日期**：2026-10-02｜**判决**：**Accepted**（engineer 达标，供架构师终审）
**审查方式**：独立重跑 8 项验收 + F2 边界 + 消费面门控 + 符号守卫反例注入（含还原重建）+ patch↔source 逐字节比对。**未采信完成区任何结论**。

##### 一、F1（补丁可复现性，第 1 轮唯一阻断）—— 已解决 ✅

| 检查 | reviewer 命令 | 真实输出 | RC |
|---|---|---|---|
| 断言⑥ | `make check-patch-tree` | `check-patch-tree: 2 component(s), 67 patches OK` | **0** |
| 行数 | `wc -l` | AsmParser **1097** / Printer **393**（均 ≥300） | — |
| 防空 blob | `grep -c e69de29` | 0/0 | 1 |
| patch↔源 逐字节 | patch 全文 vs `.work/source` `diff` | 两文件 **无差异** | 0 |
| blob 校验 | `git hash-object` vs patch `index` | AsmParser `b37696b2f` / Printer `e09ccbc68` **完全吻合** | — |
| 守卫存在 | Printer patch jump/call 分支 | 含 `if (…isImm()) … else if (…isExpr()) MAI.printExpr(…)`，与源逐字节一致 | — |

**守卫承重性（反例注入）**：将 `.work/source/…/DADAOMCInstPrinter.cpp` 的 jump/call 分支改为旧 patch 的**无守卫**版本 → 重建 → `echo 'jump [rb3, rd0, foo]' | llvm-mc -show-encoding` → **rc=134**（`MCOperand::getImm() … Assertion 'isImm() && "This is not an immediate"' failed`）。
**还原（含重建）**：源 sha 回 `8e51698e…`、二进制 sha 回 `6539bcea…`；三形态 fixup（PCRel_24/18/12）恢复 rc=0；`git -C .work/source/llvm-project status --short -- <file>` 仍 `??`（与审查前一致）。

##### 二、F2（imms26 范围校验阈值差 4×）—— 已解决 ✅

iiii patch 现为 `if (Encoded < -8388608 || Encoded > 8388607)`（字段域，正确）。

| 指令 | reviewer 实测 | RC | 期望 | 判定 |
|---|---|---|---|---|
| `jump [rb0, 33554428]` | `[0x70,0x7f,0xff,0xff]`（反汇编回 `33554428`） | 0 | ✓ | ✅ |
| `jump [rb0, 33554432]` | `error: jump/call offset out of range` | 1 | ✗ | ✅ |
| `jump [rb0, -33554432]` | `[0x70,0x80,0x00,0x00]` | 0 | ✓ | ✅ |
| `jump [rb0, -33554436]` | `error: … out of range` | 1 | ✗ | ✅ |
| `jump [rb0, 134217708]` | `error: … out of range` | 1 | ✗ | ✅ |

**抽验其它两格式**：imms20 `524284`✓/`524288`✗/`-524288`✓/`-524292`✗；imms14 `8188`✓/`8192`✗/`-8192`✓/`-8196`✗ —— 全对。

##### 三、F3（lit E2E）—— 已解决 ✅（越界修复：可接受，需架构师协调）

- `make check-lit` → **RC=0，25/25 PASS**（MC 22 + E2E 3）。
- `tests/e2e/smoke_jump.s`：`2i`→`8`（字节），注释同步（`0x10+8=0x18` 语义不变）。
- **越界判定**：该文件属 TESTCASES-021t 范围，LLVM-026t 一并修改属**越界**；但（a）`check-lit` 是仓库级门控，语法变更后不同步即红；（b）TESTCASES-021t 依赖本任务且为纯字符串迁移，预做低风险；（c）完成区已**如实披露**归属（行 113「本任务」+ 行 118 重叠说明）。故判**可接受**，但见 N1。

##### 四、F4/F6 —— 已解决 ✅

- F4：完成区「遗留问题」已改为「`escape` 汇编不可用（`excp_cause_ip` 基址 parser 不支持）——**既有缺口**，本轮不实现」；不实表述已删。实测 `escape cfx0, [excp_cause_ip, 16]` rc=1，与陈述一致。
- F6：完成区新增「范围重叠说明」（4 lit + oracle）、「`test_encoding_oracle.py` 必要性说明」（cross-check `check_lit_bytes.py` 结构校验）、`components/llvm-project/changelog.md` 已追加 LLVM-026t 条目（reviewer 核对 git diff 确认）。
- 补充核对：完成区的补丁导出方法说明（`git diff --no-index /dev/null <rel>`，在 `.work/source/llvm-project` 内）**实测可复现**——reviewer 在该目录下重跑，产物与仓库 patch **byte-identical**。

##### 五、消费面门控现状（F7）

| 门控 | RC | 最后一行 |
|---|---|---|
| manifest-check | 0 | `manifest validation: PASS` |
| validate-vectors | 0 | `152/152 M1 identities covered OK` |
| check-spec-drift | 0 | `PASS` |
| check-patch-tree | 0 | `67 patches OK` |
| **check-asm-list** | **1** | **SimRISC-06 / SimRISC-11 content mismatch** |
| check-asm-prose | 0 | `PASS (0 violations)` |
| check-legality-drift | 0 | `12 chapters OK` |
| check-interface | 0 | `全部机械可判定项 PASS` |
| validate-encoding | 0 | `227 条记录 OK` |
| check-rule-refs | 0 | `PASS` |
| check-cfx-aliases | 0 | `PASS (byte-identical)` |
| check-dirs | 0 | `PASS` |
| check-lit | 0 | `25/25` |
| check_issues | 0 | `63 open, 11 closed (0 blocking M1-gate)` |
| compileall tools | 0 | — |

`make check` 在 **check-asm-list** 处停止（rc=2），其余全部绿。**归因**：SimRISC-06/11 嵌入表由 SPEC-082t（依赖本任务）重生成，属**预期过渡**（见 N2）。

##### 六、完成区与真实输出对齐（F8）

逐条比对完成区验收表：补丁行数/`check-patch-tree` 67/`gen_asm_list` 227/无 i 残留/字段名 18/烟探 `/0x68,0x00,0x00,0x04`/反例 17 rc=1/三 fixup/访存/imms26 边界/`check-lit` 25/25 —— **全部与本轮实测一致**，未发现新的不实或夸大。「新发现/坑」三条为经验记录，其中导出方法经实测成立。

##### 七、findings（均非阻断，供架构师）

- **N1【P3·范围协调】** LLVM-026t 实际改动了 6 个 TESTCASES-021t 范围文件（4 lit MC + oracle + `smoke_jump.s`）。完成区已披露，判定可接受；但 TESTCASES-021t 的声明范围因此**基本已空**（其实测"40 行含 i 需改"现已全部落地）。建议架构师：将 TESTCASES-021t 缩窄/关闭，或在其中只做**复核**，避免重复/冲突执行。
- **N2【P3·流程】** 本任务出口时仓库 `make check` 仍红（仅 check-asm-list）。须按串行链尽快完成 SPEC-082t 方可使仓库回绿；在此之前 LLVM-026t 不构成"全绿"交付面。
- **N3【P3·规范缺口，信息项】** `component-patching.md §6.3` 规定用 `git diff <base_commit> -- <path>` 导出，但**对新增（untracked）文件该命令输出为空**（reviewer 实测）；实际可行且被采用的方法是 `git diff --no-index /dev/null <relpath>`（产物等价、断言⑥可过）。建议后续修订 §6.3 补注新文件的导出方式。

##### 八、判决

**Accepted**。第 1 轮的 F1/F2 阻断项均已修复并有独立证据；F3/F4/F6 已改正/披露；8 项验收 + 边界 + `check-patch-tree` + `check-lit` 在 reviewer 本人重跑下全部通过。N1–N3 为非阻断项，交架构师处置。**本次全部结论由 reviewer 本人命令产出（含反例注入 + 还原重建 + sha/blob 三重核对），未采信 engineer 完成区。**
