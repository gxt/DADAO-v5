# INTEG-048t: `cfx_*_cg_reg_deleg` 强制检查（QEMU 消费点缺失）

**模块**：integ
**项目里程碑**：M10
**依赖**：INTEG-044t（两轴权限模型/`CFXPERM` 落地）、INTEG-046t（Step5 启动链，写 `hypv_cg_reg_deleg` 但未强制）、INTEG-047t（SBI DMA，supv 直接访问 `cg15`）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 背景（问题根源）

1. **规范要求**：`DADAO-13 §1` cg3 `rc12` = `cfx_⟨cfxname⟩_hypv_cg_reg_deleg`，「cg 访问授权，`bit=0` 时允许 `supv` 访问，`bit3` 固定为 1」；`DADAO-23 §3` 要求各 cfx 的 `HBI_<name>_INIT` **清除自身**该寄存器（放开 supv 访问，cg3 固定禁止）。
2. **实现缺口（本轮实测）**：QEMU 只有存储点，无消费点——
   - `cpu.c.patch` 复位写 `mode[3].cg_reg_deleg = ~0ULL`（cg0–cg2 行写 0，无消费者）；
   - `helper.c.patch` 仅 `cfx_reg_ptr()` 的 `rc==12` 分支返回指针（写读均通），`helper_cfx2rd/cfx2rc` 中**没有**任何 delegation 判定；
   - 046t 遗留明确记「`cfx_*_cg_reg_deleg` 仅存储不检查，本任务只写值并断言 dump 值，权限强制另立任务」。
3. **现状实测（预检原型，`/tmp/opencode/INTEG-048t/proto.py`，QEMU md5 `72d6c653…`）**：
   - supv 下（`trap cfx0` 切入 S-mode，源 cfx=0）读 `cfx_ptw cg2 rc0`：`deleg=~0`（bit2=1，按 spec 应拒绝）→ **照样成功**，`rd5=0xFFFF_FFFF_FFFF_FFF7`、`rc=0`；
   - 同一路径 `deleg=0x…FFF3`（bit2=0）→ 成功（正例基线）；
   - user 模式（源 cfx=0、`deleg` bit0=1）读 `cfx_ptw cg0 rc0` → 成功（当前不区分模式，需保持「user/jail 不受 delegation 影响」）；
   - supv 下读 `cfx_ptw cg3 rc12` → **CFXREG**（`cid=1<<2`、`cinfo=0x7A443305`、目标 = 被访问的 `cfx_ptw`），即 cg3 已由「非 hypv ⇒ 不可见」规则挡住；
   - hypv 下写 `0x…FFF3` 后读回 **`0x…FFF3`**（bit3 可写 0）⇒「bit3 固定为 1」当前**未**实现。

## 目标（范围）

在 `helper_cfx2rd` / `helper_cfx2rc` 的访问路径上**新增 delegation 消费点**：`supv` 访问目标 cfx 的 cg 时，按该 cfx 的 `cfx_*_hypv_cg_reg_deleg` 对应位判定（`0=允许`、`1=拒绝`）；cg3 维持现状（非 hypv ⇒ `CFXREG`，固定禁止）；hypv 与 user/jail 不受本检查影响（沿用现有两轴模型）。

**前提**：先取得 §「语义缺口（BLOCKED）」四项裁定；未裁定前**不得**改 QEMU、不得猜异常类型/位范围/bit3 语义。

## 语义缺口（BLOCKED，须先裁定，不猜）

> 以下四项 **spec 正文均未直接规定**；现状由代码与旁证推导。请用户逐项裁定，裁定原话须原样写入本任务书。

- **R1 拒绝时的异常类型（阻断）**：`supv` 访问未授权 cg 时触发哪个异常？
  - 候选 a = **`CFXREG`**（`1<<2`，目标 = 被访问的 cfx，`cause_info` = 指令编码）：依据 = `DADAO-13 §1` 对 cg3 非 hypv 访问明确 `CFXREG`（同族「该模式不可见这些寄存器」）、`docs/DDLN/C-资源管理/DD-C005 §3/§4`（「supv 访问被禁止的 cg → `CFXREG`」）。
  - 候选 b = **`CFXPERM`**（`1<<7`，进入当前模式 monitor，`cause_info` = 指令编码）：依据 = `ADR-0045 D6`「权限拒绝 → `CFXPERM`，不是 ILLI」「有权但地址/寄存器非法 → `CFXMEM`/`CFXREG`」、`DADAO-12 §5.2`「目标 cfx 的 `cfxtrap`/`cfxreg` mask 拒绝源 cfx → `CFXPERM`」。
  - **反证**：`DD-C005 §4` 同段把 cfx mask 拒绝写成 `ILLI`，该句已被 ADR-0045/`DADAO-12 0.7.3-rc` 取代 ⇒ 该文档**不能单独作规范依据**。
  - **实现约束（无论哪项）**：cg3 必须**保持** `CFXREG`（`DADAO-13 §1` 明文）；若选 a，deleg 检查可覆盖 cg0–cg3（结果同类）；若选 b，deleg 检查**只覆盖 cg0–cg2**（否则 bit3=1 会把 cg3 的 `CFXREG` 改成 `CFXPERM`，回退现状）。
- **R2 `bit3` 值语义（阻断，牵动 046t 零回退）**：
  - 候选 a = **写时强制 1 / 读回 1**（0628 做法：`value | (1ULL << 3)`）；代价 = `tests/shared/bootrom/step5/hmon.S` 写 `0x…FFF3`、`smon.S` 自检、`min_rom_probe_integ046t.py::deleg_dump` 全部期望 `0x…FFFB`，须改 046t 产物（**超出「046t 零回退」**，需另行授权）。
  - 候选 b = **按写入值存储，仅靠「cg3 非 hypv ⇒ `CFXREG`」保证固定禁止**；代价 = 读回仍是 `0x…FFF3`（`bit3`≠1，字面不完全满足「固定为 1」）。
- **R3 位图覆盖范围（阻断，牵动 046t 启动链）**：
  - 候选 a = **仅 cg0–cg3**（低 4 位；cg≥4 不受 delegation 约束）；与派单口径一致，且 046t 零改动。
  - 候选 b = **bit 索引 = cg 编号、覆盖 cg0–cg63**（按「复位全 1」+「bit=0 允许」字面）；实测冲突：046t 的 `hmon.S` 对 `cfx_ptw`/`cfx_pmem` 只写 `0x…FFF3`，而 `smon.S`（supv）要访问 `cfx_ptw cg8/cg9`、`cfx_pmem cg15`、以及自身 `cfx_smon cg5` ⇒ 这些位全为 1，将全部被拒，**启动链直接失败**；选 b 必须同笔改 046t 的 deleg 常量（`0x8`）与 046t 探针，并重新验证 046t/047t。
- **R4 自身访问是否豁免（阻断-minor）**：spec 未写 `self` 例外（与两轴 mask 的「self 只绕过 cfx 轴」不同层）。
  - 候选 a = 不豁免（HBI §3「清除**自身** deleg」暗示自身访问也受位图约束）；候选 b = 豁免（supv 访问当前 cfx 自己的 cg 不查 delegation）。
  - 现状影响面：046t 的 smon 在 supv 只访问自身 `cg5`（不在 cg0–3，按 R3-a 不受影响）⇒ 两种候选对 046t 均零回退；但**新探针的期望值必须与裁定一致**（建议探针只用跨 cfx 目标 `cfx_ptw`，避免依赖 R4）。

## 接口规范（裁定后的最小改法，现行代码事实已核对）

1. **不改 `cfx_reg_ptr()` 签名**（它当前无 run-mode 参数）：该函数的职责保持「寄存器组合/读写权限不匹配 ⇒ `NULL` ⇒ 调用方报 `CFXREG`」，不掺入 delegation；否则无法在 R1 下独立选择 `CFXPERM`。
2. 在 `helper.c` 新增静态门（`helper.c.patch` 内，紧邻 `cfx_perm_denied()`）：
   ```c
   /* supv 访问目标 cfx 的 cg 需 hypv_cg_reg_deleg 对应位 = 0（DADAO-13 §1）。
    * 仅 supv；cg 范围与 cg3 处理按 R1/R3/R4 裁定。 */
   static bool cfx_deleg_denied(CPUDADAOState *env, int ci, int cg);
   ```
   判定数据源固定为 `env->cfx[ci].mode[DADAO_MODE_HYPV].cg_reg_deleg`（该字段只存于 `mode[3]`；`cfx_reg_ptr` 的 `rc==12` 亦取此行）。
3. 调用点：`helper_cfx2rd`/`helper_cfx2rc` 在 **`cfx_perm_denied(..., DADAO_CFX_PERM_REG)` 之后、`cfx_reg_ptr()`（及 `cg==15` pmem 特例）之前**插入：
   ```c
   if (cfx_deleg_denied(env, ci, cg)) { /* R1 裁定：cfx_raise(CFXREG, cfxha, pc, info) 或 cfx_raise_perm(env, info, pc) */ return; }
   ```
   顺序理由：reserved cfx → `ILLI`；未实现 cfx → `CFXREG`；cfxreg 轴 → `CFXPERM`；随后才是 delegation（`DD-C005 §4`「先 cfx 访问权限，再委派位图」，顺序按裁定冻结）。
4. **cg3**：不新增放行路径；`cfx_reg_ptr()` 中 `cg==3 && inner_run_mode != HYPV ⇒ NULL ⇒ CFXREG` 原样保留（回归用例锁死）。
5. **写侧**：仅当 R2-a 时，在 `helper_cfx2rc` 写 `cg3 rc12` 处做位掩码（`|= 1<<3`）；R2-b 不动写侧。
6. 复位值/`cpu.h` 布局**不改**（`mode[3].cg_reg_deleg = ~0ULL` 保留）。
7. 组件工作流（`docs/Process-01`）：改 `.work/source/qemu` 前/后各跑 `make check-source-state`；改完 `git reset --soft <base>` + 提交收敛为 base+1；`python3 tools/infra/make_patch.py qemu` 导出（**禁手改补丁**）；`make check-patch-tree`；`make build-qemu`；**必须** `make install-host`（安装根 `qemu-system-dadao` 才是门控/探针读的二进制）。预计增量重建 **1–3 min**（046t 实测约 1 min），不跑 `check-full`。

## 测试与证据（裁定后执行；每例须有可达 FAIL）

新增 `tools/testcases/arch/min_rom_probe_integ048t.py`（复用 044t 的 `bootstrap_rom()`/`observe()` 范式；body 先在 hypv/hmon，写目标 cfx 的 delegation 与 `cfx_ptw` 的 supv cfxreg 位，再 `trap cfx0` 切 supv，源 cfx=0）：

1. `deleg_deny_supv`：`deleg=~0`（bit2=1）+ ptw supv `cfxreg` 位0 清 0（排除 cfxreg 轴）⇒ 期望 R1 裁定的异常（cause/`cause_info=0x7A443305`/`cip`/目标 cfx 按裁定）；**FAIL 路径**：现状返回成功（预检已证）。
2. `deleg_allow_supv`：`deleg=0x…FFF3`（bit2=0）⇒ `cfx2rd` 成功、`rd5=0xFFFF_FFFF_FFFF_FFF7`；**FAIL 路径**：误报异常。
3. `deleg_hmon_toggle`：「hmon 设置前后差异」——同 ROM 内先 `deleg=0` 切 supv 读成功（`escape` 回 hmon 只作可选加强），或拆成 1/2 两例的成对断言（**推荐**：1+2 已构成前后差异，另在 2 内断言写前 `cfx2rd` 在 hypv 侧读回值 = 写入值）。
4. `cg3_always_cfxreg`：supv 读 `cfx_ptw cg3 rc12` ⇒ `CFXREG`（`cid=1<<2`、`cinfo=0x7A443305`、目标 `cfx_ptw`）；**FAIL 路径**：若 R1-b 误把 cg3 变成 `CFXPERM` 或放行。
5. `user_unaffected`：`deleg=~0`（bit0=1）、`cfx0` 切 user、读 `cfx_ptw cg0 rc0` ⇒ 成功；**FAIL 路径**：对 user 误加 delegation（预检原型已给出基线输出）。
6. `hypv_unaffected`：hmon/hypv 读 `cfx_ptw cg2 rc0`（`deleg=~0`）⇒ 成功；**FAIL 路径**：把 hypv 也纳入检查。
7. （可选）`jail_unaffected`：同 5，切 `switch_run_mode=1`。
8. 零回退：`make check-arch` 内 `044t/045t/049t/integ039t/integ040t/integ042t/integ044t/integ046t/integ047t` 与新探针全 PASS；`tests/shared/bootrom/step5/**` 默认零改动（R2-a 才改，需授权）。
9. 证据脚本 `.work/evidence/<任务ID>/{run.sh,check.py}`：默认全绿；`--inject` ≥2 处（建议：新门「bit2 判定」、cg3 回归断言）→ FAIL → `cp` 备份 + `md5sum` 还原 → 回绿，输出 `EVIDENCE INJECT: PASS`。

**门控**：`make check`、`make check-modules`、`make check-arch`、`check-patch-tree`、`check-source-state`、`check-component-changelog` 全 rc=0；`check-spec-readonly` 不受影响（不动 `spec/`）。

## 修改文件范围

- `components/qemu/patches/target/dadao/helper.c.patch`（唯一 QEMU 面；新增 `cfx_deleg_denied` + 两个调用点；R2-a 才加写侧掩码）。
- `components/qemu/changelog.md`（同变更追加一条，`Process-01 §10`）。
- `tools/testcases/arch/min_rom_probe_integ048t.py`（新）。
- `tools/testcases/arch/README.md`（表 1 行）。
- `Makefile`（`ARCH_CFX_PROBES` 加 `integ048t`）。
- `.tao/contracts/contract-see.md` §3：一条 delegation 投影（**仅在 R1/R3/R4 裁定后写**；若裁定认为 spec 缺正文不足以外投影 ⇒ 本条不写，缺口登记为另立 SPEC 任务）。
- `.tao/knowledge/milestones.md`（本任务书落盘已加流水 1 行；收尾只改状态/时间）。
- **条件文件（仅 R2-a 授权时）**：`tests/shared/bootrom/step5/{hmon.S,smon.S}`、`tools/testcases/arch/min_rom_probe_integ046t.py`（读回期望 `0x…FFFB`）。
- **不动**：`spec/**`、`manifests/**`、`contracts/**`（机器可读）、`tests/inst/**`、`docs/**`、`cpu.h.patch`/`cpu.c.patch`。

## 验收

1. §「语义缺口」R1–R4 均有**用户裁定原话**落纸（缺任一项 ⇒ 本任务不具备实现条件）。
2. 新探针 6–7 例全 PASS（每例有可达 FAIL）；`cg3_always_cfxreg` 与 `user_unaffected`/`hypv_unaffected` 全绿（证明未越界）。
3. `make check-arch` 全 PASS（新探针 + 既有 8 探针，零回退）；`make check`/`check-modules`/`check-patch-tree`/`check-source-state` rc=0。
4. 证据脚本默认与 `--inject` 均 rc=0（`EVIDENCE INJECT: PASS`），注入用 `cp`+`md5sum` 还原（禁 `git checkout/restore/stash`）。
5. `git diff` 证明 `spec/**`、`tests/shared/bootrom/**`、`contracts/**` 零改动（R2-a 授权除外）。
6. `install-host` 后 `.dadao/cross-toolchain/bin/qemu-system-dadao` md5 == `.work/build/qemu/qemu-system-dadao`（防旧安装根假绿）。
7. 完成区 ≤30 行、审阅记录每轮 ≤40 行；`**状态**` 置 `待验收`；临时目录 `/tmp/opencode/INTEG-048t/`。

**BLOCKED（如实登记，不得硬造）**
- R1–R4 四项语义裁定：spec 正文未定（R1 的「异常类型」在 0628 亦被其 `KL-111a` 记为「真正的 wiki 空白」）⇒ 未裁定前 QEMU 改动、探针期望、contract 投影全部 BLOCKED；替代证据 = 本任务书 §背景 3 的实测基线 + 上列 spec/ADR 引文 + 0628 只读对照。
- R3-b 会破坏 046t/047t 启动链（supv 访问 cg8/cg9/cg15 被拒）；若选 b，须另行授权改 046t 的 deleg 常量与探针，并重跑 046t/047t 全链。

## 约束

- 只做本任务；**不提交、不 push**（提交权归 architect）；不跑长构建/夜跑/`check-full`；重建前申报耗时（QEMU 增量 1–3 min）。
- 不改 `spec/**`（含 `manifests/spec-readonly.lock.toml`）；缺口登记，不越权补正文。
- `components/qemu/patches/**` **禁手工编辑**（`Process-01 §6.1.1`）；改源码树后导出。
- 失败保留现场并继续推进（自行处置/有据重试并记次数）；**仅需用户语义裁定**时留问。
- 临时/一次性产物一律 `/tmp/opencode/INTEG-048t/`；日志落 `.work/log/integ/`。

## 参考对照（`DADAO-0628` 只读检索；**内容溯源，非执行必需**，不复制代码、不作执行依赖）

- **0628 做法**：O1 只存储 `cfx_hypv_cg_reg_deleg[64]`，写路径 `value | (1ULL << 3)`（bit3 强制 1），注释明写「no permission enforcement reads it yet -- that is O2 scope」（`components/qemu/patches/0024-*.patch`）；`code-agent/tasks/KL-111a-*-permission-recon.md` 结论：「deleg 拒绝时的异常类别是真正的 wiki 空白」，并建议类比「读写权限不匹配 → `CFXREG`」。
- **本项目差异**：v5 已把 `cfxreg` 等两轴 mask 检查落地为 `CFXPERM`（ADR-0045），delegation 缺**唯一**消费点；v5 启动链在 supv 访问 `cg8/cg9/cg15`，对 R3 位范围形成硬约束（0628 无此链）。
- **建议落点**：在 `helper_cfx2rd/cfx2rc` 增加独立 gate（不照搬 0628 的 `| 1<<3`，会破坏 046t 读回断言）；异常类型/位范围以用户裁定为准。

## 用户授权原话

**主会话派单原话（原样落纸）**：

> 在 /mnt/tao/DADAO-v5，master 已含 INTEG-046t/047t，工作树干净。创建 `INTEG-048t` 任务书：`cfx_*_cg_reg_deleg` 强制检查（QEMU 实现缺口）。文件名放 `.tao/tasks/integ/`；先确认 048 未占用，若占用顺延。
>
> 任务范围（先调查现状再落纸，不要假设）：
> - 在 QEMU 的 `cfx2rd`/`cfx2rc` 访问路径强制 `hypv_cg_reg_deleg`：目标 cfx 的 cg 对应 bit=0 允许 supv 访问；bit=1 拒绝；cg3 固定 1（禁止）；hmon/hypv 路径按 spec 处理；user/jail 仍按现有权限模型。
> - 拒绝时按 spec 触发正确异常（先核 DADAO-12/13：是 CFXREG 还是 CFXPERM；不要猜）。
> - 不修改 `spec/**`；如 contract 投影需同步，限制在 `.tao/contracts/`。
> - 测试：deleg=0 允许、deleg=1 拒绝、cg3 固定拒绝、hmon 设置前后差异、模式轴不受影响、既有 044t/046t/047t 零回退。
> - QEMU 需重建；任务书要写清预检、预计耗时、证据脚本（注入→FAIL→cp+md5 还原→回绿）。
>
> 流程：… 若 `hypv_cg_reg_deleg` 位语义/异常类型有歧义，写 BLOCKED 并给替代证据，不要猜。

> **说明**：派单原话本身要求「不要猜」；本任务书据此把 R1–R4 立为 BLOCKED，**未**把任何候选写成已定决策。

## 下发前预检（5 项）

1. **任务书内部一致**：PASS（除 BLOCKED）——§接口规范 2–5 与 §测试 1–7 逐项对应；R1 的「cg3 保持 `CFXREG`」与 §测试 4 对应；R2/R3 的 046t 冲突与 §修改文件「条件文件」、§BLOCKED 对应。
2. **验证手段前置实际可用**（本轮实测）：PASS——QEMU `.work/build/qemu/qemu-system-dadao` 与安装根 md5 同为 `72d6c653…`；预检原型 `/tmp/opencode/INTEG-048t/proto.py` 已跑通 5 条基线（supv deleg=1 仍放行 / supv deleg=0 放行 / user 放行 / cg3→`CFXREG` `cinfo=0x7A443305` / deleg 读回 `0x…FFF3`）；`make check-source-state` 可用；`tools/infra/make_patch.py` 导出链与 `check-patch-tree` 既有绿。
3. **验收逐条可跑性**：部分 BLOCKED——验收 1（裁定原话）**必须先有**；验收 2 的 1/2/4/5/6 **现在可跑**（同一路径已被原型验证）；3/4/5/6 **现在可跑**（QEMU 增量重建 1–3 min 与 `check-arch` ~40 s，046t/047t 既有绿）；验收 3 的「零回退」在 R3-b 下**须改 046t 才可能绿** ⇒ 依赖裁定。
4. **与 `contracts/`、`tests/inst/` 一致**：PASS——只用既有指令（`trap`/`escape`/`cfx2rd`/`cfx2rc`/`ld.o`/`st.o`/`set.zw`/`or.w`），`contracts/opcodes.yaml` 无新增；`tests/inst/**` 不改；`contracts/` 机器可读目录不改。
5. **拟改文件 × `spec/` 清单**：**不命中**——`components/qemu/**`、`tools/testcases/arch/**`、`Makefile`、`.tao/contracts/contract-see.md`、`.tao/knowledge/milestones.md` 均不在 `spec/`；`manifests/spec-readonly.lock.toml` 不动 ⇒ 无 spec 授权需求。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
