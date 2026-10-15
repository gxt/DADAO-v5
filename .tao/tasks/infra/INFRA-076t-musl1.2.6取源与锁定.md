# INFRA-076t: musl 1.2.6 取源与锁定

**模块**：infra
**项目里程碑**：M8
**依赖**：`ADR-0025`（M8 范围与 Linux 兼容路线，`Accepted`；`D3` = 用 musl 自带 ldso、`D4` = musl 与 picolibc 并存）；消费方 `SPEC-139t`（动态链接 ABI 契约，musl `ldso` 路径）
**状态**：待验收

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

**测试结果**：`.work/evidence/<任务ID>/run.sh` **rc=0**（现场统计 **checks=108 / failed=0**）：A 落盘 18 项、B tag 形态 8 项、C 锁条目 20 项、D 取源幂等 11 项、E `git diff` 可用性 11 项、F 门控 35 项、G 台账复核 5 项。**反例闭环**：C 段 2 个 patchless 反例（**临时树副本**注入：去 `patchless` ⇒ `manifest-check`「component musl: missing patch series」rc=1；`commit` 截短 ⇒「enabled components require a full commit」rc=1；未注入副本回绿 rc=0）；E 段注入探针 ⇒ `status` 报 ` M`、`git diff` 10 行、**「工作树干净」断言可达 FAIL** ⇒ `cp`+md5 还原 ⇒ `status` 回空、sha256 回 `git blob` 值；`run.sh --inject 1`（真锁册注入 → 预期 FAIL → `cp`+md5 还原 → 预期回绿）**闭环 PASS**。
**修改文件**：`manifests/components.lock.toml`（**+33 行 / -0 行**，仅追加 `musl` 条目，其余 8 组件逐行未动）；本任务书（状态 + 完成区 + 自审）；`.work/evidence/<任务ID>/{run.sh,lockedit.py}`；`.work/log/<模块>/INFRA-076t-*.log`。**未提交**（提交权归 architect）；**未越界**（未动 `spec/`/`contracts/`/组件补丁/`tools/`）。
**验收结果**：以下均为现场真实输出/退出码、逐条对齐 ——
- **落盘**：`.cache/<musl>.git` `is-bare=true`、`is-shallow=true`、`origin=git.musl-libc.org/git/musl`、`HEAD=9fa28ece…`、`du -sh`=**1.5M**；`.work/source/<musl>` `--show-toplevel`=该目录、`HEAD=9fa28ece…`、`status --porcelain`=**0 行**、`is-shallow=true`、`origin`=本地 mirror、`du -sh`=**15M**、`VERSION`=**1.2.6**（文件 + `HEAD:VERSION` blob 双证）。
- **tag 形态**：`cat-file -t refs/tags/v1.2.6`=**commit**、`rev-parse`=`…9fa28ece…`、`rev-parse '…^{}'`=**同值** ⇒ **lightweight**；远端 `ls-remote`（**直连** git.musl-libc.org **rc=0**）**仅 1 行 / 无 `^{}` peel 行 / sha 同** ⇒ 锁 `commit` 无需 peel、`--depth 1 --branch v1.2.6` 形态成立（**与内核 `v7.2.10`、test-suite `llvmorg-23.1.3` 的 annotated 相反**）。
- **取源幂等**：`make fetch` **两次 rc=0**，均打印 `fetch: mirror musl.git already has 9fa28ece75d8; skipping fetch` + `fetch: musl already at 9fa28ece…`；mirror `objects` 文件数 **3→3**、字节 **1457303→1457303**（**未重下**、无网络）；`tools/infra/status.py` **rc=0** 列出 `musl enabled 9fa28ece…`。
- **移植面（现场 `find`）**：`src/*/riscv64/*.s|.S`=**12**、`arch/riscv64/`=**13**（顶层 6 + `bits/` 7）⇒ 与「实测移植面」节一致。
- **门控**：L1 的 **27 个非 `check-patch-tree` 目标逐个 rc=0**（`check-knowledge-refs` / `check-no-residue` / `check-components` 均在其中）；`check_issues.py` **rc=0**（28 open / 4 closed）；`make check-tasks` **rc=0**；`compileall` **rc=0**。
- **L1 聚合 `make check` rc=2**（唯一失败 = `check-patch-tree`）——**与本次改动无关，双重证据**：① 该门控输出**不含 `musl`**，且在「**master 锁册（无 musl 条目）**」临时树上**输出逐字节一致 / rc 相同** ⇒ musl 条目零影响；② 归属 = 换分支后仓库侧补丁表回退 master 版（blob `78648ec`）而共享 `.work/source/<llvm-project>` 工作树仍停在 `SPEC-142t-B` 的 base+1 提交（`24881a6b5`，07:46），同一临时树**仅**把该补丁换成 `SPEC-142t-B` 版（blob `010a9b6`）即 `check-patch-tree: 4 component(s), 127 patches OK` **rc=0**（A/B 落 `.work/log/<模块>/INFRA-076t-cpt-branch-ab.log`）。
**新发现/坑**：① musl `v1.2.6` = **lightweight tag**（tag sha = commit sha、`ls-remote` 无 `^{}` 行）⇒ 锁 `commit` 无需 peel，与 annotated tag 相反 ⇒ **每条目的 tag 形态须现场判、两种都合法**。② `patchless` 是「无补丁集」组件的**唯一放行开关**，与 `patch_dir`/`patch_series` **互斥**（`manifest_check` 双向拒）⇒ 落第一份 `arch/dadao` 补丁时须**同一提交内**去 `patchless` 并补两字段。③ `check-patch-tree` 同时读「仓库侧补丁表」与「**共享** `.work/source/<name>` 工作树」，工作树**不随分支切换重建** ⇒ 换分支即可能变红；**判定法 = 同门控跑「master 锁册临时树」差分对照**（勿用 `git checkout`/`stash` 复位）。④ `make fetch` 对已存在工作树先 `git fetch --no-tags origin <sha>`（origin = **本地 mirror** ⇒ 离线秒级）再按「HEAD==commit / commit 是 HEAD 祖先」决定 leave alone ⇒ 幂等、对 `patchless` 组件无副作用。（建议沉淀 `.tao/knowledge/lessons.md`）
**遗留问题**：① 【**非本任务，未处置**】L1 非全绿：唯一失败 `check-patch-tree` = `SPEC-142t-B` 分支态 × 共享 llvm 工作树错配（`components/llvm-project/patches/**` 属他模块，本任务**不得**改）⇒ 待该分支收尾/合并后自然回绿；本次已用 A/B 证明**与 musl 条目零关联**。② `milestones.md` 流水行仍写 `待开始`（状态机由主会话 `/complete` 收尾改写）；本轮只**复核**其内容与锁 `commit` 一致（G1–G3 PASS），未改动。③ 任务书「参考对照（`DADAO-0628`）」教训清单与「实测移植面」原文经现场复核（12/13）**无订正**。

## 审阅记录

#### 第 1 轮 engineer 自审（2026-10-15，分支 `INFRA-076t`；自主逐行审查）

- **范围**：`manifests/components.lock.toml` 的 `musl` 条目、 `.work/evidence/<任务ID>/{run.sh,lockedit.py}`、本任务书。
- **逐行审查**：lock 仅追加 **+33/-0** 行（`git diff --numstat master` 现场值），其余 8 组件段与注释**逐行未动**；新条目字段与 `qemu`/`linux`/`llvm-test-suite` 体例一致（`enabled` / `repository` / 40-hex `commit` / `shallow` / `shallow_ref` / `patchless` / `role`），**未**声明 `patch_dir`/`patch_series`（`patchless` 不变量）、**未**加 `source[]`（直连可用，同 `picolibc`/`embench-iot` 形态，注释已写明理由）。`run.sh`：无 `set -e`（失败继续、末尾统一判定）、无 `tee`、计数现场统计、还原一律 `cp`+md5（**无** `git checkout/restore/stash`）、注入用**临时树副本**（C 段）/真锁册 + `trap` 还原（`--inject`）；`lockedit.py` 对「未命中目标行」显式非零退出（防**空注入假绿**）。时序审查：D/E/F 段均在锁条目落盘后执行，`make fetch` 只写 `.work/source/**/.git` 与 `.cache/**`，**未触** `.work/build/**` 与安装/产物根（并发重建约束满足）；`make -n check` 31 条命令**无** `cmake/ninja/build-*` ⇒ L1 取证不触发构建。
- **防造假**：E 段用 **`git blob` sha256 作独立 oracle**（非自证），并含「注入态下工作树干净断言**必判 FAIL**」的可达 FAIL 路径；C 段两个反例均在临时树注入并在**未注入副本**上验证回绿；B 段 tag 形态用**远端 `ls-remote`** 独立佐证；D 段用 mirror 对象数/字节数**双不变**证「未重下」。
- **finding 处置**：

  | finding | 处置 | 改了什么 | 复验证据 |
  |---------|------|---------|---------|
  | A6 断言误写：`--show-toplevel` 期望写成了仓库根 | ✅已修 | 期望改为 `$ROOT/$WT`（工作树自身 toplevel） | `--sections AB` 首跑 FAIL ⇒ 修后 `ABE` 37/37 PASS |
  | A13/A14 期望值误用 tag 名（`v1.2.6`），而 `VERSION` 内容是 `1.2.6` | ✅已修 | 期望改 `1.2.6`；标签名只用于 ref 断言 | 同上（FAIL→PASS 现场） |
  | G5/INJ2 断言写法错（`grep -c … >/dev/null`、`grep -qc`） | ✅已修 | 改五字段循环 + `grep -q` | `--sections C` 20/20、`--inject 1` 闭环 PASS |
  | F1/F2 原断言「聚合日志恰好 1 条 Error 且是 check-patch-tree」= **依赖并发/分支态的易碎断言**（若他方修好即误红） | ✅已修 | 改为**状态无关**断言「聚合日志中 musl 相关错误行=0」；红归属改由 **A/B 差分**（info + 落盘日志）证明 | `--sections DF` 47/47 PASS；A/B 日志 `…cpt-branch-ab.log` |
  | `make check`(L1) 当前非全绿（`check-patch-tree`） | ⏸延后（**非本任务**：属 `components/llvm-project/patches/**` 他模块 + `SPEC-142t-B` 分支态；本任务文件集不含） | 未改 | 双重无关联证据见完成区「验收结果」；A/B：`A_RC=1` / `B_RC=0`（`4 component(s), 127 patches OK`） |
  | `milestones.md` 流水行仍是 `待开始` | ⏸延后（状态机归主会话 `/complete`） | 未改 | G1–G3 PASS（行内容 + 锁 `commit` 一致） |

- **判决**：**无本任务范围内未修 finding**（表中 ⏸ 两项均为「超文件集 / 归主会话」的登记项，已入「遗留问题」）⇒ 状态置 **`待验收`**。


#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）

#### architect 提交（挂起：WIP）+ 文件集审核（2026-10-15，分支 `INFRA-076t`）

- **档位**：**`WIP:`**（reviewer 未验收；L1 聚合 `check-patch-tree` 红 = **他分支 `SPEC-142t-B` × 共享 `.work/source/<llvm-project>` 错配**，非本任务问题）⇒ **挂起**：先提交、待其合并后回绿再验收；**未 merge、未 push**。
- **提交 1（`04891a0`）**：`WIP: INFRA-076t: musl 1.2.6 入锁（commit 9fa28ece…, shallow_ref=v1.2.6, patchless）——L1 check-patch-tree 红属 SPEC-142t-B 分支错配（双重证据与 musl 无关），待其合并后回绿再收尾`。显式 staging = `manifests/components.lock.toml` + 本任务书（`2 files changed, 64 insertions(+), 8 deletions(-)`）。
- **提交 2（`60817c9`）**：「登记 issue：分支×共享源树 patch-tree 错配（INFRA-076t 现场）」——**单独一笔**，仅 `M .tao/knowledge/issues.yaml`（+8 行，`ISS-212`）。
- **文件集对账**（`git diff --cached --name-status` vs 完成区「修改文件」）：提交 1 = **逐条对齐**（完成区声明 lock + 本任务书；`.work/evidence/**`、`.work/log/**` 为 gitignored、不入库，符合声明）；**多提 = 1 项**（提交 2 的 `.tao/knowledge/issues.yaml`，**architect 登记职责**、非 engineer 交付物，已在 `ISS-212` 留证）；**无漏提、无越界**。开工前 `status --porcelain -uall` = 恰 **2 项**（lock + 任务书），与他方分支 `SPEC-142t-B`（`fd885eb`）**未被触碰**。
- **只 `commit`、未 `push`**；提交落在本任务分支 `INFRA-076t` 内。

#### architect rebase 留痕（2026-10-15，`INFRA-076t` rebase 到 `bab267e`）

- **背景**：本任务挂起时 L1 红（`check-patch-tree`）= 他分支 `SPEC-142t-B` × 共享源树错配；`SPEC-142t-B` 已并入 `master`（`bab267e`）⇒ 本分支 rebase 到 `master` 使门控回绿（**未 merge、未 push**）。
- **rebase 后提交链**（old → new，逐笔等价、内容不变）：`04891a0` → **`9f405ce`**（`WIP:` musl 1.2.6 入锁）；`60817c9` → **`1a9a6af`**（登记 `ISS-212`）；`98c0c24` → **`c50683c`**（提交留痕）；`c83a3f3` → **`1f0389f`**（撞号修复 + lessons §3.21）。
- **冲突与解决**（**仅** `.tao/knowledge/issues.yaml`，手工解、未用 `checkout --ours/--theirs`）：① 两侧新增 issue **撞号** ⇒ **保留 `master` 的 `ISS-210`（install-host 假绿）/ `ISS-211`（MC 口径）**，本分支「分支×共享源树错配」条目**改号 `ISS-212`**（内容原样保留）；② `c83a3f3` 的「`ISS-210`→`ISS-212`」改名 hunk 在①处**已等价应用** ⇒ 取 ours、丢弃该**已成空**的 theirs 侧（`lessons.md` / 本任务书改动照常应用）；`manifests/` 无冲突。
- **门控复核（现场 rc）**：`make check-patch-tree` **rc=0**（`4 component(s), 127 patches OK`，原红消失）；L1 `make check` **rc=0**（`repository checks (L1): PASS`）；`tools/infra/check_issues.py` **rc=0**（31 open / 4 closed）且 `ISS-200`–`ISS-212` **全仓无重复**、YAML 可解析；`git merge-base --is-ancestor master HEAD` = **rc=0**。
- **文件集对账**（`git diff --name-only master..HEAD` = **4 项**）：`manifests/components.lock.toml` + 本任务书 = 完成区「修改文件」声明**逐条对齐**；**多提 2 项** = `.tao/knowledge/issues.yaml` + `.tao/knowledge/lessons.md`（**architect 登记/沉淀职责**，非 engineer 交付物，已在 `ISS-212` 留证）；**无漏提、无越界**（未动 `spec/` / `contracts/` / 组件补丁 / `tools/`）。
- **遗留问题① 状态更新**：rebase 后 L1 **已全绿** ⇒ 该遗留**已解除**（原文保留、不改写）；②（`milestones.md` 流水行 / 状态机）仍归主会话 `/complete`。
- **只 `commit`、未 merge、未 push**；未触碰其它分支。
