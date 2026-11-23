# m16-chipyard-022: RTL cfx32 pmem（DMA + hart-first 完成中断）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-021`（cfx_hart cg9 已就位）；`ADR-0060`（hart-first）
**可并行分片**：否
**预估**：4–6 h
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景

`ADR-0060`：PMEM_DMA（`1<<18`，源 cfx_pmem）投 **`cfx_hart`（cfxha 15）** 的 supv 单向量，现场/mask/pending 在 `cfx_hart cg9`（由 021 提供）。本任务补 cfx32 pmem 的寄存器/DMA 与完成中断投递。

## 要做

1. **寄存器面**：`pmem_exist`、`pmem_start[0..63]`、`pmem_size[0..63]`、`pmem_attr[0..63]`、`dma_src`/`dma_dst`/`dma_size`/`dma_ctrl`/`dma_status`（`DADAO-12 §4.9`）。
2. **DMA**：单 hart 搬运；`dma_status` DONE/错误；源/目标/大小校验；与 TLB/PTW 交互按契约。
3. **完成中断（hart-first）**：DMA 完成 ⇒ `async_cause_id=1<<18`；投 `cfx_hart` supv 单向量（`cg9 rc6`/`rc7=2`）；mask 查 `cg9 rc8–rc12`（位=32）；pending 置 `cg9 rc5`（位=`1<<18`）；无嵌套/写 0 释放同 021。
4. **escape**：`imms18=2` 选 cg9；`3` ⇒ `ILLI`。
5. **探针**：pmem 配置/DMA/回读；完成中断投 cfx_hart/supv、cg9 现场/pending/mask；escape。
6. **H/S/U 三模式**：DMA 完成在 hmon/smon/umon 下都投 cfx_hart supv；权限不允许的模式显式标注。
7. **三方用例（B）**：case 只写一份，RTL 与 QEMU/gem5 复用；`check-arch-vast` 按需。
8. **不回归**：Tiny 无 cfx32；页表装载/PTW 既有探针不回归；cfx3/4/5 不变。

## 不做

- 不做 cfx15/34（另两件）；
- 不做 monitor-first、多核、uart；
- 不改 cfx0/2 同步路由。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py chipyard` 幂等；
- 重建环境写进证据脚本；不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. pmem 配置/DMA 搬运逐字节；`dma_status` DONE/错误；
2. 完成中断：`async_cause_id=1<<18`、投 cfx_hart supv、`cg9` 现场、pending 位 `1<<18`、mask 位 32；
3. H/S/U 三模式投递目标均为 cfx_hart/supv；
4. `escape imms18=2`；`3` ⇒ `ILLI`；
5. **可达 FAIL**：注入「DMA 不搬运」/「完成投 monitor」⇒ 红；`cp`+md5 还原并强制重建后回绿；
6. `check-patch-tree` chipyard 段 0 problem、`check-index-blobs`、`check-tests-index`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
