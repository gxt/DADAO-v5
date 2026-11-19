# m15-idl-010: `SimRISC-10`（8位数据运算）逐条 operation

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-spec-001`（语法基线、寄存器模型、语义库、`idl/render.py` 已就绪）
**可并行分片**：可与其它 `m15-idl-0xx` 并行（**各册独立文件**）；`idl/README.md §4` 语义库**不得自行动手**（缺函数 ⇒ 待裁定）
**预估**：3–5 天
**档位**：中改
**状态**：待验收

## 目标

把 `spec/SimRISC-10-8位数据运算.md` 里**每条指令**写成一段 operation，落到 **`idl/SimRISC-10.idl`**，再由 `idl/render.py` 生成 spec 内的 `<!-- IDL:<id> BEGIN/END -->` 块。

> 本册若已有 `m15-spec-001` 留下的样板 operation（01/04/06/11/12 各 1 条），按**同一风格**补齐其余指令，不重写已有样板。

## 用户裁定（2026-11-19，必须遵守）

1. **不修改原来的散文内容**——`spec/` 里只允许 `render.py` 写标记块，散文一字不动；
2. **发现散文不对、或与其它册/`spec` 冲突 ⇒ 停下来问用户**：写进任务书「待裁定」（问题 + 依据 + 候选解释），**不得自行改散文、不得自行改语义库**；
3. 正常情况下**每条指令一个 operation**（一 `# id:` 一段）；确需合并/拆分时同样记「待裁定」。

## 指令清单（本册 21 条，以 `contracts/opcodes.yaml` 的 `spec_cite` 为准）

- `add.sb_orrr_rd`
- `add.ub_orrr_rd`
- `cmp.sb_orrr_rd`
- `cmp.ub_orrr_rd`
- `div.sb_orrr_rd`
- `div.ub_orrr_rd`
- `mul.sb_orrr_rd`
- `mul.ub_orrr_rd`
- `rem.sb_orrr_rd`
- `rem.ub_orrr_rd`
- `rev.b_orri_rd`
- `rol.b_orri_rd`
- `rol.b_orrr_rd`
- `shl.b_orri_rd`
- `shl.b_orrr_rd`
- `shr.sb_orri_rd`
- `shr.sb_orrr_rd`
- `shr.ub_orri_rd`
- `shr.ub_orrr_rd`
- `sub.sb_orrr_rd`
- `sub.ub_orrr_rd`


- **批 1**：§1. 算术运算类指令 + §2. Bit manipulating：位操作指令 — 值语义


- **批 1**：§1. 算术运算类指令
- **批 2**：§2. Bit manipulating：位操作指令 — 值语义

## 批次（每批 ≤4 h；做完一批返回，由主会话续派下一批）

> 任务号不拆（整册一起验收）；**同一个 `.idl` 文件，同册串行**。每批只做列出的节，做完即返回，不提交。全册 21 条 ⇒ 分 2 批。

- **批 1**：§1. 算术运算类指令
- **批 2**：§2. Bit manipulating：位操作指令 — 值语义

## 交付

1. `idl/SimRISC-10.idl`：上述每条一个 `# id: <id>` + operation；
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
2. 只动 `idl/SimRISC-10.idl` + spec 本册的标记块 + 本任务书；**不动其它册**。
3. **不改 `idl/README.md`**（语义库）——缺函数就记「待裁定」。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

（**批 1 + 批 2：均无**。§1 散文与 `contracts/opcodes.yaml`、`spec/SimRISC-04` 定值表一致；
§2 散文与附录 B 一致，且本身已写清四处易歧义点，无需另立口径：① 移位量是**位域取值**不是取模
——`orrr` 取 `rdHD[2:0]`（§2 表 + §2.2 表「0..7，即对 8 取模」）、`orri` 取 `immu6[2:0]` 且
`immu6 > 7` 直接 **ILLI**（§2「立即数形式 `immu6 > N` 触发 ILLI」，N=7）；② `rol.b` 只有
**左**旋一个方向（§2.2「符号无关、只有一个方向」），不设反向；③ `shr.sb` 的 `rdHB[63:8]`
按公式写死为 `sign_extend(rdHC[7])`（算术右移移满位时结果即全符号位，与公式自洽）；
④ `rev.b` 是**逐 8 位块**反转单元顺序（§2.1 原话「按 8 位块逐块反转…八个块一律同样处理」，
并明写「`k=1` 只反转**块内**位序，**不是** 64 位整体位反序」），未按 RISC-V `rev8` 直觉改写。）

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-19，批 1）

逐行审查 `idl/SimRISC-10.idl`（12 条）与证据脚本；逻辑/边界核查点：读后写顺序（源先入局部
`src1/src2` 再写 `rd[rdHB]`，含 `rdHB==rdHC` 自身覆盖）、`.sb` 符号扩展取结果 bit7、`div.sb`
除零/溢出必须先于有符号除法短路（UDB `doc/idl.adoc` 明言二者 undefined）、`mul` 只保留低 8 位
（IDL 运算符表：`*` 结果宽 = max(L(i),L(j))）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 解码变量宽度取自 opcodes `fields[].name`（小写 `rdhb`）⇒ `idlc` 类型检查 0/12 | ✅已修 | 改为从 operation 文本取实际拼写（README §2 大小写不敏感），宽度仍取 `fields[].bits` | type 12/12 |
| F2 `semantics.py` 字面量正则带 `$` 尾锚 ⇒ 复制表达式 `{64{1'b1}}` 求值失败（定值表 3 项假红） | ✅已修 | 去掉尾锚，改为在剩余串上 `match` | 定值表 4 条全 PASS |
| F3 `semantics.py` 用 `_sb_`/`_ub_` 判变体，而本册 id 形如 `add.sb_orrr_rd`（分隔符是 `.`）⇒ 该判据空转（恒真） | ✅已修 | 改 `.sb_`/`.ub_` | 注入⑤（符号扩展→零扩展）rc=1 |
| F4 `.ub` 曾把 `{64{1'b1}}` 误判为「符号扩展」 | ❌不修（判据收窄） | `.ub` 只禁 `{{56{…}}`（8 位符号扩展）；`{64{1'b1}}` 是 64 位常量，§1.2 明说两变体结果同值 | 基线 PASS；注入⑤仍 rc=1 |
| F5 注入 A 的 `git status` 为 `??`（新增文件未入库），`git diff --name-only` 对其为空 | ❌不修（改证据口径） | 非空注入改用 md5 变化 + `git status --porcelain -- <path>` 双证 | 运行日志「注入 A 非空」+ md5 对账还原 |

判决：无未修 finding（F4/F5 为判据/口径收窄，均有证据），批 1 可交付。

### 第 2 轮 engineer 自审（2026-11-19，批 2 = §2 位操作 9 条）

逐行审查新增 9 条：`rev.b` 的 k 合法性与三段 butterfly 的掩码/位移量、`rol.b` 的 16 位复制
算式（s=0 时右移量 8 落在 16 位宽内）、`shl.b`/`shr.ub`/`shr.sb` 的 `<<`/`>>`/`>>>` 与
零/符号扩展、orrr 与 orri 的 shamt 位域差异（3 位 vs 6 位 + 越界 ILLI）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F6 注释里写 `rol(val, s)`、`sign_extend(rdHC[7])` ⇒ `render.py` 的「调用未声明函数」判据（正则扫全文含注释）判红 | ✅已修 | 注释放措辞：改写成「按位等价式」「符号扩展 rdHC[7]」，不动 `render.py` | `render.py --check` rc=0 |
| F7 `cover.py` 原用「mnemonic 出现在 §1 区段」判 §1 ⇒ §1.1 的 `simrisc` 速查块列了全册助记符，把 §2 的 9 条误算进 §1 | ✅已修 | §2 现场派生（§2 区段）、§1 取补集 | §1 12/12 + §2 9/9 |
| F8 「源截断」判据原要求两个源都 `[7:0]` ⇒ §2 的移位量（3 位）假红 | ✅已修 | 分节：§1 两数据源、§2 仅 `rdHC[7:0]`、`rev.b` 用整 64 位 | 该判据 PASS，注入②/②b 仍可达 |
| F9 `semantics.py` 的 rev.b 参考实现（`reversed(units)` 逐位移位）实为**恒等映射** ⇒ 6 项假红 | ✅已修 | 改为「输入第 i 个单元落到第 n−1−i 个单元」直接构造 | 3 个 k × 全部 256 字节值 + 混合字 0 处不符 |
| F10 真实树注入 C 首版改 `AAAA…→…AAAB` 是**语义中性**（bit0 右移出即丢弃）⇒ 期望 FAIL 却回绿 | ✅已修 | 改 `5555…→…5554`（丢掉 bit2 那一路），注入见 128 个字节值不符 | 注入 C rc=1；还原后回绿 |
| F11 注入编号重复（清单段也用 ⑦⑧） | ✅已修 | 清单段改 ⑨⑩ | 日志编号唯一 |

判决：无未修 finding；全册 21/21 可交付。

### 第 1 轮 reviewer 验收（2026-11-19，中改：≥2 路注入）

**范围/文件**：`git diff 5a21d33e..HEAD --name-status` = 恰 5 文件（本册 `.idl`、本册 spec、`spec/.manifests.toml`、`idl/.manifests.toml`、本任务书）；`git status --porcelain -uall` 空。**散文零改动**：剥掉 `<!-- IDL:* BEGIN/END -->` 块（连块后配套空行）后与 `5a21d33e` 版**逐字节相同**（自写脚本：old 8918 = stripped 8918，差异行 0）；`git diff --numstat` 累计 440 增 0 删（批 2 当批 193 增 0 删）、`+<!-- IDL:` 42 行 = 21 对。清单只写数据：`idl/.manifests.toml` 仅新增本册条目块，`spec/.manifests.toml` 仅本册 sha256 一行。

**重跑（运行期证据目录内的 `run.sh`）**：`bash <运行期证据目录>/run.sh` → `== 汇总：PASS=62 FAIL=0` / `ALL GREEN`，**rc=0**（初跑、注入后、还原后共 3 次）。内含：`已写 operation 21 / spec 标记块 21`、`§1 12/12 + §2 9/9`；`idlc --root isa` rc=0 + 21 条 `parse 21/21`、`type 21/21`；12 个受影响 L1 门控全 rc=0。我另独立单跑：`make check-idl-sync` rc=0（`PASS（源 operation=40 条 / 落点 8 册 / 标记块 40 个，逐字节一致）`）、`make check-manifests-guard` rc=0（`结果: PASS`）、`python3 idl/render.py --check` rc=0。

**语义抽查 4 条（散文原文 ↔ operation，均以散文为据）**：
1. 移位量/ILLI：§2「移位语义见 SimRISC-04。其中 N=7」+ 表「`orrr`：`rdHD[2:0]`（高位忽略）；`orri`：`immu6[2:0]`」+「**立即数形式** `immu6 > N` 触发 ILLI；寄存器形式…不抛 ILLI」↔ `if (immu6 > 6'd7) raise`、`Bits<3> shamt = immu6[2:0];` / `rdHD[2:0]`。
2. `rol.b` 只有左旋：§2.2「符号无关、**只有一个方向**」「逻辑循环左移」↔ `dup = {2{val}}; shifted = dup >> (8 - shamt); res = shifted[7:0]`（数学上即左旋）。
3. `shr.sb` 高位：§2 公式「`rdHB[63:8] = sign_extend(rdHC[7])`」↔ `val = rd[rdHC][7:0]; … rd[rdHB] = {{56{val[7]}}, res};`。
4. `rev.b` 逐 8 位块：§2.1「按 8 位块**逐块**反转…八个块一律同样处理」「`k=1` 只反转**块内**位序，**不是** 64 位整体位反序」↔ 掩码 `AAAA/5555/CCCC/3333/F0F0/0F0F` 按字节重复（块间不搬位、无跨字节 butterfly）+ `immu6 != 1 && != 2 && != 4 ⇒ ILLI`（k=8 恒等档非法）。非 RISC-V `rev8` 直觉改写。

**独立 oracle（自写，未复用 engineer 脚本）**：期望值按 §2.1/§2.2 定义自算，实现侧从 `.idl` 现场抓 butterfly/rol 算式执行 → `k=1/2/4 ×（0x00 / 0xFF / 0x80 / seed=20261119 随机 200 + 全 256 字节值）= 461 样本`不符 0；`rol` 两式 256×8 = 2048 组不符 0，`rc=0`；ref 自检 `0xEF k=1 ⇒ 0xF7`、`0x12 k=4 ⇒ 0x21`、确认非恒等映射。

**注入（2 路，均不在 engineer 的 11 路内）→ 红 → `cp`+md5 还原 → 绿**：
- 注入①（真实树）`rol.b_orrr` `dup >> (8 - shamt)` → `dup << shamt`（md5 `197a9cd4…` → `9db76b76…`）⇒ 重跑 `run.sh` **rc=1，PASS=53 FAIL=9**（`rol.b_orrr_rd: 算式形态…实际 缺失`、`render --check`/`check-idl-sync`/`semantics.py` 全红）；`cp` 还原 → `md5sum -c` OK、`git status` 空 → 重跑 **rc=0，PASS=62 FAIL=0**。
- 注入②（真实树）`rev.b` one-hot `6'd4` → `6'd8`（md5 → `8faf56a8…`）⇒ 重跑 **rc=1，PASS=54 FAIL=8**（`[FAIL] encode_onehot 条目有 {1,2,4} 合法性判定 … 实际 ['rev.b_orri_rd']`，`cover.py` rc=1）；`cp` 还原 → md5 回 `197a9cd4…` → 重跑 **rc=0**。
- 自审 F9/F10 复核：F9 **真修**（其 `ref_rev` 与我的独立 ref 全量 0 处不符、仅 48/768 输入为恒等，非恒等映射）；F10 **真修**（注入 C `5555…→555…54` ⇒ `semantics.py` rc=1、`rev.b k=1: 128 个字节值不符`，确非语义中性）。

**约束核验**：独立 worktree、未碰主工作树（`.idl 197a9cd4…`/`spec 38b4683b…`/两清单 md5 快照前后一致）；**未提交 git**（HEAD 仍 `39691a47`，无新 commit）；只动 5 个允许文件（`git diff --name-status` 对账）；还原全程 `cp`+md5，未用 checkout/restore/stash/show；未改 `idl/README.md`、`idl/render.py`，任务书 diff 仅状态/待裁定/审阅记录/完成区（验收标准段未动）。

**判决：Accepted**。文档级 finding 2 条（交 architect 收尾改，不阻断）：① 完成区末行「`**状态**` 保持 `待开始`」与头部 `**状态**：待验收` 矛盾；② 完成区「临时树/临时文件注入 8 路」——脚本实为 11 个注入计数器（其后列举已 9 项），计数笔误。

## 完成区

**测试结果**：**全册 21/21 完成**（§1 算术 12 + §2 位操作 9）；运行期证据目录内的 `run.sh` → `PASS=62 FAIL=0`，rc=0。
**本批 id（9 条，§2）**：`rev.b_orri_rd`；`rol.b_orri_rd`/`rol.b_orrr_rd`；`shl.b_orri_rd`/`shl.b_orrr_rd`；`shr.sb_orri_rd`/`shr.sb_orrr_rd`；`shr.ub_orri_rd`/`shr.ub_orrr_rd`。批 1 的 §1 12 条不变，**累计 21/21**。
**关键 rc**：cover.py 0（全册 21/21 零缺零多、marker↔源双向 21 对、每条判 `rdHB==0 ⇒ ILLI`、§1 双源截断 / §2 仅 `rdHC[7:0]` / `rev.b` 整 64 位、`encode_sbz` 4 条有 `immu6 > 7` ILLI、`encode_onehot` 有 `{1,2,4}` 判定）；prose_unchanged 0（基线锚 merge-base `5a21d33e`，标记仅新增 42 行 = 21 对；反例 c「基线误取含块版」rc=1，ISS-475）；`render.py --check` 0、`check-idl-sync` 0、`render.py --self-test` 0；受影响 L1 门控 12 个全 0；idlc 库 `--root isa` 0、21 条 `--root instruction_operation` parse 21/21 + 类型 21/21；semantics.py 0。
**语义抽查（§2，语句 ↔ 散文）**：
- `rev.b`：`immu6 != 1 && != 2 && != 4 ⇒ ILLI` ↔ §2.1「合法 k = {1,2,4}（one-hot 且 k < 8）、否则 ILLI（`encode_onehot`）」；`x = rd[rdHC]` 整 64 位 ↔「对 64 位源寄存器按 8 位块逐块反转」；三段 butterfly（掩码按字节重复）↔「每块按 k 位切成 8/k 个单元，反转单元顺序、单元内部位序不变，八个块同法」+「不是 64 位整体位反序」。oracle 数值核对：k=1/2/4 × 全部 256 个字节值 + 5 个边界/混合字，0 处不符。
- `shr.sb_orri`：`immu6 > 7 ⇒ ILLI` ↔ §2「立即数形式 `immu6 > N`（N=7）触发 ILLI」；`shamt = immu6[2:0]` ↔ §2 表「`orri`：`immu6[2:0]`」；`$signed(val) >>> shamt` ↔ 公式「`(rdHC[7:0] >> shamt) with sign(7)`」；`{{56{val[7]}}, res}` ↔「`rdHB[63:8] = sign_extend(rdHC[7])`」。
- `shl.b_orrr`：`shamt = rdHD[2:0]` 且无 ILLI ↔「寄存器形式取 `rdHD[N:0]` 的低位（高位忽略，不抛 ILLI）」；`<<` + `{56'd0, res}` ↔ 公式「`rdHB[7:0] = rdHC[7:0] << shamt`；`rdHB[63:8] = 0`」。
- `rol.b`（orrr/orri）：16 位复制算式 ↔ §2.2「`rdHB[7:0] = rol(rdHC[7:0], amount)`、零扩展、只有一个方向」；oracle 数值核对 256 值 × 8 个 shamt，0 处不符。
**修改文件**：`idl/SimRISC-10.idl`（+9 条，共 21 条）；`spec/SimRISC-10-8位数据运算.md`（本批仅新增 9 个生成块 + 18 行标记，散文逐字节未变，`git diff --numstat` 193 增 0 删）；`spec/.manifests.toml`（只改本册 sha256）；`idl/.manifests.toml` 本轮未再改（批 1 已登记本册一行）；本任务书。
**验收结果**：`bash <运行期证据目录>/run.sh` → `== 汇总：PASS=62 FAIL=0` / `ALL GREEN`，rc=0。真实树注入 3 路（A `add.sb` 符号扩展→零扩展、B spec 生成段改 1 字节、C `rev.b` 掩码 5555→5554）均期望 FAIL、`cp` 还原后 md5 对账一致并回绿；临时树/临时文件注入 8 路（漏写 §1、漏写 §2、写 opcodes 外 id、语法错、参数个数错、`>>>`→`>>`、shamt 位域改错、清单删条目、diff 多一行）。
**新发现/坑**：① `render.py` 的「未声明函数」判据扫**注释**——注释里别写 `name(`，否则假红（F6）；② §1.1 的速查块列了全册助记符 ⇒ 分节归属不能靠「mnemonic 出现在 §1」（F7）；③ 分节判据要按语义分工，不能拿 §1 的「两条源都截断」套 §2 的移位量（F8）；④ `rev.b` 用「交换距离 1/2/4 的 butterfly + 按字节重复掩码」等价表达逐块反转，比写 64 项拼接简洁，且可用 prose oracle 全量核对；⑤ 注入要选**语义可达**的改动（改恒为无效位的掩码等于没注入，F10）。
**遗留问题**：无（整册 21/21 完成）。`**状态**` 保持 `待开始`（按派单要求，验收由主会话安排）。
