# GEM5-027t: gem5 SE 动态链接（ET_DYN / PT_INTERP / ldso）

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

1. **loader**：接受 `ET_DYN`（PIE/共享对象）与 `PT_INTERP`；按 `contract-elf` 映射各段（`p_align=64 KiB`、大端、`p_vaddr==p_paddr` 约定）。
2. **auxv**：正确构造 `AT_PHDR`/`AT_PHENT`/`AT_PHNUM`/`AT_BASE`/`AT_ENTRY`/`AT_PAGESZ`/`AT_RANDOM`/`AT_NULL` 等；与 QEMU user 同 ELF 的 auxv 可见值一致。
3. **ldso 执行**：把 `ld-musl-dadao.so.1` 映射到 `AT_BASE` 并跳转；重定位（`RELATIVE`/`GLOB_DAT`/`JUMP_SLOT` 等按 musl ldso 实际需要）由 guest ldso 自行完成，SE 只负责装载与系统调用面。
4. **syscall 面**：dynamic 线新增的 syscall（如 `mmap` 文件映射/`mprotect` 真权限、`fstat`、`readlink`、`getrandom`、`rseq` 等）按现场补齐；`mprotect` 需从「仅校验」升级为真实页权限（否则只读段可写）。
5. 不改测试用例/期望；不改 QEMU。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{se_workload.*,process.*,...}`、`components/gem5/patches/configs/dadao/se.py`、`components/gem5/changelog.md`、`components/gem5/README.md`、本任务书、`milestones.md`。

**不在范围**：静态线已通过的语义、QEMU、测试用例与期望、`tests/parity/matrix-M11.md`（G3 统一重生成）。

## 验收标准

1. `libc-test` dynamic 全量在 gem5 SE 上跑通（与 QEMU user 同口径）；`llvm-ts` dynamic 同样；失败项给最小复现与归属。
2. `qemu_only_fail` 0；`gem5_only_fail` 逐条列名并归因，不得用 BLOCKED 掩盖。
3. `mprotect` 真实权限：写只读段/执行 `PROT_NONE` 段必须 fault（补抽测）。
4. `build-gem5`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、L1/L2 rc=0。
5. 反例：把 `PT_INTERP` 处理改回拒绝 ⇒ dynamic 用例回 blocked；`cp`+`md5sum -c` 还原重建回绿（禁 git 还原）。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 先做「`ET_DYN` + `PT_INTERP` + auxv」让 ldso 能跑，再补重定位相关 syscall；每步用单个 dynamic 小程序验证。
- `mprotect` 真权限可能影响既有静态用例（例如 `vmfill`），需回归 `GEM5-021t` 基线。
