# INFRA-082t: musl 静态最小集移植（`P1`：静态可运行）

**模块**：infra
**项目里程碑**：M8
**依赖**：`ADR-0025`（M8 路线；`D6` = `P0 契约 → P1 musl 静态 → P2 动态 → P3 linux-user → P4 对照/回归`、`D2` = **无内核目标**、`D3` = musl 自带 `ldso`〔**P2**〕、`D4` = musl 与 picolibc **并存**）；`ADR-0027 D5`（compiler-rt builtins = **独立库、picolibc/musl 共用**）；`INFRA-076t`（musl 1.2.6 取源与锁定，`已验证`）；`SPEC-138t`（syscall 映射契约，`已验证`）；`SPEC-140t`（TLS 硬依赖查证，`已验证`）；`ISS-216`（`dadao-m1` 无 `SYS_UMON_SYSCALL` 服务方；**已由主会话 2026-10-15 裁定并入本任务** ⇒ 见「前置结论 2」）；`INFRA-079t`（compiler-rt builtins 接入，`待开始`——**已由主会话结论 ① 定为「不必先做」**，见「前置结论 1」）；`INFRA-057t`（picolibc 移植/构建集成的**形态先例**，**只读**）；`docs/Process-01`（组件补丁组织与构建编排）
**状态**：待验收（**仅阶段 A**：A1 = QEMU 侧 `SYS_UMON_SYSCALL` 服务；A2 = musl 补丁集骨架 + 锁条目补丁化；A3 = 静态最小程序可编出；B/C 未做 ⇒ **任务整体未完成**，见完成区「阶段 A1」/「阶段 A2+A3」）
**阶段进度**：A1 ✅ 已验证（2026-10-15，reviewer Accepted）；A2/A3 ✅ 已完成（2026-10-15，分支 `INFRA-082t-A2`，待验收）；B、C ⏳ 待做

> **`**状态**` 口径说明**：本任务 = **一个任务书、多阶段验收**（照 `SPEC-142t`/`SPEC-143t` 先例）⇒ `**状态**` 表**任务级**进度（**阶段全部验收通过后**才置 `已验证`）；**阶段级**进度见上行 `**阶段进度**`（A1 见「第 1 轮 reviewer 验收」）。

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

**做（四条）**：
1. **musl 静态最小集移植**：`arch/dadao/` 骨架（顶层 `atomic_arch.h` / `crt_arch.h` / `kstat.h` / `pthread_arch.h` / `reloc.h` / `syscall_arch.h` + `bits/` 7 头）+ `src/*/dadao/`（`.s`/`.S`）+ **crt**（`crt1` / `crti` / `crtn`）+ **syscall stub** + **TLS 就位**。移植面清单**真源 = `INFRA-076t §实测移植面`**（riscv64 底座 = `.s`/`.S` **12** + `arch/riscv64/` **13**；DADAO 预计**同形**），**不复制实现**（参考仓 `DADAO-0628` 只借教训）。
   - **syscall stub（口径真源 = `.tao/contracts/contract-syscall.md`）**：号在 **`rd15`**、**沿用 RISC-V Linux 编号**（`§1.1` + `ADR-0025 D1`）；发起 `trap cfxha, immu18`，**`umon`（`cfx0`）路径 `immu18 = 0`**（`SBI_UMON_SYSCALL`，`§2`）；参数 `rd16–rd31`/`rb16–rb31`/`rf16–rf31`、返回 **`rd8`**（`§3`）；**errno = `rd8` 负值（`-errno`）**（`§4`，用户 2026-10-14 裁定 **A**）⇒ **musl `__syscall_ret()` 零改**；返回经 `escape cfxha, [excp_cause_ip, 4]`（`§2`）。
   - **TLS/TP（硬依赖，`P1` 阻断项；真源 = `SPEC-140t`）**：**TP + 含 `struct pthread` 的 TCB/TLS 区无条件必需**（`errno`/`exit`/stdio 锁/取消点 syscall 全经 `__pthread_self()`；`__init_tls` 无 `if`、失败 `a_crash()`）⇒ 须落 `arch/dadao/pthread_arch.h`（`__get_tp()`）+ `src/thread/dadao/__set_thread_area.s` + 启动期建 TLS/写 TP；**TP 寄存器 = `rb3`**（`contract-abi §1.2`；⚠ 参考仓 `DADAO-0628` 用 `rb4`，**不可照搬**）。`TLS_*` 重定位（`DTPMOD`/`DTPOFF`/`TPOFF`/`TLSDESC`）= **条件依赖，`P1` 静态无 `__thread` ⇒ 不触发**。
2. **产出静可运行的「最小程序」E2E**：至少 `hello`（写路径 → `write`）与 `exit`（`exit`/`exit_group`）**端到端跑通**，退出码/输出正确。
3. **QEMU 侧 `SYS_UMON_SYSCALL` 服务**（**2026-10-15 主会话结论 ② 并入；`ISS-216` 对策 ⓐ**）：在 `dadao-m1` 机器补 `trap cfx0, 0`（`umon`，`immu18 = 0`）的服务方——照 `spec/DADAO-22-SBI §2` 号表 + `SPEC-138t`（`contract-syscall.md`）口径分发 `rd15` 号、以 `rd8` 返回（含 errno 负值）。**形态按 `docs/Process-01`**（`components/qemu/patches/**` 树形补丁 + `series`），**不新增载体**。
   - ⚠ **范围决定（扩大，显式标注、供用户复核）**：本项**原不在** `P1` 任务范围（原范围 = 纯 musl/`infra` 侧）⇒ **`P1` 范围因此含 QEMU 侧工作** ✗。**依据** = 「**让静态 musl 能跑**」的**必要性**（无服务方 ⇒ `trap cfx0,0` 无执行路径 ⇒ E2E 判据不可达）；**主会话要求在本任务书内显式标注此范围决定**，供用户复核。`scope` 亦已在 `ISS-216` 记为 `[qemu, infra]`。
4. **（不做项，显式登记）**：动态链接 / `.so` / `ldso` / `PIC` / `GOT`·`PLT`（`P2` ✗）；`QEMU linux-user`（`P3` ✗）；信号 / 线程完整语义（按 `SPEC-140t`「P1 只需 TP+TCB」界定，其余归 `P2+` ✗）；内核（`D2` ✗）。

## 前置结论（主会话 2026-10-15；渠道 = 经主会话问答；**原话要点逐条引录** ⇒ **闭合本册「待确认项」三项**）

> **性质**：以下三条 = **主会话 2026-10-15 结论**（渠道 = 经主会话问答），**替代**本册「待确认项」原「待裁定」状态；下方「待确认项」表**原样保留**（`lessons §4.1`：历史不回溯），并就地标注闭合。

1. **`INFRA-079t`（compiler-rt builtins）不必先做**（原话要点：「**`INFRA-079t` 不必先做** ⇒ **`P1` 内遇到缺符号再补**（musl 静态少用 `__int128`）」）。
   - ⇒ **`P1` 内遇缺符号再补**；**撞上缺符号 ⇒ 当场登记（`issues.yaml`）并转 `INFRA-079t`**（原话要点：「**不得** silently 跳过」）。对应「阶段 C」。
2. **`ISS-216` 必须先解决 ⇒ 在 `P1` 内先补 QEMU 侧 `SYS_UMON_SYSCALL` 服务**（原话要点：「**`ISS-216` 必须先解决** ⇒ **在 `P1` 内先补 QEMU 侧 `SYS_UMON_SYSCALL` 服务**」）。
   - **口径**：照 `spec/DADAO-22-SBI-主管系统二进制接口.md §2` 的 `umon`（`cfx0`，`immu18 = 0` = `SBI_UMON_SYSCALL`）/ `jmon`（`cfx1`）双层模型 + `SPEC-138t`（`.tao/contracts/contract-syscall.md`，`已验证`）号表；即采纳 `ISS-216` 候选对策 **ⓐ**。
   - ⚠ **范围决定（扩大，显式标注、供用户复核）**：**`P1` 范围因此含 QEMU 侧工作** ✗（**原** `P1` 范围 = 纯 `infra`/musl 侧 ✗）——**依据** = 「**让静态 musl 能跑**」的**必要性**（无服务方 ⇒ `trap cfx0,0` 无执行路径 ⇒ E2E 判据不可达）；按主会话要求**在此显式标注为范围决定**。落点见「范围」做项 3。
3. **musl 改源方式 = 做成补丁集**（原话要点：「**musl 改源方式 = 做成补丁集**（与 `picolibc`/`qemu` 一致）」）⇒ 建 `components/musl/{README.md,changelog.md,patches/,series}`（**样板 = `components/picolibc/**`** ✓ 现场已核）；锁条目 `patchless = true` ⇒ 改 `patch_dir`/`patch_series`，`role` 中「`no v5 patch set yet`」同步（**同一提交**内完成，不得夹带）。
   - ⚠ **标注**：**这一项在锁册/组件形态上属「组件补丁化」** ⇒ **须按 `docs/Process-01` 组织**：**树形补丁（路径镜像上游源码树）+ 一文件一补丁（双向唯一）+ `check-patch-tree` 机械校验**。

## 分期结构（三阶段；**阶段 C = 条件触发**；**不含 `P2` 动态** ✗）

| 阶段 | 名称 | 内容 | 出口判据 |
|---|---|---|---|
| **A** | **环境与骨架** | ① **补 QEMU 侧 `SYS_UMON_SYSCALL` 服务**（前置结论 2）；② **musl 补丁集骨架**＝`arch/dadao/**`（顶层 **6** + `bits/` **7**）+ `src/*/dadao/**` + **crt**（`crt1`/`crti`/`crtn`）+ **syscall stub** + **TLS 就位**；③ **锁条目补丁化**（`patchless` ⇒ `patch_dir`/`patch_series`，同提交）；④ **交叉工具链能编出静态最小程序** | `make check-patch-tree` rc=0（含 musl 补丁集）；静态最小程序**可链接产出**（阶段 A 只到「编出」）；QEMU 服务方留真命令 + 输出 + 退出码 |
| **B** | **跑通** | 静态 `hello` / `exit` **E2E**（QEMU `-M dadao-m1`）+ **独立 oracle**（**不从 LLVM/QEMU 反推**）+ **端序 = 大端** + 证据 | E2E **退出码/输出正确**且**忠实传播**到宿主 `$?`；独立 oracle 通过；**BE 敏感 ≥1 例** |
| **C** | **条件触发** | **缺符号 ⇒ 转 `INFRA-079t`**（前置结论 1）：**当场登记 `issues.yaml` + 转任务**，**不得** silently 跳过 | 触发即登记 + 转出；`INFRA-079t` 收口后回阶段 B |

- **不含**：`P2` 动态链接 / `ldso`（✗）、`P3` `linux-user`（✗）——见「范围」做项 4。

## 实现约束与阶段 A1 遗留（2026-10-15 补录；**供阶段 B**）

> **来源** = 阶段 A1 实测（见完成区「阶段 A1」坑② / 遗留②④）；**本节为规范性约束，阶段 B 执行须遵循**。

1. **实现约束（重要）：阶段 B 必须走 `-bios` + 原始镜像（「path B」）** —— **禁用** `-kernel <ELF>`（「path A」）：`-kernel <ELF>` **复位态 = `hypv`**（`inner_cfx_mask = ~0`）⇒ **不触达本服务**（`trap cfx0, 0` 走 §5 向量路径 `CFXMEM 0x81`）。进 `user` 模式须经 firmware 交接（`Machine-01 §6` 既有范式；`tests/scripts/bootrom.S` 即此用法）。**依据 = 本步实测**（`min_rom_probe_082t.py` 不回归用例 + 完成区坑②）。
2. **阶段 A1 遗留（阶段 B 输入）**：
   - **服务集仍缺（显式 `-ENOSYS`，非静默）**：`read`(63)／`brk`(214)／`set_tid_address`(96)／`set_robust_list`(99) 等 ⇒ **阶段 B 按 musl 实测需要补**（证据：musl `src/env/__init_tls.c:22` **启动即调 `set_tid_address`(96)**）。
   - **探针未接门控**（本任务**未改** `Makefile`，避免越界）⇒ 记为「**阶段 B 后评估**」；**本任务不接门控**。

## 阶段 A2+A3 遗留（2026-10-15 补录；**供阶段 B/C**）

> **来源** = 阶段 A2+A3 实测（见完成区「阶段 A2+A3」的「新发现/坑」与「遗留问题」④–⑧/⑩/⑪，**只追加、不改写**）；**本节与「阶段 A1 遗留」同为规范性输入**，阶段 B/C 执行须遵循。**逐条落纸 = 8 条**（7 条遗留 + 1 条待收尾裁定）。

1. **原子非真（单线程语义）**：机器无 LR-SC/`fence`（`contract-isa §14` = `excluded`；QEMU 侧为 ILLI 桩）⇒ `a_cas` 只给**单线程**语义（`arch/dadao/atomic_arch.h` 已写明）。**阶段 B 单线程 E2E 不受影响；开线程/`P2` 之前必须换真原子。**
2. **`GETFUNCSYM` 给链接期绝对地址**（`arch/dadao/reloc.h` 覆盖 `ldso/dlstart.c` 的唯一用户）：**静态（`P1`）成立**；**`P2` 动态须改为基址相关**（随 `ldso` 真重定位）。
3. **`bits/signal.h` 的 `mcontext_t` = `[OPEN]` 占位**：v5 无 DADAO 信号帧 ABI（`ADR-0025 D2` 无内核/信号）⇒ **仅保证编译**、头文件已标 `[OPEN]`；谁定真帧布局谁重写。
4. **无 `AT_PHDR`/`PHNUM`/`PHENT`** ⇒ `libc.tls_cnt = 0` ⇒ **静态 `__thread` 未打通**（`errno`/TP/TCB 正常）；阶段 B 若需 `__thread`，须先在 crt 侧补 auxv 注入。
5. **`sigsetjmp` 未实现**（`src/signal/sigsetjmp.c` 是上游空槽）⇒ **用之即链接失败**（非静默）；`siglongjmp` 存在但无可用缓冲。
6. **（不变量）阶段 B 加服务须同步 `arch/dadao/syscall_arch.h` 的 `__dadao_argmask` 表项**：未列号默认 mask = 0（`rb16` 被置 0），今日因服务方对未实现号一律 `-ENOSYS` 而**可证无害**，但**新增「读指针参数」的服务必须同步加表项**（已写入头文件注释 + `components/musl/README.md`）。服务集仍缺：`read`(63)／`brk`(214)／`set_tid_address`(96)／`set_robust_list`(99) 等。
7. **阶段 C（条件触发）：libcall 缺口未触发**（**显式声明，非默认通过**）—— `P1` 静态最小集全程未撞 i128 除法 / FP↔i128 / `bswap` / `*_PARTS` 等 ⇒ **本阶段无 `INFRA-079t` 转出**；阶段 B/C 若撞上须**当场登记 `issues.yaml` + 转 `INFRA-079t`**（**不得** silently 跳过）。
8. **待收尾裁定（`make build-musl`）**：构建**未接 `Makefile`**（只有 `tools/infra/build_musl.py`）⇒ **是否加 `make build-musl` target 由主会话收尾时裁定**（本阶段未改 `Makefile`，避免越界）。

## 依据（口径真源；**引用，不复制正文**）

- **syscall 映射**：`.tao/contracts/contract-syscall.md` `§1`（号在 `rd15` + 沿用 RISC-V 编号）/ `§2`（`umon`/`jmon` 入口）/ `§3`（参数与返回 `rd8`）/ `§4`（**errno = `rd8` 负值**，已裁定 A）/ `§5`（独立 oracle 口径）/ `§6`（QEMU 角色与边界）/ `§7`（裁定清单）；`ADR-0025 D1`/`D2`/`D6`。
- **TLS**：`SPEC-140t §结论` + `§证据表`（`文件:行` 逐条）；`contract-abi.md §1.2`（`rb3` = TP）。
- **builtins 归属**：`ADR-0027 D5`（**独立「DADAO compiler-rt builtins」库**，**picolibc 与 musl 共用同一份**，不属任何 libc）。
- **移植范围/教训（`DADAO-0628`，**内容溯源，非执行必需**）**：`INFRA-076t §参考对照` 的 9 条教训清单（`arch/dadao` 骨架不足以产出可链接 libc / `reloc.h` `CRTJMP` 专修 / `pthread_arch.h`+`get_tp`+`__set_thread_area` 硬依赖 / `crt_arch.h`+`arch.mak` override `__libc_start_main` / RB 寄存器组指针 / `O0` 变通非终态 / 软浮点垫片 / `AT_PAGESZ` auxv 立即数溢出 / `__int128` 算术库）。**只借判断，不复制代码。**
- **补丁/构建形态先例**：`INFRA-057t`（picolibc：真移植补丁集 + 构建集成 + syscall stub 映射），**只读**。

## 依赖与先后

- **已满足**：`INFRA-076t`（musl 1.2.6 入锁：`commit 9fa28ece…`、`shallow_ref="v1.2.6"`、**`patchless = true`**）、`SPEC-138t`（契约）、`SPEC-140t`（TLS 判据）。
- **`INFRA-079t`（compiler-rt builtins；`待开始`）= 不必先做**（**前置结论 1**，主会话 2026-10-15）：`P1` 内**遇缺符号再补**；若 `P1` 链接期撞 i128 除法 / FP↔i128 / `bswap` / `*_PARTS` 等 libcall 缺口 ⇒ **当场登记 `issues.yaml` 并转 `INFRA-079t`**（**不得** silently 跳过），收口后回「阶段 B」。
- **`ISS-216`（P2 issue，`open`）——必须先解决、已并入本任务**（**前置结论 2**）：本任务**阶段 A** 内含 QEMU 侧 `SYS_UMON_SYSCALL` 服务补齐；`ISS-216` 的 `status` 保持 `open`，**待实现后随本任务收尾关闭**。
- **串行约束**：与任何同改 `components/musl/**`、`components/qemu/**`、`manifests/components.lock.toml`、`Makefile` 的任务**串行**（不得并行）。

## 已知事实（供执行，**勿重复查证**；源已标注）

1. **musl 版本/锁**（`INFRA-076t`，已验证）：`1.2.6`，`commit = 9fa28ece75d8a2191de7c5bb53bed224c5947417`，`shallow_ref = "v1.2.6"`（lightweight tag），**`patchless = true`**，`role` = M8 libc 底座；源码检出 `.work/source/<musl>/`（`.work/` 可重建区）。
2. **`patchless` 的含义**（`manifests/components.lock.toml` 注释）：**尚无** v5 的 `arch/dadao` 补丁集；门控据此接受**缺** `patch_dir`/`patch_series`；**一旦落地首个 `arch/dadao` 补丁，须在同一提交里去掉 `patchless` 并补两字段**（不得夹带）。
3. **验证机**：`spec/Machine-01-测试机运行环境.md`（`dadao-m1`）——RAM/ROM 布局、`trap`/`escape` 流程、**semihosting 服务表（完整 25 个，含 `SYS_WRITE`/`SYS_EXIT_EXTENDED`/`SYS_HEAPINFO`）**、停机协议 = `SYS_EXIT`。QEMU 现状 = **仅 system 模式**（`qemu-system-dadao -M dadao-m1`）。
4. **⚠ 现场缺口（本任务书立项时实测，属 `P1` 的**范围/归属**问题）**：`dadao-m1` 机体现有实现**只覆盖**「一般 `trap` → cfx 向量」与「semihosting 短路（`immu18[17:16] == 2'b11`）」两条路径（`components/qemu/patches/target/dadao/{helper.c,insn_trans/trans_ctrl.c.inc}.patch`）；**未实现** `immu18 != 2'b11` 的 `umon` syscall 分发服务方（`SBI_UMON_SYSCALL`）⇒ **谁为 `P1` 的 `trap cfx0,0` 提供 Linux 语义服务**是必须先定的口径（选项见「待确认项 ①」；**2026-10-15 已由主会话裁定：选 ⓐ**，见「前置结论 2」 ⇒ **本任务阶段 A 内补齐**）。
5. **端序 = 大端（BE）**：`ADR-0003 D1`（`EI_DATA = ELFDATA2MSB`）；`AUDIT_ARCH_DADAO` = BE64（`contract-syscall §1.3`）；上游测试多在 LE 跑 ⇒ **BE 敏感用例必须自成一面**。
6. **工具链**：`clang -target dadao-unknown-elf`（`.dadao/cross-toolchain/**`）；`long double` ≡ `binary64`；`__int128` 支持但**工具链不提供 libgcc/compiler-rt builtins**（`INFRA-078t` 已查证）。

## 接口规范

- **输入**：`ADR-0025`（`D2`/`D3`/`D4`/`D6`）、`ADR-0027 D5`、`.tao/contracts/contract-syscall.md`、`contract-abi.md §1.2`、`SPEC-140t`、`INFRA-076t`（含 `§实测移植面`/`§参考对照`）、musl 源码检出（**只读**）、`.dadao/` 工具链 + sysroot（**只读**）、`.dadao/tests/harness/**`（验证载体）。
- **输出**：
  1. **musl 移植补丁集**：`components/musl/{README.md,changelog.md,patches/**,series}`（**新建**，样板 = `components/picolibc/**`；**一文件一补丁**，镜像上游仓内路径）；**同一提交**去掉锁条目 `patchless` 并补 `patch_dir`/`patch_series`（`role` 中「`no v5 patch set yet`」同步，**前置结论 3**）；形态与纪律按 `docs/Process-01`（树形补丁集 + `git apply` + `check-patch-tree` 机械校验）。
  2. **QEMU 侧 `SYS_UMON_SYSCALL` 服务补丁**（**前置结论 2** / `ISS-216` 对策 ⓐ）：`components/qemu/patches/**`（树形补丁 + `series`）——`dadao-m1` 机器的 `umon`（`cfx0`/`immu18 = 0`）分发服务，按 `DADAO-22 §2` + `contract-syscall §1–§4` 口径（`rd15` 号、`rd8` 返回、errno 负值）；形态按 `docs/Process-01`。
  3. **构建集成**（`Makefile` / `tools/infra/**`）：`clang -target dadao-unknown-elf -static` 构建 musl 静态库 + crt，落点按 `ADR-0016`（`.dadao/cross-toolchain/**` / sysroot）；target **可复跑、幂等**。
  4. **最小 E2E 程序**：`hello` + `exit`（源与构建脚本入仓库、落 `tools/<module>/` 或 `tests/`，**非易失位置**；临时产物落 `/tmp/opencode/<任务ID>/`）。
  5. **验证/证据**：一键证据脚本 `.work/evidence/<任务ID>/run.sh`（含**注入 → FAIL → 还原 → 回绿**）+ 原始产物落 `.work/log/infra/**`；本任务书完成区 + `milestones.md` 流水行。
- **约束**：**最小改动**、只碰任务范围；**不得**改 `spec/`（`docs/Process-06` / `ADR-0012 D4` 须用户事先授权）、`contracts/`、`.tao/contracts/**` 机器数据与正文；**不得**做 `P2`/`P3` 内容（不做 `ldso`/`linux-user`）；**组件源一律 git 基线**（改 musl 源只经 `patches/`，不得直接改 `.work/source/`）；**计数不写死**；**证据与期望值独立**（`contract-syscall §5`：不从 QEMU/LLVM 反推）。

## 验收标准

1. **静态可运行（E2E，主判据）**：`hello` 与 `exit` **真实跑通**——留**真实命令 + 完整输出 + 退出码**（禁 `cmd | tee` 吞码）；`exit` 的退出码须**忠实传播**到宿主 `$?`（`Machine-01 §5.5`）。
2. **契约逐条对齐**（`grep`/反汇编可证）：syscall stub 的**号来源 = `rd15`**、**沿用 RISC-V 编号**、入口 `immu18 = 0`、返回 `rd8`、**errno = `rd8` 负值**；与 `contract-syscall §1–§4` **逐条对齐**，**不自选** B/C 口径。
3. **TLS/TP 就位（`P1` 阻断项）**：`arch/dadao/pthread_arch.h` 的 `__get_tp()` 读 **`rb3`** + `__set_thread_area` 写 `rb3` + 启动期 TLS/TCB 建立；`errno`（经 `__pthread_self()`）在 E2E 中**可用**（给出证据，如故意触发一次 errno 路径）。
4. **独立 oracle + 端序**：期望值**独立派生**（不从 QEMU / LLVM 反推；口径 = `contract-syscall §5`）；**BE 敏感**用例至少 1 例并留证（我们是大端，上游多在 LE）。
5. **QEMU 侧 `SYS_UMON_SYSCALL` 服务可用**（阶段 A 出口；**前置结论 2**）：`dadao-m1` 对 `trap cfx0, 0`（`immu18 = 0`）**有服务方**——按 `rd15` 号分发、以 `rd8` 返回（含 **errno 负值**口径）；留**真实命令 + 输出 + 退出码**；形态合 `docs/Process-01`（树形补丁 + `series`）。
6. **补丁集形态 + `patchless` 收口**（**前置结论 3**）：`components/musl/{README.md,changelog.md,patches/**,series}` 已建（样板 `components/picolibc/**`）；同一提交内**去掉 `patchless` 并补 `patch_dir`/`patch_series`**（`role` 同步）；`make check-patch-tree` rc=0（**含 musl 补丁集**）。
7. **门控（分层）**：`make check`（**L1**）/ `make check-modules`（**L2**，任务收尾）/ `make check-full`（**L3**，里程碑/`/complete`）/ `check-knowledge-refs` / `check-knowledge-dir` / `check-no-residue` / `make check-tasks` / `python3 tools/infra/check_issues.py` 各 **rc=0**（各留**自身**真实 rc，禁 `tee` 吞码）。
8. **证据脚本**：`.work/evidence/<任务ID>/run.sh` 可跑通，**每条断言有可达 FAIL 路径**（注入反例 ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿；**禁** `git checkout/restore/stash`）。
9. **前置结论已闭合（原「待确认项」三项）**：三条结论（**主会话 2026-10-15**）已落「前置结论」章节；**执行中若需偏离**（如新决策/需授权）⇒ 留问，**不自行改契约**。
10. **阶段 C 触发登记（条件判据）**：若撞 libcall 缺口 ⇒ `issues.yaml` **当场登记** + 转 `INFRA-079t`（**不得** silently 跳过）；未触发则**显式声明未触发**（不给"默认通过"）。

## 待确认项（原「**开工前须用户裁定**」；**2026-10-15 已由主会话结论闭合** ✓，表内原文保留不回溯）

> **闭合口径**（主会话 2026-10-15，**原话要点**）：① ⇒ **结论 2**（`ISS-216` 选 ⓐ：**P1 内先补 QEMU 侧 `SYS_UMON_SYSCALL` 服务**；验证环境仍用 `-M dadao-m1`）；② ⇒ **结论 1**（`INFRA-079t` **不必先做**，`P1` 内缺符号再补、撞上即登记转出）；③ ⇒ **结论 3**（**musl 改源 = 做成补丁集**，建 `components/musl/**` + 锁条目补丁化，按 `docs/Process-01`）。

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

### 阶段 A1：QEMU 侧 `SYS_UMON_SYSCALL` 服务（2026-10-15，分支 `INFRA-082t-A1`）

**测试结果**：`tools/qemu/min_rom_probe_082t.py` **12/12 PASS**（服务集 write/writev/exit/exit_group + ENOSYS/EBADF/EINVAL + 不回归：hypv 交接 / jmon 不服务 / semihosting）✓；`--inject` **0/12 FAIL（rc=1）** ✓；一键证据 `.work/evidence/INFRA-082t/run-a1.sh` = **27 checks passed / 0 failed，rc=0** ✓；门控各捕自身 rc：`make check`(L1)=**0** ／ `check-qemu-semantics`=**0**（**149/149**，现场统计）／ `check-qemu-smoke`(L2)=**0** ／ `test-semihost`(L2)=**0**（M5 e2e：bootrom `hypv→user` 交接 + `trap`/`escape` + 25 服务）／ `check-patch-tree`=**0**（129 patches / 4 组件）／ `check-index-blobs`=**0**（93 new-file）／ `check-source-state`=**0**。
**修改文件**：①（M）`components/qemu/patches/target/dadao/helper.c.patch`（`tools/infra/make_patch.py qemu` 重导出：新增 `umon` 服务段 + `helper_cfx_trap` 接管分支；`series` 36 项**未变**）；②（**新增，越界披露**）`tools/qemu/min_rom_probe_082t.py`（先例 `min_rom_probe_04xt.py`，随产物入库）；③（M）本任务书（状态 + 完成区「阶段 A1」+ 第 1 轮 engineer 自审）。**未提交**（`git status --porcelain -uall` = ①②③ 三项）；`spec/`/`contracts/`/`.tao/knowledge/`/`manifests/` **未动**。
**验收结果**：**识别** = `trap cfxha=0(umon), immu18=0`（`SBI_UMON_SYSCALL`）**且 `inner_run_mode == user`**（`contract-syscall §2` + `DADAO-22 §2`「`umon` = user 模式异常入口」）；**位置** = `helper_cfx_trap` 内、**指令类型 trap mask 检查之后**、§5 向量流程之前（掩码语义不被绕过）。**接管** = QEMU 服务后按 `escape cfxha,[excp_cause_ip,4]` 语义回 `pc+4`（不写 cfx 帧/计数器：探针 `trapn0==1` 实测印证）。**最小服务集（现场定）** = `write`(64)／`writev`(66)／`exit`(93)／`exit_group`(94)，**号值取自锁定号表**（`.work/source/qemu/linux-headers/asm-generic/unistd.h`，`contract-syscall §1.2`）；fd 1/2 ⇒ 宿主 stdout/stderr（「无内核」下宿主侧转发，`contract-syscall §6`）；退出码经 `qemu_system_shutdown_request_with_code(GUEST_SHUTDOWN, code)` **忠实传 `$?`**（实测 `$?=42`／`7`；**不复用** semihosting `SYS_EXIT`，§6 停机协议不混用）。**未实现 ⇒ 显式失败**：`qemu_log_mask(LOG_GUEST_ERROR)` + **`rd8 = -ENOSYS`**（实测 `0xFFFF_FFFF_FFFF_FFDA`；不支持 fd ⇒ `-EBADF`；`iovcnt>1024` ⇒ `-EINVAL`）。**重建 + 安装**：`build-qemu` rc=0、**`install-host` rc=0**（日志 `.work/log/{qemu,infra}/INFRA-082t-*`；`/tmp/opencode/INFRA-082t/*.EXIT`），两处二进制 md5 一致 = `f21edd71d5a4352d3e0c5fdc64afbb3e`；**产品级反例**（禁服务 + 重建）⇒ 探针 **3/12（恰 9 条服务用例 FAIL，3 条不回归用例仍 PASS）** ⇒ `cp`+md5 还原 + 重建 ⇒ **12/12** 且二进制 md5 回到原值。
**新发现/坑**：① **`trap cfx0,0` 双重身份**：`immu18=0` 既是 `SBI_UMON_SYSCALL`，又被 `tests/scripts/bootrom.S` 用作 **hypv→user 交接** ⇒ 任何「解码层 / 全模式短路」都会破坏 `test-semihost` 的 bootrom 交接（app 进不了 user 模式）与 `min_rom_probe_044t/045t` 的 hypv 向量用例 ⇒ 服务**限定 user 模式**。② **无 firmware 的 `-kernel <ELF>`（path A）复位态 = hypv**（`inner_cfx_mask=~0`）⇒ 不触达本服务；进 user 模式须 firmware 交接（`Machine-01 §6` 既有范式）⇒ **阶段 B 须走 `-bios` + 原始镜像（path B）**（或 crt0 自清掩码）；否则 `trap cfx0,0` 走 §5 向量路径（`CFXMEM 0x81`）。③ 改补丁后 `make apply-series` 会因「HEAD=base+1 但内容 ≠ 新补丁集」**拒绝应用**；本步改用「编辑 `.work/source/qemu` 文件 + `commit --amend`（仍 base+1、内容 == 新补丁集）+ `make_patch.py` 导出」**不丢弃任何改动**，由断言⑥/⑨ + `--source-state` 机械核对。④ musl 现场核对（`.work/source/musl/`）：stdio 缓冲写用 **`writev`**（`src/stdio/__stdio_write.c:20`）、退出 `exit_group`→`exit`（`src/exit/_Exit.c:6-7`）、**启动即调 `set_tid_address`(96)**（`src/env/__init_tls.c:22`）。⑤ `-d cpu` 的 `MODE:` 行解析须 `re.MULTILINE`（`min_rom_probe_046t.py::_lasthex` 未加，复用其 `observe()` 取不到 MODE）。
**遗留问题**：① **A2/A3/B/C 未做**（musl 补丁集骨架／锁条目补丁化／静态程序可编出／`hello`·`exit` E2E）⇒ **本任务整体未完成**。② **服务集仍缺**（显式 `-ENOSYS`，非静默）：`set_tid_address`(96)／`set_robust_list`(99)／`read`(63)／`brk`(214) 等 ⇒ **阶段 B 按 musl 实测需要补**（上条④为预判证据）。③ **spec 覆盖缺口（未改 `spec/`，只读）**：`Machine-01 §4.3` 现只列两条路由，本步新增**第三条行为**（user 模式 `trap cfx0,0` 由 QEMU 接管、不进 guest 向量）⇒ **建议主会话登记 issue + 后续（授权后）落 `Machine-01`/ADR**（先例 `QEMU-049t`⇒`ISS-166`⇒`SPEC-121t`）。④ 探针**未接门控**（未改 `Makefile`，避免越界）⇒ 建议主会话裁定是否并入 L2。⑤ `jmon`(cfx1) `immu18=0` 未服务（保持既有向量路径）——本次范围只 `umon`。⑥ `ISS-216` **未关**（归本任务收尾）。

### 阶段 A2+A3：musl 补丁集 + 锁条目补丁化 + 静态最小程序可编出（2026-10-15，分支 `INFRA-082t-A2`）

**测试结果**：`tools/infra/build_musl.py`（configure + `make -j8` + 链接 + ELF 核对）**10/10 checks，rc=0**（**全量净构建 9.4 s**，`.work/log/musl/INFRA-082t-a23-build-musl-clean.log`）；一键证据 `.work/evidence/INFRA-082t/run-a23.sh` = **44 checks passed / 0 failed，rc=0** ✓，`--inject` = **rc=1**（4 条期望被污染 + 2 条注入断言 ⇒ 必失败）✓；门控各捕**自身** rc：`make check`(**L1**)=**0** ／ `check-patch-tree`=**0**（**5 components / 145 patches**，含 musl 16）／ `check-index-blobs`=**0** ／ `check-source-state`=**0** ／ `check-no-residue`=**0** ／ `check-tasks`=**0** ／ `check-component-changelog`=**0** ／ `python3 tools/infra/check_issues.py`=**0**（35 open / 9 closed / 0 blocking）。
**修改文件**：①（A，16 文件）`components/musl/{README.md,changelog.md,series,patches/**}`（**树形补丁、一文件一补丁**：`arch/dadao/**` 12 + `src/setjmp/dadao/**` 2 + `src/thread/dadao/__set_thread_area.s` 1 + `configure` 1）；②（M）`manifests/components.lock.toml`（musl：去 `patchless`、补 `patch_dir`/`patch_series`、`role` 同步，**同批**）；③（A，**越界披露**）`tools/infra/build_musl.py`（构建+链接+ELF 核对；先例 `tools/infra/{build_picolibc,test_picolibc_smoke}.py`，落点由本册「输出 3/4」指定）；④（M）本任务书（状态/阶段进度 + 本区块 + 第 2 轮自审）。**未提交**；`.work/source/musl` 工作树 = **base+1 且干净**（组件侧本地 commit，E1 成立）；`spec/`/`contracts/`/`.tao/contracts/`/`.tao/knowledge/`/`Makefile` **未动**。
**验收结果**：**补丁集形态** = `series` 16 行 ↔ `patches/**` 16 文件（现场统计），每份恰 1 个 `diff --git`、`patches/` 纯镜像。**A3 出口（静态最小程序）**：`clang --target=dadao-unknown-elf` 编 `write(1,"hi\n",3); return 0;` + `crt1.o` + `libc.a` → `ld.lld -T tests/scripts/dadao.lds` ⇒ `file`：**`ELF 64-bit MSB executable, *unknown arch 0xda0*, statically linked`**；自解析 ELF：ELFCLASS64 / ELFDATA2MSB / `ET_EXEC` / `e_machine=0x0DA0` / **无 `PT_INTERP`、无 `PT_DYNAMIC`** / `e_entry=0xfc0000000000`（= `dadao.lds` 的 RAM 基址）；反汇编含 `trap cfx0, 0`；`libc.a` 1336 成员（`write`/`read`/`setjmp`/`longjmp`/`__libc_start_main`/`__set_thread_area`/`malloc`(W)/`printf` 均在）。**契约对齐（静态可证）**：`write()` 生成序列 —— `sccp` 内 `rd2rd {rd15},{rd16}`（号→**`rd15`**）+ 跳表按 `__dadao_argmask` 分派 + 公共尾 `rd16=a0(fd)`／`rd17=a2(count)`／**`rd2rb {rb16},{rd4}`（指针→`rb16`）** + `trap cfx0, 0`（`immu18=0`）⇒ 与 `contract-syscall §3` 的「`read`：fd→rd16、buf→rb16、count→rd17」**逐槽一致**（跳表 71 项现场读出：`nr=63/64/65/66` → 指针槽=1 体，`nr=29` → 指针槽=2 体，`nr=96/98/99` → 指针槽=0 体）。**号表**：`bits/syscall.h.in` ↔ 锁定的 RISC-V `linux-user/riscv/syscall.tbl` **共同名 314 / 0 冲突**，关键 14 号 **14/14** 同值。**启动帧**：从产物 ELF 读 `__dadao_init_stack` 18 octa = `{1, argv0, NULL, NULL, AT_PAGESZ 6→4096, AT_UID/EUID/GID/EGID 11-14→0, AT_HWCAP 16→0, AT_EXECFN 31→argv0, AT_NULL 0→0}` ✓。**注**：A3 只到「编出/链出」，**未运行**（E2E 属阶段 B）。
**新发现/坑**：① **clang 的 DADAO target 不能把 `%N` 代进 inline asm**（代入为空串：`rb2rd %0, rb3, 1` → `rb2rd , rb3, 1`）⇒ 本端口 inline asm **一律只写字面寄存器名** + C 侧「局部寄存器变量」绑定（`register … __asm__("rd8")` + `"=r"(x)`）。② **任何 `"m"`/`"+m"` inline asm 都令后端 ISel 崩**（`Could not match memory address. Inline asm failure!`，最小复现 `void f(void){int x;__asm__("" : "+m"(x));}`）⇒ 全树唯一用户 `ldso/dlstart.c` 的 `GETFUNCSYM` 必须 arch 覆盖（musl 给 arch 留的口子，12 个 arch 均如此）否则整树编不过。③ 后端另缺 `rotl/rotr`、`bswap`、`dynamic_stackalloc`（alloca/VLA）⇒ 13 个源文件不可编译。④ **`arch/<arch>/arch.mak` 是 musl 的 per-arch Makefile 钩子**（`-include` 在 `BASE_SRCS` 之后）⇒ 用 `BASE_SRCS := $(filter-out …)` 过滤受阻源，**无需改上游 Makefile**。⑤ 构造「符号地址进寄存器」用 `set.rd rdX, sym`（展开 `set.zw`+2×`or.w` + 3×`R_DADAO_ABS48`）；大端 `.dd.o64 symbol` 亦落 `R_DADAO_ABS48`；`ld.lld -T dadao.lds` 对二者均能解析（残留重定位 0）。⑥ musl 的 `write()` 是**取消点**（`syscall_cp`）⇒ 实调链 `write → __syscall_cp → sccp → __dadao_trap`；静态核寄存器流即可验「指针进 rb16」，无需运行。⑦ `--disable-shared` 下 `SHARED_LIBS=` 为空，但 `crt/rcrt1.o` 仍必编（含 `dlstart.c`）⇒ ②不解决则「只编静态」也过不去。
**遗留问题**：① **B/C 未做** ⇒ 任务整体未完成（B = `-bios` + 原始镜像 E2E、独立 oracle、BE 敏感例）。② **后端缺口 4 类**（`%N` 代入 / `m` 操作数 ISel 崩 / `rotl`·`rotr` / `bswap` / `dynamic_stackalloc`）**未登记 issue、未转 LLVM 模块**（本册范围外）⇒ 建议主会话登记并派 LLVM 侧任务；它们是「修掉即可解锁 13 源 + 简化 GETFUNCSYM」的直接项。③ **13 源文件被显式排除**（`arch/dadao/arch.mak`，每次构建 `$(info …)` 打印）⇒ `crypt()/crypt_r()`、`exec*`、`getcwd`、`sigdelset`、`.mo` 本地化、`getgrouplist`、`nscd_query`、resolver **链接期显式失败**（不静默）。④ **原子非真**（LR-SC/`fence` = `scope: excluded`/ILLI）⇒ `a_cas` 为单线程语义；开线程前必须换。⑤ `GETFUNCSYM` 给**链接期绝对地址**（静态成立；P2 须改基址相关）。⑥ `bits/signal.h` 的 `mcontext_t` 为 **`[OPEN]` 占位**（无 DADAO 信号帧 ABI）。⑦ **无 `AT_PHDR/PHNUM/PHENT`** ⇒ `libc.tls_cnt=0`，静态 `__thread` 未打通（TP/TCB/`errno` 正常）。⑧ `sigsetjmp` 未实现（`src/signal/sigsetjmp.c` 是上游空槽）⇒ 用之即链接失败。⑨ 构建**未接 `Makefile`**（只有 `tools/infra/build_musl.py`）⇒ 是否加 `make build-musl` 建议收尾时定。⑩ 服务集仍缺（`read`/`brk`/`set_tid_address`/`set_robust_list` 等）⇒ **阶段 B 补服务时须同步 `arch/dadao/syscall_arch.h` 的 `__dadao_argmask` 表项**（不变量，已在头文件与 README 写明）。⑪ **阶段 C：libcall 缺口未触发**（显式声明，非默认通过）。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：阶段 A1（QEMU 侧 `SYS_UMON_SYSCALL` 服务）。diff = `helper.c.patch`（+~150 行）+ 新探针 `tools/qemu/min_rom_probe_082t.py`。

**逐行审查（要点 + 判决）**：
1. **拦截位置**（`helper_cfx_trap` 内、`trap_mask` 检查之后、§5 向量之前）：放解码层则看不到运行模式，且会绕过掩码语义（`min_rom_probe_044t` `mask_illi` / `045t` `trap_mask_illi` 依赖「掩码 ⇒ ILLI」）⇒ **判决：正确**。
2. **user 模式限定 vs 全模式服务**：`tests/scripts/bootrom.S` 用 hypv `trap cfx0,0` 做 `hypv→user` 交接，全模式短路会使 `test-semihost` 的 bootrom 断言失败 ⇒ **判决：必须 user 限定**（`DADAO-22 §2` 亦如此定义 `umon`）。
3. **返回语义**：`pc+4` + `rd8`（= `escape cfxha,[excp_cause_ip,4]` 落点）；不写 cfx 帧/计数器 —— 判决：**合 `contract-syscall §2`**，探针 `trapn0==1`（仅交接那一次）实测印证。
4. **`write` 宿主转发**：4 KiB 分块（避免按 `count` 大分配）、按字节读 guest（BE 无关）、`EINTR` 重试、短写如实返回 —— 判决：**正确**；`n<=0` 时**不读脏 errno**（见 F1）。
5. **`writev`**：iovcnt 上限 1024（Linux `IOV_MAX`）、iov = 16 B BE、部分写返回已写字节、无进展才返 `-errno` —— 判决：**正确**。
6. **未实现号** ⇒ `LOG_GUEST_ERROR` 日志 + `-ENOSYS`（不静默）—— 判决：**合任务要求**（实测 `0xFFFF…FFDA`）。
7. **`exit`/`exit_group`** ⇒ `qemu_system_shutdown_request_with_code(GUEST_SHUTDOWN, code)` + `cpu_exit`（**不复用** semihosting `exit()`；`contract-syscall §6` 停机协议不混用）—— 判决：**正确**（`$?` = 42／7 实测）。
8. **防造假**：12/12 与 `--inject` 0/12、门控 rc 均真命令输出；产品级反例（禁服务 + 重建）恰 9 条服务用例 FAIL、3 条不回归用例仍 PASS ⇒ 断言有鉴别力、**非恒真**；`--inject` 覆盖 12/12 用例。

**finding 处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `umon_host_write` 在宿主 `write` 返 0 时可能用上一次 `errno` 误判 `-EBADF` | ✅已修 | 条件收紧为 `n < 0 && errno == EBADF`，否则 `-EIO` | 重建 rc=0；探针 12/12 |
| F2 探针 `build_kernel` 按 `max(offset)` 定尺寸，长 blob 会静默截断 | ✅已修 | 改为 `max(off + len(blob))` | 探针 12/12；`--list` 12 == 运行 12 |
| F3 `--inject` 下 `stdout_absent` 期望被置空 ⇒ 该断言注入时静默跳过 | ✅已修 | 注入时转为 `stdout_has` presence 断言 | `--inject` 0/12（12 条用例全 FAIL） |
| F4 hypv 无 firmware 路径不触达服务（阶段 B 风险） | ⏸延后 | 不改实现（全模式服务会破坏既有路径） | 完成区坑②+遗留②；阶段 B 指引已写 |

**判决**：finding 均 `✅已修`（附复验）或 `⏸延后`（附原因/证据）⇒ 状态置 `待验收`；**仅阶段 A1**，A2/A3/B/C 未做 ⇒ 任务整体未完成。

#### 第 1 轮 reviewer 验收（2026-10-15，分支 `INFRA-082t-A1`）

**两处二进制**：`f21edd71d5a4352d3e0c5fdc64afbb3e`（`.work/build/qemu` == `.dadao/cross-toolchain/bin/qemu-system-dadao`）✓；安装位行为验证（probe `--qemu .dadao/.../qemu-system-dadao` 2/2 PASS）✓。
**识别条件（独立构造 R1/R2）**：
- R1 正例（user `trap cfx0,0`）：连续 write+exit_group(42) ⇒ stdout `R1\nR2\n`、rd8=3、$?=42、mode=0、trapn0=1 — 被接管，pc+4 由顺序两道 trap 证明 ✓。
- R2 反例（hypv 同一 `trap cfx0,0`）：未被接管 → §5 向量 handler exit(0x91)、$?=145、stdout 不含 `HS\n`、trapn0=1 ✓（若被接管：`HS\n` + 0x92）。
**最小服务集**：write(64)→stdout ✓ / writev(66)→2 iovec BE ✓ / exit(93)→$?=7 ✓ / exit_group(94)→$?=42 ✓；未实现⇒-ENOSYS（rd8=-38=0xFFFFFFDA）✓ / -EBADF（rd8=-9）✓ / -EINVAL（iovcnt>1024，rd8=-22）✓；号值与锁定表一致（sha256=9ec1fadd…）✓。
**不回归**：`check-qemu-semantics` 149/149 rc=0 ✓；`test-semihost` rc=0 ✓（25-service + bootrom hand-off + semihosting + no-regression）。
**门控**（各捕自身 rc）：`make check`(L1)=0 / `check-patch-tree`=0（4 组件 129 补丁）/ `check-source-state`=0 / `check-no-residue`=0 / `check-tasks`=0 / `check_issues.py`=0。
**证据脚本**：`run-a1.sh` rc=0（27 PASS / 0 FAIL）✓；`--inject` rc=1（0/12）✓。
**我的新反例**（不在 engineer F/G）：补丁级注入（`helper.c.patch` 内 `inner_run_mode == DADAO_MODE_USER` → `!= DADAO_MODE_JAIL`）⇒ `check-patch-tree` 断言⑥+⑨ FAIL（rc=2：`patched-index blob ≠ worktree` + `HEAD diff differs`）；cp+md5 还原 ⇒ `check-patch-tree` rc=0 回绿 ✓。行为级 R2_hypv_vector 断言需重建 ⇒ 按纪律「停下报告」未重建（已通过 R2_hypv_vector 间接证明识别条件在交付二进制中正确生效）。
**完成区对齐**：文件①②③与 commit 0986dc9 逐项相符 ✓；未动 spec/contracts/manifests ✓。**遗留判定**：§实现约束 path B ✓；服务缺项（read/brk/set_tid_address/set_robust_list ⇒ 阶段 B 补）✓；探针未接门控 ✓；越界新增探针脚本可接受（先例 `min_rom_probe_04xt.py`）✓。
**判决**：**Accepted**（仅 A1 子步骤；A2/A3/B/C 未做 ⇒ 任务整体未完成）。工作区快照：review 前后 md5 全一致，`git status` 空 ✓。

#### architect 立项提交留痕（2026-10-15，分支 `p1-taskbook`）

- **档位**：**正常提交**——本提交为**规划产物立档**（用户 2026-10-15 原话「**立**」，渠道 = 经主会话问答），**非 engineer 实现、无 reviewer 判决适用**；提交信息按用户指定。
- **提交号**：`159bc42`（「立 P1：musl 静态最小集移植任务书（ADR-0025 D6）+ 登记后续两大测试集全量（用户裁定）」）。
- **文件集对账**（`git diff --cached --name-status` = **2 项** vs 本任务书范围）：① **新增**本任务书 `.tao/tasks/infra/INFRA-081t-musl静态最小集移植.md`〔**立项提交 `159bc42` 时的历史路径**；2026-10-15 改号为 `INFRA-082t-musl静态最小集移植.md`，见文件头「改号留痕」〕；② **修改** `.tao/knowledge/milestones.md`（流水行 + M8 规划区条目，**architect 台账职责**）⇒ **无漏提、无多提、无越界**（**未动** `spec/` / `.tao/contracts/` / `manifests/` / 组件补丁 / `tools/`；`.work/**` gitignored 不入库）。
- **取号依据**（**立项时取 `INFRA-081t` ⇒ 2026-10-15 改号 `INFRA-082t`**，见文件头「改号留痕」）：扫 `.tao/tasks/infra/**` + `.tao/archive/**` 全量，**占用最大 = `INFRA-080t`** ⇒ 取 **`081`**；**`master` 现状无 `INFRA-081*` 文件 ⇒ 未被占用**（注：该号**历史**上曾被 `libc-test` 任务占用、后经 `1dc0570`（`R089`）改名释放为 `TESTCASES-044t` ⇒ 本册与其**无关联**；**改号后 `081` 不再被任何现存任务占用** ✓）。
- **门控**（各捕**自身** rc，无 `tee` 吞码）：`make check`（L1）= **0** / `check-knowledge-refs` = **0** / `check-knowledge-dir` = **0** / `check-no-residue` = **0** / `check-tasks` = **0**（②「已立未开工」计数含本任务）/ `python3 tools/infra/check_issues.py` = **0**；日志落 `.work/log/infra/INFRA-081t-gate-*.log`（**立项时留档名**，`.work/` 可删区）。
- **`push`**：**未做**（本角色**禁** `push`；`master` 落地由主会话在 `/complete` 后执行）。

#### architect 补定提交留痕（2026-10-15，分支 `infra-082t-spec`）

- **档位**：**正常提交**——本提交为**规划产物补定**（主会话 2026-10-15 三条结论 + 分期结构，渠道 = 经主会话问答），**非 engineer 实现、无 reviewer 判决适用**。
- **提交号**：`8bba126`（「INFRA-082t 任务书补定：三条前置结论（builtins 后置/ISS-216 并入/补丁集化）+ 分期结构」）。
- **文件集对账**（`git diff --cached --name-status` = **3 项** vs 本任务书范围）：① **修改** 本任务书（「§前置结论」/「§分期结构」新增 + 「§范围」做项 3（QEMU 侧，**范围决定**标注）+ 「§依赖与先后」/「§已知事实 4」/「§接口规范 输出 1–2」/「§验收标准」1–10/「§待确认项」闭合标注）；② **修改** `.tao/knowledge/milestones.md`（`INFRA-082t` 流水行 + `P1` 规划区新增补定条，**architect 台账职责**）；③ **修改** `.tao/knowledge/issues.yaml`（`ISS-216` `notes` **只追加**裁定句，`status` 保持 `open`）⇒ **无漏提、无多提、无越界**（**未动** `spec/` / `.tao/contracts/` / `manifests/` / 组件补丁 / `tools/`；`.work/**` gitignored 不入库）。
- **门控**（各捕**自身** rc，无 `tee` 吞码）：`make check`（L1）= **0** / `make check-patch-tree` = **0** / `check-knowledge-refs` = **0** / `check-knowledge-dir` = **0** / `check-no-residue` = **0** / `make check-tasks` = **0** / `python3 tools/infra/check_issues.py` = **0**（34 open / 9 closed，0 blocking）；`issues.yaml` `yaml.safe_load` 通过；日志落 `.work/log/infra/INFRA-082t-spec-*.log`。
- **`push`**：**未做**（本角色**禁** `push`；`master` 落地由主会话在 `/complete` 后执行）。

#### architect 改号留痕（2026-10-15，分支 `p1-renumber`）

- **改号**：`INFRA-081t` ✗ ⇒ **`INFRA-082t`** ✓（`git mv` 任务书 + 全文件编号同步）。**理由**：避**历史同号**——`INFRA-081t` 历史上曾指 `libc-test` 任务（`1dc0570` 内 `INFRA-081t-libc-test取源与锁定.md`，经 `R089` 改名 `TESTCASES-044t` 离开 `master`）⇒ 沿用 `081` 即**同一编号在历史中指两件事**，违背 `.tao/knowledge/lessons.md §3.21`「编号须**全仓（含历史）唯一**」；`082` 全仓（工作树 + 全历史）复核**从未被占用** ✓。
- **同步面**（`git grep -n 'INFRA-081t'` 现场全仓查证，共 **7 处**）：任务书内 **4 处**（① 标题 ② 文件集对账的路径引用 ③ 取号依据 ④ 门控日志名）+ `milestones.md` **3 处**（① 任务流水行 ② 「新组件模块归属裁定」历史行 ③ `P1` 立项行 + 指针）。**处置**：**现存/前瞻引用 → `082`**；**历史留档引用**（立项提交 `159bc42` 的路径、留档日志名、`1dc0570` 的 `libc-test` 历史号）**保留原字 + 就地加注**（`lessons §4.1`：历史快照旧路径保留不回溯；保「可审计」——与 `git show <commit> --name-status` 一致）。
- **范围**：**仅编号**变更，任务书目标/范围/验收标准**一字未改** ✓。

#### architect 提交/文件集审核留痕（2026-10-15，分支 `INFRA-082t-A1`）

- **档位**：**正常提交**（**主会话 2026-10-15 指令「不带 `WIP:`」**，渠道 = 经主会话下发；留痕备查：本分支 `HEAD` 时点 reviewer 第 1 轮验收**尚未进行**、任务书 `**状态**` = `待验收`）。
- **提交号 ①** `0986dc9`（「INFRA-082t A1: QEMU 侧 SYS_UMON_SYSCALL 服务（write/writev/exit/exit_group；未实现⇒ENOSYS；149/149 不回归）」）。
  - **文件集对账**（`git diff --cached --name-status` = **3 项**）：`M components/qemu/patches/target/dadao/helper.c.patch`、`A tools/qemu/min_rom_probe_082t.py`、`M` 本任务书 ⇒ 与「完成区·阶段 A1·修改文件」①②③**逐条相符**；`A` 一项 = 完成区**已披露的越界新增**（先例 `tools/qemu/min_rom_probe_04xt.py`；`AGENTS.md`「**生成器/脚本随产物保留** 于 `tools/<module>/`」）⇒ **无漏提、无多提、无未披露越界**；**未动** `spec/` / `contracts/` / `.tao/contracts/` / `manifests/`。
- **提交号 ②** `0fa839d`（「登记 issue：Machine-01 §4.3 未覆盖 user trap cfx0,0 路由（P1-A1 实现，待授权落规范）」）。
  - **文件集对账**：`git diff --cached --name-status` = **1 项** —— `M .tao/knowledge/issues.yaml`（**只追加** `ISS-221`，`status: open`，`scope: [spec, qemu, infra]`）⇒ 无漏提/多提/越界；`spec/**` **零改动**（现场 `git status --porcelain -uall -- spec/` = 0 行；本册为 `spec/` 只读册 ⇒ **须用户原话授权**方可落纸，见 `ISS-221` 处置建议）。
- **本分支工作树**（开工前 + 提交后各核一次）：`git status --porcelain -uall` 首检 = **恰 3 项**（= ① 两改 + 一新增，与主会话指令一致）；现检 = **干净**。
- **只读核对（供验收；各捕自身 rc，无 `tee` 吞码）**：`make check`(**L1**)=**0**（`repository checks (L1): PASS`）／`make check-patch-tree`=**0**（`4 component(s), 129 patches OK`）／`make check-source-state`=**0**（`musl`/`libc-test`/`llvm-test-suite` = `patchless; skipped`）／`make check-qemu-semantics`=**0**（`149 total, 149 passed, 0 failed`）；`python3 tools/infra/check_issues.py`=**0**（`35 open, 9 closed`，`resolved_by` 约束 OK）；`issues.yaml` `yaml.safe_load` 通过（44 条）。日志：`.work/log/infra/INFRA-082t-a1-verify-{L1,patch-tree,source-state,qemu-sem}.log`（`.work/` 可删区）。
- **`merge` / `push`**：**均未做**（本角色**禁** `push`；`master` 落地由主会话在 `/complete` 后执行）。`master` 未动（仍 `761dfa3`）。

#### architect 阶段级 A1 收尾/提交/文件集审核留痕（2026-10-15，分支 `INFRA-082t-A1`）

- **档位**：**正常提交**（依据 = 上「第 1 轮 reviewer 验收」判决 `Accepted`，**仅 A1 子步骤**；**阶段级**，见 `**阶段进度**`）。
- **提交**：分支 `INFRA-082t-A1` 头提交（提交信息 = `INFRA-082t A1: 阶段级收尾（reviewer Accepted；QEMU SYS_UMON_SYSCALL 服务 + 149/149 不回归）+ 阶段进度`；**只 `commit`，未 `push`**）。**注**：本留痕与提交同体 ⇒ **不内嵌 SHA**（SHA 随留痕内容变化而变、会自指失真）；SHA 以分支头 / 父会话回报为准。
- **本笔内容**：① `**阶段进度**` 行 + `**状态**` 口径说明（任务级 `待验收`，**不**置 `已验证`；**P1 整体未完**）；② reviewer 第 1 轮验收记录（A1）落纸；③ `milestones.md` `INFRA-082t` 流水行：`状态` `待开始` → **`待验收`** + 补「**阶段 A1（QEMU `SYS_UMON_SYSCALL` 服务）已完成并验收（2026-10-15，reviewer `Accepted`）**，A2/A3、B、C 待做 ⇒ 任务级 `待验收`」（照 `SPEC-142t`/`SPEC-143t` 阶段级先例）。
- **文件集对账**（`git diff --cached --name-status -M` ↔ 本笔范围）：**2** 项 = **2 M**，即 `.tao/tasks/infra/INFRA-082t-musl静态最小集移植.md`（reviewer 第 1 轮验收记录 + `**阶段进度**` 行 + `**状态**` 口径说明 + 本留痕）、`.tao/knowledge/milestones.md`（`INFRA-082t` 流水行状态与阶段说明）⇒ **无漏提、无多提、无越界**（未触 `spec/**`、`components/**`、`contracts/**`、`.tao/contracts/**`、`manifests/**`、`tools/**`）。
- **收尾检查（阶段级口径）**：**门控**（各捕**自身** rc，无 `tee` 吞码）`make check`(**L1**)=**0** ／ `check-patch-tree`=**0**（4 组件 129 补丁）／ `check-source-state`=**0** ／ `check-qemu-semantics`=**0**（**149/149**）／ `check-no-residue`=**0** ／ `check-knowledge-refs`=**0** ／ `check-knowledge-dir`=**0** ／ `check-tasks`=**0** ／ `python3 tools/infra/check_issues.py`=**0**（35 open / 9 closed / 0 blocking）；**L2/L3 归本任务整体收尾**（阶段级不跑）。**证据** = `.work/evidence/INFRA-082t/run-a1.sh` ✓。**无临时残留**（`git status --porcelain -uall` 仅 1 项 = reviewer 审阅记录）。日志 `.work/log/infra/INFRA-082t-a1-closeout-*.log`（`.work/` 可删区）。
- **下一件**：**A2**（musl 补丁集骨架 + 锁条目补丁化）。**`merge` / `push`**：本笔**未** `merge`、**未** `push`（`merge --ff-only` 落地由主会话/本角色按指令执行；`push` 由主会话在 `/complete` 后执行）。

#### 第 2 轮 engineer 自审（阶段 A2+A3，2026-10-15，分支 `INFRA-082t-A2`）

**范围**：musl 补丁集 16 份（`arch/dadao/**` 12 + `src/**/dadao/**` 3 + `configure` 1）+ 锁条目 1 处 + `tools/infra/build_musl.py` + 证据脚本。

**逐行审查（要点 + 判决）**：
1. `arch/dadao/syscall_arch.h`：`__dadao_trap` 只把「按 mask 选源」放在 C、把物理寄存器绑定交给局部寄存器变量 ⇒ 反汇编核对（**两次独立取证**：① `sccp` 内 71 项跳表现场读出，`nr=63/64/65/66` 指到「指针槽=1」体；② 产物 `write()` 的公共尾 `rd16=a0/rd17=a2/rd2rb {rb16},{rd4}`）⇒ 与 `contract-syscall §3` 逐槽一致。**判决：正确**。
2. `__dadao_argmask` 的 `default: p0 = 0`：未列号会把 `rb16` 置 0 —— 今日**可证无害**（服务方对未实现号一律 `-ENOSYS`，参数不被读），但它是「加服务必须同步加表项」这条不变量的落点 ⇒ 已写入头文件注释 + README。**判决：可接受（延后项 F9）**。
3. `arch/dadao/crt_arch.h`：静态帧（argc/argv/envp/auxv）**从产物 ELF 回读核对** 18 octa 全对（`AT_PAGESZ 6→4096`、`AT_UID/EUID/GID/EGID`、`AT_HWCAP`、`AT_EXECFN`、`AT_NULL` 终止）；`#ifdef SHARED` 分流使 `dlstart.c`/`rcrt1.c` 走「栈即 p」的正统形态。**判决：正确**。
4. `arch/dadao/pthread_arch.h` + `__set_thread_area.s`：TP=`rb3` 读（`rb2rd {rd8},{rb3}`）/写（`rb2rb {rb3},{rb16}`）成对；`TLS_ABOVE_TP`+零偏置与 `R_DADAO_TLS_*` 公式自洽（无 0x800 之类遗留偏置）。**判决：正确**。
5. `src/setjmp/dadao/*`：帧 161 octa 与 `bits/setjmp.h` 逐段对齐（0/512/520/776/1032，末 1288）；`cs.z {rd16}?, rd8, rd18(1), rd16` 按 `contract-isa §6.5` 实现 `val==0⇒1`（**不沿用 picolibc 端口那条等价于 no-op 的写法**）；仅 `MRPTR==0` 精确（与 `INFRA-068t` 同限度）。**判决：正确**。
6. `arch/dadao/atomic_arch.h`：机器无原子（`contract-isa §14` excluded + QEMU ILLI 桩）⇒ 单线程语义 + 头文件写明「开线程前必须换」；`__clone` 由上游通用实现返回 `-ENOSYS`（线程显式失败，非静默）。**判决：可接受（延后项 F10）**。
7. `arch/dadao/arch.mak`：`$(info …)` 每次构建打印被排除的 13 源；`check-patch-tree` 断言③/⑤/⑥/⑨ 全绿证明补丁集与工作树一致；`ar t` 复核被排除目标确不在 `libc.a`。**判决：正确**。
8. `bits/signal.h` 的 `mcontext_t`：`[OPEN]` 占位（v5 无 DADAO 信号帧 ABI；`D2` 无内核）—— 只服务编译，且**不静默**（头文件写明「谁定真帧布局谁重写」）。**判决：可接受（延后项 F11）**。
9. 证据/自审的**防造假**：`run-a23.sh` 44 条断言逐条打印「名/期望/实际」；`--inject` rc=1；两条**产物级反例**（EI_DATA 翻转后的 ELF 被同一 checker 判 FAIL；`__NR_write` 改 65 后号表 checker 退非零）⇒ 断言非恒真；注入一律在 **scratch 副本**上进行（`mktemp -d`），**未触碰**任何仓库/工作树文件 ⇒ 无需还原（更无 `git checkout`/`restore`）。**判决：合格**。

**finding 处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `bits/signal.h` 与 `pthread_arch.h` 重复定义 `MC_PC` | ✅已修 | 删 `bits/signal.h` 那份（保留 musl 惯例位 = `pthread_arch.h`，唯一用户 `pthread_cancel.c` 经 `pthread_impl.h` 取） | `make -j8` rc=0；`build_musl.py` 10/10；`check-patch-tree` rc=0 |
| F2 `build_musl.py::compile_program` 的 `inject` 形参未使用 | ✅已修 | 删形参 + 调用点 | `--inject` 仍 rc=1；正常 rc=0 |
| F3 `bits/setjmp.h` 写「`sigsetjmp`/`siglongjmp` 均未提供」不准确（实则仅前者缺） | ✅已修 | 改为「`sigsetjmp` 缺（上游空槽）⇒ 用之链接失败；`siglongjmp` 存在但无可用缓冲」 | 同上 |
| F4 README 写「用 `crypt()` 即链接失败」缺精度 | ✅已修 | 写明 `crypt_r.o` 引用被排除的 `__crypt_sha512`（`nm` 实测 `U __crypt_sha512`） | `nm lib/libc.a` 复算 |
| F5 证据 A 段 `grep -c` 多文件求和写法取不到计数（`patches/*.patch` 不是顶层 glob） | ✅已修 | 改 `grep -rh` 求和 + 逐文件循环判 `==1` | `run-a23.sh` 44/0 rc=0 |
| F6 证据 D 段 `%N` 检查命中**自己文档里引用的** `%0` | ✅已修 | 先剥注释（helper `no_pct_operand.py`）再计数 | 同上（计数=0） |
| F7 `build_musl.py` 遇损坏 ELF 抛 traceback 而非报 FAIL | ✅已修 | `parse_elf` 捕获并回 `parse_error`，新增「program headers parseable」断言 | 反例：EI_DATA 翻转 ⇒ 6 条 FAIL、rc=1（G 段） |
| F8 `__dadao_argmask` 未列号默认 mask=0（有指针的未列号会错放） | ⏸延后 | 不改行为（今日服务端一律 `-ENOSYS` ⇒ 可证无害）；写入「加服务同步加表项」不变量 | 头文件/README 注明；A1 服务集 4 号全在表内 |
| F9 原子非真（单线程语义） | ⏸延后 | 机器无 LR-SC/`fence`（`§14` excluded）⇒ P1 内无替代；头文件写明与重访触发条件 | `contract-isa §14` + QEMU 桩源码 |
| F10 `mcontext_t` 为 `[OPEN]` 占位 | ⏸延后 | 无 DADAO 信号帧 ABI 可依（`D2` 无内核/信号）⇒ 只保证编译 | 头文件 `[OPEN]` 标注 + 遗留⑨ |
| F11 `__syscall7` 未定义（上游定义了宏） | ❌不修 | 与 riscv64 及所有上游 arch 一致，且全树无 7 参调用 | `grep` 全树无 7 参 `__syscall` 调用 |

**判决**：finding 全部 `✅已修`（附复验）或 `⏸延后`/`❌不修`（附理由与证据）⇒ 状态可置 `待验收`；**仅阶段 A（A1+A2+A3）**，B/C 未做 ⇒ 任务整体未完成。
