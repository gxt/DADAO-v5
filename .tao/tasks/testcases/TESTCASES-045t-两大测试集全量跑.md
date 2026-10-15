# TESTCASES-045t: 两大测试集全量跑（libc-test + llvm-test-suite baseline）

> **收尾重定义（2026-10-15）**：本任务**收窄为「`P1` 能力边界度量」**；**阶段 2/3 取消** ✗ ⇒ 「全量」改由 **`P3`（`qemu-user`）承接** ✓（标题保留原名以维持引用稳定）。见「§收尾裁定与范围重定义」。

**模块**：testcases
**项目里程碑**：M8
**依赖**：`INFRA-082t`（musl 静态最小集移植＝`ADR-0025 D6` 的 `P1` 段，**`已验证` 2026-10-15**；含 QEMU 侧 `SYS_UMON_SYSCALL` 服务〔`ISS-216` 已关〕）；`TESTCASES-044t`（`libc-test` 取源与锁定，**`已验证` 2026-10-15**）；`LLVM-093t`（`llvm-test-suite` 取源与锁定，**`已验证` 2026-10-15**）；`SPEC-138t`（`.tao/contracts/contract-syscall.md`，**`已验证`**）；`ADR-0025`（`D1`/`D2`/`D6`/`D7`）；`INFRA-079t`（compiler-rt builtins，`待开始`——**按需转出**，见「纪律」6）
**状态**：已验证
**阶段进度**：阶段 1（基础设施 + 首份统计）**已验证**（2026-10-15；reviewer `Accepted`）；阶段 2（按统计补服务）/ 阶段 3（全量 + 报告）**已取消** ✗（2026-10-15 用户裁定；「全量」改由 `P3`（`qemu-user`）承接 ✓）

> **`**状态**` 口径**：本任务书 = **一册多阶段验收**（照 `SPEC-142t`/`SPEC-143t`/`INFRA-082t` 先例）⇒ `**状态**` 表**任务级**进度；**收尾（2026-10-15）**：范围重定义后本任务 = 「**`P1` 能力边界度量**」、**阶段 2/3 取消** ⇒ 按**新范围**置 `已验证`（见「§收尾裁定与范围重定义」）。

> **⚠ 大任务申报（规模可能显著，须分阶段）**：本任务**必然包含「补 QEMU syscall 服务」**（见「现实预期」）⇒ 工作量可能远超一般 `t` 任务。**执行纪律**：分期推进、**每批各自留证**；**一旦实际规模大幅超出预期，停下报告**（不蛮干）。**〔2026-10-15 收尾：本节「必然包含补服务」的预判已由用户裁定推翻 —— 不在 `dadao-m1` 上补服务、阶段 2/3 取消 ⇒ 以「§收尾裁定与范围重定义」为准〕**

## 收尾裁定与范围重定义（2026-10-15，`/complete`；architect）

**用户裁定（2026-10-15，渠道 = 经主会话问答；原话，原样引录）**：

- 「**我不需要在dadao-m1上实现另外一套syscall的模拟，没有意义！！！从一开始就没有意义！！！**」
- 「**1、删；2、P1/P2/P3/P4解释一下，我已经不记得了**」（第 1 项 = **撤掉 `dadao-m1` 上的 syscall 服务** ✓；第 2 项 = 主会话已解释 ✓）

**范围重定义（本任务收尾口径；取代本册「三阶段 / 补服务 / 全量」相关表述）**：

1. **本任务 = 「`P1` 能力边界度量」** ✓（产出口径 = 首份分类统计 + 服务缺口归因 + 覆盖边界声明）；**不以「全量通过」为目标** ✗。
2. **阶段 2（按统计补服务）/ 阶段 3（全量 + 报告）取消** ✗；「**全量**」改由 **`P3`（`qemu-user`）承接** ✓（两大测试集全量在 `qemu-user` 上跑 ⇒ 「补服务」需求 ≈ 0；`tools/testcases/run_suite.py` **复用** ✓）。
3. **阶段 1 成果保留为交付** ✓：runner（`tools/testcases/run_suite.py`，**入库**）+ 分类统计（**现场派生、不写死**）+ 报告（逐例结果 / `excluded` 逐条理由 / 覆盖边界声明）。
4. **`dadao-m1` 上的 syscall 服务回退**（用户第 1 项「**删**」）：**实施待落任务**（**本轮未动 `components/qemu/**`** ✗）——明细见 `milestones.md`「M8 任务链」**【待实施】ⓑ**。
5. `ADR-0025 D6` 顺序调整（`P1` → `P3` → `P2` → `P4`）为**待用户确认**项（改已 `Accepted` 的 ADR ⇒ 须**逐条确认**）——见 `milestones.md`「M8 任务链」**【待用户确认】ⓐ**。

## 执行环境
**执行环境**：本地

## 立项来源 / 用户裁定（原话引录）

- **用户要求（2026-10-15；渠道 = 经主会话问答；原话，原样引录）**：
  - 「**musl移植如果顺利完成的话，可以把新增的两个大型测试集都测完**」
- **推断（须显式声明，供用户复核）**：「两个大型测试集」= `TESTCASES-044t` 的 `libc-test` + `LLVM-093t` 的 `llvm-test-suite`；「测完」= **各自跑完并给出统计与报告**（`libc-test` 全量；`llvm-test-suite` 为其锁条目 `role` 所称的 **baseline run**）。**若用户对「测完」的口径有异议 ⇒ 停下报告**。

## 前提与事实（**已核；执行时只作复核、勿重复查证**）

1. **前提已满足 ✓（本任务可开工）**：`P1`（musl **静态**）已完成并 `**已验证**`——`INFRA-082t`（2026-10-15 20:50；阶段 B 静态 musl E2E 跑通：`exit=42` / `hello` / BE-word / `errno` / `tid`，QEMU `-M dadao-m1`）。`llvm-test-suite` 锁条目 `role` 原文 = 「baseline run **deferred until musl static/dynamic works**」⇒ **static 已 works** ⇒ **触发条件成立、可跑**。**动态链接（`P2`）= 未做 ✗**（本任务先静态）。
2. **两测试集均已取源 + 锁定 ✓（`patchless`）**：
   | 测试集 | 锁 `commit` | 模块归属 | 本地检出（执行时 `make fetch` 可重建） |
   |---|---|---|---|
   | `libc-test` | `b7ec467969a53756258778fa7d9b045f912d1c93`（`master` tip，仓无 tag） | **testcases**（用户 2026-10-14 裁定） | `.work/source/<libc-test>` |
   | `llvm-test-suite` | `2919e55176a572ee085cb46b291c47b7092c363e`（annotated tag `llvmorg-23.1.3` 的 **peel**） | **llvm**（用户 2026-10-14 裁定） | `.work/source/<llvm-test-suite>` |
   二者 `patchless = true` ⇒ **不得**改其内容、**无** `patch_dir`/`patch_series`。
3. **工具链/构建已就绪 ✓**：`make install-host`（`clang -target dadao-unknown-elf`）+ `make build-musl`（`INFRA-082t` 落地）⇒ 静态 musl `libc.a` + `crt` 可编可链。
4. **⚠ 现场核（与立项交办描述不同，如实登记）**：`libc-test` 顶层**无独立 `tests/` 目录**（现场 `ls`：`.gitignore AUTHORS COPYRIGHT Makefile README config.mak.def src/`）；用例全部在 `src/{api,common,functional,math,musl,regression}/**/*.c`（各文件自带 `main`）。

## 现实预期（**必须写清，勿许诺全绿 ✗**）

- **QEMU 侧 syscall 服务**（现场：`components/qemu/patches/target/dadao/helper.c.patch`）**只有 5 个**：`write`(64) / `writev`(66) / `exit`(93) / `exit_group`(94) / `set_tid_address`(96)；**其余号一律显式 `-ENOSYS`**（不静默成功）。
- ⇒ **`libc-test` 与 `llvm-test-suite` 会大量撞 `-ENOSYS`** ✗ ⇒ **本任务必然包含「补服务」** ✗ ⇒ **规模可能显著**（故「大任务申报」+ 分阶段）。
- ⇒ **本任务的成功判据不是「全绿」**，而是：**可重复运行 + 诚实的分类统计 + 达标（可用）子集 + `excluded` 逐条有据 + 服务补齐的增量留证**。**不得**把「子集通过」表述为「全量通过」（同 `DADAO-0628` ML-015f/015g 的教训边界，见「参考对照」）。
- **已知外部缺口（会表现为 fail/unsupported，非本任务缺陷）**：`ISS-222`（LLVM 后端 4 类缺口：`%N` inline asm / `"m"` 操作数 / `rotl`·`rotr`·`bswap` ISel / `dynamic_stackalloc`）、`ISS-223`（musl 显式排除 13 源）、`ISS-193`（picolibc 侧同类后端缺口）、`ISS-197`（`"m"` ISel 硬崩）、`ISS-206`（动态重定位编号，`P2`）。**撞上即登记、不静默跳过**。
- **上游/环境性 `excluded`（有据即可）**：动态链接用例（`ldso`/`dlopen`/`tls_*_dlopen`，`P2` ✗）、多线程/进程语义（无内核：`fork`/`waitpid`/信号/scheduler，`ADR-0025 D2` ✗）、`llvm-test-suite` 的 `External/**`（含 `SPEC/` CFP2006/CFP2017，用户口径**已排除**）、Fortran 用例（无 Fortran 前端）、需要文件系统/网络/`/proc` 的用例、`long double` 超出 `binary64` 的用例（`long double ≡ binary64`）。

## 范围

**做（四条）**：
1. **`libc-test` 全量跑（静态）**：自建 runner（落 `tools/testcases/**`、**入库**），把 `src/**/*.c` 用例编/链成静态 ELF/镜像，在 `qemu-system-dadao -M dadao-m1` 下运行，产出**逐用例结果 + 分类统计**。
2. **`llvm-test-suite` baseline run**：取上游 `SingleSource/**` + `MultiSource/**` + `MicroBenchmarks/**`（**排除 `External/**`**）中的可编译/可运行用例，编/链/跑，产出**逐用例结果 + 分类统计**。
3. **按统计逐批补 QEMU syscall 服务**（**本任务主体工作量所在**）：以首份统计为据，分批补 `components/qemu/patches/target/dadao/**` 的 `umon` 服务（口径真源 = `.tao/contracts/contract-syscall.md`）+ **同批同步 musl `arch/dadao/syscall_arch.h` 的 `__dadao_argmask()` 表项**（**不变量**，见「纪律」6）+ 探针/回归扩展。
4. **报告**：两套件各自的可重复运行命令与产物、分类统计、**`excluded` 清单与逐条理由**、覆盖边界声明（子集 ≠ 全量）。

**不做 ✗**：
- **不改** `spec/`、`contracts/`（机器数据）、`.tao/contracts/**`（契约正文）——需要改时**停下请用户裁定**（`docs/Process-02`/`Process-06`）。
- **不改测试集内容**（二者 `patchless`；参考型语料，只读）。
- **不做 `P2` 动态链接**（`ldso`/`.so`/`PIC`/`GOT`·`PLT`；动态用例 = `excluded`）✗；**不做 `P3` `linux-user`** ✗。
- **不为通过而改测试期望 / 放宽判据** ✗（见「纪律」1）。

## 分期结构（三阶段；**每阶段各自验收**）

> **〔2026-10-15 收尾〕阶段 2 / 3 **已取消** ✗（用户裁定；见「§收尾裁定与范围重定义」）——下表阶段 2/3 行**仅供参考**；只有阶段 1 属本任务交付。**

| 阶段 | 名称 | 内容 | 出口判据 |
|---|---|---|---|
| **1** | **基础设施 + 首份统计** | ① 自建 runner（**不复用上游 harness**：`libc-test` 的 `runtest.exe` 用 `fork`/`waitpid`/信号 ⇒ **无内核模型不可用**；`llvm-test-suite` 上游 CMake/lit harness 不跑）；② `libc-test` **静态可跑最小可行子集**；③ `llvm-test-suite` **小 benchmark 子集**；④ 产出**首份统计**（分类计数**现场派生**） | 两套件**各自一条命令可复跑**（真实输出 + 退出码）；首份统计落盘（**分类**：pass / fail / `ENOSYS` / unsupported / compile-error / timeout）；`make check`(L1) rc=0 |
| **2** | **按统计补服务** | 逐批补 QEMU `umon` 服务（**按首份统计排序分批**，如：内存类 `brk`/`mmap`/`munmap`、读类 `read`/`lseek`/`fstat`、文件类 `openat`/`close`、时间类 `clock_gettime`/`gettimeofday`、杂项 `set_robust_list`/`gettid`…—**批序以现场统计为准，不预设**）；**每批**须：注册服务 + **同步 `__dadao_argmask()` 表项**（读指针参数者）+ 探针/回归扩展 | **每批各自留证**（真实命令 + 输出 + 退出码 + 注入态 FAIL 证据）；统计**现场对比改善**（前后两个现场派生计数）；探针/回归绿 |
| **3** | **全量 + 报告** | **全量**跑两套件（除 `excluded`）⇒ 报告（含**明确的 `excluded` 清单与逐条理由**） | 全量命令可复跑；报告含分类统计 + `excluded` 逐条理由 + **覆盖边界声明**；门控按改动类型 L1/L2/L3 |

- **阶段 C 式条件转出（视同子阶段）**：阶段 2/3 若撞 **libcall 缺口**（i128 除法 / FP↔i128 / `bswap` / `*_PARTS` 等）⇒ **当场登记 `issues.yaml` + 转 `INFRA-079t`**（**不得** silently 跳过）；转出后本任务继续推进其余批次。

## 纪律（硬要求 ✗）

1. **不得**为通过而**改测试期望 / 放宽判据** ✗ —— **oracle 独立**（`AGENTS.md`「Independent oracle」）：期望值以**用例自身断言/退出码**与上游语义为准，**不得**从 QEMU/LLVM 反推、**不得**为绕过失败而修改测试集语料或判据。
2. **每个 `excluded` 须有据** ✗（环境限制 / 能力未支持 / 上游明确排除，**逐条写理由**）；**不得**以 skip 掩盖。
3. **动态测试留 `P2`** ✗（本任务先静态）。
4. **失败保留现场并继续推进**（`AGENTS.md`）：自行处置（查证 / 绕行 / **有据重试并记录次数** / 登记后跳过）；**只有在需用户语义裁定**（新决策 / 需授权）时才留问 ✗；**不得**以重试掩盖根因。
5. **大幅超出预期规模时停下报告** ✗（不蛮干）——「大任务申报」见文首。
6. **补服务须同步 `__dadao_argmask()` 不变量**（`lessons §1.53`）：syscall stub 按「参数槽表」选源寄存器（哪些号把指针放 RB 组、第几槽），未列号取默认档（`rb16` 被置 0）⇒ **新增「带读指针参数」的服务必须同批补表项**，否则参数被静默置 0（服务方不解引用时**不可见**）。**该不变量须由运行期断言覆盖**（专写一例读槽表结果），**仅写注释不算落地**。
7. **覆盖 ≠ 语义**：统计计数**现场派生、不写死**；每条断言/用例须有**可达 FAIL** 路径；结论须与真实输出/退出码逐条对齐。
8. **用户裁定落盘**：取得用户裁定须把**用户原话（或问答摘要）原样写入**本任务书（子会话问答对父会话不可见）。

## 接口规范

- **输入**：`ADR-0025`（`D1`/`D2`/`D6`/`D7`）；`.tao/contracts/contract-syscall.md`（`§1` 号表口径 / `§2` `umon` 入口 / `§3` 参数与返回 / `§4` errno / `§5` 独立 oracle 口径 / `§6` QEMU 角色）；`contract-abi.md §1.2`（TP = `rb3`）；`SPEC-140t`；`INFRA-082t`（阶段 A1 遗留 + A2+A3 遗留：**path B** 实现约束 + 原子非真 + `GETFUNCSYM` 等）；`.tao/knowledge/lessons.md §1.53`；两测试集本地检出（**只读**）；`.dadao/` 工具链 + sysroot（**只读**）；`tests/scripts/**`（`bootrom.S`/`dadao.lds` 等既有载体）。
- **输出**：
  1. **runner 与驱动**：`tools/testcases/**`（**新建、入库**；`libc-test` runner 与 `llvm-test-suite` 驱动，可复跑、幂等；**非易失位置**）。
  2. **QEMU 服务补丁**：`components/qemu/patches/**`（树形补丁 + `series`，按 `docs/Process-01`）；**同批**：`components/musl/patches/arch/dadao/syscall_arch.h.patch` 的 `__dadao_argmask()` 表项同步（若该批含读指针参数的服务）。
  3. **构建/门控集成**（`Makefile` / `tools/**`）：新增本任务 target（如快档代表集 + 全量 opt-in，**分层对齐** `docs/Process-07`；**不写死计数**）。
  4. **统计与报告**：逐用例结果 + 分类统计 + `excluded` 清单（落 `.work/log/<模块>/`，被引用者须迁**非易失位置**；本任务书完成区给结论 + 证据路径）。
  5. **验证/证据**：一键证据脚本 `.work/evidence/<任务ID>/run.sh`（含**注入 → FAIL → `cp`+md5 还原 → 回绿**）+ 原始产物落 `.work/log/<模块>/`。
- **约束**：**最小改动**、只碰任务范围；**组件源一律 git 基线**（改 QEMU/musl 只经 `components/**/patches/`，**不得**直接改 `.work/source/`）；**计数不写死**；**证据与期望值独立**。

## 验收标准

1. **两套件各自可重复运行**：给出**一条命令**（+ 完整输出 + 退出码），能重复得到**同值**统计；产物落**非易失位置**（runner 入 `tools/**`；报告与长日志留 `.work/log/<模块>/` + 结论入任务书）。
2. **分类计数现场派生 + 可达 FAIL 证据**：统计（pass / fail / `ENOSYS` / unsupported / compile-error / timeout / `excluded`）由 runner **运行期派生、不写死**；证据脚本能**失败**（注入 ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿，**每条断言有可达 FAIL 路径**）。
3. **每批补服务的探针/回归**：每批服务有专证据（正例 + 反例/边界）；**含 `__dadao_argmask()` 不变量**的运行期断言例（`lessons §1.53`）；不回归既有（L1/L2）。
4. **门控**：按改动类型跑 `make check`(L1)、`make check-modules`(L2)、`make check-full`(L3，里程碑/收尾时)；另 `check-patch-tree`、`check-knowledge-refs`、`check-no-residue`、`check-tasks`、`tools/infra/check_issues.py` 各 rc=0（**以现场输出为准**）。
5. **报告含 `excluded` 清单**：逐条**理由**（环境 / 未支持能力 / 上游明确排除）+ **覆盖边界声明**（「通过的子集 ≠ 上游全量」的表述纪律）。
6. **完成区 ≤30 行、审阅记录每轮 ≤40 行**；完成区与真实输出**逐条对齐**（**禁**转述/估算）。

## 已知事实（供执行，**勿重复查证**；源已标注）

1. **QEMU `umon` 服务**（`INFRA-082t` 阶段 A1 落地，现场核）：入口 = user 模式下 `trap cfx0, 0`（`immu18 = 0` = `SBI_UMON_SYSCALL`）；号在 `rd15`（沿用 RISC-V Linux 编号）；返回 `rd8`；**errno = `rd8` 负值**；参数按类型分 bank（数据 `rd16+n` / 地址 `rb16+n`）。现服务集 = **5 个**（`write`/`writev`/`exit`/`exit_group`/`set_tid_address`）；**其余显式 `-ENOSYS`**。日志标志 = `qemu_log_mask(LOG_GUEST_ERROR, "dadao-m1: umon syscall <nr> not implemented (-ENOSYS)")`。
2. **⚠ 运行必须走「path B」**（`INFRA-082t` 阶段 A1 实现约束，**硬性**）：`-bios` 加载 SEE bootrom（`tests/scripts/bootrom.S` → `bootrom.bin`）+ `-kernel` 加载**扁平镜像**（`llvm-objcopy -O binary` + `tests/scripts/dadao.lds`）在 `user` 模式交接。**禁用** `-kernel <ELF>`（复位态 = `hypv` ⇒ 不触达 `umon` 服务）。
3. **端序 = 大端（BE）**（`ADR-0003 D1`）：上游用例多在 LE 跑 ⇒ **BE 敏感面必须自成一面**（`INFRA-082t` 阶段 B 的 `be_word` 例即此）。
4. **构建命令**：`make install-host`（工具链）→ `make build-musl`（静态 musl `libc.a` + `crt` 落 `.dadao/` sysroot）。`JOBS=8`、**禁全核**（`AGENTS.md`）。
5. **原子非真（单线程语义）**：机器无 LR-SC/`fence` ⇒ `a_cas` 只给单线程语义（`INFRA-082t` 阶段 A2+A3 遗留①）。**单线程用例不受影响**；**多线程/进程语义用例 = `excluded`**。
6. **静态 `__thread` 未打通**（无 `AT_PHDR`/`PHNUM` ⇒ `libc.tls_cnt = 0`；阶段 A2+A3 遗留④）⇒ 依赖 `__thread` 的**静态**用例可能不可用（`excluded`，有据）。
7. **`libc-test` 机制**（现场核）：`Makefile` + `config.mak`（`cp config.mak.def config.mak` 后改 `CROSS_COMPILE`/`CC`/`LDLIBS`）；`CC` 编译、`-static.exe` 走 `$(CC) -static`；**上游 runner = `src/common/runtest.exe`**（`fork`/`waitpid`/`signal`/`setrlimit` ⇒ **无内核模型不可用** ⇒ **必须自建 runner**）；`.err` 文件 = 逐用例运行结果；`make` 汇总 `src/REPORT`。
8. **`llvm-test-suite` 机制**（现场核）：上游用 CMake + lit（`lit.cfg`/`lit.site.cfg.in`）；`External/`（含 `SPEC/`）= **排除**（用户口径）；`SingleSource/**` / `MultiSource/**` / `MicroBenchmarks/**` = 候选面。
9. **`Infra` 视图**：`libc-test` 锁条目 `role` = 「musl/Linux user-space conformance test suite (M8 P1/P2 validation input; no v5 patch set)」；`llvm-test-suite` 锁条目 `role` = 「…baseline run deferred until musl static/dynamic works」。

## 参考对照（`DADAO-0628` / `DADAO`；**只读、只借教训、不复制实现**）

> 来源：`.cache/refs/DADAO-0628/`、`.cache/refs/DADAO/`（只读参考树）。**逐条标注「内容溯源，非执行必需」**。**现场取证（2026-10-15，architect）**：`grep -rIl 'llvm-test-suite\|libc-test'` 在两棵参考树中命中 `DADAO-0628` 的 `manifests/`、`components/llvm-test-suite/patches/series`、`code-agent/tasks/ML-015*.md` 等；**`libc-test` 无用法命中**（`TESTCASES-044t` 已现场 grep 0 命中）。

| 0628 做法 | 本项目差异 | 建议落点 |
|---|---|---|
| `llvm-test-suite` 当 **source-only reference**（`SingleSource` pure-compute）：**不跑上游 CMake/lit harness**，只维护**仓库内 23 个 lit 切片**（QEMU + Gem5 双断言），且**明确「切片 ≠ upstream 全量」**（ML-015f/015g）〔内容溯源，非执行必需〕 | 本项目要跑**上游语料全量**（除 `External/`）；**无 Gem5**（未开工）⇒ 单后端 QEMU；`P1` **无内核** ⇒ 需补 syscall 服务 | 阶段 1 **自建 runner**（不依赖上游 CMake/lit）；阶段 3 报告**显式声明覆盖边界**（**不得**把子集说成全量） |
| 0628 的 `components/llvm-test-suite/patches/series` = **空**（附注「不建上游 harness ⇒ 无需补丁」）〔内容溯源，非执行必需〕 | 本项目 `llvm-test-suite` 锁条目 `patchless = true`（同口径） | 保持**只读**；若某源确需最小修，**先停下请用户裁定**（不得偷塞补丁） |
| 0628 **未使用 `libc-test`**（现场 grep 0 命中）〔内容溯源，非执行必需〕 | 本项目首次接入 | 阶段 1 自建 runner（上游 `runtest.exe` 依赖 `fork`/`waitpid`/信号 ⇒ **无内核不可用**） |

## 跨模块与串行约束

- **跨模块影响（显式登记）**：本任务要改 `components/qemu/**`（**`qemu` 模块面**）与 `components/musl/**`（**`infra` 模块面**）⇒ 按 `AGENTS.md`「模块里程碑与跨模块交互」，**须与相应模块里程碑协调**；若服务补齐成规模，**允许主会话拆分/另立跨模块任务**（本册**不预判**拆分粒度）。
- **同改共享文件 ⇒ 串行**：与任何同改 `components/qemu/**`、`components/musl/**`、`Makefile`、`manifests/components.lock.toml`、`tests/scripts/**` 的任务**一律串行**，不得并行。
- **同一工作树同一时间只允许一个写工作树的子代理**（`AGENTS.md`「并行任务上限」）。

## 硬约束（子代理）

1. **临时目录** `/tmp/opencode/<任务ID>/`；命令一律在 workdir（= 仓库根）内、**相对路径**；**禁**出界 `cd`（`/*`、`~*`、`..*`）；**禁**仓库内临时文件。
2. **不提交 git**（提交权归 architect）；**禁** `git add -A`/`.`（逐路径显式）。
3. **完成区与真实输出逐条对齐**；**禁** `cmd | tee` 吞码（管道取到的是末端退出码）、**禁** `cmd | tail` 接进 `&&`。
4. **只动任务书范围，越界须披露**；**不**改 `spec/`、`contracts/`、`.tao/contracts/**`；**不**改测试集内容（`patchless`）。
5. **失败保留现场并继续推进**（`AGENTS.md`）；**只在需用户语义裁定**时留问；用户裁定须**原话落纸**。
6. **补丁导出纪律**（`docs/Process-01`）：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言。
7. **复杂命令输出留存** `.work/log/<模块>/`；**被引用的材料**不得只放 `.work/`（`check-knowledge-refs`）。
8. **一键证据脚本**：`.work/evidence/<任务ID>/run.sh`（非交互、任一失败非零退出、逐项打印「检查名 + 期望/实际 + rc」、含**可达 FAIL** 自检；**计数不写死**）。
9. **反例注入的还原纪律**：**禁** `git checkout`/`restore`/`stash`/`git show <commit>:<path>` 还原（会清未提交改动）；一律 `cp` 备份 + **md5 对账**，或**优先临时树注入**；`git status`/`git diff` 干净**不作**「已还原」证据。
10. **长任务**：>10 min 者 `setsid nohup … &` 脱离 + 落 `XXX_EXIT=$rc` 完成标记，**一次只跑一个**；子代理**不得**在会话内等待长任务（由主会话承载）。
11. **命令不存在时必须告知，禁止自行换命令**（`AGENTS.md`）。

## 完成区

**测试结果**：阶段 1（只做本阶段）——fast 档 18 例：`pass 16 / fail 0 / enosys 2 / compile-error 0 / timeout 0`，`unsupported 3291`（运行期现场派生）；一键证据 48/48 断言 `rc=0`；L1 `rc=0`、L2 `rc=0`。
**修改文件**：新增 `tools/testcases/run_suite.py`；改 `Makefile`（+2 target `check-testcases-suites`/`check-testcases-suites-full`、`.PHONY`、分层归属注释）。**非入库留档**：`.work/evidence/TESTCASES-045t/run-p1.sh`、`.work/log/testcases/TESTCASES-045t-p1-report.md`、`.work/log/testcases/runs/fast.json`、`.work/log/testcases/TESTCASES-045t-p1-*.log`。
**验收结果**（真实输出节选）：
- `make check-testcases-suites` → `rc=0`；`[libc-test] attempted=9 pass=7 fail=0 enosys=2 compile-error=0 timeout=0 unsupported=116`；`[llvm-test-suite] attempted=9 pass=9 fail=0 enosys=0 compile-error=0 timeout=0 unsupported=3175`；`[enosys-census] syscall:count 29x6 214x2 222x2 56x2 79x1 113x1 169x1`
- `./.work/evidence/TESTCASES-045t/run-p1.sh` → `rc=0`；`TESTCASES-045t/P1 evidence: checks passed=48 failed=0` / `PASS`
- 门控：`make check`(L1) `rc=0`（证据 G 段）；`make check-modules`(L2) `rc=0`（78 s，`module checks (L2): PASS`）；`check-patch-tree`/`check-source-state`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-dirs`/`check_issues.py` 全 `rc=0`
- 二次复跑逐例（id,status,stdout_sha256,exit）与计数**完全一致**（证据 C 段 `yes`）
**新发现/坑**：
1. ENOSYS 的唯一可信信号 = `qemu -d guest_errors`（默认不打印）；但 **`ioctl`(29) 是 musl stdio 的 tty 探测 ⇒ 良性**（6 例照常 `pass`）⇒ 判据必须「以用例自身裁决为主、`ENOSYS` 只作根因归因」，**不得**用「stderr 有 ENOSYS」当判据。
2. 链接 libc-test 的 `src/common/*.o` 必须用**归档语义**（`--start-lib … --end-lib`，等价上游 `-ltest`）：强制包含全部 `.o` 会把 `locale_map.o` 拉进 ⇒ `__mo_lookup` **未定义**（该源被 `arch/dadao/arch.mak` 按 `bswap` 后端缺口排除 = `ISS-223`，**已登记，非新问题**）。
3. 上游语料含 **`.reference_output.small`（93 个）**＝ `SMALL_PROBLEM_SIZE` 的**专属参照**；用错参照会**假 MISMATCH**（`random.c` 首轮即撞）。BE 机器另须优先 `.reference_output.big-endian`（17 个）；`.little-endian`/`.AIX` 面向他机、不查。
4. `int\nmain(`（`ackermann.c` 等）存在 ⇒ 枚举「有无 main」不能用 `"int main"` 字面量；已改用正则 + 「curated 成员必在可尝试面内」一致性断言（当场抓到并修）。
5. 上游 benchmark 默认规模在 dadao-m1 上过大（`fib2` LENGTH=43 >180 s、SMALL(40) ≈48 s；`nestedloop`/`sieve` ≈32 s）⇒ fast 档只收 runnable 项，余者留给 `--stage full --timeout 300`（**非**放宽判据，仅规模/预算）。
6. 建议沉淀知识库：①「用例自身裁决为主 + `ENOSYS` 作根因归因」的分类口径；②「libc-test harness 必须归档语义链接」；③ 上游 `reference_output` 变体优先级（`.small` > `.big-endian` > 默认）。来源 = 本任务（`tools/testcases/run_suite.py`）。
**遗留问题**：阶段 2（按统计补服务）/ 阶段 3（全量 + 报告）**已取消**（**2026-10-15 收尾裁定**，取代原文「未做」；见「§收尾裁定与范围重定义」）——原「阶段 2 首批建议」（`brk`+`mmap` 解锁面最宽）**转为边界度量产出**；`llvm-test-suite` 中无上游参照的 3 个 gcc-c-torture 例 `pass` 口径 = 「跑到退出 0」、非输出等价（**阶段 3 取消** ⇒ 保留为**披露事项**）。

## 阶段记录

### 阶段 1｜基础设施 + 首份统计

**runner（新建、入库）**：`tools/testcases/run_suite.py`（自建：`clang -target dadao-unknown-elf` → `ld.lld -T tests/scripts/dadao.lds` → `llvm-objcopy -O binary` → `qemu-system-dadao -M dadao-m1` **path B**）。Makefile 新增两 target：`check-testcases-suites`（fast 档）/ `check-testcases-suites-full`（全量 opt-in，`--timeout 300`）；**刻意不入 L1/L2/L3**（理由见 Makefile 注释：curated 子集 ≠ `docs/Process-07 §3` 要求的「机械派生」L2 代表集）。

**两条可复跑命令**（仓库根）：
- `make check-testcases-suites` —— 两套件 fast 档，本机 ~6 s；结果 JSON `.work/log/testcases/runs/fast.json`
- `./.work/evidence/TESTCASES-045t/run-p1.sh` —— 一键证据（48 项断言，`rc=0`）

**首份分类统计（runner 运行期派生、**不写死**；18 例 curated，按依赖分层 tier1 纯计算 → tier5 文件系统）**：

| suite | attempted | pass | fail | enosys | compile-error | timeout | unsupported |
|---|---|---|---|---|---|---|---|
| `libc-test` | 9 | 7 | 0 | 2 | 0 | 0 | 116 |
| `llvm-test-suite` | 9 | 9 | 0 | 0 | 0 | 0 | 3175 |
| **total** | **18** | **16** | **0** | **2** | **0** | **0** | **3291** |

- **`enosys` 2 例**：`libc-test:src/regression/malloc-0.c`（`brk`/`mmap`）、`libc-test:src/functional/stat.c`（`openat`/`newfstatat`/`clock_gettime`/`gettimeofday`）。
- **`ENOSYS` 普查**（号→名取自端口自身 `obj/include/bits/syscall.h`）：`ioctl`(29)×6、`brk`(214)×2、`mmap`(222)×2、`openat`(56)×2、`newfstatat`(79)×1、`clock_gettime`(113)×1、`gettimeofday`(169)×1。**`ioctl`(29) = 良性**（musl stdio 的 stdout tty 探测，6 例照常 `pass`）。
- **`unsupported` 逐条理由**（现场 glob/普查派生，**无空类**）：`no main()`（helper/kernel TU）2218、C++ 956、Fortran 28、ObjC 4 + ObjC++ 4、`libc-test` harness 支撑 TU 10、`External/`（含 SPEC，用户口径排除）17、无内核类（线程/进程/IPC/socket/信号）与动态链接/TLS 类（逐条计数见报告表）。
- **子集选择依据**：两套件各按「依赖从简到难」分层取样（tier1 纯计算 / tier2 stdio+FP / tier3 堆 / tier4 时间 / tier5 文件系统），逐例 `why` 记录在 runner 内 + 报告表；判据 = 用例自身（`t_status`）或上游 `.reference_output`（BE 优先 `.reference_output.big-endian`；`SMALL_PROBLEM_SIZE` 构建用 `.reference_output.small`）——**不作任何期望放松**。
- 逐例结果 / `excluded` 逐条理由 / 覆盖边界声明 / 阶段 2 信号：`.work/log/testcases/TESTCASES-045t-p1-report.md`（**本机留档，不入库**）。
- **门控**：`make check`(L1) `rc=0`；`check-patch-tree` / `check-source-state` / `check-no-residue` / `check-tasks` / `check-knowledge-refs` / `check-dirs` / `tools/infra/check_issues.py` 全 `rc=0`（证据脚本 G 段）；`make check-modules`(L2) `rc=0`（78 s）。
- **可达 FAIL（三条独立路径，真实输出）**：① `--inject` ⇒ `pass=0 / fail=18 / rc=1`；② 「参考输出读取器」注入 ⇒ `hello` 由 `pass` 变 `enosys`（`matched=False`），`cp`+md5 还原 ⇒ 回 `pass`；③ 「ENOSYS 匹配器」注入 ⇒ `malloc-0` 由 `enosys` 变 `fail` 且 `rc=1`，还原 ⇒ 回 `enosys`+`rc=0`。
- **未撞 `ISS-222`**（fast 档 `compile-error=0`）⇒ 无新 `issues.yaml` 登记；现场观察「`libc.a` 含 `locale_map.o` 但缺 `__mo_lookup.o` ⇒ 用到即链接期未定义」**已被 `ISS-223` 覆盖**（arch.mak 显式排除的 `bswap` 后端缺口，非新问题）。
- **阶段 3 规模判断**：`--stage full --list` = libc-test 346 + llvm-test-suite 2133 = **2479 例**可尝试面；本机单例 ≈ 0.02 s（QEMU）+ ≈ 0.1 s（编译）量级 ⇒ 全量一轮约 **10~20 min**（与 `check-picolibc-tests-full` 同量级），适合 opt-in 而非 L2。

### 阶段 2｜按统计补服务

**（已取消 ✗ —— 2026-10-15 裁定：不在 `dadao-m1` 上补 syscall 服务；见「§收尾裁定与范围重定义」）**

（待填写：**逐批**记录——批内容 / 服务号 / `__dadao_argmask` 同步 / 探针与回归 / 统计前后对比）

### 阶段 3｜全量 + 报告

**（已取消 ✗ —— 2026-10-15 裁定：「全量」改由 `P3`（`qemu-user`）承接；见「§收尾裁定与范围重定义」）**

（待填写：全量命令 / 分类统计 / `excluded` 清单与逐条理由 / 覆盖边界声明 / 门控 rc）

### 阶段 1 规模度量与下一步建议（architect 追加，2026-10-15；**只追加**）

**规模判断（针对阶段 3 `full` 档）**：`--stage full --list` 可尝试面 = libc-test 346 + llvm-test-suite 2133 = **2479 例**；本机量级单例 ≈ **0.02 s（QEMU 运行）+ ≈ 0.1 s（编译）** ⇒ 全量一轮约 **10–20 min**（与 `check-picolibc-tests-full` 同量级）⇒ **适合 opt-in，不入 L1/L2/L3**（与 `docs/Process-07 §3`「L2 代表集须机械派生」一致）✓。

**阶段 2 批序建议（首份统计的直接推论）**：**最宽收益的下一步 = 补 `brk` + `mmap`** ✓（`malloc-0` 一例即同时吃这两号，可连带解锁「堆类」用例）；**含进程 / 信号类的用例（`fork`/`waitpid`/信号）永远需 `P3`** ✗ —— 非本任务（`P1` 静态 / `P2` 动态）所能覆盖，须作为 `excluded` 的**逐条理由**之一。

**（C）两步走建议 —— 已裁定（2026-10-15）✓（原「**待用户裁定**」已解除；原话见「§收尾裁定与范围重定义」）**
1. **阶段 2 不再「只补 `brk` + `mmap`」** ✗：**不在 `dadao-m1` 上补任何 syscall 服务**（用户原话「**我不需要在dadao-m1上实现另外一套syscall的模拟，没有意义！！！从一开始就没有意义！！！**」）⇒ `brk`/`mmap` 等 `enosys` 归因**保留为边界度量产出**（正是本任务第 1 项的用途）。
2. **本任务收窄为「`P1` 边界度量」** ✓（产出口径 = 首份分类统计 + 服务缺口排序 + 覆盖边界声明，**不以「全量通过」为目标**）；**另立 `P3`（`qemu-user`）任务**承接进程 / 信号 / 文件系统类语义 ✓。
3. **阶段 2/3 取消** ✗、「全量」改由 `P3` 承接 ✓、「`dadao-m1` 服务回退」**待实施**（用户「**1、删**」）⇒ 明细见「## 收尾裁定与范围重定义」+ `milestones.md`「M8 任务链」。

## 审阅记录

（按轮次追加；每轮 ≤40 行）

#### 第 1 轮 engineer 自审

**方式**：自主逐行审查（全文）`tools/testcases/run_suite.py` + `.work/evidence/TESTCASES-045t/run-p1.sh`，并以实机复跑取证。**判决**：无未修 finding（下表 11 条）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 死常量 `FAST_STAGE_BENCH_BUDGET_S` 定义未用 | ✅已修 | 删除，理由并入 `SMALL_PROBLEM_CFLAGS` 注释（含实测 48 s/32 s） | 删后 fast/full `--list` 与运行 `rc=0` |
| F2 `reference_for` docstring 列 LE/AIX 变体却只查 3 种，易误导 | ✅已修 | docstring 写明各变体现场计数与「LE/AIX 面向他机、刻意不查」 | 同上 |
| F3 `.small` 与 `.big-endian` 若同存则优先级歧义 | ✅已修（无需改序） | 现场核对两集合**无交集**，结论写入 docstring | `for f in *reference_output.small; do [ -f "${f%.small}.big-endian" ]` ⇒ 0 命中 |
| F4 `--only` 的 unknown 判定在过滤之后计算 ⇒ **任何** `--only` 都报 unknown | ✅已修 | 改为按全体 suite 选择面的**并集**判定，过滤移到 `main` | 跨 suite `--only` `rc=0`（1 例 `pass`）；未知 id `rc=2` |
| F5 「参考比对是否真读上游文件」验证方式（避免改只读语料） | ✅已证 | 不改 `.work/source/**`，改为对 **runner 自身**注入（E/F 段） | 注入 ⇒ `matched=False`、`hello` 不再 `pass`；`cp`+md5 还原 ⇒ `matched=True`、`rc=0` |
| F6 枚举「有无 main」用 `"int main"` 字面量 ⇒ 漏 `int\nmain(`（`ackermann.c`） | ✅已修 | 引入 `MAIN_RE = \b(?:int\|void)\s+main\s*\(` +「curated 成员必须在可尝试面内」断言（缺失即 exit 2） | 断言当场抓到 `ackermann.c`；修后 full 枚举 1058 → **2133** |
| F7 guest stdout/stderr 走 PIPE ⇒ 超时/巨量输出丢现场、内存无界 | ✅已修 | 落盘 `<case>.stdout/.stderr`；超时也保留 partial 并写入 JSON | `--timeout 1` ⇒ `rc=1` 且 JSON 含 `detail/stdout_len/stdout_sha256`；证据新增「failure scene kept on disk」PASS |
| F8 `--inject` 用固定哨兵期望值会与真实退出码撞车（2 例真 `exit 1` ⇒ 假 `pass`） | ✅已修 | 注入期望改为**运行后派生** `(exit_code+1)&0xFF`（构造上必不等） | 注入态由 `pass=2/fail=16` → **`pass=0/fail=18`、`rc=1`** |
| F9 `unsupported` per-file 记录不含 scan face 之外的 `External/`（与类别计数不一致） | ✅已修 | `enumerate_all` 先并入声明 glob 命中（含 `External/`）再补 scan face 普查 | 计数 3158 → **3175**，与类别表 17 条对齐；报告直方图合计 3291 |
| F10 `--stage full` 文件命名 stem 会否超长 | ❌不修（无需） | — | 现场测最长 stem **98** 字符（限 255） |
| F11 杂项：`import os` 在函数内、`common_log` 未使用、`--strict` help 文案错 | ✅已修 | `os` 移模块头；`common_log` 写入 JSON；help 文案改正 | `python3 -m compileall tools` + L1 `rc=0` |

**自审后复验**：改毕重跑 `run-p1.sh` ⇒ `checks passed=48 failed=0`、`PASS`；`make check-testcases-suites` ⇒ `rc=0`。

#### 第 1 轮 reviewer 验收

**方式**：`TESTCASES-045t-P1`@`a3a7aea`（验收前 `git status --porcelain -uall` 空）；fast 档/门控/证据脚本全部**自跑**；还原一律 `cp`+md5（无 git 还原）。注：复跑会按脚本同名重写 `.work/log/testcases/TESTCASES-045t-p1-*`（原件已备份 `/tmp/opencode/TESTCASES-045t/review-p1/eng-logs-backup/`）。

**重跑记录（真实输出/rc）**：
- `make check-testcases-suites` → `rc=0`；`[libc-test] attempted=9 pass=7 fail=0 enosys=2 compile-error=0 timeout=0 unsupported=116`；`[llvm-test-suite] attempted=9 pass=9 … unsupported=3175`；`[total] attempted=18 pass=16 … unsupported=3291`；`[enosys-census] 29x6 214x2 222x2 56x2 79x1 113x1 169x1` ⇒ 与完成区 `7/9`、`9/9`、`16/18`、census **逐项一致**；计数由 runner 运行期 `counts[status]+=1` + glob 派生（核源码：无写死）。
- `--stage full --list` → `2479`（libc-test 346 + llvm-test-suite 2133，`cut|uniq -c` 现场数）= 规模度量 ✓。
- 门控自跑：`make check`(L1) `rc=0`（`repository checks (L1): PASS`）；`check-patch-tree`/`check-source-state`/`check-component-changelog`/`check-no-residue`/`check-tasks`/`check_issues.py` 各 `rc=0`；`make check-modules`(L2) `rc=0`（79 s，`module checks (L2): PASS`）。
- `./.work/evidence/TESTCASES-045t/run-p1.sh` → `rc=0`；`checks passed=48 failed=0`/`PASS`（48 条 `[PASS]` 自数核）。

**约束核验**：
1. **不改测试集源码** ✓：`git -C .work/source/{libc-test,llvm-test-suite} status --porcelain` 均**空**、HEAD = `b7ec467…`/`2919e551…` = 锁 commit（跑前跑后各核一次）；runner 写路径仅 `.work/build/**` 与 `--json-out`（grep `write_text/open/mkdir` 核），套件树只读。
2. **enosys 归因** ✓：与 QEMU `guest_errors` 现场逐例对齐——`malloc-0`→`[214,222]`(brk/mmap)、`stat`→`[56,79,113,169]`(openat/newfstatat/clock_gettime/gettimeofday)；`ioctl(29)×6` **良性**（6 例照常 pass；`time.c` 带 `[56,214,222]` 亦 pass）⇒ 「用例自身裁决为主、ENOSYS 仅归因」口径正确。
3. **unsupported 逐条有据** ✓（≥4 类抽查 + 独立重数对齐）：no-main 2218 / C++ 956（`find`=956）/ Fortran 28（=28）/ ObjC 22+4 / `External/` 17（=17）/ harness TU 10（=10）；每类均有明确理由、无空类（`[exclusion-empty]` 0 条）。
4. **oracle 独立** ✓：llvm 例用**上游 `.reference_output*`**（现场 ls 确在；`random` 按 SMALL 用 `.small`，比对=逐字节 stdout+exit）；`libc-test` 以用例自身 `return t_status`（`print.c: volatile int t_status`）为准；3 个 gcc-c-torture 无上游参照 ⇒ 「exit 0 即跑完」口径已在报告+遗留**显式披露**，非我方私定期望值。
5. **opt-in 定位** ✓：两 target 未入 `check`(L1)/`check-modules`(L2)/`check-full`(L3)（行 497/504/508 核）；注释理由与 `docs/Process-07` line 40「代表集必须机械派生，禁止手工挑」相符。
6. **完成区对齐** ✓：统计/census/48 断言/rc 与我自跑一致；「修改文件」= Makefile + `tools/testcases/run_suite.py` + 任务书，与 `git show --stat a3a7aea` 一致；阶段 2/3 确未做（阶段记录留白）；`(C)` 确标「**待用户裁定**（未定）」。
7. **reviewer 新反例（不在 engineer 三条内）**：注入分类判据「无上游参照用例期望退出码 0→1」⇒ 同一 `run-p1.sh` **`rc=1`、`passed=41 failed=7`**（`fast stage: fail count expected=0 actual=9`；F 段 `malloc-0 expected=fail actual=pass` 连带红）⇒ `cp`+md5 还原（`4463b909…` 前后相等）⇒ 复跑 `rc=0`、`48/48` **回绿**；终态两套件源树仍空、HEAD 未变。

**判决：Accepted**（阶段 1 达标；阶段 2/3 留后续，`(C)` 两步走建议维持「待用户裁定」）。
