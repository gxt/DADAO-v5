# INFRA-082t: musl 静态最小集移植（`P1`：静态可运行）

**模块**：infra
**项目里程碑**：M8
**依赖**：`ADR-0025`（M8 路线；`D6` = `P0 契约 → P1 musl 静态 → P2 动态 → P3 linux-user → P4 对照/回归`、`D2` = **无内核目标**、`D3` = musl 自带 `ldso`〔**P2**〕、`D4` = musl 与 picolibc **并存**）；`ADR-0027 D5`（compiler-rt builtins = **独立库、picolibc/musl 共用**）；`INFRA-076t`（musl 1.2.6 取源与锁定，`已验证`）；`SPEC-138t`（syscall 映射契约，`已验证`）；`SPEC-140t`（TLS 硬依赖查证，`已验证`）；`INFRA-079t`（compiler-rt builtins 接入，**`待开始`**——**可能须先于本任务**，见「依赖与先后」）；`INFRA-057t`（picolibc 移植/构建集成的**形态先例**，**只读**）；`docs/Process-01`（组件补丁组织与构建编排）
**状态**：待开始

> **改号留痕（2026-10-15，architect；分支 `p1-renumber`）**：本任务书**原号 `INFRA-081t` ✗ ⇒ 今号 `INFRA-082t` ✓**。
> **理由 = 避「git 历史同号」**：`INFRA-081t` **历史上**曾指 `libc-test` 任务（`1dc0570` 内 `.tao/tasks/infra/INFRA-081t-libc-test取源与锁定.md`，后经 `R089` 改名 `TESTCASES-044t` 而离开 `master`）⇒ 若本册沿用 `081`，则**同一编号在仓库历史中指两件事**，违背 `.tao/knowledge/lessons.md §3.21`「编号须**全仓（含历史）唯一**」精神；`082` 经 `git grep`（工作树）+ `git log --all --name-only`（全历史）复核**从未被占用** ✓。
> **范围未变**：仅**编号**变更，任务目标/范围/验收标准**一字未改**。
> **下文「architect 立项提交留痕」中出现的 `INFRA-081t-*`（立项提交 `159bc42` 时的文件路径 / 门控日志名）属历史留档**，按 `lessons §4.1`（历史快照旧路径**保留、不回溯更新**）**保留原字** ✓——即**可审计**（与 `git show 159bc42 --name-status` 一致）。

## 执行环境
**执行环境**：本地

## 立项来源 / 用户裁定

- **来源 = `ADR-0025 D6` 的 `P1` 段**（`P0 契约 → P1 musl 静态 → P2 动态链接 → P3 qemu-linux-user → P4 对照/回归`）。**`P0` 已落地**（`SPEC-138t`/`SPEC-139t` 均 `已验证`）⇒ **`P1` 可立**。`ADR-0025 D2`：**无内核目标**（VFS / MM / 调度 / 信号都不做）。
- **用户裁定（2026-10-15，渠道 = 经主会话问答，原话）**：「**立**」⇒ 立本任务书。
- **用户后续要求（2026-10-15，渠道 = 经主会话问答，原话原样引录）**：「**musl 移植如果顺利完成的话，可以把新增的两个大型测试集都测完**」⇒ 登记为**后续依赖任务**（见下）。
- **本任务不做**：动态链接 / `ldso`（`P2` ✗）、`QEMU linux-user`（`P3` ✗）、完整 `__thread`/TLS 重定位语义（`P2` ✗）、内核（`D2` ✗）、picolibc 侧改动（并存，`D4` ✗）。

## 范围（`P1` = **静态最小集** ⇒ 判据 = 「**静态可运行**」）

**做（三条）**：
1. **musl 静态最小集移植**：`arch/dadao/` 骨架（顶层 `atomic_arch.h` / `crt_arch.h` / `kstat.h` / `pthread_arch.h` / `reloc.h` / `syscall_arch.h` + `bits/` 7 头）+ `src/*/dadao/`（`.s`/`.S`）+ **crt**（`crt1` / `crti` / `crtn`）+ **syscall stub** + **TLS 就位**。移植面清单**真源 = `INFRA-076t §实测移植面`**（riscv64 底座 = `.s`/`.S` **12** + `arch/riscv64/` **13**；DADAO 预计**同形**），**不复制实现**（参考仓 `DADAO-0628` 只借教训）。
   - **syscall stub（口径真源 = `.tao/contracts/contract-syscall.md`）**：号在 **`rd15`**、**沿用 RISC-V Linux 编号**（`§1.1` + `ADR-0025 D1`）；发起 `trap cfxha, immu18`，**`umon`（`cfx0`）路径 `immu18 = 0`**（`SBI_UMON_SYSCALL`，`§2`）；参数 `rd16–rd31`/`rb16–rb31`/`rf16–rf31`、返回 **`rd8`**（`§3`）；**errno = `rd8` 负值（`-errno`）**（`§4`，用户 2026-10-14 裁定 **A**）⇒ **musl `__syscall_ret()` 零改**；返回经 `escape cfxha, [excp_cause_ip, 4]`（`§2`）。
   - **TLS/TP（硬依赖，`P1` 阻断项；真源 = `SPEC-140t`）**：**TP + 含 `struct pthread` 的 TCB/TLS 区无条件必需**（`errno`/`exit`/stdio 锁/取消点 syscall 全经 `__pthread_self()`；`__init_tls` 无 `if`、失败 `a_crash()`）⇒ 须落 `arch/dadao/pthread_arch.h`（`__get_tp()`）+ `src/thread/dadao/__set_thread_area.s` + 启动期建 TLS/写 TP；**TP 寄存器 = `rb3`**（`contract-abi §1.2`；⚠ 参考仓 `DADAO-0628` 用 `rb4`，**不可照搬**）。`TLS_*` 重定位（`DTPMOD`/`DTPOFF`/`TPOFF`/`TLSDESC`）= **条件依赖，`P1` 静态无 `__thread` ⇒ 不触发**。
2. **产出静可运行的「最小程序」E2E**：至少 `hello`（写路径 → `write`）与 `exit`（`exit`/`exit_group`）**端到端跑通**，退出码/输出正确。
3. **（不做项，显式登记）**：动态链接 / `.so` / `ldso` / `PIC` / `GOT`·`PLT`（`P2` ✗）；`QEMU linux-user`（`P3` ✗）；信号 / 线程完整语义（按 `SPEC-140t`「P1 只需 TP+TCB」界定，其余归 `P2+` ✗）。

## 依据（口径真源；**引用，不复制正文**）

- **syscall 映射**：`.tao/contracts/contract-syscall.md` `§1`（号在 `rd15` + 沿用 RISC-V 编号）/ `§2`（`umon`/`jmon` 入口）/ `§3`（参数与返回 `rd8`）/ `§4`（**errno = `rd8` 负值**，已裁定 A）/ `§5`（独立 oracle 口径）/ `§6`（QEMU 角色与边界）/ `§7`（裁定清单）；`ADR-0025 D1`/`D2`/`D6`。
- **TLS**：`SPEC-140t §结论` + `§证据表`（`文件:行` 逐条）；`contract-abi.md §1.2`（`rb3` = TP）。
- **builtins 归属**：`ADR-0027 D5`（**独立「DADAO compiler-rt builtins」库**，**picolibc 与 musl 共用同一份**，不属任何 libc）。
- **移植范围/教训（`DADAO-0628`，**内容溯源，非执行必需**）**：`INFRA-076t §参考对照` 的 9 条教训清单（`arch/dadao` 骨架不足以产出可链接 libc / `reloc.h` `CRTJMP` 专修 / `pthread_arch.h`+`get_tp`+`__set_thread_area` 硬依赖 / `crt_arch.h`+`arch.mak` override `__libc_start_main` / RB 寄存器组指针 / `O0` 变通非终态 / 软浮点垫片 / `AT_PAGESZ` auxv 立即数溢出 / `__int128` 算术库）。**只借判断，不复制代码。**
- **补丁/构建形态先例**：`INFRA-057t`（picolibc：真移植补丁集 + 构建集成 + syscall stub 映射），**只读**。

## 依赖与先后

- **已满足**：`INFRA-076t`（musl 1.2.6 入锁：`commit 9fa28ece…`、`shallow_ref="v1.2.6"`、**`patchless = true`**）、`SPEC-138t`（契约）、`SPEC-140t`（TLS 判据）。
- **可能须先落地**：`INFRA-079t`（compiler-rt builtins；`待开始`）——若 `P1` 链接期撞 i128 除法 / FP↔i128 / `bswap` / `*_PARTS` 等 libcall 缺口，则须先有独立 builtins 库；**先后关系由主会话按实测缺口排定**（见「待确认项 ②」）。
- **串行约束**：与任何同改 `components/musl/**`、`manifests/components.lock.toml`、`Makefile` 的任务**串行**（不得并行）。

## 已知事实（供执行，**勿重复查证**；源已标注）

1. **musl 版本/锁**（`INFRA-076t`，已验证）：`1.2.6`，`commit = 9fa28ece75d8a2191de7c5bb53bed224c5947417`，`shallow_ref = "v1.2.6"`（lightweight tag），**`patchless = true`**，`role` = M8 libc 底座；源码检出 `.work/source/<musl>/`（`.work/` 可重建区）。
2. **`patchless` 的含义**（`manifests/components.lock.toml` 注释）：**尚无** v5 的 `arch/dadao` 补丁集；门控据此接受**缺** `patch_dir`/`patch_series`；**一旦落地首个 `arch/dadao` 补丁，须在同一提交里去掉 `patchless` 并补两字段**（不得夹带）。
3. **验证机**：`spec/Machine-01-测试机运行环境.md`（`dadao-m1`）——RAM/ROM 布局、`trap`/`escape` 流程、**semihosting 服务表（完整 25 个，含 `SYS_WRITE`/`SYS_EXIT_EXTENDED`/`SYS_HEAPINFO`）**、停机协议 = `SYS_EXIT`。QEMU 现状 = **仅 system 模式**（`qemu-system-dadao -M dadao-m1`）。
4. **⚠ 现场缺口（本任务书立项时实测，属 `P1` 的**范围/归属**问题）**：`dadao-m1` 机体现有实现**只覆盖**「一般 `trap` → cfx 向量」与「semihosting 短路（`immu18[17:16] == 2'b11`）」两条路径（`components/qemu/patches/target/dadao/{helper.c,insn_trans/trans_ctrl.c.inc}.patch`）；**未实现** `immu18 != 2'b11` 的 `umon` syscall 分发服务方（`SBI_UMON_SYSCALL`）⇒ **谁为 `P1` 的 `trap cfx0,0` 提供 Linux 语义服务**是必须先定的口径（选项见「待确认项 ①」）。
5. **端序 = 大端（BE）**：`ADR-0003 D1`（`EI_DATA = ELFDATA2MSB`）；`AUDIT_ARCH_DADAO` = BE64（`contract-syscall §1.3`）；上游测试多在 LE 跑 ⇒ **BE 敏感用例必须自成一面**。
6. **工具链**：`clang -target dadao-unknown-elf`（`.dadao/cross-toolchain/**`）；`long double` ≡ `binary64`；`__int128` 支持但**工具链不提供 libgcc/compiler-rt builtins**（`INFRA-078t` 已查证）。

## 接口规范

- **输入**：`ADR-0025`（`D2`/`D3`/`D4`/`D6`）、`ADR-0027 D5`、`.tao/contracts/contract-syscall.md`、`contract-abi.md §1.2`、`SPEC-140t`、`INFRA-076t`（含 `§实测移植面`/`§参考对照`）、musl 源码检出（**只读**）、`.dadao/` 工具链 + sysroot（**只读**）、`.dadao/tests/harness/**`（验证载体）。
- **输出**：
  1. **musl 移植补丁集**：`components/musl/patches/**`（**一文件一补丁**，镜像上游仓内路径）+ `components/musl/series`；**同一提交**去掉锁条目 `patchless` 并补 `patch_dir`/`patch_series`；形态与纪律按 `docs/Process-01`（树形补丁集 + `git apply` + `check-patch-tree` 机械校验）。
  2. **构建集成**（`Makefile` / `tools/infra/**`）：`clang -target dadao-unknown-elf -static` 构建 musl 静态库 + crt，落点按 `ADR-0016`（`.dadao/cross-toolchain/**` / sysroot）；target **可复跑、幂等**。
  3. **最小 E2E 程序**：`hello` + `exit`（源与构建脚本入仓库、落 `tools/<module>/` 或 `tests/`，**非易失位置**；临时产物落 `/tmp/opencode/<任务ID>/`）。
  4. **验证/证据**：一键证据脚本 `.work/evidence/<任务ID>/run.sh`（含**注入 → FAIL → 还原 → 回绿**）+ 原始产物落 `.work/log/infra/**`；本任务书完成区 + `milestones.md` 流水行。
- **约束**：**最小改动**、只碰任务范围；**不得**改 `spec/`（`docs/Process-06` / `ADR-0012 D4` 须用户事先授权）、`contracts/`、`.tao/contracts/**` 机器数据与正文；**不得**做 `P2`/`P3` 内容（不做 `ldso`/`linux-user`）；**组件源一律 git 基线**（改 musl 源只经 `patches/`，不得直接改 `.work/source/`）；**计数不写死**；**证据与期望值独立**（`contract-syscall §5`：不从 QEMU/LLVM 反推）。

## 验收标准

1. **静态可运行（E2E，主判据）**：`hello` 与 `exit` **真实跑通**——留**真实命令 + 完整输出 + 退出码**（禁 `cmd | tee` 吞码）；`exit` 的退出码须**忠实传播**到宿主 `$?`（`Machine-01 §5.5`）。
2. **契约逐条对齐**（`grep`/反汇编可证）：syscall stub 的**号来源 = `rd15`**、**沿用 RISC-V 编号**、入口 `immu18 = 0`、返回 `rd8`、**errno = `rd8` 负值**；与 `contract-syscall §1–§4` **逐条对齐**，**不自选** B/C 口径。
3. **TLS/TP 就位（`P1` 阻断项）**：`arch/dadao/pthread_arch.h` 的 `__get_tp()` 读 **`rb3`** + `__set_thread_area` 写 `rb3` + 启动期 TLS/TCB 建立；`errno`（经 `__pthread_self()`）在 E2E 中**可用**（给出证据，如故意触发一次 errno 路径）。
4. **独立 oracle + 端序**：期望值**独立派生**（不从 QEMU / LLVM 反推；口径 = `contract-syscall §5`）；**BE 敏感**用例至少 1 例并留证（我们是大端，上游多在 LE）。
5. **`patchless` 收口**：若已落 `arch/dadao` 补丁 ⇒ 同一提交内**去掉 `patchless` 并补 `patch_dir`/`patch_series`**；`make check-patch-tree` rc=0。
6. **门控**：`make check`（L1）/ `check-knowledge-refs` / `check-knowledge-dir` / `check-no-residue` / `make check-tasks` / `python3 tools/infra/check_issues.py` 各 **rc=0**（各留**自身**真实 rc）。
7. **证据脚本**：`.work/evidence/<任务ID>/run.sh` 可跑通，**每条断言有可达 FAIL 路径**（注入反例 ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿；**禁** `git checkout/restore/stash`）。
8. **待确认项**：三项（下）**须在开工前取得用户裁定**；取得后**用户原话（或问答摘要）原样写入本任务书**。

## 待确认项（**开工前须用户裁定**）

| # | 项 | 我的默认（**待用户确认**） | 备选/影响 |
|---|---|---|---|
| ① | **验证环境 / 判据**（含「谁提供 `umon` syscall 服务」） | 用**现有 QEMU 的 `dadao` 机器**（`Machine-01` 测试机，`-M dadao-m1`）跑静态 musl 程序；判据 = **退出码/输出正确** + **独立 oracle**（不从 QEMU/LLVM 反推）+ **端序 = 大端** | 见「已知事实 4」：机体现**无** `umon` syscall 服务方 ⇒ 需定 **(a) 本任务自带最小 SEE 侧 syscall 服务**（以 semihosting `SYS_*` 为底座，落 bootrom/固件）／**(b) 由 `P3` `linux-user` 承担**（则 `P1` 验收环境须改写，且 `P1`/`P3` 边界重划）／**(c) 其它** |
| ② | **是否需 `compiler-rt` builtins 支撑**（⇒ 与 `INFRA-079t` 的**先后**） | 先按「**撞缺口才引入**」：`P1` 实测缺 libcall 则**先落 `INFRA-079t`**（独立库，`ADR-0027 D5`）再回本任务 | 若不引入，则须**显式限定**最小集不触发 i128 除法 / FP↔i128 / `bswap` / `*_PARTS`（并在任务书登记该限定） |
| ③ | **musl 源改动方式**（`patchless` 现状 vs 需补丁） | 预计**需补丁**（`arch/dadao` 骨架 + `src/*/dadao/` 必是新增文件）⇒ 按 `docs/Process-01` 建 `components/musl/patches/**` + `series`，**同步去掉锁条目 `patchless`** | 若改 **`patchless` 口径本身**（如允许其它载体）⇒ **另议**（`INFRA-076t` 已写明「同一提交去掉 `patchless`」，与「另起载体」冲突时须用户裁定） |

## 后续依赖任务（用户 2026-10-15 要求；**不在本任务范围**）

- **`TESTCASES-044t`**（`libc-test` 取源与锁定，`待开始`）⇒ 其后 **`libc-test` 全量跑**；
- **`LLVM-093t`**（`llvm-test-suite 23.1.3` 取源与锁定，`待验收`）⇒ 其 **`llvm-test-suite` baseline run**（该任务 `role` 已写明「`baseline run deferred until musl static/dynamic works`」；「§基线跑触发条件」= **musl 静态/动态链跑通之后**）。
- **触发条件**：以上两项**均在 `P1`（或 `P2`）跑通之后**（用户原话「**musl 移植如果顺利完成的话，可以把新增的两个大型测试集都测完**」）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

#### architect 立项提交留痕（2026-10-15，分支 `p1-taskbook`）

- **档位**：**正常提交**——本提交为**规划产物立档**（用户 2026-10-15 原话「**立**」，渠道 = 经主会话问答），**非 engineer 实现、无 reviewer 判决适用**；提交信息按用户指定。
- **提交号**：`159bc42`（「立 P1：musl 静态最小集移植任务书（ADR-0025 D6）+ 登记后续两大测试集全量（用户裁定）」）。
- **文件集对账**（`git diff --cached --name-status` = **2 项** vs 本任务书范围）：① **新增**本任务书 `.tao/tasks/infra/INFRA-081t-musl静态最小集移植.md`〔**立项提交 `159bc42` 时的历史路径**；2026-10-15 改号为 `INFRA-082t-musl静态最小集移植.md`，见文件头「改号留痕」〕；② **修改** `.tao/knowledge/milestones.md`（流水行 + M8 规划区条目，**architect 台账职责**）⇒ **无漏提、无多提、无越界**（**未动** `spec/` / `.tao/contracts/` / `manifests/` / 组件补丁 / `tools/`；`.work/**` gitignored 不入库）。
- **取号依据**（**立项时取 `INFRA-081t` ⇒ 2026-10-15 改号 `INFRA-082t`**，见文件头「改号留痕」）：扫 `.tao/tasks/infra/**` + `.tao/archive/**` 全量，**占用最大 = `INFRA-080t`** ⇒ 取 **`081`**；**`master` 现状无 `INFRA-081*` 文件 ⇒ 未被占用**（注：该号**历史**上曾被 `libc-test` 任务占用、后经 `1dc0570`（`R089`）改名释放为 `TESTCASES-044t` ⇒ 本册与其**无关联**；**改号后 `081` 不再被任何现存任务占用** ✓）。
- **门控**（各捕**自身** rc，无 `tee` 吞码）：`make check`（L1）= **0** / `check-knowledge-refs` = **0** / `check-knowledge-dir` = **0** / `check-no-residue` = **0** / `check-tasks` = **0**（②「已立未开工」计数含本任务）/ `python3 tools/infra/check_issues.py` = **0**；日志落 `.work/log/infra/INFRA-081t-gate-*.log`（**立项时留档名**，`.work/` 可删区）。
- **`push`**：**未做**（本角色**禁** `push`；`master` 落地由主会话在 `/complete` 后执行）。

#### architect 改号留痕（2026-10-15，分支 `p1-renumber`）

- **改号**：`INFRA-081t` ✗ ⇒ **`INFRA-082t`** ✓（`git mv` 任务书 + 全文件编号同步）。**理由**：避**历史同号**——`INFRA-081t` 历史上曾指 `libc-test` 任务（`1dc0570` 内 `INFRA-081t-libc-test取源与锁定.md`，经 `R089` 改名 `TESTCASES-044t` 离开 `master`）⇒ 沿用 `081` 即**同一编号在历史中指两件事**，违背 `.tao/knowledge/lessons.md §3.21`「编号须**全仓（含历史）唯一**」；`082` 全仓（工作树 + 全历史）复核**从未被占用** ✓。
- **同步面**（`git grep -n 'INFRA-081t'` 现场全仓查证，共 **7 处**）：任务书内 **4 处**（① 标题 ② 文件集对账的路径引用 ③ 取号依据 ④ 门控日志名）+ `milestones.md` **3 处**（① 任务流水行 ② 「新组件模块归属裁定」历史行 ③ `P1` 立项行 + 指针）。**处置**：**现存/前瞻引用 → `082`**；**历史留档引用**（立项提交 `159bc42` 的路径、留档日志名、`1dc0570` 的 `libc-test` 历史号）**保留原字 + 就地加注**（`lessons §4.1`：历史快照旧路径保留不回溯；保「可审计」——与 `git show <commit> --name-status` 一致）。
- **范围**：**仅编号**变更，任务书目标/范围/验收标准**一字未改** ✓。
