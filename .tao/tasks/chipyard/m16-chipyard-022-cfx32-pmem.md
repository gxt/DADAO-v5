# m16-chipyard-022: RTL cfx32 pmem（寄存器 + DMA 完成中断）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-021` 合入
**可并行分片**：否
**预估**：4–5 h
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景

004 盘点：RTL 缺 cfx32 pmem（QEMU/gem5 已有）；现有页表装载走 `+loadmem`，没有 cfx_pmem DMA。用户 2026-11-22 定：三个 cfx 都补、每个 cfx 一件；中断源只有 cfx15 的 timer 与 cfx32 的 pmem DMA 完成。

## 要做

1. **寄存器面**：`pmem_exist`、`pmem_start[0..63]`、`pmem_size[0..63]`、`pmem_attr[0..63]`、`dma_src`/`dma_dst`/`dma_size`/`dma_ctrl`/`dma_status`（`DADAO-12 §4.9`；位域/读写属性按 `contract-see` 现场解析）。
2. **DMA**：按 `dma_ctrl` 执行一次单 hart 搬运；`dma_status` 反映 DONE/错误；源/目标/大小校验按契约；与 TLB/PTW 的交互按契约（PA 访问，必要时 `cfx_ptw` 路径）。
3. **完成中断**：DMA 完成按 `cfx_pmem bit8`（`PMEM_DMA`）触发，进入当前运行模式 monitor。
4. **探针**：RTL 探针配置一段 pmem、DMA 搬运、回读比对、观察完成状态与中断。
5. **不回归**：Tiny 无 cfx32；cfx3/4/5 既有语义不变；页表装载路径不被破坏。

6. **三方用例（B）**：cfx32 的 case 定义/期望只写一份；RTL 探针与 QEMU/gem5 后端复用同一 case（非必要不为每个平台写三份载体），由 `check-arch-vast` 按需跑三方。

**H/S/U 三模式**（用户 2026-11-22）：cfx32 的寄存器面/DMA/完成中断应在 `hmon`/`smon`/`umon` 三种运行模式下各跑一次（复用 `tests/arch/common/env/`）；权限不允许的模式显式标注 `modes` 排除原因。

## 不做

- 不做 cfx15/34（另两件）；
- 不改 cfx0/2 的模式路由（020）；
- 不加多核。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py chipyard` 幂等；
- 重建环境写进证据脚本；不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. RTL 探针：pmem 配置、DMA 搬运、回读逐字节一致；`dma_status` 的 DONE/错误；完成中断进入 monitor；
2. Tiny 代表例不回归；页表装载/PTW 既有探针不回归；
3. **可达 FAIL**：注入「DMA 不搬运」⇒ 回读红；注入「完成不触发中断」⇒ 红；`cp`+md5 还原并强制重建后回绿；
4. `check-patch-tree` chipyard 段 0 problem、`check-index-blobs`、`check-tests-index`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
