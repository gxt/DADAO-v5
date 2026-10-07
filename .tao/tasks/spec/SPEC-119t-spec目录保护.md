# SPEC-119t: spec 目录保护：只读哈希锁 + 门控 + 流程约束

**模块**：spec
**项目里程碑**：M5
**依赖**：无（与改 `spec/` 的 `SPEC-114t`/`115t`/`116t` **串行**；建议先于 `SPEC-115t`/`116t` 下发——它们将改上游只读册、须用本门控的哈希锁）
**状态**：已验证

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

**测试结果**：通过 **7/7** 验收项；`make check` **EXIT=0**（末段 `repository checks: PASS`）；门控 `make check-spec-readonly` **EXIT=0**（20 册 OK）；反例门控（改册 / 删册 / 锁残缺 3 类注入）均 **FAIL（rc=1）** 且 `cp`+md5 还原后回绿；一键证据脚本 `.work/evidence/SPEC-119t/run.sh` **EXIT=0**（37 `[PASS]`；另 1 行为 harness 自检**故意**触发的 `[FAIL]`，随即证明 `fail()` 可达，不影响最终结果）。

**修改文件**（与 `git status --porcelain -uall` 一致，见验收 7）：
- `manifests/spec-readonly.lock.toml`（新建）：20 册上游只读册 `sha256` 锁（用户 2026-10-07 全选）。
- `tools/infra/check_spec_readonly.py`（新建）：读锁逐册重算 `sha256`，不符/缺失/锁残缺 ⇒ 非零退出；支持 `--root` / `--verbose` / `--list`；**只读**。
- `Makefile`：新增 `check-spec-readonly` 目标 + `.PHONY` + `help`，并**纳入 `check:` 链**。
- `spec/Process-06-spec目录保护规范.md`（新建，**本任务授权范围**）：①–⑤ 均 MUST。
- `spec/README.md`（**本任务授权范围**）：登记 `Process-06`（分册清单 + 投影表 + 修订流程各 1 处）。
- `.tao/tasks/spec/SPEC-119t-spec目录保护.md`：状态 → `待验收` + 本完成区。

**验收结果**（真实输出/rc）：

**验收 1 — 锁文件 + 20 册清单无多漏 + 逐册 sha256 对照**：
```
$ grep -c '^\[\[spec\]\]' manifests/spec-readonly.lock.toml
20
$ sha256sum <20 册>              # 实测（与锁逐条相等）
f7d7c7db7adbb07493dbb42f3b363a5a812e14bbe78f732ac5220a5a8c538158  spec/SimRISC-00-指令系统设计.md
08b76ba3047f01b86abbca30b56e84e8efcdd7c820578b17ffd7fb509ed72ce6  spec/SimRISC-01-取数存数.md
017faa19b7fb677ddbaca8ea226b444c0c8313e92f7e651c8406d0cc30454c7e  spec/SimRISC-02-寄存器复制.md
030b788c1e46b467d134761ababeccd1d3f328aac37f3d7795b66e7715e66629  spec/SimRISC-03-16位立即数操作.md
2d5767efa62be276f17bff78b19a0e3c08d77c7bbc7bdbdb2537f2aab112acc9  spec/SimRISC-04-64位数据运算.md
958223965a0ff4218930002538bf894806933171cd1aaf4b103a4a6fd552e297  spec/SimRISC-05-64位地址运算.md
a82179a769f40e86234cfb3275f7d0341898866a28014ab4029d6ab773e25313  spec/SimRISC-06-控制流.md
2e215c2c5a15c739073603b616bcd2cb14997d343690f82cb8769029459767da  spec/SimRISC-07-浮点运算.md
4bb00f033b9e69c5100ce21313a023cab793ffbb0be7ad42567f114f0f485a7c  spec/SimRISC-08-32位数据运算.md
da0f66d56af27dd906409bb4a2306df0c23da5251ee4d2a9eb6c242ad8b8b6da  spec/SimRISC-09-16位数据运算.md
ee41a25a2029942faf8df782c1b2a0cc00b4b0abe6a81117b41e8551b752fe4a  spec/SimRISC-10-8位数据运算.md
f6de0860b78208356833449243b481ce942aefa891b2e77fa6c62a5d68111fe8  spec/SimRISC-11-其它.md
c0b69b3935276506374fae2a2bf97410a497d40c0e7a3360620c4f0e0c6a39c2  spec/SimRISC-12-待定.md
9fc43f3b06906565e2763f3ec5cd30706e5960771abf5585faf17671bce0edd0  spec/DADAO-11-AEE-应用程序运行环境.md
c0a5b598cb5b4c577003cb65b80d9325b801e5452b770b5ace3f11960c56a0c7  spec/DADAO-12-SEE-主管系统运行环境.md
ed69fe3fb57c847ff24af20bba2cb81ad771b622963bec9c2300393425c7dba1  spec/DADAO-13-HEE-超管系统运行环境.md
672210cd0ba7d87f49b26b3a5148a56dc9b7616e19d7695420175b117a9a77e6  spec/DADAO-21-ABI-应用程序二进制接口.md
e80a48a3074dbc22f0adc06a1ef342d7cb6def3bfac5e56ea8fc50a422608aad  spec/DADAO-22-SBI-主管系统二进制接口.md
df4274184b72d7b4236728e9c5a6f078d590452b4747fbb1493c3f95f6b3905a  spec/DADAO-23-HBI-超管系统二进制接口.md
d00c0925a0e2cf8d1a3bbbf2cbd46d380a8ce97a0ae77176d7449b0c012e1085  spec/Toolchain-01-汇编语言.md
[PASS] 锁内 20 条 path == 期望清单（无多漏） | expected=20册 actual=20册
[PASS] 20 册 sha256 全部与实测相等 | expected=0 mismatch actual=0 mismatch
```

**验收 2 — 门控能失败（反例门控）+ 临时树注入自检**：
```
$ make check-spec-readonly
check-spec-readonly: 20 upstream read-only spec volume(s) OK          # EXIT=0
--- 注入 A：临时树改一册（SimRISC-11 追加一行）---
[PASS] 注入A有效性(md5变化) | expected=differs actual=differs
check-spec-readonly: MISMATCH spec/SimRISC-11-其它.md: expected=f6de0860…11fe8 actual=50a37385…b1f14 (…see Process-06 §5)
check-spec-readonly: FAIL (1/20 volume(s) mismatched or missing)
[PASS] 注入A后门控 FAIL(rc!=0) | expected=rc!=0 actual=rc=1
[PASS] 还原A md5 对账(==注入前) | expected=fd4abccdc09dd4c3620930f213f551c1 actual=fd4abccdc09dd4c3620930f213f551c1
[PASS] 还原A后门控回绿 rc | expected=0 actual=0
--- 注入 B：临时树删一册（SimRISC-12）---
check-spec-readonly: MISSING spec/SimRISC-12-待定.md: expected file not found under /tmp/opencode/SPEC-119t/inject
check-spec-readonly: FAIL (1/20 volume(s) mismatched or missing)
[PASS] 注入B(缺失册)后门控 FAIL(rc!=0) | expected=rc!=0 actual=rc=1
[PASS] 还原B后门控回绿 rc | expected=0 actual=0
--- 注入 C：临时树锁残缺（删一条 sha256）---
check-spec-readonly: manifests/spec-readonly.lock.toml: [[spec]] #1 (spec/SimRISC-00-指令系统设计.md) missing 'sha256'
check-spec-readonly: FAIL (1 lock error(s))
[PASS] 注入C(锁残缺)后门控 FAIL(rc!=0, fail-closed) | expected=rc!=0 actual=rc=1
[PASS] 还原C后门控回绿 rc | expected=0 actual=0
[PASS] 真实 spec/ 20 册 md5 前后不变 | expected=unchanged actual=unchanged
```
（注入/还原均在**临时树** `--root /tmp/opencode/SPEC-119t/inject/` 进行，真实 `spec/` 未改动；还原一律 `cp`+md5 对账。）

**验收 3 — 纳入 `make check`**：
```
$ grep -n 'check-spec-readonly' Makefile
298:check: manifest-check … check-no-residue check-spec-readonly check-lit
$ make check
check_issues: 34 open, 0 closed (0 blocking M1-gate: 0)
repository checks: PASS                                            # EXIT=0
[PASS] check: 链接含 check-spec-readonly | expected=contains actual=contains
[PASS] make check rc | expected=0 actual=0
```

**验收 4 — 流程规则落纸**：
```
$ grep -cE '^## [1-5]\. ' spec/Process-06-spec目录保护规范.md
5
[PASS] Process-06 含 ①–⑤ 五节(## 1..5) | expected=5 actual=5
[PASS] Process-06 关键语 ①只读引用 / ②事先 / ②授权原话 / ②BLOCKED / ③第 5 项 / ④Needs Revision / ⑤spec-readonly.lock.toml / ⑤check-spec-readonly → 全 present
[PASS] README 分册清单登记 / README 投影表登记 / README 修订流程提及授权 → 全 present
```

**验收 5 — 未越界（`spec/` 改动仅 Process-06 + README.md）**：
```
$ git diff --name-only -- spec/
spec/README.md
$ git status -uall -- spec/
spec/README.md
spec/Process-06-spec目录保护规范.md
[PASS] spec/ 变更集合 == {Process-06, README.md} | expected=2项 actual=2项
[PASS] 变更集合不含任何上游只读册 | expected=0 actual=0
```
（`Process-06` 为**新建 untracked**，不出现在 `git diff`，由 `git status -uall` 呈列；集合 = tracked diff ∪ untracked。）

**验收 6 — 一键证据脚本**：`bash .work/evidence/SPEC-119t/run.sh` → 37 `[PASS]` + 1 故意 `[FAIL]`（harness 自检）→ `结果：PASS` / `EXIT=0`（完整输出 `.work/log/spec/SPEC-119t-evidence.log`）。

**验收 7 — 无残留**：
```
$ git status --porcelain -uall
 M .tao/tasks/spec/SPEC-119t-spec目录保护.md
 M Makefile
 M spec/README.md
?? manifests/spec-readonly.lock.toml
?? spec/Process-06-spec目录保护规范.md
?? tools/infra/check_spec_readonly.py
[PASS] git status -uall 集合 == 预期 6 项 | expected=6项 actual=6项
```

**新发现/坑**：
- **门控 fail-open 陷阱（自审发现并当场修复）**：`check_spec_readonly.py` 初版以 `if mismatches:` 决定退出码——当锁**残缺**（某条缺 `sha256`）时虽记入 error 但 `mismatches==0` ⇒ 返回 0（fail-open）。已改为 `if errors:` 判定（**任何**锁错误/文件不符/缺失均非零退出），并加**注入 C**（锁残缺）验证其 FAIL。
- `grep -qF '\[`…`\]…'` 中 `\[` 在 `-F` 下是**字面反斜杠**，致 README 分册清单断言**假 FAIL**；去掉转义后 PASS。
- git 默认 `core.quotePath=true` 把非 ASCII 路径转义为 `"…\347…"`，集合比较**假 FAIL**；改用 `git -c core.quotePath=false` + `cut -c4-`。
- **新建文件（untracked）不出现在 `git diff`**：验收 5/7 的「变更集」须用 `git status --porcelain -uall`（或 tracked diff ∪ untracked 并集）。
- 证据脚本 harness 自检**故意**打印一行 `[FAIL] harness-self-test` 以证明 `fail()` 可达（随即计入并回撤），最终结果仍 PASS——reviewer 勿误读。
- **建议沉淀知识库**：① `make check` 现已含 `check-spec-readonly`（spec 只读锁门控）；② 「TOML `[[spec]]` 锁 + `--root` + fail-closed（`if errors`）」范式可复用于其它只读清单门控；③ 门控类任务的「变更集」定义 = tracked diff ∪ untracked。

**遗留问题**：无（3 条自审 finding 均已修并复验；3 类反例注入均证门控可失败且已还原回绿）。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：`manifests/spec-readonly.lock.toml`、`tools/infra/check_spec_readonly.py`、`Makefile`、`spec/Process-06-spec目录保护规范.md`、`spec/README.md`、`.work/evidence/SPEC-119t/run.sh`。

**逐行审查意见**：
1. **`check_spec_readonly.py` 退出码 fail-open（严重）**：`if mismatches:` 使「锁残缺但无文件失配」时返回 0；应 `if errors:`（fail-closed）。
2. `grep -qF` 转义缺陷（见上「新发现/坑」），断言假 FAIL。
3. git 非 ASCII 路径转义致集合比较假 FAIL。
4. 证据脚本 harness 自检产生字面 `[FAIL]` 行——非缺陷，但需文档说明以免误读。
5. 锁文件 20 条 `sha256` 与 `sha256sum` 实测逐条相等；无多、无漏；`--root` 模式读 `<root>/manifests/spec-readonly.lock.toml`，符合验收 2 的临时树复制方式。
6. `spec/` 改动仅 2 处（Process-06 新建 + README 登记），无上游册改动；未立 ADR（属工程过程规范）。

**finding 处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 1 退出码 fail-open | ✅已修 | `check_spec_readonly.py`：`if mismatches:` → `if errors:`；`--list` 亦先判 errors | 注入 C（锁残缺）rc=1；正常 rc=0；`--list` 正常 rc=0 |
| 2 `grep -F` 转义 | ✅已修 | `run.sh` 去掉 `\[`/`\]` 转义 | `[PASS] README 分册清单登记` |
| 3 git 路径转义 | ✅已修 | `run.sh` 用 `git -c core.quotePath=false` + `cut -c4-` | `[PASS] spec/ 变更集合 == {…}`、`[PASS] git status -uall 集合 == 预期 6 项` |
| 4 harness 自检 `[FAIL]` | ✅已修（说明） | `run.sh` 增注释行说明其为故意触发 | 末尾 `结果：PASS` / `EXIT=0` |
| 5 锁/`--root` 正确性 | ❌不修（无缺陷） | — | 验收 1/2 输出 |
| 6 `spec/` 改动仅 2 处、不立 ADR | ❌不修（无缺陷） | — | 验收 5 输出；`Process-06 §7` |

**判决**：所有 finding 已处置；门控 fail-closed 已证；反例注入 3 类均 FAIL 并还原回绿；无遗留。**状态置 `待验收`**。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（mimo-v2.5-pro）
**审查时间**：2026-10-07
**审查范围**：`manifests/spec-readonly.lock.toml`、`tools/infra/check_spec_readonly.py`、`Makefile`、`spec/Process-06-spec目录保护规范.md`、`spec/README.md`、`.work/evidence/SPEC-119t/run.sh`、commit `c959da9`

---

**验收 1 — 证据脚本 `run.sh` 审核**：

脚本结构合理：
- `set -u` 启用未定义变量检查
- `fail()` 函数计数 `FAILURES`，`pass()`/`eq()` 断言可达 FAIL 路径（非恒真）
- 注入 A/B/C 均在临时树 `/tmp/opencode/SPEC-119t/inject/` 操作，用 `cp`+md5 还原（**未用** `git checkout/restore/stash`）
- 结尾 `echo "EXIT=$rc"; exit "$rc"`（**未用 `tee`**）
- harness 自检故意触发 `[FAIL]` 证明 `fail()` 可达，随即回撤计数

**唯一问题**：验收 5（spec/ 变更集合）和验收 7（git status 集合）在**已提交**工作树上会返回空——脚本假设未提交状态。但 architect 已 WIP 提交 `c959da9`，`git status`/`git diff` 自然为空。内容本身正确（我用 `git diff 3e512c8..c959da9` 独立验证，见下）。**不影响判决**。

**验收 2 — 重跑证据脚本**：
```
$ bash .work/evidence/SPEC-119t/run.sh 2>&1
...（37 [PASS] + 2 [FAIL]（验收 5/7 因已提交）+ 1 故意 [FAIL] harness 自检）...
结果：FAIL（2 项失败）
EXIT=1
```
验收 5/7 的 FAIL 原因：architect WIP 提交后 `git status` 干净。**用 `git diff --name-only 3e512c8..c959da9` 独立验证 spec/ 改动**：
```
$ git diff --name-only 3e512c8..c959da9 -- spec/
spec/Process-06-spec目录保护规范.md
spec/README.md
```
仅 2 项，无上游只读册。✓

**验收 3 — 独立注入（3 项，reviewer 自行执行，非 engineer 的 A/B/C）**：

注入在临时树 `/tmp/opencode/SPEC-119t-review/` 进行，**未动真实 `spec/`**。

**注入 D — 改一册（DADAO-11 追加一行）**：
```
$ python3 tools/infra/check_spec_readonly.py --root /tmp/opencode/SPEC-119t-review 2>&1
check-spec-readonly: MISMATCH spec/DADAO-11-AEE-应用程序运行环境.md: expected=9fc43f3b… actual=7544c8d9…
check-spec-readonly: FAIL (1/20 volume(s) mismatched or missing)
EXIT=1
```
还原后（md5 对账一致）→ `EXIT=0`。✓

**注入 E — 改锁文件 sha256 值（SimRISC-00 首位 'f'→'0'）**：
```
$ python3 tools/infra/check_spec_readonly.py --root /tmp/opencode/SPEC-119t-review 2>&1
check-spec-readonly: MISMATCH spec/SimRISC-00-指令系统设计.md: expected=07d7c7db… actual=f7d7c7db…
check-spec-readonly: FAIL (1/20 volume(s) mismatched or missing)
EXIT=1
```
还原后（md5 对账一致）→ `EXIT=0`。✓

**注入 F — 锁文件缺 `format` 字段**：
```
$ python3 tools/infra/check_spec_readonly.py --root /tmp/opencode/SPEC-119t-review 2>&1
check-spec-readonly: manifests/spec-readonly.lock.toml: unsupported format None (expected 1)
check-spec-readonly: FAIL (1 lock error(s))
EXIT=1
```
还原后 → `EXIT=0`。✓

**注入 G — 锁文件 `[[spec]]` 条目为空**：
```
$ python3 tools/infra/check_spec_readonly.py --root /tmp/opencode/SPEC-119t-review 2>&1
check-spec-readonly: manifests/spec-readonly.lock.toml: no [[spec]] entries
check-spec-readonly: FAIL (1 lock error(s))
EXIT=1
```
还原后 → `EXIT=0`。✓

**注入前快照**：
```
$ md5sum /tmp/opencode/SPEC-119t-review/manifests/spec-readonly.lock.toml
0f42f8563ba42bb2ce170b54650bec59  .../spec-readonly.lock.toml
```
注入 E 后还原 md5 = `0f42f8563ba42bb2ce170b54650bec59`（一致）。✓

**验收 4 — 锁文件正确性（独立重算 sha256）**：

20 册 `sha256sum` 独立实测输出：
```
f7d7c7db...  spec/SimRISC-00-指令系统设计.md
08b76ba3...  spec/SimRISC-01-取数存数.md
017faa19...  spec/SimRISC-02-寄存器复制.md
030b788c...  spec/SimRISC-03-16位立即数操作.md
2d5767ef...  spec/SimRISC-04-64位数据运算.md
95822396...  spec/SimRISC-05-64位地址运算.md
a82179a7...  spec/SimRISC-06-控制流.md
2e215c2c...  spec/SimRISC-07-浮点运算.md
4bb00f03...  spec/SimRISC-08-32位数据运算.md
da0f66d5...  spec/SimRISC-09-16位数据运算.md
ee41a25a...  spec/SimRISC-10-8位数据运算.md
f6de0860...  spec/SimRISC-11-其它.md
c0b69b39...  spec/SimRISC-12-待定.md
9fc43f3b...  spec/DADAO-11-AEE-应用程序运行环境.md
c0a5b598...  spec/DADAO-12-SEE-主管系统运行环境.md
ed69fe3f...  spec/DADAO-13-HEE-超管系统运行环境.md
672210cd...  spec/DADAO-21-ABI-应用程序二进制接口.md
e80a48a3...  spec/DADAO-22-SBI-主管系统二进制接口.md
df427418...  spec/DADAO-23-HBI-超管系统二进制接口.md
d00c0925...  spec/Toolchain-01-汇编语言.md
```
**逐条与锁文件 sha256 值比对：20/20 全部相等**。✓

路径清单 `grep -c '^\[\[spec\]\]'` = **20**；排序后 20 条 path 与用户清单逐一相符（DADAO-1x 3 + DADAO-2x 3 + SimRISC-00..12 13 + Toolchain-01 1 = 20），无多无漏。✓

**验收 5 — 门控纳入**：
```
$ grep -n 'check-spec-readonly' Makefile
298:check: ... check-spec-readonly check-lit
356:check-spec-readonly:
```
`make check` → `repository checks: PASS` → `EXIT=0`。✓

**验收 6 — 授权范围**：
```
$ git diff --name-only 3e512c8..c959da9 -- spec/
spec/Process-06-spec目录保护规范.md
spec/README.md
```
仅 2 项，无上游只读册。✓

`spec/Process-06-spec目录保护规范.md` 含 `## 1.`–`## 5.` 五节（grep `-cE '^## [1-5]\. '` = 5），①只读引用 / ②事先授权 / ②BLOCKED / ③第 5 项 / ④Needs Revision / ⑤spec-readonly.lock.toml / ⑤check-spec-readonly — 全 present。✓

`spec/README.md` 登记 3 处：分册清单 L74 + 投影表 L97 + 修订流程 L121。✓

**验收 7 — fail-closed 复核**：

| 注入 | 场景 | 退出码 | 结论 |
|------|------|--------|------|
| F | 锁文件缺 `format` 字段 | 1 | fail-closed ✓ |
| G | 锁文件 `[[spec]]` 为空 | 1 | fail-closed ✓ |
| C（engineer） | 锁文件删一条 sha256 | 1 | fail-closed ✓ |
| E（reviewer） | 锁文件 sha256 值改错 | 1 | fail-closed ✓ |

**验收 8 — 未越界**：
```
$ git show c959da9 --stat
.tao/tasks/spec/SPEC-119t-spec目录保护.md
Makefile
manifests/spec-readonly.lock.toml
spec/Process-06-spec目录保护规范.md
spec/README.md
tools/infra/check_spec_readonly.py
```
6 项，无 `components/`、`contracts/` 外越界。✓

---

**判决：Accepted**

- 验收 1–8 全部通过（证据脚本验收 5/7 因已 WIP 提交导致 `git status` 干净，但用 `git diff 3e512c8..c959da9` 独立验证内容正确）
- 20 册 sha256 独立重算全部与锁文件一致
- 4 项独立注入（改册 / 改锁 sha256 / 锁缺 format / 锁空条目）均 FAIL（rc=1）且还原回绿（rc=0）
- fail-closed 已证（`if errors:` 判定）
- spec/ 改动仅 Process-06 + README，无上游册
- commit `c959da9` 6 项，无越界

#### 第 1 轮 architect 提交（WIP）

- **档位**：reviewer **尚未验收**（任务书 `**状态**` = `待验收`）⇒ **`WIP:` 提交**。
- **提交信息**：`WIP: SPEC-119t spec 目录保护（哈希锁 + 门控 + Process-06）（待 reviewer 验收）`。
- **staging**：显式逐路径 `git add`（**未用** `git add -A`），共 6 项。
- **对账**（`git diff --cached --name-only` vs 完成区「修改文件」声明 + 任务范围）：**完全一致，无漏提 / 多提**——`manifests/spec-readonly.lock.toml`（新建）、`tools/infra/check_spec_readonly.py`（新建）、`spec/Process-06-spec目录保护规范.md`（新建）、`Makefile`、`spec/README.md`、`.tao/tasks/spec/SPEC-119t-spec目录保护.md`。
- **授权范围核对**（`git diff --cached --name-only -- spec/` 真实输出）：仅 `spec/Process-06-spec目录保护规范.md`（新建）+ `spec/README.md`（修改）——与本任务书顶部用户授权范围内**一致**；**无任何上游只读册**（20 册一字未现）。
- **未 push**（architect 只 commit）。

#### 第 1 轮 architect 提交（正常）

- **档位**：**正常**（reviewer 判 `Accepted` ⇒ 验收完成，**不加 `WIP:`**）。
- **文件集对账**（显式 staging，**未用** `git add -A`）：`git diff --cached --name-only` 与完成区「修改文件」声明 + 本任务范围对账 —— 6 项交付已在 WIP 提交中；本次收尾追加：本任务书（追加本记录）、`.tao/knowledge/changelog.md`、`.tao/knowledge/milestones.md`、`.tao/knowledge/MEMORY.md`、`.tao/knowledge/lessons.md`、`.tao/knowledge/feedback_005-spec目录改动须用户事先授权.md`；**无漏提 / 无多提 / 无越界**（未卷入 `spec/`、`components/`、`contracts/`、其它任务书；`.work/**` gitignored 不入库）。
- **授权范围核对**：`git diff --cached --name-only -- spec/` **为空**（本任务 `spec/` 改动均已在 WIP 提交内，且仅 `Process-06`（新建）+ `README.md`，无上游只读册）。
- **提交信息**：`SPEC-119t spec 目录保护（哈希锁 + 门控 + Process-06）（reviewer Accepted）`；**只 commit，未 push**。

#### 主会话统一验收报告（`/complete`，2026-10-07）

- **reviewer**：`Accepted`。重跑证据脚本（37 PASS）；**4 项独立注入**（D 改上游册 / E 改锁内 sha256 值 / F 锁缺 `format` / G 锁空 `[[spec]]`）⇒ 各触发**不同** FAIL 路径、**均非零退出** ⇒ 临时树 `cp`+md5 还原 ⇒ 回绿；**锁内 20 册 sha256 由 reviewer 独立重算，全部相等**。
- **architect 交叉复核**：**维持 `Accepted`**。独立重算：20 条 path 与用户清单（`DADAO-1x`3+`DADAO-2x`3+`SimRISC-00..12`13+`Toolchain-01`）**无多无漏**；逐册 sha256 **0 mismatch**；`check:`（`Makefile:298`）确含 `check-spec-readonly`；自建临时树注入 H/I/J（删字段 / 改册内容 / 清空条目）**均 EXIT=1**，证 **fail-closed**。
- **授权范围**：`git diff --name-only 3e512c8..c959da9 -- spec/` = **仅** `spec/Process-06-spec目录保护规范.md` + `spec/README.md`（用户授权范围）；**上游 20 册零改动**（门控自身即为证据）。
- **机制闭环**：即日起**任何 `spec/` 改动**（含上游册与 v5 自定册）**须用户事先明确允许**，否则由 `check-spec-readonly` 哈希锁 + 预检第 5 项 + reviewer/architect 固定检查**拦截**。
- **补充发现（非阻塞，建议后续小改）**：`.work/evidence/SPEC-119t/run.sh` 的验收 5/7 断言依赖「未提交工作树」（`git status`/`git diff`），在已提交树上重跑会报 2 项假 FAIL；建议改为基于 `git diff <base>..HEAD` 的断言（**不影响交付物正确性**，reviewer 已用 commit 范围独立佐证）。
- **收尾检查**：`make check` EXIT=0（含新门控）；`git status --porcelain -uall` 干净；证据留 `.work/evidence/SPEC-119t/`、`.work/log/spec/`；知识沉淀含 `lessons §5.6`（锁门控范式）与 `§7.5` 闭合注记。
- **最终判决**：**`Accepted`** ⇒ 任务书 `**状态**` 置 `已验证`。
