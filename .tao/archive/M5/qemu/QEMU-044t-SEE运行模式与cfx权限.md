# QEMU-044t: SEE/HEE 运行模式 + cfx 寄存器/掩码/权限/异常进入流程

**模块**：qemu
**项目里程碑**：M5
**依赖**：`SPEC-114t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `SPEC-114t` 后的 `spec/DADAO-12-SEE-主管系统运行环境.md`（§1 四运行模式 + cfxha/cfxname 表；§3 cg0–cg7 共有寄存器〔`global_cfx_mask`/`cfx2rd|cfx2rc|cfxld|cfxst|trap|escape_cfx_mask`/`switch_run_mode`/`switch_cfx_mask`/`excp_vector`/`excp_cause_mask`；§3 cg4/5/6/7 `cfx_id`/`version`/`trap_num`/`excp_sync_num`/`excp_async_num`/`escape_num`/`scratch_regs_num`、`excp_prev_run_mode`/`prev_cfx_mask`/`cause_id`/`cause_ip`/`cause_info`/`pending`/`cause_nonmaskable`、`scratch_regs`、`sram_*`〕；§4 专有寄存器〔本 M5 只做 cfx0/1/2/3/63〕；§5 异常进入/退出流程伪代码【**权威依据**】）；`spec/DADAO-13`（cg3/hmon）；`spec/SimRISC-11-其它.md`（L80：`trap/escape/cfx2rd/cfx2rc` 可在任意运行模式执行，由 cfx mask 控制；L121：reserved cfxha ⇒ ILLI、不存在寄存器组合 ⇒ CFXREG）。
  - `.tao/adr/adr-0020-see-semihosting.md`（`Accepted`，D9/D10/D11）+ `adr-0004` 修订。
  - `.tao/knowledge/contract-sbi.md`/`contract-see.md`（`SPEC-114t` 投影）。
  - 现有 `.work/source/qemu/target/dadao/**`（decode/translate/helper 结构，`ADR-0010` 的 `.c.inc` 拆分）与 `hw/dadao/dadao-machine.c`（复位值、exit port、fault→退出码映射，`ADR-0004` M1 冻结）。
- **输出**（组件源码改在 `.work/source/qemu`；**导出补丁**）：
  1. **四运行模式 `inner_run_mode`（2 位）**：user/jail/supv/hypv（编码 0/1/2/3，`DADAO-12 §1`）；**运行模式与 cfx 正交**（`SimRISC-11 L80`）。
  2. **cfx 寄存器文件（`cfx0/1/2/3/63` = umon/jmon/smon/hmon/power）**：
     - cg0–cg3（user/jail/supv/hypv）：每 mode 12 个共有寄存器（version / `global_cfx_mask` / 6 个指令类型 mask / `switch_run_mode` / `switch_cfx_mask` / `excp_vector` / `excp_cause_mask`）；复位值依 `DADAO-12 §3` 表（version `0x00090002`/`0x00070001` 等、mask 全 1、`switch_run_mode` 初值）。
     - cg4/5/6/7：`cfx_id`/`version`/`trap_num`/`excp_sync_num`/`excp_async_num`/`escape_num`/`scratch_regs_num`；异常现场寄存器（`excp_prev_*`/`cause_*`/`pending`/`cause_nonmaskable`）；暂存寄存器 `scratch_regs[0..N-1]`；SRAM 控制 regs。
     - `global_cfx_mask` 为**全局共享**（所有 cfx 同值，`DADAO-12 §3` 注）。
  3. **`inner_cfx_mask` / `inner_cfx_code`**（per-hart）内部寄存器与判断逻辑。
  4. **异常进入流程（`DADAO-12 §5` 伪代码，权威）**：步骤 1–10——确定 cfx（含 reserved ⇒ ILLI 重定向到当前 mode monitor；指令类型 mask 禁止 ⇒ ILLI；trap/cfx2* 按 cfxha 路由）→ 不可屏蔽判定 → `inner_cfx_mask`/`global_cfx_mask` 屏蔽判定（同步屏蔽 ⇒ ILLI 重定向）→ 异常原因 mask → 陷入计数递增 → 保存现场 → 模式/掩码切换（`switch_run_mode`/`switch_cfx_mask`）→ 保存 `cause_ip`/`cause_id`/`cause_info` → 跳异常向量。
     - **`switch_run_mode` 语义**须落地并在 spec/ADR 已讲清（`ADR-0020 D10`）。
  5. **权限异常**：cfx 访问权限（由 mask 控制）与 `DADAO-12 §2.2` 的 `NUPERM/NJPERM/NSPERM/NHPERM`（**PTBR 权限**层）的**关系须在实现与探针中讲清**（`INTEG-019k` 残留提醒：二者是不同层次；本 M5 权限范围 = `cfx0/1/2/3/63`，`cfx_ptw`(=cfx4)/MMU/页表步进**不在 M5**）。
  6. **未实现 cfx ⇒ `CFXREG` 异常**（出处 `spec/DADAO-22-SBI-主管系统二进制接口.md:58`；佐证 `DADAO-12:373`、`SimRISC-11:121`）：访问 `cfxha ∈ {7..14,19..61}`（reserved）⇒ **ILLI**（`SimRISC-11 L121`）；访问**未实现但已分配的 cfx**（如 cfx4/cfx5…超出本 M5 集合）⇒ **`CFXREG`**（依契约实现对不存在/超出数量的寄存器组合）。
  7. **探针**：`tools/qemu/min_rom_probe_044t.py`（或 `.work/evidence/QEMU-044t/`）——四模式切换、mask 屏蔽（同步 ⇒ ILLI 重定向）、`switch_run_mode`、权限反例（未授权 ⇒ `NU/J/SP/HPERM` 或 CFXREG）、异常进入流程步骤 1–10 的可观测子集。
- **约束（硬）**：
  - **权限范围 = 只做 `cfx0/1/2/3/63`**（`INTEG-019k` 裁定 4）；**`cfx_ptw`(=cfx4)/MMU/页表步进不在本 M5**。`smon`(cfx2) 相关寄存器按范围实现，但 M5 流程 hypv→user 直跳、**不启用 supv**（`INTEG-019k` 裁定 5），bootrom/流程面不使用 smon。
  - **不改 guest 标量指令执行语义**（`target/dadao` 现有 decode/trans 不动，除本任务新增 cfx/模式相关）；**不改 exit port/fault→退出码映射**（`ADR-0004`/`ADR-0011`）。
  - **`trap`/`escape` 执行语义、`cfx2rd`/`cfx2rc` 执行、semihosting 不在本任务**（分别归 `QEMU-045t`/`QEMU-046t`）；本任务提供其依赖的寄存器文件与异常进入流程。
  - **补丁纪律（`spec/Process-01`）**：改动**只能**在 `.work/source/qemu`；导出补丁写 `/tmp`、非空 blob；`make check-patch-tree`（含断言⑥）通过；不手改补丁。
  - **重建成本申报**：`make build-qemu`（**5–20 分钟**）；开工前写明预计耗时；受 `JOBS`（默认 8）限制；失败即停、**禁自动重试**。
  - 临时目录 `/tmp/opencode/QEMU-044t/`；**不提交 git**；复杂命令输出留存 `.work/log/qemu/`（**禁 `tee`**）。
  - **注入/还原纪律**：注入后**还原须含重建**；用 `cp`+`md5` 对账，**禁 `git checkout`/`git restore`/`git stash`**。

## 验收标准

1. **构建**：`make build-qemu` EXIT=0；给真实输出。
2. **四运行模式**：探针可设置/读取 `inner_run_mode`（经 `switch_run_mode` + 异常进入流程），四模式编码正确（真实输出）。
3. **cfx 寄存器**：`cfx0/1/2/3/63` 的 cg0–cg7 寄存器读写正确（含 `global_cfx_mask` 共享、`trap_num`/`escape_num` 递增、`scratch_regs` 数量）；复位值依 `DADAO-12 §3`。
4. **mask 屏蔽**：`global_cfx_mask`（及指令类型 mask）置位 ⇒ 目标非自身 cfx 的同步访问**触发 ILLI 并重定向到当前 mode monitor**（真实探针）。
5. **`switch_run_mode`**：异常进入后运行模式切换为该 cfx 的 `switch_run_mode` 值（真实输出）。
6. **权限反例**：未授权模式/未实现 cfx 访问 ⇒ 依契约触发 `NU/J/SP/HPERM` 或 **`CFXREG`**；reserved cfxha ⇒ **ILLI**（≥3 类，真实输出）。
7. **异常进入流程**：探针覆盖步骤 1–10 的可观测子集（确定 cfx / 不可屏蔽 / mask / 原因 mask / 计数 / 现场 / 模式切换 / cause_ip/id/info / 跳向量）。
8. **不回归**：`make check`/`make check-qemu-semantics` EXIT=0；`make test-codegen`（15/15）/`make test-elf`（5/5）EXIT=0（说明 M1–M4 路径未回归）；`check-patch-tree` EXIT=0。
9. **一键证据脚本**：`.work/evidence/QEMU-044t/run.sh`——非交互、失败非零、逐项打印；**内置注入自检**（关 mask 判定/改 `switch_run_mode` 初值/放宽 reserved 判定 ⇒ 期望 **FAIL** ⇒ 还原 + **重建** ⇒ 回绿），结尾**禁 `tee`**；给真实输出。
10. **无残留**：`git status --untracked-files=all` 仅组件补丁 + 探针 + 本任务书；`.work/source/qemu` worktree clean。

## 完成区

**测试结果**：探针 `tools/qemu/min_rom_probe_044t.py` **13/13 PASS**（`RESULT: PASS`，EXIT=0）；一键证据脚本 `.work/evidence/QEMU-044t/run.sh` **EVIDENCE: PASS**（含合并注入自检：3 反例 → 对应 3 用例 FAIL → 还原（md5 对账相等）→ 重建 → 全绿）；门控 `make check` EXIT=0、`check-qemu-semantics` PASS、`test-codegen` 15/15、`test-elf` 5/5、`check-patch-tree`（2 组件 90 补丁 OK，含断言⑥）EXIT=0；E1（`--source-state`）qemu `count=1 clean=True`。

**修改文件**（与 `git status -uall` 一致）：
- `components/qemu/patches/target/dadao/cpu.h.patch`（M）— cfx 状态结构/宏/字段。
- `components/qemu/patches/target/dadao/cpu.c.patch`（M）— 复位值 + `dump_state`。
- `components/qemu/patches/target/dadao/helper.c.patch`（M）— cfx 寄存器访问 + `§5` 异常进入/退出流程 helper。
- `components/qemu/patches/target/dadao/helper.h.patch`（M）— 4 个 helper 声明。
- `components/qemu/patches/target/dadao/insn_trans/trans_ctrl.c.inc.patch`（M）— `trap`/`escape`/`cfx2rd`/`cfx2rc` 由 ILLI 桩改为路由到流程（`cfxld`/`cfxst` 保持 ILLI）。
- `components/qemu/changelog.md`（M，+1 行；`Process-01 §10` 要求，**非**残留）。
- `tools/qemu/min_rom_probe_044t.py`（新增，**随产物入库**）。
- `.work/evidence/QEMU-044t/{run.sh,PROGRESS.md}`（gitignored，非入库）。
- 本任务书（完成区/自审/状态）。
- 组件源码改在 `.work/source/qemu`（本地收敛 commit，**不入 DADAO 库**）。

**验收结果**（真实命令输出/rc，日志在 `.work/log/qemu/`）：
1. **构建**：`make build-qemu JOBS=8` → `build-qemu: PASS` **EXIT=0**（`.work/log/qemu/QEMU-044t-build2.log`）。
2. **四运行模式**：探针对 `run_mode_0/1/2/3` 全 PASS（`switch_run_mode=0/1/2/3` → `MODE=0/1/2/3`，均 `RESULT: PASS`）。
3. **cfx 寄存器**：`cfx_rw_share` PASS（`global_cfx_mask` 经 cfx0 写、经 cfx63 读回 `0xABCD` 共享；scratch `0x1234`；`scratch_regs_num=4`；`cfx_id=63`）；`trap_counters`（`TRAPN=1`）；`escape_return`（`ESCN=1`）；`reset_values`（`GVER0/1=0x00090002`、`GVER2=0x00070001`、`GVER3=0x00010002`、`GCM0/1/2=全1`、`GCM3=0`、`SWMODE(cg0/1/2)=2`、`SWMODE(cg3)=3`）。
4. **mask 屏蔽**：`mask_illi` PASS — 置 `cfx_umon_hypv_trap_cfx_mask` bit0 ⇒ `trap cfx0` 触发 **ILLI** 并重定向到当前 mode monitor（`cfx_hmon` `CID=0x100`）。
5. **`switch_run_mode`**：`run_mode_*` PASS — 异常进入后 `MODE==switch_run_mode`（0/1/2/3）。
6. **权限反例（≥3 类）**：`reserved_illi`（reserved cfxha 7 ⇒ `CID=ILLI`）、`cfxreg_unimpl`（cfx4 ⇒ `CID=CFXREG`）、`cfxreg_badcombo`（cfx0 scratch rc≥N ⇒ `CID=CFXREG`）、`cfxreg_ro_write`（写 `cfx_id` RO ⇒ `CID=CFXREG`）全 PASS。
7. **异常进入流程**：探针覆盖步骤 1–10 可观测子集——确定 cfx（reserved/unimpl/mask）、mask、计数（trap/sync/escape）、现场（`PREVM`/`PREVMASK`）、模式切换、`cause_ip/id/info`、跳向量（handler 执行 → 退出码）。
8. **不回归**：`make check` **EXIT=0**（含 `check-qemu-semantics: PASS`、`check-patch-tree: 2 component(s), 90 patches OK`）；`test-codegen` **15/15 EXIT=0**；`test-elf` **5/5 EXIT=0**（`.work/log/qemu/QEMU-044t-{check2,test-codegen2,test-elf2}.log`）。
9. **一键证据脚本**：`.work/evidence/QEMU-044t/run.sh` **EVIDENCE: PASS**（`.work/log/qemu/QEMU-044t-evidence2.log`）：合并注入 3 反例（关 mask 判定 / 改 cg0-2 `switch_run_mode` 复位值 / 放宽 reserved 判定）→ 对应 `mask_illi`/`reset_values`/`reserved_illi` 三用例 **EXIT=1（FAIL）** → `cp` 还原且 **md5 相等**（`helper.c=e92b40fb… cpu.c=26fa1afb…`）→ **重建** → 全绿 `RESULT: PASS`；全程无 `tee`。
10. **无残留**：`git status --untracked-files=all` = 组件补丁 5 + `changelog.md` + 新增探针 + 本任务书；`.work/source/qemu` worktree **clean**（`--source-state` `count=1 clean=True`）；无 `*.preinject` 残留。

**新发现/坑**：
1. **`DADAO-12 §5` 步骤 2（不可屏蔽）使 monitor 同步异常绕过步骤 3–5**：monitor（umon/jmon/smon/hmon）异常原因表（`§4`）将**所有**列出的 cause 标为「否」（不可屏蔽）⇒ `inner_cfx_mask`/`global_cfx_mask`/`excp_cause_mask` **不**对 monitor 同步异常生效。故实现集内「mask ⇒ ILLI」的可观测路径是**指令类型 cfx mask（步骤 1）**（探针 `mask_illi` 即证）。`global_cfx_mask` 仍为真实的 per-mode 全局共享（RW）寄存器（`cfx_rw_share` 证）。建议沉淀。
2. **`§5` 步骤 3/4 的 `goto check_nonmaskable` 在 ILLI 重定向后会对「当前 mode monitor」再次套用 `inner/global` mask，导致伪代码层面死循环**；实现为「单次重定向后直接进入当前 monitor（不再复查 inner/global mask）」并注释说明（唯一必要的语义收敛）。
3. **`ASYNCN` 字段名包含子串 `SYNCN`**，`-d cpu` 日志正则须锚定（`ID:… SYNCN:` 带前导空格），否则误取 `ASYNCN` 值——探针已处理（判据/坑，供后续复用）。
4. **任务边界重叠**：本任务按验收 2–7「需可观测触发路径」把 `trap`/`escape`/`cfx2rd`/`cfx2rc` 的 **decode→流程接线** 纳入实现（task 输出 4 明列「trap/cfx2* 按 cfxha 路由」）；`QEMU-045t` 将在此之上 refine + 专探针，二者输出有重叠，供 architect 判定是否收缩 045t。
5. **semihosting tag（`immu18[17:16]==2'b11`）** 在 046t 前**显式失败**（⇒ ILLI 重定向），不留静默成功桩。

**遗留问题**：
- **PTBR 权限层（`NUPERM/NJPERM/NSPERM/NHPERM`）不在本 M5**（`ADR-0020 D9`、`Machine-01 §3`）：cfx 访问权限（mask ⇒ ILLI/CFXREG）与 PTBR 权限分属两层，本任务实现/探针只覆盖前者；`cfx_ptw`(=cfx4)/MMU/页表步进未实现（cfx4 访问⇒CFXREG）。验收 6 的「或 CFXREG」分支满足（≥3 类）。
- **`excp_cause_mask`（步骤 5）屏蔽路径**对已实现 cfx 不可观测（monitor cause 全不可屏蔽，见新发现 1）；探针只验证该寄存器为真实 RW（写 0 以放行进入），未验证「屏蔽 → pending」。
- **`escape`/`trap` 完整语义（负偏移回退、跨 cfx escape、`cfx2rd`/`cfx2rc` 全寄存器面）** 归 `QEMU-045t` 深化与专探针；本任务实现为其基础能力。
- 复核提示：`changelog.md` 为 `Process-01 §10` 要求的按任务记录（非残留）。

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

**自审范围**：逐行审查改动源码（`cpu.h`/`cpu.c`/`helper.c`/`helper.h`/`trans_ctrl.c.inc`）+ 探针 + 证据脚本；核对 Spec-first（`DADAO-12 §1/§3/§4/§5`、`DADAO-13 §1`、`SimRISC-11 §特权指令`、`contracts/opcodes.yaml`）、边界（不改标量语义/exit-port）、防造假（真实执行）。

**结论**：逻辑正确、边界受控；发现 1 处 spec 保真问题（已当场修复并复验），其余为已处理/已记录的判据。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `cfx_enter` 步骤 6 计数按「原始是否 trap」判定；发生 ILLI 重定向后 `cause` 已变 ILLI，仍记 `trap_num`（应记 `excp_sync_num`，`§5:797` 按 `cause` 判定） | ✅已修 | `helper.c`：去掉 `is_trap` 形参，步骤 6 改为 `if (cause == DADAO_CAUSE_CFXTRAP)`；更新 2 处调用点 | 重建 EXIT=0；探针 13/13 PASS；`trap_counters`(TRAPN=1)/`escape_return`(ESCN=1)/`mask_illi`(SYNCN=1) 仍 PASS；`make check`/`test-codegen`/`test-elf` 全绿 |
| F2 探针 `MODE`/`CFXCODE` 为十进制，误按十六进制解析 | ✅已修 | `min_rom_probe_044t.py`：新增 `lastdec`，`MODE`/`CFXCODE` 用十进制 | 13/13 PASS |
| F3 探针 `SYNCN` 正则被 `ASYNCN` 子串污染（误取 ASYNCN 值） | ✅已修 | 正则锚定 `ID:[^\n]* SYNCN:`（前导空格） | 13/13 PASS（`mask_illi`/`cfxreg_*` 的 `syncn` 断言可分辨 FAIL/PASS） |
| F4 `§5` 步骤 3/4 重定向后 `goto check_nonmaskable` 会死循环 | ✅已收敛（记录） | `helper.c`：重定向后进入当前 monitor 不再复查 inner/global mask，并注释 | `mask_illi` PASS；完成区「新发现 2」 |
| F5 `trap` 的 semihosting tag（`==2'b11`）在 046t 前无实现 | ✅显式失败 | `helper.c`：tag 命中 ⇒ ILLI 重定向（非静默成功） | 完成区「新发现 5」；无探针用例走该分支 |
| F6 边界：`trap`/`escape`/`cfx2rd`/`cfx2rc` decode 接线落在本任务，与 045t 输出重叠 | ⏸记录（待 architect 判定） | 无（保持实现以满验收 2–7） | 完成区「新发现 4」；reviewer 可据此判 045t 是否收缩 |
| F7 断言可达 FAIL | ✅已证 | 合并注入 3 反例各自使对应用例 FAIL | `run.sh` 注入段：`mask_illi`/`reset_values`/`reserved_illi` EXIT=1；还原+重建后回绿 |

**状态**：无未修 finding ⇒ 置「待验收」，返回主会话 `/complete`。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer（mimo-v2.5-pro）
**审查时间**：2026-10-08
**审查范围**：证据脚本审核 + 重跑 + 独立注入 + 约束核验 + 边界处置复核

---

##### A. 证据脚本 `.work/evidence/QEMU-044t/run.sh` 审核

| 检查项 | 结果 |
|--------|------|
| 无 `tee`（仅注释 L20 提及） | ✅ |
| `rc=$?` 直接捕获退出码（非管道） | ✅ L45/L56/L84/L101/L111/L123/L133/L141 |
| `cp` 备份 + `md5sum` 对账还原 | ✅ L62-65 / L122-128 |
| 注入前 `assert` 模式存在性（Python `assert old in s`） | ✅ L73 |
| `git diff --name-only` 非空验证 | ✅ L92-98 |
| 注入后重建 → 用例 FAIL → 还原 → 重建 → 回绿 | ✅ 完整流程 |
| 注入模式与当前源码匹配 | ✅ helper.c 1+1+3处，cpu.c 1处（grep 确认） |
| 3 个注入各自独立（mask/复位值/reserved） | ✅ 不同文件/不同语义 |
| 结尾 `exit 0`/`exit 1` 基于 `fail` 变量 | ✅ L146-151 |

**结论**：脚本合格，有可达 FAIL 路径，注入自检非空，还原含重建。

---

##### B. 重跑证据脚本（真实输出）

```
==============================================================
QEMU-044t evidence: SEE run mode + cfx register file/flow
==============================================================

----- [1/5] make build-qemu -----
make build-qemu EXIT=0

----- [2/5] probe (all cases) -----
[PASS] run_mode_0       switch_run_mode=0 -> run mode 0 -> ok
[PASS] run_mode_1       switch_run_mode=1 -> run mode 1 -> ok
[PASS] run_mode_2       switch_run_mode=2 -> run mode 2 -> ok
[PASS] run_mode_3       switch_run_mode=3 -> run mode 3 -> ok
[PASS] reset_values     cg0-cg7 reset values per DADAO-12 §3 / DADAO-13 §1 -> ok
[PASS] cfx_rw_share     cfx2rd/cfx2rc rw + global_cfx_mask sharing (cfx0<->cfx63) -> ok
[PASS] trap_counters    trap_num increment + cause_ip/id/info frame -> ok
[PASS] escape_return    escape -> cause_ip+4, escape_num++, prev mode/mask restore -> ok
[PASS] mask_illi        cfx trap mask bit => ILLI redirect to current-mode monitor -> ok
[PASS] reserved_illi    reserved cfxha (7-14,19-61) => ILLI -> ok
[PASS] cfxreg_unimpl    unimplemented cfx (cfx4) access => CFXREG -> ok
[PASS] cfxreg_badcombo  invalid cfx register combo (scratch rc>=N) => CFXREG -> ok
[PASS] cfxreg_ro_write  write to read-only cfx register (cfx_id) => CFXREG -> ok
RESULT: PASS
probe(all) EXIT=0

----- [3/5] injection self-check (merged: 3 anomalies, 1 rebuild) -----
pre-inject md5: helper.c=e92b40fbfdeaeed440f4caf12a8b58a8 cpu.c=26fa1afb7ab3c44a8da56ba18f3b2d4e
injections applied
inject EXIT=0
injected files (git diff --name-only):
target/dadao/cpu.c
target/dadao/helper.c
rebuild(after inject) EXIT=0
[FAIL] mask_illi        cfx trap mask bit => ILLI redirect to current-mode monitor -> exit exp=0x22 got=0x87; cid:3 exp=0x100 got=0x0; syncn:3 exp=0x1 got=0x0; cip:3 exp=0xffffffff0018 got=0x0
RESULT: FAIL
inject-check mask_illi EXIT=1 (expected NON-zero)
[FAIL] reset_values     cg0-cg7 reset values per DADAO-12 §3 / DADAO-13 §1 -> swmode:63:0 exp=0x2 got=0x1; swmode:63:1 exp=0x2 got=0x1; swmode:63:2 exp=0x2 got=0x1; swmode:0:0 exp=0x2 got=0x1
RESULT: FAIL
inject-check reset_values EXIT=1 (expected NON-zero)
[FAIL] reserved_illi    reserved cfxha (7-14,19-61) => ILLI -> cid:3 exp=0x100 got=0x4
RESULT: FAIL
inject-check reserved_illi EXIT=1 (expected NON-zero)

----- [4/5] restore + rebuild + re-green -----
post-restore md5: helper.c=e92b40fbfdeaeed440f4caf12a8b58a8 cpu.c=26fa1afb7ab3c44a8da56ba18f3b2d4e
rebuild(after restore) EXIT=0
[PASS] run_mode_0       switch_run_mode=0 -> run mode 0 -> ok
[PASS] run_mode_1       switch_run_mode=1 -> run mode 1 -> ok
[PASS] run_mode_2       switch_run_mode=2 -> run mode 2 -> ok
[PASS] run_mode_3       switch_run_mode=3 -> run mode 3 -> ok
[PASS] reset_values     cg0-cg7 reset values per DADAO-12 §3 / DADAO-13 §1 -> ok
[PASS] cfx_rw_share     cfx2rd/cfx2rc rw + global_cfx_mask sharing (cfx0<->cfx63) -> ok
[PASS] trap_counters    trap_num increment + cause_ip/id/info frame -> ok
[PASS] escape_return    escape -> cause_ip+4, escape_num++, prev mode/mask restore -> ok
[PASS] mask_illi        cfx trap mask bit => ILLI redirect to current-mode monitor -> ok
[PASS] reserved_illi    reserved cfxha (7-14,19-61) => ILLI -> ok
[PASS] cfxreg_unimpl    unimplemented cfx (cfx4) access => CFXREG -> ok
[PASS] cfxreg_badcombo  invalid cfx register combo (scratch rc>=N) => CFXREG -> ok
[PASS] cfxreg_ro_write  write to read-only cfx register (cfx_id) => CFXREG -> ok
RESULT: PASS
probe(all, post-restore) EXIT=0

----- [5/5] result ------
EVIDENCE: PASS
SCRIPT_EXIT=0
```

---

##### C. 独立注入（reviewer 自行执行，非沿用 engineer）

**注入方式**：改 helper.c trap mask 条件为 `if (0 && ...)` 短路（与 engineer 的 `replace(..., "0")` 不同）

**注入前快照**：
- helper.c md5 = `e92b40fbfdeaeed440f4caf12a8b58a8`
- cpu.c md5 = `26fa1afb7ab3c44a8da56ba18f3b2d4e`

**注入**：
```
$ python3 -c "... sub(helper.c, 'if (cfxha != env->inner_cfx_code &&\n        (env->cfx[ci].mode[env->inner_run_mode].trap_mask & (1ULL << cfxha))) {', 'if (0 && cfxha != env->inner_cfx_code &&\n        (env->cfx[ci].mode[env->inner_run_mode].trap_mask & (1ULL << cfxha))) {') ..."
injection applied (1 occurrence)
```

**验证注入有效**：
```
$ git -C .work/source/qemu diff --name-only
target/dadao/helper.c
$ md5sum .work/source/qemu/target/dadao/helper.c
652845080796cfc6f2bb4c83c7262825  (changed from e92b40fb...)
```

**增量重建**：`make build-qemu JOBS=8` → `build-qemu: PASS` EXIT=0（21 步 ninja 增量）

**探针验证**：
```
$ python3 tools/qemu/min_rom_probe_044t.py --qemu .work/build/qemu/qemu-system-dadao --only mask_illi
[FAIL] mask_illi  cfx trap mask bit => ILLI redirect to current-mode monitor -> exit exp=0x22 got=0x87; cid:3 exp=0x100 got=0x0; syncn:3 exp=0x1 got=0x0; cip:3 exp=0xffffffff0018 got=0x0
RESULT: FAIL
PROBE_EXIT=1
```

**还原**（`cp` + md5 对账）：
```
$ cp /tmp/opencode/QEMU-044t-review/helper.c.orig .work/source/qemu/target/dadao/helper.c
$ md5sum .work/source/qemu/target/dadao/helper.c /tmp/opencode/QEMU-044t-review/helper.c.orig
e92b40fbfdeaeed440f4caf12a8b58a8  .work/source/qemu/target/dadao/helper.c
e92b40fbfdeaeed440f4caf12a8b58a8  /tmp/opencode/QEMU-044t-review/helper.c.orig
```
md5 相等 ✓

**还原后重建**：`make build-qemu JOBS=8` → `build-qemu: PASS` EXIT=0

**回绿验证**：13/13 PASS，EXIT=0（完整输出见上方 B 节 post-restore 段）

---

##### D. 验收标准逐条核验

| # | 验收项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | 构建 `make build-qemu` EXIT=0 | ✅ | B 节 [1/5] EXIT=0 |
| 2 | 四运行模式编码 0/1/2/3 | ✅ | `run_mode_0/1/2/3` 全 PASS（switch_run_mode → MODE 正确） |
| 3 | cfx 寄存器 cg0-cg7 + global_cfx_mask 共享 + 复位值 | ✅ | `cfx_rw_share`（0xABCD 共享、scratch 0x1234、scrnum=4、id=63）；`reset_values`（GVER0/1=0x00090002, GVER2=0x00070001, GVER3=0x00010002, GCM0/1/2=全1, GCM3=0, SWMODE cg0-2=2, cg3=3）；`trap_counters`(TRAPN=1)；`escape_return`(ESCN=1) |
| 4 | mask 屏蔽 ⇒ ILLI 重定向 | ✅ | `mask_illi` PASS（置 bit0 → trap cfx0 触发 ILLI, CID=0x100） |
| 5 | switch_run_mode 生效 | ✅ | `run_mode_0/1/2/3` 全 PASS（MODE==switch_run_mode） |
| 6 | 权限反例 ≥3 类 | ✅ | `reserved_illi`（reserved cfxha 7⇒ILLI, CID=0x100）；`cfxreg_unimpl`（cfx4⇒CFXREG, CID=0x4）；`cfxreg_badcombo`（scratch rc≥N⇒CFXREG, CID=0x4）；`cfxreg_ro_write`（写 cfx_id RO⇒CFXREG, CID=0x4）— **4 类** |
| 7 | 异常进入流程步骤 1-10 可观测子集 | ✅ | 确定 cfx（reserved/unimpl/mask）、mask、计数（trap/sync/escape）、现场（PREVM/PREVMASK）、模式切换、cause_ip/id/info、跳向量（handler→退出码） |
| 8 | 不回归 | ✅ | `make check` EXIT=0；`test-codegen` 15/15 EXIT=0；`test-elf` 5/5 EXIT=0；`check-patch-tree` 90 patches EXIT=0 |
| 9 | 一键证据脚本 | ✅ | `run.sh` EVIDENCE: PASS, EXIT=0；含 3 注入自检（FAIL→还原+md5→重建→回绿）；无 tee |
| 10 | 无残留 | ✅ | `git status --untracked-files=all` 空；`.work/source/qemu` worktree clean |

---

##### E. 补丁集合规（Process-01）

| 检查项 | 结果 |
|--------|------|
| 一文件一补丁 | ✅ 5 个补丁（cpu.h/cpu.c/helper.c/helper.h/trans_ctrl.c.inc） |
| 非空 blob | ✅ |
| series 完整 | ✅ |
| changelog.md 一条 | ✅ QEMU-044t 条目存在 |
| `check-patch-tree`（含断言⑥） | ✅ 2 component(s), 90 patches OK |
| `.work/source/qemu` worktree clean | ✅ `--source-state` count=1 clean=True |

---

##### F. 探针落点

`tools/qemu/min_rom_probe_044t.py` 已入库（`git ls-files` 确认），非一次性脚本。13 用例覆盖验收 2-7。

---

##### G. 越界核验

`git diff --name-only dae34ee..HEAD` = 11 文件：
- 5 组件补丁 + `changelog.md` + 探针 + 044t 任务书 + 045t 任务书 + `AGENTS.md` + `lessons.md`
- `spec/` 交集为空 ✓
- `.work/**` 未入库 ✓
- 与完成区「修改文件」声明一致 ✓

---

##### H. 边界处置复核

045t 任务书「审阅记录 · 044t/045t 边界处置说明」有据：
- **依据**：引用 044t 实测补丁 `trans_ctrl.c.inc.patch`（4 个 trans 由 ILLI 桩改为 gen_helper）+ `helper.c.patch`（helper_cfx_trap/escape/cfx2rd/cfx2rc），非转述
- **045t 收缩为**：「在 044t 基线上深化/验证完整语义 + 专探针」（负偏移回退、跨 cfx escape、全寄存器面）
- **M5 总范围不变**：仅实现/验证分工调整，未扩大/缩小

---

##### 判决

**Accepted**

全部 10 项验收标准通过；证据脚本合格（含可达 FAIL 路径 + 注入自检）；独立注入（改 helper.c trap mask 条件为 `if (0 && ...)`）→ FAIL → 还原+md5→重建→回绿；不回归全绿；补丁集合规；探针已入库；未越界；边界处置有据。

#### 子代理异常登记（主会话，2026-10-08）

- **第 1 次下发**：`task(engineer)` 返回 **`aborted`**（`Tool execution interrupted`，子代理 sessionID `ses_ee70c73e3ffeJBi7uxris1o7V5`）。
- **现场核对（真实）**：`git status --porcelain -uall` = **0 项**（干净）；本任务书 `**状态**` 仍 `待开始`；`tools/qemu/min_rom_probe_044t.py` **不存在**；`.work/evidence/QEMU-044t/` **不存在**；`.work/log/qemu/` 仅既有旧日志（无 044t 产物）；无残留 `ninja`/`qemu-system-dadao`/`cc1plus` 进程。
- **判定**：**确未落盘** ⇒ 按 `AGENTS.md`「子代理返回异常处理」**重试同一任务**（不换任务/不换内容/不扩范围），并附失败现场；预算 ≤3 次。
- **重试加固（不改变任务内容）**：要求 engineer **分段落盘**（每个段落先写完成区/产物再继续），降低单轮过长导致中断的损失。

#### 第 1 轮 architect 提交（WIP，2026-10-08）

- **档位**：**WIP**（reviewer 尚未验收，`**状态**` 仍 `待验收`）。
- **提交信息**：`WIP: QEMU-044t SEE 运行模式 + cfx 权限/掩码/异常进入（+044t/045t 边界处置）（待 reviewer 验收）`。
- **文件集对账（显式 staging，禁 `git add -A`）**：
  - 与 044t 完成区「修改文件」声明一致：5 组件补丁（`cpu.h`/`cpu.c`/`helper.c`/`helper.h`/`trans_ctrl.c.inc`）+ `changelog.md`（+1 行）+ 新探针 `tools/qemu/min_rom_probe_044t.py` + 本任务书。
  - **本轮 architect 追加**（超出 044t engineer 声明，属边界处置 / 规则落纸）：`QEMU-045t` 任务书、`AGENTS.md`、`.tao/knowledge/lessons.md`。
  - **无越界**：`.work/**` 未入库（gitignored，已核）；未卷入 `spec/`（`git status -- spec/` 空）。
- **044t/045t 边界处置摘要**：见 `QEMU-045t` 任务书「审阅记录 · 044t/045t 边界处置说明」——044t 已落地 `trap`/`escape`/`cfx2rd`/`cfx2rc` 的 decode→流程接线与基础执行，045t 收敛为「基线之上深化/验证 + 专探针」，M5 总范围不变。
- **未 push**（只本地 commit；`push` 归主会话 `/complete` 后）。

#### 第 1 轮 architect 交叉复核（2026-10-08）

**复核范围**：reviewer 判决是否过严/过松/遗漏；reviewer **独立注入**的鉴别力与还原是否含恢复；关键事实**独立**核对；越界核对；遗留处置。

**判决**：**通过**（reviewer `Accepted` 成立，不推翻）。

**独立核验（architect 自跑，真实输出）**：
- **四模式编码**：`cpu.h` `DADAO_MODE_USER=0`/`JAIL=1`/`SUPV=2`/`HYPV=3`，与 `spec/DADAO-12 §1` 表（0b00/01/10/11）逐项一致 ✓。
- **`global_cfx_mask` 跨 cfx 共享**：`cpu.h` 声明 `uint64_t global_cfx_mask[4]`（**按 mode 索引**，无 per-cfx 维）；`cpu.c` 复位仅按 mode 各赋一次；`helper.c:639/654` 经 `cg` 取 `&env->global_cfx_mask[cg]` ⇒ 所有 cfx 同值（`DADAO-12 §3` 注「全局寄存器」）✓；探针 `cfx_rw_share`（cfx0 写 ⇒ cfx63 读回 `0xABCD`）证 ✓。
- **复位值逐项对 spec**：`cpu.c:131-138` — `gver0/1=0x00090002`（`DADAO-12 §3` cg0/1）、`gver2=0x00070001`（cg2）、`gver3=0x00010002`（`DADAO-13 §1` cg3）；`gcm0/1/2=~0`、`gcm3=0`（`DADAO-13 §1` cg3 mask 全0）；`switch_run_mode`：cg0–2 = `DADAO_MODE_SUPV`（`DADAO-12 §3` 均「2」）、cg3 = `DADAO_MODE_HYPV`（`DADAO-13 §1`「3」）；cg3 `excp_vector = cfxha<<42 + 0x3ff_ffff_0000`（`DADAO-13 §1`）、`switch_cfx_mask=~0`（全1）——**逐项一致** ✓。
- **权限反例 ≥3 类**（`helper.c`）：reserved `DADAO_CFX_IS_RESERVED` ⇒ `ILLI`；`cfx_idx<0`（cfx4 等未实现）⇒ `CFXREG`；`cfx_reg_ptr` cg6 `rc>=scratch_regs_num` ⇒ `NULL`⇒`CFXREG`；RO 寄存器 `write` ⇒ `NULL`⇒`CFXREG`——**4 类** ✓。
- **`check-patch-tree`**：`python3 tools/infra/check_patch_tree.py` ⇒ `2 component(s), 90 patches OK` **EXIT=0**（含断言⑥）；`--source-state` ⇒ qemu `HEAD=b4875bd5a591 count=1 clean=True` **EXIT=0** ✓。
- **越界**：`git diff --name-only dae34ee..HEAD` = **11 文件**（5 组件补丁 + `changelog.md` + 探针 + 044t/045t 任务书 + `AGENTS.md` + `lessons.md`）；`git diff --name-only dae34ee..HEAD -- spec/` **空** ✓；`.work/**` 未入库；无 `*.preinject` 残留 ✓。
- **reviewer 独立注入**：方式为 `if (0 && …)` 短路 `helper.c` trap mask（与 engineer 的 `replace(…,"0")` 不同）；注入后 `git diff` 非空 + md5 变化（有鉴别力）；`mask_illi` FAIL（`exit exp=0x22 got=0x87; cid exp=0x100 got=0x0`）；`cp`+md5 还原 ⇒ **重建** ⇒ 回绿——**还原含重建、有鉴别力** ✓（独立核对当前源码 md5 `helper.c=e92b40fb…`/`cpu.c=26fa1afb…` 与 reviewer 记录**逐字相等**，`.work/source/qemu` worktree clean ⇒ 注入已复原且重建态正确）。

**补充发现（供 `/complete` 统一报告）**：
1. reviewer 的独立注入站点与 engineer 的 `run.sh` 注入 #1 为**同一处**（`helper_cfx_trap` 的 `trap_mask` 判定），仅**语法形式不同**（`if (0 && …)` vs 替换为 `0`）。鉴别力成立（二者均落到同一语义分支），但「独立注入」的**覆盖面**未超出 engineer 自检——建议后续组件任务让 reviewer 注入**不同语义分支**（如本任务的 `switch_run_mode` 复位 / reserved 判定）以扩大独立证伪面。
2. 遗留 2–5 处置**判定可接受**：
   - **monitor 全不可屏蔽 ⇒ 集内「mask⇒ILLI」实为步骤 1 指令类型 mask**：属**对 `DADAO-12 §5` 步骤 2 + §4 异常表的正确读法**（非缺陷），engineer 登记为「新发现 1」恰当；因步骤 3/4/5 屏蔽路径在当前测试机**不可观测**（仅实现了 monitor + power，其余 cfx 访问 ⇒ `CFXREG` 回 monitor），**登记 `ISS-164`** 跟踪（待后续实现带可屏蔽 cause 的 cfx 后补验）。
   - **PTBR 权限层（`NUPERM` 等）不在 M5**：属 `ADR-0020 D9`/`spec/Machine-01 §3` 的 M5 范围决定，**非缺陷**；**无需额外任务/issue**（作为里程碑范围事项已记录）。
   - **`excp_cause_mask` 屏蔽不可观测**：并入 `ISS-164`（同上）。
   - **`escape`/`trap` 深化归 `QEMU-045t`**：已有 `QEMU-045t` 任务书承接（已收缩为「044t 基线之上深化/验证 + 专探针」，M5 总范围不变）——**无需 issue**。
3. **未发现遗漏**：验收 1–10 逐条对应真实证据；补丁集合规（一文件一补丁 / 非空 blob / `changelog.md` 一条）；探针已入库（`tools/qemu/min_rom_probe_044t.py`）。

#### 第 1 轮 architect 提交（正常，2026-10-08）

- **档位**：**正常提交**（reviewer 判 `Accepted`，`**状态**` 置 `已验证`；**不加 `WIP:`**）。
- **提交信息**：`QEMU-044t SEE 运行模式 + cfx 权限/掩码/异常进入（reviewer Accepted）`。
- **文件集对账（显式 staging，禁 `git add -A`）**：
  - 与 044t 完成区「修改文件」声明一致：5 组件补丁（`cpu.h`/`cpu.c`/`helper.c`/`helper.h`/`trans_ctrl.c.inc`）+ `changelog.md`（+1 行）+ 新探针 `tools/qemu/min_rom_probe_044t.py` + 本任务书（含 reviewer/architect 记录 + `**状态**=已验证`）。
  - **本轮 architect 追加**（知识沉淀 / 收尾，超出 engineer 声明）：`.tao/knowledge/{lessons.md,changelog.md,milestones.md,MEMORY.md,issues.yaml}`。
  - **无越界**：`spec/` 交集**空**（`git diff --cached --name-only` 与 `spec/` 无交集，已核）；`.work/**` 未入库（gitignored）。
- **未 push**（只本地 commit；`push` 归主会话 `/complete` 后，须 squash/amend 为单一「已验证」提交）。

#### 主会话统一验收报告（`/complete`，2026-10-08）

- **下发异常与重试**：第 1 次下发 `aborted`（子代理会话被中断）且**核对确认未落盘** ⇒ 按规则**重试一次**（附失败现场 + **分段落盘加固**）⇒ **成功**。据此你的新裁定已落纸：`AGENTS.md`「重试上限 = **1 次**；仍异常 ⇒ **停止重试、改任务拆分**」+ `lessons §8.9`。
- **reviewer**：`Accepted`。证据脚本重跑 **`EVIDENCE: PASS`**（探针 **13/13**，3 处注入各自 FAIL ⇒ `cp`+`md5` 还原 ⇒ **重建** ⇒ 回绿）；**独立注入**（`if (0 && …)` 短路 `helper_cfx_trap` 的 `trap_mask` 判定）⇒ `mask_illi` **FAIL** ⇒ 还原（md5 `e92b40fb…`）⇒ 重建 ⇒ 13/13。
- **architect 交叉复核**：**通过**。独立核：四模式编码与 `DADAO-12 §1` 一致；`global_cfx_mask` **按 mode 索引、无 per-cfx 维** ⇒ 跨 cfx 共享 ✓；复位值（`GVER`/`GCM`/`SWMODE`/`excp_vector`）与 `DADAO-12 §3`/`DADAO-13 §1` **逐项一致**；权限反例 **4 类**；`check-patch-tree` 90 patches（断言⑥）、`--source-state` clean。
- **交付**：四运行模式 + cfx 寄存器文件（cg0–cg7）+ 掩码/权限 + **异常进入流程步骤 1–10**；未实现 cfx ⇒ `CFXREG`、reserved cfxha ⇒ `ILLI`；探针 `tools/qemu/min_rom_probe_044t.py` **随产物入库**；补丁集 5 改 + `changelog.md`。
- **边界处置**：`QEMU-045t` 范围**最小收缩**（触发路径已由 044t 落地 ⇒ 045t 改为「044t 基线之上深化/验证 + 专探针」），**M5 总范围不变**；依据为 044t 实测补丁。
- **遗留处置**：步骤 3/4/5 的 mask 屏蔽路径当前**不可观测** ⇒ 登记 **`ISS-164`** 跟踪；PTBR 权限层（`NU/J/SP/HPERM`）不在 M5（`ADR-0020 D9`）；`escape`/`trap` 深化归 045t。
- **补充发现（非阻塞）**：reviewer 注入站点与 engineer 自检 #1 同处（仅语法不同）⇒ 建议后续组件任务让 reviewer 注入**不同语义分支**以扩大独立证伪面。
- **收尾检查**：`make check`/`check-qemu-semantics` EXIT=0、`test-codegen` 15/15、`test-elf` 5/5、`check-patch-tree` 90 patches；`git status --porcelain -uall` 干净；证据留 `.work/evidence/QEMU-044t/`、`.work/log/qemu/`（含 `PROGRESS.md`）。
- **最终判决**：**`Accepted`** ⇒ 任务书 `**状态**` 置 `已验证`。

#### 口径说明（architect，2026-10-08）

- **不改验收标准正文**（验收 6 等历史文本保留）。
- **说明**：验收 6 的「`NU/J/SP/HPERM` 或 `CFXREG`」在 M5 的实现中**实际走 cfx 级分支**（`CFXREG` / reserved ⇒ `ILLI`）；`NUPERM/NJPERM/NSPERM/NHPERM` 属 `DADAO-12 §2.2` **PTBR 层、不在 M5**（`ADR-0020 D9`）。本条与完成区「遗留问题」及 `ISS-164` 记录一致；属**口径澄清**，非新增范围、非缺陷。
