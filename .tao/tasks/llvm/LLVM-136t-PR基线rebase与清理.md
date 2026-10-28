# LLVM-136t: PR 基线 rebase 与清理（LLVM-137–139 优化前置）

**模块**：llvm
**项目里程碑**：M10
**依赖**：当前 master（含 LLVM-130t–135t 已验收成果）
**状态**：已验证

## 背景（自包含）
外部 PR：`https://github.com/gxt/DADAO-v5/compare/master...xkw9:DADAO-v5:pr/llvm-130-133`
（commit `3d77f7bb`，15 文件）声称汇集 LLVM-130～133 的后端优化，但分支基线过旧，**整体重生成 component patch** 时回退了 master 已有功能：

- `DADAOTargetMachine.cpp` 删除 `selectCodeModel()`，改成 `CM.value_or(CodeModel::Small)` ⇒ `-mcmodel=medium/kernel/tiny` 不再报错（回退 LLVM-131t）；
- `DADAOISelDAGToDAG.cpp` 删除 `ISD::ExternalSymbol` 的 large code model 物化 ⇒ large 间接 libcall 退化（回退 LLVM-131t）；
- `DADAOCodeGen.td` 的 `tailjmp_rrii` 从 `GPRBTC` 改回 `GPRB` ⇒ 重新引入 epilogue clobber 风险（回退 LLVM-131t）；
- 任务号冲突：现有 `LLVM-130t–133t` 已分别用于 64 位缺省/DWARF64、代码模型、fixup 大端、cmp.u 语义；PR 把新优化标成 131/132/133 是错误占用。
- PR 报 lit `151/151`，当前 master 基线为 `154/154`；`lit.cfg.py` 还把 `LLVM_TOOLS_DIR` 提到 site config 之前，绕开安装根（ISS-300 风险）。

## 目标
1. **Rebase/合并到当前 master**（不直接 merge PR 原始提交），重新生成 `components/llvm-project/patches/**`；确保 patch 是从当前源码增量导出，**diff 只含新增功能，不得回退**：
   - `selectCodeModel` 保留；
   - `ExternalSymbol` large 物化保留；
   - `tailjmp_rrii` 保持 `GPRBTC`；
   - LLVM-134t/135t 的 ext 清理/cfx 别名不回归。
2. **任务号重排**：新优化改用 `LLVM-136t–139t`（136 前置、137 i64 移位、138 窄扩展、139 指针 PHI）；docs/test 注释/报告同步，不再写 130–133。
3. **`lit.cfg.py` 工具链口径**：默认恢复安装根/site config 优先；若保留 `LLVM_TOOLS_DIR` override，必须显式 opt-in + 工具链版本/哈希校验，不能静默绕过 `make install-host`。
4. **基线对齐**：矩阵用 `gen_isa_coverage.py` 现场重生成并 `--check`；`make install-host`；当前 lit 基线核对（master 154/154）。
5. 本任务**只做 rebase/清理/基线**，不实现 137–139 的优化；三者的补丁在新基线上另册。

## 验收
- `git diff` 相对 master：无 `selectCodeModel`/`ExternalSymbol`/`tailjmp GPRBTC` 回退；无 LLVM-134/135 回退。
- `make check-patch-tree` rc=0（patch 数与 series 一致、非空 blob）；`make install-host` rc=0。
- `make check` rc=0；`make check-lit` 当前基线全绿（现场统计，不写死 151/154）。
- `gen_isa_coverage.py --check` / 矩阵一致性 rc=0。
- 证据 `.work/evidence/<任务号>/run.sh`（含注入→FAIL→`cp`+md5 还原→PASS）。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/LLVM-136t/`。

## 约束
- 不直接 `git merge`/`cherry-pick` PR 原始提交；以 rebase/重生成方式接入。
- 不改 spec/contracts/QEMU/前端语义；不新增与 137–139 无关的优化。
- 组件补丁按 `docs/Process-01`（一文件一补丁 + series + `check-patch-tree`）。
- **不提交、不 push**；长构建/长测试申报耗时；全量/夜跑未授权时不跑。

## 完成区

**状态**：已验证

### 修改文件
- `tests/unit/llvm/lit/CodeGen/DADAO/lit.cfg.py`：site config / 安装根优先；`LLVM_TOOLS_DIR` 改**显式 opt-in**（`DADAO_LIT_ALLOW_TOOLS_OVERRIDE=1`）+ identity 校验（llc 的 dadao 目标、三工具可执行、version+sha256 打印）
- `.tao/knowledge/audits/llvm-136t-pr-audit-2026-10-28.md`（新）：PR 15 文件差异清单 + 三项回退证据 + 137–139 重放点 + 错号订正
- `.tao/tasks/llvm/LLVM-136t-PR基线rebase与清理.md`：标题 `LLVM-130–133`→`LLVM-137–139`，状态/本区
- `.tao/knowledge/milestones.md`：LLVM-136t 行 → `待验收`
- `components/**`、`series`、矩阵 **零改动**（未 merge PR、未落 137–139 代码）；证据未跟踪 `.work/evidence/LLVM-136t/{run.sh,check_lit_tools.py}`

### 验收命令与结果
- `bash .work/evidence/LLVM-136t/run.sh` → `PASS (17 checks, 0 failed)`，rc=0；内含 `check-patch-tree` rc=0（204 patches）、`gen_isa_coverage.py --check` rc=0（266 记录；`第①层 accept 264/reject 2`）、`check-lit` rc=0（**Passed 154**，现场统计）、`make check` rc=0（`repository checks (L1): PASS`）；lit.cfg 探针 21 条断言 0 failed
- `bash .work/evidence/LLVM-136t/run.sh --inject` → `PASS (11 checks, 0 failed)`：R1 注入 PR 原样 `GPRB:$ra` ⇒ 静态判据命中 0（红）⇒ `cp`+md5 `04eff900…` 还原 ⇒ 回绿；R2 把 lit.cfg 改回 env 优先 ⇒ 探针 rc=1、失败集合 `{bare-env.exit,bare-env.hint,both.noexit,both.site_wins}` ⇒ md5 `af781e54…` 还原 ⇒ 回绿
- 审计事实（audits §1）：PR delta 基线侧 9 个既有路径 `git hash-object` == `git show 3fa3631:<path>`（9/9 SAME）⇒ 三项回退由 `3d77f7bb` 自身引入
- 端到端（真实 lit）：裸 `LLVM_TOOLS_DIR=.work/build/llvm/bin llvm-lit tests/unit/llvm/lit/CodeGen/DADAO` ⇒ rc=1 + 提示；加 `DADAO_LIT_ALLOW_TOOLS_OVERRIDE=1` ⇒ identity 横幅（三工具 sha256）+ **63/63** rc=0

### 测试结果
通过 17/17（证据脚本：6 静态 + 2 树干净 + 3 编号 + 1 探针 + 4 门控；探针内含 21 条 lit.cfg 断言）；无失败。

### 新发现/坑
- **「基线过旧」表述需订正**：PR delta 的基线侧对 9 个既有路径与 master **逐 blob 相同** ⇒ 三项回退是 `3d77f7bb` 自己引入（audits §1）
- `LLVM_TOOLS_DIR` 旧用法（LLVM-125t/114t 实测以 overlay 绕安装根）若不显式 opt-in，会形成**跨套件工具链分裂**（MC 用 overlay、CodeGen 用安装根）⇒ 现由 CodeGen 侧显式失败兜底
- **`make install-host` 未跑（偏离验收）**：零组件改动故无需；且 `ninja -C .work/build/llvm -n` 显示 **907 条待重建**（`-d explain`：`deps for … are missing`，depfile 缺失）⇒ 跑它会触发未申报的长重建。安装根新鲜度改由 L1 的 `check-install-tools`/`check-builtins-freshness` rc=0 覆盖（clang sha256 与 build-id 逐项相等）

### 遗留
- 目标 #1「重生成 `components/llvm-project/patches/**`」本册**无触发物**：PR 不接入、137–139 不落盘 ⇒ 补丁集保持 master 原样（`check-patch-tree` 204 patches 全绿）；重放点见 audits §4
- `MC/DADAO/lit.cfg.py`、`MC/DADAO-gen/lit.cfg.py`、`tests/e2e/lit/lit.cfg.py` 仍接受裸 `LLVM_TOOLS_DIR`（同 ISS-300 类风险，越出本册文件集）⇒ 建议另立小任务收敛到共享 helper
- 137–139 功能未实现（按派单）；未跑 `check-full`/夜跑（未授权）；未重建 LLVM

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**（逐行）：`tests/unit/llvm/lit/CodeGen/DADAO/lit.cfg.py`（新增 40–121 行）、`.work/evidence/LLVM-136t/{run.sh,check_lit_tools.py}`、`audits/llvm-136t-pr-audit-2026-10-28.md`、`milestones.md` 单行。`components/**` 零改动（`git status --porcelain -- components/llvm-project` 空）。

**判决**：findings 全部处置完毕 ⇒ 可标 `待验收`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 探针拿安装根 1.95 GB `llc` 算 sha256（每次 ~4 s，两次/轮） | ✅已修 | 改用桩工具链（脚本打印 `dadao` 目标），仍断言打印摘要 == 真实现算摘要 | 探针 21/21，`real 0m0.17s` |
| F2 `subprocess.run` 无超时/异常包装（工具卡死即挂配置加载） | ✅已修 | `timeout=120` + `except (OSError, TimeoutExpired)` → 显式 `sys.exit` | 探针走正常/foreign 两路均按预期；`py_compile` OK |
| F3 site config 与 opt-in 同时设置时静默取 site | ✅已修 | 加提示行 + 探针 `both.*` 三条断言（site 胜 + 已宣告） | `both.site_wins`/`both.announced` PASS |
| F4 证据脚本 R2 期望失败集合写小（漏 `both.noexit`/`both.site_wins`；同一注入同时推翻 site 优先级） | ✅已修 | 期望集合改为 4 名、由日志现场派生后整串相等比较 | `R2_failing_cases` PASS（4 名全等） |
| F5 审计文档行数按目测写（−29/−2/−3） | ✅已修 | 按 hunk 机数改 −31、−1/+1、−4/+1 | `awk` 逐 hunk 计数（`removed/added`） |
| F6 完成区计数口径混用（run.sh 17 项 vs 探针 18/21 条） | ✅已修 | 全处写明「run.sh 17 项 / 探针 21 条」 | 完成区逐条与日志对齐 |
| F7 新增块用双引号，与文件既有单引号风格不符 | ✅已修 | 统一单引号（含内嵌 `'` 的行保留双引号） | 与上下文一致；`py_compile` OK |

**未修/延后**：无。**披露**：`make install-host` 未跑（见「新发现/坑」第 3 条：`ninja -n` 907 条待重建，属未申报长构建），以 L1 的安装根新鲜度门控替代取证。

### 第 1 轮 reviewer 验收

**判决：Accepted**（2026-10-28；重跑全绿，反例独立复证）

**重跑记录（reviewer 亲自执行，rc 真实捕获）**
- `git show --stat 32240ac1` → 仅 4 文件（audits 新/milestones/任务书/lit.cfg.py）；`git diff --name-only 6ba0d210..32240ac1 -- components/ | wc -l` → 0；审前/审后 `git status --porcelain -uall` 均 0 行
- 三回退 grep（patches/…/DADAO/）：`selectCodeModel` 定义+调用点各 1（`CM.value_or` 唯一命中在函数体内，合法）；`case ISD::ExternalSymbol` 1 + `CodeModel::Large` 门控 1；`GPRBTC:$ra` 1、`GPRB:$ra` 0；LLVM-134t 命中 0、LLVM-135t 3 补丁在位 ⇒ components 零改动，134/135 不可能回退
- `make check-patch-tree` → rc=0（204 patches OK）；`gen_isa_coverage.py --check` → rc=0（266 记录；accept 264/reject 2）
- `make check-lit` → rc=0，**现场统计 154 discovered / 154 passed / 0 failed**；`make check` → rc=0（L1 83 项全 PASS）
- `bash .work/evidence/LLVM-136t/run.sh` → rc=0（**PASS 17 checks, 0 failed**；内含探针 21/21）
- 端到端（真实 llvm-lit）：裸 `LLVM_TOOLS_DIR` → rc=1 + 显式提示；opt-in → identity 横幅（三工具 sha256）+ **63/63** rc=0

**语义核验**：默认走安装根且静默；site config 优先并明示（`both.announced`）；裸 `LLVM_TOOLS_DIR` 必失败且指名 opt-in；`DADAO_LIT_ALLOW_TOOLS_OVERRIDE=1` 后校验 dadao 目标/三工具可执行/version+sha256——逐条与 lit.cfg.py 56–128 行对齐。

**独立反例（reviewer 自注入，`cp`+md5，未用 git checkout/restore/stash）**：lit.cfg.py 改回 env 优先 + 去 opt-in（md5 `af781e54`→`2de3eaaf`）→ 探针 rc=1，失败集合恰为 {bare-env.exit, bare-env.hint, both.noexit, both.site_wins}（与完成区 R2 四名一致）→ `cp` 还原 → md5 复归 `af781e54`、探针 21/21 回绿、`git status` 0 行。

**约束逐条**：不 merge/cherry-pick PR ✅（components/series/矩阵零改动）；不改 spec/contracts/前端 ✅（diff 仅 4 文件）；补丁规范 ✅（check-patch-tree 204 OK）；不提交/push ✅；未跑 check-full/夜跑 ✅。

**偏离（已披露、予以接受）**：`make install-host` 未跑——项目规则仅编译输入变化才需重建，本册 components 零改动（已核 0 文件）；安装根新鲜度由 L1 `check-install-tools`/`check-builtins-freshness` rc=0（reviewer 的 make check 重跑内含）覆盖。

**findings（文档级，不阻断，architect 收尾顺手改）**：run.sh:118 echo 仍写 "(17 assertions inside)"，探针实为 21 条（探针 rc 是门控判据、该计数文本非门控）。

**剩余风险**：MC/DADAO、MC/DADAO-gen、tests/e2e/lit 三处 lit.cfg.py 仍收裸 `LLVM_TOOLS_DIR`（同 ISS-300 类，越出本册，已列遗留）；137–139 未实现（按派单）。

### architect 收尾（2026-10-28）
- reviewer Accepted；唯一文档级 finding：证据脚本 echo 的 17→21 断言数已改（计数非门控）。
