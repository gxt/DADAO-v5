# SPEC-189t: DADAO-12 跨节异常原因表同步

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-186t`（§5.2 A/A1 模型定稿）、`SPEC-188t`（rc9/cg5 rc1 寄存器定义删除；同改 DADAO-12，须串行）
**状态**：已验证

## 执行环境
本地；只改 SPEC/合约的异常原因表与路由，不改 QEMU/gem5/tests 实现。

## 背景

`SPEC-186t` 只改 `§5.2`+`§1`；以下跨节仍写旧模型：

- `DADAO-12 §2.2.6`：页表异常“都进入 `cfx_ptw`”；原因名 `IGPTRAP`/`DGPTRAP`/`NUPERM`/`NJPERM`/`NSPERM`/`NHPERM`/`NXPERM`/`NWPERM`/`NRPERM`
- `DADAO-12 §3.6`：`1 << 7` 在 `cfx_ptw` 为 `PTWERR`
- `DADAO-12 §4.5` 原因表：`PTWERR` + `NUPERM`…`NRPERM` + `IGPTRAP`…`DSPFTRAP`
- `DADAO-22 §5.3`：A/D 回写失败报 `cfx_ptw` 的 `PTWERR`
- `Machine-v5`：`NUPERM` 等 PTW 权限层、`PTWERR` 旧描述
- `contract-see`：页表异常进入 `cfx_ptw`、A/D 回写失败报 `PTWERR`

这与 `§5.2` 的“执行期事件先入当前 monitor”冲突。

## 目标（与 §5.2/A1 一致）

1. 页表异常统一按当前 monitor 路由，原因收敛为：
   - `ptw_enable = 0`、`P = 0`、SPF/GPF 缺失、fragment 缺失、A/D 回写失败 ⇒ `CFXMEM`（当前 monitor）
   - HSJU 不符、R/W/X 不符 ⇒ `CFXPERM`（当前 monitor）
   - 取指/读写不再区分 `IGPTRAP`…/`NUPERM`…；`cause_info` 保留访存地址（A/D 回写失败用 PTE 物理地址）
2. `§4.5 cfx_ptw` 原因表只保留 cfx_ptw 自身可处理的显式原因（`CFXTRAP`、`CFXESC`）；删除 `PTWERR`/`NUPERM`…/页表缺失类原因。
3. `§3.6`：`1 << 7` 在 `cfx_ptw` 标 reserved；不再写 `PTWERR`。
4. `DADAO-22 §5.3`、`Machine-v5`、`contract-see` 同步：A/D 回写失败 ⇒ `CFXMEM` 当前 monitor；页表异常 ⇒ 当前 monitor；删除 `PTWERR`/`NUPERM` 旧口径。
5. 同笔重算 `dadao-12`/`dadao-22`/`machine-v5` 锁 sha；其它册不变。

## 接口规范

### 1. `DADAO-12 §2.2.6`

- 保留优先级顺序：IALIGN → ILLI/UNDI → MALIGN → 页表异常。
- 页表内部优先级保留：`ptw_enable=0` → L1 P/SP → SPF/GPF → L2 → HSJU → R/W/X。
- 原因名改为：前 5 类缺失/回写失败 ⇒ `CFXMEM`；HSJU/R/W/X ⇒ `CFXPERM`。
- 删除“取指 I 前缀/数据 D 前缀”原因名与“进入 cfx_ptw”句；改为“进入当前运行模式 monitor”。
- 不改变“只报最高优先级”规则。

### 2. `DADAO-12 §3.6`

- `1 << 7`：`cfx0`–`cfx3` 仍为 `CFXPERM`；`cfx_ptw` 标 reserved。
- 删除 `PTWERR`；其余位说明不动。

### 3. `DADAO-12 §4.5`

- 原因表删除 `PTWERR`（1<<7）与 `NUPERM`…`NRPERM`（1<<8–14）、`IGPTRAP`…`DSPFTRAP`（1<<16–23）。
- 保留 `CFXTRAP`（0）、`CFXESC`（3）；`CFXREG`（2）是否保留按“CFXREG 统一当前 monitor”删除。
- A/D 回写失败正文改为“按 `CFXMEM` 进入当前 monitor，`cause_info` = PTE 物理地址；失败条目保留”。
- 不改 TLB 寄存器表/命令语义。

### 4. `DADAO-22 §5.3`

- 标题与正文改为“A/D 回写失败（CFXMEM）”：`clean`/`flush` 失败保留条目，`excp_cause_info` = PTE 物理地址，进入当前 monitor 的 `CFXMEM`；不再提 `PTWERR`。

### 5. `Machine-v5` / `contract-see`

- 删除 `NUPERM`/`NJPERM`/`NSPERM`/`NHPERM` 与 `PTWERR` 旧描述；改为 `CFXPERM`/`CFXMEM` 当前 monitor。
- 保留“PTW 层权限”与“cfx 访问权限”区分的**结论**，但原因名改为 `CFXPERM`；不得把两者混同。

### 6. 锁

- 仅 `dadao-12`/`dadao-22`/`machine-v5` 重算；注记含日期 + 授权原话指针 + 改动摘要。

## 范围 / 非范围

**在范围内**：`spec/DADAO-12-*`（§2.2.6/§3.6/§4.5 的原因表/路由，及 §2.2.1/2.2.2/2.2.5/§5 中旧原因名/目标的机械同步；不改优先级/PTE 格式/结构；+ 变更记录）、`spec/DADAO-22-*`（§5.3 + §4 的 `SBI_PTW_*` 委托句机械同步 + 变更记录）、`spec/Machine-v5-*`（仅 PTW 权限/PTWERR 句）、`.tao/contracts/contract-see.md`、`manifests/spec-readonly.lock.toml`、本任务书、`milestones.md`、`ISS-344` 关闭。

**不在范围内**：`SPEC-186t` 的 §5.2/§1；`SPEC-188t` 的 rc9/cg5 rc1；QEMU/gem5/tests/LLVM；`contracts/` 机器数据；`Makefile`；门控脚本；退出码表（`SPEC-187t`）。

## 验收标准

1. **活文件清零**：`PTWERR`、`NUPERM`、`NJPERM`、`NSPERM`、`NHPERM`、`NXPERM`、`NWPERM`、`NRPERM`、`IGPTRAP`、`ISPTRAP`、`IGPFTRAP`、`ISPFTRAP`、`DGPTRAP`、`DSPTRAP`、`DGPFTRAP`、`DSPFTRAP` 在 DADAO-12/22/Machine-v5/contract-see 活文件 0 命中（历史段除外）。
2. **路由一致**：页表缺失/A/D → `CFXMEM` 当前 monitor；HSJU/R/W/X → `CFXPERM` 当前 monitor；`cfx_ptw` 不再是页表异常目标。
3. **原因表**：`§4.5` 仅保留 cfx_ptw 显式原因；`§3.6` 1<<7 在 cfx_ptw reserved；无 `PTWERR`。
4. **contract/Machine-v5**：A/D 回写失败、页表异常口径与 DADAO-12 一致；“两层权限”结论保留、原因名更新。
5. **锁**：三册 sha 与 `sha256sum` 逐字相等；其它册不变。
6. **门控**：`check-spec-readonly/refs/drift/changelog/numbering/purity/cite-targets/codeblocks`、`check-contracts-dir`、`check-contract-relocs`、`check-issues`、`check-milestones-fresh`、`make check`（L1）rc=0。
7. **反例可达 FAIL**：把 `PTWERR` 写回一处 ⇒ 断言 FAIL；`cp`+`md5sum -c` 还原后回绿。
8. **体例**：完成区 ≤30 行；状态 `待验收`。

## 说明

- 本任务只做 SPEC/合约；QEMU/gem5/tests 的页表异常原因、`PTWERR`、`NUPERM` 实现与期望值由后续实现任务处理。
- `§4.5` 删除大量原因后，`cfx_ptw` 的异常表可能只剩 `CFXTRAP`/`CFXESC`；若现场发现 cfx_ptw 仍需处理某类内部故障，先留问，不自行新增。
- 顺序：`SPEC-186t → SPEC-188t → SPEC-189t → SPEC-187t（退出码）`；`SPEC-188t/189t` 同改 DADAO-12，严格串行。

## 未决（下发前确认）

1. `§4.5` 是否保留 `CFXREG`（按“CFXREG 当前 monitor”默认删除）。
2. `Machine-v5` 的 PTW 权限段是否整段重写，还是只改原因名；默认只改原因名与 `PTWERR`。
3. QEMU/gem5/tests 实现任务是否本任务完成后按影响创建；默认是。

## 完成区

**测试结果**：一键证据 `run.sh` → `RUN_EXIT=0`（内容断言 35/35 PASS + 门控 16 项 rc=0）；`run.sh --inject` → `INJECT_EXIT=0`（PTWERR 注入、cfx_ptw 目标注入、DADAO-22 §4「SBI 委托 TLB 维护」注入 ⇒ 断言 rc=1；锁 sha 篡改 ⇒ `check-spec-readonly` rc=2；均 `cp`+`md5sum -c` 还原回绿，注入前后 `git status` 逐行一致）。
**修改文件**：`spec/DADAO-12-SEE-主管系统运行环境.md`（§2.2.1/2.2.2/2.2.5/2.2.6/§3.6/§4.5/§5 + 0.7.3-rc 一条）、`spec/DADAO-22-SBI-主管系统二进制接口.md`（§4 委托句/功能表 HANDLE_FAULT/§5.1/§5.3 + 0.7.3-rc 一条）、`spec/Machine-v5-测试机运行环境.md`（§1.2/§3 + 0.3.2-rc 一条）、`.tao/contracts/contract-see.md`、`.tao/contracts/contract-cfx-aliases.md`（生成器重生成，仅行号）、`manifests/spec-readonly.lock.toml`（仅 3 册注记+sha）、`.tao/knowledge/issues.yaml`（ISS-344 closed）、`.tao/knowledge/milestones.md`（本行）、本任务书、一键证据脚本（运行期证据，未归档）。
**验收结果**：① 16 个旧原因名在 4 文件**活正文** 0 命中（脚本现场统计，历史附录除外）；② 未映射/A-D 回写失败 ⇒ 当前运行模式 monitor `CFXMEM`（A/D 的 `cause_info` = PTE 物理地址），HSJU/R/W/X ⇒ 当前 monitor `CFXPERM`，`cfx_ptw` 非页表异常目标；③ §4.5 原因表仅 `CFXTRAP`/`CFXESC`，§3.6 `1<<7` 在 `cfx_ptw` 标保留；④ contract-see/Machine-v5 口径与 DADAO-12 一致、两层权限结论保留；⑤ sha256 DADAO-12 `271d20db…`、DADAO-22 `573d4792…`、Machine-v5 `aa6fae18…` 与锁逐字相等，其余 18 册不变；⑥ `check-spec-readonly/refs/drift/changelog/numbering/purity/cite-targets/codeblocks`、`check-contracts-dir`、`check-contract-relocs`、`check-issues`、`check-milestones-fresh`、`check-cfx-aliases`、`check-cfx-alias-table`、`check-sync-nonmaskable`、`make check`(L1) 全 rc=0。
**新发现/坑**：① 改 DADAO-12 行数会移动 `contract-cfx-aliases.md` 的 `DADAO-12:<line>` 投影 ⇒ 必须跑 `tools/spec/gen_cfx_aliases.py` 重生成（禁手改）。② `check-milestones-fresh` 要求未完成任务时间加「（登记）」；`待验收` 也属未完成。③ 任务书「仅 §2.2.6/§3.6/§4.5」与验收 1「活文件 0 命中」冲突；按验收 1/2 同步了 §2.2.1/2.2.2/2.2.5/§5 及 DADAO-22 §4 的旧路由句（只改原因名/目标，优先级与结构不变），已披露。④ 任务 worktree 的 `.work` 为指向主树软链，证据脚本须用 `git rev-parse --show-toplevel` 定根，不能用 `dirname $0`。⑤ 范围扩展曾把「TLB 维护」写进 §4 的 `SBI_PTW_*` 委托，与同册 §5「不提供 SBI 级 TLB 服务」冲突；已收敛为「页表步进与缺页处理」，并加断言/注入防回归。
**遗留问题**：① `spec/README.md` 的 `contract-mmu.md` 延迟注记仍含 `NUPERM` 等（不在本任务 4 文件验收范围与任务书范围，未改）。② QEMU/gem5/tests 的旧原因名实现/期望值未改（任务书 §说明 明确另立实现任务）。③ 本任务未 commit/push（按派单）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审方式**：自主逐行审查（`subagent_depth=1`，无嵌套子代理）。逐行核对 §2.2.1/2.2.2/2.2.5/2.2.6/§3.6/§4.5/§5、DADAO-22 §4/§5.3、Machine-v5 §1.2/§3、contract-see、锁、issue/里程碑、证据脚本与注入逻辑。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 任务书范围「仅 §2.2.6/§3.6/§4.5」与验收 1「活文件 0 命中」冲突：§2.2.1/2.2.2/2.2.5/§5 仍含旧名 | ✅已修 | 只改这些句的原因名/目标（未动优先级、PTE 格式、权限规则）；完成区披露 | 断言 A 4 文件 0 命中；`make check` rc=0 |
| F2 DADAO-22 §4 仍写「页表异常由硬件直接路由至 cfx_ptw」，与验收 2 冲突（任务书只列 §5.3） | ✅已修 | §4 路由句改为 monitor 接收、经 `SBI_PTW_*` 委托页表步进与缺页处理；§5.3 同步；披露 | 断言 I 无旧路由短语；`check-spec-refs` rc=0 |
| F3 改 DADAO-12 行数导致 `.tao/contracts/contract-cfx-aliases.md` 行号投影漂移 | ✅已修 | 用 `tools/spec/gen_cfx_aliases.py` 重生成（禁手改） | `check-cfx-aliases`、`check-cfx-alias-table` rc=0 |
| F4 §2.2.1/2.2.2 仍有「对应 PERM 异常」模糊表述 | ✅已修 | 两处改为「触发 `CFXPERM`」 | 断言 A 0 命中且 L1 rc=0 |
| F5 任务 worktree 的 `.work` 为软链，证据脚本按 `dirname $0` 定位根会读主树（首轮断言全红） | ✅已修 | `run.sh` 改用 `git rev-parse --show-toplevel`；checker 用 `SPEC189_ROOT` | `RUN_EXIT=0`；`--inject` 回绿 |
| F6 注入脚本硬编码旧 sha 且锁篡改返回 rc=2（`make` 语义），首轮 `INJECT_EXIT=2` | ✅已修 | 锁篡改改为按 path 定位 sha；期望值改 `nonzero` | `INJECT_EXIT=0` |
| F7 里程碑 `待验收` 时间未加「（登记）」，`check-milestones-fresh` rc=2 | ✅已修 | 时间改 `2026-11-05 13:10（登记）` | `check-milestones-fresh` rc=0 |
| F8 reviewer 指出 §4 把「TLB 维护」也列为 `SBI_PTW_*` 委托，与 §5「不提供 SBI 级 TLB 服务」及 §4 功能表冲突 | ✅已修 | §4 两处正文 + 变更记录 + 功能表 HANDLE_FAULT 只留「页表步进与缺页处理」；§5 结论与 cg12 寄存器接口不动，未新增 SBI TLB 功能码；引用改为 `DADAO-12 §2.2.6/§5.2` | 新增断言 F §4 无「TLB 维护」/`SBI_TLB`；`inject-4` 写回「TLB 维护」⇒ rc=1；还原回绿 |

**判决**：F1–F8 全部已修并复验；无未修 finding，状态保持 `待验收`。

#### 第 1 轮 reviewer 验收

**重跑（独立执行；审查期间产物曾被并发更新，以下为稳定树终态结果）**
- 一键证据 `run.sh` → `RUN_EXIT=0`：内容断言 rc=0 + 门控 16 项（14 个 `make` 门控 + `check-issues` + `make check` L1）全部 rc=0。
- `run.sh --inject` → `INJECT_EXIT=0`：inject-1/2/4 断言 rc=1、inject-3 `check-spec-readonly` rc=2，各 `md5sum -c` 还原 rc=0，注入前后 `git status` 逐行一致。
- 独立注入（与任务书注入不同；`cp`+`md5sum -c` 还原，未用 git 还原）：① §2.2.6「HSJU 不符 → `CFXPERM`」改写为 `CFXMEM` ⇒ 断言 FAIL rc=1（D/J 共 2 项）；② DADAO-22 §5.3 标题写回 `PTWERR` ⇒ FAIL rc=1（A/F/J 共 4 项）；还原后复跑 rc=0、`git status` 与注入前逐行一致。
- `check_content.py` → rc=0，**35/35 PASS**；16 个旧原因名在 4 文件**活正文 0 命中**（余 6 处均在「附录：版本与变更记录」）。
- 锁：三册 `sha256sum` 实算与锁内逐字相等（DADAO-12 `271d20db…`、DADAO-22 `573d4792…`、Machine-v5 `aa6fae18…`）；21 条目全匹配，vs HEAD 仅 3 册变化、条目数不变。

**约束核验**
1. 路由/原因表：§2.2.6 七级优先级与顺序未动，前 5 级 `CFXMEM`、后 2 级 `CFXPERM`、目标=当前运行模式 monitor；§4.5 表仅 `CFXTRAP`/`CFXESC`；§3.6 `1<<7` 在 `cfx_ptw` 保留；DADAO-22 §5.3、Machine-v5、contract-see 口径一致，两层权限结论保留。✅
2. 范围争议：DADAO-12 §2.2.1/2.2.2/2.2.5/§5 与 DADAO-22 §4 的改动**只改原因名/目标/委托句**，未动优先级、PTE 格式、结构与其它语义 ⇒ 判为验收 1/2 的机械后果，**可接受**（任务书 §范围表述冲突见 F3）。
3. 我首轮提出的阻断项已修并回归：DADAO-22 §4 原「`SBI_PTW_*` …页表步进与 TLB 维护」与 §5「不提供 SBI 级 TLB 服务」冲突 → 现功能表/两处正文/变更记录统一为「页表步进与缺页处理」；全册 `TLB 维护`/`SBI_TLB` 仅剩 §5 结论与历史附录；§5 原文未动；新增断言 + `inject-4` 可达 FAIL。✅
4. ISS-344 `status: closed`、`resolved_by: SPEC-189t`，其它 issue 字段未变；里程碑行 `待验收`。✅
5. 体例/范围：完成区 7 行（≤30）、无运行期路径；改动 9 文件与完成区声明逐一对账，无 QEMU/gem5/tests/`Makefile` 改动；验收标准段 diff 为空（未改判据）。✅
6. `spec/README.md` 的 `contract-mmu` 延迟注记仍含旧名 → 已在遗留问题①登记，非本任务 4 文件范围；完成区未声称全册一致。✅

**环境记录（非交付物缺陷，重试有据）**：① 首轮 `make check` rc=2，根因=并发任务 QEMU-083t 重建共享 QEMU 源码检出（reflog 12:51:04 +「锁内补丁集 == 该时点前源码 diff」证明此前一致；主树 `master` 同样红），环境恢复后任务 worktree/主树均 rc=0（重试 2 次）；② 临时盘瞬时写满打断 1 次注入，重试成功；③ 审查期间产物被并发更新（F8 + 证据脚本），一次 `run.sh` 因脚本被改写报 `syntax error line 134` rc=2 → 已对稳定树全量重验。

**Findings（均非阻断）**
- F3 任务书 §范围「仅 §2.2.6/§3.6/§4.5」与验收 1「活文件 0 命中」自相冲突 ⇒ 建议 architect 收尾时修订 §范围表述。
- F4 `spec/README.md` 旧注记遗留 ⇒ 建议并入 SPEC-185t 或另立册。
- F5 §4.5 注「未列出的位（含 `1<<1`/`1<<2`/`1<<7`）为保留」与同节「非法操作数 ⇒ `CFXREG`」、§3.6「不可恢复的错误」句有措辞张力 ⇒ 建议改为「不属于 cfx_ptw 可处理的原因（由 §5.2 monitor 表定义）」。

**判决：Accepted** —— 上述重跑在我方独立执行下全部通过、约束无违反；主会话可将状态改 `已验证`。

#### 收尾（architect，2026-11-05）

- F3：范围条款已改为实际同步面（§2.2.1/2.2.2/2.2.5/§5 + DADAO-22 §4），并注明“只改原因名/目标，不改优先级/结构”。
- F4：`spec/README.md` 旧注记（`NUPERM` 等）并入 `SPEC-185t` 的 README 索引清理范围。
- F5：§4.5 “保留位”措辞张力记入后续小项，不阻断本任务。
- 判决 Accepted，状态置 `已验证`。
