# SPEC-044t: SimRISC-04（64位数据运算）正文改为新汇编格式

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`ADR-0013`、`docs/spec/assembly-language.md` v1.1、`tools/llvm/gen_asm_list.py`、内嵌速查表（生成区）；前置 `SPEC-041t`/`042t`/`043t`
**状态**：待开始

## 修改范围（仅 `spec/SimRISC-04-64位数据运算.md`）

### A. 代码块

| 位置 | 旧 | 新（以生成表为准） |
|---|---|---|
| 61 | `add.uo  rdha, rdhb, rdhc, rdhd` | `add.uo  {rdHA, rdHB}, rdHC, rdHD` |
| 62 | `add.so  rdha, rdhb, rdhc, rdhd` | `add.so  {rdHA, rdHB}, rdHC, rdHD` |
| 63 | `sub.uo  rdha, rdhb, rdhc, rdhd` | `sub.uo  {rdHA, rdHB}, rdHC, rdHD` |
| 64 | `sub.so  rdha, rdhb, rdhc, rdhd` | `sub.so  {rdHA, rdHB}, rdHC, rdHD` |
| 77 | `add.si  rdha, imms18` | `add.si  rdHA, imms18` |
| 92 | `cmp.si  rdha, rdhb, imms12` | `cmp.si  rdHA, rdHB, imms12` |
| 93 | `cmp.ui  rdha, rdhb, immu12` | `cmp.ui  rdHA, rdHB, immu12` |
| 99 | `cmp.uo  rdhb, rdhc, rdhd` | `cmp.uo  rdHB, rdHC, rdHD` |
| 100 | `cmp.so  rdhb, rdhc, rdhd` | `cmp.so  rdHB, rdHC, rdHD` |
| 112 | `mul.so  rdha, rdhb, rdhc, rdhd` | `mul.so  {rdHA, rdHB}, rdHC, rdHD` |
| 113 | `mul.uo  rdha, rdhb, rdhc, rdhd` | `mul.uo  {rdHA, rdHB}, rdHC, rdHD` |
| 121 | `div.uo  rdhb, rdhc, rdhd` | `div.uo  rdHB, rdHC, rdHD` |
| 122 | `div.so  rdhb, rdhc, rdhd` | `div.so  rdHB, rdHC, rdHD` |
| 123 | `rem.uo  rdhb, rdhc, rdhd` | `rem.uo  rdHB, rdHC, rdHD` |
| 124 | `rem.so  rdhb, rdhc, rdhd` | `rem.so  rdHB, rdHC, rdHD` |
| 216–221 | `shl.uo/shr.uo/shr.so rdhb, rdhc, rdhd` / `..., immu6` | `... rdHB, rdHC, rdHD` / `... rdHB, rdHC, immu6`（`orri` **不是**组记法：`immu6`=移位量） |
| 223–226 | `ext.uo/ext.so rdhb, rdhc, rdhd` / `..., immu6` | `... rdHB, rdHC, rdHD` / `... rdHB, rdHC, immu6` |
| 228–231 | `and.o/or.o/xor.o/xnor.o rdhb, rdhc, rdhd` | `... rdHB, rdHC, rdHD` |

> **注意**：`add.uo`/`add.so`/`sub.uo`/`sub.so`/`mul.uo`/`mul.so` 是**双目的**（`rdha`、`rdhb` 均为 dst）→ `{rdHA, rdHB}, rdHC, rdHD`（无 `?`）。其余 `orrr` 三操作数**不加**花括号。

### B. 普通 Markdown 表格中的指令书写

| 位置 | 旧 | 新 |
|---|---|---|
| 144 | `and.o rdhb, rdhc, rdhd` | `and.o rdHB, rdHC, rdHD` |
| 159 | `xnor.o rdhb, rdhc, rd0` | `xnor.o rdHB, rdHC, rd0` |
| 169 | `sub.so rd0, rdhb, rd0, rdhc` | `sub.so {rd0, rdHB}, rd0, rdHC`（双目的）**逐条核对生成表** |
| 211 | `ext.uo rdhb, rdhc, rdhd` 或 `ext.uo rdhb, rdhc, immu6` | `ext.uo rdHB, rdHC, rdHD` / `ext.uo rdHB, rdHC, immu6` |

### C. 正文散文与伪代码中的字段名引用

`rdha`/`rdhb`/`rdhc`/`rdhd` → `rdHA`/`rdHB`/`rdHC`/`rdHD`（含行 51–52、67、103、109、116、127、140–151、182、199、207 等；**伪代码块**行 185–188、202–205 中的 `rdhb[N:0]`→`rdHB[N:0]`、`rdhc[N:0]`→`rdHC[N:0]` 同步）。

- 具体寄存器（`rd0`、`rd3`、`rd4`）**保持**。
- 行 173 `neg.o rd3, rd4` 为具体示例，**保持**（`neg.o` 为伪指令，调用写法不改）。

## 约束

- **只改 `spec/SimRISC-04-64位数据运算.md`**；不改生成器 / `contracts/` / `docs/`
- **不改生成区**（`<!-- ASSEMBLY_LIST_START/END -->`，本文件行 6–43）
- **语义零变化**：数值/位宽/公式/限制条文一字不动（只改记法与大小写）
- 逐条核对；命令缺失 → 停下报告，禁止自行安装

## 验收标准

1. A 段 17 条代码块行全部为新格式（双目的 `{…, …},`、`orri` 移位量不加花括号）
2. B 段 4 处表格指令书写转换正确（尤其行 169 的双目的形式）
3. C 段引用一致大写；具体寄存器未误改
4. **语义零变化**（逐 hunk；公式/数值逐字未动）
5. **不改生成区**（证据：命中行号 > 43）
6. 每条新形式与生成表「汇编形式」列**逐条相符**（独立复算；双目的/`orri` 分类正确）
7. 反例验证：注入一处回退（如双目的去掉 `{}`、或 `orri` 移位量误加组记法）→ 检查可检出；复原后无残留
8. `make check` EXIT=0

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
