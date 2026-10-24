# SPEC-172t: 发布 SimRISC 0.5.5（去 `-rc`）

**模块**：spec
**项目里程碑**：M9（**终局复跑绿之后**、M9 收尾同一批）
**依赖**：终局全量复跑通过
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源（用户裁定，2026-10-24）

- 版本号：**0.5.5**（不跳到 0.6.0；release note 首行须明示"含编码不兼容变更"）
- 时机：**终局复跑绿之后**再做，与 M9 收尾同批提交
- **发布时不预开新的 `-rc` 空段**（有改动时再加）

## 现状（执行前复核）

- 13 册册头均为 `> **版本：0.5.5-rc**`
- changelog（`SimRISC-00` 附录）有 `### 0.5.5-rc（未发布）` 段，**34 行**
- 另 4 处引用版本号：`spec/README.md`、`manifests/spec-readonly.lock.toml`、根 `README.md`、`docs/Process-06-spec目录保护规范.md`

## 目标

1. 13 册册头：`0.5.5-rc` → `0.5.5`。
2. `### 0.5.5-rc（未发布）` → `### 0.5.5（2026-10-24）`；**不预开** `0.5.6-rc`。
3. 该段补齐本周期变更并**去掉任务号**（门控会查）：
   - `OPC-MISC` 迁 `op 0x47`（含 `ctpop/ctlz/cttz` 并入）+ `fence`/`lr`/`sc` 解 `excluded`
   - FMA：`ftfma`/`fofma`（`rrrr` 四操作数、`0x5E/0x5F`）立册并落地
   - 窄位算术/位操作/`ldm`/`stm` 等后端能力（不改变 ISA 记录）
   - 分册重组（11=核芯功能扩展 / 12=其它指令 / 非法指令并入 00）—— 属文档结构，可写一句
4. 重算 13 册 sha256 写入 `manifests/spec-readonly.lock.toml`；同步 `spec/README.md`、根 `README.md`、`docs/Process-06` 的版本串。
5. release note 首行加一句：**本版含编码不兼容变更**（`OPC-MISC` 编码迁移）。

## 验收

1. `grep -rn '0\.5\.5-rc' spec/ manifests/ README.md docs/Process-06*` ⇒ **0**（发布后不应再有 rc 标记）。
2. `check_spec_changelog` rc=0（互锁组/逆序/无任务号/无表格）；`check-spec-readonly` rc=0（sha 相符）；`check-spec-numbering` rc=0。
3. 13 册册头版本一致；changelog 顶部段版本 = 册头版本。
4. 语义零漂移：除版本串与 changelog 段外无改动（逐段 diff）。
5. 证据 `.work/evidence/<任务ID>/run.sh`（只跑上述门控，不跑 L1/L2）。

## 约束

- 不改任何指令语义/编码；只动版本串、changelog 段、锁与 4 处引用。
- 不 commit/push；开工 `git switch -c SPEC-172t`；临时目录 `/tmp/opencode/SPEC-172t/`。

## 完成区
（执行后填写，≤30 行）

## 审阅记录
