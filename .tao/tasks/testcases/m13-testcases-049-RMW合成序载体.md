# m13-testcases-049: 原子 RMW 合成序载体（`tests/inst/00-isa-design/`）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-spec-010`（`rf2rf` 已合）、`m13-testcases-037`（保留粒度向量已合）
**可并行分片**：否
**预估**：3–4 h
**档位**：中改（≥2 路注入 + 相关门控）
**状态**：已验证

## 用户裁定（2026-11-15）

> 「我建议放00，因为01-12的文件数量正好可以和指令数对上」

⇒ **`01`–`12` 各册保持"一个 opcode id 一个文件"的对应关系，不再往册内塞非 id 载体**；原子 RMW 合成序属"非 id 载体"，放 **`tests/inst/00-isa-design/`**（与 `undi_reserved.S`、`pseudo_set.*.S` 同册）。

## 背景：现有 lr/sc 载体**不覆盖** RMW 合成序

`12-misc` 的 24 个 `lr.*`/`sc.*` 载体只测**单指令语义**（保留置位/清除、成败、失败不写内存、保留粒度）；实测 **`br.` 回跳数 = 0、`lr` 与 `sc` 之间无算术** ⇒ 完全没覆盖 C11/`__atomic_*` 编译出来的"**lr → 计算 → sc → 失败重试**"环。

## 任务：新增 `tests/inst/00-isa-design/atomic_rmw.S`（单文件，约 12–16 点）

每点"一行、期望内联、点号连续"，期望**独立推导自 `spec/SimRISC-12 §1` + `contract-isa §14.2`**（不从 qemu/llvm/gem5 反推）。覆盖：

1. **`fetch_add`（含强制失败重试）**：内存初值 `0x100`；
   `lr t0,[A]` → **插一条 `lr t1,[B]` 清除保留**（等价"被抢"）→ `sc [A], t0+8` ⇒ **失败返回 1 且 A 仍 `0x100`**（失败不写）→ 重新 `lr t0,[A]` → `sc [A], t0+8` ⇒ 成功返回 0、`A == 0x108`；并断言**第一步读到的 old == `0x100`**（返回旧值语义）；
2. **`fetch_sub`**：同构，断言 `A == old - d` 且返回 old；
3. **`fetch_and` / `fetch_or` / `fetch_xor`**：各 1 点（不需重试，断言返回值 = old、内存 = old op val）；
4. **`exchange`**：`lr` 得 old → `sc` 写新值 ⇒ 返回 old、内存 = 新值；
5. **`compare_exchange` 两路**：① 比较相等 ⇒ `sc` 成功、内存 = 期望新值；② 比较不等 ⇒ **不执行 `sc`**、内存不变、返回 old（对应"比较后决定是否尝试"这层）；
6. **重试必须重读（关键负例）**：构造"若实现复用旧值直接重试就会错"的序列 —— 在失败后**改变内存内容**（用普通 `st`，注意同 hart 同址同宽 `st` **不清**保留，所以顺序要放在清除之后、重读之前）⇒ 正确实现应读到新值并算出正确结果；把该点写成显式断言（`A` 最终 = 新值 + d）。

> 说明：**多 hart 争用**与**内存序强度**在单 hart 机型不可观测 ⇒ 继续记 GAP（与 `ISS-440`/`ISS-443` 同线），不伪造。

## 任务要求

1. 新建 `tests/inst/00-isa-design/atomic_rmw.S`（**非 id 载体**）；
2. **双注册表**逐文件登记：`tools/testcases/validate_vectors.py::NON_ID_CARRIERS` 与 `tools/testcases/check_tests_index.py::NON_ID_CARRIERS`；
3. `tests/inst.yaml` 增 1 条（`inst-00-isa-design-009`，`platforms: [system]`、`level: full`）；
4. `tests/case-ledger.tsv` 重生成；`tests/inst/README.md`（00 册说明）与 `MIGRATION.md`（§ 新增一节）同步；
5. 每点检查点 ≤127、点号连续；期望内联（优先用 `macros/inst_test.inc` 现有宏，缺宏在 `.S` 内 `.macro`）。

## 验收（真实 rc）

1. `run_asm_suite --platforms qemu --id atomic_rmw`（或按文件跑）⇒ 全过，贴检查点数与字节流；
2. **三平台可选**：chipyard/gem5 若对 RMW 序列无差异，跑一次并贴结果；若存在平台差异 ⇒ 记 GAP 并给实测值，**不把某平台行为写成期望**；
3. 门控：`validate-vectors`（非 id 载体 9 条）、`check-tests-index`（现场条数）、`check-case-ledger`、`check-inst-asm`（id 264 不变、镜像 +N）、`check-no-residue`、`check-knowledge-refs` rc=0；
4. **≥2 路可达 FAIL 注入**（`cp`+md5 还原）：① 把"失败不写内存"那条的期望改成"写了" ⇒ 应红；② 把"重试必须重读"那条改成复用旧值 ⇒ 应红；
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只改 `tests/inst/00-isa-design/**`、`tests/inst.yaml`、`tests/case-ledger.tsv`、`tools/testcases/{validate_vectors.py,check_tests_index.py}`（仅 `NON_ID_CARRIERS`）、`tests/inst/{README.md,MIGRATION.md}`、本任务书；
- **不改** `spec/`、`contracts/`、`components/**`、`tests/inst/12-misc/**`（01–12 册保持 id 一一对应）；
- 禁 `install-host`/`check-modules`/`build-*`；不 sync/reset 节点；不提交 git；注入还原 `cp`+md5。

## 待裁定

无（本任务无新语义决策；「放 00 册」已由用户 2026-11-15 裁定，GAP 四项沿用既有口径，不新增裁定）。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：`tests/inst/00-isa-design/atomic_rmw.S` 全文逐行 + 两处注册表 + 索引 + ledger + 证据脚本。
**判据**：期望逐条对 `spec/SimRISC-12 §1`（lr 读+置标记 / sc 命中才写 / 成败都清标记 / 清标记三事件 /
保留粒度 = 精确地址+宽度）+ `contract-isa §14.2`（`.o`=8 B、自然对齐、`rdHB=rd0` ⇒ ILLI）复核；未引用
任何实现行为。

**审查项（无需改动，已核）**：
1. 数据区偏移 0x500–0x548、0x5F8 全落在 `__TEST_SECTIONS` 的零区（0x0C0–0x800），不撞宏层生成区
   （0x800 起 MDATA_*/0x1100 MSTORE/0x1300 RDATA/0x1500 WDATA）；每例独立 8 B 拍、8 B 对齐。
2. 保留寄存器未占用（rb3/rb29/rb30/rb27/rb16/rb21/rb24、rd4/rd16–rd26）；用例只用 rd2/3/5–10、rb4。
3. 点 10「不执行 sc」的可观测性：除「内存不变」外另置 `rd7 = 0xFF` 哨兵并断言未被写（sc 命中会写 0）
   ⇒ 「跳过 sc」与「执行了但写同值」可区分。初稿即含，非事后补。
4. 点 11–12 的序列依据：`st`（同 hart 同址同宽）**不清**标记，且此处标记早在点 11 的失败 sc 时已清
   ⇒ `st` 置于「清除之后、重读之前」在两种解释下都得出同一期望（不依赖争议事件）。
5. 点 2/11 的「被抢」只用「本 hart 另一条 `lr`」这一条清标记事件（单 hart 唯一可构造者）。

**finding 与处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 点 4 用 `sub.so`（有符号）：fetch_sub 语义是模 2^64 减，而 `sub.so` 的高半为符号扩展（本例低 64 位相同，但形态不忠实） | ✅已修 | `sub.so {rd0,rd5}, rd2, rd6` → `sub.uo`（借位丢弃） | 全部证据重跑 31/31 PASS（点 4 仍 0x1D0） |
| F2 证据脚本初稿用 `git diff --name-only <载体>` 判「注入确实落地」：载体是**未跟踪新文件**，`git diff` 恒空 ⇒ 该断言恒 FAIL/或反过来放过空注入（假绿风险） | ✅已修 | 改为「锚点恰 1 行命中 + 行内含待替换文本」的 python 断言 + 注入后 **md5 ≠ 注入前** | E1/F1 现场打印「注入前 md5 == 备份、注入后 md5 ≠ 备份」，E4/F4 还原后 md5 与注入前逐字符相同 |
| F3 注入用 `sed -i 's/^…$/'`：全行含中文注释与多空格，锚点漂移即静默不替换（空注入假绿） | ✅已修 | 改 python 锚点替换，命中数 ≠ 1 直接非零退出 | `inject()` 内 `assert len(hit)==1` + `assert old in line` |
| F4 worktree 基线为 c7fe9a5e（派单提交 `7a5521df` 的**父**）⇒ 任务书不在树内；且 master 已前进（spec-011 / MIGRATION 口径） | ✅已处置 | `git merge --ff-only master` 到 `f86c71b3`；`MIGRATION.md` 冲突以「备份本人的追加段 → 截断回 HEAD 版（749 行，`git status` 无差异）→ ff-merge → 重新追加本节」解决，未用 `git checkout/restore/stash` | 合并后全部门控 + 证据 31/31 重跑通过；`contract-isa §14.2` 未被本次合入改动（只 §5 引用标题变化） |

**判决**：4 条 finding 全部 ✅已修/已处置；无 ⏸延后、无 ❌不修 ⇒ 状态可置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-15，中改档：看 diff + 2 路注入 + 门控 + 越界核对）

**重跑（全部本人执行，真实输出）**：① `bash <运行期证据目录>/run.sh` ⇒ **30/30 PASS、exit=0**（含 L2 `check-inst-asm`「265 个 id / 897 个镜像 / 897/897 通过」、`validate-vectors`「265 .S carriers, 2 non-id」、`check-tests-index`「inst=274、载体↔索引 265↔265」、`check-case-ledger` 5325、`check-no-residue`、`check-knowledge-refs` 全 rc=0）；② `run.sh --tri` ⇒ **31/31 PASS、exit=0**（与自报 31/31 一致）；③ 自跑 `run_asm_suite --vectors tests/inst/00-isa-design --id atomic_rmw --platforms qemu,gem5,chipyard` ⇒ rc 0/0/0、三平台各 **104 B**、三份 out md5 全同 `81237169ab03e7c27cb685fca9163aac`；字节流与本人手算 oracle 逐条相同（`100 1 0 0 0 0 0 0 0 200 1 0 0`）。
**注入（本人自设计 2 路，`cp`+md5 还原）**：① 点 5 `fetch_and` 期望改 `0xFFF0FFF0FFF0FFF0`（fetch_or 结果）⇒ suite rc=1 / **guest rc=5**；② 点 8 返回值期望改新值 `0xDEADBEEFCAFEF00D` ⇒ **guest rc=8**；两路还原 md5 均回 `f9bd0baac6f29de85fa991291f9b3d49`、回绿 rc=0。engineer 的 E/F 两路我在其脚本内重跑复现（点 2 改「写了」⇒ guest rc=2；点 12 改复用陈旧值 ⇒ guest rc=12），锚点断言与 md5 对账均真实生效，无空注入。
**语义推导（本人独立按 `spec/SimRISC-12 §1` + `contract-isa §14.2` 推，非采信）**：点 2 = lr 置标记 → **本 hart 另一条 lr**（spec 明列的清标记事件）→ sc 未命中 ⇒ 不写、rdHB=1（断言 mem=0x100 + rd7=1，非巧合）；点 10 = `cmp.uo` 0x200>0x100 ⇒ rd8=1≠0 ⇒ `br.ne` 跳过 sc，**rd7 预置 0xFF 有判别力**（sc 一旦执行必写 0（成功）或 1（失败），`rd7==0xFF ⟺ sc 未执行`，可区分「跳过」与「执行但写同值」）；点 12 = 失败 sc 已清标记后 `st` 0x40（同 hart 同址本就不清、且标记已空 ⇒ 两种解释下期望同）→ 重 `lr` 得 0x40 → 算 0x48；复用陈旧值会写 0x108 被 `__VERIFY_MEM 12` 抓 ⇒ **有判别力**（注入实测 rc=12）。
**单 hart 合法性 / GAP**：「被抢」只用 spec 明列的「本 hart 另一条 lr」清标记，单 hart 可构造、合法；GAP 四项（多 hart / 内存序强度 / spurious / 异常中断清标记）在 `.S` 头与 `MIGRATION §6` 如实登记，`ISS-440`/`ISS-443` 确存在，未伪造。
**01–12 未动 / 越界**：`git show b6078b70 --name-only` 恰 8 个文件（任务书、`atomic_rmw.S`、`inst.yaml`、`case-ledger.tsv`、`README/MIGRATION`、两注册表），**不含** `tests/inst/{01..12}-*/`、无 `12-misc`、无 `spec/`、`contracts/`、`components/`；双 `NON_ID_CARRIERS` 均逐文件键、`inst-00-isa-design-009` 正确（-002…-008 留给 048）；完成区 17 行、grep 无运行期路径。
**约束核验**：工作树快照前后均干净（`git status -uall` 空）、载体 md5 注入前后一致；安装根 `llvm-mc` mtime 14:00 早于任务窗口 ⇒ 未跑 `install-host`；未见 `check-modules`/`build-*`/节点 sync 痕迹；未提交 git（HEAD=b6078b70 未变）；注入只用 `cp`+md5，未用 checkout/restore/stash。
**finding（均文档级，不阻断）**：F-a 自审「保留寄存器未占用（rb3…）、用例只用 rb4」与实不符——`.S` 有 25 处 `LOAD_ADDR rb3`，而 rb3 正是宏层指定的「数据基址」（01 册载体同用法、宏内自重载 ⇒ 代码无缺陷，仅自审表述错）；F-b 点 10 注释「不等 ⇒ rd8=-1」应为 **1**（0x200>0x100，spec §1.3：大于⇒1；`br.ne` 判 ≠0，行为不受影响）；F-c 任务书验收写「非 id 载体 9 条」、本分支现场 2 条（048 的 7 个 `pseudo_set.*` 未合入，engineer 已如实披露，合入后自然为 9）；F-d 证据脚本 G1 名含「字节数一致」但只断言 rc（字节数仅打印）⇒ 建议补断言，逐字节一致已由我独立跑证实。
**判决：Accepted** —— 验收命令块在本人重跑下全部通过、≥2 路注入均达 FAIL、约束无违反；4 条 finding 交 architect 收尾修订（文档级，不返工）。

## 完成区

**测试结果**：证据脚本 31/31 通过（0 失败）。qemu 链例 13 点 / 104 B / rc=0；三平台同 ELF
（qemu/gem5/chipyard）各 104 B 且逐字节一致、rc 均 0；L2 `check-inst-asm` 897/897 镜像全绿。

**修改文件**：`tests/inst/00-isa-design/atomic_rmw.S`（新增，13 点）、`tests/inst.yaml`（+`inst-00-isa-design-009`、头部非 id 载体注释）、`tests/case-ledger.tsv`（`--write` 重生成，+13 行）、`tests/inst/README.md`（00 册两处：文件表 + 跑法）、`tests/inst/MIGRATION.md`（§6 新增本节）、`tools/testcases/validate_vectors.py` 与 `tools/testcases/check_tests_index.py`（各 +1 条 `NON_ID_CARRIERS`）、本任务书。

**验收结果**（真实 rc）：
- 覆盖表：1–3 `fetch_add`（首读 old=0x100 / 被抢后 sc 失败=1 且 A 不变 / 重试成功=0 且 A=0x108）、4 `fetch_sub`（0x1D0，返回 old=0x200）、5 `fetch_and`（0x00F000F000F000F0）、6 `fetch_or`（0xF123456789ABCDEF）、7 `fetch_xor`（0xF0F0F0F0F0F0F0F0）、8 `exchange`（A=0xDEADBEEFCAFEF00D，返回 old=0x1111…）、9–10 `compare_exchange`（相等 ⇒ 执行 sc / 不等 ⇒ 不执行 sc，哨兵未被写）、11–12 重试必须重读（陈旧候选 0x108 ⇒ 重读 0x40 后写 0x48）、13 `fetch_add` 回绕（全 1+1 ⇒ 0）。
- 字节流：`0x100 0x1 0 ×6 0x200 0x1 0 0`（13 条 × 8 B，大端；与手算 oracle 逐条相同）。
- 门控 rc=0：`validate-vectors`（265 载体 / **2** 非 id 载体；本分支未含 `pseudo_set.*`，故非 9）、`check-tests-index`（inst 274 条 / 载体↔索引 265↔265 / 非 id 2）、`check-case-ledger`（现场 5325 条，asm 4804）、`check-inst-asm`（opcode id 数不变 / 镜像 896→897）、`check-no-residue`、`check-knowledge-refs`；另 `check_tests_index.py --self-test` 全 PASS。
- 注入（`cp`+md5 还原）：①「失败不写」期望改成「写了」⇒ guest rc=2（点 2）；② 点 12 改复用陈旧值 ⇒ guest rc=12；两路均还原后 md5 相同且 qemu rc=0。

**新发现/坑**：① 证据脚本用 `git diff` 判「注入落地」对**未跟踪新文件**恒空 ⇒ 假绿，须用锚点断言 + md5 变化。② 任务 worktree 基线是派单提交的**父**提交 ⇒ 任务书不在树内；需 ff-merge master 才能填完成区（`MIGRATION.md` 冲突处置见自审 F4）。③ 单 hart 构造「保留被抢」只有合法途径一条（本 hart 另一条 `lr`），另三条清标记事件不可构造。④ 三平台对本合成序**无分歧**（对照 `m13-testcases-037`：分歧在「异常/中断清标记」路径，不在 RMW 环本身）⇒ 合成序可进三平台逐字节口径，无需写平台相关期望。

**遗留问题**：① 多 hart 争用 / 内存序强度 / `sc` 偶发失败 / 异常中断清标记 ⇒ 记 GAP，不伪造（同 `ISS-440`/`ISS-443` 线）。② 与 `m13-testcases-048`（7 个 `pseudo_set.*`）并行：两任务都要往两个 `NON_ID_CARRIERS` 与 00 册 README 加行，合并冲突由主会话处理（本分支只加自己那一行）。③ 本分支已 ff 到 master `f86c71b3`；未提交 git，提交由 architect 执行。

