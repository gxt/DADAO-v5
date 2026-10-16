# QEMU-062t: `qemu-user`（`linux-user`）的 DADAO 后端 = `P3`（**静态档 + 动态档都能跑起来**）

**模块**：qemu
**项目里程碑**：M8
**依赖**：`ADR-0025`（M8 范围，**`Accepted`**；本册 = `D2`（无内核 / 用户态可见语义）/ `D6`（路线第 3 步 = `linux-user`）/ `D7`（errno 与 oracle 口径）的执行落点）、**`SPEC-138t`（`P0` 契约，`已验证`）** = `.tao/contracts/contract-syscall.md`（`§1` 号表 = **`rd15`** + **沿用 RISC-V 编号** / `§1.3` `AUDIT_ARCH_DADAO` / `§2` 入口 / `§3` 传参与返回 `rd8` / `§4` `errno` = **`rd8` 负值** / `§5` oracle 禁止项 / `§6` **QEMU user-mode 角色与边界**）、**`SPEC-139t`（`P0` 契约，`已验证`）** = `.tao/contracts/contract-dynlink.md`（`§1.2` 角色分工〔「内核 / 加载器侧」= **QEMU user-mode**〕/ `§6.2`–`§6.6` auxv 注入 · `PT_INTERP` 装载 · guest-root 路径解析 · 入口栈向量 / `§8` oracle 禁止项）、**`INFRA-085t`（`P2`，`待开始`）** = **动态档的被测产物来源**（`libc.so` + `ld-musl-dadao.so.1` + 动态可执行）、`QEMU-061t`（`aip.si` 解码与语义，`已验证`；动态档 AOT 侧 GOT/PLT 取址链）、`QEMU-060t`（`dadao-m1` syscall 服务**已撤回** ⇒ **运行验证移交本册**）、`LLVM-095t`/`SPEC-145t`（`已验证`；`aip.si` / `PCREL_HI`·`PCREL_LO` / PLT 12 B）、`ADR-0003`（ELF machine / 端序；`.tao/contracts/contract-elf.md §1`）、`ADR-0018`（ABI 传参）；纪律 = `docs/Process-01`（组件补丁树，本册**必过** `check-patch-tree`）、`docs/Process-05`（L1/L2/L3）、`docs/Process-07`（门控分层）、`ISS-210`（改组件 ⇒ 安装根须同代）、`ISS-229`（重建 / 门控**串行**）
**状态**：待开始

> **编号（现场取号，2026-10-17）**：`.tao/tasks/qemu/` 现存最大 = `QEMU-061t`（`ls` 现场：`QEMU-060t-…md` / `QEMU-061t-…md`）⇒ 取 **`062`**；`QEMU-062` 经 `git log --all --name-only`（全历史）复核**从未被占用**（`lessons §3.21`「编号须全仓〔含历史〕唯一」）。

## 立项来源 / 路线位置

- **路线 = `ADR-0025 D6` 的第 3 步（`P3`）**：`P0 契约 → P1 musl 静态 → P2 动态链接 → **P3 qemu-linux-user** → P4 对照/回归`。`P0` = `SPEC-138t`/`SPEC-139t`（均**已验证**）、`P1` = `INFRA-082t`（**已验证**）、`P2` = `INFRA-085t`（**待开始**；生产者侧 `LLVM-094t`/`LLVM-095t` 已 **`已验证`**）⇒ **本册 = `P3` 的落点**。
- **用户裁定（原话逐字引录；渠道 = 经主会话问答）**：
  - **2026-10-17**：「**静态和动态都需要支持**」⇒ 本册验收**两档**（静态档 + 动态档），**逐字**落纸（见「验收标准」2 / 3）。
  - **2026-10-15**：「**不用改D6，就按原来的顺序进行，然后增加embench和两个新的test suite的测试；测试的时候区分静态链接和动态链接，先测静态链接，再测动态链接**」⇒ `P3` = `qemu-user`；两档**先静态、后动态**。
  - **2026-10-15**：「**1、删；2、P1/P2/P3/P4解释一下，我已经不记得了**」⇒ `dadao-m1` 上的 syscall 服务**已删**（`QEMU-060t`）⇒ **运行验证由本册承担**（`TESTCASES-045t` 的 `tools/testcases/run_suite.py` 在该路径上已硬失败）。
- **为何必须新做（非改造既有）**：现场 `qemu` 树**只有 system 模式**（`configs/targets/dadao-softmmu.mak`；`target/dadao/**`；产物 `qemu-system-dadao`）——**无** `linux-user/dadao/**`、**无** `configs/targets/dadao-linux-user.mak`（现场 `ls` 复核）⇒ 本册 = **新增** `linux-user` 目标（`contract-syscall.md §6` 原话：「`linux-user` 的 DADAO 目标是**新增工作**（非改造既有）」）。

## 执行环境
**执行环境**：本地

## 目标（交付物）

1. **新增 user-mode 目标**：`components/qemu/**` 增加 `linux-user` 面补丁（`patches/linux-user/**` + `patches/configs/targets/dadao-linux-user.mak` + `series` + `components/qemu/changelog.md`；`docs/Process-01` 树形补丁、一文件一补丁）⇒ `make build-qemu` 产出 user-mode 二进制（现场名以 `configure` 为准，下称 `qemu-dadao`），`make install-host` 安装进 `$(HOST_TOOLCHAIN_BIN)`。
2. **ELF 加载**：按 `.tao/contracts/contract-elf.md §1` 接受 `e_machine = EM_DADAO (0x0DA0)` / `EI_CLASS = ELFCLASS64` / `EI_DATA = ELFDATA2MSB` 的 guest ELF：**静态可执行**（无 `PT_INTERP`）与**动态可执行**（带 `PT_INTERP`）；`e_flags[7:0] = 1`。
3. **`cpu_loop`（guest 异常 / 退出路径）**：
   - syscall 号**从 `rd15` 读**（`contract-syscall.md §1.1`）且**沿用 RISC-V 编号**——号值真源 = `§1.2` 锁定快照（`qemu` 树内 `linux-user/riscv/syscall.tbl` + `linux-headers/asm-riscv/unistd.h` + `linux-headers/asm-generic/unistd.h` + 派生 `unistd_64.h`，四者 `sha256` 见该节），**不另设** arch-specific 私有号（`§1.3` 已裁定）。
   - **两层不互相覆盖**（`§1.1`/`§2`）：`immu18` = 硬件分发层（`umon` `cfx0` / `jmon` `cfx1`，**`immu18 = 0`** = `SBI_{U,J}MON_SYSCALL`）、`rd15` = Linux 号层；M8 主入口取 **`umon`（`cfx0`）**。
   - **宿主 syscall 转发**：guest 号 → 宿主号（宿主 = Linux x86-64）→ `do_syscall`；参数按 `§3` 取（数据 `rd16–`、地址 `rb16–`、浮点 `rf16–`，三 bank 各自独立、自 16 起；例 `read(fd, buf, count)` ⇒ `fd→rd16` / `buf→rb16` / `count→rd17`）。
   - **返回 = `rd8`**；**`errno` = `rd8` 负值（`-errno`）**（`§3`/`§4`；`rd1`/`rderrno` **不参与** syscall 错误路径；候选 B/C 不采用）。
   - **未实现号 ⇒ 显式 `-ENOSYS`**，**不得**静默成功；**停机协议不混用**（`exit`/`exit_group` 走 syscall；**不得**用 exit port / semihosting `SYS_EXIT`，`§6`）。
4. **端序**：guest = **大端**（`contract-elf.md §1`）、宿主 = 小端 ⇒ 全部 syscall 标量/结构体须按目标端序转换（qemu 惯例 `TARGET_WORDS_BIGENDIAN` + `tswap*` + 目标结构体 thunk）；**禁**把宿主结构体直接当 guest 结构体使用。
5. **`AUDIT_ARCH_DADAO`**：按 `contract-syscall.md §1.3`（用户 2026-10-14 裁定）= `EM_DADAO (0x0DA0) | AUDIT_ARCH_64BIT`、**不带** `AUDIT_ARCH_LE`（**BE、64 位**）；`AUDIT_ARCH_*` 属 audit 子系统标识、**与 `rd15` 号空间无关**。
6. **动态档装载（「内核 / 加载器侧」**全部**由本册承担，无内核）**：按 `.tao/contracts/contract-dynlink.md §1.2` 角色表 ⇒ auxv 注入 / `PT_INTERP` 解释器装载 / 加载偏置分配 / guest-root 路径解析**均归 QEMU user-mode**；须满足 `§6.2`–`§6.5`：注入 musl 消费的 `AT_*` 项且 **`AT_BASE` = 实际解释器装载基址**；`e_entry` 跳转对象 = **解释器入口**（被测程序入口由 `AT_ENTRY` 回指）；解释器 `open()` 走**宿主侧 guest-root 前缀**（`-L` / `QEMU_LD_PREFIX`）；入口栈向量（`argc`/`argv`/`envp`/auxv）SP **8 B 对齐**。
7. **门控与证据**：新增 `Makefile` 目标（分层按 `docs/Process-07`）+ `tools/qemu/**` 新增工具（**随产物保留**）+ `.work/evidence/QEMU-062t/**`（一键脚本 + 独立 oracle + 可达 FAIL）。

## 接口规范

- **输入**：
  - **静态档被测物** = `P1`（`INFRA-082t`）的 musl **静态**可执行（`make build-musl` 现状可编；`hello`/`exit` 等）。
  - **动态档被测物** = `P2`（`INFRA-085t`）的 `libc.so` + `ld-musl-dadao.so.1`（作为 `PT_INTERP` 解释器）+ 动态可执行；**`P2` 未 `已验证` 前动态档不得开工**（依赖单向 `P2 → P3`）。
  - **组件面** = `components/qemu/patches/**` + `components/qemu/series` + `components/qemu/changelog.md`（补丁树；`check-patch-tree` 断言）。
- **输出**：
  - **能构建**：`make build-qemu`（新增 target 首轮建议 `make build-qemu-reconfig`）rc=0 + `make install-host` rc=0；安装根二进制 mtime 晚于补丁 mtime、md5 与构建树产物相同（`ISS-210`）。
  - **能跑**：① **静态档** `qemu-dadao ./hello` ⇒ 正确 stdout + 退出码；② **动态档** `qemu-dadao -L <guest-root> ./dyn_hello` ⇒ 解释器装载（`AT_BASE ≠ 0` 且 = 实际基址）+ `ldso` 完成重定位 ⇒ 正确 stdout + 退出码。
  - **证据**：`.work/evidence/QEMU-062t/**`（`run.sh` 全绿 + `--inject` 可达 FAIL + `cp`/md5 还原纪律）、`.work/log/qemu/**`（复杂命令输出留存）。
- **约束**：
  - **期望值不得从本仓实现反推**（`contract-syscall §5` / `contract-dynlink §8` 禁止项）：syscall 语义期望值取自 `spec/` + RISC-V/musl **golden 对照**；号值取自 `§1.2` 锁定快照。**P3 实现（含 v5 的 `qemu`/`musl` 端口、本仓工具）不得充当期望值来源**。
  - **大端**为先验，不可商量；BE 敏感例 ≥1。
  - **`spec/` / `contracts/` / `.tao/contracts/**` 不在本册范围** ✗（如需改动 ⇒ 停下请示**用户授权**，`docs/Process-06`）。
  - 改 `components/**` ⇒ 必 `build-qemu`(+`install-host`)；且按 `ISS-229` **串行**、`JOBS=8`（**禁** `-j$(nproc)`）。
  - `Makefile` / `tests/vectors/**` 属**共享文件** ⇒ 同改者**一律串行**（`AGENTS.md`）。

## 验收标准

1. **构建**：`make build-qemu` rc=0（产物含 user-mode 目标）+ `make install-host` rc=0；`check-patch-tree` rc=0（patches 计数现场派生）；安装根新鲜度与 md5 对账 ✓（`ISS-210`）。
2. **静态档（用户 2026-10-17 原话「静态和动态都需要支持」= 第 1 档）**：`qemu-dadao` 跑 `P1` 的 musl **静态**可执行 ⇒ stdout/退出码与**独立 oracle** 一致（≥1 例**大端敏感**断言）。
3. **动态档（同句 = 第 2 档）**：`qemu-dadao` 跑 `P2` 的**动态**可执行 ⇒ ① `PT_INTERP` 解释器被装载（`AT_BASE` ≠ 0 且 = 实际装载基址）；② `ldso` 完成重定位（`RELATIVE`/`JUMP_SLOT`/`ABS48` 逐条按 `contract-dynlink §4.3`）；③ stdout/退出码与 oracle 一致。
4. **syscall 契约逐条**：`rd15` 读号 ✓ + 沿用 RISC-V 编号（抽样对照 `§1.2` 快照）✓ + 参数/返回（`§3`）✓ + **`errno` = `rd8` 负值**（≥1 例真错误路径，如 `openat` 不存在路径 ⇒ `rd8 = -ENOENT`）✓ + **未实现号 ⇒ 显式 `-ENOSYS`**（不得静默成功）✓。
5. **大端**：BE 敏感例 ≥1（`write` 字面量 / `stat` 结构体字段等）且该断言**可达 FAIL**（注入 → FAIL → `cp` 还原 + md5 对账 → 回绿）。
6. **`AUDIT_ARCH_DADAO`**：机读断言现场取值 = `0x0DA0 | AUDIT_ARCH_64BIT`（**不带** `LE`）、与 `§1.3` 逐字一致（**非目测**）。
7. **门控**：新增目标 rc=0；`make check`(L1) rc=0；L2/L3 串行（`ISS-229`）且**载体清单 + 用例计数现场派生并打印**（防 `ISS-235`「载体 ≠ 全量」/ `ISS-236`「默认档日志不可自证」同类）。
8. **证据**：`.work/evidence/QEMU-062t/**` 一键脚本全绿 + `--inject` 反例**可达 FAIL** + 还原纪律（`cp` + md5 对账；**禁** `git checkout`/`restore`/`stash`）。
9. **不混停机协议**：`exit`/`exit_group` 走 syscall；现场核**未**使用 exit port / semihosting `SYS_EXIT`（`§6`）。

## 前置申报（长任务 / 构建成本；执行前必读）

- 本册改 `components/qemu/**` ⇒ 必跑 `make build-qemu`（**新增 target 首轮建议 `build-qemu-reconfig`**）+ `make install-host`。
- **参照实测**：`QEMU-061t` 现场 `install-host` = `start=2026-10-16 18:37:06` → `end=18:43:18`（**≈6 min**；日志 `.work/log/llvm/QEMU-061t-install.log`）。新增 `linux-user` 目标会引起一次 **re-configure + 较大增量编译** ⇒ **申报预计 ≥30 min**（首轮可能 1–2 h，视 `linux-user` 面改动规模）。
- **纪律**：`ISS-229` ⇒ 与其它 `install-host` / `build-*` / L2 / L3 **串行**；`JOBS=8`（**禁** `-j$(nproc)`）；长构建由**主会话** `setsid nohup` **脱离会话** + 落 `*.EXIT`；**子代理不得在会话内等待长任务**。

## 不做（边界）

- **三套大型测试的「跑」**（`embench-iot` / `libc-test` / `llvm-test-suite`，各分静态档/动态档两轮）⇒ **另立任务**，且**在本册跑通之后**（用户 2026-10-15 原话见「立项来源」；`milestones.md`「测试面 = 三套 × 两档」）。本册**只交付「能跑起来」**（两档各 ≥1 例 E2E + 独立 oracle + 门控）。
- **`dadao-m1`（system 模式）的 syscall 服务** ✗（用户 2026-10-15 裁定「**1、删**」；`QEMU-060t` 已撤回 ⇒ **不重引入**，`helper.c.patch` 保持 `761dfa3` 基线）。
- `spec/` / `contracts/` / `.tao/contracts/**` ✗（如需改 ⇒ 停下请示授权）。
- **内核**（VFS / MM / 调度 / 信号）✗（`ADR-0025 D2`：M8 无内核）；`P4`（golden 对照 harness / 回归）✗。
- **musl 侧** ✗（归 `infra` / `P2`）；跨模块影响须按 `AGENTS.md`「模块里程碑与跨模块交互」处置（存在未处置跨模块影响时**不得**置模块里程碑）。

## 完成区
**测试结果**：（待填写）
**修改文件**：（待填写）
**验收结果**：（待填写）
**新发现/坑**：（待填写）
**遗留问题**：（待填写）

## 审阅记录

按轮次追加，每次返工新增一轮，避免多轮记录混杂。

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
