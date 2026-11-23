# m18-infra-003: musl 补丁集同步（ISS-507）与信号帧复核

**模块**：infra
**项目里程碑**：M18
**依赖**：无（与 linux/musl 写者串行；`m18-linux-006` 的返工与 `TEST_ADAPT` 待本任务）
**可并行分片**：否
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测中位 86 min；本任务为源树重放 + 重建 + 复核，取 1.5–2× 中位）
**档位**：中改（组件源树/补丁集 + 运行复核）
**状态**：待开始
**执行环境**：本地（QEMU system `-M kaiwu-vast`）

## 背景

`m18-linux-006` 复核纠正了「DADAO 用户态信号帧 ABI 缺失」的结论：

- 现象：`sigaction` 安装/查询 PASS，`p_raise`/`p_usr1` 投递即 SIGSEGV（rc=139）。
- **反证**：reviewer 用 `SA_RESTORER=0x04000000` + 真 `rt_sigreturn` 桩的探针 `p_raise3` **PASS**（handler 执行、返回主流程、rc=0），不改内核 ⇒ **内核信号帧可用**，与 `m14-linux-046` K5 帧往返、`m14-infra-005` 36/36 一致。
- 真因链：**musl 源树未打补丁集**（`check-patch-tree` musl ⑥⑨ = `ISS-507`：`src/signal/dadao/restore.s` 缺、`bits/signal.h` 与补丁集不一致）⇒ `sigaction.o` 无 `0x04000000` 立即数 ⇒ 内核 `setup_rt_frame` -EFAULT → force_sigsegv。
- 因此「`m18-linux-020` 信号帧 ABI」的立项前提不成立；本任务改为**先恢复 musl 源树/补丁集一致**，再复跑信号帧与 LTP 新接口用例。

## 目标

1. 按 `docs/Process-01` 把共享 musl 源树恢复到锁定补丁集：删源树 → `make fetch` → `apply_series.py --component musl` → `make build-musl`（必要时 `build-musl-shared`）；不手工改源树、不手抄补丁。
2. `check-patch-tree` musl 段 **0 problem**（ISS-507 闭合）；`check-musl-freshness` rc=0。
3. 重建后复核：`p_raise`/`p_usr1` 不再 SIGSEGV；`SA_RESTORER` 立即数在 `sigaction.o` 中可见；`sigreturn` 返回路径正确。
4. 复跑 `m18-linux-006` 的 `sigaction01`/`open01` 与 64 KiB 候选（`mmap01`/`brk01`/`munmap01`），把结果交回 006 返工。

## 验收（逐条贴真实 rc）

1. `make fetch` + `apply_series.py --component musl` rc=0；`check-patch-tree` musl 段 0 problem（`ISS-507` 关闭或缩到 0）。
2. `make build-musl` rc=0；`libc.a` 重建；`readelf`/`objdump` 确认 `sigaction.o` 含 `0x04000000` 立即数、`restore.s` 符号存在。
3. `p_raise`、`p_usr1` 连续 5 次 rc=0（不再 SIGSEGV）；`p_raise3` 仍 PASS。
4. `run_suite.py --suite ltp --only ltp-sigaction01` / `--only ltp-open01` 不再 `rc=139`，给出真实 PASS/FAIL；`mlockall02` 仍按 `SUITE_ENV` 记录。
5. **可达 FAIL ≥1 路**：临时移走 `restore.s` 补丁（或回退 `bits/signal.h`）⇒ `p_raise`/`sigaction01` 复现 SIGSEGV；`cp`+md5 还原 + 重建后回绿。
6. 不回归：`check-linux-k5` 280/280、`check-linux-k6` 71/71；`check-config-pins`/`check-component-changelog`/`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
7. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`components/musl/**`（仅源树/补丁集重放与必要文档）、`components/musl/changelog.md`、`tests/unit/linux/suite/**`（triage/用例配置）、`tools/linux/**`（仅必要）、`.tao/knowledge/issues.yaml`（ISS-507）、本任务书。
3. 不改 `components/linux|qemu|busybox/**`、`spec/`、`.tao/contracts/`、`Makefile`；不改版本号。
4. 源树重放严格按 `docs/Process-01`；禁止手工 `cp` 补丁进源树；还原一律 `cp`+md5；还原后重建。
5. 若重放后 `check-patch-tree` 仍有非零 problem：保留逐行证据，区分「基线/补丁集漂移」与「本任务引入」，不得用 `|| true` 放行。
6. 术语「bank = 寄存器组」；大端/64 KiB 页口径按 `MEMORY.md`。

## 待裁定

无。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（工程师自审意见、问题、判决及 finding 处置）

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）
