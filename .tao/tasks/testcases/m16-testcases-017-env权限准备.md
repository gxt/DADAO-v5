# m16-testcases-017: env 权限准备（执行环境起点 = cfx_hmon 源）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-testcases-015`（运行模式 env）、`m16-qemu-005`（cfx5 通用 cg0–cg7）已合入
**可并行分片**：否
**预估**：2–3 h（已追加：交付源改造 + 全量回归 + 测试适配）
**档位**：大改（复核 ≤60 min）
**状态**：已验证

## 背景

每个 cfx 测试都要在 H/S/U 下跑，但缺省的两轴来源掩码只允许源 `cfx_hmon`
（`DADAO-12 §3`，`0xFFFF_FFFF_FFFF_FFF7` 的 bit3=0）；015 的 env 只负责进入模式。
**用户方向（2026-11-22/23）**：执行环境起点必须是 hmon 源（cfx3）、body 一份、
env 三份各管自己的模式；用例声明 `cfx_access` 即白名单，未声明访问必须 fail-closed。

## 要做（全部完成）

1. **BootROM 交付**：`tests/ee-vast/hmon_vast.S` 的 hmon 阶段直接 `jump` 到 ENTRY
   （源 cfx = cfx_hmon），不再写 `cfx_umon` 的 hypv 向量再 `trap`；power→hmon 阶段
   与固件 fault policy 不变。
2. **env 三份**：hmon 只做准备后直跳；smon/umon 在 hypv 下按 `cfx_access`
   **打开**声明的 cfx（掩码 + `cg_reg_deleg`）、**收窄**未声明的 cfx，再
   `trap cfx_hmon` 降模式；退出回 hypv 还原（打开项）并回读校验。
3. **接线**：`platform.py` 把 `cfx_access`/`--bootrom`/`--cache-model` 交给
   环境型驱动；`check_mode_env.py` 落成逐 cfx 的 `--defsym ENV_CFX_ACCESS_<n>=1`
   并给 llvm-mc 传 `-I tests/arch/common/env`（单份 `cfx_perm.inc`）。
4. **测试适配**（本轮新增）：
   - `arch-umon-002`：不再拿 `cfx_jmon` 当反例（J 不纳入 M16），改为先把
     `cfx_smon`（cfx2）hypv 行 `cfxtrap` 的 bit3（源 cfx_hmon）置 1，再
     `trap cfx_smon` ⇒ `CFXPERM`；同步 `@m5` 头与 `expected.yaml`。
   - `arch-umon-011`：槽 2/3 换成与交付无关的观测点（`cfx_id`、第二个暂存寄存器
     写后回读），保留三模式签名验证。
   - **未声明 ⇒ `CFXPERM`**：env 收窄未声明 cfx（`cfx_hmon` 是源 ⇒ 跳过；
     `cfx_umon` 的 `rc0` 保留给环境自用的 trap 回落；`cfxreg` 最后写且不读回——
     self-lockout）。
5. **cfx5 + supv**：`m16-qemu-005` 之后 cfx5 走通用 `cg0`–`cg7` ⇒ `cfx_access:
   [cache]` 可在 **hmon/smon/umon** 三模式访问（实测三模式签名一致）。
   **ISS-520（open）当前状态**：共享 `.work/source/qemu` 仍旧态（`helper.c` 缺 002/003、qemu 段 8 条 ⑥⑨ 未清）、
   `.work/build/qemu/qemu-system-dadao` 已重建（`md5 dd831552…97fd`），但
   **安装根 `.dadao/cross-toolchain/bin/qemu-system-dadao` 仍是旧态**（未跑
   `make install-host`）⇒ 证据取「最新构建的那个」并按 md5 基线比对（见下）。

## 不做

- 不改 cfx 实现、不改 RTL 的 U/S 路由（020）；
- 不改写既有用例的观测语义（本轮 002/011 的改法由用户 2026-11-23 指定）。

## 约束

- 独立 `git worktree`；**不提交 git**；变更集限 `tests/arch/common/env/**`、
  `tests/arch/modes.yaml`、`tests/arch/run_arch.py`、`tests/arch/common/platform.py`、
  `tests/arch/umon/check_mode_env.py`、`tests/arch/umon/m5_perm_mask_cfxperm.s`、
  `tests/arch/umon/mode_regs.body.S`、`tests/arch/umon/expected.yaml`、
  `tests/arch/README.md`、`tests/ee-vast/hmon_vast.S`、本任务书；
- 不写运行期路径；术语「寄存器组」；BootROM 证据构建落运行期私有目录（不动共享
  安装根）。

## 验证

运行期证据目录内的 `run.sh`（正向判据 + 全量回归 + 4 路注入 + 门控）：

1. 权限准备：声明 cfx4 后 smon/umon 都能读到 cfx4 的寄存器（deleg 打开的效果），
   另一模式行不被触碰；未声明 cfx5 被收窄（反汇编计数）；
2. 代表验证 **cfx5**：三模式各退出 0、`-d cpu` 观测 MODE=3/2/0、签名逐槽相同；
3. 未声明 ⇒ `CFXPERM`：umon 走 `0xE0` + cause、hmon 走固件记录；
4. 交付源 cfx = cfx_hmon：hmon 下写 cfx4 的 hypv 行掩码不报异常；
5. 全量回归 26 条全 PASS；`check-tests-index`/`check-tasks`/`check-knowledge-refs` 记录 rc；
6. 可达 FAIL：4 路注入（不写 deleg / 还原写错值 / 不收窄未声明 cfx / 交付回退到
   `trap cfx_umon` 并重建 BootROM），注入→红→`cp`+md5 还原→回绿。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` **rc=0**：工具链自检（含「缺 llvm-mc ⇒
exit 2」反例）PASS、正向判据 **45 项全 PASS**、全量回归 **26/26 PASS**
（`runner rc=0 ∧ 判决 26 条 = 现场派生 26 条 ∧ 全 PASS`）、**5 路**注入全绿、门控
rc 记录（见下）；`run.sh --inject` 单独跑 **rc=0**。QEMU = 共享构建树产物
`md5 dd831552353a3dcbb70719c3a80297fd`（qemu-005 之后；**安装根仍是旧态**，待
`make install-host` 刷新，见 ISS-520）。

**修改文件**：
- `tests/ee-vast/hmon_vast.S`（hmon 阶段 `jump` 到 ENTRY，源 cfx = cfx_hmon）；
- `tests/arch/common/env/{hmon,smon,umon}/env.S` + 新增 `common/env/cfx_perm.inc`
  （单份权限准备宏块）+ `common/env/env.lds`（新增 `.envperm` 段 @ +0x4000）；
- `tests/arch/common/platform.py`、`tests/arch/umon/check_mode_env.py`
  （`--cfx-access`/`--bootrom`/`--cache-model`、`-I` env 目录、`ENV_PERM_OFF`、
  槽 2/3 期望、`cfx_id` 现场解析）；
- `tests/arch/umon/m5_perm_mask_cfxperm.s` + `umon/expected.yaml`（改用 cfx_smon 反例）、
  `tests/arch/umon/mode_regs.body.S`（槽 2/3 换与交付无关的观测点）；
- `tests/arch/modes.yaml`（`arch-umon-011` 声明 `cfx_access: [umon]`）、
  `tests/arch/run_arch.py`（声明校验 + 「权限准备只留一份宏块」自检）、
  `tests/arch/README.md`、`common/env/{README.md,MIGRATION.md}`、本任务书。

**验收结果**（真实输出摘要）：
- 交付源：hmon 下写 `cfx4` 的 hypv 行掩码不报异常（fault-record cause=0）⇒ 源 cfx=3。
- 权限准备：smon 声明 cfx4 ⇒ supv body 读到 `cfx_id=4`/`ptw_enable=1`（deleg 缺省
  全 1 时不可能）、`cfxreg` 掩码保持缺省、cfx5 被收窄（4 次写）；umon 同（不碰 deleg）。
- **cfx5 代表验证**：hmon/smon/umon 三模式退出 0、MODE=3/2/0、签名
  `[exist=3, enable=3, 0xC5]` **逐槽相同**（D4 PASS）；supv 需要 qemu-005（已验）。
- 未声明：umon 访问 cfx4 ⇒ `0xE0` + cause `CFXPERM|[39]`；hmon ⇒ 固件记录同值
  （活体槽继续）⇒ 「未声明 ⇒ CFXPERM」成立。
- 回归：`arch-umon-002`（cfx_smon 反例）与 `arch-umon-011`（新槽 2/3）均 PASS，
  26 条全绿。
- 注入 4 路（均 `cp`+md5 还原回绿）：I1 不写 deleg ⇒ B 红；I3 还原写错 ⇒ B 红；
  I4 不收窄 cfx4 ⇒ E 红；I5 交付回退 `trap cfx_umon`（重建 BootROM）⇒ F 红。
- 注入 5 路（均 `cp`+md5 还原回绿）：I1 不写 deleg ⇒ B 红；I3 还原写错 ⇒ B 红；
  I4 不收窄 cfx4 ⇒ E 红；I5 交付回退 `trap cfx_umon`（重建 BootROM）⇒ F 红；
  **I6 runner 早退（`run_arch` 直接 rc=2、0 判决）⇒ 回归判据红**（不再 0/0 假绿）。
- 门控：`check-tests-index` rc=0、`check-tasks` rc=0、`check-knowledge-refs` rc=2
  （KNOWN-RED：`MEMORY.md:15`/`milestones-m18.md:39` 的 ADR-0059 不存在，与本次无关）。

**新发现/坑**：
- **收窄会 self-lockout**：`cfxreg`（rc2）一置位就再也读不到该 cfx 的任何寄存器 ⇒
  它必须最后写且只写不校验（其余三类 trap/mem/exe 照常回读校验）。
- **权限准备段会挤爆 4 KiB 窗口**：三份 env 全内联时 smon`.envcode` 达 4383 B
  （body 在 +0x1000）⇒ 新增 `.envperm` 段 @ +0x4000（只在 hypv 跑、不拷进 U 页）；
  umon 的收尾改为 `trap cfx_hmon` 回 hypv 还原（user 下写不了 cg3，tail 因此只剩 2 条指令）。
- `llvm-mc` 不搜索源文件所在目录；驱动给 `-I tests/arch/common/env` 后三份 env 才能
  共用单份 `cfx_perm.inc`（`run_arch --self-test` 机械防回退成多份）。
- `cfx5` 的掩码/`deleg` 在 qemu-005 之前是 `CFXREG`：不声明 cfx5 会被收窄（无误），
  声明它会因掩码写不进触发 `0xE2`——两种表现都指向「需要 qemu-005」。

**遗留问题**：
1. **ISS-520（open，口径分两句）**：① 共享 **`.work/source/qemu` 旧态** —— 仍旧态
   （`helper.c` 缺 002/003、qemu 段 8 条 ⑥⑨ 未清）；② **安装根旧态** —— `.dadao/cross-toolchain/
   bin/qemu-system-dadao` 仍是 qemu-005 之前的二进制，待 `make install-host`。
   ⇒ 证据用共享构建树产物（脚本按「最新构建」自动选，md5 基线
   `dd831552…97fd`，变化只 WARN 且要求复核）。**安装根刷新后必须复跑 `run.sh` 并
   重新标定基线 md5**。
2. 无其它遗留；上一轮的三项待裁定（cfx5+supv、`arch-umon-002`、`arch-umon-011`）
   已按用户 2026-11-23 的指定落地。

## 审阅记录

### 第 1 轮 engineer 自审（源 cfx0 方案，已被推翻）

首轮按「源 cfx0 + 打开掩码」实现，实测证明该前提不成立：cfx0 对其它 cfx 的
`cfxreg` 读/写均 `CFXPERM`，掩码写不进去；10 条 finding 全修，判决为「核心目标
阻塞，待裁定」。用户随后定方向 A（执行环境起点 = cfx_hmon 源）。

### 第 2 轮 engineer 自审（hmon 源交付）

交付改 `jump`（源 cfx=3）、三份 env 重写、接线打通；9 条 finding 全修（含
`trap cfx_hmon` 的向量冲突、smon 收尾往返、umon 的 cg3=CFXREG、cfx5 掩码不可写、
`cache-model` 未传、`-d cpu` 日志撑爆磁盘）。判决：24 PASS + 2 待裁定。

### 第 3 轮 engineer 自审（本轮：测试适配 + 收窄）

**审查范围**：`tests/arch/umon/m5_perm_mask_cfxperm.s`、`umon/expected.yaml`、
`umon/mode_regs.body.S`、`check_mode_env.py`（槽 2/3 期望 + `-I` + `ENV_PERM_OFF`）、
`common/env/cfx_perm.inc`（收窄）、三份 `env.S`、`env.lds`、`run_arch.py`（自检换形）、
证据脚本（QEMU 选择、检查项、注入点）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| H1 `cfx_jmon` 反例随源 cfx 变 3 失效（缺省掩码允许源 cfx3） | ✅已修 | 002 改为自置 `cfx_smon` 的 hypv `cfxtrap` bit3 再 `trap cfx_smon`；`@m5`/`expected.yaml` 同步 | 回归 `arch-umon-002` PASS（cause=CFXPERM，退出 0x21） |
| H2 `arch-umon-011` 槽 2/3 是入口 trap 现场（交付改跳转后恒 0） | ✅已修 | 换 `cfx_id`（cg4 rc0）+ 第二个暂存寄存器 rc1 写后回读；期望从 `spec §3.5`/`§1` 现场派生 | 三模式 PASS（签名 `[…, 0, 0xFEDC…]` 一致） |
| H3 未声明 cfx 仍可访问（源 cfx3 在缺省允许集内） | ✅已修 | `cfx_perm.inc` 增加**收窄**（未声明 ⇒ 源 cfx 位置 1）+ 豁免（cfx3 自身、cfx_umon 的 rc0） | E1/E2/E4/E5 PASS；I4 注入（不收窄 cfx4）⇒ E 红 |
| H4 收窄 `cfxreg` 后回读必失败（self-lockout） | ✅已修 | `cfxreg` 最后写、只写不校验；其余三类照常校验 | B/C/D 全绿（smon/umon/hmon 三模式） |
| H5 权限准备全内联超出 4 KiB（`.env` 重叠 `.body`） | ✅已修 | 新增 `.envperm` 段（`ENV_PERM_OFF=0x4000`，只在 hypv 跑）；umon 收尾改回 hypv 还原（tail 仅 2 条指令） | ld.lld 无重叠；B/C/D 全绿 |
| H6 cfx5 在 supv 下旧 QEMU 恒拒（`cg0`–`cg3` = `CFXREG`） | ✅已修（依赖 qemu-005） | 证据改用「最新构建」的 QEMU 并打印 md5；cfx5 声明 `[cache]` 走通用行 | D1–D4 PASS（三模式签名一致）；ISS-520 登记遗留 |
| H7 三份 env 各复制宏块（llvm-mc 无相对 include） | ✅已修 | 驱动给 `-I tests/arch/common/env`；只留 `cfx_perm.inc`；自检改为「都 include、无人内联」 | `--self-test` PASS；三 env 各只剩 3 行入口 |
| H8 注入点随宏块搬移失效（I1/I3 补丁找不到） | ✅已修 | `inject.py` 的补丁文件改到 `cfx_perm.inc` 并加唯一上下文；I4 换成「不收窄 cfx4」 | 4 路注入均「注入→红→还原→回绿」（run.sh --inject rc=0） |
| H9 证据 QEMU 与安装根不一致（ISS-520） | ✅已修 | `run.sh`/`check_perm.py` 取「最新构建」并打印路径+md5，`DADAO_QEMU` 可覆盖 | 全量 run.sh rc=0，日志首行含 QEMU md5 |

**判决**：正向 45 项 PASS、回归 26/26 PASS、4 路注入全绿；本轮用户指定的三项测试
适配与收窄语义均已落地并实测 ⇒ 状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-23）

**重跑（均在 worktree 根执行；日志落运行期证据目录）**
- `run.sh` 第 1 次 **rc=0**，但 `check_perm: PASS（45 项）` 之后 `check_regression:
  PASS（0/0 全 PASS）`，日志首行 `run_arch: ERROR: llvm-mc 不存在: <本工作树>
  .dadao/cross-toolchain/bin/llvm-mc` ⇒ **回归 0 条却报绿（假绿）**。
- 补齐 `.dadao`→共享安装根链接后 `run.sh` 第 2 次 **rc=0**：`check_perm 45/45`、
  `check_regression: PASS（26/26 全 PASS）`、I1/I3/I4/I5 均「基线绿 → 注入 rc=1
  （B 7/8、B 5/8、E 4/5、F 3/3 红）→ `cp`+md5 还原（744faccb…/75ebd77e…）→ 回绿」；
  门控 `check-tests-index rc=0`、`check-tasks rc=0`、`check-knowledge-refs rc=2`
  （悬空 `ADR-0059`×2 = `MEMORY.md:15`/`milestones-m18.md:39`，两文件不在变更集、
  目标文件确实不存在 ⇒ 基线红，与本任务无关）。
- `run.sh --inject` **rc=0**：4 路红→还原→回绿。
- **独立注入（reviewer）**：`cfx_perm.inc` 的 `ENV_PERM_DENY` 改 `0x0` ⇒
  `check_perm.py --only E` **rc=1**（E1/E2/E4 红）；`cp` 回备份 + md5 相等
  （`744faccb77aaaf7329aed2ec59088081`）后 **rc=0**。全程未用 `git checkout/restore/stash`。

**交付/三模式核验（本人 diff + 实测）**
- `hmon_vast.S`：hmon 阶段 `set.rb rb2, ENTRY` + `jump [rb2, rd0, 0]`（源 cfx=3）；
  全文 diff 仅 2 hunk（头注释 + 交接段），`hmon_fault`/固件向量未动；I5 回退
  `trap cfx_umon` ⇒ F1–F3 红（重建私有 BootROM 后），证明判据可达。
- 三份 env：hmon 直跳；smon/umon 在 hypv 写 **cfx_hmon** hypv 行
  `switch_run_mode`/`excp_vector` 后 `trap cfx_hmon`；B7 `[8,2]`（smon 开/还
  supv 行 4 类掩码 + `cg3 rc12` deleg 2 次）、C6 `[8,0]`（umon user 行、不碰
  deleg）；退出回读校验 ⇒ B1/C1 rc=0；`-d cpu` 实测 MODE=3/2/0（D1/D2/D3、B2、C2）。
- 收窄/豁免：`ENV_PERM_NARROW_ALL` 无 cfx3（self）、cfx0 `keep_trap=1`（rc0 留用）；
  E3 `[4,4]`；未声明 cfx4 ⇒ E1 `0xE0`(224)、E2 cause `0x8000000080`(549755814016)。
- cfx5 三模式签名 D4 `len(set)=1` 逐槽一致；**cfx4 无三模式同 body 签名**（B/C/F
  各用不同 body，任务书验证条款只要求 cfx5 作三模式代表 ⇒ 不算缺口）。
- 002 改 `cfx2rc cfx_smon,cg3,rc0` 置 bit3 → `trap cfx_smon`，`@m5`/`expected.yaml`
  derivation 已同步，回归 PASS；011 槽2=`cg4 rc0 cfx_id`、槽3=`cg6 rc1` 写后回读
  （期望由 spec 现场解析），三模式 PASS。以上均本人重跑，非采信完成区。

**cfx5 二进制判定：合规，但登记口径要补**
- 证据用共享构建树产物 `dd831552353a3dcbb70719c3a80297fd`（mtime 11-23 00:15，
  含 qemu-005：源树 `helper.c:2598`「cfx5 does not special-case them」）；安装根
  `1e8ff6e9…`（11-22 21:28）实测 `--only D` **16/16 全红**（0xE2）⇒ 不是「用错
  二进制假绿」，两二进制行为确实不同；路径+md5 每次打印、`DADAO_QEMU` 可覆盖。
- 残余风险：选择判据是 **mtime 最新**而非「含 qemu-005」⇒ 共享构建树被他人重建即
  静默换二进制。安装根刷新（`make install-host`）前，本轮证据基线应写死为
  `md5=dd831552…97fd`（md5 变化 ⇒ 打印 WARN 并要求复核），刷新后必须复跑 `run.sh`。
- 引用口径：任务书/README 把 **ISS-520** 写成「共享安装根仍是旧态」，而
  `issues.yaml:1391` 的 ISS-520 正文是「共享 `.work/source/qemu` 停在 002/003 之前
  旧态」；安装根旧态无对应 issue（文档级，交 architect 收尾订正/补登）。

**判决：Needs Revision**（仅证据脚本，交付本身已达标）
- **F1（阻断）`check_regression.py` 可达假绿**：不检查 `run_arch` 返回码、不核对
  用例数（现场派生自 `tests/arch` 索引），runner 报 ERROR 时 `0/0 全 PASS`、
  `run.sh` rc=0 —— 我第 1 次重跑即复现。修法：`proc.returncode != 0 ⇒ FAIL` +
  `len(verdict) != 索引用例数 ⇒ FAIL`。
- **F2（阻断）`run.sh` 工具链自检不完整**：只验 qemu，不验 `llvm-mc/ld.lld/
  llvm-objcopy`（`run_arch` 按 manifest 解析本工作树 `.dadao`）；`.dadao` 已存在但
  无 `cross-toolchain`（本工作树实测空目录链 `.dadao/tests/arch/probes`，合法产物
  路径）时符号链接被跳过 ⇒ 回归静默退化为 0 条。修法：建链/借用后显式 `-x` 校验
  三件工具，缺则 `exit 2` 并打印处置建议。
- 非阻断 finding：`check_perm.py`/`check_regression.py` 文件头 docstring 仍写
  「B=声明 cfx_umon」「E=实测仍成功 GAP」「24+2 待裁定」，与正文代码不符（文档级）。
- 采信项：门控 KNOWN-RED 的「与本次无关」判定（我核了变更集未触 `knowledge/` 且
  `ADR-0059` 文件全仓不存在）、engineer 完成区的 md5 数字（与我实测一致）。

### 第 4 轮 engineer 自审（返工：证据脚本四处）

**审查范围**：`check_regression.py`（F1）、`run.sh`（F2、F3、工具链反例、安装根子项链）、
`check_perm.py`/`check_regression.py` 文件头（F4）、`inject.py`（新增 I6）、
任务书/README 的 ISS-520 口径。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1（阻断）`check_regression.py` 假绿：不查 runner 返回码、不核对用例数 ⇒ `0/0 全 PASS` | ✅已修 | ① `proc.returncode != 0 ⇒ FAIL`；② 用 `run_arch.load_index()` **现场派生**条数（26），`len(verdict) != 派生数 ⇒ FAIL`；③ 逐例非 PASS ⇒ FAIL | **I6 注入**（`run_arch.py` 直接 `return 2`）：`runner rc=2；判决 0 条 / 现场派生 26 条` ⇒ `check_regression: FAIL`；还原后 `runner rc=0；判决 26 条 / 现场派生 26 条：PASS 26` ⇒ PASS |
| F2（阻断）`run.sh` 工具链自检不完整（只验 qemu），`.dadao` 已存在时软链被跳过 | ✅已修 | ① 工具链自检逐件 `-x`（qemu/llvm-mc/ld.lld/llvm-objcopy），缺件 `exit 2` + 处置建议（`make install-host` / `DADAO_TOOLCHAIN_BIN`）；② 安装根改为**按子项**补链（`cross-toolchain`、`tests/bootrom`），已存在则不动、结束只摘自己建的；③ 新增「只给 qemu、缺 llvm-mc ⇒ 必须 exit 2」的**反例自检** | `run.sh`：`缺 llvm-mc 时 exit 2: PASS (rc=2)`；全量 rc=0（回归不再 0 条） |
| F3 QEMU 选择按 mtime 最新 ⇒ 他人重建即静默换二进制 | ✅已修 | 证据基线写死 `QEMU_MD5_BASELINE=dd831552353a3dcbb70719c3a80297fd`；不符则打印 `WARN` 并要求**重新复核**（cfx5 三模式/收窄）+ 更新基线；`run.sh` 头注与任务书写明「`install-host` 后必须复跑」 | 本轮日志：`md5 = dd831552…97fd（证据基线 dd831552…97fd）`；反例路径已由「缺件 exit 2」自检覆盖 |
| F4（非阻断）两个证据脚本 docstring 与正文不符 | ✅已修 | `check_perm.py` 文件头重写（B/C=声明 cfx_ptw、D=cfx5 三模式、E=未声明⇒CFXPERM、无 GAP 项）；删掉已无用的 `gap()` 机制；`check_regression.py` 头改成三条硬判据（rc=0 / 条数=派生 / 全 PASS） | `grep gap check_perm.py` 无命中；两脚本 `ast.parse` 通过 |
| F5（本轮自查）`.dadao` 目录被门控建出后，整目录软链失效 ⇒ 回归又退化 0 条 | ✅已修 | 见 F2②（按子项补链） | 连续两次全量 `run.sh` 均 rc=0（第二次在门控已建 `.dadao/tests/` 之后） |

**判决**：F1–F5 全部 ✅；`run.sh` rc=0（正向 45 项 + 回归 26/26 + 5 路注入 + 门控），
`run.sh --inject` rc=0。状态置 `待验收`。

### 第 2 轮 reviewer 验收（2026-11-23）

**重跑（均本人终端输出；证据 = 运行期证据目录内的 `run.sh`）**
- 全量 `run.sh` 第 1 次 **rc=0**（real 1m21s）：工具链自检 PASS；内置「缺 llvm-mc ⇒ exit 2」PASS (rc=2)；`check_perm: PASS（45 项）`；`--self-test` rc=0；`check_regression: PASS（26/26 全 PASS）` —— `runner rc=0；判决 26 条 / 现场派生 26 条：PASS 26 / 非 PASS 0`，我现场 `grep -c` 判决行 = **26**（全 PASS，非 0/0）；I1/I3/I4/I5/I6 五路均「基线绿 → 注入 rc=1 → `cp`+md5 还原 → 回绿」；门控 `check-tests-index rc=0`、`check-tasks rc=0`、`check-knowledge-refs rc=2`（悬空 `ADR-0059`×2，`MEMORY.md:15`/`milestones-m18.md:39` 不在变更集、ADR 文件全仓不存在 ⇒ 基线红）。汇总 `run.sh: PASS`、`FINAL_RC=0`。
- `run.sh --inject` **rc=0**（real 52s，5 反例被抓住 / 5 回绿）；一切还原后的末次全量 **rc=0**、末次 `--inject` **rc=0**、日志 0 处 WARN。
- **假绿注入（本人独立做，非采信 I6）**：`cp`+md5 备份 `run_arch.py`（`d6d86122…`）⇒ A 在 `select_level(...)` 前 `return 2`（runner 早退、0 判决）→ `check_regression.py` **rc=1**（`runner rc=2；判决 0 条 / 现场派生 26 条` + 两条 FAIL）；B `cases = cases[:-1]`（runner 自身 **rc=0**、25/25 全 PASS）→ **rc=1**（`FAIL 判决条数 25 ≠ 现场派生 26`，计数判据独立成立）；两次还原均 **rc=0 / 26/26**、md5 与审前相等。首注入曾被「`run.sh` 收尾摘掉 `.dadao/cross-toolchain` 链 ⇒ `llvm-mc 不存在`」污染成假红，补链后重做（如实区分，不充绿）。
- **工具链自检（隔离注入，未动共享安装根）**：`DADAO_TOOLCHAIN_BIN` 指向临时目录三变体——缺 `llvm-mc` / `llvm-mc` 存在但 644 不可执行 / 只有 qemu ⇒ 三次均 **rc=2** 并逐件打印缺件与处置建议；`.dadao` 未被污染。
- **md5 基线**：临时把 `QEMU_MD5_BASELINE` 改 `000…000` ⇒ 打印 WARN 块（要求复核 cfx5 三模式/收窄并更新基线）且 `--inject` 仍 rc=0（只 WARN、不门控，符合设计）；`cp` 还原后 md5 `c3e1e4ce…` 与审前相等，末次全量 0 WARN（`dd831552…97fd` = 基线）。
- **ISS-520 口径与当前事实不一致（文档级，记 finding）**：② 安装根旧态**属实**（`1e8ff6e9…` 11-22 21:28 vs 构建树 `dd831552…` 11-23 00:15）；①「共享 `.work/source/qemu` 已刷新」**不属实** —— `helper.c` 仍 3322 行、0 处 `dcache`/`tb_invalidate_phys_range`（正是 ISS-520 登记的旧态，缺 002/003 段），`tools/infra/check_patch_tree.py` 真实 **rc=1、qemu 段 8 条 ⑥⑨**（`dadao-machine.c/cpu.c/cpu.h/helper.c`）与该 issue 症状逐条相同，源树 HEAD 00:17 早于 005 合入 00:46 ⇒ 任务书 L40/L125、`common/env/README.md` L107、`MIGRATION.md` L52 须改回「源树仍旧态 + 安装根仍旧态」两句，**ISS-520 不得关闭**；附带：证据 QEMU 二进制亦无 `dadao-dcache` 字样（缺 002），但 45 项/26 条期望值由 spec 现场派生、不依赖 002/003 ⇒ 不影响本轮证据成立。
- **约束核验**：审前/审后 `git status --porcelain -uall` 逐行相同（17 项 = 完成区「修改文件」17 项）；`run_arch.py`/`cfx_perm.inc`/`hmon_vast.S`/`run.sh`/`check_regression.py` 五个 md5 与审前逐一相等；全程 `cp`+md5 还原，未用 `git checkout/restore/stash`；未提交 git；本记录无运行期具体路径。
- **判决：Accepted** —— F1–F4 返工项在本人重跑下全部成立；ISS-520「源树已刷新」一句为文档级事实错误 ⇒ finding，由 architect 收尾订正，不另开一轮。
