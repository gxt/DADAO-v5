# INFRA-053t: 修复 `install-host` 幂等性（`cp` 间歇 `File exists`）

**模块**：infra
**项目里程碑**：M6
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `ISS-172`（`.tao/knowledge/issues.yaml`）：`install-host` 幂等性缺陷——`make install-host`（及依赖它的 `make test-elf`/`test-semihost`）**间歇** `rc=2`，报 `cp: cannot create regular file '<HOST_TOOLCHAIN_BIN>/<tool>': File exists`（`make: *** [Makefile:278: install-host] Error 1`）。
  - `Makefile` 的 `install-host` 目标（`Makefile:276–293`），尤其：`278` 的 `for t in $(HOST_LLVM_TOOLS) … cp -aL --remove-destination …`、`284` 的 `cp -a $(QEMU_BUILD)/qemu-system-dadao …`（**唯一**无 `--remove-destination` 的 `cp`）、`281`/`283` 的 `cp -aL --remove-destination`。
  - 观测：`QEMU-053t` 任务书「审阅记录·第 2 轮 reviewer 补正 §③」；gate 日志 `.work/log/qemu/QEMU-053t-review-gate-test-{elf,semihost}.log`（`test-elf`/`test-semihost` **并行**执行时**同时**失败、失败文件不同；`test-codegen`/`install-host` 单独跑通过）。
- **输出**：`make install-host` 与 `make test-semihost` **连续两次均 `EXIT=0`**（首次为冷态）；不改变已装工具集与落点（`ADR-0016 D3/D4/D5/D11`）。
- **约束**：
  - **先定位再修**：先复现并按证据判定根因（**并发调用 install-host 的竞态** vs `cp` 标志语义），**不得**在未定位时改。
  - **最小改动**：只动 `install-host` 幂等性相关行；**不改**工具集清单/落点/`Makefile` 其它目标。
  - **不引新依赖**。
  - **`spec/`/`contracts/`/`components/**` 交集为空**（纯 `Makefile` 修复）。

## 验收标准

1. **现象复现与根因**：给出失败 `rc` + 完整 `cp` 错误真实输出，并给出根因判定（并发竞态 / `cp` 语义），附证据。
2. **串行幂等**：`make install-host` **连跑两次**均 `EXIT=0`；`make test-semihost` **连跑两次**均 `EXIT=0`（附真实输出与退出码）。
3. **并发场景**：至少重现一次「`make test-elf` 与 `make test-semihost` 并行」**不再**触发 `File exists`（修复后）；或在证据脚本中**明确证明**并发为不支持用法并在 `Makefile` 注释/文档处声明（二者择一，须给真实输出）。
4. **一键证据脚本**（`.work/evidence/INFRA-053t/run.sh`）：非交互；任一检查失败即非零退出；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp` + `md5sum` 还原 → 预期回绿**；结尾**禁** `tee`。
5. **不回归**：`make check` 等既有门控 `EXIT=0`（通过数与改前**逐项相等**，或按门控现场统计**不下降**）。
6. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 硬约束

- **临时目录** `/tmp/opencode/INFRA-053t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须披露。
- **失败即停、禁自动重试**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入）；`git status`/`git diff` 干净**不作**「已还原」证据。
- 复杂命令输出留 `.work/log/infra/INFRA-053t-<命令名>.log`（**不得只留 `/tmp`**）。

## 完成区

**测试结果**：全绿。串行 `install-host`×2=0；并行 `install-host` 8 对：修复前 7/8 `rc=2`、修复后 0/8（`File exists` 计数 0）；串行 `test-semihost`×2（含冷态首跑，先清 install 根）=0；并行 `test-elf`+`test-semihost` 2 轮均=0、`File exists`=0；`make check`=0（改前/改后逐项**相等**：231 PASS 行、lit 73/73、`repository checks: PASS`）。一键脚本 `.work/evidence/INFRA-053t/run.sh` EXIT=0。
**修改文件**：`Makefile`（install-host 配方 + 注释）；`.work/evidence/INFRA-053t/run.sh`（新，gitignored）；本任务书。
**验收结果**：
- #1 根因：`cp -aL --remove-destination` = `unlinkat(dst)` 后 `openat(dst,O_WRONLY|O_CREAT|O_EXCL)`（strace 实证，coreutils 9.4）；两进程并发时后者 O_EXCL 撞前者新建→`EEXIST`。复现：8 对并行 `make install-host` 中 7 对 `rc=2`，报 `cp: cannot create regular file '…/bin/llvm-objdump': File exists`（`make: *** [Makefile:278: install-host] Error 1`）→ `.work/log/infra/INFRA-053t-baseline-parallel-FAIL.log`。
- #2 修复：`$(call atomic-install,src,dst)` = `cp -aL src dst.tmp.$$ && mv -f … dst`（rename(2) 原子替换，兼容 dangling symlink）。串行/冷态/并行均 EXIT=0。
- #3 并发：选 (a)——并行 `test-elf`+`test-semihost` 2 轮均 EXIT=0、0 `File exists`（`.work/log/infra/INFRA-053t-evidence-run.log`）；并加注释声明「同 worktree 并发跑 gate 仍不支持」（AGENTS.md），install 写已原子化。
- #4 注入自检：把 `atomic-install` 体还原为 `--remove-destination`（md5 由 `c28e50…` 变）→ 并发检查报 `File exists`/失败（预期 FAIL）→ `cp`+md5 还原（md5 相符）→ 回绿；脚本整体 EXIT=0。
- #5 门控：`make check` EXIT=0；baseline/fixed 逐项 diff 完全一致（`.work/log/infra/INFRA-053t-{baseline,fixed}-make-check.log`）。
- #6 残留：`git status --porcelain -uall` 仅 `M Makefile` + 本任务书；无 `*_tmp*`/`*.orig`/`*.rej`。
**新发现/坑**：`cp -L --remove-destination` 的 unlink+O_EXCL 非原子，跨进程并发必竞态；install 类写应用 temp+rename 原子替换。该 flaky 曾被误判为 pre-existing（ISS-172）。
**遗留问题**：lit 目录仍 `rm -rf`+`cp`（未原子化，非本次报告缺陷）；同 worktree 并发 gate 仍按 AGENTS.md 不支持。

## 审阅记录

### 第 1 轮 engineer 自审

**逐行审查**（改动仅 `Makefile` install-host + 注释）：
- 逻辑：`atomic-install` 唯一 temp 名（PID）→ `rename(2)` 原子替换；对现有普通文件与 dangling symlink 均成立（实验：`cp -aLf` 不能替换 dangling symlink，`mv` 可）。`$$$$`→shell PID 已经 `make -n` 核对。
- 一致性：`HOST_LLVM_TOOLS`/`HOST_TOOLCHAIN_BIN`/`HOST_TOOLS_BIN`/lit 落点/ sysroot 未变（ADR-0016 D3/D4/D5/D11）；仅把 `cp -a`(qemu) 改为 `cp -aL`（qemu 为普通文件，`-L` 无副作用，test-semihost 实跑通过）。
- 依赖：仅 `cp`/`mv`/`ln`/`mkdir`/`rm`，无新依赖。
- 防造假：`run.sh` 真实跑通并可失败（首轮因一条断言写错而 `EXIT=1`，证明断言有 FAIL 路径；修正后 `EXIT=0`）；注入后日志实测出现 `File exists`。
- finding：① 注入打印标签 `expected=>0` 略歧义（cosmetic）；② lit 目录未原子化。
  处置：① ❌不修（语义正确、脚本可读，改则需重跑 11min 证据）；② ⏸延后（非本次缺陷，已在 Makefile 注释声明并发边界）。其余无 finding，判决：实现达验收。

### 第 1 轮 reviewer 验收

**脚本审核**（`.work/evidence/INFRA-053t/run.sh`）：`report()` 失配即 `FAILED=1` 且两向断言（含 `>0` 双向）均可达 FAIL；注入断言 `s.count(old)==1` + md5 判非空；`cp -p` 备份 + `md5sum` 对账 + `trap restore_on_exit EXIT` 还原；全脚本无 `tee`，`make … > log 2>&1; rc=$?` 直捕退出码。**合格**。

**重跑**：`bash .work/evidence/INFRA-053t/run.sh > /tmp/opencode/INFRA-053t-review/run.log 2>&1; rc=$?` ⇒ **`EXIT=0`**，18 项 CHECK 全 PASS（串行 install-host×2=0、并行 4 对 failed=0/File exists=0、test-semihost×2（冷态，run.sh L64 清 install 根）=0、并行 test-elf+semihost=0/0、make check=0、注入 changed/>0/>0、还原 md5 `c28e5005…`==`c28e5005…`、回绿 0/0）。

**① 根因独立判定（成立=并发竞态）**：strace 实证 `cp -aL --remove-destination` 对已存在目标 = `unlinkat(dst0)` 后 `openat(dst0,O_WRONLY|O_CREAT|O_EXCL)`（非原子对）；本人临时目录 20 对并行 `cp -aL --remove-destination` ⇒ `failed_invocations=17 file_exists_lines=17`（`cp: cannot create regular file 'P': File exists`）；串行同命令 `cp_rc=0`。⇒ ISS-172 竞态根因成立，非串行 `cp` 语义问题。

**独立注入（与 engineer 不同）**：保留 `cp -aL $(1) $(2).tmp.$$` 参数与 tmp 步，仅把原子 `mv -f … dst` 换成非原子 `cp -aL --remove-destination … dst && rm -f`。`git diff --name-only` 非空、md5 `c28e5005…→4e9b571c…`；4 对并行 `make install-host` ⇒ **FAIL：`failed_invocations=4 file_exists_lines=4`**（`cp: … File exists` / `make: *** [Makefile:299: install-host] Error 1`）⇒ `cp -p` 还原，**md5 相等 `c28e5005…`** ⇒ 回绿 `failed=0 file_exists=0`。注：dispatcher 建议的 `mv -f→cp -f` 形态实测 `failed=0`（注入无效，不 FAIL），故改用上述形态（微实验先行）。

**③ 并发对照**：修复后并行 install-host 4 对 0 失败/0 `File exists`；并行 `test-elf`+`test-semihost` 均 EXIT=0/0；`Makefile` 已含 NOTE 声明「gate 并发同 worktree UNSUPPORTED」（两路线要件齐备）。

**④ 不改落点/工具集**：`git diff Makefile` 仅 1 个 hunk（@@ -268,20 +268,41 @@，install-host 配方 + 注释 + `atomic-install` define），无 `HOST_LLVM_TOOLS`/`HOST_TOOLCHAIN_BIN`/`HOST_TOOLS_BIN`/lit 落点增删改；`cp -a→cp -aL`（qemu，普通文件）已披露、实测无副作用。

**⑤ 门控不回归**：`make check` EXIT=0；改前（baseline log）vs 本人重跑：PASS 行均 231、lit `Passed: 73 (100.00%)`、`repository checks: PASS`、FAIL 行 0；lit 73 项**集合逐项相同**（仅并行执行顺序差）。逐项相等/不下降 ✓。

**⑥ 残留/快照对账**：注入前后 `git status --porcelain -uall` 均仅 `M Makefile` + 本任务书（与「修改文件」声明对齐；run.sh 在 `.work/evidence/` 不入库）；无 `*_tmp*`/`*.orig`/`*.rej`/`*_preinject`；Makefile md5 `c28e5005…` 与注入前快照相等。

**判决：Accepted**（验收 1–6 全部以本人重跑证据通过；遗留 lit 目录未原子化、同 worktree 并发 gate 不支持——均已在 Makefile 注释/完成区声明，非阻断）。
