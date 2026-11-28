# m19-testcases-007: 重生成 swym 签名数据（inputs.sha256 + expected.tsv）

**模块**：testcases
**项目里程碑**：M19
**依赖**：`m19-testcases-001`（已合入、已验证；本任务承接其遗漏的签名数据刷新）
**可并行分片**：否
**预估**：≤1 h
**档位**：小改
**状态**：待开始

## 背景

`m19-testcases-001`（已合入、已验证）重写了 `tests/inst/12-misc/swym_oiii_imm.S`（加 4 条高位 ILLI 故障例 + N 合法链例，链例检查点由 13 个收敛到 11 个），但**没有重生成签名数据**，导致 master 上入库生成物与现场 `.S` 漂移：

- `tests/data/inst-signature/inputs.sha256` 行 283：该 `.S` 的哈希为 `599b13c6…`，现场实测 `b3a13ccb…`（`sha256sum tests/inst/12-misc/swym_oiii_imm.S` 现取）。
- `tests/data/inst-signature/expected.tsv`：swym 段（自 4682 行起）仍是旧 13 槽 / 104 B（源行号引用 `:39` 等），现场 `.S` 为 11 槽 / 88 B（源行号 `:46` 起）。
- `make check-idl` 264/274，swym 唯一红即此假红（生成物陈旧，非语义错）。

现场已核实（2026-11-28）：
- `python3 tools/testcases/inst/check_inst_sig.py --data-only` ⇒ rc=1，报 `expected.tsv:4682 行不一致` + `inputs.sha256:283 行不一致`（两处均指向 swym）。
- `python3 tools/infra/check_case_ledger.py` ⇒ rc=0 PASS（`tests/case-ledger.tsv` 已随 `m19-testcases-001` 同步，无需再 `--write`，但作为判据保留）。

## 目标

1. **现场盘点所有陈旧项，不只 swym**：用官方工具检查 `inputs.sha256`/`expected.tsv` 与现场 `.S` 的一致性，列出全部漂移项（不得写死「只有 1 处」；当前仅 swym 一处镜像、两个文件，engineer 须自行复核确认无其它镜像陈旧）。
2. **用官方生成路径重生成**：`make inst-signature-data`（等价 `python3 tools/testcases/inst/check_inst_sig.py --write`，唯一生成入口；只重生成数据、不跑 QEMU）。若身份清单也需同步则 `python3 tools/infra/check_case_ledger.py --write`（当前已 PASS，预判无需）。
3. **判据 rc=0**：`check_inst_sig.py --data-only`、`sha256sum -c tests/data/inst-signature/inputs.sha256`（仓库根执行）、`make check-tests-index`、`make check-case-ledger`、`make check-index-blobs`。
4. **`make check-idl` 的 swym 单例一致**：重生成后 swym 对 regenerated `expected.tsv` 逐槽一致；QEMU 腿若因 `m19-qemu-002` 未合入（高位 SBZ/ILLI 未实现）而红，如实记录 IDL 腿 + QEMU 腿结果，**不得 `|| true` 凑绿**。
5. **只改生成物**：`tests/data/inst-signature/{expected.tsv,inputs.sha256}` 与（若需要）`tests/case-ledger.tsv`；不改 `.S`、不改 spec/契约/引擎。
6. **范围红线**：生成 diff 逐条解释（哪些镜像、为什么变、槽数/源行号/哈希如何变）；不得夹带无关镜像漂移；若发现其它镜像也陈旧，一并修并在完成区逐条列出。

## 验收（逐条贴真实 rc）

1. **盘点前**：`check_inst_sig.py --data-only` 的 rc 与逐条 DATA-FAIL（预期 ≥2 条，均 swym）；`check_case_ledger.py` rc。
2. **重生成 + diff**：`make inst-signature-data` 输出（`已写 … N 镜像 / M 槽`）；`git diff --stat` 只含 swym 相关生成物；`git diff` 逐条贴出并解释（expected.tsv swym 段 13→11 槽、源行号 39→46 等、inputs.sha256 行 283 hash `599b13c6…`→`b3a13ccb…`）。若 case-ledger 无 diff，明确写「无 diff，未 --write」。
3. **判据 rc=0**（贴真实 rc）：
   - `check_inst_sig.py --data-only` ⇒ rc=0（PASS --data-only）；
   - `sha256sum -c tests/data/inst-signature/inputs.sha256` ⇒ rc=0（仓库根）；
   - `make check-tests-index`、`make check-case-ledger`、`make check-index-blobs` ⇒ 各 rc=0。
4. **swym 单例四方一致**：`python3 idl/tools/idl_four_way.py --only swym_oiii_imm`（或 `make check-idl` 全量，取其一并贴 rc）。IDL 腿对 regenerated `expected.tsv` 逐槽一致；QEMU 腿若因 `m19-qemu-002` 未合入而红，如实记录两腿结果（含退出码/签名流字节数），**不得 `|| true`**。若安装根 QEMU/bootrom 陈旧（见 `m19-testcases-006` 待裁定 1），如实记录环境并说明对 swym 判定的影响。
5. **可达 FAIL ≥1 路**：运行期证据目录内 `run.sh` 含「注入 → FAIL → `cp`+md5 还原 → 回绿」1 路（例如：注入改 regenerated `expected.tsv` 某槽值 ⇒ `--data-only` rc=1 且点名该行；或注入改 `inputs.sha256` 某行哈希 ⇒ `sha256sum -c` 报该行；均 `cp` 备份 + md5 对账还原后回绿）。
6. **约束**：未改 `.S`/spec/契约/引擎源码；生成差异逐条解释；不接板；不提交 git。

## 约束

独立 `git worktree`；**不提交 git**；只动 `tests/data/inst-signature/{expected.tsv,inputs.sha256}` 与（若需要）`tests/case-ledger.tsv`；完成区不写具体 `.work/**` 路径；不升版本号。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审

（待填）

### 第 1 轮 reviewer 验收

（待填）
