# INFRA-107t: 补 0.5.3 PROVENANCE 的组合 sha 与逐文件表

**模块**：infra
**项目里程碑**：M10
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地（纯文档，无构建）

## 接口规范

### 背景（ISS-333，实测 2026-10-25）
- `python3 tools/spec/gen_spec_archive.py --verify` rc=1，唯一失败项 = `SimRISC-0.5.3`（5 文件）：其 `PROVENANCE.md` 缺「版本组合 sha256」行与「逐文件 sha256」表；`0.5.4` / `0.5.5` 均 OK。
- `0.5.4` 的现成格式：`- 版本组合 sha256：\`<64 hex>\`` + `## 逐文件 sha256` 表。

### 输入
- `.tao/archive/SimRISC-0.5.3/PROVENANCE.md`（**只增不改**）
- `.tao/archive/SimRISC-0.5.4/PROVENANCE.md`（格式范例）
- `tools/spec/gen_spec_archive.py`（sha 计算口径真源；**不得自创公式**）

### 输出
- 在 0.5.3 `PROVENANCE.md` 追加：版本组合 sha256 行 + 逐文件 sha256 表（5 文件），数值按脚本口径/现场重算。
- 归档正文（5 个 `.md`）**不改**。

### 约束
- 遵守 `docs/Process-06 §8`（归档只增不改，不改归档文件本体）。
- 不改 `tools/spec/**`；若发现脚本口径缺陷，停下报告。

## 验收标准
1. `python3 tools/spec/gen_spec_archive.py --verify` rc=0（0.5.3 通过）。
2. `python3 tools/spec/check_spec_archive.py`（L1）rc=0。
3. `make check` rc=0。
4. 逐文件 sha 与现场重算一致（贴命令与输出）。
5. 完成区贴真实输出与退出码。

## 完成区

**测试结果**：5/5 通过（验收项 1 原不可达——见「新发现/坑」①，经用户裁定授权改脚本后 rc=0）。
证据脚本 `.work/evidence/INFRA-107t/run.sh` → `failed=0`，含 4 条 PROVENANCE 注入 + 1 条脚本注入（均真红→还原回绿、md5 对账）。

**修改文件**：
1. `.tao/archive/SimRISC-0.5.3/PROVENANCE.md`（+17 行，原 31 行字节不变：`head -31 | md5sum` = 备份 md5 `21dfbae9…`）
2. `tools/spec/gen_spec_archive.py`（+49/−0：`is_rc()`；`--verify` 跳过 `-rc` 打 `SKIP`；新增 `--self-test` 3 例；docstring 同步）
3. `.tao/knowledge/milestones.md`：L46 `INFRA-107t` 状态 `待开始`→`待验收`（`check-milestones-fresh` 硬要求，与任务书对账）
4. 新增证据（未跟踪）：`.work/evidence/INFRA-107t/{run.sh,checks.py}`；日志 `.work/log/infra/INFRA-107t-*.log`

**验收结果**（真实输出，日志见上）：
1. `python3 tools/spec/gen_spec_archive.py --verify` → **rc=0**：`OK   SimRISC-0.5.3（5 文件@清单快照）`、`SKIP SimRISC-0.5.5-rc（预发布 -rc：不纳入归档校验）`，无 FAIL 行。
2. `python3 tools/spec/check_spec_archive.py` → rc=0：`PASS（声明 7 个版本目录，磁盘 8 个，A3/A4 启用）`。
3. `make check`（L1）→ rc=0：`repository checks (L1): PASS`（42s，`INFRA-107t-make-check.log`）。
4. 逐文件 sha：`sha256sum SimRISC-*.md` 5 行与 PROVENANCE 表**逐行相等**（table==disk True）；组合 sha 由脚本 `composite()` 现场重算 = 声明 `955bc111…f23ba`。
5. `gen_spec_archive.py --self-test` → rc=0（3/3）；证据脚本 rc=0。

**用户裁定（原话，2026-10-25）**：「本任务内顺手改 gen_spec_archive.py」。

**新发现/坑**：
① 任务书「唯一失败 = 0.5.3」**已过时**：`8c1bbaa5`（2026-10-25 用户裁定）删了 `SimRISC-0.5.5-rc` 目录，`check_spec_archive.py` 已排除 `-rc`，`gen_spec_archive.py --verify` 当时**未同步** ⇒ 第二个 FAIL，验收项 1 无法达标。
② 格式陷阱：组合 sha 行必须放在 `## 逐文件 sha256` **标题之前**（正则要求标题后仅空行即代码块）；首版把 bullet 放标题下 ⇒ `PROVENANCE 缺「逐文件 sha256」表`。
③ 不可在 0.5.3 写「快照提交：`<sha>`」——`provenance_snapshot()` 会改锚为 `eb4eff43`（版本声明点）而失配；实测该函数返回 `None`（回落派生快照 `86fdcc8e…`）。
④ `--apply` **仍会**重建 `-rc` 目录（未授权改动，见遗留）；`docs/Process-06` §8 未列 `--self-test` 与 `-rc` 跳过。

**遗留问题**：
- `--apply` 与 `--verify` 对 `-rc` 口径不一致（verify 跳过、apply 会建）：需再裁定是否同步（本次用户只授权 `--verify`/`--list`/`--report`）。
- `docs/Process-06-spec目录保护规范.md:62` 未同步「`-rc` 不纳入归档校验」与 `--self-test`：建议随知识沉淀补一行。
- 归档正文 5 个 `.md`、`tools/spec/**` 其余文件**未改**；未提交 git（提交权归 architect）。

## 审阅记录

#### 第 1 轮 engineer 自审
逐行审查 `PROVENANCE.md` 追加段与 `gen_spec_archive.py` 改动：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 组合 sha 行置于 `## 逐文件 sha256` 标题下 ⇒ 脚本正则取不到表 | ✅已修 | 行序改为 bullet → 空行 → 标题 → 空行 → 代码块 | verify 中 `0.5.3` OK（首版为 FAIL「缺表」） |
| F2 自审疑「追加文本含『快照提交』字样会改锚」 | ❌不修（已排除） | 未加该字样 | `provenance_snapshot(0.5.3)=None`，verify 用派生快照 |
| F3 sha 值若手抄易错 | ✅已修 | 由 `gen.derive()`+`gen.composite()` 编程写入，非手填 | `sha256sum` 5/5 相等；C3/C4/C5 三路独立比对 |
| F4 `--verify` 跳过 `-rc` 缺反例证明（可能恒绿） | ✅已修 | 新增 `--self-test`（3 例，含非 -rc 必红支）+ 证据脚本临时停用跳过注入 | self-test 3/3；I-verify-skip：rc=1、`FAIL SimRISC-0.5.5-rc`、md5 复原 |
| F5 `--verify` 跳过 `-rc` 后，现存 `-rc` 目录内容不再校验 | ❌不修（符合裁定） | docstring 已写明「`-rc` 不纳入归档校验」 | 裁定源自 `8c1bbaa5`（用户 2026-10-25） |
| F6 self_test 用 lambda+`noqa`（无 lint 也带噪声） | ✅已修 | 改为内嵌 `def fake()` | `--self-test` 仍 rc=0 |
| F7 `--apply` 仍可建 `-rc` 目录（口径不一致） | ⏸延后 | 未改（未授权） | 已登记「遗留问题」 |
| F8 任务书状态 / 完成区与真实输出对账 | ✅已修 | 状态改 `待验收`，逐条贴命令与 rc | 见「验收结果」 |

判决：findings 除 F5（裁定内）/F7（未授权，已登记）外全部已修，可标 `待验收`。

#### 第 1 轮 reviewer 验收

**独立重跑（reviewer 前台跑完，日志 `.work/log/infra/INFRA-107t-reviewer-*.log`；不采信 engineer 日志）**

| 命令 | rc | 我方真实输出关键行 |
|---|---|---|
| `python3 tools/spec/gen_spec_archive.py --verify` | 0 | `OK   SimRISC-0.5.3（5 文件@清单快照）`、`SKIP SimRISC-0.5.5-rc`，无 FAIL |
| `python3 tools/spec/gen_spec_archive.py --self-test` | 0 | 3/3 PASS（case1 rc=0 SKIP / case2 rc=1 FAIL / case3 rc=1 FAIL） |
| `python3 tools/spec/check_spec_archive.py` | 0 | `PASS（声明 7 个版本目录，磁盘 8 个，A3/A4 启用）` |
| `make check`（L1） | 0 | `repository checks (L1): PASS`（42s） |
| `bash .work/evidence/INFRA-107t/run.sh` | 0 | `failed=0`，C1-C11+I×5+R×2 全 PASS |

**独立数据复核（自写 hashlib / sha256sum，不复用脚本正则）**
- 表 vs 现场 `sha256sum`：5/5 逐行全等；表 vs 快照 `86fdcc8e` 平铺 blob：5/5 全等；归档正文 vs 快照 blob：5/5 全等（搬运未改内容）。
- 组合 sha：声明 `955bc111…f23ba` == 我方重算 == `sha256sum|sha256sum` shell 口径 == `--list` 清单值（四路一致）。
- 只增不改：HEAD~1 原 31 行 md5 `21dfbae9…` == 现 `head -31` md5；`git diff` 纯追加 +17 行、无 `-` 行。

**独立反例（`cp` 备份 + md5 还原，禁 git checkout/restore；A/B/C 三组）**
- A 组合 sha 改 1 位 → `FAIL SimRISC-0.5.3` rc=1 → 还原 md5 `b0cbfeae…` 一致 → 回绿 rc=0。
- B 表 SimRISC-01 行 sha 改 1 位 → `FAIL 0.5.3`（表≠快照 + 组合不符）rc=1 → 还原回绿 rc=0。
- C 停用脚本 `-rc` 跳过 → `FAIL SimRISC-0.5.5-rc（目录缺失）` rc=1，且 self-test case1 同步变红（证明 `-rc` 分支非恒真）→ 还原 md5 `328430d1…` 一致 → verify+self-test 均回绿。
- 三次注入后 `git status` 干净、md5 与基线逐一对账一致，无残留。

**约束核验**：归档正文 5 个 `.md` 未改（sha 与快照全等、时间戳仍 Sep 9）；`tools/spec` 仅改 `gen_spec_archive.py`（+49/0 纯追加：`is_rc` + `--verify` SKIP + `--self-test` + docstring），在用户裁定「本任务内顺手改 gen_spec_archive.py」范围内；`--list`/`--report` 仍列 0.5.5-rc（无回归）；milestones 仅 L46 状态；工作树无越界文件（`.work/*` 为 gitignored 未跟踪）。

**finding（非阻断，文档级数字笔误）**
- F-R1 完成区「修改文件」第 2 条写脚本「+46/−3」，实测 `git diff --numstat` = **+49/−0**（纯追加）。不影响代码行为/门控/退出码，请 architect 收尾改。
- 观察（engineer 已登记遗留，符合授权）：`--apply` 仍会重建 `-rc` 目录；`docs/Process-06 §8` 未同步 `-rc` 跳过与 `--self-test`。

**判决：Accepted**（5 项验收标准在我方独立重跑下全通过；数据四路交叉一致；三组独立反例真红→还原→回绿；仅 1 条文档级数字笔误交 architect 收尾修）。
