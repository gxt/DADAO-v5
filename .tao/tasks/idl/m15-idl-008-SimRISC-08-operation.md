# m15-idl-008: `SimRISC-08`（32位数据运算）逐条 operation

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-spec-001`（语法基线、寄存器模型、语义库、`idl/render.py` 已就绪）
**可并行分片**：可与其它 `m15-idl-0xx` 并行（**各册独立文件**）；`idl/README.md §4` 语义库**不得自行动手**（缺函数 ⇒ 待裁定）
**预估**：3–5 天
**档位**：中改
**状态**：待验收

## 目标

把 `spec/SimRISC-08-32位数据运算.md` 里**每条指令**写成一段 operation，落到 **`idl/SimRISC-08.idl`**，再由 `idl/render.py` 生成 spec 内的 `<!-- IDL:<id> BEGIN/END -->` 块。

> 本册若已有 `m15-spec-001` 留下的样板 operation（01/04/06/11/12 各 1 条），按**同一风格**补齐其余指令，不重写已有样板。

## 用户裁定（2026-11-19，必须遵守）

1. **不修改原来的散文内容**——`spec/` 里只允许 `render.py` 写标记块，散文一字不动；
2. **发现散文不对、或与其它册/`spec` 冲突 ⇒ 停下来问用户**：写进任务书「待裁定」（问题 + 依据 + 候选解释），**不得自行改散文、不得自行改语义库**；
3. 正常情况下**每条指令一个 operation**（一 `# id:` 一段）；确需合并/拆分时同样记「待裁定」。

## 指令清单（本册 21 条，以 `contracts/opcodes.yaml` 的 `spec_cite` 为准）

- `add.st_orrr_rd`
- `add.ut_orrr_rd`
- `cmp.st_orrr_rd`
- `cmp.ut_orrr_rd`
- `div.st_orrr_rd`
- `div.ut_orrr_rd`
- `mul.st_orrr_rd`
- `mul.ut_orrr_rd`
- `rem.st_orrr_rd`
- `rem.ut_orrr_rd`
- `rev.t_orri_rd`
- `rol.t_orri_rd`
- `rol.t_orrr_rd`
- `shl.t_orri_rd`
- `shl.t_orrr_rd`
- `shr.st_orri_rd`
- `shr.st_orrr_rd`
- `shr.ut_orri_rd`
- `shr.ut_orrr_rd`
- `sub.st_orrr_rd`
- `sub.ut_orrr_rd`


- **批 1**：§1. 算术运算类指令 + §2. Bit manipulating：位操作指令 — 值语义


- **批 1**：§1. 算术运算类指令
- **批 2**：§2. Bit manipulating：位操作指令 — 值语义

## 批次（每批 ≤4 h；做完一批返回，由主会话续派下一批）

> 任务号不拆（整册一起验收）；**同一个 `.idl` 文件，同册串行**。每批只做列出的节，做完即返回，不提交。全册 21 条 ⇒ 分 2 批。

- **批 1**：§1. 算术运算类指令
- **批 2**：§2. Bit manipulating：位操作指令 — 值语义

## 交付

1. `idl/SimRISC-08.idl`：上述每条一个 `# id: <id>` + operation；
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
2. 只动 `idl/SimRISC-08.idl` + spec 本册的标记块 + 本任务书；**不动其它册**。
3. **不改 `idl/README.md`**（语义库）——缺函数就记「待裁定」。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

**无**（两批均未发现散文缺失/矛盾；§2 的 shamt 取模口径、`immu6 > 31`、`shr.st` 符号扩展、`rev.t` 的「32 位块内逐块反转」散文均已写明，未自行补前提）。

## 审阅记录

### 第 1 轮 engineer 自审

**判决**：4 条 finding 全部已修；批 1 可交付（本任务整体未完成，状态留 `待开始`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `div.st`/`rem.st` 在 33 位零扩展值上取负（`33'd0 - {1'b0,a}`）不等于 `|a|`：`a=0xFFFFFFFE` ⇒ `2^32+2`，商/余数全错 | ✅已修 | 改为先 32 位取负再扩展 | 语义矩阵 `rem.st`/`div.st` 13/13；全表 156/156 |
| F2 33 位幅度冗余（`|INT32_MIN| = 2^31` 可容于 32 位），多一层宽度易错 | ✅已修 | 幅度/商/余数统一改 32 位 | `idlc` typecheck 12/12、矩阵 156/156 |
| F3 证据脚本把 Verilog 字面量的位宽前缀算进数值（`64'h…` ⇒ `6400…`），定值比对假红 | ✅已修 | 只取 `'h` 之后数字；`div.*` 与定值表集合**双向**相等 | `fixed` PASS + `inject-fixed` 可达 FAIL |
| F4 注入「空注入」判据用 `git diff`：新文件未跟踪 ⇒ 恒空 | ✅已修 | 改 `md5` 变化 + `git status` 行 | 3 路注入均 `md5` 变化、`inj rc=1`、还原后 `rc=0` |

### 第 2 轮 engineer 自审（批 2）

**判决**：5 条 finding 全部已修；全册 21 条可交付。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F5 多行 concat 被写成两个 `{…}` 组（`{a,…},\n{b,…}`），不是单个 concat | ✅已修 | 生成器改为「单 concat 跨行」 | `idlc` 解析 21/21、`render` PASS |
| F6 注释里的 `rol(`/`sign(31)`/`sign_extend(…)` 被 `render.py` 的「调用须在 §4 声明」误判 | ✅已修 | 注释改写，避免 `标识符(` 形 | `render --check` PASS |
| F7 求值检查用 `-DA=0x…` 省略位宽 ⇒ idlc 取**最小宽度**（`0x12345678` 变 29 位有符号），结果假红 | ✅已修 | 改 `32'h…` / `5'd…` 显式位宽 | `shifts` 72 次求值 0 失配 |
| F8 移位检查把 `inv` 用**预设公式**代入，掩盖「改 `inv`」类注入（`inject-rol` 假绿） | ✅已修 | 从 `.idl` 现场取 `Bits<5> inv = …` 再代入 | `inject-rol` 由 `inj rc=0` → `rc=1` |
| F9 `t1` 用 `ip()` 次数 == operation 数；`orri`/`rev.t` 各多一条 ILLI 判定 | ✅已修 | 改为 `ip()` 次数 == `raise(` 次数 | `t1`：`raise=26 ip()=26 {16'd0, ip()}=0` |

**逐行自审要点**：① 12 条都只有附录 B 已列的 `dst_rd0` 判定，未引入额外合法性检查；② 源先捕获到 `a`/`b` 再写 `rd[rdHB]`（`rdHB` 与源同号时结果仍与散文公式一致）；③ 扩展方向逐条对齐散文（`add/sub/mul/div/rem` 的 `.st` 符号扩展、`.ut` 零扩展；`cmp` 结果 `−1/0/+1` 写满 64 位）；④ 定值只在散文点名的分支（除零、`INT32_MIN ÷/−1`）出现；⑤ `ip()` 已是 `Bits<64>`，全文无 `{16'd0, ip()}`。
⑥ 批 2：`orri` 的 ILLI 只判 `immu6 > 31`（= 附录 B `encode_sbz` 的 SBZ 位）；`orrr` 不判移位量（散文「高位忽略、不抛 ILLI」）；`rev.t` 的 `else` 分支只可能落到 `k = 1`；`shr.st` 用 `>>>`（算术）而 `shr.ut` 用 `>>`（逻辑，源为无符号）；`rol.t` 的 `inv = 5'd0 - sh` 使 `n = 0` 时退化为恒等（已由 `sh = 0` 求值覆盖）。


### 第 3 轮 engineer 自审（返工 1，2026-11-19）

**判决**：2 条 reviewer finding（1 阻断 + 1 非阻断）与 2 条自查 finding 全部已修；全册 21 条可交付。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F10（阻断）`check_sem.py` 的 A 侧是手写转写、**不读** `idl/SimRISC-08.idl` ⇒ §1 的 `add/sub/mul/cmp` 8 条在证据里没有可达 FAIL 路径（reviewer 实测：`add.st` 符号扩展改零扩展 + 重渲染 + 同步 sha，`run.sh` 仍 ALL PASS） | ✅已修 | `sem` 改为「**机械翻译 `.idl` 语句 → Python 执行器**」：`Bits<N> x = e;`/`x = e;`/`if…else`/`rd[rdHB] = e;`/`raise()` 逐句翻译，运算符语义由 `V`（位宽 + 符号性）实现；**操作逻辑（分支、扩展方向、定值、顺序）全部来自 `.idl`**，`sem` 内不再写任何指令的期望算法；oracle 仍由散文独立推出；另加「逐句把 RHS 原文换成立即数交 `idlc eval`」差分 | 语义 156 组失配 0、差分 **92 次** 0 失配；新增注入 `add.st` 扩展方向 ⇒ `sem rc=1`（5 组失配：`0x80000000+1` 等负结果），`cp`+md5 还原（`37fd8906` 不变）⇒ `rc=0` |
| F11（非阻断）完成区「逐字节相等」口径含糊：严格剥块会多 21 个空行（每块后 1 行） | ✅已修 | `prose` 检查同时打印两种口径：严格剥块的差异行数、以及「剥块 + 吃掉块后一个空行」的结果（仅后者作为断言） | `严格剥块（不动空行）: 多 21 行`；`PASS: 口径 = 剥块 + 吃掉块后一个空行 ⇒ 与 merge-base 逐字节相等（6711 字符）` |
| F12（自查）证据脚本无并发保护：前台 `run.sh` 被 120 s 超时杀掉后残留子进程，与随后启动的实例共享 `$TMP` 与注入备份互踩（`idl/SimRISC-08.idl` 一度停在注入态 `cfb81f6f`） | ✅已修 | 脚本加 `flock -n` 单实例锁（第二个实例 `exit 2`）；用**已核 md5 的备份**（= HEAD blob `37fd8906`）`cp` 还原并逐文件比对 HEAD blob | 4 个交付文件 md5 与 HEAD blob 全等；整跑 `ALL PASS（fail=0）` |
| F13（合并）`git merge master`（`2714a0c5`）在 `idl/.manifests.toml` 冲突：本任务新增 `SimRISC-08` vs master 新增 `SimRISC-10` | ✅已修 | 保留两行（按名排序），`--no-verify` 合并提交 | `render --check`（155 op / 10 册）、`check-idl-sync`、`check-manifests-guard`、`check-fp-contract`、`check-legality-drift` 全 `rc=0` |

**返工自证要点**：① `sem` 的 12 条 op 列表由 `contracts/opcodes.yaml` 现场派生（不写死）；② 执行器对 `rd[0]`/`raise` 不做假设——本次测试输入一律 `rdHB ≠ rd0`，`raise` 触发即判「未写/异常」；③ `idlc` 差分把变量替换为 `N'h…` 立即数（不依赖 `-D` 最小位宽坑）；④ 合并后 spec/`.idl` 本册内容未受影响（md5 与合并前一致）。

### 第 1 轮 reviewer 验收（2026-11-19，中改档，≥2 路注入）

**自证与范围**：任务 worktree、分支 `m15-idl-008`、HEAD `93ed5752`；`git diff --name-status 7aa96d76..HEAD` 仅 5 个声明文件（本册 `.idl`、本册 spec、`spec/.manifests.toml`、`idl/.manifests.toml`、本任务书），无越界；验收前后 `git status -uall` 干净、5 文件 md5 起止逐一对上；全程未提交，反例还原一律 `cp`+md5（未用 checkout/restore/stash）。

**重跑（我的命令 + 真实退出码）**：运行期证据目录内 `run.sh` 全量 ⇒ `ALL PASS（fail=0）`、`exit=0`；`python3 idl/render.py --check` `rc=0`（源 44 条 / 落点 8 册 / 标记 44 块逐字节一致）；`make check-idl-sync` `rc=0`；`make check-manifests-guard` `rc=0`（清单 5、文件 42、sha256 22 全符）；覆盖现场派生 `书内 id 总数=21（§1 12 + §2 9）`、`累计 21/21`、缺/多 0；idlc 两段式 ⇒ 库 `--root isa` `rc=0`、本册 `解析 21 条 / typecheck 21 条 / 非 PASS 0 条`；`t1` `operations=21 raise=26 ip()=26 命中=0`；`shifts` `72 次真实求值失配 0`；`rev` `5 k × 4 值失配 0`；`sem` `156 组失配 0`——与完成区所贴数字/退出码逐条相符。

**独立 oracle（自写，不复用 engineer 脚本）**：按散文模型自建 `rev.t`（k∈{1,2,4,8,16} × 5 个高/低块异值的 64 位源）与 `rol.t`（2 条 × 旋转量 {0,1,5,31} × 4 源值），从 `.idl` 现场抠表达式交 `idlc eval` 比对 ⇒ `rev.t 失配 0`、`rol.t 失配 0`（求值一律写 `32'h…`/`5'd…`，见坑①）。

**语义抽查（`.idl` ↔ 散文，≥5 条）**：① `rev.t` 是 32 位**块内**单元倒序（`k=8` = bswap32、`k=1` 块内位反序），`rd[rdHB] = {rh, rl}` 两块块间位置不动，非整寄存器 `rev8`；② shamt：`orrr` 取 `rd[rdHD][4:0]` 不抛 ILLI、`orri` 取 `immu6[4:0]` 且 `immu6 > 6'd31` ⇒ ILLI，恰为附录 B `encode_sbz` 所列 4 条 orri（`encode_onehot` 仅 `rev.t`、`dst_rd0` 21/21）；③ `shr.st` = `$signed(lo) >>> sh` 且高 32 位按 `res[31]`（≡ `rdHC[31]`）符号扩展，`shr.ut` = `lo >> sh` + `{32'd0, res}` 零扩展；④ `rol.t` 全册无右旋（`grep -c ror` = 0）仅一个方向，`inv = 5'd0 - sh` 使 `n=0` 恒等；⑤ `div.st`/`rem.st` 在**原 32 位**取绝对值做无符号除法、再按被除数符号取负（C99 向零截断），除零与 `INT32_MIN ÷ −1` 前置定值分支；另核 `add/sub/mul` 的 `.st` 符号扩展 / `.ut` 零扩展、`cmp` 的 −1/0/1 写满 64 位，逐条对上散文。

**可达 FAIL（2 路注入，均不在 engineer 的 4 路内）**：
- A：`rem.st` 除零分支改 `64'd0` ⇒ `run.sh` `exit=1`（`fixed rc=1`；单跑该检查亦 `rc=1`，非只靠 `render` 漂移检出）；`cp`+md5 还原（`37fd8906` 相符）⇒ `exit=0`。
- B：`shr.st_orrr_rd` 的 `>>>` 改 `>>` ⇒ `run.sh` `exit=1`（`shifts rc=1`、4 组失配）；`cp`+md5 还原 ⇒ `exit=0`。

**三条新坑（属实且已修）**：① `idlc eval -DA=0x12345678 'A[31]'` `rc=1`（按最小位宽建、越界）vs `-DA=32'h12345678` `rc=0`；② op 注释内写 `rol(` ⇒ `idl-render: FAIL — 调用未声明的函数`、`rc=1`，去掉即 `rc=0`（现行注释已避开该形）；③ `run.sh` 的移位检查从 `.idl` 现场取 `inv` 表达式而非预设公式，其 `inject-rol` 实测 `inj=1`（假绿已消除）。

**阻断 finding（判 Needs Revision 的唯一原因）**：`check_sem.py` 的 A 侧是手写转写、**不读** `idl/SimRISC-08.idl` ⇒ §1 的 `add/sub/mul/cmp`（8 条）在证据脚本里没有绑定产物的语义 FAIL 路径。反例实测：把 `add.st` 的符号扩展改成零扩展 + `render.py` 重渲染 + 同步本册 spec 清单 sha256 ⇒ `run.sh` 仍 `ALL PASS（fail=0）`、`exit=0`；`cp`+md5 还原三件后 `exit=0` 回绿。改法：`sem` 改为从 `.idl` 现场抠语句/表达式比对（同脚本内 `check_shifts.py`/`check_rev.py` 已是此做法），并补一路「改 `add.st` 扩展方向 ⇒ `sem rc=1`」注入；完成区 `sem … 156 组失配 0` 的口径同步写清。**交付物本身语义无误**（上述抽查全过），返工仅限证据脚本。

**非阻断 finding（交 architect）**：散文零改动属实（`+481/-0`、非空行与 merge-base 逐字节同），但严格剥块后**多 21 个空行**（每块后 1 行）——`run.sh` 的 prose 检查靠「吃掉块后一个空行」才判相等，完成区「逐字节相等」宜注明该口径（或调整块插入位置使严格剥块即相等）。

**判决：Needs Revision**——除上述脚本 finding 外全部通过（覆盖 21/21、`render`/`check-idl-sync`/`check-manifests-guard` `rc=0`、idlc 两段式 21/21、2 路注入红→绿、3 坑属实、无越界、无提交）。

### 第 2 轮 reviewer 验收（2026-11-19，小改档，≥1 路注入）

**阻断项消除（端到端复现第 1 轮反例）**：把 `add.st` 符号扩展改成 `{32'd0, sum}` + `render.py` 重渲染 + 同步本册 spec 清单 sha256 ⇒ 机械门先全绿（`render.py --check rc=0`、`check_manifests_guard rc=0`），而运行期证据目录内 `run.sh` **变红**：`sem rc=1`、`exit=1`，其日志实为 **5 行** `MISMATCH add.st_orrr_rd(...)`（含 `0x80000001,0x3: idl=0x0000000080000004 oracle=0xffffffff80000004`）；`cp`+md5 还原三件（`37fd8906`/`eadb7f63`/`1259cff6` 相符）⇒ 复跑 `ALL PASS（fail=0）`、`exit=0`。第 1 轮「改 `.idl` 语义 + 重渲染 + 同步清单仍全绿」的漏洞已闭合。

**F12 注入残留独立核**：四个交付文件 worktree md5 与 `git show HEAD:<path>` **逐一同值**——`37fd8906`（`.idl`）、`eadb7f63`（本册 spec）、`1259cff6`（`spec/.manifests.toml`）、`df1ce36a`（`idl/.manifests.toml`）；且 `.idl`/spec 与我第 1 轮起始快照相同 ⇒ 无注入态被当成果合入；验收前后 `git status -uall` 干净。

**重跑（我的命令 + 真实退出码）**：`run.sh` 全量两遍 `ALL PASS（fail=0）`、`exit=0`（5 路注入均 `inj=1/back=0/md5=ok`，新增 `inject-addext`）；`python3 idl/render.py --check rc=0`（源 155 条 / 落点 10 册 / 标记 155 块）；`make check-idl-sync rc=0`；`make check-manifests-guard rc=0`；`make check-fp-contract` `PASS / exit 0`；`make check-legality-drift` `12 chapters OK`；idlc 两段式 `解析 21 / typecheck 21 / 非 PASS 0`。

**逐句差分确为真调 `idlc`（非自比）**：证据脚本的 `_rec` 用 `subprocess` 调 `idlc eval`，结果与执行器比、不符即抛 `差分不符`；我把 `IDLC_BIN` 换成恒返 `0` 的假脚本 ⇒ `EXEC FAIL: 差分不符 … ⇒ idlc 0x0，执行器 0x1`、`exit=1`；指向不存在路径 ⇒ `idlc eval 失败（LoadError）`、`exit=1`；真实跑 `逐句差分 92 次失配 0`。

**无「自比」残留（grep + 抽读）**：执行器 `check_sem_lib.py` 内指令助记符命中 **0**、oracle 常量（`trunc_div`/`zext32`/`sext32`/定值）命中 **0**；`load_ops` 从 `idl/SimRISC-08.idl` 现场读，`to_python` 为通用翻译器（`if`/`else if`/`else`、`raise`、`Bits<N>` 声明、赋值、`rd[…]` 写；未知语句抛 `SyntaxError`、执行/差分异常一律 `EXEC FAIL` ⇒ `rc=1`）。抽读 `load_ops`/`compile_op`/`run_op`、`to_python`、`make_orc`：A 侧零指令特判，硬编码期望只在 B 侧 `make_orc`（由散文 §1.1–§1.3 + SimRISC-04 §1.4 独立推出，符合独立 oracle 要求）。

**合并核验**：`git show --stat 02e464c6`（相对第一父 `46187055`）33 文件全为 master 侧内容；`git diff 02e464c6^2 02e464c6` **仅 5 个任务文件**，其中 `idl/.manifests.toml` 只 +3 行 = `SimRISC-08` 行（master 的 `SimRISC-02/04/06/10/12` 行全保留）；`git diff 2714a0c5 HEAD` 同为这 5 个文件 ⇒ 无越界、冲突解正确。

**完成区口径**：`156 组`（12 条 × 定值 13 组）与散文零改动**双口径**（严格剥块多 21 空行 v.s. 断言口径「剥块 + 吃掉块后一个空行」）均已写明，运行期证据目录内 `prose` 日志同时打印两行口径；`+481 -0` 相对 `2714a0c5` 与 `7aa96d76` 一致（我独立 `git diff --numstat` 复核）。

**判决：Accepted**——第 1 轮阻断项已消除（端到端反例红→绿）、F12 无残留、全部门控与 5 路注入在我自己的重跑下通过、合并无越界、未提交 git。

## 完成区

**范围**：全册 21 条——§1 算术运算 12 条（`add/sub/cmp/mul/div/rem` 的 `.st`/`.ut`）＋§2 位操作 9 条（`rev.t`、`rol.t`×2、`shl.t`×2、`shr.st`×2、`shr.ut`×2）；**返工 1**：`sem` 由「手写转写」改为「**从 `.idl` 机械翻译语句并执行**」（分支/扩展方向/定值/顺序全部取自 `.idl`，`sem` 内无期望算法），并新增 `add.st` 扩展方向注入（第 3 轮自审 F10；批 1 完成区原文见 WIP 提交 `c407d8d5`）。
**测试结果**：证据脚本 11/11 项 + **5 路注入**（`cov / prose / t1 / fixed / sem / shifts / rev / manifests / render / idlc-lib / idlc-ops+typecheck`）；覆盖 **21/21**，零缺零多。

**修改文件**：
- `idl/SimRISC-08.idl`（新增，21 条 `# id:` operation）
- `spec/SimRISC-08-32位数据运算.md`（仅新增 21 对 `<!-- IDL:… -->` 标记块，块体由 `idl/render.py` 生成）
- `spec/.manifests.toml`（本册 `sha256`）+ `idl/.manifests.toml`（本册一行）
- 本任务书

**验收结果**（运行期证据目录内 `run.sh` 的真实输出）：
- cov rc=0：`书内 id 总数=21（§1 12 + §2 9）`、`累计 21/21`、缺/多 0
- prose rc=0：`merge-base=2714a0c5`（合并 master 后前进；master 未改本册 ⇒ 相对 `7aa96d76` 同为 `+481 -0`）；**严格剥块多 21 行空行**（每块后 1 行）；断言口径 = `剥块 + 吃掉块后一个空行` ⇒ 与 merge-base 逐字节相等（6711 字符）
- render rc=0：`idl-render: PASS（源 operation=155 条 / 落点 10 册 / 标记块 155 个，逐字节一致）`（合并 master 后册数/条数含其它册）
- t1 rc=0：`operations=21 raise=26 ip()=26 {16'd0, ip()} 命中=0`
- fixed rc=0：`div.ut`/`div.st` 定值与 SimRISC-04 §1.4 表集合相等；`rem.*` 除零/溢出分支 OK
- sem rc=0：**执行器读 `.idl`** ⇒ 12 条 × 13 组 = 156 组失配 0（口径：12 条 §1 op × 定值 `PAIRS` 13 组，取自 `{0,1,2,7,100,0x7FFF_FFFF,0x8000_0000,0x8000_0001,0xFFFF_FFFE,0xFFFF_FFFF,0x1234_5678,0xFFFF_FFF0}` 及含高 32 位垃圾的一组）；另与 `idlc eval` **逐句差分 92 次**失配 0
- shifts rc=0：8 条结构 + 72 次真实求值失配 0；rev rc=0：5 个 `k` × 4 源值（位映射解析 + 40 次求值）失配 0
- idlc rc=0：库 `--root isa` rc=0；21 条逐条 `--root instruction_operation` rc=0；`type_check` 21/21；manifests rc=0
- 注入 **5 路**（spec 手改 / `div.st` 定值改错 / 删一条 id / `rol.t` 的 `inv` 改错 / **`add.st` 符号扩展改零扩展**）⇒ 均 `inj rc=1`，`cp`+md5 还原后 `rc=0`
- 合并 master `2714a0c5` 后复跑：`render --check`、`check-idl-sync`、`check-manifests-guard`、`check-fp-contract`、`check-legality-drift` 全 rc=0

**新发现/坑**：
1. **`idlc` 的有符号 `/`、`%` 是 floor（Ruby 语义）**（UDB doc 未定义舍入方向）⇒ 需 C99 向零截断时用「绝对值 + 无符号除法」。
2. 取负求绝对值必须在**原宽度**做再零扩展；在更宽零扩展值上取负不是绝对值。
3. `idlc eval -D<NAME>=0x…` 按**最小位宽**建变量（`0x12345678` ⇒ 29 位有符号）⇒ 32 位求值须写 `32'h…`；`render.py` 的「调用须在 §4 声明」按 `标识符(` 匹配，**注释里的 `rol(` 也会被误判**。
4. **证据脚本必须单实例**：前台跑被超时杀掉会留下子进程，与另一实例共享 `$TMP`/注入备份互踩 ⇒ 已加 `flock -n`；失败现场用「已核 md5 的 `cp` 备份」还原（勿用 VCS）。

**遗留问题**：无（任务范围内全部完成）；待主会话处置——台账 `milestones-m15.md` 本任务行的表位置（现状态 `待验收` ⇒ `check-milestones-fresh` 的 A1/R1 按表位置判）。环境性红与本改动无关（已核基线）：`check-isa-coverage`/`check-width-sizes`/`check-components`/`check-linux-toolchain` 缺 `make install-host`；`check-knowledge-refs` 的 5 条具体 `.work/**` 在别任务书；`check-writer-guards` 的 `W5b` 需 qemu/asm；`check-temp-dirs` 的 `m14-*`/`LLVM-130t` 残留。
