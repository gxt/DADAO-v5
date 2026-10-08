# INFRA-048t: 生成物落点迁移（`test-codegen`/`test-elf`/lit → `.dadao/tests/`）

**模块**：infra
**项目里程碑**：M5
**依赖**：`INFRA-047t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **背景与规则（原样引用用户 2026-10-06 裁定，见 `.tao/knowledge/milestones.md`）**：
  > **生成物落点口径**：运行产物**默认为 `.dadao/tests/`**；**只有"难以放进 `.dadao/`"时**才退到**当前模块对应目录**；判据 = **"能否用配置选项解决"——能配置解决的一律不算"难"，必须放 `.dadao/`**。
  >
  > **落点规则生效时点**：**M4 已完成/在做的测试落点一律不动**；**自 M5 起按新规则**。M5 起步须迁移：① `test-codegen` 运行产物 `tests/llvm/codegen-e2e` → **`.dadao/tests/codegen-e2e`**；② `test-elf` 运行产物（`run_elf_e2e.py` 的 `DEFAULT_WORK_DIR` / `Makefile`）→ **`.dadao/tests/elf-e2e`**；③ lit 的 `test_exec_root`（现 `<build>/test-output/<name>`，在 `.work/build/llvm/` 内）→ **`.dadao/tests/lit-output/<name>`**。**`.work/log`（日志）与 `.work/evidence`（证据）不算"生成物"、不动**。
  - `.dadao/tests/` 已是安装根（`ADR-0016 D6`）下的测试产物根；路径经 `tools/infra/paths.py`（`test_artifacts_dir`）解析（**禁硬编码**）。
- **输入（自包含；现状须以 `grep`/`sed` 实测为准）**：
  - `Makefile`：`CODEGEN_E2E_WORK = tests/llvm/codegen-e2e`、`CODEGEN_ELF_WORK = .work/codegen-e2e-elf`、`test-codegen`/`test-elf` 目标（`--work-dir $(…)`）。
  - `tools/integ/run_codegen_e2e.py`：`DEFAULT_WORK_DIR = "tests/llvm/codegen-e2e"`。
  - `tools/integ/run_elf_e2e.py`：`DEFAULT_WORK_DIR`（当前 `.work/codegen-e2e-elf` 或等价，**以实测为准**）。
  - lit 的 `test_exec_root`：`tests/llvm/lit/MC/DADAO/lit.cfg.py`、`tests/llvm/lit/CodeGen/DADAO/lit.cfg.py`、`tests/e2e/lit/**`（现指向 `<build>/test-output/<name>`，在 `.work/build/llvm/` 内）。
  - `.gitignore`：现有 `tests/llvm/codegen-e2e/` 等生成物忽略规则。
- **输出**：
  1. `Makefile`：`CODEGEN_E2E_WORK` → **`$(TEST_ARTIFACTS_DIR)/codegen-e2e`**；`CODEGEN_ELF_WORK` → **`$(TEST_ARTIFACTS_DIR)/elf-e2e`**；`test-codegen`/`test-elf` 目标同步（跑前清空、跑后按需保留）。
  2. `tools/integ/run_codegen_e2e.py`、`tools/integ/run_elf_e2e.py`：`DEFAULT_WORK_DIR` 指向 `.dadao/tests/{codegen-e2e,elf-e2e}`（可经 `paths.py` 解析；`--work-dir` 默认值同步）。
  3. lit `test_exec_root` → **`.dadao/tests/lit-output/<name>`**（经 `paths.py`/相对仓库根解析）。**须核实的 lit 配置共 4 处**（实测 `find tests -name lit.cfg.py`）：
     - `tests/llvm/lit/MC/DADAO/lit.cfg.py`、`tests/llvm/lit/CodeGen/DADAO/lit.cfg.py`、`tests/e2e/lit/lit.cfg.py`：**设置 `test_exec_root`**（现指向 `<build>/test-output/<name>`，在 `.work/build/llvm/` 内）⇒ **同改**。
     - **第 4 处 `tests/llvm/lit/tools/DADAO/lit.cfg.py`（730 B，另含 `README.md`）**：**占位套件、当前无测试、且不在 `check-lit` 套件列表**（`Makefile` 的 `check-lit` 只跑 `tests/llvm/lit/MC/DADAO tests/llvm/lit/CodeGen/DADAO tests/e2e/lit`）；其 `test_exec_root` 仅见于**注释**（第 7 行"…a build-tree `test_exec_root`…"，正文未设置）。
       **处置口径**：先由 engineer `grep` 核实该套件是否被任何门控/脚本**实际运行**——**被运行** ⇒ **同改**；**未**被运行 ⇒ 按最小原则**不改**，但须在「完成区」/「遗留问题」**明确登记**（说明其 `test_exec_root` 仍指构建树、属**未被门控覆盖**的配置），并注明 `check-lit` 不含该套件故**无门控验证**。**不得**为它引入新门控。
  4. `.gitignore`：清理 `tests/llvm/codegen-e2e/` 旧模式（新落点 `.dadao/` 整体已被忽略），保留 M4/E2E 其它必要忽略规则。
     - **删除残留旧产物目录**（`gitignore` 一旦移除旧模式，这些运行产物会暴露为未跟踪残留，与「验收 7」冲突，**必须一并删除**）：`tests/llvm/codegen-e2e/`（gitignored 运行产物 `arith_*.bin/.o/.s/.prog.s` 等、可再生、非源码；用 `rm -rf`），以及 `.work/codegen-e2e-elf`（若存在，同理）。
     - 完成区须贴删除前后 `ls`/`git status` 的**真实输出**。
     - **不得**以「保留 `.gitignore` 旧忽略规则」回避——按 M4 不动 / **M5 起生效**的落点口径，旧落点自本任务（M5）起须清除。
- **约束（硬）**：
  - **只改落点，不改语义**：`test-codegen` 用例/流水线/期望值/通过数（15/15）、`test-elf`（5/5）、lit 用例与通过数**零改动**。
  - **`.work/log`/`.work/evidence` 不动**（日志/证据留存纪律，`.tao/README.md`）。
  - **与 `INFRA-047t` 串行**（同改 `Makefile`）。
  - `Makefile` 为共享文件，与其它改 `Makefile` 的任务**串行**。
  - 失败即停、**禁自动重试**；临时目录 `/tmp/opencode/INFRA-048t/`；**不提交 git**；复杂命令输出留存 `.work/log/infra/`（**禁 `tee`**）。
  - **重建成本申报**：本任务不触发重建（仅改落点/路径）；若为验收需跑 `test-codegen`/`test-elf`，其前置 `build-*` 视现状增量，开工前说明。

## 验收标准

1. **新落点产出**：`make test-codegen` EXIT=0（15/15）后，`.dadao/tests/codegen-e2e/` 内有产物；`make test-elf` EXIT=0（5/5）后，`.dadao/tests/elf-e2e/` 内有产物；给 `ls -l` 真实输出。
2. **lit 落点**：`make check-lit` EXIT=0（60/60）后，`.dadao/tests/lit-output/<name>` 有输出（给 `ls`）；`grep -rn "test-output" tests/ --include="lit.cfg.py"` 不再指向 `.work/build`（第 4 处 `tests/llvm/lit/tools/DADAO/lit.cfg.py` 如按口径不改，其注释中的 `test_exec_root` 属白名单，须在完成区说明）。
3. **路径清零**：`grep -rn "tests/llvm/codegen-e2e\|\.work/codegen-e2e-elf" Makefile tools/ .gitignore | grep -v __pycache__` 无旧落点残留（历史归档/任务书正文除外）；默认 `work_dir` 指向新落点。
4. **语义零改动**：`test-codegen` 15/15、`test-elf` 5/5、`check-lit` 60/60 与改前**逐项相等**（给真实输出）。
5. **门控**：`make check` EXIT=0；`make check-no-residue` EXIT=0；`git status --untracked-files=all` 不显示 `.dadao/` 下生成物；**旧落点目录 `tests/llvm/codegen-e2e/`、`.work/codegen-e2e-elf` 已不存在**（`git status --porcelain -uall` 干净，不因清理 `.gitignore` 旧规则而暴露未跟踪残留）。
6. **一键证据脚本**：`.work/evidence/INFRA-048t/run.sh`——非交互、失败非零、逐项打印、**内置注入自检**（把某个 `*_WORK` 改回旧路径/重命名新落点目录 ⇒ 断言 **FAIL** ⇒ 还原 ⇒ 回绿），结尾**禁 `tee`**；给真实输出与退出码。
7. **无残留**：`git status --untracked-files=all` 仅本任务应有改动（`Makefile` + `tools/integ/run_*_e2e.py` + `lit.cfg.py` + `.gitignore` + 本任务书）；**旧落点目录 `tests/llvm/codegen-e2e/`、`.work/codegen-e2e-elf` 已不存在**，`git status --porcelain -uall` 干净；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：通过 4/4 门控项（改前/改后逐项相等）：
- `make test-codegen` → **EXIT=0，Results: 15/15 passed, 0 failed**（改前工作目录 `tests/llvm/codegen-e2e`；改后 `work dir /mnt/tao/DADAO-v5/.dadao/tests/codegen-e2e`）
- `make test-elf` → **EXIT=0，Results: 5/5 passed, 0 failed**（改前 `/mnt/tao/DADAO-v5/.work/codegen-e2e-elf`；改后 `work dir /mnt/tao/DADAO-v5/.dadao/tests/elf-e2e`）
- `make check-lit` → **EXIT=0，Total Discovered Tests: 60 / Passed: 60 (100.00%)**（输出落 `.dadao/tests/lit-output/{DADAO-MC,DADAO-CodeGen,DADAO-E2E}`）
- `make check` → **EXIT=0，repository checks: PASS**；`make check-no-residue` → **EXIT=0，check-no-residue: PASS**
- 一键证据脚本 `.work/evidence/INFRA-048t/run.sh` → **30/30 checks PASS，RUN_EXIT=0**（含注入自检 注入→FAIL→还原→回绿）

日志（真实留存）：`.work/log/infra/INFRA-048t-pre-{test-codegen,test-elf,check-lit}.log`（改前）、`.work/log/infra/INFRA-048t-post-{test-codegen,test-elf,check-lit,make-check,check-no-residue}.log`（改后）、`.work/log/infra/INFRA-048t-evidence-run.log`（证据脚本整轮）。

**修改文件**（与 `git status --porcelain -uall` 一致，7 项）：
- `Makefile` — `CODEGEN_E2E_WORK` → `$(TEST_ARTIFACTS_DIR)/codegen-e2e`；`CODEGEN_ELF_WORK` → `$(TEST_ARTIFACTS_DIR)/elf-e2e`
- `tools/integ/run_codegen_e2e.py` — `DEFAULT_WORK_DIR = str(_dadao_paths.test_artifacts_dir() / "codegen-e2e")`
- `tools/integ/run_elf_e2e.py` — `DEFAULT_WORK_DIR = str(_dadao_paths.test_artifacts_dir() / "elf-e2e")`
- `tests/llvm/lit/MC/DADAO/lit.cfg.py`、`tests/llvm/lit/CodeGen/DADAO/lit.cfg.py`、`tests/e2e/lit/lit.cfg.py` — `test_exec_root = str(dadao_paths.test_artifacts_dir() / "lit-output" / config.name)`（不再经 `build_root`）；顺带把 repo-root/manifest 定位 + `import paths` 提前（供工具定位与 exec_root 共用）
- `.gitignore` — 删除 `tests/llvm/codegen-e2e/` 旧忽略规则
- **删除（gitignored 运行产物、可再生）**：`tests/llvm/codegen-e2e/`（60 文件）、`.work/codegen-e2e-elf/`（16 文件）
- 任务书 `.tao/tasks/infra/INFRA-048t-生成物落点迁移.md`（完成区/状态）
- 证据脚本 `.work/evidence/INFRA-048t/run.sh`（gitignored，不入库）

**验收结果**：逐条真实输出：

- **验收 1（新落点产出）**：
  ```
  $ ls -l .dadao/tests/codegen-e2e/   # 60 files (15 程序 × .s/.prog.s/.o/.bin)
  -rw-rw-r-- 84  arith_add_sub_neg.bin
  -rw-rw-r-- 640 arith_add_sub_neg.o
  -rw-rw-r-- 647 arith_add_sub_neg.prog.s
  -rw-rw-r-- 2347 arith_add_sub_neg.s ...
  $ ls -l .dadao/tests/elf-e2e/       # 16 files
  -rwxrwxr-x 66504 cross_tu_pdiff.elf
  -rw-rw-r-- 624   cross_tu_pdiff.m4_pdiff_data.o
  -rw-rw-r-- 552   crt0.o ...
  ```
- **验收 2（lit 落点）**：`ls .dadao/tests/lit-output/` → `DADAO-CodeGen  DADAO-E2E  DADAO-MC`；
  `grep -rn "test-output" tests/ --include="lit.cfg.py"` → **无匹配（rc=1）**。
  **第 4 处 `tests/llvm/lit/tools/DADAO/lit.cfg.py` 按口径未改**（未引入新门控）：实测 `grep -rn "lit/tools" Makefile tools/ tests/` → **无匹配（rc=1）**，即该套件**不被任何门控/脚本运行**；`check-lit` 只跑 `tests/llvm/lit/MC/DADAO tests/llvm/lit/CodeGen/DADAO tests/e2e/lit`（`Makefile:383`），不含该套件。其 `test_exec_root` 仅见于注释、正文未设置，属**未被门控覆盖**的配置（详见遗留）。
- **验收 3（路径清零）**：`grep -rn "tests/llvm/codegen-e2e\|\.work/codegen-e2e-elf" Makefile tools/ .gitignore | grep -v __pycache__` → **无匹配（rc=1）**；默认 `work_dir` 已指向新落点。
- **验收 4（语义零改动）**：见「测试结果」——15/15、5/5、60/60 与改前**逐项相等**。
- **验收 5（门控 + 旧落点清零）**：`make check` EXIT=0；`make check-no-residue` EXIT=0；`git status --untracked-files=all` 不显示 `.dadao/` 下生成物；旧落点已不存在：
  ```
  $ ls -la tests/llvm/codegen-e2e   → No such file or directory
  $ ls -la .work/codegen-e2e-elf    → No such file or directory
  $ git status --porcelain -uall    → 仅 7 行（6 源文件 + 本任务书），无 ?? 残留
  ```
  **删除前后真实输出（F2）**：
  ```
  删除前：ls tests/llvm/codegen-e2e/ → 60 files；.work/codegen-e2e-elf/ → 16 files。
  清 .gitignore 旧规则后 git status --porcelain -uall 暴露 60 个未跟踪文件（67 行 = 7 改 + 60 ??），
  证实若不删目录会与「验收 7」冲突。
  $ rm -rf tests/llvm/codegen-e2e .work/codegen-e2e-elf   → rm EXIT=0
  删除后：git status --porcelain -uall → 7 行（无 ??）。
  ```
- **验收 6（一键证据脚本）**：`.work/evidence/INFRA-048t/run.sh` → 30/30 PASS，`RUN_EXIT=0`（内容见 `.work/log/infra/INFRA-048t-evidence-run.log`）。注入自检真实输出：
  ```
  PASS  injection applied (Makefile md5 changed)   actual=40e656e7ef84eea5a92118b063c31f1b rc=0
  PASS  injection => 落点 check FAIL               actual=FAIL                               rc=0
  PASS  restore md5 == pre-injection md5           expected=41cb2edd... actual=41cb2edd...    rc=0
  PASS  git snapshot unchanged by injection        expected=9a4c5aea... actual=9a4c5aea...    rc=0
  PASS  restore => 落点 check PASS                 actual=PASS                               rc=0
  ```
  注入还原纪律：`cp Makefile → /tmp/opencode/INFRA-048t/Makefile.preinject` + md5 对账（注入前 `41cb2edd475aaeb008722a16f038514f`，还原后一致）；改前快照 `git -c core.quotePath=false status --porcelain -uall` md5 = `dd5973f185738f84d6b099106cbcdcc6`，注入后还原一致（最终一轮，此时本任务书已完成区改动）。**未用 `git checkout/restore/stash`**。
- **验收 7（无残留）**：`git status --untracked-files=all` 仅本任务应有改动（`Makefile` + `.gitignore` + `tools/integ/run_{codegen,elf}_e2e.py` + 3 处 `lit.cfg.py` + 本任务书）；旧落点目录已不存在；无 `*_tmp*`/`*.orig`/`*.rej`（`make check-no-residue` PASS）。

**新发现/坑**：
1. **lit `test_exec_root` 现落 `.dadao/cross-toolchain/test-output/`（非任务书所述 `.work/build/llvm/`）**：INFRA-047t 把 tools_dir 默认改指 install 根后，`build_root = dirname(tools_dir) = .dadao/cross-toolchain`，故 047t 后 lit scratch 实际落 `.dadao/cross-toolchain/test-output/`。本次已统一迁至 `.dadao/tests/lit-output/<name>`（不再依赖 tools_dir）。
2. **`.gitignore` 旧规则与残留目录的耦合**：清 `tests/llvm/codegen-e2e/` 忽略规则会把该目录 60 个运行产物暴露为未跟踪（实测 67 行）。迁移旧忽略规则时**必须同时删残留目录**，否则「无残留」门控自相矛盾（F2 已按此处置）。
3. **lit 配置的 repo-root 定位可复用**：3 个门控 lit 配置原先仅在「未显式给出 tools_dir」分支内做 repo-root 定位 + `import paths`；本次将其提前为无条件（供工具定位与 `exec_root` 共用），不改变外部行为（这些配置恒在仓库内）。
4. **`git status --porcelain` 默认对非 ASCII 路径加引号（`core.quotePath`）**：本任务书文件名含中文，默认输出 `".tao/tasks/infra/INFRA-048t-\347...md"`（八进制转义 + 引号），会与证据脚本按原文匹配的白名单错配（自审时实测 `bad-count=1` 假阳性）。证据脚本改用 `git -c core.quotePath=false status --porcelain -uall` 后消除。**教训**：脚本比对 git 路径须先关 `core.quotePath`。
5. 建议沉淀：M5「生成物落点=`.dadao/tests/`」迁移的落点映射、「清 .gitignore 需同删残留目录」的耦合、以及「脚本比对 git 路径须 `core.quotePath=false`」，可并入 `.tao/knowledge/milestones.md` 或 lessons。

**遗留问题**：
1. **第 4 处 lit 配置 `tests/llvm/lit/tools/DADAO/lit.cfg.py` 按口径未改**（占位套件、当前无测试）：实测无任何门控/脚本引用（`grep -rn "lit/tools" Makefile tools/ tests/` 无匹配），`check-lit` 不含该套件，故**无门控验证**；其注释提及 `test_exec_root`（正文未设置），**仍指向构建树口径**，属未被门控覆盖的配置。按要求**未引入新门控**、未改动。
2. **迁移前的 lit scratch 旧目录残留**：`.dadao/cross-toolchain/test-output/`（INFRA-047t 后产生）与 `.work/build/llvm/test-output/`（更早产生）仍在。二者均在 gitignored 树内（`.dadao/`、`.work/`），**不在本任务「输出」列的删除范围内**（任务只列 `tests/llvm/codegen-e2e/` 与 `.work/codegen-e2e-elf`），故**未删**（避免越界）；后续可选清理。
3. `.work/evidence/INFRA-048t/run.sh` 为任务专用脚本，落 `.work/evidence/`（gitignored、不入库），符合规范。

## 审阅记录

#### 第 0 轮：下发前预检修订（architect，2026-10-07）
下发前预检（主会话实测）发现 3 项，任务书按最小原则修订如下（状态保持 `待开始`）：

- **F2（真冲突，必改）**：`.gitignore:34` = `tests/llvm/codegen-e2e/`（旧落点忽略规则），而 `tests/llvm/codegen-e2e/` **目录实际存在**（内含 `arith_*.bin/.o/.s/.prog.s` 等运行产物）。若只按「输出 4」清理该忽略规则，该目录将出现在 `git status --untracked-files=all`，与「验收 7：无残留」**自相矛盾**。
  ⇒ **改动**：「输出 4」增补**删除残留旧产物目录** `tests/llvm/codegen-e2e/` 与 `.work/codegen-e2e-elf`（若存在），并要求贴删除前后真实输出；明确**不得**以保留旧忽略规则回避（M4 不动 / M5 起生效口径）。「验收 5」「验收 7」增补「旧落点目录已不存在、`git status --porcelain -uall` 干净」。
- **F1（范围澄清，必写）**：第 4 处 lit 配置 `tests/llvm/lit/tools/DADAO/lit.cfg.py`（730 B，另含 `README.md`）不在 `check-lit` 套件列表（`Makefile` 的 `check-lit` 只跑 `MC/DADAO`、`CodeGen/DADAO`、`tests/e2e/lit`），其 `test_exec_root` 仅见于注释（第 7 行）。
  ⇒ **改动**：「输出 3」由「三处」改为**列明 4 处**，并定处置口径：engineer 先核实该套件是否被任何门控/脚本实际运行——被运行则**同改**；未运行则**按最小原则不改**但须在「完成区/遗留问题」**明确登记**（仍指构建树、未被门控覆盖），注明 `check-lit` 不含该套件故**无门控验证**；**不引入新门控**。
- **F3（命令口径，顺带）**：「验收 2」的 `grep -rn "test-output" tests/**/lit.cfg.py` 中 `**` 在非 globstar 下不递归 ⇒ 改为 `grep -rn "test-output" tests/ --include="lit.cfg.py"`。

**依据（下发前实测，read-only）**：`sed -n '34p' .gitignore` → `tests/llvm/codegen-e2e/`；`ls tests/llvm/codegen-e2e/` 有运行产物；`ls .work/codegen-e2e-elf` 存在；`find tests -name lit.cfg.py` → 4 处；`check-lit` 目标套件列表为 3 处。

#### 第 0 轮 architect 提交
- **档位**：正常提交（任务未开工，属规划修订）。
- **文件集对账**：显式 staging 仅本任务书一份；`git diff --cached --name-only` 应仅 `.tao/tasks/infra/INFRA-048t-生成物落点迁移.md`，与本次修订范围一致，无漏提/多提/越界。
- **提交信息**：`INFRA-048t 预检修订：旧落点目录清理 + 第 4 处 lit 配置口径`（commit SHA 见 git 历史，此处不写死）。

#### 第 1 轮 engineer 自审
（自主逐行审查改动源码 + 证据脚本，判决：无未修 finding）

**审查范围**：`Makefile`（2 处变量）、`tools/integ/run_{codegen,elf}_e2e.py`、3 个 `lit.cfg.py`、`.gitignore`、`.work/evidence/INFRA-048t/run.sh`。

**逐项审查要点与结论**：
- `Makefile`：`$(TEST_ARTIFACTS_DIR)` 由 `paths.py test_artifacts_dir` 解析为绝对 realpath，`rm -rf`/`--work-dir` 引用无空格/特殊字符，行为正确；目标依赖（`install-host`）未动。
- `run_*_e2e.py`：`_dadao_paths` 在模块级第 55/63 行已 import，`DEFAULT_WORK_DIR` 第 80/88 行使用，顺序正确；`_abspath` 对绝对路径原样透传；`--work-dir` 显式传入时仍优先（Makefile 恒传），语义零变化。
- `lit.cfg.py`：`import paths` 提到无条件（原先条件块内），对「仓库内套件」无行为差异；`test_exec_root = str(test_artifacts_dir()/"lit-output"/config.name)` 正确为字符串；`os.makedirs` 保留；工具定位逻辑（`tools_dir` 决策链）未变。
- `.gitignore`：仅删 1 行旧规则，其余保留。
- 证据脚本：每条断言均可达 FAIL（改回旧值/移走产物/计数不符 ⇒ 非零）；恒真断言不存在；注入段以 md5 判「注入生效」+ md5 判「还原成功」+ git 快照 md5 判「无副作用」；结尾 `rc=$?` 直取、无管道/无 `tee`。

**findings（自审提出并处置）**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 自审 F-a：`tests/e2e/lit/lit.cfg.py` 中 `here` 在 hoist 后于第 73 行被重复赋值（冗余，非错误） | ✅已修 | 删除 e2e 配置中重复的 `here = os.path.dirname(os.path.abspath(__file__))`（保留上方 hoist 定义与用途） | `python3 -m py_compile tests/e2e/lit/lit.cfg.py` OK；`make check-lit` EXIT=0，60/60；证据脚本重跑 30/30 PASS |
| 自审 F-b：证据脚本 `bad` 白名单用默认 `git status`，对含中文的本任务书路径被 `core.quotePath` 加引号转义 ⇒ 假阳性（实测 bad-count=1，脚本在完成区填写后会误报 FAIL） | ✅已修 | 脚本 4 处 `git status` 改为 `git -c core.quotePath=false status --porcelain -uall` | 任务书已含完成区改动后重跑脚本：`unexpected git-status entries expected=0 actual=0`；整轮 30/30 PASS、RUN_EXIT=0（`.work/log/infra/INFRA-048t-evidence-run.log`） |

**判决**：无未修 finding；`**状态**` → `待验收`。

#### 第 1 轮 reviewer 验收
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例**〔改 `run_elf_e2e.py` 的 `DEFAULT_WORK_DIR` 回旧落点 `.work/codegen-e2e-elf`〕+ 约束核验 + 判决）

##### A.1 证据脚本审核

逐条核 `.work/evidence/INFRA-048t/run.sh`（153 行）：

| 检查项 | 断言逻辑 | FAIL 路径可达？ | 恒真？ |
|--------|---------|---------------|--------|
| `Makefile CODEGEN_E2E_WORK` | `check_eq` 比较 `make` 展开值 vs `paths.py` 解析值 | ✅ 改 Makefile 变量值 → 不等 | ✗ |
| `Makefile CODEGEN_ELF_WORK` | 同上 | ✅ | ✗ |
| `run_codegen_e2e.DEFAULT_WORK_DIR` | `check_eq` 比较 Python import 值 vs expected | ✅ 改 py 文件 → 不等 | ✗ |
| `run_elf_e2e.DEFAULT_WORK_DIR` | 同上 | ✅ | ✗ |
| `lit.cfg.py refs to 'test-output'` | `check_eq` 比较 grep 计数 vs 0 | ✅ 在 lit.cfg.py 中写入 `test-output` → 非零 | ✗ |
| `3 gated lit.cfg.py use lit-output` | `check_eq` 比较 grep 计数 vs 3 | ✅ 删一个引用 → 计数变2 | ✗ |
| `old落点 refs` | `check_eq` grep 计数 vs 0 | ✅ 写入旧路径 → 非零 | ✗ |
| `residual dir` (×2) | `check_eq` 文件存在性 vs absent | ✅ 目录存在 → present | ✗ |
| `make test-codegen rc` | `check_eq` 退出码 vs 0 | ✅ 测试失败 → 非零 | ✗ |
| `test-codegen 15/15` | `check_eq` grep 计数 vs 1 | ✅ 测试部分失败 → 计数0 | ✗ |
| `test-codegen work dir` | `check_eq` grep 匹配新落点 | ✅ 旧落点不匹配 → 计数0 | ✗ |
| `codegen-e2e product count` | `check_ge` 产物数 >=15 | ✅ 产物不足 → <15 | ✗ |
| `test-elf` 系列(×4) | 同上模式 | ✅ | ✗ |
| `check-lit` 系列(×4) | 同上模式 | ✅ | ✗ |
| `make check` / `check-no-residue` | `check_eq` 退出码 vs 0 | ✅ | ✗ |
| `untracked entries` | `check_eq` grep 计数 vs 0 | ✅ 有未跟踪文件 → 非零 | ✗ |
| `unexpected git-status entries` | `check_eq` 白名单外条目 vs 0 | ✅ 多出文件 → 非零 | ✗ |
| 注入：md5 changed | `if` 比较注入前后 md5 | ✅ sed 未命中 → md5 相同 | ✗ |
| 注入：落点 check FAIL | `if validate_codegen_work` 返回 false | ✅ sed 改回旧值 → false | ✗ |
| 注入：restore md5 | `check_eq` 还原后 md5 vs 原始 | ✅ 还原失败 → 不等 | ✗ |
| 注入：git snapshot | `check_eq` 快照 md5 vs 原始 | ✅ 注入有副作用 → 不等 | ✗ |
| 注入：restore PASS | `if validate_codegen_work` 返回 true | ✅ 还原失败 → false | ✗ |

**注入段逻辑**：sed 把 `CODEGEN_E2E_WORK = $(TEST_ARTIFACTS_DIR)/codegen-e2e` 改为 `tests/llvm/codegen-e2e`（旧落点），`validate_codegen_work()` 用 `make --eval` 展开变量与 `EXP_CODEGEN`（`paths.py` 解析的新落点绝对路径）比对 → 不等 → FAIL。**无恒真断言、无「两支同一结果」**。

**还原纪律**：`cp Makefile → $TMP_DIR/Makefile.preinject`（注入前）+ `cp` 还原 + `md5sum` 对账（注入前 `41cb2edd475aaeb008722a16f038514f`，还原后一致）；git snapshot md5 对账（`3f5f516ce1a637582117554e4df72cf9` 一致）。**未用 `git checkout/restore/stash`**。

**结尾**：`exit 0` / `exit 1`（无 `tee`）。

**结论：脚本合格**，无需修订。

##### A.2 重跑证据脚本

```
$ bash .work/evidence/INFRA-048t/run.sh
== INFRA-048t evidence (repo /mnt/tao/DADAO-v5) ==
-- static落点 checks --
PASS  Makefile CODEGEN_E2E_WORK                          expected=/mnt/tao/DADAO-v5/.dadao/tests/codegen-e2e actual=/mnt/tao/DADAO-v5/.dadao/tests/codegen-e2e rc=0
PASS  Makefile CODEGEN_ELF_WORK                          expected=/mnt/tao/DADAO-v5/.dadao/tests/elf-e2e   actual=/mnt/tao/DADAO-v5/.dadao/tests/elf-e2e   rc=0
PASS  run_codegen_e2e.DEFAULT_WORK_DIR                   expected=/mnt/tao/DADAO-v5/.dadao/tests/codegen-e2e actual=/mnt/tao/DADAO-v5/.dadao/tests/codegen-e2e rc=0
PASS  run_elf_e2e.DEFAULT_WORK_DIR                       expected=/mnt/tao/DADAO-v5/.dadao/tests/elf-e2e   actual=/mnt/tao/DADAO-v5/.dadao/tests/elf-e2e   rc=0
PASS  lit.cfg.py refs to 'test-output'                   expected=0                                        actual=0                                        rc=0
PASS  3 gated lit.cfg.py use lit-output via paths.py     expected=3                                        actual=3                                        rc=0
PASS  old落点 refs in Makefile/tools/.gitignore        expected=0                                        actual=0                                        rc=0
PASS  residual dir tests/llvm/codegen-e2e                expected=absent                                   actual=absent                                   rc=0
PASS  residual dir .work/codegen-e2e-elf                 expected=absent                                   actual=absent                                   rc=0
-- gate runs (semantic zero-change) --
PASS  make test-codegen rc                               expected=0                                        actual=0                                        rc=0
PASS  test-codegen 15/15                                 expected=1                                        actual=1                                        rc=0
PASS  test-codegen work dir == new落点                 expected=1                                        actual=1                                        rc=0
PASS  codegen-e2e product count                          expected=>= 15                                    actual=60                                       rc=0
PASS  make test-elf rc                                   expected=0                                        actual=0                                        rc=0
PASS  test-elf 5/5                                       expected=1                                        actual=1                                        rc=0
PASS  test-elf work dir == new落点                     expected=1                                        actual=1                                        rc=0
PASS  elf-e2e product count                              expected=>= 5                                     actual=16                                       rc=0
PASS  make check-lit rc                                  expected=0                                        actual=0                                        rc=0
PASS  check-lit Total Discovered Tests 60                expected=1                                        actual=1                                        rc=0
PASS  check-lit Passed 60                                expected=1                                        actual=1                                        rc=0
PASS  lit-output/DADAO-MC exists                         expected=present                                  actual=present                                  rc=0
PASS  make check rc                                      expected=0                                        actual=0                                        rc=0
PASS  make check-no-residue rc                           expected=0                                        actual=0                                        rc=0
-- worktree state --
PASS  untracked (??) entries in git status               expected=0                                        actual=0                                        rc=0
PASS  unexpected git-status entries                      expected=0                                        actual=0                                        rc=0
-- injection self-check (Makefile CODEGEN_E2E_WORK -> old落点) --
PASS  injection applied (Makefile md5 changed)           expected=md5 differs                              actual=40e656e7ef84eea5a92118b063c31f1b         rc=0
PASS  injection => 落点 check FAIL                     expected=FAIL                                     actual=FAIL                                     rc=0
PASS  restore md5 == pre-injection md5                   expected=41cb2edd475aaeb008722a16f038514f         actual=41cb2edd475aaeb008722a16f038514f         rc=0
PASS  git snapshot unchanged by injection                expected=3f5f516ce1a637582117554e4df72cf9         actual=3f5f516ce1a637582117554e4df72cf9         rc=0
PASS  restore => 落点 check PASS                       expected=PASS                                     actual=PASS                                     rc=0
== summary: 0 check(s) failed ==
INFRA-048t evidence: PASS
EXIT=0
```

**30/30 PASS，EXIT=0**。与 engineer 完成区一致。

##### A.3 独立注入反例

**注入目标**：`tools/integ/run_elf_e2e.py` 第 88 行，`DEFAULT_WORK_DIR` 改回旧落点 `.work/codegen-e2e-elf`。

**鉴别力说明**：旧落点 `.work/codegen-e2e-elf/` 已被删除（验收确认 `absent`），若落点逻辑失效（仍指向旧路径），则 `test-elf` 跑时 `rm -rf` + 写入旧路径，产物不会出现在 `.dadao/tests/elf-e2e/`；同时 `grep` 旧落点检查会在 `run_elf_e2e.py` 中命中 → 非零。两条路径均可检测。

**注入前快照**：
```
$ git -c core.quotePath=false status --porcelain -uall | md5sum
3f5f516ce1a637582117554e4df72cf9  -
$ md5sum tools/integ/run_elf_e2e.py
585d9788daa47a7c558ab547ae1b826b  tools/integ/run_elf_e2e.py
$ cp tools/integ/run_elf_e2e.py /tmp/opencode/INFRA-048t-review/run_elf_e2e.py.preinject
```

**注入后验证**：
```
$ sed -i 's|DEFAULT_WORK_DIR = str(_dadao_paths.test_artifacts_dir() / "elf-e2e")|DEFAULT_WORK_DIR = ".work/codegen-e2e-elf"|' tools/integ/run_elf_e2e.py
$ grep -n 'DEFAULT_WORK_DIR' tools/integ/run_elf_e2e.py
88:DEFAULT_WORK_DIR = ".work/codegen-e2e-elf"
$ md5sum tools/integ/run_elf_e2e.py
a32b18506d918702845782817a959422  tools/integ/run_elf_e2e.py
$ git diff --name-only
tools/integ/run_elf_e2e.py
```

**注入后静态检查（FAIL 证据）**：
```
$ python3 -c "import sys; sys.path.insert(0,'tools/integ'); import run_elf_e2e as m; exp='/mnt/tao/DADAO-v5/.dadao/tests/elf-e2e'; actual=m.DEFAULT_WORK_DIR; print('FAIL' if exp!=actual else 'PASS')"
FAIL
$ grep -rn "\.work/codegen-e2e-elf" Makefile tools/ .gitignore 2>/dev/null | grep -v __pycache__
tools/integ/run_elf_e2e.py:88:DEFAULT_WORK_DIR = ".work/codegen-e2e-elf"
→ 非零（1 条匹配），old落点 refs check FAIL
```

**还原**：
```
$ cp /tmp/opencode/INFRA-048t-review/run_elf_e2e.py.preinject tools/integ/run_elf_e2e.py
$ md5sum tools/integ/run_elf_e2e.py
585d9788daa47a7c558ab547ae1b826b  tools/integ/run_elf_e2e.py
→ md5 与注入前一致 ✓
$ git -c core.quotePath=false status --porcelain -uall | md5sum
3f5f516ce1a637582117554e4df72cf9  -
→ git snapshot md5 与注入前一致 ✓
$ git diff tools/integ/run_elf_e2e.py
→ 无输出（文件已还原到 WIP 提交状态）
```

**还原后回绿验证**：
```
$ python3 -c "import sys; sys.path.insert(0,'tools/integ'); import run_elf_e2e as m; exp='/mnt/tao/DADAO-v5/.dadao/tests/elf-e2e'; actual=m.DEFAULT_WORK_DIR; print('PASS' if exp==actual else 'FAIL')"
PASS
$ grep -rn "\.work/codegen-e2e-elf" Makefile tools/ .gitignore 2>/dev/null | grep -v __pycache__ | wc -l
0
→ 回绿 ✓
```

**还原纪律**：全程 `cp` 备份 + `md5sum` 对账，**未用 `git checkout/restore/stash`**。

##### A.4 验收 1–7 逐条核验

| # | 检查项 | reviewer 独立验证 | 结果 |
|---|--------|------------------|------|
| 1 | 新落点产出 | 证据脚本 `make test-codegen` 15/15 + `ls .dadao/tests/codegen-e2e/` 60 文件；`make test-elf` 5/5 + `ls .dadao/tests/elf-e2e/` 16 文件 | ✅ |
| 2 | lit 落点 | `make check-lit` 60/60；`ls .dadao/tests/lit-output/` → `DADAO-CodeGen DADAO-E2E DADAO-MC`；`grep -rn "test-output" tests/ --include="lit.cfg.py"` → 无匹配 | ✅ |
| 3 | 路径清零 | `grep -rn "tests/llvm/codegen-e2e\|\.work/codegen-e2e-elf" Makefile tools/ .gitignore` → 无匹配 | ✅ |
| 4 | 语义零改动 | `test-codegen` 15/15、`test-elf` 5/5、`check-lit` 60/60，与改前逐项相等 | ✅ |
| 5 | 门控 | `make check` EXIT=0；`make check-no-residue` EXIT=0；旧落点目录 `tests/llvm/codegen-e2e/`、`.work/codegen-e2e-elf` 均不存在 | ✅ |
| 6 | 一键证据脚本 | 30/30 PASS、EXIT=0；注入自检 5 项全绿；还原纪律合规 | ✅ |
| 7 | 无残留 | `git status --porcelain -uall` 仅 1 行（本任务书 working tree 修改）；无 `??` 残留；`check-no-residue` PASS | ✅ |

**改动范围核验**：WIP 提交 `90cb1ff` 改动 8 文件（`git show --stat`）：`.gitignore`、任务书、`Makefile`、3 个 `lit.cfg.py`、`run_codegen_e2e.py`、`run_elf_e2e.py`。与任务书「输出」范围一致，**无越界**。

##### B.1 第 4 处 lit 配置

`tests/llvm/lit/tools/DADAO/lit.cfg.py`：占位套件，无测试文件，`test_exec_root` 仅见于注释（第 7 行），正文未设置。

**独立核验**：
- `grep -rn 'lit/tools' Makefile tools/ tests/` → **0 匹配**（无门控/脚本引用该目录）
- `check-lit` 目标（`Makefile:383`）：`$(LIT_BIN) tests/llvm/lit/MC/DADAO tests/llvm/lit/CodeGen/DADAO tests/e2e/lit -v`，**不含 `tests/llvm/lit/tools/DADAO`**

**结论**：理由成立。该套件**未被任何门控/脚本运行**，按最小原则不改是正确处置。已在「遗留问题」登记。✅

##### B.2 旧 lit scratch 目录残留

`.dadao/cross-toolchain/test-output/` 和 `.work/build/llvm/test-output/` 均存在，内含 `DADAO-CodeGen`、`DADAO-E2E` 等子目录。

**判定**：
- 两者均在 gitignored 树内（`.dadao/`、`.work/`），不暴露为未跟踪文件
- 任务书「输出」仅列 `tests/llvm/codegen-e2e/` 与 `.work/codegen-e2e-elf` 为删除目标，**不含这两个目录**
- 工程师处置（不删、登记为遗留）符合**最小原则**——不越界删任务书未列目录

**结论**：处置可接受。属迁移历史残留，可后续清理，不影响本任务验收。✅

##### C 任务书结构

- `## 审阅记录` 仅出现 1 次（第 130 行），**无重复段**；主会话去重操作正确
- 子段完整：第 0 轮预检修订（132）、第 0 轮 architect 提交（143）、第 1 轮 engineer 自审（148）、第 1 轮 reviewer 验收（169）、第 1 轮 architect 提交 WIP（173）
- **无真实记录被删**（去重只删副本，原始记录保留在130–167）

完成区计数笔误：自述「7 项（6 源文件 + 本任务书）」，实际改动源文件为 **7**（`Makefile` + `run_codegen_e2e.py` + `run_elf_e2e.py` + 3 个 `lit.cfg.py` + `.gitignore`）+ 本任务书 = **8** 项。清单本身完整无缺，仅计数表述错误。此笔误已在 architect WIP 提交记录中登记。**如实指出，未改写完成区**。

##### 判决

**Accepted**

全部 7 项验收标准通过（证据脚本30/30 PASS、独立注入 FAIL→还原→回绿、语义零改动 15/15+5/5+60/60、门控全绿、无残留）。B/C 结论均正面。完成区计数笔误已如实记录，不影响验收。


#### 第 1 轮 architect 提交（WIP）
- **档位**：`WIP:`（reviewer 尚未验收；文件 `**状态**` 为 `待验收`）。
- **文件集审核（只核"提交哪些文件是否合适"，不核内容）**：
  - 显式 staging（逐个路径，**未用** `git add -A`），实提 **8** 份；`git diff --cached --name-only` 与完成区「修改文件」声明**逐条对账**：
    - 命中声明：`Makefile`、`tools/integ/run_codegen_e2e.py`、`tools/integ/run_elf_e2e.py`、`tests/llvm/lit/MC/DADAO/lit.cfg.py`、`tests/llvm/lit/CodeGen/DADAO/lit.cfg.py`、`tests/e2e/lit/lit.cfg.py`、`.gitignore`、本任务书 —— **无漏提、无多提、无越界**。
  - **删除项**（`tests/llvm/codegen-e2e/`、`.work/codegen-e2e-elf/`）：实测两目录**已不存在**，且 `git ls-files` 从无跟踪（`.work/` 由 `.gitignore:2` 忽略）⇒ **未出现在 staged 集**（`git diff --cached --name-only` 无 `D` 项），符合"gitignored 运行产物不入库"。
  - `git status --porcelain -uall` 提交前仅 8 行 `M `，无未跟踪残留。
  - **计数表述笔误（登记备查，非文件集不一致）**：完成区「修改文件」自述"7 项（6 源文件 + 本任务书）"，实际改动源文件为 **7**（含 `.gitignore`）+ 本任务书 = **8**；清单本身完整无缺，不影响提交范围。
  - **文件内容结构异常（登记，交 reviewer / 主会话处置）**：本任务书 `## 审阅记录` 段出现**重复**——第 130 行与第 172 行各有一处 `## 审阅记录`，第 172–194 行为第 130–150 行同段落的重复（原模板段未删除）。属 engineer 落盘时的内容缺陷，**超出 architect 提交岗"只核文件集"的授权，未改动**；提请注意 reviewer 验收/主会话收尾时处置。
- **提交信息**：`WIP: INFRA-048t 生成物落点迁移（待 reviewer 验收）`（commit SHA 见 git 历史，此处不写死）。

#### 第 1 轮 architect 提交（正常）
- **档位**：**正常提交**（reviewer 判 `Accepted`；**非** `WIP:`）。
- **文件集审核（只核"提交哪些文件是否合适"，不核内容）**：显式 staging（逐个路径，**未用** `git add -A`）：
  - `.tao/tasks/infra/INFRA-048t-生成物落点迁移.md`（本任务书：reviewer 验收记录 + 主会话去重后的 `## 审阅记录`）。
  - `.tao/knowledge/changelog.md`、`.tao/knowledge/milestones.md`、`.tao/knowledge/MEMORY.md`（本任务知识沉淀）。
  - `.tao/knowledge/feedback_002-生成物落点迁移与残留目录耦合.md`（本任务新增操作规范）。
  - `git diff --cached --name-only` 与本次收尾范围一致，**无漏提、无多提、无越界**（源文件改动已于 WIP 提交）。
- **与完成区「修改文件」对账（跨提交）**：完成区声明 7 项源文件（`Makefile` + `tools/integ/run_{codegen,elf}_e2e.py` + 3 处 `lit.cfg.py` + `.gitignore`）+ 本任务书；其中源文件已于 WIP 提交 `90cb1ff` 落地；本次提交含任务书（reviewer 记录）+ 本任务知识沉淀。**两次提交并集 = 完成区声明范围**，无遗漏、无越界。
- **提交信息**：`INFRA-048t 生成物落点迁移（reviewer Accepted）`（commit SHA 见 git 历史，此处不写死）。

#### 主会话统一验收报告（`/complete`，2026-10-07）

- **reviewer**：`Accepted`。证据脚本重跑 **30/30 PASS, EXIT=0**；**独立注入**（自行改 `tools/integ/run_elf_e2e.py` 的 `DEFAULT_WORK_DIR` 回旧落点 `.work/codegen-e2e-elf`）⇒ 断言 **FAIL**（静态比对不符 + 旧落点 grep 命中）⇒ `cp`+`md5` 还原 ⇒ **回绿**；**鉴别力成立**（旧落点目录已删，若落点逻辑失效必然无产物）。判据：验收 1–7 全过；语义零改动（15/15、5/5、60/60 逐项相等）；门控 `make check`/`check-no-residue` **EXIT=0**。
- **architect 交叉复核**：**维持 `Accepted`**（无过严/过松/遗漏）。独立复现 reviewer 注入（注入 md5 `a32b1850`，与 reviewer 记录**一致可复现**；还原后文件 md5 `585d9788`、git 快照 md5 `3f5f516c` 逐字一致）。**M5 落点口径扫描：无漏网**（`Makefile` 的 `$(TEST_ARTIFACTS_DIR)` 用途全部在新根；其余写目录者为 `/tmp/opencode/<任务ID>/` 临时约定）。
- **共识**：落点迁移在 `Makefile`/两个 e2e runner/3 处 `lit.cfg.py`/`.gitignore` 完成；**旧产物目录同删**（`tests/llvm/codegen-e2e/`、`.work/codegen-e2e-elf`）；未越界；`.work/log`、`.work/evidence` 未动。
- **分歧/澄清**：① **完成区计数笔误**——自述「7 项（6 源文件 + 本任务书）」，实际 **8 项（7 源文件 + 本任务书）**；清单本身完整、不影响验收（按纪律**不改写**完成区，在此如实记录）；② 第 4 处 lit 配置 `tests/llvm/lit/tools/DADAO/lit.cfg.py` **按最小原则未改**（`grep "lit/tools"` 全仓 0 引用、`check-lit` 不含该套件）——**理由经两方独立验证成立**。
- **补充发现（非阻塞，建议登记/另立任务）**：ⓐ 旧 lit scratch 目录 `.dadao/cross-toolchain/test-output/`、`.work/build/llvm/test-output/` 仍在（gitignored 树内、不在本任务删除范围）；ⓑ `tests/scripts/verify_harness_dump.py` 硬编码 `/tmp/opencode/QEMU-014t/`（持久脚本绑定任务临时落点）；ⓒ `tests/scripts/gen_trampoline.py` 再跑会写源码树（其产物 `trampoline.bin` 已入库、属**构建输入**，**不违** M5 口径）。
- **收尾检查**：源文件改动的门控由 reviewer 在 WIP 提交上重跑（`EXIT=0`）；本次台账/任务书为**纯文档**（豁免 `make check`）；`git status --porcelain -uall` 干净；证据留 `.work/evidence/INFRA-048t/`、`.work/log/infra/`（非 `/tmp`）。
- **最终判决**：**`Accepted`** ⇒ 任务书 `**状态**` 置 `已验证`。
