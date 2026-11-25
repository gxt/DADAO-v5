# m18-testcases-004: 异步 escape 出口帧向量与探针（任务链第 2 环）

**模块**：testcases
**项目里程碑**：M18
**依赖**：`m18-spec-007`（已合入）、`m18-llvm-002`（汇编器支持 `escape cfxHA`）、`m18-qemu-008`（可选，用于执行侧证据）；RTL/gem5/IDL 执行证据待各自任务
**可并行分片**：否
**预估**：3–4 h（标定：同档 testcases-003 2–3 h；本任务覆盖 cg5/cg9 新布局 + escape 五类判据，取 1.2–1.5×）
**档位**：中改（独立向量 + 探针）
**状态**：待开始
**执行环境**：本地（QEMU `kaiwu-vast`；RTL/gem5 视可用性）

## 背景

`m18-spec-007` 定了出口帧：`cg5 rc0`–`rc3` 入口记录（只读）、`rc8`–`rc11` 出口意图；`cg9 rc0`–`rc4` 记录/源集合、`rc14` switch、`rc15` vector；`escape cfxHA` 按 `rc8`–`rc11` 返回并把 `rc11` 整字写目标 monitor `cg8 rc1`。目前没有任何独立向量覆盖这些判据，实现任务（QEMU/RTL/gem5/IDL/内核）各自没有共同 oracle。

## 目标（每条一向量，独立派生自 spec，**不得**从任何实现生成期望值）

1. `cg5` 布局：`rc0`–`rc3` 写入 ⇒ `CFXREG`；`rc4`/`rc5` cause id/info；`rc8`–`rc11` 读写；`rc11` 复位全 1；`excp pending`（旧 `rc5`）访问 ⇒ 按新布局语义（`rc5` 是 cause info，写入/读取行为按表）。
2. `cg9` 布局：`rc0`–`rc4` 只读、`rc5` pending 只读、`rc14`/`rc15` 读写、`rc6`–`rc13` ⇒ `CFXREG`；`rc15` 低 2 位写忽略。
3. `cg0`–`cg3`：`rc14` switch、`rc15` vector 生效；`rc8`/`rc10` ⇒ `CFXREG`。
4. 进入自动填：同步 `trap` 后目标 cfx `cg5 rc0`–`rc5`/`rc8`–`rc11` 正确；异步进入后 `cg9 rc0`–`rc4` 与 hart `cg5 rc8`–`rc11` 正确、hart `cg5 rc0`–`rc3` 不变。
5. `escape` 判据：正常返回四元组（mode/cfx/ip/mask）；`imms18 != 0` ⇒ `ILLI`；`cfxha` ≠ 当前 cfx ⇒ `CFXESC`；目标模式升权 ⇒ `CFXESC`；目标 cfx 未实现/无 monitor ⇒ `CFXESC`；`escape_num` +1；`rc11` 整字覆盖（反例：增量写 ⇒ 向量红）。
6. 与 `m18-linux-024` 的窗口场景对应：新模型下“恢复→escape”不可被异步插入（向量/探针应证明 mask 在跳转前生效）。

## 验收（逐条贴真实 rc）

1. 向量在 `tests/inst/**`（或既有向量框架）落地，`check-inst-asm`、`check-idl`、`check-tests-index`、`check-case-ledger` rc=0；生成物重算。
2. 执行侧：QEMU（`m18-qemu-008` 合入后）逐条 PASS；RTL/gem5/IDL 未就绪的条目登记 `expected-divergences` 或 KNOWN-RED（不得静默跳过）。
3. **可达 FAIL ≥2 路**：故意把某期望值写错/把 `rc11` 当增量 ⇒ 向量红；`cp`+md5 还原回绿。
4. 不回归：`check-spec-codeblocks`/`-refs`/`check-contracts-*`（向量引用 spec 的锚点有效）。
5. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`tests/inst/**`、`tests/unit/**`（向量侧）、`tests/case-ledger.tsv`、`tests/data/inst-signature/**`、`tests/arch/**`（探针，如需）、本任务书。
3. 不改实现（QEMU/RTL/gem5/IDL/LLVM/内核）、spec/契约/Makefile；不改版本号。
4. 期望值必须**独立派生自 spec**，不得从 QEMU/RTL 生成；`cp`+md5 还原；临时目录 `/tmp/opencode/m18-testcases-004/`。

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
