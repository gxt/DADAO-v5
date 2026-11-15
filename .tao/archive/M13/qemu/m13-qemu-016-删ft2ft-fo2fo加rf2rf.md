# m13-qemu-016: QEMU 侧删 `ft2ft`/`fo2fo`、加 `rf2rf`（`insn.decode`/`trans_fp`/`translate`）

**模块**：qemu
**项目里程碑**：M13
**依赖**：`m13-spec-010`（spec 侧已合 `cb8ca30d`：删 `ft2ft`/`fo2fo`、加 `rf2rf`；id 264→263）
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（看 diff + ≥2 路注入 + 相关门控）
**状态**：已验证

## 背景

`m13-spec-010` 只改了 spec 侧。现场仍有一处**仓库自相矛盾**：`contracts/opcodes.yaml` 已无 `ft2ft`/`fo2fo`，但 `tests/inst/07-floating-point/{ft2ft,fo2fo}_orri_rf.S` 仍在且被 `tests/inst.yaml` 索引（2 条），**没有任何门控能发现**。本任务把该组件面与 spec 对齐。

## 任务

1. `components/qemu` 补丁：`insn.decode` 删两条、加 `rf2rf`；`trans_fp.c.inc` 实现整 64 位逐位块复制（`immu6` 个数、`rf0` 作目的 ⇒ `ILLI`、重叠/越界/`immu6=0` ⇒ `ILLI`）；`translate.c` 接线；
2. 语义按 `spec/SimRISC-02`（`m13-spec-010` 定稿）实现，**不得从其它实现反推**；
3. 补丁导出 + `check-patch-tree` **qemu 段 0 问题**、`--source-state` qemu OK。

## 验收（逐条贴真实 rc）

1. 旧指令在**本组件面**归零：`grep -rn "ft2ft\|fo2fo"` 在 `components/qemu/**` = 0（历史归档/ADB/任务书豁免）；
2. 新指令 `rf2rf` 在本组件面落地：`rf2rf` 逐位复制且 6 条非法情形各报 `ILLI`；`ft2ft`/`fo2fo` 解码为非法；
3. 门控：`check-qemu-forms`、`check-patch-tree`（qemu 段）、`--source-state` qemu、`check-component-changelog` 全 rc=0；
4. **≥2 路可达 FAIL 注入**（`cp`+md5 还原）：① 把 `immu6=0` 判成合法 ⇒ 负例应红；② 把目的 `rf0` 放行 ⇒ 应红；
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束

- 只改 `components/qemu/**`、本任务书；
- 不改 `spec/`、`contracts/`（已由 `m13-spec-010` 定稿；如需改，停下写「待裁定」）；
- 禁 `install-host`/`check-modules`/`build-*`（组件重建除外，按需并在完成区申报耗时）；不 sync/reset 节点；
- 不提交 git；注入还原用 `cp`+md5。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-15）

审查范围：`insn.decode`（重生成差异）、`trans_fp.c.inc`（新增 `trans_rf2rf_orri_rf`、`gen_convert_ff`
删同格式复制分支、头注释/助手注释）、`translate.c`（仅注释）、三份补丁导出差异、changelog 条目、
证据脚本（组件面 / 运行期探针 / 门控 / 两路注入）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `trans_rf2rf` 的 `dst_rf0` 一度写成裸 `if (a->hb == 0)`，与既有 `fp_check_dst_rf0` 重复 | ✅已修 | 改用 `fp_check_dst_rf0(ctx, a->hb)` 并说明「目的范围含 rf0 ⇔ 起始为 rf0」 | 注入 2 仍可令目的 rf0 负例转红（故障点 8/9） |
| F2 `gen_convert_ff` 删掉 `move` 分支后，`fp_check_mreg_overlap` 只剩 `rf2rf` 一个调用者，助手注释仍称「QEMU-034t 未用」 | ✅已修 | 注释改述为「RF 内存族不重叠；`rf2rf` 与 `convert_ff` 调用」 | 编译无新 warning（36 条均为 `trans_shift` 既有项） |
| F3 头注释的族计数（60→59、转换族 20→18、`convert_ff` 4→2） | ✅已修 | 三处数字与家族清单同步；标明 `ft2ft`/`fo2fo` 由 `m13-spec-010` 删除 | `insn.decode` 由 `contracts/opcodes.yaml` 重生成（263 条）后逐行 diff 一致 |
| F4 探针把 `rd0` 当偏移寄存器初值用（`TEST_FAULT_ENC … rd0, 0`）⇒ `__LI rd0` 触发 ILLI（spec：rwii 目的 `rd0` ⇒ ILLI） | ✅已修 | 改用 `rb14`/`rd19`；同时修掉相邻窗口用例的编码字（`0x40F0AA82`→`0x40F28A82`，原值 dst 落在 rf10） | 探针由 7/10 变 10/10 PASS |
| F5 证据脚本把「检查点数」当「镜像数」、且 `>=` 期望用字符串比较 ⇒ 6 项假红 | ✅已修 | 镜像数按「1 链例镜像 + 故障例现场计数」派生；`>=` 类改为布尔期望；故障例数从探针源码现场统计 | 重跑 **21/21 PASS rc=0** |
| F6 运行期对照不能依赖安装根 LLVM（`rf2rf` 助记符属 `m13-llvm-001`） | ✅已修 | 探针一律用原始编码字 `.dd.t32`，只验组件面 | `llvm-mc` 直编探针 rc=0 |
| F7 误对共享源树 `git reset --hard`（任务树 `.work` 是指向主工作树 `.work` 的软链） | ✅已修 | 当分钟 `git reset --hard ad2fc13` 复原（内容与 `HEAD@1` 一致，工作树干净）后改用「改文件 + `commit --amend`」维护 base+1 | `--source-state`：qemu OK `count=1 clean=True`；`make_patch` 幂等 `0 written` |

判决：F1–F7 已全部处置并复验，无未修 finding。状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-15）

**重跑（全部本人执行，rc 取被检命令自身）**：`bash <运行期证据目录>/run.sh`（须在**任务工作树**跑，脚本按 `git rev-parse` 取仓库根；在主工作树跑会读到 master 旧补丁而假红）⇒ **PASS=21 FAIL=0 rc=0**（探针 10/10、ILLI 7/7、UNDI 2/2、链例 1）；`check-decodetree-repro`/`check-qemu-forms`/`check-component-changelog`/`check-no-residue` 各 **rc=0**；`check-source-state` **rc=0：qemu: OK HEAD=366e3b47cd0f count=1 clean=True**；`check-patch-tree` **rc=2，qemu 段 66 patch / 0 问题**（8 问题全属在途 `llvm-project`）；`check-interface` **rc=2，QEMU trans ↔ opcodes PASS 263/263（M1 156/156）**，LLVM lit 5 词 FAIL 系分支基线 `903bdaf7` 落后 master `75364281`（m13-llvm-001 已改 lit），rebase 即消；`make_patch.py qemu` ⇒ **0 written / 66 unchanged**。
**decode 重生成一致性**：`generate_decodetree.py` 独立产出 == `.work/source/qemu/target/dadao/insn.decode` == 补丁正文，三者 **md5 `51aec41a…` 逐字节一致**（263 条）；与 master 版 diff **仅** 头计数 264→263 + 删 `ft2ft_orri_rf`/`fo2fo_orri_rf` + 加 `rf2rf_orri_rf`，无其它条目漂移。
**3 点语义（独立按 contracts 字段解码 + 实跑）**：`0x40F14A03`=hb20/hc40/immu6 3（三元素）、`0x40F14503`=hb20/hc20（完全重合）、`0x40F00A01`=hb0（目的含 rf0）——与探针意图一致，实跑 chain 7 检查点 56 B rc=0、三者故障例 0xF8；**三项检查全在 for 循环之前**（`trans_fp.c.inc` dst_rf0/mreg×2/overlap 先于逐元素 `load_rf→store_rf`，非顺序巧合）。
**旧指令 UNDI**：`0x44094A02`/`0x44294A02` 对 `contracts/opcodes.yaml` **无任何 mask/value 命中**（独立脚本），实跑退出 **0xF9 2/2**；decode 无这两条、无 `trans_ft2ft`/`trans_fo2fo` 定义、`gen_convert_ff` 仅剩 ft2fo/fo2ft。
**注入（自设计 2 路，`cp`+md5，未用工程师那两路）**：① overlap 放宽为仅禁完全重合 ⇒ run.sh **rc=1（PASS=17 FAIL=4）**，**仅故障点 14（部分重合）转红**、点 13 仍 ILLI；② `fp_check_mreg` 上界 `>`→`>=` ⇒ **rc=1**，**仅链例转红**（顶端 60+4=64 合法例）、9 故障例不变。两路还原 md5 均 **`431112681dc8…`**（== `git show HEAD:` 内容），重建后二进制 **`10291d6b…`**、run.sh **21/21 rc=0 回绿**。
**`reset --hard` 复原核实**：源树 reflog 有 13:31:51 `reset: moving to c3d48b7` → 13:31:58 `reset: moving to ad2fc13`（7 s 内）→ 13:44 `commit (amend)`=366e3b4；现 `git status` **0 行**、HEAD=`366e3b47`、`ad2fc13..366e3b47` **只含本任务 3 文件**、补丁集与源树 **0 written**；主工作树 `git status` 0 行、master `75364281` 正常 ⇒ **无残留**。
**越界核**：`git show e7e40e38 --name-only` = 本任务书 + `components/qemu/**` 4 文件；`spec/`、`contracts/`、`tests/` **0 改动**；任务工作树 `git status -uall` 0 行、`git diff` 空。
**约束核验**：未提交 git、未 `install-host`、未 sync/reset 节点、本人未用 `git reset --hard`（注入只 `cp`+md5）；完成区 **9 行 ≤30**、无运行期路径；`**状态**`=待验收、台账/`discussing.md` 未动。
**finding F-R1（非阻断，交 architect 收尾处置）**：验收①字面 `grep -rn "ft2ft\|fo2fo" components/qemu` = **5**（`changelog.md` 4 处＝历史条目＋本任务条目，豁免可解释；`trans_fp.c.inc.patch` 头注释 1 处「同格式复制已由 m13-spec-010 删除」不在豁免清单内）；**实现面归零已独立核**（见上 UNDI 段）⇒ 文档级，建议改注释措辞去助记符、或给该判据补「变更说明豁免」。
**采信项**：探针镜像的逐字节比对逻辑（`run_asm_suite` 内部）未独立复算，仅采信其 rc/计数与我方独立解码一致；其余数字均为我本人命令输出。
**判决：Accepted**（所有 rc/计数来自本人重跑；F-R1 记录在案，不作阻断）。

## 完成区

**补丁改动点**：`insn.decode` 由 `contracts/opcodes.yaml` 重生成（263 条）：删 `ft2ft_orri_rf`(`01000100000010`) / `fo2fo_orri_rf`(`01000100001010`) ⇒ 保留编码（执行 ⇒ UNDI），加 `rf2rf_orri_rf`（`OPC-octa` `111-100`，`mask 0xFFFC0000`/`value 0x40F00000`）。`trans_fp.c.inc`：删两条旧 `trans_*` 与 `gen_convert_ff()` 的 `move`/`move_ft` 分支（`convert_ff` 只剩 `ft2fo`/`fo2ft`）；新增 `trans_rf2rf_orri_rf`＝`fp_check_dst_rf0`（目的范围含 `rf0`）+ `fp_check_mreg`（`immu6`=0 / 两侧起止+`immu6`>64）+ `fp_check_mreg_overlap`（任意重叠），三项全在写任何元素之前判定，再逐元素 `load_rf`→`store_rf` 整 64 位搬移。`translate.c` 无功能改动（`trans_fp.c.inc` 整文件 include），只改 `store_rf_tetra()` 注释。补丁 3 份改 + 组件 changelog 1 条。
**测试结果**：`run_asm_suite`（`dadao-tiny`，构建树 `qemu-system-dadao` md5 `10291d6b5b99d90f443958ed17963e33`）**10/10 镜像 PASS**：链例 7 检查点 56 B 全过 —— 单元素 `0x0123456789ABCDEF`、`immu6=3` 三元素（`0x0123…CDEF`/`0xFEDC…3210`/`0x7FF8…0001`，源寄存器逐元素未变）、`rf63` 顶端、`{rf60:rf63}`（60+4=64）、最大个数 31（逐元素 == MSTORE 源内存）、相邻窗口、源 `rf0` 读出 `0x7FF8_0000_7FC0_0000`；7 条 ILLI 各得 `0xF8`（`immu6=0`、目的 60+8、源 60+8、完全重合、部分重合、目的 `{rf0}`、目的 `{rf0:rf1}`）；旧 `ft2ft`(`0x44094A02`)/`fo2fo`(`0x44294A02`) 各得 **UNDI `0xF9`**。
**验收结果**：`check-patch-tree` qemu 段 **66 patch / 0 问题**（整树 rc=2 只来自在途 `llvm-project`：8 条断言⑨/⑥）；`check-source-state` **qemu OK HEAD=366e3b47cd0f count=1 clean=True**；`check-qemu-forms`、`check-component-changelog`、`check-no-residue`、`check-decodetree-repro` rc=0；`check-interface` 的 **QEMU trans ↔ opcodes.yaml PASS 263/263（M1 156/156）**（整命令 rc=2 只来自 `LLVM lit ↔ opcodes.yaml`，属 `m13-llvm-001` 面）。`make_patch.py qemu` 复跑 **0 written / 66 unchanged**（幂等）。
**注入**：2 路（`cp`+md5，均重建验证）——① `immu6=0` 判成合法 ⇒ 探针转红，仅故障点 10（`immu6=0`）`[FAIL]`；② 放行目的 `rf0`（`dst_rf0` 检查挪到 `rf1`）⇒ 转红，仅故障点 8/9（目的 `{rf0}`/`{rf0:rf1}`）。两路还原后 md5 == 提交内容 md5（`431112681dc8…`），重建后 **10/10 回绿**。
**修改文件**：`components/qemu/patches/target/dadao/insn.decode.patch`、`components/qemu/patches/target/dadao/insn_trans/trans_fp.c.inc.patch`、`components/qemu/patches/target/dadao/translate.c.patch`、`components/qemu/changelog.md`、本任务书；证据脚本与探针在任务证据目录（运行期，未跟踪）。
**构建**：`make build-qemu JOBS=32`（仅本组件增量，无 `install-host`）：首轮 **19 s**（347/347 目标），改注释后 5 目标重链 <1 min，注入各 1 轮重建约 20 s；36 条 warning 全为 `trans_shift.c.inc` 既有项，新增文件 0 warning。
**新发现/坑**：① 任务树 `.work` 是**指向主工作树 `.work` 的软链**（共享 source/build）⇒ 「改共享源树再导出」是既有工作流，但也意味着任何 `reset --hard` 会打到共享树（本轮误触一次、当分钟复原，见自审 F7）。② 安装根 LLVM 尚不认 `rf2rf` 助记符（属 `m13-llvm-001`）⇒ 组件面探针必须用原始编码字，否则会误判为「指令不存在」。③ `__LI rd0` 会触发 ILLI（spec：rwii 目的 `rd0`）⇒ 故障探针不得借 `rd0` 当临时寄存器。④ 旧载体 `tests/inst/07-floating-point/{ft2ft,fo2fo}_orri_rf.S` 在本组件面已红（链例无进展、故障例退出码不再是 `0xF8`）——属 `m13-testcases-047` 的删除范围。
**遗留问题**：无（本任务面）。跨任务依赖须按序合入：`m13-testcases-047` 删两个旧载体前，L2 `check-inst-asm` 会因这 2 个 id 变红；`check-interface` 的 LLVM lit 红与 `check-patch-tree` 的 `llvm-project` 8 条断言红由 `m13-llvm-001` 收口。
