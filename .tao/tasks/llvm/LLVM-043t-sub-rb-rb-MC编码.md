# LLVM-043t: 新增指令 `sub.o rd, rb, rb` 的 MC（汇编/反汇编/编码）

**模块**：llvm
**项目里程碑**：M3
**依赖**：`SPEC-100t`（**须其编码/legality 定稿后**；助记符/`ha` 以用户确认结论为准）
**状态**：待开始

> **前置**：`adr-0012 D9`（`Accepted`）已定：`id=sub.o_orrr_dbb`、助记符 `sub.o`、`ha=0x33`、`value=0x40CC0000`。`SPEC-100t` 落地编码后本任务执行。
>
> **串行**：本任务与 `LLVM-033t`–`041t` 同改 `DADAOInstrInfo.td` 与 `.work/source/llvm-project`（共享文件），按 `AGENTS.md`「同改共享文件串行」**不得并行**；**且须在 `SPEC-101t`（三条既有 RB 算术指令改名/改编码，改同一 `.td`）之后**；在串行链中**先于 `LLVM-035t`**（`LLVM-034t → [SPEC-101t] → LLVM-043t → LLVM-035t`）。
>
> **本任务只做 MC**：新增指令定义 + 汇编/反汇编/编码/decode + lit 往返。**ISel pattern 不在本任务**（→ `LLVM-035t`）；指令定义先带 `Pattern = []`。

## 执行环境
**执行环境**：本地

## 接口规范

### 输入

- `adr-0012 D9` / `SPEC-100t` 的指令事实：`id=sub.o_orrr_dbb`、助记符 `sub.o`、格式 `orrr`、字段 `rdhb`(dst,rd)/`rbhc`(src,rb)/`rbhd`(src,rb)、`op=0x40`/`ha=0x33`/`mask=0xFFFC0000`/`value=0x40CC0000`、legality `dst_rd0`、`scope=m3`。
- 现有 MC 实现（`.work/source/llvm-project/llvm/lib/Target/DADAO/`，对应补丁 `components/llvm-project/patches/llvm/lib/Target/DADAO/`）：
  - `DADAOInstrFormats.td`：`class DADAOOrrr<string mnemonic> : DADAOInst<mnemonic # "\t$rb, $rc, $rd">`（`hb=rb`/`hc=rc`/`hd=rd`）。
  - `DADAOInstrInfo.td`：`cmp_uo_dbb : DADAOOrrr<"cmp.uo"> { OutOperandList=(outs GPRD:$rb); InOperandList=(ins GPRB:$rc, GPRB:$rd); op=0x40; ha=0x32; }` ——本指令的**直接同形参照**（`SPEC-101t` 后由 `cmp_uo_rb`/`ha=0x29` 改名改槽）。
  - `AsmParser/DADAOAsmParser.cpp`：汇编匹配走 TableGen `MatchInstructionImpl`（同形指令无需手写分支）；`Disassembler/DADAODisassembler.cpp`、`MCTargetDesc/DADAOMCInstPrinter.cpp` 由 TableGen 生成。
- `tools/llvm/test_encoding_oracle.py`（独立编码 oracle）、`tools/llvm/check_lit_bytes.py`、`tests/lit/MC/Dadao/*.s`。
- `spec/Process-01-组件补丁组织与构建编排.md`（补丁导出纪律：一文件一补丁、`git apply` 可复现）。

### 输出

1. `DADAOInstrInfo.td`（及其补丁 `DADAOInstrInfo.td.patch`）新增定义：
   ```tablegen
   def sub_o_dbb : DADAOOrrr<"sub.o"> {
     let OutOperandList = (outs GPRD:$rb);     // rd 目的（dbb）
     let InOperandList = (ins GPRB:$rc, GPRB:$rd);
     let op = 0x40;
     let ha = 0x33;
     let Pattern = [];        // ISel pattern 由 LLVM-035t 添加
   }
   ```
   > def 名 `sub_o_dbb` 与 `SPEC-101t` 的 `sub_o_bbd`（`sub.o` rb 目的形态）**不同**，避免 TableGen 重名；两者助记符同为 `sub.o`、由寄存器类区分（同 `cmp.uo` 两形态）。
2. `llvm-mc` 汇编/反汇编往返证据（`sub.o` 汇编 ↔ 4 字节编码 ↔ 反汇编回 `sub.o`）。
3. `tests/lit/MC/Dadao/` 新增/扩展 `; OBJ:`/`; ASM:` 往返用例（建议加入 `rb_ops.s` 或新建，含新指令；`; OBJ:` 字节须与 `opcodes.yaml` 新条目一致）。
4. `tools/llvm/test_encoding_oracle.py`：新增 `sub.o` 的独立编码断言（往返）。
5. 导出的组件补丁（`make check-patch-tree` 通过）。

### 约束

- **只加 MC，不加 ISel**：`Pattern=[]`；不得在 `.td` 添加 `Pat<...>`/`SDNode` 相关内容（归 `LLVM-035t`）。
- **编码单一真源**：`.td` 的 `op`/`ha` 必须与 `SPEC-100t` 定稿的 `contracts/opcodes.yaml` 新条目一致；不得各自为政。
- **AsmMatcher/Decoder 由 TableGen 自动生成**：确认 `MatchInstructionImpl` 能匹配；如确需手写 AsmParser 分支，须在完成区说明理由（同形 `cmp.uo-rb` 无需手写）。
- **补丁导出纪律**（`spec/Process-01`）：补丁写 `/tmp`、非空 blob、行数下限、`make check-patch-tree`（含断言⑥）；修改类补丁须从真实源导出。
- **构建**：`make build-mc`（LLVM 增量构建；首次全量 30–90 分钟，增量按 `JOBS` 限制；重建前在回复写明预计耗时）。
- **不回归** MC lit；临时目录 `/tmp/opencode/LLVM-043t/`；复杂命令输出留存 `.work/log/llvm/`（不 `tee` 吞退出码）；**不提交 git**。

## 验收标准

1. `make build-mc` 退出 0（`ninja` 无错误）。
2. `llvm-mc --triple=dadao-unknown-elf -show-encoding` 对 `<mnemonic> rd8, rb9, rb10` 输出 `[0x40,0xBC,0x…,0x…]` 与 `opcodes.yaml` 新条目 `mask/value` 一致（给真实输出）。
3. **往返**：`llvm-mc` 汇编 → `llvm-objdump -d --triple=dadao-unknown-elf` 反汇编回同一助记符/操作数（给真实输出）。
4. `tests/lit/MC/Dadao/` 新用例 PASS（`llvm-lit` EXIT=0）；`check_lit_bytes.py` EXIT=0。
5. `tools/llvm/test_encoding_oracle.py` EXIT=0（新断言通过，总数较基线 +n）。
6. `make check-patch-tree` EXIT=0；补丁可 `git apply` 干净复现。
7. 反例门控：注入（把 `.td` 的 `ha` 改错 / 改 lit 期望字节）→ `check_lit_bytes` 或 `llvm-lit` **FAIL**；复原（含重建）→ 回绿；真实输出留存 `.work/log/llvm/`。
8. 一键证据脚本 `.work/evidence/LLVM-043t/run.sh`（规格同 `LLVM-033t`）。
9. 未越界：仅改本任务列出的文件；`git status` 干净。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
