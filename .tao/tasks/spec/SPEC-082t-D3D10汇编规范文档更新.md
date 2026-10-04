# SPEC-082t: D3/D10 汇编规范文档更新

**模块**：spec
**项目里程碑**：M2
**依赖**：LLVM-026t（需要 gen_asm_list.py 更新后重新生成嵌入表格）
**状态**：已验证

## 目标

落地 ADR-0013 D3（汇编地址立即数单位=字节、取消 `i` 后缀）与 D10（汇编层字段改名 `imms14/imms20/imms26`）的规范文档更新：修改 `docs/spec/assembly-language.md`、`spec/SimRISC-06`、`spec/SimRISC-11`、`spec/DADAO-12-SEE`、`spec/DADAO-22-SBI`、`spec/DADAO-23-HBI` 的示例与措辞；重新生成嵌入汇编表格。

## 执行环境

**执行环境**：本地

## 范围

### 文件清单

| 文件 | 改动 |
|---|---|
| `docs/spec/assembly-language.md` | §2.4（去 `i` 后缀说明→字节化）；§3.1/§3.2（字段改名 `imms14/imms20/imms26`、公式保留 `(imms << 2)`）；§3.3/§4.3/§5（所有示例值 ×4、去 `i`）；§5 escape 行（去 `i`、字段改名 `imms20`、补充两层说明）；新增字段映射表；§11 缺口表更新 |
| `spec/SimRISC-06-控制流.md` | 嵌入表格（**由 gen_asm_list.py --embed-spec 自动重生成**）+ 手动更新散文部分分支/跳转示例（~28 处去 `i`、值 ×4） |
| `spec/SimRISC-11-其它.md` | 嵌入表格（自动重生成）+ escape 示例去 `i`（2 处） |
| `spec/DADAO-12-SEE-主管系统运行环境.md` | escape 示例表（`0i`→`0`、`1i`→`4`、`Ni`→`N*4`）+ §666 措辞补充两层说明 |
| `spec/DADAO-22-SBI-主管系统二进制接口.md` | 56 处 `i` 后缀 → 字节值（`escape`/`jump` 示例） |
| `spec/DADAO-23-HBI-硬件二进制接口.md` | 1 处（`escape cfx_power, [excp_cause_ip, 0i]` → `[excp_cause_ip, 0]`） |

### 不改的文件

| 文件 | 理由 |
|---|---|
| `contracts/opcodes.yaml` | 编码层不变（D10 明确"编码层名字保持 `imms12/18/24`"） |
| `.tao/knowledge/adr-0013-assembly-syntax.md` | 已定稿，不改 |
| `spec/SimRISC-0.5.3/` | 历史记录，不改 |
| `tests/vectors/isa/*.yaml` | 只含 raw encoding，不含汇编文本 |
| `docs/assembly-list.md` | 生成物，由 LLVM-026t 的 gen_asm_list.py 自动重生成 |

### 约束

- ISA 编码语义不变；仅改汇编层文档
- 嵌入表格由 `gen_asm_list.py --embed-spec` 重生成，不手工编辑嵌入区块
- 散文部分（非嵌入表格区域）需手动更新
- escape 措辞须写明**两层**：编码层 `imms18`（`Addr = excp_cause_ip + (imms18 << 2)`）；汇编层 `imms20`、字节、须 `%4==0`

### 详细改动

#### 1. docs/spec/assembly-language.md

**§2.4 数字与单位后缀**：
- 删除"单位后缀 `i`"整段（原 L38–40）
- 新增：「地址立即数（跳转/分支目标偏移与 escape 偏移）单位为**字节**，**不含任何单位标记**。装配器将其右移 2 位写入编码字段；汇编器**校验** `%4==0` 与范围。字段名映射见 §3.1。」

**§3.1 语法**：去掉 `[单位后缀]` 语法项

**§3.2 语义**：
- iiii 跳转/分支：目标 = `基址 + 立即数`（**字节**，`imms26`/`imms20`/`imms14`）。例：`jump [rb0, 8]` ⇒ `rb0 + 8`
- rrii 跳转：目标 = `基址 + 寄存器偏移 + 立即数`（**字节**，`imms14`）。例：`jump [rb3, rd0, 96]` ⇒ `rb3 + rd0 + 96`
- 访存：不变（`imms12`，字节）
- **新增映射表**：`imms14 ⇔ 编码 imms12`（汇编字节 = 编码 ×4）、`imms20 ⇔ imms18`、`imms26 ⇔ imms24`

**§3.3 示例**：`jump [rb0, 2i]`→`jump [rb0, 8]`、`call [rb0, 3i]`→`call [rb0, 12]`、`jump [rb3, rd0, 24i]`→`jump [rb3, rd0, 96]`、`br.eq {rd8, rd0}?, [rb0, 4i]`→`br.eq {rd8, rd0}?, [rb0, 16]`

**§4.3 示例**：`br.n {rd0}?, [rb0, 4i]`→`[rb0, 16]`、`br.eq {rd8, rd0}?, [rb0, 4i]`→`[rb0, 16]`、`br.z {rb2}?, [rb0, 4i]`→`[rb0, 16]`

**§5 指令语法表**：
- `rrii` 行：`24i`→`96`；单位说明→"跳转偏移 = 字节"
- `riii` 行：`4i`→`16`；→"分支偏移 = 字节"
- `iiii` 行：`2i`→`8`；→"偏移 = 字节"
- `escape` 行：`1i`→`4`；补充"汇编层 `imms20`（字节，`%4==0`）；编码层 `(imms18 << 2)`"
- `ret` 行：不变（`imms18` 非地址）

**§11 缺口表**：更新新记法状态

#### 2. spec/SimRISC-06-控制流.md

- 嵌入表格：`python3 tools/llvm/gen_asm_list.py --embed-spec` 自动重生成
- 散文部分：手动更新所有 `i]` 示例（~28 处）为字节值

#### 3. spec/SimRISC-11-其它.md

- 嵌入表格：自动重生成
- 散文：escape 示例去 `i`（2 处）

#### 4. spec/DADAO-12-SEE-主管系统运行环境.md

- §666 措辞："imms18 按指令字偏移（×4 字节）"→ "**编码层**：imms18，`Addr = excp_cause_ip + (imms18 << 2)`；**汇编层**：imms20 以字节为单位，值须 `%4==0`"
- §670–672 示例表：汇编列 `0i`→`0`、`1i`→`4`、`Ni`→`N*4`；**编码层公式保持** `cause_ip + (imms18 << 2)`（`imms18` = 编码字段/字数）。
  - ⚠️ **防二次乘 4**：示例列改为**字节值**后，若表格同时给出"地址结果"，必须与 `cause_ip + 字节值` 一致；**不得**再用 `N×4` 指代字节列（否则等于把字节又乘 4）。

#### 5. spec/DADAO-22-SBI-主管系统二进制接口.md

- 56 处 `i` 后缀 → 字节值（主要是 `escape cfx_*, [excp_cause_ip, 1i]`→`[excp_cause_ip, 4]`、`jump [rb3, rd0, 0i]`→`[rb3, rd0, 0]`）

#### 6. spec/DADAO-23-HBI-硬件二进制接口.md

- 1 处：`escape cfx_power, [excp_cause_ip, 0i]`→`[excp_cause_ip, 0]`

## 验收标准

1. **全量无 `i` 残留**：`grep -rn '[0-9]i\]' docs/spec/assembly-language.md spec/SimRISC-06-*.md spec/SimRISC-11-*.md spec/DADAO-12-SEE-*.md spec/DADAO-22-SBI-*.md spec/DADAO-23-HBI-*.md` 退出码 1
2. **字段改名正确**：`grep -c 'imms14\|imms20\|imms26' docs/spec/assembly-language.md` 输出 > 0；`grep -c 'imms12i\|imms18i\|imms24i' docs/spec/assembly-language.md` = 0
3. **字节值抽验**：手动核对 3 处 —— `jump [rb0, 8]`（8>>2=2 ✓）、`br.n {rd0}?, [rb0, 16]`（16>>2=4 ✓）、`escape cfx63, [excp_cause_ip, 4]`（4>>2=1 ✓）
4. **DADAO-12 两层措辞**：§666 同时提及编码层（imms18、`<<2`）与汇编层（imms20、字节、`%4==0`）
5. **嵌入表格已更新**（BLOCKED，见预检）：`spec/SimRISC-06`、`spec/SimRISC-11` 嵌入区块不含 `i]`

## 下发前预检

1. **任务书内部一致性**：✅ D3/D10 均覆盖；6 个文件全量列出；escape 两层措辞明确；访存/ret 排除明确
2. **依赖链实际可用性**：⚠️ 嵌入表格重生成依赖 LLVM-026t（gen_asm_list.py 更新后）；散文部分可先行更新
3. **验收可执行性**：
   - 验收 1（全量 grep）：**现在可跑**（散文更新后即可验证）
   - 验收 2（字段改名）：**现在可跑**
   - 验收 3（字节值抽验）：**现在可跑**
   - 验收 4（DADAO-12 措辞）：**现在可跑**
   - 验收 5（嵌入表格）：**BLOCKED**（需 LLVM-026t 完成 + `python3 tools/llvm/gen_asm_list.py --embed-spec`；替代证据：验收 2 + 检查 gen_asm_list.py 源码已去 `i`）
4. **与 spec/vectors 一致**：✅ 不改 `contracts/opcodes.yaml`、不改 `tests/vectors/`

## 完成区

**测试结果**：5/5 验收项通过；`make check-asm-list` 12/12 OK；`make check-asm-prose` 5 violations（R2 规则未更新，归属 INFRA-024t）

**修改文件**：
- `docs/spec/assembly-language.md`（§2.4 去 `i` 后缀说明→字节化+标题改为「数字与立即数单位」+术语表去掉「单位后缀」；§3.1 去 `[单位后缀]`；§3.2 字段改名 `imms14/20/26`+映射表；§3.3/§4.3 示例值 ×4 去 `i`；§5 指令表 ×4+字节说明+3 处「不加 `[]`」统一；§11 缺口表去 `i`）
- `spec/SimRISC-06-控制流.md`（散文：14 处 `imms12i/18i/24i` → `imms14/20/26`；嵌入表格由 `gen_asm_list.py --embed-spec` 重生成）
- `spec/SimRISC-11-其它.md`（散文：escape 措辞两层说明；嵌入表格由 `gen_asm_list.py --embed-spec` 重生成）
- `spec/DADAO-12-SEE-主管系统运行环境.md`（§666 两层措辞；§670–672 示例表 `0i→0`、`1i→4`、`Ni→N*4`；§674 跨 cfx prose `Ni→N*4`）
- `spec/DADAO-22-SBI-主管系统二进制接口.md`（56 处 `i` 后缀→字节值：`[excp_cause_ip, 1i]→4` ×48、`[excp_cause_ip, 0i]→0` ×3、`[rb3, rd0, 0i]→0` ×5）
- `spec/DADAO-23-HBI-超管系统二进制接口.md`（1 处：`[excp_cause_ip, 0i]→0`）

**验收结果**（第 2 轮，含 reviewer F1/F2 返工）：
1. `grep -rnE '[0-9]+i[][,; )]'` 6 文件 ⇒ **EXIT=1**（0 匹配）✅
2. `imms14/20/26` 出现 4 次；`imms12i/18i/24i` 出现 0 次 ✅
3. 字节值抽验：`jump [rb0, 8]`（8>>2=2 ✓）、`br.n {rd0}?, [rb0, 16]`（16>>2=4 ✓）、`escape cfx63, [excp_cause_ip, 4]`（4>>2=1 ✓）✅
4. DADAO-12 §666：「**编码层** `imms18`（指令字偏移），`Addr = excp_cause_ip + (imms18 << 2)`；**汇编层** `imms20` 以字节为单位，值须 `%4==0`」✅
5. `make check-asm-list` ⇒ **12 spec files OK** ✅；`make check-asm-prose` ⇒ 5 violations（R2 `跳转立即数缺i后缀`，检查脚本 `tools/spec/check_asm_prose.py` 的 R2 规则未同步 D3 更新，**归属 INFRA-024t**）⚠️
6. `grep -nE '单位后缀|加 .i.|.i. 后缀' docs/spec/assembly-language.md` ⇒ **EXIT=1**（0 匹配）✅（F2 返工验证）

**新发现/坑**：
- `gen_asm_list.py --embed-spec` 已具备 D3/D10 改动（`_ASM_IMM_RENAME` 映射 + `IMM_EXAMPLE` 字节值），可直接重生成嵌入表格，无需等待 LLVM-026t
- `check_asm_prose.py` 的 R2 规则（line 492–506）仍要求 `jump`/`call` 立即数带 `i` 后缀——这是 D3 落地后的遗留门控缺口，需 INFRA-024t 修复
- DADAO-12 line 674 的 `Ni`（跨 cfx escape prose）不在任务书的 2 处计数内，但需同步更新为 `N*4` 以保持一致性
- DADAO-22-SBI 有 56 处（任务书准确），全部为 escape/jump 示例中的 `1i`/`0i` 后缀
- 「不加 `[]`/`i`」同款短语共 3 处（`oiii`/`trap`/`ret`），第 1 轮漏修 `trap`（reviewer F1）——AGENTS.md「修复须修一类」教训

**遗留问题**：
- `check_asm_prose.py` R2 规则需同步 D3 更新（归属 INFRA-024t），当前 `make check-asm-prose` 仍红

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：6 个文件的所有改动（docs/spec/assembly-language.md、spec/SimRISC-06、SimRISC-11、DADAO-12、DADAO-22、DADAO-23）

**发现**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | DADAO-12 line 674 `Ni` 未在任务书 2 处计数内，但使用旧 `i` 约定 | ✅已修 | `Ni` → `N*4` | grep 0 匹配 |
| 2 | `check_asm_prose.py` R2 规则仍要求 `i` 后缀 | ⏸延后 | 归属 INFRA-024t | `make check-asm-prose` 5 violations |
| 3 | 嵌入表格由 `gen_asm_list.py --embed-spec` 自动重生成 | ✅已验 | 脚本已有 D3/D10 改动 | 生成结果 0 `i` 残留 |

**判决**：所有可修 finding 已修，仅 `check_asm_prose.py` 延后（INFRA-024t 归属）。可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查范围**：任务书 + 决策真源（`ADR-0013` D3/D10）+ `contracts/opcodes.yaml` 字段语义 + 待验改动集 `git status --short`（6 文件 + 任务书）。所有判断均来自 reviewer 独立重跑。

**改动集核对（git status --short）**：仅 7 个文件 M —— `docs/spec/assembly-language.md`、`spec/SimRISC-06/11`、`spec/DADAO-12/22/23`、任务书。**无夹带**：`contracts/opcodes.yaml`、`docs/assembly-list.md`、`.tao/knowledge/adr-0013-*`、`spec/SimRISC-0.5.3/`、`tests/vectors/` 均未改。✅

##### 1. 逐处 ×4 算术核对（全量，非抽样）

从 `git show HEAD:<file>` 提取旧版全部 `<数字>i`，独立重算 `N×4` 与现版比对：

**docs/spec/assembly-language.md（旧版 15 处数字 `Ni`）**

| 旧值 | 现版字节值 | `N×4` 重算 | 判定 |
|---|---|---|---|
| `2i`（§2.4 定义段 L38） | 整段删除 | — | ✓ |
| `2i`（§3.2 `jump`） | 8 | 8 | ✓ |
| `24i`（§3.2 `jump`） | 96 | 96 | ✓ |
| `2i`（§3.3 `jump`） | 8 | 8 | ✓ |
| `3i`（§3.3 `call`） | 12 | 12 | ✓ |
| `24i`（§3.3 `jump`） | 96 | 96 | ✓ |
| `4i`（§3.3 `br.eq`） | 16 | 16 | ✓ |
| `4i`×3（§4.3 `br.n/br.eq/br.z`） | 16×3 | 16 | ✓ |
| `24i`（§5 `rrii` 行） | 96 | 96 | ✓ |
| `4i`（§5 `riii` 行） | 16 | 16 | ✓ |
| `2i`（§5 `iiii` 行） | 8 | 8 | ✓ |
| `1i`（§5 `escape` 行） | 4 | 4 | ✓ |
| `24i`（§5 特例 `rrii`） | 96 | 96 | ✓ |

**spec/DADAO-12**：`0i`→`0`（0×4=0 ✓）、`1i`→`4`（1×4=4 ✓）、`Ni`→`N*4`（2 处：§672 表 + §674 prose）。**防二次乘 4 核验**：表中 `[excp_cause_ip, 4]` 的「返回位置」为 `cause_ip + 4`（字节直加，**非** ×4）；`N*4`→`cause_ip + N×4`。两列口径自洽，**无二次乘 4**。✓

**spec/DADAO-22**（56 处，现版实点）：`[excp_cause_ip, 1i]`→`4` **×48**、`[excp_cause_ip, 0i]`→`0` **×3**、`[rb3, rd0, 0i]`→`[rb3, rd0, 0]` **×5**；合计 48+3+5=**56**，与任务书一致。现版 `grep -oE` 统计恰为 48/3/5，无其它数字地址偏移。✓

**spec/DADAO-23**：`[excp_cause_ip, 0i]`→`0` ×1。✓

**spec/SimRISC-06（28）/SimRISC-11（2）**：均为**字段名** `imms12i/18i/24i`→`imms14/20/26`（D10 改名，非算术），非 `N×4` 语义。✓

> 结论：全量逐处重算**无一处错值**。

##### 2. 字段改名范围（对照 `contracts/opcodes.yaml`）

`opcodes.yaml` 实测字段：`jump_iiii`/`call_iiii`=imms24、`jump_rrii`/`call_rrii`/`br.eq_rrii`=imms12、`br.*_riii`=imms18、`escape`=imms18、`ret`=imms18、`ld.ub`/`st.b`=imms12。据此：

- ×4 地址字段改名：`imms12→imms14`、`imms18→imms20`、`imms24→imms26` —— 6 文件中**仅**用于 br/jump/call/escape。✓
- **未误改**：访存 `imms12`（assembly-language L62、L66；SimRISC-06 无）、`ret` 的 `imms18`（SimRISC-06 L27 表 + L140 prose、assembly-language L160）保持不变。✓
- 保留的 `imms12/18/24` 经逐行核对**全部为编码层公式、访存、ret 或硬件伪码**（SimRISC-06 L55/70/90/93/99/104/108/116/124/127、DADAO-12 L830/853）。✓

##### 3. escape 两层措辞（三处口径自洽）

- `assembly-language.md` L156：汇编层 `imms20`（字节、`%4==0`）+ 编码层 `Addr = excp_cause_ip + (imms18 << 2)`。✓
- `SimRISC-11` L111：`imms20`（字节、`%4==0`；`实际地址 = excp_cause_ip + imms20`；编码层 `<<2`）。✓
- `DADAO-12` L666：**编码层** `imms18`（`<<2`）+ **汇编层** `imms20`（字节、`%4==0`）。✓

##### 4. 嵌入表格幂等 + 口径一致

- 重跑 `python3 tools/llvm/gen_asm_list.py --embed-spec`：EXIT=0。对全部 14 个文件（12 spec + assembly-language + assembly-list）取 sha256 前后比对 → **完全一致**；`git status --short` 恒为 7 文件。**幂等成立**。✓
- 嵌入区块与 `docs/assembly-list.md`（LLVM-026t, commit `9dab0b9`）逐行一致（br/jump/call→imms14/20/26、ret→imms18、escape→imms20）。✓
- **门控可失败验证**：注入反例（把 `SimRISC-06` 嵌入块 `br.n … imms20` 改为 `imms18`）→ `make check-asm-list` **FAIL**（`content mismatch … expected 21 lines, got 21 lines`）；复原（md5 `5c55b07e…` 与备份一致）后重跑 **12 spec files OK**。✓

##### 5. 残留 / 门控

- `grep -rn '[0-9]i\]'`（6 文件）⇒ **EXIT=1**（0 匹配）；宽口径 `[0-9]+i` ⇒ EXIT=1；`offi/offseti/immi/immsNi` ⇒ EXIT=1。数字型 `i` 残留**已清零**。✓
- `make check-asm-list` ⇒ `12 spec files OK`，EXIT=0。✓
- `make check-asm-prose` ⇒ **5 violations，全为 R2(跳转立即数缺i后缀)**（`DADAO-22` L191/207/224/257/274 的 `jump [rb3, rd0, 0]`），EXIT=2。核对 `check_asm_prose.py` L492–506：R2 **确为**「jump/call 裸数字须带 `i` 后缀」的 D3 前旧规则；`INFRA-024t` 为真实存在的 `待开始` 任务（专项改此规则）。**确因 R2 旧规则，非文档残留 `i`**，归属 INFRA-024t 成立。⚠️（但见 finding F3：模块门控当前为红状态）

##### 6. finding（分级）

| # | 级别 | 位置 | 问题 | 建议 |
|---|---|---|---|---|
| **F1** | **阻断（Needs Revision）** | `docs/spec/assembly-language.md` L157 | `trap cfx63, 1` 行末仍写「**不加** `[]`/`i`」。**同类模式修复不全**：HEAD 中「不加 `[]`/`i`」共 3 处（L150 `oiii`、L158 `trap`、L161 `ret`），本任务已修 `oiii`(→「不加 `[]`」)与 `ret`(→「不加 `[]`」)，**独漏 `trap`**。`i` 后缀已被 D3 取消，此处引用已废止记法，与同段其它两行自相矛盾；也违反 AGENTS.md「修复须修一类」。 | 将 L157 改为「…**不加** `[]`。」（同 `oiii`/`ret`） |
| F2 | 次要（建议同轮清理） | 同文件 L16、L35 | 术语表 L16 仍列「**单位后缀**——见 §2.4」；§2.4 标题仍为「数字与单位后缀」。D3 已「取消任何单位标记」，该术语/标题悬空。 | 若架构师认可属本任务范围：L16 去「**单位后缀**」项（或改为「**地址立即数（字节）**」）；§2.4 标题可改为「数字与立即数单位」。否则请架构师登记为后续任务 |
| F3 | 说明（非本任务缺陷） | `Makefile` / `check_asm_prose.py` | `make check-asm-prose` 当前红（5×R2），归属 `INFRA-024t`（待开始）。工程未改门控凑绿，处置正确；但该门控属 `make check` 的一部分，模块里程碑核验前须完成 INFRA-024t。 | 由架构师在里程碑层面跟踪 |

##### 7. 完成区一致性核对

- 完成区 `修改文件` 列表与实测 7 文件集合**一致**；DADAO-22「56 处」实测 48/3/5=56 **属实**。
- 完成区「5/5 验收项通过」：验收 1–5 的**命令/判据**经 reviewer 重跑**全部通过**，属实。
- 完成区「无 `i` 残留」的**口径为窄 grep `[0-9]i\]`**，与其给出的命令一致；但**验收标准 1 的标题为「全量无 `i` 残留」**——L157 的 prose `i` 引用说明「全量」未达成（见 F1）。属**口径收窄**，非直接伪造。
- `make check-asm-prose` 5 violations / R2 / INFRA-024t 归属：**与实测一致**，属实。

##### 判决

**Needs Revision**。

- 核心交付（6 文件字段改名、全量字节值 ×4、escape 两层、嵌入表幂等）经独立重跑**全部正确**；5 条验收命令亦全部通过。
- 但 **F1 阻断**：`trap` 行的 `[]`/`i` 属「同类模式修复不全」——本任务明确改了 `oiii`/`ret` 的同款措辞却漏掉 `trap`，直接抵触 D3「取消 `i` 后缀」与验收 1「全量无 `i` 残留」之意图。请按上表 **F1** 修正（建议 F2 一并处理），改后重跑 6 文件 grep 与 `make check-asm-list` 报回。
- F3 为跨任务门控事项，不构成本任务的实现缺陷，但请架构师知晓模块红门。

（证据文件：`/tmp/opencode/SPEC-082t-review/`：`diff-assembly.md`、`diff-spec.md`、`sha-before2.txt`/`sha-after2.txt`、`embed-run.log`、`backup/`。）

#### 第 2 轮 engineer 自审（返工 F1/F2）

**返工内容**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1（阻断）「不加 `[]`/`i`」漏修 `trap` | ✅已修 | L157 `不加 []/i` → `不加 []` | `grep -nE '不加.*\/i' docs/spec/assembly-language.md` EXIT=1（0 匹配）；3 处同类（L149 oiii、L157 trap、L160 ret）现一致 |
| F2（次要）术语表/标题「单位后缀」悬空 | ✅已修 | L16 `单位后缀` → `地址立即数（字节）`；L35 标题 `数字与单位后缀` → `数字与立即数单位` | `grep -nE '单位后缀' docs/spec/assembly-language.md` EXIT=1（0 匹配） |

**全文件同类排查**：`grep -nE '单位后缀|加 .i.|.i. 后缀' docs/spec/assembly-language.md` ⇒ EXIT=1（0 残留）。

**判决**：F1/F2 均已修复，验收命令全部通过。可标「待验收」。

#### 第 2 轮 reviewer 验收（复核 F1/F2 返工）

**审查范围**：返工增量（对比 reviewer 第 1 轮备份）+ 全部 6 文件 i 后缀判据重扫 + 门控重跑 + 完成区一致性。所有判断来自 reviewer 独立重跑，不采信完成区。

##### 1. 返工增量隔离（现版 vs 上轮备份 `diff`）

`diff -u backup/assembly-language.md docs/spec/assembly-language.md` 仅 **3 个 hunk**：

| 位置 | 旧 | 现 | 判定 |
|---|---|---|---|
| L16 术语表 | `**单位后缀**` | `**地址立即数（字节）**` | F2 ✓ |
| L35 §2.4 标题 | `数字与单位后缀` | `数字与立即数单位` | F2 ✓ |
| L157 `trap` 行 | `**不加** `[]`/`i`` | `**不加** `[]`` | F1 ✓ |

**纯文字修订，未触碰任何数值行**——故第 1 轮「全量 ×4」结论**继续成立**（数值行零改动）。其余 5 文件 `diff -q` vs 上轮备份**全部 SAME**。

##### 2. F1 复核（同类模式一致性）

现版「不加 `[]`」同款短语：L149 `oiii`、L157 `trap`、L160 `ret` —— **3 处一致为「不加 `[]`」**，`[]`/`i` 已清零。✓

##### 3. 全文件 i 后缀残留自定判据（超出 engineer 的 grep）

对 6 文件独立重扫，判据与结果：

| 判据 | 命令 | 结果 |
|---|---|---|
| A 术语「单位后缀」 | `grep -rn '单位后缀'` | EXIT=1（0）✓ |
| B 反引号 `` `i` `` | `grep -rn '`i`'` | EXIT=1（0）✓ |
| C 后缀/加 i 措辞 | `grep -rnE '后缀\|单位标记\|\[\]/i'` | 仅命中 L38 正确新文本「不含任何单位标记」✓ |
| D 数字 i 残留 | `grep -rnE '[0-9]+i'` | EXIT=1（0）✓ |
| E 旧占位符 | `grep -rnE 'offi\|offseti\|immi\|immsNi\|immuNi'` | EXIT=1（0）✓ |
| F 任意 `<word>i` 记号 | `grep -rnoE '[A-Za-z_]+i\b'` 排除格式类 | 仅剩 `rrri/rwii/crii/add.si/cmp.ui/abi/hi` 等合法记号，无 `i` 后缀 ✓ |

**结论：`i` 后缀残留全清。**

##### 4. 门控与幂等重跑

- `grep -rn '[0-9]i\]'`（6 文件）⇒ **EXIT=1**；宽口径 `[0-9]+i[][ ,;)]` ⇒ EXIT=1。✓
- `imms14|20|26` = **4**；`imms12i|18i|24i` = **0**。✓
- `make check-asm-list` ⇒ `12 spec files OK`，EXIT=0。✓
- `python3 tools/llvm/gen_asm_list.py --embed-spec` EXIT=0；14 文件 sha256 前后一致 ⇒ **幂等**。✓
- `make check-asm-prose` ⇒ 5×R2（`jump [rb3, rd0, 0]`），EXIT=2 —— 与上轮一致，确因 R2 旧规则，归属 `INFRA-024t`。⚠️（跨任务门控，非本任务缺陷）
- `git status --short` ⇒ 恒 **7 文件**（6 目标 + 任务书），无夹带。✓

##### 5. 完成区一致性

- 完成区（第 2 轮）「修改文件」新增描述（标题改「数字与立即数单位」、术语去「单位后缀」、§5「3 处不加 `[]` 统一」）与实测**一致**。
- 验收 #6 精确命令 `grep -nE '单位后缀|加 .i.|.i. 后缀'` ⇒ **EXIT=1**，属实。
- 遗留问题（check-asm-prose 红/INFRA-024t）与实测一致。**无不实/夸大**。

##### 判决

**Accepted**。

- F1/F2 均已修复并复验；返工为纯文字、无回归、无夹带。
- 6 文件字段改名、字节值、escape 两层、嵌入表幂等经第 1 轮全量核验 + 本轮增量复核，**全部正确**。
- 唯一红灯 `make check-asm-prose`（5×R2）归属 `INFRA-024t`（真实 `待开始` 任务），非本任务实现缺陷；请架构师在模块里程碑层面跟踪该红门。
