# m17-testcases-001: `tests/inst` 签名区（槽级比对 + 诊断）

**模块**：testcases
**项目里程碑**：M17
**依赖**：`m16-testcases-002`（签名机制已抽到 `tests/shared/asm/signature.inc` + `tools/testcases/lib/signature.py`）
**可并行分片**：否
**预估**：4–6 h
**档位**：中改
**状态**：待开始

## 背景（用户 2026-11-20 定：放 M17，不放 M15）

M15 已收口（58/58），且签名区不是「ISA 语义结构化」；它的**消费者是 M17**——IDL 差分要能报「槽 N 期望 X 实际 Y」，而不是只知道第 N 条断言失败（现在的判据是 guest 内联期望 + `SYS_EXIT(N)`，见 `tests/arch/ptw/expected.yaml` 抬头的同款说明）。

`m16-testcases-002` 已把机制落好：`tests/inst/macros/inst_test.inc` 的 `__REC` 已委托 `SIGUPD`，收尾打印走 `SIG_DUMP_CHARS`；**因此 `.S` 的指令流目前逐字节未变**。

## 关键约束（不许破坏 M16 的周期基线）

`tests/inst` 的 272 个镜像就是 M16 周期标定的语料（`m16-chipyard-001` 的 15 行实测）。本任务**不得改动这 272 个 `.S`**（一改指令流，拍数全变、M16 结论要重验）。

## 目标

1. **期望值从 `.S` 派生到数据**（不跑实现、不拿实测当真值）：写一个解析脚本，从 `__CHECK_RD`/`__CHECK_MEM` 等宏的内联期望常量派生每个镜像的「槽 → 期望值」序列，落 `tests/data/inst-signature/`（带来源：`文件:行` + 生成命令，按「入库产物三件套」）；
2. **host 侧槽级比对**：复用 `tools/testcases/lib/signature.py`（`parse`/`compare`/`unwritten`），不另写解析器；新增 `make check-inst-sig`（L2），对 272 镜像逐槽比对；
3. **诊断能力**：失败输出必须给「槽 N 期望 X 实际 Y + 该槽来自哪个 `.S` 的哪一行」；
4. 现有 `check-inst-asm`（退出码判据）保持不变。

## 验收（逐条贴真实 rc）

1. **272 镜像全量槽级一致**（不是抽样），且镜像数/槽数与 `tests/case-ledger.tsv` 现场派生一致；
2. **`.S` 零改动**：`git diff` 对 `tests/inst/**/*.S` 为空；计时构建的 `.text` 与改前逐字节相同（抽样 ≥20 + 全量 md5 对比更强）；
3. **漏跑可见**：删一条 `SIGUPD`（临时树）⇒ 该槽为 `0xdeadbeef`，报「槽 N 未写」；
4. **可达 FAIL ≥3 路**：① 改一条派生期望值 ⇒ 槽号 + 两侧值报红；② 删一条 `SIGUPD` ⇒ 漏跑红；③ 某镜像签名流缺失 ⇒ BLOCKED 而非 PASS；
5. **不自我实现当真值**：派生的期望值来自 `.S`（spec 派生、已复核），并给「期望值来源」与「实测流」两条独立路径；
6. 门控：`check-inst-asm` **272/272**、`check-tests-index`、`check-case-ledger`、`check-index-blobs`、`check-knowledge-refs`。

## 若解析不可行（退路，需在完成区说明理由）

只做「槽级诊断报告」：不改判据、不新增门控，`check-inst-asm` 失败时额外 dump「哪个槽、什么值」；真正的 conformance 门控留给 `m17-idl-004`（IDL 作 oracle）。**不得**用「把实测值冻结成 golden」来充当期望（那是以实现反推）。

## 约束

独立 `git worktree`；**不提交 git**；**不改 272 个 `.S`**；不改 `signature.inc`/`signature.py` 的机制语义（只消费）；`tests/data/` 新增产物须带输入清单 + 生成命令 + 不可入库原因；术语「寄存器组」；完成区不写具体 `.work/**` 路径。
