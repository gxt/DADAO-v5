# m20-testcases-004: `stm` 63 例注释编号订正（m20-testcases-003 reviewer finding）

**模块**：testcases
**项目里程碑**：M20
**依赖**：`m20-testcases-003` 已合入（`1b2584e9`）
**可并行分片**：否（三个同批 `.S` 注释 + 签名输入）
**预估**：30 min
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（m20-testcases-003 第 1 轮 reviewer finding 1）

`stm.t_rrri_rd.S`、`stm.t_rrri_rf.S`、`stm.w_rrri_rd.S` 的 63 例注释把
`0x100` / `0x080` 写成“第 64 个元素”，实际 63 个元素为 1..63；尾数据单元
`0x0F8` / `0x078` 内已含“第 64 个元素”的未写半区，`0x100` / `0x080` 是
**第 65 个元素（i=64）**。断言值本身正确，仅注释编号错。

## 目标

1. 三处注释改为“第 65 个元素（i=64）”，并保持“未写 ⇒ 保持 MSTORE 模式”的说明。
2. 因 `.S` 内容变化会改变 `tests/data/inst-signature/inputs.sha256`，必须用
   `python3 tools/testcases/inst/check_inst_sig.py --write` 重生成；不得手改。
3. 只改注释，不改变任何指令、点号、槽值；`expected.tsv`/`case-ledger.tsv`
   应无非预期变化。

## 验收（逐条贴真实 rc）

1. `grep` 三个文件不再出现“第 64 个元素”；三处均为“第 65 个元素（i=64）”。
2. `python3 tools/testcases/inst/check_inst_sig.py --write` 后
   `--data-only` rc=0；`inputs.sha256` 与现场 `sha256sum` 一致。
3. `make check-inst-asm` 274/274、`check-case-ledger`、`check-tests-index` 真 rc；
   槽数仍 4576；`expected.tsv`/`case-ledger.tsv` 无非预期 diff。
4. 注释改动不影响二进制：三个镜像的 `llvm-mc` 产物 md5 与改动前一致（或给
   `check-idl` 274/274 作证）。
5. `check-patch-tree` 若总 rc 受在途组件任务影响，按“本任务未触碰组件补丁”披露。

## 约束

独立 `git worktree`（分支 = `m20-testcases-004`）；不提交 git；只改上述三个 `.S`
注释、签名 `inputs.sha256` 与本任务书；不改 `expected.tsv`/`case-ledger.tsv` 的
语义内容、`spec/`、契约、`components/**`、`Makefile`。证据落在运行期证据目录内
`run.sh`。

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
