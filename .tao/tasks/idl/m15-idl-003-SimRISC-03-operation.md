# m15-idl-003: `SimRISC-03`（16位立即数操作）逐条 operation

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-spec-001`（语法基线、寄存器模型、语义库、`idl/render.py` 已就绪）
**可并行分片**：可与其它 `m15-idl-0xx` 并行（**各册独立文件**）；`idl/README.md §4` 语义库**不得自行动手**（缺函数 ⇒ 待裁定）
**预估**：1–2 天
**档位**：中改
**状态**：已验证

## 目标

把 `spec/SimRISC-03-16位立即数操作.md` 里**每条指令**写成一段 operation，落到 **`idl/SimRISC-03.idl`**，再由 `idl/render.py` 生成 spec 内的 `<!-- IDL:<id> BEGIN/END -->` 块。

> 本册若已有 `m15-spec-001` 留下的样板 operation（01/04/06/11/12 各 1 条），按**同一风格**补齐其余指令，不重写已有样板。

## 用户裁定（2026-11-19，必须遵守）

1. **不修改原来的散文内容**——`spec/` 里只允许 `render.py` 写标记块，散文一字不动；
2. **发现散文不对、或与其它册/`spec` 冲突 ⇒ 停下来问用户**：写进任务书「待裁定」（问题 + 依据 + 候选解释），**不得自行改散文、不得自行改语义库**；
3. 正常情况下**每条指令一个 operation**（一 `# id:` 一段）；确需合并/拆分时同样记「待裁定」。

## 指令清单（本册 8 条，以 `contracts/opcodes.yaml` 的 `spec_cite` 为准）

- `andn.w_rwii_rb`
- `andn.w_rwii_rd`
- `or.w_rwii_rb`
- `or.w_rwii_rd`
- `set.ow_rwii_rd`
- `set.w_rwii_rf`
- `set.zw_rwii_rb`
- `set.zw_rwii_rd`


- **批 1**：§1. 立即数常数赋值：RD 组 + §2. 立即数常数赋值：RB 组
- **批 2**：§3. 立即数常数赋值：RF 组


- **批 1**：§1. 立即数常数赋值：RD 组 + §2. 立即数常数赋值：RB 组 + §3. 立即数常数赋值：RF 组

## 批次（每批 ≤4 h；做完一批返回，由主会话续派下一批）

> 任务号不拆（整册一起验收）；**同一个 `.idl` 文件，同册串行**。每批只做列出的节，做完即返回，不提交。全册 8 条 ⇒ 分 1 批。

- **批 1**：§1. 立即数常数赋值：RD 组 + §2. 立即数常数赋值：RB 组 + §3. 立即数常数赋值：RF 组

## 交付

1. `idl/SimRISC-03.idl`：上述每条一个 `# id: <id>` + operation；
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
2. 只动 `idl/SimRISC-03.idl` + spec 本册的标记块 + 本任务书；**不动其它册**。
3. **不改 `idl/README.md`**（语义库）——缺函数就记「待裁定」。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

原 4 项均已处置：**T2/T3/T4 由用户裁定后的散文/语义库改动消解**（`m15-idl-013`，已合入 master），T1 保留说明（按散文实例化）；另新增 1 项口径确认（第 5 条）。

1. **【待确认】§2（rb 组）未复述逐位语义**：§2 只列 `set.zw/or.w/andn.w` 与操作数类型；operation 按 §1 同名指令定义实例化到 `rb` 组。
   `m15-idl-013` 在 §1 补了 `wpN ↔ 位段` 与「`immu16` 整体写入该 wyde」，但未在 §2 复述。建议维持（§2 = §1 的实例化）；若 §2 另有语义须补写。

2. **【已裁定（`m15-idl-013` 改散文）】** 原「选中 wyde = immu16」是跨句合成（旧 §1 只讲其余 48 位置 1/置 0）。新 §1 已明写：
   「`wpN` 选中的就是寄存器中 `[16*N+15 : 16*N]` 这 16 位（`wp0` = `[15:0]` LSW、`wp1` = `[31:16]`、`wp2` = `[47:32]`、`wp3` = `[63:48]` MSW），
   指令的 16 位 `immu16` 字段**整体**写入该 wyde；`set.ow`/`set.zw` 的「其余 48 位」即**未被选中的另外三个 wyde**。」
   ⇒ 8 条逐条复核：`wpN` 位段与「整体写入」一致，无改动。

3. **【已裁定（`m15-idl-013` 改散文）】** 原 `set.w` 写 `rf` 与 SimRISC-00 §2.3「浮点寄存器只能用于浮点类指令」的表面冲突。新 §2.3 改为
   「浮点寄存器**专用于**浮点类指令」，并补「**直接赋值/复制类不受此限**：`set.w`/`set.ft`/`set.fo`/`ld.t`/`ldm.t`/`rf2rf`/`rd2rf` 只是对 `rf` 的
   **直接赋值或位复制**，**不牵涉任何运算**，因此不属「浮点类指令」，不受「专用于浮点类指令」的限制」⇒ `set.w_rwii_rf` 合法，operation 无需改动。

4. **【已裁定（`m15-idl-013` 改语义库）】** rf 的 16 位写原无对位视图。`idl/README §3` 已补「**按 wyde 写 = 切片赋值**：
   `set.w`/`or.w`/`andn.w`/`set.ow`/`set.zw` 只改 `wpN` 选中的那**一个** wyde ⇒ 写成切片赋值 `rf[d][wpN*16+15 : wpN*16] = …`…
   `set.ow`/`set.zw` 的「其余 48 位全 1 / 全 0」按整寄存器赋值表达」⇒ 8 条已改用该写法（见第 2 轮自审）。

5. **【口径确认】§1 新补段「`immu16` 字段**整体**写入该 wyde」与 `or.w`/`andn.w` 的组合语义**：该句在总述段（覆盖本节 4 条指令），
   字面上与 §1 后文「`or.w` … 替换为 `(rdHA[wyde] | immu16)`」「`andn.w` … `(rdHA[wyde] & ~immu16)`」并存时易读成矛盾（后两条是「与既有值组合」而非「整体写入」）。
   本任务按「**位段归属**」读该句（`immu16` 的 16 位全部落在选中 wyde、不跨 wyde），组合方式仍按各指令句 ⇒ 与实现一致。
   建议：若求无歧义，该句可加限定「`set.*` 为整体写入；`or.w`/`andn.w` 见各条」。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| semcheck 首版把「目的寄存器被改」误判成「其它组被改」（164/384 FAIL） | ✅已修 | 改为「只允许 `(bank, idx)` 变化 + 写次数 ≤1」 | 384/384 PASS |
| rf0 的 `wp1/wp3`「完全写无效」若写成 `rf[0]=old` 也等价，但会掩盖「不写」 | ❌不修 | 保留分支留空（不产生写） | 向量断言 `writes=0` 且值不变 |
| 异常码错误（Malign 冒充 Illegal）原 semcheck 不查 | ✅已修 | 加静态断言：7 条须含 `raise(…Illegal…)`、`set.w_rf` 不得含 `raise(` | 注入 Malign ⇒ 7 条报红 rc=1 |
| `idlc` 的 type_check 不查赋值位宽（65 位拼进 `Bits<64>` 仍 rc=0） | ✅已修（兜底） | semcheck 求值器对整寄存器写入强制位宽 64、切片目标强制「位段宽 == 表达式宽」 | 注入 65 位拼接 ⇒ semcheck 报红 |
| spec 需插入 8 对 `BEGIN/END` 锚点（原册无标记） | ✅已修 | 只插锚点，块内容由 `render.py` 写；散文正文由 `prose_check.py` 与 HEAD 逐行比对 | `prose` 非空行逐行相同 |

判决：全部 finding 已处置，无未修项（当时状态置 `待验收`）。

### 第 2 轮 engineer 自审（合入 master `629f8d7e` 后）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `idl/README v0.1` 把 `ip()` 改为 `Bits<64>`：原 `{16'd0, ip()}` 变 80 位，而 `idlc` type_check **不报**（实测 rc=0） | ✅已修 | 7 处 `raise(…{16'd0, ip()})` → `raise(…, ip())`；semcheck 静态断言同步为新形态 | `tc.rb` 8/8 rc=0；semcheck 384/384 PASS |
| `idl/README §3` 新约定「按 wyde 写 = 切片赋值」：原实现用整寄存器拼接 | ✅已修 | `or.w`/`andn.w`/`set.w` 改 `r[i][lo+15:lo] = …`；`set.w rf0` 用 `rf[0][33:32]`/`rf[0][4:0]`；`set.ow`/`set.zw` 仍按约定用整寄存器赋值；semcheck 解释器补切片目标 | semcheck 384/384 PASS；idlc 8/8 |
| 新散文 §1 补段（`wpN` 位段 + `immu16` 整体写入）与本实现是否一致 | ❌不修（已一致） | 无 | `semantic-compare.md` 逐句对照更新；`wpN` 四分支位段 = `[16N+15:16N]` |
| 新散文 §2.3「直接赋值/复制类不受此限」 | ❌不修（已一致） | `set.w_rwii_rf` 注释补该依据 | operation 无合法性判定，与附录 B「无附加合法性规则」一致 |
| `idl/README §3` 示例写可变切片 `wpN*16+15 : wpN*16`（idlc 实测接受） | ❌不修 | 保留常量四分支：下游模型不必支持可变切片，且逐 wyde 一目了然 | semcheck 覆盖 `wpN=0..3` 全 4 分支 |

判决：无未修 finding ⇒ 状态保持 `待验收`。

### 第 1 轮 reviewer 验收（中改，≥2 路注入）

**重跑（worktree `/tmp/opencode/m15-idl-003/wt`，分支 `m15-idl-003`，HEAD `34c25358`，`git status -uall` 干净）**
- `./.work/evidence/m15-idl-003/run.sh` → rc=0，`PASS=30 FAIL=0`（注入前、注入还原后各 1 次，两次同分）
- `python3 idl/render.py --check` → rc=0（源 13 / 落点 6 册 / 块 13）；`make check-idl-sync` rc=0；`make check-manifests-guard` rc=0
- `coverage.py` → `8 条 / 8 条，集合相等` rc=0；标记块 8 == `# id:` 8
- idlc：库 `compile --root isa` rc=0；逐条 `instruction_operation` **8/8 rc=0**；`tc.rb` 现场跑出 **8 行 OK、rc=0**
- `semcheck.py` → `8 × 48 = 384` 向量一致 rc=0
- **reviewer 独立注入（run.sh 未列的 2 路）**：① `rf[6'd0][33:32]=immu16[1:0]` → `[4:0]` ⇒ semcheck rc=1（`切片目标宽 2 != 表达式位宽 5`，4/384 FAIL）；② `set.ow` wp0 `{48'hFFFF…, immu16}` → `{48'd0, immu16}` ⇒ semcheck rc=1（8/384 FAIL）。`cp` 还原后 md5 `a05d19ac…` 与注入前相等，`run.sh` 回绿 rc=0
- run.sh 内置 4 类注入在我重跑中同样各 rc=1、还原回绿；覆盖计数（标记块/id/切出条数）均现场派生，未写死

**约束核验（逐条）**
- diff 对 merge-base `629f8d7e` **恰 5 文件** = 任务书 / `idl/.manifests.toml` / `spec/.manifests.toml` / 本册 spec / 新增 `idl/SimRISC-03.idl`
- 散文零改动：`git diff <base> -- spec/SimRISC-03*` = **192 insertions / 0 deletions**
- T1：本册 7 处 `raise(…, mode(), ip())`，本册 `{16'd0, ip()}` = 0 处；T2：`or.w`/`andn.w`/`set.w` 均切片赋值 `r[i][16N+15:16N]`，`set.w rf0` 分写 `[33:32]`/`[4:0]`（wp1/wp3 不写），`set.ow`/`set.zw` 仍整寄存器赋值
- 语义抽查 4 条（`andn.w_rd`/`or.w_rb`/`set.ow_rd`/`set.w_rf`）与 §1/§3/附录 B 逐句相符；`set.w` 写 `rf` 与**新** `SimRISC-00 §2.3`（「专用于浮点类」+「直接赋值/复制类不受此限」列明 `set.w`）及 §2.3.1（rf0 只更新 `[33..32]`/`[4..0]`）一致
- 清单：`idl/.manifests.toml` 对 base 只 +3 行（仅 `[files."SimRISC-03.idl"]` 一条）；`spec/.manifests.toml` 对 base 仅本册 sha256 1/1；无「银行」；完成区 16 行（≤30）

**判决：Accepted**（验收命令块在本人重跑下全绿，约束无违反）

**未闭合项 / finding（均非阻断）**
1. run.sh 散文基线取 `HEAD`（= 本分支 WIP 自身）⇒ 散文改动若随提交进入则自检恒绿；本轮由 reviewer 以 `git diff <merge-base>` 0 deletions 独立闭合，建议后续任务把基线锚到 merge-base/master。
2. 验收窗口内 master 已前进（`71c359ee`、`8d141209` 005 合入、`fc46861f`）⇒ 现在 `git diff master` 显示 6 文件，多出的 `idl/README.md` 是 **master 侧**变化、非本任务改动；合入时 `idl/.manifests.toml`、`spec/.manifests.toml` 与 005 条目相邻，需架构师留意冲突。
3. 跨册 T1 残留：`SimRISC-01/04/11/12.idl` 仍有 5 处 `{16'd0, ip()}`，我实测 idlc 对 80 位拼接 rc=0（不报）；master `fc46861f` 已在 001/004/012 任务书加前置提醒，非本任务范围。
4. 待裁定第 1 条（§2 未复述逐位语义）与第 5 条（T5 措辞）仍留用户/架构师确认。

**对 T5（「`immu16` 整体写入」× `or.w`/`andn.w` 组合语义）的判断**：该句在 §1 **总述段**，与后文各指令句并存；唯一自洽读法是**位段归属**读——`immu16` 16 位全部落在 `wpN` 选中 wyde、不跨 wyde，**组合方式以更具体的各指令句为准**（`or.w` = 旧 wyde | immu16、`andn.w` = 旧 wyde & ~immu16）。实现与该读法一致，语义无二义；建议按待裁定第 5 条给该句加限定（`set.*` 为整体写入；`or.w`/`andn.w` 见各条），由用户裁定措辞。

## 完成区

**测试结果**：通过 30/30（运行期证据目录内 `run.sh`，`rc=0`）；失败原因：无
**修改文件**：`idl/SimRISC-03.idl`（新增，8 条 operation）；`spec/SimRISC-03-16位立即数操作.md`（仅加 8 对锚点 + `render.py` 生成的块；散文为 `m15-idl-013` 版本，本任务一字未改）；`idl/.manifests.toml`（只加 `[files."SimRISC-03.idl"]` 一条，用户 2026-11-19 授权，照 `m15-idl-005` 做法）；`spec/.manifests.toml`（只改本册 sha256）；本任务书
**验收结果**（合入 master `629f8d7e` 后重跑）：
1. 覆盖率：`opcodes.yaml(SimRISC-03)=8 条 / .idl=8 条`，集合相等 rc=0；标记块 8 == id 8
2. `python3 idl/render.py --check` → `PASS（源 operation=13 / 落点 6 册 / 标记块 13，逐字节一致）` rc=0；`make check-idl-sync` rc=0
3. `idlc` 两段式：库 `compile --root isa` rc=0；逐条 `compile --root instruction_operation` 8/8 rc=0；`tc.rb`（库符号+解码变量）8/8 rc=0
4. 语义：`semcheck.py`（小解释器 vs 按新散文另写的参照模型）8 × 48 = 384 向量一致 rc=0（含切片目标与 rf0 掩码）
5. 逐句对照：证据目录 `semantic-compare.md`（`andn.w_rd` / `or.w_rb` / `set.ow_rd` / `set.w_rf`，已按新散文更新）
6. 注入自检 4 类（改 spec 块 / 改 id / 语义改错 / 改散文）均 rc=1，重新快照后 rc=0
7. 散文保全：正文非空行与 `HEAD`（= `m15-idl-013` 版）逐行相同 rc=0
8. `make check-manifests-guard` → `PASS（双向文件/子目录集合一致、sha256 全符）` rc=0
**新发现/坑**：
- `ip()` 改 `Bits<64>` 后 `{16'd0, ip()}` 变 80 位，`idlc` type_check **不报**（实测 rc=0）⇒ 拼接宽度错须靠静态断言/独立 oracle。
- `idlc` 不在 PATH；UDB 参考的 `bin/idlc` 是 mise 包装（脱离 git 检出会失败）；用 mise ruby 直接跑：`ruby -I<udb>/tools/ruby-gems/idlc/lib -ridlc/version <udb>/…/bin/idlc`。
- `idlc` type_check 不查赋值/切片位宽 ⇒ 由 `semcheck.py` 求值器强制（整寄存器 64 / 切片「位段宽 == 表达式宽」）。
**遗留问题**：无。清单已按用户 2026-11-19 指示登记（`idl/.manifests.toml` 一条 + `spec/.manifests.toml` 本册 sha256）；其余 finding 全部已修。
