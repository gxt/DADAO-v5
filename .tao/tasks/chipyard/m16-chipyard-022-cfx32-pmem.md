# m16-chipyard-022: RTL cfx32 pmem（DMA + 源 cfxha 32 的完成投递）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-026`（R2 捕获缓冲）合入；`m18-spec-005`（R2 规格）已合入；`m16-chipyard-024` 已合入
**可并行分片**：否（同改 `components/chipyard`）
**预估**：4–6 h
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景

`ADR-0061`：PMEM_DMA 以 **cfxha 32** 标识；pending/帧内位 = `1<<32`；掩码在**当前模式 monitor** 的 `cg8 rc1`（bit32）；帧内细节回 `cfx_pmem cg15 rc4`（W1C），不走 `cause_info`。`cfx_hart cg9` 七槽与仲裁由 024 提供，本任务补 cfx32 的寄存器/DMA 与完成投递。

## 要做

1. **寄存器面**：`pmem_exist`、`pmem_start[0..63]`、`pmem_size[0..63]`、`pmem_attr[0..63]`、`dma_src`/`dma_dst`/`dma_size`/`dma_ctrl`/`dma_status`（`DADAO-12 §4.9`；`DONE/ERROR` W1C、`ERR_CODE` one-hot、`BUSY` 期写忽略）。
2. **DMA**：单 hart 搬运；源/目标/大小校验；`dma_status` DONE/错误；与 TLB/PTW 交互按契约。
3. **完成投递（R2 捕获缓冲）**：完成（或错误）⇒ 置 `cfx_hart cg9 src_pending` 的 bit32；放行（当前模式 monitor 掩码 bit32=0）⇒ 同一指令边界投递并**整体覆盖** `cg9` 捕获；同界多源时 `src_frame` 为位图并集（与 timer 15 同一次进入）。**没有帧空/帧活动期门控**。
4. **pending 跟随源**：投递即清 bit32；`dma_status` W1C 后 pending 落（不产生遗留投递）。
5. **`escape`（R2）**：`imms18=2` **不用于异步返回**——按所选帧无效报当前 cfx 的 `CFXESC`，不改变 cfx/mode/`cg9`；`imms18=3`/`[17:2]≠0` ⇒ `ILLI`。
6. **探针**：pmem 配置/DMA/回读；完成投递（单源 + 与 timer 同帧多源）；H/S/U 三模式（各写自己 monitor 掩码）。
7. **不回归**：Tiny 无 cfx32；页表/PTW 既有探针；cfx3/4/5/15 不变。

## 不做

- 不做 cfx34（023）；
- 不改 `escape` 编码、不改 `cfx_hart cg9` 布局（024）；
- 不做 monitor-first、多核、uart。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py chipyard` 幂等；
- 重建环境写进证据脚本；失败路径短 timeout、禁长时间 `-d cpu` dump（ISS-522）；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. pmem 配置/DMA 逐字节；`dma_status` DONE/ERROR/ERR_CODE；
2. 完成投递：`src_pending` bit32、`src_frame=1<<32`、mask 位 32、ack 后 pending 落；
3. **同界多源**：timer(15)+DMA(32) 同时 pending ⇒ 一次进入、`src_frame` 并集、`excp_async_num` +1；
4. H/S/U 三模式投递目标均 `cfx_hart`/supv；覆盖语义（不搬走再到期 ⇒ 整体覆盖）；
5. `escape imms18=2` ⇒ `CFXESC`、`cg9` 不变；`3`/`[17:2]≠0` ⇒ `ILLI`；
6. **可达 FAIL ≥2**：注入"DMA 不搬运"、"完成投 monitor"、"pending 记 18" ⇒ 红；`cp`+md5 还原并强制重建回绿；
7. `check-patch-tree` chipyard 段 0 problem、`check-index-blobs`、`check-tests-index`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
