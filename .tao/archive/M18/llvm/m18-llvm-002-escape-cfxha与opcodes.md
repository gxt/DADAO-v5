# m18-llvm-002: LLVM/opcodes 支持 `escape cfxHA` 与新槽位（任务链第 1 环）

**模块**：llvm
**项目里程碑**：M18
**依赖**：`m18-spec-007`（已合入：`escape cfxHA`、`imms18` 恒 0、cg5/cg9 新槽位、opcodes/legality/别名表已重生成）；**LLVM 写者**须等 `m20-llvm-003` 释放（同 `components/llvm-project`，串行）
**可并行分片**：否
**预估**：2–3 h（标定：同档 llvm-001 汇编/反汇编支持约 2 h；本任务另含 legality/别名重生成，取 1–1.5×）
**档位**：中改（MC/AsmParser/Disassembler）
**状态**：已验证
**执行环境**：本地

## 背景

`m18-spec-007` 已把 `escape` 汇编格式改为 **`escape cfxHA`**（无 `imms18` 操作数；机器码字段保留但必须为 0，非 0 ⇒ `ILLI`），并改了 `cg5`/`cg9`/`cg0–cg3` 的槽位。`contracts/opcodes.yaml`、`legality_rules.yaml`、`cfx-aliases.txt` 已按新规范重生成，但 LLVM 侧仍：接受 `escape cfxha, imms` 形式、按旧操作数打印、未拒绝非 0 `imms18`。

所有后续任务（QEMU/RTL/gem5 探针、内核汇编、测试向量）都要用汇编器生成新编码/新槽位，因此本任务必须排在最前。

## 目标

1. **AsmParser**：`escape cfxHA` 合法；带第二个立即数（旧 `escape cfxha, 0/4/8`）⇒ 汇编错误（提示改用 `escape cfxHA` + 写 `cg5 rc10`）。
2. **编码**：生成的机器码 `imms18 = 0`；`imms18[17:2]` 与非 0 的 `imms18[1:0]` 由 legality 判 `ILLI`（与 `legality_rules.yaml` 一致）。
3. **反汇编**：统一打印 `escape cfxHA`；不得再打印偏移或帧选择位。
4. **生成物**：`opcodes`、`instrinfo`、别名/`.set` 表、asm-list 由仓库生成器重跑（`make generate-*` / `tools/llvm/gen_asm_list.py`），`check-opcodes-repro`/`check-asm-list-drift` rc=0。
5. **测试**：`tests/unit/llvm/lit/**` 更新（含 `cfx2-trap-escape.s` 的 `excp_cause_ip` 槽位 rc3→rc2、`escape` 新语法）；补一条“带立即数 ⇒ 汇编失败”和一条“`imms18 != 0` ⇒ ILLI 合法性”用例。
6. **不做**：不改 `tests/inst/**` 向量（`m18-testcases-004`）、不改 QEMU/RTL/gem5/IDL/内核。

## 验收（逐条贴真实 rc）

1. `lit` 全绿（记录总数）；`llvm-mc -show-encoding` 对 `escape cfx0` 输出 `imms18 = 0`；带立即数报错。
2. `llvm-objdump` 往返：`escape cfxHA` 汇编→反汇编→汇编，字节一致。
3. `check-opcodes-repro`、`check-asm-prose`、`check-asm-list`、`check-asm-list-drift`、`check-legality-drift`、`check-legality-invariants`、`check-cfx-aliases`、`check-instrinfo`、`check-decodetree-repro` rc=0。
4. 可达 FAIL ≥2 路（改回旧语法/允许非 0 imms18），`cp`+md5 还原回绿。
5. 组件补丁经 `make_patch.py llvm` 重导；`check-patch-tree` llvm 段 0 problem；不改版本号。
6. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/llvm-project/patches/**`、`components/llvm-project/changelog.md`、`tests/unit/llvm/**`、`tools/llvm/gen_asm_list.py`（如需）、本任务书。
3. 不改 spec/契约/Makefile/QEMU/RTL/gem5/IDL/内核；不改版本号；`cp`+md5 还原。
4. LLVM 写者互斥：等 `m20-llvm-003` 合入后再动同一组件。

## 待裁定

无。

## 完成区

**测试结果**：`make check-lit` **186/186 PASS**（rc=0，现场统计）；`check-lit-full` 11/11 rc=0；`check-cfx-vectors` **36 条 0 错误**、rc=0（修前 rc=2，唯一红是 `cfx_umon_excp_cause_ip` rc3 旧槽位，已回绿）。证据脚本默认 **40/40**、`--inject` **16/16**，均 rc=0。
**修改文件**：`components/llvm-project/patches/.../{AsmParser/DADAOAsmParser,Disassembler/DADAODisassembler,MCTargetDesc/DADAOMCInstPrinter}.cpp.patch`（`make_patch.py llvm-project`：3 written/96 unchanged，series 99 不变）；`components/llvm-project/changelog.md`；`tests/unit/llvm/lit/MC/DADAO/{cfx2-escape-frame,cfx2-escape-frame-err,cfx2-trap-escape,cfx2-trap-escape-err}.s`、`validate_cfx_vectors.py`、`README-m5.md`、`gen-fast.s`；`tests/unit/llvm/lit/MC/DADAO-gen/gen-ciii.s`；`tests/case-ledger.tsv`（生成物，+26/−11，`--write`）；`tests/ee-tiny/cfx_hmon_tiny.S`、`tests/ee-vast/hmon_vast.S`（**越界披露**：仅改 `escape` 语法使 `build-bootrom` 可汇编，槽位语义归 `m18-testcases-004`）；本任务书。证据 = 运行期证据目录内 `run.sh`。
**验收结果**：汇编 `escape cfx_umon/cfx0/cfx_hart/cfx_power` ⇒ `7e000000/7e000000/7e3c0000/7efc0000`（imms18=0）；旧第二操作数（`0/4/8`、`[excp_cause_ip, …]`、`sym`）rc=1 且诊断含 `use 'escape cfxHA'` + `cg5 rc10`；反汇编只回显 `escape cfxHA`、无 `excp_cause_ip`，asm→asm→obj `cmp` rc=0；手工字 `7e000001/…02/…04/7effffff` ⇒ `<unknown>`，`7e000000` 对照 ⇒ `escape cfx_umon`。门控 rc：opcodes-repro/asm-prose/asm-list/asm-list-drift/legality-drift/legality-invariants/cfx-aliases/instrinfo/decodetree-repro/cfx-vectors 全 **0**；`check-patch-tree` llvm 段 **99 patch、0 assertion**（整库 rc=1 仅 musl 2 条基线漂移）；`check-case-ledger`/`check-component-changelog`/`check-cfx-alias-install` 均 0。安装根==构建树 md5：llvm-mc `609b72a8…`、llvm-objdump `944f2521…`。注入①恢复旧语法（接受第二操作数）⇒ 负例 lit 红、汇编 rc=0（mutation caught）；②解码器放行非 0 imms18 ⇒ `<unknown>` 变 `escape`、legality lit 红；均 `cp`+md5 还原、重建后 llvm-mc md5 回 `609b72a8…`。
**新发现/坑**：① `tools/testcases/generate_lit_vectors.py` 仍按旧 `escape cfx63, [excp_cause_ip, 4]` 生成（不在本任务允许路径），本次手改生成物 `gen-fast.s`/`DADAO-gen/gen-ciii.s`，须由 `m18-testcases-004` 修生成器；② `make_patch.py` 要求组件源树 clean，须先 `git commit --amend` 收敛 base+1；③ `cp -p` 还原保留 mtime 会让 ninja 不重建（用 `cp`+`touch`）；④ 重建后 llvm-objdump 二进制 md5 与旧安装根不同，重跑 `install-host` 后一致。
**遗留问题**：① `tests/ee-vast/hmon_vast.S` 仍用旧槽位（rc3=cause_ip、旧 +4 返回点），本次仅改语法；`escape` 的 +4 语义需迁移到 `cg5 rc10`，归 `m18-testcases-004`；② 全库其它旧语法（`tests/unit/gem5`、`tests/unit/linux`、`tools/chipyard`、`tests/inst`）未改，按任务链后续任务处理；③ `check-patch-tree` 整库 rc=1 为 musl 基线红，与本任务无关。

## 审阅记录

### 第 1 轮 engineer 自审

**逐行审查**（源树 `.work/source/llvm-project` 3 文件；与重导补丁逐字节一致）：
- AsmParser：`parseOperand` 后仅在 `Comma` 时报「第二操作数」错、`not EOS` 报尾随记号错，其余 push `createImm(0)`；SBZ 值唯一可产生 0，`.td` 两操作数布局未动 ⇒ 解码器/CodeGen 无影响。
- Disassembler：`hasInvalidEscapeImm` 先判 `opcode == DADAO::escape_ciii`（trap/fence 不误伤），operand 1 必存在（该 def 固定两操作数）；非 0 返回 `Fail` ⇒ `<unknown>`，与既有 ILLI 字（mreg/ISS-468）同口径。
- InstPrinter：`Mnem != "escape"` 才打印 imm18；cfx 名解析不变；trap/fence 路径未改。
- 测试/期望值：编码独立派生自 `contracts/opcodes.yaml`（`0x7E | cfxha<<18 | imms18=0`），oracle 不调 llvm-mc；负例每条 rc 可达且诊断串可失配；raw 字用例独立于汇编器。
- 可达 FAIL：注入①旧语法复活、②解码放行非 0，均实测红并 `cp`+md5 还原（见完成区）；证据脚本无恒真断言、计数现场统计。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `check-lit` 依赖 `build-bootrom`，`tests/ee-*` 旧语法使门控红（超出允许路径） | ✅已修（披露） | 仅改两处 `escape` 语法；vast 注释指向 testcases-004 | `make check-lit` 186/186 rc=0 |
| F2 生成物 `gen-fast.s`/`gen-ciii.s` 的生成器仍产旧语法（不在允许路径） | ⏸延后（记录） | 手改两份生成物为 `escape cfx63`/enc `7efc0000` | `check-lit-full` 11/11、`check_lit_gen` rc=0 |
| F3 新增/改写 lit 使 `check-case-ledger` 红（生成物越界） | ✅已修（披露） | `check_case_ledger.py --write`（+26/−11） | `check-case-ledger` rc=0 |
| F4 `cp -p` 还原不触发重建（首轮 inject md5 未回） | ✅已修 | 还原改 `cp`+`touch`，并断言二进制 md5 | `--inject` 16/16 rc=0，md5 回 `609b72a8…` |
| F5 `escape cfx20` 等 reserved cfx 仍可汇编 | ❌不修（口径） | MC 层不判 `encode_cfx_reserved`，与 `trap cfx20` 现有 lit 一致；运行期 ILLI | `cfx2-trap-escape.s` reserved 用例通过 |

**判决**：无未修 finding；状态 → `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录**（全部本人执行，命令取自任务验收块/证据脚本；退出码为真实 `$?`）
- 汇编：`llvm-mc -show-encoding` ⇒ `escape cfx_umon`/`cfx0` = `7e,00,00,00`、`cfx_hart` = `7e,3c,00,00`、`cfx_power` = `7e,fc,00,00`（均 rc=0，imms18=0）；对象 `.text` 原始字节 `7e 00 00 00 / 7e 00 00 00 / 7e 3c 00 00 / 7e fc 00 00`（od 实测）。
- 负例：`escape cfx_umon, 0`、`escape cfx0, 4`、`escape cfx_hart, [excp_cause_ip, n]`、`escape cfx0, sym` ⇒ **rc=1**，诊断含 `escape takes no second operand; use 'escape cfxHA' and set the return point with 'cg5 rc10' (imms18 is SBZ)`；`escape cfx_umon 4` ⇒ **rc=1** `unexpected token after 'escape cfxHA'`。
- 反汇编/往返：`llvm-objdump -d` 4 行只回显 `escape cfx_*`，`excp_cause_ip`/偏移 0 命中；`-filetype=asm` → 再汇编 → `cmp` **rc=0**（`cfx0` 归一回显 `cfx_umon`，属别名表 canonical）。
- ILLI：手工字 `7e000001/7e000002/7e000003/7e000004/7effffff` 全 `<unknown>`；对照 `7e000000` ⇒ `escape cfx_umon`。与 `contracts/opcodes.yaml escape_ciii_cfx`（`imms18` bits[17:0]、legality `imms18 == 0`）、`legality_rules.yaml`（escape 非 0 ⇒ ILLI）一致。
- 门控（本人逐条重跑，rc 全 0）：`check-opcodes-repro`、`check-instrinfo`、`check-decodetree-repro`、`check-asm-list`、`check-asm-list-drift`、`check-asm-prose`、`check-legality-drift`、`check-legality-invariants`、`check-cfx-aliases`、`check-cfx-alias-install`、`check-cfx-vectors`（`向量 36 条，错误 0 条`）、`check-case-ledger`、`check-component-changelog`。
- `make check-lit` **rc=0，现场统计 Total Discovered 186 / Passed 186**；新负例 `cfx2-escape-frame-err.s`、`cfx2-trap-escape-err.s` 均在 186 内 PASS；`make check-lit-full` **rc=0，11/11**。`check-patch-tree`：`llvm-project: 99 patch(es)`、llvm 段 assertion 0（整库 rc=1 仅 musl 2 条基线漂移，本任务未碰 musl）。
- 证据脚本：**运行期证据目录内的 `run.sh`** 默认 **40/40 pass、rc=0**；`--inject` **16/16 pass、rc=0**（两路注入均实测转红、`cp`+md5 还原，二进制 md5 回 `609b72a8…`）。
- 安装根 == 构建树 md5：llvm-mc `609b72a871b57623c987b9a324cb2545`、llvm-objdump `944f25214b39792f72fd3e356220002b`，与记录值一致。
- **本人独立注入③**（与 engineer 两路均不同）：源树 AsmParser 的 SBZ 操作数 `createImm(0)` → `createImm(4)` 并 `build-mc` ⇒ 编码 `7e000004`、反汇编 `<unknown>`、受影响 lit **FAIL 2/2**、`run.sh` **rc=1（38 pass/2 fail）**；`cp`+`touch` 还原 + 重建 ⇒ 源文件 md5 回 `aeace925…`、llvm-mc 回 `609b72a8…`、`run.sh` 回 **40/40 rc=0**、源树 `git status` clean。

**约束核验**
1. 变更集 16 文件与完成区声明逐一对上（`git diff --name-only` 16 行；验收前后两次快照 diff 无差异、工作树 `git status --porcelain -uall` 空）。
2. 越界两处披露属实：`tests/ee-tiny/cfx_hmon_tiny.S`、`tests/ee-vast/hmon_vast.S` **仅改 `escape` 语法**（`escape cfx_hmon, [excp_cause_ip, 0/4]` → `escape cfx_hmon`）与配套注释，无槽位/`cfx2rc` 写入/策略改动；语义迁移已披露归 `m18-testcases-004`。
3. 无 `components/{qemu,linux,gem5,chipyard}/**`、无 `spec/`、无 `.tao/contracts/`、无 `Makefile`；版本号未升；未 push（`git branch -r --contains HEAD` 空）；状态 `待验收`。
4. oracle 独立性：`validate_cfx_vectors.py` 不调 llvm-mc、`n==0` 即 FAIL；`check_lit_gen.py` 独立于生成器。lit `@@ OBJ:` 由真实 objdump 输出驱动，非同源自比。

**finding（不阻断，已披露）**：`gen-fast.s`/`DADAO-gen/gen-ciii.s` 为手改生成物，`tools/testcases/generate_lit_vectors.py` 仍产旧语法（不在本任务允许路径）⇒ 归 `m18-testcases-004` 修生成器，否则重生成会回退旧写法。

**判决：Accepted**

