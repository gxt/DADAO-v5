# m20-testcases-004: `stm` 63 例注释编号订正（m20-testcases-003 reviewer finding）

**模块**：testcases
**项目里程碑**：M20
**依赖**：`m20-testcases-003` 已合入（`1b2584e9`）
**可并行分片**：否（三个同批 `.S` 注释 + 签名输入）
**预估**：30 min
**档位**：小改（复核 ≤20 min）
**状态**：已验证

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

**测试结果**：运行期证据目录 `run.sh` rc=0（全绿）；`--data-only` rc=0（274 镜像 / 4576 槽）；`sha256sum -c` rc=0（286/286 OK）；`check-inst-asm` 274/274；`check-case-ledger` rc=0；`check-tests-index` rc=0。
**修改文件**：
- `tests/inst/01-load-store/stm.t_rrri_rd.S`（1 行注释）
- `tests/inst/01-load-store/stm.t_rrri_rf.S`（1 行注释）
- `tests/inst/01-load-store/stm.w_rrri_rd.S`（1 行注释）
- `tests/data/inst-signature/inputs.sha256`（生成器 `--write` 重写 3 行 sha256）
- 本任务书
**验收结果**：
1. 三文件 `第 64 个元素` 命中 0；三处均为 `第 65 个元素（i=64）`，保留「未写 ⇒ 保持 MSTORE 模式」与模式常量。算术派生：0x100/4=64、0x080/2=64 ⇒ 第 65；63×宽 = 0xFC/0x7E 落在尾单元 0x0F8/0x078 未写半区（第 64 元素 i=63）。
2. `inputs.sha256` 仅 3 行变化（git diff）且 `sha256sum -c` 286/286 全过。
3. `expected.tsv`、`tests/case-ledger.tsv` 对 HEAD 无 diff（注释未移动行号/未改值）；槽数 HEAD/入库/`--data-only` 均 4576。
4. 三个镜像 `llvm-mc` 产物 md5 改动前基线/HEAD/现场三方相等：`1a96863f…` / `4d320fe3…` / `b64d6bc0…`。
5. `check-patch-tree` rc=2：34 problem = 32 gem5 + 2 musl（`arch/dadao/bits/signal.h`）的 assertion ⑥/⑨，均为在途组件源树/补丁集不一致（m16-gem5-025 独立树、m18-linux 串行改 musl）；本任务未触碰 `components/**`。
6. 证据脚本注入自检：旧注释 / sha 篡改 / expected 篡改 / 二进制追加四类均 FAIL，cp+md5 还原后回绿。
**新发现/坑**：
- `expected.tsv` 只含有检查点的 273 个镜像；零槽载体 `undi_reserved.S` 仅故障例，`--data-only` 仍报 274 镜像，勿混用口径。
- 纯注释改动不移动行号、不改宏展开值 ⇒ `expected.tsv` 不变；只有 `.S` 输入 sha256 变。
- 本次 `check-patch-tree` 34 problem = 32 gem5 + 2 musl（`signal.h`），均与 testcases 无关，判红须按组件段归因。
**遗留问题**：无（`check-patch-tree` 的 gem5 红由 m16-gem5-025 收口，不属本任务）。

## 审阅记录

#### 第 1 轮 engineer 自审

**判决**：无未修 finding；状态 = 待验收。

逐行审查：
- 三处注释：仅 `@@` 注释行变化，指令、点号、期望常量未动（`git diff` 逐行核对）；编号由 `off/width` 重算，非照抄。
- `inputs.sha256`：由 `check_inst_sig.py --write` 重写，未手改；3 行变化均对应三个 `.S` 的新 sha256，`sha256sum -c` 全绿。
- `expected.tsv`/`case-ledger.tsv`：对 HEAD 零 diff，符合「注释不改语义」预期。
- 二进制不变：llvm-mc 产物基线/HEAD/现场 md5 三方相等；注入追加数据后 md5 变化，证明比较非恒真。
- 证据脚本：断言直捕 rc、计数现场派生；注入用 cp 备份+md5 对账并带 EXIT trap 还原，未用 `git checkout/restore`。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| 初版把 expected.tsv 唯一镜像数（273）当载体数（274），误报 | ✅已修 | run.sh 分开「有检查点镜像」与「载体数」两个口径 | run.sh rc=0；同屏 `273=273`、`274/274` |
| 初版用 `grep __CHECK` 数有检查点镜像，漏宏展开（212≠273） | ✅已修 | 改用 `run_inst_tiny.scan_source` 独立扫描 | run.sh rc=0，打印「有检查点的载体=273」 |
| `check-patch-tree` rc=2 | ❌不修 | 未改 | 34 problem = 32 gem5 + 2 musl `signal.h`；本任务 diff 不含 `components/**` |

#### 第 1 轮 reviewer 验收

**判决**：**Accepted**（下列均为 reviewer 本人重跑，非采信工程师转述）

**重跑记录**（worktree 根执行，真实 rc）：
1. `grep "第 64 个元素"` 三个 `.S` ⇒ rc=1（0 命中）；`grep -c "第 65 个元素（i=64）"` 各=1；尾单元 `0x0F8`/`0x078` 的未写半区说明保留（`低 4 B/末 2 B 保持 MSTORE 模式` 行在）。`git diff --numstat` 三文件各 1+/1-，仅 `@@` 注释行，指令/点号/期望值未动。
2. `check_inst_sig.py --write` rc=0，`inputs.sha256` 生成前后 md5 同为 `4c2a9dbb…`（确系生成器产物、非手改）；`--data-only` rc=0（274 镜像 / 4576 槽）；`sha256sum -c` rc=0（286/286 OK）。
3. `make check-inst-asm` rc=0（274/274）；`check-case-ledger` rc=0（现场 5750 条）；`check-tests-index` rc=0（504 条）；`expected.tsv`/`case-ledger.tsv` 对 HEAD 零 diff；槽数 HEAD/入库/--data-only = 4576/4576/4576。
4. 三镜像 `llvm-mc` 产物 md5 三方相等（base/HEAD/现）：`1a96863f…`、`4d320fe3…`、`b64d6bc0…`。
5. `check-patch-tree` rc=2、`34 problem(s)` = 32 gem5（assertion ⑥/⑨）+ 2 musl `signal.h`（⑥/⑨）；本任务 diff 不含 `components/**` ⇒ 按「本任务未触碰组件补丁」披露，不阻断。

**证据脚本审核**：仓库根执行运行期证据目录内 `run.sh` ⇒ rc=0（26 PASS / 0 FAIL）；各断言直捕 rc、计数现场派生、注入用 cp+md5 且带 EXIT trap 还原，无恒真/两支同结果。

**独立注入**（reviewer 亲手改被测产物，`cp`+md5 还原，未用 `git checkout`）：
- 注入：`stm.w_rrri_rd.S` 注释改回「第 64 个元素」（备份 md5 `ff1b7ddb…`）⇒ 重跑同一 `run.sh` **rc=1**（`[FAIL] 第 64 个元素 期望=0 实际=1`、`--data-only rc=1`、`sha ok=285/286`）。
- 还原：`cp` 回、md5 `ff1b7ddb…` 相等 ⇒ 重跑 `run.sh` **rc=0**（ALL PASS）。
- `git status` 与开工快照逐行相同（恰 5 个允许文件）。

**约束核验**：变更集仅三个 `.S` + `inputs.sha256` + 本任务书；未碰 `expected.tsv`/`case-ledger.tsv`/`spec/`/契约/`components/**`/`Makefile`；未提交 git；未动 m16-gem5-025 与 m20-gem5-003。
**遗留**：`check-patch-tree` 组件红（32 gem5 + 2 musl）随在途任务收口，不属本任务。
