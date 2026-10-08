# QEMU-052t: 改走 `load_elf()`（钉子②）

**模块**：qemu
**项目里程碑**：M6
**依赖**：无（M5 已验证态）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `components/qemu/patches/hw/dadao/**`（现自建 `dadao_load_regions[]` 白名单路径，以**实测**为准）。
  - QEMU 上游 `hw/core/loader.c`（`load_elf()` 标准 API；复用、不重写）。
  - `.tao/adr/adr-0004-test-machine.md`（加载/入口模型）、`.tao/adr/adr-0020-see-semihosting.md`（`-bios` bootrom 与 M4 ELF 路径**并存**）。
  - `.tao/knowledge/issues.yaml`：`ISS-168`（`-bios`+ELF 组合加载/ELF loader 扩展/组合 ADR）。
  - `spec/Process-01-组件补丁组织与构建编排.md`。
- **输出**：
  1. `components/qemu/patches/hw/dadao/**`：ELF 直载**改走 `load_elf()`**；**取消**自建 `dadao_load_regions[]` 白名单。
  2. **验证项**（作为验收）：多段 `PT_LOAD` / `RELA` / `e_entry` / 栈初始化由 `load_elf()` 提供 ⇒ 逐项验证；**`-bios` + ELF 组合不需要**。
  3. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - **复用上游标准 API**（不重写 loader）；不改变外部加载接口契约（用户仍经 `-kernel <elf>`）。
  - **`spec/` 交集为空**。
  - 与 `QEMU-053t` **同改 `components/qemu/patches` ⇒ 串行**。

## 硬约束

- **临时目录** `/tmp/opencode/QEMU-052t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/QEMU-052t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **重建成本申报**：改 `components/qemu/patches/**` ⇒ 开工前写明「重建 QEMU（增量），预计 N 分钟」；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/qemu/QEMU-052t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **走 `load_elf()`**：`grep`/代码证据证明 ELF 直载经 `load_elf()`；**自建白名单已移除**（`grep dadao_load_regions` 无残留，或给正当理由）。
2. **验证项逐条**：多段 `PT_LOAD`（≥2 段）/`RELA`/`e_entry`/栈初始化各 ≥1 例（给真实输出）。
3. **接口不变**：用户经 `-kernel <elf>` 加载的行为与改前**等价**（给真实输出）。
4. **不回归**：`make check`/`check-interface`/`check-patch-tree` EXIT=0（通过数与改前**逐项相等**）。
5. **`spec/` 交集为空**：`git diff --name-only | grep -E '^spec/'` → 无输出。
6. **一键证据脚本**：`.work/evidence/QEMU-052t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检，给真实输出与退出码。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

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
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
