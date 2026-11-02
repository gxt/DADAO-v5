# INTEG-045t: cfx 指令清理（reserved 规则/删除 cfxld-cfxst/fence 宏）

**模块**：integ
**项目里程碑**：M10
**依赖**：INTEG-041t（fence ciii）、INTEG-044t（权限）
**状态**：已验证

## 背景

1. `encode_cfx_reserved` 目前只挂 `fence`，应覆盖所有带 `cfxha` 的核芯功能扩展指令；根因是 `contracts/legality_rules.yaml` 的 spec_cite/description 和 `opcodes.yaml` 的 rule_refs 只挂 fence，生成器按 rule_refs 输出。
2. 用户决定删除 `cfxld/cfxst`；SimRISC-11 仍有一整节/汇编表/decode ILLI，SimRISC-00 编码表仍有 `crii` 和两格。
3. SimRISC-11 缺 fence 12 个宏名表；`7–14` reserved 也应统一为 `6–14`。

## 目标

1. **reserved 规则**
   - `legality_rules.yaml`：`encode_cfx_reserved` 描述改为“所有带 cfxha 的核芯功能扩展指令”；spec_cite 改 SimRISC-11；
   - `opcodes.yaml`：`trap/escape/cfx2rd/cfx2rc/fence` 都挂 `encode_cfx_reserved`；
   - 生成器/附录重新生成；补测试覆盖各 cfx 指令的 reserved→ILLI。
2. **删除 cfxld/cfxst**
   - SimRISC-11：删除该节、汇编速查行、`crii`、decode ILLI；更新分类/说明；
   - SimRISC-00：删除 `crii` 格式定义、编码表两格、历史引用；
   - `contracts/opcodes.yaml`：删除 `cfxld_crii_cfx`/`cfxst_crii_cfx`；
   - LLVM MC/汇编器/别名/矩阵/统计/测试同步；不再保留 `crii`。
3. **fence 宏表**
   - SimRISC-11 增 12 个宏：`PRED_CR/CW/CI/CO/MR/MW`、`SUCC_CR/CW/CI/CO/MR/MW`；
   - 值与 LLVM AsmParser 一致（1<<6..1<<11 / 1<<0..1<<5）；
   - `|` 组合，整体作为 immu18；`hb`/保留位 SBZ。
4. **版本/锁/索引/合同** 同步；不改 fence 编码语义。

## 验收

- `make check`、`check-modules`、`check-arch-smoke`、`check-arch`、`check-lit`、`check-spec-readonly`、`check-spec-changelog`、`check-patch-tree`、`check-source-state`、`check-isa-coverage` 全 rc=0。
- 证据 `.work/evidence/<任务号>/run.sh` 注入→FAIL→cp+md5 还原→PASS。
- 不删除 QEMU-047t 已删探针之外的内容；不改权限模型/启动链。
- 完成区 ≤30 行；任务书/里程碑 `待验收`；临时 `/tmp/opencode/INTEG-045t/`。

## 约束

- 只做本任务；不提交、不 push；不跑 full/夜跑；重建先申报。
- `encode_cfx_reserved` 必须由源规则/生成器修，不能手改生成附录。

## 用户授权原话（派单原话，原样落纸）

> 范围：
> 1. `encode_cfx_reserved` 应覆盖所有带 cfxha 的核芯功能扩展指令（trap/escape/cfx2rd/cfx2rc/fence），不能只挂 fence。修 `contracts/legality_rules.yaml`、`contracts/opcodes.yaml` 的 rule_refs/spec_cite/description，重新生成附录；补覆盖测试。
> 2. 删除 cfxld/cfxst：SimRISC-11 整节/汇编表/decode ILLI；SimRISC-00 `crii` 格式定义、编码表两格、历史引用；contracts/opcodes 两个条目；LLVM MC/汇编器/别名/矩阵/统计/测试同步；不再保留 `crii`。
> 3. SimRISC-11 补 fence 12 个宏表：`PRED_CR/CW/CI/CO/MR/MW`、`SUCC_CR/CW/CI/CO/MR/MW`，值与 AsmParser 一致；`|` 组合，整体 immu18；hb SBZ。
> 4. reserved 列表统一 6–14/19–61。
> 5. 同步版本/锁/索引/合同；不改 fence 编码语义。

（`spec/` 只读册修改授权依据即本条原话；锁文件注记引用本节。）

## 完成区

**状态**：已验证

**测试结果**：`make check` rc=0；`check-modules` rc=0（L2 PASS）；`check-arch-smoke`/`check-arch` rc=0（7 个 cfx 探针 + arch-smoke PASS）；`check-lit` 159/159；`check-isa-coverage` PASS（264 身份，accept 264/reject 0）；`check-spec-readonly` 21 册 OK；`check-spec-changelog`/`check-patch-tree`(205)/`check-source-state`/`check-qemu_trans --strict`(264/264, orphan 0) rc=0。证据 `.work/evidence/INTEG-045t/run.sh`：默认全绿；`--inject` 三处（删 rule_ref / 改 `PRED_MR` 值 / reserved 退回 7–14）均 FAIL→cp+md5 还原→回绿。

**修改文件**：
- 合约：`contracts/opcodes.yaml`（重生成：264 条，excluded 0；5 条 cfx 挂 `encode_cfx_reserved`）、`contracts/legality_rules.yaml`（spec_cite=SimRISC-11 §1、6–14/19–61、覆盖全部 cfx 指令）；`.tao/contracts/{contract-isa,contract-asm,contract-asm-list,contract-see}.md`。
- 规范：`spec/SimRISC-11`（删 SRAM 节、屏障节前移 §5、12 宏表、6–14）、`spec/SimRISC-00`（删 `crii`/两格/ILLI 条、附录 0.5.6-rc）、`spec/Toolchain-01`、`spec/Machine-01`、`spec/README.md`、`manifests/spec-readonly.lock.toml`（4 册 sha256 + 授权注记）。
- 生成器/门控：`tools/spec/{generate_opcodes,gen_legality_list,check_scope,check_legality_invariants,check_asm_prose,check_qfc_coverage}.py`、`tools/llvm/{gen_asm_list,gen_isa_coverage}.py`、`tools/llvm/llvm-isa-backend-matrix.{md,tsv}`、`tools/qemu/{check_harness_ops,generate_atomics_vectors}.py`、`tools/testcases/{generate_lit_vectors.py,lib/build_test_binary.py,validate_m5_vectors.py}`。
- 测试：`tests/unit.yaml`（删 gen-excluded 条目）、`tests/unit/llvm/lit/MC/DADAO-gen/*`（重生成，删 `gen-excluded.s`）、`tests/inst/atomics/atomics-fence.yaml`、`tests/arch/umon/m5_perm_reserved_illi.s`、`tests/unit/llvm/lit/MC/DADAO/README-m5.md`、17 个 `tools/testcases/arch/min_rom_probe_*.py`（ILLI 毒饵改 `fence cfx0, hb=1`）。
- 组件：`components/qemu/patches/{target/dadao/insn.decode,target/dadao/insn_trans/trans_ctrl.c.inc}.patch`（删 2 桩、fence 保留集 6–14）、`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrFormats.td.patch`（删 `crii` 注释）；两组件 changelog 各 1 条。
- 文档/台账：`README.md`、`tests/INVENTORY.md`、`docs/DDLN/{A002,C001,C004,E003,Z003}`、`.tao/knowledge/milestones.md`；证据 `.work/evidence/INTEG-045t/{run.sh,check.py}`。

**验收结果**：真实输出见 `.work/log/INTEG-045t-evidence.log`（各门控 `RESULT ... rc=0`）与 `.work/evidence/INTEG-045t/*.log`；`build-qemu` rc=0（改 2 份补丁后重建，`.work/log/qemu/INTEG-045t-build.log`）。

**新发现/坑**：
- 删记录会连带触发 **`check-interface`**（`check_qemu_trans --strict` 报 orphan trans）⇒ QEMU 两桩必须同删（非只改 spec）。
- `0x7C` 毒饵失效：删指令后该格变保留（UNDI），全部探针毒饵改 `fence cfx0, hb=1`（`encode_sbz` ⇒ ILLI，与 cfx 域无关）。
- `scope: excluded` 现 0 条 ⇒ `check_scope` 的「每 scope 非空」对 `excluded` 放行（词表保留）；`gen_legality_list`/`gen_asm_list`/`gen_isa_coverage` 的空分区文案需现场派生分支。
- 知识库待同步（主会话）：`.tao/knowledge/MEMORY.md` 第 46 行「fence 现位于 SimRISC-11 §6」→ §5、第 81 行「12 种格式含 crii」→ 11 种、第 39/44 行 `excluded` 2 条口径。
- 改 LLVM 补丁（即使仅注释）会重编 clang ⇒ `clang --version` 的源码版本串变 ⇒ `check-musl-freshness` 的两枚 stamp 红；按提示 `make build-musl-shared JOBS=8` 重装即回绿（rc=0）。

**遗留问题**：
- `spec/DADAO-12`（SEE）§5.1/§5.2 仍以「预留未启用」描述 `cfxld`/`cfxst`：改它须与 `DADAO-22` 版本互锁同步升版，超出本任务列举的 spec 面 ⇒ 建议单立 spec 任务（`DADAO-12` C8 段 + §5.1/§5.2/cg7 注记）。
- `min_rom_probe_034t.py` 的 C7/C9/C16（`cs.eq/ne` 的 rf 变体）FAIL 为**既有**失效（该指令 `SPEC-163t` 已删，探针未随之更新，不在本任务门控内）；本任务仅改其 ILLI 毒饵常量（`git diff --stat` = 1 行）；C7/C9/C16/F23/F24 均为 `SPEC-163t` 既有失效。

## 审阅记录

### 第 1 轮 engineer 自审

范围：本任务全部改动（源规则/生成器/规范/合约/组件补丁/门控/测试/证据脚本）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `check_scope` 自检 `break_decode` 在无 excluded 记录时 `next()` 抛 StopIteration | ✅已修 | 缺失时合成一条 excluded 记录再删 decode | `check_scope --self-test` 11 例全 PASS |
| F2 生成器删 `f_crii` 后误删 docstring 空行（无关噪声） | ✅已修 | 恢复空行 | `git diff` 仅语义行 |
| F3 证据脚本 `check.py` 把 AsmParser 的 `1<<N` 读成 N（比较错位），宏值断言恒假 | ✅已修 | `wants = 1 << int(sh)`；A1d 改为「书 + 节标题真实存在」 | `check.py` 全 PASS；注入改宏值可达 FAIL |
| F4 删记录只改 spec 会红 `check-interface`（orphan trans） | ✅已修 | QEMU 两桩+两 pattern 同删；`fence_cfx_reserved` 同步 6–14 | `check_qemu_trans --strict` 264/264 orphan 0；`check-arch` PASS |
| F5 `0x7C` 毒饵语义变化（ILLI→UNDI）会让 17 个探针假失败 | ✅已修 | 毒饵统一改 `fence cfx0, hb=1`（`encode_sbz`）；注释同步 | `check-arch` PASS；006t/042t 直跑 PASS；034t 仅既有 cs.eq-rf 失效 |
| F6 `tests/unit.yaml` 仍指向已删的 `gen-excluded.s` | ✅已修 | 删该条目 | `check-tests-index` PASS（239 条） |
| F7 组件补丁改动未留痕 | ✅已修 | 两组件 changelog 各 1 条（M10） | `check-component-changelog` PASS |
| F8 `crii` 在 LLVM `.td` 注释残留 | ✅已修 | 删注释 4 行（仅注释），重导出 1 补丁 | `check-patch-tree` 205 OK；`check-index-blobs` OK |
| F9 空分区文案（矩阵/汇编表）会产生「（）」「分布为 」 | ✅已修 | 生成器加空分区分支 | `check-isa-coverage --check` PASS；`gen_asm_list` 幂等 |
| F10 SEE（`DADAO-12`）仍描述 `cfxld`/`cfxst` | ⏸延后 | 需与 `DADAO-22` 互锁升版，超出任务列举 spec 面 | 已登记「遗留问题」第 1 条 |
| F11 权限/启动链未受影响 | ❌不修 | 本次不改权限模型与启动流程（QEMU 仅删 2 桩 + fence 保留集） | `check-arch` 的 044t/integ044t 权限探针全 PASS |

判决：全部 finding 已处置（F10 延后、F11 无需改）；状态置 `待验收`，请 reviewer 独立验收。

### 第 1 轮 reviewer 验收

**重跑记录（reviewer 亲自执行，workdir=仓库根）**：`.work/evidence/INTEG-045t/run.sh` 全量重跑
`RUNSH_EXIT=0`；逐项 `RESULT`：static-assertions / legality-invariants / qfc-coverage / harness-ops /
qemu-trans(264/264, orphan 0) / check(L1 83 项) / check-modules(L2 PASS) / check-arch-smoke / check-arch
(7 cfx 探针 PASS) / check-lit(159/159) / check-spec-readonly(21 册) / check-spec-changelog /
check-patch-tree(205) / check-source-state / check-isa-coverage(264, accept 264/reject 0) 共 15 项 rc=0。
`check.py` 独立重跑 26 断言全 PASS（rc=0）；`run.sh --inject` 三处注入→FAIL(rc=1)→cp+md5 还原(md5 相等)→回绿，
`EVIDENCE INJECT: PASS`。**独立注入（第 4 处，非 engineer 三处）**：改
`components/llvm-project/patches/.../DADAOAsmParser.cpp.patch` `SUCC_MW 1<<5→1<<6`（md5
2b4f8f86→d601568c）→ `check.py` A5d FAIL（`{'SUCC_MW': (64, 32)}`，rc=1）→ `cp`+md5 对账还原
（2b4f8f86 相等）→ `check.py` rc=0。快照对账：验收前后 `git status -uall` 逐行一致、4 个关键文件 md5
`md5sum -c` 全 OK，仓库内无 `.preinject` 残留。`generate_opcodes.py` 幂等重跑 md5 不变 ⇒ `opcodes.yaml`
确为生成产物、无手改。

**约束核验**：① cfx 覆盖：opcodes 5 条带 `cfxha` 记录全挂 `encode_cfx_reserved`（rule_refs + 保留表达式），
QEMU 侧 `DADAO_CFX_IS_RESERVED`=6–14/19–61 与 fence `fence_cfx_reserved` 一致；② `cfxld/cfxst/crii`
在 SimRISC-11/00、opcodes、组件补丁、测试/矩阵、合约中零残留（仅历史变更记录/DDLN 背景说明保留）；
③ fence 12 宏名/值与 AsmParser 逐项一致（`PRED 1<<6..11`/`SUCC 1<<0..5`），`|` 组合整体 immu18、
`hb=immu18[17:12]` SBZ 说明正确；④ 保留编号 6–14/19–61 统一（规则/SimRISC-11/QEMU/测试，无 7–14 残留于现场面）；
⑤ 未提交、未 push（工作树全为未提交改动，`master..HEAD` 0 commit）、未跑 full/夜跑、未改权限模型/启动链。

**遗留核验**：`DADAO-12` §5.1/§5.2/cg7 仍描述 `cfxld/cfxst`——已披露（建议单立 spec 任务，成立）；
MEMORY.md 4 处口径未同步——已披露（主会话收尾沉淀）；`min_rom_probe_034t` 独立重跑 FAIL 5 项
（C7/C9/C16 **及 F23/F24**），rf 变体已随 `SPEC-163t` 删除、非本任务门控面（check-arch 不含 034t），既有失效判断成立。

**Findings（均文档级，不阻断，architect 收尾一并改）**：
- F-R1 完成区遗留第 2 条「F* ILLI 例全 PASS」与真实不符：034t 实跑 F23/F24 亦 FAIL（共 5 项）；措辞应改为「C7/C9/C16/F23/F24 均为 `SPEC-163t` 既有失效」。
- F-R2 `spec/DADAO-12` 附录 0.7.3-rc 内「保留 cfx（7–14、19–61）」未统一 6–14（该行未被遗留声明点名）⇒ 并入后续 DADAO-12 spec 任务。
- F-R3 `tests/unit/llvm/lit/MC/DADAO/README-m5.md` 1 行口径改未在完成区「修改文件」逐条列出（枚举遗漏）。

**判决：Accepted**——验收命令块在 reviewer 独立重跑下全 rc=0、注入反例双向可达且可还原、四类阻断面
（代码行为/门控退出码/断言计数/语义）无违反；上述 3 条文档级 finding 由 architect 在收尾提交修正。
