# QEMU-077t: reserved cfx 注释 `7-14` → `6-14`（与 `DADAO_CFX_IS_RESERVED` 一致）

**模块**：qemu
**项目里程碑**：M10 后（维护）
**依赖**：无（与 `INFRA-115t` 同改 `milestones.md` ⇒ 两者串行，不得并行）
**状态**：已验证

## 执行环境
**执行环境**：本地（QEMU 组件源树已就位：HEAD = base+1、`git status` 干净；**不重建** qemu，注释不改行为）

## 问题根源

注释与宏口径不一致，**口径真源**是宏：

- 宏：`QEMU 组件源树中的 target/dadao/cpu.h:167` / `components/qemu/patches/target/dadao/cpu.h.patch:173`
  → `#define DADAO_CFX_IS_RESERVED(h) (((h) >= 6 && (h) <= 14) || ...)` ⇒ **6–14**。
- 注释（现场 **3 处**，全写 `7-14`）：
  - `QEMU 组件源树中的 target/dadao/helper.c:636`：`*   reserved cfx (7-14, 19-61) plain ld/st -> CFXMEM (ADR-0039 Step 1-c).`
  - `QEMU 组件源树中的 target/dadao/helper.c:842`：`*  - reserved cfxha (7-14, 19-61) plain ld/st => CFXMEM (ADR-0039`
  - `QEMU 组件源树中的 target/dadao/cpu.h:112`：`* Reserved cfx (7-14, 19-61) plain ld/st are also CFXMEM (ADR-0039 Step 1-c).`
- 补丁侧同 3 处：`components/qemu/patches/target/dadao/helper.c.patch:642,848`、`cpu.h.patch:118`。
- **范围追加（已披露）**：下发清单只列 `helper.c` 两处；`cpu.h` 1 处**同一笔误**，若不改则错误口径仍在盘上 ⇒ 本任务一并修（3 处）。其余仓内文档/向量已是 `6-14`（`tests/arch/umon/m5_perm_reserved_illi.s:5`、`tests/inst/atomics/atomics-fence.yaml:5`），**不改**。

## 接口规范

### 输入
上列 3 行注释；替换规则：该行内 `7-14` → `6-14`，**其余字符逐字不变**（含缩进、`19-61`、句末标点）。

### 输出（改动顺序固定）
1. 改动前先自检 E1：`python3 tools/infra/check_patch_tree.py --source-state`（期望 qemu `OK ... clean=True count=1`），**记下当时 `git -C <组件源树> rev-parse HEAD`（旧 HEAD）**。
2. 在 `QEMU 组件源树` 内改上述 3 行。
3. **收敛为 base+1 且干净**（`docs/Process-01` §6.4）：`git -C <组件源树> reset --soft HEAD~` → `git add -A` → `git commit`（或等价 `commit --amend`），之后 `git status --porcelain` 为空、`rev-list --count <base>..HEAD` = 1。
4. **重新导出补丁**（**禁手工编辑补丁**，`docs/Process-01` §6.1.1）：
   `python3 tools/infra/make_patch.py qemu` ⇒ 只应改写 `patches/target/dadao/helper.c.patch` 与 `cpu.h.patch`（§6.2 幂等：内容未变者不重写）。
5. 仓库内 `git status --porcelain -uall` 只应出现上两份补丁 + 本任务书（+ `milestones.md`）。

### 约束
- 不改任何逻辑、宏、字面量、期望值；**只改注释**（diff 里不得出现非 `*` 注释行）。
- 不改 `tests/`、`spec/`、`contracts/`、`.tao/contracts/`、`.tao/adr/`、其它组件。
- **不重建** qemu（注释不改变行为）；若某门控现场要求 rebuild，则**记录门控名与要求**并在完成区说明处置，不静默跳步。
- 还原纪律：任何注入/临时改动一律 `cp` 备份 + `md5sum` 对账；**禁** `git checkout`/`restore`/`stash`/`show <commit>:<path>`。
- 临时目录 `运行期临时目录`；仓库内不留临时/探针文件。

## 验收标准

1. **零残留（源 + 补丁）**：`grep -rn '7-14' components/qemu/patches QEMU 组件源树中的 target/dadao` ⇒ **0 行**（rc=1）。
2. **替换到位**：`grep -c '6-14' QEMU 组件源树中的 target/dadao/helper.c` = **2**、`.../cpu.h` = **1**、`components/qemu/patches/target/dadao/helper.c.patch` = **2**、`.../cpu.h.patch` = **1**。

   > **口径更正（architect 2026-11-01 裁定）**：`cpu.h` / `cpu.h.patch` 在 base 已各含 1 行 `6-14`（`cpu.h:162` / `cpu.h.patch:168`，`cfxha either is reserved`），本任务未触碰 ⇒ 绝对计数现场为 **2**。**权威判据 = diff 增量**：`a5fc0fc..1e5bcaa` 新增 `6-14` 3 行、删除 `7-14` 3 行，且每文件各 +1。
3. **补丁树**：`make check-patch-tree` ⇒ **rc=0**（断言⑥/⑨：补丁可重建源树、补丁 == `git diff <base> HEAD`）。
4. **源树状态**：`make check-source-state` ⇒ **rc=0**，qemu 行 `OK ... clean=True count=1`。
5. **行为不变证据**：`git -C <组件源树> diff <旧HEAD> <新HEAD>` ⇒ 仅 2 文件 3 行，**全部为 `*` 开头的注释行**（贴 diff）；`git -C <组件源树> diff <base> HEAD --stat` 与改动前同文件集（helper.c/cpu.h）。
6. **L1**：`make check` ⇒ **rc=0**（含 `check-qemu-forms` 扫 `helper.c.patch`）。若 `gate.lock` 被占用，按 `docs/Process-07` 说明；rc=75 **不作**通过证据。
7. **反例可达 FAIL（cp + md5，禁 git 还原）**：
   - `cp` 备份 `components/qemu/patches/target/dadao/helper.c.patch` + `md5sum`；
   - 把其中**一处** `6-14` 改回 `7-14`（只改文本，`@@` 行数不变）⇒ `make check-patch-tree` **rc≠0** 且输出点名 `helper.c`（断言⑥ 或 ⑨）；
   - `cp` 还原 ⇒ `md5sum` 与备份一致 ⇒ `make check-patch-tree` 复跑 **rc=0**。
8. **体例**：`make check-milestones-fresh` ⇒ rc=0；`make check-tasks` ⇒ rc=0；本任务书完成区 **≤30 行**。
9. **证据脚本**：`运行期证据（已清理，未归档）` 下一键脚本跑通（打印 `checks=N failures=0` 并把自身 rc 落盘），每条断言有**可达 FAIL** 路径。

## 文件范围

- 允许：`QEMU 组件源树中的 target/dadao/{helper.c,cpu.h}`（组件工作树，非 v5 跟踪）、`components/qemu/patches/target/dadao/{helper.c.patch,cpu.h.patch}`、`.tao/tasks/qemu/QEMU-077t-*.md`、`.tao/knowledge/milestones.md`、`运行期证据（已清理，未归档）`。
- 禁止：其余一切（尤其 `tests/`、`spec/`、`contracts/`、`.tao/adr/`、`components/qemu/series`、其它补丁）。

## 下发前预检（5 项，均为现场核）

1. **任务书内部一致**：3 处注释、2 份补丁、验收 1–9 与文件范围一一对应；编号 `QEMU-077` 未被占用（`.tao/tasks/qemu/` 空、`.tao/archive/**` 最大 `QEMU-076t`）。
2. **验证前置可用**：`QEMU 组件源树` 在位、`git status --porcelain` 空、`rev-list --count` = 1；`tools/infra/make_patch.py` 可跑；`make check-patch-tree` / `check-source-state` / `check-qemu-forms` 均在 L1 列表内。
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

**测试结果**：验收 1–5、8–9 通过；验收 6（`make check`）**rc=2 且原因在本任务之外**：唯一红项 `check-knowledge-refs` 的 2 条悬空引用均在 `.tao/tasks/infra/INFRA-115t-tests文档小项收口.md:77,81`（该册 `待开始`、不属本任务文件范围）；本任务自身的 2 条悬空引用（`运行期证据（已清理，未归档）`）已随证据目录创建转绿。`make -k check` 跑完全部 L1，仅该 1 个子目标红（`grep -c 'Error 1'` = 1）。

**修改文件**：`QEMU 组件源树中的 target/dadao/{helper.c:636,842, cpu.h:112}`（组件工作树，非 v5 跟踪）；`components/qemu/patches/target/dadao/{helper.c.patch,cpu.h.patch}`（`make_patch.py qemu` 重导出：`2 written, 61 unchanged`）；`运行期证据（已清理，未归档）`（新）；`运行期日志（已清理，未归档）`；本任务书；`.tao/knowledge/milestones.md`。

**验收结果**（真实输出，日志见 `运行期日志（已清理，未归档）`）：
1. `grep -rn '7-14' components/qemu/patches QEMU 组件源树中的 target/dadao` ⇒ 0 行，rc=1 ✅
2. 计数：`helper.c` `6-14`=2、`helper.c.patch`=2 ✅；`cpu.h`=**2**、`cpu.h.patch`=**2** —— 与任务书「cpu.h=1」差 1，多出者 `cpu.h:162` / `cpu.h.patch:168`（`cfxha either is reserved (6-14, 19-61 => ILLI)`）**base 既有**、非本任务引入；改用权威判据（diff 增量）：`a5fc0fc..1e5bcaa` 新增 3 行 `6-14`、删除 3 行 `7-14` ✅
3. `make check-patch-tree` ⇒ rc=0（`check-patch-tree: 5 component(s), 205 patches OK`）✅
4. `make check-source-state` ⇒ rc=0；`qemu: OK HEAD=1e5bcaa843f6 count=1 clean=True`（旧 HEAD `a5fc0fc3cc06`；base `c3d48b7d1e89`）✅
5. `git -C <组件源树> diff a5fc0fc3cc06 1e5bcaa843f6` ⇒ 2 文件 3 行（3+/3-），6 条变更行全为 `*` 注释行、非注释行 0（diff 全文见 `运行期日志（已清理，未归档）`）；`--name-only` = 仅 `target/dadao/{cpu.h,helper.c}`；`base..HEAD` 文件数 63 = `components/qemu/series` 行数 63 ✅
6. 见「测试结果」：`make check` rc=2（外部原因）；`make -k check` 证明除 `check-knowledge-refs` 外全部 L1 子目标 rc=0
7. 注入（`cp` 备份 + md5，禁 git 还原）：把 `helper.c.patch` 一处 `6-14` 文本改回 `7-14`（`@@` 未动）⇒ `make check-patch-tree` **rc=2**，输出点名 `helper.c`（断言⑨「HEAD diff differs from helper.c.patch」+ 断言⑥「patched-index blob differs」）；`cp` 还原 ⇒ md5 与备份一致（`d306326751a6…`）⇒ 复跑 rc=0 ✅
8. `make check-milestones-fresh` rc=0；`make check-tasks` rc=0 ✅
9. `运行期证据脚本（已清理，未归档）` ⇒ `checks=22 failures=0`，自身 `rc=0`（`run.EXIT` = `rc=0`）✅

**新发现/坑**：
- 任务书验收 2 的「`cpu.h` = 1」不可机械满足：base 内另有 1 行 `6-14`（`cpu.h:162`）⇒ 绝对计数会误判；正确判据是 **diff 增量**（本任务 +1 行/文件）。
- `check-knowledge-refs` 对**任何**未落地的 `运行期证据（已清理，未归档）` 引用判悬空，含 `待开始` 任务书 ⇒ 立册即令 L1 红；本任务只能解自己 2 条，INFRA-115t 的 2 条须其开工后才绿（建议门控对 `待开始` 册豁免该路径）。
- 重导出后补丁 `index 0000000..10e9fa5` → `7fd9f1b` 随 blob 变化，属正常，非手工编辑。
- `运行期日志（已清理，未归档）` 下新文件名必须为 `check-<name>.log` 或 `<TASK-ID>-<purpose>.log|json|txt`（`check-run-artifacts` A3），否则 L1 红（本任务初版日志名违规 3 个 ⇒ 已改名转绿）；`运行期证据（已清理，未归档）` 不受 A3 约束。

**遗留问题**：L1 未全绿（rc=2，唯一红项 `check-knowledge-refs`，2 条悬空引用属 INFRA-115t、不在本任务范围，未处置）。**未重建 qemu**：改动纯注释、不改变行为，无门控要求 rebuild（`check-patch-tree`/`check-source-state`/`check-qemu-forms`/`make check` 均未触发构建）。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：3 行注释替换 + 补丁重导出 + 证据脚本（`run.sh` 165 行）+ 任务书/milestones 状态。
**逐行审查结论**：
- 注释替换：`python3` 按**行号定位**（cpu.h:112、helper.c:636/842）后仅做 `7-14`→`6-14` 子串替换，`cat -A` 核对行尾/缩进无变化；diff 已证 6 条变更行全为 `*` 注释行。
- 收敛：`reset --soft HEAD~` → `add -A` → `commit`；新 HEAD `1e5bcaa`，`clean=True count=1`；旧 HEAD 记录在案，old..new diff = 3 行（未把 63 文件系列改动当成本任务改动）。
- 补丁：全程只经 `make_patch.py qemu`（禁手编）；`2 written, 61 unchanged` 符合 §6.2 幂等；v5 侧 `git status` 仅 2 份补丁。
- 证据脚本：断言 1（rc=1 零残留）、3/4（门控 rc）、5（非注释行计数=0）、7（注入 md5 变化 + 门控点名 `helper.c` + 还原 md5 一致）均有可达 FAIL；计数现场统计（`wc -l series`）不写死；无 `tee`，rc 逐条显式捕获；`trap` 保证中断也还原。
- 判据口径偏差已披露：任务书 `cpu.h=1` 与现场冲突，已在验收 2 与「新发现」写明，并用 diff 增量替代；**未**擅自改任务书验收正文。
| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 任务书验收 2 `cpu.h`=1 与 base 既有 `6-14` 冲突 | ❌不修（越权：改写验收正文属架构师职权） | 不改验收正文，增补 diff 增量判据（验收 2、新发现） | `a5fc0fc..1e5bcaa` 新增 `6-14` 行=3、删除 `7-14` 行=3；`cpu.h:162` 在 base 未变（不在 diff 中） |
| `make check` rc=2（`check-knowledge-refs`） | ❌不修（越界：悬空引用属 INFRA-115t 册，文件范围禁止改） | 仅创建自有 `运行期证据（已清理，未归档）` | `make -k check` 仅 1 个子目标红；悬空 2 条均指向 INFRA-115t |
| 证据脚本 L1 段把「外部红」当通过的风险（恒真） | ✅已修 | 改为双条件：failing 目标集必须恰为 `check-knowledge-refs` 且日志含 `QEMU-077t` 次数=0，否则 FAIL；L1 全绿则走另一分支 | 注入式核对：若本任务留下悬空或其它门控红，`failing_targets` 不为该单值 ⇒ 走 FAIL 分支 |
| L1 段用全文 `grep -c QEMU-077t` 计悬空 ⇒ 误把 A3 非法文件名等无关行算成本任务悬空 | ✅已修 | 只截取 `check-knowledge-refs` 悬空小节再计数 | 末轮 `own dangling 运行期临时目录 refs: expected 0 actual 0` 且该断言另支可红 |
| source-state 行断言正则字段顺序写反（`clean=True count=1`）⇒ 假 FAIL | ✅已修 | 改为 `qemu: OK HEAD=[0-9a-f]+ count=1 clean=True` | 复跑该断言 PASS（前一轮值 `[FAIL] source-state qemu line not OK`） |
| `运行期日志（已清理，未归档）` 新日志名违规触发 `check-run-artifacts` A3 红（3 个） | ✅已修 | 改为 `<TASK-ID>-<purpose>.log` / `check-<name>.log` | `make check-run-artifacts` rc=0（`0 illegal`）；末轮 L1 仅剩外部红项 |
| 完成区把注入门控 rc 写成 1（实际 2） | ✅已修 | 按实测改为 rc=2 并附点名断言号 | `运行期日志（已清理，未归档）` |

**判决**：**本任务改动范围内无未修 finding**（上表 2 项均为范围外/架构师职权，已在完成区披露）；状态置 `待验收`，交 reviewer 独立验收（含 L1 外部红的裁定）。

#### 第 1 轮 reviewer 验收

（未执行：主会话 2026-11-01 授权 architect 交叉复核代验收——理由：改动仅 3 行纯注释、行为不变、无二进制重建；复核依据见下节。）

#### 第 1 轮 architect 交叉复核（代验收）

**授权**：主会话 2026-11-01 指示「本任务纯注释、行为不变，允许 architect 交叉复核直接判 Accepted」；本子会话即 architect，仅做独立复核 + 定案。

**独立复核（architect 本人重跑，不采信工程师叙述；日志 `运行期日志（已清理，未归档）`）**：
1. 源树：`QEMU 组件源树` HEAD `1e5bcaa`、`status --porcelain` 空、`rev-list --count c3d48b7..HEAD` = 1。
2. `diff a5fc0fc3cc06 1e5bcaa843f6 --stat` ⇒ `cpu.h 2 +-`、`helper.c 4 ++--`（2 文件 3+/3-）；逐行核：6 条变更行全为 `*` 注释行、非注释行 0 ⇒ **行为不变**成立。
3. `grep -rn '7-14' components/qemu/patches QEMU 组件源树中的 target/dadao` ⇒ 0 行（rc=1）；`6-14` 计数：补丁 `cpu.h.patch`=2 / `helper.c.patch`=2，源 `cpu.h`=2 / `helper.c`=2。
4. `make check-patch-tree` **rc=0**（`5 component(s), 205 patches OK`）；`make check-source-state` **rc=0**（`qemu: OK HEAD=1e5bcaa843f6 count=1 clean=True`）；`make check-qemu-forms` **rc=0**（`PASS`）。
5. `make check` **rc=0**（53s，全 L1 子目标绿）——工程师记录的「L1 rc=2、`check-knowledge-refs` 2 条悬空属 INFRA-115t」已随主会话的 INFRA-115t 证据路径占位（`e1c6c5c0`）消除，**该遗留项现场关闭**。
6. 证据脚本重跑：`运行期证据脚本（已清理，未归档）` ⇒ `checks=22 failures=0`、自身 rc=0；其中注入断言实测 `check-patch-tree` **rc=2 且点名 helper.c**，`cp` 还原后 md5 `d3063267…` 与备份一致、仓库 `git status` 干净（`运行期日志（已清理，未归档）`）。

**裁定**：验收 2 的绝对计数改以 **diff 增量**为权威判据（已在验收 2 加注）；工程师未擅改验收正文的处置正确。

**判决**：**Accepted** ⇒ 状态 `已验证`。范围内 finding 已闭环；2 项范围外项（`cpu.h` 计数口径 / INFRA-115t 悬空）分别由本裁定与 `e1c6c5c0` 关闭。产物来自真实门控 + 真实注入，无伪造。
