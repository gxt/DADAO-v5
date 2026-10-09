# INFRA-053t: 修复 `install-host` 幂等性（`cp` 间歇 `File exists`）

**模块**：infra
**项目里程碑**：M6
**依赖**：无
**状态**：待开始

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
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
