# m17-testcases-004: `st.o` 语义行订正 + `rf0` 作源用例 + `.S` 注释术语统一（去 “beat”）

**模块**：testcases
**项目里程碑**：M17
**依赖**：`m17-testcases-001`（签名区数据派生；本任务改 `.S` 后须重生成）
**可并行分片**：否（`tests/inst/**` 为共享文件，串行）
**预估**：3–4 h
**档位**：中改
**状态**：已验证

## 背景（用户 2026-11-23 观察，三条已现场核实，另有一条追问追加）

1. **`st.o` 语义行写错**：`tests/inst/01-load-store/st.o_rrii_{ra,rb,rd,rf}.S` 第 4 行均写
   `mem[EA] ← 源寄存器低 64 位；…；只改这几条字节通道，beat 其余字节保持`。
   `st.o` 是**整 64 位写满 8 字节**，没有「其余字节保持」这回事；且 “beat” 是存储流水/颗粒的**实现术语**，不应出现在 ISA 语义行。
2. **`st.o_rrii_rf.S` 缺 `rf0` 作源用例**：全文件 `rf0` 只出现在第 6 行注释里（「rf0 读出完整 64 位（合法）」），无实际用例；同族 `ldm.o_rrri_rf.S` 已有 `rf0` 作目的/源的实测例。
3. **“beat” 术语全族不统一**：`tests/inst/**/*.S` 共 **41 个文件**出现 “beat”，其中注释行型为
   `数据块：TEST_DATA（24 个 8 字节 beat，…）`（19 处）、`取自 TEST_DATA 现有 beat`（38 处）、以及窄写语义行里的 `beat 其余字节保持`（`st.b`/`st.w`/`st.t` 共 4 处）。用户裁定：注释统一改用「数据单元」，**并标明宽度**（8 字节）；宏参数名 `\beat` 属代码标识符，**不改**。
4. **窄写语义行同病（用户 2026-11-23 追问追加）**：窄写 4 个文件的第 4 行也只写「只改这几条字节通道，beat 其余字节保持」，既含实现术语又没写清改几个字节。宽度已由 spec 确认：`st.b`=8 位、`st.w`=16 位、`st.t`=32 位；改为「只改 k 个字节，其余 8−k 个字节保持」（`st.o` 仍为「整 8 字节全部写入」）。

## 目标

1. **`st.o` 4 个文件第 4 行**改为：`语义：mem[EA] ← 源寄存器整 64 位；EA = rb[47:0] + imms12（大端）；整 8 字节全部写入`。
2. **`st.o_rrii_rf.S` 补 `rf0` 作源用例**（新增 1 个链例，插在故障段之前）：
   - 先用 `set.w rf0, wp0, 0x0000` 清异常状态、`set.w rf0, wp2, 0x0000` 置舍入模式 RNE（`spec/SimRISC-03 附录 B` 注：wp0 命中 `[4:0]`、wp2 命中 `[33:32]`、wp1/wp3 写无效）；
   - `st.o rf0, [<base>, <off>]`，用 `__CHECK_MEM` 逐字节比对；
   - **期望值必须由 `spec/SimRISC-00 §2.3.1` 位域独立派生**（禁从实测反推）：`[63:51]=0b0111111111111`、`[50:34]` SBZ、`[33:32]`=RM(00)、`[31:22]=0b0111111111`、`[21:5]` SBZ、`[4:0]`=flags(0) ⇒ **`0x7FF8_00FF_C000_0000`**（engineer 复核：按位域应为 `0x7FF8_0000_7FC0_0000`，见「待裁定」1）；
   - 原故障例点号顺延（现为 21/22，新增链例占 21 ⇒ 故障例改 22/23），并同步第 8 行「用例：…」计数（`legality 3`、`链例 21 + 故障例 2`）。
3. **注释术语全族统一**（只动 `@@` 注释文本，不动指令）：
   - `24 个 8 字节 beat` → `24 个 8 字节数据单元`；
   - `取自 TEST_DATA 现有 beat` → `取自 TEST_DATA 现有 8 字节数据单元`；
   - 窄写语义行改为「只改 k 个字节，其余 8−k 个字节保持」：`st.b` → `只改 1 个字节，其余 7 个字节保持`；`st.w` → `只改 2 个字节，其余 6 个字节保持`；`st.t`（rd/rf 两文件）→ `只改 4 个字节，其余 4 个字节保持`；`低 N 位` 本身正确，不改；
   - 其余零散注释里的 “beat” 按语义改成「数据单元（8 字节）」/「整 8 字节」；
   - **宏参数 `\beat` 与代码标识符不改**；改完 `grep -rn "beat" tests/inst --include=*.S` 只应剩宏定义/调用里的参数名。

## 验收（逐条贴真实 rc）

1. **注释改动不改指令流**：被注释改动触及的每个 `.S`，其 `.text` md5 与改前相同（`st.o_rrii_rf.S` 除外，它新增用例）；窄写 4 文件只改第 4 行注释，md5 必须不变。
2. **`st.o`/窄写语义行**：4 个 `st.o` 第 4 行逐字为「源寄存器整 64 位…整 8 字节全部写入」；窄写 4 行逐字为「只改 k 个字节，其余 8−k 个字节保持」（k=1/2/4/4）；全仓 `grep "源寄存器低 64 位"` **0 命中 rc=1**（窄写文件写的是「低 8/16/32 位」，本就不该被这条 grep 命中）。
3. **`rf0` 用例逐字节**：写入结果 = `0x7FF8_00FF_C000_0000`（engineer 复核为 `0x7FF8_0000_7FC0_0000`，见「待裁定」1）；至少 2 条可达 FAIL（① 把期望常量改错 ⇒ 红；② 删 `set.w rf0, wp2, …` 让 RM 非 0 ⇒ 红；engineer 实测该删除不可达，改用 `wp2=0x0003`，见「待裁定」2）。
4. **三平台**：同一 ELF 的签名流 qemu / gem5 / chipyard 逐字节相等；chipyard 若被其它任务占用 ⇒ 记 BLOCKED + 替代证据（不得并发构建）。
5. **数据同步**：`make inst-signature-data` 重生成 `tests/data/inst-signature/expected.tsv` 与 `inputs.sha256`；`make check-case-ledger --write` 重生成 `tests/case-ledger.tsv`；两者 `git diff` 只含本任务预期变化。
6. **门控**：`make check-inst-asm`（镜像数应与改前相同 = 272，新增用例不新增镜像）、`make check-inst-sig`（engineer 注：该目标已退役，见「待裁定」3）、`make check-case-ledger`、`make check-tests-index`、`make check-inst-macro-scope`、`make check-knowledge-refs` 真实 rc。
7. 完成区必须写**需重测周期的镜像清单**（本任务改指令流的镜像：`st.o_rrii_rf`）。

## 约束

独立 `git worktree`（分支 = `m17-testcases-004`）；**不提交 git**；只改 `tests/inst/**`、`tests/data/inst-signature/**`、`tests/case-ledger.tsv` 与本任务书；不改 `spec/`/契约/`contracts/opcodes.yaml`；术语「寄存器组」；完成区不写具体 `.work/**` 路径；`rf0` 期望值不得以实测反推。

## 待裁定（engineer 2026-11-23，4 条；**主会话 2026-11-23 已逐条裁定**）

> 裁定结论：① 采纳 spec 派生值 `0x7FF8_0000_7FC0_0000`（任务书原值是我算错：把 10 位 `0b0111111111` 当 `0x3FF` 并误置 RM=11；engineer 未按实测反推，正确）；② 采纳 `wp2=0x0003` 作第 2 条可达 FAIL；③ `check-inst-sig` 退役属实，验收改用 `check_inst_sig.py --data-only`；④ `拍` 统一已立 `m17-testcases-005`（依赖本任务合并）。

1. **任务书期望常量算术错误（实现已取 spec 值，待确认）**：任务书给 `0x7FF8_00FF_C000_0000`；按 `spec/SimRISC-00 §2.3.1` 逐位独立派生 = `0x7FF8_0000_7FC0_0000`。前者 `[50:34] SBZ`（17 位）= `0x3F`，非 0，与同节 SBZ 定义冲突。三平台（qemu/gem5/chipyard）实测均为 `0x7FF8_0000_7FC0_0000`，与 spec 派生一致。实现取 spec 派生值（未用实测反推）；若坚持任务书原值，须先改 spec 的 SBZ 定义。
2. **验收 3 的 FAIL 注入②不可达**：删除 `set.w rf0, wp2, 0x0000` 后 QEMU 仍 PASS（rf0 复位 RM=00，删前删后同值）。证据脚本改用「`wp2` 改 `0x0003`（RM=11）」作第 2 条可达 FAIL，实测 rc=21。
3. **验收 6 的 `make check-inst-sig` 目标不存在**：`m17-testcases-003` 已退役该目标（`make -n check-inst-sig` rc=2，`No rule to make target`）。改用其现行等价数据门控 `python3 tools/testcases/inst/check_inst_sig.py --data-only`（rc=0）。
4. **“拍”术语是否统一（用户追加，待拍板）**：`stm.*` 语义行的「元素不跨 8 B 拍」等 `拍` 用法本轮未改。现场统计 `grep -rl "拍" tests/inst --include=*.S` = **54 个文件**、`grep -rc` 合计 **208 处**（用户估计 50 文件/百余处）；是否统一为「8 字节数据单元 / 8 字节边界」，等用户裁定（后续任务 `m17-testcases-005` 承接）。

## 完成区

**测试结果**：`make check-inst-asm` 272/272 镜像 PASS（rc=0，镜像数与改前相同）；三平台同 ELF（`st.o_rrii_rf`）签名流 qemu=gem5=chipyard=168 B、rc 全 0；`check_inst_sig.py --data-only` rc=0；`check-case-ledger`/`check-tests-index`/`check-inst-macro-scope`/`check-knowledge-refs` 全 rc=0；`inst-signature-data` rc=0（272 镜像 / 4540 槽）。
**修改文件**：41 个 `tests/inst/**/*.S`（`git diff --name-only -- tests/inst`）；`tests/case-ledger.tsv`；`tests/data/inst-signature/expected.tsv`；`tests/data/inst-signature/inputs.sha256`；本任务书。
**验收结果**：4 个 `st.o` 第 4 行逐字为裁定措辞；窄写 4 行逐字为「只改 1/2/4 个字节，其余 7/6/4 个字节保持」；`grep -rn "源寄存器低 64 位" tests/inst --include=*.S` 无命中；`grep "beat" tests/inst --include=*.S` 只剩宏参数（`.macro` 形参 + `\beat`）；40 个仅注释改动的 `.S` `.text` md5 全同（逐文件 40/40，基线存于运行期证据目录；含窄写 4 文件改前/改后对照），仅 `st.o_rrii_rf` 变化；`rf0` 例逐字节 = `0x7FF8_0000_7FC0_0000`。注入：期望常量改错 ⇒ rc=21；`wp2=0x0003` ⇒ rc=21；均 `cp`+md5 还原并回绿。证据脚本：运行期证据目录内 `run.sh`（rc=0，全 PASS；含注入→FAIL→还原→回绿）。
**需重测周期镜像**：`st.o_rrii_rf`（唯一改指令流的镜像）。

`grep -rn "beat" tests/inst --include=*.S`（只剩宏参数）：

```
tests/inst/01-load-store/st.o_rrii_rb.S:35:.macro TEST_ST_RB pt, mnem, src, base, baseval, off, srcval, beat
tests/inst/01-load-store/st.o_rrii_rb.S:39:	__CHECK_MEM \pt, \baseval, \off, \beat
tests/inst/01-load-store/st.o_rrii_ra.S:17:.macro TEST_ST_RA pt, mnem, src, base, baseval, off, srcval, beat
tests/inst/01-load-store/st.o_rrii_ra.S:22:	__CHECK_MEM \pt, \baseval, \off, \beat
```

**新发现/坑**：三平台开跑前应留**紧邻的** `pgrep -af simulator-chipyard` 快照（本轮未留，事后时间线：他人 chipyard 20:39:04 结束、本任务三平台 20:39:44 完成，无重叠；reviewer 判轻 finding，不改结论）；任务书常量把 `[31:22]` 的 `0x1FF` 误叠加到 `[39:32]`；`check-inst-sig` 已退役；`.inc`/`MIGRATION.md` 仍有「beat」，不属本任务 41 个 `.S` 范围；`拍` 现场统计 54 文件/208 处。
**遗留问题**：待裁定 4 条（常量、删 `wp2` 注入不可达、`check-inst-sig` 退役、`拍` 是否统一）；`.inc` 宏注释与 `tests/inst/MIGRATION.md` 的「beat」术语未统一（超出本任务范围）；`m17-testcases-005` 承接全族去 beat/拍。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-23）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 任务书常量与 spec `[50:34] SBZ` 冲突 | ✅已修（取 spec 派生值，待用户确认） | `st.o_rrii_rf.S` 期望改 `0x7FF8_0000_7FC0_0000` | 三平台 168 B 相等；`run.sh` PASS |
| 任务书「删 wp2」注入不可达 | ✅已修（换 `wp2=0x0003`） | 证据脚本 10b | 注入 rc=21 → 还原回绿 |
| 窄写 4 行未写字节数（用户追加） | ✅已修 | 4 行改「只改 k 个字节，其余 8−k 保持」 | `.text` md5 4/4 不变 |
| `make check-inst-sig` 目标缺失 | ⏸延后（记待裁定） | 用 `--data-only` 等价门控 | rc=0 |
| `.inc`/`MIGRATION.md` 仍有「beat」 | ⏸延后（超出 41 `.S` 范围，005 承接） | 无 | `grep` 范围限定 |

判决：finding 均已处置；状态 → 待验收。

### 第 1 轮 reviewer 验收（2026-11-23）

**重跑记录（rc 均取被检命令自身；命令在 worktree 根、相对路径执行）**

1. `rf0` 期望常量：只读 `spec/SimRISC-00 §2.3.1` 自行逐位重算 `(0b0111111111111<<51)|(0b0111111111<<22)` = `0x7ff800007fc00000`，与代码 `0x7FF800007FC00000` **一致**；任务书原值 `0x7FF800FF_C000_0000` 使 `[39:32]=0xFF`，违反 `[50:34] SBZ`，确系任务书算错。派生说明引 spec 位域（`.S` 注释第 80–82 行 + 待裁定 1），**未从三平台实测反推**。
2. 语义行：4 个 `st.o` 第 4 行 md5 全同 `44e1415c0cd7613e3d08821386dda38b`，逐字「源寄存器整 64 位…整 8 字节全部写入」；窄写 4 行逐字「只改 1/2/4 个字节，其余 7/6/4 个字节保持」；`grep -rn "源寄存器低 64 位" tests/inst --include=*.S` → **0 命中 rc=1**（窄写本写「低 8/16/32 位」，任务书「只剩窄写文件」表述与实际不符，0 命中更严格，不判缺陷）；`grep -rn "beat"` 仅 4 行、全为宏形参与 `\beat`；`8 字节 beat`/`beat 其余` 残留 0。
3. 新增用例：`set.w rf0, wp0, 0x0000` + `set.w rf0, wp2, 0x0000` + `st.o rf0,[rb3,0x038]` + `__CHECK_MEM 21, TEST_DATA, 0x038, 0x7FF800007FC00000`；点号 1..21 唯一且递增，`TEST_FAULT 22/23` 仍在最后；第 8 行 `legality 3`、`链例 21 + 故障例 2` 已同步。
4. 语义零漂移（我独立重算，非采信日志）：`git show HEAD:<file>` 出基线到运行期临时目录，同 `.lds` + `llvm-mc`→`ld.lld`→`llvm-objcopy --only-section=.text` 比 md5 ⇒ **比对 40 / 不一致 0**（含 `st.b_rrii_rd`、`st.t_rrii_rf`、`stm.o_rrri_ra`、`rf2rf_orri_rf`、`pseudo_set.rb_imm`、`st.o_rrii_rb`；改单中无 `12-misc` 文件，无可比对象）；`st.o_rrii_rf` `.text` `1e981dca…`→`8607b926…`（与 engineer 基线记录同值）。
5. 可达 FAIL（我独立注入，非采信完成区）：期望常量改 `0x7FF800FFC0000000` ⇒ `inj_rc=1`、`rc {'qemu': 21}`；`wp2` 改 `0x0003` ⇒ `inj_rc=1`、`rc {'qemu': 21}`；`cp` 还原后 md5 `fa9cf19aadf11b29a67843056260a1ac` 与注入前相等、回绿 `back_rc=0`。还原证据 = **md5 对账**（非 `git status`）。`__CHECK_MEM` 为 `br.eq` 相等跳过、不等 `__EXIT pt`，无恒真/两支同结果。
6. 门控真 rc（我重跑）：`check-inst-asm rc=0`（272/272 镜像、632 例）、`check-case-ledger rc=0`、`check-tests-index rc=0`、`check-inst-macro-scope rc=0`、`check_inst_sig.py --data-only rc=0`（272 镜像 / 4540 槽）、`check-knowledge-refs rc=0`（悬空 0）；无基线红。
7. 数据一致性：`expected.tsv` 4544→4545 行（+1 = 新用例 21）；`case-ledger.tsv` 5705→5706（+1 新用例行、2 故障例行点号 21/22→22/23、2 行仅注释文本 beat→数据单元）；`inputs.sha256` 82 行变化 = 41 个 `.S`×2，无其它文件；镜像数 272 与改前相同。
8. 三平台：运行期证据目录内 `run.sh` 我重跑 **rc=0（64 PASS / 0 FAIL）**，含 `platform parity (qemu,gem5,chipyard)` = `{'chipyard': 168, 'qemu': 168, 'gem5': 168} B`、rc 全 0（168 B = 21 检查点×8 B）；比对逻辑在 `tests/ee-tiny/run_inst_tiny.py`（逐槽 tuple 相等，不一致即 FAIL）。并发：run.sh 内 pgrep 判据本次未触发 BLOCKED；工程师 20:38:58 占用检查后，他人 chipyard 任务 20:39:04 落盘结束、其三平台日志 20:39:44 完成，未见重叠（缺开跑前紧邻 pgrep 快照，记轻）。
9. 范围：`git diff --name-only` 44 项全在 `tests/inst/**`、`tests/case-ledger.tsv`、`tests/data/inst-signature/**`；未跟踪仅本任务书；`spec/`、`contracts/`、`Makefile`、`tools/` 改动数 **0**。审查前后 `git status --porcelain -uall` 均 45 行逐行相同、4 个目标文件 md5 不变、无 stash、无残留注入。

**判决：Accepted**。轻 finding（不阻断，交 architect 收尾改）：① 任务书验收 2「`grep "源寄存器低 64 位"` 只剩窄写文件」表述与实际不符（实际 0 命中）；② 三平台开跑前缺紧邻 pgrep 快照。

