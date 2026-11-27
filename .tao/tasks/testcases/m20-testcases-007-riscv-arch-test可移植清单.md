# m20-testcases-007: riscv-arch-test 可移植清单与覆盖对照（评估，不写向量）

**模块**：testcases
**项目里程碑**：M20
**依赖**：M17 四方基线（274）、`tests/arch` 39 条索引；无代码依赖
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：已验证

## 背景（用户 2026-11-27）

`riscv-arch-test` 不是 RISC-V 代码可直接复用——DADAO 编码、四寄存器组、cfx 寄存器与异常模型均不同。可移植的是**测试意图 + 边界值 + 期望判据**。用户要求先出一份「可移植候选 + 与现有覆盖对照」的分批清单，再决定立项。

## 要做（只做评估，不写测试向量）

1. 按扩展/测试族列出候选（至少覆盖）：整数 ALU/移位/比较/分支、乘除余、load/store（宽度/符号扩展/非对齐）、位操作（`clmul`/`ctlz`/`ctpop`/`cttz`/`rev`/`rol`）、`lr/sc`、浮点（`ft/fo`：NaN/次正规/舍入/异常标志/FMA/min-max）、privileged（异常/中断进入返回）；
2. 每条候选写清四项：
   - **移植的测试意图**（例：除零、最小负数/−1、商余关系；NaN 传播、舍入模式、标志位）；
   - **DADAO 对应能力**：`contracts/opcodes.yaml` 的 op + `spec/` 段落（必须引用真实存在的 op/段）；
   - **现有覆盖**：`tests/inst`（274 镜像，按册 01–12）与 `tests/arch`（39 条）里是否已有、大致到哪一层（无/单点/边界齐）；
   - **落点建议与参考条数（不设上限）**：进 `tests/inst`（四方签名槽 + 退出码）还是 `tests/arch`（Vast 探针），参考条数仅用于估算。
3. 明确**不可移植**清单及依据：C 压缩（定长 4 字节）、V 向量、Zicsr/Zifencei、Sv39/MMU/PMP、H 扩展、AMO 系列（DADAO 只有 `lr/sc`）、RVWMO 细节；
4. 输出「分批建议」：按收益排序（建议 FP 边界 → 乘除边界 → 位操作 → load/store → lr/sc），每批一句范围 + 预估；
5. 结果写进 `.tao/knowledge/m20-riscv-arch-test-porting.md`（≤60 行，只放结论与清单；过程日志落运行期目录），完成区给摘要与指针。

## 约束与求真

- **不得臆造上游测试名/条数**：无法核实的写到「测试族」粒度并注明「未核实」；需要联网核实上游清单时，说明取证方式与来源；
- 每条「DADAO 对应能力」必须能在 `contracts/opcodes.yaml`/`spec/` 中 grep 到，不得凭印象；
- 不写/不改任何测试向量、不改 spec/契约/任务书以外文件；独立 `git worktree`；不提交 git；完成区 ≤30 行。

## 验证

1. 清单覆盖率：A 类候选每族至少 1 条，且每条的 op/spec 引用可 grep 命中（脚本断言，输出计数）；
2. 现有覆盖对照：逐条给出「无/单点/边界齐」的判断依据（引用具体镜像册或 arch case id）；
3. 不可移植清单有 spec/opcode 依据；
4. 文档 ≤60 行；`make check-knowledge-refs` rc=0；`git status -uall` 仅新文档 + 任务书。

## 完成区

**结论摘要**：ACT 只可移植测试意图/边界值；A 族（指令）多数已「边界齐」，增量主要是独立签名与寄存器字段组合，不建议整族照搬；B 族（系统）仅 S3「lr 后异常/中断进入 ⇒ sc 必败」为明确缺口，S1/S2 只补跨切面。
**文档路径**：`.tao/knowledge/m20-riscv-arch-test-porting.md`（新增，54 行；含 10 个 A 族 + 3 个 S 族候选，每条有上游族/意图/op+spec/现有覆盖/参考条数）。
**分批建议**：① 指令批 A1–A10（按缺口逐条立项，不设总数上限，`tests/inst`）——007 完成后即可开始，不必等 006；只依赖 `tests/inst` 共享生成物，必须与 `m20-testcases-006`、`m20-infra-002`（若在改生成器）串行写；② 系统批 S1–S3（按缺口逐条立项，不设总数上限，`tests/arch`）——cfx W1–W3 + `m20-integ-002` 后、006 前；不重复 cfx/cg/rc 矩阵；时间顺序 = 007 → 指令批（可与 W1–W3 并行，避开 infra-002/006 共享写者）→ W1–W3 → integ-002 → 系统批 → 006；006 最后统一收口，两批先落地则只需一次重生成；两批各预估 4–8 h。
**测试结果**：运行期证据目录内 `run.sh` rc=0——文档 54 行（≤60）、`tests/inst` 274 `.S`/`tests/arch` 39 条现场计数、13 候选 op 全命中 `contracts/opcodes.yaml`、硬编码 33 个 spec 段 + 文档现场抽取 36 个 spec 引用全部按标题 grep 命中、`make check-knowledge-refs` rc=0；注入坏 op/坏 spec 均 rc=1，`cp`+md5 还原后 rc=0（md5 `62812d32…`）。
**验收结果**：`make check-knowledge-refs` PASS（0 悬空）；`git status -uall` 仅新文档 + 本任务书；未改测试向量/spec/契约/引擎/cfx 组件，未提交 git。
**新发现/坑**：ACT 的 `mulh`/`clmulh`/`clmulr`/`ror`/PMP/Sv39/Zicsr 无直接 DADAO 对应（`clmul` 高半用 `{rdH,rd0}`，`clmulr` 用 `rev` 组合）；`ft` 窄写高 32 保持、无 NaN-boxing；S3 的 GAP 已在 `12-misc/lr.*` 与 `00/atomic_rmw.S` 显式登记（ISS-440/443）。
**未核实项**：上游只核对 `rv64i/{I,M,F,D,Zalrsc,Zbb,Zbc,Zbs,Zba}` 的文件名/存在，未逐文件统计 ACT 用例数/签名槽数；`priv` 仅核对目录与少量文件名；参考条数仅为估算，不是上限，也不是上游条数。
**遗留问题**：① 新文档未登记 `.tao/knowledge/.manifests.toml`（任务限定只新增文档；主会话 `/complete` 补登记）；`make check-manifests-guard` 另报基线 2 项（`issues-m16.yaml`/`milestones-m16.md` 登记但磁盘缺失，非本任务）；② 待用户裁定两批是否立项、A1–A3/A10 是否降为 0–3 条、S3 是否等 ISS-440/443 裁决后再做。

## 审阅记录

### 第 1 轮 engineer 自审

审查范围：新文档全文、任务书完成区、运行期证据脚本（逐行）。核对方式：13 条候选的 op 逐个 `grep '^- id:'`、spec 段逐个按标题 grep、基线计数现场 `find`/`grep -c`；注入坏 op 后必须 FAIL。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 A6 误把 `Zbs-bset` 当可移植族，DADAO 无 bset/bclr/binv/bext | ✅已修 | 上游族改为 `Zbc-clmul`/`Zbb-clz`/`Zbb-cpop`/`Zbb-rol`；不可移植清单补 Zbs 一条 | 脚本 `check_absent` 四项 rc=0；A6 op 全命中 |
| F2 A10 的 `I-addi` 映射缺 `add.si` | ✅已修 | op 列表改为 `set.zw_rwii_rd`/`add.si_riii_rd`/`aip.si_riii_rb` | 脚本 op 检查 PASS；`add.si_riii_rd` 在 `opcodes.yaml` |
| F3 S1 写「嵌套未覆盖」超出证据 | ✅已修 | 改为「连续/嵌套进入未见专门用例」 | `grep -rn '嵌套\|nested' tests/{arch,inst}` 只有不相关命中 |
| F4 证据脚本行数用等号、工作树只过滤未计行数 | ✅已修 | 改 `-le 60`；状态改「过滤 + 计数 == 2」 | 两次重跑 normal/restored rc=0 |
| F5 任务书写具体运行期证据路径，触发 `check-knowledge-refs` | ✅已修 | 改为「运行期证据目录内 `run.sh`」 | `make check-knowledge-refs` rc=0（0 具体引用） |
| F6 文档增删后行数 52→53 | ✅已修 | 同步完成区行数与脚本断言 | 文档 53 行；`run.sh` PASS |

**判决**：范围内 finding 已全部修复，无未修项；证据为现场 rc，状态 `待验收`。

### 第 1 轮 reviewer 验收

**重跑记录**（均在仓库根、相对路径；证据 = 运行期证据目录内的 `run.sh`）：
1. 运行期证据目录内 `run.sh` ⇒ **rc=0**，`[SUMMARY] candidates=13 op_checks=33 spec_checks=33 fail=0`、`restored_rc=0`（reviewer 重跑 2 次，输出一致）。
2. 独立注入坏 op：文档 `clmul.o_rrrr_rd`→`clmul.o_bogus_xxx` ⇒ 同一脚本 **rc=1**（FAIL：`文档包含候选 op: A6/clmul.o_rrrr_rd`）；`cp` 备份还原 + md5 相等（`3dc7164d…`）⇒ 重跑 **rc=0**；全程未用 `git checkout`。
3. 独立注入坏 spec：文档 `SimRISC-04 §1.1`→`§9.9` ⇒ 同一脚本 **rc=0（未检出）** ⇒ 见 R2。
4. 现场计数：`tests/inst` `.S`=**274**、`tests/arch.yaml` `- id: arch-`=**39**、文档=**53 行**；29 个 op 逐个 `grep -qx "- id: …"` **全命中**；36 个 spec 段标题逐个按标题 grep **全命中**（A1 `SimRISC-04 §1.1` 已恢复）。
5. `make check-knowledge-refs` **rc=0**；`make check-manifests-guard` **rc=2** ⇒ 3 项 = 新文档未登记 `.tao/knowledge/.manifests.toml`（完成区已声明由 `/complete` 补登记）+ 基线 2 项（`issues-m16.yaml`/`milestones-m16.md`，非本任务）。
6. 覆盖抽查：`07-floating-point`=50、`03-wyde-imm`=8、`06/br.*`=10、`pseudo_set.*`=7、`12-misc lr/sc`=24、arch-ptw=14、arch-power=2、arch-umon-010/hart/pmem 均存在；不可移植依据 PMP/vector/amo/bset/fence.i 均 0 命中。

**约束核验**：`git status -uall` 仅新文档 + 本任务书（2 项）✓；未改测试向量/spec/契约/引擎 ✓；未提交 git ✓；分批顺序 = 007 → 指令批（007 后即可开始、与 006/infra-002 串行写，无「必须等 006」）→ cfx W1–W3 → integ-002 → 系统批 → 006 最后 ✓；待裁定三项（两批是否立项、A1–A3/A10 降 0–3 条、S3 等 ISS-440/443）记录清楚 ✓。

**发现**
- **R1（阻断）旧版残留**：文档行 45/46 仍写「46 条上限」「13 条上限」、行 51「新增上限」、列头「建议落点/条数」，实际 53 行，与完成区「54 行 / 不设总数上限 / 参考条数」矛盾。**根因披露（责任在 reviewer）**：reviewer 本轮 `cp` 备份还原（15:08:47）覆盖了 engineer 15:05–15:06 的第二轮文档修正（证据：运行期证据目录内 engineer 的 `last.log` 15:06:17 记 `实际=54` 且 rc=0；现文档 md5 与 reviewer 15:04:34 备份逐字节相同）——还原前未复查并发写者。请 engineer 重放第二轮文档修改（删上限、列改「参考条数（估算，不是上限）」、同步行数），并保证文档与完成区一致。
- **R2（阻断）证据脚本缺口**：坏 spec 引用写进文档后 `run.sh` rc=0；spec 断言取自脚本内硬编码清单、与文档未绑定（op 有「文档包含候选 op」绑定，spec 无对应），不满足验证 1「每条 op/spec 引用可 grep 命中（脚本断言）」。请在 `run.sh` 增加「文档内 spec 引用可 grep 命中」断言，复验：注入坏 spec → rc=1 → `cp`+md5 还原 → rc=0。

**判决**：**Needs Revision**（R1、R2）。

### 第 2 轮 engineer 返工

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1 文档旧版残留（53 行/上限/旧列头） | ✅已修 | 重放：删 46/13 上限，改「按缺口逐条立项，不设总数上限」；两处列头改「参考条数（估算，不是上限）」；加估算说明；未核实段改「参考条数仅为估算，不是上限」 | 文档 54 行（≤60）；旧词 grep 0；表头/分批/未核实段现场核对 |
| R2 spec 断言未绑定文档 | ✅已修 | 运行期证据目录内 `run.sh` 新增 `check_doc_specs`：Python 从文档现场抽取全部 `book §sec`（含 `/` 续引与 `2.1–2.5` 范围），逐条按标题 grep；`run_checks` 调用并计入 SUMMARY | 正常 rc=0（36 条）；注入 `SimRISC-04 §9.9` ⇒ rc=1；`cp`+md5 还原 ⇒ rc=0；坏 op 注入/还原仍 rc=1/0 |

**判决**：R1/R2 已修；`run.sh` 全流程 `ALL CHECKS PASS`，md5 `62812d32…` 注入前后一致；状态 `待验收`。

### 第 2 轮 reviewer 验收

**重跑记录**（仓库根、相对路径；证据 = 运行期证据目录内的 `run.sh`；注入前记 md5+mtime、还原前复查 mtime 未变）：
1. `run.sh` ⇒ **rc=0**，`[SUMMARY] candidates=13 op_checks=33 spec_checks=33 doc_spec_refs=36 fail=0`、`op_injected_rc=1`、`spec_injected_rc=1`、`restored_rc=0`、`ALL CHECKS PASS`，脚本内三处 md5 均 `62812d32…`。
2. **独立注入坏 spec**（文档 `SimRISC-04 §1.1`→`§9.9`）⇒ 同一脚本 **rc=1**，FAIL = `文档内每个 spec 引用可 grep … BAD SimRISC-04 §9.9（无该节标题）`；`cp` 还原后 md5=`62812d32…` 相等。
3. **独立注入坏 op**（`clmul.o_rrrr_rd`→`clmul.o_bogus_xxx`）⇒ 同一脚本 **rc=1**，FAIL = `文档包含候选 op: A6/clmul.o_rrrr_rd`；`cp` 还原 md5=`62812d32…`；全程未用 `git checkout`，未覆盖并发改动（还原前 mtime 复查一致）。
4. reviewer 独立抽取文档 spec 引用并按**严格**标题匹配（排除 §1 被 §1.1 顶替）：**36 条全部命中**、NOBOOK 0；29 个 op 逐个 `grep -qx "- id: …"` 全命中；现场计数 `tests/inst` `.S`=**274**、`tests/arch` `- id:`=**39**、文档=**54 行**。
5. `make check-knowledge-refs` **rc=0**；`git status -uall` **仅 2 项**（新文档 + 本任务书）；`make check-manifests-guard` rc=2 = 新文档未登记（完成区声明 `/complete` 补）+ 基线 2 项（issues-m16/milestones-m16，非本任务）；完成区 md5 声明 `62812d32…` 与现场一致。

**约束核验**：R1 ✓ —— 54 行；禁词「46/13 条上限、建议条数、建议落点/条数、新增上限」0 命中；两处表头 =「建议落点/参考条数（估算，不是上限）」；行 5「不作为上限或验收门槛」、分批段「不设总数上限」在；分批顺序 = 007 → 指令批（007 后即可开始、与 006/infra-002 串行写，无「必须等 006」）→ cfx W1–W3 → integ-002 → 系统批 → 006 最后 ✓；待裁定三项记录清楚 ✓。R2 ✓ —— `run.sh` 新增 `check_doc_specs` 从文档现场抽取 `book §sec`（含 `/` 续引、`2.1–2.5` 范围展开）逐条按标题 grep。范围 ✓ —— 仅新增文档 + 本任务书，未改测试向量/spec/契约/引擎，未提交 git。

**非阻断观察**：`check_doc_specs` 的标题匹配形如 `^#+ <sec>([ .]|$)`，会把 `### 1.1` 视作 `§1` 的命中（潜在假绿）；本轮 36 条经 reviewer 严格复核均真实存在对应标题，故不阻断，建议后续收紧为 `(?!\.?\d)`。

**判决**：**Accepted**（R1/R2 均已修复并经 reviewer 独立注入复验）。
