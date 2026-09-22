# TESTCASES-009t 逐族重推导审计记录

> 本文件满足验收标准 1：为每个族给出「重推导公式 + 依据章节 + 与现有数据比对结论」。
> 审计方法：独立 Python 脚本（`tools/testcases/009t-audit.py`）+ reviewer 独立 oracle（`/tmp/opencode/TESTCASES-009t-review/oracle.py`）。
> reviewer 独立全量重算确认 **0 残留错值**（319 条抽查 + 595 条 mask/value）。

---

## 1. reg-arith（reg-arith.yaml）

**case 数**：140（encoding 45 + semantic 47 + boundary 42 + overlap 6）
**涉及指令**：`add.uo/so-rd`、`sub.uo/so-rd`、`mul.uo/so-rd`（rrrr）；`add/sub/mul/div/rem .ub/.sb/.uw/.sw/.ut/.st`（orrr）；`add.si-rd`（riii）；`add.so/sub.so-rb`（orrr）；`rela.si-rb`（riii）；`add.si-rb`（riii）

### 重推导公式

| 指令族 | 公式 | 依据章节 |
|--------|------|---------|
| `add.uo` rrrr | `rdha:rdhb = zero_extend(rdhc,128) + zero_extend(rdhd,128)`；rdha = carry (0/1)，rdhb = low 64 | §3.1.1 |
| `add.so` rrrr | `rdha:rdhb = sign_extend(rdhc,128) + sign_extend(rdhd,128)`；rdha = high 64，rdhb = low 64 | §3.1.1 |
| `sub.uo` rrrr | `rdha:rdhb = zero_extend(rdhc,128) − zero_extend(rdhd,128)`；rdha = borrow (0/1) | §3.1.1 |
| `sub.so` rrrr | `rdha:rdhb = sign_extend(rdhc,128) − sign_extend(rdhd,128)`；rdha = high 64 | §3.1.1 |
| `mul.uo` rrrr | `rdha:rdhb = zero_extend(rdhc) × zero_extend(rdhd)`（128-bit unsigned） | §3.1.4 |
| `mul.so` rrrr | `rdha:rdhb = sign_extend(rdhc) × sign_extend(rdhd)`（128-bit signed） | §3.1.4 |
| `add/sub .ub/.sb/.uw/.sw/.ut/.st` orrr | 仅 size 位宽参与运算；溢出丢弃；`.u` 零扩展至 64，`.s` 符号扩展至 64 | §3.1.2 |
| `mul/div/rem .ub~.so` orrr | 源按 size 截断；结果仅保留 size 位宽；div truncate-toward-zero；rem 符号=被除数 | §3.1.5 |
| `add.si-rd` riii | `rdha = rdha + sign_extend(imms18)`，全 64 位 | §3.1.3 |
| `add.so/sub.so-rb` orrr | `rbhb = rbhc op zero_extend(rdhd)`，全 64 位补码 | §4.5.1 |
| `rela.si-rb` riii | `rbha = (PC & ~0xFFF) + (imms18 << 12)`；PC 低 12 位清零得 4KB 对齐基地址 | §4.7 |
| `add.si-rb` riii | `rbha = rbha + sign_extend(imms18)`，全 64 位 | §4.5.2 |

### 附加规则
- rrrr 双目的：`rdha` 与 `rdhb` 同为 rd0 或同为同一非 rd0 → ILLI（§3.1.1/§3.1.4）
- 固定位宽：`rdhb` 为 rd0 → ILLI（§3.1.2/§3.1.5）
- div/rem：除数为零 → ILLI；`div.s` INT_MIN÷(−1) → ILLI（§3.1.5）

### 比对结论
- **mismatch 数**：0（reviewer 独立 oracle 重算 90+ 条，全部一致）
- `.sb` 符号扩展 bug 已修复（见 `tools/testcases/009t-audit.py`），脚本 exit 0、Mismatches: 0

---

## 2. reg-logic（reg-logic.yaml）

**case 数**：48（encoding 16 + semantic 16 + boundary 16）
**涉及指令**：`and/or/xor/xnor .b/.w/.t/.o`（orrr）

### 重推导公式

| 指令 | 公式 | 依据章节 |
|------|------|---------|
| `and.N` | `rdhb[N:0] = rdhc[N:0] & rdhd[N:0]`；bits[63:N+1] 不变 | §3.3 |
| `or.N` | `rdhb[N:0] = rdhc[N:0] \| rdhd[N:0]`；高位不变 | §3.3 |
| `xor.N` | `rdhb[N:0] = rdhc[N:0] ^ rdhd[N:0]`；高位不变 | §3.3 |
| `xnor.N` | `rdhb[N:0] = ~(rdhc[N:0] ^ rdhd[N:0])`；高位不变 | §3.3 |

N = 7(.b) / 15(.w) / 31(.t) / 63(.o)。高位保持 rdhb 初始值不变。

### 比对结论
- **mismatch 数**：0（reviewer 独立重算 16 条 semantic，全部一致）

---

## 3. reg-shift-extend（reg-shift-extend.yaml）

**case 数**：120（encoding 40 + semantic 40 + boundary 40）
**涉及指令**：`shl/shr/ext .ub/.sb/.uw/.sw/.ut/.st/.uo/.so` × orrr + orri

### 重推导公式

| 指令 | 公式 | 依据章节 |
|------|------|---------|
| `shl.u` orrr/orri | `rdhb[N:0] = (rdhc[N:0] << shamt)`；低位补零；高位不变 | §3.4.1 |
| `shr.u` orrr/orri | `rdhb[N:0] = (rdhc[N:0] >> shamt)`；高位补零 | §3.4.1 |
| `shr.s` orrr/orri | `rdhb[N:0] = sign_extend(rdhc[N:0] >> shamt)`；高位补符号位 | §3.4.1 |
| `ext.u` orrr/orri | `rdhb[hd:0] = rdhc[hd:0]`；`rdhb[N:hd+1] = 0`；高位不变 | §3.4.2 |
| `ext.s` orrr/orri | `rdhb[hd:0] = rdhc[hd:0]`；`rdhb[N:hd+1] = sign_extend(rdhc[hd])`；高位不变 | §3.4.2 |

**关键区分**：
- **orrr**：shamt/ext_pos 取 `rdhd` **寄存器值**（不是编码字段），需从 `input_state.rd.rdhd` 读取
- **orri**：shamt/ext_pos 取 `immu6`（编码 `hd[5:0]`）
- `.b/.w/.t` 变体只修改 bits[N:0]，**高位保持 rdhb 初始值**（`input_state` 预置）
- `shamt > N` → ILLI（§3.4.1）；`hd > N` → ILLI（§3.4.2）

### 比对结论
- **mismatch 数**：0（reviewer 独立重算 80+ 条，全部一致）
- 此族为 F1 已修复的重点族（40 条期望值曾全错），本次审计确认已全部正确

---

## 4. reg-compare（reg-compare.yaml）

**case 数**：22（encoding 11 + semantic 11）
**涉及指令**：`cmp.ui/cmp.si`（rrii）；`cmp.ub~cmp.so`（orrr）；`cmp.uo-rb`（orrr）

### 重推导公式

| 指令 | 公式 | 依据章节 |
|------|------|---------|
| `cmp.ui` rrii | `rdha = cmp(rdhb, zero_extend(immu12))`；结果 −1/0/1 写入全 64 位 | §3.2.1 |
| `cmp.si` rrii | `rdha = cmp(rdhb, sign_extend(imms12))`；结果 −1/0/1 | §3.2.1 |
| `cmp.N` orrr | 源按 size 截断后比较；`.u` 无符号、`.s` 有符号；结果 −1/0/1 | §3.2.2 |
| `cmp.uo-rb` orrr | 无符号 64 位 RB 比较；bits[63:48] 不影响 | §4.6 |

### 比对结论
- **mismatch 数**：0（reviewer 独立重算 11 条 semantic，全部一致）

---

## 5. reg-cond-assign（reg-cond-assign.yaml）

**case 数**：15（encoding 5 + semantic 5 + overlap 5 deferred）
**涉及指令**：`cs.n/z/p/eq/ne`（rrrr）

### 重推导公式

| 指令 | 公式 | 依据章节 |
|------|------|---------|
| `cs.n` | `if (rdha < 0) rdhb = rdhc; else rdhb = rdhd` | §3.5 |
| `cs.z` | `if (rdha == 0) rdhb = rdhc; else rdhb = rdhd` | §3.5 |
| `cs.p` | `if (rdha > 0) rdhb = rdhc; else rdhb = rdhd` | §3.5 |
| `cs.eq` | `if (rdha == rdhb) rdhc = rdhd`（条件成立时写入 rdhc） | §3.5 |
| `cs.ne` | `if (rdha != rdhb) rdhc = rdhd` | §3.5 |

- 5 条 overlap case 为 C-27 deferred（`deferred_reason: C-27`），不参与 active 比对

### 比对结论
- **mismatch 数**：0（5 条 active semantic 全部一致）
- 5 条 deferred overlap 有明确 `deferred_reason: C-27`

---

## 6. reg-imm-block（reg-imm-block.yaml）

**case 数**：26（encoding 13 + semantic 13）
**涉及指令**：`set.zw/set.ow/or.w/andn.w .rd/.rb`（rwii）；`rd2rd/rd2ra/ra2rd/rb2rb/rd2rb/rb2rd`（orri）

### 重推导公式

| 指令 | 公式 | 依据章节 |
|------|------|---------|
| `set.zw` rwii | `rdha[wyde(wp)] = immu16`；其余 48 位清 0 | §3.6 |
| `set.ow` rwii | `rdha[wyde(wp)] = immu16`；其余 48 位置 1 | §3.6 |
| `or.w` rwii | `rdha[wyde(wp)] \|= immu16`；其余 wyde 不变 | §3.6 |
| `andn.w` rwii | `rdha[wyde(wp)] &= ~immu16`；其余 wyde 不变 | §3.6 |
| 块赋值（orri） | 64 位二进制不变，按 immu6 个连续寄存器逐对复制 | §3.7/§4.3/§4.9.3 |

**rwii 立即数解码**（`opcodes.yaml` fields 定义）：
- `wpN = hb[5:4]`（wyde-position，0–3）→ `wp = (word >> 16) & 0x3`（bits[17:16]）
- `immu16 = hb[3:0] << 12 | hc[5:0] << 6 | hd[5:0]`（高 4 + 中 6 + 低 6 = 16 位）
  - `immu16_hi = (word >> 12) & 0xF`（bits[15:12]）
  - `immu16_mid = (word >> 6) & 0x3F`（bits[11:6]）
  - `immu16_lo = word & 0x3F`（bits[5:0]）

### 比对结论
- **mismatch 数**：0（reviewer 独立重算 13 条 semantic，全部一致）
- `rwii` 解码 bug 已修复（见 `tools/testcases/009t-audit.py`），脚本 exit 0、Mismatches: 0

---

## 7. mem-rd（mem-rd.yaml）

**case 数**：126（encoding 22 + legality 60 + semantic 22 + boundary 22）
**涉及指令**：`ld.ub~ld.o / st.b~st.o`（rrii）；`ldm.ub~ldm.o / stm.b~stm.o`（rrri）

### 重推导公式

| 指令 | 公式 | 依据章节 |
|------|------|---------|
| `ld.N` rrii | `rdha = {sign/zero}_extend(mem{size}[rbhb + imms12])` | §4.1.1 |
| `st.N` rrii | `mem{size}[rbhb + imms12] = rdha[N:0]` | §4.1.1 |
| `ldm/stm` rrri | 从 `rbhb + rdhc` 地址加载/存储 immu6 个连续寄存器 | §4.1.2 |

**异常条件**：`rdha` 为 rd0 → ILLI；未对齐 → MALIGN；`immu6=0` → ILLI；`rdha+immu6>64` → ILLI
**F10 守卫**：encoding base `rbhb` 不为 rb0/rb1/rb2；base 预置且落 RAM 窗口

### 比对结论
- **mismatch 数**：0（reviewer 独立重算 22 条 semantic + 22 条 boundary，全部一致）

---

## 8. mem-rb（mem-rb.yaml）

**case 数**：24（encoding 4 + legality 12 + semantic 4 + boundary 4）
**涉及指令**：`ld.o/st.o-rb`（rrii）；`ldm.o/stm.o-rb`（rrri）

### 重推导公式

| 指令 | 公式 | 依据章节 |
|------|------|---------|
| `ld.o` rrii | `rbha = mem64[rbhb + imms12]`，全 64 位覆盖 | §4.2 |
| `st.o` rrii | `mem64[rbhb + imms12] = rbha` | §4.2 |
| `ldm.o/stm.o` rrri | 多 RB 寄存器加载/存储 | §4.2 |

- **RB 全 64 位**：bits[63:48] 正常读写，无 48-bit 截断
- 异常：`rbha` 为 rb0 → ILLI；未对齐 → MALIGN

### 比对结论
- **mismatch 数**：0（reviewer 独立重算 4 条 semantic + 4 条 boundary，全部一致）

---

## 9. mem-ra（mem-ra.yaml）

**case 数**：22（encoding 4 + legality 10 + semantic 4 + boundary 4）
**涉及指令**：`ld.o/st.o-ra`（rrii）；`ldm.o/stm.o-ra`（rrri）

### 重推导公式

| 指令 | 公式 | 依据章节 |
|------|------|---------|
| `ld.o` rrii | `raha = mem64[rbhb + imms12]`，全 64 位覆盖 | §4.9.1 |
| `st.o` rrii | `mem64[rbhb + imms12] = raha` | §4.9.1 |
| `ldm.o/stm.o` rrri | 多 RA 寄存器加载/存储 | §4.9.2 |

- `raha` 为 ra0 时不触发异常（ra0 可读写，§4.9.1）
- `immu6=0` → ILLI；`raha+immu6>64` → ILLI

### 比对结论
- **mismatch 数**：0（reviewer 独立重算 4 条 semantic + 4 条 boundary，全部一致）

---

## 10. ctrl-br（ctrl-br.yaml）

**case 数**：30（encoding 10 + semantic 20）
**涉及指令**：`br.n/nn/z/nz/p/np`（riii）；`br.eq/ne`（rrii）；`br.z/nz-rb`（riii）

### 重推导公式

| 指令 | 公式 | 依据章节 |
|------|------|---------|
| `br.cond` riii（taken） | `PC = rb0 + (imms18 << 2)` | §5.2.2 |
| `br.cond` riii（not-taken） | `PC = rb0 + 4` | §5.2.2 |
| `br.eq/ne` rrii（taken） | `PC = rb0 + (imms12 << 2)` | §5.2.1 |
| `br.eq/ne` rrii（not-taken） | `PC = rb0 + 4` | §5.2.1 |
| `br.z/nz-rb` riii | 按 `rbha == 0` / `rbha != 0` 判断 | §5.2.3 |

**条件判断**（§B.1）：N=bit63==1, Z=all zero, P=bit63==0且非全零

### 比对结论
- **mismatch 数**：0（reviewer 独立重算 20 条 semantic（taken+not-taken），全部一致）
- `rb0 = 0xFFFF00000000`（RAM 入口，ADR-0004 D2.2），`imm=2` → target = rb0+8

---

## 11. ctrl-jump（ctrl-jump.yaml）

**case 数**：5（encoding 2 + legality 1 + semantic 2）
**涉及指令**：`jump-iiii`（iiii）；`jump-rrii`（rrii）

### 重推导公式

| 指令 | 公式 | 依据章节 |
|------|------|---------|
| `jump` iiii | `PC = rb0 + (imms24 << 2)` | §5.3 |
| `jump` rrii | `PC = rbha + rdhb + (imms12 << 2)` | §5.3 |

### 比对结论
- **mismatch 数**：0（reviewer 独立重算 2 条 semantic，全部一致）

---

## 12. ctrl-call（ctrl-call.yaml）

**case 数**：9（encoding 2 + legality 2 + semantic 5）
**涉及指令**：`call-iiii`（iiii）；`call-rrii`（rrii）

### 重推导公式

| 指令 | 公式 | 依据章节 |
|------|------|---------|
| `call` iiii | `PC = rb0 + (imms24 << 2)` + RA 压栈（§5.6.1） | §5.4 |
| `call` rrii | `PC = rbha + rdhb + (imms12 << 2)` + RA 压栈 | §5.4 |

**RA 压栈**（§5.6.1）：3 种情况——空栈直接压入（ra63 高 16=0x0001）、递归（高 16+1）、移位压栈（可能 RASOF）

### 比对结论
- **mismatch 数**：0（reviewer 独立重算 5 条 semantic，全部一致）

---

## 13. ctrl-ret（ctrl-ret.yaml）

**case 数**：2（encoding 0 [ret-riii encoding 豁免] + legality 1 + semantic 1）
**涉及指令**：`ret-riii`（riii）

### 重推导公式

| 指令 | 公式 | 依据章节 |
|------|------|---------|
| `ret` | `PC = ra63[47:0]`（RegRAS 栈顶低 48 位）+ `rdha = sign_extend(imms18)` | §5.5 |

**RA 弹栈**（§5.6.2）：3 种情况——高 16>1 递减、高 16=1 弹出+移位、高 16=0 RASUF/MemRAS

### 比对结论
- **mismatch 数**：0（reviewer 独立重算 1 条 semantic，全部一致）

---

## 14. misc（misc.yaml）

**case 数**：6（encoding 2 + legality 2 + semantic 2）
**涉及指令**：`illi`（oiii）；`fence`（oiii）；`swym`（iiii）

### 重推导公式

| 指令 | 公式 | 依据章节 |
|------|------|---------|
| `illi` | 恒 ILLI，encoding/semantic 豁免（F6） | §7.2 / §9.1 |
| `fence` | 无架构副作用（M1 仅串行化语义）；SBZ 非零 → ILLI | §7.3 |
| `swym` | PC 自增外无副作用（nop） | §7.1 |

### 比对结论
- **mismatch 数**：0（reviewer 独立重算 2 条 semantic，全部一致）

---

## 15. reserved（reserved.yaml）

**case 数**：2（encoding 0 [reserved 标志] + legality 2 [active, UNDI]）
**涉及指令**：保留编码（QFC/子表空白单元格）

### 重推导公式

| 指令 | 公式 | 依据章节 |
|------|------|---------|
| 保留编码 | `expected_fault = UNDI`；无 `(insn, format)` 身份 | §8.2 / §9 |

- `encoding.reserved: true` → 不参与 `(insn, format)` 覆盖率门控
- 全零字 `0x00000000` 是 `illi` → ILLI（§8.3），不是 UNDI

### 比对结论
- **mismatch 数**：0（2 条 UNDI legality，结构合法）

---

## 汇总

| 族 | 文件 | case 数 | active | deferred | 编码校验 | 语义比对 | mismatch |
|---|---|---|---|---|---|---|---|
| reg-arith | reg-arith.yaml | 140 | 140 | 0 | ✓ | ✓ | 0 |
| reg-logic | reg-logic.yaml | 48 | 48 | 0 | ✓ | ✓ | 0 |
| reg-shift-extend | reg-shift-extend.yaml | 120 | 120 | 0 | ✓ | ✓ | 0 |
| reg-compare | reg-compare.yaml | 22 | 22 | 0 | ✓ | ✓ | 0 |
| reg-cond-assign | reg-cond-assign.yaml | 15 | 10 | 5 | ✓ | ✓ | 0 |
| reg-imm-block | reg-imm-block.yaml | 26 | 26 | 0 | ✓ | ✓ | 0 |
| mem-rd | mem-rd.yaml | 126 | 126 | 0 | ✓ | ✓ | 0 |
| mem-rb | mem-rb.yaml | 24 | 24 | 0 | ✓ | ✓ | 0 |
| mem-ra | mem-ra.yaml | 22 | 22 | 0 | ✓ | ✓ | 0 |
| ctrl-br | ctrl-br.yaml | 30 | 30 | 0 | ✓ | ✓ | 0 |
| ctrl-jump | ctrl-jump.yaml | 5 | 5 | 0 | ✓ | ✓ | 0 |
| ctrl-call | ctrl-call.yaml | 9 | 9 | 0 | ✓ | ✓ | 0 |
| ctrl-ret | ctrl-ret.yaml | 2 | 2 | 0 | ✓ | ✓ | 0 |
| misc | misc.yaml | 6 | 6 | 0 | ✓ | ✓ | 0 |
| reserved | reserved.yaml | 2 | 2 | 0 | ✓ | N/A | 0 |
| **合计** | | **597** | **592** | **5** | | | **0** |
