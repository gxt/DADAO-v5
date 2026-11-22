# m15-idl-004: `SimRISC-04`（64位数据运算）逐条 operation

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-spec-001`（语法基线、寄存器模型、语义库、`idl/render.py` 已就绪）
**可并行分片**：可与其它 `m15-idl-0xx` 并行（**各册独立文件**）；`idl/README.md §4` 语义库**不得自行动手**（缺函数 ⇒ 待裁定）
**预估**：3–5 天
**档位**：中改
**状态**：已验证

## 目标

把 `spec/SimRISC-04-64位数据运算.md` 里**每条指令**写成一段 operation，落到 **`idl/SimRISC-04.idl`**，再由 `idl/render.py` 生成 spec 内的 `<!-- IDL:<id> BEGIN/END -->` 块。

> 本册若已有 `m15-spec-001` 留下的样板 operation（01/04/06/11/12 各 1 条），按**同一风格**补齐其余指令，不重写已有样板。

## 用户裁定（2026-11-19，必须遵守）

1. **不修改原来的散文内容**——`spec/` 里只允许 `render.py` 写标记块，散文一字不动；
2. **发现散文不对、或与其它册/`spec` 冲突 ⇒ 停下来问用户**：写进任务书「待裁定」（问题 + 依据 + 候选解释），**不得自行改散文、不得自行改语义库**；
3. 正常情况下**每条指令一个 operation**（一 `# id:` 一段）；确需合并/拆分时同样记「待裁定」。

## 指令清单（本册 33 条，以 `contracts/opcodes.yaml` 的 `spec_cite` 为准）

- `add.si_riii_rd`
- `add.so_rrrr_rd`
- `add.uo_rrrr_rd`
- `and.o_orrr_rd`
- `clmul.o_rrrr_rd`
- `cmp.si_rrii_rd`
- `cmp.so_orrr_rd`
- `cmp.ui_rrii_rd`
- `cmp.uo_orrr_rd`
- `div.so_orrr_rd`
- `div.uo_orrr_rd`
- `ext.so_orri_rd`
- `ext.so_orrr_rd`
- `ext.uo_orri_rd`
- `ext.uo_orrr_rd`
- `mul.so_rrrr_rd`
- `mul.uo_rrrr_rd`
- `or.o_orrr_rd`
- `rem.so_orrr_rd`
- `rem.uo_orrr_rd`
- `rev.o_orri_rd`
- `rol.o_orri_rd`
- `rol.o_orrr_rd`
- `shl.o_orri_rd`
- `shl.o_orrr_rd`
- `shr.so_orri_rd`
- `shr.so_orrr_rd`
- `shr.uo_orri_rd`
- `shr.uo_orrr_rd`
- `sub.so_rrrr_rd`
- `sub.uo_rrrr_rd`
- `xnor.o_orrr_rd`
- `xor.o_orrr_rd`


- **批 1**：§1.1 加减操作 + §1.2 自增自减 + §1.3 比较操作
- **批 2**：§1.4 乘除操作 + §1.5 无进位乘法 + §2.1 Logic operators：逻辑运算
- **批 3**：§2.2 Bit manipulating：位操作指令


- **批 1**：§1.1 加减操作 + §1.2 自增自减 + §1.3 比较操作
- **批 2**：§1.4 乘除操作 + §1.5 无进位乘法
- **批 3**：§2.1 Logic operators：逻辑运算 + §2.2 Bit manipulating：位操作指令

## 批次（每批 ≤4 h；做完一批返回，由主会话续派下一批）

> 任务号不拆（整册一起验收）；**同一个 `.idl` 文件，同册串行**。每批只做列出的节，做完即返回，不提交。全册 33 条 ⇒ 分 3 批。

- **批 1**：§1.1 加减操作 + §1.2 自增自减 + §1.3 比较操作
- **批 2**：§1.4 乘除操作 + §1.5 无进位乘法
- **批 3**：§2.1 Logic operators：逻辑运算 + §2.2 Bit manipulating：位操作指令

## 前置（语义库 v1 连带，`m15-idl-013`）

本册样板 `.idl` 里若出现 `{16'd0, ip()}`（`m15-spec-001` 时代写法），按 T1 裁定改为 `ip()` —— `ip()` 现为 `Bits<64>`、高 16 位恒 0；旧写法会拼成 80 位，而 **idlc 不校验位宽、不会报错**，必须人工核。

## 交付

1. `idl/SimRISC-04.idl`：上述每条一个 `# id: <id>` + operation；
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
2. 只动 `idl/SimRISC-04.idl` + spec 本册的标记块 + 本任务书；**不动其它册**。
3. **不改 `idl/README.md`**（语义库）——缺函数就记「待裁定」。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

（执行中如有 → 写入本节并返回）

**批 1：无。** 两处散文未明写项不构成矛盾、按契约依据实现（见语义对照 §2/§6/§8 与第 1 轮自审）。
**批 2：无。** 倍乘的 128 位布局（§1.4）、GF2 语义（§1.5）、除零/溢出定值表、截断方向与余数符号（§1.4）散文均已写明，逐条照写；见语义对照 §9–§13。
**批 3：无。** 逻辑运算（§2.1）、移位量位域/范围与循环移位公式、扩展的 `hd` 取位与扩展方向（§2.2）、`rev` 的块/单元算法与 `k` 合法性（§2.2.1/§2.2.2）散文均已写明；唯一推导是 `rev` 的等价位级置换（见语义对照 §19/§20）。

## 审阅记录

### 第 1 轮 engineer 自审（批 1，2026-11-19）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 样板 `add.so` 的 `raise(…, {16'd0, ip()})` 在语义库 v1 下是 80 位拼接，而 idlc **不校验实参位宽** | ✅已修 | 该行改 `raise(…, ip())`（T1） | `t1_no_legacy_ip.py` PASS（本册 0 处旧写法，9 处 raise 均 `ip()`）；idlc 类型检查 9/9 |
| `add.uo` 若照「ZX 至 128 位、rdHA=高 64 位」写，`rdHA` 恒 0，与散文「`rdHA` 为进位（0 或 1）」矛盾 | ❌不修（现写法已正确） | 65 位加宽加取 `sum[64]`，`rdHA = {63'd0, sum[64]}` | 语义对照 §2；idlc 类型检查通过（`Bits<65>` 来源可解析） |
| `sub.uo`「借位（0 或 1）」未写死方向 | ❌不修（按「借位发生 ⇒ 1」，即 x86 CF/borrow 口径，也是「借位」的直接读法） | 65 位零扩展减法取 `diff[64]` | 语义对照 §3；`bit64=1 ⇔ 被减数<减数` 的算术推导 |
| `cmp.si`/`cmp.ui` 立即数扩展方向散文未明写 | ❌不修（依据：`opcodes.yaml` 的 `imms12 signed=true`/`immu12 signed=false` + §1.3「通过指令编码区分数据类型」+ README §2） | 符号/零扩展至 64 位后比较 | 语义对照 §6/§8；未改散文 |
| 散文基线若取 `HEAD` ⇒ 新增标记恒 0、判据恒真/恒假（ISS-475） | ✅已修 | 默认基线锚 `merge-base`，并加「本次必须新增 ≥1 对标记」探针 | `run.sh` 反例 c（基线误取含块版本）rc=1；正例 rc=0 |
| 覆盖率若写死批内 9 条 id ⇒ 与编码表脱节无告警 | ✅已修 | `cover.py` 从 §1.1–§1.3 的 `simrisc` 助记符 × `opcodes.yaml` 的 `spec_cite` **现场派生** | 派生 9 条，与 `.idl` 相等；注入③（漏写一条）rc=1 |
| 他册（01/11/12）仍有 `{16'd0, ip()}` | ❌不修（越界） | T1 脚本只判本册，他册仅打印提示 | `run.sh` T1 段输出「提示·他册，不判红」 |

### 第 2 轮 engineer 自审（批 2，2026-11-19）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `render.py` 的「调用未声明函数」扫描把注释里的 `GF(2)` 当函数调用，渲染直接 FAIL | ✅已修 | 注释改「GF2 上的多项式乘（系数域两个元素）」 | `render.py --check` rc=0；`make check-idl-sync` rc=0 |
| 有符号除余若直接用 `$signed(a) / $signed(b)`：IDL 未规定有符号舍入方向、且溢出未定义，与散文「truncate-toward-zero」不能保证一致 | ❌不修（现写法正确） | 幅值相除/取余 + 按符号恢复；除零与溢出先判定 | `fixed_values.py` 逐值 PASS；语义对照 §11/§12 |
| 除零定值 / 溢出定值是否与 §1.4 表格逐值一致（人工核易漏） | ✅已修（加机器对账） | 新增 `fixed_values.py`：表格 ⇒ 分支取值 | 4 条 `.o` 全一致；注入⑨（定值改错）rc=1 |
| 覆盖率脚本对 §2.1 表格的解析会误收 `hd`/`orrr`/`immu6` 等字段名 | ✅已修 | 表格分支只认「带点」助记符（`TABLE_MNEMONIC_RE`） | `--upto 3 --derive-only` 派生 33/33 且集合相等；注入⑧ rc=1 |
| `fixed_values.py` 初版用 `endswith(".o")` 判 size ⇒ `div.so` 漏判（`.so` 结尾不是 `.o`） | ✅已修 | 改 `\.(?:[su])?o$`，并支持一行多助记符（`rem.sb`/…/`rem.so`） | 表格派生 4 条（原 0 条） |
| 注入⑦初版删 `div.uo` 围栏行不生效（定值表里还有 `div.uo` ⇒ 派生不缩水） | ✅已修 | 改用只出现在围栏的 `mul.so` 行 | 注入⑦ rc=1 |
| 注入⑧初版 needle 拼错（`xnor.o` 行尾无 `/`）⇒ 空注入却判「绿」；注入脚本 rc 无人检查 | ✅已修 | needle 改 `xor.o`；注入 python 后加 `rc` 守卫（失败即 `bad`） | 注入⑧ rc=1（日志点名未知助记符） |
| 7 条的 128 位布局 / GF2 语义 / 定值 / 符号规则是否都出自散文 | ❌不修（已逐句核对，无自造前提） | — | 语义对照 §9–§13 |

### 第 3 轮 engineer 自审（批 3，2026-11-19）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 注释里写 `rol(x, n)` 会被 `render.py` 的「调用未声明函数」扫描判红（批 2 的同类坑换了个函数名复现） | ✅已修 | 注释改为不带括号的公式叙述 | `render.py --check` rc=0；`make check-idl-sync` rc=0 |
| `cover.py` 的 `sections()` 只把「带编号标题」当边界 ⇒ §2.2 吞掉「附录 A 汇编速查表」，派生集合被附录表补齐（注入⑦因此失效） | ✅已修 | 任意标题（含「附录 A」）都作为节边界 | 派生 33 条来自正确节；注入⑦（删 §1.4 `mul.so` 行）rc=1 |
| 注入⑦的 f-string 里写了 `{rdHA, rdHB}` ⇒ `NameError` ⇒ 空注入却判绿 | ✅已修 | print 去掉花括号；注入脚本后加 rc 守卫 | 注入⑦ rc=1（日志报「多出 mul.so」） |
| `legality_guard.py` 规则名正则 `[a-z_]+` 不匹配 `dst_rd0` 的数字 ⇒ 26 条规则全被忽略 | ✅已修 | 改 `[a-z0-9_]+` | 规则解析 26/7/1；33 条守卫全一致 |
| `bit_ops.py` 只按 `hd[5:0]` 找表格行 ⇒ 漏掉 ext 行（散文写作 `rdHD[5:0]`） | ✅已修 | 两种写法都认 | 检查 13 条（原 9 条 + ext 4 条 + rev 1 条） |
| `BARE_RDHD_RE` 的否定前瞻多写一个 `)` ⇒ 误报「未切片」 | ✅已修 | 改 `(?!\[5:0\])` | `bit_ops.py` PASS |
| 「`shamt > N` 触发 ILLI」若按字面写成分支，在 `N=63`、6 位移位量下是**死代码** | ❌不修（不可达规则按注释说明，不写死分支） | — | 语义对照 §15；`bit_ops.py` 断言 13 条只有 `dst_rd0` 一个 raise |
| `rev.o` 用「位级置换」表达而散文给的是「块/单元」算法 | ❌不修（已独立复算等价） | — | Python 独立复算：`k∈{1,2,4,8,16,32}` 的位映射 == 单元反转；`k=8`/`k=1` 退化例与散文用途映射一致（语义对照 §19） |

### 第 1 轮 reviewer 验收（2026-11-19，档位：中改；结论：Accepted）

**重跑记录（全部为本人实跑，退出码现场取）**
1. 重跑运行期证据目录内 `run.sh`：`== 汇总：PASS=52 FAIL=0`、`ALL GREEN`、**rc=0**；其中 idlc 两段式：库 `compile --root isa` rc=0、33 条 operation `parse rc=0` **33/33**、`PASS typecheck` **33/33**；17 条「期望 rc=1」检查实际全为 rc=1。
2. 直跑验收命令：`python3 idl/render.py --check` → `PASS（源 operation=51 条 / 落点 7 册 / 标记块 51 个）` **rc=0**；`render.py --self-test` rc=0；`make check-idl-sync` **rc=0**；`make check-manifests-guard` **rc=0**；`cover.py --upto 3` → `RESULT: PASS（…累计 33/33；实际 33/33）` **rc=0**（派生集合现场得 33 条、与本册 `opcodes.yaml` 集合相等）。
3. 独立 oracle（本人自写、固定 seed=20261119、不复用 engineer 脚本）**15 项全 OK、rc=0**：`mul.uo`/`mul.so` 高 64=rdHA·低 64=rdHB（18×200 抽样）；`div.so`/`rem.so` 除零与 INT64_MIN÷−1 定值 + 向零截断 + 余数符号=被除数（363 组）且与 §1.4 定值表 6 项逐值一致；`clmul.o` == 系数数组独立复算（散文例 0b11×0b11=0b101≠9）；`ext` mask == 散文 `[hd:0]` 复制+符号/零扩展（hd 取边界+随机），4 条产物核对 orrr 切 `[5:0]`、orri 用 `immu6`、无裸 `rd[rdHD]`；`rev.o` 散文单元反转 == IDL 位级置换，**k∈{1,2,4,8,16,32}×277 值**，且 k=8==bswap64、k=1==整体位反序、合法 k={1,2,4,8,16,32}；`rol.o` IDL 公式 == 位串旋转 oracle，n∈0..63×73 值、n=0 恒等。
4. 散文零改动：剥标记块（含块后配套空行）后与 merge-base `5a21d33e` **逐字节相同**；非空散文行 247==247 逐行相同、两版文件最大连续空行均为 1；spec/.idl 相对 merge-base 各仅 1 行删除 = T1 裁定的 `raise(…,{16'd0, ip()})`→`ip()`（位于生成块内，属任务书「前置」授权）；相对批 1 WIP `3fa30b26` 起 spec 与 `.idl` **0 删除行（纯新增）**。
5. 改动范围：相对 merge-base **仅 4 文件**（`.idl`、本册 spec、`spec/.manifests.toml`（只动本册 sha256）、本任务书）；`idl/.manifests.toml` **0 改动**（本册已登记）；无版本号改动；起止两次 `git status --porcelain -uall` 均干净，HEAD 仍为 `86ad668b`（本人未提交）。
6. 独立注入 2 路（真文件，`cp`+md5 还原，均不在 engineer 的 18 路内）：A. 本册 spec §2.2.1 `rev.o` 合法 k 列删 `32` → `bit_ops.py` **rc=1**（`rev 表合法 k [1,2,4,8,16] ≠ 2 的幂集合 [1,2,4,8,16,32]`）→ `cp` 还原、md5 相同 → **rc=0**；B. `and.o_orrr_rd` 追加一条多余 `raise` → `legality_guard.py` **rc=1**（`raise 个数 2 ≠ 规则数 1`）→ 还原、md5 相同 → **rc=0**；还原后 `render --check` rc=0、`git status` 干净。
7. 三条自审独立复现：① 旧「只认带编号标题」边界 ⇒ §2.2 吞「附录 A」、`mul.so` 由附录表补齐——删 §1.4 `mul.so` 行后旧逻辑 **rc=0（假绿成立）**，现版同注入 **rc=1**；② 旧正则 `[a-z_]+` 丢 `dst_rd0` ⇒ 只解析 2 规则/8 id，新正则 3 规则/34 id（26 条在内）——机制复现；惟现版脚本对该状态**大声判红**，「静默」取决于未留存的旧脚本结构（无法复原，如实标注）；③ 旧谓词只认 `hd[5:0]` ⇒ 命中 1 行/**9 id**、ext 4 条不在检查集（新 **13 id**）；注入 ext 漏切片时旧谓词不产生任何 ext 报错，现版 `rc=1` 点名 `ext.uo_orrr_rd`。

**约束核验**：独立 worktree ✓ 未改主工作树 ✓ 未提交 git ✓ 临时文件仅落任务临时目录 ✓ 只动允许的 4 文件 ✓ 未改语义库与 `idl/README.md` ✓ 还原只用 `cp`+md5（未用 checkout/restore/stash）✓ 任务书无运行期路径 ✓ 完成区 19 行、各轮记录 ≤40 行 ✓「待裁定」批 1/2/3 均列明 ✓。

**发现（文档级，不阻断，交 architect 收尾改）**：a) 完成区「反例 18 路，均 rc=1」——实跑为 **17** 条「期望 rc=1」检查全 rc=1（另有 `render --self-test` 一条 rc=0、内含 4 路负向注入），18 的口径需注明；b) 第 3 轮自审「原 9 条 + ext 4 条 + rev 1 条」算术为 14，现版实际 13（移位 8 + ext 4 + rev 1）；c) 任务书「## 批次」段重复三处，且首处「批 3」仅 §2.2、与另两处「§2.1+§2.2」不一致。

**判决：Accepted**——验收命令块在我的重跑下全部通过、2 路独立注入均可达 FAIL 并回绿、三条自审复现成立、硬约束无违反。

## 完成区（全册 33/33 已交付，2026-11-19；`**状态**` → `待验收`）

**本批 id（批 3，17 条）**：`and.o`/`or.o`/`xor.o`/`xnor.o`（`_orrr_rd`）；`shl.o`/`rol.o`/`shr.uo`/`shr.so`/`ext.uo`/`ext.so` 各两形态（`_orrr_rd` + `_orri_rd`）；`rev.o`（`_orri_rd`）
**测试结果**：证据脚本 **52/52 PASS，rc=0**；idlc 库 rc=0、全册 33 条解析 33/33、类型检查 33/33；受影响 L1 门控 9 项 rc=0；三张表 oracle（§1.4 定值 / 附录 B 守卫 / §2.2 位域与合法 k）全绿
**修改文件**：`idl/SimRISC-04.idl`（批 3 新增 17 条 operation，全册 33 条）；`spec/SimRISC-04-64位数据运算.md`（17 对标记 + `render.py` 生成块；散文零改动）；`spec/.manifests.toml`（本册 sha256 `fdfdd679→092b9e97`）；本任务书。`idl/.manifests.toml` 无需改（已登记）。证据脚本、三张表 oracle 与逐句对照在运行期证据目录
**验收结果**：
1. 覆盖率：**33/33**（现场派生 = `.idl`，零缺零多）；派生集合另与 `opcodes.yaml` 本册 33 条**集合相等**（防解析漏读缩水）
2. `python3 idl/render.py --check` rc=0；`make check-idl-sync` rc=0；`idl/render.py --self-test` rc=0；`make check-manifests-guard` rc=0 及其余 L1 门控 8 项 rc=0
3. idlc 两段式：库 rc=0；全册 33 条 `compile --root instruction_operation` 全 rc=0；类型检查 33/33（解码变量由 `opcodes.yaml` 现场派生）
4. 散文零改动：删块后与 `merge-base` `5a21d33e` 逐字节相同（相对 WIP 提交：spec 与 `.idl` 均纯新增）
5. 表 oracle：§1.4 定值表 4 条 `.o` 逐值一致；附录 B 26+7+1 条规则 ⇒ 33 条 ILLI 守卫逐条一致（含「无规则的条不得有守卫」）；§2.2 移位量位域 8 条 + ext 4 条 + rev 合法 k 一致
6. T1：本册 `{16'd0, ip()}` 0 处；33 处 `raise` 第三参数全为 `ip()`
7. 反例（18 路，均 rc=1，含本轮新增 3 路）：散文改 1 字 / 基线误取含块版本（ISS-475）/ 生成段改字节 / 删 `# id:` / 漏写一条 / 派生源缺一行 / §2.1 表格未知助记符 / 定值改错 / **缺 ILLI 守卫** / **移位量未切片** / **one-hot 判定缺失** / 语法错 / 参数个数错 / T1 回退旧写法 / 清单删条目 / manifest diff 多一行；真文件注入经 `cp`+md5 还原后回绿
**新发现/坑**：
- 派生脚本的「节边界」必须认**任意**标题：只认带编号标题会让 §2.2 吞掉「附录 A 汇编速查表」，把缺失的助记符从附录补齐 ⇒ 覆盖率判据假绿（本轮注入⑦才暴露）。
- `render.py` 的「调用未声明函数」扫描连**注释**里的 `名(...)` 也算（`GF(2)`、`rol(x, n)` 两次踩到）⇒ 注释里别写带括号的公式。
- 注释/print 里的 `{…}` 在 f-string 中是插值 ⇒ 空注入/报错；注入脚本必须带 rc 守卫（本轮注入⑦再次踩到）。
- 「`shamt > N` 触发 ILLI」在本册是**不可达规则**（6 位移位量 vs N=63）：写成分支会是死代码，改为注释说明并用「raise 计数」断言机械守住。
**遗留问题**：无（批 3 完成，全册 33/33）；他册（01/11/12）`{16'd0, ip()}` 残留属各自任务范围。
