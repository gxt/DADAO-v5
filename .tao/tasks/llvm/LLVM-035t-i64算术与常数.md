# LLVM-035t: i64 算术 / 常数

**模块**：llvm
**项目里程碑**：M3
**依赖**：`LLVM-034t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`LLVM-034t` 的骨架 + 双 bank ISel；v5 指令定义（`.work/source/llvm-project/llvm/lib/Target/DADAO/DADAOInstrInfo.td`）。
- **输出**：i64 算术与立即数材料化的 ISel 选择（TableGen pattern 或 `ISelDAGToDAG`），含伪指令/多目的处理的展开；导出的补丁。
- **约束**：
  - **指令事实（实测，来自 `DADAOInstrInfo.td` + `contract-isa.md`）**：
    - rrrr 双目的（128 位）加减乘：`add.uo`/`add.so`/`sub.uo`/`sub.so`/`mul.uo`/`mul.so rdha, rdhb, rdhc, rdhd`；`rdhb` = 结果**低 64 位**、`rdha` = 高位/进位。**i64 运算取 `rdhb`，高位写 `rd0`**（`add.uo rd0, <dst>, <s1>, <s2>`）。两目的不得同时为 `rd0`（`contract-isa.md §6.1`）。
    - orrr 单目的 64 位：`and.o`/`or.o`/`xor.o`/`xnor.o`/`add.uo`/`sub.uo`（MISC-octa）`rdhb, rdhc, rdhd`；`cmp.uo`/`cmp.so`。
    - 立即数：`add.si rd, imm18`（riii，18 位有符号、原地加）；`cmp.ui`/`cmp.si rdha, rdhb, imm12`（rrii）。
    - 移位：`shl.u*/shr.u*/shr.s*`（orrr 变量移位 / orri 立即移位）。
    - 除余：`div.u*/div.s*/rem.u*/rem.s*`（orrr/orri；语义见 `contract-isa.md §6.2`，含除零规则）。
    - 常数材料化（**C12 已判**）：`set.ow`/`set.zw` **按正负选基调** + `or.w`/`andn.w` 修正其余 wyde（镜像 `set.rd` 策略）；`add.si` 仅用于**增减**（不用于立即数设置）；**不引 constant pool**（M3 无 `.rodata`）。指针常量（绝对地址）用 `set.zw-rb`/`or.w-rb` 材料化（`contract-isa.md §5.2`；C14/`ADR-0018（C14）`）。
    - **wyde 位置写法（C12，`ISS-128`）**：`set.zw`/`set.ow`/`or.w`/`andn.w` 的 wyde 位置**只能写作 `wp0`–`wp3`**；**裸数字 0–3 属非法、须报错**（现状为被静默接受，`ISS-128` 待修）。注：本任务书旧表述「`wpN` 会被静默忽略、须用数值 0/1/2/3」与 §5 判定**相反**，已按 §5 更正。
  - **v5 现状**：`DADAOInstrInfo.td` 无任何 pattern（`Pattern = []`），且**无伪指令**；本任务按需新增 `Pattern` 与（如需要）伪指令（如 `ADD_PSEUDO`/`SUB_PSEUDO`），并在 `expandPostRAPseudo`（`LLVM-040t` 或本任务）展开。
  - **范围**：i64 `add/sub/and/or/xor/shl/shr/mul`（`div/rem` 至少 `llvm_unreachable` 或 LibCall 兜底，完整语义可后置——**在完成区明确列出已覆盖/未覆盖**）；常数 i64 材料化。**不含** branch/compare-setcc（→`LLVM-037t`）、访存、调用、FP。
  - **不回归** GPRD/GPRB MIR（`LLVM-034t` 验收 1 的 `pass_ptr`/`add_i64`）。
  - 补丁纪律、构建/日志/临时目录/防造假纪律同 `LLVM-033t`；`make check-patch-tree`、`make check-source-state`。
  - 参照 **0628 `DL-060a`（shift/mul）/`DL-060b`（div/rem）/`DL-061a`（wyde imm）**（只读溯源）。

## 验收标准

1. `ninja` 退出 0。
2. `llc -march=dadao -stop-after=finalize-isel` 对下列（**真实 MIR，含目标指令**）：
   - `define i64 @f(i64 %a,i64 %b){ %r=add i64 %a,%b  ret i64 %r }` → 含 i64 add 选择（如 `ADD_PSEUDO`/`add.uo`），非 `COPY`+未实现；
   - 大常数：`define i64 @c(){ ret i64 123456789012345 }` → 材料化为 `set.zw`/`or.w` 序列（或 `add.si`）；给出 MIR。
3. `llc -stop-after=finalize-isel` 对以上程序退出 0、不 `Cannot select`。
4. 补丁导出且 `make check-patch-tree` 通过；`make check-lit` 不回归。
5. 一键证据脚本 `.work/evidence/LLVM-035t/run.sh`（规格同 `LLVM-033t`；反例注入：改一条 pattern/操作数使选择失败 → 预期 FAIL）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
