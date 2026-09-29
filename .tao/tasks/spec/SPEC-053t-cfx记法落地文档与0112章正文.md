# SPEC-053t: cfx 记法落地——assembly-language.md 与 SimRISC-00/11/12 正文

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`ADR-0013 D8`（Accepted）、`SPEC-052t`（已重命名字段 + 重生成生成表）
**状态**：待开始

## 背景

`SPEC-052t` 已完成 cfx 字段重命名与生成表重生成（内嵌速查表 cfx 行现为 `cfxHA` / `cgHB, rcHC, rdHD`）。本任务落地 **D8.5 的文档部分**与第 11/12 章正文转换（含第 00 章的 cfx 字段引用）。

## 修改范围

### A. `docs/spec/assembly-language.md` §151–156（D8.5）

| 旧 | 新 |
|---|---|
| `cfxcode` 写作 `cfxN`（第 151、155、156 行） | `cfxha` 写作 **`cfxHA`** |
| `cfx2rd cfx63, cg8, rc1, rd8`（第 152 行，占位说明） | 补明**字段占位**为 `cfxHA, cgHB, rcHC, rdHD`；具体写法 `cfx63, cg8, rc1, rd8` 保留为具体示例 |
| §5 表格中 `oiii` 行的 `illi 0`/`fence 0`/`swym 0` 示例 | **保留**（具体示例） |

### B. `spec/SimRISC-00-指令系统设计.md`

第 200、235 行的 `cfxcode` → `cfxha`（字段名）；第 237–239 行的槽位描述（`cg 在 hb`、`rc 在 hc`、`rd 在 hd`）**保持**（槽位名，非字段名）。

### C. `spec/SimRISC-11-其它.md` 正文

| 位置 | 旧 | 新 |
|---|---|---|
| 31 | `swym    0` | `swym    immu18` |
| 54 | `illi    0` | `illi    immu18` |
| 84 | `trap    cfx_<cfxname>, immu18` | `trap    cfxHA, immu18` |
| 96 | `escape  cfx_<cfxname>, imms18` | `escape  cfxHA, [excp_cause_ip, imms18i]` |
| 108 | `cfx2rd    cfx_<cfxname>, cghb, rchc, rdhd` | `cfx2rd    cfxHA, cgHB, rcHC, rdHD` |
| 109 | `cfx2rc    cfx_<cfxname>, cghb, rchc, rdhd` | `cfx2rc    cfxHA, cgHB, rcHC, rdHD` |
| 128 | `cfx2rd  cfx_umon, 5, 3, rd2` | `cfx2rd  cfx_umon, cg5, rc3, rd2` |
| 129 | `cfx2rc  cfx_power, 8, 1, rd2` | `cfx2rc  cfx_power, cg8, rc1, rd2` |
| 44 | `nop ; 展开为 swym 0` | **保持**（`swym 0` 为具体用法） |

- 散文：行 73 `cfxcode` → `cfxha`；行 112/113/114/116/120 的 `cghb`/`rchc`（作寄存器组名时）→ `cgHB`/`rcHC`；`rdhd` → `rdHD`
- **行 70–71、87、99、112–116、120 的 `cfx_<cfxname>`（别名）与 `cfx_umon_…` 形式保持**（`cfx_<cfxname>` 是 D8.3 的合法别名）
- 行 34/35/41 的 `swym 0`/`swym N` 为**具体用法**，保持

### D. `spec/SimRISC-12-待定.md` 正文

| 位置 | 旧 | 新 |
|---|---|---|
| 37 | `fence   immu18` | **保持**（已与生成表一致）|
| 58–61 | `lr_nn.o   rdhc, rbhd` 等 4 条 | `lr_nn.o   rdHC, [rbHD]` 等 |
| 63–66 | `sc_nn.o   rdhb, rdhc, rbhd` 等 4 条 | `sc_nn.o   rdHB, rdHC, [rbHD]` 等 |
| 89 | `rela.si    rbha, imms18` | `rela.si    rbHA, imms18` |
| 111–112 | `cfxld    cfx_<cfxname>, rbhb, immu12` | `cfxld    cfxHA, [rbHB, immu12]`（cfxst 同）|

- 散文：`rdhc`/`rbhd`/`rdhb`/`rbha`/`rbhb` → 大写；行 115 的 `cfx_<cfxname>` 保持

### E. **不在范围**（须在完成区列明）

- `spec/DADAO-*.md`（SEE/HEE/ABI/SBI/HBI，**上游原始规范**，其 `cfxcode` 属外部概念）——不改
- `docs/m1-retrospective.md`（历史记录）——不改
- `docs/self-consistency.md`（SEE 概念）——不改

## 约束

- 不改**生成区**（`<!-- ASSEMBLY_LIST_START/END -->`）
- 语义零变化：数值/位宽/限制条文一字不动
- 具体寄存器/编号（`cfx63`、`rd2`、`rb0`）保持
- 命令缺失 → 停下报告，禁止自行安装

## 验收标准

1. A/B/C/D 四段转换正确；`fence`、`nop ; 展开为 swym 0`、`cfx_<cfxname>` 别名**未被误改**
2. 与生成表 cfx 行一致（C/D 段指令书写）
3. **不改生成区**（给出命中行号 > `ASSEMBLY_LIST_END` 的证据）
4. **语义零变化**（逐 hunk）
5. E 段范围外文件**零改动**（`git status` 证据）
6. 反例验证：注入一处回退（如 `cfxHA`→`cfxcode`、`lr_nn.o rdHC, rbhd`）→ 检查可检出；复原后无残留
7. `make check` EXIT=0

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
