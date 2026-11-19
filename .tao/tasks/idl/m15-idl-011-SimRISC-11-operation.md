# m15-idl-011: `SimRISC-11`（核芯功能扩展指令）逐条 operation

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-spec-001`（语法基线、寄存器模型、语义库、`idl/render.py` 已就绪）
**可并行分片**：可与其它 `m15-idl-0xx` 并行（**各册独立文件**）；`idl/README.md §4` 语义库**不得自行动手**（缺函数 ⇒ 待裁定）
**预估**：1–2 天
**档位**：中改
**状态**：已验证

## 目标

把 `spec/SimRISC-11-核芯功能扩展指令.md` 里**每条指令**写成一段 operation，落到 **`idl/SimRISC-11.idl`**，再由 `idl/render.py` 生成 spec 内的 `<!-- IDL:<id> BEGIN/END -->` 块。

> 本册若已有 `m15-spec-001` 留下的样板 operation（01/04/06/11/12 各 1 条），按**同一风格**补齐其余指令，不重写已有样板。

## 用户裁定（2026-11-19，必须遵守）

1. **不修改原来的散文内容**——`spec/` 里只允许 `render.py` 写标记块，散文一字不动；
2. **发现散文不对、或与其它册/`spec` 冲突 ⇒ 停下来问用户**：写进任务书「待裁定」（问题 + 依据 + 候选解释），**不得自行改散文、不得自行改语义库**；
3. 正常情况下**每条指令一个 operation**（一 `# id:` 一段）；确需合并/拆分时同样记「待裁定」。

## 指令清单（本册 5 条，以 `contracts/opcodes.yaml` 的 `spec_cite` 为准）

- `cfx2rc_crrr_cfx`
- `cfx2rd_crrr_cfx`
- `escape_ciii_cfx`
- `fence_ciii_cfx`
- `trap_ciii_cfx`


- **批 1**：§1. 指令域与执行条件 + §2. 陷入指令
- **批 2**：§3. 退出指令 + §4. 寄存器传输指令
- **批 3**：§5. 屏障指令


- **批 1**：§1. 指令域与执行条件 + §2. 陷入指令 + §3. 退出指令 + §4. 寄存器传输指令 + §5. 屏障指令

## 批次（每批 ≤4 h；做完一批返回，由主会话续派下一批）

> 任务号不拆（整册一起验收）；**同一个 `.idl` 文件，同册串行**。每批只做列出的节，做完即返回，不提交。全册 5 条 ⇒ 分 1 批。

- **批 1**：§1. 指令域与执行条件 + §2. 陷入指令 + §3. 退出指令 + §4. 寄存器传输指令 + §5. 屏障指令

## 交付

1. `idl/SimRISC-11.idl`：上述每条一个 `# id: <id>` + operation；
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
2. 只动 `idl/SimRISC-11.idl` + spec 本册的标记块 + 本任务书；**不动其它册**。
3. **不改 `idl/README.md`**（语义库）——缺函数就记「待裁定」。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

**结论：R1–R4 全部已裁定并落实**（用户 2026-11-19 裁定 T5/T6/T7，由 `m15-idl-013`（master `90b9ee66`）落进 `idl/README.md §4`）；本册 5 条 operation 已全部写出，不再有待裁定阻塞项。

### R1 `escape_ciii_cfx` —— **已裁定（T5）并落实**

- 裁定：补 `inner_cfx_code() -> Bits<6>`、`cfx_frame_valid(cfxha) -> Boolean`、`cfx_escape_enter(cfxha, imm)`（`imm` 为**字节**偏移 0/4）。
- 落实：`idl/README.md §4.6` 三函数已在；本册 `escape_ciii_cfx` 按 `DADAO-12 §5.3` 步骤 0–3 写出（步骤 0 的 4 项检查在 operation、步骤 1–3 在 `cfx_escape_enter`；步骤 2 的 `inner_cfx_code ← excp_prev_cfx_code`（cg5 rc1，`m14-spec-009` 2026-11-18 裁定 B）由该 builtin 承担，operation 注释指明）。
- 「跨册取事实」口径：`SimRISC-11 §3` 未写旧语义，实现细节取 `DADAO-12 §5.1/§5.3`，与派生方向一致。

### R2 `cfx2rd_crrr_cfx` / `cfx2rc_crrr_cfx` —— **已裁定（T6）并落实**

- 裁定：补 `cfx_read(cfxha, cg, rc) -> Bits<64>`、`cfx_write(cfxha, cg, rc, value)`；**读写权限（RW/HW/RO/保留 ⇒ `CFXREG`）不在 operation 里判**，由 SEE 寄存器表（`DADAO-12 §3`–`§4`）描述。
- 落实：两条 operation 均为「reserved ⇒ ILLI」+ 一次 `cfx_read`/`cfx_write`；`cfxreg` 来源掩码拒绝（⇒ `CFXPERM`，`DADAO-12 §5.2`）同样留给实现按 SEE 的 mask 表给出（operation 注释声明）。

### R3 `fence_ciii_cfx` —— **已裁定（T7）并落实**

- 裁定：照 UDB 加 `builtin function cfx_fence(Bits<6> cfxha, Bits<6> pred, Bits<6> succ)`（**无 body**，`pred`/`succ` 为 **6 位**，非 RISC-V 的 4 位）。
- 落实：operation 末尾为 `cfx_fence(cfxHA, immu18[11:6], immu18[5:0])`；顺序/可见性由实现提供、IDL v0 不建模（注释声明，与裁定一致）。

### R4 `CFXESC` 的进入目标 —— **已裁定并落实**（master `71c359ee`）

- 裁定：`idl/README.md §4.3` 的 `raise` 描述已写明「**进入目标由 `code` 按 spec 路由**：一般同步异常进当前运行模式 monitor（`DADAO-12 §5.2`）；**`CFXESC` 进当前 cfx**（`§5.3` 步骤 0）」。
- 落实：本册 `escape_ciii_cfx` 的 `raise(ExceptionCode::CfxEsc, mode(), ip())` 与该说明一致（目标 cfx 由 `code` 路由），无需新增 `cfx_raise`；`trap`/`cfx2rd`/`cfx2rc` 的 `ILLI`/`CFXPERM` 目标本就是当前 monitor，同样相符。

## 语义逐句对照（验收第 4 条）

> 5 条全量对照（①–⑤）；`ip()` 按 T1 为 `Bits<64>`（高 16 位恒 0），故 `raise` 的地址实参直接写 `ip()`。

**① `trap_ciii_cfx` ↔ `SimRISC-11 §1/§2` + `DADAO-12 §5.2`**

- `cfx_is_reserved ⇒ ILLI` ↔ §1「保留 cfx ⇒ ILLI」+ `§5.2（一）` 表第 1 行（⇒ 当前运行模式 monitor）。
- `cfx_trap_denied ⇒ CFXPERM` ↔ `§5.2（一）` 表第 2 行（目标 cfx 的 `<mode>_cfxtrap` 拒绝源 cfx ⇒ `CFXPERM` ⇒ 当前 monitor）+ `README §4.6` 的函数定义（同义）。
- `cfx_trap_enter(cfxHA, immu18)` ↔ `§5.2（一）` 表第 3 行（CFXTRAP ⇒ 目标 cfx）+ 步骤 4–7（计数 → 现场（`excp_prev_cfx_code` 在改写前保存）→ 模式/目标 → 向量）；`immu18` 为服务号。

**② `escape_ciii_cfx` ↔ `SimRISC-11 §3` + `DADAO-12 §5.1/§5.3`**

- `imms18[17:1] != 17'd0 ⇒ ILLI` ↔ §3「`imms18[17:1]` 为 SBZ、手工编码非零 ⇒ ILLI」。
- `cfx_is_reserved ⇒ ILLI` ↔ §1（本章保留 cfx 均 ILLI）+ `§5.3 步骤 0` 第 2 条。
- `cfxHA != inner_cfx_code()` ⇒ `CFXESC` ↔ `§5.1`「第一个参数必须是当前 cfx」+ `§5.3 步骤 0` 第 3 条（切换任何状态之前）。
- `!cfx_frame_valid(cfxHA)` ⇒ `CFXESC` ↔ `§5.3 步骤 0`「当前 cfx 无有效异常帧（`excp_cause_id = 0`）」（README §4.6 该函数即此判据）。
- `imm = {61'd0, imms18[0], 2'b00}` ↔ §3「`imms18[0]` 即字节偏移 bit2，合法值只有 0 或 4」。
- `cfx_escape_enter(cfxHA, imm)` ↔ `§5.3 步骤 1–3`（恢复 `global_cfx_intr_mask`；`inner_run_mode ← excp_prev_run_mode`、`inner_cfx_code ← excp_prev_cfx_code`（cg5 rc1，`m14-spec-009` 2026-11-18 裁定 B）；`escape_num++`；`IP = excp_cause_ip + (imms18 << 2)`）。
- 结论：与 2026-11-18 / 2026-11-19 两次裁定后的语义一致；散文 §3 未写旧语义（只是不完整），无冲突。

**③ `cfx2rd_crrr_cfx` ↔ `SimRISC-11 §4`（+ `DADAO-12 §5.2`）**

- `cfx_is_reserved ⇒ ILLI` ↔ §4「`cfx_<cfxname>` 为 reserved ⇒ ILLI」+ §1。
- `rd[rdHD] = cfx_read(cfxHA, cgHB, rcHC)` ↔ §4「cfx2rd 是将 `cfx_<cfxname>_cgHB_rcHC` 的值设置到 `rdHD` 中」；`cg/rc` 取值即编码字段。
- 存在性/权限（⇒ `CFXREG`）与 `cfxreg` 掩码拒绝（⇒ `CFXPERM`）**不写成语句** ↔ §4 散文把它们交给 SEE 寄存器表 / `DADAO-12 §5.2`（T6 裁定：operation 只表达访问）。

**④ `cfx2rc_crrr_cfx` ↔ `SimRISC-11 §4`（+ `DADAO-12 §5.2`）**

- `cfx_is_reserved ⇒ ILLI` ↔ §4「reserved ⇒ ILLI」。
- `cfx_write(cfxHA, cgHB, rcHC, rd[rdHD])` ↔ §4「cfx2rc 是将 `rdHD` 的值设置到 `cfx_<cfxname>_cgHB_rcHC` 中」。
- 权限/存在性/`cfxreg` 掩码同上（T6）。

**⑤ `fence_ciii_cfx` ↔ `SimRISC-11 §5`**

- `immu18[17:12] != 0 ⇒ ILLI` ↔ §5 位域表 `hb`「SBZ，必须为 0」+ 异常规则「`hb != 0` ⇒ ILLI」。
- `cfx_is_reserved ⇒ ILLI` ↔ §5 异常规则 + §1。
- `cfx_fence(cfxHA, immu18[11:6], immu18[5:0])` ↔ §5「`pred` = `immu18[11:6]`、`succ` = `immu18[5:0]`」+ 资源域「`cfx0`/`cfx_umon` = all cfx，`cfx1`–`cfx63` = 指定 cfx」+「只保证本 hart…不跨 hart、不等待 DMA、不负责 TLB/icache」；顺序语义由实现提供（T7，builtin 无 body）。

## 审阅记录

### 第 2 轮 reviewer 验收

**判决：Accepted**（阻断项已消除；小改档，1 路独立注入）

**自证**：worktree `/tmp/opencode/m15-idl-011/wt`、分支 `m15-idl-011`、HEAD `6b39be30`；`git status --porcelain -uall` **rc=0 干净**；相对 merge-base `71c359ee` 改动集仍**恰 4 文件**（`idl/SimRISC-11.idl`、`spec/SimRISC-11`、`spec/.manifests.toml`、本任务书）；`idl/.manifests.toml` diff 0 行。

**阻断已消除（已提交状态下重跑）**：运行期证据目录内的 `run.sh` ⇒ **`PASS=37 FAIL=0`、`RUN_RC=0`、`ALL GREEN`**（`grep '\[FAIL\]'` 无命中），跑于 HEAD `6b39be30`（比完成区声明的 `05af728a` 更新，结论更强）。第 1 轮红的两项现均绿：`prose_unchanged.py（显式基线=merge-base 71c359ee）rc=0`、`（默认基线=merge-base）rc=0`；新增反例 c「基线误取含块版本」期望 rc=1 ⇒ **实际 rc=1**（可达 FAIL 成立）。

**独立注入 1 路（未在 run.sh 内）**：`cp` 备份 `prose_unchanged.py`（md5 `4f045e01848d98cf2d3a68c6ca2c63d3`）→ 把 `merge-base HEAD master` 改回 `rev-parse HEAD` ⇒ `基线: 6b39be30… / 基线=10 现=10 / 新增标记 0 行 / RESULT: FAIL`、**rc=1** → `cp` 还原 ⇒ md5 `4f045e01848d98cf2d3a68c6ca2c63d3` **相等** ⇒ `基线: 71c359ee… / 基线=2 现=10 / 新增标记 8 行 / RESULT: PASS`、**rc=0**；无 `*.preinject` 残留。

**门控（我自跑，全 rc=0）**：`idl/render.py --check`、`make check-idl-sync`、`make check-manifests-guard`；`idlc` 库 `--root isa` rc=0、operation 解析 **5/5**、类型检查 **5/5**；`cover.py` 覆盖 **5/5** 零缺零多。

**文档项核对**：完成区 `PASS=37` 与末次日志 `汇总：PASS=37 FAIL=0` **一致**（11 路注入分类 3+2+1+1+1+1+2=11 自洽）；R4 已改为「**已裁定并落实**（master `71c359ee`）」，其引文与 `idl/README.md §4.3` 逐字相符（「一般同步异常进当前运行模式 monitor；`CFXESC` 进当前 cfx」），与 `raise(CfxEsc, mode(), ip())` 一致。

**约束核验**：散文零改动（删块+配套空行后与 master 逐字节相同）、5 条语义未回退、无「银行」、未提交 git、未改主工作树、临时文件均在 `/tmp/opencode/m15-idl-011/`。

**未闭合（非阻塞，沿第 1 轮）**：ISS-475 仍 open（跨任务系统性问题，架构师已登记处置口径）；`.work/**` 证据脚本不入仓（gitignore），其修改仅存在于工作树——属既定约定，不作 finding。

### 第 1 轮 reviewer 验收

**判决：Needs Revision**（唯一阻断项 = 证据脚本提交后不回绿；5 条语义与门控本身全过）

**重跑**（worktree `wt`，先 `git merge master` 拿 `71c359ee` 的 `raise` 路由说明；基线 = merge-base `71c359ee`）
- 运行期证据目录内的 `run.sh` ⇒ **`PASS=34 FAIL=1`，`RUN_RC=1`**；失败项 `prose_unchanged.py（期望 rc=0，实际 rc=1）`，输出 `标记行数: 期望 基线+8 / 实际 基线=10 现=10 … 新增标记 实际 0 行`
- 根因（非环境）：`prose_unchanged.py` 默认基线取 `git show HEAD:<spec>`，而 WIP `074adc2d` 已把本册 spec 提交进 HEAD ⇒ 「新增标记」恒 0 ⇒ **提交后必红**（违反 `DD-Y003`「提交后仍须回绿」）。同一类问题已被架构师登记 **ISS-475**（master `5a21d33e`，P3/open，处置口径 = 锚 merge-base）。
- 独立复核：把基线换成 `git show merge-base:spec/…` 后 `prose_unchanged.py` **rc=0**（散文删块后与基线**逐字节相同**，新增恰 4 对标记）⇒ 交付物散文无恙，红仅来自基线锚点。

**门控（我自跑，全 rc=0）**：`render.py --check`、`check-idl-sync`、`render.py --self-test`、`check-manifests-guard`、`check-spec-purity/-codeblocks/-drift/-numbering/-changelog/-refs`；`idlc` 库 `--root isa` rc=0、operation **5/5**、类型检查 **5/5**；`cover.py` rc=0（覆盖 **5/5**、零缺零多）。

**注入（3 路，均未列于 run.sh；临时树 `inj/`，`cp` 还原）**：① `.idl` 加 opcodes 外 id ⇒ `cover rc=1`+`render rc=1`；② `fence` 位域 `immu18[11:6]/[5:0]`→`[11:5]/[4:0]`（打 T7 六位）⇒ `render rc=1`；③ `escape` 的 `CfxEsc`→`Illegal`（打路由）⇒ `render rc=1`；三路还原后 `render/cover` 均 rc=0。

**约束核验**：① 改动集恰 4 文件（`idl/SimRISC-11.idl`、`spec/SimRISC-11`、`spec/.manifests.toml` 一行 sha256、本任务书），`git status -uall` 干净；② 散文零改动（删块+配套空行后与 master 逐字节相同）；③ 语义 5 条与 `DADAO-12 §5.2/§5.3`、`SimRISC-11 §3–§5` 逐句相符（escape 步骤 0 四检查、步骤 2 归 `cfx_escape_enter`；cfx2* reserved⇒ILLI 后 `cfx_read/write`，权限不进 operation；fence 两条 ILLI + `cfx_fence(cfxHA, immu18[11:6], immu18[5:0])` 六位）；④ `raise(CfxEsc, mode(), ip())` 与 master `idl/README.md §4.3`「`CFXESC` 进当前 cfx」一致；⑤ `idl/.manifests.toml` diff **0 行**；⑥ 无「银行」。

**返工要求（1 处）**：运行期证据目录内 `run.sh` 的第 78 行给 `prose_unchanged.py` 传 merge-base 基线（把第 80 行 `git show "$BASE:$SPEC" > "$TMP/spec_head.md"` 上移，并改为 `… "$ROOT" "$SPEC" "$TMP/spec_head.md"`），或改其默认基线为 `merge-base`。预期：**提交后**重跑 `run.sh` ⇒ `FAIL=0`、`RUN_RC=0`。

**非阻塞 finding**：a) 完成区写 `PASS=32`，末次 `run_final3.log` 实为 **35**（数字不对齐）；b) 任务书 R4 仍写「请确认」，但 master `71c359ee` 已把路由说明补进 `README §4.3`（提交信息称「011 的 R4 裁定」）⇒ R4 实已裁定、任务书未同步；c) 「删块后逐字节相同」须连块后配套空行（4 行排版间隔）一并删，仅删块差 3 处空行——非散文内容。

### 第 1 轮 engineer 自审

逐行审了 `idl/SimRISC-11.idl` 的新增段、spec 内 fence 标记块（render 生成）、`spec/.manifests.toml` 的 1 行、证据脚本 6 个文件。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `escape`/`cfx2rd`/`cfx2rc` 需要 §4 未声明的库函数（`inner_cfx_code`/`cfx_escape_enter`/`cfx_reg_*`），`render.py` 门控 E 也会判红 | ⏸延后（待裁定 R1/R2；硬约束 3 禁扩库） | 这 3 条**不写** operation；任务书给「问题+依据+建议签名」 | 注入③：临时树加 `cfx_reg_read(...)` ⇒ `render.py --check` rc=1（`语义库缺项`） |
| F2 `fence` 的屏障（访存序）在 IDL v0 无状态可写，只写 ILLI 判定可能被读成「静默 no-op」 | ✅已修 | operation 末段显式写明 pred/succ 位域、资源域、「顺序/可见性不建模」；另立 R3 请裁定是否加 `cfx_fence`；不调用不存在的函数 | typecheck 2/2 PASS；`prose_unchanged` PASS；逐句对照 ① |
| F3 插入标记块会改散文（初版删块后与 HEAD 差 1 空行，第 144 行） | ✅已修 | 调整块前后空隙；新增 `prose_unchanged.py`（删块+块后配套空行后与 HEAD 逐字节比） | 修前 FAIL（第 144 行）→ 修后 PASS；散文反例 a/b 各 1 路 |
| F4 类型检查驱动：库 `add_global_symbols` 与 `IsaAst#type_check` 同用 ⇒ `DuplicateSymError`；只 `type_check` 又注册不到函数（`No symbol raise`） | ✅已修 | 库只走 `add_global_symbols`；operation 走 `compile_inst_scope` + `type_check` | 2/2 PASS；注入⑥（多传一参）rc=1 |
| F5 本机 `idlc -v` 抛 `NoMethodError: undefined method 'version'`（该检出 `idlc.rb` 未 require `idlc/version.rb`） | ❌不修（上游检出问题，不属本任务） | 证据脚本统一用 `ruby -r idlc/version` 绕行 | `idlc -v` rc=0 打印 `IDL Compiler 0.1.8` |
| F6 `fence` 位域/资源域与合约是否一致（`contract-isa §14.1`、`DADAO-12 §2.1`） | ✅已核对（无需改） | — | 三处表述一致（hb SBZ、cfx0=all cfx、pred/succ 位义、保留 ⇒ ILLI） |
| F7 覆盖率断言会不会恒真 | ✅已修 | `cover.py` 除集合比对，还断言「缺=0 / 多=0 / 清单过期=0 / 标记双向一致 / 待裁定已落任务书」 | 注入④：临时树删整段 fence operation ⇒ `cover.py` rc=1（缺 1 + 有标记无源） |
| F8 `spec/.manifests.toml` 的 sha256 是否必须随改 | ✅已改并披露（超出任务书字面清单，属 `check-manifests-guard` 硬要求） | 仅本册一行 sha256 | `make check-manifests-guard` rc=0；`manifest_delta.py` PASS + 反例 FAIL |

判决：已交付部分无未修 finding；F1 是**待用户裁定**的阻塞项（按硬约束登记 R1/R2，不写静默桩）。

### 第 2 轮 engineer 自审（语义库 v1 合入后）

`git merge master` 拿 `idl/README.md §4` 新函数后，逐行审了 5 条 operation、3 对新标记块、`spec/.manifests.toml` 一行、证据脚本 3 处期望值。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| G1 master 同时改了本任务书与 `spec/.manifests.toml`，与本地未提交改动冲突（`merge --ff-only` 被拒） | ✅已修 | `cp` 备份 4 文件 + md5；用 `git show master:` 取两文件 → `merge --ff-only`（`40a85ae0→629f8d7e`）→ `git merge-file` 三方合回（0 冲突） | `git status` 仅本任务 4 文件；批次节与我的节并存；备份 md5 记录在运行期日志 |
| G2 T1 把 `ip()` 改成 `Bits<64>`，样板/fence 仍是 `{16'd0, ip()}`（80 位拼接） | ✅已修 | 4 处改 `ip()`（值等价，高 16 位恒 0）；逐句对照注明 T1 | typecheck 5/5 PASS；另测 80 位拼接仍能过 idlc（idlc 不严判宽度）⇒ 属语义/风格迁移，非「原来写错」 |
| G3 `CFXESC` 目标 = 当前 cfx，而库 `raise` 只进「当前运行模式 monitor」 | ⏸延后（非阻塞，R4 说明请确认） | operation 用 `raise(CfxEsc, mode(), ip())` + 注释；任务书 R4 给建议 `cfx_raise(cfxha, code)` | 逐句对照 ② 列明目标差异 |
| G4 `cfx2rd/rc` 的 `cfxreg` 掩码拒绝（⇒ `CFXPERM`）库中无函数 | ✅已改（按 T6 口径） | operation 不判，注释声明由 SEE 寄存器/mask 表给出（与 T6「只表达访问」一致） | 逐句对照 ③④ |
| G5 证据脚本期望值随 5/5 更新（`cover.py` 待裁定清单清空、`prose_unchanged.py` 4 对标记、`run.sh` typecheck 变量表） | ✅已修 | 三处脚本 | `cover.py` 5/5 PASS；prose +8 标记 PASS；typecheck 5/5 PASS；注入②④ 仍可 FAIL |
| G6 spec 增 3 块后 `spec/.manifests.toml` 的 sha256 需重算 | ✅已修 | 仅本册一行（`d8a68f46…`） | `make check-manifests-guard` rc=0；`manifest_delta.py` PASS + 反例 FAIL |
| G7 `idl/.manifests.toml` 是否登记本册 `.idl` | ✅已核对（**无需改动**） | 该文件已有 `[files."SimRISC-11.idl"]` + `owner = "idl"`（本册文件自 `m15-spec-001` 起即在册）；本文件工作树与 `master` 无差异 | `idl_manifest_entry.py` PASS + 反例（临时清单删条目）FAIL；`check-manifests-guard --self-test` 15/15 |

判决：无未修 finding（G3 为**非阻塞**建模说明，已按「不写静默桩」登记 R4）；5 条交付齐。

### 第 3 轮 engineer 自审（Needs Revision 返工：散文基线）

逐条对照 reviewer 意见，只改证据脚本与任务书，**不动** `.idl`/spec 块。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| H1 散文基线取 `HEAD`：WIP 已把 spec 提交进 HEAD ⇒ 基线本身含 4 对新标记 ⇒ 「新增标记」恒 0 ⇒ **恒红**（`ISS-475` 同源） | ✅已修 | ① `prose_unchanged.py` 默认基线改为 `git merge-base HEAD master`（取不到退化 HEAD，并打印所用基线）；② `run.sh` 显式传 merge-base 基线给第一处检查（不再裸调） | 反例三路：①临时把默认基线改回 `rev-parse HEAD` ⇒ `rc=1`（基线=10/现=10、新增 0）⇒ `cp` 还原 + md5 `4f045e01…` 一致 ⇒ `rc=0`；②「基线误取含块版本」反例（`run.sh` 反例 c）rc=1；③`run.sh` 在**已提交状态**（HEAD `05af728a`）下 `RUN_RC=0`、`PASS=37` |
| H2 完成区 `PASS=32` 与实测不符 | ✅已修 | 改为实测 **37**（并列出 11 路注入分类） | `run.sh` 末行 `汇总：PASS=37 FAIL=0` |
| H3 R4 仍写「请确认」 | ✅已修 | 改为「已裁定并落实（master `71c359ee`）」：`idl/README.md §4.3` 的 `raise` 已写明「一般异常进当前 monitor、`CFXESC` 进当前 cfx」 | `raise(CfxEsc, mode(), ip())` 与该说明逐句相符（逐句对照 ②） |

判决：Needs Revision 的唯一阻断已消除；新增可达 FAIL 路径「基线误取含块版本 ⇒ FAIL」，并在**已提交状态**下整体回绿。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` ⇒ `PASS=37 FAIL=0`、`RUN_RC=0`（**在已提交状态（HEAD `05af728a`）下运行**；5 条 operation + 11 路注入/反例：散文 3、生成块/源 2、未声明函数 1、漏写 1、idlc 语法 1、类型 1、清单 2；注入前后真实文件 md5 不变）
**修改文件**：`idl/SimRISC-11.idl`（5 条 operation：样板 `trap` 随 T1 改 `ip()`，新增 `escape`/`cfx2rd`/`cfx2rc`/`fence`）、`spec/SimRISC-11-核芯功能扩展指令.md`（仅 4 对新标记块，散文逐字节未改）、`spec/.manifests.toml`（仅本册 sha256 一行）、本任务书
**验收结果**：
1. 覆盖率 **5/5**（`trap`/`escape`/`cfx2rd`/`cfx2rc`/`fence`），零缺零多、标记双向一致、待裁定清单为空 ⇒ `cover.py` rc=0
2. `python3 idl/render.py --check` rc=0（源 operation 9 条 / 标记块 9 个逐字节一致）；`make check-idl-sync` rc=0；`render.py --self-test` rc=0
3. `idlc`：库 `compile --root isa` rc=0；operation `compile --root instruction_operation` **5/5** rc=0；类型检查（`add_global_symbols` + 逐条 `type_check`，按条注入解码变量）**5/5** rc=0
4. L1 全绿（rc=0）：`check-manifests-guard`、`check-spec-purity`/`-codeblocks`/`-drift`/`-numbering`/`-changelog`/`-refs`、`check-asm-prose`/`-list`/`-list-drift`、`check-legality-drift`/`-invariants`、`check-contracts-dir`
   - 清单登记：`SimRISC-11.idl` 本就在 `idl/.manifests.toml`（`[files."SimRISC-11.idl"]` + `owner = "idl"`，与 `master` 无差异）⇒ **无需新增行**；`idl_manifest_entry.py` PASS + 反例 FAIL、guard `--self-test` 15/15
   - BLOCKED（环境/他人）：`check-isa-coverage` 需 `llvm-mc`（未进入检查逻辑）；`check-temp-dirs` 红项全属他人陈旧目录
5. 语义抽查：5 条全量逐句对照见上（①–⑤），与 `DADAO-12 §5.2/§5.3`（含 `m14-spec-009` 与 T5/T6/T7 裁定）一致；散文未发现与 `DADAO-12` 冲突
6. 待裁定：**R1–R4 全部已裁定并落实**（R1–R3 引 `m15-idl-013` / T5–T7；R4 引 master `71c359ee` 在 `idl/README.md §4.3` 补的 `raise` 路由说明）
7. 证据脚本（`ISS-475` 同源问题已消除）：散文基线取 **merge-base**（非 `HEAD`）；`run.sh` 在**已提交状态**下 `RUN_RC=0`，反例「基线误取含块版本（= 旧取 HEAD 效果）」可达 FAIL（rc=1）
**新发现/坑**：① **证据脚本的历史基线不能取 `HEAD`**——WIP 一旦把断言对象提交进 `HEAD`，基线即含新内容、判据恒红（`ISS-475` 同源）；一律取 `git merge-base HEAD master`，并留「基线误取含块版本 ⇒ FAIL」反例；② `ip()` 位宽 48→64 后 `{16'd0, ip()}` 仍能过 idlc（不严判宽度），只能人工按 T1 统一；③ master 与本任务同改任务书/清单时，禁 `stash`/`checkout` 下的合回路径 = `git show master:` 覆盖 → `merge --ff-only` → `git merge-file` 三方合；④ 本机 UDB 检出的 `bin/idlc` 缺 `require "idlc/version"`；⑤ 库只用 `add_global_symbols` 注册函数（再 `type_check` 会 `DuplicateSymError`）
**遗留问题**：无（R1–R4 均已裁定并落实；`check-isa-coverage`/`check-temp-dirs` 的环境/他人项见上，不属本任务）
