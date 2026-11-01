# GEM5-002t — M11 指令语义重导矩阵（报告）

> 口径：**Spec-first**。语义只从当前 `spec/` + `.tao/contracts/contract-{isa,fp}.md` +
> `contracts/{opcodes,fp_semantics,legality_rules}.yaml` 派生；0628 与 PR #3 只作**旧表对照**，
> 不作语义来源，不复制代码。矩阵逐行见 `semantic-matrix.tsv`（264 行 × 29 列）。

## 1 基线（现场统计）

- 当前 `contracts/opcodes.yaml`：**264** 条 = M1 156 / FP 66 /
  M3 1 / M8 7 / M9 34；excluded 0。
- 旧表 A（0628，0.4.1）：`.cache/refs/DADAO-0628/tools/opcodes.yaml` **92** 条（仅 M1；无 FP/窄位宽子表）；
  另用其 `contracts/isa/spec.md §2.8/§3–§8` 核对语义（表外条目：`trap=0x76`）。
- 旧表 B（PR #3，0.5.4）：`git show 7ea82cfe:contracts/opcodes.yaml` **259** 条
  = M1 156 / FP 60 / excluded 27 / M3 1 / M8 7 / M9 8。
- 条数差：264 − 259 = 5 = FP 净 +6（新增 rnd2/minmax4/fma2，删 cs.eq/ne-rf −2）
  + clmul +1 + 删 cfxld/cfxst −2；lr/sc 24 条与 fence 由 `excluded` 转入 `m9`（净 0）。

## 2 分类统计

### 2.1 对 PR #3（0.5.4）

- 同义 222、编码迁移 29、
  新增 7、同编码异义 2、
  仅助记符相同 4。
- 语义上新增共 9 条（clmul + ftrnd/fornd/ftmin/ftmax/fomin/fomax + ftfma/fofma）；
  其中 ftfma/fofma 落在 PR 的 `cs.eq/ne-rrrr-rf` 编码（0x5E/0x5F）上 ⇒ 标为**同编码异义**。
- 编码迁移 29 条：fence/swym + 24 条 lr/sc + ctlz/cttz/ctpop（PR 0x77xx/0x407x → 现 0x47xx/0x79）。
- 仅助记符相同 4 条：cfx2rd/cfx2rc/escape/trap —— legality 新增 `encode_cfx_reserved` + escape SBZ。

### 2.2 对 0628（0.4.1）——身份轴

| 类别 | 条数 | 说明 |
| --- | --- | --- |
| 同义 | 51 | 操作语义逐条一致（仅改名/编码迁移）⇒ 仍须重导，非"可复用" |
| 改名+语义变更 | 37 | 改名且语义/合法性有变（详见 §3） |
| 仅助记符相同 | 11 | 助记符逐字相同但语义/编码不同 |
| 新增 | 99 | 0.4.1 无此操作（含全部 M8/M9/窄位宽/FP 族） |
| 旧表未覆盖 | 66 | FP 66 条：0628 参考树无 FP 编码表 |

### 2.3 对 0628——编码轴

| 类别 | 条数 | 判据 |
| --- | --- | --- |
| 同编码同义 | 0 | 同 mask/value + 同助记符 + 同操作 |
| 仅编码相同 | 1 | 同 mask/value + 同操作但改名（可作字段交叉校验） |
| 同编码异义 | 48 | 同 mask/value 但旧表为**另一指令** |
| 粗掩码吞并 | 177 | 旧 op 级掩码（0xFF000000）覆盖当前细掩码条目 |
| 无旧编码 | 38 | 旧表该模式无条目 |
| 编码迁移 | — | 见 PR 轴；对 0628 以"无旧编码/粗掩码"表达 |

编码冲突：精确冲突 49 行（旧表 49 个条目）、粗掩码吞并 177 行
（旧表 7 个条目：`swym@0x10`（MISC 子表槽）+ `ldbu/ldwu/ldtu/ldo@0x40–0x43`
+ `ldmbu@0x44` + `ldmo@0x47`；0.4.1 这些是单指令，v5 是 OPC 子表前缀）。
逐条见 `old-collisions.tsv`。

## 3 语义变化重点（必须重写，不得沿用旧实现）

1. **FP（66 条，contract-fp §1–§20）**：NaN/舍入/标志口径齐全——舍入 `rf0[33:32]`；
   `NV/DZ/OF/UF/NX` sticky；`UF` 仅 tiny+inexact（tininess=舍入后）且 `UF⇒NX`；
   `ftrnd/fornd` 六档 one-hot、仅 0x20 置 NX；`ftmin/ftmax/fomin/fomax` 严格
   `minimumNumber/maximumNumber`（单 NaN 取数、双 NaN canonical qNaN、`-0<+0`、sNaN⇒NV、不置 NX）；
   `ftfma/fofma` **单次舍入**；`ftqcmp/ftscmp` unordered 返回 qNaN/sNaN（符号 0）；
   `ftcls/focls` 类位序为 IEEE 754-2019 class（与 RISC-V `fclass` 不兼容）。
   PR 基线少 8 条（rnd/minmax/fma），且 fma 与已删的 `cs.eq/ne-rf` **同编码**。
2. **M9（34 条）**：`rol.o/.t/.w/.b`（orrr+orri 共 8；ADR-0032）、`clmul.o`（GF(2) 128 位，
   ADR-0035）、`fence`（ciii 0x79，pred/succ 六位掩码、hb SBZ、cfx 域；ADR-0044）、
   `lr/sc` 24 条（`<lr|sc>.<b|w|t|o>.<nn|an|ar|nr>`，ADR-0034）——旧 fence 的 `fm/TSO`、
   旧 `lr.nr`/`sc.an` 与旧 `0x77xx` 编码全部作废。
3. **M10 / 0.5.6-rc（无新 opcode，改语义）**：`cmp.{ut,uw,ub}` 的 −1 改为 **64 位全 1**
   （ADR-0037；旧实现零扩展即错）；`fence` 迁 `ciii` + hb SBZ；`cfxld/cfxst` 删除、`crii` 撤销；
   `escape` 汇编偏移收窄为 0/4 且 `imms18[17:1]` SBZ；cfx 保留编号统一 6–14/19–61。
4. **`sub.o` / `aip.si` / `cmp.uo` / RB 算术**：RB 运算由「低 48 位 + 高 16 保留」改为**整 64 位**
   （ADR-0012 D8.2/D8.7）；`sub.o dbb` = `rdhb = rbhc − rbhd`（M3 新增，sub.o_orrr_dbb）；
   `aip.si` = `IP + (sext18<<12)` 且 **IP 不清低位**（ADR-0029；旧 `rela` 是向下对齐 + 保留高位）。
5. **`ldm/stm`**：元素地址 `rbhb + rdhc + i*N`（用原始 rdhc）、按 i 递增**先读后写**、
   `immu6∈1..63`、起始+count≤64、元素对齐；`ldm` 目的 rd0/rb0 ⇒ ILLI，`stm` 作源**允许** rd0/rb0
   （旧 0.4.1 对 st/stm 的 rd0 一律 ILLI）。
6. **RA / RegRAS**：`call/ret` 走 `RACNT/MRPTR` 状态机（C1/C2/C3a/C3b、D1/D2/D3/D4a/D4b，
   含递归折叠与 MemRAS 换出）；`ret` 的返回地址**可能不来自 ra63**；
   `ret rd0, imms18` 仅 `imms18=0` 合法；RA 单/多存取按不透明 64 位传输（不清高 16）。
7. **算术/比较/移位值语义**：窄位宽结果一律**写满 64 位**（cmp −1=全 1、shl/rol/shr 高位扩展）；
   `div/rem` 除零与 `INT_MIN÷−1` 为**定值**（旧 0.4.1 为 ILLI），商向零截断、余数符号=被除数；
   `add/sub rrrr` 拆 `.uo`（零扩展、高半=进位/借位 0/1）与 `.so`（符号扩展、高半=高 64 位）。
8. **cfx**：`trap/escape/cfx2rd/cfx2rc` 静态规则 = 保留 cfx ⇒ ILLI；CFXREG 属运行期
   （不在译码期抛）；数据通路只连 RD 银行。

## 4 复用判决

**264 / 264 行判「否」；允许复用执行语义的行数 = 0。**

- 规则：`同义`/`仅编码相同` 只说明**该行文本与旧表一致**，不构成复用证据；复用需同时满足
  ① 当前 spec 条款与旧实现依据的条款逐字一致；② 该行有独立派生的 G1 单测并通过
  （现无任何一行具备②）。
- 允许范围（`reuse_scope`）：仅编码/字段交叉校验 29 行
  （PR #3 的 mask/value/fields/legality 与当前一致，可用来**交叉校验解码器**，不可搬运执行语义）；
  仅语义参考 70 行；无 165 行。
- 反例（同编码不同义）：0x5E/0x5F `cs.eq/ne-rf → ftfma/fofma`；0x76 `trap → ret`；
  0x40–0x47 旧单指令 → 现子表前缀（177 行粗掩码吞并）。

## 5 G1 实现顺序（先共用 ISA 核心，再接 SE）

| 批次 | 内容 | 行数 | 依据 |
| --- | --- | --- | --- |
| B0 | 解码/字段/格式/合法性表（由 contracts 生成 + 逐行校验） | 264 | `semantics`/`exceptions` 列 |
| B1 | 存取：RD/RB/RA/RF 单/多 load/store | 38 | contract-isa §3 / contract-fp §11 |
| B2 | 16 位立即数 & RF 立即数 | 8 | §5 / contract-fp §13 |
| B3 | 64 位算术/逻辑/移位/扩展/rev/rol/位扫描 | 42 | §6 / §7 |
| B4 | 32/16/8 位算术/比较/移位/rev | 63 | §10–§12 |
| B5 | 块复制 / 条件赋值 / 控制流 / RAS | 28 | §3.3.3/§4/§6.5/§8 |
| B6 | 系统/原子/屏障（swym/trap/escape/cfx2rd/cfx2rc/fence/lr/sc） | 30 | §13.6/§14 |
| B7 | FP 15 族（convert/arith/root/sign/compare/classify/cs/roundint/minmax/fma/rf_move） | 55 | contract-fp §2–§20 |

SE 接入（另任务）：B0–B7 是 FS/SE 共用核心；SE 只需 `Process`/`SEWorkload` 桥与 syscall，
不得为 SE 另写一套 ISA。每批实现须引用矩阵行 id + `contract_ref`，并配 `tests/inst` 向量。

## 6 发现 / 风险

- **F1（契约缺口）**：`lr` 的 12 行 `legality` 为空，但 spec `SimRISC-12 §1.1` 明文
  「hb（rdHB）固定 rd0，手工编码 ≠0 ⇒ ILLI」；`contract-isa §14.2` 未列该规则 ⇒
  若照契约实现 gem5 会错误接受 `hb≠0`。建议另立 SPEC/契约任务补规则与向量（本任务不改 contracts）。
- **F2（流程状态）**：`ADR-0044`（fence ciii）仍为 `Proposed`，但 spec `0.5.6-rc` 与 contracts
  已按 ciii 冻结；ADR 状态与规范不一致，请架构师确认。
- **F3（旧表覆盖不足）**：0628 机器可读表仅 92 条 0.4.1 M1（无 FP、无窄位宽子表）；
  PR 表为 0.5.4。两者都不能作为当前 264/66/0 的覆盖基线。
- **F4（粗掩码）**：0.4.1 的 op 级表（`0xFF000000`）与当前子表（`0xFFFC0000`）粒度冲突，
  177 行会被旧解码器错译（如 0x43 旧 `ldo-rb` 吞掉整个 OPC-byte 子表）。
- **F5（FP 独立性）**：FP 期望值必须独立派生自 spec（不得用 QEMU/LLVM/gem5 校准）；
  `ftrem/forem`、`ftsclb/fosclb` 边界与 `convert_f2i` 的 NX 属 spec 未明（contract-fp §16）。
- **F6（RAS）**：`call/ret` 的 RACNT/MRPTR 精确异常（RASOF/RASUF、MemRAS 换出）是最高实现风险，
  必须做状态机单测而非按"寄存器栈"近似。
- **F7（需 G1 固定）**：`call` 压栈的返回地址 spec 只写「计算返回地址」，未逐字写 `IP+4`；
  由 IP=当前指令地址推得下一指令 = IP+4，建议 G1 用向量固定该口径。
- **F8（平台相关/未明）**：`lr/sc` 保留标记粒度由平台定义（精确地址或 cache line）；
  `sc` 目的 `rdHB` 是否可为 `rd0`、异常/中断清标记的时序 spec 未逐条写明。

## 7 建议任务拆分

1. **SPEC/CONTRACT**：补 `lr` hb==rd0 合法性 + 向量；确认 ADR-0044 状态（F1/F2）。
2. **GEM5 解码核心**：按本矩阵生成 decode/legality + 264 行逐行断言（B0）。
3. **GEM5 整数执行**：B1–B6 分族实现，配 `tests/inst` 复用（不新建 `tests/gem5`）。
4. **GEM5 FP 执行**：B7 + FP oracle 对接（NaN/舍入/标志）。
5. **GEM5 SE 桥**：`Process`/`SEWorkload` + `tests/tset`（另任务）。
6. **INFRA（可选）**：把矩阵升级为门控（每条 opcode 必填 semantics/证据字段），防契约漂移。

## 8 复现

```
python3 gen_matrix.py --repo <仓库根> --out <本目录>   # 重生成矩阵/统计/冲突表
python3 check_matrix.py --repo <仓库根>               # C1–C10 校验
./run.sh                                              # 生成 + 校验 + 反例注入自检
```
