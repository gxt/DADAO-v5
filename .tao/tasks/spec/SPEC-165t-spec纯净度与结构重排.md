# SPEC-165t: spec 纯净度与结构重排（去 v5 痕迹 / 附录归位 / 正文重编号 / `MISC-`→`OPC-`）

**模块**：spec
**项目里程碑**：M9（收尾前，优先于其它动 spec 的册）
**依赖**：`SPEC-160t`（min/max 翻转，已收）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源（用户裁定，2026-10-22）

1. **纯净化**：用户原话「我在查看 SimRISC 的 12 个册子的时候，发现你把很多不属于规范文档的内容塞到了文档中，包括 `scope:fp` 以及 `contract-fp.md` 等；这个事情很严重，我建议先处理一下」⇒ 方案 **A（彻底）**。
2. **结构**：「`附录：版本与变更记录` 集中在 `SimRISC-00` 中，其它分册不再逐一单独记录；汇编指令速查 和 合法性检查 放到每个分册的最后，作为附录出现；汇编指令速查 下面的子标题就一个，没必要」；正文重编号选「重编号（彻底）」。
3. **改名**：「前缀用 `OPC-`；`-AMO` 改为 `-MISC`；其它都不做改动」⇒ 只改 6 个表名，不动编码、不新增 `OPC-AMO`/`OPC-LRSC`、不改 `ALU/FPU/IMM/ARITH` 之类。

## 现场盘点（2026-10-22 实测，执行前须复核）

### 污染面
| 类别 | 命中 | 主要分布 |
|---|---|---|
| `scope:` 标记 | 30 | `07` 17、`00` 5、`12` 3、`01` 2、`11` 2、`03` 1 |
| ADR 指针 | 27 | `00` 7、`04/08/09/10` 各 4、`11` 3、`06` 1 |
| 任务号 | 36 | `00` 10、`07` 7、`08/09/10` 各 5、`04` 4 |
| `contract-*.md` 引用 | 2 | `00` |
| 生成区（`ASSEMBLY_LIST_*`） | 13 册各 1 | 含 `### 1.1 <分类>（N 条）｜ scope: …` 子标题与分类列 |
| `附录：版本与变更记录` | 13 册各 1 | 版本重叠、条目不同 |

**溯源**：`git log -S 'scope: fp' -- spec/` 首条 = `SPEC-086t`（M2 期），之后 `SPEC-087t`/`089t`/`16x` 叠加；`.tao/archive/SimRISC-0.5.3/` 原文零命中。

### 改名面（live 树实测 **417 处**）
`MISC-octa` 223 / `MISC-byte` 120 / `MISC-tetra` 87 / `MISC-wyde` 94 / `MISC-RF` 155 / `MISC-AMO`（含在上述总数内）。分布：`contract-isa.md` 168、`contracts/opcodes.yaml` 46、`spec/SimRISC-00` 24、lit 生成物 46、qemu 补丁注释 32、`tools/**` 30+、`spec/SimRISC-04/09/10` 等。
**归档 `.tao/archive/**` 不改**（历史记录保真）。

## 目标

### 1. 纯净化（方案 A）
`spec/SimRISC-00…12` 只允许：指令定义、编码、格式、语义、异常、revision。
**禁止**：`scope`、里程碑（`M1`/`M9`）、任务号（`SPEC-/QEMU-/LLVM-/INFRA-/TESTCASES-`）、`ADR-`、`ISS-`、`contract-*`、`.tao/`、分桶计数（“`scope: fp` 共 64 条”之类）。

**迁出去向（不新建容器）**：
- `scope` + 分桶计数 → `contracts/opcodes.yaml`（已有）+ `contract-isa.md`「范围表」
- ADR / 契约指针 → `contract-isa.md` 对应行
- 落地记录/任务号 → 各任务书 + `milestones.md`

### 2. 结构归位（固定顺序）
```
# <标题>
> 版本 / 分类（不含 scope）
## 1. …（正文，指令定义/编码/语义）
…
## 附录 A：汇编指令速查      ← 单标题，一张表；无 ### 子标题、无分类列
## 附录 B：合法性检查
## 附录：版本与变更记录      ← 仅 SimRISC-00，且必须是最后一个 ##
```

### 3. 正文重编号
原 `§3…§N` → `§1…§(N−2)`；同步改 `contracts/opcodes.yaml` 的 `spec_cite`（264 条）、`tests/**`（约 162 处）、`.tao/contracts/*.md`、`docs/**`、`contract-isa.md`。
一并处理 `ISS-315`/`ISS-316`/`ISS-192`/`ISS-219`（迁册旧引用 `SimRISC-12 §3.x` → `SimRISC-11 §6.x`）。

### 4. 表名改名（用户 2026-10-22：只此 6 项）
`MISC-octa → OPC-octa`、`MISC-tetra → OPC-tetra`、`MISC-wyde → OPC-wyde`、`MISC-byte → OPC-byte`、`MISC-RF → OPC-RF`、**`MISC-AMO → OPC-MISC`**。
- 依据：`SimRISC-00:201` 已定义 `op` 简称 **opc**（8 位头），这些表正是**按 op 划分**的表族；`AMO` 名不符实（`0x77` 装的是 `fence`/`swym`/`lr`/`sc`，无一条读改写原子操作）。
- **不动编码**：不新增 op、不迁移 `lr/sc`、不拆分 `AMO`/`LRSC`（全留 M10）。
- 范围：live 树全部（含注释、生成物、门控常量）；`.tao/archive/**` 不改。

### 5. 工具与门控同步
- `tools/llvm/gen_asm_list.py`：输出改册尾、去子标题与分类列；
- `tools/spec/gen_legality_list.py`：落附录 B；
- `tools/spec/check_numbering.py`：`## 附录 A：`/`## 附录 B：` 与 `## 附录：版本与变更记录` 一并视为**无编号尾段**；断言正文 §1 起连续、附录 A→B 顺序、changelog（仅 00）是最后一个 `##`；
- `tools/spec/check_spec_changelog.py`：扫描面收窄到 `SimRISC-00`；「互锁组一致」改为比 **13 册册头版本**；
- `check_asm_list_consistency.py` / `check_asm_prose.py` / `check_tables.py` / `check_spec_codeblocks.py`：文本格式同步；
- **新增** `tools/spec/check_spec_purity.py`（L1）：禁用词表 ⇒ FAIL；`--self-test` ≥3 类注入（`scope:` / 任务号 / `ADR-` / `MISC-`）；
- **新增** `tools/spec/check_spec_cite_targets.py`（L1）：`spec_cite` 的「书 + 节标题」必须真实存在（覆盖 `contracts/*.yaml` + `tests/**/*.yaml`）。

## 接口规范

- **输入**：`spec/SimRISC-00…12`、`tools/llvm/gen_asm_list.py`、`tools/spec/**`、`contracts/**`、`tests/**`、`.tao/contracts/**`、`docs/**`、`components/qemu/patches/**`（仅注释）。
- **输出**：纯净化 + 归位 + 重编号 + 改名的 13 册；同步后的引用；2 个新门控；同步后的旧门控。
- **约束**：不改任何**指令语义/编码**；不改 `opcodes.yaml` 记录字段（除 `spec_cite` 节号与注释里的表名）；不 commit/push。

## 验收

1. **纯净度**：`grep -nE 'scope:|ADR-[0-9]|ISS-[0-9]|(SPEC|QEMU|LLVM|INFRA|TESTCASES)-[0-9]+|contract-[a-z]+\.md|\.tao/|MISC-' spec/SimRISC-*.md` ⇒ **0 命中**；`check_spec_purity` rc=0。
2. **改名**：live 树 `grep -rn 'MISC-'`（排除 `.tao/archive/**`、`.work/**`、`.cache/**`）⇒ **0 命中**；6 个新名各命中数与旧名总数（417）一致（现场统计，不写死）。
3. **结构**：每册以 `## 附录 A：汇编指令速查`、`## 附录 B：合法性检查` 结尾（顺序固定）；速查下无 `###`；`## 附录：版本与变更记录` 仅 `SimRISC-00`。
4. **重编号**：每册正文 `## 1.` 起连续；`check_numbering` rc=0。
5. **引用完整性**：`check_spec_cite_targets` rc=0；`validate-vectors`、`check_contracts_dir`、`check-spec-refs` rc=0。
6. **语义零漂移**：`git diff` 中指令表行/语义段落逐行相同（仅位置/编号/表名变化）；`check_tables`、`check_asm_list_consistency`、`check-legality-*`、`check_scope`、`check_fp_contract` 全绿。
7. **可达 FAIL ≥4**：① 塞 `scope: fp` ⇒ purity 红；② 塞 `MISC-octa` ⇒ purity 红；③ 附录 A 挪回册首 ⇒ numbering 红；④ 改一条 `spec_cite` 节号 ⇒ cite_targets 红。
8. 收尾：`make check`(L1) + `make check-modules`(L2) 绿；`ISS-315/316/192/219` 按实际结果关闭。

## 风险与纪律

- **体量**：13 册 + 417 处改名 + 约 400 处引用重编号 ⇒ 先建**映射表**（旧节号→新节号、旧表名→新表名）落 `.work/`，再机械替换，禁手改。
- **串行**：本册期间禁止其它册改 `spec/**`（FMA 链等全部后置）。
- **逐册自检**：单册失败不污染其它册。
- `spec/` 改动已获用户 2026-10-22 授权（原话见「立项来源」）。

## 完成区
（执行后填写，≤30 行）

## 审阅记录
