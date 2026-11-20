# m17-testcases-001: `tests/inst` 签名区（槽级比对 + 诊断）

**模块**：testcases
**项目里程碑**：M17
**依赖**：`m16-testcases-002`（签名机制已抽到 `tests/shared/asm/signature.inc` + `tools/testcases/lib/signature.py`）
**可并行分片**：否
**预估**：4–6 h
**档位**：中改
**状态**：待验收

## 背景（用户 2026-11-20 定：放 M17，不放 M15）

M15 已收口（58/58），且签名区不是「ISA 语义结构化」；它的**消费者是 M17**——IDL 差分要能报「槽 N 期望 X 实际 Y」，而不是只知道第 N 条断言失败（现在的判据是 guest 内联期望 + `SYS_EXIT(N)`，见 `tests/arch/ptw/expected.yaml` 抬头的同款说明）。

`m16-testcases-002` 已把机制落好：`tests/inst/macros/inst_test.inc` 的 `__REC` 已委托 `SIGUPD`，收尾打印走 `SIG_DUMP_CHARS`；**因此 `.S` 的指令流目前逐字节未变**。

## 关键约束（不许破坏 M16 的周期基线）

`tests/inst` 的 272 个镜像就是 M16 周期标定的语料（`m16-chipyard-001` 的 15 行实测）。本任务**不得改动这 272 个 `.S`**（一改指令流，拍数全变、M16 结论要重验）。

## 目标

1. **期望值从 `.S` 派生到数据**（不跑实现、不拿实测当真值）：写一个解析脚本，从 `__CHECK_RD`/`__CHECK_MEM` 等宏的内联期望常量派生每个镜像的「槽 → 期望值」序列，落 `tests/data/inst-signature/`（带来源：`文件:行` + 生成命令，按「入库产物三件套」）；
2. **host 侧槽级比对**：复用 `tools/testcases/lib/signature.py`（`parse`/`compare`/`unwritten`），不另写解析器；新增 `make check-inst-sig`（L2），对 272 镜像逐槽比对；
3. **诊断能力**：失败输出必须给「槽 N 期望 X 实际 Y + 该槽来自哪个 `.S` 的哪一行」；
4. 现有 `check-inst-asm`（退出码判据）保持不变。

## 验收（逐条贴真实 rc）

1. **272 镜像全量槽级一致**（不是抽样），且镜像数/槽数与 `tests/case-ledger.tsv` 现场派生一致；
2. **`.S` 零改动**：`git diff` 对 `tests/inst/**/*.S` 为空；计时构建的 `.text` 与改前逐字节相同（抽样 ≥20 + 全量 md5 对比更强）；
3. **漏跑可见**：删一条 `SIGUPD`（临时树）⇒ 该槽为 `0xdeadbeef`，报「槽 N 未写」；
4. **可达 FAIL ≥3 路**：① 改一条派生期望值 ⇒ 槽号 + 两侧值报红；② 删一条 `SIGUPD` ⇒ 漏跑红；③ 某镜像签名流缺失 ⇒ BLOCKED 而非 PASS；
5. **不自我实现当真值**：派生的期望值来自 `.S`（spec 派生、已复核），并给「期望值来源」与「实测流」两条独立路径；
6. 门控：`check-inst-asm` **272/272**、`check-tests-index`、`check-case-ledger`、`check-index-blobs`、`check-knowledge-refs`。

## 若解析不可行（退路，需在完成区说明理由）

只做「槽级诊断报告」：不改判据、不新增门控，`check-inst-asm` 失败时额外 dump「哪个槽、什么值」；真正的 conformance 门控留给 `m17-idl-004`（IDL 作 oracle）。**不得**用「把实测值冻结成 golden」来充当期望（那是以实现反推）。

## 约束

独立 `git worktree`；**不提交 git**；**不改 272 个 `.S`**；不改 `signature.inc`/`signature.py` 的机制语义（只消费）；`tests/data/` 新增产物须带输入清单 + 生成命令 + 不可入库原因；术语「寄存器组」；完成区不写具体 `.work/**` 路径。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-20）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 宏展开器按空格切 head，制表符分隔的指令未识别 | ✅已修 | `inst_expected._Engine` 改 `split(None,1)` | 272 镜像派生成功（0 异常） |
| `__REC` 被当成「记录点」直接拦截 ⇒ `__NCHECK` 不累加、槽数恒 0 | ✅已修 | 只拦 `SIGUPD`，让 `__REC` 正常展开 | 槽数 4519 == `scan_source` 现场计数 |
| 数据区地址少加 `.testdata` 段基址 ⇒ `_MEM` 期望读错偏移 | ✅已修 | 从 `.lds` 现场解析段基址 | 8 个 `table` 槽与 `WDATA` 字面量注释逐项一致 |
| 误以为 inst 用 `SIG_BEGIN` 预填 `0xdeadbeef`；实测合法期望可为 `0xdeadbeef`（`rol.t` 两例） | ✅已修 | 解析用 `sentinel=False`；漏跑改由源码 `kind=unwritten` 静态判 | 272/272 通过；注入删除 `SIGUPD` 报「槽 1 未写」 |
| 错误期望会让 guest 先 `SYS_EXIT`，拿不到「实际值」 | ✅已修 | `inst_test.inc` 的 `__EXIT` 加 `SIG_CONTINUE` 诊断开关（未定义零改动） | 全量 272 `.text` md5 与 HEAD 版逐字节相同；注入错误期望得到「槽 N 期望/实际 + 来源」 |
| 脚本依赖调用方 cwd（`.include "tests/…"`） | ✅已修 | `main()` 内 `os.chdir(root)` | 从仓外目录跑 `--data-only` rc=0 |
| 272 个 `.S` 的 stem 是否唯一（线程工作目录冲突） | ✅已核 | 无需改 | 现场统计 272 个 stem 无重复 |
| 输入 sha256 清单漏了链接布局 `.lds`（派生读它取 `ENTRY`/段基址） | ✅已修 | `_INPUT_GLOBS` 增 `DEFAULT_LDS` | `inputs.sha256` 285 行（含 `tests/ee-tiny/inst_tiny.lds`）；`--data-only` rc=0 |

### 第 1 轮 reviewer 验收（2026-11-20，中改档；判决 **Needs Revision**，1 项）

**我自己的重跑（命令 / 真实输出 / 退出码）**
- `python3 tools/testcases/inst/check_inst_sig.py --data-only` ⇒ **rc=0**：`272 镜像 / 4519 槽（静态期望 4481 / 运行期关系 38）；数据与 case-ledger 对账一致`。
- `make check-inst-sig` ⇒ **rc=0**：`272/272 镜像通过；静态槽 4481 逐槽一致；运行期关系槽 38（不比对取值）`。
- `make check-inst-asm` ⇒ **rc=0**：`272/272 镜像通过（272 个 id；链例 + 故障链 632 例）`。
- `make check-tests-index` / `check-case-ledger` / `check-index-blobs` / `check-inst-macro-scope` / `check-knowledge-refs` ⇒ 各 **rc=0**（末行：`472 条 PASS` / `清单 == 现场派生` / `343 new-file + 100 modification patch OK` / `三分层 + 死宏 0 PASS` / `结果: PASS`）。
- 运行期证据目录内 `run.sh` 全量重跑 ⇒ **rc=0**，`40/40 PASS`（含 4 路注入 → FAIL → 还原 → 回绿）。
- `sha256sum -c tests/data/inst-signature/inputs.sha256` ⇒ **rc=0**，`285/285 OK`（`wc -l` = 285）。

**计数现场派生（我自己从数据文件/台账重算，不采信完成区）**
- `expected.tsv` 数据行 **4519** = `value 4473 + table 8 + relation 38`（`unwritten 0`）；镜像 **272**（`undi_reserved.S` 为 0 槽，故数据文件只出现 271 个路径）。
- `tests/case-ledger.tsv` `asm` 行 5151 / 路径 272，与派生镜像集**双向相等**；`undi_reserved` 3 行 − 3 故障例 = 0 槽 ⇒ 与门控报数逐项吻合。

**期望值来源（抽 3 例手工核对 槽号 ↔ `.S` 行 ↔ 期望值）**
- `atomic_rmw.S:56/66/76` → 槽 1/2/3 = `0x100 / 0x1 / 0x0`；`st.b_rrii_rd.S:63`（`__CHECK_MEM`）→ 槽 19 = `0x11`；`andn.w_rwii_rb.S:44`（`TEST_WI_RB_MEM`）→ 槽 7 `table` = `0x012345670000cdef`，与共享宏层 `WDATA+0x58` 字面量 `0x012345670000CDEF` 一致（另 7 个 `table` 槽逐一命中 WDATA 表）；`st.o_rrii_rb.S:93` 的 `ENTRY + 0x1800` → `0x0000ffffff011900`（`ENTRY=0xffffff010100`）。`derive()` 全程静态、不调 QEMU/LLVM ⇒ **无实测冻结成 golden**。
- 38 个 `relation` 槽**不是**其它槽的重复：宏体（`__CHECK_RD_IP`/`__CHECK_MEM_RB`/`TEST_WI_RF0_*`）内均有 `br.eq`+`__EXIT`，且 `relation` ⟺ 源码确有 `SIGUPD`（无写入口即落 `unwritten` 判红）⇒ 跳过取值不掩盖失败，`check-inst-asm` 仍比退出码与结果字节流。

**可达 FAIL（我在临时树 `cp`+md5 独立注入 2 路，均已还原回绿）**
- ① 改 `.S` 期望 `0x100→0x101` ⇒ `--data-only` **rc=1**：`DATA-FAIL: expected.tsv:6 行不一致` + `inputs.sha256:2 行不一致`；还原后 md5 `5b018abeb5bffbc35fe41e06e524ab4b`、**rc=0**。
- ② 删 `SIGUPD`（`pt==10` 只加 `__NCHECK`）⇒ 重生成数据后 `--id atomic_rmw` **rc=1**：`槽 10 未写（__NCHECK 记了该检查点，但源码没有 SIGUPD 写入口；来源 atomic_rmw.S:175）` + `槽 11 期望/实际`；还原 md5 `9af30a1cad94617a5e33c54045659620`，重生成数据与本仓逐字节相同、**rc=0** ⇒ 替代判据（`__NCHECK`/`SIGUPD` 静态派生）**可达 FAIL**、非恒真。

**`.S` 零改动 + 指令流**
- `git diff master -- 'tests/inst/**/*.S'` 为空（该 pathspec 实测命中 272 个 `.S`）；验收前后 `git status -uall` 均空。
- 我自己做全量 `.text` 对比：`master` 版 `inst_test.inc`（md5 `0ebf8f229883a8667212be076de2da1d`）vs 当前版（`9af30a1cad94617a5e33c54045659620`）各建 272 镜像 ⇒ `compared 272 mismatch 0`，**rc=0**。

**判决：Needs Revision（仅 1 项；其余全部通过）**
- **失败项**：运行期证据目录内 `run.sh` §4「272 镜像 .text md5 全同」基线取 `git show HEAD:`，而 HEAD 已含本任务改动（实测：工作树 = HEAD = `9af30a1c…`，`master` = `HEAD^` = `0ebf8f22…`）⇒ 两支比同一份文件，**恒真、无可达 FAIL 路径**（违「验证脚本反例门控」），完成区「与改动前逐字节相同（非抽样）」在一键脚本里缺有效证据；§1 的 `.S` 零改动只看工作树，抓不到「已提交的 `.S` 改动」。
- **改哪、怎么改**：只改该 `run.sh`（不动被测产物）——§4 基线改 `git show master:tests/inst/macros/inst_test.inc`，并加一条**基线 md5 断言**（期望 `0ebf8f229883a8667212be076de2da1d`），使 master 吸收该改动后**响亮报红**而非静默恒真；§1 改用 `git diff master -- 'tests/inst/**/*.S'`。改完重跑 `run.sh` 期望 **rc=0**。
- **约束逐条核验**：272 个 `.S` 零改动 ✓；未动 `signature.inc`/`signature.py` ✓；未 `install-host`、未重建 QEMU/gem5/chipyard ✓；未提交 git ✓；`git show --name-only HEAD` 恰 10 文件 ✓；术语按「寄存器组」口径 ✓；本记录无具体运行期路径 ✓；写入后已重跑 `check-knowledge-refs` ⇒ **rc=0**。

### 第 2 轮 reviewer 验收（2026-11-20；判决 **Accepted**）

**打回项复验（我自己的重跑）**
- 运行期证据目录内 `run.sh` ⇒ **rc=0、`[PASS]` 50 / `[FAIL]` 0**（我 grep 现场计数）。§1 六项全绿：基线 `9db0656f6cb3a30ea75217b0ecde7f0de23c6d32` 为 HEAD 祖先 rc=0、基线 `inst_test.inc` md5 锚定 `0ebf8f229883a8667212be076de2da1d`、`.S` 路径集 272==272、`git diff <SHA> -- tests/inst` rc=0、`.S` 内容差异 0。
- §4：基线树 md5 == 锚定内容 PASS；**反向探针**「当前 `.inc` ≠ 基线 md5」PASS（`9af30a1c…` vs `0ebf8f22…`）；`images 272 mismatch 0` rc=0；脚本内注入④' 加一条指令 ⇒ `MISMATCH` rc=1 ⇒ `cp`+md5 还原后回绿 rc=0。
- **我自己的锚定反例**：把该脚本副本的 `BASE_SHA` 换成当前 `HEAD` 跑一次（原 `run.sh` 全程未动、md5 `032f1bdabb2050f4cfb1464c32afde58`）⇒ **rc=1、`[FAIL]` 2**，红在且仅在两处：`基线 inst_test.inc md5 锚定 expected=0ebf8f22… actual=9af30a1c…`、`基线树 inst_test.inc == 锚定内容 …`（此时 §4 的 `.text` 比对本身 PASS ⇒ 判别力正来自锚定断言，旧恒真已堵死）；`cp`+md5 还原（`md5sum -c` OK）后同一脚本重跑 ⇒ **rc=0、50/50**。

**合入后仍可跑**：`git merge-base --is-ancestor 9db0656f… HEAD` rc=0、对 `master` 也 rc=0（`9db0656f..master`=5，派单台账提交已在 master 历史）；基线是固定 git 对象 + 内容 md5 锚定，全程不读 `master`/`HEAD` 内容 ⇒ squash 合入后行为不变。
**`expected.tsv`/`inputs.sha256` 不需同类锚定**：二者是**当前树的生成物**，对照物 = 现场 `derive()` 重派生（`check_data` 逐字节比 + §2 `--write` md5 不变），`inputs.sha256` 另钉住 285 个输入哈希；这些输入本身已被 §1/§4 锚定（272 个 `.S` 路径+内容、`inst_test.inc` md5）。锚到固定 SHA 反会把合法 `.S` 更新判红——要锚的是**历史对照物**（`.inc` 改前版本），不是可派生的生成物。

**未回归抽样**：`make check-inst-sig` ⇒ rc=0（`272/272 …静态槽 4481 …关系槽 38`，4519 槽）；`make check-inst-asm` ⇒ rc=0（`272/272，632 例`）；`check-tests-index`/`check-case-ledger`/`check-index-blobs` 我单独直跑各 rc=0；`check-knowledge-refs` rc=0；5 个实现/数据文件 md5 与第 1 轮快照逐一相同。
**范围与约束**：`git diff --name-only HEAD~1 HEAD` 只有任务书，实现 10 文件仍在 `328fd3ef`，`git status -uall` 干净、未提交 git；未 `install-host`、未重建组件；本记录无具体运行期路径；写后重跑 `check-knowledge-refs` ⇒ rc=0。

## 完成区

**测试结果**：证据脚本 50/50 项 PASS（rc=0）；`check-inst-sig` 272/272 镜像、4519 槽（静态 4481 逐槽全等；38 个运行期关系槽不比对取值（静态保证写入口存在））；`check-inst-asm` 272/272（632 故障例）；`check-tests-index` / `check-case-ledger` / `check-index-blobs` / `check-knowledge-refs` / `check-inst-macro-scope` 真实 rc=0。
**修改文件**：`Makefile`；`docs/Process-07-门控分层规范.md`；`tests/inst/macros/inst_test.inc`（`__EXIT` 诊断开关）；`tools/testcases/README.md`；新增 `tools/testcases/lib/inst_expected.py`、`tools/testcases/inst/check_inst_sig.py`、`tests/data/inst-signature/{expected.tsv,inputs.sha256,README.md}`。272 个 `.S` 零改动。
**验收结果**：① 镜像数/槽数 272/4519 与 `tests/case-ledger.tsv` 现场派生一致；② `.S` 对**固定基线** `9db0656f6cb3a30ea75217b0ecde7f0de23c6d32` 的 diff/路径集/内容差异均为 0，**全量 272** 镜像 `.text` md5 与该基线 `inst_test.inc` 构建逐字节相同（非抽样）；③ 删 `SIGUPD` 注入 ⇒「槽 1 未写 + 来源 `.S:行`」（缓冲未预填，实际值 0，见坑）；④ 可达 FAIL 4 路：改派生期望值 / 改 `.S` 期望（数据漂移）/ 删 `SIGUPD` / 删 dump（BLOCKED），均临时树注入→红→`cp` 还原→回绿；⑤ 既有门控见测试结果。
**新发现/坑**：`tests/inst` **不用** `SIG_BEGIN`，槽未预填；合法期望本身可为 `0x00000000deadbeef`（`08-arith-logic-tetra/rol.t` 两例）⇒ 不能拿哨兵判漏跑，改由 `__NCHECK` 加一而无 `SIGUPD` 的静态派生判「未写」。`__EXIT` 诊断开关未定义时零指令增量（已全量 md5 证）。`tests/data/inst-signature/expected.tsv` 约 600 KB 纯文本、逐行带 `文件:行`。
**遗留问题**：`make check` 在 `check-patch-tree` 红（共享构建树里 chipyard/linux 源码被并行任务改动，与本任务 diff 无关）；`check-temp-dirs` 红（`m14-*` 的历史临时目录，只报告不删除）。两者均非本任务引入。

### 返工（第 1 轮 reviewer，2026-11-20）

- **问题**：证据脚本 §4 用 `git show HEAD:` 取基线——WIP/squash 合入后 HEAD == 工作树 ⇒ `.text` 比对恒真、无可达 FAIL；§1 用 `git status`/裸 `git diff`，抓不到已提交的 `.S` 改动。脚本内同类「与当前提交比」的断言一并排查。
- **改法**：固定基线 `9db0656f6cb3a30ea75217b0ecde7f0de23c6d32`（本分支 merge-base；合并后仍是祖先，不用 `HEAD`/`master`）+ 断言基线 `inst_test.inc` md5=`0ebf8f229883a8667212be076de2da1d`；§1 改 `git diff <SHA>` + 基线/工作树 `.S` 路径集 + 内容差异；§4 用该 SHA 内容建基线；注释写明基线含义。
- **重跑**：运行期证据目录 `run.sh` rc=0，**50/50 PASS**；`check-inst-sig` 272/272 镜像、4519 槽；`.S` 差异 0；272 `.text` md5 全同。
- **注入验证**：① 临时树 `__TEST_BEGIN` 加一条指令 ⇒ §4 比对 rc=1（MISMATCH），`cp`+md5 还原后回绿；② 把脚本基线换成 `HEAD` 跑一次 ⇒「基线 md5 锚定」红、整脚本 rc=1（证明旧写法在合入后必红、固定 SHA 有效）。
