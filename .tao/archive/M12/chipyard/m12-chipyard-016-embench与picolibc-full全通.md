# m12-chipyard-016: embench / picolibc-full 在 chipyard Tiny 上全通

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-015`（已完成）
**可并行分片**：否（chipyard 组件单写者；跑批可分节点）
**预估**：6–8 h（runner 改动 2–4 h + 跑批 15–30 min + 报告/注入 1–2 h + 余量）
**状态**：已验证

## 背景与口径（用户 2026-11-14 裁定）

- **M12 不依赖 M13**；**三平台差分是 M13 的事**，本任务**不做**三平台比对。
- **跑在 chipyard Tiny（`WumingTinyConfig` Verilator）上**，不是 qemu-user、不是 qemu-system、也不是 gem5。
- **不收 `tests/inst`**（其迁移归 M13）、**不收 llvm-ts**。
- chipyard Tiny 的 semihosting 由 hmon 的 cfx0 服务提供（`immu18[17:8]==0x3FF`）：`SYS_EXIT` 给出退出码、`SYS_WRITE` 给出输出/markers；`tests/inst` 的 `.S` 套件已长期用它。

## 现状（实测，勿重新推导）

- `tools/testcases/tset/embench/run_embench_e2e.py`：**已能**把 19 个 benchmark（× `-O0/-O2` = 38 例）以 freestanding 方式编到 `dadao-tiny-app.lds`、链接 crt0 + 板级 shim，判据 = **guest 退出码 0**（`main` 返回 `!correct`）；但它**只驱动 `qemu-system-dadao -M dadao-tiny`**（`grep -c chipyard` = 0）。
- `tools/testcases/picolibc_tests.py`：同样**只驱动 qemu-system `dadao-tiny`**（`grep -c chipyard` = 0）。
- `tools/testcases/inst/run_asm_suite.py` 已有 chipyard 调用范式可直接复用：
  `simulator-chipyard.harness-WumingTinyConfig +permissive +loadmem=<elf> +semiout=<out> +max-cycles=<N> +permissive-off none`。

## 目标

1. 给两个 runner 加 **chipyard 引擎**（`--engine chipyard` 或等价开关，复用上述范式；markers/退出码从 `+semiout` 与 semihosting 读）。
2. **embench 全量全通**：19 benchmark × `-O0/-O2` = **38/38**，判据 = guest 退出码 0（+ markers）。
3. **picolibc full 全通**：`picolibc_tests.py --stage full` 在 chipyard 上全绿（现场统计例数，不写死）；对**确实依赖 qemu 专有行为**的用例，逐条记 BLOCKED 并说明，不得静默跳过。
4. 不改 benchmark/测试语义，只加引擎与判据；qemu 通路保持可用（回归）。

## 验收

1. embench **38/38**、picolibc full 全绿（计数现场统计），两者均给出**运行时实际执行的指令/周期量级**（`+max-cycles` 触顶即 FAIL，防"跑不完也绿"）。
2. qemu 通路回归：`check-tset-embench-smoke` 与 `check-picolibc-tests` 仍 rc=0（证明加引擎未破坏旧路径）。
3. 报告落 `.tao/knowledge/refs/m12-016-embench-picolibc.{json,md}`（含每例退出码、markers、墙钟、所用 sim md5）。
4. **≥2 路可达 FAIL 注入**（例：把某 benchmark 的 `verify_benchmark` 改坏 ⇒ 退出码非 0 ⇒ 判红；把 `+max-cycles` 调到极小 ⇒ 触顶红）+ `cp`+md5 还原。
5. Verilator 构建 rc=0；`check-patch-tree` chipyard 段 0 问题。
6. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；chipyard 组件补丁按 `docs/Process-01` 导出。
3. 跑批在**节点**（`--jobs` 用默认 = 核数/2）；跑批前用 `tools/infra/sync_node_artifacts.sh <host>` 核对 sim 与主控机 md5 一致（`ISS-429`）。
4. 构建后必须删 `.classpath_cache/chipyard.jar` 与 `generated-src/<cfg>` 再 `make verilog`（否则静默沿用旧 RTL）。
5. 禁 `git checkout/restore/stash`/`git show <commit>:<path>` 还原；注入还原用 `cp`+md5。
6. 大文件落 `/tmp/opencode/m12-chipyard-016/` 并测完即删；日志 `.work/log/chipyard/<任务ID>-<用途>.log`。

## 待裁定

**A. chipyard harness 的服务号通道（现状 = `rd16`；等用户确认后再决定是否修 §1 措辞/加双通道）**
- **当前实现（实测确认）**：服务号取自 **`rd16`**——`WumingDecoder.scala` 在 `isSemi` 时置 `srcAIdx := 16.U; srcABank := WumingBank.RD`；
  `WumingCore.scala` 用 `semiOp := rf.io.r0Data(7, 0)` 填 `io.semi.req.op`；参数块指针仍取 `rb16`（`rf.io.r2Data`）。
  这与 `contract-semihosting §2`、`Machine-v5 §5.2`、QEMU `common_semi_arg(0)=env->rd[16]` 以及全部 guest 一致。
- **最小证据（A/B 实测，同一 spec 形式 ELF）**：旧的 `inst(7,0)` 通道 ⇒
  `[WumingSemi] ERROR: semihosting op 0x00 is not implemented (pc=0xffffff010160)`、进程 rc=1；
  现在的 `rd16` 通道 ⇒ `[WumingSemi] SYS_EXIT(0x18) reason=0x20026 code=0x7 cycle=1824 -> host exit status 7`。
  两份日志留证在**运行期证据目录**（`<evidence>/work/op-channel/{old-inst-mode,new-rd16}.log`）；证据脚本 B1/B4 每次机械复核。
- **仍未定**：`contract-semihosting §1` 仍写「服务号占 `immu18` 低 8 位（`0x3FF00+op`）」。三种收法待用户选：
  （a）保留 §2 口径、把 §1 该句改为「immu18 只承载 `0x3FF` tag」；（b）双通道（rd16 优先，immu18 低 8 位非 0 时用后者）；
  （c）维持现状不改 spec。**未做任何进一步改动**。

**B. picolibc 判据 = engine parity（用户 2026-11-14 已裁定，✅ 落地）**
- qemu 基线（同一 ELF、`--jobs 62`、360 s 预算）：total 235 / pass 208 / fail 1（`test-math-errhandling` exit 3）/
  excluded 22 / blocked 4（3× `ISS-193` long-double libcall、1× `test-abort-failure` CFX6）⇒ qemu 自己也不「全绿」。
- **判据**：① chipyard vs qemu **逐例状态差集 = 0**；② chipyard 独有失败 = 0；③ qemu 既有缺口登记为清单
  （`run.sh` 的 `QEMU_GAPS`、报告 JSON 的 `qemu_baseline_gaps`），清单多/少/变状态即红。
- 落地位置：`run.sh` D 段（D1–D6）+ `make_report.py`（`CRITERION`/`QEMU_BASELINE_GAPS`/`parity` 块）+ 报告 §0。

**C. 跑批墙钟（现场实测，供复核定档）**
- 仿真吞吐实测：`server208` 32 并发 ≈ **1.75 k cycles/s/例**；`ics180` 18 并发 ≈ **2.8 k**；主控机 62 并发 ≈ 1.7–2.0 k。
- 单例规模实测（`+semiout` 退出行 `cycle=`）：embench **7.0–17.5 M cycles**（aha-mont64 6.96 M / depthconv 10.09 M / ud 11.50 M / nettle-aes 16.38 M / qrduino 17.47 M）；picolibc **26 k–710 k cycles**（最重数学例 >1.5 M）。
- ⇒ 全量 embench 38 例在单节点 62 并发下 ≈ **2–3 h**（瓶颈是单例 17 M cycles）；picolibc 234 例 ≈ **1–1.5 h**（重数学例为主）。

## 完成区

**code freeze（2026-11-14 23:10）**：chipyard 侧**不再改代码**；sim md5 固定为 **`079ae01569e5fbf9fa9944bd6aee89cd`**（含 `SYS_FLEN` 修复）。结果**不跨二进制**：受 `SYS_FLEN` 影响的 picolibc 用例一律用该 sim 复跑；`embench` 批次留在旧 sim `ac35dffb…` 是**唯一允许的例外**（证据见下「sim md5 一致性」）。
**判据（用户 2026-11-14 裁定）= engine parity**：picolibc 与 qemu **逐例状态差集 = 0**、chipyard 独有失败 = 0；qemu 侧既有缺口（1 fail + 4 blocked + 22 excluded）登记在册、**不计到 chipyard**，**不再使用「全绿」一词**。embench 判据 = guest 退出码 0 + 三个 board marker + `+max-cycles` 未触顶 + 批前后 sim md5 一致。
**budget 类口径（用户 2026-11-14）**：host timeout（`cycles=None`、无 guest verdict）**不是用例判决**，记 `blocked (budget: host timeout …)` 并**单列**，**不计入「chipyard 独有失败」**；依据 = 实测吞吐 1.76 k cycles/s/例（`slre(-O2)` 19.60 M / 11140 s）⇒ 4 h 预算 ≈ 25.3 M cycles 上限，超时例即需 >25 M cycles（`-O0` 因代码未优化普遍更慢，`nettle-sha256(-O2)` 实测 25.17 M / 9040 s 为下限参照）；**不放宽** `+max-cycles`、**不改**超时阈值凑绿。
**测试结果**：引擎 / 判据 / 防假绿实测通过（证据脚本 A3+B4+H8 = **15 项 PASS**）；**两项全量数字未收完**（19:15 现场：embench **16/38**、picolibc **75/234**，节点仍在跑，见「批次现场」）。
**修改文件**（12 项，与 `git status -uall` 逐项一致：9 M + 3 ??）：本任务书；`tools/testcases/lib/chipyard_engine.py`（新）；`tools/testcases/picolibc_tests.py`；`tools/testcases/tset/embench/run_embench_e2e.py`；`tests/shared/linker/picolibc-tiny.ld`；`components/chipyard/patches/**` 5 个补丁；`.tao/knowledge/refs/m12-016-embench-picolibc.{json,md}`（新，2 项）。
**验收结果**：① `make verilog` rc=0（先删 `.classpath_cache/chipyard.jar` + `generated-src/<cfg>`）→ `make` rc=0，产物 md5 `ac35dffbc90cef736e5e0788cecb51d2`，**三节点跑批用的就是这个 md5**（生成物 md5：`WumingSemi.cc 68356dc0…`、`WumingSemi.v aeb8dd27…`、`WumingCore.sv 163fb650…`、`TLROM.sv 9752a7a9…`）；② **重导出（2026-11-14 23:0x，共享源树 21:35 被 amend 成「016+002」之后）**：`make_patch.py chipyard` → **`1 written, 20 unchanged`（rc=0）**，`check_patch_tree` → **chipyard 段 0 问题**（整树 rc=1 的 28 项全在 gem5(16)/qemu(12)，均为在途 `m16-gem5-008`/`m13-qemu-011+034` 的共享源树），`--source-state` → **chipyard `OK HEAD=707f0c84facc count=1 clean=True`**，`check-component-changelog` → **PASS（rc=0）**；**注**：导出的 `components/chipyard/patches/**` 现含 `m13-chipyard-002` 的 `sc` 改动（共享源树 21:35 被 amend 为 016+002）。**更正（reviewer 2026-11-15 核实）**：016 的 5 份补丁 = **002 的 5 份 + FLEN 修复**（`WumingCore`/`WumingDecoder`/`WumingSemi.scala`/`WumingSemi.v` 与 002 逐字节相同，`resvWord`/`scCheckFail` 已 0 命中；016 相对 002 的额外改动**只有 FLEN**；`changelog.md` 归 002）——此前「两支补丁集一致、002 合并无新增 hunk」的表述**作废**；`check-patch-tree --source-state` **chipyard OK** `HEAD=12cfdf3c count=1 clean=True`，整树 rc=1 的 22 项**全部在 gem5(12)/qemu(10)**（在途 `m16-gem5-008`/`m13-qemu-011+034` 的共享源树），**chipyard 0 问题**；③ qemu 回归 `check-tset-embench-smoke` **rc=0（165 s）**、`check-picolibc-tests` **rc=0（18 s）**；④ 注入 4 路全可达：改坏 `verify_benchmark` ⇒ 客人退出 1（非 guard）FAIL、`+max-cycles=2000` ⇒ 触顶 FAIL（理由含 `max-cycles`）、假 baseline md5 ⇒ `binary changed before the run` FAIL、内置 `--inject` 反例 PASS；还原用 `cp` + md5 对账（`f9e93249…` 前后一致）后**回绿**。
**批次现场**（节点 / 并行度 / 起止 / 墙钟 / sim md5，全部 `ac35dffb…`）：embench `server208` jobs=32 `16:07`→跑中；`ics180` jobs=18、`ics160` jobs=20 均 `17:16`→跑中；picolibc-chipyard `ics150` **两池共享队列**（池 A jobs=20 `18:26`→跑中；池 B jobs=18 `19:2x`→跑中，逐例 `.claim`/`.done` + `_elf_running` 认领，互不双写）；`ics170` **池 D** jobs=19 `19:46`→跑中（**不是重复池**：重跑 ics150 上撞 2400 s 预算、判 `blocked(host timeout)` 的 19 例长尾）+ 用户起的 `test-memmem` 单例（jobs=1）；**冻结声明（给 `m13-chipyard-002` 的开工资格）**：**自 2026-11-14 20:51（+08:00）起，本任务不再主动启动任何新用例进程**，19 个 `-O0` 已全部在跑（`server208` 18 例 + `ics170` 1 例 `xgboost-O0`，后者独立批次 PID 682670 / `-embench-o0xg.json`）⇒ **此后可安全重编 `simulator-chipyard.harness-WumingTinyConfig`**。唯一残留：`server208` 夜跑批次队列里还剩 1 个**自动**任务（同 `xgboost-O0`；仅在 18 槽有释放时自动起）——若它在重建之后才起会撞 md5 guard 并记 `guard:`（非用例判决、不作判据），该例一律以 `ics170` 批次为准。`server208` **`-O0` 夜跑窗口** jobs=18 `20:46`→跑中（`--opt O0 --timeout 43200`，JSON `-embench-o0night.json`，PID 1100018；12 h 内不够的例记 `blocked(budget: 12h)` 单列，不再自行延长）；`server207` **池 F** jobs=62 `19:54`→跑中（`--only` **在途集 164 例** = `235 − 71 终态`，与 ics150/ics170 **跨节点重复跑同一例**，各自本地目录独立、union 取先到终态）；`server207` **池 E**（jobs=40 `19:50`）**已停**——它确实重复：跨节点不共享 `.done`，所以在全新节点上重跑了 ics150 已完成的例（实测 43 例结果后停，3 min）。picolibc-qemu 基线 主控机 jobs=62 `17:43`→`17:51`（8 min，235 例）。**并行度偏离**：picolibc 首轮本地 jobs=16（旧规则下自拟）已作废；现按配额（208=32、ics150=20、ics* 余者 18/20）；**本批之后不再起本地跑批**。
**每例证据结构（可抽查，reviewer 不必重跑全量）**：报告 JSON 的 `cases[]` 逐例带 `status` / `rc`（guest 退出码）/ `cycles` / `semi_out`（`<节点>:<运行期路径>`）/ `sim_log` / `sim_md5` / `shard`（哪个分片/节点）；`make_report.py` 从原始 JSON+分片日志 **union 去重**（同例只计一次，优先已完成）重算全部汇总；`collect.sh` 把逐例 `semi.out`/`sim.log` 回传到 `.work/log/chipyard/m12-chipyard-016-cases/<node>/`（现 76 个 embench + 93 个 picolibc）⇒ 抽查 = 挑 3–5 例比 `semi.out`/`sim.log` 与 JSON 的 `rc`/`cycles` + 重算汇总 + 验 md5。
**新发现/坑（规则修正）**：⓪ **节点侧未提交文件不得靠 `reset --hard`/`clean -x` 收尾**（本轮事故：`m13-testcases-040` 同步 `server208` 时 reset+clean，抹掉了该节点上未提交的 `tools/testcases/lib/chipyard_engine.py` 与两个 runner 的本地改动；`.work/` 因 gitignore 幸存、**正在跑的 Python 进程因已加载不受影响**，但**新起的批会缺文件**）。后续同步一律 bundle / 临时 worktree + `cp`，并在同步后逐件 md5 核对；① **节点配额作废 ⇒ 有空位就发**（AGENTS 2026-11-14 `43ab120a`）；② **长批启动前必须算「待跑例数 ÷ 池深 = 波数」**，波数 > 1 就跨节点分片（本任务的实测教训：picolibc 234 例 × 单例 20–60 min 在 20 深度下波数 ≈ 8，导致 19 例撞 2400 s 预算被判 blocked，后在 `ics170` 用 19 并发的专用重跑池修掉）；③ **每 ~15 分钟核一次节点负载**（`tools/infra/nodetop.py --once`），有空闲节点就迁移队列；④ 多池共享同一队列时靠**逐例原子认领**（`.claim` O_EXCL + `.done` 带 sim md5 + `_elf_running` 扫 `/proc`）避免双写；⑤ **判断「是否还有排队」必须用 `cases − run 目录 − EXCLUDED`**，不能拿 qemu 总例数减目录数（本任务 235 = 226 run + 5 EXCLUDED + 3 blocked(ISS-193) + 1 memmem，实际零排队）；⑥ **跨节点不共享 `.done`**：新节点上的池会重跑别的节点已完成的例（池 E 实例），要么先 rsync `.done`/结果 JSON，要么按 `--only` 精确分片；⑧ **重复跑的允许/禁止口径**：**允许**不同节点重复跑同一例（节点本地目录独立、无写冲突，union 取先到终态）；**禁止**同一节点上两个池跑同一例（共享 `picolibc-tests` meson build dir + 同一 `+semiout` 路径）。⑨ **判「在途/排队」= `cases − 已有终态结果`**（不是 `cases − run 目录`：目录数会被历史轮次与本机探针污染）；本任务现场 235 − 71（48 pass + 19 excluded + 3 ISS-193 blocked + 1 memmem） = **164 在途**。⑦ picolibc 的 5 例（thread-safety/tls/tls-no-flash/semihost-system/semihost-system-failure）在 runner 的 `EXCLUDED` 表里——**不做仿真**，两池都只花毫秒判 `excluded`。
**sim md5 一致性（现场 grep，不猜）**：受影响集 = picolibc 里 sim.log 出现 `SYS_FLEN`/`SYS_SEEK`/`SYS_READ`/`SYS_OPEN`/`SYS_REMOVE`/`SYS_RENAME` 的 **30 例**（`semihost-close/errno/exit-extended/-failure/flen/iserror/istty/open/read/remove/rename/seek`、`test-dprintf/fflush/fgetc/fgets-eof/fopen/fread-fwrite/freopen/getdate/grp/mktemp/posix-io/pwd/rename/setvbuf/stat/tmpnam/ungetc-ftell/wchar`），重跑于 `ics160`（`--chipyard …/sim-079ae015-WumingTinyConfig`、独立 `--work-dir picolibc-flenz-run`、JSON `-chipyard-zflen.json`）：**29/30 已 pass（新 sim）**，剩 `test-fread-fwrite` 仍在跑（完成即进同一 JSON，报告断言随之转真）；**embench 不触发的证据**：① 静态 —— `grep -rn "fopen|fseek|ftell|SYS_FLEN|SYS_OPEN"` 在 embench 语料/`examples/dadao/boardsupport.c`/`embench_runtime.c`/`dadao_mem_runtime.ll` **零命中**，且 `embench_runtime.c` 无任何 stdio 符号；② 动态 —— 全部已完成 embench 例的 `sim.log` 里只出现 `SYS_WRITE0` 与 `SYS_EXIT`（无 FLEN/SEEK/OPEN/READ）。
**报告断言**：每例带 `sim_md5`；`sim_md5_consistency.flen_affected_all_on_current_sim` 必须为真；`embench` 与**不触发**该路径的 picolibc 例允许留在旧 md5（唯一例外，附上述证据）。
**engine parity 现场（23:2x union）**：picolibc `pass 127 / fail 1（`test-math-errhandling`，qemu 同样 fail = 登记缺口）/ excluded 22 / blocked 85（81 条 host timeout 待重跑 + 3 条 ISS-193 + 1 条 memmem）`；**逐例状态差集 = 0、chipyard 独有失败 = 0、qemu 缺口登记 5/5 匹配**；embench `pass 32 / pending 6`（`-O0` 夜跑窗口内，`budget 0`）。
**合并交接（reviewer 2026-11-15 核实，须照此合并）**：先合 016、再合 002 会在 **`WumingSemi.cc.patch` 产生 3 处冲突**（因为 002 不含 FLEN 修复）⇒ **冲突时一律取 016 侧**，否则会把 FLEN 修复回退掉；其余 4 份补丁两侧逐字节相同，直接取任一侧即可；`components/chipyard/changelog.md` 归 002。
**审查返工（reviewer 2026-11-15 Needs Revision）**：① 任务书 4 条具体 `.work/**` 引用改为「运行期证据/日志目录」与 `<evidence>` 占位形，`make check-knowledge-refs` 回到 **rc=0**（`0 具体引用 / 0 悬空`）；② 证据脚本 C1 改为**现场统计**断言 `cases_seen == 38`（原 `38 − len()` 恒真）、C5 改为断言 `len(set(sim_md5)) == 1` 并打印该 md5（原只判非空）；可达 FAIL 已验：注掉一条 md5 后集合大小变 2。重跑 `run.sh` **rc=1**（19 passed / 3 failed：C1「32≠38」与 D6「budget 80」为数据未到，属预期）、`run.sh --inject` **rc=1**（27 passed / 3 failed，H1–H8 全 PASS）。
**可合入**：代码与补丁已定稿（无待改项）；`-O0` 夜跑与 picolibc 重跑池只是**数据补齐**，不改代码，可与合并并行进行；合入后按 `make_report.py` 重算即可得到最终计数。
**遗留问题**：① 两批全量未收完 —— 收尾 = 等节点批次自然结束 →把各分片 JSON （`m12-chipyard-016-embench*.json` / `…-picolibc-chipyard*.json`）拷回**运行期日志目录** → 跑**运行期证据目录**里的 `make_report.py`（自动 union 分片、可重算）→ 跑 `TASK_WT=<worktree> bash <evidence>/run.sh`；实测吞吐 1.75–2.8 k cycles/s/例、单例 7.0–17.5 M cycles ⇒ 全量 embench ≈ 2–3 h、picolibc ≈ 1–1.5 h；② `picolibc_tests.py` 的 `DEFAULT_JOBS` 写死 8 属 `ISS-439`，**未动**；③ `test-memmem` 单列未跑（需 >1 h）。

## 越界改动与必要性（用户 2026-11-14 要求逐条披露）

> 名义范围是「加 chipyard 引擎」。实测发现**不加下面这些，判据根本达不到**；逐条给「改什么 / 不做会怎样（实测）/ 是否改架构语义 / 是否已重导出并重生成 RTL」。

1. **`WumingCore.scala`**：① semihosting 服务号改从 **`rd16`** 取（原 `inst(7,0)`），并把核内 `cycles` 随请求上送（退出行多一个 `cycle=`，供周期证据）；② 不做则**全部合同 guest 立刻失败**：`[WumingSemi] ERROR: semihosting op 0x00 is not implemented` rc=1（实测 `t_spec.elf`、crc32 e2e、picolibc 全 235 例）；③ **是**（服务号来源）⇒ 见「待裁定 A」，已按 contract-semihosting §2 / Machine-v5 §5.2 / QEMU 对齐；④ 已重导出 + 删 jar/`generated-src` 重生成（sim md5 见上）。
2. **`WumingDecoder.scala`**：① 给 semihosting `trap` 增加 `rd16` 读口（r0 端口，trap 无源操作数）；② 不做则 ①无从取值（同 1 的失败现象）；③ 否（只加读口，不改译码语义）；④ 同上。
3. **`WumingSemi.cc`**：① 服务集 5 → 24（open/close/writec/write0/write/read/readc/iserror/istty/seek/flen/tmpnam/remove/rename/clock/time/system/errno/get_cmdline/exit/synccache/exit_extended/elapsed/tickfreq），语义逐条对齐 QEMU `semihosting/arm-compat-semi.c`；`SYS_HEAPINFO` 仍**不实现**（无用例、不编造值，显式报错）；② 不做则 picolibc 在 `SYS_OPEN` 处 rc=1（实测 `semihosting op 0x01 is not implemented`），argv/stdio/tmpnam 类例全灭；③ 否（服务表是 spec §5.3 的 25 服务，实现抄 QEMU 同语义；**没有**为了让用例过而放宽任何期望值）；④ 同上。**另**：23:0x 修 `SYS_FLEN` —— 原实现 `fseek(END)` 后未复位文件位置，调用方紧接着的 `SYS_READ` 读到 0 字节；picolibc 的 `:semihosting-features` 探针因此丢了 4 字节 magic，把 `semihost-exit-extended`/`-failure` 自跳过（exit 77），与 qemu 产生 2 例 parity 差；改为 fstat 语义（`ftell` 保存→`fseek END`→`ftell`→复位），重编后 2 例 **pass**（复跑 5 例 5/5 pass，sim md5 `079ae015…`），**parity 差回到 0**；此修复只在与 qemu 同语义方向收敛，未放宽任何判据。
4. **`WumingSemi.v` / `WumingSemi.scala`**：① 新增 guest 内存**写通道**（TL `Put` + `mem_write/mem_wdata`，C++ 侧整字合并 + 大端/位序与读路径互逆）与 `+semicmdline=` 选参；② 不做则 `SYS_GET_CMDLINE`/`TMPNAM`/`READ`/`ELAPSED` 无法回写 guest（实测 argv 例 `cmdline` 乱序/失败）；③ 否（同一 TL client、读路径不变、写只用于应答者回写参数块）；④ 同上。
5. **`tests/shared/linker/picolibc-tiny.ld`**：① `.stack` 由 `:ram` 改 `:NONE`（不再并入唯一 `PT_LOAD`）；② 不做则每个 picolibc ELF 的 `memsz=8.2 MiB`（`filesz` 仅 2.7 KiB），`+loadmem` 要流 **1,031,788 个字** ⇒ 实测**单例 240 s 仍未起跑**；改后同一 ELF 只流 340 字（8 s 级）；③ 否（stack 写后读、RAM 起始为零；qemu 侧同一 ELF 逐例状态不变，见 D 段 parity）；④ 不涉 RTL。
6. **两个 runner**：`--engine {qemu,chipyard}`（默认 qemu，旧通路不变）、`--jobs`（embench 新增，原来串行）、`--skip` 与逐例进度行（可观测）、`--only`（分片）、chipyard 判据（guest 退出码 + 三 marker + `+max-cycles` 触顶 FAIL + 跑批前后 sim md5 一致）、`chipyard_engine.py` 复用 `writer_guard`（若该文件存在则本模块的 md5 检查自动让位，避免第二套护栏）。

## 审阅记录
### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 chipyard harness 服务号取自 `immu18[7:0]`，与 contract-semihosting §2 / QEMU / 全部 guest 不符 ⇒ 合同 guest 一律 rc=1 | ✅已修（语义变更，已登记「待裁定 A」） | `WumingCore`/`WumingDecoder` 改取 `rd16` | 证据脚本 B1：spec 形式 guest（`trap cfx0,0x3FF00` + op 在 rd16）退出 7；B3 退出行带 `cycle=1824` |
| F2 服务集只有 5 个 ⇒ picolibc 的 open/seek/tmpnam/argv 类例必挂 | ✅已修 | `WumingSemi.cc` 5→24 服务（语义抄 QEMU arm-compat-semi） | `picolibc --only semihost-exit,semihost-get-cmdline,semihost-argv,semihost-istty,basename,test-hello` ⇒ 6/6 pass（chipyard） |
| F3 应答者不能写 guest 内存 ⇒ `SYS_GET_CMDLINE`/`TMPNAM`/`READ` 无法回写 | ✅已修 | `WumingSemi.v`/`.scala` 加 TL `Put` + `mem_write/mem_wdata`，C++ 侧整字 + 位序互逆 | 同 F2 的 `semihost-get-cmdline`/`semihost-argv` pass（回写内容逐字节正确） |
| F4 大端/位序：首次实现写回后 cmdline 变成「按 8 字节倒序」 | ✅已修 | `ask_write()` 增 lane 交换（与读路径 `Cat(tl.d.data(8i+7,8i))` 互逆） | 改前 `cmdline -margorpleh emandlrow ol…`；改后 `semihost-get-cmdline` pass |
| F5 分段状态机重入 bug：`SYS_READ`/`TMPNAM`/`ELAPSED`/`GET_CMDLINE` 在内存请求返回后重置写游标 ⇒ 死循环 | ✅已修 | 每个写突发服务把「准备工作」与「可恢复写」拆成独立 `sub` 段（`S.sub` 先推进再发起写） | 改前 `semihost-get-cmdline` 卡在首次 `SYS_GET_CMDLINE` 240 s 无退出；改后 pass（53k–122k cycles） |
| F6 picolibc ELF 的唯一 `PT_LOAD` 覆盖 8.2 MiB（`.stack` 在段内）⇒ `+loadmem` 流 103 万个字，单例 240 s 仍未起跑 | ✅已修 | `picolibc-tiny.ld`：`.stack` 改 `:NONE` | 改前 `+loadmem … loaded 8257024 byte(s)`/`1032128 write`；改后 `4840 byte(s)`/`340 write`，8 s 起跑 |
| F7 「零字省略」优化把被 RANDOMIZE 的 SRAM 当零 ⇒ 读回校验失败（自造风险） | ✅已回退 | 复原 `WumingLoadMem.cc`（`git hash-object` = 补丁 `index 5a3e96c`） | 回退后 `stream: 372 write` 且无 readback mismatch |
| F8 引擎的 `LD_LIBRARY_PATH` 依赖构建机 rpath ⇒ 节点上 rc=127 全灭 | ✅已修 | `chipyard_engine.run()` 用模块自身 repo 根注入 `default_env()`（`_REPO` 少算一层的 off-by-one 一并修正） | 修前 ics150 全 `blocked … rc=127`；修后 ics150 4 例 probe 4/4 pass |
| F9 与 `m13-infra-003` 的 `writer_guard` 判据重叠 | ✅已收口 | `enforce_sim_md5()`：检测到 `tools/infra/writer_guard.py` 存在即让位（复用优先，不造第二套） | `_shared_guard_available()` 在本基线返回 False ⇒ 本模块检查生效；合入后自动让位 |
| F10 并行度：首轮 picolibc 用 `--jobs 16`（违反当时规则） | ✅已纠正（披露） | 后续一律 62/38/20（按配额）；不再本地起批 | 完成区「批次现场」记录每批节点+并行度+起止+md5 |
| F11 判据「picolibc 全绿」不可达（qemu 基线亦 1 fail + 4 blocked） | ⏸延后（语义裁定） | 改判据为 engine parity，登记「待裁定 B」 | qemu 基线 `pass=208 fail=1 blocked=4 excluded=22`（jobs 62） |
| F12 两批全量未收完（embench 9/38、picolibc 58/234） | ⏸延后（长跑批归主会话监督） | 节点批次继续跑；报告生成器已支持 union 分片 + 从运行日志解析部分结果 | 完成区「遗留问题」给收尾命令与实测速率推算 |

### 第 1 轮 reviewer 验收（2026-11-15，全部由 reviewer 亲自重跑）

**判决：Needs Revision**（2 项阻断，均为小修；判据三条 / 代码 / 补丁成立，数据项不阻断）

**重跑记录**
- md5：现场 sim = `079ae01569e5fbf9fa9944bd6aee89cd` = 报告 `code_freeze.chipyard_sim_md5` ✅；ics160 **只读**核验 `sim-079ae015-…` 同 md5，zflen 进程 PID 844630 命令行 `--chipyard …sim-079ae015…` 仍在跑 `test-fread-fwrite`（JSON 未落）。
- 报告确定性：`make_report.py` 两次重生成 + 已提交件三者逐字节相同（json `e7787ea7…`、md `71923389…`）✅
- D3/D4/D5：reviewer **自写 union 脚本独立重算**（不走 make_report）⇒ differing=0、chipyard_only_failures=0、gaps 5/5、budget=81（80 host-timeout + memmem）；chipyard 127/1/22/85、qemu 208/1/4/22，与报告逐项一致 ✅
- `run.sh` 默认：rc=1，20 PASS / 3 FAIL（C2 32≠38、C3 pending 6、D6 budget 81）＝数据未收完；D1–D5、E3a/b/c 全 PASS
- `run.sh --inject`：28 PASS / 3 FAIL，H1–H8 全 PASS（注入→FAIL→cp+md5 还原→回绿，md5 `f9e93249…` 一致）
- reviewer 独立注入①（临时树，未碰真数据）：chipyard pass→fail ⇒ D3=1/D4=1；qemu 缺口例 fail→pass ⇒ D5 4/5；qemu pass→blocked ⇒ D3=1；还原后 0/0/5，真输入 md5 `b5b07aa8…`/`2bd8e09a…` 未变
- reviewer 独立注入②（被测产物）：`chipyard_engine.py` 把 `exit=obs["guest_exit"]` 改成 `exit=0` ⇒ H2/H3 转红；`cp`+md5 还原（`45c580d5…`）后回绿 28 PASS
- 抽检 5 例本地复跑（079ae015）：`semihost-flen` 98024/exit0、`semihost-exit-extended` 77823/exit0、`test-hello` 53523/exit0（＝旧 sim 记录）、`test-math-errhandling` fail rc=3 cyc=4871291（＝批次记录）、`aha-mont64-O2` PASS 6959558（＝ac35dff 记录）⇒ rc/cycles 全对上
- 回归/门控：`check-tset-embench-smoke` rc=0(17s)、`check-picolibc-tests` rc=0(31s)、`check-component-changelog` rc=0、`check-patch-tree` **chipyard 段 0 问题**（整树 51 项全在 gem5 16 / linux 23 / qemu 12，在途任务漂移）
- SYS_FLEN A/B（同一 ELF）：旧 sim `FLEN→5` 后 `READ→0x4`（＝4 字节未读，位置停在 EOF）⇒ magic 校验失败 ⇒ `exit 77` 自跳过；新 sim `READ→0x0`（全读成功）⇒ `SYS_EXIT_EXTENDED` ⇒ exit 0 ＝ qemu 同状态；补丁＝`ftell 存 → SEEK_END → ftell → 复位`，长度＝文件大小且**不改文件位置** ✅
- embench 不依赖 SYS_FLEN：静态 grep（fopen/fseek/ftell/fread/fwrite/SYS_FLEN/OPEN/READ/SEEK）于 `support/ examples/dadao/ src/ embench_runtime.c dadao_mem_runtime.ll` **0 命中**；76 份 sim.log 仅 `SYS_EXIT(32)` / `SYS_WRITE0(330)`；新 sim 上 cycles 逐字相同 ⇒ **未找到反例** ✅
- 补丁超集：016 的 5 份 ＝ 002 的 5 份 + FLEN 修复（4 份与 002 逐字节相同；`resvWord`/`scCheckFail` 6→0 ⇒ 已含 002 的 sc 改动）；016 相对 002 的额外改动**只有 FLEN**；changelog 归 002

**阻断（返工必改）**
1. `make check-knowledge-refs` **rc=2**：4 条具体 `.work/**` 引用全部由本任务书新增（`:58`、`:90`×3，其中 `:90` 在完成区）⇒ 违 AGENTS「具体 `.work/**` 一律 FAIL」**且**违验收 6「完成区…无运行期路径」。改法：按 2026-11-08 裁定改「运行期…」措辞，改后该门控须 rc=0。
2. 证据脚本两条断言不达「可达 FAIL」：**C1 恒真**（make_report 中 `pending=38−len` ⇒ `T+PEND` 恒 38，永不可能红）；**C5 断言弱于标签**（标签「整批只有一份 sim md5」，实际只判非空，两份 md5 也 PASS）。改法：C1 改判 `len(cases)==38`，C5 改 `len(sim_md5)==1`。

**数据待补齐（不阻断，合入后复验）**：embench pending 6（O0 夜跑）、budget 81（重跑池收敛）、`test-fread-fwrite`（ics160 在跑）⇒ `flen_affected_all_on_current_sim=false` 与 C2/C3/D6 届时转真；另 picolibc `rc` 230/235 为 null、embench `markers` 全 null（验收 3 字段，待分片 JSON 收回）、报告 §3 `sim md5 None`（`pic()` 未透传）、§0.1 例外文案写死需随数据校正。
**可合入依据**：code freeze md5 一致 ＋ D3/D4/D5 独立重算成立 ＋ 抽检 5 例 rc/cycles 全对 ＋ FLEN A/B 成立 ＋ 越界/补丁树/回归门控全过 ⇒ 与「数据补齐即收口」一致。
**对账**：`git status -uall` 12 项（9 M＋3 ??）＝完成区「修改文件」；`spec/`、`contracts/`、`tests/inst/**` 未动；reviewer 注入前后快照逐行相同、无残留。
**合并建议（修正完成区）**：先 016 后 002 可行，但 `WumingSemi.cc.patch` 三方合并有 **3 处冲突**（002 无 FLEN），解法唯一＝取 016 侧；完成区「两支补丁集一致、002 合并无新增 hunk」已过时。

### 第 2 轮 reviewer 验收（2026-11-15，返工 `cff9560c`，全部由 reviewer 亲自重跑）

**判决：Accepted**（两项阻断均经复验解除；数据项按用户 2026-11-15 口径不阻断，合入后补齐即收口）
- **阻断 1 解除**：`make check-knowledge-refs` **rc=0**（`0 具体 .work/** 引用 / 0 悬空`）；任务书 `grep -n "\.work/"` 仅剩占位与转述形（`:47 <任务ID>`、`:84 <node>`、`:85 裸 .work/`、`:90 glob 转述），完成区 16 行内无具体运行期路径。
- **阻断 2（C1）**：`make_report` 新增 `cases_seen=len(cases)`，C1 断言 `cases_seen==38`；默认态实跑 **`[FAIL] C1 … expected=38 actual=32`** ⇒ 真值断言、当前即红（原恒真已消）。
- **阻断 2（C5）**：新实现 `len(set(sim_md5))==1` 并打印该 md5；**reviewer 注入**（`cp`+md5 `83de056a…`）塞入第二条 md5 ⇒ **`[FAIL] C5 … expected=1 actual=2`**；还原 md5 一致、`git status` 干净，重跑 C5 回 PASS。
- **脚本 rc**：默认 `rc=1`＝19 PASS / 3 FAIL（仅 C1 32≠38、C2 32≠38、D6 budget 80＝数据未到）；`--inject` `rc=1`＝27 PASS / 3 FAIL，**H1–H8 全 PASS**（H4 还原 md5 `f9e93249…` 一致）。
- **合并交接核实**：4 份补丁 016/002 **md5 逐字节相同**；`WumingSemi.cc.patch` 016＝002＋FLEN（diff 仅 14 行，002 侧独有 3 行全是旧 `fseek` 与 `index`/`@@` 头）；三路合并 5 CLEAN ＋ 该文件 3 冲突、**theirs 独有行 0** ⇒ 取 016 侧不丢 002 任何改动；`changelog.md` 归 002 且合并 CLEAN。完成区交接文本与实测一致。
- **数据/对账**：`flen_affected_all_on_current_sim=True`（zflen JSON 30/30 全 `079ae015`：29 pass ＋ 1 host timeout）；reviewer 独立重算 union 235＝128/1/22/84 ⇒ **D3=0、D4=0、D5=5/5、budget=80** 与报告逐项一致；`cff9560c` 恰 12 文件、无越界，`git status -uall` 干净。
- **新发现（不阻断，收尾一并处理）**：① `flen_affected_all_on_current_sim` 只统计非空 md5——`test-fread-fwrite` 因主池 log 行（`sim_md5=None`、2400 s timeout）在 union 中盖掉 zflen 的 CUR 行而被排除在断言外（底层事实已核真），建议把「flen 例 md5 为空」也判红；② 完成区「29/30 仍在跑」「engine parity 现场 127/85/81」仍是 23:2x 快照，与现报告 128/84/80 不符；③ picolibc `rc` 89/235、embench `markers` 0/32 仍待分片 JSON 收回（沿用第 1 轮结论）。
