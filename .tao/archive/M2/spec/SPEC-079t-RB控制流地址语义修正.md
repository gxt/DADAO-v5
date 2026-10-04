# SPEC-079t: RB/控制流 地址语义修正（spec + contracts，按 ADR-0012 D8）

**模块**：spec
**项目里程碑**：M2
**依赖**：`ADR-0012 D8`（已 `fb4ef7c`）
**状态**：已验证

## 目标

按 `ADR-0012 D8` 修正 `spec/SimRISC-00/05/06` 与 `.tao/knowledge/contract-isa.md` 的文字/契约（**本任务只改文档/契约**；QEMU 实现 + 向量属 `QEMU-031t`，**串行**）。

## 改动清单

### `spec/SimRISC-00-指令系统设计.md`
1. **§基址寄存器（L62 `rb0`）**：保留「`rb0` **只读 = 不可作显式目的寄存器**」；**删**「`rb0[63:48]` **恒为 0**」（依 D8.4：初值 0，由 D8.3 硬件写入）。
2. **§基址寄存器 高 16 表（L70–74）**：
   - L71「赋值类-寄存器」**删去 `ra2rd`/`rd2ra`**（保留 `rd2rb`/`rb2rb`）——它们归 §返回地址栈（D8.5）。
   - L74 **`cmp.uo-rb`**：「无符号 **64** 位比较」⇒「**低 48 位**无符号比较」（D8.2）。
3. **§基址寄存器 高 16 表（L75–76，控制流）**：按 **D8.3** 重写「跳转 `br*`/`jump`」与「函数支持 `call`」两行：
   - `rb0` 以 **64 位**参与地址计算；**结果写回 `rb0`**，取 **`rb0[47:0]`（低 48）**为下一条指令地址；
   - **iiii 基址 = `rb0`；rrii 基址 = `rbHA`（仅读、不修改）**；
   - `rb0[63:48]` 保留结果高 16 并**参与后续运算**（供溢出检测）；
   - **`ret` 不在此处**（归 §返回地址栈）。
4. **L78**：RB 高 16 初值全 0（用途未定义，软件勿依赖）；**删去 RA 相关句**（`ra0[53:48]`/`ra1`–`ra63` 高 16），归 §返回地址栈（D8.5）。
5. **L80 存储模型**：与 D8 对齐（RB 整 64 位；**作基址时取低 48**；控制流地址计算按 64 位）。
6. **§返回地址栈**：
   - 增补 **`ra2rd`/`rd2ra`** 的说明；
   - 增补 **`ret`** 的返回地址来源（**可能不是 `ra63`**，取决于 RAS 状态）**及可能引发的异常（如 RASUF）**；
   - **`call`/`ret` 在本节也列**（D8.5：两节均列）；
   - RA 高 16（`RACNT`/递归计数）**统一在此描述**。

### `spec/SimRISC-05-64位地址运算.md`
- L58「`cmp.uo-rb` 对两个 **64 位**无符号数进行比较」⇒「对**低 48 位**无符号比较」（D8.2）。

### `spec/SimRISC-06-控制流.md`
- 各地址公式处（L55/L70/L93/L101/L116/L124 等）「**地址位宽为 48 位，不产生溢出**」⇒ 按 **D8.3** 改写：**64 位计算 → 写回 `rb0` → 取低 48 为下一条地址**；rrii 的 `rbHA` 仅读。
- **`ret` 段**（L131 附近）改为指向 §返回地址栈（来源可能不是 `ra63`；可能 RASUF）。

### `.tao/knowledge/contract-isa.md`
- L125「高 16 位在地址计算时被硬件忽略…」⇒ 按 D8.3/D8.1 修正；
- L700「`cmp.uo …` 无符号 **64** 位比较」⇒ **低 48 位**（D8.2）；
- 控制流地址公式条目按 D8.3 修正；`rb0` 条目（L44–46）按 D8.4 修正（删"恒为 0"表述）。

## 范围外 ✗
- **不改** QEMU/LLVM/向量（属 `QEMU-031t`）；
- **不改** `ADR-0012 D8` 本身；不改历史文件；不碰生成区（`ASSEMBLY_LIST`/`LEGALITY`）。

## 验收标准（须真实可失败）
1. 各改动与 `ADR-0012 D8` **逐条一致**（贴 diff 对照）。
2. **无残留旧口径**：`grep -rn "rb0\[63:48\] 恒为 0"` / "无符号 64 位比较（`cmp.uo-rb`）" / "地址位宽为 48 位，不产生溢出" 在**生效文件**（`spec/` 非历史、`contract-isa.md`）= **0**（逐条说明豁免）。
3. **门控不回归**：`make check` **EXIT=0**（`check-asm-prose` 0、`check-legality-drift`、`check-rule-refs` 等）；生成区**未动** ✓。
4. **未越界**：`git diff --name-only` = `spec/SimRISC-00/05/06` + `contract-isa.md` + 任务书；历史文件干净。
5. 退出码用 `cmd >log 2>&1; rc=$?`（禁管道吞码 ✗）；命令失败 ⇒ 停下报告 ✗。

## 完成区
**测试结果**：通过 25/25；`make check` EXIT=0
**修改文件**：
- `spec/SimRISC-00-指令系统设计.md`（L62 rb0、L71 赋值类行、L74 cmp.uo-rb、L75-76 控制流行、L78 RB高16、L80 存储模型、§返回地址栈增补 ra2rd/rd2ra + call/ret）
- `spec/SimRISC-05-64位地址运算.md`（L58 cmp.uo-rb）
- `spec/SimRISC-06-控制流.md`（L42 通用约定、L55/L70/L93/L101/L116/L124 地址公式、L131 ret）
- `.tao/knowledge/contract-isa.md`（L44-46 rb0、L125 存储模型、L127 rb0、§7.3 cmp.uo-rb、§8.1 通用约定、§8.2-8.5 地址公式、§8.5 ret）

**D8 逐条对照**：
| D8 条目 | 改前（旧口径） | 改后（D8 口径） | 涉及文件 |
|---------|--------------|----------------|---------|
| D8.1 RB 整64位 | 「高16位在地址计算时被硬件忽略，寄存器存取时保持高16位原值不变」 | 「RB 为整64位寄存器，存取/复制/立即数赋值等均为全64位操作；**作访存基址时取rb[47:0]（低48位）**；控制流地址计算按64位全宽进行」 | 00(L78,L80), contract(L125) |
| D8.2 cmp.uo-rb 48位 | 「无符号64位比较」 | 「**低48位**无符号比较」 | 00(L74), 05(L58), contract(§7.3) |
| D8.3 控制流64位地址写回rb0 | 「地址位宽为48位，不产生溢出」「地址计算仅在低48位进行，溢出丢弃；bits[63:48]保持不变」 | 「rb0以64位参与地址计算；结果写回rb0，取低48位为下一条地址；rrii的rbHA仅读」 | 00(L75-76), 06(L42,L55,L70,L93,L101,L116,L124), contract(§8.1-8.4) |
| D8.4 rb0只读含义 | 「rb0[63:48] 恒为 0」 | 「rb0[63:48] 初值为0，由控制流指令硬件写入」（保留"只读=不可作显式目的"） | 00(L62), contract(L44-46,L127) |
| D8.5 文档归位 | ra2rd/rd2ra在赋值类行；ret在控制流函数支持行；call/ret未在§返回地址栈列出 | ra2rd/rd2ra归§返回地址栈；call/ret两节均列；ret来源可能非ra63+RASUF；RA高16统一在§返回地址栈 | 00(L71,L75-76,§返回地址栈), 06(L131), contract(§8.5) |

**旧口径残留 grep（应 0）**：
- `rb0[63:48] 恒为 0`：spec/ 非历史 = **0**（仅存于 `SimRISC-0.5.3/` 历史文件，豁免）；contract-isa.md = **0**
- `无符号 64 位比较`：spec/ 非历史 = **0**（仅存于 `SimRISC-0.5.3/` 历史文件，豁免）；contract-isa.md = **0**
- `地址位宽为 48 位，不产生溢出`：spec/ 非历史 = **0**（仅存于 `SimRISC-0.5.3/` 历史文件，豁免）；contract-isa.md = **0**
- `高 16 位在地址计算时被硬件忽略`：contract-isa.md = **0**

**验收结果**：`make check` EXIT=0（check-asm-prose PASS 0 violations, check-legality-drift 12 chapters OK, check-patch-tree 67 patches OK, 25/25 tests passed）；`git diff --name-only` = 4 个目标文件（contract-isa.md + SimRISC-00/05/06），历史文件/生成区/ADR-0012 均未动。
**新发现/坑**：
- contract-isa.md 中 `rb0[63:48] 恒为 0` 出现在 3 处（L45/L127/L712），需逐一修复
- SimRISC-06 中 rrii 格式的地址公式在 jump 和 call 各出现一次（共2处），需分别匹配上下文避免 edit 多匹配
**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：4 个文件的全部改动（36 insertions, 27 deletions）

**逐条核对**：
1. ✅ D8.1：contract-isa.md L125 已改为「RB 为整64位…」，SimRISC-00 L78/L80 已对齐
2. ✅ D8.2：contract-isa.md §7.3 已改为「低48位无符号比较」，SimRISC-00 L74、SimRISC-05 L58 已对齐
3. ✅ D8.3：contract-isa.md §8.1-8.4 地址公式均改为「64位计算→写回rb0→取低48位」；rrii 的 rbHA 仅读；SimRISC-06 全部6处地址公式已对齐
4. ✅ D8.4：contract-isa.md L45/L127/L712 均已改为「初值为0，由控制流指令硬件写入」；SimRISC-00 L62 已对齐；保留「只读=不可作显式目的」
5. ✅ D8.5：ra2rd/rd2ra 已从赋值类行删除（SimRISC-00 L71）；call/ret 在§返回地址栈列出（SimRISC-00 §返回地址栈新增两子节）；ret 来源改为「可能不是ra63」+RASUF（SimRISC-06 L131, contract §8.5）
6. ✅ 旧口径归零：grep 全部=0（生效文件）
7. ✅ `make check` EXIT=0
8. ✅ `git diff --name-only` 未越界

**判决**：全部 finding = 0，可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（独立重跑，不采信完成区）
**工作目录**：`/mnt/tao/DADAO-v5`；证据：`/tmp/opencode/SPEC-079t-r1/`（`full.diff`、`make_check.log`、`check_spec_refs.log`、`acceptance_greps.txt`）
**构建**：无（本任务只改文档/契约；`.work/build/{llvm,qemu}` 已有产物，直接跑门控）

##### 重跑记录（真实输出/退出码）

1) **`make check`** —— `make check > make_check.log 2>&1; rc=$?` → **`EXIT=0`**
   关键门控行（自 log 摘录）：
   - `manifest validation: PASS`
   - `validate_vectors: 152/152 M1 identities covered OK ... data coverage gaps: 0`
   - `spec drift check: PASS`
   - `check-patch-tree: 2 component(s), 67 patches OK`
   - `check-asm-list-consistency: 12 spec files OK`
   - **`check-asm-prose: PASS (0 violations)`**
   - **`check-legality-drift: 12 chapters OK`**
   - `check-qemu-semantics: PASS`（146/146）
   - `llvm-lit: 25 tests, Passed 25 (100.00%)`
   - `repository checks: PASS`

2) **旧口径 grep（生效文件 = `spec/SimRISC-00/05/06` + `contract-isa.md`）**——全部 `rc=1`（0 命中）：
   - `rb0[63:48] 恒为 0` → rc=1
   - `无符号 64 位比较` → rc=1
   - `地址位宽为 48 位，不产生溢出` → rc=1
   - `高 16 位在地址计算时被硬件忽略`（仅 contract）→ rc=1
   - 附加：`软件不应依赖` 在生效文件 → rc=1
   - **鉴别力反证**：同类旧口径在历史目录 `spec/SimRISC-0.5.3/` 命中 **10 行**（豁免），证明 grep 能失败、非恒绿。

3) **边界**：`git diff --name-only` = `spec/SimRISC-00/05/06.md` + `.tao/knowledge/contract-isa.md`（4 个）；未跟踪 = 本任务书。**无越界**（无 QEMU/LLVM/向量/历史/生成区/ADR-0012）。

4) **生成区未动**：`git diff` 全文无 `ASSEMBLY_LIST`/`LEGALITY`/生成区标记（grep `rc=1`）；且 `check-asm-list-consistency`/`check-legality-drift` 双双 PASS。

##### 逐条 D8 核验（对照 ADR-0012 D8，`full.diff` 证据）

- **D8.1（RB 整 64 位）✅**：`SimRISC-00` L80「存储模型」删「高16在地址计算被忽略，存取时保持高16原值」，改为「RB 为整 64 位寄存器…作访存基址时取 `rb[47:0]`（低48）…控制流按 64 位全宽」；`contract-isa` §1.5（L125）同步。生效文件「保持高/被硬件忽略」grep=0。
- **D8.2（`cmp.uo-rb` = 低 48 位无符号）✅**：`SimRISC-00` L74、`SimRISC-05` L58、`contract-isa` §7.3 均改为「低 48 位无符号比较」。**未越界**：RD 数据变体 `cmp.uo`（`contract-isa` §6.2 L574「`cmp.uo`/`cmp.so` | 64 位」）**保持 64 位未动**——符合 D8.2 与备选 R2（否决）。
- **D8.3（控制流 64 位地址写回 `rb0`）✅**：`SimRISC-00` L75–76 两行、`SimRISC-06` L42 + 6 处公式（L55/L70/L93/L101/L116/L124）、`contract-isa` §8.1–§8.4 均改为「64 位计算→写回 `rb0`→取 `rb0[47:0]`」；rrii 的 `rbHA` 标注**仅读**；iiii 基址 `rb0`。**`ret` 未混入**本规则（归 §返回地址栈）。
- **D8.4（`rb0` 只读含义）✅**：`SimRISC-00` L62 保留「任何指令以 rb0 为显式目的时触发 ILLI」，删「`rb0[63:48]` 恒为 0」→「初值为 0，由控制流指令硬件写入」；`contract-isa` L45 同步。生效文件 `rb0[63:48] 恒为 0` grep=0。
- **D8.5（文档归位）✅（附 1 处解释性备注）**：`SimRISC-00` §返回地址栈新增「RA↔RD 块赋值」（`ra2rd`/`rd2ra`）与「call / ret 在本节的说明」（ret 来源**可能不是 `ra63`** + **RASUF**）；RA 高16（RACNT/递归计数）本就在该节表格；原 L78 的 RA 句已删；`SimRISC-06` L131、`contract-isa` §8.5 同步。
  - **备注（非阻断，供架构师）**：D8.5 字面「`call`/`ret` 两节均列」——现状为 **§返回地址栈** 两指令各有条目（✓），**§基址寄存器** 表中 `call` 为独立行、`ret` 以交叉引用「（…`ret` 见 §返回地址栈）」出现。任务书改动清单第 3 条明确要求「`ret` 不在此处（归 §返回地址栈）」，工程师依此执行；D8.5 的实质意图（ret 来源/异常归 §返回地址栈、两节均可定位）已满足。判定为**满足**。
- **D8.6（同步面）**：QEMU/向量属 `QEMU-031t`，本任务范围外，**正确未改**。

##### 追加项（主会话代行删除）核验 ✅
- `SimRISC-00` L78 原句（HEAD）：「RB 的高 16 位尚未定义用途，初始值为全 0。**软件不应依赖高 16 位的值。**RA 寄存器的高 16 位另有定义（…）」。
- 现句： 「RB 的高 16 位初值为全 0。`rb0[63:48]` 由控制流指令硬件写入（见 §控制流指令），参与后续运算（累积/传播），供溢出检测。」
- **已删**（生效文件 `软件不应依赖` grep=0）；删「不应依赖/保持原值」后文字与 **D8.1（RB 整 64 位、高16 正常读写）不矛盾**：现句只陈述初值与 rb0 高16 由硬件写入，未限制软件读写高16，与 D8.3 一致。

##### 引用可定位性
新引入的 `（见 §控制流指令）` 为**裸节名跨文件引用**（指向 `SimRISC-06 §控制流指令`）。核对本 spec 集既有惯例：`SimRISC-06` 用裸 `§返回地址栈` 指 `SimRISC-00`、`SimRISC-02` 用裸 `§存取RA寄存器`/`§浮点状态寄存器` 指 `SimRISC-01/00`——**裸节名跨文件引用是本 doc set 既有约定**，故**非悬空引用**，不构成缺陷。

##### 完成区逐条复读
与真实一致：`make check EXIT=0`（真实）、lit 25/25（真实）、4 文件 diff（真实）、旧口径生效文件=0（真实）、历史 `0.5.3/` 豁免（真实，10 命中）。完成区未发现与真实输出矛盾处。

##### 约束核验（逐条）
| 约束 | 结果 |
|------|------|
| D8.1–D8.5 逐条落地 | ✅（D8.5 附解释性备注） |
| 旧口径生效文件归零 | ✅（rc=1；历史豁免已证） |
| 追加项删除 + 与 D8.1 不矛盾 | ✅ |
| `make check` EXIT=0 / `check-asm-prose` 0 | ✅ |
| 生成区（ASSEMBLY_LIST/LEGALITY）未动 | ✅ |
| 未越界（仅 4 目标文件 + 任务书） | ✅ |
| 退出码用 `cmd >log; rc=$?`（未管道吞码） | ✅ 本轮 reviewer 均用重定向取码 |

##### 非阻断观察（范围外/供架构师，非本任务缺陷）
1. `.tao/knowledge/adr-0004-test-machine.md` / `contract-elf.md` / `adr-0003-object-abi.md` 仍引 `contract-isa §1.5`「高 16 位在地址计算时被硬件忽略」。该表述对**访存有效地址（取低 48）**仍成立，且任务书验收范围仅限 `spec/`+`contract-isa.md`，故非本任务遗漏；如需口径统一可另立任务。
2. `SimRISC-05` §加减（L34）/`contract-isa` §7.2（L684）的 `add.so-rb`/`sub.so-rb` 仍保留「地址计算仅在低 48 位有效，溢出丢弃」。属 **RB 算术**（非 D8.3 控制流），任务范围外且与 `SimRISC-00` L73「bits[63:48] 为运算结果，可用于溢出检测」大体一致；非本任务缺陷。
3. `check-spec-refs` 为 standalone 目标（`Makefile` 注释明确**不属** `make check`），当前 `EXIT=2`（80 violations，均为既有，与本任务改动无关）——故不影响门控结论，仅记录。

##### 判决
**Accepted** —— 本任务 5 条验收标准在**独立重跑**下全部通过（`make check` EXIT=0；旧口径生效文件 grep 全 0；边界仅 4 目标文件；完成区与真实一致）。第 1、2、3 点明确表态：**1（D8 逐条）=通过；2（旧口径归零）=通过；3（追加项删除且不与 D8.1 矛盾）=通过**。唯 D8.5「两节均列」存在一处可解释空间（`ret` 在 §基址寄存器 为交叉引用而非独立行），已按任务书明示要求执行、判定满足，**提请架构师终审时留意**。无 finding 需返工。

> 说明：本轮未对「验证脚本反例」单独注入——本任务未新增任何验证脚本/检查器；唯一任务特定判据（旧口径 grep）已用历史 `0.5.3/` 的 10 处命中证明其**可失败、非恒绿**。



#### 主会话收尾（2026-10-02）

1. **提交推送**：`SimRISC-00/05/06` + `contract-isa.md` 按 `ADR-0012 D8` 修正（见 git log）。
2. **reviewer 第 1 轮 Accepted**：D8.1–D8.6 逐条 diff；旧口径生效文件 **0**（历史 `0.5.3/` 命中 10 行反证 grep 非恒绿）；**追加项**（主会话代行删除「软件不应依赖 rb1–rb63 高16」）与 D8.1 不矛盾；RD 变体 `cmp.uo` 仍 64 位（未触否决项 R2）。
3. **非阻断观察（供终审/后续）**：
   - D8.5「`call`/`ret` 两节均列」：§返回地址栈 两者均列；§基址寄存器 中 `call` 独立行、`ret` 交叉引用（任务书要求「`ret` 不在此处」）⇒ 判**满足**。
   - 范围外：`adr-0004`/`contract-elf`/`adr-0003` 仍引 §1.5「高16被忽略」（**对访存基址仍成立**）；`SimRISC-05 §加减`/`contract §7.2` 的 `add/sub.so-rb`「溢出丢弃」属 RB 算术（非 D8.3 控制流）；`check-spec-refs` standalone EXIT=2 为既有 violation（不属 `make check`）。
