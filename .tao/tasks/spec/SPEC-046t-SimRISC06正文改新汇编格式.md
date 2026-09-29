# SPEC-046t: SimRISC-06（控制流）正文改为新汇编格式

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`ADR-0013`（尤其 D2 `?`、D3 `i`、D4 `[...]`）、`assembly-language.md` v1.1、`tools/llvm/gen_asm_list.py`、内嵌速查表；前置 `SPEC-041t`…`045t`
**状态**：待开始

## 修改范围（仅 `spec/SimRISC-06-控制流.md`）

### A. 代码块

| 位置 | 旧 | 新（以生成表为准） |
|---|---|---|
| 42 | `br.eq    rdha, rdhb, imms12` | `br.eq    {rdHA, rdHB}?, [rb0, imms12i]` |
| 43 | `br.ne    rdha, rdhb, imms12` | `br.ne    {rdHA, rdHB}?, [rb0, imms12i]` |
| 53 | `br.n     rdha, imms18` | `br.n     {rdHA}?, [rb0, imms18i]` |
| 54 | `br.nn    rdha, imms18` | `br.nn    {rdHA}?, [rb0, imms18i]` |
| 55 | `br.z     rdha, imms18` | `br.z     {rdHA}?, [rb0, imms18i]` |
| 56 | `br.nz    rdha, imms18` | `br.nz    {rdHA}?, [rb0, imms18i]` |
| 57 | `br.p     rdha, imms18` | `br.p     {rdHA}?, [rb0, imms18i]` |
| 58 | `br.np    rdha, imms18` | `br.np    {rdHA}?, [rb0, imms18i]` |
| 68 | `br.z     rbha, imms18` | `br.z     {rbHA}?, [rb0, imms18i]` |
| 69 | `br.nz    rbha, imms18` | `br.nz    {rbHA}?, [rb0, imms18i]` |
| 81 | `jump    imms24` | `jump    [rb0, imms24i]` |
| 89 | `jump    rbha, rdhb, imms12` | `jump    [rbHA, rdHB, imms12i]` |
| 104 | `call    imms24` | `call    [rb0, imms24i]` |
| 112 | `call    rbha, rdhb, imms12` | `call    [rbHA, rdHB, imms12i]` |
| 131 | `ret     rdha, imms18` | `ret     rdHA, imms18` |

> **要点**：
> - `br.eq`/`br.ne` = **双**寄存器条件组 `{rdHA, rdHB}?`；其余 `br.*` = **单**寄存器条件组 `{rdHA}?`/`{rbHA}?`（`?` 紧跟 `}`）。
> - 跳转/分支目标一律 `[rb0, <imm>i]`（基址恒 `rb0`，立即数**加 `i` 后缀** = 指令字单位）。
> - `jump`/`call` 绝对地址 `rrii` 形式 → `[rbHA, rdHB, imms12i]`（立即数在括号内且加 `i`）。
> - `ret` **不是**跳转：`ret rdHA, imms18`（`rdHA` 为普通目的寄存器，`imms18` **无 `i`**）。

### B. 行 139 `return` 伪指令展开注释

`return                  ; 展开为 ret rd0, 0` —— `ret rd0, 0` 为**具体寄存器**示例，**保持**（`return` 为伪指令，调用写法不改）。

### C. 正文散文引用

- 行 63 `rdha`→`rdHA`（`rd0` 保持）
- 行 65 `rbha`→`rbHA`
- 行 95 / 118 中 `rdhb`→`rdHB`
- 行 93 / 116 中的裸后缀 `ha`/`hb` **保持**（非完整寄存器字段名，最小改动）

## 约束

- **只改 `spec/SimRISC-06-控制流.md`**；不改生成器 / `contracts/` / `docs/`
- **不改生成区**（`<!-- ASSEMBLY_LIST_START/END -->`，本文件行 6–29）
- **语义零变化**：数值（`<<2`、`48`、`16`、`63:48`、`7.4%`、P226 等）、公式、限制条文一字不动
- 逐条核对；命令缺失 → 停下报告，禁止自行安装

## 验收标准

1. A 段 15 条代码块行为新格式：
   - 条件组个数正确（`br.eq/ne` 双、其余单）
   - 跳转/分支目标带 `[...]` 且立即数带 `i`；`ret` 为普通形式（**无 `i`、无 `[]`**）
2. B 段 `ret rd0, 0` 未被误改
3. C 段引用大写正确；裸 `ha`/`hb` 未被误改
4. **语义零变化**（逐 hunk）
5. **不改生成区**（命中行号 > 29）
6. 15 条与生成表「汇编形式」列**逐条相符**（独立复算）
7. 反例验证：注入一处回退（如 `br.eq` 写成单条件组、`jump` 漏 `i` 后缀、`ret` 误加 `[]`）→ 检查可检出；复原后无残留
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
