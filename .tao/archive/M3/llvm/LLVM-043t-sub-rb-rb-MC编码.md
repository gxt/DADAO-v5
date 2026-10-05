# LLVM-043t: 新增指令 `sub.o rd, rb, rb` 的 MC（汇编/反汇编/编码）

**模块**：llvm
**项目里程碑**：M3
**依赖**：`SPEC-100t`（**须其编码/legality 定稿后**；助记符/`ha` 以用户确认结论为准）
**状态**：已验证

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
2. `llvm-mc --triple=dadao-unknown-elf -show-encoding` 对 `<mnemonic> rd8, rb9, rb10` 输出 `[0x40,0xCC,0x…,0x…]` 与 `opcodes.yaml` 新条目 `mask/value` 一致（给真实输出；`ha=0x33 ⇒ 0xCC`）。
3. **往返**：`llvm-mc` 汇编 → `llvm-objdump -d --triple=dadao-unknown-elf` 反汇编回同一助记符/操作数（给真实输出）。
4. `tests/lit/MC/Dadao/` 新用例 PASS（`llvm-lit` EXIT=0）；`check_lit_bytes.py` EXIT=0。
5. `tools/llvm/test_encoding_oracle.py` EXIT=0（新断言通过，总数较基线 +n）。
6. `make check-patch-tree` EXIT=0；补丁可 `git apply` 干净复现。
7. 反例门控：注入（把 `.td` 的 `ha` 改错 / 改 lit 期望字节）→ `check_lit_bytes` 或 `llvm-lit` **FAIL**；复原（含重建）→ 回绿；真实输出留存 `.work/log/llvm/`。
8. 一键证据脚本 `.work/evidence/LLVM-043t/run.sh`（规格同 `LLVM-033t`）。
9. 未越界：仅改本任务列出的文件；`git status` 干净。

## 完成区

**测试结果**：通过 **11/11**（一键证据脚本 `.work/evidence/LLVM-043t/run.sh` 全 PASS，`EXIT=0`）；`run.sh --inject` 自检 PASS（`ha` 0x33→0x37 → 重建 → encoding+lit FAIL → 还原+重建 → 回绿，`EXIT=0`）。`make check` `EXIT=0`（lit `31/31`）；`make check-patch-tree` `EXIT=0`；`make check-source-state` OK。

**修改文件**：

- 组件源码（`.work/source/llvm-project`，收敛为 base+1 commit `3f02dc671`；base=`6dfe1677ab8dffbc6ec13d53a1e0215d75147689`）：
  - `llvm/lib/Target/DADAO/DADAOInstrInfo.td`（+9 行：新增 `def sub_o_dbb`，`op=0x40`/`ha=0x33`/`Pattern=[]`）
- DADAO-v5 仓库：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfo.td.patch`（由 `tools/infra/make_patch.py llvm-project` 从真实源导出；未手改补丁）
  - `components/llvm-project/changelog.md`（`Process-01 §162` 要求的「按任务一条、追加式」记录；任务书未列但规范要求）
  - `tests/lit/MC/Dadao/orrr.s`（+1 `; OBJ:`/`; ASM:` 往返用例）
  - `tools/llvm/test_encoding_oracle.py`（+1 独立编码断言，121→122）
  - 本任务书
- 非易失证据（gitignored）：`.work/evidence/LLVM-043t/{run.sh,check_encoding.py}`；日志 `.work/log/llvm/LLVM-043t-*.log`；临时 `/tmp/opencode/LLVM-043t/`。

**验收结果**（真实命令 + 真实输出 + 退出码；`cmd > log 2>&1; rc=$?; echo "EXIT=$rc"` 制式，无 `tee`）：

1. **构建**（验收 1）：`make build-mc` → `EXIT=0`（增量：27 步，`[25/27] Linking ... llvm-mc` … `[27/27] Linking ... llc`；log `.work/log/llvm/LLVM-043t-build-mc.log`；首次全量 30–90 分钟为历史，本次仅 DADAO 表重生成 + 目标重编译）。
2. **编码**（验收 2）：
   ```
   $ .work/build/llvm/bin/llvm-mc --triple=dadao-unknown-elf -show-encoding <<< 'sub.o rd8, rb9, rb10'; echo "EXIT=$?"
   sub.o rd8, rb9, rb10                    ; encoding: [0x40,0xcc,0x82,0x4a]
   EXIT=0
   ```
   与 `contracts/opcodes.yaml` 新条目一致：`word=0x40CC824A`，`word & mask(0xFFFC0000) = 0x40CC0000 = value` ✅。
   > **注**：任务书验收 2 写作 `[0x40,0xBC,…]`，与 D9.1 的 `ha=0x33 ⇒ value=0x40CC0000` 不符（第二字节应为 **0xCC**）；以 opcodes.yaml 单一真源为准（见「新发现 1」）。
3. **往返**（验收 3）：
   ```
   $ llvm-mc --triple=dadao-unknown-elf -filetype=obj -o sub.o - <<< 'sub.o rd8, rb9, rb10'; echo "EXIT=$?"   → EXIT=0
   $ llvm-objdump -d --triple=dadao-unknown-elf sub.o; echo "EXIT=$?"
   0000000000000000 <.text>:
          0: 40 cc 82 4a  sub.o rd8, rb9, rb10
   EXIT=0
   $ llvm-mc --triple=dadao-unknown-elf -filetype=asm - <<< 'sub.o rd8, rb9, rb10'; echo "EXIT=$?"
   sub.o rd8, rb9, rb10
   EXIT=0
   ```
4. **lit + 字节校验**（验收 4）：`llvm-lit tests/lit/MC/Dadao` → `Passed: 27 (100.00%)`，`EXIT=0`；`tools/llvm/check_lit_bytes.py` → `check_lit_bytes: 114 patterns OK`（113→114），`EXIT=0`。
5. **独立 oracle**（验收 5）：`tools/llvm/test_encoding_oracle.py` → `Results: 122 passed, 0 failed out of 122 tests`、`Cross-check OK: oracle tests (122) >= lit OBJ lines (114)`，`EXIT=0`（基线 `HEAD:` 版 121 → 122，**+1**；新增 `("sub.o rd8, rb9, rb10", encode_orrr(0x40,0x33,8,9,10))`）。
6. **补丁**（验收 6）：`python3 tools/infra/make_patch.py llvm-project` → `1 written, 44 unchanged (skipped)`，`EXIT=0`；`make check-patch-tree` → `check-patch-tree: 2 component(s), 77 patches OK`，`EXIT=0`；`make check-source-state` → `llvm-project: OK HEAD=3f02dc671ac3 count=1 clean=True`。导出补丁含 `def sub_o_dbb` + `ha = 0x33`。
7. **反例门控**（验收 7，真实输出，`cmd > log 2>&1; rc=$?`）：
   ```
   $ .work/evidence/LLVM-043t/run.sh --inject; echo "EXIT=$?"
   inject: changing sub_o_dbb ha = 0x33 -> 0x37 (free reserved slot)
   inject: dirty: llvm/lib/Target/DADAO/DADAOInstrInfo.td
   inject: rebuilding llvm-mc/llvm-objdump ...
   inject: rebuild EXIT=0
   [FAIL] encoding | ... actual: [FAIL] sub.o rd8, rb9, rb10: word 0x40dc824a != derived 0x40cc824a | rc=1
   inject: got expected encoding FAIL
   inject: got expected lit FAIL (orrr.s rc=1)
   inject: restoring source and rebuilding ...
   inject: rebuild EXIT=0
   inject: restore sha256 unchanged (b16293228ae21e168d86bcf66aeae20351fc1fd4f8a735ccb77e324c72a5e8da)
   [PASS] encoding | expected: sub.o dbb word 0x40CC824A; bbd distinct | actual: 2 case(s) PASS | rc=0
   inject: PASS (injection FAILed encoding+lit; restore sha256 unchanged; green again)
   EXIT=0
   ```
   注入非空（`git -C .work/source/llvm-project diff --name-only` 非空）；还原后源码 sha256 一致、`git status --porcelain` 空、重建回绿。
8. **一键证据脚本**（验收 8）：`.work/evidence/LLVM-043t/run.sh`（非交互、任一失败非零退出、逐项打印检查名/期望/实际/rc、内置注入自检、结尾 `exit "$rc"` 无 `tee`）→ 正常模式 `RESULT: PASS (11 checks, 0 failures)`，`EXIT=0`。
9. **未越界**（验收 9）：`git status --short --untracked-files=all` 仅列 4 个改动文件（补丁、changelog、lit、oracle）+ 本任务书；无 `*_tmp*`/`*.orig`/`*.rej`；`.work/source/llvm-project` 干净且 `base..HEAD` count=1。

**新发现/坑**：

1. **任务书验收 2 的 `[0x40,0xBC,…]` 是笔误**：D9.1 定 `ha=0x33`，`value=op<<24|ha<<18=0x40CC0000`，第二字节为 **0xCC**（`0x33<<18=0xCC0000`）；真实 `llvm-mc` 输出 `[0x40,0xcc,0x82,0x4a]`，与 `opcodes.yaml` 的 `mask/value` 一致。已按单一真源落地（见完成区 2 的注）。
2. **反例注入的 `ha` 不能随便取**：`0x34` 是既有 `rb2rb`(orri) 的 opx，把 `sub_o_dbb` 的 `ha` 改成 0x34 会让 TableGen `-gen-disassembler` 直接报 `Decoding Conflict`（构建失败，而非「可构建的错误编码」）；注入改用空槽 `0x37`（MISC-octa `x111` reserved），可构建且编码变 `0x40dc824a`，从而干净地驱动 encoding/lit FAIL。
3. **`DADAOInstrInfo.td` 头部计数注释早已失准**：文件头 `// ... (178 instructions)`，实际仅 164 个 `def`（`generate_instrinfo.py` 已陈旧、非门控、与 `SPEC-101t` 改名后失同步）。本次未改该注释（越界，且改动它属另一任务）。`tools/llvm/validate_instrinfo.py` 的预存错误同属该陈旧生成器问题（`SPEC-100t`/`SPEC-101t` 已登记，非本次引入）。
4. **`components/<name>/changelog.md` 不在任务书 §输出 列名内，但 `spec/Process-01 §162` 强制要求「每次改动按任务一条追加」**；沿用 `LLVM-033t` 先例补一行（见「新发现 3」同类的越界披露）。

**遗留问题**：

- 无功能遗留。ISel pattern（`sub.o` 用于 M3 CodeGen 选择）**按任务明确归 `LLVM-035t`**，本任务 `.td` 保持 `Pattern=[]`（未加任何 `Pat<…>`/`SDNode`）。
- `DADAOInstrInfo.td` 头部「178 instructions」计数陈旧（见「新发现 3」）：非本次引入、非门控；建议由 `LLVM-046t`（instrinfo 生成器/校验器刷新）一并处理。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**（逐行）：`.work/source/.../DADAOInstrInfo.td`（+9）、导出的 `DADAOInstrInfo.td.patch`、`tests/lit/MC/Dadao/orrr.s`（+7）、`tools/llvm/test_encoding_oracle.py`（+3）、`components/llvm-project/changelog.md`（+1）、`.work/evidence/LLVM-043t/{run.sh,check_encoding.py}`。

**逐项审查**：

- **逻辑/编码正确性**：`sub_o_dbb` 的字段绑定为 `OutOperandList=(outs GPRD:$rb)`、`InOperandList=(ins GPRB:$rc,GPRB:$rd)`，经 `DADAOOrrr` 的 `let hb=rb/hc=rc/hd=rd` 落到 `[17:12]/[11:6]/[5:0]`；`op=0x40`/`ha=0x33` 与 `contracts/opcodes.yaml::sub.o_orrr_dbb` 逐字段一致（`value=0x40CC0000`）。实测 `sub.o rd8, rb9, rb10 → 0x40CC824A`，`&mask=0x40CC0000` ✅。
- **与既有形态不冲突**：与 `sub_o_bbd`(`ha=0x31`, dst rb) 同助记符但寄存器类不同（`(rb,rb,rd)` vs `(rd,rb,rb)`），汇编按类消歧、反汇编按 opx 消歧；实测 `sub.o rb8, rb9, rd10 → 0x40C4824A`（ha=0x31）仍正确（`check_encoding.py` 第二条断言，非回归）。无 TableGen 解码冲突（build EXIT=0）✅。
- **设计/惯用法**：def 紧邻同形参照 `cmp_uo_dbb` 放置并加注释指向 D9.1/LLVM-035t；未引入 `Pat`/`SDNode`；AsmMatcher/Decoder/AsmWriter 全由 TableGen 生成（无需手写 AsmParser 分支，同 `cmp.uo-dbb`）✅。
- **防造假**：完成区所有输出均为真实运行后 `cmd > log 2>&1; rc=$?` 捕获；日志落 `.work/log/llvm/`；注入自检真实重建、真实 FAIL、真实还原 ✅。
- **边界**：`sub.o rd8, rb9, rb10`（dbb）与 `sub.o rb8, rb9, rd10`（bbd）两形态均实测；反例注入覆盖「编码变更 + lit 变更」两条 FAIL 路径，且还原含重建 ✅。
- **越界**：仅 4 个仓库文件 + 组件源 1 文件；`changelog.md` 越出任务书列名（Process-01 §162 强制），已披露。

**findings 与处置**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | 反例注入首版改 `ha=0x34`，与 `rb2rb`(orri) 冲突致 TableGen `Decoding Conflict`、构建失败（二进制未变，encoding 检查误报 PASS） | ✅已修 | 注入点改空槽 `0x37`；并在 `rebuild_mc` 失败时显式报错并还原 | `run.sh --inject`：`inject: rebuild EXIT=0` → encoding `FAIL 0x40dc824a != 0x40cc824a` → lit FAIL → 还原回绿，`EXIT=0` |
| 2 | `run.sh` 注入路径只重建 `llvm-mc`，而 lit 的 OBJ 检查走 `llvm-objdump`（反汇编表同源） | ✅已修 | `rebuild_mc` 改 `ninja … llvm-mc llvm-objdump`；注入路径重建失败即停 | `run.sh --inject` lit `orrr.s rc=1`（预期 FAIL），还原重建后正常模式 `lit-mc 27/27` |
| 3 | 任务书验收 2 的 `[0x40,0xBC,…]` 与 D9.1 编码冲突 | ✅已修（以真源为准） | `.td`/lit/oracle 均按 `ha=0x33 ⇒ 0x40CC824A`；任务书注记笔误 | `llvm-mc` 真实输出 `[0x40,0xcc,0x82,0x4a]`；`check_lit_bytes 114`；oracle 122 |
| 4 | `.td` 头部「178 instructions」早已失准（实 164 def） | ⏸延后（越界） | 未改（非本次引入、非门控、属 LLVM-046t） | 已记「新发现 3 / 遗留 2」 |
| 5 | `changelog.md` 不在任务书 §输出 列名 | ✅已披露 | 按 Process-01 §162 追加一行 | `git status` 列该文件；`make check` 不受影响 |

**判决**：所有 finding 已处置或按依据披露，无未修项 → 状态置 `待验收`，交 reviewer 独立验收。

#### 第 1 轮 reviewer 验收

**证据脚本审核**：

`run.sh` 合格——逐项核验：
- 无恒真断言：每条 `record()` 均基于独立 rc 值，PASS/FAIL 路径分明
- 两条 FAIL 路径均可达：`check_encoding`（python rc≠0）与 `check_lit_mc`/`inject lit`（llvm-lit rc≠0）
- 注入点 `ha=0x37`（空槽）可构建、编码变为 `0x40dc824a`（≠`0x40cc824a`），不触发 TableGen Decoding Conflict
- 结尾 `exit "$rc"` 未被 tee 吞掉
- 注入后重建失败路径有显式 `restore_source` + `rebuild_mc`

`check_encoding.py` 合格——从 `contracts/opcodes.yaml` 独立派生期望字节（非硬编码回读 llvm-mc），dbb/bbd 两 case 期望字节不同（`0x40CC824A` vs `0x40C4824A`），FAIL 路径有3种独立触发条件（yaml 未找到/派生≠预期/编码≠派生）。

**独立重跑 run.sh**（正常模式）：

```
$ bash .work/evidence/LLVM-043t/run.sh > .work/log/llvm/LLVM-043t-reviewer-run1.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
```

逐项输出（`.work/log/llvm/LLVM-043t-reviewer-run1.log`）：

| # | 检查名 | 期望 | 实际 | rc |
|---|--------|------|------|----|
| 1 | mc-exists | executable .../llvm-mc | exists+exec | 0 |
| 2 | encoding | sub.o dbb word 0x40CC824A; bbd distinct | 2 case(s) PASS | 0 |
| 3 | roundtrip-objdump | objdump shows 40 cc 82 4a sub.o rd8, rb9, rb10 | match=yes | 0 |
| 4 | roundtrip-asm | llvm-mc -filetype=asm -> sub.o rd8, rb9, rb10 | match=yes | 0 |
| 5 | check-lit-bytes | 114 patterns OK | check_lit_bytes: 114 patterns OK | 0 |
| 6 | oracle | 122 passed, 0 failed | ok | 0 |
| 7 | lit-mc | 27/27 MC PASS | Passed: 27 (100.00%) | 0 |
| 8 | patch-def | exported patch has sub_o_dbb ha=0x33 | ok | 0 |
| 9 | check-patch-tree | make check-patch-tree rc=0 | rc=0 | 0 |
| 10 | check-source-state | make check-source-state rc=0 | rc=0 | 0 |
| 11 | check-lit | make check-lit rc=0 | rc=0 | 0 |

**RESULT: PASS (11 checks, 0 failures)**，`EXIT=0`。

**独立编码/往返验证**（不通过 engineer 脚本）：

```
$ echo "sub.o rd8, rb9, rb10" | .work/build/llvm/bin/llvm-mc --triple=dadao-unknown-elf -show-encoding
sub.o rd8, rb9, rb10                    ; encoding: [0x40,0xcc,0x82,0x4a]
EXIT=0

$ .work/build/llvm/bin/llvm-objdump -d --triple=dadao-unknown-elf /tmp/opencode/LLVM-043t-review/rt.o
       0: 40 cc 82 4a  sub.o rd8, rb9, rb10
OD_EXIT=0

$ python3 -c "op=0x40;ha=0x33;hb=8;hc=9;hd=10;word=(op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd;print(f'{word:#010x}')"
0x40cc824a    # & mask 0xFFFC0000 = 0x40CC0000 = value ✓
```

独立派生确认：`ha=0x33` → 第二字节 = `0x33<<2 >> 0` ... 实际计算 `0x33<<18 = 0xCC0000`，第二字节 = **0xCC**（非 task doc 的 0xBC）。

**bbd 非回归**：

```
$ echo "sub.o rb8, rb9, rd10" | .work/build/llvm/bin/llvm-mc --triple=dadao-unknown-elf -show-encoding
sub.o rb8, rb9, rd10                    ; encoding: [0x40,0xc4,0x82,0x4a]
EXIT=0
```

dbb=`0xCC` vs bbd=`0xC4`，两形态编码不重叠 ✓。

**独立注入反例**（不同于 engineer 的注入点）：

注入点：`tests/lit/MC/Dadao/orrr.s` 的 `; OBJ:` 期望字节 `cc` → `cb`（改 lit 期望值，无需重建）。

```
# 注入前备份
$ cp tests/lit/MC/Dadao/orrr.s /tmp/opencode/LLVM-043t-review/orrr.s.orig

# 注入：把 OBJ 行的 40 cc 82 4a 改为 40 cb 82 4a
# git diff --name-only 确认非空
$ git diff --name-only
tests/lit/MC/Dadao/orrr.s    ← 非空 ✓

# check_lit_bytes FAIL
$ python3 tools/llvm/check_lit_bytes.py > /tmp/.../check_lit_bytes-injected.log 2>&1; echo "EXIT=$?"
EXIT=1
# (KeyError: 'id' — OBJ 模式 cb 不匹配 opcodes.yaml 中的 cc)

# llvm-lit orrr.s FAIL
$ .work/build/llvm/bin/llvm-lit tests/lit/MC/Dadao/orrr.s > /tmp/.../lit-orrr-injected.log 2>&1; echo "EXIT=$?"
EXIT=1
# FAIL: DADAO-MC :: orrr.s

# 还原
$ cp /tmp/opencode/LLVM-043t-review/orrr.s.orig tests/lit/MC/Dadao/orrr.s
$ diff /tmp/opencode/LLVM-043t-review/orrr.s.orig tests/lit/MC/Dadao/orrr.s; echo "restore-diff=$?"
restore-diff=0    # 文件一致 ✓

# 还原后回绿
$ python3 tools/llvm/check_lit_bytes.py > /tmp/.../check_lit_bytes-restored.log 2>&1; echo "EXIT=$?"
EXIT=0
# check_lit_bytes: 114 patterns OK

$ .work/build/llvm/bin/llvm-lit tests/lit/MC/Dadao/orrr.s > /tmp/.../lit-orrr-restored.log 2>&1; echo "EXIT=$?"
EXIT=0
# PASS: DADAO-MC :: orrr.s (1 of 1)
```

注入→FAIL→还原（无需重建，源码级还原）→回绿，完整闭环 ✓。

**全量门控**：

| 命令 | 输出 | 退出码 |
|------|------|--------|
| `make check-patch-tree` | 2 component(s), 77 patches OK | 0 |
| `make check-source-state` | llvm-project: OK HEAD=3f02dc671ac3 count=1 clean=True | 0 |
| `make check` | Passed: 31 (100.00%) | 0 |
| `test_encoding_oracle.py` | 122 passed, 0 failed out of 122 tests | 0 |
| `check_lit_bytes.py` | 114 patterns OK | 0 |
| `llvm-lit MC/Dadao` | Passed: 27 (100.00%) | 0 |

**约束核验**：

| # | 约束 | 判定 |
|---|------|------|
| 1 | 只加 MC，不加 ISel：`Pattern=[]` | ✅ `.td` 确认 `let Pattern = [];`，无 `Pat<…>`/`SDNode` |
| 2 | 编码单一真源：op/ha 与 opcodes.yaml 一致 | ✅ `op=0x40`/`ha=0x33`/`value=0x40CC0000` 逐字段对齐 |
| 3 | AsmMatcher/Decoder 由 TableGen 生成 | ✅ 无需手写 AsmParser 分支（同 cmp.uo-dbb） |
| 4 | 补丁纪律：check-patch-tree 77 OK | ✅ |
| 5 | 不回归 MC lit：27/27 | ✅ |
| 6 | 不越界：仅 5 个文件改动 | ✅ 见下方越界判定 |
| 7 | 临时目录 /tmp/opencode/LLVM-043t/ | ✅ |

**披露判定**：

1. **任务书验收 2 的 `[0x40,0xBC,…]` 笔误**：engineer 已在完成区注记并以 opcodes.yaml 为单一真源，实际编码 `[0x40,0xcc,0x82,0x4a]`。**判定：非阻塞，但建议正式改正任务书验收 2 原文**（将 `0xBC` 改为 `0xCC`），避免后续 task 阅读时产生误导。工程师只加注未改原文，reviewer 建议在本轮收尾时一并改正。

2. **`.td` 头部「178 instructions」陈旧**：文件头注释 `// ... (178 instructions)` 实际仅 164 个 def。**判定：非阻塞**，非本次引入、非门控检查项，归 `LLVM-046t` 处理。

3. **`components/llvm-project/changelog.md` 越界**：任务书 §输出 未列此文件，但 `spec/Process-01 §162` 明文要求「`components/<name>/changelog.md`：记录每次改动，按任务一条，追加式」。**判定：必要、可接受**，属规范强制要求，非擅自扩展。

**判决：Accepted**

全部 11 项验收通过（独立重跑 EXIT=0）、编码独立派生一致、bbd 非回归、独立注入反例触发 FAIL→还原回绿、门控全绿（make check 31/31、check-patch-tree 77 OK）、无越界违规。验收标准逐条满足。
