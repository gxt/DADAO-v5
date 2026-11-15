# m13-llvm-001: LLVM 侧删 `ft2ft`/`fo2fo`、加 `rf2rf`（.td/MC/AsmParser/MCInstPrinter + lit）

**模块**：llvm
**项目里程碑**：M13
**依赖**：`m13-spec-010`（spec 侧已合 `cb8ca30d`：删 `ft2ft`/`fo2fo`、加 `rf2rf`；id 264→263）
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（看 diff + ≥2 路注入 + 相关门控）
**状态**：已验证

## 背景

`m13-spec-010` 只改了 spec 侧。现场仍有一处**仓库自相矛盾**：`contracts/opcodes.yaml` 已无 `ft2ft`/`fo2fo`，但 `tests/inst/07-floating-point/{ft2ft,fo2fo}_orri_rf.S` 仍在且被 `tests/inst.yaml` 索引（2 条），**没有任何门控能发现**。本任务把该组件面与 spec 对齐。

## 任务

1. `components/llvm-project` 补丁：`DADAOInstrInfo{,FP}.td` 删两条定义、加 `rf2rf`（`opc=OPC-octa`、`opx=111-100`、`orri`/`rf` 组、目的含 `rf0` ⇒ 由 legality 诊断/报错）；`AsmParser` 助记符、`MCInstPrinter` 反汇编；
2. lit：`tests/unit/llvm/lit/MC/DADAO/` 与 `CodeGen/DADAO/` 增删对应用例；`DADAO-gen` 生成矩阵同步；
3. 补丁用 `make_patch.py llvm` 导出，`check-patch-tree` **llvm 段 0 问题**、`--source-state` llvm OK。

## 验收（逐条贴真实 rc）

1. 旧指令在**本组件面**归零：`grep -rn "ft2ft\|fo2fo"` 在 `components/llvm-project/**`、`tests/unit/llvm/**` = 0（历史归档/ADB/任务书豁免）；
2. 新指令 `rf2rf` 在本组件面落地：`rf2rf` 可汇编/反汇编、编码与 `contracts/opcodes.yaml` 一致、`ft2ft`/`fo2fo` 报未知助记符；
3. 门控：`check-lit`、`check-patch-tree`（llvm 段）、`--source-state` llvm、`check-component-changelog` 全 rc=0；
4. **≥2 路可达 FAIL 注入**（`cp`+md5 还原）：① 把 `rf2rf` 的 `opx` 改一位 ⇒ 编码 lit 应红；② 删 `dst_rf0` 相关诊断 ⇒ 负例 lit 应红；
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束

- 只改 `components/llvm-project/**`、`tests/unit/llvm/**`、本任务书；
- 不改 `spec/`、`contracts/`（已由 `m13-spec-010` 定稿；如需改，停下写「待裁定」）；
- 禁 `install-host`/`check-modules`/`build-*`（组件重建除外，按需并在完成区申报耗时）；不 sync/reset 节点；
- 不提交 git；注入还原用 `cp`+md5。

## 完成区

**测试结果**：lit `MC/DADAO` **85/85**、`CodeGen/DADAO` **71/71**（合计 156/156）、`MC/DADAO-gen` **11/11**、`check_lit_gen` **62/62**；`validate_mc_vectors` 78 向量/0 错；`check_lit_bytes` 258 patterns OK；`check-instrinfo` rc=0（263 def ↔ 263 记录）；`check-component-changelog` rc=0；`check-asm-list-drift`/`check-legality-drift`/`check-scope`/`check-rule-refs`/`check-fp-contract`/`check-asm-prose`/`check-spec-codeblocks` rc=0。运行期证据脚本 `.work/evidence/<任务ID>/run.sh` rc=0（9 项检查），`--inject` 自检 2 路注入均可达 FAIL、`cp`+md5 还原后回绿。
**修改文件**：补丁 4 份（`DADAOInstrInfoFP.td`/`AsmParser/DADAOAsmParser.cpp`/`MCTargetDesc/DADAOMCInstPrinter.cpp`/`DADAOInstrInfo.cpp`）+ `components/llvm-project/changelog.md`；lit 10 个（`fp-encoding.s`、`fp-legality.s`、`set-ft-fo.s`、`m4-pseudo-set.s`、`m4-option-mts.s`、`multiple-to-single-orri.s`、`gen-fast.s`、`MC/DADAO-gen/gen-orri.s`、`CodeGen/DADAO/{fp-codegen.ll,fp-canonicalize.ll}`）；生成物 `tools/llvm/llvm-isa-backend-matrix.{tsv,md}`（`gen_isa_coverage.py` 重生成，按主会话裁定纳入本任务范围）；本任务书。`series` 99 行不变。
**验收结果**：
1. 编码：`rf2rf {rf10:rf12}, {rf14:rf16}` ⇒ `encoding: [0x40,0xf0,0xa3,0x83]`，与 `contracts/opcodes.yaml`（value `0x40F00000`/mask `0xFFFC0000`/ha `0x3C`）现场派生逐字节一致；`llvm-objdump -d` 反汇编回读同一文本。
2. 旧指令：`ft2ft {rf1}, {rf2}`、`fo2fo {rf1}, {rf2}` ⇒ rc=1 `error: unrecognized instruction mnemonic`。
3. 合法性：目的含 rf0（`{rf0:rf2}`）⇒ rc=1 `dst_rf0`；`{rf3:rf4},{rf2:rf3}` ⇒ `mreg_range_overlap`；`{rf0:rf63}` ⇒ `mreg_range_overflow`；源 `{rf0:rf2}` rc=0；位数不等 / 扁平写法 / 显式第三操作数 ⇒ rc=1。
4. 注入（`cp`+md5 还原、逐次重建）：① `opx` 单 bit `0x3C→0x1C` ⇒ `fp-encoding.s` 红（`OBJ: expected string not found`，实得 `40 70 a3 83`）；② 删 `isFPDstRfMnemonic` 的 `rf2rf` ⇒ `fp-legality.s` 红（ERR-DST 管线 rc 非零、FileCheck 得到空输入）。还原后各自回绿（md5 一致）。
5. 门控：`check-patch-tree` **llvm-project 段 0 问题**（99 补丁）、`--source-state` llvm `OK clean=True count=1`；`check-component-changelog` rc=0。**全量 `check-patch-tree` rc=1 仅因 qemu 段**（断言⑥/⑨，`m13-qemu-016` 在飞，非本改动）。
6. 覆盖率矩阵：重生成后 `gen_isa_coverage.py --check --llvm-mc <构建树>` **rc=0（PASS）**：真源 263、第①层 accept **263**/reject **0**、第②层 yes 202/no 61、证据行复核 447；矩阵差异 = `rf2rf_orri_rf` reject→accept（+ buildmi 证据）+ 真缺口 55→54 + 仅 post-ISel 1→2。
**新发现/坑**：① 注入要挑**空 opx 槽**：`0x3C→0x3D` 与 `rd2rf` 撞车 ⇒ TableGen `Decoding conflict` 直接构建红（拿不到 lit 红），改 `0x1C` 才落到编码 lit；② `check-isa-coverage` 默认读**安装根** `llvm-mc`（陈旧 ⇒ `rf2rf` 记 reject），须 `--llvm-mc <构建树>` 才反映新实现；③ `gen-fast.s` 的「每 shape 取首条」机械规则使 `rf2rf` 落在全量档而非快档（`orri-block` 首条为 `focls`），未手工挑。
**遗留问题**：① `check-isa-coverage` 默认读**安装根**（陈旧，仍把 `rf2rf` 记 reject，故 `make check-isa-coverage` 现为 rc=2）；**构建树实测 accept 263/reject 0 且矩阵 `--check` rc=0**；**安装根刷新归主会话在 llvm/qemu/gem5/chipyard 四组件合入后统一做**；② **跨模块待收敛（不属本任务、不修）**：`check-interface`（QEMU `trans_*` 264 vs 263）→ `m13-qemu-016`；`validate-vectors`（`tests/inst/07-floating-point/{ft2ft,fo2fo}_orri_rf.S` 2 条载体）→ `m13-testcases-047`；③ **合入前需主会话在组件源树刷新（重建/`install-host`）后复跑 L1**：现主控机 L1 的 `validate-vectors`（`.td` 已改、`tests/inst` 未改的暂态）与本任务在工作树共享源树有关，`check-patch-tree` 的 qemu 段断言（⑥/⑨）为 `m13-qemu-016` 在飞，两条均为在途暂态；④ `check-lit` 的 e2e 段未跑（需安装根 qemu/bootrom，且 qemu 侧尚无 `rf2rf`）；⑤ 未跑 `make check-lit` 本体（会读安装根），改用构建树 `llvm-lit` + 既有 `DADAO_LIT_ALLOW_TOOLS_OVERRIDE=1` 覆盖，MC+CodeGen 全绿。
**耗时申报**：组件构建 `ninja -j 32 llvm-mc llc llvm-objdump llvm-readobj` 77 s + 收尾 60 s；注入重建各约 15–20 s（共 3 次）；未 `install-host`。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-15）

改动逐行复查：4 份补丁（`.td` 增 1/删 2、AsmParser 6 处、MCInstPrinter 1 处、InstrInfo 2 处）+ 10 个 lit 文件；核对 `rf2rf` 在 `isFPBlockMnemonic`/`isFPMregMnemonic`/`isFPRFCopyMnemonic`/`isFPDstRfMnemonic`/`isMultiToSingleOrriMnemonic` 五处覆盖，以及 `copyPhysReg`、打印器的范围形态。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 注释「4 pure copies」与列表（3 条）不符 | ✅已修 | AsmParser 注释 4→3 | 重导出补丁；lit 156/156、门控 rc 全 0 |
| `fp-legality.s` 新增正例期望字节算错（写 0x40F42003，实为 0x40F04203） | ✅已修 | 改 OK 行 | 该 lit 由红转绿（85/85） |
| 助手名 `isFPConvertFFMnemonic` 与新语义不符（rf2rf 非 convert_ff） | ✅已修 | 改名 `isFPRFCopyMnemonic`（3 处引用 + 注释） | 重建 rc=0；lit 全绿 |
| `-multiple-to-single`/溢出/位数不等是否覆盖 `rf2rf` | ✅已修（并入既有 `isFPBlockMnemonic`/`isFPMregMnemonic`，未加新分支） | — | `m4-option-mts.s`、`multiple-to-single-orri.s`、`{rf0:rf63}`、位数不等实测 rc=1 |
| `copyPhysReg` 的 RF→RF 漏改 | ✅已修 | 改 `rf2rf_orri_rf` | `fp-codegen.ll` 的 `CHECK-DAG: rf2rf` 绿 |
| 快档 `gen-fast.s` 不含 `rf2rf` | ❌不修 | — | 生成器「每 shape 首条」规则（该 shape 首条为 `focls`）；全量档 `gen-orri.s` 覆盖且绿 |
| `check-isa-coverage` 矩阵漂移 | ✅已修（主会话扩范围授权） | 用生成器重生成 `tools/llvm/llvm-isa-backend-matrix.{tsv,md}` | `--check --llvm-mc <构建树>` rc=0（accept 263/reject 0） |

### 第 1 轮 reviewer 验收

- **重跑（本人执行）**：`llvm-mc -show-encoding`：`rf2rf {rf10:rf12}, {rf14:rf16}` rc=0 ⇒ `40 f0 a3 83`；独立按 `contracts/opcodes.yaml`（value `0x40F00000`、mask `0xFFFC0000`、rfhb[17:12]/rfhc[11:6]/immu6[5:0]）复算同值且 `word&mask==value`；`set.ft rf1, rf2`⇒`40 f0 10 81`、`set.fo rf2, rf7`⇒`40 f0 21 c1`（展开 count=1 整 64 位，与 SimRISC-03 §例一致）；`llvm-objdump -d` 回读 `rf2rf {rf10:rf12}, {rf14:rf16}`。
- **五条限制落点**：目的含 rf0 `{rf0:rf2}` rc=1 `dst_rf0`（AsmParser `isFPDstRfMnemonic` 后置硬 Error；Flat[1]=连续区间起点 ⇒ 含 rf0 iff 起点为 rf0，非静默）；重叠 rc=1 `mreg_range_overlap`（`isFPRFCopyMnemonic` 块）；越界 rc=1 `mreg_range_overflow`（`isFPMregMnemonic`）；immu6=0 语法不可表达（`{a:b}` end<start 硬错 + 计数 >63 挡截断为 0，与其余 8 条 mreg_zero 指令同口径，非本任务回归）；源 `{rf0:rf2}` rc=0 合法；计数不等/扁平/显式第三操作数各 rc=1；`ft2ft`/`fo2fo` rc=1 `unrecognized instruction mnemonic`。
- **copyPhysReg 等价性**：RF→RF 改 `rf2rf_orri_rf`，仍 `.addImm(1)` 单寄存器 64 位逐位复制（immu6=1 ∈ 1..63）；重叠/dst_rf0 检查仅在 AsmParser 解析路径，对程序化构造的 MCInst 与原 `fo2fo` 路径完全同构 ⇒ **无语义变化**；dst==src 恒等复制的理论 ILLI 改前改后等同，非本任务引入。
- **矩阵核对**：tsv 仅 `rf2rf_orri_rf` 一行 reject→accept（+证据列），md 仅 rf2rf 行迁徙 + 统计口径（accept 262→263、真缺口 55→54、仅 post-ISel 1→2），「无 reject 段」系生成器模板（`gen_isa_coverage.py:668`），无其它条目漂移；`gen_isa_coverage.py --check --llvm-mc <构建树>` rc=0（accept 263/reject 0）。
- **门控重跑 rc**：构建树 `llvm-lit`+`DADAO_LIT_ALLOW_TOOLS_OVERRIDE=1`：MC/DADAO 85/85、CodeGen/DADAO 71/71、DADAO-gen 11/11（合计 167/167）全 rc=0；`check_lit_gen` 62/62 rc=0；`check-patch-tree` llvm 段断言 0 行、99 补丁（rc=1 仅 qemu 在途段⑥⑨）；`--source-state` llvm `OK clean=True count=1`；`check-component-changelog`/`check-instrinfo`/`check-asm-list-drift`/`check-legality-drift`/`check-fp-contract`/`check-scope`/`check-rule-refs`/`check-asm-prose`/`check-spec-codeblocks`/`validate_mc_vectors`（78 向量 0 错）/`check_lit_bytes`（258）全 rc=0；`make check-isa-coverage` rc=2（陈旧安装根 ⇒ rf2rf 记 reject，与完成区声明一致，非本任务验收项）。
- **自设计注入 2 路（`cp`+md5 还原、逐次重建，未 install-host）**：① `.td` rf2rf `outs GPRF→GPRD`（先试 `GPR` 类不存在 ⇒ TableGen 构建红、弃）⇒ 探针 `invalid operand`、lit MC/DADAO 79/85 红 rc=1；还原 md5 `2cde27f7` 一致 ⇒ 重建后 156/156 回绿。② AsmParser 置死 rf2rf 重叠判定 ⇒ 重叠静默受理 rc=0、lit 84/85 红 rc=1；还原 md5 `5fa2e2e6` 一致（与任务树副本同值）⇒ 重建后 167/167 回绿。
- **越界与格式**：`git show 2da1032f --name-only` 白名单外 0 命中（`spec/`、`contracts/`、`tests/inst/` 0 改动；`series` 未动）；审查全程 `git status -uall` 干净、未提交；完成区 14 行、全任务书无运行期绝对路径；证据脚本 `run.sh` 重跑 rc=0（9 项）、`--inject` 自检 rc=0，其注入日志（实得 `40 70 a3 83`、ERR-DST 管线 exit 1）与完成区逐字一致。
- **判决：Accepted**（验收命令块在本人重跑下全过、硬约束无违反）。未决（不阻断，供 architect 收尾）：① `make check-isa-coverage` 在安装根刷新前保持 rc=2（完成区遗留①③，owner=主会话）；② 按遗留③合并后复跑 L1。
