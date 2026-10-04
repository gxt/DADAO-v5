# LLVM-037t: compare / branch

**模块**：llvm
**项目里程碑**：M3
**依赖**：`LLVM-035t`、`LLVM-036t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`LLVM-035t`（算术/常数）、`LLVM-036t`（访存）；v5 指令定义。
- **输出**：条件比较 + 条件/无条件分支的 ISel 与基本块布局；导出的补丁。
- **约束**：
  - **指令事实（实测，`DADAOInstrInfo.td` + `contract-isa.md`）**：
    - 比较：`cmp.ui rdha, rdhb, imm12`（无符号立即数）、`cmp.si`（有符号立即数）；`cmp.uo`/`cmp.so rdhb, rdhc, rdhd`（64 位寄存器，orrr）。比较结果写 rd，零/符号扩展写满 64 位。
    - 双寄存器条件分支 rrii：`br.eq`/`br.ne rdha, rdhb, imms12`。
    - 单寄存器条件分支 riii（测 rd 对 0）：`br.n`/`br.nn`/`br.z`/`br.nz`/`br.p`/`br.np rdha, imms18`；另有 `br.z`/`br.nz` 的 `rb` 变体（`br_z_rb`/`br_nz_rb`）。
    - 无条件：`jump`（iiii 24 位 / rrii 12 位）；函数返回 `ret`（riii）。
    - 分支立即数为 **PC 相对、字偏移（`<<2`，无 +4 流水偏移）**（`contract-isa.md §5`；`MCTargetDesc/DADAOFixupKinds.h` 已定义 `PCRel_12/18/24`）。
  - **必须**：`icmp`（至少 `eq/ne/slt/sle/sgt/sge` 6 个有符号谓词；`ult/ule/ugt/uge` 若本任务不覆盖，在完成区明确列出并说明由无符号比较需求时再补）降低到 `cmp*` + `br.*`；无条件 `br` → `jump`；基本块落地/fall-through/跳转目标正确（可参照 0628 `DL-058a`：`BR_CC` 设 `Custom` + `LowerBR_CC` + `BRCOND` 或 `SETCC`+`BRCOND`；`DL-058b` 补无符号）。
  - **无标志位 / compare-branch 约束（C17，只写任务书、不立 ADR/issue）**：DADAO **无标志位**（CZSO 取消）→ `cmp.*` 结果（−1/0/1）落 **rd**、`br.*` 测 rd/rb；**rd 用虚拟寄存器**（(A)，不设固定 RDCC、不做融合）；`==`/`!=`（`br.eq/ne`）省 cmp；`p==NULL` 用 **`br.z/nz {rb}`**（1 条）；`p==q` 用 `cmp.uo-rb` + `br.z`（2 条，**暂不新增指令**）。**`cmp.*` 的 SDNode 不得标 `SDNPCommutative`**（0628 教训）。
  - **指针比较（C14/`ADR-0018（C14）` D2）**：指针比较用 `cmp.uo-rb`（结果→RD，供 `br.*`/`cs.*`）。
  - **范围**：整数条件控制流（if/else、循环）。**不含** `select`/`setcc` 的独立值语义（→M4，若顺手支持需在完成区声明）、间接跳转、`jump` 表。
  - 不回归 `LLVM-034t`~`LLVM-036t`（GPRD/GPRB/算术/访存 MIR）。
  - 补丁纪律、构建/日志/临时目录/防造假纪律同 `LLVM-033t`。
  - 参照 0628 `DL-058a`/`DL-058b`（只读溯源）。

## 验收标准

1. `ninja` 退出 0。
2. `llc -march=dadao -stop-after=finalize-isel` 真实 MIR：
   - 条件：`define i64 @abs(i64 %x){ %c=icmp slt i64 %x,0  br i1 %c, label %neg, label %pos ... }` → 含 `cmp*` + `br.*` + 基本块标签；
   - 循环：`sum(1..N)` 类 IR → 含回边 `jump`。
3. 覆盖谓词矩阵：给出 `eq/ne/slt/sle/sgt/sge`（+ 无符号如有）各自的 MIR 片段；未覆盖项须显式列出。
4. `llc -verify-machineinstrs -stop-after=finalize-isel` 退出 0。
5. 补丁导出且 `make check-patch-tree` 通过；`make check-lit` 不回归。
6. 一键证据脚本 `.work/evidence/LLVM-037t/run.sh`（规格同 `LLVM-033t`；反例注入：改一个谓词映射/分支目标 → 预期 FAIL）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
