# TESTCASES-039t: Embench 接入（钉子③）

**模块**：testcases
**项目里程碑**：M6
**依赖**：`INFRA-051t`（Embench 组件接入）、`LLVM-062t`/`063t`（编译能力）、`QEMU-052t`（ELF 加载）
**状态**：已验证

> **追加（2026-10-10）**：本任务**新增依赖** `LLVM-069t`（整数 `setcc`/`select_cc` lowering，`ISS-173`）+ `INFRA-054t`（clang 内置头/resource-dir，`ISS-174`）；**二者就绪后重新下发**。当前 `状态` 保持 `待开始`，阻塞说明（完成区）保留。证据指针：`.work/log/testcases/TESTCASES-039t-{blocker.log,progress.md}`。

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `INFRA-051t` 产出：`.work/source/embench-iot`（工作树）+ `components/embench-iot/{patches/**,series,changelog.md}`。
  - `LLVM-062t`/`063t` 的 DADAO 工具链（编译能力）；`QEMU-052t` 的 ELF 加载。
  - `spec/Process-01-组件补丁组织与构建编排.md`（board shim/运行时补充的承载）。
  - `INTEG-023k §A（#3 不引 libc）`、`§C（TESTCASES-039t）`：board shim 3 函数 + 最小运行时 + `md5sum` 大端适配；**首验收 = 最小基准 QEMU 正确退出码**。
- **输出**：
  1. **board shim 3 函数**：`initialise_board`/`start_trigger`/`stop_trigger`（落 `components/embench-iot/patches/**`）。
  2. **最小运行时**：`mem*`/`str*`/`ctype`/`sqrt`（**不引 libc**）。
  3. **`md5sum` 大端适配**（Embench 的 `md5sum` 依赖端序）。
  4. **最小基准**端到端跑通：DADAO 工具链编译/链接 → QEMU 执行 → **正确退出码**（首验收）。
- **约束**：
  - **不引 libc**（最小运行时自写）。
  - 组件补丁遵循 `Process-01`（树形补丁集 + 一文件一补丁）；工作树 `.work/source/embench-iot` 由 `make fetch` 生成（gitignored）。
  - **首验收 = 最小基准正确退出码**；全量基准可后续增量，**不**在首验收硬性要求。
  - **计数不写死**：基准条数/通过数由脚本/门控**现场统计**。

## 硬约束

- **临时目录** `/tmp/opencode/TESTCASES-039t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**（涉 `components/**` 者）：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/TESTCASES-039t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **重建成本申报**：涉 `components/**/patches/**` 或 QEMU 重建 ⇒ 开工前写明「重建 X，预计 N 分钟」；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/testcases/TESTCASES-039t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **board shim 3 函数**：`initialise_board`/`start_trigger`/`stop_trigger` 存在并被 Embench 调用（给真实输出）。
2. **最小运行时**：`mem*`/`str*`/`ctype`/`sqrt` 自写实现，**不引 libc**（给证据）。
3. **`md5sum` 大端**：Embench `md5sum` 在大端 DADAO 上结果正确（给真实输出）。
4. **首验收 = 最小基准正确退出码**：至少**一个**最小基准经「编译 → QEMU 执行 → 正确退出码」端到端通过（给真实命令 + 退出码）。
5. **门控**：`make check`/`check-interface`/`check-patch-tree` EXIT=0（通过数**不下降 / 逐项相等**）。
6. **一键证据脚本**：`.work/evidence/TESTCASES-039t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检，给真实输出与退出码。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

> ✅ **已完成**（重新下发后，`LLVM-069t` + `INFRA-054t` 已解除上轮阻塞）。判据**恒为退出码 0**，未降级。
> **首验收达标**：`-O2` depthconv/nettle-aes exit=0；`-O0` 10/19 exit=0。

**测试结果**：见「验收结果」现场统计。**一键证据脚本** `.work/evidence/TESTCASES-039t/run.sh` 全绿（`EVIDENCE: PASS`，C1–C6）；`--inject` 自检 `INJECT: PASS`。

**修改文件**：
- `components/embench-iot/patches/{examples/dadao/boardsupport.c.patch,examples/dadao/boardsupport.h.patch,src/md5sum/md5.c.patch}` + `series` / `changelog.md` / `README.md`。
- `tests/scripts/embench_runtime.c`、`tests/scripts/embench_include/{string,ctype,math,stdlib,stdio,assert}.h`；**复用** `tests/scripts/dadao_mem_runtime.ll`（未改）。
- 证据/日志：`.work/evidence/TESTCASES-039t/run.sh`、`.work/log/testcases/TESTCASES-039t-*`。

**验收结果**（真实命令 + 退出码）：
1. **board shim**：`boardsupport.{c,h}` 三函数存在、被 `support/main.c` 调用（运行期打印 `[board:init/start/stop]`）。
2. **最小运行时**：`embench_runtime.c`+freestanding 头 +（复用）`dadao_mem_runtime.ll`；链接产物 **无 undefined 符号**（`llvm-objdump -t` UND 空）⇒ 不引 libc。
3. **md5 大端**：修复版在大端 DADAO **exit=0**、未修版（`patch -R` 重建）**exit=1**；独立 oracle（Python `hashlib`）`h0^h1^h2^h3 = 0x33f673b4` 一致。
4. **首验收**：`-O2` depthconv/nettle-aes **exit=0**；`-O0` exit=0 = depthconv/huffbench/matmult-int/nettle-aes/nettle-sha256/nsichneu/statemate/tarfind/ud/xgboost。
5. **门控**：`make check` / `check-interface` / `check-patch-tree` 均 **EXIT=0**（不下降）。
6. **⑥证据脚本**：`run.sh` = `EVIDENCE: PASS`；`--inject` = `INJECT: PASS`（注入→FAIL→`cp`+md5 还原→回绿）。

**阶段 1（编译矩阵，现场统计）**：`-O2` = **6/19** 通过；`-O0` = **10/19**。失败跨 **5+ 类后端缺口**，**不集中**于已知遗留（G1）：G1 大常量比较>12 位（edn/slre/wikisort/crc32/sglib-combined/md5sum）；G2 `umul_lohi` 128 位乘（aha-mont64）；G3 `br_jt` 跳转表（picojpeg/qrduino）；G4 尾调用 `LowerCall` 断言（crc32/md5sum/tarfind/ud/xgboost，仅 -O2）；G5 分支目标超 12 位（nsichneu，-O2）；G6 **-O2 运行期误编译致死循环**（huffbench/matmult-int/nettle-sha256/statemate；-O0/-O1 正常）。详见 `.work/log/testcases/TESTCASES-039t-stage1-gaps.md`。

**新发现/坑**：① `-O2` 可产生**运行期死循环**（G6），须与编译期失败并列登记；② `bitcast f64<->i64` 不可 select（`fabs`/`__builtin_sqrt` 崩），`sqrt` 经 `memcpy` 内存型 pun 规避；③ 本轮未命中上轮阻塞（setcc/内置头均已解）。

**遗留问题**：G1–G6 后端缺口（**越界**，须改 `components/llvm-project/**`）——建议**各立新 LLVM 任务**（G1 已知；G2 128 位乘；G3 跳转表；G4 尾调用；G5 分支范围；G6 -O2 误编译）。**本任务交付物不受阻**（首验收已达标）。

## 审阅记录

#### 第 1 轮 engineer 自审（2026-10-10，**无代码改动**，自审=阻塞核实）

- 本任务无源码改动（未产出交付物），自审=**独立复核阻塞结论**：先用手工 `.ll`（不含 clang）在 `llc` 上复现 `setcc` 崩溃 → 排除 clang/TargetInfo 因素，确认为后端 ISel 能力缺口；再矩阵化 C 构造（O0/O2）→ 确认 Embench 必经形态无一可编。**判定**：首验收不可达，判据不降级，`待开始`（阻塞）返回。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 整数 `setcc`/`select_cc` 无 lowering ⇒ Embench 不可编译 | ⏸延后（越界，须改 `components/llvm-project/**`） | 无（越界；仅记录） | `.work/log/testcases/TESTCASES-039t-{blocker.log,matrix_result.txt}`；`llc sc.ll` rc=134 |
| clang 内置头缺失（resource-dir 不存在） | ⏸延后（可绕过，非本任务致命项） | 无 | `.work/log/testcases/TESTCASES-039t-blocker_probe_result.txt`（D1 rc=1 / D3 NO） |

#### 第 1 轮 reviewer 验收（2026-10-10，独立重跑）

**判决：Accepted**（验收标准 1–7 全过；约束无违反）。证据全量落 `.work/log/testcases/TESTCASES-039t-review-*.log`（本轮由 reviewer 留存）。

**重跑记录（reviewer 自建管线 `/tmp/opencode/TESTCASES-039t-review/{e2e,md5,matrix}.sh`，非复用 run.sh）**：
1. **首验收独立复现**：`e2e.sh {ud,xgboost,nettle-aes} O0`（clang→llc/llvm-mc→ld.lld→QEMU）⇒ 各 `GUEST_EXIT=0`；QEMU 输出 `[board:init]/[board:start]/[board:stop]`（shim 3 函数运行期实证被 `support/main.c` 调用）。全量矩阵 **-O0 = 10/19 exit=0**（逐项与完成区 10 条一致）。
2. **md5 大端（独立 oracle）**：Python `hashlib.md5(bytes(i&0xff for i in range(1000)))` ⇒ `digest=cbecbdb0…08cc79`，`h0^h1^h2^h3 = 0x33f673b4` **== `RESULT`**。DADAO 侧：修复版 **exit=0**；`patch -R` 反推上游（rc=0，无 `.orig/.rej`）重建未修版 **exit=1**（判别力成立）。二者均带同一 G1 绕行（`r==RESULT` ⇒ `volatile rr` 比较，语义等价，已在脚本注释披露）。
3. **不引 libc**：链接命令行 `ld.lld -T dadao.lds <objs> -o x.elf`（**无 `-lc/-lm`**）；`llvm-objdump -t xgboost.elf | grep -i UND` ⇒ **无匹配（rc=1）**；唯一名似 libc 者为 BEEBS 自带 `malloc_beebs`（已定义）。`tests/scripts/dadao_mem_runtime.ll` tracked 且 md5 `e0295436…f9b890` 与注入前快照一致 ⇒ **未改**。宿主 oracle 复核 `sqrt/strlen/strcmp`：**15/15 值 0 mismatch**（rel 1e-12）。
4. **G6 独立复现（成立）**：`TO=25` 下 `-O2` `huffbench`/`matmult-int` ⇒ `GUEST_EXIT=124`（超时被杀），`-O0` 同基准 ⇒ **0**；QEMU 输出仅 `[board:init]`、无 `[board:start]`（hang 于 `warm_caches`）。全量 -O2 矩阵 **2/19 exit=0**（depthconv/nettle-aes）+ **4 个 TIMEOUT**（huffbench/matmult-int/nettle-sha256/statemate）⇒ 与 G6 清单逐项吻合。**结论：G6 成立**（-O2 运行期误编译致死循环，非算法）。
5. **G1 独立复现（成立）**：`llc -march=dadao -O0 -filetype=obj` on `icmp slt i64 %v, 5000` ⇒ **rc=134**，`LLVM ERROR: DADAO: select/setcc compare against a constant that does not fit a 12-bit immediate is not supported yet`。**结论：G1 成立且为显式失败**。
6. **门控（逐个 make，均 rc=0）**：`check-patch-tree` EXIT=0（`3 component(s), 109 patches OK`，含断言⑥⑨）；`check-interface` EXIT=0（`PASS 83 / FAIL 0`）；`make check` EXIT=0（lit `Passed 76 / Unsupported 1`，`repository checks: PASS`）。
7. **补丁纪律**：`series` 新增 3 条目、路径字典序 ✓；4 补丁各恰 1 个 `diff --git` + 1 hunk（非空）✓；`git diff <base 09c2ed8> HEAD`（组件工作树）与「4 补丁按 series 拼接」**逐字节相同**（140 行 vs 140 行，`diff` rc=0）⇒ base+k 自洽；`check_patch_tree.py --source-state`：embench-iot `HEAD=6d327b27a1af count=1 clean=True` ✓。`git status --porcelain -uall` 仅本任务 14 项；`spec/ contracts/ tools/ Makefile` 交集**空**；其它 `components/**` **零改**；无 `_tmp/_orig/_rej`。
8. **证据脚本（审+重跑+独立注入）**：全量重跑 `EVIDENCE: PASS` / **`RUN_EXIT=0`**；engineer 自带 `--inject` ⇒ `INJECT: PASS`（exit=0）。**独立注入 A**（与 engineer 不同，篡改 `$W/src/md5sum/md5.c` 小端组装 `<<24`→`<<16`）⇒ `RUN_EXIT=1`、`EVIDENCE: FAIL (2 checks)`（含语义项 `C3 md5sum (fixed) exit=1 (want 0)`）；`cp`+md5 还原（前后均 `7cbbad585bca3af70960f4bf6578def6`，内层工作树 `git status` 空）⇒ 重跑 `EVIDENCE: PASS / RUN_EXIT=0`。**独立注入 B**（补丁区外 `LEFTROTATE 32-c`→`31-c`）⇒ 仅语义项 FAIL（`EVIDENCE: FAIL (1 checks)`，`reconstructed upstream` 仍 PASS）⇒ 证明该断言有**独立可达 FAIL 路径**，未被结构性检查掩盖。

**约束核验**：判据恒为退出码（未降级）✓；shim 3 函数 ✓；运行时自写不引 libc（复用 `.ll` 未改）✓；md5 大端适配正确 ✓；改动范围仅 `components/embench-iot/**` + `tests/**` + 任务书 + `.work/**` ✓；临时目录 `/tmp/opencode/TESTCASES-039t-review/` ✓；未提交 git、未用 `git checkout/restore/stash`/`git show >` ✓。**快照对账**：审查前后 `git status --porcelain -uall` + 17 个目标文件 md5 **逐行相同**（`snapshot-{pre,post}.txt` diff rc=0）；本记录写入后任务书 md5 变更属预期。

**非阻断问题（建议后续处理，不返工）**：① `run.sh` 用 `> "$LOG"` 截断 `.work/log/…-evidence.log`，会覆盖上一轮留证（engineer 原始输出另存 `-evidence-final.log` 未失）——建议改追加或带时间戳；② C1 用 `grep` 匹配函数名，注释中同名亦匹配 ⇒「删定义留注释」仍 PASS，靠 C4 链接失败与 `[board:*]` 运行期输出兜底——建议改符号表/定义正则；③ C2 的 UND grep 只列 5 个 libc 符号，真正兜底是 ld.lld 对未定义符号默认报错；④ `sqrt` 在当前通过集内是死代码（仅 wikisort 引用，wikisort 因 G1 编译失败），已由宿主 oracle 独立验证。

#### 第 2 轮 engineer 自审（2026-10-10，重新下发；有代码改动 ⇒ 自主逐行审查）

**范围**：`tests/scripts/embench_runtime.c`、`tests/scripts/embench_include/*.h`、`components/embench-iot/patches/**`（board shim + md5）、`series`/`changelog`/`README`。**逐行审查要点与判决**：
- 逻辑：`strlen/strchr/strcmp`/ctype（ASCII，无 locale）；`sqrt` 位技巧 seed + 6 次 Newton（host oracle 比对 libm：15 值全 OK；DADAO E2E：144/1000/12345/1 → exit=0）。
- 防脆弱：md5 修复**不改语义**（LE 组装等价于小端宿主 `uint32_t*`），未修版在大端 exit=1 证明判别力；board shim 的 semihosting asm **补声明 `rd8` 输出**（服务写回 rd8，原缺声明属潜伏缺陷）。
- 防造假：`run.sh` 每条断言有可达 FAIL 路径；`--inject` 改**临时** `.ll`（未触 tracked 文件，`git status` 佐证）、`cp`+md5 还原回绿。
- 越界核对：改动仅在 `components/embench-iot/**`、`tests/**`、`.work/**`、本任务书；未触 `spec/`/`contracts/`/`Makefile`/其它 `components/**`/`tools/**`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| semihosting asm 未声明 `rd8`（返回寄存器）为输出 ⇒ 潜伏误优化 | ✅已修 | `boardsupport.c` 加 `register long ret __asm__("rd8")` + `"=r"(ret)` | `clang rc=0`；`[board:*]` 仍打印、benchmark exit=0 |
| 证据脚本 C3 依赖旁存 `md5_upstream.c`（易失） | ✅已修 | 改为 `patch -R` 反应用已提交组件补丁重建 upstream | `run.sh` C3 全绿（`PASS C3 reconstructed upstream…`） |
| 证据脚本注入改**全部** mem 函数 ⇒ `memcmp` 恒等掩盖 memcpy 损坏（假绿） | ✅已修 | 注入**仅** `@memcpy`（正则限函数域），断言仅 1 行变更 | `--inject`：注入 exit=1、还原 exit=0（真实输出） |
| G1–G6 后端缺口（编译期/运行期） | ⏸延后（越界，须改 `components/llvm-project/**`） | 无（仅记录并给出最小复现） | `.work/log/testcases/TESTCASES-039t-stage1-gaps.md` + `-stage1-matrix{,-O0}.log` |

**判定**：全部 finding 已修或已按越界延后；首验收达标、门控/证据脚本全绿 ⇒ **`待验收`** 返回。

#### architect 提交 + 文件集审核（2026-10-10，分支 `TESTCASES-039t`）

- **档位**：**正常提交**（reviewer 判 **Accepted**，验收标准 1–7 全过、约束无违反）。
- **提交**：本分支**单条**提交（`TESTCASES-039t: Embench 接入（board shim + 最小运行时 + md5 大端；-O0 10/19 退出码 0）+ 登记 6 类后端缺口（G1–G6）并立 LLVM-070t…074t`）；**只 commit、未 push**；由主会话 `git switch master && git merge --squash` **一次性落地**。
- **文件集对账**（`git -c core.quotepath=false diff --cached --name-only`，显式 staging、**禁** `git add -A`）：
  - **交付物**（完成区「修改文件」）：`components/embench-iot/{patches/examples/dadao/boardsupport.{c,h}.patch,patches/src/md5sum/md5.c.patch,series,changelog.md,README.md}`、`tests/scripts/embench_runtime.c`、`tests/scripts/embench_include/{assert,ctype,math,stdio,stdlib,string}.h` —— 与声明**逐条相等**。
  - **收尾台账**：本任务书（`**状态**`→`已验证` + 本条留痕）、`milestones.md`、`issues.yaml`（`ISS-175`–`180` 新登记）、`lessons.md §8.42`、新任务书 `LLVM-070t…074t`、`INTEG-023k`（追加）。
  - **漏提 0 / 多提 0 / 越界 0**（`spec/`、`contracts/`、`Makefile`、其它 `components/**` 交集为空——见 reviewer 约束核验 §7）。`.work/**`（证据脚本/日志）按 `.gitignore` 不入库。
