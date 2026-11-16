# m15-testcases-004: 整例宏化（扫描器新前缀 + 台账重生成 + 试点转换）

**模块**：testcases
**项目里程碑**：M15
**依赖**：`m15-testcases-003`（试点：准备段宏化，已验证 −24.8% 方法论）**必须先合入**
**可并行分片**：否（改扫描器/台账 + 转换试点文件，单写者）
**预估**：4–6 h（含台账重生成与全量回归）
**档位**：大改（**改门控判据** + 30 文件结构重构 + 台账基线重建；复核 ≥4 路注入 + 行为级等价）
**状态**：已验证

## 背景（用户 2026-11-16 裁定）

用户在「只宏化准备段 / 整例宏化」二选一中裁定 **整例宏化**（原话：「整例宏化」）。

动机：`m15-testcases-003` 只把**准备段**宏化（`__LI`/`set.rb`/`st.o`），点号行 `__CHECK_MEM 5, …` 必须留在正文，因为——

- `run_asm_suite.CHAIN_CASE_RE` 是**行首白名单**（`^\t(TEST_LD\w*|…|__CHECK_(?:RD|MEM)\w*)\b`）；
- `CHAIN_PT_RE` 从该行取**点号字面量**，并校验「点号 == 该用例在文件里的序号」（`pts_ok`）；
- `check_case_ledger` 以这些行的**文本**作删除哨兵。

整例宏化后一行变成 `__PT_SET_RB 5, rb9, 0xBABE` ⇒ 不在白名单 ⇒ 检查点数归零 ⇒ `check-inst-asm` rc=2、台账丢行。故须同步改三处。

## 目标

1. **扫描器扩展**（`tools/testcases/inst/run_asm_suite.py`）：
   - `CHAIN_CASE_RE` 增加 `__PT_\w*` 前缀；
   - `CHAIN_PT_RE` 对 `__PT_*` 取**第一个实参**为点号（`__PT_XXX <pt>, …`）；
   - `pts_ok` 语义**不变**：链例点号 1..N 连续、故障例续 N+1..N+M、无跳号重号；
2. **台账重生成**（`tools/testcases/check_case_ledger.py`）：用例行文本改为「宏调用行 + 其展开语义」（宏调用行文本即可）；**删除哨兵必须仍能 FAIL** —— 删掉任意一条 `__PT_*` 行 ⇒ 台账红；
3. **防"用例藏进宏里"的静态判据**（新增，写入 `check-inst-macro-scope` 或同文件）：
   - 每个 `__PT_*` 宏体**恰含 1 处** `__CHECK_RD`/`__CHECK_MEM`（或 `TEST_*` 断言），且该处的点号实参**必须引用 `\pt`**（不是常量）；
   - `.S` 正文里**不得**再出现裸的 `__CHECK_RD`/`__CHECK_MEM`（即"用例只能以宏调用行形式出现在正文"），否则计数与台账口径会分叉；
4. **试点转换**：把 `m15-testcases-003` 的三处试点文件（`00-isa-design/pseudo_set.rb_reg.S`、`12-misc/sc.*`、`02-reg-copy/rf2rf_orri_rf.S`）改为**整例宏化**，出收敛数据；
5. 全量批次的**分批建议**（按实测密度），供后续任务使用。

## 验收（真实 rc + 输出；判据 = 用户 2026-11-16 裁定 A）

1. **等价（核心）**：试点文件在**全部形态**下 —— A1 节字节 / A2 重定位 / A3 标号值 / A5–A6 `strip-all` 后 `.o`、`.elf` 字节相等；**行为**：`semi.out` 字节 + 退出码逐例相等；`check-inst-asm` **904/904**、镜像数与改前一致；
2. **检查点不变**：每文件「链例数 + 故障例数 + 点号序列」与基线**逐个相同**（贴逐文件表，不只首末）；
3. **防藏判据可达 FAIL**（≥3 路）：① 把某 `__PT_*` 宏体的点号改成常量 ⇒ 静态判据红；② 把一个宏体塞两条 `__CHECK_*` ⇒ 判据红；③ 在正文留一条裸 `__CHECK_MEM` ⇒ 判据红；
4. **删除哨兵可达 FAIL**：删掉一条 `__PT_*` 调用行 ⇒ `check-case-ledger` 红（贴真实输出）；
5. **台账基线重建留痕**：写清「旧基线 = N 行 / 新基线 = M 行、变更原因 = 整例宏化」；重生成后的台账必须**逐条可回溯**（宏调用行 + 点号）；
6. **门控全绿**：`check-inst-asm`、`check-case-ledger`、`check-inst-macro-scope`、`check-tests-index`、`check-dirs`、`check-no-residue`、L1 `make check`；
7. **≥4 路注入**（`cp`+md5 还原）：① 宏多展开一次 ⇒ A1/行为红；② 点号实参错位（跳过 3）⇒ `pts_ok` 红；③ 宏体缺 `__CHECK_*` ⇒ 静态判据红；④ 扫描器白名单去掉 `__PT_` ⇒ `check-inst-asm` rc=2（**证明扫描器改动是必要而非摆设**）；
8. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- **只改必要处**：扫描器 2 个正则 + 台账 1 处 + 新增静态判据；**不得放宽**任何既有判据（`pts_ok` 语义、点号连续性、镜像数一律不变）；
- **点号与用例顺序不得变**；
- 不改 `spec/`、`contracts/`、`components/`；不动共享宏层的语义（只允许为整例宏新增 `__PT_*` 定义）；
- 不提交 git；注入还原 `cp`+md5；证据基线**钉死 commit**（`ISS-458`）；脚本按 `git rev-parse --show-toplevel` 推根（`ISS-456`）。

## 审阅记录

### 第 1 轮 engineer 自审（实现后逐行审查）

**审查范围**：`run_asm_suite.py`（2 处正则 + `scan_source` 1 行）、`check_inst_macro_scope.py`（S6/S7/S8 + 计数递归 + selfcheck）、`check_case_ledger.py`（口径注释）、`12-misc.inc`（+10 宏）、`pseudo_set.rb_reg.S`（3 宏 / 20 例）、`rf2rf_orri_rf.S`（+10 宏 / 11 例）、6 支证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 新扫描器把正文里的 `__PT_*` **辅助**宏（0 断言）也计为用例行（pt=-1）⇒ 文件若只半宏化就会 rc=2 | ✅ 已修（判据兜底 + 设计约束） | 新增 S7「一行 `__PT_*` 调用传递展开恰 1 个检查点」；试点三处一次到位（14 文件正文无 0 断言 `__PT_*` 调用） | `check-inst-macro-scope` PASS（用例行 228 / `__PT_*` 30）；注入「宏体缺断言」命中 S7 |
| F2 基线树不能用新扫描器扫（`__PT_` 前导行双计）、也不能用旧扫描器扫现状树（不认调用行） | ✅ 已修 | 证据脚本按「基线代码 + 基线树 / 现状代码 + 现状树」两侧各自扫描（独立模块 alias） | 14 文件逐文件 SAME；全仓 4917 点 / 904 镜像两侧相等 |
| F3 `__PT_RF_COPY_N31` 若照抄 31 行逐元素断言，宏体比原用例还长 | ✅ 已修 | 改 `.irp k,2,…,31` + `rf\k` + `((\k-1)*8)`，宏体 8 行 | rf2rf 7 形态 A1/A5/A6 全等（含 31 元链例） |
| F4 `rf2rf_orri_rf.S` 净增 31 行（11 例 11 形，无形状复用） | ⏸ 保留并披露 | 未改（整例宏化按用户裁定执行；收益 = 一例一行 + 31 行断言收进宏） | 该文件 A1–A6 + 行为 + 检查点全等；计入完成区「不划算档」 |
| F5 开发中曾用 `git checkout -- tests/inst/12-misc/` 回滚，把已写的 `.inc` 改动一并清掉（并因此出现假「invalid operand」） | ✅ 已修（纪律违规，已纠正） | 重建 `.inc` 改动；此后全部注入/还原一律 `cp` 备份 + md5 对账 | 证据脚本每条注入后 `md5_chk` 全等；`git status` 仅列本任务文件 |
| F6 断言写法 `chk … "$(cmd)" $?` 恒真（命令替换先重置 `$?`；`m15-testcases-003` 的 run.sh 有此缺陷） | ✅ 已修 | 一律 `rc=$?` 先落变量，再传 `$rc` 给断言 | 证据脚本 41 条断言逐条打印真实 rc；注入路径会红 |
| F7 `__PT_RF_COPY_N31 9` 只有点号一个实参，既有 `CHAIN_PT_RE` 要求行尾逗号 | ✅ 已修 | **不放宽**既有正则，另加 `CHAIN_PT_PT_RE`（`\s+(\d+)\s*(?:,|$)`)；`pts_ok` 语义一字未改 | 14 文件 `pts_ok=True`；点号错位注入 rc=2 |
| F8 删除哨兵是否仍可 FAIL（台账身份改文本后） | ✅ 已核 | 无需改码（`--write` 重生成） | 删一条 `__PT_SC_LD` 调用行 ⇒ `check-case-ledger` rc=1（缺 1 行），还原后 rc=0 |

**判决**：F1/F2/F3/F5/F6/F7/F8 已修/已核；F4 为「按裁定保留 + 披露」，无未修阻塞项。**任务状态与判决对账：→ `待验收`**。

### 第 2 轮 engineer 自审（用户调整：回退 `rf2rf_orri_rf.S` 的整例宏化）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| G1 回退后的文件仍会挂掉扫描器：`__PT_ST_VERIFY`（0 断言的文件内准备宏，首实参就是点号）被新扫描器按用例行计数 ⇒ 链例 11→21、`pts_ok=False` | ✅ 已修（最小改名，0 行增减） | 该文件内 `__PT_ST_VERIFY` → `__RF_ST_VERIFY`（1 处定义 + 10 处调用）；理由 = `__PT_` 前缀已归「一行一条用例」的宏（与 S7 同义） | 纯回退实测 `checks=21 pts_ok=False`、`check-inst-asm` rc=2；改名后 201 行、`11+6 pts_ok=True`、rc=0 |
| G2 「逐字节恢复到基线」与 G1 冲突（改名使源 md5 变） | ⏸ 披露（口径：源 md5 ≠ 基线，**编译产物逐字节相同**） | 先 `cp` 落盘逐字节基线（md5 `a089fed4…` 与基线 blob 全等）证明回退本身干净，再做 11 处改名（`3ed00aa4…`） | 与基线 `diff` 22 行 = 11 删 11 加；该文件 7 形态 A1–A6 全 PASS，且**未 strip 的 `.o`/`.elf` 与基线逐字节相同（14/14 文件）** |
| G3 只被该文件用的 `__PT_*` 宏定义 | ✅ 已核（回退即消失，无 `.inc` 需要删） | `__PT_RF_*`×10 与 `__PT_ST_VERIFY` 原本写在该 `.S` 内 ⇒ 随回退消失；`02-reg-copy.inc` 未动；`12-misc.inc` 的 `__PT_SC_*` 仍被 `sc.*.S` 使用（共用，保留） | `02-reg-copy.inc` `git diff` 为空；`check-inst-macro-scope` 死宏 0 / `__PT_*` 30→19 / 用例行 228→217 |
| G4 台账该文件 11 条身份回退到「点号行」 | ✅ 已核（重生成） | `check_case_ledger.py --write` | 总行数 5438 不变；变更身份 228→**217**（现场派生）；`check-case-ledger` PASS；删一条 `__PT_SC_LD` 仍 rc=1 |
| G5 回退后整体复验 | ✅ 已核 | 未改证据脚本（断言数仍 41） | 41/41 断言 rc=0、`check-inst-asm` 904/904、行为 41/41 SAME、L1 53 绿 + 2 项外部红（同前） |

**判决**：G1/G3/G4/G5 已修/已核，G2 为口径披露（源 md5 与基线不同仅因 11 处改名，产物字节全等）。→ `待验收`。

### 第 1 轮 reviewer 验收（大改档：看 diff + 独立重跑 + 7 路自设计注入）

**判据未放宽（逐字核 diff `41e32760..HEAD`）**：`CHAIN_CASE_RE` 只在既有分支后增 `|__PT_\w*`；`CHAIN_PT_RE` 与 `FAULT_*_RE` 一字未改；新增 `CHAIN_PT_PT_RE` 仅匹配 `^\t__PT_`（旧句式优先、解析不到才落新式 ⇒ `pts=-1` fail-closed）；`pts_ok` 表达式两版逐字相同；`check_case_ledger.py` 仅 +4 行口径注释、判据码未动；`check_inst_macro_scope.py` S1–S5 未删改（selfcheck `move_book_to_shared` 改为从册 .inc 摘除该宏，断言仍须 rc=1 且命中 `[S1]`）。
**重跑（我自己的 rc/输出）**：`bash .work/evidence/m15-testcases-004/run.sh --with-gates --with-l1 --with-l2` ⇒ **exit=0、`证据: PASS（0 项失败）`** —— 基线 blob md5 14/14、形态 **41/41（A1–A6）**、`pts_report: 14 文件 0 处不一致`、`behdiff 41/41 镜像 SAME`、`L2 check-inst-asm rc=0（904/904；272 id、链 271/故障 633）`、`check-case-ledger`/`check-inst-macro-scope`(+selfcheck 8 路)/`check-tests-index(476)`/`check-dirs`/`check-no-residue` 全 rc=0。
**L1 外部红独立核**：本树 L1 失败仅 `check-patch-tree`、`check-milestones-fresh`，前者 32 problem **全在 linux/qemu**（非 linux/qemu 行 = 0），后者违约仅 `m14-qemu-006`；我在主工作树复跑 `make check-patch-tree` **rc=2**（同因）、`make check-milestones-fresh` **rc=0** ⇒ 2 项外部红属实、与本任务无关。
**台账（现场派生）**：数据行 **5438**（asm 4917 / lit 521；`wc -l`=5442 含 4 行头注释）、`__PT_` 身份 **217**、正文 `^\t__PT_` 调用行 217（同数）；基线台账同为 5438/4917 且 `__PT_` 身份 0；`--write` 幂等（md5 不变）。
**rf2rf 等价（我自己拉基线树 + 自己 llvm-mc/ld 汇编）**：blob md5 `a089fed4…`(基线)/`3ed00aa4…`(现状)；**7 形态 × {未strip .o, 未strip .elf, strip .o, strip .elf} = 7/7 全 SAME**；扫描 `11+6`；`__RF_ST_VERIFY` 全仓 11 处仅此一文件、`__PT_ST_VERIFY` 残留 0。
**我自设计 7 路注入（`cp`+md5 还原、逐路回绿）**：① `__RF_ST_VERIFY`→`__PT_ST_VERIFY`（**0 断言 `__PT_` 宏**）⇒ **S7 红 + 扫描 rc=2**（故回退改名不是绕洞）；② `.S` 内宏体点号写常量 ⇒ **S6 rc=1**；③ 已宏化正文补裸 `__CHECK_MEM` ⇒ **S8 rc=1**；④ `__PT_` 调用拆两行 ⇒ **扫描 rc=2**（`pts=-1`；S7 不红、由扫描器兜住）；⑤ 点号 13→130 ⇒ **rc=2**；⑥ 删一条 `__PT_` 调用行 ⇒ **`check-case-ledger` rc=1**；⑦ 白名单去掉 `__PT_` ⇒ scan-only **rc=2**、**`make check-inst-asm` rc=2**。
**全仓/越界**：基线(基线码+基线树) vs 现状逐行 `diff` = **0 行**，两侧均 `272 id / 904 镜像`、现场求和 **4284+633=4917 点**；改动 20 文件与完成区声明一致，`tests/arch|components|spec|contracts` 改动 **0**；收尾 `git status -uall` 干净、4 个工具/数据文件 md5 与注入前快照一致；行数核 sc.* **−789**、pseudo **112→104**、rf2rf **201→201**、`12-misc.inc` **117→235**、`tests/inst` 净 **−679**。
**采信边界**：A1–A6/QEMU 行为依赖 engineer 脚本，我已审其断言（节 md5/`-r` 文本/符号多重集/strip md5、`behdiff` 集合不等即 rc=2 fail-closed、计数现场派生、基线钉死 `41e32760`）并**整轮重跑**取真实 rc；台账/计数/行数/rf2rf 字节为我独立复算。
**findings（文档级，不阻断）**：F-a `S8`/扫描器同以 `^\t` 为界，列 0 裸断言不被 S8 抓（实测 llvm-mc 接受列 0 宏调用；全仓现存列 0 断言行 0，且该边界基线即有 ⇒ 未被本任务放宽）；F-b `pts_report` 比计数与 `pts_ok`、未逐元素比 `pts` 序列（`pts_ok` 强制 1..N 连续 ⇒ 计数同+双侧 `pts_ok=True` 即序列同）；F-c 完成区「5438 行」为数据行口径（`wc -l`=5442 含头注释），建议收尾补注。

**判决：Accepted** —— 验收命令块在我自己的重跑下全部通过、硬约束逐条守住、无放宽/凑绿/越界；上列 findings 由 architect 收尾处置。

## 完成区

**测试结果**：通过 41/41 断言（一键证据 `run.sh --with-gates --with-l1 --with-l2`，rc=0；另 1 项 BLOCKED，见遗留）；失败：无。
**修改文件**：`run_asm_suite.py`（白名单 + `__PT_*` 点号正则）、`check_case_ledger.py`（口径注释）、`check_inst_macro_scope.py`（S6/S7/S8 + selfcheck 8 路）、`tests/case-ledger.tsv`（重生成）、`12-misc.inc`（+10 宏）、`12-misc/sc.*.S`×12、`pseudo_set.rb_reg.S`、`rf2rf_orri_rf.S`（**已回退**：= 基线 + 1 处宏改名）、本任务书。披露：台账工具实际在 `tools/infra/`；`tests/case-ledger.tsv` 是目标 2 的生成物（硬约束清单未列，必需）。
**验收结果**：
- 等价：41 形态 A1–A6 全过（节字节/重定位/局部标号值/全局符号/strip 后 `.o`/`.elf`）；行为 41/41 镜像 QEMU `semi.out` 字节 + 退出码 SAME；`check-inst-asm` **904/904**（272 id；链 271 / 故障 633）、`check-case-ledger` / `check-inst-macro-scope`（含 selfcheck）/ `check-tests-index`（476）/ `check-dirs` / `check-no-residue` 全 PASS。
- 检查点：14 文件逐文件「链例数 + 故障例数 + 点号序列」与基线逐项 SAME（逐文件表见证据输出）；全仓 4917 点 / 904 镜像前后相等（现场派生，未写死）。
- 台账：旧基线 5438 行（asm 4917 / lit 521）→ 新基线 5438 行（同），其中 **217 条 asm 身份**由「点号行」换成「`__PT_*` 调用行」（现场派生；`rf2rf_orri_rf.S` 的 11 条随回退回到点号行）；身份即宏调用行全文（点号 + 操作数），逐条可回溯；删除哨兵粒度不变。
- 注入 8 路全命中（cp + md5 还原）：删一条 `__PT_*` ⇒ 台账红；S6 宏体点号写常量 / S7 宏体两条断言 / S8 正文裸 `__CHECK_MEM` 三路防藏各红；宏体缺断言 ⇒ S7；宏多展开 ⇒ 链例 strip 后字节变；点号错位（跳过 3）⇒ `pts_ok` rc=2；扫描器白名单去掉 `__PT_` ⇒ `check-inst-asm` rc=2。
- 收敛：`sc.*` 2053→1264（−789 / **−38%**）、`pseudo_set.rb_reg.S` 112→104（**−8**）、`rf2rf_orri_rf.S` **已回退（0 变更，201 行）**；`.S` 级合计 −797，扣 `12-misc.inc`（117→235，10 个整例宏定义，12 文件共用）后试点净 **−679（−27%）**。宏数：`12-misc.inc` 16（+10）/ pseudo 3 / rf2rf 0（回退后无新增）；`__PT_*` 共 19，用例行 217。
**新发现/坑**：
- `chk … "$(cmd)" $?` 恒真：命令替换先重置 `$?`（`m15-testcases-003` 的 run.sh 有该缺陷）⇒ 断言一律 `rc=$?` 先落变量。
- **判据经验：净收益 = 同形状复用次数 −(宏定义成本)**。`sc.*` 每形状 ×12 复用 ⇒ −38%；`rf2rf` 11 例 11 形 ⇒ 整例宏化 +31 行（**净亏损 ⇒ 回退**）。**后续批次遇到「无复用的逐元素断言/一次性形状」直接跳过**，只收敛复用 ≥2 的形状（仍先试点出数再铺开）。
- 新扫描器把正文里的 `__PT_*` **0 断言辅助宏**也计为用例行（首实参被当点号）⇒ 假点号/双计导致 `pts_ok` 红；故 `__PT_` 只能留给「一行一条用例」的宏，准备/断言辅助宏一律用非 `__PT_` 前缀（回退时实测：纯回退 rc=2，改名后恢复 11+6）。
- 基线侧扫描/行为必须用**基线扫描器**（新扫描器在未宏化文件上双计，旧扫描器不认 `__PT_*`）。
- 分批建议（目标 5，按 lines/case 实测降序、一册一批）：12-misc 9.04 → 06-control-flow 8.95 → 11-cfx 8.06 → 00-isa-design 7.57 → 02-reg-copy 6.62 → 05-arith-addr 6.25 → 04-arith-logic-octa 5.25 → 10-arith-logic-byte 5.20 → 03-wyde-imm 5.09 → 09-arith-logic-wyde 5.01 → 08-arith-logic-tetra 4.60 → 01-load-store 3.73 → 07-floating-point 3.12；先做复用率高的册（12-misc / 06 / 11-cfx），01 / 07 最后且预期收益低。
**遗留问题**：
- L1 `make check` 窗口内非全绿（2 项**外部红**，已用「主工作树复跑」判别，均与本任务改动无关）：`check-patch-tree`（30 problem 全落在 linux/qemu 组件 worktree 脏，主工作树同样红 ⇒ 并行任务在改组件）；`check-milestones-fresh`（违约仅 `m14-qemu-006`，主工作树 PASS ⇒ 本 worktree 快照早于并行派单）。其余 53 个 L1 目标全绿。

