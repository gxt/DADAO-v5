# m15-idl-009: `SimRISC-09`（16位数据运算）逐条 operation

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-spec-001`（语法基线、寄存器模型、语义库、`idl/render.py` 已就绪）
**可并行分片**：可与其它 `m15-idl-0xx` 并行（**各册独立文件**）；`idl/README.md §4` 语义库**不得自行动手**（缺函数 ⇒ 待裁定）
**预估**：3–5 天
**档位**：中改
**状态**：已验证

## 目标

把 `spec/SimRISC-09-16位数据运算.md` 里**每条指令**写成一段 operation，落到 **`idl/SimRISC-09.idl`**，再由 `idl/render.py` 生成 spec 内的 `<!-- IDL:<id> BEGIN/END -->` 块。

> 本册若已有 `m15-spec-001` 留下的样板 operation（01/04/06/11/12 各 1 条），按**同一风格**补齐其余指令，不重写已有样板。

## 用户裁定（2026-11-19，必须遵守）

1. **不修改原来的散文内容**——`spec/` 里只允许 `render.py` 写标记块，散文一字不动；
2. **发现散文不对、或与其它册/`spec` 冲突 ⇒ 停下来问用户**：写进任务书「待裁定」（问题 + 依据 + 候选解释），**不得自行改散文、不得自行改语义库**；
3. 正常情况下**每条指令一个 operation**（一 `# id:` 一段）；确需合并/拆分时同样记「待裁定」。

## 指令清单（本册 21 条，以 `contracts/opcodes.yaml` 的 `spec_cite` 为准）

- `add.sw_orrr_rd`
- `add.uw_orrr_rd`
- `cmp.sw_orrr_rd`
- `cmp.uw_orrr_rd`
- `div.sw_orrr_rd`
- `div.uw_orrr_rd`
- `mul.sw_orrr_rd`
- `mul.uw_orrr_rd`
- `rem.sw_orrr_rd`
- `rem.uw_orrr_rd`
- `rev.w_orri_rd`
- `rol.w_orri_rd`
- `rol.w_orrr_rd`
- `shl.w_orri_rd`
- `shl.w_orrr_rd`
- `shr.sw_orri_rd`
- `shr.sw_orrr_rd`
- `shr.uw_orri_rd`
- `shr.uw_orrr_rd`
- `sub.sw_orrr_rd`
- `sub.uw_orrr_rd`

- **批 1**：§1. 算术运算类指令
- **批 2**：§2. Bit manipulating：位操作指令 — 值语义

## 批次（每批 ≤4 h；做完一批返回，由主会话续派下一批）

> 任务号不拆（整册一起验收）；**同一个 `.idl` 文件，同册串行**。每批只做列出的节，做完即返回，不提交。全册 21 条 ⇒ 分 2 批。

- **批 1**：§1. 算术运算类指令
- **批 2**：§2. Bit manipulating：位操作指令 — 值语义

## 交付

1. `idl/SimRISC-09.idl`：上述每条一个 `# id: <id>` + operation；
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
2. 只动 `idl/SimRISC-09.idl` + spec 本册的标记块 + 本任务书；**不动其它册**。
3. **不改 `idl/README.md`**（语义库）——缺函数就记「待裁定」。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

（全册无。§2 的两处易混口径已逐条核对、均无冲突：① `rev.w` 的 `k=8` 括号「须源高 48 位为 0」
是 **bswap16 的用途映射前提**（SimRISC-04 §2.2.1「用途映射（供后端参考）」），指令本体仍按
四块同法处理；② §2 表把 `rdHD[3:0]` 写作**寄存器内容**，IDL 落到 `rd[rdHD][3:0]`
（解码变量 `rdHD` 是寄存器号，见 `idl/README.md` §2/§3）。逐句对照见运行期证据目录内 `sem-check.md`。）

## 完成区

**测试结果**：全册 21/21 条 id 零缺零多；正例 11/11 全绿；注入 9/9 均「注入⇒FAIL⇒cp 还原⇒回绿」；`run.sh` 全量 rc=0。
**修改文件**：`idl/SimRISC-09.idl`（新增 21 条 = §1 算术 12 + §2 位操作 9）；
`spec/SimRISC-09-16位数据运算.md`（**只加** 21 对 IDL 标记，`+470 −0`，散文零改动）；
`idl/.manifests.toml`（+本册一行）；`spec/.manifests.toml`（本册 sha256 `01ceb917…`→`1e7a64f8…`）；本任务书。
**验收结果**（运行期证据目录内 `run.sh`）：
- `cov`：`书内 id 总数=21`、`批 1 §1 12/12；批 2 §2 9/9`（零缺零多）
- `prose`：`merge-base=4029147e…`、`+470 -0`、剔除标记块后逐字节相等（6697 字符）
- `fixed`：`div.sw`/`div.uw` 表值 == .idl 字面量；`rem.sw` 除零⇒被除数符号扩展、溢出⇒0；`rem.uw` 除零⇒被除数零扩展
- `sem`：§1 `12 条 × 14 组 = 168 组，失配 0`；`rdHB=rd0 ⇒ ILLI：21 条中未判非法 0 条`
- `shift`：`8 条结构 + 240 组公式对账 + 越界判定；失配 0`（`immu6>15`⇒ILLI；`orrr` 取 `rd[rdHD][3:0]` 不抛）
- `rev`：`结构 3 项 + 4 个 k × 4 源值 + 2 项口径区分 + 10 个非法 k；失配 0`（k=1 非 64 位反序、k=8 非 bswap64）
- `width`（类型求解）：`104 条，失配 0`；`idlc`：库 rc=0、21 条 parse+typecheck 全 PASS
- `render --check` rc=0（96 条 / 10 册 / 96 块）；`manifests-guard` 与 `spec-purity`/`spec-codeblocks`/`numbering`/`asm-list`/`legality-drift`/`idl-sync` 全 rc=0
**新发现/坑**：
1. `idlc` 的 `/`、`%` 有符号下是 floor（Ruby）：`div.sw`/`rem.sw` 须在原宽度取绝对值（`16'd0 - src1`）再做无符号除法，最后按符号取负。
2. 位宽断言用 `compile_expression(...).type.width`：`{{32{…}}, sum}`、`rd[rdHD][4:0]` 这类缩/扩宽错误**能编译通过**，只有类型求解抓得到。
3. **`orrr` 的 shamt 必须写 `rd[rdHD][3:0]`**（`rdHD` 是 6 位寄存器号）；已合入的 `idl/SimRISC-10.idl` 4 处疑同类缺陷，建议转 reviewer：
   `rol.b_orrr_rd`(243)、`shl.b_orrr_rd`(273)、`shr.sb_orrr_rd`(304)、`shr.ub_orrr_rd`(332)，原文 `Bits<3> shamt = rdHD[2:0];`。
4. 第 1 轮报的 `m15-idl-008 rem.st` **撤回**：当时是 WIP 中途快照（除零档 `64'd0`）；现分支 `93ed5752` 为 `{{32{a[31]}}, a}`，与定值表一致。
5. 任务书重复且矛盾的批次行已删（4 行，只留与「## 批次」一致的一份）。
**遗留问题**：无（全册 21/21；`**状态**` → `待验收`）。

## 审阅记录

### 第 1 轮 engineer 自审（批 1）

逐行审查 `idl/SimRISC-09.idl` 12 条 + spec 标记落点 + 清单改动：

1. 符号扩展宽度逐条核对：`add/sub/mul/div/rem.sw` 均 `{{48{x[15]}}, x}`（48+16=64），
   `.uw` 均 `{48'd0, x}`；`cmp` 三档 `{64{1'b1}}`/`64'd0`/`64'd1`。类型求解 66 条断言零失配。
2. 截断方向（C99 vs IDL floor）：`div.sw`/`rem.sw` 全程避免有符号 `/`、`%`；
   `16'd0 - src1` 在原 16 位取负（`|INT16_MIN| = 2^15` 可容纳），再零扩展参与无符号除法；
   边界向量 `(-7,2)`→`-3`、`(7,-2)`→`-3`、`(-7,2)%`→`-1`、`(7,-2)%`→`1` 均由 `.idl` 正文求值复现。
3. 定值表四行：`div.sw` 0/all-ones、overflow `0xFFFF_FFFF_FFFF_8000`；`div.uw` 0 → `0x0000_0000_0000_FFFF`；
   `rem.sw` 除零 ⇒ 被除数符号扩展、溢出 ⇒ 0；`rem.uw` 除零 ⇒ 被除数零扩展 —— 与 SimRISC-04 §1.4 现场解析比对通过。
4. 合法性：12 条全部 `rdHB == 6'd0 ⇒ raise(Illegal, mode(), ip())`（附录 B `dst_rd0` 列出的 21 条含这 12 条）；
   求值器对 `rdHB=0` 12/12 触发 ILLI。批 1 全是 `orrr`，无 `encode_sbz`/`encode_onehot` 项。
5. 先读后写：两源在任何写入前捕获到局部变量（`src1`/`src2`），`rdHB == rdHC/rdHD` 时行为正确。
6. 散文零改动：spec 只加标记块（`+270 −0`），剔除后与 merge-base 逐字节相同；未改 `idl/README.md`、未碰其它册。
7. 防造假：证据脚本每条断言都有可达 FAIL 路径（6 路注入均实测 FAIL 并以 `cp`+md5 回绿）；
   覆盖率/定值表/解码变量集均现场从 `contracts/opcodes.yaml`、SimRISC-04 表格派生，未写死。
8. 术语核对：正文/注释无「银行」，一律「目的寄存器 / 写满 64 位」。

判决：**无需返修**，可交主会话续派批 2。

### 第 2 轮 engineer 自审（批 2 + 全册）

逐行审查新增 9 条 operation 与全册一致性：

1. **shamt 取值（本轮发现的实质缺陷，已修）**：`orrr` 形式原写 `Bits<4> shamt = rdHD[3:0];`，
   而 `rdHD` 是 6 位**寄存器号**（`idl/README.md §2`），这样取到的是号而非内容 —— 已改为
   `rd[rdHD][3:0]`（4 处：shl/rol/shr.sw/shr.uw 的 `orrr`）。类型求解与求值器都改用
   `rd[rdHD]` 后，`rdHD=0x3F` 取低 4 位=15 且不抛 ILLI 的用例通过。
2. **移位边界**：`s=0..15` 全档 + `s=15` 移满（`shl 0xFFFF << 15 = 0x8000`、`shr.sw 0x8000 >>> 15 = 全 1`）
   均由 `.idl` 正文求值复现；`orri` 越界 `immu6 ∈ {16,17,31,32,63}` ⇒ ILLI，`orrr` 不抛。
3. **`shr.sw` 符号扩展**：`{{48{val[15]}}, res}`（48+16=64），`res` 由 `$signed(val) >>> shamt` 得（算术右移）；
   对照 §2 公式 `rdHB[63:16] = sign_extend(rdHC[15])` 一致。
4. **`rev.w` 口径**：四块同法（距离 8 恒做）+ `k∈{1,2,4,8}` 才启用距离 2/4（k=8 只做 8；k=4 做 8,4；…）；
   实测 `k=1` 得 `0x…01 → 0x8000`（非 64 位整体反序）、`k=8` 得逐块 bswap16（非 bswap64）；
   非法 `k∈{0,3,5,6,7,9,15,16,32,63}` 全 ILLI。
5. **标记落点**：§2 的 6 条块落在 §2 prose 与 `### 2.1` 之间、`rev.w` 落在 `### 2.1` 之后、`rol.w` 两条落在
   `### 2.2` 的 ```simrisc 块之后；`+470 −0`、剔除标记块与 merge-base 逐字节相同（散文未动）。
6. **全册一致性**：21 条全部 `rdHB==rd0 ⇒ ILLI`；`width` 104 条断言零失配；`idlc` 21/21 解析+typecheck 通过。
7. **防造假**：新增 3 路注入（`rd[rdHD][4:0]` 扩宽、`immu6[4:1]` 取错位、rev 距离 8 掩码改 `0x0FF0…`）
   均实测 FAIL 且 `cp`+md5 还原后回绿；合计 9 路注入全绿。
8. **任务书缺陷**：删除「指令清单」后重复且矛盾的批次行 4 行（保留与「## 批次」一致的一份）——
   「删重复批次行」✅已做。
9. **更正第 1 轮第 3 条**：`m15-idl-008 rem.st` 的判断**撤回**。当时读到的是该分支 WIP 中途快照
   （除零档 `64'd0`）；其现分支 `93ed5752` 为 `if (b == 32'd0) { rd[rdHB] = {{32{a[31]}}, a}; }`，
   与 SimRISC-04 §1.4 定值表一致。教训：报他人册子问题须同时给「commit 快照 + id + 行号 + 原文」，
   且需确认该分支已稳定（非 WIP 中途）。
10. **术语**：新增正文/注释无「银行」，一律「目的寄存器 / 写满 64 位」。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `orrr` shamt 取成 `rdHD[3:0]`（寄存器号而非内容） | ✅已修 | 4 处改为 `rd[rdHD][3:0]`，注释同步 | `shift` 240 组零失配；`width` 104 条零失配 |
| 任务书重复批次行 | ✅已修 | 删 4 行，只留一份 | `sed -n '42,56p'` 现为单一批次列表 |
| 第 1 轮 `m15-idl-008 rem.st` 误报 | ✅已撤回 | 完成区坑 4 记录更正 + 快照证据 | 该分支 `93ed5752` 原文 `{{32{a[31]}}, a}` |
| `SimRISC-10` 同类 `rdHD[2:0]` 4 处疑点 | ⏸延后（越界） | 不在本任务范围，只报 id/行号/原文 | 见完成区坑 3 |

判决：**无需返修**；全册 21/21，`**状态**` → `待验收`。

### 第 1 轮 reviewer 验收（2026-11-19；中改档，≥2 路注入；接 engineer 自审两轮之后）

**重跑记录**（全部本人执行；分支 `m15-idl-009`，HEAD `6d72ea3c` 全程未变）
1. 运行期证据目录内 `run.sh` → `ALL PASS（fail=0）` rc=0：`cov 书内 21（批1 12+批2 9）`、`prose +470 -0 / 剥块后 6697 字符逐字节相等`、
   `fixed 四行 OK`、`sem 168 组失配 0、rd0 未判非法 0 条`、`shift 240 组失配 0`、`rev 失配 0`、`width 104 条失配 0`、
   `idlc 库 rc=0 + 解析 21/typecheck 21、非 PASS 0`、engineer 自检 9 路注入全 `inj=1/back=0/md5=ok`。
2. `python3 idl/render.py --check` → `PASS（96 条/10 册/96 块）` rc=0；`make check-idl-sync` rc=0；`make check-manifests-guard` → `PASS（双向集合一致、sha256 全符）` rc=0。
3. 覆盖率独立复算：`contracts/opcodes.yaml` 中 `spec_cite` 起首 `SimRISC-09:` 恰 21 条 == `.idl` `# id:` 集合（零缺零多）；散文零改动独立复核（不用证据脚本）：`git diff --numstat 4029147e` = `470 0`（删除 0 行），自写剥块实现比对 merge-base `4029147e`，6697 字符逐字节相等。

**注入 2 路**（均不在 engineer 的 9 路内；`cp` 备份于运行期临时目录 + md5 还原，未用 checkout/restore）
- A `shr.sw_orrr` `{{48{val[15]}}, res}` → `{48'd0, res}`：`shift rc=1`（`MISMATCH … v=0x8000 s=15: idl=000000000000ffff 公式=ffffffffffffffff`）、
  `render rc=1`、`FAIL（fail=3）` rc=1 ⇒ 还原 md5 `bbba5f3a…` 相等 ⇒ `ALL PASS` rc=0。
- B `shl.w_orrr` `Bits<4> shamt = rd[rdHD][3:0];` → `rdHD[3:0]`（SimRISC-10 同类写法）：`shift rc=1`
  （`rdHD=0x3F 应取低 4 位=15 且不抛 ILLI`、恒 shamt=3）、`render rc=1`、`FAIL（fail=3）` rc=1 ⇒ 还原 md5 相等 ⇒ `ALL PASS` rc=0。

**语义抽查 7 条**（operation 语句 ↔ 散文逐句对照）
1. `orrr` shamt：4 处 `Bits<4> shamt = rd[rdHD][3:0];`（shl/shr.uw/shr.sw/rol 的 orrr）↔ §2 表「`orrr`：`rdHD[3:0]`（高位忽略）」
   +「寄存器形式取低位、不抛 ILLI」+ `idl/README.md §2`（`rdHD` 是编码字段＝寄存器号）/§3（内容写 `rd[…]`）⇒ 取**内容**低 4 位正确。
2. `rev.w`：guard 恰 `{1,2,4,8}` ↔ §2.1；掩码 `FF00_FF00…` 每 16 位重复 ↔「四个块一律同样处理」；我独立两路（散文模型 vs `.idl` 逐句
   转写）220 组失配 0；`k=1 ⇒ 0x…8000`（非 64 位整体反序）、`k=8 ⇒ 0x2211443366558877`（逐块 bswap16，非 bswap64）。
3. `shr.sw`：`$signed(val) >>> shamt` + `{{48{val[15]}}, res}` ↔ §2 公式 `with sign(15)`、`rdHB[63:16]=sign_extend(rdHC[15])`；
   独立 96 组失配 0；移满位 `0x8000>>15 ⇒ 0xFFFF_FFFF_FFFF_FFFF`、`0x8001>>1 ⇒ 0xFFFF_FFFF_FFFF_C000`。
4. `div.sw/uw`、`rem.sw/uw`：`64'hFFFF_FFFF_FFFF_FFFF`、`64'hFFFF_FFFF_FFFF_8000`、`64'h0000_0000_0000_FFFF`、rem 除零档
   符号/零扩展、溢出 `64'd0` ↔ SimRISC-04 §1.4 定值表四行逐字一致。
5. `cmp.*` 三档 `{64{1'b1}}`/`64'd0`/`64'd1` ↔ §1.2「−1/0/+1 按 64 位扩展」；`rol.w` `dup>>(16-shamt)` ↔ §2.2
   `rol(x,n)=(x<<n)|(x>>(16-n))`（我独立 80 组失配 0）；4 条 `orri` 的 `immu6>15 ⇒ ILLI` ↔ §2/§2.2 表（计数 4 处）。
6. 全 21 条 `rdHB == 6'd0 ⇒ raise(Illegal, mode(), ip())` ↔ 附录 B `dst_rd0` 21 条（grep 计数 21）。

**约束核验**：独立 worktree（toplevel 已核）；未提交 git、HEAD 未变；主工作树 `master`/`2714a0c5` 且 `git status` 干净；相对 `4029147e` 仅 5 文件（`.idl`、本册 spec、两份 manifests、本任务书），未动其它册与 `idl/README.md`；版本仍 `0.5.7-rc`；写入本记录前 4 个交付文件 md5 与审查前快照一致、`git status -uall` 逐行相同（无残留）；完成区 25 行、本记录 ≤40 行。

**跨任务判定**：`idl/SimRISC-10.idl` 4 处 `Bits<3> shamt = rdHD[2:0];`（`rol.b_orrr_rd` L243、`shl.b_orrr_rd` L273、`shr.sb_orrr_rd`
L304、`shr.ub_orrr_rd` L332）＝**真 bug**，应为 `rd[rdHD][2:0]`（只判定，未改 010）。依据原文：① `spec/SimRISC-04 §2.2.2` rol.o 表
「`orrr` | `rdHD[5:0]`（**源寄存器低位**）| `0..63`（即对 64 取模）」⇒ 该记法指源寄存器**内容**低位；② `spec/SimRISC-10 §2` 表
「`orrr`：`rdHD[2:0]`（高位忽略）」沿用同一记法，正文亦「移位量取 `rdHD` 的低位（寄存器形式，`orrr`）」；③ `idl/README.md §2`
「直接用编码字段名作解码变量」（`rdHD`＝6 位寄存器号）+ §3 `rd[…]` 数组访问 ⇒ IDL 的 `rdHD[2:0]` 取**寄存器号**低位，shamt 被编码
定死（`rdHD=3` 恒 3），与「寄存器形式」语义矛盾；④ 二者同为 `Bits<3>`，idlc 类型求解抓不到（注入 B 实测）。

**判决：Accepted** —— 验收命令块在我本人重跑下全部通过（`render --check`/`check-idl-sync`/`check-manifests-guard` rc=0、idlc 两段式
21/21、覆盖率 21/21、散文零改动），2 路新增注入均「注入⇒红⇒`cp`+md5 还原⇒回绿」，硬约束无违反；SimRISC-10 4 处真 bug 转
architect 另立修复任务（本任务不放行该缺陷）。
