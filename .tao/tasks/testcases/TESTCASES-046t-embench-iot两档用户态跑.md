# TESTCASES-046t: Embench-IoT 两档用户态跑（静态档 → 动态档）

**模块**：testcases
**项目里程碑**：M8
**依赖**：`QEMU-062t`（`qemu-user` 的 DADAO 后端，**`已验证`**；`qemu-dadao` 已装进安装根 `paths.host_toolchain_bin()`）；`INFRA-082t`（`P1` musl 静态，**`已验证`**；产 `crt1.o` + `libc.a`）、`INFRA-085t`（`P2` 动态，**`已验证`**；产 `libc.so` + `ld-musl-dadao.so.1`）；`TESTCASES-039t`（Embench 移植 + 系统模式 runner `tools/integ/run_embench_e2e.py`，M6 起 38/38）；`ISS-247`（**链接基址口径**：不得用 `tests/scripts/dadao.lds`）、`ISS-246`（**known-fail 唯一依据**）、`ADR-0025`（`D2` 无内核 / `D6` 路线 / `D7` golden 对照归 `P4`）、`ISS-229`（重建 / 门控**串行**）、`ISS-210`（安装根新鲜度）；**同批三册**：`TESTCASES-046t`（本册）/ `TESTCASES-047t`（`libc-test`）/ `TESTCASES-048t`（`llvm-test-suite`）⇒ **同改共享文件（`Makefile` / `milestones.md`）⇒ 串行**，禁并行。
**状态**：待开始

> **阶段进度**：静态档 ✅ 38/38 pass / 动态档 ✅ 38/38 pass（**终局复跑（新工具链产物）**，`INFRA-079t` 后端改动 + 22:44 重建 `libc.a`/`libc.so` 后；逐例与上次作数零变化；`ISS-258` 已处置：`libc.so` 重装 + L1 产物新鲜度门控）

> **编号（现场取号，2026-10-17）**：`.tao/tasks/testcases/` 现存最大 = `TESTCASES-045t`（现场 `ls`：`044t` / `045t`）⇒ 取 **`046`**；`git log --all --name-only | grep -E 'TESTCASES-04[678]'` **0 命中**（全历史复核）。

## 立项来源 / 用户裁定（原话逐字引录，渠道 = 经主会话问答）

- **2026-10-15**：「**不用改D6，就按原来的顺序进行，然后增加embench和两个新的test suite的测试；测试的时候区分静态链接和动态链接，先测静态链接，再测动态链接**」⇒ ① 三套测试（`embench-iot` / `libc-test` / `llvm-test-suite`）都要跑；② **区分静态 / 动态**；③ **先静态、后动态**（口径 = 串联两轮，不是二选一）。
- **2026-10-17**：「**静态和动态都需要支持**」⇒ `P3` 两档已由 `QEMU-062t` 交付（`已验证`）⇒ 本册 = 在该运行环境上**跑真实测试集**。
- **本册边界来源（用户既定点）**：判据 = 与 `RISC-V + musl` golden 对照归 **`P4`**（`ADR-0025 D7`）⇒ **本册不做对照** ✗（见「判据边界」）。

## 目标（两轮，顺序固定：静态档 → 动态档）

1. **第 1 轮 = 静态档**：`embench-iot` 全部基准按 **musl 静态**（`crt1.o` + `libc.a`）编链，在 **`qemu-dadao`** 上跑，判定 = guest 进程退出码。
2. **第 2 轮 = 动态档**：同一批基准按 **musl 动态**（`-dynamic-linker /lib/ld-musl-dadao.so.1` + `-lc` 取 `libc.so`）编链，同法跑、同法判定。
3. **两档各自产出**：逐例结果 + **失败分类** + `excluded` 逐条理由 + 覆盖边界声明 + 一键证据脚本（含**可达 FAIL**）。
4. **不回归**：既有**系统模式** runner（`tools/integ/run_embench_e2e.py`，`-T dadao.lds` + `qemu-system-dadao -M dadao-m1` + 半主机运行时）**默认行为不变**，重跑仍 **38/38**（M6/L3 既有门控）。

## 已核事实（本笔现场；执行时只作复核，不重复查证）

| 项 | 现场值（2026-10-17） |
|---|---|
| 基准目录 | `.work/source/<embench-iot>/src/` = **19** 个基准（`ls \| wc -l`）：`aha-mont64 crc32 depthconv edn huffbench matmult-int md5sum nettle-aes nettle-sha256 nsichneu picojpeg qrduino sglib-combined slre statemate tarfind ud wikisort xgboost` |
| 每档规模 | 19 基准 × `{-O0,-O2}` = **38 例/档**（与既有系统模式 38/38 同数，**执行期现场派生、不写死**） |
| 既有 runner | `tools/integ/run_embench_e2e.py`（编译 `support/{main,beebsc}.c` + `examples/dadao/boardsupport.c` + `src/<bench>/*.c`；`-T tests/scripts/dadao.lds`；`qemu-system-dadao -M dadao-m1`） |
| 板级钩子 | 框架只要求 `initialise_board` / `start_trigger` / `stop_trigger`（`support/support.h`）；现 DADAO 版（`examples/dadao/boardsupport.c`，属组件补丁集）用**半主机** `SYS_WRITE0` 打标记 ⇒ **user 模式不可用**（`qemu-dadao` 只认 `rd15` 号表的 `umon` 入口，无半主机通道） |
| 判定通道 | `support/main.c` = `return (!correct)` ⇒ **退出码 0 ⇔ 基准自校验通过**（`verify_benchmark` 在用例内，天然独立于 LLVM/QEMU） |
| 静态档产物 | `.work/source/<musl>/lib/{crt1.o,libc.a}`（`P1`；`libc.a` 在 **13:49** 批次） |
| 动态档产物 | 同目录 `libc.so` + 安装根/目标 sysroot `lib/ld-musl-dadao.so.1`（`P2`/`QEMU-062t` 已用） |
| 运行器 | `paths.host_toolchain_bin()/qemu-dadao`（`QEMU-062t` 落地；`-L <guest-root>` 走 `PT_INTERP`） |
| 组件树 | `.work/source/<embench-iot>` = **组件补丁集**（`HEAD` 主题 `dadao: embench-iot patch series`）⇒ **只读**（本册**不改** `components/embench-iot/**`） |

## 链接与运行口径（自包含；`<...>` 为占位）

- **基址**：**一律 lld 默认基址**，**禁** `-T tests/scripts/dadao.lds`。依据 = `ISS-247` 现场：`dadao.lds` 的 `RAM ORIGIN = 0xFC00_0000_0000` 超出 47 位宿主用户 VA ⇒ `qemu-user` 报 `Unable to find a guest_base to satisfy all guest address mapping requirements`（`probe_guest-base.c` 只向上搜索，不搜负平移）。验收须给出「产物 `PT_LOAD` 最低地址 ≠ `0xFC00…`」的现场证据。
- **头文件**：musl 口径，与 `tools/infra/build_musl.py` / `tools/testcases/run_suite.py` 同集合（`arch/dadao`、`arch/generic`、`obj/src/internal`、`src/include`、`src/internal`、`obj/include`、`include`，配合 `-nostdinc`）＋ Embench 侧 `-I <src>/support -I <src>/examples/dadao`。
- **板级 shim**：为 user 模式新增**本仓**的 hosted 板级实现（建议 `tests/scripts/embench_user_boardsupport.c`，提供同名三钩子，标记经 musl `write`/`printf` 落到 stdout 或**不输出**）；**不得**修改 `.work/source/<embench-iot>/**`、**不得**改 `components/embench-iot/**`（若确需改组件补丁 ⇒ 先停下报告并说明 `check-patch-tree` 计数影响）。
- **静态档**：`clang --target=dadao-unknown-elf -<O> -nostdinc <musl 头> -c <每 TU>` ⇒ `ld.lld -o <b>.elf <musl>/lib/crt1.o <objs> -L <musl>/lib -lc` ⇒ `qemu-dadao <b>.elf`。
- **动态档**：同编译段；`ld.lld -o <b>.elf <musl>/lib/crt1.o <objs> -L <musl>/lib -lc -dynamic-linker /lib/ld-musl-dadao.so.1` ⇒ `qemu-dadao -L <target-sysroot> <b>.elf`。
- **驱动**：`--link-mode static|dynamic` 显式二选一（**无默认歧义**）；两档 **顺序执行**（先 static 全量跑完并落报告，再 dynamic）；单例 `timeout`（默认 60 s，可调，`124` 判 `blocked`）。
- **编译参数**：沿用既有 `-DWARMUP_HEAT=1 -DGLOBAL_SCALE_FACTOR=1 -ffreestanding -fno-builtin` 的**语义**；user 模式为 hosted，`-ffreestanding/-fno-builtin` 是否保留由工程师按「不改变基准工作负载」判定并写入报告（改了就说，不隐式改）。

## 失败分类（计数一律运行期派生，禁写死）

| 类 | 定义 | 判定后果 |
|---|---|---|
| `pass` | 编链成功 + guest 退出码 `0` | 计入 pass |
| `fail`（**真失败**） | 编链成功 + 退出码非 `0` / 崩溃 / 超时以外异常 | 计入 fail |
| `known-fail` | 失败**可归因到已登记 issue**（本册**唯一**允许的依据 = `ISS-246` `__thread`），且**逐条注明 issue + 症状原文 + 依据行** | 单列，**不计 pass** |
| `blocked` | 编链失败 / 缺符号 / 后端或链接器缺口 / `qemu` 崩 / `timeout`（`124`） | 计入 blocked；**`blocked>0 ⇒ 本档 rc=1`**（口径同 `ISS-248` 修正后的 `picolibc-tests`） |
| `excluded` | **开工前**声明、**结构性**范围外（如非 `.c` 后缀、上游明确不支持的平台），逐条给 reason + 现场计数 | **唯一** skip 通道 |

- **禁止**把真失败归入 `known-fail` 或 `excluded`；**禁止**为让门控变绿而改标（`ISS-248` 教训）。
- 本册预期 `known-fail = 0`（19 个基准均不依赖 `__thread`）；**若现场出现**，必须按上表口径逐条登记并给 `ISS-246` 依据，**不得**预设结论。
- `excluded` 若为空，须明写「0 条」；不得用「未尝试」充当 `excluded`。

## 接口规范

- **输入**：`.work/source/<embench-iot>`（组件补丁集检出，只读）、musl 静态/动态产物、`qemu-dadao`、本册新增驱动与 hosted 板级 shim。
- **输出**：① `tools/` 下的驱动（入 git；路径与名由工程师定，建议 `tools/testcases/run_embench_user_suite.py`）；② hosted shim（入 git，建议 `tests/scripts/embench_user_boardsupport.c`）；③ 逐例 JSON/CSV + 人类可读报告（落 `.work/log/testcases/`）；④ `.work/evidence/<任务ID>/run.sh`（一键、非交互、任一失败非零、含可达 FAIL）；⑤ `Makefile` 可选 target（**刻意不入** L1/L2/L3，理由同 `TESTCASES-045t`：curated 语料 ≠ `Process-07 §3` 机械派生的代表集）；⑥ 本任务书完成区 + 报告摘要。
- **约束**：不改 `spec/`、`.tao/contracts/`、`contracts/`、`components/**`、`.work/source/**`；不改既有系统模式 runner 的默认路径行为；`--inject` 注入须 `cp` + md5 还原（**禁** `git checkout`/`restore`/`stash`）。

## 验收标准

1. **两档可跑且顺序正确**：证据里可见 **static 轮先完成、dynamic 轮后开始**（时间序或日志段序），两档各自 rc 与用例数。
2. **枚举封闭**：驱动**运行期**枚举 `src/*/`（现场 19），**执行集 == 枚举集**（少一个即 FAIL）；两档都不得因「上一档已跑」而裁剪用例；计数不写死。
3. **链接基址 = lld 默认**：给出至少 1 例每档的 `readelf -l` / `llvm-readobj` 现场输出，证明最低 `PT_LOAD` 地址 ≠ `0xFC00_0000_0000`，且**未**传 `-T dadao.lds`（命令留证）。
4. **两档形态可核**：静态档产物**无** `PT_INTERP`；动态档产物**有** `PT_INTERP` 且 = `/lib/ld-musl-dadao.so.1`，并证明 `ldso` 真跑（如 `AT_BASE ≠ 0` 或 `ldso` 侧可观察证据），不以「链接成功」冒充「动态运行」。
5. **判定独立**：判据 = guest 退出码（Embench 自带 `verify_benchmark` 口径），**不**从 LLVM/QEMU/本仓工具反推期望值；每例记录 `exit` 与超时。
6. **分类与报告**：五类计数现场派生；`fail` 逐条含命令 + 首行错误；`known-fail`（若有）逐条含 `ISS-246` 指针 + 症状原文；`excluded` 逐条 reason；**覆盖边界声明**（哪些档/优化级/基准不在范围内、为何）。
7. **可达 FAIL**：`--inject`（或等价）令至少 1 例期望值错误 ⇒ 驱动 rc=1 且恰该例报 `FAIL`；`cp` + md5 还原 ⇒ 回绿（留三态输出：绿 → 红 → 绿）。
8. **不回归**：`python3 tools/integ/run_embench_e2e.py --embench-src <src> --work-dir <work>`（系统模式）重跑 **38/38**、rc=0。
9. **门控**（**串行**，`ISS-229`；各留自身 rc）：`make check`(L1) rc=0；`make check-modules`(L2) rc=0；`check-patch-tree` rc=0（**预期计数不变 = 177**；若变须说明改了什么并给依据）；`check-no-residue` / `check-tasks` / `check-knowledge-refs` / `tools/infra/check_issues.py` 各 rc=0。
10. **前置申报**：开工前申报预计耗时；若需 `make install-host`（改组件 / 安装根与构建树不同代）⇒ **申报 ≈5 min**、`JOBS=8`、**不并发**、改后**必须**跑（`ISS-210`）；本册预期**不改**组件 ⇒ 只做安装根新鲜度核对（`qemu-dadao` 存在 + 与构建树产物 md5 一致，或如实记录构建树缺失）。
11. **完成区 ≤30 行**，与真实输出逐条对齐；长输出落 `.work/log/testcases/`。

## 判据边界（本批**不做** ✗）

- **不做**与 `RISC-V + musl` golden 的对照 ⇒ 归 **`P4`**（`ADR-0025 D7`）。本册**只做**「自跑 + 失败分类 + 证据可达 FAIL」。
- **不做** `ISS-246`（`__thread`）修复 ⇒ 归 **`LLVM-100t`**；本册只允许把它当 `known-fail` 依据。
- **不做**改 `dadao.lds` 基址（属 `tests/scripts/` + `contract-elf §5` 契约口径 ⇒ 须用户授权）。
- **不做** `P2`/`P3` 的实现返工；撞到 `qemu-dadao` / `ldso` 缺陷 ⇒ 登记 issue + 继续推进，不自行改组件。
- **不做** `llvm-test-suite` / `libc-test`（各自独立成册）。

## 硬约束

1. 临时目录 `/tmp/opencode/TESTCASES-046t/`；命令一律在 workdir（= 仓库根）内、**相对路径**；**禁**出界 `cd`；禁仓库内临时文件。
2. **不用** `git add -A`/`.`；**禁** `git checkout`/`restore`/`stash` 还原注入（一律 `cp` + md5）。
3. **只动**：`tools/testcases/**`（新驱动）、`tests/scripts/**`（hosted shim）、`Makefile`（可选 target）、`.work/**`（gitignored）、本任务书、`.tao/knowledge/milestones.md`（如需订正）。**不动** `spec/` / `.tao/contracts/` / `contracts/` / `components/**` / `.work/source/**`。
4. 完成区与真实输出逐条对齐；**禁** `cmd | tail` 接进 `&&`、**禁** `cmd | tee` 吞码。
5. **不提交**（提交权归 architect）；取得用户裁定须把**原话**写入本任务书。
6. **失败保留现场并继续推进**（自行处置：查证 / 绕行 / 有据重试并记录次数 / 登记后跳过）；**只在需用户语义裁定**时留问。
7. 长任务（单档预计 >10 min）⇒ `setsid nohup` 后台 + 落 `XXX_EXIT=$rc` 标记，**不在会话内等待**；**一次只跑一档**。
8. **共享文件串行**：本册与 `TESTCASES-047t`/`TESTCASES-048t` 同改 `Makefile`/`milestones.md` ⇒ 不得并行。

## 完成区
**测试结果**：静态档（`qemu-dadao`，lld 默认基址）运行时枚举 total=38（19 基准 × `-O0/-O2`）pass=38 fail=0 known-fail=0 excluded=0 blocked=0，driver rc=0；`.work/evidence/TESTCASES-046t/run.sh` 默认 rc=0、`--inject` rc=0（绿→红→绿，两处注入同次前台闭合）。动态档未跑（下一笔）。
分类表（逐例；每格 = O0/O2）：
| 基准 | 类 | 基准 | 类 | 基准 | 类 |
|---|---|---|---|---|---|
| aha-mont64 | pass/pass | crc32 | pass/pass | depthconv | pass/pass |
| edn | pass/pass | huffbench | pass/pass | matmult-int | pass/pass |
| md5sum | pass/pass | nettle-aes | pass/pass | nettle-sha256 | pass/pass |
| nsichneu | pass/pass | picojpeg | pass/pass | qrduino | pass/pass |
| sglib-combined | pass/pass | slre | pass/pass | statemate | pass/pass |
| tarfind | pass/pass | ud | pass/pass | wikisort | pass/pass |
| xgboost | pass/pass | — | — | — | — |

known-fail 0 条：无 `ISS-246` 命中（该分支按 `thread-local storage is not supported` / `GlobalTLSAddress` 原文症状才可归入，未预设）；excluded 0 条（`src/*/` 19 目录均有 `.c`，现场统计）；blocked 0 ⇒ 本档 rc=0（`ISS-248` 口径）。
**修改文件**：`tools/testcases/run_embench_user_suite.py`（新驱动，两档 `--link-mode static|dynamic` 必选，无默认）、`tests/scripts/embench_user_boardsupport.c`（新 hosted 三钩子 shim，musl `write` 标记）；gitignored 辅助：`.work/evidence/TESTCASES-046t/run.sh`、`.work/log/testcases/embench-user-static.json`（同名 `.log`）、`.work/build/embench-user-static/`、`.work/log/testcases/m6-embench-regression.log`；本任务书。

**验收结果**：
- 基址：38/38 `min PT_LOAD=0x10000`（≠ `0xFC00_0000_0000`）；样例 `.work/build/embench-user-static/static/O0/crc32/crc32.elf` 经 `llvm-readobj --program-headers` 见最低 `PT_LOAD VirtualAddress: 0x10000`；链接命令无 `-T`/无 `dadao.lds`。静态档显式用 `<musl>/lib/libc.a`：同目录 `-lc` 会选 `libc.so`（实测产物仅 `PT_DYNAMIC` 无 `PT_INTERP`，`qemu-user` **SIGSEGV**）⇒ 与 `QEMU-062t` smoke 同口径。
- 形态：静态 38/38 无 `PT_INTERP`/`PT_DYNAMIC`；板级标记 3/3（`[board:init/start/stop]`）。
- 独立 oracle：`support/main.c` `return !correct`（`verify_benchmark` 为基准自身判据；期望常量 0，非从 LLVM/QEMU 反推）；另独立重放 `crc32(-O0)` ⇒ exit=0 + 3 markers。编译参数保留 `-ffreestanding -fno-builtin`（与系统模式一致、不变工作负载），头文件改为 musl 口径（不叠 `embench_include` 桩）。
- 不回归：`tools/integ/run_embench_e2e.py --embench-src .work/source/embench-iot --work-dir .work/build/m6-embench` ⇒ 38/38、rc=0。
- `--inject`：① `EXPECTED_GUEST_EXIT 0→1` ⇒ rc=1、pass=0/fail=19；② `benchmarks[1:]` 静默跳例 ⇒ `[FAIL] closure: executed 18 != discovered 19`、rc=1；各 `cp` 备份 + md5 还原（末态 `ae389da7e7b2fddd5f6f11421ebdc94c`），还原后 O0 与全量各回绿一次。
- 门控（各自身 rc）：`validate-vectors` 0、`check-no-residue` 0、`check-tasks` 0、`check-knowledge-refs` 0、`check-component-changelog` 0、`check_issues.py` 0、`make check`(L1) 0（`check-patch-tree` 177 patches 不变）；未跑 L3/`install-host`（无组件改动；安装根与构建树 `qemu-dadao` md5 均 `c74b319d4de036875e51afbc769477c3`，新鲜）。
- 耗时：静态全量 15.6 s；`run.sh` 默认 ≈16 s、`--inject` 49 s（均前台，未用后台长任务）。

**新发现/坑**：① `-L <musl>/lib -lc` 不能表达静态档（同目录 `.so` 优先 ⇒ 无 `PT_INTERP` 的 `PT_DYNAMIC` 镜像在 `qemu-user` 段错误），静态档须显式 archive（建议沉淀并回填本批三册口径）。② `-nostdinc` + musl 头可直接编 embench，勿叠 `tests/scripts/embench_include` 的 freestanding 桩；组件 `boardsupport.c` 走半主机，user 模式必须用本仓 hosted shim。③ embench 在 qemu-user 很快（38 例 15.6 s），无需后台；`ISS-246` 分支已实现但本轮 0 命中，未自证（需 `libc-test` TLS 例）。

**遗留问题**：动态档（驱动 `--link-mode dynamic` 已实现但**未执行**，下一笔）；`P4` golden 对照、`ISS-246` 修复不在本册。无阻塞项。

### 动态档（第 2 轮，2026-10-17）

**测试结果**：`--link-mode dynamic --libc .dadao/dadao-unknown-elf/lib/libc.so`，运行期枚举 **total=38**（19 基准 × `-O0/-O2`）⇒ **pass=0 / fail=0 / known-fail=0 / excluded=0 / blocked=38**，driver rc=1（`blocked>0 ⇒ rc=1`，`ISS-248` 口径）。逐例（19 × O0/O2）**全部 blocked**，同一签名：`exit=127` + `Error relocating /lib/ld-musl-dadao.so.1: RELRO protection failed: No error information`，board marker 0/3（⇒ `support/main.c` 从未执行）；逐例记录 `.work/log/testcases/embench-user-dynamic.json`。
**与静态档对比**：静态 **38/38 pass**（rc=0；本轮为验证驱动改动**重跑仍 38/38**）；动态 **0/38**。差异不在用例、在运行环境（见下）。
**失败分类（动态）**：`fail=0`；`blocked=38`（loader 阶段死亡，非 benchmark 判定）⇒ **归属 `ISS-258`**（安装根 `libc.so` 早于 `ISS-249` argmask 变更，与现行 `qemu-dadao` 不匹配；根因三证 = `-strace` 参数整体右移 / 随包 `libc.so` 的 `reloc_all` 旧桩布局反汇编 / mtime 序 13:49<17:33<18:31）；`known-fail=0`、`excluded=0`（现场统计）。
**动态特有项**：① `ldso` **确实被装载并执行**（其自身 RELRO 报错 + `-strace` 显示解释器映射；非"链接成功"冒充）；② 38/38 产物 `PT_INTERP` = `/lib/ld-musl-dadao.so.1`（逐例 JSON + 样例逐字节解析复核）、`min PT_LOAD=0x10000`、链接命令无 `-T`/无 `dadao.lds`、显式 `libc.so`；③ **`AT_PHDR`/`AT_ENTRY` 与 `/proc/self/maps` 含 `libc.so` 无法观测**（loader 在重定位阶段即退出，guest 未达入口）⇒ 如实标 blocked，不推断。
**验收结果**：`.work/evidence/TESTCASES-046t-dyn/run.sh` default **rc=0**（ALL GREEN，30 s）＝38 例逐条 JSON 复核（blocked/exit127/interp/libc.so/无 `-T`/ldso 签名/产物存在）+ 根因三证 + 静态档回归 38/38；`--inject` **rc=0**（65 s，三处注入同次前台闭合，`cp`+md5）：I1 关掉 loader-abort 判据 ⇒ fail=19、`fail==0` 翻红；I2 静默跳 1 例 ⇒ `[FAIL] closure: executed 18 != discovered 19`；I3 `PT_INTERP` 改 `.so.2` ⇒ 逐例 ldso 签名检查翻红（exit=255）；三处均还原（md5 `e4be5e0f…`）后回预期态；静态档原证据脚本亦复跑 default rc=0（16 s）/ `--inject` rc=0（49 s，见自审 F9）。
**修改文件**：`tools/testcases/run_embench_user_suite.py`（+`--libc` 产物覆盖；+「ldso 诊断 + 无 marker ⇒ blocked」判据；+`PT_DYNAMIC` 形态判据——动态档缺 `PT_DYNAMIC` / 静态档带 `PT_DYNAMIC` 显式 blocked）、`.tao/knowledge/issues.yaml`（+`ISS-258`）、本任务书；gitignored：`.work/evidence/TESTCASES-046t-dyn/run.sh`、`.work/log/testcases/embench-user-dynamic.json`、`.work/log/testcases/embench-user-dynamic.log`、`.work/build/embench-user-dynamic/`。
**新发现/坑**：① "安装根已是最新"不能由单一 commit 时点推断——须**逐产物**核（本轮 `libc.a` 是 18:34 新产物、`libc.so` 仍 13:49 旧产物）；`ISS-249` 这类**协议双侧变更**必须把产物重建纳入同批验收。② loader 阶段死亡 ≠ 用例失败：加"ldso 诊断 + 无 marker ⇒ blocked"归类（不放松：`blocked>0` 仍 rc=1），否则会把环境缺陷误记成 38 个 benchmark 失败。③ `llvm-readobj` 不打印 `PT_INTERP` 字符串，证据脚本须自解析 ELF。④ 前置复核与派单文字有出入：随包 `libc.so` **无 `PT_TLS`**（`llvm-readobj --program-headers` 0 命中、无 `.tdata/.tbss`），与 `ISS-246`（TLS 未实现，归 M9）一致；embench 不用 `__thread`，不构成本册阻塞，**如实记录**。
**遗留问题**：动态档**未达"可跑"** —— `ISS-258` 需 `make build-musl-shared JOBS=8`（自安装 `libc.so`+`ld-musl-dadao.so.1`）后复跑；本笔按派单**禁 build-musl**，未越界。`AT_*`/`maps` 类动态特有项待环境修复后补测；`P4` golden 对照、`ISS-246` 修复不在本册。
> **〔追加（2026-10-17 19:5x，复跑后）〕** 本节 = 重跑前状态，数字保持原样；原始输出已归档 `.work/log/testcases/ISS-258-blocked-round/`。复跑与 `ISS-258` 处置见下节。

### 动态档（第 2 轮复跑 + `ISS-258` 处置，2026-10-17 19:50–19:58）

**测试结果**：`make build-musl-shared JOBS=8`（rc=0；**clean 全量 18.8 s**）重装 `libc.so` 后复跑 ⇒ 运行期枚举 **total=38**：**pass=38 / fail=0 / known-fail=0 / excluded=0 / blocked=0**，driver **rc=0**（16 s）。与静态档一致：静态 38/38（同轮复跑 rc=0）。**逐例**：19 基准 × `-O0/-O2` 全 pass、`exit=0`、board marker 3/3、`PT_INTERP=/lib/ld-musl-dadao.so.1`、`min PT_LOAD=0x10000`、链接无 `-T`（`.work/log/testcases/embench-user-dynamic.json`）。
**疑点 A（`libc.a` 来源）= 非旧 musl，是 picolibc 同名产物**：① 046t/047t 驱动实际吃 **`.work/source/musl/lib/libc.a`**（`--musl` 默认；两册同路径），md5 **`ab9c61aa…`**/sha256 `1bad81fd…`（19:49 重建，与 18:34 版**逐字节相同**）；② `.dadao/dadao-unknown-elf/lib/libc.a` md5 **`73630d61…`** = `.work/build/picolibc/libc.a` **同一份**（成员名 `libc_argz_*.c.o`；ADR-0016 D4 两个 libc 同名共存，装于 14:45）⇒ 与 `ISS-249` 无关；③ 故**未**触发「重建 + 047t 静态重跑」条件（047t 用的就是 `ab9c…`，数字不可能变）。
**疑点 B（`PT_TLS`）= 记录无误，不是配方漂移**：`INFRA-085t` 的 `PT_TLS` 证据测的是**合成 TLS 对象**（`tls_seed.s` → p_filesz 8 / memsz 16 / align 8），其 **F11/S6 明写**「musl 线程态走 `struct pthread` 字段，`libc.so` 无 `SHF_TLS` 节 ⇒ 无 `PT_TLS` 是正确形态 / `no PT_TLS`」；现场复核 `libc.so`：`PT_TLS=0`、`.tdata/.tbss=0`，与设计一致。**可重复性**：`make -C .work/source/musl clean` + 同 target 全量重建（18.8 s）⇒ `libc.so`/`libc.a` sha256 **逐字节相同**（`a86a12cb…`/`1bad81fd…`）⇒ 配方未漂移、可重复。**记录处置**：不改历史证据，本处追加更正：§「动态特有项」里"派单前置 `PT_TLS` ✓"应读作**TLS 基础设施已验**，不是 `libc.so` 有 `PT_TLS`。
**动态特有项（真观测）**：`tests/scripts/dadao_user_dyn_probe.c`（新增，动态链接）⇒ `AT_PHDR=0x10040`、`AT_ENTRY=0x20554`（== 探针 `e_entry`）、`AT_BASE=0x7aa0a8250000`（≠0、页对齐、≠`AT_ENTRY`）、`AT_PHNUM=8`/`AT_PHENT=56`（== ELF 头）、`/proc/self/maps` 命中 `…/root/lib/ld-musl-dadao.so.1` 映射行（`r--p`，偏移 0）；`ldso` 装载已由探针成功执行直接证明（非"链接成功"冒充）。
**`ISS-258` 处置②（可机械判定的新鲜度）**：`build_musl.py` 成功构建后新增 **source stamp**（`obj/.dadao-musl-source-stamp` = 全树内容 sha256，与既有 toolchain stamp 并列），且 **digest 变化强制 `make clean`**（musl 的 Makefile 不依赖全部头文件，ISS-249 恰是改 `arch/dadao/syscall_arch.h`，增量构建可能漏掉）；新增 **`check-musl-freshness`**（`tools/infra/check_musl_freshness.py`，**L1**，~1.2 s，已登记 `docs/Process-07 §1.1`）= 两戳记 == 当前 + 安装副本与构建产物 sha256 一致 + `ld-musl-dadao.so.1` 链接指向；不符 ⇒ FAIL 并提示 `make build-musl-shared`；无构建树/无共享产物 ⇒ SKIP。**可达 FAIL**：戳记改错 / 真加一行 musl 源码 / 篡改安装副本 —— 三者均 rc=1，`cp`+md5 还原后 rc=0（见证据脚本 I3–I5）。**源变强制 clean 实测**：加一行注释 ⇒ `sources: musl source digest changed` + `'make clean' (full rebuild)`（20 s）；还原后再 clean 重建 ⇒ 产物 sha 回到 `a86a12cb…`（逐字节复原）。
**验收结果**：`.work/evidence/TESTCASES-046t-dyn/run.sh` **default rc=0**（33 s，含形状/戳记/38 例逐条/探针/静态回归）、**`--inject` rc=0**（73 s，五处注入：I1 期望退出码→`fail=19`；I2 跳例→`[FAIL] closure: executed 18 != discovered 19`；I3 戳记→gate rc=1；I4 真改 musl 源→gate rc=1；I5 篡改安装 `libc.so`→gate rc=1；全部 `cp`+md5 还原，驱动 md5 `e4be5e0f…` 不变，末轮 38/38）。
**修改文件**：`tests/scripts/dadao_user_dyn_probe.c`（新探针）、`tools/infra/build_musl.py`（+source stamp）、`tools/infra/check_musl_freshness.py`（新门控）、`Makefile`（`check-musl-freshness` + L1 接线）、`docs/Process-07-门控分层规范.md`（§1.1 登记）、`.tao/knowledge/issues.yaml`（`ISS-258` 处置）、本任务书；gitignored：`.work/evidence/TESTCASES-046t-dyn/run.sh`、`.work/log/testcases/embench-user-dynamic.json`、`.work/log/testcases/embench-user-dynamic.log`、`.work/log/testcases/ISS-258-blocked-round/`、`.work/log/infra/ISS-258-*.log`、`.work/build/embench-user-dynamic/`、`.work/source/musl`（重建产物）。
**新发现/坑**：① 同名 `libc.a` 在 sysroot 是 **picolibc**、在 musl 构建树是 **musl** —— 判"产物是否旧"不能只看 mtime/路径，要看**成员名/md5 归谁**（本轮疑点 A 即此）。② 「TLS 基础设施已验」≠「`libc.so` 有 `PT_TLS`」：musl 的 TCB 不在 `.tdata`，报告引用时要写清测的是哪个对象。③ 增量构建 sha 不变**不能**证明可重复（可能什么都没重编）；要 `clean` 全量重建再比 sha（本轮已补）。
**遗留问题**：047t 静态档未重跑（其 `libc.a` 与现状 sha256 相同，数字无变化空间；如需现场复证，`--musl .work/source/musl` 全量约 508 s）；`AT_*`/`maps` 观测由独立探针承担（驱动本身不探 auxv）；`P4` golden 对照、`ISS-246` 不在本册。

### 终局复跑（`INFRA-079t` 后端 + `libc.so` 重建后，2026-10-17 22:12–22:41）

**测试结果**：按派单**只跑测**（未改 `musl`/`LLVM`/`QEMU` 源码、未动 `Makefile`、未 `install-host`），4 组顺序执行、逐组落日志（`.work/log/testcases/final-rerun/`）。本册：**静态 38/38 pass（rc=0，16.1 s）→ 动态 38/38 pass（rc=0，16.3 s）**；运行期枚举 19 基准 × `{O0,O2}` = 38（现场派生），`fail/known-fail/excluded/blocked` 全 0。
**与基线对比（逐例）**：静态 38/38、动态 38/38，与上次作数**完全一致**；`diff_baseline.py` 对两档 JSON 逐例比对 ⇒ **transitions=0**（无 `pass→fail`、无新 `fail`、无增删例）。
**新产物口径**：`libc.a` sha256 `a65c3351…`、`libc.so` `d5fa2da3…`（`INFRA-079t` 重建后；安装根副本与之同 sha）；安装根 clang/lld/qemu 与 `.work/build` md5 全等（`854dd25e`/`cfd64e80`/`c40bc7f9`）；`clang --target=dadao-unknown-elf -print-libgcc-file-name -rtlib=compiler-rt` ⇒ 真实 archive（`lib/dadao-unknown-unknown-elf/libclang_rt.builtins.a`，217 640 B）。
**验收结果**：① 基址：样例 `llvm-readobj --program-headers` 两档最低 `PT_LOAD=0x10000`（≠`0xFC00_0000_0000`），38/38 链接行无 `-T`/`dadao.lds`；② 形态：静态 38/38 无 `PT_INTERP`、动态 38/38 `PT_INTERP=/lib/ld-musl-dadao.so.1`（逐例 JSON + 脚本自解析 ELF）；③ pass 例 board marker 均 3/3；④ 证据脚本 `/tmp/opencode/FINAL-RERUN/run.sh` **default rc=0**（96 项独立复核 + 三份既有证据脚本 default）、**`--inject` rc=0**（I0 篡改静态 libc-test JSON ⇒ 复核翻红 ⇒ `cp`+md5 还原回绿；另 046t 静态 2 / 046t 动态 5 / 047t 动态 3 处既有注入同次闭合）；⑤ 门控各自 rc=0：`check-musl-freshness`/`check-tasks`/`check-knowledge-refs`/`check-no-residue`/`check_issues.py`/`make check`(L1)。
**修改文件**：本任务书（仅追加本节 + `阶段进度`）；无源码/脚本改动。gitignored：`.work/log/testcases/final-rerun/`。
**新发现/坑**：① 复用 046t 动态证据脚本的 I4（`cp` 还原真 musl 源）会**抬高源文件 mtime**，使 047t 动态证据脚本的 **mtime 代理**报 `stale`（内容已复原、`check-musl-freshness` 内容摘要绿）。终局脚本改为注入前后快照/还原 2592 个 musl 源 mtime，并在末段复核 `libc.so` sha + 内容门控 ⇒ **内容才是新鲜度真源，mtime 只作代理**。② 4 组逐例同构 ⇒ `INFRA-079t` 的 i128/FP↔i128 后端改动与 `libc.so` 重建在本册语料上**无行为变化**。
**遗留问题**：无本册遗留（`P4` golden 对照、`ISS-246` 修复不在本册）。

### 终局复跑（新工具链产物，2026-10-17 22:44–23:07）

> **上一轮（22:12–22:41）作废**：其 `libc.a`/`libc.so` 是 **19:49 旧 clang** 编的（`install-host` 21:26 换新工具链后未重建），L2 `check-musl-freshness` 当场报 `toolchain stamp != current clang/ld.lld`。已 `make build-musl-shared JOBS=8` **rc=0**（21 s，22:43:40→22:44:01）重建，`check-musl-freshness` **PASS**；本节数字 = 新产物上的**最终作数**。

**测试结果**：按派单只跑测（未改源码、未动 `Makefile`、未 `install-host`），顺序执行、逐组落日志（`.work/log/testcases/final-rerun-round2/`）：**静态 38/38 pass（rc=0，15.9 s）→ 动态 38/38 pass（rc=0，16.3 s）**；运行期枚举 19 基准 × `{O0,O2}` = 38（现场派生），`fail/known-fail/excluded/blocked` 全 0。
**与上轮对比（逐例）**：4 组共 750 条记录逐例比对（`diff_baseline2.py`）⇒ **transitions=0**、无增删例；本册两档 **38/38 全等**，无 `pass→fail`、无新 `fail`。
**产物/工具链指纹（证明吃的是新产物）**：`libc.a` = `.work/source/musl/lib/libc.a`（**2 660 248 B，mtime 22:44:00，sha256 `a65c3351…`**）；`libc.so` = 同目录（**1 046 488 B，mtime 22:43:59，sha256 `d5fa2da3…`**，与旧构建字节相同）；sysroot `libc.so` 同 sha；`clang` md5 `854dd25e…`、`ld.lld` `cfd64e80…`、`qemu-dadao` `c40bc7f9…`（安装根 == `.work/build`）；驱动实吃路径：静态 → `<musl>/lib/libc.a`，动态 → `.dadao/dadao-unknown-elf/lib/libc.so`（38/38 链接行逐条核）；**76/76 ELF mtime 均晚于产物 mtime**。
**验收结果**：① `prove_products.py` 全绿（指纹/路径/ELF 新旧/工具链 md5）；② `verify_groups.py` **96/96 PASS**（计数、闭包、形态、链接行、known-fail 依据）；③ 基址/形态同前：最低 `PT_LOAD=0x10000`（≠`0xFC00…`）、静态无 `PT_INTERP`、动态 `=/lib/ld-musl-dadao.so.1`、无 `-T`；④ 门控各自 rc=0：`check-musl-freshness`/`check-tasks`/`check-knowledge-refs`/`check-no-residue`/`check_issues.py`/`make check`(L1)。
**修改文件**：本任务书（仅追加本节）；无源码/脚本/驱动改动。gitignored：`.work/log/testcases/final-rerun-round2/`。
**新发现/坑**：`check-musl-freshness` 的 **toolchain stamp** 能抓到「工具链换了但 libc 未重建」这类**跨产物代际错配**，本轮即是（L2 抓到，早于任何测试结论）；另证「sha256 不变」≠「没重建」——mtime 22:43:59/22:44:00 才是重建证据，须二者并列记录。
**遗留问题**：无本册遗留（`P4` golden 对照、`ISS-246` 修复不在本册）。

## 审阅记录

#### 第 1 轮 engineer 自审

自主逐行审查 driver / shim / `run.sh`，并以真实重跑对齐（非抽样）。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|---|
| F1 | ELF 程序头解析把 `e_phoff/e_phentsize/e_phnum` 一并按 `>QHH@32` 读 ⇒ 19/19 例 “ELF parse failed” | ✅已修 | `>Q@32` + `>HH@54` | 修后 19/19、38/38 pass，`min_pt_load=0x10000` |
| F2 | 静态档按册内 `-lc` 链接选到 `libc.so` ⇒ `PT_DYNAMIC` 无 `PT_INTERP`，`qemu-dadao` SIGSEGV（rc=139） | ✅已修 | 静态档显式传 `<musl>/lib/libc.a`；动态档显式 `libc.so` + `-dynamic-linker` | `PT_INTERP=0/PT_DYNAMIC=0`，38/38 exit=0；证据脚本再判 `libc.a`/无 `-T` |
| F3 | JSON `counts.excluded` 恒为 0，与 live `excluded` 列表可能不一致 | ✅已修 | `counts["excluded"]=len(excluded)`，汇总同源 | 本轮 excluded=0 两处一致；脚本 check 由 live census 派生 |
| F4 | 证据脚本对“预期非零”的注入跑仍打印 `[FAIL]`，易被误读为证据失败 | ✅已修 | 新增 `run_driver_fail`（预期非零 ⇒ `[PASS] … rc=1`） | `--inject` 输出逐条 PASS，末行 ALL GREEN、rc=0 |
| F5 | 证据脚本内嵌 python 缺 `import os`（artifact 存在性检查） | ✅已修 | heredoc 补 `import os` | 默认 `run.sh` rc=0（38 条记录检查通过） |
| F6 | `--json-out`/`--report-out` 传裸文件名时 `makedirs("")` 崩溃 | ✅已修 | `os.path.dirname(...) or "."` | 默认路径与显式路径两次运行均 rc=0 |
| F7 | shim 块注释含 `/**` ⇒ `-Wcomment` 警告（不影响判定） | ✅已修 | 改写路径写法 | 单编 shim rc=0、无警告；全量重跑仍 38/38 |
| F8 | 闭合保护是否真能失败（非恒真） | ✅验证 | 注入“跳 1 例” | `[FAIL] closure: executed 18 != discovered 19`、rc=1；还原 md5 后回绿 |
| F9 | `--link-mode` 无默认歧义 | ✅验证 | 不传参调用 | argparse rc=2，报 “required: --link-mode” |

判决：无未修 finding；静态档实现与证据完成，交验收（动态档按册留待下一笔）。


#### 第 1 轮 reviewer 验收
（独立重跑、约束核验、判决）


#### 第 2 轮 engineer 自审（动态档）

逐行审查 `tools/testcases/run_embench_user_suite.py` 的两处改动 + `.work/evidence/TESTCASES-046t-dyn/run.sh`，并以真实重跑对齐（default + `--inject` 各一次，非抽样）。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|---|
| F1 | 动态档 38/38 `exit=127`：随包 `libc.so`（13:49）早于 `ISS-249` argmask（17:33），与现行 `qemu-dadao`（18:31）不匹配 ⇒ ldso RELRO `mprotect` 参数右移一位 | ✅处置（归类修 + 登记） | 驱动加「ldso `Error relocating` + 无 marker ⇒ blocked」；登记 `ISS-258`（重建 `libc.so` 属越界，按派单不做） | `-strace` = `mprotect(NULL,<start>,0x6000)`；`reloc_all` 反汇编 = `rd16/rd17/rd18` + `rd2rb {rb16},{rd19}`（旧桩）；mtime 13:49<17:33<18:31 |
| F2 | 驱动默认 `<musl>/lib/libc.so` 不存在（P2 的 `libc.so` 只在 target sysroot）⇒ 动态档 SetupError rc=2 | ✅已修 | 新增 `--libc`（默认行为不变） | `--libc .dadao/dadao-unknown-elf/lib/libc.so` ⇒ total=38；不传 `--libc` 时静态档仍 38/38 |
| F3 | 证据脚本用 `llvm-readobj` 取 `PT_INTERP` 字符串 ⇒ 该工具不打印，样例检查恒 FAIL | ✅已修 | 脚本内 python 自解析 ELF（独立于驱动） | 样例 = `/lib/ld-musl-dadao.so.1`；default rc=0 |
| F4 | 脚本把 `$((...))` 当命令替换用（`PT_TLS`/`reloc_all Size`）⇒ 算术求值报错 | ✅已修 | 改 `$(...)` | `PT_TLS count=0`、`reloc_all size=908` 正常打印 |
| F5 | 完成区用 brace 形式合并两条日志路径，被判为悬空引用 | ✅已修 | 拆成两条全路径；本条只写现象不写路径 | `check-knowledge-refs` rc=0（悬空 0） |
| F6 | 若沿用「rc≠0 ⇒ fail」，会把环境缺陷记成 38 个 benchmark 真失败（错误归属） | ✅已修 | 同上 F1 判据；`blocked>0` 仍 `rc=1`（不放松） | `fail=0/blocked=38`，driver rc=1；注入 I1 关掉判据 ⇒ fail=19、检查翻红 |
| F7 | 三处注入是否真能翻红（非恒真） | ✅验证 | 未改 | I1 `fail` 检查、I2 `[FAIL] closure: executed 18 != discovered 19`、I3 逐例签名检查，均翻红；`cp`+md5（`e4be5e0f…`）还原后回预期态 |
| F8 | `--libc` 误传 archive 时会不会静默成功 | ✅已修 | 加 `PT_DYNAMIC` 形态判据（动态档缺 / 静态档带 ⇒ blocked，带 reason） | `--link-mode dynamic --libc libc.a` ⇒ 19/19 `BLOCKED (dynamic image has no PT_DYNAMIC …)`，rc=1（不静默、不误记 fail）；正常动态档不受影响（38/38 仍按 ldso 签名 blocked） |
| F9 | 静态档证据脚本的前置仍要求 `.work/source/musl/lib/libc.so` ⇒ 该 P2 产物现只在 target sysroot，脚本 prerequisite 恒 FAIL（与本次改动无关的陈旧路径） | ✅已修 | 前置改指 sysroot 的 `libc.so` | 静态证据 default rc=0（38/38 pass，16 s）、`--inject` rc=0（49 s，两处注入翻红 + md5 `e4be5e0f…` 还原） |

判决：无未修 finding（唯一未闭环项 = `ISS-258` 的产物重建，**越界**，按派单不修）；动态档结论 = **38/38 blocked（环境阻塞，证据自洽）**。按派单**未改**本册 `**状态**`（保持 `待开始`）、未 commit/push。


#### 第 3 轮 engineer 自审（疑点 A/B + 复跑 + 新鲜度门控）

逐行审查 `build_musl.py` 的 source-stamp 增量、`check_musl_freshness.py`（新）、`Makefile`/`Process-07` 接线、`dadao_user_dyn_probe.c`（新）与重写后的动态证据脚本；两条疑点均按现场证据定性，不用"看起来对"结案。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|---|
| F1 | 疑点 A：sysroot `libc.a` mtime 14:45 < `ISS-249` 17:33 | ✅已查清（非旧 musl） | 未改产物 | 成员名 `libc_argz_*.c.o` + md5 `73630d61…` == `.work/build/picolibc/libc.a`；046t/047t 用 `.work/source/musl/lib/libc.a`（`--musl` 默认），md5 `ab9c61aa…`（19:49 重建后与 18:34 版相同）⇒ 不触发重建/047t 重跑条件 |
| F2 | 疑点 B：`libc.so` 无 `PT_TLS`，与"INFRA-085t 验过 PT_TLS"冲突 | ✅已查清（记录无误） | 未改产物；任务书追加更正（历史证据不动） | `INFRA-085t` D1 测的是**合成 TLS 对象** `tls_seed.s`（p_filesz 8/memsz 16/align 8）；同册 F11/S6 断言 `libc.so` **无** `PT_TLS` 是正确形态。现场 `PT_TLS=0`、`.tdata/.tbss=0` |
| F3 | 增量重建 sha 不变不足以证"可重复"（可能零重编） | ✅已修（补证） | 未改代码 | `make -C .work/source/musl clean` + `make build-musl-shared JOBS=8`（18.8 s）⇒ `libc.so`/`libc.a` sha256 与重建前**逐字节相同**（`a86a12cb…`/`1bad81fd…`）⇒ 配方可重复、无漂移 |
| F4 | 新门控须能在"源变/工具链变/装错副本"三种真实故障下 FAIL，且不能把新克隆/纯静态流程变红 | ✅已验证 | 新增 `check_musl_freshness.py` + source stamp + L1 接线 | I3 戳记、I4 真改 musl 源、I5 篡改安装副本 ⇒ 均 rc=1；还原后 rc=0；`mv` 走构建树 ⇒ `SKIP` rc=0，移回后 rc=0（md5 不变） |
| F5 | source stamp 若含 `obj/`/`lib/`/`config.mak` 会自污染（每次构建改摘要） | ✅已修 | `SOURCE_STAMP_SKIP_TOP` 排除生成物；内容摘要（非 mtime） | 两次构建 + 一次 clean 重建后摘要恒为 `811d143a…` |
| F9 | 只"检测"源变不够：`make build-musl-shared` 若走增量、musl 又漏了头文件依赖 ⇒ 戳记写成新值而产物仍旧 | ✅已修 | `source_decision()`：digest 变即 `make clean`（与工具链戳记同风格，日志打印两行判定） | 加一行注释 ⇒ `sources: musl source digest changed` + `'make clean' (full rebuild)`（20 s）；还原后再次 clean 重建 ⇒ `libc.so` sha 回到 `a86a12cb…`（逐字节复原） |
| F6 | 复跑证据若覆盖旧 `blocked` 轮输出 = 改写历史 | ✅已修 | 旧输出归档 `.work/log/testcases/ISS-258-blocked-round/`；旧节只追加指针 | `dynamic-baseline.log` 仍 `blocked=38`；新证据脚本按 `pass` 口径重写 |
| F7 | 五处注入是否真能翻红（含 gate 三例） | ✅验证 | 未改 | I1 `fail=19`；I2 `closure 18 != 19`；I3–I5 gate rc=1；全部 `cp`+md5 还原（驱动 `e4be5e0f…`、装副本 `cb9b585b…`）后末轮 38/38 |
| F8 | 探针断言是否"自证"（loader 值 vs loader 自己） | ✅验证 | 探针只打印；断言在脚本里与 **ELF 头**比对 | `AT_ENTRY 0x20554 == e_entry`、`AT_PHNUM 8 == e_phnum`、`AT_PHENT 56 == e_phentsize`；`AT_BASE` 独立判「≠0、页对齐、≠AT_ENTRY」 |

判决：无未修 finding。`ISS-258` 已由「重装产物 + L1 新鲜度门控」闭环（`resolved_by = TESTCASES-046t`），动态档 38/38 pass。按派单**未改**本册 `**状态**`（仍 `待开始`）、未 commit/push。

#### 第 4 轮 architect 提交（2026-10-17）
- 档位：按主会话派单给定消息**正常提交**（本册无 reviewer 判决块、`**状态**` 保持 `待开始` ⇒ 按 architect 默认档位应为 `WIP:`；此处按派单原话执行，如实披露）。
- 提交 ①：`7ef1c6f` = 本册 + `tools/testcases/run_embench_user_suite.py` + `tests/scripts/dadao_user_dyn_probe.c` + `.tao/knowledge/issues.yaml`（`ISS-258`）。
- 提交 ②：musl 新鲜度（`build_musl.py` / `check_musl_freshness.py` / `Makefile` / `docs/Process-07`）+ `milestones.md` / `INTEG-036m` 台账 + 本条。
- 文件集对账：显式 staging（逐路径），命中第 2/3 轮完成区「修改文件」并集 **8** 路径 + 本轮台账 **2** 路径；**无漏提**（`.work/**` 均 gitignored）/ **无多提** / **无越界**。
