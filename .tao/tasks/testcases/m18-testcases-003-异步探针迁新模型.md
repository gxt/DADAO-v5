# m18-testcases-003: 旧异步探针迁新模型 + `escape` cg9 向量（合并已作废的 001/002）

**模块**：testcases
**项目里程碑**：M18
**依赖**：`m18-spec-004` 合入；`m18-qemu-005` 合入（QEMU 新模型）
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景

`ADR-0061` 改写异步模型：来源掩码在**运行模式 monitor**（`cfx0–3 cg8 rc1`，位=源 cfxha）、源身份统一 cfxha（`1<<15`/`1<<32`，取消 `1<<17`/`1<<18`）、`cg9` 七槽且 `src_frame`/`src_pending` 只读、同一界面多源**一帧承载**、帧由 `escape` 结束。原 `m18-testcases-001`（探针迁 hart-first）与 `m18-testcases-002`（escape cg9 向量）按旧口径，已作废，内容合并到本任务。

## 要做

1. **探针迁移**（`min_rom_probe_async_094t.py`、`min_rom_probe_integ050t.py`、`min_rom_probe_integ042t.py`）：
   - 投递目标 `cfx_hart` supv 单向量（`cg9 rc5 excp_vector`、`rc6 switch_run_mode=2`）；
   - 现场 `cg9 rc0–rc2`、`rc3 src_frame`、`rc4 src_pending`（均为 `1<<15`/`1<<32` 位，**不是** 17/18）；
   - 掩码：写**当前模式 monitor** 的 `cg8 rc1`（`0=允许`）；屏蔽 ⇒ 只置 pending；
   - `src_frame`/`src_pending` 只读（写不改变读数）；
   - **同帧多源**：timer+DMA 同时 pending ⇒ 一次进入、`src_frame=(1<<15)|(1<<32)`、`excp_async_num` +1；
   - pending 跟随源：ack（重装 `timer_cmp` / W1C `dma_status`）后 pending 落；
   - `escape imms18=2` 返回并释放（`src_frame` 回 0）。
2. **`escape` cg9 向量**（原 002）：`imms18=2` 合法；`3` ⇒ `ILLI`；`[17:2]≠0` ⇒ `ILLI`；`src_frame==0` 时 `escape` cg9 ⇒ `CFXESC`；汇编层 `imms20=8`（工具链不变）。
3. **文档**：`tools/testcases/arch/README.md` 的 integ051t 摘要、`tests/arch/vast-arch-inventory.md` 改新口径。
4. **不做**：不改 QEMU/kernel/RTL；不改 `escape` 编码。

## 约束

- 独立 `git worktree`；**不提交 git**；只动上述探针/文档与本任务书；不写运行期路径；术语"寄存器组"；
- 失败路径短 timeout，禁长时间 `-d cpu` dump（ISS-522）。

## 验证

运行期证据目录内的 `run.sh`：

1. 三个探针在新模型 QEMU 上 rc=0；对旧模型 QEMU（掩码在 cg9、位 17/18）判红；
2. 覆盖进入/现场/只读/屏蔽→pending/一帧多源/ack 语义/释放/`escape` 四类编码；
3. **可达 FAIL ≥2**：把期望临时改回 17/18 或"串行两帧" ⇒ 红；`cp`+md5 还原回绿；
4. `check-qemu-forms`、`check-tests-index`、`check-tasks`、`check-knowledge-refs` 记录 rc。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
