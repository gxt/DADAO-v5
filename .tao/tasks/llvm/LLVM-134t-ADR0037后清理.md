# LLVM-134t: ADR-0037 后清理（冗余 `ext.so` + ABS48 显示偏移）

**模块**：llvm
**项目里程碑**：M10
**依赖**：LLVM-133t（语义核对）、LLVM-132t（fixup 大端修正）
**状态**：待开始

## 执行环境
**执行环境**：本地（LLVM 增量重建由主会话执行）

## 接口规范

### 背景（实测）
1. `DADAOISelLowering.cpp` 两处在窄无符号比较后做 `SIGN_EXTEND_INREG`：
   - `LowerBR_CC`（≈2541–2547）：为 `br.n/np/p/nn` 规范化 {-1,0,1}；
   - `LowerCmpSelect`（≈2721–2726）：为 `cs.*`/`setcc` 同款。
   ADR-0037 后 `cmp.ut/uw/ub` 的 -1 **已是 64 位全 1** ⇒ 该扩展是恒等变换，只多发射一条 `ext.so`（注释仍是旧口径）。
2. `DADAOAsmBackend::getFixupKindInfo` 的 `DADAO_FK_ABS48` 仍 `{0, 16, 0}`；按 LLVM-132t 的大端规则（`offset = 32 − size`）应为 **16**。它只影响 `--show-encoding` 的位标记（整字节标记，不触发断言），不影响编码/链接。

### 输出
1. 删除上述两处 `SIGN_EXTEND_INREG`，同步过时注释；确认窄无符号分支/条件赋值语义不变（`cmp.u*` 已全 1）。
2. `DADAO_FK_ABS48` 的 `TargetOffset` `0 → 16`。
3. 补 lit：
   - i32/i16/i8 无符号比较 + `br.n`/`cs.n` 的汇编**不含** `ext.so`；
   - `set.zw/or.w/andn.w`（带符号）`--show-encoding` 的 A 标记落在正确位。
4. 不改 QEMU/spec/契约；不改 `applyFixup`。
5. **DWARF64 默认的 `cc1as`/`llvm-mc` 路径**（LLVM-130t 遗留）：目前 `clang -c x.s`（cc1as）与 `llvm-mc` 不继承 DADAO 的默认 DWARF64，也不报 `-gdwarf32`。需改共享 `clang/lib/Driver/ToolChains/Clang.cpp`（`-gdwarf64` 注入与 `-gdwarf32` 拒绝的 target 门控），与本次重建同批；完成区须单列共享文件理由。

### 约束
- 若删除 `ext.so` 暴露其它路径依赖（例如某处仍需窄位规范化），停下报告，不硬删。

## 验收标准
1. `llc -O2`：窄无符号比较用于分支/选择时无 `ext.so`（贴指令计数，修复前有、修复后 0）。
2. `llvm-mc --show-encoding` 的 ABS48 三指令标记与预期一致。
3. `make install-host` 后 L1 / L2 绿；新增 lit PASS。
4. 反例注入（恢复 `SIGN_EXTEND_INREG` 或 `0` 偏移）⇒ 断言红 ⇒ 还原 ⇒ 绿。
5. 完成区贴真实输出与退出码。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
