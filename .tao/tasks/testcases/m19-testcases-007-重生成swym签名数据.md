# m19-testcases-007: 重生成 swym 签名数据（inputs.sha256 + expected.tsv）

**模块**：testcases
**项目里程碑**：M19
**依赖**：`m19-testcases-001`（已合入、已验证；本任务承接其遗漏的签名数据刷新）
**可并行分片**：否
**预估**：≤1 h
**档位**：小改
**状态**：已验证

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

**测试结果**：证据脚本 12/12 项通过（含 3 路注入）；data-only / sha256sum / tests-index / case-ledger 全 rc=0；index-blobs 基线红；idl_four_way rc=1（IDL 腿环境红）。
**修改文件**：`tests/data/inst-signature/expected.tsv`、`tests/data/inst-signature/inputs.sha256`（case-ledger 无 diff，未 `--write`；`.S`/spec/契约/引擎未动）。
**验收结果**：
- 盘点（改前）：`check_inst_sig.py --data-only` rc=1，仅 2 条 DATA-FAIL 均 swym（`expected.tsv:4682`、`inputs.sha256:283`）；`check_case_ledger.py` rc=0。
- 生成：`make inst-signature-data` rc=0，输出「274 镜像 / 4687 槽（静态期望 4649 / 运行期关系 38）」。
- diff（numstat 11/13 + 1/1，仅 swym）：expected.tsv swym 段 13→11 槽；`.S` 头注释 30→37 行 ⇒ 其余源行号整体 +7（`:39`→`:46` …）；用例替换：删旧 #10（bit17 编码 0x478A0000）、#11（低 17 位全 1）、#13（rd0），新增 #10（N=4095 与 N=0 相邻，期望 0xC）⇒ 净 −2；inputs.sha256:283 `599b13c6…`→`b3a13ccb…`（`m19-testcases-001` 重写 `.S`，现场 `sha256sum` 复核一致）；274 镜像无其它漂移。
- 判据：data-only rc=0（274/4687）、`sha256sum -c` rc=0（286 行）、`check-tests-index` rc=0（503 条）、`check-case-ledger` rc=0（5884 条）。
- `check-index-blobs` rc=1：4 处 chipyard patch index 不符，与 master 基线逐行相同（KNOWN-RED，非本任务引入）。
- swym 单例：`idl_four_way.py --only swym_oiii_imm` rc=1；QEMU 腿 88 B/11 槽与重生成 expected.tsv 逐槽全等；IDL 腿 rc=1（`idl_exec.py` 按 0xE000 读 BootROM 表，8 KiB 镜像 `struct.error`，ISS-543 环境问题，非 swym 语义；`m19-idl-001` 未合入）。
- 注入/还原（md5）：expected.tsv `bb7aadb6…` → 注入槽值 `8e858b11…`（data-only rc=1 点名 4682）→ 还原 `bb7aadb6…`；inputs.sha256 `d2f19951…` → 注入哈希 `f5779299…`（data-only + sha256sum 均 rc=1）→ 还原 `d2f19951…`；删末槽（槽数 10≠11）→ 还原；还原后两项 rc=0。
**新发现/坑**：四方差分当前被 ISS-543（BootROM 表偏移 0xE000 vs 8 KiB 新布局）挡在 IDL 腿，重生成数据无法当场取得四方绿；master 的 check-index-blobs 4 处 chipyard 基线红。
**遗留问题**：`check-idl` 全绿需 `m19-idl-001` / ISS-543 修复后复跑；index-blobs 基线红按既有 issue 处置，不在本任务范围。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查生成物 diff、证据脚本与门控输出：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 注入是否只改目标行、是否真触发 FAIL | ✅已修 | 注入前后均 `md5sum` 回读并断言变化；data-only 输出点名 4682/283 | 证据运行日志三路 `md5 changed` + `expected=1 actual=1` |
| 还原是否可靠（禁 git restore） | ✅已修 | 每路 `cp -p` 备份 + 还原后 md5 相等断言 | `restore-{value,hash,drop}: md5 match`，回绿 rc=0 |
| 槽数断言是否写死 | ✅已修 | 从 expected.tsv 与 `.S` 两侧现场派生并互比（含首/末源行号） | `swym slots=11 first_src=46 last_src=132` |
| index-blobs 基线红是否夹带新错 | ✅已修 | 在 master 独立临时树取基线错误集，与本树逐行 diff | 两侧均 4 条 chipyard、diff 为空 |
| 是否夹带无关镜像漂移 | ✅已修 | numstat 仅 swym 两文件；data-only 改前仅 2 条 DATA-FAIL | `git diff --numstat` 11/13 + 1/1 |
| 证据脚本退出码是否被吞 | ✅已修 | 全部用重定向 + `rc=$?`，末尾显式 `exit 1/0` | `bash -n` rc=0；`--inject` 运行 rc=0 |

**判决**：全部 finding 已修，无未修项；状态 → 待验收。

### 第 1 轮 reviewer 验收

**重跑记录**（审查者独立执行，均在任务 worktree 仓库根；不采信完成区转述）：
1. 改前盘点复现：`git archive master` 干净临时树跑 `python3 tools/testcases/inst/check_inst_sig.py --data-only` ⇒ rc=1，恰好 2 条 DATA-FAIL（`expected.tsv:4682` 入库 `:39` vs 现场 `:46`；`inputs.sha256:283` `599b13c6…` vs 现场 `b3a13ccb…`），均 swym，与任务书预期（≥2 条）一致。
2. 修复后同命令本树 ⇒ rc=0：`274 镜像 / 4687 槽（静态期望 4649 / 运行期关系 38）`；槽数现场统计 4689→4687（改前快照 `grep -c 'tests/'` = 4689）。
3. `sha256sum -c tests/data/inst-signature/inputs.sha256` ⇒ rc=0（286 行 OK）；`sha256sum tests/inst/12-misc/swym_oiii_imm.S` = `b3a13ccb9235415a2d677b809287c05b551460f0eb81a2cf7f6b059d6eeb98a0`，与清单 283 行一致。
4. `make check-tests-index` ⇒ rc=0（PASS 503 条）；`make check-case-ledger` ⇒ rc=0（5884 条）；`python3 tools/infra/check_index_blobs.py` ⇒ rc=1（4 处 chipyard patch index 不符）。
5. 基线红独立判定（不 `|| true`）：同一命令在 `git archive master` 干净临时树 ⇒ rc=1，路径前缀规范化后与本树输出 `diff` 为空 ⇒ 错误集逐行相同，非本任务引入。
6. `python3 idl/tools/idl_four_way.py --only swym_oiii_imm` ⇒ rc=1。QEMU 腿产出 88 B，用 `tests/shared/signature.py` 的 `parse(..., 11)` 解析得 11 槽，与 expected.tsv 逐槽比对 mismatch=0；IDL 腿 `idl_exec.py` 按 0xE000 读 BootROM 表、8 KiB 镜像 `struct.error`（已知前置 ISS-543）；另用 master 的 `idl_exec.py` 对同一镜像复跑仍同错 ⇒ 属安装根 bootrom 陈旧，非本任务引入。
7. 证据脚本：仓库根执行运行期证据目录内的 `run.sh --inject` ⇒ rc=0，12/12 CHECK（6 主检 + 3 路注入 + 2 还原回绿）。逐条审计：均捕被检命令自身退出码、槽数两侧现场派生不写死、注入带 `cp -p` 备份 + md5 对账，无恒真/两支同写；其 index-blobs 基线文件我已用 master 独立复核（见 5）。

**独立注入**（注入前 `expected.tsv` md5 `bb7aadb6…`、`inputs.sha256` `d2f19951…`，mtime 2026-11-28 11:05:52）：
- 改 swym 第 1 槽期望 `0x…08 → 0x…77` ⇒ `--data-only` rc=1 且点名 `expected.tsv:4682`；`cp -p` 还原 ⇒ md5 相等、rc=0。
- 改 `inputs.sha256:283` 哈希为 64 个 `0` ⇒ `sha256sum -c` rc=1（该行 FAILED）、`--data-only` rc=1 点名 283；还原 ⇒ md5 相等、双 rc=0。
- 还原后 mtime 未变，`git status -uall` 仍为 3 个文件，与注入前快照逐行一致。

**约束核验**：
- 范围：`git status -uall` = 任务书 + `expected.tsv` + `inputs.sha256`；`git diff HEAD -- tests/inst spec .tao/contracts components idl tests/case-ledger.tsv Makefile` 为空 ⇒ `.S`/spec/契约/引擎/case-ledger 未动；未提交 git。
- diff 全等：`expected.tsv` 24 条变更行 100% 属 swym（非 swym 0 条），`inputs.sha256` 仅 1 行 ⇒ 无夹带无关镜像；274 镜像无其它漂移（由 1 的 rc=0 反证）。
- 逐条解释对上：头块 30→37 行 ⇒ 源行号整体 +7（`:39→:46 … :109→:116`）；新增 #10 期望 `0xC`（N=4095 与 N=0 相邻）、删旧 #10（`0x478A0000`）/#11（`0x4789FFFF`）/#13（rd0）——与 `m19-testcases-001` 合入提交的 `.S` diff 逐条一致 ⇒ 13→11 槽、4689→4687。
- 完成区 15 行 ≤30、无运行期路径、文件清单与 `git status` 对齐；完成区数字（12/12、503、5884、286、274/4687、88 B/11 槽）与我方重跑逐项一致。

**判决**：Accepted —— 验收命令在审查者重跑下全部达标；index-blobs 基线红与 IDL 腿环境红均经独立证实为已知前置、非本任务引入；约束无违反。
