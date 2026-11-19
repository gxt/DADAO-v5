# m15-idl-006: `SimRISC-06`（控制流）逐条 operation

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-spec-001`（语法基线、寄存器模型、语义库、`idl/render.py` 已就绪）
**可并行分片**：可与其它 `m15-idl-0xx` 并行（**各册独立文件**）；`idl/README.md §4` 语义库**不得自行动手**（缺函数 ⇒ 待裁定）
**预估**：2–3 天
**档位**：中改
**状态**：待验收

## 目标

把 `spec/SimRISC-06-控制流.md` 里**每条指令**写成一段 operation，落到 **`idl/SimRISC-06.idl`**，再由 `idl/render.py` 生成 spec 内的 `<!-- IDL:<id> BEGIN/END -->` 块。

> 本册若已有 `m15-spec-001` 留下的样板 operation（01/04/06/11/12 各 1 条），按**同一风格**补齐其余指令，不重写已有样板。

## 用户裁定（2026-11-19，必须遵守）

1. **不修改原来的散文内容**——`spec/` 里只允许 `render.py` 写标记块，散文一字不动；
2. **发现散文不对、或与其它册/`spec` 冲突 ⇒ 停下来问用户**：写进任务书「待裁定」（问题 + 依据 + 候选解释），**不得自行改散文、不得自行改语义库**；
3. 正常情况下**每条指令一个 operation**（一 `# id:` 一段）；确需合并/拆分时同样记「待裁定」。

## 指令清单（本册 15 条，以 `contracts/opcodes.yaml` 的 `spec_cite` 为准）

- `br.eq_rrii_rd`
- `br.n_riii_rd`
- `br.ne_rrii_rd`
- `br.nn_riii_rd`
- `br.np_riii_rd`
- `br.nz_riii_rb`
- `br.nz_riii_rd`
- `br.p_riii_rd`
- `br.z_riii_rb`
- `br.z_riii_rd`
- `call_iiii_ra`
- `call_rrii_ra`
- `jump_iiii_rb`
- `jump_rrii_rb`
- `ret_riii_ra`


- **批 1**：§1. 条件跳转指令 + §2. 无条件跳转指令
- **批 2**：§3. 函数调用 + §4. 函数返回


- **批 1**：§1. 条件跳转指令 + §2. 无条件跳转指令
- **批 2**：§3. 函数调用 + §4. 函数返回

## 批次（每批 ≤4 h；做完一批返回，由主会话续派下一批）

> 任务号不拆（整册一起验收）；**同一个 `.idl` 文件，同册串行**。每批只做列出的节，做完即返回，不提交。全册 15 条 ⇒ 分 2 批。

- **批 1**：§1. 条件跳转指令 + §2. 无条件跳转指令
- **批 2**：§3. 函数调用 + §4. 函数返回

## 交付

1. `idl/SimRISC-06.idl`：上述每条一个 `# id: <id>` + operation；
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
2. 只动 `idl/SimRISC-06.idl` + spec 本册的标记块 + 本任务书；**不动其它册**。
3. **不改 `idl/README.md`**（语义库）——缺函数就记「待裁定」。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

无。（说明：`spec/SimRISC-06 §1` 未逐条写六种条件的判据，但条件码 `N/NN/Z/NZ/P/NP` 的判据在
`spec/SimRISC-00 §3.2 标识位说明` 有定义、`.tao/contracts/contract-isa.md §8.2.2` 逐条列出并有
`spec_cite`，故按 spec 落，不算散文缺失/矛盾。）
批 2 同理无待裁定：`ret` 的落点口径（「来源可能不是 `ra63`、可能 RASUF，弹栈判定见 SimRISC-00」）
由 `ras_pop()` 承担 §2.4.2 D1–D4b；`call` 的压栈（含递归折叠 / RASOF / MemRAS）由 `ras_push()`
承担 §2.4.1 C1–C3b；两条库函数的语义在 `idl/README §4.5` 有声明，散文与 `SimRISC-00 §2.4` 一致。

## 完成区

**测试结果**：通过 52/52（运行期证据目录内的 `run.sh`，rc=0）；全册 15 条 idlc 解析 15/15、类型检查 15/15；`render.py --check` PASS（源 37 条 / 块 37 个）。
**修改文件**：`idl/SimRISC-06.idl`（全册 15 条）、`spec/SimRISC-06-控制流.md`（14 对 IDL 标记 + 渲染块，散文零改动）、`spec/.manifests.toml`（本册 sha256）、本任务书。
**验收结果**：
- **覆盖率**：全册 id 由 `contracts/opcodes.yaml` 的 `spec_cite: SimRISC-06` 现场派生，与 `.idl` 双向一致 **15/15**（批 1 `br.`/`jump` 12 + 批 2 `call`/`ret` 3），零缺零多。
- **散文零改动**：剥掉 IDL 块后与 **merge-base `bbea18db`** 逐字节相同（ISS-475 口径，不用 HEAD）。
- **T1**：全册无 `{16'd0, ip()}`；目标形态 = IP 相对 12 条（`jump(ip() + $signed(…))`）/ 绝对 2 条（`jump(rb[rbHA] + rd[rdHB] + $signed(…))`）/ RAS 1 条（`target = ras_pop(); jump(target);`）。
- **RAS 纪律**：指令正文无 `ra[]` 直访；`call` 只 `ras_push` + 跳转、不写 `rd`；`ret` 落点来自 `ras_pop()`、不写死 `ra63`（对齐 §4「来源可能不是 `ra63`」）。
- **idlc 两段式**（mise ruby 3.4.11 + UDB 只读参考 ruby-gems）：库 `compile --root isa` rc=0；15 条 operation `compile --root instruction_operation` 全 rc=0；类型检查（`add_global_symbols` → 注入解码变量 → `type_check`）15/15 rc=0。
- **语义抽查（批 2 三条，散文 ↔ operation）**：
  - `call_iiii_ra`：「返回地址 = 当前 `call` 指令地址 + 4」↔ `Bits<64> ret_addr = ip() + 64'd4; ras_push(ret_addr[47:0]);`；「压入 `ra63`（RegRAS 栈顶），`[63:48]` 递归计数、`[47:0]` 返回地址，压栈判定见 SimRISC-00」↔ `ras_push`（§2.4.1 C1–C3b 由该库函数承担）；「Addr = rb0 + (imms24 << 2)」↔ `Bits<26> scaled = {imms24, 2'b00}; jump(ip() + $signed(scaled));`。
  - `call_rrii_ra`：「Addr = rbHA + rdHB + (imms12 << 2)、`rbHA` 仅读」↔ `jump(rb[rbHA] + rd[rdHB] + $signed(offset));`（无 `rb[rbHA]`/操作数写）；返回地址同 iiii 形式。
  - `ret_riii_ra`：「从 RAS 弹出并跳转、来源可能不是 `ra63`、可能 RASUF」↔ `Bits<48> target = ras_pop(); … jump(target);`；「同时把 `rd` 改成 18 位立即数（符号扩展至 64 位）」↔ `rd[rdHA] = {{46{imms18[17]}}, imms18};`；「`rd0` 时 `imms18` MUST 为 0，否则运行期 ILLI」↔ ILLI 检查。
- **反例注入 7 路**（各「注入 → 预期 FAIL → `cp`+md5 还原 → 回绿」）：渲染漂移、T1 零扩展拼接、`jump` 参数个数、散文改一字、删 `# id:`、`ret` 的 ILLI 判据被改软、`ret` 落点写死 `ra63`。
- **门控 rc=0**：`check-idl-sync`、`check-manifests-guard`、`check-spec-drift`/`-codeblocks`/`-purity`/`-refs`/`-cite-targets`、`check-asm-list-drift`/`-prose`、`check-legality-drift`/`-invariants`、`check-no-residue`、`check-dirs`、`check-spec-numbering`、`check-index-blobs`、`check-contracts-dir`。
**新发现/坑**：① **idlc 的赋值左值 / 数组索引查符号大小写敏感**（值读取路径不敏感）：注入解码变量须用 `.idl` 实际拼写（`rdHA` 而非 `rdha`），否则 `no symbol named 'rdHA'`——这是 oracle 注入口径问题，与 README §2「书写上不敏感于 opcodes.yaml」不矛盾；② `check-knowledge-refs` 在 master 上本就红（5 条具体证据脚本路径落在 m15-idl-003/005/011 任务书），非本任务引入；③ 本 worktree 无 `.dadao/cross-toolchain` ⇒ `check-isa-coverage`/`check-width-sizes` 缺 `llvm-mc`/`clang` 红，需 `make install-host`；④ `idlc` CLI 须 `ruby -I … -r idlc/version` 预载版本模块；⑤ 反例锚点须取唯一文本：`jump(ip() + $signed(scaled));` 首现在 `br.eq`，按首现注入会改错条。
**遗留问题**：无（全册 15/15 交付）；②③为环境/既有红，非本任务改动所致。

## 审阅记录

### 第 1 轮 engineer 自审

自审范围：`idl/SimRISC-06.idl` 全文（79 行新增）、spec 新增 11 对标记块、证据脚本与判据实现。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 反例 f3 锚点取 `jump(ip() + $signed(scaled));` 首次出现 → 实际改的是 `br.eq`，却检查 `br.n` ⇒ 假绿 | ✅已修 | 锚点改为 `br.eq` 那行唯一注释尾，检查改为 `tc_one br.eq_rrii_rd` | 注入后 rc=1，日志 `Wrong number of arguments to 'jump' … Expecting 1, got 2`；还原后 rc=0 |
| F2 `C2`/`D1` 断言 `exp="all rc=0"` 与 `got="fail=0/12"` 恒不等（恒红） | ✅已修 | 期望值改为 `fail=0/$n`（现场计数，不写死） | `run.sh` PASS：`exp=fail=0/12 got=fail=0/12` |
| F3 注入「非空」断言拿 md5 与字面量 `changed` 比 ⇒ 恒红 | ✅已修 | 比较改为 `changed`/`same` 二值 | 5 路注入均 `exp=changed got=changed` |
| F4 「预期 FAIL」断言用文本 `rc!=0` 比 `rc=$rc` ⇒ 恒红 | ✅已修 | 二值化为 `nonzero`/`zero` | 5 路均 `exp=nonzero got=nonzero` |
| F5 各 operation 重复声明局部变量 `scaled`/`offset` | ❌不修 | — | 每条 op 独立编译（README §6.1 第 8/9 条），与已合入的 SimRISC-05 同形，无冲突 |
| F6 是否夹带散文未说的前提（如 `rd0` 判 ILLI、rb0 特判） | ❌不修（确认无） | — | 批 1 各条只写条件 + 地址 + `jump`；`rd0` 特例仅 br.z/br.nz 按散文写注释，未新增判据 |
| F7 `$signed({immsN, 2'b00})` 的符号语义依赖拼接视为补码 | ⏸延后（已双证） | — | 与样板 `br.eq` 同形；idlc 类型检查 12/12 rc=0；位宽 14/20/26 = 编码层 + 2，人工核对无溢出 |


### 第 2 轮 engineer 自审

自审范围：批 2 新增 3 条 operation（`call_iiii_ra`/`call_rrii_ra`/`ret_riii_ra`）、新增 3 对 spec 标记块、判据脚本改动（coverage 改全册、新增 `ras`、T1 改形态断言）、7 路注入。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 批 2 首版 typecheck 全红（`no symbol named 'rdHA'`）：注入名取 opcodes 小写、而 idlc 在**赋值左值/数组索引**处大小写敏感 | ✅已修 | `split_ops.py` 增加 `resolve_spelling()`，从 operation 正文按大小写不敏感匹配出真实拼写再注入 | `ret_riii_ra.vars` = `rdHA=6,imms18=18`；15/15 typecheck rc=0 |
| F2 `sem`/`ras` 判据把**注释里**的 `ra63` 误判成「写死落点」⇒ 恒红 | ✅已修 | 判据改看「去 `#` 注释后的代码」（`code_of()`） | `A sem`/`A ras` rc=0；7 路注入签名不变 |
| F3 T1 原判据「op 内含 `ip()`」对 `ret` 会假绿（`ip()` 只出现在 ILLI `raise` 里） | ✅已修 | 改按形态表：IP 相对 / 绝对 / RAS 三档，`ret` 断言 `jump(target);` 且禁 `jump(ip()` | `A t1` PASS：IP 相对 12 / 绝对 2 / RAS 1 |
| F4 `call` 注释写「RASOF 时不得跳转」「判定先于**任何**状态修改」超出散文口径 | ✅已修 | 改为引用 §2.4.1 C1–C3b / §2.4.2 D1–D4b 原文措辞，只保留「判定通过后才修改 RA/存储」 | 重新渲染后 `render --check` rc=0；散文零改动仍 PASS |
| F5 `ret` 中 `ras_pop()` 与 `rd` 写的先后（散文只说「同时」） | ❌不修（不作语义断言） | 按「先判定、后修改」排列并注明依据 | 两处语句各自对应散文一句，未新增前提 |
| F6 `jump(target)` 以 48 位实参隐式零扩展 | ❌不修（人工核） | — | 类型检查通过；48 位地址零扩展与 `jump` 只写 `target[47:0]` 一致；`ret` 不读 `ra` 直访（`ras` 判据） |
| F7 注入 f6/f7 是否真能失败（防恒绿） | ✅已验 | — | 日志分别为「缺 `if (rdHA == 6'd0 && imms18 != 18'd0) {`」「直接访问 ra[]、未弹栈、落点写死 ra63」 |

### 第 1 轮 reviewer 验收

**自证**：`git rev-parse --show-toplevel` = 本任务独立 worktree；branch `m15-idl-006`、HEAD `180812b1`、`git status -uall` 空（rc=0）；merge-base(HEAD, master) = `bbea18db`；主工作树 `master` 干净，本审 **0 commit**。
**改动面**：`git diff --numstat bbea18db..HEAD` = 仅 4 文件（任务书 54/3、`idl/SimRISC-06.idl` 114/0、`spec/.manifests.toml` 1/1、本册 spec **184/0**）⇒ spec 零删除；剥标记块+块后让位空行后与 `bbea18db` 逐字节相同（`prose` rc=0）。
**重跑（我自己的 rc）**：`idl/render.py --check` rc=0（源 37 / 块 37）；`make check-idl-sync` rc=0；`make check-manifests-guard` rc=0（PASS，sha256 22 全符）。
**覆盖**：opcodes.yaml `spec_cite: SimRISC-06` 现场派生 **15** == `.idl` 15 == spec 标记 15，集合相等零缺零多；证据脚本 `coverage` rc=0（15/15 = 批1 12 + 批2 3）。
**idlc 两段式（独立于 run.sh 重跑）**：库 `compile --root isa` rc=0；15 条 `compile --root instruction_operation` fail=0/15 rc=0；类型检查 fail=0/15。
**一键证据**（运行期证据目录内的 `run.sh`）整跑：`checks=52 failed=0 RESULT: PASS` rc=0 ⇒ 与完成区 52/52 一致。
**完成区所列其余门控逐个重跑 rc=0**：spec-drift / -purity / -codeblocks / -refs / -cite-targets / -numbering、asm-list-drift / asm-prose、legality-drift / -invariants、no-residue、dirs、index-blobs、contracts-dir。
**既有/环境红（非本任务）**：`check-knowledge-refs` rc=2，5 条具体引用全在 m15-idl-003/005/011 任务书、本任务书 0 条；`check-isa-coverage`、`check-width-sizes` rc=2（缺 `llvm-mc`/`llvm-readelf`、无 cross-toolchain）——与完成区声明一致。

**语义抽查 5 条（散文 ↔ operation）**
- `call_iiii_ra`：「返回地址 = 当前 call 地址 + 4」↔ `ret_addr = ip() + 64'd4; ras_push(ret_addr[47:0]);`，且**先压栈后 jump**（`jump()` 写 rb0，ret_addr 必须取自跳转前的 `ip()`）；「Addr = rb0 + (imms24 << 2)」↔ `jump(ip() + $signed({imms24,2'b00}))`；「rbHA 仅读」↔ 无操作数写。
- `call_rrii_ra`：「Addr = rbHA + rdHB + (imms12 << 2)、rbHA 仅读」↔ `jump(rb[rbHA] + rd[rdHB] + $signed(offset))`；返回地址同 iiii 形式。
- `ret_riii_ra`：落点只经 `ras_pop()`（去注释后 `ra[`、`ra63` 各 0 处）；`rd[rdHA] = {{46{imms18[17]}}, imms18}` = 46+18 = 64 位、符号位取 bit17（imms18 为 [17:0] 有符号，opcodes.yaml 实核）；`rdHA==0 && imms18!=0 ⇒ raise(Illegal, mode(), ip())` ↔ §4 硬约束。
- 条件位级 ↔ `SimRISC-00 §3.2` + `contract-isa §8.2.2`：N=[63]=1、NN=[63]=0、Z=全0、NZ=非全0、P=[63]=0 ∧ [62:0]≠0、NP=[63]=1 ∨ 全0、EQ/NE=全宽 ==/!= —— 逐条一致，无 RISC-V 分支直觉。
- 位宽：`{imms12,2'b00}`=14、`{imms18,2'b00}`=20、`{imms24,2'b00}`=26 = 编码位宽+2（opcodes.yaml 12/18/24 实核）符号扩展不溢出；rb0 读出 = IP、`jump` 只写低 48 位 ↔ idl/README §3/§4.3。
- **T1**：`.idl` 内 `16'd0` 0 处、唯一 `raise(...)` 用 `ip()`；形态 = IP 相对 12 / 绝对 2 / RAS 1（`t1` rc=0）。

**独立注入 3 路（均不在 engineer 7 路内；一律 cp+md5 还原）**
- R1 `br.p` 砍掉 `[62:0] != 63'd0` → 证据脚本 `sem` rc=**1**（缺该片段）→ cp 还原 md5 `2be7c37e…` 一致 → rc=**0**。
- R2 手改 spec 内 `br.n` 渲染块 `1'b1 → 1'b0`（不碰 `.idl`）→ `render --check` rc=**1**（贴出漂移 diff），同时 `prose` rc=0（两门控互补）→ 还原 md5 `1ba63c9e…` 一致 → rc=**0**。
- R3 `spec/.manifests.toml` 本册 sha256 改一位 → `manifests` rc=**1**、`check-manifests-guard` rc=**2** → 还原 md5 `e0635e44…` 一致 → rc=**0**、rc=**0**。
- 还原后：`git status -uall` 空；4 个目标文件 pre/post md5 逐行 diff 无差异。

**engineer 三条自审发现核实**
- ① idlc 大小写敏感：**属实**（注入 `rdha` → rc=1 `no symbol named 'rdHA'`；注入 `rdHA` → rc=0）；**但括注「值读取路径不敏感」不成立**——`x = rdHA;`、`jump(ip()+rdHA)` 注入小写均 rc=1，真正不检查的是「`if` 条件里的数组索引」（注入垃圾名或零变量也 rc=0）。
- ② T1 假绿陷阱：**属实**（`ret` 正文含 `ip()` 且只出现在 `raise(..., ip())` 一行，旧「含 `ip()`」判据对 ret 必绿）。
- ③ 注释误判：**属实**（`ret` 的 `ra63` 只在注释里；不剥注释 `ras` 恒红、剥后 rc=0，两种算法我均实测）。

**findings（不阻断，交 architect 收尾处理）**
- f-a 完成区「新发现/坑①」的括注「值读取路径不敏感」与实测相反，建议删掉该括注（①其余部分属实）。
- f-b 「散文零改动」的机器判据连带剥掉块后 1 个让位空行；只剥标记行会多出 14 个空行（spec 零删除、各 spec 门控 rc=0），口径宜写明「标记块 + 其后让位空行」。
- f-c 证据脚本「F 无残留改动」的白名单恰是被注入的 4 个文件，发现不了「这 4 个文件未还原」；还原另由逐路 md5 断言兜底（本审 3 路实测可达 FAIL）。

**约束核验**：独立 worktree、未改主工作树、本审 0 commit、只动 4 文件、`idl/README.md` 未改、版本号未升（`0.5.7-rc` 原样）、还原全用 cp+md5（未用 checkout/restore/stash/show）、任务书与本记录无运行期路径、完成区 18 行 / 每轮审阅记录 ≤40 行。

**判决：Accepted** —— 上述验收命令在我自己的重跑下全部 rc=0；3 路独立注入均「注入 → 红 → cp+md5 还原 → 回绿」；三条自审发现已核，f-a~f-c 记为非阻断 finding。
