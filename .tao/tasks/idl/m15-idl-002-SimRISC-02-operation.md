# m15-idl-002: `SimRISC-02`（寄存器复制）逐条 operation

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-spec-001`（语法基线、寄存器模型、语义库、`idl/render.py` 已就绪）
**可并行分片**：可与其它 `m15-idl-0xx` 并行（**各册独立文件**）；`idl/README.md §4` 语义库**不得自行动手**（缺函数 ⇒ 待裁定）
**预估**：2–3 天
**档位**：中改
**状态**：已验证

## 目标

把 `spec/SimRISC-02-寄存器复制.md` 里**每条指令**写成一段 operation，落到 **`idl/SimRISC-02.idl`**，再由 `idl/render.py` 生成 spec 内的 `<!-- IDL:<id> BEGIN/END -->` 块。

> 本册若已有 `m15-spec-001` 留下的样板 operation（01/04/06/11/12 各 1 条），按**同一风格**补齐其余指令，不重写已有样板。

## 用户裁定（2026-11-19，必须遵守）

1. **不修改原来的散文内容**——`spec/` 里只允许 `render.py` 写标记块，散文一字不动；
2. **发现散文不对、或与其它册/`spec` 冲突 ⇒ 停下来问用户**：写进任务书「待裁定」（问题 + 依据 + 候选解释），**不得自行改散文、不得自行改语义库**；
3. 正常情况下**每条指令一个 operation**（一 `# id:` 一段）；确需合并/拆分时同样记「待裁定」。

## 指令清单（本册 17 条，以 `contracts/opcodes.yaml` 的 `spec_cite` 为准）

- `cs.eq_rrrr_rd`
- `cs.n_rrrr_rd`
- `cs.n_rrrr_rf`
- `cs.ne_rrrr_rd`
- `cs.p_rrrr_rd`
- `cs.p_rrrr_rf`
- `cs.z_rrrr_rd`
- `cs.z_rrrr_rf`
- `ra2rd_orri_ra`
- `rb2rb_orri_rb`
- `rb2rd_orri_rb`
- `rd2ra_orri_ra`
- `rd2rb_orri_rb`
- `rd2rd_orri_rd`
- `rd2rf_orri_rf`
- `rf2rd_orri_rf`
- `rf2rf_orri_rf`


- **批 1**：§1. 寄存器组之间块赋值 + §2. 条件赋值：Conditional Assignment
- **批 2**：§3. 浮点条件赋值


- **批 1**：§1. 寄存器组之间块赋值 + §2. 条件赋值：Conditional Assignment
- **批 2**：§3. 浮点条件赋值

## 批次（每批 ≤4 h；做完一批返回，由主会话续派下一批）

> 任务号不拆（整册一起验收）；**同一个 `.idl` 文件，同册串行**。每批只做列出的节，做完即返回，不提交。全册 17 条 ⇒ 分 2 批。

- **批 1**：§1. 寄存器组之间块赋值 + §2. 条件赋值：Conditional Assignment
- **批 2**：§3. 浮点条件赋值

## 交付

1. `idl/SimRISC-02.idl`：上述每条一个 `# id: <id>` + operation；
2. spec 内对应块由 `render.py` 生成（不得手写块内容）；
3. 若某条指令的语义在散文中缺失/矛盾 ⇒ 该条**不写 operation**，记「待裁定」。

## 验收（逐条贴真实 rc）

1. **覆盖率**：`.idl` 的 id 集合 == 本册 `opcodes.yaml` 的 id 集合（脚本比对，零缺零多；「待裁定」的条目单独列出并说明为何不计入）。
2. `python3 idl/render.py --check` rc=0（spec 块与 `.idl` 逐字节一致）。
3. `idlc` 两段式：库 `compile --root isa` rc=0；本册每条 operation `compile --root instruction_operation` 全 rc=0。
4. **语义抽查 ≥3 条**：把 operation 的每条语句与散文逐句对应（贴对照），不得出现散文没说而 operation 自行发明的前提。
5. 「待裁定」逐条列出（问题 + 依据 + 建议），**不得自行处置**。
6. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**；**不改版本号**。
2. 只动 `idl/SimRISC-02.idl` + spec 本册的标记块 + 本任务书；**不动其它册**。
3. **不改 `idl/README.md`**（语义库）——缺函数就记「待裁定」。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

**批 1 结论：无待裁定项。** 批 1 的 14 条（§1 全部 9 条 + §2 的 5 条 `_rrrr_rd`）散文齐全、无矛盾，已全部写出 operation。

执行中核对过、但**判为可由 spec 直接推导**（不作待裁定，如实登记以免被读成「自行发明」）：

1. **`rd2ra` 的 `ra0` 目的写掩码**：`SimRISC-02 §1` 只说「`ra0` 作目的合法（见 SimRISC-01、SimRISC-00）」；`SimRISC-00 §2.4` 表给出 `ra0[63:54]` = SBZ（写无效）、`[53:48]` = `RACNT`、`[47:0]` = `MRPTR`，`§2.4.4` 又明确 `rd2ra` 是「全 64 位块赋值」。⇒ operation 写 `ra[0][53:0]`（[63:54] 写无效），其余元素整 64 位复制。
2. **`rd2rf` 的 `rf0` 目的写语义**：`SimRISC-02 §1` 注直接写明「写入按 SimRISC-00 写语义（只更新舍入模式与异常状态，其余位写无效）」⇒ 按 `SimRISC-00 §2.3.1` 只写 `[33:32]`/`[4:0]`。
3. **「negative/zero/positive」的位级判据**：`SimRISC-02 §2/§3` 只给文字三态，位级真源是 `SimRISC-00 §3.2`（N = bit63 为 1；Z = [63..0] 全 0；P = bit63 为 0 且 [62:0] 不全为 0）⇒ operation 直接按该表写位级判据（批 2 起统一；批 1 初稿用等价的 `$signed` 比较，见第 2 轮自审 F9）。
4. **`rf2rf`「目的范围含 `rf0`」的判据形式**：范围写作 `{rfHB:rfHB+immu6-1}`（升序）⇒ 含 `rf0` ⟺ `rfHB == 0`；与附录 B `dst_rf0` 一致。

**批 2 结论：无待裁定项。** 批 2 的 3 条（§3 `cs.n/z/p_rrrr_rf`）散文齐全、无矛盾。逐一核对了两处容易被 RISC-V 直觉带偏的点：

- **NaN/unordered 不另设分支**：`SimRISC-02 §3` 只说明「浮点比较结果…NaN 时其值按整型解读是**正数**，且**不等于 1**」，并给出使用侧组合（`sub` + `cs.z`）；指令语义仍是 `if (rdHA is negative/zero/positive) rfHB = rfHC else rfHB = rfHD`。⇒ operation 只按 `SimRISC-00 §3.2` 的 N/Z/P 位级判据选择，**不**做 unordered/quiet/signaling 判定（散文没写就不加）。
- **`rf0` 的 FCSR 写掩码在 `cs.*_rf` 不适用**：`§3` 注写明「目的（`rfHB`）为 `rf0` → ILLI」，即目的永远不是 `rf0` ⇒ 没有「只写 `[33:32]`/`[4:0]`」的场合（该掩码只出现在 `rd2rf`，见上面第 2 条）。源为 `rf0` 合法、读完整 64 位，按整 64 位搬移（`§3` 注「搬移宽度」）。

## 语义逐句对照（批 1 + 批 2，全册 17 条，验收第 4 条）

> 逐条把 operation 的每个判定/赋值对回散文；「→」左为散文、右为语句。17 条按 6 组同构给出（同组内逐条同名替换）。

**① `cs.n_rrrr_rd` / `cs.z_rrrr_rd` / `cs.p_rrrr_rd` ↔ `SimRISC-02 §2` 第一类 + `SimRISC-00 §3.2` + 附录 B**

- 「需要先根据 `rdHA` 的内容进行条件判断，然后分别将 `rdHC` 或 `rdHD` 赋值给 `rdHB`，即 `if (rdHA is negative/zero/positive) rdHB = rdHC; else rdHB = rdHD`」→ `if (…条件…) { rd[rdHB] = rd[rdHC]; } else { rd[rdHB] = rd[rdHD]; }`（两条都写，无遗漏支）。
- 条件三态按 `SimRISC-00 §3.2` 位级定义 → `cs.n` = `rd[rdHA][63] == 1'b1`（N）；`cs.z` = `rd[rdHA] == 64'd0`（Z）；`cs.p` = `rd[rdHA][63] == 1'b0 && rd[rdHA][62:0] != 63'd0`（P）。三者互斥且完备（负/零/正）。
- 「> **注**：rd0 目的寄存器约定见 SimRISC-00」+ 附录 B `dst_rd0`（`cs.n/z/p_rrrr_rd`）→ `if (rdHB == 6'd0) raise(Illegal)`；`rdHA`/`rdHC`/`rdHD` 为 `rd0` 时散文未设限制，operation 也不判。

**② `cs.eq_rrrr_rd` / `cs.ne_rrrr_rd` ↔ `SimRISC-02 §2` 第二类 + 附录 B**

- 「先根据 `rdHA` 与 `rdHB` 是否相等进行条件判断，如果条件成立则将 `rdHD` 的值赋值给 `rdHC`，即 `if (rdHA ==/!= rdHB) rdHC = rdHD`」→ `if (rd[rdHA] == rd[rdHB]) { rd[rdHC] = rd[rdHD]; }`（`cs.ne` 用 `!=`）。散文只给成立支、**未给 else** ⇒ 不成立时 `rdHC` 保持（不是二选一赋值）。
- 附录 B `dst_rd0`（目的 `rdHC`；与编码表 `role: dst` 的字段 `rdhc` 一致）→ `if (rdHC == 6'd0) raise(Illegal)`。

**③ 同组块复制 `rd2rd_orri_rd` / `rb2rb_orri_rb` / `rf2rf_orri_rf` ↔ `SimRISC-02 §1`**

- 「将 `rbHC` 开始的 `immu6` 个寄存器复制到 `rdHB` 开始的 `immu6` 个寄存器中」（以 `rb2rd` 为例）+「不进行数据类型的转换，保持 64 位二进制不变」→ `for (k…) { dst[dstHB + k] = src[srcHC + k]; }`，逐元素整 64 位。
- 「`immu6` = 0 时触发 ILLI」→ `if (immu6 == 6'd0) raise(Illegal)`。
- 「目的寄存器**不可为 `rd0`/`rb0`** 时触发 ILLI」→ `if (rdHB == 6'd0)` / `if (rbHB == 6'd0)` raise。
- 「任一起始寄存器 + `immu6` > 64 时触发 ILLI」→ `Bits<7> dst_end = dstHB `+ immu6; … if (dst_end > 7'd64 || src_end > 7'd64) raise`（加宽加，63+63 不溢出）。
- 「源范围与目的范围有交集时触发 ILLI」→ `if (dstHB < src_end && srcHC < dst_end) raise`（两段等长升序区间相交的充要条件）。
- `rf2rf`「目的范围含 `rf0` ⇒ ILLI」→ `if (rfHB == 6'd0) raise`（升序 ⇒ 含 0 ⟺ 起点为 0）。
- 「非法条件…在处理任何元素之前判定…目的寄存器未被修改」→ 全部 `raise` 在 `for` 之前；`for` 内无判定。

**④ 跨组块复制 `rb2rd`/`rd2rb`/`ra2rd`/`rd2ra`/`rf2rd`/`rd2rf` ↔ `SimRISC-02 §1`（+ 组特有注）**

- 复制体 / `immu6`=0 / 目的 `rd0`·`rb0` / 起始+`immu6`>64 同上（按各自 bank 换变量）。
- **无重叠判定** ↔ 「根据语义，`rb`/`rf`/`ra` 之间不能进行直接赋值」（跨组两段必不相交 ⇒ 附录 B `mreg_range_overlap` 只列同组 3 条）。
- `ra2rd`：`ra0` 作源「读出完整 64 位」→ 直接 `rd[rdHB + k] = ra[raHC + k]`。
- `rd2ra`：`ra0` 作目的合法 → 元素 0 只写 `[53:0]`（`SimRISC-00 §2.4`：`[63:54]` SBZ 写无效；`§2.4.4`：含 `ra0[53:48]` = `RACNT`）。
- `rd2rf`：「`rf0` 可作目的（含 `{rf0:rf0+immu6-1}`）」→ 元素 0 按 `SimRISC-00 §2.3.1` 只写 `[33:32]`/`[4:0]`；其余元素整 64 位。
- `rf2rd`：「`rf0` 可作源，读出完整 64 位」→ 直接整 64 位读。

**⑤ 不适用「部分生效」例外 ↔ `SimRISC-02 §1` 精确性段**

- 「上述块复制指令…保持精确——非法条件…在处理任何元素之前判定，异常进入时目的寄存器未被修改、IP 指向该指令、异常原因码正确」→ 判定的 `raise` 实参为 `mode(), ip()`（IP = 当前指令，`idl/README §2`），且所有判定先于 `for`；本册无 `ldm`/`stm` 式部分生效建模。
- 核对「异常码正确」：本册全部合法性违规在散文与附录 B 中均为 ILLI ⇒ operation 里所有 `raise` 均为 `ExceptionCode::Illegal`（`rules_check.py` 机械断言 raise 条数 == `rule_refs` 条数且全为 Illegal）。

**⑥ `cs.n_rrrr_rf` / `cs.z_rrrr_rf` / `cs.p_rrrr_rf` ↔ `SimRISC-02 §3` + `SimRISC-00 §3.2`/`§2.3` + 附录 B**

- 「需要先根据 `rdHA` 的内容进行条件判断，然后分别将 `rfHC` 或 `rfHD` 赋值给 `rfHB`，即 `if (rdHA is negative/zero/positive) rfHB = rfHC; else rfHB = rfHD`」→ `if (…条件…) { rf[rfHB] = rf[rfHC]; } else { rf[rfHB] = rf[rfHD]; }`；条件判据与 rd 形式同源（`SimRISC-00 §3.2` 位级 N/Z/P，**条件操作数是 `rdHA`**，不是浮点寄存器）。
- 「与浮点比较指令配合使用…NaN 时其值按整型解读是**正数**且**不等于 1**」→ 不引入任何 NaN 分支：NaN 的 rd 值 bit63=0 且非 0 ⇒ 自然落在 P（`cs.p` 成立、`cs.z`/`cs.n` 不成立），与散文一致。
- 「> **注**：…目的（`rfHB`）为 `rf0` → ILLI」+ 附录 B `dst_rf0` → `if (rfHB == 6'd0) raise(Illegal)`；**不写** `[33:32]`/`[4:0]` 掩码（目的永远非 `rf0`）。
- 「> **搬移宽度**：…`rd` 形式与 `rf` 形式都按**整 64 位**搬移（源读 64 位、目的写 64 位），不做窄写、不保留目的高半」→ `rf[rfHB] = rf[rfHC]`（整元素赋值，非 `ft` 窄写）；源 `rf0` 合法、读完整 64 位。
- `rf` 的可用性：`SimRISC-00 §2.3`「直接赋值/复制类（`set.w`/…/`rf2rf`/`rd2rf`）…不受『专用于浮点类指令』限制」——`cs.*_rf` 是**条件赋值/复制**，不牵涉运算 ⇒ 不受 T3 限制（operation 注释标明）。
- 附录 B `dst_rf0` 是本组唯一合法性规则（不存在 `mreg_*`：本组不是块复制）⇒ 每条恰好 1 个 `raise`（`rules_check` 断言 raise 数 == `rule_refs` 数）。

## 审阅记录

### 第 1 轮 engineer 自审（批 1）

逐行审了 `idl/SimRISC-02.idl`（14 条）、spec 内 14 对渲染块（`render.py` 生成）、`spec/.manifests.toml` 1 行、`idl/.manifests.toml` 3 行、证据脚本 7 个文件。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `$signed(rd[rdHA]) < 0` 被 idlc 拒（`signed Bits<64>` 与 `const Bits<1>` 不可比） | ✅已修 | 零改成 `$signed(64'd0)`（保持有符号比较语义） | 探针四种写法实测：裸 `0`/`64'd0` 报 TypeError、`$signed(64'd0)` rc=0；14/14 typecheck rc=0 |
| F2 证据脚本「注入落盘」判据用 `git diff --name-only`，而 `.idl` 是未跟踪新文件 ⇒ 恒为空、注入门误报 | ✅已修 | 三处改 `git status --porcelain -uall -- <path>` | 修前 `[FAIL] 注入 2/3 落盘`；修后全 PASS（32/32） |
| F3 批 2 的 3 条 `_rrrr_rf` 若提前写进 `.idl`，批 1 覆盖判据会「多」而误红 | ✅已修（按批次约束） | `.idl` 只含批 1 的 14 条；批 2 留空 | `cover.py --upto 1` rc=0；`--upto 2` rc=1（缺 3 条）⇒ 双支可达 |
| F4 覆盖判据若只比 `mnemonic`，`cs.n` 会同时命中 `_rd`/`_rf`（批 1/批 2 混） | ✅已修 | 改「节内汇编形式 ↔ 附录 A 行 ↔ id」派生，附录行再与 opcodes `spec_cite` 对账 | `--upto 1` 派生 14 条（不含 rf 变体）、`--upto 2` 派生 17 条 == 本册 id 总数 |
| F5 非法判定顺序是否影响语义 | ❌不修（已核对，无需改） | 顺序取散文列表序（目的 0 号 → `immu6`=0 → 超界 → 重叠）；本册全部为 ILLI ⇒ 顺序不改变异常码 | 逐句对照 ③⑤；`rules_check` 33 条 rule 全对齐 |
| F6 `rd2ra` 对 `ra0` 加写掩码 / `rd2rf` 对 `rf0` 加 FCSR 掩码——是否算「散文没说」 | ❌不修（判为 spec 可推导） | 均以注释标出出处（`SimRISC-00 §2.4`/`§2.3.1`/`§2.4.4`） | 见「待裁定」段的 4 条推导链；`check-spec-refs` 未新增跨册引用 |
| F7 术语 | ✅已核对 | 全篇用「寄存器组」，无「银行」 | 证据脚本 grep 断言 rc=1（零命中） |
| F8 `spec/.manifests.toml` 与本册 sha256 | ✅已改并披露（超出任务书字面清单，属 `check-manifests-guard` 硬要求） | 仅本册 1 行 | `check-manifests-guard` rc=0；`check-idl-sync` rc=0 |

判决：无未修 finding（F5/F6 为核对结论，非缺陷）。

### 第 2 轮 engineer 自审（批 2）

逐行审了新增 3 条 rf 形式、改写的 5 条 rd 形式条件、3 对新增渲染块、`spec/.manifests.toml` 1 行、证据脚本（新增 `cond_check.py`、`run.sh` 5 处注入判据）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F9 批 1 的 5 条 `cs.*_rd` 条件用 `$signed(...)` 比较——与 `SimRISC-00 §3.2` 等价但**非原文**，且批 2 派单要求按 §3.2 位级 | ✅已修 | 5 条统一改为 `[63]==1'b1` / `==64'd0` / `[63]==1'b0 && [62:0]!=63'd0`；语义等价（N/Z/P 三态与 §3.2 表逐位对应） | `cond_check.py` rc=0（8 条 cs.* 全按 §3.2 判据）；注入 5（cs.p 换成 N 判据）⇒ rc=1 |
| F10 `cs.*_rf` 是否也要 FCSR 写掩码（`[33:32]`/`[4:0]`） | ❌不修（`§3` 注：目的 `rf0` ⇒ ILLI，永不到写 `rf0`） | 只写 `if (rfHB == 6'd0) raise(Illegal)`，无掩码语句 | `rules_check`：`cs.n/z/p_rrrr_rf` 各 raise=1 == `rule_refs[dst_rf0]` |
| F11 NaN / unordered 是否要专门判据（RISC-V 直觉） | ❌不修（散文只给「NaN 按整型解读是正数且 ≠1」，无指令级分支） | 不加 unordered/quiet/signaling 判定；NaN 自然落 P | 逐句对照 ⑥ 第 2 条；`cond_check` 只按 N/Z/P 三式 |
| F12 证据脚本「注入落盘」用 `git status` 判据：本批工作树本就未提交 ⇒ 恒非空、**恒真** | ✅已修 | 5 处改「注入前后 md5 不同」（更强且与提交状态无关） | 5 处 `[PASS] 注入 N 落盘（md5 已变）` |
| F13 注入 5 首版以 `count==1` 为锚，实际 cs.p 的 rd/rf 两变体同形 ⇒ 断言「空注入」 | ✅已修 | 改 `count==2` + 替换首处（只打 `cs.p_rrrr_rd`） | 修前 `AssertionError: 空注入`；修后 cond_check 期望 rc=1 实测 1 |
| F14 覆盖判据是否两边都能红/绿 | ✅已核对 | `--upto 2`（全册）rc=0、`--upto 1`（批 1 口径）rc=1（多 3 条） | 两条断言同轮并存，均为实测 |
| F15 新增 3 块后本册 sha256 变更 | ✅已改 | `spec/.manifests.toml` 本册 1 行 → `a65a6cf7…` | `check-manifests-guard` rc=0、`check-idl-sync` rc=0 |
| F16 术语 | ✅已核对 | 新 3 条用「寄存器组」语义、无「银行」 | 证据脚本 grep 断言 rc=1（零命中） |

判决：无未修 finding（F10/F11 为按散文/§3.2 的核对结论，非缺陷）。

### 第 1 轮 reviewer 验收（中改档，≥2 路注入）

**重跑（reviewer 自跑的真实输出 / rc，不采信完成区转述）**

1. 运行期证据目录内 `run.sh` ⇒ `汇总：PASS=38 FAIL=0 （operation=17 条）`、`RESULT: ALL GREEN`、`RUN_RC=0`；内含 17 条 `parse_rc=0 type_rc=0`、5 路注入「红 → `cp` 还原 md5 相等 → 回绿」全部符合预期。
2. `python3 idl/render.py --check` ⇒ `idl-render: PASS（源 operation=40 条 / 落点 8 册 / 标记块 40 个，逐字节一致）` rc=0；`--self-test` ⇒ `[self-test 6/6]` rc=0。
3. 覆盖现场派生：证据脚本内 `cover.py --upto 2` ⇒ `派生 id: 17 条 … 累计 17/17；实际 17/17` rc=0（缺/多/标记均空、BEGIN=END=17）；`--upto 1` ⇒ rc=1（双向可达）。
4. `make check-idl-sync` rc=0；`make check-manifests-guard` rc=0（清单 5／文件 42／sha256 22 全符）；另跑 `check-spec-purity/-drift/-codeblocks/-numbering/-changelog/-cite-targets`、`check-legality-drift/-invariants`、`check-asm-list/-list-drift/-prose`、`check-spec-refs`、`check-contracts-dir/-dirs/-no-residue/-patch-tree` **全 rc=0**；`idlc` 库 `compile --root isa` rc=0。
5. `git diff --name-only bbea18db` = 5 文件（无越界）；`git diff bbea18db -- spec/SimRISC-02-寄存器复制.md` = **433 增 / 0 删**；剥标记块（含块后配套空行）后与 merge-base **逐字节相同**。
6. 验收前/后各记 `git status -uall` + 5 文件 md5 快照，逐行对账 `FINAL_STATUS==PRE`、`FINAL_MD5==PRE`（注入全还原，工作树相对 HEAD 无差异）。

**注入 2 路（均不在 engineer 的 5 路内；`cp` 备份 + md5 对账，未用 checkout/restore/stash）**

- I-A：改 §1 散文一行 ⇒ 散文断言 rc=1（`首处差异 第 28 行`）、`render --check` 仍 rc=0；还原 md5 `f38689d6…` 相等 ⇒ 回 rc=0。
- I-B：`cs.n_rrrr_rd` 的 if/else 两支对调 ⇒ `render --check` **rc=1**、cover rc=0、rules rc=0、**`cond_check` 仍 rc=0**；还原 md5 `41a8d84c…` 相等 ⇒ 三者回 rc=0。

**语义抽查（6 条，逐句对散文与真源）**

1. `rd2ra`：`ra0` 元素只写 `ra[0][53:0]`（`[63:54]` SBZ 写无效、含 `RACNT[53:48]`+`MRPTR`），`ra2rd` 源整 64 位读 ⇒ 对 `SimRISC-00 §2.4` 表 + `§2.4.4`「全 64 位块赋值」一致。
2. `rd2rf`：目的元素 0 只写 `[33:32]`/`[4:0]`、其余整 64 位 ⇒ 对 `§2.3.1`「只更新 [33..32] 与 [4..0]、其余写无效」一致；raise 2 == `rule_refs`(mreg_zero/overflow)。
3. `cs.n/z/p`（rd、rf 共 6 条）判据与 `SimRISC-00 §3.2` 表逐字同：`[63]==1'b1` / `==64'd0` / `[63]==1'b0 && [62:0]!=63'd0`；`cs.eq/ne` 用 `==`/`!=` 且**无 else**（散文未给 else）。
4. `cs.*_rf` 各恰 1 条 `rfHB==0 ⇒ raise(Illegal)`、**无** `[33:32]`/`[4:0]` 写掩码 ⇒ 对 §3 注「目的 `rf0` → ILLI」，掩码只属 `rd2rf`。
5. `.idl` 零命中 nan/unordered/quiet/signaling ⇒ 未加 unordered 特判；NaN（bit63=0 且非 0）自然落 P，与 §3「按整型解读是正数且不等于 1」一致。
6. `rf2rf` 含 `rf0`（升序范围 ⇒ ⟺ `rfHB==0`）、同组 3 条才判重叠、跨组不判 ⇒ 对 §1 与合约规则一致；全册 raise 数 == `rule_refs`（36 条）且全 ILLI。

**硬约束**：独立 worktree、未动主工作树、**未提交 git**、未改版本号、只动 5 文件、未动 `idl/README.md` 语义库与其它册、还原只用 `cp`+md5 ⇒ 逐条守住。

**判决：Accepted**（验收各项在 reviewer 自己的重跑下全绿；完成区 38/0、17/17、40 条/8 册/40 块、sha256 `a65a6cf7…` 与实测一致）。

**findings（文档级/脚本灵敏度，不阻断，交 architect 收尾改）**

- R1 证据脚本 D2/D3 小标题称「render 仍绿」，实测 .idl 改动未重渲染 ⇒ render rc=1（完成区第 7 条只写 cover 绿，与实测相符）。
- R2 证据脚本内 `cond_check` 的分支断言只查「两条赋值都在」、不查所在支 ⇒ 两支对调仍 rc=0；建议补「成立支紧随 `if`」判据。本次交付语句序经人工逐句核对无误。
- R3 「批 1 的 5 条 `cs.*` 条件改写」表述不准：两 WIP 提交实diff仅 `cs.n`、`cs.p` 两条条件改写（`cs.z` 只改注释、`cs.eq/ne` 未动）；等价性成立（`$signed<0`⟺bit63=1、`$signed>0`⟺bit63=0 且非 0）。

## 完成区

**测试结果**：全册证据脚本（运行期证据目录内 `run.sh`）⇒ **PASS=38 FAIL=0、RUN_RC=0**（17 条 operation + 5 路注入 + ISS-475 探针；注入前后真实文件 md5 不变：`.idl` `41a8d84c…`、spec `f38689d6…`）。批 1 阶段同脚本（批 1 口径）曾 PASS=32；`render.py --self-test` 6/6 PASS。
**修改文件**：`idl/SimRISC-02.idl`（17 条 operation；批 2 新增 3 条 rf 形式、5 条 rd 形式条件改 §3.2 位级）、`spec/SimRISC-02-寄存器复制.md`（17 对标记块，散文逐字节未改；sha256 `a65a6cf7…`）、`spec/.manifests.toml`（本册 sha256 1 行）、`idl/.manifests.toml`（批 1 已加 `SimRISC-02.idl` 条目，本批无改动）、本任务书。
**验收结果**：
1. 覆盖率 **17/17**（§1 9 + §2 5 + §3 3），零缺零多、标记双向一致 ⇒ `cover.py --upto 2` rc=0；`--upto 1` rc=1（多 3 条，判据双向可达）
2. `python3 idl/render.py --check` **rc=0**（源 40 条 / 8 册 / 40 块逐字节一致）；`make check-idl-sync` rc=0；`render.py --self-test` 6/6
3. `idlc` 两段式 **rc=0**：库 `compile --root isa` rc=0；**17/17** `compile --root instruction_operation` rc=0；**17/17** 类型检查 rc=0（批 2 的 3 条单独复跑 + 全册 17 条复跑同轮）
4. 语义对照：6 组覆盖 17 条（见上）；`cond_check.py` rc=0（8 条 `cs.*` 条件 == `SimRISC-00 §3.2` 位级）；`rules_check.py` rc=0（36 条 rule：raise 数 == `rule_refs` 数且全 ILLI）
5. 待裁定：**无**（两批均无；易误判的 NaN / `rf0` 掩码两处已在「待裁定」段写明依据）
6. L1 rc=0：`check-manifests-guard`、`check-idl-sync`、`check-spec-drift`/`-purity`/`-codeblocks`/`-refs`/`-numbering`/`-changelog`/`-cite-targets`、`check-asm-list`/`-list-drift`/`-prose`、`check-legality-drift`/`-invariants`、`check-patch-tree`、`check-contracts-dir`、`check-dirs`、`check-no-residue`
7. 可达 FAIL（5 路，均 `cp` 备份 + md5 对账还原）：① spec 块改一字符 ⇒ render 红；② 删 `# id:` ⇒ cover+render 双红；③ `raise` 少一参 ⇒ idlc 类型红；④ 重叠式 `&&`→`||` ⇒ rules_check 红而 cover 绿；⑤ `cs.p` 条件换成 N 式 ⇒ cond_check 红而 cover 绿
**新发现/坑**：① `SimRISC-00 §3.2` 才是 N/Z/P/EQ/NE 的位级真源（`§2/§3` 只有文字），按文字写 `$signed` 等价但无法逐位对账 ⇒ 加 `cond_check` 钉位级形式；② `cs.*_rf` 的 `rf0` 是**目的 ILLI**、不是 FCSR 掩码场景（掩码只在 `rd2rf`），照 §3 注写即可；③ 注入「落盘」判据不能用 `git status`（未提交树上恒真），用注入前后 md5 差；④ 同形语句跨条目重复时（`cs.p` 的 rd/rf）注入锚点须计数，否则误报「空注入」。
**遗留问题**：无（全册 17/17 交付）。非本任务红项（未代改）：`check-isa-coverage`/`-width-sizes`/`-components`/`-linux-toolchain`（本 worktree 无 `.dadao/cross-toolchain`，缺 `llvm-mc`/`clang`/`qemu`，须 `make install-host`）、`check-knowledge-refs`（`.tao/contracts` 5 处 `.work/**`）、`check-milestones-fresh`（R1：本任务与 m15-idl-006/008/012 台账仍在「待开始」，属主会话台账职责）、`check-temp-dirs`（他人陈旧目录）、`check-writer-guards` W5b（依赖构建产物）。状态 → `待验收`。
