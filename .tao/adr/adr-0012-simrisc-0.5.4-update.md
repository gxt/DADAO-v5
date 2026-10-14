# ADR-0012: SimRISC 0.5.3→0.5.4 规范更新

**状态**：Accepted（rev. 2026-09-30 D3.1 修订 + D5/D6/D7 新增；2026-10-14 新增 D10 并经用户逐条确认——**确认范围含 `D10`**，唯 `D10.6b`（`scope` 取值）**仍待用户确认**，见 `## 状态说明`）
**日期**：2026-09-27
**决策者**：用户

## 背景

SimRISC 0.5.3 的指令文档按寄存器类型分类（数据类/地址类/浮点类/系统类），与 `docs/assembly-list.md` 的按数据宽度/操作类型分类不一致。同时需要进行多项语义变更和字段结构调整。

## 决策

### D1：文档分类重组

将指令文档从 4 个文件（SimRISC-01~04）拆分为 12 个文件（SimRISC-01~12），按以下分类和顺序组织：

| 编号 | 分类 | 条数 |
|------|------|------|
| 01 | 取数存数 | 38 |
| 02 | 寄存器复制 | 18 |
| 03 | 16位立即数操作 | 8 |
| 04 | 64位数据运算 | 29 |
| 05 | 64位地址运算 | 4 |
| 06 | 控制流 | 15 |
| 07 | 浮点运算 | 44 |
| 08 | 32位数据运算 | 26 |
| 09 | 16位数据运算 | 26 |
| 10 | 8位数据运算 | 26 |
| 11 | 其它 | 6 |
| 12 | 待定 | 11 |

SimRISC-00（指令系统设计）保持独立，版本号更新为 0.5.4。

### D2：opcodes.yaml 字段调整

1. `insn` → `id`，格式 `mnemonic_format_feature`
2. orrr/orri/oiii 格式的 `ha`（opx）并入 `op`（14位）；其余格式 `ha` 保留为操作数
3. 所有立即数拆分（hi/lo/mid）合并为单个 field
4. ~~删除 `role` 字段（dst/src/imm）~~（2026-09-28 就地修订：`role` 字段已恢复——SPEC-024t 删除 `role` 导致 `validate_vectors.py` 的 F9① 守卫语义错误，把 orrr/orri 的 `hb` 误判为 src；用户裁定恢复。见 `SPEC-031t`。）

### D3：语义变更

1. ~~**st 类指令允许 0 号寄存器**：st/stm 的 rdha/rbha/raha 不再触发 ILLI（寄存器操作数都是读，没有写）~~（2026-09-30 就地修订：`st.*`/`stm.*` 的**源**为 `rd0`（读出 **0**）/ `rb0`（读出**当前指令的地址**，**非下一条**）→ **合法**，**不得** ILLI；**仅**「**目的**为 0 号寄存器」才触发 ILLI；`rb0` **可作访存基址**（`[rb0, imms12]` / `[rb0, rdHC]`）。依据：`SPEC-055t`、`QEMU-028t`、`TESTCASES-019t`）（2026-09-30 就地修订：**各寄存器组的 0 号寄存器都有专门的用途**：`rd0`（恒 0）、`rb0`（读出当前指令的地址）：**只读**。`rb0` 作**任何显式目的** → ILLI；`rd0` 作**目的** → ILLI，**例外**：① rrrr 双目的 `add.uo`/`add.so`/`sub.uo`/`sub.so`/`mul.uo`/`mul.so` 允许其中一个目的为 `rd0`（丢弃对应半结果），但**不能同时为 `rd0`**、也**不能为同一非 `rd0` 寄存器**；② `ret rd0, 0` 允许（无需设置返回值）。`rd0`/`rb0` 作**源**合法（`rd0` 读出 0、`rb0` 读出当前指令的地址）。`ra0`（`RACNT` + `MRPTR`，见 D7）、`rf0`（FCSR，位域与写语义见 D6）：**可读写**。依据：`SPEC-061t`、`ADR-0015`）
2. **寄存器复制不允许覆盖范围**：rd2rd/rb2rb 等块赋值指令，源范围与目的范围有任何交集即报 ILLI
3. **swym 编码修改**：格式从 iiii 改为 oiii，立即数从 immu24 改为 immu18
4. **删除 ftmadd/fomadd 指令**：从 QFC 表、opcodes.yaml、spec 文档中移除融合乘加指令（2条）
5. **`illi` 指令删除 + oiii 子表编码调整**（2026-10-06 就地增补；用户逐条确认）：① **删除 `illi` 指令**（`op=0x77, ha=0x00`）——**ILLI 异常保留**（由非法操作数/非法条件触发，**不再**有专门的 `illi` 指令）；② **`fence` 编码 `ha` 由 `0x01` 移至 `0x00`**：`value` `0x77040000` → **`0x77000000`**（`fence` 仍 `excluded`，见 `ADR-0014`）；③ **`swym` 编码 `ha` 由 `0x02` 移至 `0x22`**：`op=0x77` 不变，`value` `0x77080000` → **`0x77880000`**。**落地**：`spec/SimRISC-00/11` + `contract-isa §13` + `contract-asm §6` + `contracts/opcodes.yaml` + LLVM MC + QEMU `insn.decode`/`trans_ctrl` + `tests/vectors` + `ADR-0004`「全零字 UNDI」注 + crt0 `swym 0`。

### D4：spec/ 只读策略调整

0.5.3 中 spec/ 标注为只读。0.5.4 起调整为：**只有 spec 模块的任务才能修改 spec/ 下的文件**。

### D5：删除 `rela.si`（2026-09-30 新增）

- **`rela.si`（`riii`，`rbha, imms18`）→ UNDI**：编码 `0x5A` 保留但不再指派，执行触发 UNDI 异常。
- **影响**：指令总数 **254 → 253**；M1 身份集 **177 → 176**。
- **不预设替代方案**：PC 相对寻址改用 `rb0` 基址路径（见 D3.1），遇具体问题再议。
- **关联任务**：`SPEC-057t`（从 QFC 表、`opcodes.yaml`、spec 文档移除 `rela.si`）。

### D6：rf0（FCSR）位域调整与访问规则（2026-09-30 新增）

用户逐条确认 D6 第 1–7 条全部同意。

1. **位域调整**：舍入模式 `[17..16]` → `[33..32]`；SBZ 由 `[50..32]`/`[21..18]`/`[15..5]` 合并为 `[50..34]`、`[21..5]`；只读 qNaN 头 `[63..51]`/`[31..22]` 与异常 `[4..0]` 不变。每个 R/W 字段独占一个 wyde（wp0=异常、wp2=舍入、wp1/wp3 完全只读）。
2. **写入语义（rf0 作目的）**：允许 `rd2rf`（含 `{rf0:rf0+immu6-1}`）、`ld.o`/`ldm.o`、`ld.t`/`ldm.t`、`set.w rf0`；写只更新 `[33..32]` 与 `[4..0]`，其余位写无效、保持原值（含 `ld.t`/`ldm.t` 的 `[63:32]` 不变）。
3. **ILLI 边界**：仅「rf0 作**目的**」触发 ILLI —— SimRISC-07 浮点运算指令（家族 **44 条**；其中带 rf 目的字段者 **30 条**，加 `cs.eq`/`cs.ne`/`cs.n`/`cs.z`/`cs.p` 5 条 = **35 条**触发 ILLI；只读类 14 条无 rf 目的字段，不涉及）。
4. **读取语义（rf0 作源）**：合法（含 `ftsgnj`/`fosgnj` + `rfHD=rf0` 的 `abs()`、`rf2rd`、`st.*`/`stm.*`、`cs.*` 的 rf 源）。
5. **`SimRISC-00:90` 改写**：从「不应采用 rf0 作为普通的浮点寄存器参与运算」改为区分源/目的的新表述。
6. **合同修正**：`rf0_as_operand` → `rf0_as_dst`；并修头部计数（254→253，177→176）。
7. **复位值不变**：`0x7FF8_0000_7FC0_0000`。

### D7：RegRAS 有效性判据与 RAS 流程修订（2026-09-30 新增）

用户逐条确认 D7 第 1–7 条全部同意。

1. **`ra0` 位域**：`[63:54]` = SBZ（写无效；原 MemRAS 引用计数**取消**）；`[53:48]` = **`RACNT`**（RegRAS 有效条目数，0–63，初始 0）；`[47:0]` = **`MRPTR`**（**MemRAS 下一个待弹出条目（栈顶）的字节地址**，条目 8 字节、8 字节对齐；**`0` = 未启用 MemRAS**）。
2. **`ra1`–`ra63`（RegRAS，63 槽）**：`[63:48]` = **递归计数**、`[47:0]` = **返回地址**；**`ra63` 恒为栈顶**；**有效性判据 = `RACNT`**（**不**看条目自身的值）——**有效条目 = 自 `ra63` 起向下连续 `RACNT` 个**（第 k 新 = `ra[64−k]`，栈底（最旧）= `ra[64−RACNT]`）；有效区之外的 `ra_i` 内容未定义（不参与栈语义；复位后全 0）。
3. **压栈（`call`）**：
   - **C1** `RACNT == 0` → 压入新条目（递归计数 = 1、返回地址），`RACNT = 1`；
   - **C2** `RACNT > 0` 且 返回地址 == `ra63[47:0]`（栈顶返回地址）且 `ra63[63:48] < 0xFFFF` → **递归折叠优先**：`ra63[63:48] += 1`，`RACNT` 不变；
   - **C3** 其余：**C3a** `RACNT < 63` → 压入新条目（递归计数 = 1），`RACNT += 1`；**C3b** `RACNT == 63` → ① `MRPTR == 0` → **RASOF**；② `MRPTR −= 8` 并把**栈底（最旧）条目**（`ra[64−RACNT]`）写入 `MRPTR` 处；③ 压入新条目 ⇒ **出栈底一条、入栈顶一条，`RACNT` 保持 63**。
4. **弹栈（`ret`）**：**D1** `RACNT > 0` 且 `ra63[63:48] == 0` → **RASUF**；**D2** `RACNT > 0` 且 `ra63[63:48] > 1` → 计数 −1，`RACNT` 不变；**D3** `RACNT > 0` 且 `ra63[63:48] == 1` → 弹出栈顶，`RACNT −1`；**D4** `RACNT == 0` → **D4a** `MRPTR == 0` → **RASUF**；**D4b** 读 `MRPTR` 处条目并作判定（`MRPTR` 暂不修改）：递归计数 = 0 → **RASUF**、= 1 → 返回地址 = 条目低 48 且 `MRPTR += 8`、> 1 → 该条目压入成为栈顶（计数 −1）且 `MRPTR += 8`、`RACNT = 1`。
5. **实现注（非架构语义）**：实现可用**环形缓冲 + 隐藏基准索引**避免压栈/弹栈时的数据搬移；`ra_i` 为软件可见（`ld.o-ra`/`st.o-ra`/`rd2ra`/`ra2rd`），访问须按基准索引换算以与架构视图一致。
6. **精确异常**：压栈/弹栈**先完成全部 `RASOF`/`RASUF` 判定**（含 D4b 的 MemRAS 条目**读取与内容判定**），判定通过后才进行 RA 寄存器或 MemRAS 访存的任何修改；异常时 RA 寄存器与内存均保持原状。
7. **影响**：M1 已验收的 RA 语义被**推翻**（`trans_ctrl.c.inc` 的 `gen_ras_push`/`gen_ras_pop`、`ctrl-call.yaml`/`ctrl-ret.yaml` 及其生成器 `tools/testcases/generate_ctrl_jump_call_ret.py`、探针 `008t`/`012t`/`013t`）；**复位值不变**（`ra0 = 0` ⇒ `RACNT = 0`、`MRPTR = 0`）；**无 MemRAS 引用计数**，MemRAS 越界（容量耗尽）不由硬件检测（交 OS）。`docs/m1-retrospective.md` 为历史记录，**不改写**。

### D8：RB / 控制流 地址语义澄清（2026-10-02 新增）

**引用**：`SimRISC-00 §基址寄存器/§返回地址栈`、`SimRISC-05 §比较`、`SimRISC-06 §控制流`、`contract-isa`、`QEMU trans_mem/trans_compare/trans_ctrl`

- **D8.1（RB 高 16 位语义，澄清）**：RB 为 64 位全宽；`load`/`store`、复制（`rd2rb`/`rb2rb`）、立即数赋值（`set.zw-rb`/`or.w-rb`/`andn.w-rb`，允许 `wp3`）、`ldm`/`stm` 均**整 64 位**操作（`bits[63:48]` 正常读写）；**不存在**"存取/复制保持高 16 不变"的语义。
- **D8.2（RB 的判断/比较 = 整 64 位；2026-10-02 就地修订）**：**`cmp.uo-rb` 对操作数整 64 位做无符号比较**（结果 −1/0/1）；**`br.z-rb`/`br.nz-rb` 条件亦按整 64 位判零**。理由：RB 是 64 位寄存器、其高 16 为**合法内容**（D8.1），且**判断/比较不是"地址使用"**（48 位截断只发生在地址总线使用，见 D8.7）。`cmp.uo`（RD 数据变体）同为 64 位无符号；`cmp.so` 不变。⇒ **RB 的 cmp/br 均不截 48**（高 16 意外非 0 时按 64 位**暴露**，而非隐藏）。
- **D8.3（控制流地址计算，`br.*`/`jump`/`call`）**：`rb0` 为 **64 位**并**以 64 位参与运算**；**不假定其高 16 位为 0**（可为前一次地址回绕保留下来的值）。计算结果（64 位）**写回 `rb0`**。**CPU 发出的地址总线只有 48 位** ⇒ **凡将地址用于取指、访存有效地址、跳转目标，一律取低 48 位**；**`rb0[63:48]` 保留计算结果的高 16**（**当结果跨出 48 位地址空间时即进位**），并作为 64 位值**参与后续运算**（供溢出检测）。计算式：**iiii** = `rb0 + (immsN<<2)`；**rrii** = `rbHA + rdHB + (imms12<<2)`（`rbHA` **仅读**）；顺序 / not-taken = `rb0 + 4`。**两种格式都写 `rb0`**；**rrii 的 `rbHA` 不修改**。**不含 `ret`**（见 D8.5）。
- **D8.4（`rb0` 只读的含义）**：`rb0` 不可作**显式目的寄存器**（`[47:0]`/`[63:48]` 皆然；**`rwii` 类不得以 `rb0` 作 `rbHA`**）——该描述**保持**；「`rb0[63:48]` **恒为 0**」**作废**（初值 0；由 D8.3 的硬件写入）。
- **D8.5（文档归位）**：**`ret`** 的返回地址来源（**可能不是 `ra63`**，取决于 RAS 状态）及可能引发的异常（如 **RASUF**）**统一在 §返回地址栈 描述**；`ra2rd`/`rd2ra` 说明归入 §返回地址栈；`call`/`ret` 在 §基址寄存器 与 §返回地址栈 **两节均列**；RA 高 16（`RACNT`/递归计数）**统一记述于 §返回地址栈**。
- **D8.6（同步面）**：`spec/SimRISC-00`、`spec/SimRISC-05`、`spec/SimRISC-06`、`contract-isa`、**QEMU**（`trans_cmp_uo_orrr_rb` **与本文件其余 RB 比较一致（不截 48）**；`trans_ctrl` 改 64 位地址并**写回 `rb0`**）、**向量**（`cmp.uo-rb` / `ctrl-*` 期望值）。

- **D8.7（一般原则，2026-10-02 用户确认）**：**所有 RB 寄存器（`rb0`–`rb63`）与 RA 寄存器（`ra0`–`ra63`）均为 64 位**；**凡其值被用作地址（取指 / 访存有效地址 / 跳转目标 / 返回地址）时，一律取低 48 位**（CPU 地址总线 48 位）；其高 16 位为**寄存器自身内容**——RB 为普通 64 位值（见 D8.1），RA 为递归计数 / `RACNT` / `MRPTR` 等（见 §返回地址栈 / D7）。该原则与「寄存器 64 位、地址运算 64 位」**不冲突**。

**备选（否决）**：
- R1：沿用"存取/复制保持高 16 不变" → 与实测/实现不符；否决。
- R2：`cmp.uo`（RD 变体）也改 48 位 → 超范围（用户选 (a)）；否决。
- R3：把 `ret` 并入 D8.3 控制流地址计算 → `ret` 来源/异常属 RAS；否决。

### D9：新增 `sub.o`（RB − RB → RD）与 RB 算术指令 id/编码槽重整（2026-10-04 新增）

**用户 2026-10-04 逐条确认追加。** 背景：M3 CodeGen 需 `ptr−ptr`（`ADR-0018 C14 D4`、`ISS-130`）；同时把 orrr 单目的指令 id 后缀统一为**操作数 bank 签名**约定。

**D9.1（新增指令）**

- `id = sub.o_orrr_dbb`，助记符 `sub.o`，格式 `orrr`。
- 字段：`rdhb`(dst,rd)[17:12]、`rbhc`(src,rb)[11:6]、`rbhd`(src,rb)[5:0]（同 `cmp.uo`）。
- 编码：`op=0x40`、`ha=0x33`、`mask=0xFFFC0000`、`value=0x40CC0000`。
  - ✅ **算术修正（用户 2026-10-04 已确认）**：原裁定笔误写 `value=0x40C00000`（该 `ha` 实为 `0x30`）；按 `value = op<<24 | ha<<18` 定为 **`ha=0x33 ⇒ value=0x40CC0000`**，已确认。
- 语义：`rd = rb − rb`（二进制补码 64 位减法，全 64 位参与；结果按有符号差值解释）。**单条、无 `.s`/`.u` 变体**——64 位单目的加减的结果位型与符号性无关。
- legality：复用 `dst_rd0`（`rdhb != rd0` → ILLI）；`rb0` 作**源**合法。
- `scope = m3`（归属里程碑；**非** M1 身份，不要求 M1 向量覆盖）。

**D9.2（三条既有指令改名 + 改编码槽）**：op 保持 `0x40`，mask `0xFFFC0000`。

| 旧 id | 新 id | 新 mnemonic | 旧 ha | 新 ha | value |
|---|---|---|---|---|---|
| `add.so_orrr_rb` | `add.o_orrr_bbd` | `add.o` | `0x20` | `0x30` | `0x40C00000` |
| `sub.so_orrr_rb` | `sub.o_orrr_bbd` | `sub.o` | `0x28` | `0x31` | `0x40C40000` |
| `cmp.uo_orrr_rb` | `cmp.uo_orrr_dbb` | `cmp.uo`（名不变） | `0x29` | `0x32` | `0x40C80000` |

**D9.3（id 后缀约定）**：orrr 单目的指令 id 后缀 = **操作数 bank 签名**（`b`=rb、`d`=rd），按字段顺序（dst 在前）：`bbd`=(rb dst, rb, rd)；`dbb`=(rd dst, rb, rb)。本 ADR **仅**对 D9.1/D9.2 的 4 条应用；其它既有 id（如 `cmp.uo_orrr_rd`、`add.si_riii_rb`）**不**在本次改名范围（如需全局迁移另立任务）。

**D9.4（并存的同名/近名形态）**：
- `add.o`/`sub.o`（orrr，rb 目的，`bbd`）与 **rrrr 双目的** `add.so`/`sub.so`（rd 双目的）**并存**（助记符不同）。
- `sub.o`（orrr）同时有 `bbd`（`sub.o_orrr_bbd`，rb 目的）与 `dbb`（`sub.o_orrr_dbb`，rd 目的）两种操作数形态，由汇编器按寄存器类区分（同 `cmp.uo` 的 `dbb`/`rd` 两形态）。

**D9.5（计数影响）**：新增 1 条（`scope: m3`）⇒ `contracts/opcodes.yaml` **227→228**；**M1 身份数不变（152）**；`tools/spec/check_scope.py` 须纳入 `m3`（`ALLOWED_SCOPES`、计数 `m3=1`/`total=228`）。

**D9.6（同步面）**：`spec/SimRISC-00` QFC `MISC-octa` 子表 + `spec/SimRISC-05` 正文/计数；`contracts/opcodes.yaml`（生成器 `tools/spec/generate_opcodes.py`）；`.tao/knowledge/contract-isa.md`、`contract-asm-list.md`；`tests/vectors/{reg-arith,reg-compare}.yaml` + `inventory.md` + `tools/testcases/generate_isa_vectors.py`；MC（`DADAOInstrInfo.td` mnemonic/def、`DADAOAsmParser`/`DADAOInstPrinter`/decode）；QEMU（`insn.decode` token + `trans_*` 函数名）；`tools/qemu/check_005t_coverage.py`。D8.6 中 `trans_cmp_uo_orrr_rb` 的引用由本 D9 更名（`trans_cmp_uo_orrr_dbb`）**取代**；**D8.6 原文不改写**。

**备选（否决）**：
- R1：新指令沿用 `sub.so` 名 → 与既有 `sub.so_orrr_rb` 重名/重 id、易混；否决。
- R2：`sub.so`+`sub.uo` 两变体 → 结果位型一致、冗余；否决。
- R3：新指令保留 `scope: m1` → 用户裁定归 `m3`、不要求 M1 向量覆盖；否决。

**关联任务**：`SPEC-100t`（新增指令）、`SPEC-101t`（三条既有指令改名+改编码）、`LLVM-043t`（新指令 MC）、`QEMU-040t`（新指令 trans）、`LLVM-035t`（ISel）。

### D10：新增 `rev.{o,t,w,b}`（逐块反转）——**（2026-10-14 新增；用户逐条确认 ✓）**

> **确认状态**：`D10` 及其子项 `D10.1`–`D10.8` 已经用户 **2026-10-14 逐条确认**（原话见 `D10.0` 与 `§状态说明`）⇒ **视为 `Accepted`**；本 ADR 顶部 `**状态**：Accepted` 的确认范围**含 `D10`**。**唯 `D10.6b`（`scope` 取值）仍待用户确认**（见下），确认前不得写其 `scope`。

**D10.0（授权与用户裁定原话，原样引录；渠道 = 经主会话问答，2026-10-14）**

- **授权**：用户原话「**a/b授权**」——即授权修改**本 ADR** ✓ 且授权修改 **`spec/SimRISC-00` + `contracts/opcodes.yaml` + `contracts/legality_rules.yaml`** ✓（满足 `docs/Process-06 §2`「`spec/` 下任何新增/修改须用户事先明确允许」✓）。
- **设计确认（Q1/Q3/Q4）**：
  - Q1（`immu6` 语义 = **单元序反转、单元内位序不变**）⇒ 用户原话：「**前者，你的理解很正确**」。
  - Q3（非法 `immu6` 的异常与规则落点）⇒ 用户原话：「**ILLI；需要增加 `encode_onehot` 合法性规则，配合 `encode_sbz` 合法性规则；此外，还有 `dst_rd0`**」。
  - Q4（零寄存器 / 同寄存器边界）⇒ 用户原话：「**`rdHC` 可以为 `rd0`，`rdHB` 可以和 `rdHC` 是同一个寄存器**」。
- **语义（Q2 最终确认）** ⇒ 用户原话：「**按 `t/w/b` 做划分……以 `w` 为例，每个 64 位寄存器，划分为四个 `w`，如果 `immu6` 为 4，每个 `w` 内部的 4 个 4 位进行翻转；所以，如果 `rdHC` 高 48 位为 0，则 `rdHB` 的高 48 位也为 0，否则，也进行类似运算**」⇒ **逐块语义**。

**D10.1（新增指令）**

- 新增 **4 条**：`rev.o` / `rev.t` / `rev.w` / `rev.b`，格式统一为 **`orri`**。
- 操作数：`rdhb`（**目的**，`hb[5:0]` = bits`[17:12]`，bank `rd`）、`rdhc`（**源**，`hc[5:0]` = bits`[11:6]`，bank `rd`）、`immu6`（bits`[5:0]`，**无符号**）。
- id 沿用既有 `mnemonic_format_feature` 约定（`orri` 变体如 `shl.ub_orri_rd`/`ext.uo_orri_rd`）：`rev.o_orri_rd` / `rev.t_orri_rd` / `rev.w_orri_rd` / `rev.b_orri_rd`。
- `ha` 为 `opx`（见 D10.2），故不在操作数之列。

**D10.2（编码位置）**

`opx = 001100`（即 `ha[5:0] = 0b001100 = 0x0C`；行 `001-xxx` × 列 `xxx-100`），四子表**各一条**：

| 指令 | 子表 | `op` | `ha` | `mask` | `value` |
|---|---|---|---|---|---|
| `rev.o_orri_rd` | `MISC-octa`（`§4.2`） | `0x40` | `0x0C` | `0xFFFC0000` | `0x400C0000` |
| `rev.t_orri_rd` | `MISC-tetra`（`§4.3`） | `0x41` | `0x0C` | `0xFFFC0000` | `0x410C0000` |
| `rev.w_orri_rd` | `MISC-wyde`（`§4.4`） | `0x42` | `0x0C` | `0xFFFC0000` | `0x420C0000` |
| `rev.b_orri_rd` | `MISC-byte`（`§4.5`） | `0x43` | `0x0C` | `0xFFFC0000` | `0x430C0000` |

- `value = op<<24 | ha<<18`；`ha` 布局 = 行 `ha[5:3]` × 列 `ha[2:0]`（实证：`and.o` 行`001`列`000` ⇒ `ha=0x08`、`value=0x40200000`；`add.o` 行`110`列`000` ⇒ `ha=0x30`、`value=0x40C00000`）。
- **为何不冲突**（2026-10-14 现场核对）：① `001-100` 在四个子表**均为空**（`spec/SimRISC-00 §4.2–§4.5` 第 5 列全空）；② `SPEC-069t` 的 reserved / 已删条目集 = 每子表 **8 条** = `001-000…011`（4 逻辑）+ `010-000/001` 与 `011-000/001`（2 ext × 2 格式），**不含 `001-100`**；③ `contracts/opcodes.yaml` 中**无任何** `ha: '0x0C'` 或形如 `0x??0C0000` 的条目（现场 `grep` **0 命中**）。
- 四条均为 `orri`（`opx` + 两个寄存器 + 6 位立即数在 `hd[5:0]`），与 `§3.1` 的 `orri` 定义一致。

**D10.3（语义：逐块）**

- 后缀 ⇒ **块大小 `S`**：`.o`=64、`.t`=32、`.w`=16、`.b`=8。
- 每个 64 位寄存器 ⇒ **`64/S` 个块**：`.o` 1 块、`.t` 2 块、`.w` 4 块、`.b` 8 块。
- `immu6 = k` ⇒ **每块内部**按 `k` 位切分为 `S/k` 个**单元**，**反转单元顺序**；**单元内部的位序不变**。
- **所有块一律同样处理**：不存在"范围之外的更高位保持原值 / 清零"的情形（即 `.t` 的两个 32 位块都做、`.w` 的四个 16 位块都做、`.b` 的八个 8 位块都做）。
- 伪代码：`for i in 0..(64/S)−1: out_block[i] = 把 in_block[i] 的 S/k 个 k 位单元按下标倒序拼接`（单元内位序保持）。
- 例（用户原话场景）：`.w` + `k=4` ⇒ 每个 16 位块切成 4 个 4 位单元，块内这 4 个单元**顺序翻转**；故若 `rdHC[63:16] == 0`，则 `rdHB[63:16] == 0`。

**D10.4（`immu6` = one-hot）**

| 后缀 | `S` | 块数 `64/S` | 合法 `k`（`immu6`） |
|---|---|---|---|
| `.o` | 64 | 1 | `{1, 2, 4, 8, 16, 32}` |
| `.t` | 32 | 2 | `{1, 2, 4, 8, 16}` |
| `.w` | 16 | 4 | `{1, 2, 4, 8}` |
| `.b` | 8 | 8 | `{1, 2, 4}` |

- 判据：`k` 必须为 **2 的幂（one-hot）且 `k < S`**（即 `k ∈ {S/2, S/4, …, 1}`）；**排除 `k = S` 的恒等档**。
- **非 one-hot（`0`、`3`、`5`、`6`、…、`63`）或 `k ≥ S`（越范围）⇒ `ILLI`**。

**D10.5（合法性规则）**

- 新增规则 **`encode_onehot`**，写入 `contracts/legality_rules.yaml`，**与 `encode_sbz` 并列**（同属"字段编码合法性"类；`fault: ILLI`、`kind: static`）。
- 四条指令 `rule_refs = ['dst_rd0', 'encode_onehot']`；`legality` 表达式 = `rdhb != rd0` + 该后缀的 one-hot 约束。
- **`rdHC` 可为 `rd0`**（源，合法；读出 0 ⇒ 结果为 0），**不**触发 ILLI（`dst_rd0` 只约束**目的**）。
- **`rdHB == rdHC` 允许**（源与目的为同一寄存器，原地反转），**不**触发 ILLI。
- 参照先例：`shl.ub_orri_rd` = `rule_refs: [dst_rd0, encode_sbz]` + `legality: [rdhb != rd0, immu6 <= 7]`（`contracts/opcodes.yaml` 现场）。

**D10.6（同步面；照 D9.6 形式逐项列）**

1. `spec/SimRISC-00`：QFC 四子表（`§4.2 MISC-octa`／`§4.3 MISC-tetra`／`§4.4 MISC-wyde`／`§4.5 MISC-byte`）各补 `xxx-100` 列一条 + 相关**计数**（如子表条数）+ 文末 changelog。
2. **`rev` 正文分册归位**：**已定案 (b) 分册**（用户 2026-10-14 裁定原话「1、分册写」，见 `D10.6a`）。
3. `spec/SimRISC-0x` 各册 **`LEGALITY` 生成区**（`tools/spec/gen_legality_list.py --apply`，随归位落定）。
4. `contracts/opcodes.yaml`（生成器 `tools/spec/generate_opcodes.py`）；**含 `scope` 取值与总数——待用户确认**，见 `D10.6b`。
5. `contracts/legality_rules.yaml`（新增 `encode_onehot`）。
6. `.tao/knowledge/contract-isa.md`（QFC/编码表 + 语义 + 合法集）、`contract-asm-list.md`（生成投影，`tools/llvm/gen_asm_list.py`）。
7. `tests/vectors/**` + `tests/vectors/inventory.md` + `tools/testcases/generate_isa_vectors.py`（**注**：`inventory.md` 的 M1 矩阵由 `validate_vectors.py` 与 `scope == "m1"` 集合**机械对齐** ⇒ 若 `rev` 非 `m1` 则**不入 M1 矩阵**，向量落独立文件）。
8. **MC**：`DADAOInstrInfo.td`（def / mnemonic）、`DADAOAsmParser`（`orri` 受理）、`DADAOInstPrinter`、`MCCodeEmitter`/decode、`DADAOMCInstLower`（如需）。
9. **QEMU**：`insn.decode`（四条 token）+ `trans_rev.c.inc`（`trans_rev_o`/`_t`/`_w`/`_b`）+ `translate.c` 分派 + `helper.c`（如需）。
10. **门控**：L1（`validate-encoding`／`check-scope`／`check-rule-refs`／`check-instrinfo`／`check-isa-coverage`／`check-asm-list-drift`／`check-legality-drift`／`check-legality-invariants`／`check-spec-readonly` 等）+ L2/L3。

**D10.6a（`rev` 正文分册归位——**定案 = (b) 分册**）**

- **定案 (b)**（用户 2026-10-14 裁定，原话「**1、分册写**」；渠道 = 经主会话问答）：按既有后缀约定**分册**（`.o`→`spec/SimRISC-04`、`.t`→`08`、`.w`→`09`、`.b`→`10`），逐块语义**总述置于 `04 §4.2`**、其余三册（`08/09/10`）**引用**。
- **已否 (a)**：四条同归 `04 §4.2`（一处写全）——**不采用**（用户裁定分册写）。
- **现场**（判据溯源，非定案依据）：`spec/SimRISC-04 §4.2「Bit manipulating：位操作指令」`已承载 `shl.uo`/`shr.uo`/`ext.uo` 与 `§4.1` 的 `and.o`/`or.o`/`xor.o`/`xnor.o`；窄位宽分册（`SimRISC-08/09/10`）按后缀 `t/w/b` 承载且口径为"值语义写满 64 位"。

**D10.6b（`scope` 取值——待用户确认）**

- `contracts/opcodes.yaml` 每条须带 `scope`（现允许 `m1`/`fp`/`excluded`/`m3`，见 `tools/spec/check_scope.py`）。
- `rev` **非 M1 身份**；建议 **`scope: m8`**（仿 `scope: m3` 先例：新增非 M1 指令自成一档），须同步 `check_scope.py` 的 `ALLOWED_SCOPES` + 分区计数 + 注释，及 `generate_opcodes.py` 的 scope 说明。**本项待用户确认，确认前不得写入 `opcodes.yaml` / `check_scope.py`。**

**D10.7（用途 / 映射）**

- **`bswap`**：`bswap16` = `rev.w` + `k=8`；`bswap32` = `rev.t` + `k=8`；`bswap64` = `rev.o` + `k=8`。**前提：源的高 `(64−S)` 位为 0**（否则其余块也被逐字节反转）⇒ **列为后端待核实项**（`__bswapsi2`/`__bswapdi2` 接入时须核该前提是否成立；见 `INFRA-079t`、`ISS-193`(c)）。
- **位反转**：`bitreverse` = `rev.o` + `k=1`（整 64 位位序反转）。**`rev.t` + `k=1` ≠ 64 位全位反序**（只在**每个 32 位块内**反转）、`rev.w` + `k=1` 同理（**每个 16 位块内**）⇒ **须在正文写明以防误用**。
- 上述映射**各只需一条指令**（对比 ARM `REV*`/`RBIT`、RISC-V `rev8` 等需 2 条组合）。

**D10.8（被否方案）**

- **R1**：为 `k = S`（恒等档：块内仅 1 个单元，反转即自身）分配编码 ⇒ **不分配**。理由：恒等无语义价值，且收窄合法集能把编码错误暴露为 `ILLI`。
- **R2**：「仅低 N 位反转 + 高位保持 / 清零」的窄位宽语义 ⇒ **被逐块语义取代**。理由：① 无需读目的寄存器（纯 `src → dst`）；② 无"块大小 × 高位数"的边界情形；③ 与主流逐块做法（ARM `REV` 系列按定宽单位反转）一致。

**关联任务**：`SPEC-142t`（`rev.{o,t,w,b}` 落地，**前置 = `D10` 逐条确认 ✓ 已完成；唯 `D10.6b` 仍待确认**）——**已确认，可实现 / 下发**。

### D11：新增 `ctlz` / `cttz` / `ctpop`（位扫描与计数）——**（2026-10-14 新增；提案，待用户逐条确认 ✗）**

> **确认状态**：`D11` 及其子项 `D11.1`–`D11.10` **均为提案**，尚未经用户逐条确认 ⇒ **不得视为 `Accepted`**；本 ADR 顶部 `**状态**：Accepted` 的确认范围**不含 `D11`**（照 `D10` 提案期先例：顶部 `**状态**` 行**待逐条确认后**再更新）。**显式待确认项**：`D11.4`（`cttz` 的 `hd` 语义）、`D11.9`（正文分册归位、`scope` 取值）、**`spec/` 修改授权**（`docs/Process-06 §2`；须在任务书中留存授权原话）。

**D11.0（用户裁定原话，原样引录；渠道 = 经主会话问答，2026-10-14）**

- **指令名**：用户原话「**ctlz/cttz/ctpop**」。
- **范围**：用户原话「**先就这三个吧**」⇒ `cls`/`clo`/`cto`/`parity`/`ffs`/`ffz` 等**首版不做**（判据见 `D11.10(c)`）。
- **编码**：用户原话「**ctlz/cttz/ctpop 的 opx：011-110/011-111/011-101**」。
- **前序已接受（渠道同）**：① **定值** = `ctlz(0)`/`cttz(0)` 返回**范围宽度（`hd+1`）**；② **不新增** `encode_onehot`；③ **不带位宽后缀**（编码借 `MISC-octa` 格位）；④ `cttz` 的 `hd` 语义「**保持 `[hd:0]` 上界**」= **主会话建议、用户未反对 ⇒ 仍标「待确认」**（见 `D11.4`）。

**D11.1（新增指令）**

- 新增 **3 条**：`ctlz` / `cttz` / `ctpop`，格式统一为 **`orri`**。
- 操作数：`rdHB`（**目的**，`hb[5:0]` = bits`[17:12]`，bank `rd`）、`rdHC`（**源**，`hc[5:0]` = bits`[11:6]`，bank `rd`）、`hd`（bits`[5:0]`，**无符号立即数**，**有效位上界**，见 `D11.4`）。
  - **注**：`hd` 是格式定义中「6 位立即数在 `hd[5:0]`」的域；`contracts/opcodes.yaml` 中该字段名惯用 **`immu6`**（`role: imm`、`bank: imm`、`signed: false`），现场先例 `ext.uo_orri_rd`。
- id 沿用既有 `mnemonic_format_feature` 约定（`orri` 变体如 `ext.uo_orri_rd`）：**`ctlz_orri_rd`** / **`cttz_orri_rd`** / **`ctpop_orri_rd`**。
- `ha` 为 `opx`（见 `D11.2`），故不在操作数之列。
- 汇编语法（`spec/Toolchain-01 §5` 的 `orri` 行 = `助记符 dst, src, immu6`）：`ctlz rdHB, rdHC, hd`（例：`ctlz rd8, rd9, 63`）⇒ `ctlz` 即 `clz64`、`ctlz rd8, rd9, 7` 即 `clz8`。

**D11.2（编码位置）**

`opx` = 行 `011-xxx` × 列 `xxx-101/110/111`；主 op = **`0x40`**（`MISC-octa` 子表）：

| 指令 | `id` | 子表 | `op` | `opx` | `mask` | `value` |
|---|---|---|---|---|---|---|
| `ctpop` | `ctpop_orri_rd` | `MISC-octa`（`§4.2`） | `0x40` | `011-101`（`0x1D` = 29） | `0xFFFC0000` | `0x40740000` |
| `ctlz` | `ctlz_orri_rd` | `MISC-octa`（`§4.2`） | `0x40` | `011-110`（`0x1E` = 30） | `0xFFFC0000` | `0x40780000` |
| `cttz` | `cttz_orri_rd` | `MISC-octa`（`§4.2`） | `0x40` | `011-111`（`0x1F` = 31） | `0xFFFC0000` | `0x407C0000` |

- `opx` 在 `bits[23:18]`（= `ha`），`value = op<<24 | opx<<18`；`mask = 0xFFFC0000`（锁 `op` + `opx`）。
- **为何不冲突**（2026-10-14 现场核对，三条实证）：
  1. `spec/SimRISC-00 §4.2 MISC-octa` 第 `011-xxx` 行**仅** `000`–`100` 有条目（`ext.uo`/`ext.so`/`shr.uo`/`shr.so`/`shl.uo`），`101`/`110`/`111` **三格为空**（= reserved）；
  2. `SPEC-069t` 的 reserved / 已删条目集 = 每子表 **8 条** = `001-000…011`（4 逻辑）+ `010-000/001` 与 `011-000/001`（2 ext × 2 格式）⇒ **不含 `011-101/110/111`**；
  3. `contracts/opcodes.yaml` 中 `op: '0x40'` 的 **32** 条，`ha`（十进制）集合 = `{8–11, 16–20, 24–28, 42–46, 48–54, 56–59, 61–62}`（现场统计）⇒ **`29`/`30`/`31` 无条目**；且 `0x40740000`/`0x40780000`/`0x407C0000` 全文**0 命中**。
- 三条均为 `orri`（`opx` + 两个寄存器 + 6 位立即数在 `hd[5:0]`），与 `§3.1` 的 `orri` 定义一致。

**D11.3（无位宽后缀）**

- 三条**不带** `.b`/`.w`/`.t`/`.o` 后缀：`hd`（`0..63`）**已覆盖全部宽度**（`D11.4`）⇒ 加后缀只会**丢掉"任意宽度"**且无谓扩充编码（见 `D11.10(a)`）。
- 三条因此**借 `MISC-octa` 格位**（`D11.2`）。
- **既有先例（现场）**：`MISC-octa` 中 **已存在 8 条无位宽后缀**的指令——`rd2rd` / `rd2ra` / `ra2rd` / `rb2rb` / `rd2rb` / `rb2rd` / `rd2rf` / `rf2rd`（`id`/`mnemonic` 均无后缀）⇒ 「**子表 ⇔ 位宽后缀**」**并非无例外**。
- 仍**须在 `spec/SimRISC-00` 明确一句例外 / 澄清**（"位宽后缀规则的例外"，见 `D11.9` 第 1 项）。

**D11.4（语义：`hd` = 有效位上界，三者统一；⚠ `cttz` 待确认）**

- **有效位** = `rdHC[hd:0]`（共 **`hd+1`** 位，`hd ∈ 0..63`）；`hd` 以上的位**不参与**运算。
- `ctlz`：从 bit `hd` **向下**数前导零（到首个 1 为止）⇒ 结果 = 有效位内的前导零个数。伪代码：`n=0; for i = hd down to 0: if bit(i)==1 break; n++`。
- `cttz`：从 bit 0 **向上**数末尾零（到 bit `hd` 为止）⇒ 结果 = 有效位内的末尾零个数。伪代码：`n=0; for i = 0 up to hd: if bit(i)==1 break; n++`。
- `ctpop`：`rdHC[hd:0]` 内 **1 的个数**（∈ `0..hd+1`）。
- 三者**全 0 / 无 1** 时的结果见 `D11.5`。
- **⚠ 待用户确认**：`cttz` 的 `hd` 作 **上界**（`[hd:0]`）系**主会话建议、用户未反对**（见 `D11.0` 前序④）——**未经明示确认**；备选「下界」语义见 `D11.10(b)`。

**D11.5（定值：全 0 / 无 1）**

- `rdHC[hd:0]` **全 0** 时：`ctlz` = `cttz` = **`hd+1`**（= 有效位范围宽度，**消除 UB**）。
- 口径一致（现场对照）：RISC-V（`clz`/`ctz` 对 0 返回 XLEN）、x86（`lzcnt`/`tzcnt` 返回操作数宽度）、ARM（`CLZ(0)` = 32/64）；对比 C `__builtin_clz(0)` 为 **UB**。
- `ctpop(0)` = `0`（自然值，无特例）。

**D11.6（合法性）**

- `hd ∈ 0..63`（6 位立即数域）⇒ **全部合法**，**无非法 `hd` 值** ⇒ **不新增** `encode_onehot`，**不新增**任何合法性规则。
- 沿用既有 **`dst_rd0`**（`rdHB != rd0`）；`rdHC` **可为 `rd0`**（读出 0 ⇒ 结果 = `hd+1` 或 0，合法）；**`rdHB == rdHC` 允许**。
- 现场先例：`ext.uo_orri_rd` = `rule_refs: [dst_rd0]` + `legality: [rdhb != rd0]`（`hd` 全 6 位 ⇒ 无额外约束）。

**D11.7（结果语义）**

- 结果 ∈ **`0..64`**，**写满 64 位**（值语义；非"只写低位 / 高位保持"）——与 `SPEC-069t` 的值语义通则一致。

**D11.8（用途 / 映射）**

- ↔ LLVM 内建 **`int_ctlz` / `int_cttz` / `int_ctpop`**（**1:1**）↔ C++20 `std::countl_zero` / `countr_zero` / `popcount`。
- `ctlz` **单条**覆盖 `clz8`/`clz16`/`clz32`/`clz64`（`hd` = 7/15/31/63）——对比 RISC-V 需 `clz` + `clzw` **两条**。
- **现状（现场，`LLVM-079t`）**：后端**无** ISA 位扫描 / 计数指令 ⇒ `CTLZ`/`CTTZ`/`CTPOP` 走 `Expand` **软件展开**（`xnor.o`/`and.o`/`sub.uo`/`shr.uo`/`mul.uo`，无 libcall）。本 `D11` 落地后可为 ISel 提供单指令 ⇒ **ISel 接入另立任务**（**不在**本 `D11` 落地任务的范围，见 `D11.9` 末行）。

**D11.9（同步面；照 `D10.6` 形式逐项列）**

1. `spec/SimRISC-00`：QFC `§4.2 MISC-octa` 补 `011-101`/`011-110`/`011-111` **三格** + **例外说明一句**（"子表 ⇔ 位宽后缀"规则的例外，见 `D11.3`）+ 相关**计数** + 文末 changelog。
2. **正文分册归位 —— 建议 `spec/SimRISC-04 §4.2`（`Bit manipulating：位操作指令`，与 `rev` 总述同处）⇒ 标「待用户确认」**（现场：`ext.uo_orri_rd` 的 `spec_cite` 即该节）。
3. `spec/SimRISC-0x` 各册 **`LEGALITY` 生成区**（`tools/spec/gen_legality_list.py --apply`）。
4. `contracts/opcodes.yaml`（生成器 `tools/spec/generate_opcodes.py`）；**含 `scope` 取值——待用户确认**（与 `D10.6b` 同一未决项 ⇒ 引用之）。
5. `contracts/legality_rules.yaml`：**不新增**规则（`D11.6`）。
6. `.tao/knowledge/contract-isa.md`（QFC/编码表 + 语义 + 定值 + 合法集 + `§2.5`/`§2.8` 的例外说明）、`contract-asm-list.md`（生成投影，`tools/llvm/gen_asm_list.py`）。
7. `tests/vectors/**` + `tests/vectors/inventory.md` + `tools/testcases/generate_isa_vectors.py`（**注**：`inventory.md` 的 M1 矩阵由 `validate_vectors.py` 与 `scope == "m1"` 集合**机械对齐** ⇒ 若三条**非 `m1`** 则**不入 M1 矩阵**，向量落独立文件）。
8. **MC**：`DADAOInstrInfo.td`（def / mnemonic）、`DADAOAsmParser`（`orri` 受理）、`DADAOInstPrinter`、`MCCodeEmitter`/decode。
9. **QEMU**：`insn.decode`（三条 token）+ `trans_ctlz`/`trans_cttz`/`trans_ctpop` + `translate.c` 分派。
10. **门控**：L1（`validate-encoding`／`check-scope`／`check-rule-refs`／`check-instrinfo`／`check-isa-coverage`／`check-asm-list-drift`／`check-legality-drift`／`check-legality-invariants`／`check-spec-readonly` 等）+ L2/L3。

- **不在本项**：LLVM **ISel** 接入（`int_ctlz` 等 → 单指令，见 `D11.8`）**另立任务**。

**D11.10（被否方案）**

- **(a) 带位宽后缀**（如 `ctlz.o`/`ctlz.t`/… 共 4 条一后缀）⇒ **不采用**：`hd`（`0..63`）**已覆盖任意宽度** ⇒ 后缀会**丢掉"任意宽度"**能力，且无谓扩充编码（4 倍条目）。
- **(b) `cttz` 改用"下界"语义**（有效位 = `rdHC[63:hd]`，从第 `hd` 位向上找）⇒ **不采用**：使 `cttz` 与 `ctlz`/`ctpop` 的**字段语义分裂**（同名 `hd` 含义不同，易误用）；如需"从第 k 位起向上找"**另立指令**。**（本节即 `D11.4` 待确认项的备选。）**
- **(c) `cls`/`clo`/`cto`/`parity`/`ffs`/`ffz` 一并做** ⇒ **本轮不做**。判据 = 「后端组合成本 ≥ 3 条 **且** 后端有对应 intrinsic」。现场实测（clang 18.1.3）：`cls` **4–5 条**、`ffs` **5 条**（**够格但本轮不做**，用户原话「先就这三个吧」）；`parity` **2 条**、`clo`/`cto` **2 条**（**≤2 条 ⇒ 不做**）。

**关联任务**：`SPEC-143t`（`ctlz`/`cttz`/`ctpop` 落地，**前置 = `D11` 逐条确认完成 + `spec/` 修改授权**；**与 `SPEC-142t` 须串行**——二者同改 `contracts/opcodes.yaml` / `tests/vectors/**`）——**提案，未逐条确认前不得下发**。

## 影响

- ~~256 条指令 → 254 条（删除 ftmadd/fomadd）~~（2026-09-30 修订：254 条 → 253 条，删除 `rela.si`）
- 下游合约（contract-isa.md）、机器可读数据（opcodes.yaml）、工具脚本全部同步更新
- assembly-list.md 分类顺序与新文档一致
- M1 身份集 177 → 176（删除 `rela.si`）

## 状态说明

- 2026-09-27：用户逐条确认 D1–D4 后置 `Accepted`。
- 2026-09-30：就地修订——D3.1 强化（`rd0`/`rb0` 作 `st`/`stm` 源的语义明确，依据 `SPEC-055t`/`QEMU-028t`/`TESTCASES-019t`）；新增 D5（删除 `rela.si`，编码 `0x5A` → UNDI，254→253，M1 177→176）。`ADR-0015` 退场（`Superseded`），其 D1–D4 并入本 ADR D3.1。
- 2026-09-30：术语统一（`SPEC-058t`）——D2.2「minor-op」→「opx」（就地措辞修订，decision 语义不变）。
- 2026-09-30：新增 D6（rf0 位域调整与访问规则：`[17:16]`→`[33:32]`、SBZ 合并、源合法/目的 ILLI、`rf0_as_operand`→`rf0_as_dst`、头部 254→253/177→176）。用户逐条确认 D6 第 1–7 条全部同意。
- 2026-09-30：新增 D7（RegRAS 有效性判据改为 `ra0[53:48]` 的 `RACNT`；`ra0[63:54]` SBZ、MemRAS 引用计数取消、`ra0[47:0]` 明确为 `MRPTR`；压栈/弹栈流程与精确异常点重定义）。用户逐条确认 D7 第 1–7 条全部同意。
- 2026-09-30：就地措辞修订（计数澄清，decision 语义不变）——D6-3 与 `legality_rules.yaml` `rf0_as_dst` 的「46 条」澄清为「家族 46 条；其中带 rf 目的字段者 32 条，加 cs.* 5 条 = 37 条触发 ILLI」。
- 2026-09-30：就地措辞修订（`SPEC-061t`）——D3.1 从「仅「目的为 0 号寄存器」才触发 ILLI」细化为各寄存器组 0 号寄存器分类（`rd0`/`rb0` 只读 + 两条例外；`ra0`/`rf0` 可读写），消除与 `D7`、`SPEC-060t` 的口径不一致。decision 语义不变。
- 2026-10-01：就地措辞修订（计数澄清，decision 语义不变）——因删除 `ftlog`/`folog`（`SPEC-067t`），D1 表浮点运算 **46→44**、**待定 12→11**（与 canonical `docs/assembly-list.md` 对齐）、D6-3 计数改为 **44/30/35**（家族 44、带 rf 目的 30、+`cs.*` 5 = 35）；同步 `legality_rules.yaml` 的 `rf0_as_dst` 与 `docs/README.md`、`spec/Toolchain-01-汇编语言.md`。
- 2026-10-02：新增 **D8**（RB / 控制流地址语义澄清：D8.1 RB 高16 语义、D8.2 `cmp.uo-rb` 48 位无符号、D8.3 控制流 64 位地址写回 `rb0`、D8.4 `rb0` 只读含义、D8.5 文档归位、D8.6 同步面）。用户逐条确认 D8 第 1–6 条全部同意。
- 2026-10-02：D8.3 **措辞澄清**（用户同意，decision 语义不变）：明确**不假定 `rb0` 高 16 位为 0**（可为前一次地址回绕保留下来的值）；`rb0[63:48]` 保留计算结果高 16，**跨出 48 位地址空间时即进位**。**CPU 发出的地址总线只有 48 位** ⇒ **取指 / 访存有效地址 / 跳转目标一律取低 48 位**（与"寄存器 64 位""地址运算 64 位"不冲突）。文档中**不用「PC」指代 `rb0`**。
- 2026-10-02：新增 **D8.7（一般原则，用户确认）**：**所有 RB/RA 寄存器（`rb0`–`rb63`/`ra0`–`ra63`）均为 64 位**；**凡其值被用作地址（取指 / 访存有效地址 / 跳转目标 / 返回地址）时一律取低 48 位**（CPU 地址总线 48 位）；高 16 为寄存器自身内容（RB 普通 64 位值；RA 递归计数 / `RACNT` / `MRPTR`）。与「寄存器 64 位、地址运算 64 位」不冲突。
- 2026-10-02：**D8.2 就地修订**（用户确认，decision 变更）：`cmp.uo-rb` 由「低 48 位」改为「**整 64 位**」无符号比较，`br.z-rb`/`br.nz-rb` 条件同样**整 64 位**判零。理由：RB 高 16 是**合法内容**（D8.1），且**判断/比较不是「地址使用」**（48 位截断仅生于地址总线，D8.7）；高 16 意外非 0 时按 64 位**暴露**而非隐藏。连带返工：QEMU（去 `trans_cmp_uo_orrr_rb` 的 48 掩码）、向量、`spec/SimRISC-05`/`contract-isa` 措辞（见 `SPEC-081t`）。
- 2026-10-04：新增 **D9**（新增指令 `sub.o`（RB−RB→RD，`sub.o_orrr_dbb`，`ha=0x33`，`scope:m3`）+ 三条既有 RB 算术指令改名/改编码槽 `add.so_orrr_rb`→`add.o_orrr_bbd`(0x30)、`sub.so_orrr_rb`→`sub.o_orrr_bbd`(0x31)、`cmp.uo_orrr_rb`→`cmp.uo_orrr_dbb`(0x32) + id 后缀 bank 签名约定）。**用户 2026-10-04 逐条确认追加**。关联 `SPEC-100t`/`SPEC-101t`/`LLVM-043t`/`QEMU-040t`/`LLVM-035t`。
  - **算术修正（用户 2026-10-04 已确认）**：D9.1 定 `ha=0x33 ⇒ value=0x40CC0000`；旧 id 清零验收**仅覆盖活载体**（`spec/`/`contracts/`/`tests/`/`tools/`/`components/`），**映射记录豁免**。
- 2026-10-06：**D3 就地增补第 5 项**（用户逐条确认）：**删除 `illi` 指令**（**ILLI 异常保留**，由非法操作数/条件触发）、**`fence` `ha` `0x01`→`0x00`**（`value` `0x77040000`→`0x77000000`）、**`swym` `ha` `0x02`→`0x22`**（`value` `0x77080000`→`0x77880000`）；`op=0x77` 不变。关联 M4 前置任务 `SPEC-109t`（跨组件原子落地）。
- 2026-10-14：**新增 `D10`（提案）**——`rev.{o,t,w,b}` 逐块反转（新增 4 条 `orri` 指令，`opx=001100`，`immu6` = one-hot 位单元大小，新增 `encode_onehot` 合法性规则）。**⚠ `D10` 及其子项 `D10.1`–`D10.8` 均为提案，尚未经用户逐条确认；未确认前不得视为 `Accepted`**，本 ADR 顶部 `**状态**：Accepted` **不含 `D10`**。用户**授权**与**裁定原话**（Q1–Q4，渠道 = 经主会话问答）**原样引录于 `D10.0`**；落地任务 = `SPEC-142t`（`待开始`，**前置 = `D10` 逐条确认完成**）。**待确认项**：`D10.6a`（正文分册归位）与 `D10.6b`（`scope` 取值）。
- 2026-10-14：**`D10` 由提案转 `Accepted`（用户逐条确认 ✓）**——**用户裁定原话（原样引录，渠道 = 经主会话问答，2026-10-14）**：「**1、分册写；2、你来定；D10.1-D10.8 认可**」。**结果**：① 「`D10.1-D10.8` 认可」⇒ `D10` 及其子项 `D10.1`–`D10.8` **逐条确认完成**；本 ADR 顶部 `**状态**：Accepted` 的确认范围**含 `D10`**（上一条同日记述的「不含 `D10`」**已被本条取代**）。② 「1、分册写」⇒ **`D10.6a` 定案 = 备选 (b) 分册**（`.o`→`SimRISC-04`、`.t`→`08`、`.w`→`09`、`.b`→`10`；逐块语义总述置于 `04 §4.2`、其余三册引用）；「建议 (a)」**已否**。③ 「2、你来定」⇒ **实现分阶段由主会话决定**，已定案为「一个任务书、三阶段验收（A 契约/编码层 → B MC → C QEMU）」，写入 `SPEC-142t`。**仍待确认**：**`D10.6b`（`scope` 取值；建议 `scope: m8`）**——**未确认前不得写入 `opcodes.yaml` / `check_scope.py`**。
- 2026-10-14：**新增 `D11`（提案，待用户逐条确认 ✗）**——`ctlz`/`cttz`/`ctpop`（**位扫描与计数**：新增 **3 条** `orri` 指令；`opx` = `011-101`/`011-110`/`011-111`（29/30/31）、主 op `0x40`（`MISC-octa`）、`value` = `0x40740000`/`0x40780000`/`0x407C0000`、`mask` = `0xFFFC0000`；`hd` = **有效位上界**（有效位 `[hd:0]`）、全 0 定值 = **`hd+1`**、**无新合法性规则**（沿用 `dst_rd0`）；**不带位宽后缀**）。**⚠ `D11` 及其子项 `D11.1`–`D11.10` 均为提案，尚未经用户逐条确认；未确认前不得视为 `Accepted`**，本 ADR 顶部 `**状态**：Accepted` **不含 `D11`**（照 `D10` 提案期先例：顶部 `**状态**` 行**待逐条确认后**再更新）。用户**指令名 / 范围 / 编码 / 前序四项**的**裁定原话**（渠道 = 经主会话问答）**原样引录于 `D11.0`**；落地任务 = `SPEC-143t`（`待开始`，**前置 = `D11` 逐条确认完成 + `spec/` 修改授权**；**与 `SPEC-142t` 须串行**）。**待确认项**：`D11.4`（`cttz` 的 `hd` 语义）／`D11.9`（正文分册归位、`scope` 取值〔与 `D10.6b` 同一未决项〕）。
