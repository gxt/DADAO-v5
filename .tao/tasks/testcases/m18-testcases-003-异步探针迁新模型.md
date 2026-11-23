# m18-testcases-003: 异步探针迁新模型 + `escape` cg9 向量（合并已作废的 001/002）

**模块**：testcases
**项目里程碑**：M18
**依赖**：`m18-spec-005`、`m18-qemu-006`（ADR-0061 R2：cg9 捕获缓冲、escape 不异步返回）
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为 3 探针 + 向量 + 签名，取 1.5–2× 中位）
**档位**：中改（复核 ≤40 min）
**状态**：待开始
**执行环境**：本地（QEMU system；RTL/gem5 未支持 cg9 时按平台标注）

## 背景

`ADR-0061 R2` 已定：

- 来源掩码在**运行模式 monitor**（`cfx0–3 cg8 rc1`，位=源 cfxha 15/32，复位全 1）；
- 源身份统一 cfxha（`1<<15`/`1<<32`，取消 17/18）；
- `cg9` 是**进入瞬间捕获缓冲**：每次 async 进入覆盖 `prev_*`/`cause_ip`/`src_frame`/`src_pending`；`src_frame`/`src_pending` **HW/RO**；无 `frame_valid`、无软件清 `src_frame`；
- 硬件**不因 `src_frame != 0` 拒绝/只置 pending**；mask 只决定是否投递；
- 同界多源一次捕获（`src_frame` 并集、pending 扣除、`excp_async_num+1`）；
- `escape imms18[1]=1`（cg9）**不再异步返回**；cg9 非返回帧 ⇒ 当前 cfx `CFXESC`；sync/cg5 不变；
- 入口/嵌套由软件处理（hart 捕获 → `task_pt_regs` → `cfx_smon`）。

原 `m18-testcases-001/002` 已作废，内容并入本任务。

## 要做

1. **探针迁移**（`min_rom_probe_async_094t.py`、`min_rom_probe_integ050t.py`、`min_rom_probe_integ042t.py`）：
   - 投递目标 `cfx_hart` supv 单向量（`cg9 rc5 excp_vector`、`rc6 switch_run_mode=2`）；
   - 现场 `cg9 rc0–rc2`、`rc3 src_frame`、`rc4 src_pending`（位 15/32，**不是** 17/18）；
   - mask 写**当前模式 monitor** `cg8 rc1`（`0=允许`）；屏蔽 ⇒ 只置 pending；解除后进入；
   - `src_frame`/`src_pending` 只读（写不改变读数）；
   - **每次进入覆盖**：连续两次 async，第二次覆盖第一次（`src_frame` 从 bit32 变 bit15 等），无“帧活动期阻塞”；
   - **同界多源**：timer+DMA 同时 pending ⇒ 一次进入、`src_frame=(1<<15)|(1<<32)`、`excp_async_num+1`；
   - pending 跟随源：ack（重装 `timer_cmp` / W1C `dma_status`）后 pending 落；
   - `escape imms18=2`（cg9）⇒ **`CFXESC`**，不返回、不清 `src_frame`。
2. **`escape` 向量**（原 002）：`imms18=2` 合法但 `CFXESC`；`3`/`[17:2]≠0` ⇒ `ILLI`；sync `cg5` 的 0/4 不变；汇编层 `imms20=8`（工具链不变）。
3. **文档**：`tools/testcases/arch/README.md` 的 integ051t 摘要、`tests/arch/vast-arch-inventory.md` 改 R2 口径。
4. **050t 处理**：`min_rom_probe_integ050t.py` 自 qemu-005 起已不兼容 ADR-0061（首例 TIMEOUT）；按 R2 重写其异步部分；无法可判定覆盖的条目按 `expected-divergences.yaml` 或 SKIP 记录原因，不静默。
5. 生成 `case-ledger.tsv`、`inst-signature/{expected.tsv,inputs.sha256}`（工具重算）。

## 约束

- 独立 `git worktree`；**不提交 git**；只动 3 探针、`tools/testcases/arch/README.md`、`tests/inst/11-cfx/**`、`tests/inst.yaml`、`case-ledger.tsv`、`inst-signature/**`、本任务书；不写运行期路径；术语「寄存器组」；
- 不改 QEMU/RTL/gem5/IDL/内核/spec/契约/Makefile；不改版本号；
- 失败路径短 timeout，禁长时间 `-d cpu` dump（`ISS-522`）。

## 验证

运行期证据目录内的 `run.sh`：

1. 三个探针在新模型 QEMU 上 rc=0；旧模型 QEMU（帧活动 gating/位 17/18）判红；
2. 覆盖：投递/现场/只读/屏蔽→pending/解除/每次覆盖/同界多源/ack/`escape 2 ⇒ CFXESC`/ILLI；
3. **可达 FAIL ≥2**：把期望临时改回 17/18 或“帧活动只 pending” ⇒ 红；`cp`+md5 还原回绿；
4. `check-inst-asm`、`check-idl`、`check-tests-index`、`check-case-ledger`、`check-inst-macro-scope`、`check-qemu-forms`、`check-tasks`、`check-knowledge-refs` 记录 rc；`make check` 与基线逐行相同。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
