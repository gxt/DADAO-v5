# SPEC-147t: 汇编注释符迁移 `;`→`@@`（规范面：`@@` 注释 + `;` 语句分隔符）

**模块**：spec
**项目里程碑**：M8
**依赖**：用户 2026-10-19 授权（原话见下「用户授权」）；`docs/Process-06`（`spec/` 改动须事先授权 + 只读册哈希锁）；`ADR-0013 D9.1`（本裁定**部分取代**；ADR 处置待用户确认，本册不擅自改 ADR）；`LLVM-109t`（实现与语料迁移，本册只做规范面）
**状态**：待开始

> **立册说明（2026-10-19，architect）**：本册是**规范面执行落点**。architect 已按用户授权在本分支同一提交内完成 §2.2、示例、变更记录、`contract-asm.md` 同步与只读锁重算；`**状态**` 按本批派单置 `待开始`，执行/验收者只需按「验收标准」复核并补完成区，**不得回退**既有改动。

## 执行环境
**执行环境**：本地

## 用户授权（原话逐字，渠道 = 经主会话问答，2026-10-19）
> 「**很好，就改成 `@@` 了**」

对照过程原话（同渠道，2026-10-19）：「**为什么不能用单个`#`做注释符**」「**用`@`做注释的ISA有哪些**」「**`@_@` 这个符号如何？写一段小程序我看看**」「**我个人倾向于 `@@`，你再做一次判断**」。

`docs/Process-06 §2`：`spec/` 下任何修改须用户事先明确允许 ⇒ 本册已具备；授权原话须原样写入任务书/完成区。

## 问题根源

1. 现行 `spec/Toolchain-01 §2.2` 规定 `;` 起至行尾为注释（`CommentString = ";"`），而 `;` 同时是 LLVM MC 的默认语句分隔符（`SeparatorString = ";"`）；注释检查先于分隔符检查 ⇒ `;` 永远不能分隔语句、一行只能一条语句。
2. 用户裁定改用**两字符 `@@`** 作注释符、`;` 回归语句分隔符。**单字符 `@` 不可用**：ELF 指令/指导符中 `@` 合法出现——`.type <sym>,@function`、`.section ".note.GNU-stack","",@progbits`——单字符注释会把 `@function`/`@progbits` 起至行尾误吞。
3. `#` 仍**不是**注释（保留给 C 预处理器）；`//`、`/* … */` 不采用。

## 接口规范

- **输入**：用户裁定（上）；`spec/Toolchain-01` 0.5.2 现状；`.tao/contracts/contract-asm.md`（原投影 0.5.0）。
- **输出（规范面，已在本分支落地）**：
  1. `spec/Toolchain-01-汇编语言.md §2.2`：
     - `@@` 起至行尾为注释（`CommentString = "@@"`）；
     - `;` 是语句分隔符（`SeparatorString = ";"`），**MAY** 一行多条语句，`;` 之后不是注释；附一行三语句示例；
     - `#` 非注释、`//`/`/* */` 不采用；
     - 理由一句：单一 `@` 出现在 `.type <sym>,@function` ⇒ 取两字符 `@@` 以免误吞。
  2. `§6.2`（被删伪指令替代示例）与 `§13.8`（cfx 示例）的注释符同步改 `@@`。
  3. 册头状态行版本 `0.5.2 → 0.5.3`；附录新增 `### 0.5.3（2026-10-19）`（**不改**历史 `0.2.2`「`#`→`;`」行）。
  4. `.tao/contracts/contract-asm.md`：版本 `0.5.0 → 0.5.3`；`§2.2` 四条同步；`§13.8` 示例注释改 `@@`。
  5. `README.md` 根版本表 `Toolchain 0.5.0 → 0.5.3`（`check-spec-drift` 以此比对，**非** `spec/` 改动）。
  6. `manifests/spec-readonly.lock.toml`：`spec/Toolchain-01` 的 `sha256` 重算（`89c9…` → `d866…`）+ 变更注记。
- **约束**：
  - **上游只读册不改**（`docs/Process-06 §1`）：`spec/DADAO-*`/`spec/SimRISC-*` 中的 `;` 示例是上游历史正文，由上游按本规范另行生成新版；本册**不**逐册改写、**不**动其 `sha256`。
  - **不改历史变更记录行**（历史是历史）。
  - ADR-0013 `D9.1` 的处置（新 ADR / 标 `Superseded` / 经授权的就地修订）**必须由用户确认**；本册不擅自改 ADR 正文。

## `spec/` 全量命中点（现场 `grep -rn ';' spec/`，2026-10-19）

> 只列**上游只读册**的旧注释示例；本册一律**不改**（`docs/Process-06 §1`）。计数 = `grep -c ';'` / 行首注释 `grep -c -E '^\s*;'`。

- `spec/DADAO-11-AEE-应用程序运行环境.md`：23 / 8
- `spec/DADAO-12-SEE-主管系统运行环境.md`：6 / 6
- `spec/DADAO-22-SBI-主管系统二进制接口.md`：181 / 90
- `spec/DADAO-23-HBI-超管系统二进制接口.md`：6 / 6
- `spec/SimRISC-03-16位立即数操作.md`：50 / 27
- `spec/SimRISC-04-64位数据运算.md`：30 / 0（均为行内注释）
- `spec/SimRISC-06-控制流.md`：1 / 0
- `spec/SimRISC-07-浮点运算.md`：2 / 0
- `spec/SimRISC-08-32位数据运算.md`：1 / 0
- `spec/SimRISC-09-16位数据运算.md`：1 / 0
- `spec/SimRISC-10-8位数据运算.md`：1 / 0
- `spec/SimRISC-11-其它.md`：5 / 2
- `spec/SimRISC-02-寄存器复制.md`：2 / 0（C 伪代码分号，**非**汇编注释）
- `spec/DADAO-21-ABI-应用程序二进制接口.md`：25 / 0（C 结构体分号，**非**汇编注释）
- `spec/Toolchain-01-汇编语言.md`：改后仅 4 处，均为**叙述分号**（状态行 / §2.2 分隔符 / 0.5.3 记录 / 历史 `0.2.2` 行），**无** `;` 注释示例。

## 验收标准

1. **规范文本**：`spec/Toolchain-01 §2.2` 明确「`@@` 注释 / `;` 语句分隔符 / `#` 非注释 / `//`、`/* */` 不采用 / 理由」；`§6.2`、`§13.8` 示例无 `;` 注释。
2. **变更记录**：册头版本 = 附录顶部段 = `0.5.3`；`python3 tools/spec/check_spec_changelog.py` rc=0。
3. **只读锁**：`make check-spec-readonly` rc=0；锁内**仅** `Toolchain-01` 的 `sha256` 变化，与实际文件 `sha256sum` 一致。
4. **合约投影**：`contract-asm.md` 版本 `0.5.3`、§2.2 四条与 spec 一致；`python3 tools/infra/check_spec_drift.py` rc=0（根 `README.md` 版本表已同步）。
5. **漂移/一致性门控**：`make check`（L1）rc=0，至少含 `check-spec-readonly` / `check-spec-changelog` / `check-spec-drift` / `check-spec-codeblocks` / `check-asm-prose` / `check-knowledge-refs` / `check-no-residue` / `check-milestones-fresh`。
6. **可达 FAIL**：临时把 `§2.2` 的 `CommentString = "@@"` 改回 `";"`（`cp` 备份 + md5 对账，**禁** `git checkout/restore/stash`）⇒ `check-spec-changelog` 或文本断言应红；还原后回绿。
7. **证据**：`.work/evidence/SPEC-147t/run.sh` 跑通，日志落 `.work/log/spec/SPEC-147t-*.log`；完成区贴真实命令输出与退出码。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
