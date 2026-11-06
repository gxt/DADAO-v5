# GEM5-027t: gem5 SE 动态链接（装载器 + auxv + 配置）

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-026t`（线程/TLS；同改 gem5 补丁，须先合并）
**状态**：待开始

## 背景与事实

- gem5 SE 当前只接受 **静态 `ET_EXEC`**（`GEM5-014t`）；`configs/dadao/se.py --binary` 与 loader 均无 `ET_DYN`/`PT_INTERP` 路径
- `libc-test` / `llvm-ts` 的 **dynamic** 线在 QEMU user 上已全绿（libc 338 pass / llvm 214 pass），gem5 SE 尚无 dynamic 覆盖
- `ADR-0048 D4`：SE 最终覆盖完整 `tset`（静态先行，动态链接后补但不得降级）
- 参考：QEMU linux-user 的 `ET_DYN`/`PT_INTERP`/auxv/ldso 处理（只读参考，不复制代码）

## 目标

1. **loader**：放行 `ET_EXEC + PT_INTERP`（保留 `e_flags`/端序/段/入口校验）；复用 gem5 `ElfObject`/`Process::updateBias`/`interpImage`/`getStartPC`，不重写 loader。**主程序 PIE（`ET_DYN`）本轮不支持**（见「范围」）。
2. **auxv**：补 `AT_BASE`（=解释器装载基址）、`AT_FLAGS=0`、`AT_SECURE=0`、`AT_UID/EUID/GID/EGID=0`、`AT_EXECFN`；保留 `AT_PHDR/PHNUM/PHENT/ENTRY/PAGESZ/RANDOM/NULL`；与 QEMU 同 ELF 值一致。
3. **配置**：`configs/dadao/se.py` 增 `--interp-dir`（`m5.setInterpDir`，必须在 `Process()` 之前）与 `--redirect app=host`（`system.redirect_paths`，供 `/lib/ld-musl-dadao.so.1` 解析到 guest libc）。
4. **验收边界**：本轮只要求 ldso **能启动并越过 `_dlstart_c` 的 `AT_BASE` 分支**（PC 落解释器区间、无 fatal）；ldso 映射 DSO 的文件映射 `mmap` 归 `GEM5-028t`。
5. 不改测试用例/期望；不改 QEMU。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{process.*,...}`、`components/gem5/patches/configs/dadao/se.py`、`components/gem5/changelog.md`、`components/gem5/README.md`、本任务书、`milestones.md`。

**不在范围**：文件映射 `mmap`/ldso 映射 DSO（`GEM5-028t`）、`mprotect` 真权限（保持已登记限制，另立任务再评估）、主程序 `-pie`/`ET_DYN`（本轮不支持，登记 backlog）、QEMU、测试用例与期望、矩阵。

## 验收标准

1. 动态 `ET_EXEC + PT_INTERP` 小程序在 gem5 SE 上能进入 ldso（PC 在解释器区间、越过 `AT_BASE` 分支），并打印 ldso 首条诊断。
2. auxv 探针逐项等于 QEMU 同 ELF：`AT_BASE/AT_PHDR/AT_ENTRY/AT_PAGESZ` 一致，`AT_SECURE/UID/EUID/GID/EGID` 显式为 0，`AT_EXECFN` 正确。
3. 反例：`AT_BASE` 注 0 ⇒ ldso 走 static-PIE 分支失败（可达 FAIL）；`cp`+`md5sum -c` 还原重建回绿。
4. `build-gem5`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、L1/L2 rc=0。
5. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 事实依据（调研）：gem5 上游已有 `ET_DYN`/解释器装载/偏置/`getStartPC()`；DADAO 侧只需放行 `PT_INTERP` 并补 auxv/配置，不重写 loader。
- 解释器占位无 VMA（`updateBias` 只写页）⇒ `brk` 上限与 `MAP_FIXED` 需在 `GEM5-028t` 里一并约束，避免堆/固定映射撞解释器。
- `interp_dir` 时序：`ElfObject` 在 `Process` 构造时解析 `PT_INTERP`，`m5.setInterpDir` 必须先调用。
