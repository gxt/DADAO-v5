# LLVM-067m: M6 llvm 里程碑

**模块**：llvm
**项目里程碑**：M6
**状态**：待开始
**目标**：LLVM 支持 M6——整数**完整调用约定**（变参/聚合/`sret`/多返回/间接调用）+ 小欠账收口；**DADAO clang target + driver/sysroot**（仅 freestanding）；大帧四形态寻址 + `mem*` 内建 + `MaxStoresPerMem*=16`；**lld reloc 完善**（`REL12` + `ld/st` 符号偏移新类型 + `FK_Data_1/2/4` 静默 0 + `ABS48` 数据表示）；FP/RF codegen；`make build-mc`/`build-clang`/`check`/`check-patch-tree`/`check-lit` 绿；`ISS-110` 留后。
**关联任务**：`LLVM-062t`、`LLVM-063t`、`LLVM-064t`、`LLVM-065t`、`LLVM-066t`

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（含 clang `TargetInfo`/driver）、`lld/ELF/Arch/DADAO.cpp`、`clang/lib/Driver/**`、`series`/`changelog.md`；对应 lit L1/L2 向量与独立 oracle
- 不回归：`make build-mc`/`make check`/`make check-patch-tree`（断言⑥）/`make check-lit` EXIT=0；`check-source-state`（`.work/source/llvm-project` clean、HEAD=base+1）
- ADR 前置（`SPEC-122t` 的 ADR）均已 `Accepted` 后方进入实现
（核验通过后，主会话将 `**状态**` 置为 `里程碑`）

## 审阅记录

#### 第 1 轮 reviewer 验收
（审查者独立验证：关联任务状态、产出存在性、构建/门控重跑、`check-source-state`、判决）
