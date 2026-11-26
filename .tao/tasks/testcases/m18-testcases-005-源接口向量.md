# m18-testcases-005: 每源 pending/mask/ack 向量（cg15/cg16）

**模块**：testcases
**项目里程碑**：M18
**依赖**：`m18-spec-008`、`m18-qemu-009`（执行侧）、`m18-testcases-004`（R3 载体基线）
**可并行分片**：否
**预估**：3–4 h（标定：同档 testcases-004 3–4 h；本任务为布局迁移 + 新语义向量，取 1–1.2×）
**档位**：中改（独立向量）
**状态**：待开始

## 背景

`m18-spec-008` 把异步捕获移到 `cg15`、monitor mask 移到 `cg15 rc3`、两个源各有 `cg16 rc16/17/18`，并把 pending 改为 ack 才清。现有向量（`m18-testcases-004` 的 escape/pmem/hart 载体）仍按 `cg9`/`cg8 rc1` 写。

## 目标

1. 迁移现有载体/探针：`tests/inst/11-cfx/**`、`tests/arch/**`、`tests/ee-vast|tiny/**`、`tests/shared/asm/**`、legacy 探针、`tools/testcases/generate_lit_vectors.py` 到 `cg15`/`cg15 rc3`/`cg16`。
2. 新向量（独立派生自 spec）：
   - timer：ENABLE/cmp/pending/mask/ack 五组（含使能即检、ack 幂等、写 cmp 不清 pending）；
   - DMA：bit0 合并 DONE|ERROR、ack 只清 pending、status 另行 W1C、`IRQ_EN` 已删；
   - 进入判定：源 mask 与 monitor mask 各自生效、多源合并、`cg15 rc4/rc5` 聚合；
   - `escape rc11` 写 `cg15 rc3` 整字。
3. 执行侧：QEMU（qemu-009 构建）+ RTL/gem5/IDL 可跑项；不可跑项登记 KNOWN-RED。
4. 旧槽位/旧措辞 grep 0；生成物重算。

## 验收

1. `check-inst-asm`、`check-tests-index`、`check-case-ledger`、`check-qemu-forms`、`check-spec-refs` rc=0；向量在 QEMU 上逐条 PASS。
2. 可达 FAIL ≥2（改期望/把 pending 改回进入即清），`cp`+md5 还原。
3. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动 `tests/**`、`tools/testcases/**`、`tools/llvm/*matrix*`（生成物）、本任务书；不改实现/spec/契约/Makefile；期望独立派生。
3. 等 `m18-spec-008` 与 `m18-qemu-009` 落地后派。
