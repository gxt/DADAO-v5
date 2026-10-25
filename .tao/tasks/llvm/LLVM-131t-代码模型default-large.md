# LLVM-131t: 代码模型 default / large（驱动 + 后端）

**模块**：llvm
**项目里程碑**：M10
**依赖**：ADR-0036（已 Accepted）、INFRA-106t（跨度门控，验收用）
**状态**：待开始

## 执行环境
**执行环境**：本地（LLVM 重建 `make install-host` 由主会话执行，属长任务）

## 接口规范

### 背景事实（实测，2026-10-25）
- 直接 `call` / `jump` = REL26（`imms24` 字偏移）⇒ **±32 MiB**；实测 64 MiB 布局 LLD 报
  `R_DADAO_REL26 out of range: 16515066 is not in [-8388608, 8388607]`，16 MiB 布局正常。
- `DADAOTargetMachine.cpp` 默认 `CodeModel::Small`，但后端**零处** `getCodeModel()`；驱动拒绝 `-mcmodel=large|medium`（`unsupported argument`）。
- 动态链接：PLT 12 B、紧贴 `.text`（实测 `.text@0x20240`、`.plt@0x20260`），跨 DSO 调用天然在 ±32 MiB。
- ADR-0036 决策：**两种模型**——`default`（代码 ≤32 MiB、数据任意 48 位）与 `large`（代码任意）；不提供 `medium`/`kernel`/`tiny`。

### 输入
- `components/llvm-project/patches/clang/lib/Driver/ToolChains/DADAO.cpp.patch`（`-mcmodel` 取值与拒绝）
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOTargetMachine.cpp.patch`（`CodeModel::Large` 生效）
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch` / `DADAOInstrInfo.cpp.patch`（large 的调用/跳转形态）

### 输出
1. **驱动口径**：接受 `-mcmodel=default`、`-mcmodel=large`；`small` = `default` 别名；`medium|kernel|tiny` ⇒ **明确报错**（rc≠0，文案含目标名与允许值）。
2. **`large` 形态**：超出 ±32 MiB 的 `call` / `jump` ⇒ `ABS48` 物化 48 位目标地址 + 间接 `call rb, rd, imm12` / `jump [rb, rd, imm]`；动态导入（走 PLT）保持直接调用；条件分支仍由 `BranchRelaxation` 处理，不引入链接器 thunk。
3. **测试**（lit / 脚本，落 `components/llvm-project/patches/llvm/test/CodeGen/DADAO/` 或既有测试目录）：
   - 远距布局（>32 MiB）在 `large` 下链接成功；
   - 同一布局在 `default` 下 LLD 报 REL26 越界（既有行为，作对照）；
   - 小镜像在 `large` 下功能正确（qemu 运行或等价回归）。

### 约束
- 不改 ISA、不改 `spec/`、不改 REL26 字段定义；
- `-mcmodel=large` 必须在后端**真实生效**后才允许被驱动接受（不得"接受但无行为"）；
- 共享文件（`Clang.cpp` / `CommonArgs.cpp`）如需改动，完成区单列理由。

## 验收标准
1. `-mcmodel=default|large|small` 接受；`medium|kernel|tiny` 报错且信息可读。
2. 远距布局：`large` 链接 rc=0；`default` 报 REL26 越界（对照）。
3. `large` 产物反汇编可见 ABS48 物化 + 间接 `call`；小镜像运行结果与 `default` 一致。
4. `make install-host` 后 L1 绿、L2 代表集绿。
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
