# LLVM-036t: 标量 load/store

**模块**：llvm
**项目里程碑**：M3
**依赖**：`LLVM-034t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`LLVM-034t`（GPRB 地址 bank + 跨 bank 搬运）；v5 指令定义。
- **输出**：标量 load/store 的 ISel pattern（GPRB base + 12 位偏移），覆盖各访存宽度；导出的补丁。
- **约束**：
  - **指令事实（实测，`DADAOInstrInfo.td`）**：
    - 装载 rrii：`ld.o rd, [rb, imm12]`（64 位）、`ld.ut`/`ld.st`（tetra 零/符号扩展）、`ld.uw`/`ld.sw`（wyde）、`ld.ub`/`ld.sb`（byte）——`(outs GPRD:$ra) (ins GPRB:$rb, imms12:$imm12)`。
    - 存储 rrii：`st.o/st.t/st.w/st.b rd, [rb, imm12]`——`(ins GPRD:$ra, GPRB:$rb, imms12:$imm12)`。
    - 地址 = `rb[47:0] + sign_extend(imm12)`（`contract-isa.md §4`；RB 全 64 位、访存取低 48 位，C14/`ADR-0018（C14）` D3）；负偏移/大偏移需 base 先算（GPRB 算术，`add.o`（orrr，rb 目的；旧名 `add.so-rb`，见 `adr-0012 D9`）/`add.si`，C14/`ADR-0018（C14）` D1）。
    - **大端窄访存（C13，`ADR-0018（C13）` D2）**：byte/wyde/tetra 装载按大端语义；`ld.ub/uw/ut` 零扩展、`ld.sb/sw/st` 符号扩展，结果写满 64 位（`SPEC-069t` 值语义）。**须显式保证/测试** `ReduceLoadWidth` 类 combine 的**字节偏移**（大端下窄 load 的字节偏移与掩码，0628 `DL-068a` silent miscompile 教训）。
  - **必须**：给对应 format class（`DADAORrii` 的 load/store 子类）加 `mayLoad`/`mayStore`（`DADAOInstrInfo.td` 现**无** `mayLoad`/`mayStore`——实测 grep 计数 0）；新增 `Pattern`：`(load (addr))`→`ld.*`、`(store val, addr)`→`st.*`；地址匹配支持 `base + simm12` 偏移。
  - **范围**：标量 i8/i16/i32/i64 及 `ptr` 的 load/store。**不含** FrameIndex 栈槽（→`LLVM-038t`）、全局符号地址（→M4）。本任务用「参数指针 + 常量偏移」验证。
  - 不回归 GPRD/GPRB/算术 MIR（`LLVM-034t`/`LLVM-035t`）。
  - 补丁纪律、构建/日志/临时目录/防造假纪律同 `LLVM-033t`。
  - 参照 0628 `DL-051a`（zero-offset load/store pattern + `copyPhysReg`）/`DL-052a`（带偏移）；`DL-068a`（大端窄装载掩码）——只读溯源。

## 验收标准

1. `ninja` 退出 0。
2. `llc -march=dadao -stop-after=finalize-isel` 真实 MIR：
   - `define i64 @ld(ptr %p){ %v=load i64, ptr %p  ret i64 %v }` → 含 `ld.o` MI + GPRB 地址；
   - `define void @st(ptr %p, i64 %v){ store i64 %v, ptr %p  ret void }` → 含 `st.o` MI + GPRB 地址；
   - 带偏移（`getelementptr i64, ptr %p, i64 2`）→ `ld.o ..., 16`（非零 imm12）；
   - 窄宽度（`load i8`/`i32`）→ 对应 `ld.ub`/`ld.ut`/`ld.st` 等 + 正确扩展；**大端窄访存须给出字节偏移/掩码的显式核对**（C13/`ADR-0018（C13）` D2，0628 `DL-068a` 教训）。
3. `llc -verify-machineinstrs -stop-after=finalize-isel` 退出 0。
4. 补丁导出且 `make check-patch-tree` 通过；`make check-lit` 不回归。
5. 一键证据脚本 `.work/evidence/LLVM-036t/run.sh`（规格同 `LLVM-033t`；反例注入：改 imm12 或 pattern → 预期 FAIL）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
