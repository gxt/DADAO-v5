# LLVM-132t: ISS-232 fixup 元数据大端修正（--show-encoding）

**模块**：llvm
**项目里程碑**：M10
**依赖**：无（用户 2026-10-25 裁定方案 a）
**状态**：待开始

## 执行环境
**执行环境**：本地（LLVM 重建由主会话执行）

## 接口规范

### 背景（ISS-232，实测 2026-10-25）
- `llvm-mc --show-encoding` 对 `ld.o rb4, [rb4, %pcrel_lo(.Lhi0)]` **rc=134**（上游断言 `Encoder wrote into fixed up bit!`）；`rb1/2/3` rc=0，`rb4/8/16/32/63` 全 rc=134。
- 根因：`DADAOAsmBackend::getFixupKindInfo` 的 `TargetOffset=0, TargetSize=12` 按**小端位序**描述；DADAO 是**大端**，`--show-encoding` 实际标记到最高 12 位（`opcode + ra[5:2]`），`ra≥4` 时标记位非零 ⇒ 断言。
- 影响面：仅 `--show-encoding` 显示；`-filetype=obj`、链接、运行均正常。

### 输出
- `getFixupKindInfo` 的 `TargetOffset` 改为**大端字节流**位置：12 位 → **20**、18 位 → **14**、24 位 → **8**、32 位（整字）→ **0**；`TargetSize` 不变。
- **不改**：`applyFixup`（自定义位写入，不读 `TargetOffset`）、编码/链接行为、`spec/`、契约正文。
- 补一条 `--show-encoding`（`rb≥4`）用例（lit 或脚本），防回归。

### 约束
- 若发现门控/文档钉住该表（issue 提到 `check_mc` A7，现场未找到），**停下报告**，不擅自改契约。
- 共享文件（`MCAsmStreamer.cpp` 等）**不碰**（方案 a 只改目标侧）。

## 验收标准
1. `llvm-mc --show-encoding` 对 `rb4/8/16/32/63` 均 rc=0；`rb1` 仍 rc=0。
2. `-filetype=obj` 产物与修复前**逐字节一致**（md5 对账）。
3. 反例注入（`20` 改回 `0`）⇒ 复现 SIGABRT（rc=134）⇒ `cp` 还原 ⇒ 绿。
4. `make install-host` 后 L1 / L2 绿。
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
