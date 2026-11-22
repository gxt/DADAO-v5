# m17-idl-016: spec 生成注记路径更新（263 块）

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-012`（生成器已迁 `idl/tools/idl_render.py`）
**可并行分片**：否
**预估**：30–60 min
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景

`m17-idl-012` 把生成器从 `idl/render.py` 迁到 `idl/tools/idl_render.py`，但 21 册 `spec/SimRISC-*` 的 263 个生成块首行仍写「由 `idl/render.py` 生成」——该路径已不存在，成为坏指针。012 故意未重渲染（避免本任务外的大 diff），本任务收尾。

## 要做

1. `idl/tools/idl_render.py` 的生成注记改为**不含具体路径**的稳定写法（如「本块由 IDL 源生成，禁手改；生成器见 `idl/tools/`」），避免以后再改名又要全量重渲染;
2. 用该工具重渲染 21 册（只更新 263 个块的首行注记，块内容与散文逐字节不变）；
3. 更新 `spec/.manifests.toml` 中受影响的册 sha256（按现场重算）；
4. `spec/README.md` 等若有 `idl/render.py` 旧引用，一并改成新路径（或泛指 `idl/tools/`）；
5. **不升版本号**、不改语义/散文/.idl 源。

## 不做

- 不改任何 operation 正文、不新开 spec 版本段；
- 不改 `spec/` 之外的语义/清单。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；
- 只动 `idl/tools/idl_render.py`、21 册 spec、`spec/.manifests.toml`、`spec/README.md`（如需）、本任务书；
- 完成区 ≤30 行、不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. `make check-idl-sync` rc=0（`idl-render: PASS … 263 块逐字节一致`）；
2. `make check-manifests-guard`、`check-spec-numbering`、`check-spec-changelog`、`check-spec-purity`、`check-spec-cite-targets` rc=0；
3. `grep -rn "idl/render\.py" spec/` 命中 **0**；
4. **diff 审计**：`git diff --numstat` 中每册增删行数 == 该册块数（只换注记行）+ sha 行；**块内容零变化**（可用 `idl_render.py --check` 前后对比或抽 3 册逐块比对）；
5. **可达 FAIL**：手改一个块的注记行 ⇒ `idl_render.py --check` rc≠0；`cp`+md5 还原后回绿。

## 完成区

**测试结果**：通过 6/6（运行期证据目录的 `run.sh` 一次跑通 rc=0）：① `make check-idl-sync` rc=0（263 条/12 册/263 块，认证块数与现场统计一致）；② `check-manifests-guard`、`check-spec-numbering`、`check-spec-changelog`、`check-spec-purity`、`check-spec-cite-targets` 全 rc=0；③ `grep -rn "idl/render\.py" spec/` 命中 0；④ diff 审计：12 册逐册 `增=删=该册块数`（合计 263/263），非注记变更行 0，逐块审计 263 个「注记之外逐字节相同」，散文哈希 13/13 一致，`spec/.manifests.toml` 14 增 14 删（= 12 册块 + 2 册散文，现场派生）；⑤ 注入 1 处注记字 ⇒ `--check` rc=1（`FAIL（1 册漂移/共 12 册）`），`cp`+md5 还原（md5 与备份相同、注入串 0 次、新注记 8 行）后 rc=0；⑥ `make check-idl` 272/272 rc=0。附加：`idl_render.py --self-test` 11/11 PASS；`check-spec-codeblocks`/`check-spec-refs`/`check-spec-drift` rc=0。负对照：把 ⑥ 期望改成 271 ⇒ 脚本 rc=1（证明断言非恒真）。

**修改文件**：`idl/tools/idl_render.py`（`GENERATED_NOTE` 改不含文件名的稳定串 + docstring 示例同步）、12 册 `spec/SimRISC-0[1-9]-*.md`/`SimRISC-1[0-2]-*.md` 的块首行注记（263 行）、`spec/.manifests.toml`（14 条 sha256 现场重算）、`spec/README.md` 与 `spec/IDL-ISA语义描述语言与语义库.md`（各 1 处旧路径 → `idl/tools/idl_render.py`）、本任务书。仅此 17 个文件，未升任何版本号。

**验收结果**：`git diff --numstat -- spec/` 逐册 38/17/8/33/6/15/50/21/21/21/5/28（= 各册块数），`.manifests.toml` 14/14，`spec/README.md` 1/1，语义册 1/1；`idl/tools/idl_render.py` +4/−3。新注记只写目录 `idl/tools/`、不含生成器文件名。

**新发现/坑**：① 265 处 = 263 块 + README 1 + 语义册 1（背景里的「README 与语言规范册的散文引用」共 2 处，已一并改）；② 任务 worktree 未预建 `.work`/`.dadao` 软链，`check-idl` 依赖其中 qemu/bootrom，本次手工软链到主工作树（两者已 ignore、不入 diff）；③ 仓库无「重算 manifest sha」工具，用一次性脚本按现场 sha256 改写清单行，事后由 `check-manifests-guard`（sha256 36 条全符）复核；④ 新注记故意只到目录级，后续生成器改名无需再重渲染。

**遗留问题**：无。

## 审阅记录

### 第 1 轮 engineer 自审

逐行核了 `idl/tools/idl_render.py` 两处 hunk（docstring 示例、`GENERATED_NOTE` 及其用途：`build_region` 用它插注记、`self_test.first_rendered_region` 用同一常量跳过注记行——同名引用，改一处即两处同步）、12 册渲染 diff、清单 sha、两册散文改动，以及证据脚本每条断言的可达 FAIL。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `run.sh` 的「注入后 git diff 非空」恒真（该册本就有未提交注记改动） | ✅已修 | 换成「注入串出现次数=1」「未改注记数 = 块数−1」，还原后反向（0 / 块数） | `run.out` §5：1 / 7，还原后 0 / 8 |
| 「散文 12/12」「manifests 14 行」写死 | ✅已修 | 期望值现场派生：册数循环计数、`PROSE_FILES` 由 `git grep HEAD` 取 | `run.out` §4c 打印 12+2=14；§4d 13/13（含 SimRISC-00） |
| 新注记若与旧串相同 ⇒ 注入/断言恒真 | ✅已修 | 脚本显式断言新≠旧、且新串不含 `idl/render.py` | `run.out` 头部三行打印 |
| 证据脚本自身能否 FAIL | ✅已修 | 负对照：期望 272→271 | `negctl.out`：`[FAIL] …期望=271 实际=272`，rc=1 |

判决：全部 finding 已修；门控全绿 ⇒ 状态置「待验收」。

### 第 1 轮 reviewer 复核

**重跑记录**（仓库根，reviewer 本人执行，非采信完成区）：
- 运行期证据目录内 `run.sh`：`rc=0`、`RESULT: PASS`，6 段检查全绿（263 块/12 册/散文 13/13/272/272）。
- `make check-idl-sync` rc=0，原文：`idl-render: PASS（源 operation=263 条 / 落点 12 册 / 标记块 263 个，逐字节一致）`。
- 5 门控各自 rc：`check-manifests-guard`=0、`check-spec-numbering`=0、`check-spec-changelog`=0、`check-spec-purity`=0、`check-spec-cite-targets`=0。
- `grep -rn "idl/render\.py" spec/` 0 命中（grep rc=1）；`make check-idl`：`check_four_way: 272/272` rc=0。

**约束核验**：
- 只动注记：`git diff -U0 spec/` 非注记变更行 32 = `.manifests.toml` 14 对 sha + 散文 2 对（README、语义册各 1 句仅路径词 `idl/render.py`→`idl/tools/idl_render.py`，word-diff 确认）；SimRISC 侧 +263/−263 全为注记行。
- 抽 3 册（07/01/12，含 50 块册）独立逐块比对 HEAD：id 集相同、注记之后逐字节相同、剔注记后整册相同。
- 注记文本：`GENERATED_NOTE` 只到目录 `idl/tools/`、不含文件名；12 册 `--check` 绿；diff 中版本号/日期 0 命中；SimRISC-00 未改。
- 自注入 1 路（07 册改一个注记字）：`idl_render.py --check` rc=1 `FAIL（1 册漂移）` → `cp` 还原 md5 一致 → rc=0；收尾 14/14 文件 md5 与注入前一致。
- 越界：`git status -uall` 恰 17 文件与完成区对账一致；无 `.idl`/`tests/`/`contracts/` 改动（唯一 .py 为任务书许可的 `idl/tools/idl_render.py`）。
- 负对照：复跑 `run_negctl.sh` rc=1，`[FAIL] 四方一致例数: 期望=271 实际=272` ⇒ 断言非恒真。

**finding 表**：

| # | finding | 级别 | 处置 |
|---|---|---|---|
| 1 | 无阻断项 | — | — |
| 2 | `run.sh` §4b 非注记行过滤按子串剔除注记，理论上可掩蔽「内含注记子串的其它改动」；实际由 §4d 全量 263 块逐字节 + 散文哈希独立覆盖，且 reviewer 已手工逐行核过全部 32 条非注记变更 | 观察 | 不阻断 |

**判决：Accepted**（验收命令块 reviewer 重跑全绿、约束无违反；状态未改，留 architect 终审）。
