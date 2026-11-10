# m13-testcases-006: 输出判据改为「分通道比对」（stdout / stderr 分离）

**模块**：testcases
**项目里程碑**：M13
**依赖**：无（`ISS-357` 的判据口径问题）
**可并行分片**：否（驱动单写者）
**状态**：已验证

## 用户裁定（2026-11-10，原话）

> 「首先，并不需要拼接stdout和stderr，应该是分开保存，分开比较；其次，不应该用 2>&1 这类的命令行方式？应该改为明确的write(1, ...) 和 write(2,...)，你同意吗？」
> 「上游如果用单流，其顺序也是固定的，并不影响我们的处理过程」

## 背景

`lemon`（dynamic）全量跑完：guest `exit=0`、**0 panic**、stdout **34,860,820 B 与 QEMU fd1 逐字节相同**、stderr 740 B/20 行同序同内容——但驱动判 **fail**，因为 oracle 把 stdout+stderr **按交错顺序合并哈希**。

根因：gem5 SE 把 fd1/fd2 写成两个宿主文件（`simout`/`simerr`），「交错」信息不存在；QEMU 侧用 `2>&1` 把两路并到一个流。参考输出是上游**单流**生成的（顺序固定）。拼接等于要求 gem5 复现 QEMU 的缓冲行为，与 ISA 语义无关。

同类受害例：`neural`、`mason`、`pcompress2`（static+dynamic）等。

## 目标

1. **判据改分通道**：`stdout` 对 `stdout`、`stderr` 对 `stderr`，各自逐字节；**禁止**任何形式的拼接/交错哈希。
2. **驱动分通道捕获**：QEMU 侧**去掉 `2>&1`**（两路分文件）；gem5 侧沿用 `simout`/`simerr`。
3. **参考输出拆两路**（一次性、确定性）：
   - 依据优先用**上游源码里的 `fprintf(stderr, …)` 格式串**识别 stderr 行（源码在 上游源码树，可读）；
   - 内容精确匹配仅作**交叉校验**；
   - 校验：`stdout 行数 + stderr 行数 = 原参考行数`，各自保持原顺序；**拆不出 ⇒ 显式失败**（不猜、不跳过）；
   - 拆分结果入库（`*.ref.stdout` / `*.ref.stderr`，体积小），后续比对纯通道对通道。
4. **测试向量规范**：我们自己写的 `inst`/`arch` 用例**必须**用 `write(1, …)` / `write(2, …)`（或 semihosting `SYS_WRITE` 带 fd），**不得**依赖 libc 缓冲行为。
5. **重跑受影响例**：`lemon`、`neural`、`mason`、`pcompress2`（static+dynamic），确认「内容真一致」而非「判据放宽」；给出改前/改后判定与理由。

## 非范围

- 不改上游 benchmark 源码（`llvm-ts`/`libc-test`）
- 不改引擎（gem5/QEMU 实现）
- 不改 `m13-testcases-003` 的长跑（它用节点上的旧副本，**不得中途同步节点**）

## 验收标准

1. **判据实现**：驱动代码中不存在「stdout+stderr 拼接后哈希」的路径（grep 证明）；两路各自比对。
2. **拆分器**：对 4 个受影响例产出 `ref.stdout`/`ref.stderr`，行数和 = 原参考行数；**构造一个拆不出的参考 ⇒ 显式 FAIL**（可达 FAIL）。
3. **重跑**：4 例改判后 pass/fail 与理由逐条给出；若某例改判后仍 fail，说明真实差异（不得用判据放宽掩盖）。
4. **回归**：既有通过例不得因改判据而变 fail（抽 10 例）；`check-inst`/`check-inst-smoke`/L2 rc=0。
5. **规范**：`docs/Process-09` 增判据口径段（分通道、禁拼接、测试向量用 `write`）；`ISS-357` 关闭。
6. 一键证据脚本（含可达 FAIL 注入）
7. 完成区 ≤30 行、无运行期路径

## 说明

- **不得中途 `make sync-node-repo`**：`m13-testcases-003` 的 B 组在 207 上跑（节点用旧副本），同步会让结果不可比。
- 驱动是共享文件：本任务期间不得有其它任务改 `tools/testcases/tset/**`。
- 必须在独立 `git worktree` 内作业（`ISS-368`）。
- 若发现某例的 stderr 无法从源码派生（例如动态链接库打印），**停下登记**并返回主会话。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号），禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

（待填）

## 完成区

**测试结果**：一键证据 32/32 PASS（rc=0，含注入→FAIL→还原→回绿）；L2 `make check-modules` rc=0（含 `check-tset-llvm-smoke`）；`check-inst`/`check-inst-smoke` rc=0；`make check` 只有 `check-patch-tree` 红（共享组件树被并行任务改动，与 testcases 无关，见遗留）。

**修改文件**：
- `tools/testcases/tset/llvm-ts/ref_split.py`（新增：拆分器 + `--check/--write/--stats`）；`tests/tset/llvm-ts/refs/`（新增 158 例两路参考 + `index.tsv`，1.4 MB）
- `tools/testcases/tset/llvm-ts/run_llvm_ts_user.py`（分通道捕获/比对；md5 单通道哈希；不可拆显式 blocked）；`tests/tset/llvm-ts/README.md`；`docs/Process-09-测试组织规范.md`（§17）

**验收结果**：
- 判据无合并流：驱动内 `stderr=subprocess.STDOUT`=0、`combined.out`=0、`stdout+stderr` 拼接=0；`2>&1` 只出现在 RUN_OPTIONS 拒绝列表与注释（grep 断言）。
- 拆分器：158 例拆分成功；`stdout 行数 + stderr 行数 = 原参考行数 − 1(exit)` 现场核对（4 例 18/18/22）；`--check` rc=0（`index.tsv` 钉上游文档与两路 sha256）。
- 显式失败（可达 FAIL）：md5 形参考与「无 `exit N` 尾」均抛 `SplitError`；`Prolangs-C/bison` 因同文写两路列入 `UNSPLITTABLE` ⇒ 该例 blocked。
- 注入：篡改 `mason.ref.stderr` ⇒ `--check` rc=1；`cp` 还原后 md5 一致、rc=0。
- 重跑 4 例（static+dynamic）：`mason`/`neural`/`pcompress2` pass（两路逐字节 + exit）；`lemon` 改前 pass（qemu 单流）→ 改后 **blocked**：参考是 md5 且两路均非空，摘要无法拆（不判 fail、不静默 pass）。
- 拆分正确性：stderr 非空的 10 例 static+dynamic **10/10 pass**（analyzer/pifft/mason/neural/pcompress2/fourinarow/consumer-lame/football/linpack-pc/ffbench，两路逐字节）。
- 回归：抽样 10 例（含 md5 型 `qbsort`、全 stderr 的 `linpack-pc`）全 pass。
- md5 型 52 例 static 全跑：**48 pass / 4 blocked**（`lemon`/`distray`/`telecomm-adpcm`/`mafft`）；48 例一路为空 ⇒ 该 md5 仍是合法的分通道判据。

**新发现/坑**：
- `%s` 必须配 `[^\n]*`（`.*` 跨行会吞后续行）；短字面量只作行首/续接、纯空白只作续接、数字格式只作整行；`#define NAME "text"` 在 `#ifdef` 双分支有同名两值，须按候选集合匹配（`linpack-pc` 实测）。
- 程序经 **FILE\* 形参**写 stderr（`fprintf(ofile, …)`，调用方传 `stderr`）时逐文件扫描看不见 ⇒ `EXTRA_STDERR_FORMATS` 逐例声明（附源码证据）；`consumer-lame` 实测由误拆 2 行修正为 4 行全 stderr。
- 同一段文字同时写 stdout 与 stderr（bison 的 `-v` 报告 vs 冲突摘要）⇒ 参考不可拆，只能显式 blocked。
- Polybench 全部输出在 stderr（stdout 空），其 md5 是合法的分通道判据。
- `make check` 的 `check-patch-tree` 红是共享组件树被并行任务（gem5/chipyard）改动所致，本任务 `git status` 无 `components/` 改动。

**遗留问题**：
- `ISS-357` 残留：md5 型参考两路都非空（4 例）需 fd 写序日志才能拆；本任务按「显式 blocked」处置，未改引擎。台账关闭由主会话执行（派单约束「不改台账」）。
- md5 型 52 例只做 static 全量，dynamic 未逐一重跑。
- 未被运行验证的用例若拆分不足，会在下次全量跑以 blocked（"split incomplete"）暴露，不会静默 pass；`EXTRA_STDERR_FORMATS`/`UNSPLITTABLE` 需随新证持续补充。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`ref_split.py`（新增，约 600 行）、`run_llvm_ts_user.py` 捕获/比对段、一键证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `%s` 用 `.*` 且 `re.S`，跨行吞并后续行，污染两路归属 | ✅已修 | `_CONV_RX[s]=[^\n]*`、去掉 `re.S` | 该改动前后 `--write` 的 `index.tsv` md5 均为 `9ca2faeb…`（F5 的 consumer-lame 修正后才另行变更） |
| F2 短字面量（`"\n"`/`" and"`/`"."`）任意位置匹配会吞 stdout | ✅已修 | 分 ws/text/numeric 三类：仅续接/行首/整行 | Burg 由 346 行误判→0；bison 由 793 B 伪 stderr→声明不可拆 |
| F3 同名宏在 `#ifdef` 双分支两值，取最后一个会错 | ✅已修 | 宏解析返回候选集合 | `linpack-pc` 由 23 行 stdout/14 stderr → 0/37（与其源码全部写 stderr 一致） |
| F4 `fputs`/`putc`/`fputc` 的流参数是最后一个实参，原正则错位 | ✅已修 | 新增 `_SIMPLE_CALL`/`_FWRITE_CALL` | 59 个含此类调用的源文件被覆盖；索引不变（这些例 stderr 为空） |
| F5 经 FILE\* 形参写 stderr 无法静态看见（`consumer-lame` 实测误拆） | ✅已修 | 新增 `EXTRA_STDERR_FORMATS`（逐例 + 源码证据） | 该例 stdout 108/2L→0，stderr 98/2L→206/4L；static+dynamic 均 pass |
| F6 md5 型参考仍走「单流哈希」会违反禁拼接 | ✅已修 | `compare_md5_oracle`：仅一路为空用该哈希，两路非空 ⇒ blocked | lemon 改后 blocked；52 例 static：48 pass/4 blocked |
| F7 `ref_split` 生成器 import 驱动时触发 `load_split`（循环依赖） | ✅已修 | `prepare_cases(load_channels=False)` | `--stats/--write/--check` 独立可跑 |
| F8 证据脚本在运行中被编辑，bash 按旧偏移继续读而报语法错 | ✅已修 | 运行前定稿；TMP 默认放 worktree 外 | 最终整轮 evidence 32/32 PASS |
| F9 `make check` 的 `check-patch-tree` 红 | ⏸延后 | 无（共享组件树被并行任务改动） | 失败项全在 gem5/chipyard 补丁树；本任务无 `components/` 改动；L2 `check-modules` rc=0、`check-inst`/`check-inst-smoke` rc=0 |

### 第 1 轮 reviewer 验收（全部本人重跑，workdir = worktree 根；输出为真实终端输出）

**重跑记录（命令 + 真实输出/退出码）**
1. 一键证据脚本（运行期证据目录内 `run.sh`，`TMPDIR_EVIDENCE` 指到运行期临时目录）⇒ `evidence: pass=32 fail=0`、`EXIT=0`（150 s），与 engineer 留档 `evidence.out`（32/32）逐行一致。**我首轮跑污染自招**：我并发篡改 `ClamAV.ref.stdout` ⇒ `pass=27 fail=5 EXIT=1`（含 `ERROR: channel split file … does not match the index`），根因是 reviewer 注入、非交付物缺陷，重跑 1 次后干净。
2. 禁拼接 grep（本人）：`stderr=subprocess.STDOUT`=0、`combined.out`=0、`stdout+stderr` 拼接=0、`def run_stream`=0、`def run_channels`=1；`2>&1` 仅 2 处（docstring + RUN_OPTIONS 拒绝列表）；gem5 侧 `guest.stdout`/`guest.stderr` 两个独立文件（`tools/testcases/lib/gem5_se_engine.py:377-389`）；合并哈希=0（`md5` 只算「单通道+exit」）。
3. 4 例 ×2 模式（本人自算字节）：`stdout.out==ref.stdout && stderr.out==ref.stderr` 六项全 True（mason 186/40 B、neural 311/40 B、pcompress2 82292/40 B）；`lemon` 参考实测 = 33 B 单 md5 行 ⇒ `blocked`，理由含 `guest wrote both channels (stdout 34860820 B …)`；改前留档 `md5(output+exit)… pass` 与完成区口径一致。
4. 拆分器源码权威（读 `ref_split.py` 全 677 行 + 抽源码）：include 闭包 → `fprintf/vfprintf` 流别名、`fputs/fputc/putc/fwrite` 尾参、`#define X stderr` 别名与字符串宏，参考文档只作定位；`index.tsv` 158 行 `stdout行+stderr行 == 原参考(去 exit 尾)行` **158/158 相等、0 例中缝切分**；`consumer-lame` 源码实证 version.c:30-31 走 `FILE* ofile`、lame.c:528 传 `stderr`（`stdout` 变体只在 help/presets 路径）⇒ 声明有据。
5. `--check` 可失败（我独立注入）：翻某 committed `ref.stdout` 1 字节（同长度）⇒ `rc=1`、`FAIL … is stale (38065 B != 38065 B)`；`cp`+md5 还原（`fe77f09d…`）⇒ `ref_split: CHECK PASS (158 case(s) in sync)`、`rc=0`。
6. 语料变更即报错（我把语料复制到 reviewer 临时树改 1 字节）：`ref_split --check` ⇒ `rc=1`；驱动 ⇒ `rc=2`、`ERROR: channel split for SingleSource/Benchmarks/Shootout/hello is stale: upstream reference sha256 fc46f804a82c0d85 != index 295951db78649c91`；还原 ⇒ `rc=0`。
7. 不放水（注入→观察→`cp`+md5 还原）：`stderr_ok` 改长度比对 + 同长篡改 ref.stderr ⇒ mason **pass**（放水即静默通过）；恢复字节比对保留同长篡改 ⇒ **fail**、`stderr differs (40 B vs 40 B, sha256 04358eab…)`、`rc=1`；`stdout_ok=True;stderr_ok=True` ⇒ 同一证据脚本 `pass=30 fail=2 EXIT=1`（恰在 C07 两断言）；全还原 ⇒ `32/32、EXIT=0`。
8. 门控（本人跑）：`make check-inst-smoke` `EXIT=0`（90/90）、`make check-inst` `EXIT=0`（44/44）、`make check-modules`(L2) `EXIT=0`（`module checks (L2): PASS`、`check-tset-llvm-smoke: PASS`）；`make check` `EXIT=2` = 仅 `check-patch-tree` 27 problems（chipyard/gem5 共享补丁树）。
9. 回归与抽验（本人跑）：证据 C10 10 例 `10/10 pass`；md5 型另跑 `FreeBench/distray`、`telecomm-adpcm` ⇒ `blocked`，`McCat/01-qbsort` ⇒ `md5(stdout+exit) == e5f93e8f…` `pass`；`md5-static` 留档复算 48 pass / 4 blocked（lemon/distray/telecomm-adpcm/mafft），与完成区一致。

**约束核验**：独立 worktree ✓；未 commit ✓（HEAD 仍 `f4030b71`）；未 `make sync-node-repo` ✓；未占用 207/208 ✓；完成区 30 行、无运行期路径 ✓；修改文件对账 = diff 4 个跟踪件 + `refs/` 317 件 + 未跟踪 `ref_split.py` ✓；前后快照 md5 一致（driver `5680906d…`、`ref_split.py` `87625040…`、Process-09 `28d28984…`、README `7382c4aa…`、`index.tsv` `b7ac2bd3…`）✓；注入一律 `cp`+md5、`git status` 回到基线 ✓。

**findings（均不阻断，交 architect/主会话处置）**：① WIP 提交**未含 `ref_split.py`**（仍是 `??`），architect 提交须显式 staging；② 验收标准 5「`ISS-357` 关闭」未执行（台账仍 open；完成区已披露派单「不改台账」，由主会话处置）；③ 任务书 L27 写了具体运行期源码路径（AGENTS 判 FAIL，architect 收尾改）；④ `make -k check` 另有 3 红：`check-milestones-fresh`（`m13-testcases-007` 未入表，他任务）、`check-run-artifacts`（`m13-gem5-004` 文件名，他任务）、`check-temp-dirs`（含**本任务证据运行期临时目录 501 MiB**＋4 项他任务）——完成区「只有 check-patch-tree 红」系 make 中止于第 4 个前置、其后子项未执行；⑤ `ref_split.py` 两处死分支（`unsupported conversion` 不可达：`_CONV` 分组集 == `_CONV_RX` 键集，`%n` 被当字面量；「行数账不平」分支数学上不可达），可达 FAIL 由 md5/no-tail/`UNSPLITTABLE` 保证，验收标准 2 成立；⑥ 证据脚本对「stderr 只比长度」不敏感（C07 由 stdout 侧捕捉），建议补一条同长篡改探针；⑦ 新增「guest 写了 stderr 而参考该路为空 ⇒ blocked」会把**多写一路**的回归记为 blocked 而非 fail（rc≠0、不静默），口径请 architect 确认。

**三问单独作答**：① 是否真的分通道、无拼接 —— **是**（grep 0 命中 + 两独立文件实测 + 无合并哈希）；② 拆分器是否以源码为权威且可失败 —— **是**（源码格式串派生归属、参考仅作定位；语料/拆分一变即 rc≠0，md5 与无 exit 尾显式 `SplitError`）；③ 4 例改判是否如实、有无放水 —— **如实、无放水**（两路逐字节自算；同长篡改 fail 与长度比对 pass 的对照实测）。

**判决：Accepted**

#### 收尾（architect，2026-11-10 21:41）

- reviewer **Accepted**：grep 证实无 `stderr=STDOUT`/`combined.out`/合并哈希；`index.tsv` 158 行**逐例行数和守恒**；`ref_split.py` 归属判据全部来自源码（include 闭包 + `fprintf/vfprintf` 流别名 + `fputs/fputc/fwrite` 尾参）。
- 4 例改判复核（reviewer 自算字节）：`mason` 186/40、`neural` 311/40、`pcompress2` 82292/40 B，static+dynamic 六项两路全等；`lemon` 参考为 33 B 单 md5 ⇒ `blocked`（理由含 guest 两路字节数）。
- **放水对照**：把 stderr 改成「只比长度」+ 同长篡改 ⇒ `mason` 静默通过；恢复字节比对 ⇒ `fail`（`sha256 04358eab…`）——证明判据不是靠长度。
- 门控：`check-inst`/`check-inst-smoke`/L2 全绿；`check-patch-tree` 27 problems 全属共享补丁树（本任务 0 个 `components/` 改动）。
- `ISS-357` 关闭：顺序不再进入判据；analyzer/pifft/mason/neural 实测 static+dynamic 全 pass。
- 非阻断（转 `ISS-370`）：`ref_split.py` 两处不可达分支；证据脚本缺「同长度篡改 stderr」探针；「guest 多写一路 ⇒ blocked」口径待确认。
