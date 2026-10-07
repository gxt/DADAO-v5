# SPEC-119t: spec 目录保护：只读哈希锁 + 门控 + 流程约束

**模块**：spec
**项目里程碑**：M5
**依赖**：无（与改 `spec/` 的 `SPEC-114t`/`115t`/`116t` **串行**；建议先于 `SPEC-115t`/`116t` 下发——它们将改上游只读册、须用本门控的哈希锁）
**状态**：待开始

> **⚠️ 本任务改 `spec/` 已获用户授权（原话落盘）**：本任务**新建 `spec/Process-06-spec目录保护规范.md`** 并**登记 `spec/README.md`**——按新规则「**所有针对 spec 目录的修改，都应该经过我的允许，不能擅自进行**」，此两处 `spec/` 改动**经用户本轮裁定授权**（授权内容 = 落地本保护机制）。**除这两处外，不得改动任何既有 `spec/` 册正文。**

## 执行环境
**执行环境**：本地

## 接口规范

- **定位（问题根源）**：`SPEC-114t` 的 engineer **无授权擅自修改上游只读册** `spec/DADAO-12-SEE-主管系统运行环境.md`、`spec/DADAO-22-SBI-主管系统二进制接口.md`（各插入 2 行）。用户严厉指出并裁定新规则。本任务把「**不许擅自改 `spec/`**」从**口头纪律**落为**机械门控**（哈希锁 FAIL）+**三处固定检查**（下发预检 / reviewer 验收 / architect 提交），使违规在下发、验收、提交三个环节均可被拦截。
- **用户裁定（原话落盘，2026-10-07，经主会话转达——子会话问答对父会话不可见，`lessons §7.3`）**：
  1. **「DADAO-21 和 DADAO-22 都不应该做修改」**；
  2. **「所有针对 spec 目录的修改，都应该经过我的允许，不能擅自进行」**（⇒ 不止上游册：`spec/` 下**任何**新增/修改/删除均须用户**事先**明确允许，含 v5 自定册 `Machine-*`/`Process-*`/`spec/README.md`）；
  3. **上游只读册清单（用户全选）** = `DADAO-1x`（11/12/13）+ `DADAO-2x`（21/22/23）+ `SimRISC-00..12` + `Toolchain-01`——共 **20 册**（见下 §上游只读册清单）。
- **输入（自包含）**：
  - **上游只读册清单**（本文件 §上游只读册清单，20 册；含**当前** `sha256` 参考值）。
  - **复用范式（不另造轮子）**：`tools/infra/check_index_blobs.py`（manifest 驱动、逐项校验、`--verbose`、显式路径注入、只读、非零退出）；`tools/infra/check_dirs.py`（`--root` 覆盖，供**临时树注入**）。
  - `manifests/*.lock.toml`（既有锁文件体例）+ `tools/infra/manifest_check.py`；
  - `Makefile`（`check:` 目标链、`.PHONY`、`help`、各 `check-*` 目标体例，见 `Makefile:38-102`、`297`）；
  - `spec/README.md`（分册清单 / 投影表 / 规范修订流程体例）；`spec/Process-03-ADR编写规范.md`（判 ADR 判据）。

- **输出**：
  1. **`manifests/spec-readonly.lock.toml`（新建）**：上游只读册清单 + 逐册 `sha256` 锁。体例（对齐既有 `[[component]]` 体例）：
     ```toml
     format = 1
     # 上游只读册：sha256 锁。修改须用户事先明确允许（授权原话落盘），并在
     # 同一变更内更新此处哈希。见 spec/Process-06。
     policy = "readonly-requires-authorization"
     [[spec]]
     path = "spec/SimRISC-11-其它.md"
     group = "simrisc-00..12"          # 之一：simrisc-00..12 / dadao-1x / dadao-2x / toolchain-01
     sha256 = "f6de0860b78208356833449243b481ce942aefa891b2e77fa6c62a5d68111fe8"
     ```
     清单 = §上游只读册清单 的 **20 册**，逐一登记其**当前实测** `sha256`（下表值为架构师实测，engineer 须以 `sha256sum` 重算复核）。
  2. **`tools/infra/check_spec_readonly.py`（新建）**：读 `manifests/spec-readonly.lock.toml`，逐一重算 `spec/<path>` 的 `sha256`；**任一条不符即 FAIL（非零退出）**；文件缺失 ⇒ FAIL；`--verbose` 逐项打印 `OK`/`MISMATCH`（含 literal / computed）；支持 **`--root DIR`**（对**另一根目录**做检查，供临时树注入/自测，缺省=仓库根）；`--list` 可选。**只读**，不改任何文件。结构与 `check_index_blobs.py`/`check_dirs.py` 一致，**复用其范式**。
  3. **`Makefile`**：新增目标
     ```make
     # spec 目录只读锁 (SPEC-119t): 上游只读册 sha256 校验；失配 ⇒ FAIL（须先取用户授权并同步改锁）。
     check-spec-readonly:
     	@$(PYTHON) tools/infra/check_spec_readonly.py
     ```
     并**纳入 `check:` 目标链**（`Makefile:297`）、补 `.PHONY`（`Makefile:38-47`）与 `help`（`Makefile:82-102` 区）。
  4. **`spec/Process-06-spec目录保护规范.md`（新建，v5 自定流程规范）**——正文规则（**①–⑤，均 MUST**）：
     - **① 任务书「输出」不得把上游只读册列为可改对象**：对上游册只作**只读引用**（引其 `§` 章节号，不改一字）。
     - **② 任何 `spec/` 改动须用户事先明确允许**：`spec/` 目录下**任何新增/修改/删除**（含 v5 自定册 `Machine-*`/`Process-*`/`spec/README.md`）**须用户事先明确允许**，授权**原话落盘**；未获授权而拟改 `spec/` ⇒ **BLOCKED**。
     - **③ 下发前预检新增第 5 项**：`/dispatch` 前，把**拟改文件清单 × `spec/` 清单**逐一对照——命中 `spec/` 而无**用户授权原话** ⇒ **BLOCKED**（`AGENTS.md`「下发前预检」由 4 项扩为 **5 项**）。
     - **④ reviewer / architect 固定检查**：`reviewer` 验收与 `architect` 提交前，固定执行 `git diff --name-only`（提交前为 `git diff --cached --name-only`）与 `spec/` 清单交叉；**有交集而缺用户授权证据 ⇒ reviewer 判 `Needs Revision` / architect 拒绝提交**。
     - **⑤ 上游只读册哈希锁机制**：上游只读册以 `manifests/spec-readonly.lock.toml` 逐册 `sha256` 锁定，由 **`make check-spec-readonly`**（纳入 `make check`）校验；确需修改某只读册（**先经用户授权**）时，**同一变更**内须更新该册 `sha256` 锁 + 完成区记录授权原话；**未更新锁即改册 ⇒ 门控 FAIL**。
     - 规范等级：①②③④⑤ 均标 **MUST**。
  5. **`spec/README.md` 登记**：① 分册清单「**工程流程**」组新增 `Process-06-spec目录保护规范.md` 行；② **投影表**新增 `Process-06` 行（① `—`、② `—`、③ 机械门控 = `tools/infra/check_spec_readonly.py`〔`make check-spec-readonly`〕、④ `不适用（人工遵守）`）；③ 「**规范修订流程**」补一句「改 `spec/` 须**用户事先授权**（见 `Process-06`）」。
- **约束（硬）**：
  - **不立 ADR**：属**工程过程规范**（可逆、单项目、无外部契约），与 `Process-01…05` 体例一致（`Process-03` 判据不命中）。
  - **不改任何既有 `spec/` 册正文**：本任务只**新建** `spec/Process-06-…md` + **登记** `spec/README.md`（二者为**本任务授权范围**）；`DADAO-12`/`DADAO-22` 及其余 18 册**一字不改**。
  - 复用 `check_index_blobs.py`/`check_dirs.py` 范式，**不另造轮子**；门控**必须能失败**（注入反例见验收 2）。
  - 临时目录 `/tmp/opencode/SPEC-119t/`（**注入优先在临时树**，避免动真实 `spec/`）；失败即停、**禁自动重试**；**不提交 git**；复杂命令输出留存 `.work/log/spec/`（**禁 `tee`**）。
  - **重建成本申报**：不触发组件重建。

## 上游只读册清单（20 册；用户 2026-10-07 全选）

> `sha256` 为架构师**实测**（`sha256sum spec/<册>`，工作树 = 还原后基线）；engineer 须**重算复核**后再写入锁文件。

| # | 路径 | group | 实测 `sha256` |
|---|------|-------|---------------|
| 1 | `spec/SimRISC-00-指令系统设计.md` | simrisc-00..12 | `f7d7c7db7adbb07493dbb42f3b363a5a812e14bbe78f732ac5220a5a8c538158` |
| 2 | `spec/SimRISC-01-取数存数.md` | simrisc-00..12 | `08b76ba3047f01b86abbca30b56e84e8efcdd7c820578b17ffd7fb509ed72ce6` |
| 3 | `spec/SimRISC-02-寄存器复制.md` | simrisc-00..12 | `017faa19b7fb677ddbaca8ea226b444c0c8313e92f7e651c8406d0cc30454c7e` |
| 4 | `spec/SimRISC-03-16位立即数操作.md` | simrisc-00..12 | `030b788c1e46b467d134761ababeccd1d3f328aac37f3d7795b66e7715e66629` |
| 5 | `spec/SimRISC-04-64位数据运算.md` | simrisc-00..12 | `2d5767efa62be276f17bff78b19a0e3c08d77c7bbc7bdbdb2537f2aab112acc9` |
| 6 | `spec/SimRISC-05-64位地址运算.md` | simrisc-00..12 | `958223965a0ff4218930002538bf894806933171cd1aaf4b103a4a6fd552e297` |
| 7 | `spec/SimRISC-06-控制流.md` | simrisc-00..12 | `a82179a769f40e86234cfb3275f7d0341898866a28014ab4029d6ab773e25313` |
| 8 | `spec/SimRISC-07-浮点运算.md` | simrisc-00..12 | `2e215c2c5a15c739073603b616bcd2cb14997d343690f82cb8769029459767da` |
| 9 | `spec/SimRISC-08-32位数据运算.md` | simrisc-00..12 | `4bb00f033b9e69c5100ce21313a023cab793ffbb0be7ad42567f114f0f485a7c` |
| 10 | `spec/SimRISC-09-16位数据运算.md` | simrisc-00..12 | `da0f66d56af27dd906409bb4a2306df0c23da5251ee4d2a9eb6c242ad8b8b6da` |
| 11 | `spec/SimRISC-10-8位数据运算.md` | simrisc-00..12 | `ee41a25a2029942faf8df782c1b2a0cc00b4b0abe6a81117b41e8551b752fe4a` |
| 12 | `spec/SimRISC-11-其它.md` | simrisc-00..12 | `f6de0860b78208356833449243b481ce942aefa891b2e77fa6c62a5d68111fe8` |
| 13 | `spec/SimRISC-12-待定.md` | simrisc-00..12 | `c0b69b3935276506374fae2a2bf97410a497d40c0e7a3360620c4f0e0c6a39c2` |
| 14 | `spec/DADAO-11-AEE-应用程序运行环境.md` | dadao-1x | `9fc43f3b06906565e2763f3ec5cd30706e5960771abf5585faf17671bce0edd0` |
| 15 | `spec/DADAO-12-SEE-主管系统运行环境.md` | dadao-1x | `c0a5b598cb5b4c577003cb65b80d9325b801e5452b770b5ace3f11960c56a0c7` |
| 16 | `spec/DADAO-13-HEE-超管系统运行环境.md` | dadao-1x | `ed69fe3fb57c847ff24af20bba2cb81ad771b622963bec9c2300393425c7dba1` |
| 17 | `spec/DADAO-21-ABI-应用程序二进制接口.md` | dadao-2x | `672210cd0ba7d87f49b26b3a5148a56dc9b7616e19d7695420175b117a9a77e6` |
| 18 | `spec/DADAO-22-SBI-主管系统二进制接口.md` | dadao-2x | `e80a48a3074dbc22f0adc06a1ef342d7cb6def3bfac5e56ea8fc50a422608aad` |
| 19 | `spec/DADAO-23-HBI-超管系统二进制接口.md` | dadao-2x | `df4274184b72d7b4236728e9c5a6f078d590452b4747fbb1493c3f95f6b3905a` |
| 20 | `spec/Toolchain-01-汇编语言.md` | toolchain-01 | `d00c0925a0e2cf8d1a3bbbf2cbd46d380a8ce97a0ae77176d7449b0c012e1085` |

> **不改册的说明**：`spec/Machine-01-测试机运行环境.md`、`spec/Process-0x`、`spec/README.md` 为 **v5 自定册**，**不在**哈希锁清单内（其正当修订由 `②` 流程约束 + 授权原话把关）；哈希锁只覆盖**上游只读册**（其「不该被擅改」可由机械门控判定）。

## 验收标准

1. **锁文件**：`manifests/spec-readonly.lock.toml` 存在；`grep -c '^\[\[spec\]\]'` = **20**；20 条 `path` 与 §上游只读册清单 逐一相等（**无多、无漏**）；每条 `sha256` = 对应册 `sha256sum` 实测值（给真实 `sha256sum` 对照输出）。
2. **门控能失败（反例门控）**：`make check-spec-readonly` EXIT=0（真实输出）；**注入反例**——在**临时树**（`--root /tmp/opencode/SPEC-119t/inject/`，复制 `spec/` 与锁文件）改一册（改一行 / 删一册）⇒ 门控 **FAIL（非零退出）** ⇒ 还原临时树 ⇒ **回绿**（给注入→FAIL→还原→绿的真实输出与退出码）。**不得**在真实 `spec/` 上留改动。
3. **纳入 `make check`**：`Makefile` 的 `check:` 目标链含 `check-spec-readonly`（`grep` 证据）；`make check` EXIT=0（末段 `repository checks: PASS`）。
4. **流程规则落纸**：`spec/Process-06-spec目录保护规范.md` 存在，含 **①–⑤** 五条（`grep` 证据，逐条可定位）；`spec/README.md` 已登记（分册清单 + 投影表 + 修订流程各 1 处）。
5. **未越界**：`git diff --name-only -- spec/` **仅**含 `spec/Process-06-spec目录保护规范.md` + `spec/README.md`（给真实输出；**无任何上游只读册**）。
6. **一键证据脚本**：`.work/evidence/SPEC-119t/run.sh`——非交互、失败非零、逐项打印；**内置注入自检**（临时树改一册 ⇒ 断言 **FAIL** ⇒ 还原临时树 ⇒ 回绿），结尾用 `rc=$?; echo "EXIT=$rc"`，**禁 `tee`**；给真实输出。
7. **无残留**：`git status --untracked-files=all` 仅 `manifests/spec-readonly.lock.toml` + `tools/infra/check_spec_readonly.py` + `Makefile` + `spec/Process-06-spec目录保护规范.md` + `spec/README.md` + 本任务书。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证：审核 `run.sh` + 重跑 + **独立注入一次反例**〔临时树改一册 ⇒ FAIL ⇒ 还原回绿〕+ 逐条核 20 册清单完整/哈希一致 + 核 `spec/` 改动仅 Process-06/README + 判决）
