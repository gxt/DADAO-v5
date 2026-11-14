# m14-linux-004: K1 内核自建页表并写 PTBR（Vast；索引口径按 spec）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-003`（到 `start_kernel`）
**可并行分片**：否
**预估**：3–4 h
**状态**：待开始

## 用户裁定（2026-11-14，原话）

> 「K1要开PTBR，但是qemu-system应该不需要tlb」
> （PTBR 语义）「内核自建表并写 PTBR」
> （页表索引口径）「按 spec：index 4096 + 1 超页」

## 现状

- smon 预建**一张**页表（`PTBR=0`，表在 PA 0），用 1 个超页映射 `VA [0x0200_0000_0000, 0x0200_2000_0000) → PA [0, 0x2000_0000)`，`ptw_enable=1`，内核以 VA 入口进入（`m14-qemu-001`、`ADR-0051 D6`）；
- `spec/DADAO-12 §4`：**L1 索引 = `VA[41:29] × 8`**，PTBR 只存 `PPN[55:16]`（64 KiB 对齐）、`[15:0]` 强制 0；
- **旧口径残留**：`m14-qemu-001` 任务书 §3/§5/验收 1d 与部分 ADR/契约文本里仍有「L1 index 0、4 个 PTE、`rd28==4`」表述，与 spec 冲突 ⇒ 本任务按用户裁定**以 spec 为准**并在同一变更内订正这些文本（不改语义，只改口径）。

## 范围

1. 内核在 `start_kernel` 之前/之内**自建 L1（及必要的二级）页表**（在 pmem 中、64 KiB 对齐），映射内核窗口与必要的 boot info 区域；
2. **写 PTBR**（`cfx_ptw_ptbr`，PPN 形式）+ 必要时重写 `ptw_enable`（保持 1）；**qemu-system 无 TLB 语义要求**，不实现 TLB 失效/填充逻辑；
3. 切换后**继续执行**（取指与数据访问都走新表），并打印 PTBR 新旧值 + 关键 PTE 索引（`VA[41:29]` 的现场值，应为 **4096**）；
4. 订正旧口径文本：`m14-qemu-001` 任务书的「4 个 PTE / `rd28==4`」段（加「已被 `m14-linux-004` 口径取代」注记，**不改写完成区**）；`ADR-0051`/契约中若写死「index 0」，按 spec 改为「索引由 `VA[41:29]` 求出，内核窗口为 4096」。

## 验收（逐条贴真实输出）

1. **PTBR 写入生效**：打印切换前后 PTBR；切换后 guest 仍能输出下一行（证明取指/数据都走新表）；
2. **索引正确**：现场打印 `VA[41:29]` 与所用 PTE 索引 = **4096**；表项内容与 `spec/DADAO-12 §4` 的字段定义逐项相符（P/SP/SPF/HSJU/R/W/X）；
3. **映射正确性**：抽 2 个地址（内核窗口内 + boot info 所在地址）做「VA→PA」核对（可用探针读回 PA 内容比对）；
4. **负例**：故意把 PTBR 写到一个未对齐/未映射的物理基址 ⇒ 内核应触发 `CFXMEM` 并**具名退出**（或按 spec 的异常路径），不得静默 continue；
5. 可达 FAIL 注入 ≥2 路（把 PTE 的 SP 位清零 ⇒ 缺页；把 PTBR 的 PPN 改 1 位 ⇒ 映射错），`cp`+md5 还原；
6. `check-linux-k0` 仍 rc=0（K0 不回归）；补丁 `make_patch.py linux` 重导出；`--source-state` linux OK；changelog 一条；
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；禁 `install-host`/`check-modules`；`build-linux` 用 `JOBS=32`；禁边构建边测试。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. 只改 `components/linux/**`（`arch/dadao` 补丁）、`components/linux/changelog.md`、`tools/linux/**`、`m14-qemu-001` 任务书的口径注记、`ADR-0051`/契约的必要订正（**需在完成区逐条列出改了哪句、依据 spec 哪段**）；不改 QEMU/RTL 语义。
5. 只在 `qemu-system vast` 上验收。

## 待裁定

（实现中写）

## 审阅记录

（待填）
