# GEM5-021t: gem5 SE tset 基线调查（static 先行）

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-014t`（已验证；SE 平台骨架）、`ADR-0048 D3/D4`（SE 复用 `tests/tset`，最终覆盖完整 tset）
**状态**：已验证

## 用户裁定（2026-11-06）

> M11 的「GEM5 == QEMU」按 **「补完整 tset（D4 字面）」** 收口。
>
> 追问后授权：**「允许加 SE 驱动（推荐）」** —— 允许在 `tools/testcases/` 加 gem5 SE 运行路径（driver 层），**不动 `tests/tset` 用例与期望**，先测出缺口。

## 现状（事实）

- gem5 SE 平台存在：`configs/dadao/se.py`（`--binary`，只接受静态 `ET_EXEC`）、`DadaoSEWorkload` + `Process` + SE TLB（`GEM5-014t`）
- SE 侧 syscall 面目前只到最小 libc 启动集（`set_tid_address`/`write`/`writev`/`exit`/`exit_group`）
- `tests/tset` 三个驱动（`run_libc_test_user_suite.py` / `run_llvm_ts_user.py` / `run_embench_user_suite.py`）都是 QEMU user 专用，**没有 gem5 SE 运行路径**
- `.dadao/tests/` 下没有任何 gem5 tset 运行目录 ⇒ 完整 tset 在 SE 上当前覆盖为 0

## 目标

1. **加 SE 运行路径**（driver 层，`tools/testcases/`）：让三类 tset 的 **static** 产物可在 gem5 SE 上执行并收集退出码/stdout；不修改 `tests/tset/**` 的用例、期望值、语料。
2. **跑出基线**：`libc-test` / `llvm-ts` / `embench` 的 static 全量（或按现场可枚举全集）在 gem5 SE 上逐一执行，记录：
   - `PASS` / `FAIL` / `SKIP` / `BLOCKED`
   - 退出码、stdout 摘要
   - `BLOCKED` 必须给**根因证据**（未实现 syscall 号/名称、`ET_DYN`/`PT_INTERP`、TLS 相关 syscall、`mmap`/`brk`、线程/futex、信号等）
3. **与 QEMU user 基线逐 case 对照**：同 case ID 比较 pass/fail/exit；输出差异清单（`gem5_only_fail` / `qemu_only_fail` / `blocked`），不得把 BLOCKED 写成 PASS。
4. **产出可复跑报告**：JSON（机器可读）+ Markdown 摘要（计数现场统计，不手写数字）；摘要落知识层（`.tao/knowledge/refs/`），运行期产物不入库。
5. 给出**缺口分类清单**（按能力分组、每组案例数与预估补做顺序），作为后续实现任务的输入。

## 范围 / 非范围

**在范围内**：`tools/testcases/lib/**`、`tools/testcases/tset/**` 的驱动层（新增 SE 模式）、`.tao/knowledge/refs/GEM5-021t-*`（摘要）、本任务书、`milestones.md`。

**不在范围**：实现缺失的 SE 能力（syscall/TLS/动态链接/线程等，另立任务）；`tests/tset` 用例与期望；QEMU/gem5 语义实现；`tests/parity/matrix-M11.md`（等完整 tset 对齐后再重生成）。

## 验收标准

1. 新增 SE 运行路径可复跑，命令写入任务书；**static 三类套件各跑一轮**并产出 JSON + 摘要。
2. 每个未通过案例都有 `BLOCKED`/`FAIL` 分类与证据；`BLOCKED` 不得计入 PASS；计数现场统计。
3. 与 QEMU user 基线逐 case 对照，输出 `gem5_only_fail`/`qemu_only_fail`/`blocked` 清单；若出现 `gem5 通过而 QEMU 未通过`，单列并标注（按 `ADR-0048 D5` 需定位）。
4. 缺口分类清单：每类给出「能力名、阻塞案例数、代表案例、所需改动面（syscall/TLB/TLS/loader）」。
5. 不改 `tests/tset/**`；`make check`（L1）rc=0；完成区 ≤30 行、无运行期路径。
6. 反例：把某个已知不可运行的产物（如 `ET_DYN`）喂给 SE 路径 ⇒ 必须记 `BLOCKED`（`PT_INTERP`/`ET_DYN`），不得 PASS。

## 实现（engine 参数化，驱动层）

- **共享引擎模块** `tools/testcases/lib/gem5_se_engine.py`：`static_gate`（只放行 `ET_EXEC`；`ET_DYN`/`PT_INTERP` 直接判 `BLOCKED`，不启动 gem5）、`run_gem5_se`（`gem5.opt --outdir <运行期目录> configs/dadao/se.py --binary <elf>`；guest fd1/2 落各自文件、sim 日志单独落盘）、`evaluate`（超时 / 非 guest 结束 `EXIT_CAUSE`/125 / `DADAO SE: syscall N not implemented` → `BLOCKED` + 证据；syscall 名从锁定 musl 的 `arch/dadao/bits/syscall.h.in` 现场解析）。
- **三个 tset 驱动**（`tset/libc-test`、`tset/llvm-ts`、`tset/embench`）新增 `--engine qemu|gem5-se`、`--gem5`、`--gem5-config`、`--gem5-timeout`；libc-test/embench 另加 `--jobs`（libc-test 原先串行）。语料枚举、构建行、期望值（t_status / verify_benchmark + board markers / 上游 reference）**一律不变**；`--engine gem5-se` 只换执行器。
- **基线编排** `tools/testcases/tset/gem5-se-baseline/run_gem5_se_baseline.py`：同一套件分别跑 qemu 与 gem5-se 两轮，按 case id 归并，输出 `gem5_only_fail` / `qemu_only_fail` / `blocked` 与缺口分类；摘要写 `.tao/knowledge/refs/`（计数全部现场统计）。摘要另记引擎身份：`--engine-banner <快照某例 sim.log>` 取 gem5 版本/编译时间，组件 commit 与 `series` 条数从仓库读；共享构建树的 gem5.opt sha256 在快照后可能已被并行任务重建覆盖，摘要会显式标注「不可复原」而不是写一个不对应这批数字的哈希。
- llvm-ts 的 SE 轮把 guest stdout、stderr 依次拼接为比较文档（SE 的 fd1/fd2 是两个宿主文件，无交错）；JSON 记录该口径。

**复跑命令**（运行期目录用占位符，不留具体路径）：

```sh
# 单套件单引擎
python3 tools/testcases/tset/libc-test/run_libc_test_user_suite.py \
  --link-mode static --engine gem5-se --jobs 32 \
  --work-dir <运行期临时目录> --json-out <运行期临时目录>/libc.json
python3 tools/testcases/tset/llvm-ts/run_llvm_ts_user.py \
  --link-mode static --engine gem5-se --jobs 32 \
  --work-dir <运行期临时目录> --json-out <运行期临时目录>/llvm.json
python3 tools/testcases/tset/embench/run_embench_user_suite.py \
  --link-mode static --engine gem5-se --jobs 32 \
  --work-dir <运行期临时目录> --json-out <运行期临时目录>/embench.json

# 三套件 × 两引擎 + 交叉表 + refs 摘要
JOBS=32 python3 tools/testcases/tset/gem5-se-baseline/run_gem5_se_baseline.py \
  --work-dir <运行期临时目录> --json-out <运行期临时目录>/baseline.json
```

**反例**（`BLOCKED`，不得 PASS）：`ET_DYN`（`ld.lld -shared` 产物）与 `PT_INTERP`（dynamic 轮镜像）喂给 SE 路径 ⇒ 驱动记 `BLOCKED` + 理由；gem5 本体对 `ET_DYN` 也 `fatal: DADAO SE: only ET_EXEC is supported`。证据脚本 `INJECT=1` 另做两处注入（驱动 oracle、摘要计数）证明断言可 FAIL。

## 说明

- 本轮只做 **static**；动态链接、TLS、线程/futex 按 `ADR-0048 D4` 属「后补但不得降级」，本轮只需**如实列入缺口**。
- 允许为了跑通 SE 路径做**最小**驱动改造（参数化 engine、产物选择、超时/日志），不得改测试语义。
- 若某套件在 SE 上连启动都不到（例如 loader 拒绝 `ET_EXEC` 以外），按 `BLOCKED` 记录并给出首个失败点（stderr/退出码）。

## 完成区

**测试结果**：证据脚本默认轮 **PASS=12 FAIL=0 BLOCKED=0**；`RUN_L1=1 INJECT=1` → **PASS=18 FAIL=0 BLOCKED=1**（BLOCKED = `make -k check` rc=2，归属见下）；两处注入均「注入→FAIL→`cp`+md5 还原→回绿」。回归复跑：embench full（O0,O2）gem5 **38/38**（与快照一致）；libc 子集（argv/strtod/memstream）gem5 **3/3 pass**（memstream 由 `GEM5-022t` 的 `brk` 转绿，属预期差异）。
**修改文件**：`tools/testcases/lib/gem5_se_engine.py`（新）、`tools/testcases/tset/gem5-se-baseline/run_gem5_se_baseline.py`（新）、三个 tset 驱动（`--engine/--gem5[-config|-timeout]`；libc/embench 另加 `--jobs`）、`.tao/knowledge/refs/GEM5-021t-baseline-{summary.json,summary.md,findings.md}`、本任务书、`milestones.md`。**未改** `tests/tset/**`、QEMU/gem5 语义、`components/gem5/**`、`tests/parity/matrix-M11.md`。
**验收结果**：static 全量两引擎逐 case 对照（快照）：QEMU pass=587 / gem5 pass=310 / both_pass=310 / blocked=270（其中 QEMU 通过 268）/ `gem5_only_fail`=9 / **`qemu_only_fail`=0**。分套件 gem5：libc-test 245+83 blocked+9 fail（337）、llvm-ts 27+187 blocked（214）、embench 38/38。超预算重测（600s）另计：7 例转 PASS、`Misc/pi` 转 fail、22 例仍 blocked。摘要已注明「2026-11-06 快照，随 GEM5-022t 落地会变」并记录引擎身份（lock commit `c8222cc6` + series 97 + gem5 25.1.0.1 / 编译于 `Nov 6 2026 01:17:05`；gem5.opt sha256 因共享构建树被并行任务重建而不可复原，已说明）。`ET_DYN`/`PT_INTERP` 反例：驱动判 BLOCKED 且 `cmd=0`，gem5 本体亦 `fatal: only ET_EXEC`。
**新发现/坑**：① 9 个 `math/*` + `pi` 的根因是 **float→int 舍入口径三方不一致**（SPEC 写 `rf0[33:32]` 控制、工具链不写 `rf0`、QEMU 截断），cast 位点三处：`__rem_pio2_large.c:303/304/311`（sin/cos/tan）、`expm1.c:153`（expm1/sinh/tanh）、`lgamma_r.c:156/255`（lgamma/lgamma_r/tgamma）；**归属待用户裁定**（`discussing.md` A/D/B/C），本轮不实现、不单方定性；② syscall 缺口排序 `brk` > 文件 I/O > 时钟 > `mmap`/信号 > IPC > futex；③ 120s/例偏紧（32 例超时，600s 下 7 例转绿），门控需按套件给预算；④ `--guest-stdout/err` 必须显式给文件，否则 gem5 打不开宿主管道。
**遗留问题**：① `make -k check` 唯一红 = `check-patch-tree` 的 **gem5** 断言（共享源树与分支补丁集不符）：共享 gem5 源树正被并行 `GEM5-022t` 改写（`brk` 实现），**本任务 `components/gem5` 改动 0**，证据脚本记 BLOCKED 并注明归属，不伪装绿；② 仅 static（dynamic/TLS/线程按 ADR-0048 D4 未测）；③ llvm-ts 只跑 scope A；④ 22 例 600s 仍超时（纯计算量，未判能力结论）。

## 审阅记录

#### 第 1 轮 engineer 自审
审查范围：本轮全部改动（新模块 `gem5_se_engine.py`、三个驱动 diff、基线编排、证据脚本）逐行审查，并以证据脚本复验。**判决：无未修缺陷**；发现项全部当场修完（见下表）。边界核对：`tests/tset/**`、QEMU/gem5 语义、`tests/parity/matrix-M11.md` 改动 **0**；工作树仅 5 个预期新增/修改。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 运行期产物落在 worktree 内（`baseline/`/`rt/`/`ev/` 等） | ✅已修 | 全部移到仓库外运行期目录；证据脚本默认值同步 | `git status --porcelain -uall` 只剩 5 项预期 |
| 摘要泄漏绝对运行期路径（驱动 reason 自带源码树绝对值） | ✅已修 | `sanitize()`：去仓库根/临时目录前缀，组件源树前缀折叠 | 摘要内绝对路径前缀计数 0 |
| 聚合器 `suites` 缺 `cases`，markdown 抛 `KeyError` | ✅已修 | `build_summary` 补 `cases`（截断 reason） | `--aggregate-only` rc=0；C6 复算 PASS |
| libc-test 并行后长时间无输出（诊断性差） | ✅已修 | stderr 进度 `[n/total] status case`（stdout 报表不变） | C4 驱动日志有进度行 |
| llvm-ts gem5 `rc<0` 会误入 qemu `-strace` 探针 | ✅已修 | SE 分支先判 `rc<0` ⇒ `blocked`（宿主信号非 guest 判定） | 代码级核对；C4/C5 重跑 PASS |
| 死代码（`parse_engines`/`describe_cmd`/`syscall_label`/`first_error_line`/`_first_line`） | ✅已修 | 删除未用函数 | `grep` 无引用 |
| 能力桶 `other` 未覆盖常见 syscall（12 例） | ✅已修 | 补 40+ `__NR_*` → 能力映射，重跑 libc-test gem5 | `other`=0（现 11 个能力桶） |
| `time budget` 与能力缺口混为一谈 | ✅已修 | 增设超预算重测（600s）单列，不计入主表 | summary「超预算重测」节；C6c 覆盖检查 PASS |
| `JOBS` 非数字静默降级为 1 | ✅已修 | 改 rc=2（与 `run_qemu_test.py` 同口径） | 代码级核对；证据脚本默认 JOBS 未设 |

#### 第 1 轮 reviewer 验收（2026-11-06）

**判决：Needs Revision**（返工 2 项；`make check` 红属并发环境、**不计入返工**）。以下全为本人现场重跑，日志在运行期目录（未入库）；注入前后 `git status --porcelain -uall` 快照**逐行一致**、9 个交付文件 `md5sum -c` 全 OK。

**重跑记录（真实 rc/输出）**
- 证据脚本（工作树内运行期证据目录）：默认轮 `PASS=11 FAIL=0` **rc=0**（两次）。注：按绝对路径调用会因 `.work` 符号链接把 ROOT 推到主树而红，属我方调用方式，已改正。
- `RUN_L1=1 INJECT=1`：`PASS=17 FAIL=1` **rc=1**，唯一 FAIL=`C7.make_check expected=0 actual=2`：`check-patch-tree: gem5 assertion⑦ worktree is not clean`（脏文件 `src/arch/dadao/{process.cc,process.hh,se_workload.cc}`，mtime 11:37–12:08，系 **GEM5-022t** 并发改写共享组件树）；脚本自带 I1/I2 注入均 `注入→FAIL→cp+md5→回绿` PASS。
- `make check` 我独立重试 **2 次均 rc=2**，根因同上、非本任务改动（本任务 diff 仅 `tools/testcases/**`+`.tao/**`，`tests/` 改动 0）；工程师 11:04 日志 `check-patch-tree: 7 component(s), 305 patches OK`、`repository checks (L1): PASS`。**请 architect 待 GEM5-022t 落地后复跑 L1**。
- 计数独立复算（自写脚本、不走被审代码，从三份驱动 JSON 现场统计）：`qemu_pass=587 / gem5_pass=310 / both=310 / blocked=270 / gem5_only_fail=9 / qemu_only_fail=0`；分套件 libc `335 vs 245+83+9`、llvm `214 vs 27+187`、embench `38 vs 38` —— 与 refs 摘要**逐项一致，无手写**。
- 子集独立复跑：embench 两引擎各 `38/38 pass`；libc `--filter '^math/'` ⇒ qemu `199 pass`、gem5 `190 pass+9 fail`，**fail ID 与基线同 9 例**。
- BLOCKED 归因（要求2）：270 条全有 `capability`+`reason`；238 条为 `syscall N (名) not implemented`（名字现场解析 musl `syscall.h.in`），32 条 timeout 单列 `time budget` 且 `required_change` 标注 *not a capability*，`other`=0；抽 3 例核 `sim.log` 原文与 JSON reason 逐字一致（如 `se_workload.cc:221: fatal: DADAO SE: syscall 214 not implemented (pc=0x25548)`）。
- 反例（要求6）：C1/C2/C2b/C3 全 PASS —— `ET_DYN`/`PT_INTERP` 驱动判 `BLOCKED:loader/ELF modality` 且 `cmd=0`（不启动 gem5），gem5 本体亦 `fatal ... only ET_EXEC`；**我方独立注入**（改 `static_gate` 放行 ET_DYN）⇒ `C1 FAIL`，`cp`+`md5sum -c ... OK` 还原 ⇒ C1/C2/C3 回 PASS。
- f2i（要求4）：我自写程序、同一 ELF 两引擎：`2.7→2 / -2.7→-2`（qemu）vs `2.7→3 / -2.7→-3`（gem5），另有 `-2.9→-2/-3`、`1.5→1/2`；9 例**同一 ELF** 上 qemu 真实致败行 0、gem5 >0（harness 判据 = 非 `X ` 前缀行）。**差异确证**；位点见返工项 B。

**约束核验**：交付物齐全 ✓；驱动仅加 `--engine/--gem5*`/`--jobs`，期望值/语料/`tests/tset/**` 未动（逐行 diff 核对，删除行仅并行化与 cmd 分支重构）✓；运行期产物全在仓库外 ✓；完成区 5 行 ≤30、无运行期路径 ✓；refs 三件套无绝对路径 ✓；BLOCKED 不计 PASS ✓。

**返工项**
- **A（阻断，门控断言写死 vs 现场值）** `run.sh` C4 断言 `memstream ⇒ blocked:heap/VMA (brk)`，而 GEM5-022t 已落地 brk ⇒ 当前树重跑 `C4.paths expected=ok actual=not-ok`、整脚本 rc=1（11:41 尚为绿，12:08 后红）。请改为不依赖他任务在途能力的稳定断言（例：SE 能跑通 + 若有 blocked 则必须带 syscall 证据），改完在当前树重跑至绿。
- **B（口径/归因）** `findings.md §2` 与完成区① 把 9 例一律归给 `__rem_pio2_large` 大参数规约：实测为**三处 cast 位点** —— `__rem_pio2_large` 的 `(int32_t)` 仅覆盖 sin/cos/tan；`expm1` 的 `int k = invln2*x+0.5`（我实测 k=2/qemu vs 3/gem5）覆盖 expm1/sinh/tanh；`lgamma_r::sin_pi` 的 `(int)(x*4.0)` 与 `i=(int)x` 覆盖 lgamma/lgamma_r/tgamma。另「gem5 核心 FP 缺陷」与 `discussing.md`「暂不判 gem5 单方缺陷、待用户裁定」冲突，须改回「SPEC/工具链不一致，语义归属待裁定」。

**非阻断 finding**：① summary 未记录所用引擎版本（gem5.opt md5/组件 commit），基线快照现已不可复现（blocked=270 随 GEM5-022t 收缩）；② `gem5_reason` 取首行 `first_error`，对 math/* 常是被容忍的 `X ` 行，真实致败行在 `guest.stdout` 的非 `X ` 行；③ `sanitize()` 硬编码仓库根绝对路径；④ libc-test 在 `--engine gem5-se` 下把 `unexplained_fail` 由门控降为 NOTE（fail 行仍在计数与交叉表可见，知悉即可）；⑤ 驱动 JSON 的 `sim_log/run_cmd` 指向搬迁前路径（运行期 JSON，refs 已净化）。

#### 第 2 轮 engineer 自审（返工，对应 reviewer Needs Revision）
**触发**：reviewer 判 Needs Revision（A 证据脚本断言写死在途能力；B 归因/口径）。本轮只改证据脚本、摘要生成、findings/完成区，不动驱动语义。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| A（阻断）C4 断言 `memstream ⇒ blocked:brk`，`GEM5-022t` 落地后必红 | ✅已修 | C4 改为**能力无关**的驱动契约检查（引擎=gem5-se、每案有状态、非 pass 必有 reason、blocked 必有归因、至少 1 例 pass）；新增 C4b（llvm-ts 单例同契约）。具体 blocked 名单不进断言 | 默认轮 PASS=12 FAIL=0；`RUN_L1=1 INJECT=1` PASS=18 FAIL=0 BLOCKED=1 |
| B 9 例归因写成单一 `__rem_pio2_large` + 「gem5 核心缺陷」单方定性 | ✅已修 | findings §1/§2 改为三方口径不一致（SPEC `rf0[33:32]` / 工具链不写 rf0 / QEMU 截断），列出三处 cast 位点；归属**待用户裁定**（`discussing.md` A/D/B/C），删除单方定性 | findings §2 与完成区① 逐条核对 musl 源码行号 |
| 非阻断：summary 补引擎版本 + 快照说明 | ✅已修 | 摘要新增「引擎与快照」节（lock commit / series / 版本 / 编译时间；sha256 不可复原的说明）+ 文首快照注记 | 摘要渲染见 `.tao/knowledge/refs/GEM5-021t-baseline-summary.md` 首两节 |
| 非阻断：`sanitize()` 硬编码绝对路径 | ✅已修 | 改为仅按仓库相对根标记剥前缀，不再硬编码任何宿主路径 | 摘要内绝对路径前缀计数 0；C6 复算 PASS |
| L1 红需归因而非伪造绿 | ✅已修 | `make -k check` 全量；若唯一红是 `check-patch-tree` 的 gem5 断言且本任务 `components/gem5` 改动 0 ⇒ 记 `BLOCKED` + 归属（不记 PASS） | `BLOCKED C7.make_check rc=2; 仅 check-patch-tree 的 gem5 断言红（6 条）；共享源被 GEM5-022t 改写`；`git status components/gem5` 0 |

#### 第 2 轮 reviewer 验收（2026-11-06）

**判决：Accepted**（A/B 均已复验；`make check` 红按 BLOCKED 归因，机械可核）。以下全为本人现场重跑；前后 `git status --porcelain -uall` 快照逐行一致、14 个文件 `md5sum -c` 全 OK、注入残留 0、`tests/` 与 `components/` 改动 0。

**重跑记录（真实 rc）**
- 默认轮运行期证据脚本 → **`PASS=12 FAIL=0 BLOCKED=0 rc=0`**（注入前、还原后各一次）；`RUN_L1=1 INJECT=1` → **`PASS=18 FAIL=0 BLOCKED=1 rc=0`**，脚本自带 I1/I2 均「注入→FAIL→`cp`+md5→回绿」。
- **A（能力无关契约）**：当前树 `functional/memstream` 已由 `GEM5-022t` 的 `brk` 转 **pass**（我实测 `drv-libc.json` 3/3 pass、`drv-lts.json` Bubblesort pass），C4/C4b 仍绿 ⇒ 断言不再绑定具体能力状态。
- **断言非恒真（我的两次独立注入）**：① libc 驱动 `record.engine="qemu"`（JSON mtime 13:12:29 为新产物）⇒ `FAIL C4 actual=cases=3 engine=qemu`、rc=1；② llvm 驱动同字段（mtime 13:22:30）⇒ `FAIL C4b actual=engine=qemu`、rc=1；`cp`+`md5sum -c … OK` 还原后回 `PASS=12 FAIL=0`。
- **B（位点我逐行看源码核对）**：`__rem_pio2_large.c:303/304/311`（另 `:378/379`）`(int32_t)` ✓；`expm1.c:153` `k = invln2*x ± 0.5`（`int k`）✓；`lgamma_r.c:156` `n = (int)(x*4.0)`、`:255` `i = (int)x` ✓；`llvm-test-suite/SingleSource/Benchmarks/Misc/pi.c:49` `(long int)(iprod/74383)`、`:52` `(long int)(prod/ymod)` ✓。refs+任务书扫描无「gem5 缺陷/单方缺陷」定性（仅存「**不判**「gem5 单方缺陷」」的否定句）。
- **数字复算（我自写脚本、从驱动 JSON 现场统计）**：`qemu 587 / gem5 310 / both 310 / blocked 270 / gem5_only_fail 9 / qemu_only_fail 0`，与摘要逐项一致。**取数时点**：驱动 JSON mtime `2026-11-06 10:16–10:56`（摘要 `04:23:42Z` 由其聚合）；引擎身份我核对属实 —— lock `c8222cc6`（== `manifests/components.lock.toml` == 组件仓 `HEAD~1`）、`components/gem5/series` 97 条、sim.log banner `gem5 25.1.0.1 / compiled Nov 6 01:17:05`。`GEM5-022t` 落地后 blocked 会下降（我实测 memstream 已转 pass），摘要已注明快照性质。
- **L1（要求4）**：我独立 `make check` **rc=2**，去重后失败目标**仅 `check-patch-tree`**、6 条问题行全为 `check-patch-tree: gem5:`（断言⑨⑥，根因 = 并发 `GEM5-022t` 本地提交 `0d811d3` 未导出补丁集）、非 gem5 问题行 **0**、本任务 `components/` 改动 **0**、其余 `总计 88 项 | PASS 88 | FAIL 0` ⇒ BLOCKED 归因机械成立，**不判 Needs Revision**。
- **反例**：C1/C2/C2b/C3 全 PASS（`ET_DYN`/`PT_INTERP` ⇒ `BLOCKED:loader/ELF modality`、`cmd=0` 不启动 gem5，本体亦 `fatal only ET_EXEC`）。

**约束核验**：交付物齐全、驱动仅加 `--engine/--gem5*`/`--jobs`、期望与语料未动 ✓；运行期产物全在仓库外 ✓；完成区无运行期路径 ✓；BLOCKED 不计 PASS ✓。

**非阻断 finding**：① C4/C4b 未校验驱动 `rc`、也未校验 JSON 新鲜度——gem5 不可用时驱动提前退出、脚本会读上一次 JSON 而 C4 单项假绿（我首次注入即撞到；同轮 C2b `rc=126` 仍 FAIL，整脚本不会绿），建议补 `rc==0`/mtime 断言；② 摘要只写聚合时刻，未逐份记录驱动 JSON mtime；③ `gem5_reason` 仍取首行，对 `math/*` 常是被容忍的 `X ` 行。

#### 收尾（architect，2026-11-06）

- 第 1 轮 Needs Revision 的 A/B 已修：C4/C4b 改为能力无关的驱动契约断言；cast 归因改为三处位点并去掉「gem5 单方缺陷」定性（语义归属待用户裁定）。
- 非阻断 finding ①②③ 记遗留：C4 未校验驱动 rc/JSON 新鲜度、摘要未逐份记 mtime、`gem5_reason` 取首行对 math 不精确。
- `GEM5-022t` 已实现 `brk/mmap/mremap`，本册基线数字（blocked 270）为 2026-11-06 快照，后续以 022t 复测为准。
- 判决 Accepted（第 2 轮），状态置 `已验证`。
