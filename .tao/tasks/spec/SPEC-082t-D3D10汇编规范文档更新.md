# SPEC-082t: D3/D10 汇编规范文档更新

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：LLVM-026t（需要 gen_asm_list.py 更新后重新生成嵌入表格）
**状态**：待开始

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

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
