# m20-testcases-006: cfx 测试向量与四方迁移

**模块**：testcases
**项目里程碑**：M20
**依赖**：W2/W3（QEMU/gem5/RTL 实现）；M16/M17 收口后派发
**可并行分片**：否（共享 tests/case-ledger/signature）
**预估**：4–8 h
**档位**：大改（测试数据）
**状态**：待开始

## 背景

执行 `m20-spec-001` 已决口径：cg4–7、PTWFAULT/PTWFAIL、cfx 编号、UART32/33、中断删除、每 cfx 五种原因。需要刷新测试向量/签名/台账，并保持四方差分可解释。

## 范围

- `tests/inst/11-cfx/**`、`tests/arch/**`、`tests/unit/gem5/**` 中受影响的探针/期望；
- `tests/case-ledger.tsv`、`tests/data/inst-signature/**`（生成器写）；
- 四方差分/夜跑基线/README（只改与本批相关部分）。

## 验收

1. 旧 cg/编号/原因/名称残留 0；生成器产出可复现，签名/台账一致。
2. `check-inst-asm`、`check-idl`、`check-case-ledger`、`check-tests-index`、`check-arch-smoke` 真 rc；四方代表集可运行（缺引擎时按门控语义披露）。
3. PTW 故障复用现有 PTW 用例，改期望为 `PTWFAULT 1<<15` + `cfx_ptw cg8 rc4` ID；**不新增专用 PTWFAULT/PTWFAIL 用例**。
4. UART32/33 cg16、power 五种原因、hart 无 IPI 各有最小代表覆盖；不重造全量矩阵。
5. 证据落运行期证据目录内 `run.sh`。

## 约束

独立 worktree（分支 = `m20-testcases-006`）；不提交 git；不改 `spec/`、契约、引擎源码、`Makefile`；生成物禁手改。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填）

#### 第 1 轮 reviewer 验收
（待填）
