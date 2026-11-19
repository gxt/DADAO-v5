# m15-idl-005: `SimRISC-05`（64位地址运算）逐条 operation

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-spec-001`（语法基线、寄存器模型、语义库、`idl/render.py` 已就绪）
**可并行分片**：可与其它 `m15-idl-0xx` 并行（**各册独立文件**）；`idl/README.md §4` 语义库**不得自行动手**（缺函数 ⇒ 待裁定）
**预估**：1–2 天
**档位**：中改
**状态**：待验收

## 目标

把 `spec/SimRISC-05-64位地址运算.md` 里**每条指令**写成一段 operation，落到 **`idl/SimRISC-05.idl`**，再由 `idl/render.py` 生成 spec 内的 `<!-- IDL:<id> BEGIN/END -->` 块。

> 本册若已有 `m15-spec-001` 留下的样板 operation（01/04/06/11/12 各 1 条），按**同一风格**补齐其余指令，不重写已有样板。

## 用户裁定（2026-11-19，必须遵守）

1. **不修改原来的散文内容**——`spec/` 里只允许 `render.py` 写标记块，散文一字不动；
2. **发现散文不对、或与其它册/`spec` 冲突 ⇒ 停下来问用户**：写进任务书「待裁定」（问题 + 依据 + 候选解释），**不得自行改散文、不得自行改语义库**；
3. 正常情况下**每条指令一个 operation**（一 `# id:` 一段）；确需合并/拆分时同样记「待裁定」。

## 指令清单（本册 6 条，以 `contracts/opcodes.yaml` 的 `spec_cite` 为准）

- `add.o_orrr_bbd`
- `add.si_riii_rb`
- `aip.si_riii_rb`
- `cmp.uo_orrr_dbb`
- `sub.o_orrr_bbd`
- `sub.o_orrr_dbb`


- **批 1**：§1. 加减操作 + §2. 自增自减
- **批 2**：§3. 比较操作 + §4. IP 相对寻址


- **批 1**：§1. 加减操作 + §2. 自增自减 + §3. 比较操作 + §4. IP 相对寻址

## 批次（每批 ≤4 h；做完一批返回，由主会话续派下一批）

> 任务号不拆（整册一起验收）；**同一个 `.idl` 文件，同册串行**。每批只做列出的节，做完即返回，不提交。全册 6 条 ⇒ 分 1 批。

- **批 1**：§1. 加减操作 + §2. 自增自减 + §3. 比较操作 + §4. IP 相对寻址

## 交付

1. `idl/SimRISC-05.idl`：上述每条一个 `# id: <id>` + operation；
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
2. 只动 `idl/SimRISC-05.idl` + spec 本册的标记块 + 本任务书；**不动其它册**。
3. **不改 `idl/README.md`**（语义库）——缺函数就记「待裁定」。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定（已裁定：T1/T2）

### T1/T2 已裁定（2026-11-19；语义库 v1 = `m15-idl-013`，合入 `90b9ee66`）

1. **原「待裁定 1：`aip.si` 的 IP 宽度」→ T1 已裁定**：`ip()` 为 `Bits<64>`（高 16 位恒 0），控制流写回只保留 `target[47:0]`。依据：用户 2026-11-19 裁定 T1（`discussing.md` N23）；`idl/README.md §4.3`/§7 v0.1。处置：`aip.si` 基址由临时方案 `rb[6'd0]` 改为 `ip()`（`rb[rbHA] = ip() + offset;`），并与本册 §4「IP = `rb0` 读出值」「全 64 位运算」一致；**该待裁定项关闭**。
2. **T1 连带项**：`ip()` 变宽后，6 处异常地址 `{16'd0, ip()}` 成为 80 位拼接 ⇒ 一并改为 `raise(…, ip())`（`raise` 的 `addr` 为 `Bits<64>`；不依赖 idlc 不校验位宽的行为）。
3. **T2（`set.w` 按 wyde 写 = 切片赋值）**：本册 6 条均不涉 `rf`/wyde 切片，无改动。依据：`idl/README.md §3` 新增段。
4. 无其它待裁定项；原「跨册另注（`SimRISC-06` 的 `br.eq` 用 `{16'd0, ip()}`）」已由 `m15-idl-013` 修正（`br.eq` 现为 `jump(ip() + $signed(scaled))`）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-19）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `aip.si` 初版用 `{16'd0, ip()}`，引入散文未述的「IP 高 16 位 = 0」前提（等同套用 48 位截断） | ✅已修（后被 T1 取代） | 基址临时改 `rb[6'd0]`（整 64 位 IP）；宽度分歧记「待裁定」 | 第 2 轮按 T1 改回 `ip()` |
| 证据脚本 `$RUBY_BIN/bundle` 拼错（RUBY_BIN 是文件而非目录）⇒ rc=126 | ✅已修 | 增加 `BUNDLE_BIN=$(dirname "$RUBY_BIN")/bundle` | `run.sh` 全 PASS |
| 注入判定只看 rc≠0：rc=126（命令失败）会被误判为「反例命中」 | ✅已修 | 三类注入分别加日志关键字门控 | `inj-tc` 日志点名该条，rc=1 |
| 复核 `cmp.uo` 写满 64 位是否属「自行发明」 | ❌不修 | 散文「结果 -1/0/1 可以作为有符号数解读」要求 -1 以 64 位全 1 位型写入；与 SimRISC-04 的 `cmp.uo` 一致 | `semantic-review.md` 第 5 节 |

### 第 2 轮 engineer 自审（返工：语义库 v1，2026-11-19）

返工前先 `git merge master`（FF 到 `629f8d7e`，含 `idl/README.md` v0.1 与 spec/SimRISC-00/03 散文改动）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| T1：`aip.si` 仍用临时 `rb[6'd0]` | ✅已修 | `rb[rbHA] = rb[6'd0] + offset;` → `ip() + offset;`；注释改为「`ip()` 64 位、高 16 位恒 0」 | `t1-ip64` PASS；idlc 类型检查 6/6 |
| T1 连带：`ip()` 变 64 位后 6 处 `{16'd0, ip()}` = 80 位拼接 | ✅已修 | 6 处 `raise(…, {16'd0, ip()})` → `raise(…, ip())` | 文件内无 `{16'd0, ip()}`/`rb[6'd0]`；`t1-ip64` 门控 |
| 复核其余 5 条是否受 T1 影响（IP/48 位） | ❌不修 | 逐条核：仅 `raise` 的异常地址涉及 IP；`add.o`/`sub.o`/`add.si`/`cmp.uo` 运算全用 `rb[]`/`rd[]`，无 48 位截断 | `semantic-review.md` §1/§2/§3/§5；`t1-ip64` |
| T2（`set.w` 切片赋值）是否涉及本册 | ❌不修 | 本册 6 条无 `set.w`/`rf` 切片 | 覆盖率 6/6 + 文件内容 |
| 新增 `idl/SimRISC-05.idl` 未登记、spec 本册 sha256 未更新 | ✅已修 | `idl/.manifests.toml` 增 `SimRISC-05.idl`；`spec/.manifests.toml` 重算本册 sha256 | `check-manifests-guard` rc=0 |

### 第 1 轮 reviewer 验收（2026-11-19，中改档，≥2 路独立注入）

**自证/范围**：分支 `m15-idl-005`，HEAD `d248cd6d`（WIP），`git status --porcelain -uall` 干净；注入前后两次 5 文件 md5 快照 `diff` 为空。`git diff 629f8d7e HEAD --stat` = **5 文件**（任务书、`idl/.manifests.toml`、`spec/.manifests.toml`、`spec/SimRISC-05-64位地址运算.md`、新增 `idl/SimRISC-05.idl`），与完成区声明一致。

**重跑（我的输出/退出码）**：
- `bash .work/evidence/m15-idl-005/run.sh` → **rc=0，13/13 PASS**：coverage `idl=6 opcodes=6 missing=[] extra=[]`；`render-check` PASS；`t1-ip64` PASS；`idlc-lib-isa` rc=0；6 条 op `compile rc=0`；typecheck `fail_count=0`；4 路注入 rc=1 且日志点名；restored 2 项 rc=0。
- `python3 idl/render.py --check` → `idl-render: PASS（…11 个，逐字节一致）` **rc=0**；`make check-idl-sync` **rc=0**；`make check-manifests-guard` → `结果: PASS（双向集合一致、sha256 全符）` **rc=0**。
- 独立覆盖率（我按 `contracts/opcodes.yaml` 的 `spec_cite` 前缀现场算）= 6 条，与 `.idl` 6 个 `# id:` 集合相等。

**独立注入（cp+md5，非 engineer 自检）**：
- A：`aip.si` 的 `rb[rbHA] = ip() + offset;` → `rb[6'd0] + offset;` ⇒ 重跑 `run.sh` **rc=1**（`FAIL t1-ip64`、`FAIL render-check`）⇒ `cp` 还原，md5 `30777fd9…` 相等。
- B：spec 标记块内 `rd[rdHB] = rb[rbHC] - rb[rbHD];` 的 `-`→`+` ⇒ 重跑 `run.sh` **rc=1**（`FAIL render-check`）⇒ 还原 md5 `32bd0a72…` 相等 ⇒ 复跑 **rc=0 全 PASS**。

**约束逐条**：
1. **T1 落实** ✅：`aip.si` 用 `ip()`；本册 `raise(..., ip())` **6/6**；`{16'd0, ip()}` 与 `rb[6'd0]` 在本册 `.idl`+spec **均 0 处**（`grep -c` 实测 0）。
2. **语义抽查 5 条** ✅：add.o/sub.o-bbd ↔ §1「64 位补码加减、全 64 位参与、不做地址截断」；sub.o-dbb ↔ §1「`rdHB = rbHC − rbHD`」；add.si ↔ §2「18 位有符号符号扩展后相加写回」（`{{46{imms18[17]}}, imms18}`=64 位）；aip.si ↔ §4「基址=IP、imms18 左移 12 位、全 64 位」（`{{34{…}}, imms18, 12'd0}`=64 位）；cmp.uo ↔ §3「整 64 位无符号、-1/0/1」（`Bits<N>` 无符号，README §2）。守卫 rb0/rd0 ⇒ ILLI ↔ 附录 B `dst_rb0`(4)/`dst_rd0`(2)。IP 口径 ↔ `SimRISC-00 §2.2`（rb0=当前指令地址、只读、64 位）+ `SimRISC-06`（64 位计算、写回 `rb0`、取低 48 位）+ README §4.3（`ip()`=Bits<64>、`jump` 写 `target[47:0]`）——一致。
3. **散文零改动** ✅：`git diff master -- spec/SimRISC-05-64位地址运算.md` = **93 insertions / 0 deletions**；逐行核 93 行全在 6 对 `<!-- IDL:* BEGIN/END -->` 块 + 6 个块间空行，无散文新增。
4. **清单** ✅：`idl/.manifests.toml` 仅 +3 行（`SimRISC-05.idl`，`owner="idl"`），其它条目未动；`spec/.manifests.toml` 仅改本册 sha256 `11bd07ba…`，与 `sha256sum` 实测一致。
5. **术语/越界** ✅：三处改动文件 `grep 银行` 无；任务书 diff 仅 状态/待裁定/审阅记录/完成区，**验收标准 6 条未改**。

**未闭合（不阻断）**：① `idl/SimRISC-01/04/11/12.idl` 仍残留 `{16'd0, ip()}`（1/1/2/1 处，engineer 已披露、属他任务范围）；② 审查期间 `master` 前进到 `71c359ee`（`idl/README.md` 的 `raise` 描述改写），本分支基于 `629f8d7e`，合入前需 rebase 并复跑门控。

**判决：Accepted**（diff 核 + 2 路独立注入（注入→FAIL→还原→回绿）+ `run.sh` 重跑 rc=0 + 3 项门控 rc=0；硬约束无违反）

## 完成区

**测试结果**：通过 13/13（覆盖率、render --check、T1 口径、idlc 库、6 条 operation 解析、真实类型检查、4 路注入、2 项还原回绿均 PASS；`run.sh` 退出码 0）
**修改文件**：`idl/SimRISC-05.idl`（新增，6 条 operation）；`spec/SimRISC-05-64位地址运算.md`（`git diff` 93 insertions / 0 deletions：6 对标记行 + render.py 生成块）；`idl/.manifests.toml`（登记新文件）；`spec/.manifests.toml`（本册 sha256）；本任务书。证据脚本/类型检查驱动/逐句对照在运行期证据目录
**验收结果**：
1. 覆盖率：`idl=6 opcodes=6 missing=[] extra=[]` rc=0
2. `python3 idl/render.py --check` rc=0；`make check-idl-sync` rc=0
3. idlc 两段式：`compile --root isa` rc=0；6 条 `compile --root instruction_operation` 全 rc=0；Ruby 驱动真实类型检查 `fail_count=0`
4. T1 复核：`ip()` = `Bits<64>`（README §4.3）；`aip.si` 用 `ip() + offset`；6 处异常地址已去 80 位拼接；其余 5 条无 IP/48 位截断
5. 反例门控：改 spec 1 字符 / 删 1 个 id / 注入未声明函数 / 回退 `aip.si` 到 `rb[6'd0]` ⇒ 均 rc=1 且日志点名；临时树重拷后 rc=0
6. `make check-manifests-guard` rc=0（双向集合一致、sha256 全符）
7. 「待裁定」→「已裁定」：T1 落 `aip.si`；T2 本册不涉（见上）
**新发现/坑**：T1 后 `ip()` 已是 64 位，旧样板里的 `{16'd0, ip()}` 会变成 80 位拼接，而 idlc **不校验实参位宽**（类型检查仍绿）⇒ 必须靠文本/语义门控发现；本册已清零，01/04/11/12 的残留属他任务。
**遗留问题**：无（原 T1 待裁定已关闭；跨册 `br.eq` 已由 `m15-idl-013` 修正）。
