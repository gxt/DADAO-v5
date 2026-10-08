# QEMU-053t: RAM@0 step2（`ISS-165`）+ 探针迁移（`ISS-169`）

**模块**：qemu
**项目里程碑**：M6
**依赖**：`QEMU-052t`（load_elf）、`TESTCASES-034t`（exit-port→`SYS_EXIT` 迁移，已验）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `.tao/knowledge/issues.yaml`：`ISS-165`（C1 step2：旧向量/harness/`crt0`/e2e 迁到 `0` + 删旧 RAM 段 `0xffff_0000_0000` + 收紧 `check-interface` 断言）、`ISS-169`（6 个 M1/M2 手写探针 `006t/008t/009t/010t/012t/013t` 仍以 exit-port 退出）。
  - `.tao/adr/adr-0004-test-machine.md`（`R3`/`D15`：RAM@0 = `0x0000_0000_0000` 16 MiB / cfxha 0；旧 RAM 段过渡保留）、`.tao/adr/adr-0020-see-semihosting.md`。
  - `components/qemu/patches/{hw/dadao/**,target/dadao/**}`（step1 双映射现状）。
  - `tools/integ/check_interface_alignment.py`；`tests/vectors/**`（`mem-*`/`ctrl-*` 以 EA=0 作 unmapped 的用例）；`tools/qemu/*.py` 探针；`tests/e2e/*`；`tests/scripts/{codegen_crt0.s,build_test_binary.py,run_qemu_test.py}`。
- **输出**：
  1. **RAM@0 收口（`ISS-165`）**：旧向量/harness/`crt0`/e2e **迁到 `0`**（EA=0 语义由「unmapped」改为「合法 RAM」）；**删旧 RAM 段**（`0xffff_0000_0000`）；**收紧** `check-interface` 断言（RAM@0 为唯一 RAM 段）。
  2. **`ISS-169`**：6 个 M1/M2 手写探针（`006t`/`008t`/`009t`/`010t`/`012t`/`013t`）退出通道改写为 **`SYS_EXIT`**（**含按新字长重算手算分支偏移**）；相应移除 `check_interface_alignment.py` 的注释例外。
  3. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - **门控保持全绿**：迁移与断言收紧须在同一变更内完成，不得留「门控暂时红」的中间态。
  - **`spec/` 交集为空**。
  - 与 `QEMU-052t` **同改 `components/qemu/patches` ⇒ 串行**。
  - `ISS-169` 的 6 探针改动须**保持其被测量语义不变**（仅换退出通道 + 重算偏移），不做无关重构。

## 硬约束

- **临时目录** `/tmp/opencode/QEMU-053t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/QEMU-053t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **重建成本申报**：改 `components/qemu/patches/**` ⇒ 开工前写明「重建 QEMU（增量），预计 N 分钟」；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/qemu/QEMU-053t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **旧 RAM 段已删**：`grep`/代码证据证明 `0xffff_0000_0000` 旧 RAM 段**不再映射**；机器模型只剩 RAM@0（+ boot ROM + exit port 视裁定）。
2. **迁移完成**：旧向量/harness/`crt0`/e2e 迁到 `0`；EA=0 语义已更新（给逐类真实输出）。
3. **`check-interface` 收紧**：断言反映「RAM@0 唯一 RAM 段」（给真实输出）。
4. **`ISS-169`（6 探针）**：`006t/008t/009t/010t/012t/013t` 退出通道 == `SYS_EXIT`（`grep` 证据 + 探针重跑真实输出）；**手算分支偏移已按新字长重算且探针通过**。
5. **不回归**：`make check`/`make check-interface`/`make check-qemu-semantics`/`check-patch-tree` EXIT=0（通过数与改前**逐项相等**，或按门控现场统计**不下降**）。
6. **`spec/` 交集为空**：`git diff --name-only | grep -E '^spec/'` → 无输出。
7. **一键证据脚本**：`.work/evidence/QEMU-053t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检，给真实输出与退出码。
8. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

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
