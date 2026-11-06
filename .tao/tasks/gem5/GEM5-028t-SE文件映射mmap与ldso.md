# GEM5-028t: gem5 SE 文件映射 mmap 与 ldso 装载

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-027t`（装载器 + auxv + 配置；同改 gem5 补丁，须先合并）、`GEM5-023t`（文件 I/O 提供 `FileFDEntry`）
**状态**：待开始

## 背景与事实（只读调研，2026-11-06）

- gem5 SE 的 `doMmap()` 只支持匿名映射；非匿名分支直接返回 `-ENODEV`（`se_workload.cc` 现状），而 **musl ldso 通过 `mmap(fd, offset)` 映射 `libc.so`/DSO 的每个 `PT_LOAD`** ⇒ 这是动态线硬阻塞
- gem5 `MemState::mapRegion()` 已有文件映射能力（`src/sim/vma.cc`：宿主 `mmap` 成 buffer，`fixupFault` 懒填页）；`FileFDEntry` 可提供宿主 fd/文件名
- 解释器占位只写页、不注册 VMA（`Process::updateBias`）⇒ `brk` 上限若仍取 `MmapWindowEnd`，堆极大时会撞解释器；`MAP_FIXED` 探测也可能覆盖解释器区间
- 64 KiB 页：ldso 的 `mmap` 段需满足 `(p_vaddr − p_offset) % 65536 == 0`；当前工具链产物满足（lld `defaultMaxPageSize=0x10000`），但必须在任务里逐段断言

## 目标

1. **文件映射 `mmap`**：非匿名分支改为查 `FileFDEntry` → `memState->mapRegion(start, length, name, sim_fd, offset)`；按 Linux 语义校验 `offset` 页对齐、`offset+length <= file_size`、`PROT/MAP_SHARED|PRIVATE`；`close(fd)` 后映射仍有效（持有引用）。
2. **地址窗口约束**：`doBrk` 上限改为 `min(stackMin, 解释器基址)`；`MAP_FIXED` 探测限制在解释器基址以下；必要时为解释器区间注册占位 VMA。
3. **段一致性检查**：对每个被映射的 `PT_LOAD` 断言 `(p_vaddr − p_offset) % 65536 == 0`，不满足则明确报错（不得静默错位）。
4. **验收边界**：让 ldso 完成 `libc.so`/DSO 装载并进入主程序；`mprotect` 仍保持「仅校验」的已登记限制，不在本任务实现真权限。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{se_workload.*,process.*}`、`components/gem5/changelog.md`、`components/gem5/README.md`、本任务书、`milestones.md`。

**不在范围**：装载器/auxv/配置（`GEM5-027t`）、`mprotect` 真权限（另立任务再评估）、主程序 `-pie`/`ET_DYN`（本轮不支持）、动态驱动的全量语料（`TESTCASES-104t`）、QEMU、测试用例与期望。

## 验收标准

1. 动态 `ET_EXEC + PT_INTERP` 小程序在 gem5 SE 上跑完：ldso 映射 `libc.so` 各段成功，进入主程序 `main` 并正常退出。
2. 代表子集（`libc-test dynamic` 的 `functional/argv`、`functional/memstream`、`api/main` 等，按现场）在 gem5 SE pass；逐条给命令与 rc。
3. `readelf -l` 段一致性断言：每个 `PT_LOAD` 满足 `(vaddr-offset)%65536==0`；不满足的产物明确报错。
4. `build-gem5`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、L1/L2 rc=0；静态基线不退化（`GEM5-021t` 抽套件复跑）。
5. 反例：把文件映射分支改回 `-ENODEV` ⇒ 代表子集回 blocked；`cp`+`md5sum -c` 还原重建回绿（禁 git 还原）。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- `mprotect` 不建模权限会让 RELRO 只读不生效：功能不受影响，但「写只读段应 fault」类 oracle 不可信，须在完成区与 README 写明。
- 文件映射与 `brk`/`MAP_FIXED` 的地址窗口冲突是本任务的主要风险，先做「解释器占位 + 上限约束」再跑 ldso。
