# QEMU-077t: reserved cfx 注释 `7-14` → `6-14`（与 `DADAO_CFX_IS_RESERVED` 一致）

**模块**：qemu
**项目里程碑**：M10 后（维护）
**依赖**：无（与 `INFRA-115t` 同改 `milestones.md` ⇒ 两者串行，不得并行）
**状态**：待开始

## 执行环境
**执行环境**：本地（组件源树 `.work/source/qemu` 已就位：HEAD = base+1、`git status` 干净；**不重建** qemu，注释不改行为）

## 问题根源

注释与宏口径不一致，**口径真源**是宏：

- 宏：`.work/source/qemu/target/dadao/cpu.h:167` / `components/qemu/patches/target/dadao/cpu.h.patch:173`
  → `#define DADAO_CFX_IS_RESERVED(h) (((h) >= 6 && (h) <= 14) || ...)` ⇒ **6–14**。
- 注释（现场 **3 处**，全写 `7-14`）：
  - `.work/source/qemu/target/dadao/helper.c:636`：`*   reserved cfx (7-14, 19-61) plain ld/st -> CFXMEM (ADR-0039 Step 1-c).`
  - `.work/source/qemu/target/dadao/helper.c:842`：`*  - reserved cfxha (7-14, 19-61) plain ld/st => CFXMEM (ADR-0039`
  - `.work/source/qemu/target/dadao/cpu.h:112`：`* Reserved cfx (7-14, 19-61) plain ld/st are also CFXMEM (ADR-0039 Step 1-c).`
- 补丁侧同 3 处：`components/qemu/patches/target/dadao/helper.c.patch:642,848`、`cpu.h.patch:118`。
- **范围追加（已披露）**：下发清单只列 `helper.c` 两处；`cpu.h` 1 处**同一笔误**，若不改则错误口径仍在盘上 ⇒ 本任务一并修（3 处）。其余仓内文档/向量已是 `6-14`（`tests/arch/umon/m5_perm_reserved_illi.s:5`、`tests/inst/atomics/atomics-fence.yaml:5`），**不改**。

## 接口规范

### 输入
上列 3 行注释；替换规则：该行内 `7-14` → `6-14`，**其余字符逐字不变**（含缩进、`19-61`、句末标点）。

### 输出（改动顺序固定）
1. 改动前先自检 E1：`python3 tools/infra/check_patch_tree.py --source-state`（期望 qemu `OK ... clean=True count=1`），**记下当时 `git -C .work/source/qemu rev-parse HEAD`（旧 HEAD）**。
2. 在 `.work/source/qemu` 内改上述 3 行。
3. **收敛为 base+1 且干净**（`docs/Process-01` §6.4）：`git -C .work/source/qemu reset --soft HEAD~` → `git add -A` → `git commit`（或等价 `commit --amend`），之后 `git status --porcelain` 为空、`rev-list --count <base>..HEAD` = 1。
4. **重新导出补丁**（**禁手工编辑补丁**，`docs/Process-01` §6.1.1）：
   `python3 tools/infra/make_patch.py qemu` ⇒ 只应改写 `patches/target/dadao/helper.c.patch` 与 `cpu.h.patch`（§6.2 幂等：内容未变者不重写）。
5. 仓库内 `git status --porcelain -uall` 只应出现上两份补丁 + 本任务书（+ `milestones.md`）。

### 约束
- 不改任何逻辑、宏、字面量、期望值；**只改注释**（diff 里不得出现非 `*` 注释行）。
- 不改 `tests/`、`spec/`、`contracts/`、`.tao/contracts/`、`.tao/adr/`、其它组件。
- **不重建** qemu（注释不改变行为）；若某门控现场要求 rebuild，则**记录门控名与要求**并在完成区说明处置，不静默跳步。
- 还原纪律：任何注入/临时改动一律 `cp` 备份 + `md5sum` 对账；**禁** `git checkout`/`restore`/`stash`/`show <commit>:<path>`。
- 临时目录 `/tmp/opencode/QEMU-077t/`；仓库内不留临时/探针文件。

## 验收标准

1. **零残留（源 + 补丁）**：`grep -rn '7-14' components/qemu/patches .work/source/qemu/target/dadao` ⇒ **0 行**（rc=1）。
2. **替换到位**：`grep -c '6-14' .work/source/qemu/target/dadao/helper.c` = **2**、`.../cpu.h` = **1**、`components/qemu/patches/target/dadao/helper.c.patch` = **2**、`.../cpu.h.patch` = **1**。
3. **补丁树**：`make check-patch-tree` ⇒ **rc=0**（断言⑥/⑨：补丁可重建源树、补丁 == `git diff <base> HEAD`）。
4. **源树状态**：`make check-source-state` ⇒ **rc=0**，qemu 行 `OK ... clean=True count=1`。
5. **行为不变证据**：`git -C .work/source/qemu diff <旧HEAD> <新HEAD>` ⇒ 仅 2 文件 3 行，**全部为 `*` 开头的注释行**（贴 diff）；`git -C .work/source/qemu diff <base> HEAD --stat` 与改动前同文件集（helper.c/cpu.h）。
6. **L1**：`make check` ⇒ **rc=0**（含 `check-qemu-forms` 扫 `helper.c.patch`）。若 `gate.lock` 被占用，按 `docs/Process-07` 说明；rc=75 **不作**通过证据。
7. **反例可达 FAIL（cp + md5，禁 git 还原）**：
   - `cp` 备份 `components/qemu/patches/target/dadao/helper.c.patch` + `md5sum`；
   - 把其中**一处** `6-14` 改回 `7-14`（只改文本，`@@` 行数不变）⇒ `make check-patch-tree` **rc≠0** 且输出点名 `helper.c`（断言⑥ 或 ⑨）；
   - `cp` 还原 ⇒ `md5sum` 与备份一致 ⇒ `make check-patch-tree` 复跑 **rc=0**。
8. **体例**：`make check-milestones-fresh` ⇒ rc=0；`make check-tasks` ⇒ rc=0；本任务书完成区 **≤30 行**。
9. **证据脚本**：`.work/evidence/QEMU-077t/` 下一键脚本跑通（打印 `checks=N failures=0` 并把自身 rc 落盘），每条断言有**可达 FAIL** 路径。

## 文件范围

- 允许：`.work/source/qemu/target/dadao/{helper.c,cpu.h}`（组件工作树，非 v5 跟踪）、`components/qemu/patches/target/dadao/{helper.c.patch,cpu.h.patch}`、`.tao/tasks/qemu/QEMU-077t-*.md`、`.tao/knowledge/milestones.md`、`.work/evidence/QEMU-077t/`。
- 禁止：其余一切（尤其 `tests/`、`spec/`、`contracts/`、`.tao/adr/`、`components/qemu/series`、其它补丁）。

## 下发前预检（5 项，均为现场核）

1. **任务书内部一致**：3 处注释、2 份补丁、验收 1–9 与文件范围一一对应；编号 `QEMU-077` 未被占用（`.tao/tasks/qemu/` 空、`.tao/archive/**` 最大 `QEMU-076t`）。
2. **验证前置可用**：`.work/source/qemu` 在位、`git status --porcelain` 空、`rev-list --count` = 1；`tools/infra/make_patch.py` 可跑；`make check-patch-tree` / `check-source-state` / `check-qemu-forms` 均在 L1 列表内。
3. **验收逐条可跑性**：1/2/3/4/5/6/8/9 **现在可跑**；`make check` 受 `gate.lock` 串行 ⇒ 若被夜跑占用则取 1–5 证据 + 锁空后补跑（rc=75 不算通过）。
4. **与 `contracts/`、`tests/inst/` 一致**：二者零改动；`6–14` 口径与 `tests/` 现有 `6-14` 文本一致。
5. **拟改文件 × `spec/` 清单**：全部不在 `spec/` ⇒ **无命中、无 BLOCKED**。

## 风险

- **R1 手工编辑补丁**（禁止）⇒ 必须走 `make_patch.py`；若导出后 `check-patch-tree` 红，按 §6.4 收敛后重导，**不要**直接改 `.patch`。
- **R2 源树变脏**：改完未提交即运行 `--source-state` 必红（断言⑦）⇒ 先收敛再自检。
- **R3 误触发重建**：本任务不跑 `build-qemu`；若发现门控要求重建（预计无），按「约束」记录并说明。
- **R4 `milestones.md` 与 `INFRA-115t` 冲突** ⇒ 两任务串行下发。

## 用户授权原话

> 「**QEMU-077t：注释 `7-14` → `6-14`** … 范围只改注释；导出补丁、`check-patch-tree`/`check-source-state`；不重建二进制（注释不改变行为，若现场要求 rebuild 则说明）。」
> （2026-11-01 11:2x，主会话下发；`cpu.h` 第 3 处为本任务发现的同笔误，已按最小范围追加。）

## 完成区

**测试结果**：（待填写）
**修改文件**：（待填写）
**验收结果**：（待填写）
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

（待填）

#### 第 1 轮 reviewer 验收

（待填）
