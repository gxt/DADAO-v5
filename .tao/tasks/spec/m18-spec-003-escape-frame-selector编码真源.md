# m18-spec-003: escape frame selector 编码真源同步（SimRISC-11/IDL/Toolchain-01/contract-asm）

**模块**：spec
**项目里程碑**：M18
**依赖**：`m18-spec-002`（`DADAO-12`/`contract-see` 已改 hart-first/cg9 + selector）
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务跨 4 处编码真源 + IDL 渲染，取 1.5–2× 中位）
**档位**：中改（编码/IDL/工具链规范）
**状态**：已验证
**执行环境**：本地

## 背景

`m18-spec-002` 只在 `DADAO-12 §5.1/§5.3`、`contract-see`、`contract-isa` 落了 `escape` 的 **frame selector bit1**（0=cg5，1=cg9；`imms18 ∈ {0,1,2}`、`3 ⇒ ILLI`；`imms18[17:2]` SBZ；cg9 仅偏移 0）。以下**编码真源仍未同步**，会导致工具链/IDL/QEMU/RTL/gem5 按旧编码实现：

- `spec/SimRISC-11-其它.md` 正文与 263 个 IDL 渲染块中的 `escape` 编码/合法立即数；
- `idl/SimRISC-11.idl` 的 `escape` 语义/约束；
- `spec/Toolchain-01 §2.4/§5`（汇编 `imms20` 合法值）；
- `.tao/contracts/contract-asm.md §5`；
- `spec/Kaiwu-测试机运行环境.md` §4.2 的 escape 编码说明；
- `.tao/contracts/contract-asm-list.md`、`contracts/opcodes.yaml`、`contracts/legality_rules.yaml` 与 `tools/llvm/gen_asm_list.py` 中的 escape 编码/合法立即数真源。

## 目标

1. `spec/SimRISC-11`：`escape` 编码层 `imms18` 增 `bit1 = frame`（0=cg5/1=cg9）；合法 `imms18 ∈ {0,1,2}`，`3 ⇒ ILLI`；`imms18[17:2]` SBZ；汇编层 `imms20 ∈ {0,4,8}`，8=cg9/偏移 0；cg9 只允许偏移 0。
2. `idl/SimRISC-11.idl`：同步 `escape` 的编码/约束；重新渲染受影响的 `SimRISC-11` 块（只改 `escape` 相关块，其它块逐字节不变）。
3. `spec/Toolchain-01`：汇编器接受 `imms20 ∈ {0,4,8}`、拒绝其它；`8` 对应 cg9。
4. `.tao/contracts/contract-asm.md §5`：同步该编码口径。
5. `spec/Kaiwu §4.2`、`contract-asm-list.md`、`contracts/opcodes.yaml`、`contracts/legality_rules.yaml`、`tools/llvm/gen_asm_list.py`：同步 escape 的编码/合法立即数（`check-spec-codeblocks`/`check-asm-list`/`check-legality-drift` 以它们为真源）。
6. `spec/.manifests.toml` 重算 `SimRISC-11`、`Toolchain-01`、`Kaiwu` 的 sha256；版本仍 `0.8.0-rc`。

## 验收（逐条贴真实 rc）

1. `make check-spec-refs`/`check-spec-drift`/`check-spec-purity`/`check-spec-changelog`/`check-spec-numbering`/`check-spec-codeblocks`/`check-asm-list`/`check-contracts-*`/`check-idl-sync`/`check-idl-parse` 全 rc=0（按实际目标）。
2. `grep` 活文档中 `escape` 的旧约束 `imms18[17:1] SBZ`、`imms20 ∈ {0,4}` 已不再作为唯一合法集；新的 `{0,1,2}`/`{0,4,8}` 明文。
3. IDL 渲染：只 `escape` 相关块变化，其它 262 块逐字节相同（`git diff` 逐块核；渲染工具可复现）。
4. 锁哈希与文件一致；`DADAO-12` 不改（spec-002 已改）。
5. 不回归：`make check` 与基线逐行相同；`check-knowledge-refs` rc=0。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`spec/SimRISC-11-其它.md`、`idl/SimRISC-11.idl`、`spec/Toolchain-01-*.md`、`spec/Kaiwu-测试机运行环境.md`、`.tao/contracts/contract-asm.md`、`.tao/contracts/contract-asm-list.md`、`contracts/opcodes.yaml`、`contracts/legality_rules.yaml`、`tools/llvm/gen_asm_list.py`、`spec/.manifests.toml`、本任务书；第 1 轮返工扩范围：`idl/data/idl_parse_fixture.json`、`idl/data/exec_anchor.toml`、`idl/.manifests.toml`（生成锁重算）、`docs/DDLN/C-资源管理/DD-C004-资源管理--异常进入与退出.md`、`tests/inst/inventory.md`、`components/gem5/README.md`、`tools/spec/generate_opcodes.py`、`tools/gem5/check_b6.py`（静态 checker）；`README.md`、`docs/DDLN/Z-发展历程/DD-Z003-发展历程--用AI编程-v5.md` 的旧编码句属历史里程碑记录，保留不改；不改实现/QEMU/RTL/gem5/LLVM 代码。
3. 不改版本号；不复制 spec 正文；IDL 渲染必须用仓库工具，不手改生成块。
4. 还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；术语「bank = 寄存器组」。

## 待裁定

无。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` **65/65 PASS（rc=0）**，基线 = `git merge-base master HEAD` = `b3a02f5d`（不随提交漂移）；`--inject` 4/4 PASS。21 个门控逐项真实 rc=0。`make check` rc=2，输出与基线逐行相同（`diff` rc=0；基线缺 `llvm-mc`，停在 `check-isa-coverage`）。
**修改文件**：真源/工具 10 = `spec/SimRISC-11-核芯功能扩展指令.md`、`idl/SimRISC-11.idl`、`spec/Toolchain-01-汇编语言.md`、`spec/Kaiwu-测试机运行环境.md`、`.tao/contracts/contract-asm.md`、`.tao/contracts/contract-asm-list.md`、`contracts/opcodes.yaml`（生成器重算）、`contracts/legality_rules.yaml`、`tools/llvm/gen_asm_list.py`、`spec/.manifests.toml`；返工 5 = `docs/DDLN/C-资源管理/DD-C004-资源管理--异常进入与退出.md`、`tests/inst/inventory.md`、`components/gem5/README.md`、`tools/spec/generate_opcodes.py`、`tools/gem5/check_b6.py`；生成锁 3 = `idl/data/idl_parse_fixture.json`、`idl/data/exec_anchor.toml`、`idl/.manifests.toml`；另本任务书。`README.md`、`docs/DDLN/Z-发展历程/DD-Z003` 的旧编码句属历史里程碑记录，按返工指示保留不改。
**验收结果**：IDL 渲染仅 `escape_ciii_cfx` 1 块变化（12 册 263 块对照 merge-base：未变 262，`--check` rc=0）。F3：`generate_opcodes.py` 改为生成 `imms18[17:2] == 0` + `imms18 != 3`，重生成后与文件一致且二次重生成 byte-identical（rc=0）；`check-legality-drift`/`check-asm-list`/`-drift`/`check-spec-codeblocks`/`validate-encoding`/`check-fp-contract` 全 rc=0。F4：`check_b6.contract_rule_errors(live_b6_entries())` = **0 error**（escape legality 三项、rules 仍 `encode_sbz`+`encode_cfx_reserved`；仅跑静态部分，未构建/运行 gem5 harness）。锁哈希一致、`check-manifests-guard` rc=0；版本未动（SimRISC-11 0.5.7、Toolchain-01 0.5.4-rc、SEE 0.8.0-rc）。
**新发现/坑**：① 生成器原先不幂等（8 条 fp `ld.t/o`、`st.t/o`、`ldm.t/o`、`stm.t/o` 的 `aligned()` 未在生成器内），重生成会回退他人手工项；已补齐生成器使重生成 byte-identical（派生差异仅 4 条单元素 `rule_refs` 排版与计数 242→246 的生成态修正）；② 改 `.idl` 必须同步 parse fixture + exec anchor 两把锁；③ `gen_asm_list.py` 头部为 f-string，`{0,4,8}` 须写 `{{0,4,8}}`；④ IDL 无 `cfx_hart` 谓词内建，cg9 帧判定用 `cfxHA != 6'd15` + `cfx_read(cfxHA,9,3)`。
**遗留问题**：① `idl/tools/idl_exec.py::_op_escape`、② `tests/inst/11-cfx/escape_ciii_cfx.S` case 13/14、③ 语义库 `§4.6 cfx_escape_enter` 仍为 `excp_cause_ip + imm` 口径——均由 `m18-idl-001` 覆盖；④ `.tao/knowledge/MEMORY.md:76` 旧「0/+4」待主会话更新；⑤ gem5 模型/`exec/b6.cc` 仍按旧编码（本任务只改静态 checker 与文档口径，模型跟改待 M18 gem5 任务）；⑥ `spec/SimRISC-00:461` 属 0.5.6 历史条目，保留。

## 审阅记录

### 第 1 轮 engineer 自审

**审查面**：`idl/SimRISC-11.idl` escape 块（逐行语义对照 `DADAO-12 §5.1/§5.3`、`contract-see §6.2`、`contract-isa §13.6`）、5 处散文真源、`opcodes.yaml`/`legality_rules.yaml`/`gen_asm_list.py`、两个 `.manifests.toml`、证据脚本。
**语义核对**：步骤 0 次序 = SBZ(`[17:2]`) → `imms18=3` → reserved → `cfxha!=inner` → 所选帧无效，均先于状态切换 ✓；`cg5` 用 `cfx_frame_valid`、`cg9` 用 `cfxHA==15 && async_cause_id(9,3)!=0` ✓；`imm` 仅 `cg5` 取 `imms18[0]<<2`（`{61'd0,...}` 合计 64 位）、`cg9` 恒 0 ✓；`imms20={0,4,8}⇔imms18={0,1,2}`、8↔cg9 ✓。散文未写任务号/ADR/里程碑（`check-spec-purity` rc=0）✓。未改 QEMU/RTL/gem5/LLVM/测试代码 ✓。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 生成器 f-string 把 `{0, 4, 8}` 渲染成 `(0, 4, 8)` | ✅已修 | `gen_asm_list.py` 头部改 `{{0, 4, 8}}` 重生成 | `contract-asm-list.md` 行含 `{0, 4, 8}`；`check-asm-list`/`-drift` rc=0 |
| F2 Toolchain-01 changelog 旧条仍把 `{0,4}` 写成最终口径 | ✅已修 | 0.5.4-rc 条目改为 `{0,4,8}` + 帧选择位 | `check-spec-changelog` rc=0；grep 无旧集 |
| F3 contract-asm §5 初稿嵌套括号、可读性差 | ✅已修 | 改 `只接受 {...}：…；…。基址…` 结构 | 人工复读 + `check-spec-refs` rc=0 |
| F4 只重算 `spec/.manifests.toml` 时 `check-manifests-guard` rc=2 | ✅已修 | 补 `idl/.manifests.toml` 的 SimRISC-11.idl sha256（`d647f6…`→`62fae6…`） | `check-manifests-guard` rc=0（36 个 sha 全符） |
| F5 证据脚本块比对初版只扫 SimRISC-11（5 块） | ✅已修 | 改为扫 12 册 + 断言总数 263、变化仅 escape | run.sh 输出「总块=263 未变=262」 |
| F6 临时注入备份落在仓库内会污染变更集 | ✅已修 | 备份改到运行期临时目录 | `--inject` 后 `git status` 无新增；md5 还原一致 |
| F7 完成区写具体运行期目录路径 ⇒ `check-knowledge-refs` rc=2（ISS-352） | ✅已修 | 改为「运行期证据目录内 `run.sh`」；审阅记录去掉临时目录绝对路径 | `check-knowledge-refs` rc=0；证据脚本复跑 65/65 |

### 第 1 轮 reviewer 验收

**重跑（本人执行，命令均在仓库根）**
- 运行期证据目录内 `run.sh`：**64 PASS / 1 FAIL，rc=1**（完成区称 65/65 rc=0）。FAIL 原文：`变化块=[] 期望=['escape_ciii_cfx'] 总块=263 未变=263 | rc=1`。
- 根因：块比对基线取 `git show HEAD:`，WIP 提交 `113685cd` 后 HEAD 已含改动 ⇒ 空比对恒不等于期望；同因 `--inject` 分支用 `git diff --name-only`（提交态为空）⇒「DADAO-12 / contract-see 未改」两条断言在提交态恒真。
- IDL 块独立复核（基线 = merge-base `b3a02f5d`、13 个 `spec/SimRISC-*.md` 现场 glob、12 册落点）：总块 263、块集合相同、仅 `escape_ciii_cfx` 变、未变 262；`idl_render.py --check` rc=0（12 册 263 块逐字节一致）。
- 门控：`run.sh` 内 21 项逐项捕获 rc 全 0；本人另单独复跑 11 项（`check-spec-codeblocks`/`check-asm-list`/`-drift`/`check-legality-drift`/`check-idl-sync`/`-parse`/`-exec-anchor`/`check-manifests-guard`/`check-knowledge-refs`/`check-spec-refs`/`check-rule-refs`）**全 rc=0**。
- `make check` rc=2，唯一失败 = `check-isa-coverage`（缺 `llvm-mc`，环境）；基线 `b3a02f5d` 临时 worktree 同机对跑，日志归一化后 `diff` rc=0（169/169 行）。
- 自设注入①（`cp`+md5）：`idl/SimRISC-11.idl` `imms18 == 18'd3`→`18'd4` ⇒ `check-idl-sync` rc=2、`check-idl-parse` Error 1、`check-idl-exec-anchor` sha 漂移；还原 md5 `d83a89a4…` 一致 ⇒ 三项回 rc=0。
- 自设注入②：Toolchain-01 `{0,4,8}`→`{0,4}` ⇒ `run.sh` 4 FAIL（内容断言 + 锁 sha + `check-manifests-guard` rc=2）；还原 md5 `97011513…` 一致 ⇒ 回 64/65。生成锁 `--update` 幂等：fixture / anchor md5 前后相同。
- 锁哈希（本人 `sha256sum`）：SimRISC-11 `2686d8a5…`、Toolchain-01 `91f98d41…`、Kaiwu `b026c798…`、`.idl` `62fae622…` 与两份清单逐字一致；版本未动（0.5.7 / 0.5.4-rc / 0.8.0-rc）。

**编码/IDL 核对**：SimRISC-11 / Toolchain-01 / contract-asm(-list) / Kaiwu §4.2 / `opcodes.yaml` / `legality_rules.yaml` 六处口径一致（bit1 选帧、`{0,1,2}`、`3 ⇒ ILLI`、`[17:2]` SBZ、`imms20 {0,4,8}`、cg9 仅偏移 0）；IDL 步骤 0 次序与 `DADAO-12 §5.3` 逐条对齐，cg9 判据 `cfxha == 15` + `cfx_read(cfxHA,9,3)`（= cg9 rc3 `async_cause_id`）✓、cg9 `imm = 0` ✓；活文档无 `[17:1]`/`{0,4}` 于本任务 6 处真源。

**范围**：`git diff --name-status master...HEAD` = 14 路径，与完成区（10 真源 + 3 生成锁 + 本任务书）逐条相符；无实现/QEMU/RTL/gem5/内核/`DADAO-12`/`contract-see` 改动；完成区 6 行 ≤30；状态 待验收；工作树干净、14 文件与 HEAD md5 全等（注入全还原）；diff 无「银行」违禁术语。WIP 提交 `113685cd` 存在（本人未做任何 git 写操作；提交归属无法由对象判定，供架构师核对硬约束 1）。

**遗留确认**：`m18-idl-001`（master `70018e2a`，待开始，依赖本任务）已覆盖 `_op_escape` / `§4.6` / case13·14 / 两把 IDL 锁；`m18-qemu-004`、`m18-llvm-001` 覆盖 QEMU/LLVM 侧。**但 L2 `check-idl` 在其落地前为假绿**：`idl_exec._op_escape`、QEMU `helper_cfx_escape`（`imms18 & ~0x1u`）、case13 三方同按旧口径判 `imms18=2` 为 ILLI。

**判决：Needs Revision**（阻断 = F1；F2 文档级记 finding，F3/F4 须披露或派任务）
- F1（阻断·门控/输出真实性）证据脚本在被审提交 rc=1（64/65），完成区「65/65 rc=0」不可复现，且两条断言在提交态恒真。改法：块比对基线改 `git merge-base master HEAD`、变更集断言改 `git diff --name-status master...HEAD`；重跑须 65/65 rc=0 并同步完成区数字。
- F2（文档级）活文档旧口径未披露：`README.md:109/127`、`docs/DDLN/C-资源管理/DD-C004:9,69`、`docs/DDLN/Z-发展历程/DD-Z003:98`、`tests/inst/inventory.md:182`、`components/gem5/README.md:51` 仍以「0/+4、`imms18[17:1]`」为唯一合法集 ⇒ 与验收 2 冲突；均不在硬约束 2 清单 ⇒ 应写「待裁定」，现为「无」。
- F3（真源回退）`tools/spec/generate_opcodes.py:589/925` 仍生成 `imms18[17:1] == 0` 且无 `[17:2]`/`!= 3` 映射 ⇒ 重生成即回退 `contracts/opcodes.yaml` 并使 `check-legality-drift` 红；未披露。
- F4（回归）`tools/gem5/check_b6.py` 的 `EXPECTED_LEGALITY` 未随改：本人调其 `contract_rule_errors()` 实跑 ⇒ `escape_ciii_cfx legality … != ('imms18[17:1] == 0', …)` 1 error；未披露，M18 台账无 gem5 侧任务。
- 不阻断记档：IDL 注释称 cg9 转 `async_cause_ip`，而 `cfx_escape_enter` §4.6 仍 `excp_cause_ip + imm`（遗留③，已由 `m18-idl-001` 目标 2 覆盖）。

### 第 2 轮 engineer 自审

**返工范围**：仅处置 reviewer F1–F4；未改第 1 轮已通过的真源语义（IDL 块/prose 保持）。**F1**：`run.sh` 基线改 `git merge-base master HEAD`（实测 `b3a02f5d`）、块比对用 `$BASE:path`、变更集取 `git diff --name-status $BASE...HEAD ∪ 未提交`；提交态下 F1 两条断言不再恒真（`git diff $BASE...HEAD` 现有 14 路径）。**F2**：活文档 `DD-C004`/`inventory.md`/gem5 README 更新为新口径；`README.md`（M10 段）、`DD-Z003`（M10 段）属历史里程碑记录，保留并在完成区说明。**F3**：生成器 escape legality + `EXPR_TO_RULE` 同步；重生成前发现生成器对 8 条 fp 对齐项不幂等（会回退他人手工项），已补齐后重生成 byte-identical。**F4**：`check_b6.EXPECTED_LEGALITY` 加 `imms18[17:2] == 0` / `imms18 != 3`；静态 `contract_rule_errors()` 0 error。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 阻断：基线用 HEAD、变更集用裸 `git diff` ⇒ 提交态恒真 | ✅已修 | run.sh 改 merge-base 基线 + `$BASE...HEAD ∪ 未提交` 变更集 | run.sh 65/65 rc=0；`git diff --name-status b3a02f5d...HEAD` 14 路径非空 |
| F2 活文档旧口径（DDLN/inventory/gem5 README） | ✅已修 | 更新 3 处活文档；`README`/`DD-Z003` 历史句保留并说明 | grep 3 处无 `[17:1]`/「0 或 4」；`check-knowledge-refs` rc=0 |
| F3 生成器真源回退 | ✅已修 | escape legality/映射改 `[17:2]`+`!=3`；补 8 条 fp 对齐使生成幂等 | 二次重生成 diff 空；`check-legality-drift`/`check-asm-list`/`check-spec-codeblocks`/`validate-encoding` rc=0 |
| F4 gem5 静态 checker 未同步 | ✅已修 | `EXPECTED_LEGALITY.escape` 加 `_ESCAPE_CG9` | `contract_rule_errors(live_b6_entries())` 0 error（30 entries） |
| F1b 返工后完成区数字/变更集须同步 | ✅已修 | 完成区改 65/65、加返工 5 文件与生成态说明 | 完成区与 `git status` 逐条对账 |

### 第 2 轮 reviewer 验收

**重跑（本人执行，命令均在仓库根）**
- **F1**：运行期证据目录内 `run.sh` 基线 = `git merge-base master HEAD` = `c5cbcbf2`；提交态重跑 **65/65 PASS、rc=0**（44 快检 + 21 门控），块断言 `变化块=['escape_ciii_cfx'] 总块=263 未变=262`；变更集取 `$BASE...HEAD ∪ 未提交`（提交态非空 19 路径），两条原恒真断言已失效。
- **F1 注入①（未列）**：删 `contracts/opcodes.yaml` 的 `imms18 != 3` ⇒ `run.sh` FAIL（`opcodes !=3 实际缺失`）rc=1 + `check_b6.contract_rule_errors` 1 error；`cp`+md5 还原 `3d0535ff…` ⇒ 回 65/65、0 error。注：该注入下 21 门控仍全 rc=0 ⇒ `!=3` 无 L1 覆盖（见 F-3）。
- **F1 注入②（改块）**：手改 spec 内 `escape_ciii_cfx` 渲染块 `18'd3`→`18'd5` ⇒ `check-idl-sync` rc=2（漂移 diff 可见）；还原 md5 `e02786cb…` ⇒ rc=0；`run.sh --inject` 4/4 PASS、rc=0。
- **F2**：`DD-C004:9/69`、`tests/inst/inventory.md:182`、`components/gem5/README.md:50-52` 已改新口径（gem5 README 另注「模型跟改随 M18 实现任务」）；`README.md:109/127`、`DD-Z003:98` 均处 `### M10（2026-11-01）` 历史里程碑段，保留合理。余留 `[17:1]`：`spec/SimRISC-00:461`（0.5.6 变更记录，遗留⑥）、`tests/inst/11-cfx/*.S`（`m18-idl-001` 覆盖，遗留②）、`min_rom_probe_045t.py` 注释（用例 `imms18=-1`，新口径下仍 ILLI，行为不变）——均非活口径。
- **F3**：`generate_opcodes.py:596/932/933` 生成 `imms18[17:2] == 0` + `imms18 != 3` 并映射 `encode_sbz`；重生成 rc=0 且 **byte-identical**（md5 `3d0535ff…` 前后同、工作树净）；`check-legality-drift`/`check-asm-list`/`-drift`/`check-spec-codeblocks`/`validate-encoding` rc=0。`opcodes.yaml` 差异仅：escape legality 2 行、4 条单元素 `rule_refs` 流式→块式、头部计数 242→246（现场核：基线与现文件非空 `rule_refs` 均 246 ⇒ 原头部为陈旧值）；无 opc/mask/value/fields 变化。
- **F4**：`check_b6.py` `_SBZ_ESCAPE="imms18[17:2] == 0"`、`_ESCAPE_CG9="imms18 != 3"`；`contract_rule_errors(live_b6_entries())` = **0 error**（30 entries）。
- 21 门控逐项 rc=0 + 本人单独复跑 11 项 rc=0；锁哈希（本人 `sha256sum`）`2686d8a5…`/`91f98d41…`/`b026c798…`/`62fae622…` 与两份清单逐字一致；版本未动（0.5.7 / 0.5.4-rc / 0.8.0-rc；diff 中 0 行版本变更）。
- `make check` rc=2（唯一失败 `check-isa-coverage`，缺 `llvm-mc`）；与基线 `c5cbcbf2` 临时 worktree 同机对跑，日志归一化后 `diff` rc=0（169/169 行）。

**范围**：`git diff --name-status c5cbcbf2...HEAD` = `master...HEAD` = **19 路径**，与完成区（真源/工具 10 + 返工 5 + 生成锁 3 + 本任务书）逐条相符；无实现/QEMU/RTL/gem5 模型/内核/`DADAO-12`/`contract-see` 改动；完成区 9 行 ≤30；状态 `待验收`；工作树净、19 文件 md5 == HEAD（注入全还原）；diff 无「银行」。

**遗留**：`m18-idl-001`（master，待开始）覆盖 `_op_escape`/`§4.6`/case13·14/两把 IDL 锁，`m18-gem5-001`/`m18-chipyard-001`/`m18-qemu-004`/`m18-llvm-001` 覆盖实现侧；本任务未把 L2 `check-idl` 列为通过项，第 1 轮记录仍明写其落地前为假绿 ⇒ **无假绿**。

**判决：Accepted**（F1–F4 全部处置，本人重跑复核通过；下列记档不阻断，交架构师收尾）
- F-1：`run.sh` 输出标签仍写「12 册对照 HEAD」，实际基线已用 `$BASE`（文案陈旧）。
- F-2：`.tao/knowledge/discussing.md:34` N2 结论仍 `{0,+4}` + `imms18[17:1]`，已被 `ADR-0060 D4` 取代；属主会话写者，建议收尾更新。
- F-3：`imms18 != 3` 无 L1 门控覆盖（`check-legality-drift` 只渲染带 `rule_refs` 的 LEGALITY 段），现仅 `run.sh` 内容断言 + `check_b6` 守；建议补 `rule_ref` 或登记。
- F-4：遗留④已完成（`MEMORY.md:76` 随 master `70018e2a` 更新），完成区该条可删。
