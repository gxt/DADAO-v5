# INFRA-108t: PIC libc 归档与 `-static-pie` 支持（ISS-303）

**模块**：infra
**项目里程碑**：M10
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地（需 `build-musl-shared` / 安装集；无 LLVM 重建）

## 接口规范

### 背景（ISS-303，实测 2026-10-20）
- `clang -static-pie` 用**非 PIC** 的 `libc.a` ⇒ lld 逐条拒绝 `R_DADAO_ABS48`（`recompile with -fPIC`），仓库**未提供 PIC 版 `libc.a`**。
- `build-musl-shared` 已产 `.lo`（PIC 档）但**未归档、未入安装集**。

### 输出（提议方案；实施前与用户确认口径）
1. 由 musl 的 PIC `.lo` 归档出 PIC 版 libc 归档（命名/落点按安装约定），**入安装集**；
2. 驱动在 `-static-pie`（以及 `-pie` + 静态 libc）时**自动选** PIC 归档；普通 `-static` 仍用现有 `libc.a`；
3. `components/musl/README.md`（或安装说明）写明用法与边界；
4. 不改变默认静态链接（非 PIE）的产物。

### 约束
- 不改 musl 上游源码；不改 LLVM target 行为；
- 归档内容与 `.lo` 一致（md5/成员清单可核）；
- 若发现驱动无法可靠区分「静态 PIE」与「动态 PIE」（需要额外标志），停下报告口径选项。

## 验收标准
1. `clang -static-pie` 链接 rc=0，并在 `qemu-dadao` 运行得到预期退出码（贴命令/输出）。
2. 普通 `-static` 产物与改动前**逐字节一致**（md5）。
3. 反例注入（去掉 PIC 归档选择）⇒ `-static-pie` 复现链接失败 ⇒ `cp` 还原 ⇒ 绿。
4. L1 / L2 绿。
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
