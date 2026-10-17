# TESTCASES-046t: Embench-IoT 两档用户态跑（静态档 → 动态档）

**模块**：testcases
**项目里程碑**：M8
**依赖**：`QEMU-062t`（`qemu-user` 的 DADAO 后端，**`已验证`**；`qemu-dadao` 已装进安装根 `paths.host_toolchain_bin()`）；`INFRA-082t`（`P1` musl 静态，**`已验证`**；产 `crt1.o` + `libc.a`）、`INFRA-085t`（`P2` 动态，**`已验证`**；产 `libc.so` + `ld-musl-dadao.so.1`）；`TESTCASES-039t`（Embench 移植 + 系统模式 runner `tools/integ/run_embench_e2e.py`，M6 起 38/38）；`ISS-247`（**链接基址口径**：不得用 `tests/scripts/dadao.lds`）、`ISS-246`（**known-fail 唯一依据**）、`ADR-0025`（`D2` 无内核 / `D6` 路线 / `D7` golden 对照归 `P4`）、`ISS-229`（重建 / 门控**串行**）、`ISS-210`（安装根新鲜度）；**同批三册**：`TESTCASES-046t`（本册）/ `TESTCASES-047t`（`libc-test`）/ `TESTCASES-048t`（`llvm-test-suite`）⇒ **同改共享文件（`Makefile` / `milestones.md`）⇒ 串行**，禁并行。
**状态**：待开始

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
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（自审意见、finding 处置及判决）

#### 第 1 轮 reviewer 验收
（独立重跑、约束核验、判决）
