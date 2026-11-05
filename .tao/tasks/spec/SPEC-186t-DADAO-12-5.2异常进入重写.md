# SPEC-186t: DADAO-12 §5.2 异常进入流程重写（同步路由定稿）

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-184t`（同改 `manifests/spec-readonly.lock.toml`，本任务须在其后串行，不得并发改锁）；`SPEC-183t`（DADAO-12 现行基线）
**状态**：已验证

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
> 「A1：删除 `inner_cfx_mask`、`switch_cfx_mask`、`excp_prev_cfx_mask`；monitor 用自身 `cfx_intr_mask` + `excp_pending`。寄存器定义删除另立 `SPEC-188t`。」（2026-11-05 裁定；本任务只改使用模型，不删 §3.x 寄存器定义。）
> 「跨节同步选 B：本任务只改 §5.2+§1；`§2.2.6`/`§3.6`/`§4.5` + `DADAO-22 §5.3` + `contract-see` 另立 `SPEC-189t`，过渡期不一致登记 issue。」（2026-11-05 裁定）
> 「异步中断屏蔽不冻结，明确列为后续修订，M11 不承诺完整异步语义。」
> 「退出码表归 `Machine-v5`，不在本任务；本任务只改 DADAO-12 异常流程/原因路由，不改 QEMU/gem5/tests/tools。」

## 目标

1. 整体重写 `spec/DADAO-12-SEE-主管系统运行环境.md §5.2`：执行期同步异常与异步中断都先进入当前运行模式 monitor（模型 A）；monitor 是第一处理者，可自行处理或 `trap` 到源 cfx；删除 `inner_cfx_mask`/`switch_cfx_mask`/`excp_prev_cfx_mask` 的**使用**；处理期间新事件置 pending、不嵌套；调度细节可列后续修订。
2. 同步 §1：`inner_*` 注记（删除 `inner_cfx_mask`，改为 monitor 的 `cfx_intr_mask` + `excp_pending`）＋异常归属句/表（同步/异步入口统一当前 monitor；地址转换异常不再进 `cfx_ptw`；外部中断先入 monitor；`umon/jmon/smon/hmon` 表项加异步中断；显式 `trap`/`escape` 仍隶属目标/当前 cfx）。保留 §2/§3/§4 其它内容不动；`global_cfx_intr_mask` 保留。
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

**（3）异常进入步骤（重排为 7 步；删除原同步 mask 步骤与 cause mask 步骤）**

1. 确定异常原因与目标（按上表）；执行期同步异常与异步中断目标均为当前运行模式 monitor。
2. 同步异常全部不可屏蔽，不查任何 cause mask；异步中断只按来源过滤（下一步），也不查 cause mask。
3. **异步中断来源过滤**（仅异步）：查 monitor 的 `cfx_intr_mask`（cg0–3 rc4）与 `global_cfx_intr_mask`（cg8 rc1）；被屏蔽时置 monitor `excp_pending`（cg5 rc5），不投递；`excp_cause_mask`/`excp_cause_nonmaskable` 不存在。
4. 更新陷入计数（`trap_num`/`excp_sync_num`/`excp_async_num`）。
5. 保存现场：`excp_prev_run_mode`、`excp_cause_ip`/`excp_cause_id`/`excp_cause_info`；`trap` 进入时另保存 `global_cfx_intr_mask` 并置全 1；**不保存 `excp_prev_cfx_mask`**。
6. 模式/目标切换：`inner_run_mode` 取目标 cfx 的 `<mode>_switch_run_mode`，`inner_cfx_code` 取目标 cfx；**不切换独立 cfx 屏蔽层**。
7. 跳转至目标 cfx 的 `<mode>_excp_vector`。

**（4）`inner_cfx_mask` 约束**

- §5.2 正文与伪代码中**不得出现 `inner_cfx_mask` 标识符**（同步屏蔽层已拆除；状态保存用「异常前核芯功能扩展掩码状态」描述）。
- 不得再出现「若 `inner_cfx_mask` 为 1，同步异常触发 `ILLI`」一类语句。
- A1：§5.2/§1 不再引用 `switch_cfx_mask`/`excp_prev_cfx_mask`/`excp_cause_mask`/`excp_cause_nonmaskable`；`escape` 不恢复 `excp_prev_cfx_mask`；`global_cfx_intr_mask` 仍按 trap 保存/escape 恢复。异步来源过滤用 monitor 自身 `cfx_intr_mask`（cg0–3 rc4），屏蔽期间 pending 用 monitor `excp_pending`（cg5 rc5）。寄存器定义删除由 `SPEC-188t` 负责，本任务不改 §3.x。
- 同步异常不可屏蔽：不得出现任何“cause mask 屏蔽同步异常”或“被屏蔽时改 ILLI”的语句。

**（5）异步中断边界（模型 A：monitor 第一处理者）**

- 必须有独立段落/条目写明：**执行过程中的异步中断先进入当前运行模式的 monitor**，不是直接进入源 cfx。
- monitor 拥有异步来源屏蔽、pending、分发决策；可自行处理并 `escape`，也可 `trap` 到源 cfx。
- monitor 处理期间的新事件**置 pending，不嵌套 monitor**；不得写成可递归进入 monitor。
- 具体的 pending 位布局、优先级/抢占顺序可列为后续修订，但“先入 monitor / 不嵌套 / monitor 可分发给源 cfx”三条必须定稿。
- 不得把未定的调度细节写成已定稿规则；同步路由段、异步入口段、异步调度待修订段须可区分。

**（6）伪代码**

按 7 步重写现有伪代码：删除 inner mask 判定与 mask 切换；同步分支按上述路由设置 `cause` 与 `temp_cfx_code`；`CFXREG`/`CFXPERM`/`CFXMEM`/`ILLI` 等同步目标均为当前 monitor；`CFXTRAP` 目标为 `cfxha`；`CFXESC` 目标为当前 cfx；**异步分支目标 = 当前运行模式 monitor**，monitor 再按来源决定自行处理或 `trap` 到源 cfx，并标注「处理期间新事件置 pending、不嵌套」。伪代码注释沿用现有风格，不引入新寄存器名。

### 2. `spec/DADAO-12-SEE-主管系统运行环境.md §1`（最小同步）

改 `inner_*` 注记，并同步 §1 的异常归属句/表（语义等价即可）：

> `inner_*` 为硬件内部寄存器（不对外暴露），用于异常处理流程中的中间状态保存。`inner_run_mode`（2 位）记录当前运行模式（0=user, 1=jail, 2=supv, 3=hypv），`inner_excp_cause_*` 等用于现场保存；A1 下不再使用 `inner_cfx_mask`，异步来源过滤与 pending 由 monitor 的 `cfx_<monitor>_<mode>_cfx_intr_mask` 与 `cfx_<monitor>_excp_pending` 承担；`switch_cfx_mask`/`excp_prev_cfx_mask` 的寄存器定义删除由后续任务负责。

硬性断言：§1 不再出现「`inner_cfx_mask` … 用于异常屏蔽判断」的表述；保留 `inner_run_mode` 四位编码说明。§1 的异常归属句不得再写「页表异常均由 `cfx_ptw` 处理」「外部设备异常由源 cfx 处理」；改为「执行期同步异常/异步中断先入当前 monitor，显式 trap/escape 才隶属 cfx」；`umon/jmon/smon/hmon` 表项含“同步异常与异步中断”。

### 3. 附录 `0.7.3-rc`（未发布）

在 `0.7.3-rc` 段追加一条（**不得写任务号/ADR/ISS 号/`.work` 路径**，`check-spec-changelog` 硬约束）：

> 异常进入流程重写：同步异常统一按「当前运行模式 monitor」路由（`CFXPERM`/`CFXREG`/`CFXMEM`/`ILLI` 等）；`CFXTRAP` 仍进入目标 cfx，`CFXESC` 仍进入当前 cfx；删除同步异常的独立 cfx 屏蔽层；未映射页归当前 monitor 的 `CFXMEM`，页权限拒绝归 `CFXPERM`；monitor 原因编号沿用 DADAO 位索引，不再使用 `PTWERR` 作为 monitor 原因；异步中断先进入当前运行模式 monitor，屏蔽/pending 由 monitor 管理，处理期间不嵌套；具体调度细节列入后续修订。

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
2. **屏蔽层拆除（A1）**：§5.2 正文与伪代码中 `inner_cfx_mask`/`switch_cfx_mask`/`excp_prev_cfx_mask`/`excp_cause_mask`/`excp_cause_nonmaskable` 出现次数均为 **0**；无「同步异常触发 ILLI」的 mask 判定；同步异常不可屏蔽；§1 注记不再把 `inner_cfx_mask` 写成同步异常屏蔽层。
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
- **跨节同步（B）**：`§2.2.6`/`§3.6`/`§4.5`、`DADAO-22 §5.3`、`contract-see` 的旧 `cfx_ptw`/`PTWERR`/`NUPERM` 口径由 `SPEC-189t` 重写；本任务完成区必须登记 `ISS-344`，不得声称全册已一致。
- **版本**：不发布，仍 `0.7.3-rc`；附录只追加一条，不改册头。

## 未决（下发前需处理）

1. **A/D 回写失败（原 `PTWERR`）的最终落点（已裁定）**：按 `CFXMEM`（当前运行模式 monitor）处理；`cause_info` = PTE 物理地址；不进入 `cfx_ptw` 异常入口，不归 `CFXPERM`。用户原话：「不对，还是应该当前运行模式monitor的CFXMEM」。
2. **`cfx_ptw`/`PTWERR` 的跨节同步面（已裁定 B）**：本任务只改 §5.2+§1；`DADAO-12 §2.2.6`/`§3.6`/`§4.5` + `DADAO-22 §5.3` + `contract-see` 由 `SPEC-189t` 收口；过渡期不一致登记 `ISS-344`。
3. **`inner_cfx_mask` 寄存器面（已裁定 A1）**：本任务只拆 §5.2/§1 的使用与描述，不删 §3.x 寄存器定义；`switch_cfx_mask`/`excp_prev_cfx_mask`/`inner_cfx_mask` 的定义删除由 `SPEC-188t` 负责。
4. **异步屏蔽文本边界（已裁定 A）**：§5.2 必须写「异步中断先入当前 monitor」「monitor 可分发给源 cfx」「处理期间置 pending、不嵌套」；具体 pending 位/优先级/抢占细节可列后续修订。
5. **锁串行**：`SPEC-184t` 也改 `manifests/spec-readonly.lock.toml`；本任务须在其后执行/合入，避免锁 sha 互相覆盖。

## 完成区

**测试结果**：返工后一键证据 `run.sh` → `RUN_EXIT=0`（断言 49/49 PASS + 门控 12 项 rc=0 + 锁/编号/范围全过）；注入 `--inject` → `INJECT_EXIT=0`（§5.2 注入 `inner_cfx_mask` 屏蔽行 ⇒ rc=1；注入 `excp_cause_mask` 屏蔽同步行 ⇒ rc=1；`CFXPERM` 7→6 ⇒ rc=1；均 `cp`+`md5sum -c` 还原回绿，注入前后 `git status` 逐行一致）。
**修改文件**：`spec/DADAO-12-SEE-主管系统运行环境.md`（§5.2、§1 注记/归属句/表项、附录 `0.7.3-rc` 一条）、`manifests/spec-readonly.lock.toml`（仅 `dadao-12` 块注记 + 1 行 sha）、`.tao/knowledge/milestones.md`（仅本行状态）、本任务书。
**验收结果**：`make check-spec-readonly`/`check-spec-refs`/`check-spec-drift`/`check-spec-changelog`/`check-spec-numbering`/`check-spec-purity`/`check-spec-cite-targets`/`check-spec-codeblocks`/`check-sync-nonmaskable`/`check-milestones-fresh`/`check-asm-prose` 全 **rc=0**；`python3 tools/infra/check_issues.py` **rc=0**；`make check`（L1，含 `check-cfx-aliases`）**rc=0**；§5.2 与 §1 的 `excp_cause_mask`/`excp_cause_nonmaskable` 计数均为 **0**（`inner_cfx_mask`/`switch_cfx_mask`/`excp_prev_cfx_mask` 在 §5.2 均为 0）；`sha256sum` = `5a220ea50610d5b36630938f242d85773b59e97c9e1f0f7e9d8c5ef0d88e037f` 与锁逐字相等；标题行零变更；改动文件 4 项、无残留。
**新发现/坑**：
- §1 增删行会移动 §3/§4 行号，`check-cfx-aliases` 逐字比对因 `DADAO-12:<line>` 漂移而红；把 §1 归属句并入原 3 条 bullet（保持行数）后 L1 回绿，无需改任务书未列的 `.tao/contracts/**` 生成物。
- 任务书 §(6) 原写「按 8 步」，与 §(3) 7 步自相矛盾；已按 §(3) 改为 7 步（仅一词）。
- 任务书保留集 `6–14、19–61` 是 INTEG-053t 前旧集；§5.2 沿用现行 `6–14、16–31、35–61`。
- §5.2/§1 不写 `excp_cause_mask`/`excp_cause_nonmaskable`/`PTWERR` 字面（连否定句也省略），避免 0 计数断言歧义。
**遗留问题**：
- `ISS-344`（未改 `issues.yaml`）：§2.2.6/§3.6/§4.5、`DADAO-22 §5.3`、`Machine-v5`、`contract-see` 仍为旧 `cfx_ptw`/`PTWERR`/`NUPERM` 口径，由 `SPEC-189t` 收口；**未声称全册一致**。
- `excp_cause_mask`（cg0–3 rc11）/`excp_cause_nonmaskable`（cg5 rc63）的**定义删除**仍待 `SPEC-188t`（本任务只删 §5.2/§1 的使用）。
- `§5.1`/`§5.3` 仍恢复 `excp_prev_cfx_mask`、`§3.x` 仍定义三件套，均由 `SPEC-188t` 处理。
- 未决处置：1 A/D→`CFXMEM`；2 跨节只改 §5.2+§1、`ISS-344`；3 只拆使用不删定义；4 三条冻结+调度后续；5 锁串行（基线已含 `SPEC-184t`）。均已落地。
- 已改 `milestones.md`（本行 `待开始`→`待验收`）；未 commit/push；已 `git merge master`（FF 到 `facd53fb`）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审方式**：自主逐行审查（`subagent_depth=1`，无嵌套子代理）。审查 §5.2 路由/编号/8 步/伪代码、§1 注记、附录条目、锁注记与 sha、改动范围。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 伪代码 step 6 的 `saved_global_cfx_intr_mask` 原写 `cfx_⟨cfxname⟩_global_cfx_intr_mask`（`⟨cfxname⟩`=目标 cfx）；`trap` 到非 monitor cfx 时会取目标而非「当前模式 monitor」，与步骤 6 正文不符 | ✅已修 | 改为 `cfx_⟨mode_monitor⟩_global_cfx_intr_mask`（保存与置全 1 同源） | 断言重跑 35/35 PASS；`run.sh --inject` 回绿；L1 rc=0 |
| F2 任务书保留集 `6–14、19–61` 与现行 spec（INTEG-053t 后 `6–14、16–31、35–61`）冲突 | ❌不修（以现行 spec 为准） | §5.2 写现行保留集；完成区披露 | §1 表 / §5.1 现行集一致 |
| F3 任务书 §1 模板点名两寄存器，与验收「0 引用」字面冲突 | ✅已修 | §1 改为不点名（语义等价，保留「后续任务删定义」） | 断言「§1 不引用两标识符」PASS |
| F4 `check-issues` 非 make 目标，直接 `make` 会 rc=2 假红 | ✅已修（脚本内改直调） | `run.sh` 用 `python3 tools/infra/check_issues.py` | 直调 rc=0 |

**判决**：F1/F3/F4 已修并复验；F2 按 spec 现行口径保留并披露。无未修 finding，状态置 `待验收`。


#### 第 2 轮 engineer 自审（返工：7 步 + 删除 cause mask/nonmaskable + §1 归属同步）

**自审方式**：自主逐行审查；已 `git merge master`（FF `d4f04582`→`facd53fb`，autostash 无冲突），按新版任务书重做。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 §5.2 仍保留“不可屏蔽判定 / 异常原因 mask”两步，且伪代码含 `excp_cause_nonmaskable`/`excp_cause_mask` | ✅已修 | 删两步，重排 7 步；伪代码 async 直接按来源过滤，注释重编号 1–7 | 断言 49/49 PASS；两标识符 §5.2/§1 计数 0 |
| F2 §1 异常归属仍写「均由 `cfx_ptw`」「由相应的核芯功能扩展处理」，表项只写同步异常 | ✅已修 | 表项改「同步异常与异步中断」；三条归属句改 monitor 首处理；`trap`/`escape` 归属并入首条 | §1 归属断言 5 项 PASS |
| F3 §1 新增一条 bullet 使 §3/§4 行号 +1，`check-cfx-aliases` 逐字比对红（`DADAO-12:434/433`） | ✅已修 | 把「显式 trap/escape」并入首条 bullet，§1 保持 3 行；不改 `.tao/contracts/**` | `make check`（L1）rc=0；`check-cfx-aliases` rc=0 |
| F4 注入脚本锚定旧步骤 2 文本，返工后失效 | ✅已修 | 改为锚定「（三）异常进入步骤」；新增 cause mask 注入 | `--inject` 三注入均 FAIL→还原回绿，`INJECT_EXIT=0` |
| F5 任务书 §(6) 仍写「按 8 步」 | ✅已修 | 改为「按 7 步」（一词） | `grep` 无「按 8 步」 |

**判决**：F1–F5 全部已修并复验；无未修 finding，状态保持 `待验收`。


#### 第 1 轮 reviewer 验收

**独立重跑**（分支 worktree `SPEC-186t`，HEAD `facd53fb` 未变；判定全部以本人命令输出/退出码为准）：

- 证据脚本 `run.sh`（运行期临时目录 `SPEC-186t-tmp/evidence/`）⇒ `RUN_EXIT=0`：`ASSERT SUMMARY: 49/49 PASS`；11 个 `make check-spec-*`/`check-sync-nonmaskable`/`check-milestones-fresh`/`check-asm-prose` + `python3 tools/infra/check_issues.py` 全 **rc=0**；锁 sha `5a220ea50610d5b36630938f242d85773b59e97c9e1f0f7e9d8c5ef0d88e037f` 与锁值逐字相等（本人另跑 `sha256sum` + 解析 lock，21 册仅 dadao-12 一 hunk）；锁 diff sha 行=2（-/+ 各 1）；`git diff -U0 | grep -E '^[+-]#{2,3} '` **rc=1（标题增删 0）**；改动文件 4 项、无 `*_tmp*/_gate*/*.orig/*.rej`。
- `run.sh --inject` ⇒ `INJECT_EXIT=0`：`mask`/`causemask`/`cfxperm-idx` 三注入均「非空 md5 变化 → 断言 `rc=1` → `md5sum -c rc=0` → 回绿 `rc=0`」，注入前后 `git status` 逐行相同。
- **独立注入 A（与任务书两处不同）**：§1「外部设备触发的异步中断先进入当前运行模式 monitor」→「由源 cfx 处理」⇒ `ASSERT §1 外部设备中断先入 monitor: FAIL`、`48/49`、**rc=1**；`cp`+`md5sum -c` 还原 **rc=0** ⇒ `49/49` **rc=0**。
- **独立注入 B**：§5.2 步骤3 `cfx_<monitor>_global_cfx_intr_mask`（cg8 rc1）→ `inner_cfx_mask` ⇒ `ASSERT §5.2 inner_cfx_mask 计数: FAIL — 实际 1`、**rc=1**；还原 **rc=0** ⇒ `49/49`。还原后 4 文件 md5 与 4 行 `git status` 快照 `diff` 均 **rc=0**（禁 checkout/restore/stash，全程 `cp`+md5）。
- `make check`（L1）3 次：#1 **rc=2**、#2 **rc=2**（唯一红 `check-run-artifacts`：10 个非法名全在共享 `.work/log/testcases/TESTCASES-099t-review/`，目录 born 12:09:20，为并发 TESTCASES-099t reviewer 写入；**master 主树同门控 rc=2、10 个名称逐条相同** ⇒ 环境/基线红，非本任务引入；未杀进程、未绕锁）；#3 该目录被 099t 清空后 ⇒ **rc=0**、`check-cfx-aliases: PASS (byte-identical)`。

**约束核验（逐条）**：§5.2 `inner_cfx_mask`/`switch_cfx_mask`/`excp_prev_cfx_mask`/`excp_cause_mask`/`excp_cause_nonmaskable`/`PTWERR` 计数均 **0**（§1 除 `inner_cfx_mask` 1 次且为「不再作为同步屏蔽层」否定句外，cause_mask/nonmaskable/PTWERR 均 0）；步骤恰 **7**，无“不可屏蔽判定/异常原因 mask”两步，步骤2 写明同步不可屏蔽，步骤3 仅 `cfx_intr_mask`（cg0–3 rc4，§3.1/§3.2/§3.3 行核对）+ `global_cfx_intr_mask`（cg8 rc1，§4.x 行核对）过滤、屏蔽置 `excp_pending`（cg5 rc5，§3.6 行 388 核对）；伪代码注释 1–7 与 7 步同步、async 直接进来源过滤；`trap` 保存/`escape` 恢复 `global_cfx_intr_mask` 保留（步骤5 + 伪代码 895–897）；A/D 回写失败 = `CFXMEM` 当前 monitor、`cause_info`=PTE 物理地址；§5.2 开篇 +（四）段写明「同步/异步先入当前 monitor、monitor 第一处理者、自行处理或 `trap` 到源 cfx、处理期间置 pending 不嵌套」，`CFXTRAP`→目标 `cfxha`、`CFXESC`→当前 cfx；§1 三句归属（地址转换不再 `cfx_ptw`、外部中断先入 monitor、显式 `trap`/`escape` 隶属 cfx）+ umon/jmon/smon/hmon 表项均含「同步异常与异步中断」；`§2.2.6`/`§3.6`/`§4.5`/`§5.1`/`§5.3` 与 HEAD **逐字相同**，`## 2/## 3/## 4` 行号 57/299/423 **未漂移**；`DADAO-13`/`DADAO-22`/`Machine-v5`/`contracts`/`.tao/adr`/`issues.yaml`/`Makefile` **零 diff**；`excp_cause_mask`（317/341/357）/`excp_cause_nonmaskable`（389）§3.x 定义**仍在**（留 SPEC-188t）；`ISS-344` `status: open`、完成区写明「**未声称全册一致**」；完成区 **17 行**（≤30）、无运行期路径、sha/49/12/rc 与真实输出逐条对齐；任务书仅改 `状态`、`8 步→7 步`（一词）、完成区、审阅记录。

**finding（不阻断，architect 收尾处置）**：F-a 证据未落 `.work/evidence/SPEC-186t/`，而落运行期目录且名带 `-tmp` 后缀，收尾按 `/tmp/opencode/<任务ID>/` 清理会漏删；F-b 任务书 §(6) 由 engineer 改词（8→7 步，与 §(3) 自相矛盾，已在完成区披露，语义与用户口径“删两步=7 步”一致）；F-c L1 的 `check-run-artifacts` 红源于并发 reviewer 的共享 `.work` 日志，建议收尾时以“目录已清空后的 rc=0”为最终口径。

**判决：Accepted**（验收命令在本人重跑下全部通过；L1 三次运行的 rc 差异已按环境/并发对账，非交付物缺陷）
