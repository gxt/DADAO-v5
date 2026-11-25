# m18-spec-007: 定义「异步 escape」——从异步进入现场返回

**模块**：spec
**项目里程碑**：M18
**依赖**：用户给出语义定义（本任务书「待裁定 1」）；`m18-spec-005`（ADR-0061 R2 现行口径）
**可并行分片**：否（spec/契约 + 活文档）
**预估**：待定（语义由用户给出后再标定）
**档位**：大改（异步模型 + `escape` 语义）
**状态**：**待开始（不派发：等用户回复可派发）**
**执行环境**：本地

## 背景

`m18-linux-024` 为“内核态异步返回”不得不借一个**未被使用的 monitor cfx（jmon）**：异步进入把当前 cfx 置为 `cfx_hart`，而 `escape` 只能从**当前 cfx 的 `cg5`** 恢复 `prev_run_mode`/`prev_cfx_code`，且要求 `cg5.cause_id != 0`；异步进入只填 `cg9`，不填 `cg5`，所以无法直接 `escape cfx_hart`。

用户 2026-11-25 裁定：**定义“异步 escape”，使软件可以从异步中断现场直接返回**（不再借 jmon 或其它 monitor）。

## 待裁定（用户给出，未给前本任务不动 spec）

1. **语义定义**（用户提供）：
   - 触发条件：进入异步现场后（当前 cfx = `cfx_hart`、`cg9` 有本次捕获、无 `cg5`）执行 `escape`；
   - 恢复来源：`prev_run_mode`/`prev_cfx_code`/`cause_ip` 取 `cg9 rc0/rc1/rc2`（是否允许软件先改写这几个槽？）；
   - 编码：沿用 `imms18 ∈ {0,1,2}`？`cg9` 选择位（`imms18[1]=1`）在新语义下是“异步返回”还是仍 `CFXESC`？偏移语义（+0/+4）；
   - 与 mask/pending 的关系：返回前后是否重开运行模式 mask、是否扣 pending、是否允许在返回窗口内再投递（嵌套）；
   - 计数：`excp_async_num`/`escape_num` 是否变化；
   - 错误：不同步现场、目标不是 `cfx_hart`、编码非法、重复 escape 的 cause；
   - 与 `cg9` “捕获缓冲、每次覆盖、无 frame_valid”的关系（是否需要“返回后使捕获失效”？）。
2. 版本号是否升级（默认不动，除非用户明确）。

## 目标（待语义确定后细化）

1. `spec/DADAO-12` §5.1/§5.4（`escape` 与异步现场）新增“异步 escape”条文；`§4.7 cg9` 若需配合（如返回后状态）同步。
2. `.tao/contracts/contract-see.md` 同步（`escape` 行、异步边界、掩码/pending 口径）。
3. 活文档残留扫描（`ADR-0060/0061`、`vast-arch-inventory`、`expected-divergences` 等）按新口径更新或标注。
4. 不实现：QEMU/RTL/gem5/IDL/LLVM/内核各实现由后续任务承接（`m18-qemu-007`、内核换帧任务等）。

## 验收（待语义确定后细化）

1. spec/契约一致、`check-spec-codeblocks`/`-changelog`/`-purity`、`check-contracts-*`、`check-manifests-guard` rc=0。
2. 语义条文的**每条断言可被后续实现直接判定**（触发/恢复/编码/嵌套/错误 五类齐全）。
3. 全文无自相矛盾（旧 R2 的“`escape` 不以 `cg9` 为返回帧”必须显式改写或限定）。
4. 版本号按裁定执行；完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动 spec/契约/活文档 + 本任务书；不改实现组件。
3. **语义由用户给出**：未给出前不得自行发挥、不得把 `m18-linux-024` 的现状反推成规范。
4. 术语「bank = 寄存器组」；还原 `cp`+md5。

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
