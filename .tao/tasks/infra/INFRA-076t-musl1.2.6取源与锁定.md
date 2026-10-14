# INFRA-076t: musl 1.2.6 取源与锁定

**模块**：infra
**项目里程碑**：M8
**依赖**：`ADR-0025`（M8 范围与 Linux 兼容路线，`Accepted`；`D3` = 用 musl 自带 ldso、`D4` = musl 与 picolibc 并存）；消费方 `SPEC-139t`（动态链接 ABI 契约，musl `ldso` 路径）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 问题根源 / 立项来源

- **用户裁定（2026-10-14，原话 / 选项标签）**：
  - 「**用最新 1.2.6**」——musl 版本 = **`1.2.6`**（tag `v1.2.6`）；
  - 源 = `https://git.musl-libc.org/git/musl`（**实测可直连**）。
- **用户裁定·放行入锁（2026-10-14，原话；渠道 = 经主会话问答）**：
  - 「**三个新组件，我记得都已经定好了的，可以入锁，libc-test取最新版本即可**」
  - ⇒ musl **放行入锁**（`manifests/components.lock.toml` 新增 `musl` 条目**已获授权**，见「输出 3」）；**本任务前置已满足 ⇒ 可开工**（**不放宽**既有验收标准与门控）。
  - 同一裁定的另两句落点：`llvm-test-suite` 放行 = `LLVM-093t`；`libc-test`「取最新版本」= **`TESTCASES-044t`**（本任务§libc-test 定源的旧快照**作废**）。
- **动机**：M8 主线 = **无内核的 Linux 用户态栈**（`ADR-0025 D2`）；`P1 musl 静态`（`ADR-0025 D6`）与 `P2 动态链接`（`D3` = musl 自带 ldso）**均以 musl 源码为唯一底座** ⇒ 须先在 v5 内把 musl **取源 + 锁定**，使其**可 `git diff`**（组件源一律 git 基线，见 `AGENTS.md`「工作区落点」/`lessons §3.19`）。
- **已顺手落盘（主会话代行）**：`.cache/<name>.git`（**bare**，**1.5 MB**）+ `.work/source/<name>/`（**15 MB**，HEAD = `9fa28ece75d8a2191de7c5bb53bed224c5947417`）。**本任务须先核验其真实性**（见「验收标准 1」）。
- **`libc-test` 定源 = 已定**（用户 2026-10-14 原话，见「§libc-test 定源」）：**只登记、不下载**；**锁定移交 `TESTCASES-044t`**（取**最新 commit**；旧登记的 2022-03 快照 `b7ec4679…` **已作废** ✗）。

## 接口规范

- **输入**：musl 源 URL（`https://git.musl-libc.org/git/musl`，实测可直连）、`ADR-0025`（`D3`/`D4`）、用户裁定（版本 1.2.6）。
- **输出**：
  1. `.cache/<name>.git`（**bare 裸仓库**，浅克隆）**确认/补齐**，供离线重建工作树；
  2. `.work/source/<name>/`（**git 检出**，detached at 锁 `commit`，**可 `git diff`**；**不入 git** —— `.work/` 已 gitignore）；
  3. `manifests/components.lock.toml` 新增 **`musl`** 条目（**体例对齐 `qemu`**：`repository` + 40-hex `commit` + `shallow = true` + `shallow_ref = "v1.2.6"` + `patchless = true`〔**尚无** v5 的 `arch/dadao` 补丁〕+ `role`）；
  4. 本任务书「实测记录」+「参考对照（DADAO-0628 教训）」。
- **约束**：**不**改组件补丁 / `spec/` / `contracts/`；**不**写契约正文；sha / 体积 / 耗时 / tag 形态**现场取证**；正文引用 `.work/**` 一律用 `<>` 占位。

## 验收标准

1. **落盘核验（先做）**：`.cache/<name>.git` 为 **bare**（`git rev-parse --is-bare-repository` = `true`）+ `.work/source/<name>/` 为 **git 检出**，`rev-parse HEAD` = 锁 `commit`、`status --porcelain` 空、`rev-parse --is-shallow-repository` 现场记录；体积 `du -sh` 现场值与「1.5 MB / 15 MB」核对。
2. **`git diff` 可用性证明**：向工作树任一源文件注入探针行 ⇒ `git -C <wt> status --porcelain` 报 ` M`、`git diff` **非空**；还原用 `cp` 备份回写 + **md5 逐位对账**（**禁** `git checkout`/`restore`/`stash`）⇒ `status` 回空、文件 sha256 回记录值（注入态下「工作树干净」断言须**可达 FAIL**）。
3. **tag 形态核**（参照 `INFRA-075t` 的 `tag≠commit` 经验）：`git cat-file -t refs/tags/v1.2.6` + `git rev-parse refs/tags/v1.2.6` + `rev-parse 'refs/tags/v1.2.6^{}'`——**现场判** lightweight tag（tag sha = commit sha）还是 annotated tag（须 peel）；据此定锁 `commit` 记 **peel 后 commit**（**对齐 `qemu` 体例**），并**记录是否需改 `--depth` / `shallow_ref` 形态**（现场结论）。
4. `manifests/components.lock.toml` 新增 **`musl`** 条目（字段见上「输出 3」，**体例对齐 `qemu`**）；`make check`(L1) **rc=0**。
5. **参考对照落纸**：`DADAO-0628` 用 **1.2.5**（commit `0784374d…`）+ 其 **12 个 `arch/dadao` 补丁**的**教训清单**（**只借教训、不复制实现**；见「§参考对照」）；并记录**实测移植面**（riscv64 = **12 个 `.s`/`.S`** + `arch/riscv64/*`）。
6. **libc-test 定源**（**只登记、不下载**）：源 / 取源通道 / 锁 `commit` / 快照日期 / 体积 / 构成写入本任务书（见「§libc-test 定源」）；**旧快照已作废、锁定移交 `TESTCASES-044t`**（本任务**不下载** `libc-test`）。
7. 门控：`make check`(L1) / `check-modules`(L2) / `check-no-residue` / `check-knowledge-refs` / `check_issues.py` 各 **rc=0**。
8. `milestones.md`：`INFRA-076t` 流水行 + M8 规划区登记（**已由 architect 预置**，本任务复核）。

## 参考对照（`DADAO-0628`；**只读、只借教训、不复制实现**）

> 来源：`.cache/refs/DADAO-0628/`（只读参考树；`内容溯源，非执行必需`）。

- **版本差异**：参考仓用 **musl 1.2.5**（tag `v1.2.5`，commit `0784374d561435f7c787a555aeab8ede699ed298`）；**我们 = 1.2.6**（更新）。
- **参考仓补丁规模**：`components/musl/patches/` 共 **15** 个补丁，其中 **12** 个涉及 `arch/dadao`（另 3 个 = `mallocng` 入口抽取 / `divsc3` 单精度复数除法 / `__fixsfti`·`__udivti3`·`__int128` 算术库）。**教训清单（借判断，不搬实现）**：
  1. **`arch/dadao` 编译期骨架（`syscall_arch.h`/`reloc.h`/`bits/*.h`/`kstat.h`）本身不足以产出可链接 libc**——须续接 crt / pthread / atomic 接线（参考仓 `recon` 记「arch 移植 ~15–20 文件」）。
  2. **`reloc.h` 的 `CRTJMP` 需专修**（参考仓补丁 0002 = subagent review finding）。
  3. **`pthread_arch.h` + `get_tp.s` + `__set_thread_area` 是硬依赖**（TLS/线程；对应 `ADR-0025 D5`「先查证再定」）。
  4. **`crt_arch.h` + `arch.mak` override `__libc_start_main`** 须一并处理。
  5. **调用约定**：参考仓为 **RB 寄存器组指针**专修（补丁 0006）。
  6. **`O0` 变通**：曾为 `mmap`/`mallocng` 编译降级 `O0`（0007），后又**撤销 `O0` 变通 + `optnone`**（0009）——**提示**：降级是临时手段、非终态。
  7. **软浮点垫片**：为 `vfprintf` 补 **IEEE-754 binary64 soft-float shim**（0010/0012，家族符号）+ **单精度软浮点家族**（0013）。
  8. **`crt_arch` 的 `AT_PAGESZ` auxv 立即数溢出**需修（0011）。
  9. **`__int128` 算术库 / `divsc3`**（0014/0015）亦在上游 libc 侧补。
  - **`recon` 判断（借）**：「musl 现在上是早的——syscall 面不够（malloc 要 `mmap`、`__init_libc` 要 TLS/线程指针）+ arch 移植大」⇒ 与 `ADR-0025 D6`「契约→musl→动态→linux-user」顺序一致。

## 实测移植面（riscv64 底座，musl 1.2.6；现场 `find`）

- **`.s`/`.S` = 12 个**（`src/{fenv,ldso,process,setjmp,signal,thread}/riscv64/*`）：
  `fenv/riscv64/fenv.S`、`ldso/riscv64/dlsym.s`、`ldso/riscv64/tlsdesc.s`、`process/riscv64/vfork.s`、`setjmp/riscv64/longjmp.S`、`setjmp/riscv64/setjmp.S`、`signal/riscv64/restore.s`、`signal/riscv64/sigsetjmp.s`、`thread/riscv64/__set_thread_area.s`、`thread/riscv64/__unmapself.s`、`thread/riscv64/clone.s`、`thread/riscv64/syscall_cp.s`。
- **`arch/riscv64/` = 13 文件**（顶层 **6**：`atomic_arch.h`/`crt_arch.h`/`kstat.h`/`pthread_arch.h`/`reloc.h`/`syscall_arch.h`；`bits/` **7**：`alltypes.h.in`/`fenv.h`/`float.h`/`setjmp.h`/`signal.h`/`syscall.h.in`/`user.h`）——即题述「12 + 7（`bits/`）」口径的事实来源。
- **用途**：DADAO 的移植面**预计与 riscv64 同形**（`arch/dadao/` + `src/*/dadao/`），故上表 = **后续 `arch/dadao` 骨架任务的清单真源**（本任务只测量、不移植）。

## libc-test 定源（**只登记，不下载**；**2026-10-14 收窄**）

> **用户裁定（2026-10-14，原话）**：「**libc-test: https://github.com/kraj/libc-test**」
> **用户裁定（2026-10-14，原话；经主会话问答）**：「**…libc-test取最新版本即可**」⇒ 由 `TESTCASES-044t` **取最新 commit 并锁死**；下表「锁」列的旧快照**作废** ✗。

| 项 | 值 |
|---|---|
| 源 | `github.com/kraj/libc-test`（用户指定） |
| 取源通道 | `ghfast.top` 代理主 / 直连备（本任务登记时的探测口径；**实际通道以 `TESTCASES-044t` 现场实测为准**） |
| 锁 | ~~`commit b7ec467969a53756258778fa7d9b045f912d1c93`~~ ⇒ **已作废** ✗（2022-03 快照，**非最新**）；**改由 `TESTCASES-044t` 取最新 commit** |
| 快照日期 | **2022-03-19**（最后推送；**快照性质、非最新** ⇒ 已作废 ✗） |
| 体积 | ≈**2.3 MB**（2341 KB，GitHub API 实测） |
| 顶层构成 | `Makefile` / `config.mak.def` / `src/{api,common,functional,math,musl,regression}` / `README` / `AUTHORS` / `COPYRIGHT` |

⇒ **本任务只登记、不下载**；取源与锁定执行 = **`TESTCASES-044t`**（`.tao/tasks/testcases/TESTCASES-044t-libc-test取源与锁定.md`）。

## 硬约束

1. 临时目录 `/tmp/opencode/INFRA-076t/`；命令一律在 workdir（= 仓库根）内、**相对路径**；**禁**出界 `cd`；禁仓库内临时文件。
2. **不**用 `git add -A`/`.`；**禁** `git checkout`/`restore`/`stash` 还原（一律 `cp` + md5）。
3. 文本**不写** `.work/<具体路径>` 字面（用 `<>` 占位）。
4. **只动**：`.cache/<name>.git`（确认/补齐）、`.work/source/<name>/**`、`.work/log/<模块>/`、`manifests/components.lock.toml`、本任务书、`.tao/knowledge/milestones.md`（若需订正）。**不下载 `libc-test`**。
5. 完成区与真实输出逐条对齐；**禁** `cmd | tail` 接进 `&&`。
6. 大文件（裸仓库 / 工作树）**不得**入 git（`.cache/`、`.work/` gitignored）。
7. **不提交**（提交权归 architect）；取得用户裁定须把**原话**写入本任务书。

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
（审查者独立验证的重跑记录、约束核验、判决）
