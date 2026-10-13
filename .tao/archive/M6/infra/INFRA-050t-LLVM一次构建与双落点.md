# INFRA-050t: LLVM 一次构建与双落点

**模块**：infra
**项目里程碑**：M6
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `Makefile`（现 `build-mc`/`install-host` 等目标；构建变量与 install 布局以**实测**为准）。
  - `.tao/adr/adr-0016-dadao-install-layout.md`（install 落点 `D1–D11`；安装根 `.dadao/`）。
  - `manifests/components.lock.toml`（`llvm-project` 精确 commit，`ADR-0006`）。
  - `spec/Process-01-组件补丁组织与构建编排.md`（构建编排约束）。
- **输出**：
  1. `Makefile`：一次构建 `LLVM_TARGETS_TO_BUILD="DADAO;X86"`，产出 **`clang`/`llc`/`ld.lld`/`lli`**（`lli` 为 host 工具，走 X86 back-end）；**一次构建、双落点**：
     - 交叉工具链 → `.dadao/cross-toolchain/bin/`（`clang`/`llc`/`ld.lld`；
     - host `lli` → `.dadao/host-tools/bin/`（可作为**可选**落点；若采纳须在完成区给实测路径）。
  2. `install-dirs`/install 规则同步（`ADR-0016` 布局）。
- **约束**：
  - **一次构建**（不重复全量 configure/build）；`JOBS` 受限（默认 8），**禁** `-j$(nproc)`。
  - **不改组件补丁语义**（本任务只编排构建/落点，不动 `components/llvm-project/patches/**` 的指令/编码内容）。
  - 交叉工具链与 host 工具**同源同 commit**（`manifests/components.lock.toml`）。
  - `DADAO;X86` 双 target 是「`lli` 值级 oracle」（`TESTCASES-038t`）的前置。

## 硬约束

- **临时目录** `/tmp/opencode/INFRA-050t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**（涉 `components/**` 者）：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/INFRA-050t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **重建成本申报**：本任务即一次构建立项，开工前写明「构建 LLVM（`DADAO;X86`），预计 N 分钟」；**一次构建、勿零散重跑**。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/infra/INFRA-050t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **一次构建产出四工具**：构建目标 EXIT=0；`clang`/`llc`/`ld.lld`/`lli` **均存在且可执行**（给 `ls -l` 与逐工具 `--version`/`-help` 的真实输出）。
2. **双落点**：`.dadao/cross-toolchain/bin/{clang,llc,ld.lld}` 存在；host `lli` 落点（`.dadao/host-tools/bin/lli` 或实测等价）存在（给实测路径 + `ls -l`）。
3. **同源**：四工具来自同一 commit（对照 `manifests/components.lock.toml`；给证据）。
4. **不回归**：`make check` EXIT=0；`make check-patch-tree` EXIT=0。
5. **一键证据脚本**：`.work/evidence/INFRA-050t/run.sh` 逐项通过、`RUN_EXIT=0`；**含注入自检**（如把落点变量指向旧路径/移除某工具 ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出与退出码。
6. **无残留**：`git status --porcelain -uall` 仅本任务应有改动（`Makefile`/install 规则 + 本任务书）；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：`make build-mc` EXIT=0（stamp 命中 → `ninja: no work to do`）；`make build-lld` EXIT=0（`[1/1] Linking CXX executable bin/lld`）；`make install-host` EXIT=0；`make check` EXIT=0（lit 62/62，repo checks PASS）；`make check-patch-tree` EXIT=0（92 patches OK）；证据脚本 `RUN_EXIT=0`（含注入自检 FAIL→还原→回绿）。

**修改文件**：`Makefile`（本任务未提交改动：install 循环 `cp -a`→`cp -aL --remove-destination` 修复断链 + 注释）；任务书本身。已提交半成品 `baf4a43`（`manifests/install-dirs.lock.toml`+`tools/infra/paths.py`+`tools/infra/check_dirs.py`）本次未再改。证据脚本 `.work/evidence/INFRA-050t/run.sh`；日志 `.work/log/infra/INFRA-050t-*.log`。

**验收结果**（逐条真实输出）：
1. 一次构建：`make build-mc`/`build-lld` EXIT=0；`.work/build/llvm/bin/{clang,llc,lld,lli}` 均 `-x`；`--version` 见 `.work/log/infra/INFRA-050t-tools.log`。
2. 双落点：`.dadao/cross-toolchain/bin/{clang,llc,ld.lld}` 与 `.dadao/host-tools/bin/lli` 均 `-x`（clang 现为真实可执行，非断链）。
3. 同源：install==build md5 逐工具相等（clang `02df414a…`/llc `89016c4d…`/ld.lld `d89ba2ba…`/lli `d317c938…`）；四工具版本 `23.1.1` == `components.lock.toml` `shallow_ref=llvmorg-23.1.1`；source HEAD `0e9e52f7b` 父 = 锁定 `6dfe1677a`。
4. `make check` EXIT=0；`make check-patch-tree` EXIT=0。
5. `run.sh` `RUN_EXIT=0`；注入：移除 `host-tools/bin/lli` → 断言 FAIL(rc=1) → `cp`+md5 还原=`d317c938…` → 回绿 PASS。
6. `git status --porcelain -uall` = `M Makefile`（+本任务书）；`check_dirs --residue` EXIT=0；无 `*_tmp*`/`*.orig`/`*.rej`。

**外部（非本任务）改动**：`.tao/knowledge/lessons.md`（主会话 06:54 并发新增 §8.21），未触碰。

**新发现/坑**：
- **安装断链坑**：LLVM build 树 `bin/clang -> clang-23`（版本化软链）；`cp -a` 只复制软链本身 → 安装出断链 `clang`。修复 `cp -aL --remove-destination`（解引用 + 幂等；实测 `cp -f`/`-aLf` 均不能覆盖断链）。
- stamp 命中判据：`.work/build/llvm/.dadao-llvm-config` == `targets=DADAO;X86 projects=clang;lld …` ⇒ 增量跳过 configure（已验证）。
- 建议沉淀：LLVM 版本化软链工具安装须解引用；`cp -f` 不能覆盖断链，须 `--remove-destination`。

**遗留问题**：无（acceptance 1–6 全 PASS）。注：`clang --version` 报 `Target: unknown`（未设默认 triple）——属 clang 侧配置，不在本任务范围（`LLVM-063t`）。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`Makefile` diff（一次配置 stamp + 双落点 install）与 `.work/evidence/INFRA-050t/run.sh`。

**逐行审查意见/问题**：
- (a)【已修】`HOST_LLVM_TOOLS` 含 `clang`，而 build 树 clang 是软链 → `cp -a` 产生断链。改 `cp -aL --remove-destination`，实测安装后 `clang --version` rc=0。
- (b)【非缺陷】`lld`/`lli` 亦用 `cp -aL --remove-destination`（真实文件，`-L` 无副作用），换取一致与幂等。
- (c)【非缺陷】`run.sh` 放行 `.tao/knowledge/*`（主会话领域）并显式打印 `INFO external …`，不隐藏；`check_dirs --residue` 独立覆盖临时文件。
- (d)【非缺陷】`md5()` 双缺文件时可能假 PASS，但 section 1/2 先断言存在并累加 `FAILS`，verdict 不受影响。
- (e)【非缺陷】注入仅覆盖 host `lli` 一处断言（任务要求「如…一处」即足），FAIL→还原→回绿三段均有真实输出。

**finding 处置表**

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| clang 安装断链 | ✅已修 | `Makefile` install 循环 `cp -a`→`cp -aL --remove-destination` | `INFRA-050t-clang-version.log`（rc=0）；`run.sh` 断言 `cross-toolchain/bin/clang` PASS |
| 证据脚本缺 `make check` | ✅已修 | `run.sh` §4 增 `make check` | `run.log`：`make check expected=0 actual=0 rc=0` |
| 残留检查漏 git status | ✅已修 | `run.sh` §6 增 allowed-path 检查 | `run.log`：`git status: only task files changed expected= actual= rc=0` |

**判决**：所有 finding 已修/判非缺陷，acceptance 1–6 全 PASS → 状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**脚本审核**：`run.sh` 合格——`check_exec`/`check_eq` 两支均打印不同结果且 return 1；§5 注入移除 lli→FAIL→cp+md5 还原→回绿，非恒真；无 `tee`；退出码用 `r=$?`。

**重跑**（`/tmp/opencode/INFRA-050t-review/run.log`）：EXIT=0，26 项全 PASS。

**独立注入**：cp 备份 `.dadao/host-tools/bin/lli`（md5=d317c938）→ `rm -f` → 重跑脚本 EXIT=1（4 处 FAIL：存在性/md5/版本/注入前置）→ `cp` 还原 md5=d317c938 相等 → 重跑 EXIT=0 全绿。

**独立复核 ①–⑥**：
- ① `.work/build/llvm/bin/{clang,llc,lld,lli}` 均可执行，clang version=23.1.1 ✓
- ② `.dadao/cross-toolchain/bin/{clang,llc,ld.lld}` + `.dadao/host-tools/bin/lli` 均可执行；clang 为真实文件（readlink -f 解引用后存在）✓
- ③ 四工具 install==build md5 相等（02df414a/89016c4d/d89ba2ba/d317c938）；版本均=23.1.1==lock ✓
- ④ `make check` EXIT=0；`make check-patch-tree` EXIT=0 ✓
- ⑤ `check_dirs --residue` EXIT=0 ✓
- ⑥ `git status --porcelain -uall` = `M Makefile` + `M .tao/tasks/infra/INFRA-050t-*`（+`M .tao/knowledge/lessons.md` 属主会话并发改动，不计入）✓

**重建纪律**：JOBS=8（`-j8`），无 `-j$(nproc)`；`components/llvm-project/patches/**` 未被改（`git diff` 无 components/）；一次 configure（stamp 命中后增量）✓

**判决：Accepted** —— 验收 1–6 全 PASS，约束无违反。

#### 主会话下发前预检结论（2026-10-08，只追加；下次据此直接下发）

- **前置（实测）**：`Makefile` 现为 `-DLLVM_TARGETS_TO_BUILD=DADAO`、`LLVM_ENABLE_PROJECTS` 为 `""`/`lld` ⇒ 本任务须改 **targets = `DADAO;X86`** 且 **`LLVM_ENABLE_PROJECTS` 含 `clang`**（`clang` 源码在 `.work/source/llvm-project/clang` 已就位）；`lli` 由 X86 target + JIT 自然产出。
- **成本申报**：**LLVM 重建 30–90 分钟**（新增 X86 + clang，编译量显著增加）；`JOBS=8`、禁全核、**一次一个长构建**。
- **越界边界**：**不改 `components/llvm-project/patches/**`**（clang 侧补丁归 `LLVM-063t`）——本任务**只改构建配置 + install 落点**。
- **落点**：经 `manifests/install-dirs.lock.toml` + `tools/infra/paths.py` 解析（禁硬编码）；host `lli` → `.dadao/host-tools/bin/lli`（如需新锁键，按 `ADR-0016 D7` 加键 + getter）。
- **中断记录**：首次下发 `engineer` 于 **2026-10-08 夜**被 `aborted`（`Tool execution interrupted`，子代理会话 `ses_ee3d102daffe…`）；**核对：工作树干净、无 `.work/evidence/INFRA-050t/`、`.dadao/` 未变 ⇒ 未落盘**。按规则下次**重新下发同一任务**（本预检结论已内联，可直接用）。
- **续跑指针**：M6 链首 = `INFRA-050t`（本任务）→ 见 `.tao/knowledge/milestones.md`「当前进度」。
#### 更正（2026-10-08 夜，只追加）：中断前**已有部分改动落盘**

- 上文「未落盘」**有误**。实测 `git status` 显示**已落盘 3 个文件**（被中断的 engineer 已开始实现）：
  - `manifests/install-dirs.lock.toml`、`tools/infra/paths.py`、`tools/infra/check_dirs.py`
- 已由**主会话以 `WIP:` 提交保命**（信息含「中断」字样），**未 push**；续跑时**先看该提交**决定**继续或重做**（任务未完成：无完成区、无证据脚本、`Makefile` 尚未改）。
- **续跑动作**：① 读本任务书 + 该 `WIP:` 提交的 diff；② **重新下发同一任务**（预检结论见上节，已内联）；③ 若判该半成品不可用 ⇒ **先 `cp` 备份再重做**（**禁** `git checkout/restore/stash`）。

