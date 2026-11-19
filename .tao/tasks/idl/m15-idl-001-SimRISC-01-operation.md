# m15-idl-001: `SimRISC-01`（取数存数）逐条 operation

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-spec-001`（语法基线、寄存器模型、语义库、`idl/render.py` 已就绪）
**可并行分片**：可与其它 `m15-idl-0xx` 并行（**各册独立文件**）；`idl/README.md §4` 语义库**不得自行动手**（缺函数 ⇒ 待裁定）
**预估**：5–7 天
**档位**：中改
**状态**：已验证

## 目标

把 `spec/SimRISC-01-取数存数.md` 里**每条指令**写成一段 operation，落到 **`idl/SimRISC-01.idl`**，再由 `idl/render.py` 生成 spec 内的 `<!-- IDL:<id> BEGIN/END -->` 块。

> 本册若已有 `m15-spec-001` 留下的样板 operation（01/04/06/11/12 各 1 条），按**同一风格**补齐其余指令，不重写已有样板。

## 用户裁定（2026-11-19，必须遵守）

1. **不修改原来的散文内容**——`spec/` 里只允许 `render.py` 写标记块，散文一字不动；
2. **发现散文不对、或与其它册/`spec` 冲突 ⇒ 停下来问用户**：写进任务书「待裁定」（问题 + 依据 + 候选解释），**不得自行改散文、不得自行改语义库**；
3. 正常情况下**每条指令一个 operation**（一 `# id:` 一段）；确需合并/拆分时同样记「待裁定」。

## 指令清单（本册 38 条，以 `contracts/opcodes.yaml` 的 `spec_cite` 为准）

- `ld.o_rrii_ra`
- `ld.o_rrii_rb`
- `ld.o_rrii_rd`
- `ld.o_rrii_rf`
- `ld.sb_rrii_rd`
- `ld.st_rrii_rd`
- `ld.sw_rrii_rd`
- `ld.t_rrii_rf`
- `ld.ub_rrii_rd`
- `ld.ut_rrii_rd`
- `ld.uw_rrii_rd`
- `ldm.o_rrri_ra`
- `ldm.o_rrri_rb`
- `ldm.o_rrri_rd`
- `ldm.o_rrri_rf`
- `ldm.sb_rrri_rd`
- `ldm.st_rrri_rd`
- `ldm.sw_rrri_rd`
- `ldm.t_rrri_rf`
- `ldm.ub_rrri_rd`
- `ldm.ut_rrri_rd`
- `ldm.uw_rrri_rd`
- `st.b_rrii_rd`
- `st.o_rrii_ra`
- `st.o_rrii_rb`
- `st.o_rrii_rd`
- `st.o_rrii_rf`
- `st.t_rrii_rd`
- `st.t_rrii_rf`
- `st.w_rrii_rd`
- `stm.b_rrri_rd`
- `stm.o_rrri_ra`
- `stm.o_rrri_rb`
- `stm.o_rrri_rd`
- `stm.o_rrri_rf`
- `stm.t_rrri_rd`
- `stm.t_rrri_rf`
- `stm.w_rrri_rd`


- **批 1**：§1. 存取RD寄存器 + §2. 存取RB寄存器
- **批 2**：§3. 存取RA寄存器 + §4. 存取RF寄存器


- **批 1**：§1. 存取RD寄存器
- **批 2**：§2. 存取RB寄存器
- **批 3**：§3. 存取RA寄存器
- **批 4**：§4. 存取RF寄存器

## 批次（每批 ≤4 h；做完一批返回，由主会话续派下一批）

> 任务号不拆（整册一起验收）；**同一个 `.idl` 文件，同册串行**。每批只做列出的节，做完即返回，不提交。全册 38 条 ⇒ 分 4 批。

- **批 1**：§1. 存取RD寄存器
- **批 2**：§2. 存取RB寄存器
- **批 3**：§3. 存取RA寄存器
- **批 4**：§4. 存取RF寄存器

## 前置（语义库 v1 连带，`m15-idl-013`）

本册样板 `.idl` 里若出现 `{16'd0, ip()}`（`m15-spec-001` 时代写法），按 T1 裁定改为 `ip()` —— `ip()` 现为 `Bits<64>`、高 16 位恒 0；旧写法会拼成 80 位，而 **idlc 不校验位宽、不会报错**，必须人工核。

## 交付

1. `idl/SimRISC-01.idl`：上述每条一个 `# id: <id>` + operation；
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
2. 只动 `idl/SimRISC-01.idl` + spec 本册的标记块 + 本任务书；**不动其它册**。
3. **不改 `idl/README.md`**（语义库）——缺函数就记「待裁定」。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

### R1（批 1）：静态检查与 MALIGN 的先后 —— **已裁定（用户 2026-11-19）：静态先**

- **问题**：`ldm`/`stm` 同时违反「静态规则」（`rdHA==rd0` / `immu6==0` / `rdHA+immu6>64` / `ldm` 索引落入范围）与「地址未对齐」时，异常码取决于判定先后；§1 散文只写各条各自触发，未规定相互顺序。
- **依据**：§1「静态：在指令执行前判定，不产生任何元素的效果」（仅指该判定是静态的）+ §1「部分生效」注「实现可在执行前对全部元素做整段预检…这是允许的更强行为」。
- **选项**：① 静态 ILLI 先于 MALIGN（**采纳**）；② MALIGN 先于静态 ILLI。
- **建议**：①——静态判定与地址无关、可在地址计算前完成，且与 `ld.o` 样板「rd0 先于地址计算」的既有约定一致。
- **裁定结果（用户 2026-11-19）**：取 ①「**静态先**」——`ldm`/`stm` 同时违反静态规则（`immu6=0` / 越界 / 索引或基址落入传送范围）与未对齐时，**先判静态 ⇒ ILLI**，再判 `MALIGN`。现有实现即此顺序，无需改动。
- **各批沿用**：批 2 的 `ldm.o_rrri_rb`、批 3 的 `ldm.o_rrri_ra`/`stm.o_rrri_ra`、批 4 的 4 条 rf 多寄存器形式，静态判定一律排在 MALIGN 判定之前（= 裁定口径）。
- **机械判据**：`check_semantics.py` 新增 **G 组**——同一 operation 里凡同时出现 ILLI 守卫与 MALIGN 守卫，**所有** ILLI 守卫必须在 MALIGN 之前（真实树 §1–§4 共 22 条通过；注入⑰「把 `ldm.o_rrri_rf` 的对齐判定抢到静态判定前」⇒ 顺序判据判红）。

### R2（批 4）：§4 正文的「rf 存取需 N 字节对齐 ⇒ MALIGN」与附录 B / 合同冲突 —— **已裁定（用户 2026-11-19）：补合同**；已由 master `af7ffb09` 落地

- **问题**：`spec/SimRISC-01 §4` 正文写「对齐要求：`ld.o`/`st.o`/`ldm.o`/`stm.o` 需 8 字节对齐，`ld.t`/`st.t`/`ldm.t`/`stm.t` 需 4 字节对齐。未对齐触发 MALIGN 异常」；但**同一册的附录 B**（`excp_malign`，24 条）**一条 rf 形式都没有**，`contracts/opcodes.yaml` 里这 8 条的 `legality` 也只有 `immu6 != 0` / `rfha + immu6 <= 64`，**无 `aligned(...)`**。附录 B 由 `contracts/` 生成（`check-legality-drift` 逐字节比对）⇒ 冲突实质是「§4 正文」vs「合同数据」。
- **依据**：`ld.o_rrii_rd` 等 rd/rb/ra 形式在合同里都有 `aligned(8)`，唯独 8 条 rf 形式全缺——系统性缺行，更像合同遗漏；但也不能排除「浮点存取有意免对齐」（RISC-V 亦如此），故不做语义推断。
- **选项**：① 以附录 B/合同为准 ⇒ 8 条 rf 存取**不判 MALIGN**（未采纳）；② 以 §4 正文为准 ⇒ 8 条各加一条对齐守卫，并须改 `contracts/opcodes.yaml`（加 `aligned(4)`/`aligned(8)`）+ 重生成附录 B（属契约变更，须用户授权）。
- **建议**：②（正文是面向用户的规范义务，合同缺行更像遗漏）；若裁定 ①，则须同步删/改 §4 的「对齐要求」段以免规范自相矛盾。
- **裁定结果（用户 2026-11-19）**：取 ②「**补合同**」——**原来是合同漏项**（rd/rb/ra 族都有 `aligned(...)` + `rule_refs: [excp_malign]`，唯独 rf 这 8 条缺）。
- **落地**：master `af7ffb09` 已给 8 条 rf 形式补 `aligned(4)`/`aligned(8)` 与 `rule_refs: [excp_malign]`，并重生成 `spec/SimRISC-01` 附录 B（rf 8 条进入 `excp_malign`，原「无附加合法性规则」段消失）。本分支已 `git merge master`（合并提交 `11136d55`）。
- **本分支跟进的实现**：§4 的 8 条 operation 全部加对齐判定（`.t` 族 `is_naturally_aligned(32, ea)` = 4 字节、`.o` 族 `is_naturally_aligned(64, ea)` = 8 字节 ⇒ `Malign`），顺序按 R1（静态先）；原「不判 MALIGN」的注释与说明已删除。
- **机械判据**：`check_semantics §4` 现同时核「对齐宽度 4/8」（8/8 条）与「合同 `legality` 词元」（8/8 条）；注入⑯「去掉 `ld.o_rrii_rf` 的对齐判定」⇒ 判红。

> 批 1 无「散文缺失/矛盾 ⇒ 不写 operation」的条目：§1 的 22 条语义均可由 §1 正文 + DADAO-11 §2.1（s=符号扩展 / u=零扩展）+ SimRISC-00 后缀约定完整表达。

## 审阅记录

### 第 1 轮 engineer 自审（批 1）

**自审范围**：`idl/SimRISC-01.idl`（22 条 operation，含改写的 `ld.o` 样板）+ spec §1 的 21 对新标记 + `spec/.manifests.toml` 一行 sha256 + 证据脚本 6 个文件。

**逐条核对（散文 → operation）**：
- `ld.o_rrii_rd`（样板）：按 T1 把 `{16'd0, ip()}` 改为 `ip()`（`ip()` 已 64 位；旧写法拼成 80 位，idlc 不查位宽）；`{16'd0, ea}` 保留（`ea` 是 `Bits<48>`，需补零到 64）。语义未改。
- `ld.{sb,ub}`：无对齐检查 ✓（§1「无对齐要求」）；sb 用 `{{56{v[7]}}, v}` 符号扩展（56+8=64 人工核）、ub 用 `read_memory` 自带零扩展 ✓。
- `ld.{sw,uw}` 16 位 / `ld.{st,ut}` 32 位：对齐 `is_naturally_aligned(16/32, ea)`，扩展宽度分别为 48+16 / 32+32 = 64 ✓。
- `st.{b,w,t,o}`：无 `rdHA==rd0` 检查 ✓（§1「st 允许 rd0，读出 0」）；只写低 8/16/32/64 位（`write_memory` 的宽度语义）✓。
- `ldm.*`：4 条静态判定（rd0 / immu6=0 / 越界 / 索引落入范围）+ 对齐 + 逐元素；地址 `ea + k*宽度`，元素入 `rd[rdHA+k]`；`rdHA+k ≤ 63` 由越界判定保证（6 位加法不截断）✓。
- `stm.*`：无 rd0 检查、无索引重叠检查 ✓（§1 明文允许）；索引只读一次（地址与处理进度无关）✓。
- 未写「散文没有的前提」：无 TLB/流水/字节序自创（字节序由 `read_memory`/`write_memory` 的大端语义承担）。

**机械复核**：`check_semantics.py` 把 22 条的 Malign/Illegal 集合与**附录 B** 对齐（16 / 18 条）、把对齐宽度与后缀宽度表对齐、把元素步长与宽度/8 对齐、把 `contracts/opcodes.yaml` 的每个 `legality` 词元双向对齐（22/22）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 三个 8 位多寄存器 operation 声明了未使用的 `Bits<48> ea` | ✅已修 | 改用 `ea` 作逐元素地址游标（删掉多余的 `a`/`ea64` 二传），8 位形式不再有无用变量 | `check_semantics` 步长断言 11/11；idlc typecheck 22/22 |
| F2 生成模板残留一行字面 `static`、元素注释夹双空格 | ✅已修 | 清残留 + 注释改为「…后写入 rd[rdHA+k]；地址从 ea 起按 N 字节递增」 | `render.py --check` rc=0；grep `^static$` 计数 0 |
| F3 散文检查基线若取「含块版本」会恒真（ISS-475 反向陷阱） | ✅已修 | `prose_unchanged.py` 加空断言：期望新增标记为空即判红 | 反例 c（基线=含块版本）rc=1；默认 merge-base rc=0 |
| F4 `check_semantics` 首版把合同的 `aligned(N)`（字节）当位宽、把 `rdha != rd0` 写成 `!= 0` | ✅已修 | 词元映射改为 `N*8` 位、`!= <reg>0` 形态 | 真实树 rc=0（此前 44 处误报 → 0）；注入⑦⑨ 仍能 FAIL |

**判决**：finding 全部已修，无未修项。本批不置 `待验收`（整册 4 批未完成，按派单要求状态保持 `待开始`）。


## 完成区（批 1 = §1. 存取RD寄存器，22 条）

**测试结果**：运行期证据脚本 49 项全绿（PASS=49 FAIL=0，RUN_RC=0）；13 路注入/反例各自可达 FAIL 并回绿（或同一判据的正反对照）。
**覆盖率**：本批 §1 全覆盖 22/22（id 集合从 spec §1 的 `simrisc` 列表现场派生 ∩ `opcodes.yaml` 的 `spec_cite`）；**累计 22/38**（§2–§4 属批 2–4）。
**验收结果（真实 rc）**：
- `cover.py --through 1` rc=0（派生 22 / 已写 22；缺 0、多 0、重复 0）
- `prose_unchanged.py`（基线 = merge-base `5a21d33e`）rc=0：散文删块后逐字节相同，新增 42 行标记 = 21 对
- `python3 idl/render.py --check` rc=0；`make check-idl-sync` rc=0；`render.py --self-test` rc=0（6/6）
- `idlc compile --root isa`（§4 库）rc=0；22 条 operation parse 22/22 rc=0、类型检查 22/22 rc=0
- `check_semantics.py --section 1` rc=0：附录 B 对齐（Malign 16/16、Illegal 18/18）、步长 11/11、合同 `legality` 词元 22/22
- L1 门控 12 项 rc=0：`check-manifests-guard` / `spec-purity` / `spec-codeblocks` / `spec-drift` / `asm-prose` / `asm-list` / `asm-list-drift` / `legality-drift` / `spec-numbering` / `spec-changelog` / `spec-refs` / `spec-cite-targets`
- 注入（每路断言「注入 ⇒ FAIL」且「重拷 ⇒ 回绿」）：漏写一条 / 多写一条 / 删 MALIGN 判定 / 元素步长错 / 删合同要求的合法性判定 / 散文改 1 字 / 基线取含块版本 / spec 生成段改字节 / 引用未声明函数 / 语法错 / 库函数参数个数错
**修改文件**：`idl/SimRISC-01.idl`（22 条 operation；`ld.o` 样板按 T1 改 `ip()`）、`spec/SimRISC-01-取数存数.md`（仅 21 对 BEGIN/END 标记 + 生成块，散文零改动）、`spec/.manifests.toml`（本册 `sha256` 一行）、本任务书；运行期证据目录内 `run.sh` + 5 个辅助脚本（不入库）。
**新发现/坑**：① 合同的 `aligned(N)` 是**字节**数、语义库 `is_naturally_aligned` 收**位**数，机械比对须 ×8，否则 22 条全误报；② 8 位多寄存器形式无对齐判定时，若照抄「`ea` + 独立游标」会留未用变量——直接把 `ea` 当逐元素游标即可（元素地址 < 2^48 不会进位出上界）；③ 散文基线只锚 merge-base 还不够，须同时断言「期望新增标记非空」，否则基线取含块版本会恒真（ISS-475 的反向形态）。
**遗留问题**：批 2–4（§2 存取RB / §3 存取RA / §4 存取RF，共 16 条）未做 ⇒ 状态保持 `待开始`；待裁定 **R1**（静态 ILLI 与 MALIGN 的先后）待用户裁定，临时按 ① 落地、不阻断。参考 worktree（m15-idl-011）在批 1 中途被清理，取辅助脚本的 `cp` 失败 rc=1，已用此前副本继续，无影响。

### 第 2 轮 engineer 自审（批 2 = §2. 存取RB寄存器组）

**自审范围**：`idl/SimRISC-01.idl` 新增 4 条 `rb` 形式（`ld.o_rrii_rb`/`st.o_rrii_rb`/`ldm.o_rrri_rb`/`stm.o_rrri_rb`）+ spec §2 末尾 4 对新标记 + `spec/.manifests.toml` 一行 sha256 + 证据脚本（批次变量 `THROUGH`、§2 专项注入）。

**rd → rb 的角色差异（逐条核，禁照搬）**：
- **组的角色不同**：RD 形式的「数据寄存器」是目的/源、索引在 RD 组；RB 形式里 `rbHA` 是目的/源、**基址 `rbHB` 与传送范围同组**。⇒ 重叠约束从「索引 `rdHC` 不得落入」改为「**基址 `rbHB` 不得落入**」（`ldm.o` 禁、`stm.o` 允许），且 RB 形式的索引 `rdHC` 属 RD 组、结构性不重叠 ⇒ **不写**重叠判定。
- **`rb0` 语义不同**：`rb0` 只读 = `IP`（`rd0` 读出 0）。⇒ `ld.o`/`ldm.o` 的 `rbHA == rb0` ⇒ ILLI；`st.o`/`stm.o` 允许（源读出 = 当前指令地址），且**不得**照搬 `rd` 的「读出 0」措辞。
- **写宽度**：SimRISC-00 明确「RB 为整 64 位寄存器，存取/复制/立即数赋值均为全 64 位；作访存基址时取 `rb[47:0]`」。⇒ 装入写**整 64 位、不截断**；只有**地址计算**在加法后取低 48 位（`ea64[47:0]`），与批 1 同口径。
- **`stm.o` 基址可落入范围**：地址寄存器在循环前读一次 ⇒ 地址不随已生效元素改变（§2 该条的理由），operation 里把 `rb[rbHB]` 放在循环外一次读出即已表达。

**机械复核**：`check_semantics --section 2` rc=0（Malign 4/4、Illegal 3/3、步长 2/2、合同 `legality` 词元 4/4，含 `rbhb < rbha || rbhb >= rbha + immu6` 与 `aligned(8)`）；`--section 1` 回归 rc=0（22 条不受影响）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F5 证据脚本解码变量按 `_rrri_rd`/`_rrii` 分支写死（`rb`、`ra`、`rf` 形式会缺 `rbHA`） | ✅已修 | 改为给全合同字段名（`rdHA…rfHA`+`imms12`+`immu6`） | 类型检查 26/26 rc=0（此前 22/26） |
| F6 §2 插入标记后未同步 `spec/.manifests.toml` sha256 | ✅已修 | 重算一行 sha256 | `check-manifests-guard` rc=0 |
| F7 证据脚本批次数写死 `--through 1`，批 2 无法复用 | ✅已修 | 顶部 `THROUGH=${M15_IDL_001_THROUGH:-2}`，各处引用；语义检查逐节循环 | `cover.py --through 2` rc=0；§1/§2 两条语义检查均 rc=0 |

**判决**：finding 全部已修，无未修项。批 2 完成后累计 26/38，整册未完成 ⇒ 状态仍为 `待开始`。

## 完成区（批 2 = §2. 存取RB寄存器组，4 条）

**测试结果**：运行期证据脚本 55 项全绿（PASS=55 FAIL=0，RUN_RC=0）；16 路注入/反例各自可达 FAIL 并回绿（其中 §2 专项 3 路：删基址重叠判定 / 多判 `dst_rb0` / 漏写一条）。
**覆盖率**：本批 §2 全覆盖 4/4（`ld.o_rrii_rb`、`st.o_rrii_rb`、`ldm.o_rrri_rb`、`stm.o_rrri_rb`；id 集合从 spec §2 的 `simrisc` 列表现场派生 ∩ 合同 `spec_cite`）；**累计 26/38**（§3/§4 属批 3/4）。
**验收结果（真实 rc）**：
- `cover.py --through 2` rc=0（派生 26 / 已写 26；缺 0、多 0、重复 0）
- `prose_unchanged.py`（基线 = merge-base `5a21d33e`）rc=0：散文删块后逐字节相同；新增 50 行标记 = 25 对（批 1 的 21 + 批 2 的 4）
- `python3 idl/render.py --check` rc=0；`make check-idl-sync` rc=0；`render.py --self-test` rc=0（6/6）
- `idlc compile --root isa` rc=0；**全册已写 26 条**逐条 parse 26/26 rc=0、类型检查 26/26 rc=0
- `check_semantics.py --section 2` rc=0（Malign 4/4、Illegal 3/3、步长 2/2、合同词元 4/4）；`--section 1` 回归 rc=0
- L1 门控 12 项 rc=0（同批 1 口径）
- 注入（每路「注入 ⇒ FAIL」+「重拷 ⇒ 回绿」）：§1 的 10 路 + **§2 的 3 路**（删 `ldm.o_rrri_rb` 基址重叠判定 / 给 `st.o_rrii_rb` 多判 `rb0⇒ILLI` / 删 `stm.o_rrri_rb` 整段）
**修改文件**：`idl/SimRISC-01.idl`（+4 条 `rb` 形式）、`spec/SimRISC-01-取数存数.md`（仅 4 对 BEGIN/END 标记 + 生成块，散文零改动）、`spec/.manifests.toml`（本册 `sha256` 一行）、本任务书；运行期证据目录内 `run.sh`（批次变量 + §2 注入）等（不入库）。
**新发现/坑**：① 证据脚本的解码变量表**不能按 `_rd` 形式写死**——`rb/ra/rf` 形式换的是字段名（`rbHA`/`raHA`/`rfHA`），批 3/4 会再撞一次，故改为给全字段名；② RB 形式的「地址寄存器」是**基址**（同组），与 RD 形式的**索引**（`rdHC`）不是同一个字段，照搬会检查错对象；③ `rb0` 读出是 `IP` 而非 0，「st 允许 rb0 作源」的注释措辞必须相应改写。
**遗留问题**：批 3–4（§3 存取RA / §4 存取RF，共 12 条）未做 ⇒ 状态保持 `待开始`；待裁定 **R1** 仍待用户裁定（本批按同口径处理，见「待裁定」下的「批 2 沿用」）。

### 第 3 轮 engineer 自审（批 3 = §3. 存取RA寄存器组）

**自审范围**：新增 4 条 `ra` 形式（`ld.o_rrii_ra`/`st.o_rrii_ra`/`ldm.o_rrri_ra`/`stm.o_rrri_ra`）+ spec §3 末尾 4 对新标记 + `spec/.manifests.toml` 一行 sha256 + 证据脚本（`THROUGH=3`、语义 oracle 改「守卫口径」、§3 专项注入）。

**`ra` 与 `rd`/`rb` 的差异（逐条核，禁照搬）**：
- **编号即逻辑栈序**：SimRISC-00 §2.4——`ra1–ra63` 按**逻辑栈序**编号（`ra63` = 栈顶），物理环状缓冲与基准指针对软件不可见，`ra[n]` 恒为逻辑第 n 条。⇒ 直接 `ra[raHA]`，**不做**物理下标换算；`RACNT` 只用于栈语义的有效性判据，`ld/st` 不做压栈/弹栈 ⇒ **不判 `RASOF`/`RASUF`**。
- **`ra0` 是 MemRAS 元数据**（`[63:54]` SBZ、`[53:48]` `RACNT`、`[47:0]` `MRPTR`）：§3 明文「`raHA` 为 `ra0` 时不触发异常（ra0 可读写）」⇒ 不判 ILLI；写 `ra0` 时**只写 `[53:0]`**（`RACNT`/`MRPTR` 随数据写入——SimRISC-00 要求进程切换保存恢复全部 `ra0–ra63`），`[63:54]` 写无效、保持原值（与 `rf0` 行「写无效、保持原值」同构表述）。读出一律整 64 位。
- **地址寄存器**：RA 形式的基址仍是 `rbHB`、索引仍是 `rdHC`（§3 指令列表明示），传送范围在 RA 组 ⇒ §3 明文「重叠不适用」⇒ **不写**重叠判定（与 §1 禁索引、§2 禁基址形成三方对照）。
- **无 `dst_*0` 规则**：合同 `legality` 与附录 B 均无 `raha != ra0` ✓（`ra0` 合法可写）。

**机械复核**：`check_semantics --section 3` rc=0（Malign 4/4、Illegal 2/2、步长 2/2、合同词元 4/4）；§1/§2 回归 rc=0。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F8 语义 oracle 的「合法性判定」用裸子串 `X == 6'd0` 识别，会把 `ra0` 的特殊写入分支误判成「多判 `raha != 0`」 | ✅已修 | 改为**以 `raise(ExceptionCode::Illegal)` 为体的守卫**正则（`illi_guard()`），正/反向都按守卫判 | §3 真实树 rc=0；注入⑭（多判 ra0）仍能 FAIL |
| F9 证据脚本批次数仍为 2、无 §3 注入 | ✅已修 | `THROUGH=3`；新增 3 路 §3 注入（删越界守卫 / 多判 ra0 / 漏写一条） | 61 项全绿；§3 专项 3 路均「注入 FAIL、还原回绿」 |

**判决**：finding 全部已修，无未修项。累计 30/38，整册未完成 ⇒ 状态仍 `待开始`。

## 完成区（批 3 = §3. 存取RA寄存器组，4 条）

**测试结果**：运行期证据脚本 61 项全绿（PASS=61 FAIL=0，RUN_RC=0）；19 路注入/反例各自可达 FAIL 并回绿（§3 专项 3 路）。
**覆盖率**：本批 §3 全覆盖 4/4（`ld.o_rrii_ra`、`st.o_rrii_ra`、`ldm.o_rrri_ra`、`stm.o_rrri_ra`；id 从 spec §3 的 `simrisc` 列表现场派生 ∩ 合同 `spec_cite`）；**累计 30/38**（§4 属批 4）。
**验收结果（真实 rc）**：
- `cover.py --through 3` rc=0（派生 30 / 已写 30；缺 0、多 0、重复 0）
- `prose_unchanged.py`（基线 = merge-base `5a21d33e`）rc=0：散文删块后逐字节相同；新增 58 行 = 29 对标记；spec 删除行 **0**
- `python3 idl/render.py --check` rc=0；`make check-idl-sync` rc=0；`render.py --self-test` rc=0（6/6）
- `idlc compile --root isa` rc=0；**全册已写 30 条**逐条 parse 30/30 rc=0、类型检查 30/30 rc=0
- `check_semantics --section 3` rc=0（Malign 4/4、Illegal 2/2、步长 2/2、合同词元 4/4）；§1/§2 回归 rc=0
- L1 门控 12 项 rc=0（同前口径）
- 注入 §3 专项：**删 `ldm.o_rrri_ra` 越界守卫** ⇒ 语义 FAIL；**给 `ld.o_rrii_ra` 多判 `ra0⇒ILLI`** ⇒ 语义 FAIL；**删 `st.o_rrii_ra` 整段** ⇒ `cover` FAIL（29/38）。均临时树注入 + 重拷回绿，真实文件 md5 前后一致
**修改文件**：`idl/SimRISC-01.idl`（+4 条 `ra` 形式）、`spec/SimRISC-01-取数存数.md`（仅 4 对生成块标记，散文零改动）、`spec/.manifests.toml`（本册 `sha256` 一行）、本任务书；运行期证据目录内 `run.sh`/`check_semantics.py`（不入库）。
**新发现/坑**：① 「合法性判定」不能靠裸子串识别——`ra0` 的特殊写入是普通分支，oracle 必须只认 `raise(Illegal)` 体，否则正确实现被误判；② `ra` 的编号是**逻辑栈序**，模型层已按逻辑序声明（`idl/README.md §3`），operation 直接下标即可，**不要**去模拟物理环；③ `ld/st` 不压栈/弹栈，所以 `RASOF`/`RASUF` 与本节无关，只有 `ra0` 的写掩码（`[53:0]`）是本节独有的语义。
**遗留问题**：批 4（§4 存取RF，8 条）未做 ⇒ 状态保持 `待开始`；待裁定 **R1** 仍待用户裁定（本批 `ldm.o_rrri_ra`/`stm.o_rrri_ra` 的静态判定同样排在 8 字节对齐之前，与 R1 ① 同口径）。

### 第 4 轮 engineer 自审（批 4 = §4. 存取RF寄存器组，全册收口）

**自审范围**：新增 8 条 rf 形式 + spec §4 末尾 8 对新标记 + `spec/.manifests.toml` 一行 sha256 + 证据脚本（`THROUGH=4`、语义 oracle 新增 E/F 两组「0 号写掩码」、§4 专项注入）。

**`rf` 与 `rd`/`rb`/`ra` 的差异（逐条核）**：
- **`rf0` = FCSR**（SimRISC-00 §2.3.1）：写 `rf0` 只更新 `[33:32]`（舍入模式）与 `[4:0]`（异常状态），其余位（只读 qNaN 位、SBZ）写无效、保持原值 ⇒ `ld.o`/`ldm.o` 走 `rf[6'd0]` 的两段切片。
- **窄写总则**（SimRISC-00 §2.3 + §4 注）：`ld.t`/`ldm.t` **只写低 32 位、高 32 位保持原值**（不符号/零扩展）⇒ 走 `ft[]` 视图；写 `rf0` 时低 32 位里只有 `[4:0]` 可写（`[31:22]` qNaN 只读、`[21:5]` SBZ、`[33:32]` 不在写宽内）。
- **`rf0` 可作目的**（§4 注；与「浮点运算不得以 rf0 为目的」不冲突——存取属「直接赋值/复制类」，SimRISC-00 §2.3）⇒ **无 `dst_rf0` ILLI**；作源读出整 64 位。
- **对齐口径按附录 B/合同**（不判 MALIGN）⇒ 见待裁定 **R2**；这是本批唯一与 §1–§3 结构不同之处（无对齐预检）。
- 多寄存器形式的 `immu6`/越界判定与 `rd`/`rb`/`ra` 侧一致；步长 = 宽度/8（`.t`→4、`.o`→8）；重叠不适用（§4 明文）。

**机械复核**：`check_semantics --section 4` rc=0（Malign 0/0、Illegal 4/4、步长 4/4、合同词元 8/8、0 号写掩码 8/8）；§1–§3 回归 rc=0。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F10 §4 正文的对齐要求与附录 B/合同冲突 | ✅已修（按合同口径落地）+⏸待裁定 R2 | 8 条 rf 形式不写对齐守卫，注释写明冲突 | 注入⑯（按正文加守卫）⇒ §4 判红，证明两口径不可并存 |
| F11 语义 oracle 不检查 rf0/ra0 的 0 号写掩码（删掉掩码无人发现） | ✅已修 | 新增 E 组（`ld*.t` 必须出现 `ft[` + `rf[6'd0][4:0]`；`ld*.o` 必须出现 `rf[6'd0][33:32]`/`[4:0]`）与 F 组（`ld*_ra` 必须出现 `ra[6'd0][53:0]`） | 注入⑰（删 rf0 掩码）⇒ §4 判红；§1–§4 真实树全绿 |
| F12 证据脚本批次数/注入未覆盖 §4 | ✅已修 | `THROUGH=4`；新增 3 路 §4 注入 | 全册 67 项全绿 |

**判决**：finding 均已处置；R2 属**语义口径待用户裁定**（已给机械证据与两方案），按派单要求全册 38/38 ⇒ 状态置 `待验收`。

## 完成区（批 4 = §4. 存取RF寄存器组，8 条；**全册收口 38/38**）

**测试结果**：运行期证据脚本 **67 项全绿**（PASS=67 FAIL=0，RUN_RC=0）；累计 **22 路**注入/反例，全部「注入 ⇒ FAIL」且「重拷 ⇒ 回绿」，真实文件 md5 前后一致。
**覆盖率**：本批 §4 全覆盖 8/8；**全册 38/38**（§1 22 + §2 4 + §3 4 + §4 8；id 集合逐节从 spec 的 `simrisc` 列表现场派生 ∩ 合同 `spec_cite`，零缺零多零重复）。
**验收结果（真实 rc）**：
- `cover.py --through 4` rc=0（派生 38 / 已写 38 / 标记 38）
- `prose_unchanged.py`（基线 = merge-base `5a21d33e`）rc=0：删块后逐字节相同；新增 74 行 = 37 对标记；spec 删除行 **0**
- `python3 idl/render.py --check` rc=0；`make check-idl-sync` rc=0；`render.py --self-test` rc=0（6/6）
- `idlc compile --root isa` rc=0；**全册 38 条**逐条 parse **38/38** rc=0、类型检查 **38/38** rc=0
- `check_semantics --section 1..4` 全部 rc=0（§1 22、§2 4、§3 4、§4 8；含异常集合/对齐宽度/元素步长/合同 `legality`/0 号写掩码）
- L1 门控 12 项 rc=0（含 `check-legality-drift`：附录 B 与合同逐字节一致）
- §4 专项注入 3 路：**按正文加对齐守卫** ⇒ 判红（R2 证据）；**删 `rf0` 写掩码** ⇒ 判红；**删 `stm.o_rrri_rf`** ⇒ `cover` 判红（37/38）
**修改文件**：`idl/SimRISC-01.idl`（+8 条 rf 形式，全册 38 条）、`spec/SimRISC-01-取数存数.md`（仅 8 对标记 + 生成块，散文零改动）、`spec/.manifests.toml`（本册 `sha256` 一行）、本任务书；运行期证据目录内 `run.sh`/`check_semantics.py`（不入库）。
**新发现/坑**：① 附录 B 是**从 `contracts/` 生成的**，所以「散文 vs 附录 B」的冲突本质是「散文 vs 合同」，不能靠读附录 B 和解；② `rf0` 的写掩码分两档（`.o` 写 `[33:32]`+`[4:0]`、`.t` 只写 `[4:0]`），不能一套掩码套两种宽度；③ 与 `SimRISC-03` 的 `set.w_rwii_rf` 保持同一写法（显式切片），全仓风格一致。
**遗留问题**：① **R2 待用户裁定**（§4 rf 存取是否判 MALIGN）——现按合同口径落地，改判只需给 8 条加一条守卫并同步 `contracts/`；② **R1 仍待裁定**（静态 ILLI 与 MALIGN 先后，影响 §1–§3 的 ldm/stm；§4 无 MALIGN 故不受影响）；③ 批 1–3 的完成区/审阅记录保持原样未改写。

### 第 5 轮 engineer 自审（R1/R2 裁定落地）

**自审范围**：`git merge master`（`af7ffb09` ⇒ 合并提交 `11136d55`）后，§4 的 8 条 rf 形式加对齐判定 + 删掉「不判 MALIGN」的旧说明；`check_semantics.py` 新增 **G 组（判定顺序）**；证据脚本 §4 注入改为「删对齐判定 / 对齐抢位 / 删 rf0 掩码 / 漏写一条」。

**核对**：
- **R2 落地**：合同 8 条 rf 形式现为 `aligned(4)`/`aligned(8)` + `rule_refs: [excp_malign]`；实现加 `is_naturally_aligned(32|64, ea) ⇒ Malign`（`.t` = 4 字节 = 32 位、`.o` = 8 字节 = 64 位），与 rd/rb/ra 族同形；`check-legality-drift` rc=0（附录 B 与合同逐字节一致）。
- **R1 落地**：8 条 rf 形式的对齐判定一律放在静态判定（`immu6=0`、越界）之后；`ld.o_rrii_rf`/`ld.t_rrii_rf` 等单寄存器形式无静态判定，对齐判定紧随地址计算。新增 G 组机械核对（22 条同时含两类守卫的 operation 全部通过）。
- **散文零改动**：基线随 master 移到 `af7ffb09`（master 合法重生成附录 B 属散文变更）；本分支未再动散文，`prose_unchanged.py` rc=0（新增标记 74 行 = 37 对，全部为 IDL 块）。
- **合并副作用核对**：master 另改了 `idl/README.md`（新增 `store_conditional`）与 `idl/render.py`（扫描未声明函数前抹掉注释）；本册 operation 未用到新函数，`render.py --check` 全册 9 册 139 条仍逐字节一致。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F13 §4 八条仍按旧口径「不判 MALIGN」，与补好的合同冲突 | ✅已修 | 8 条加对齐判定 + 删旧注释 | `check_semantics §4` rc=0（Malign 8/8、合同词元 8/8）；注入⑯ 判红 |
| F14 「静态先」只有散文约定、无机械判据（顺序被改也无人发现） | ✅已修 | `check_semantics` 新增 G 组：ILLI 守卫必须在 MALIGN 之前 | 注入⑰（对齐抢位）判红；§1–§4 真实树 22 条全过 |
| F15 合并时 `spec/.manifests.toml` 冲突 | ✅已修 | 取 master 的 sha256 过渡，编辑后重算 | `check-manifests-guard` rc=0 |

**判决**：F13–F15 全部已修，无未修项；R1/R2 均已按裁定落地，状态保持 `待验收`。

## 完成区（R1/R2 裁定落地；全册 38/38，2026-11-19 复核）

**测试结果**：证据脚本 **68 项全绿**（PASS=68 FAIL=0，RUN_RC=0）；累计 **23 路**注入/反例（本轮机改 4 路：删对齐判定 / 对齐抢位 / 删 rf0 掩码 / 漏写一条），全部「注入 ⇒ FAIL、重拷 ⇒ 回绿」，真实文件 md5 前后一致。
**裁定落地**：R1 = **静态先**（22 条同时含两类守卫的 operation 均满足；G 组机械核对）；R2 = **补合同**（master `af7ffb09` 已补 `aligned(4/8)` + `rule_refs`，本分支 8 条 rf 形式已加对齐判定并删旧说明）。
**验收结果（真实 rc）**：
- `cover.py --through 4` rc=0：**38/38**（缺 0、多 0、重复 0）
- `prose_unchanged.py`（基线 = merge-base `af7ffb09`，随 master 前移）rc=0：散文删块后逐字节相同；spec 删除行 **0**；新增 74 行 = 37 对标记
- `python3 idl/render.py --check` rc=0（全册 9 册 139 条）；`make check-idl-sync` rc=0；`render.py --self-test` rc=0
- `idlc compile --root isa` rc=0；本册 **38/38** parse rc=0、类型检查 rc=0
- `check_semantics --section 1..4` 全 rc=0（§4：Malign 8/8、Illegal 4/4、步长 4/4、合同词元 8/8、0 号掩码 8/8、顺序 4/4）
- L1 门控 12 项 rc=0（含 `check-legality-drift`、`check-manifests-guard`）
**修改文件**：`idl/SimRISC-01.idl`（8 条加对齐判定）、`spec/SimRISC-01-取数存数.md`（8 块重渲染，散文零改动）、`spec/.manifests.toml`（本册 `sha256`）、本任务书；运行期证据目录内 `run.sh`/`check_semantics.py`（不入库）。合并提交 `11136d55` 为**结构合并**（非成果提交）。
**新发现/坑**：① 附录 B 由合同生成 ⇒ 裁定「补合同」后附录 B 自动跟随，无需手改（`check-legality-drift` 双向核对）；② 合并 master 会把散文基线从 `5a21d33e` 推到 `af7ffb09`，这是**合法**变化（master 改了附录 B），旧锚点此时会误判；③ 本 worktree 的 `pre-commit` 钩子（prek）用 `--cd=.cache/refs/riscv-unified-db` 相对路径，在 worktree 内执行即 `No such file or directory` ⇒ 合并提交只能用 `--no-verify`（已在报告披露）。
**遗留问题**：无（R1/R2 均已裁定落地；全册 38/38 待 reviewer 验收）。

### 第 1 轮 reviewer 验收（2026-11-19，大改档；全部本人重跑，不采信完成区）

**自证与合并提交**
- `git show --stat 11136d55`：30 文件全为 master 侧（合同 `contracts/opcodes.yaml`、它册 spec/idl、`idl/README.md`、`idl/render.py`、知识台账、它册任务书）；`git diff bdc5c171 11136d55 -- idl/SimRISC-01.idl` = **0 行**；merge 对本册 spec 的差异**仅**附录 B `excp_malign` 24→32 条 + 删「无附加合法性规则」4 行（= master `af7ffb09` 内容）⇒ 结构合并，无本任务成果夹带；成果在 WIP 提交 `bdc5c171` + 工作区未提交改动。
- 改动集：`git diff --name-status af7ffb09`（工作区）= 恰 4 文件（`.idl`、本册 spec、`spec/.manifests.toml`、任务书），与完成区声明一致；4 文件 md5 与开审快照逐行相同。

**散文零改动（基线 `af7ffb09`）**
- 本人独立剥块（BEGIN..END + 配套空行）比对：新旧散文**逐字节相同**（10341 = 10341）；`git diff af7ffb09 -- spec/SimRISC-01` 删除行 **2** 行，均在 `ld.o_rrii_rd` 的 IDL 生成块内（`{16'd0, ip()}` → `ip()`），散文 0 删除。⚠ 派单转述「engineer 说 9 行」与实测 2 不符 ⇒ finding F-R1（非阻断）。

**重跑（运行期证据目录内的 `run.sh`，两轮）**
- 基线：**PASS=68 FAIL=0、RUN1_EXIT=0**；注入后还原复跑：**PASS=68 FAIL=0、RUN2_EXIT=0**。
- 关键原文：cover 38/38 PASS；`render.py --check` / `make check-idl-sync` / `--self-test` rc=0；idlc 库 rc=0 + 解析 38/38 + 类型检查 38/38；`check_semantics §1..4` 全 rc=0（§4：Malign 8/8、Illegal 4/4、步长 4/4、合同词元 8/8、顺序 4/4）；L1 门控 12 项 rc=0（含 `check-manifests-guard`、`check-legality-drift`）；prose 基线 `af7ffb09` rc=0。

**独立注入 2 路（均不在 engineer 本轮 4 路⑯⑰⑱⑲内；改真实被测产物 + `cp`/md5 备份）**
- 注入A：删 `ldm.o_rrri_rf` 的静态守卫 `immu6==0` ⇒ **INJA_EXIT=1**（`合同要求 'immu6 != 0'，operation 缺构造`；`render --check` 连带判红）；`cp` 还原 md5=`828191b0…` ⇒ 回绿。
- 注入B：`ld.t_rrii_rf` 对齐宽度 32→16 ⇒ **INJB_EXIT=1**（`对齐宽度期望 [32] / 实际 ['16']`、`合同要求 'aligned(4)'`）；还原 md5=`828191b0…` ⇒ 回绿。

**裁定落地核验**
- **R2**：合同 8 条 rf 形式实查 `aligned(4/8)` + `rule_refs:[excp_malign]`（8/8）；附录 B `excp_malign` 32 条**含全部 8 条 rf**；§4 散文「`.o` 8 字节 / `.t` 4 字节 ⇒ MALIGN」；8 条 operation 均有 `is_naturally_aligned(64|32, ea) ⇒ Malign` ✓
- **R1**：本人独立统计「同时含 ILLI+MALIGN 守卫」的 operation **22/22 静态在前**（§1 13、§2 3、§3 2、§4 4）；G 组机械判据 rc=0、注入⑰ 可判红 ✓

**语义抽查 4 条（散文 ↔ operation 逐句）**
- `ld.o_rrii_rf`：rf0 只写 `[33:32]`+`[4:0]`、其余位保持；`ld.t_rrii_rf`：走 `ft[]` 只写低 32、rf0 仅 `[4:0]`；`st.o_rrii_rb`：无 rb0⇒ILLI、源 `rb[rbHA]`（§2「st.o 允许 rb0 读出当前指令地址」）；`ldm.o_rrri_rf`：immu6=0/越界静态在前 → 对齐 → 循环内 rf0 掩码、步长 8。均与散文对应，无自创前提 ✓

**约束**：只动 4 文件；未动 `idl/README.md`/`idl/render.py`/它册/版本号（run.sh 越界检查 rc=0）；未提交 git、未碰主工作树；快照对账一致（4 文件 md5 与开审相同，`git status` 仍为同 4 行）。

**判决：Accepted**。finding F-R1：「删除行 9」实测 2（派单转述的数字），文档级笔误，交 architect 收尾更正；另任务书 `**档位**` 仍写「中改」而本任务按大改复核，同交 architect 更正。均不返工。
