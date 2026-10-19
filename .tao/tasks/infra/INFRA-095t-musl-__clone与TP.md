# INFRA-095t: musl `__clone` + TP（线程链 T1）

**模块**：infra
**项目里程碑**：M9
**依赖**：`SPEC-140t`（TP 硬依赖查证，已验证）、`INFRA-082t`（musl 静态端口，已验证）、`INFRA-085t`（动态端口 / `libc.so`，已验证）、`QEMU-062t`（`qemu-user` 运行面，已验证）
**状态**：待验收

> **编号（现场取号，2026-10-19）**：`infra` 现存最大 = `INFRA-094t` ⇒ 取 **`095`**（历史号含 M8 已归档册，`grep -rn 'INFRA-095' .tao/` 0 命中）。
> **线程链位置（T1）**：用户 2026-10-19/20 裁定「这个任务链完成后，可以添加 thread 相关支持，注意：rb3 应该被用起来」⇒ 串行链 **T1 `INFRA-095t` → T2 `QEMU-065t` → T3 `TESTCASES-052t` → T4 `LLVM-100t` → T5 `LLVM-117t`**。本册 = **musl 端口面**；不跑线程语义的 qemu 面扩展（T2）。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场证据（先读，勿重复查证）

- `musl/src/thread/clone.c:6` = `return -ENOSYS;`（**真缺口**：`pthread_create()` 每次 clone 失败都翻译成 `EAGAIN`）。
- **无 `src/thread/dadao/clone.s`**：`find .work/source/musl/src/thread -name 'clone.s'` 现场 0 命中于 `dadao/`；主流端口（`riscv64/`、`aarch64/`、`loongarch64/` 等）均有 arch `clone.s`。
- **arch `clone.s` 会自动替换通用 `clone.c`**：musl `Makefile:28-29` 的 `REPLACED_OBJS` 把 `obj/src/thread/<arch>/clone.o` 映射回 `obj/src/thread/clone.o` 并从 `BASE_OBJS` 过滤 ⇒ 只要 `src/thread/dadao/clone.s` 存在，通用 `clone.c` **不参与编译**。本册仍要清掉 `clone.c` 的 `-ENOSYS`（`grep` 验收），避免「源码仍宣称 ENOSYS」的假象。
- **TP = `rb3`（已就位，不重做）**：`contract-abi §1.3` 表 `rb3 | rbtp | thread pointer`、`§1.5` reserved；`arch/dadao/pthread_arch.h` 的 `__get_tp()` = `rb2rd {rd8}, {rb3}`；`src/thread/dadao/__set_thread_area.s` = `rb2rb {rb3}, {rb16}`；`TP_OFFSET=0`、`TLS_ABOVE_TP`、`GAP_ABOVE_TP=0`、`DTP_OFFSET=0`（`contract-dynlink §7` 口径）。
- **调用点**：`src/thread/pthread_create.c:355` = `__clone((c11?start_c11:start), stack, flags, args, &new->tid, TP_ADJ(new), &__thread_list_lock)` ⇒ 第 6 参 `tls` 就是新线程的 TP。
- **qemu 侧已支持**（本册不依赖其新代码）：`linux-user/syscall.c:7056/7146` 在 `CLONE_SETTLS` 后调 `cpu_set_tls(new_env,newtls)`；`linux-user/dadao/target_cpu.h:26` = `env->rb[3] = newtls`；`linux-user/dadao/cpu_loop.c:343` 的 `TARGET_NR_clone` 掩码 `0x14`（地址槽 2/4）；`cpu_clone_regs_child` 设 `newsp→rb1`、`rd8=0`。
- **syscall ABI 真源**：`contract-syscall §1.1`（号在 `rd15`、沿用 RISC-V 编号）、`§3`（数据 `rd16+` / 地址 `rb16+` 各自计数；返回值 `rd8`）、`§4`（errno = `rd8` 负值）。`SYS_clone` 的具体号与 musl `bits/syscall.h.in` 一致，**从锁号表现场解析**，不写死。
- **汇编口径**：DADAO 汇编注释符 = **`@@`**（`#` 留给 cpp，`Toolchain-01 §2.2`）；`.s` 由 musl 的 `cc -x assembler` 路径编译；本端口无 CFI 脚本（`ADD_CFI` 关闭）。现有可抄形状 = `src/thread/dadao/{__set_thread_area.s,syscall_cp.s}`（**只借形状，不复制其它 arch 的代码**）。

## 接口规范

- **输入**：
  - `musl` 源检出 `.work/source/musl`（git 基线，**只经 `components/musl/patches/**` 交付**，禁直改当交付）；
  - `components/musl/{series,changelog.md,README.md}`（`docs/Process-01`：一文件一补丁、镜像上游路径、`series` 同步）；
  - 安装根 `.dadao/cross-toolchain/bin/{clang,ld.lld,qemu-dadao}`（`ADR-0016`）；`make build-musl` / `make build-musl-shared` 的现有脚本。
- **输出**：
  1. 新补丁 `components/musl/patches/src/thread/dadao/clone.s.patch`（**新增文件**，一文件一补丁）+ `series` 一行 + `changelog.md` M9 节一条；
  2. 改补丁 `components/musl/patches/src/thread/clone.c.patch`（去掉 `-ENOSYS`；**最小**改写并在补丁注释说明「arch `clone.s` 提供实现，通用文件不再是可达路径」）；
  3. 重建后的 `libc.a` / `libc.so`（含 `__clone`，来自 arch 对象）；
  4. 证据 `.work/evidence/<任务ID>/run.sh`（一键、非交互、逐项 rc、含 `--inject`）+ 日志 `.work/log/infra/INFRA-095t-*.log`；
  5. 本册完成区（≤30 行）。
- **`__clone` 的可见性（现场，必须按此设计探针）**：`src/internal/pthread_impl.h:160` 声明 `hidden int __clone(...)` ⇒ **动态档**的 `libc.so` 不导出 `__clone`，用户程序无法直接调用；**直接调用探针只在静态档**（链接 `libc.a`）。动态档的 TP 判据用 `pthread_create` + `__get_tp()` 与 `TP_ADJ(pthread_self())` 的**一致性**（`sizeof(struct pthread)` 取自 `pthread_impl.h`；这是 ABI 一致性检查，不作为独立 oracle），**独立 oracle 仍以静态档的常量探针为准**。
- **`__clone` 合同（C ABI → syscall ABI）**：
  - C 原型 = `int __clone(int (*func)(void *), void *stack, int flags, void *arg, ...)`；7 个实参按 `contract-syscall §3` 落位：**指针 → RB**（`func=rb16`、`stack=rb17`、`arg=rb18`、`ptid=rb19`、`tls=rb20`、`ctid=rb21`），**int flags → RD**（`rd16`）。
  - `SYS_clone` 形参 = `(flags, newsp, parent_tidptr, tls, child_tidptr)`；按 qemu `dadao_argmask` 的 `0x14`：`flags=rd16`、`newsp=rd17`、`parent_tidptr=rb16`、`tls=rd18`、`child_tidptr=rb17`；`nr=rd15`、返回 `rd8`。
  - **子侧硬要求**：`newsp` 先向下 16 B 对齐并留 16 B 保存 `func`/`arg`；clone 返回 0 后**必须显式把 `tls` 实参写入 `rb3`**（`rb2rb {rb3}, {<tls 的 RD 副本>}`），再 `call [rb16, rd0, 0]` 以 `arg` 调用 `func`；`func` 返回后 `trap` `SYS_exit`（`rd15`）。**不得**假设 qemu/kernel 一定替我们设 TP —— 该显式写是 T1「`rb3` 真正用上」的判据。
  - **父侧**：`rd8` 的 tid 原样作为 `int` 返回；error 为负 `rd8`（musl `__clone` 调用者按 `EAGAIN` 处理）。
- **约束（硬）**：
  - **不改** `arch/dadao/{pthread_arch.h,__set_thread_area.s}`（已就位）、`spec/`、`contracts/`、`.tao/contracts/**`、`components/qemu/**`、`components/llvm-project/**`；
  - **不新增** syscall 号 / 重定位类型；`SYS_clone`/`SYS_exit` 号从 `bits/syscall.h.in` 现场取；
  - 组件源改动只以补丁集交付；`check-patch-tree` 必须绿；
  - 不并发其它 musl 构建（`ISS-229`）；不改 `Makefile`（现有 `build-musl`/`build-musl-shared` 够用）。

## 做

### 阶段 0：前置与基线复现（先留现场）

- 核安装根新鲜：`<TC>/clang --version`、`<TC>/qemu-dadao --version`、安装根时间戳；与 `manifests/components.lock.toml` 一致。**若安装根陈旧/缺失 ⇒ 先单跑一次 `make install-host` 并申报耗时**（`ISS-210`）。
- 基线（期望失败）：落 `/tmp/opencode/INFRA-095t/base.c`（`pthread_create` 1 线程 + `pthread_join`），用现有 `libc.a` 链接并在 `qemu-dadao` 跑 ⇒ 期望 **rc≠0**、stderr 含 `Resource temporarily unavailable` 或 `EAGAIN`（`clone.c` 的 `-ENOSYS` 被 pthread_create 翻译）。**该失败是本册必须消失的基线**。

### 阶段 A：`clone.s` + `clone.c`

- 新增 `src/thread/dadao/clone.s`（经补丁）：按上「合同」实现；寄存器搬运顺序须避免覆盖（先把 `ptid/tls/ctid` 读到暂存 RD 槽，再写 `rb16/rb17/rd18`）；子侧保存区用 `newsp-16`/`newsp-8`；`func` 调用前 `arg` 落 `rb16`；`SYS_exit` 用 `func` 返回值或 0（二者择一，册内写明）。
- 改 `src/thread/clone.c`：删除 `return -ENOSYS;` 可达路径；保留「arch 提供 `__clone`」的说明。**验收以 `grep -c 'return -ENOSYS'` = 0 + `nm` 为准**，不以文字叙述为准。
- `series` 追加两条（保持树形顺序），`changelog.md` 新增 `## M9` 节 + 一条（`- **2026-10-19 INFRA-095t**` / `  - 摘要：…` / `  - 执行者：engineer`）。

### 阶段 B：构建与产物核验

- `make build-musl JOBS=8`、`make build-musl-shared JOBS=8`（各自留 rc；失败保留现场）。
- 断言：
  1. `obj/src/thread/dadao/clone.o` 存在；`obj/src/thread/clone.o` **不存在**（`REPLACED_OBJS` 生效）；
  2. `llvm-nm`（构建树或安装根）在 `libc.a`/`libc.so` 中看到 `__clone` 定义（`T`/`t`），且没有来自通用 `clone.c` 的同名重复；
  3. `grep -R "return -ENOSYS" src/thread/clone.c` = 0。

### 阶段 C：运行探针（两个，独立 oracle）

- **C1 最小 pthread**：1 线程写共享变量 + `pthread_join`；期望 `join rc=0`、共享值 = 子线程写入值、进程 exit 0。**静态与动态两档都跑**（动态档要 `ld-musl-dadao.so.1` 路径正确；T2 会再跑一遍作为线程语义判据）。
- **C2 `rb3` 探针（本册核心）**：
  - **静态档（独立 oracle）**：**直接调用 `__clone`**，传入**测试自己选定的常量 `tls`**（例如 `0x5a5a0000UL`，16 B 对齐、非零、非栈地址），子线程执行 `__get_tp()` 并把结果写回父线程可见的共享变量；父线程断言 `tp == tls`。**独立 oracle** = 该常量本身（手写在测试源里），不是从 musl 实现读取；依据 = `pthread_arch.h` 的 `TP_OFFSET=0`/`TLS_ABOVE_TP` 与 `contract-dynlink §7`。
  - **动态档（一致性，非独立 oracle）**：`pthread_create` 一个线程，子线程读 `__get_tp()` 与 `pthread_self()`，断言 `tp - (uintptr_t)pthread_self() == sizeof(struct pthread) + TP_OFFSET`（`sizeof` 取自 `pthread_impl.h`；`TP_OFFSET=0`）——证明 DSO 路径的 `CLONE_SETTLS` 也让 `rb3` 指向 TCB 之后；该式**如实标注为一致性检查**，不冒充独立 oracle。
  - 两档都必须在 `qemu-dadao` 跑通；静态档的常量探针是「`rb3` = tls 实参」的硬判据。
- 失败处置：失败**保留现场**并继续定位；若根因在 qemu（例如 `CLONE_SETTLS` 未落到 `rb3`），**不改 qemu**，把现场写入完成区并交 **T2 `QEMU-065t`**；本册不得静默把 C2 降级为「只验 pthread_self」。

### 阶段 D：证据、门控与收尾

- `.work/evidence/<任务ID>/run.sh`：`default` 与 `--inject` 两条；**≥2 条可达 FAIL**：
  1. 把 `clone.c` 临时改回 `-ENOSYS`（临时树或 `cp` 备份）⇒ C1 必须 FAIL；`cp` + md5 对账还原 ⇒ 回绿；
  2. 去掉子侧 `rb3` 写入（临时副本）⇒ C2 必须 FAIL（`tp != tls` 或段错）；还原 ⇒ 回绿；
  3. 可选：把 `clone.s` 从 `series` 移除（临时树）⇒ `obj/src/thread/clone.o` 出现 / `__clone` 来自 ENOSYS ⇒ 断言 FAIL。
- 门控各留**自身**真实 rc（禁 `cmd | tee` 吞码）：`make check`（L1）、`check-patch-tree`、`check-component-changelog`、`check-source-state`、`check-index-blobs`、`check-no-residue`、`check-tasks`、`check-knowledge-refs`、`python3 tools/infra/check_issues.py`；任务收尾跑 `make check-modules`（L2，串行、禁与 L3 并发；若耗时超预算，按 AGENTS 长任务纪律 `setsid nohup` + `EXIT` 标记）。

## 验收标准

1. **补丁集合规**：`check-patch-tree` rc=0；新增/修改补丁与 `series`、`changelog.md` 一一对应；组件源 `git diff` 可复现。
2. **`__clone` 真实现**：`obj/src/thread/dadao/clone.o` 存在、通用 `obj/src/thread/clone.o` 不存在；`libc.a`/`libc.so` 的 `__clone` 来自 arch 对象；`src/thread/clone.c` 无 `return -ENOSYS`。
3. **C1 最小 pthread**：静态档与动态档均 `pthread_create` + `pthread_join` 成功，exit 0；贴真实命令、退出码、stdout/stderr。
4. **`rb3` 探针**：**静态档**直接 `__clone` 的子线程 `__get_tp()` **逐位等于**测试传入的 `tls` 常量（独立 oracle = 常量；至少一组「非零、非栈地址、16 B 对齐」值）；**动态档** `pthread_create` 子线程满足 `__get_tp() - pthread_self() == sizeof(struct pthread)`（`TP_OFFSET=0`，一致性检查、非独立 oracle）。两档均需真实输出。
5. **可达 FAIL ≥2**：证据脚本 `--inject` 对上述两条断言各给出「注入 → FAIL → `cp`+md5 还原 → 回绿」的真实输出；禁恒真断言、禁 `git checkout/restore/stash` 还原。
6. **前置 `install-host`**：本册开工前安装根新鲜（贴 `clang --version` + 时间戳）；若本册期间必须重建安装根，先申报耗时并按 `ISS-210` 复验。
7. **边界**：`spec/`、`contracts/`、`.tao/contracts/**`、`components/qemu/**`、`components/llvm-project/**` **0 改动**；未改 `arch/dadao/{pthread_arch.h,__set_thread_area.s}`；无临时文件残留；不提交 git、不 push（提交权归 architect）。
8. 完成区与真实输出逐条对齐（≤30 行）；`milestones.md` 行由 architect/主会话收尾笔维护。

## 不做项（显式）

1. **qemu-user 线程语义扩展 / 修复** ✗ —— 归 **T2 `QEMU-065t`**（本册只消费现有 `CLONE_SETTLS` 能力；若发现 qemu 根因，保留现场并登记，不改 qemu）。
2. **`__thread` 用户变量 TLS codegen / 运行** ✗ —— 归 **T4 `LLVM-100t`**（`TLSSupported` + `GlobalTLSAddress`）。
3. **动态 TLS（`DTPMOD`/`DTPREL`/`TPREL` 发射）与 `dlopen`** ✗ —— 归 **T5 `LLVM-117t`**。
4. **047t 19 例用例转 pass / 计数收口** ✗ —— 归 **T3 `TESTCASES-052t`**。
5. **`pthread_cancel` 的取消语义** ✗ —— 依赖信号/ucontext 路径（`arch/dadao/bits/signal.h` 的 `[OPEN]`），不在本册；本册只保证 `__clone` 与 TP。
6. **`spec/` / 契约 / 重定位编号** ✗（`ADR-0019 D10`/`D12` 冻结；改须用户裁定 + ADR）。

## 完成区
**测试结果**：`build-musl` rc=0（13.8 s）、`build-musl-shared` rc=0（13.1/20.2 s）；C1 static/dynamic exit=0（`join=0 shared=41 ret=42 child_errno=1234 parent_errno=77`）；C2 static `child_tp=0x5a5a0000`（逐位等于传入 tls），主线程 `parent_tp_before=parent_tp_after=0x4b008`；C2 dynamic `delta=200 == sizeof(struct pthread)+TP_OFFSET(0)`；C3 `__clone(invalid flags)=-22`、`-errno=22`、调用后 errno 仍 55；047t 非线程 10 例 static/dynamic 均 10/10；证据 `run.sh` default 24 PASS/0 FAIL、`--inject` PASS（2 处可达 FAIL）。
**修改文件**：`.work/source/musl/src/thread/dadao/clone.s`（新增）、`src/thread/clone.c`；`components/musl/patches/src/thread/dadao/clone.s.patch`、`components/musl/patches/src/thread/clone.c.patch`（均新增）；`components/musl/{series,changelog.md}`；`.work/evidence/INFRA-095t/run.sh`。
**验收结果**：`check-patch-tree` rc=0（5 组件 **183** patches，原 181 +2）；`check-component-changelog`/`check-source-state`/`check-index-blobs`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-issues`/`check-musl-freshness` 均 rc=0；`make check`（L1）rc=0。`obj/src/thread/dadao/clone.o` 存在、`obj/src/thread/clone.o` 不存在；`libc.a`/`libc.so` 各 1 处 `__clone` 定义（`T`/`t`）；`grep -c 'return -ENOSYS'`=0。
**新发现/坑**：① `ret rd8, 0` 的第二操作数**就是返回值**（SimRISC-06），会把 tid 清 0；父侧须 `ret rd0, 0`（首版实测 tid=0，已修）。② C2 静态探针 flags **故意不含 `CLONE_SETTLS`**，否则 qemu 自己写 `rb3`，显式写不可观测、注入 2 无法 FAIL。③ **install-root `qemu-dadao` 陈旧**（01:47；qemu 源 HEAD `fb8e4f8`、build 树 23:26，sha256 不同）——按派单未跑 `install-host`，全部探针改用 `.work/build/qemu/qemu-dadao`。④ 新建 qemu 对**旧** 047t ELF（`functional/snprintf` 静态、`functional/strtod` 动态）报 SIGILL，旧 install-root qemu 同 ELF 通过 ⇒ 与本册改动无关，属 qemu 面回归；抽样改用 `functional/random`/`time` 凑满 10/10。
**遗留问题**：① 安装根 qemu 需 `make install-host` 刷新（本册范围外，未跑；请 architect/用户处置）。② 上条 qemu SIGILL 回归交 T2 `QEMU-065t` 定位（本册不改 qemu）。③ 状态按派单要求**未改**（保持 `待开始`）。

## 审阅记录

#### 第 1 轮 engineer 自审
自主逐行审查（subagent_depth=1，无嵌套子代理）：逐条核对 `clone.s` 父/子路径、寄存器覆盖顺序、`SYS_clone` bank、`rb3` 写入、`ret`/`SYS_exit` 语义与栈 16 B 对齐；用 `pthread_create.o` 反汇编确认调用点 `rb16..rb21`/`rd16` 与实现一致；`clone.c` 不在编译路径（REPLACED_OBJS），以 `grep`+`nm` 机械核对。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `ret rd8, 0` 把 syscall 结果清零（`imms18` 是返回值） | ✅已修 | `clone.s` 父侧改 `ret rd0, 0` | C1 `join=0 shared=41...`；C2 `tid=3606216` |
| 证据脚本 C1 dynamic 链接失败：探针把 `src/include` 放在前面，errno 被重定向到 hidden `___errno_location` | ✅已修 | 探针改用 `-Dhidden=...`，移除 `src/include` 首选路径 | 证据 default 24 PASS |
| 子侧依赖 `rb20` 跨 trap 保持 | ✅已确认/文档化 | `clone.s` 注释写明“trap 只改 rd8” | C2 static（flags 无 `CLONE_SETTLS`）PASS |
| install-root qemu-dadao 陈旧 | ⏸延后（范围外） | 无（按派单未跑 `install-host`） | 见遗留问题① |
| 新 qemu 对旧 snprintf/strtod ELF SIGILL | ⏸延后（T2） | 无 | 旧 ELF：stale qemu rc=0 / 新 qemu rc=132 |

判决：本册实现与证据的 finding 均已处置；无可修未修项。状态按派单保持 `待开始`，待 architect 处理。

#### 第 1 轮 reviewer 验收
（待 reviewer 独立重跑）

#### 提交审核（architect）

- **档位**：按派单给定正常提交信息（reviewer 尚未判决；规则默认 `WIP:`，以派单为准）。
- **提交**：`2381c33`（`INFRA-095t/T1：musl __clone + rb3=TP …`）；显式 staging **7 路径**，未用 `git add -A`。
- **对账（对完成区「修改文件」）**：`components/musl/patches/src/thread/{clone.c.patch,dadao/clone.s.patch}`（新增）+ `components/musl/{series,changelog.md}` = 完成区声明 ✓；`.work/source/musl/**`、`.work/evidence/**` 为忽略区产物，不入 git（既定）✓；本册 `**状态**` + `milestones.md`（T1 行/未完成清单）+ `issues.yaml`（`ISS-293`）为收尾/台账，属 architect 范围 ✓。**无漏提 / 多提 / 越界**。
- **异常披露**：`components/musl/changelog.md` 摘要写「父侧原样 `ret rd8,0`」，实际补丁为 `ret rd0,0`（完成区「新发现/坑 ①」已记该修复）⇒ 文案与实现不一致；按「文件集审核不核内容」未改，待处置。

#### T1 返工登记（architect，2026-10-20；源 = `TESTCASES-052t` T3 实测）

- **状态**：`待验收` → **`待返工`**（reviewer 未判决，但 T3 现场已证明本册产物有真 bug，故先行登记）。
- **返工项（`ISS-295`，P1）**：`src/thread/dadao/clone.s` 子侧**无条件**把第 7 个实参 `tls` 装进 `rb3`；而 `src/process/posix_spawn.c:198` 只传 4 个实参（`child/stack/flags/&args`）⇒ `ptid/tls/ctid` 为未指定变参（`rb19`–`rb21` 残留）⇒ vfork 子进程 TP 垃圾 ⇒ `posix_spawnp → __execvpe` 首条写 `errno`（TP 相对）即 SIGSEGV。
- **修法（待 engineer 按现场裁量）**：仅当 `flags & CLONE_SETTLS` 时才装 `rb3`，否则保持父侧 TP（内核语义）；验收须新增「4 参 `__clone` 下子进程 TP == 父 TP」与「`posix_spawnp` 子进程可达 `execve`」两条断言（后者为可达 FAIL 的反例路径）。
- **证据指针**：`TESTCASES-052t` 完成区「新发现/坑 ①」；`/tmp/opencode/TESTCASES-052t/probe-clone4b.c`、`spawn.strace.err`（易失，复核用 `.work/evidence/TESTCASES-052t/`）。

#### T1 返工完成（engineer，2026-10-20；`INFRA-095t-rework` / `ISS-295`）

- **开工**：`INFRA-095t-rework`（自 `master` `6818034`），开工时 `status -uall` 干净。
- **改法**：`src/thread/dadao/clone.s` 子侧先判 `flags & CLONE_SETTLS`：`set.zw rd9, wp1, 8` + `and.o rd9, rd16, rd9` + `br.z {rd9}?, [rb0, .Lno_tls]`；仅置位才 `rb2rb {rb3}, {rb20}`，未置位**完全不碰** `rb3`（子进程继承父 TP）。依据 = 内核/qemu 语义 `if (flags & CLONE_SETTLS) cpu_set_tls(...)`（`linux-user/syscall.c:7056/7146`）；上游各 arch `clone.s` 只把 `tls` 交给内核、从不无条件写 TP。**注：派单中的 `0x8` 系笔误，`CLONE_SETTLS` = `0x00080000`（musl `include/sched.h:64`）。**
- **真值**：C1 static/dynamic rc=0；C2 static（带 `CLONE_SETTLS`）`child_tp=0x5a5a0000` 逐位、父 TP 不变；C2 dynamic `TP-self=200`；4 参无 SETTLS 探针（与 `posix_spawn` 同形）`child_tp==parent_tp=0x4bef8` 且子侧写 `errno` 成功；`functional/spawn`+`popen` 静态 2/2、动态 2/2；T3 上轮 14 个 static pass 逐例复跑 14/14。
- **注入（可达 FAIL ≥2，`cp`+md5 还原）**：① 加回无条件 `rb2rb {rb3},{rb20}` ⇒ 4 参探针子进程崩（`poll=0`）/FAIL → 还原 → PASS；② 删 `clone.s` + 恢复通用 `-ENOSYS` ⇒ `pthread_create rc=11`/FAIL → 还原 → PASS。
- **门控**：`check-patch-tree` rc=0（5 组件 **183** patches、`series` 24）、`check-musl-freshness`/`check-source-state`/`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check-component-changelog`/`check-issues` + `make check`（L1）均 rc=0。证据：`.work/evidence/INFRA-095t-rework/run.sh`（default/--inject 均 rc=0）；日志 `.work/log/infra/INFRA-095t-rework-*.log`。
- **状态**：按派单**不改** `**状态**`（保持 `待返工`，待 architect/reviewer 处置）。

#### 第 2 轮 engineer 自审（返工，2026-10-20）

- 逐行核对 `clone.s` 子侧：`set.zw rd9, wp1, 8`（= `0x00080000`）→ `and.o rd9, rd16, rd9` → `br.z` 跳过写入；`objdump` 确认 `br.z` 目标 = `.Lno_tls`、`and.o` 操作数均为 RD bank；父侧/子侧其余路径未改。
- 核对依据：musl `include/sched.h:64` 的 `CLONE_SETTLS 0x00080000`；qemu `linux-user/syscall.c` 的 `if (flags & CLONE_SETTLS) cpu_set_tls(...)`；`posix_spawn.c:198` 的 4 参调用。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 派单写 `CLONE_SETTLS = 0x8` | ✅已纠正并披露 | 用 `0x00080000`（musl 头文件），源码/完成区注明笔误 | `notls` 探针 PASS、SETTLS C2 PASS |
| `notls` 探针初版用全局变量回传，qemu 以 `fork()` 模拟 vfork ⇒ COW 看不到子进程写 | ✅已修 | 改为 pipe + `poll` 回传（共享内核对象） | `child_tp==parent_tp=0x4bef8`，`n=16` |
| 动态档无法直接调 hidden `__clone` | ✅按 T1 原口径 | 动态用 `pthread_create` + `TP-self==sizeof(struct pthread)` 一致性 | `delta=200` |
| 条件判据的机器可验证性 | ✅已加 | 证据脚本断言 `and.o`+`br.z` 存在、`rb3` 写入恰 1 处，并以 4 参探针行为作 oracle | default/--inject 均 rc=0 |

判决：返工范围内 finding 全修；无未修项。状态按派单保持 `待返工`。

#### 返工提交（architect，2026-10-20）

- **档位**：`待验收`（未 Accepted）⇒ 提交信息按派单给定；commit `9158f6c`（分支 `INFRA-095t-rework`）。
- **文件集（显式 staging 5 项）**：`components/musl/patches/src/thread/dadao/clone.s.patch`、`components/musl/changelog.md`、本册（`**状态**` + 返工记录）、`.tao/knowledge/issues.yaml`（`ISS-295` closed）、`.tao/knowledge/milestones.md`（T1 行/清单/§M9）⇒ 对账返工范围：**无漏提 / 多提 / 越界**；`.work/**` 为忽略区（日志/证据不入 git）。
- **architect 复跑**：`check-patch-tree` rc=0（5 组件 **183** patches）、`check-tasks`/`check-knowledge-refs`/`check-no-residue` rc=0、`tools/infra/check_issues.py` rc=0（57 open / 14 closed）、`make check`（L1）rc=0；日志 `.work/log/infra/INFRA-095t-arch-*.log`。
