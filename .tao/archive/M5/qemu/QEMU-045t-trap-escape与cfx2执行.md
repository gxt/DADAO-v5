# QEMU-045t: `trap`/`escape` 语义 + `cfx2rd`/`cfx2rc` 执行

**模块**：qemu
**项目里程碑**：M5
**依赖**：`SPEC-115t`、`SPEC-114t`、`QEMU-044t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `SPEC-115t`（4 条 re-scope）+ `SPEC-114t`（SEE §5 正文）+ `QEMU-044t`（cfx 寄存器文件 + 异常进入流程 + 权限/mask）。
  - `spec/SimRISC-11-其它.md`（`trap cfxHA, immu18`；`escape cfxHA, [excp_cause_ip, imms20]`；`cfx2rc`/`cfx2rd cfxHA, cgHB, rcHC, rdHD`；简化 regname 写法；L80 任意模式执行；L121 reserved/不存在组合）。
  - `spec/DADAO-22-SBI §1`（调用约定：`trap` 陷入目标 cfx；被调方 `escape cfxha, [excp_cause_ip, 4]` 返回下一条；参数与 ABI 一致）；`spec/DADAO-12 §5`（异常进入流程步骤 1–10；**异常退出流程** §5 伪代码——步骤 0 `escape` cfx mask 检查 + 1 恢复 `prev_cfx_mask` + 2 恢复 `prev_run_mode` + 3 `escape_num`++ + 4 计算返回地址 `excp_cause_ip + (imms18<<2)`）。
  - `.tao/adr/adr-0020-see-semihosting.md`（`Accepted`，**D10 两条路**）。
  - `contracts/opcodes.yaml`（`trap_ciii_cfx`/`escape_ciii_cfx`/`cfx2rc_crrr_cfx`/`cfx2rd_crrr_cfx` 编码）。
- **输出**（组件源码改在 `.work/source/qemu`；**导出补丁**）：
  0. **范围调整（见「审阅记录 · 044t/045t 边界处置说明」）**：`QEMU-044t` 已把 `trap`/`escape`/`cfx2rd`/`cfx2rc` 的 **decode→流程接线与基础执行** 落地（`trans_*_cfx` 由 ILLI 桩改为 `gen_helper_cfx_*` + `exit_tb`；`helper_cfx_trap`/`helper_cfx_escape`/`helper_cfx2rd`/`helper_cfx2rc`，见 044t 完成区实测）。本任务**不再重复实现**这些触发路径，只在其**基线**上**深化并验证完整语义 + 交付独立专探针/向量**。
  1. **在 044t 基线上深化/验证完整语义**（以读写 + **回读校验**为主；发现 044t 基线缺口时补齐）：
     - **`trap` 完整语义（一般 trap）**：`trap cfxHA, immu18`（`immu18[17:16] ≠ 2'b11`）→ `cause = CFXTRAP`（`1<<0`）→ **进入该 cfx 的向量**（`cfx_⟨cfxname⟩_<mode>_excp_vector`）；核对 `cause_id`/`cause_ip`/`cause_info`；reserved cfxha（7–14、19–61）⇒ **ILLI**（重定向到当前 mode monitor）；指令类型 `trap_cfx_mask` 禁止 ⇒ **ILLI**。
     - **`escape` 完整语义（异常退出流程）**：步骤 0 `escape_cfx_mask`（**跨 cfx**：非自身 cfxha 且禁止 ⇒ ILLI）；1 恢复 `inner_cfx_mask`←`excp_prev_cfx_mask`；2 恢复 `inner_run_mode`←`excp_prev_run_mode`；3 `escape_num`++；4 `PC ← excp_cause_ip + (imms18 << 2)`（**含负偏移回退**：`imms18` 18 位**有符号**展开、字节偏移 `%4==0`，与 `Toolchain-01 §3.2` 一致）。
     - **`cfx2rd`/`cfx2rc` 全寄存器面深化**：`cfx2rd cfxHA, cgHB, rcHC, rdHD`（读 cfx 寄存器 → `rdHD`）；`cfx2rc`（写 `rdHD` → cfx 寄存器）；读写覆盖 cfx 的 cg0–cg7 **全集**（含 RO/RW、`scratch_regs_num` 边界、cg3 仅 hypv）；**reserved cfxha ⇒ ILLI**；读写不存在/超出数量的寄存器组合 ⇒ **CFXREG**（`DADAO-12:373`/`SimRISC-11:121`）；经 `set.zw`/`or.w` 构造并**回读校验**。**简化 regname 写法**在汇编期已展开（`LLVM-060t`），QEMU 侧只见标准三操作数编码。
  2. **专探针/向量**：`tools/qemu/min_rom_probe_045t.py`（或 `.work/evidence/QEMU-045t/`）——一般 trap 进入向量并可由 `escape` 返回；`escape` 恢复模式/掩码、`escape_num` 递增、**负偏移回退**、**跨 cfx escape**；`cfx2rd`/`cfx2rc` **全寄存器面**读写正确；reserved ⇒ ILLI；不存在组合 ⇒ CFXREG。
- **边界（硬）**：
  - **semihosting 短路（`immu18[17:16] == 2'b11`）不在本任务**：其“QEMU 译码层短路、不进入向量、直接服务并按 PC 步进返回”归 **`QEMU-046t`**。本任务只做**一般 trap**（进入向量）。
  - **触发路径已由 `QEMU-044t` 落地**：本任务**不重复实现** `trap`/`escape`/`cfx2rd`/`cfx2rc` 的 decode→流程接线（见「审阅记录 · 044t/045t 边界处置说明」），只在其基线上**深化/验证 + 专探针**；**不改** `QEMU-044t` 已交付的 cfx 寄存器文件/异常进入流程语义；**不改** M1–M4 标量语义/exit port。
  - **补丁纪律（`spec/Process-01`）**：改动**只能**在 `.work/source/qemu`；导出补丁写 `/tmp`、非空 blob；`make check-patch-tree`（含断言⑥）通过；不手改补丁。
  - **重建成本申报**：`make build-qemu`（**5–20 分钟**）；开工前写明预计耗时；受 `JOBS` 限制；失败即停、**禁自动重试**。
  - 临时目录 `/tmp/opencode/QEMU-045t/`；**不提交 git**；复杂命令输出留存 `.work/log/qemu/`（**禁 `tee`**）。
  - **注入/还原纪律**：注入后**还原须含重建**；`cp`+`md5` 对账，**禁 `git checkout`/`git restore`/`git stash`**。

## 验收标准

1. **构建**：`make build-qemu` EXIT=0；给真实输出。
2. **一般 trap 进入向量**：`trap cfx0, immu18`（`immu18[17:16]≠2'b11`）→ `cause=CFXTRAP`、进入 `cfx_umon`（或对应 cfx）的 `excp_vector`（探针观测 PC/`cause_id`；真实输出）。
3. **`escape` 返回**：handler 内 `escape cfx0, [excp_cause_ip, 4]` → 返回到 trap 下一条指令；`escape_num` 递增；`prev_run_mode`/`prev_cfx_mask` 恢复（真实探针）。
4. **`escape` 偏移**：`imms20` 字节偏移（`%4==0`）正确反映到 `PC = cause_ip + (imms18<<2)`；含**负偏移回退**用例（真实输出）。
5. **`cfx2rd`/`cfx2rc`**：读写 `cfx_umon`/`cfx_power` 某寄存器值正确（含经 `set.zw`/`or.w` 构造并回读校验）；给真实输出。
6. **reserved / 不存在组合**：reserved cfxha ⇒ **ILLI**（`0x88`）；读写不存在/超出数量寄存器组合 ⇒ **CFXREG**（≥2 类，真实输出）。
7. **不回归**：`make check`/`make check-qemu-semantics` EXIT=0；`make test-codegen`（15/15）/`make test-elf`（5/5）EXIT=0；`check-patch-tree` EXIT=0。
8. **一键证据脚本**：`.work/evidence/QEMU-045t/run.sh`——非交互、失败非零、逐项打印；**内置注入自检**（把 `escape` 偏移 `imms18<<2` 改成固定值/关掉 reserved 判定 ⇒ 期望 **FAIL** ⇒ 还原 + **重建** ⇒ 回绿），结尾**禁 `tee`**；给真实输出。
9. **无残留**：`git status --untracked-files=all` 仅组件补丁 + 探针 + 本任务书；`.work/source/qemu` worktree clean。

## 完成区

**测试结果**：探针 `tools/qemu/min_rom_probe_045t.py` **14/14 PASS**（`RESULT: PASS`，EXIT=0）；一键证据脚本 `.work/evidence/QEMU-045t/run.sh` **`EVIDENCE: PASS` / `SCRIPT_EXIT=0`**（含合并注入自检：6 反例 → 对应 8 用例 FAIL → 还原（md5 对账相等）→ **重建** → 全绿）；门控 `make check` **EXIT=0**（含 `check-patch-tree: 2 component(s), 90 patches OK`、`check-qemu-semantics: PASS`、`check-spec-readonly`）、`test-codegen` **15/15 EXIT=0**、`test-elf` **5/5 EXIT=0**；`check_patch_tree.py --source-state` ⇒ qemu `count=1 clean=True`。

**修改文件**（与 `git status --untracked-files=all` 一致）：
- `tools/qemu/min_rom_probe_045t.py`（**新增，随产物入库**）——14 用例覆盖验收 2–6（一般 trap 进入向量 + cause 帧；`escape` 正/负偏移 + 跨 cfx（禁止→ILLI / 允许→恢复非复位 prev 模式/掩码）；`cfx2rd`/`cfx2rc` cg0–cg7 全寄存器面读写回读 + RO/RW + `scratch_regs_num` 边界 + cg3 仅 hypv；reserved⇒ILLI；不存在组合⇒CFXREG）。
- `.work/evidence/QEMU-045t/run.sh`（gitignored，非入库）。
- 本任务书（完成区/自审/状态）。
- **无组件补丁改动**：未发现 `QEMU-044t` 基线缺口（见「遗留问题」），故按任务输出 0/1「发现缺口时补齐」的条件约束，无补丁导出需求。

**验收结果**（真实命令输出/rc，日志在 `.work/log/qemu/`）：
1. **构建**：`make build-qemu JOBS=8` ⇒ `build-qemu: PASS` **EXIT=0**（增量 1.87s，`.work/log/qemu/QEMU-045t-build.log`）。
2. **一般 trap 进入向量**：`trap_vector_roundtrip` PASS — `trap cfx0, 0x0123`（`immu18[17:16]=0`）⇒ `cid:0=CFXTRAP(1)`、`cip:0=ROM_BASE+trap_idx*4`、`cinfo:0=0x7F000123`、`trapn:0=1`、`prevm:0=HYPV`、`prevmask:0=~0`；handler 内 `escape cfx0, 1` 返回到 trap 下一条 ⇒ `escn:0=1`、`rd9=1`、`rd10=cause_ip`、`rd11=HYPV`、`rd12=~0`。
3. **`escape` 返回/恢复**：`escape_cross_allowed` PASS — 预置 `cfx63 prev_run_mode=USER`、`prev_cfx_mask=0xDEADBEEF`、`cause_ip=ROM_BASE+0x300`，`escape cfx0, 0`（跨 cfx 允许）⇒ `MODE=0(USER)`、`CFXMASK=0xDEADBEEF`、`escn:63=1`（**非复位** prev 值恢复，强判别）。
4. **`escape` 偏移（含负偏移回退）**：`escape_fwd_offset` PASS（`imms18=+3 ⇒ PC=cause_ip+12`，落在独立 exit 0x99；错偏移会落 0x66/0x77 ⇒ 可 FAIL）；`escape_neg_offset` PASS（`imms18=1-trap_idx<0 ⇒ PC=cause_ip+(imms18<<2)` 回退到 trap 之前的独立 exit 0xAA；错偏移会落 0xEE）；`escape_cross_mask` PASS（跨 cfx 且 `escape_cfx_mask` 位=1 ⇒ 步骤 0 触发 `cid:3=ILLI`、`syncn:3=1`）。
5. **`cfx2rd`/`cfx2rc`**：`cfx2_full_regface` PASS — cg0–cg7 构造（`set.zw`/`or.w`）+ 回读：`cg0 rc1` 共享（cfx0 写→cfx63 读 `0x1111`）、`cg0/1/2/3 rc8` 运行模式、`cg3 rc12`、`cg4 rc0/rc1/rc2/rc6`（RO，`version=0x00010000`/`scrnum=4`）、`cg5 rc0/rc1/rc3/rc5`（RW）、`cg5 rc2/rc63`（RO，`cause_nonmaskable=0x3F07`）、`cg6 rc0/rc3` scratch、`cg7 rc0/rc1`、`cg2 rc1=0x2222`、cfx63（power）`cg5 rc3=0x12345678`/`cg6 rc1=0xFFFF`；`cfx2_cg3_nonhypv` PASS（user 模式访问 cg3 ⇒ `cid:0=CFXREG`）。
6. **reserved / 不存在组合**：`reserved_illi`（cfx2rd cfx7 ⇒ `cid:3=ILLI`）、`trap_reserved_illi`（trap cfx7 ⇒ `cid:3=ILLI`）、`cfxreg_cg_oor`（cg8 ⇒ CFXREG）、`cfxreg_rc_oor`（cg0 rc12 ⇒ CFXREG）、`cfxreg_scratch_oor`（cg6 rc4≥N ⇒ CFXREG）、`cfxreg_ro_write`（写 cg4 rc0 RO ⇒ CFXREG）全 PASS（**ILLI 1 类 + CFXREG 4 类**）。
7. **不回归**：`make check` **EXIT=0**（`check-patch-tree: 2 component(s), 90 patches OK`；`check-qemu-semantics: PASS`；`.work/log/qemu/QEMU-045t-check.log`）；`test-codegen` **15/15 EXIT=0**；`test-elf` **5/5 EXIT=0**；另跑 `min_rom_probe_044t.py` 13/13 PASS（044t 路径未回归）。
8. **一键证据脚本**：`.work/evidence/QEMU-045t/run.sh` ⇒ `EVIDENCE: PASS` **SCRIPT_EXIT=0**（`.work/log/qemu/QEMU-045t-evidence.log`）；合并注入 6 反例（A `imms18<<2`→固定 `+4` / B 关 reserved 判定〔3 处〕/ C 破 `cfx2rd` 回读 / D 去 `scratch_regs_num` 边界 / E 关跨 cfx `escape_mask` / F 去 cg3-only-hypv），重建后对应 **8 用例 EXIT=1（FAIL）** → `cp` 还原且 **md5 相等**（`helper.c=5e51db2a…`）→ **重建** → 全绿；全程无 `tee`。
9. **无残留**：`git status --untracked-files=all` = 仅新增探针 `tools/qemu/min_rom_probe_045t.py`（+本任务书待提交）；`.work/source/qemu` worktree **clean**（`--source-state` `count=1 clean=True`）；无 `*.preinject`/`*.orig`/`*.rej` 残留。

**新发现/坑**：
1. **`DADAO-12 §5` 异常退出流程伪代码（步骤 0–4）不恢复 `inner_cfx_code`**，只恢复 `inner_cfx_mask`←`prev_cfx_mask` 与 `inner_run_mode`←`prev_run_mode`。实现与伪代码一致；**探针据此不对 escape 后的 `cfxcode` 作断言**（escape 后 `inner_cfx_code` 保持进入时的 cfx）。建议沉淀，避免后续任务想当然认为 escape 会切回调用 cfx。
2. **§5 prose 与伪代码在跨 cfx escape 上有措辞张力**：prose 称「直接恢复到 A 的 prev 现场」，但伪代码 `⟨cfxname⟩` 明确定义为 `inner_cfx_code`（当前 cfx），返回地址用**当前 cfx** 的 `excp_cause_ip`。实现按**伪代码（权威）**。此为 spec 层面待厘清点，非 044t 缺陷。
3. **验收 6 的「ILLI（0x88）」**：`0x88` 是 ILLI cause 的 exit-port 码（`ADR-0004 D5.8`）。按 `DADAO-12 §5`，reserved cfxha 触发的 ILLI 会**重定向进入当前 mode monitor 向量**，故可观测语义是 `cause_id=ILLI(=1<<8)`（handler 决定退出码）；若 monitor 向量未设（复位值 `0x0FFF_FFFF_0000` 不可映射）反会得到 0x87，**不会**裸得 0x88。探针据此断言 `cid=ILLI`（并给出 handler 退出码），已在验收 6 逐条注明。
4. **偏移用例的假 PASS 防护**：`escape_fwd_offset` 每个候选返回点用 `jump` 指向**独立 exit 码**（0x66/0x77/0x99），`escape_neg_offset` 用 `idx0` forward jump 跳过 negative target、错偏移落 0xEE——避免「错偏移也落回同一 exit」的恒真。
5. **`ASYNCN` 含子串 `SYNCN`**：`-d cpu` 日志正则须锚定（`ID:… SYNCN:` 带前导空格），已沿用 044t 处理。

**遗留问题**：
- **未发现 `QEMU-044t` 基线缺口** ⇒ 本任务**无组件补丁改动**；045t 交付为「044t 基线之上**深化/验证** + **独立专探针/证据**」，符合任务输出 0/1「发现缺口时补齐」的条件。044t 已交付的 `trap`/`escape`/`cfx2rd`/`cfx2rc` 触发路径与基础执行经 14 用例（含负偏移回退、跨 cfx escape、cg0–cg7 全寄存器面、cg3 仅 hypv、reserved/CFXREG 组合）验证语义正确。
- **§5 prose 与伪代码的跨 cfx escape 措辞张力**（见新发现 2）：本任务按伪代码（权威）验证；语义厘清建议另立 spec 任务，**不在本任务范围**（不改 `spec/`）。
- **semihosting 短路**（`immu18[17:16]==2'b11`）归 `QEMU-046t`，本任务未触及（探针不覆盖该分支）。
- **`cfx2rd`/`cfx2rc` 数据通路仅连 rd 寄存器组**（`SimRISC-11` 注意）：探针经 rd 构造/回读，符合；rb/rf 中转不在本任务。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**：逐行审查新增探针 `tools/qemu/min_rom_probe_045t.py` + 证据脚本 `.work/evidence/QEMU-045t/run.sh`；核对 Spec-first（`DADAO-12 §1/§3/§5`、`SimRISC-11 §特权指令`、`Toolchain-01`、`contracts/opcodes.yaml`、`ADR-0004/0020`）、边界（不改标量语义/exit-port、不改 `spec/`、不碰 046t semihosting）、防造假（真实执行、真实输出逐条对齐）。

**结论**：逻辑正确、边界受控；实现期发现 4 处探针构造缺陷（已当场修复并复验），其余为已记录的判据/坑。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `trap_vector_roundtrip` handler 误写为 `hand(0x100,0x00)`（exit 而非 escape），致未走 escape 回程（escn=0） | ✅已修 | 探针改为 `{0x100:[escape(0,1)]}` | 该用例 PASS（`escn:0=1`、rd9–12 正确） |
| F2 `escape_cross_allowed`/`cfx2_cg3_nonhypv` 的 `cause_ip` 误填 ROM **字节偏移**（`0x300`），应**绝对地址**（`ROM_BASE+0x300`） | ✅已修 | 两用例改 `load_rd(20, ROM_BASE + EXIT_CONT)` | 两用例 PASS（`MODE=USER`/`CFXMASK=0xDEADBEEF`；`cid:0=CFXREG`） |
| F3 初版 `exit_seq` 的 `rb16` 构造用错 word 索引（得 `0xFFFF_0000_8000_0000`） | ✅已修 | 回退为 044t 口径 `set.zw rb16 wp2=0xFFFF + or.w wp1=0x8000` | 全用例退出码正确（exit 断言全绿） |
| F4 未用常量 `H2` | ✅已修 | 删除 | `py_compile` OK |
| F5 断言可达 FAIL（反例门控） | ✅已证 | 证据脚本 6 反例（A–F）覆盖 offset/reserved/readback/scratch-bound/escape-mask/cg3-mode 六类机制 | 注入后 **8 用例 EXIT=1**；`cp`+md5 还原 ⇒ 重建 ⇒ 14/14 回绿 |

**状态**：无未修 finding ⇒ 置「待验收」，返回主会话 `/complete`。

#### 第 1 轮 reviewer 验收（2026-10-08）

**审查范围**：独立验证 engineer 产出，对照验收 1–9 + 约束。

##### 一、证据脚本审核（`.work/evidence/QEMU-045t/run.sh`）

逐条核对：
- **非交互**：无 stdin 读取 ✓
- **失败非零**：`fail` 变量追踪，任一检查失败 ⇒ `exit 1` ✓
- **逐项打印**：每条检查打印名称 + EXIT 码 ✓
- **注入模式匹配 helper.c 实际内容**：
  - A `env->cfx[ci].cause_ip + ((int64_t)imm << 2)` → 替换为 `+ 4`：grep 命中 **1** 处 ✓
  - B `if (DADAO_CFX_IS_RESERVED(cfxha)) {` → 替换为 `if (0) {`：grep 命中 **3** 处 ✓
  - C `env->rd[rd] = *p;` → 替换为 `env->rd[rd] = 0;`：grep 命中 **1** 处 ✓
  - D `if ((uint64_t)rc >= r->scratch_regs_num) {` → 替换为 `if (0) {`：grep 命中 **1** 处 ✓
  - E `(env->cfx[ci].mode[mode].escape_mask & (1ULL << cfxha))` → 替换为 `0`：grep 命中 **1** 处 ✓
  - F `if (env->inner_run_mode != DADAO_MODE_HYPV) {` → 替换为 `if (0) {`：grep 命中 **1** 处 ✓
- **注入非空检查**：`git diff --name-only` 空 ⇒ 报 FAIL ✓
- **还原**：`cp` + md5 对账（**非** `git checkout`）✓
- **还原含重建**：`make build-qemu JOBS=8` ✓
- **结尾禁 `tee`**：`rc=$?` 直接捕获，日志用 `>` 重定向 ✓

**脚本审核结论**：合格，可达 FAIL 路径均存在，无恒真断言。

##### 二、重跑证据脚本

```
QEMU-045t evidence: trap/escape semantics + cfx2rd/cfx2rc regface

[1/5] make build-qemu → EXIT=0
[2/5] probe (all cases) → 14/14 PASS, EXIT=0
[3/5] injection self-check:
  pre-inject md5: helper.c=5e51db2ae4a111f1e1d7ca728a506697
  injected files: target/dadao/helper.c
  rebuild(after inject) EXIT=0
  escape_fwd_offset  → FAIL (exit exp=0x99 got=0x66) EXIT=1
  escape_neg_offset  → FAIL (exit exp=0xaa got=0xee) EXIT=1
  reserved_illi      → FAIL (cid exp=0x100 got=0x4) EXIT=1
  trap_reserved_illi → FAIL (cid exp=0x100 got=0x4) EXIT=1
  cfx2_full_regface  → FAIL (all rd=0) EXIT=1
  cfxreg_scratch_oor → FAIL (exit exp=0xcc got=0xee) EXIT=1
  escape_cross_mask  → FAIL (exit exp=0xcc got=0x89) EXIT=1
  cfx2_cg3_nonhypv   → FAIL (exit exp=0xcc got=0xee) EXIT=1
[4/5] restore + rebuild:
  post-restore md5: helper.c=5e51db2ae4a111f1e1d7ca728a506697 (MATCH)
  rebuild EXIT=0
  probe(all, post-restore) → 14/14 PASS, EXIT=0
[5/5] EVIDENCE: PASS
```

**重跑结论**：EVIDENCE: PASS，SCRIPT_EXIT=0。

##### 三、独立注入（reviewer 自行执行，区别于 engineer 的 A–F）

**注入方式**：改 escape 偏移计算 `<< 2` → `<< 4`（偏移 4 倍放大），与 engineer 的 anomaly A（替换为固定 `+4`）**不同**。

```
# 注入前快照
cp helper.c helper.c.preinject
md5sum: 5e51db2ae4a111f1e1d7ca728a506697  helper.c.preinject

# 注入
python3: replace 'env->cfx[ci].cause_ip + ((int64_t)imm << 2)'
              with 'env->cfx[ci].cause_ip + ((int64_t)imm << 4)'  (1 site)

# 确认注入生效
git -C .work/source/qemu diff --name-only → target/dadao/helper.c (非空)

# 重建
make build-qemu JOBS=8 → build-qemu: PASS

# 重跑探针（预期 escape 用例 FAIL）
escape_fwd_offset → [FAIL] exit exp=0x99 got=0x87; escn:0 exp=0x1 got=0x0  EXIT=1
escape_neg_offset → [FAIL] exit exp=0xaa got=0x87; escn:0 exp=0x1 got=0x0  EXIT=1
reserved_illi     → [PASS]  (不受影响，注入有针对性)  EXIT=0

# 还原
cp helper.c.preinject helper.c
md5sum: 5e51db2ae4a111f1e1d7ca728a506697  (与注入前一致)

# 重建
make build-qemu JOBS=8 → build-qemu: PASS

# 回绿验证
probe(all) → 14/14 PASS, RESULT: PASS, EXIT=0
```

**独立注入结论**：注入有效（2 用例 FAIL，1 用例不受影响），还原 + 重建后 14/14 回绿。注入/还原全程用 `cp` + md5，**未使用** `git checkout/restore/stash`。

##### 四、验收 1–9 逐条核验

| # | 验收项 | 真实输出 | 判定 |
|---|--------|---------|------|
| 1 | 构建 `make build-qemu` EXIT=0 | `build-qemu: PASS`，EXIT=0 | ✓ |
| 2 | 一般 trap 进入向量 | `trap_vector_roundtrip` PASS — `cid:0=CFXTRAP(1)`、`cip:0=ROM_BASE+trap_idx*4`、`cinfo:0=0x7F000123`、`trapn:0=1` | ✓ |
| 3 | escape 返回 + 恢复 | `trap_vector_roundtrip` `escn:0=1`、`rd9=1`、`rd10=cause_ip`、`rd11=HYPV`、`rd12=~0`；`escape_cross_allowed` `MODE=USER`、`CFXMASK=0xDEADBEEF`、`escn:63=1`（非复位 prev 值） | ✓ |
| 4 | escape 偏移（含负偏移） | `escape_fwd_offset` PASS（exit=0x99）；`escape_neg_offset` PASS（exit=0xAA）；`escape_cross_mask` PASS（cid:3=ILLI） | ✓ |
| 5 | cfx2rd/cfx2rc 全寄存器面 | `cfx2_full_regface` PASS（cg0–cg7 全读写回读正确，含 RO/RW、scratch、cfx0↔cfx63 共享）；`cfx2_cg3_nonhypv` PASS（user 访问 cg3 ⇒ CFXREG） | ✓ |
| 6 | reserved / 不存在组合 | `reserved_illi` PASS（ILLI）、`trap_reserved_illi` PASS（ILLI）、`cfxreg_cg_oor`/`cfxreg_rc_oor`/`cfxreg_scratch_oor`/`cfxreg_ro_write` 全 PASS（CFXREG ≥2 类：cg_oor + rc_oor + scratch_oor + ro_write） | ✓ |
| 7 | 不回归 | `make check` EXIT=0（check-patch-tree 90 patches OK）；`test-codegen` 15/15 EXIT=0；`test-elf` 5/5 EXIT=0；`min_rom_probe_044t.py` 13/13 EXIT=0 | ✓ |
| 8 | 一键证据脚本 | `.work/evidence/QEMU-045t/run.sh` → EVIDENCE: PASS，SCRIPT_EXIT=0；注入自检 6 反例 → 8 用例 FAIL → 还原+重建 → 回绿 | ✓ |
| 9 | 无残留 | `git status` = 干净；`.work/source/qemu` clean；无 `*.preinject`/`*.orig`/`*.rej` | ✓ |

##### 五、约束核验

| 约束 | 核验 | 判定 |
|------|------|------|
| 无组件补丁改动 | `git show 2b49946 --stat` 仅 2 文件（任务书 + 探针）；`components/qemu/**` 零改动 | ✓ |
| 14 用例覆盖面论证 | 探针覆盖：一般 trap 向量往返 + cause 帧 + escape 正/负偏移 + 跨 cfx（禁止→ILLI / 允许→恢复非复位 prev） + cg0–cg7 全寄存器面 + RO/RW + scratch 边界 + cg3 仅 hypv + reserved→ILLI + 不存在组合→CFXREG。044t 基线经此 14 用例验证无缺口 | ✓ |
| `spec/` 零改动 | `git diff --name-only e056f52..HEAD -- spec/` 为空 | ✓ |
| `.work/**` 未入库 | `git show 2b49946 --stat` 不含 `.work/` | ✓ |
| 遗留问题如实 | 新发现 ①②③ 均记录在完成区，未改 `spec/`，建议另立 spec 任务（合理） | ✓ |

##### 六、判决

**Accepted**

验收 1–9 全部通过，约束无违反，独立注入验证有效，证据脚本合格。

#### 044t/045t 边界处置说明（architect，2026-10-08，**只追加**）

**背景**：engineer 为使 `QEMU-044t` 验收 2–7 可观测，把 `trap`/`escape`/`cfx2rd`/`cfx2rc` 的 **decode→异常流程接线** 一并实现（044t 完成区「新发现 4」已登记，供 architect 判定）。经核 `QEMU-045t` 任务书与该实现的**实际交叉面**，二者输出重叠。

**依据（044t 实测交付，非转述）**：
- `components/qemu/patches/target/dadao/insn_trans/trans_ctrl.c.inc.patch`：`trans_trap_ciii_cfx`/`trans_escape_ciii_cfx`/`trans_cfx2rd_crrr_cfx`/`trans_cfx2rc_crrr_cfx` 由 `gen_exception_illegal`（ILLI 桩）改为 `gen_helper_cfx_*` + `tcg_gen_exit_tb`（`cfxld`/`cfxst` 仍 ILLI）。
- `components/qemu/patches/target/dadao/helper.c.patch`：新增 `helper_cfx_trap`（一般 trap ⇒ `CFXTRAP` 进入向量；**reserved ⇒ ILLI**；`trap_mask` 禁止 ⇒ ILLI；未实现 cfx ⇒ CFXREG；semihosting tag ⇒ 显式 ILLI）、`helper_cfx_escape`（`DADAO-12 §5` 退出流程步骤 0–4，含 **18 位有符号展开** 与 **跨 cfx escape mask** 检查）、`helper_cfx2rd`/`helper_cfx2rc`（经 `cfx_reg_ptr` 覆盖 cg0–cg7 全寄存器面 + RO/RW + `scratch_regs_num` 边界 + cg3 仅 hypv，异常组合 ⇒ CFXREG）。
- 044t 完成区实测：探针 13/13 PASS、`make check` EXIT=0 等（见 044t 完成区）。

**调整决定（最小化收缩 045t 范围）**：045t 依赖 044t 之上，**044t 已落地的触发路径与基础执行不再重复实现**；045t 收敛为「**在 044t 基线上深化并验证完整语义 + 交付独立专探针/向量**」，保留其**独有内容**：
- `escape` **负偏移回退**（`imms18` 有符号展开、`%4==0`）与 **跨 cfx** escape mask（步骤 0）；
- `trap` **完整语义**（一般 trap 进入向量 + `cause_id`/`cause_ip`/`cause_info` 回读；reserved/`trap_mask` ⇒ ILLI）；
- `cfx2rd`/`cfx2rc` **全寄存器面深化**（cg0–cg7、RO/RW、`scratch_regs_num` 边界、cg3 仅 hypv、CFXREG 组合）；
- **专探针/向量** `tools/qemu/min_rom_probe_045t.py`（一般 trap 向量往返、负偏移、跨 cfx、全寄存器面）。

**边界与影响**：
- **M5 总范围不变**：045t 的语义能力仍在 M5 内（044t 落地 + 045t 验证/深化），**未扩大或缩小** M5 覆盖；仅调整两任务之间的实现/验证分工。
- **未改 `spec/`**；semihosting（`immu18[17:16] == 2'b11`）仍归 `QEMU-046t`。
- 045t **状态**保持 `待开始`（尚未下发）。
- 本说明**只追加**，不改写 045t 既有内容。

#### 第 1 轮 architect 提交（WIP）（2026-10-08，只追加）

**档位**：**`WIP:`**（engineer 已返回、reviewer 尚未验收 ⇒ 按提交分档规则先本地提交）。

**文件集对账**（显式 staging，禁 `git add -A`）：
- **入库集**：`tools/qemu/min_rom_probe_045t.py`（新增，555 行）+ 本任务书（完成区/自审/044t–045t 边界说明/本记录）。
- 与完成区「修改文件」声明**一致**：`.work/evidence/QEMU-045t/run.sh` 属 **gitignored**（`.gitignore:2 .work/`），**未入库**；**无组件补丁改动**（`components/**` 无改动），与声明一致。
- **漏提 / 多提 / 越界**：无。`spec/` 交集为**空**；`.work/**` **未入库**。

**说明（本任务无组件补丁改动的原因）**：`QEMU-044t` 已把 `trap`/`escape`/`cfx2rd`/`cfx2rc` 的 decode→异常流程接线与基础执行落地（见上文「044t/045t 边界处置说明」）；本任务据此**只做深化/验证 + 独立专探针**，经 14 用例（负偏移回退、跨 cfx escape、cg0–cg7 全寄存器面、cg3 仅 hypv、reserved/CFXREG 组合）验证 **044t 基线无缺口**，故无补丁导出需求，交付 = 专探针 + 深化验证证据。

**约束**：只 `commit`、**绝不 `push`**。

#### 第 1 轮 architect 提交（正常，2026-10-08）

**档位**：**正常提交**（reviewer 判 `Accepted` ⇒ `**状态**` 置 `已验证`；**不加 `WIP:`**）。**只 `commit`，绝不 `push`**（push 归主会话 `/complete` 后；须把 WIP `2b49946` + 本次正常提交 + 收尾台账 squash/amend 为单一「已验证」提交）。

**交叉复核判决**：**通过**（reviewer `Accepted` 成立，不推翻/不补充 Needs Revision，无遗漏需补判）。独立核（architect 自跑，真实输出）：

- **reviewer 独立注入有鉴别力、特异、还原含重建** ✓：reviewer 注入与 engineer 的 A–F **不同**——改 `helper.c` 的 `cause_ip + ((int64_t)imm << 2)`→`<< 4`（`grep` 命中 **1** 处，即 escape 返回地址计算；见下）。该注入**只命中 escape 偏移路径** ⇒ `escape_fwd_offset`/`escape_neg_offset` **FAIL** 而 `reserved_illi`（走 `cfx2rd`，不经 escape）**仍 PASS** ⇒ **特异、非广域**；还原后 **重建** + 14/14 回绿。
- **独立核「无组件补丁改动」成立** ✓：`git show 2b49946 --stat` = **2 文件**（`tools/qemu/min_rom_probe_045t.py` + 本任务书）；`git diff --name-only e056f52..HEAD -- components/` **空**；`.work/source/qemu` `git status --porcelain -uall` **空**（clean）；`helper.c` md5 `5e51db2a…` 与注入前一致、无 `*.preinject`/`*.orig`/`*.rej` 残留。
- **独立核「未发现 044t 基线缺口」的依据充分** ✓：`min_rom_probe_045t.py` `@case` **14** 个，覆盖任务输出 1 的全部范围——`trap`（一般进入向量 + `cause` 帧；`trap_mask` ⇒ ILLI；reserved ⇒ ILLI）、`escape`（正偏移 / **负偏移回退** / 跨 cfx 禁止 ⇒ ILLI / 跨 cfx 允许 ⇒ 恢复**非复位** `prev_run_mode`/`prev_cfx_mask`）、`cfx2rd`/`cfx2rc` **cg0–cg7 全寄存器面**（含 RO/RW、`scratch_regs_num` 边界、cg3 仅 hypv、cfx0↔cfx63 共享）、reserved ⇒ ILLI、**CFXREG 4 类**（cg_oor / rc_oor / scratch_oor / ro_write）。**045t 已收缩为「044t 基线之上深化/验证 + 专探针」**（见「044t/045t 边界处置说明」），对**该收缩范围**而言 14 用例覆盖充分，「基线无缺口」结论**有覆盖依据**（非以 validator 绿灯充数）。
- **独立核「未越界」** ✓：**2 文件**（新探针 + 本任务书）；`git diff --name-only e056f52..HEAD -- spec/` **空**（`spec/` 交集**空**）；`.work/**` gitignored、**未入库**（含 `evidence/QEMU-045t/run.sh`/`log/qemu/`/`source/qemu`）。
- **新发现 ①②③ 处置** ✓（详见下「新发现处置」）：①（escape 不恢复 `inner_cfx_code`）为**澄清**、实现与伪代码一致 ⇒ 入 `lessons`；②（§5 prose 与伪代码在跨 cfx escape 的措辞张力）为**上游只读册覆盖缺口** ⇒ **仅登记 `ISS-167` + 建议另立 spec 任务**，**未改 `spec/`**；③（`ILLI` 观测语义）已在完成区新发现 3 **说明清楚**，无需另动。

**新发现处置**（architect，2026-10-08）：
- **① `DADAO-12 §5` 异常退出流程不恢复 `inner_cfx_code`**：核 `spec/DADAO-12-SEE-主管系统运行环境.md` §5「异常退出流程」步骤 1–4 + 伪代码（L846–853）确认——只恢复 `inner_cfx_mask`←`excp_prev_cfx_mask`、`inner_run_mode`←`excp_prev_run_mode`，**无** `inner_cfx_code` 恢复（`inner_cfx_code` 仅在异常**进入**步骤写 `<= temp_cfx_code`）。实现与伪代码一致，非缺陷 ⇒ 沉淀 `lessons §7.18`，避免后续任务想当然认为 escape 会切回调用 cfx。
- **② §5 prose 与伪代码在跨 cfx escape 的措辞张力**：prose（L674）称「硬件直接恢复到 **A 的 prev 现场**」，而伪代码 `⟨cfxname⟩` 明确定义为 `inner_cfx_code`（**当前**执行 escape 的 cfx），返回地址用**当前 cfx** 的 `excp_cause_ip`（L830/L853）⇒ 存在张力；**伪代码为权威**、实现按伪代码。`DADAO-12` 为**上游只读册**（`manifests/spec-readonly.lock.toml` 锁定），改它须**用户事先授权**（`lessons §8.5`/`Process-06`）⇒ **登记 `ISS-167`（`open`）+ 建议另立 spec 任务**，**本任务 `spec/` 零改动**。
- **③ `ILLI` 观测语义（`cause_id=ILLI` vs exit-port 码 `0x88`）**：完成区新发现 3 已说明——`0x88` 是 ILLI cause 的 exit-port 码（`ADR-0004 D5.8`），reserved cfxha 触发的 ILLI 按 `DADAO-12 §5` **重定向进入当前 mode monitor 向量** ⇒ 可观测语义为 `cause_id=ILLI(=1<<8)`；探针据此断言 `cid=ILLI` 并给 handler 退出码。**说明清楚**，无需另动。

**文件集对账（只核「提交哪些文件是否合适」；逐个路径显式 staging，禁 `git add -A`）**：
- **staged**：本任务书（`**状态**=已验证` + reviewer 记录 + 本 architect 提交记录）、`.tao/knowledge/lessons.md`（§7.18/§8.12）、`.tao/knowledge/changelog.md`（+1 行）、`.tao/knowledge/milestones.md`（QEMU-045t 落地条目）、`.tao/knowledge/MEMORY.md`（M5 摘要行 + QEMU-045t 项）、`.tao/knowledge/issues.yaml`（+`ISS-167`）。
- **对账结论**：staged 与「完成区 · 修改文件」声明 + 本轮「知识沉淀 / 收尾」追加**一致** ⇒ **无漏提、无多提、无越界**；`spec/` 交集**空**（`git diff --cached --name-only` 与 `spec/` 无交集）；`.work/**`（gitignored：`source/qemu`、`evidence/QEMU-045t/run.sh`、`log/qemu/`）**未入库**。
- 判据：新探针 `tools/qemu/min_rom_probe_045t.py` 已在 **WIP 提交 `2b49946`** 内；本轮正常提交只含「状态 + 审阅记录 + 知识沉淀」。

#### 主会话统一验收报告（`/complete`，2026-10-08）

- **reviewer**：`Accepted`。证据脚本重跑 **`EVIDENCE: PASS`**（14/14；6 类注入命中 **8 用例 FAIL** ⇒ `cp`+`md5` 还原 ⇒ **重建** ⇒ 回绿）；**独立注入**（`escape` 返回地址 `<<2`→`<<4`）⇒ `escape_fwd/neg_offset` **FAIL** 而 `reserved_illi` 仍 PASS（**特异、非广域**）⇒ 还原 ⇒ 重建 ⇒ 14/14。
- **architect 交叉复核**：**通过**。独立核：注入点 `helper.c` **唯一命中 1 处**（`cause_ip + (imm<<2)`）⇒ 特异；**「无组件补丁改动」成立**（`git show 2b49946 --stat` = 探针 + 任务书；`components/qemu/**` 零改动；`.work/source/qemu` clean）；「未发现 044t 基线缺口」**有覆盖依据**（14 用例逐条对应收缩后范围：trap 进向量/cause 帧/`trap_mask`;escape 正负偏移/跨 cfx;`cfx2rd/rc` cg0–cg7 全面〔RO/RW、scratch 边界、cg3 仅 hypv、cfx0↔cfx63 共享〕;reserved;CFXREG 4 类）——**非以 validator 绿灯充数**。
- **交付**：**验证型任务**（无实现改动）——`tools/qemu/min_rom_probe_045t.py`（14 用例，**随产物入库**）+ 证据脚本；`make check`/`check-qemu-semantics`/`test-codegen` 15/15/`test-elf` 5/5/`check-patch-tree` 90 patches EXIT=0；`min_rom_probe_044t` 仍 13/13。
- **新发现处置**：① `DADAO-12 §5` 退出流程**不恢复 `inner_cfx_code`** ⇒ 与伪代码一致（**澄清类**，入 `lessons §7.18`，**不立** spec 任务）；② §5 **prose 与伪代码**在跨 cfx escape 有**措辞张力**（伪代码权威、实现按伪代码）⇒ 因 `DADAO-12` 为**上游只读册**，登记 **`ISS-167`** 并建议另立 spec 任务（**`spec/` 零改动**）；③ `ILLI` 观测语义（`cause_id=ILLI` vs exit-port 码 `0x88`）已在完成区说明清楚。
- **知识沉淀**：`lessons §7.18`（验证型任务须交付**可失败**专证据 +「基线无缺口」须有覆盖依据）+ **`§8.12`**（**伪代码为权威**；上游册张力只登记/提请授权，禁静默改 `spec/`）。
- **最终判决**：**`Accepted`** ⇒ 任务书 `**状态**` 置 `已验证`。
