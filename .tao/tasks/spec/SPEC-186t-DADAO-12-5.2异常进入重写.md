# SPEC-186t: DADAO-12 §5.2 异常进入流程重写（同步路由定稿）

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-184t`（同改 `manifests/spec-readonly.lock.toml`，本任务须在其后串行，不得并发改锁）；`SPEC-183t`（DADAO-12 现行基线）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 问题根源

`spec/DADAO-12-SEE-主管系统运行环境.md §5.2` 严重落后于已定稿的异常路由，三处结构性冲突：

1. **独立屏蔽层未拆**：§5.2 步骤 3 仍用 `inner_cfx_mask` 对**同步异常**做屏蔽判定，被屏蔽时改写为 `ILLI`；与「同步异常全部不可屏蔽、统一进入当前运行模式 monitor」冲突。
2. **目标 cfx 路由过时**：`CFXREG` 仍可能进入被访问 cfx；`CFXPERM`/`CFXMEM` 仍按目标 cfx 或 `cfx_ptw` 路由；页表缺失/权限仍进入 `cfx_ptw`，并保留独立的 `PTWERR`；与「同步权限拒绝统一 `CFXPERM`、`CFXREG` 统一当前 monitor、未映射归当前 monitor `CFXMEM`」冲突。
3. **异步与同步混写**：异步中断的 `cfx_intr_mask`/`global_cfx_intr_mask`/`excp_cause_mask`/pending 与同步流程混在同一组步骤里，无法区分「已定稿的同步路由」与「尚未冻结的异步屏蔽」。

本任务只重写规范侧的异常进入流程/原因路由，不改退出码、其它 spec 册、Machine-v5、QEMU/gem5/tests/tools。

## 用户口径（本任务依据，经主会话转达）

> 「`DADAO-12 §5.2` 严重落后，需要整体重写。」
> 「删除 `inner_cfx_mask`（作为独立屏蔽层）。」
> 「同步权限拒绝统一 `CFXPERM`，进入当前运行模式对应 monitor（user/jail/supv/hypv）。」
> 「`CFXREG` 统一进入当前运行模式 monitor，不进入被访问 cfx。」
> 「保留 cfx（6–14、19–61）普通 `ld/st` → `CFXMEM` 当前 monitor；`trap`/`escape` → `ILLI` 当前 monitor。」
> 「`unmapped` 归当前运行模式 monitor 的 `CFXMEM`。」
> 「monitor 异常编号使用 DADAO 位索引：CFXTRAP=0、CFXMEM=1、CFXREG=2、CFXESC=3、CFXPERM=7、ILLI=8、UNDI=9、RASOF=10、RASUF=11、MALIGN=12、IALIGN=13；PTWERR 删除。」
> 「A/D 回写失败（原 `PTWERR`）按当前运行模式 monitor 的 `CFXMEM` 处理；`cause_info` = PTE 物理地址；不进入 `cfx_ptw` 自己的异常入口，也不归 `CFXPERM`。」（2026-11-05 裁定，用户原话：「不对，还是应该当前运行模式monitor的CFXMEM」）
> 「执行过程中的同步异常和异步中断应该先进对应运行模式的 monitor 中。」（2026-11-05 裁定；异步模型选 **A**：monitor 是第一处理者，拥有屏蔽/pending/分发；显式 `trap`/`escape` 仍直接到 cfx；monitor 处理期间新事件置 pending，不嵌套。）
> 「异步中断屏蔽不冻结，明确列为后续修订，M11 不承诺完整异步语义。」
> 「退出码表归 `Machine-v5`，不在本任务；本任务只改 DADAO-12 异常流程/原因路由，不改 QEMU/gem5/tests/tools。」

## 目标

1. 整体重写 `spec/DADAO-12-SEE-主管系统运行环境.md §5.2`：同步异常按定稿路由统一进入当前运行模式 monitor；删除 `inner_cfx_mask` 同步屏蔽层；异步屏蔽明确列为后续修订。
2. 同步 §1 的 `inner_*` 注记（删除「用于同步异常屏蔽判断」的表述），保留 §2/§3/§4 其它内容不动。
3. 在附录 `0.7.3-rc`（未发布）追加一条变更记录；版本号不变（不发布）。
4. 同笔重算 `manifests/spec-readonly.lock.toml` 中 `DADAO-12` 的 `sha256`，并写授权注记（日期 + 用户口径摘要）；其它册的 `sha256`/注记不动。
5. 十项门控全绿、两处注入可达 FAIL、证据与完成区真实 rc；状态置 `待验收`。

## 接口规范（精确改动）

### 1. `spec/DADAO-12-SEE-主管系统运行环境.md §5.2`（整体重写）

保留标题 `### 5.2 异常进入流程`，**不得新增/改号 `##`/`###` 标题**。新正文必须包含以下路由与步骤（语义等价即可，关键字/目标不得变）。

**（1）同步异常路由（全部不可屏蔽）**

- `trap`/`cfx2rd`/`cfx2rc`，`cfxha` 为 reserved（`6–14`、`19–61`）⇒ `ILLI`，目标 = **当前运行模式 monitor**。
- `trap`/`cfx2rd`/`cfx2rc`，目标 cfx 的 `<mode>_cfxtrap`/`<mode>_cfxreg` 拒绝源 cfx ⇒ `CFXPERM`，目标 = **当前运行模式 monitor**。
- `trap` 合法且被允许 ⇒ `CFXTRAP`，目标 = **目标 `cfxha`**。
- `cfx2rd`/`cfx2rc` 合法且被允许 ⇒ 正常寄存器访问，**不进入本流程**（不得把成功访问写成异常）。
- 非法核芯功能扩展寄存器访问 `CFXREG` ⇒ 目标 = **当前运行模式 monitor**，**不进入被访问的核芯功能扩展**。
- 两轴权限拒绝（`cfxtrap`/`cfxmem`/`cfxreg`/`cfxexe` mask 拒绝）与页表权限拒绝（HSJU 或 R/W/X 不符）统一 `CFXPERM` ⇒ 目标 = **当前运行模式 monitor**。
- `CFXMEM`（核内地址空间/内部存储故障）⇒ 目标 = **当前运行模式 monitor**，至少覆盖：
  - `ptw_enable = 0` 且 `addr[47:42] = 0` 的普通访存；
  - reserved cfx（`6–14`、`19–61`）的普通 `ld/st`；
  - SRAM/MMIO 越界或非法核内偏移；
  - 页表**未映射**（L1/L2 `P = 0`、SPF/GPF 对应小页位为 0、fragment 缺失）；
  - A/D 回写失败（PTE 物理写失败；`cause_info` = PTE 物理地址）。
- `ILLI`/`UNDI`/`RASOF`/`RASUF`/`MALIGN`/`IALIGN`（非 `trap`/`escape`/`cfx2*` 路径）⇒ 目标 = **当前运行模式 monitor**。
- `CFXESC`（`escape` 帧或目标错误）⇒ 目标 = **当前核芯功能扩展**（保持既有语义，不属于 monitor 路由）。
- 当前运行模式到 monitor 的对应关系：`U-mode → cfx_umon (cfx0)`、`J-mode → cfx_jmon (cfx1)`、`S-mode → cfx_smon (cfx2)`、`H-mode → cfx_hmon (cfx3)`；使用异常前运行模式对应的 `<mode>_*` 寄存器行。

**（2）monitor 异常编号**

明确 monitor 原因使用 DADAO 位索引，且逐项出现：

| 名称 | 位索引 |
| --- | --- |
| `CFXTRAP` | 0 |
| `CFXMEM` | 1 |
| `CFXREG` | 2 |
| `CFXESC` | 3 |
| `CFXPERM` | 7 |
| `ILLI` | 8 |
| `UNDI` | 9 |
| `RASOF` | 10 |
| `RASUF` | 11 |
| `MALIGN` | 12 |
| `IALIGN` | 13 |

`PTWERR` 不再出现在 §5.2 的 monitor 编号与投递目标中；A/D 回写失败已裁定按 `CFXMEM`（当前运行模式 monitor）处理，`cause_info` = PTE 物理地址；不得改为 `CFXPERM` 或 `cfx_ptw` 闭环。

**（3）异常进入步骤（重排为 8 步，删除原步骤 3）**

1. 确定异常原因与目标（按上表）。
2. 判断是否不可屏蔽：同步异常全部不可屏蔽，直接进入步骤 5；异步按原因表。
3. **异步中断来源过滤**（仅异步；`cfx_intr_mask`/`global_cfx_intr_mask`/pending 语义列入后续修订，本节不冻结）。
4. **异常原因 mask**（仅异步；同步跳过）。
5. 更新陷入计数（`trap_num`/`excp_sync_num`/`excp_async_num`）。
6. 保存现场：`excp_prev_run_mode`、异常前核芯功能扩展掩码状态（供 `escape` 恢复）、`excp_cause_ip`/`excp_cause_id`/`excp_cause_info`；`trap` 进入时另保存 `global_cfx_intr_mask` 并置全 1。
7. 模式/目标切换：`inner_run_mode` 取目标 cfx 的 `<mode>_switch_run_mode`，`inner_cfx_code` 取目标 cfx；**不切换独立 cfx 屏蔽层**。
8. 跳转至目标 cfx 的 `<mode>_excp_vector`。

**（4）`inner_cfx_mask` 约束**

- §5.2 正文与伪代码中**不得出现 `inner_cfx_mask` 标识符**（同步屏蔽层已拆除；状态保存用「异常前核芯功能扩展掩码状态」描述）。
- 不得再出现「若 `inner_cfx_mask` 为 1，同步异常触发 `ILLI`」一类语句。

**（5）异步中断边界（模型 A：monitor 第一处理者）**

- 必须有独立段落/条目写明：**执行过程中的异步中断先进入当前运行模式的 monitor**，不是直接进入源 cfx。
- monitor 拥有异步来源屏蔽、pending、分发决策；可自行处理并 `escape`，也可 `trap` 到源 cfx。
- monitor 处理期间的新事件**置 pending，不嵌套 monitor**；不得写成可递归进入 monitor。
- 具体的 pending 位布局、优先级/抢占顺序可列为后续修订，但“先入 monitor / 不嵌套 / monitor 可分发给源 cfx”三条必须定稿。
- 不得把未定的调度细节写成已定稿规则；同步路由段、异步入口段、异步调度待修订段须可区分。

**（6）伪代码**

按 8 步重写现有伪代码：删除 inner mask 判定与 mask 切换；同步分支按上述路由设置 `cause` 与 `temp_cfx_code`；`CFXREG`/`CFXPERM`/`CFXMEM`/`ILLI` 等同步目标均为当前 monitor；`CFXTRAP` 目标为 `cfxha`；`CFXESC` 目标为当前 cfx；**异步分支目标 = 当前运行模式 monitor**，monitor 再按来源决定自行处理或 `trap` 到源 cfx，并标注「处理期间新事件置 pending、不嵌套」。伪代码注释沿用现有风格，不引入新寄存器名。

### 2. `spec/DADAO-12-SEE-主管系统运行环境.md §1`（最小同步）

只改 `inner_*` 注记一处，改为（语义等价即可）：

> `inner_*` 为硬件内部寄存器（不对外暴露），用于异常处理流程中的中间状态保存。`inner_run_mode`（2 位）记录当前运行模式（0=user, 1=jail, 2=supv, 3=hypv），`inner_excp_cause_*` 等用于现场保存；`inner_cfx_mask`（64 位，per-hart）仅作为异步中断投递/`escape` 恢复的核芯功能扩展掩码状态，**不构成同步异常的独立屏蔽层**；异步屏蔽语义待后续修订（§5.2）。

硬性断言：§1 不再出现「`inner_cfx_mask` … 用于异常屏蔽判断」的表述；保留 `inner_run_mode` 四位编码说明。

### 3. 附录 `0.7.3-rc`（未发布）

在 `0.7.3-rc` 段追加一条（**不得写任务号/ADR/ISS 号/`.work` 路径**，`check-spec-changelog` 硬约束）：

> 异常进入流程重写：同步异常统一按「当前运行模式 monitor」路由（`CFXPERM`/`CFXREG`/`CFXMEM`/`ILLI` 等）；`CFXTRAP` 仍进入目标 cfx，`CFXESC` 仍进入当前 cfx；删除同步异常的独立 cfx 屏蔽层；未映射页归当前 monitor 的 `CFXMEM`，页权限拒绝归 `CFXPERM`；monitor 原因编号沿用 DADAO 位索引，不再使用 `PTWERR` 作为 monitor 原因；异步中断屏蔽与 pending 语义列入后续修订，本版不承诺完整异步语义。

版本号仍为 `0.7.3-rc`（不发布、不改册头）。

### 4. `manifests/spec-readonly.lock.toml`

- 仅重算 `spec/DADAO-12-SEE-主管系统运行环境.md` 的 `sha256`；在 `dadao-12` 块注释追加 `2026-11-05（SPEC-186t，授权原话见任务书 §用户口径）` + 一句改动摘要（§5.2 重写、同步路由、拆同步屏蔽层、异步列后续）。
- 其它 20 册 `sha256`/注释一字不动；尤其 `Machine-v5`、`DADAO-13`、`DADAO-22` 零 diff。

## 范围 / 非范围

**在范围内**：`spec/DADAO-12-SEE-主管系统运行环境.md`（仅 §5.2、§1 注记、附录 `0.7.3-rc` 一条）、`manifests/spec-readonly.lock.toml`（仅 `dadao-12` 块）、本任务书、`.tao/knowledge/milestones.md`（本行状态）、运行期证据（已清理，未归档）。

**不在范围内**（违反即越界）：

- `spec/DADAO-12` 的 §2（含 §2.2.6 异常检查优先级）、§3（含 §3.6 编号说明）、§4（含 §4.5 `cfx_ptw`/`PTWERR`）、§5.1、§5.3 及其它章节。
- `spec/DADAO-13`（HEE）、`spec/DADAO-22`（SBI）、`spec/Machine-v5`、其它 `spec/*` 册。
- `.tao/contracts/**`、`contracts/**`、`.tao/adr/**`、`.tao/knowledge/issues.yaml`。
- `components/**`、`tests/**`、`tools/**`、`Makefile`、门控脚本、退出码表。
- 版本发布、`spec/README.md`、`.tao/archive/**`、`.tao/knowledge/discussing.md`。

## 验收标准

1. **§5.2 路由可机械断言（脚本从 §5.2 正文派生）**：
   - `CFXPERM` 目标含「当前运行模式 monitor」；`CFXREG` 目标含「当前运行模式 monitor」且含「不进入被访问」；`CFXMEM` 目标含「当前运行模式 monitor」，且含 A/D 回写失败（`cause_info` = PTE 物理地址）、不含 `PTWERR`；reserved cfx 的 `ld/st` 归 `CFXMEM`、`trap`/`escape` 归 `ILLI` 且均为当前 monitor；未映射页归 `CFXMEM` 当前 monitor；页权限拒绝归 `CFXPERM` 当前 monitor；`CFXTRAP` 目标为目标 cfx；`CFXESC` 目标为当前 cfx。
   - monitor 编号 11 项逐项命中：0/1/2/3/7/8/9/10/11/12/13 与名称一一对应。
2. **`inner_cfx_mask` 同步屏蔽拆除**：§5.2 正文与伪代码中 `inner_cfx_mask` 出现次数为 **0**；无「同步异常触发 ILLI」的 mask 判定；§1 注记不再把它写成同步异常屏蔽层。
3. **异步边界（模型 A）**：§5.2 明确出现「异步中断先入当前运行模式 monitor」「monitor 可分发给源 cfx」「处理期间置 pending、不嵌套」；调度细节可有「后续修订」，但上述三条不得写成未定；同步路由段与异步段可区分。
4. **门控（逐条贴真实命令 + 命令自身 rc，禁 `| tee` 吞码）**：`make check-spec-readonly`、`check-spec-refs`、`check-spec-drift`、`check-spec-changelog`、`check-spec-numbering`、`check-spec-purity`、`check-spec-cite-targets`、`check-spec-codeblocks`、`check-issues`、`check-milestones-fresh`、`check-sync-nonmaskable` 全 **rc=0**；既有基线红须逐条与 `master` 对账（名称 + rc），不得以基线红掩盖本任务引入的红。
5. **只读锁**：`sha256sum spec/DADAO-12-SEE-主管系统运行环境.md` 与锁值逐字相等；锁 diff 仅 `dadao-12` 块（注释 + 1 行 sha256）；其它册 sha 不变；注记含日期 + 用户口径摘要。
6. **编号零漂移**：`git diff -U0` 证明 `DADAO-12` 的所有 `##`/`###` 标题行未变；§5.2 标题仍为 `### 5.2 异常进入流程`。
7. **反例可达 FAIL（≥2 处，`cp` 备份 + `md5sum -c` 还原，禁 `git checkout/restore/stash`）**：
   - 在 §5.2 注入一行 `inner_cfx_mask` 同步屏蔽判定 ⇒ 断言 2 FAIL；还原后回绿。
   - 把 `CFXPERM` 的位索引 `7` 改成 `6`（或把 `CFXREG` 目标改成「被访问 cfx」）⇒ 断言 1 FAIL；还原后回绿。
   - 注入/还原后 `git status --porcelain -uall` 与注入前快照逐行一致。
8. **越界零改动**：`git status --porcelain -uall` 与 `git diff --name-only` 仅含任务书、`spec/DADAO-12`、锁、`milestones.md`；不含 §2/§3/§4/§5.1/§5.3 以外的 `DADAO-12` 改动，不含 `DADAO-13`/`DADAO-22`/`Machine-v5`/`contracts`/`components`/`tests`/`tools`/`Makefile`；无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej` 残留。
9. **体例**：完成区 ≤30 行；证据落运行期临时目录（已清理，未归档；`run.sh`、`run.EXIT`、`*.log`）；状态置 `待验收`。
10. **未决处置**：§未决 1–3 若在下发前未确认，相关条目不得写入 §5.2；须在完成区逐条说明处置。

## 证据

- 一键证据脚本（运行期临时目录，已清理，未归档）：一条命令重跑「§5.2 路由断言 + §1 注记断言 + 全部门控 + 锁 sha 对账」，逐项取**被检命令自身** rc；输出 `RUN_EXIT`。
- 注入脚本（运行期临时目录，已清理，未归档）：两处注入 / `cp` + `md5sum -c` 还原 / 回绿，输出 `INJECT_EXIT`。
- 原始输出（运行期临时目录，已清理，未归档）：门控日志、`sha256sum` 前后快照、`git diff --stat`、标题行 `git diff -U0`。
- 完成区只写结论 + 命令 rc + 证据路径；证据不入库。

## 说明

- **§5.2 为唯一真源**：本任务只对 §5.2 的异常进入流程/原因路由负责；§2.2.6、§4.5、§3.6 仍保留旧的 `cfx_ptw`/`PTWERR` 表述，属已知跨节不一致，完成区必须登记，**不得声称全册已一致**；后续同步另立任务（见 §未决 2）。
- **`inner_cfx_mask` 寄存器面**：本任务只拆 §5.2 的同步屏蔽层与 §1 注记；`cfx_⟨cfxname⟩_<mode>_switch_cfx_mask`（含 DADAO-13 的 hypv 行）与 `excp_prev_cfx_mask` 的存废跨 DADAO-12/13、Machine-v5、contracts 与 QEMU，**不在本任务**（见 §未决 3）。
- **异步不冻结**：异步屏蔽只写「后续修订」，不得把未定稿的 mask/pending 细节写成已定；M11 语义边界以本任务书与 §5.2 为准。
- **0628 溯源（内容溯源，非执行必需）**：`DADAO-0628` 的异常进入仍是 `inner_cfx_mask`/`global_cfx_mask` 两级门 + `cfx_ptw`/`cfx_tlb` 独立目标；其任务书记录了同步异常绕过 mask 的实测观察。本项目定稿改为「同步统一当前 monitor、`CFXREG` 不进被访问 cfx、页表失败不投 `cfx_ptw`」，差异按本任务书落点，不复用 0628 常量/代码。
- **A/D 回写失败**：归 `CFXMEM`（当前 monitor），不是 `cfx_ptw` 闭环、不是 `CFXPERM`；`cfx_ptw` 只负责检测/报告。
- **版本**：不发布，仍 `0.7.3-rc`；附录只追加一条，不改册头。

## 未决（下发前需处理）

1. **A/D 回写失败（原 `PTWERR`）的最终落点（已裁定）**：按 `CFXMEM`（当前运行模式 monitor）处理；`cause_info` = PTE 物理地址；不进入 `cfx_ptw` 异常入口，不归 `CFXPERM`。用户原话：「不对，还是应该当前运行模式monitor的CFXMEM」。
2. **`cfx_ptw`/`PTWERR` 的跨节同步面**：`DADAO-12 §2.2.6`（页表异常进入 `cfx_ptw`）、`§4.5`（`PTWERR` 行/正文）、`§3.6`（`1 << 7` 在 cfx_ptw 为 `PTWERR`）与 `DADAO-22 §5.3`、`contract-see` 仍写旧口径；本任务范围仅 §5.2+§1。下发前须确认：(A) 允许本任务最小同步 §3.6/§4.5/§2.2.6（推荐，保持 DADAO-12 自洽）；(B) 只改 §5.2，旧口径留后续任务并登记 issue（会暂时保留跨节矛盾）。
3. **`inner_cfx_mask` 寄存器面**：`switch_cfx_mask`（cg0–cg3 rc9，hypv 在 DADAO-13）与 `excp_prev_cfx_mask`（cg5 rc1）是否保留/删除/标保留，跨多册与实现；本任务默认只拆 §5.2 同步屏蔽层、§1 注记，寄存器面留后续。若用户要求本任务一并删除，须扩大范围并另行授权。
4. **异步屏蔽「不冻结」的文本边界**：§5.2 可保留「目标 = 中断源 cfx」与「被屏蔽置 pending」的高层描述，但不得写死两级 mask/优先级；下发前确认是否接受该粒度。
5. **锁串行**：`SPEC-184t` 也改 `manifests/spec-readonly.lock.toml`；本任务须在其后执行/合入，避免锁 sha 互相覆盖。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
