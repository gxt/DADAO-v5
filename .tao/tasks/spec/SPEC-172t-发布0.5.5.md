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


## 追加要求（用户 2026-10-24）：changelog 需重写，不是只改标题

发布时 `SimRISC-00` 附录「版本与变更记录」的 `0.5.5-rc` 段（**30 条**）必须整理：

1. **该合并的合并**：同一对象的**多次中间态**合并为一条**最终态**。已知至少：
   - `fence`/`swym`/`lr`/`sc`/`ct*` 的编码：现分散在 5–6 条（`fence` 迁 `100-000`、`lr/sc` 改名重排、`ct*` 新增、`OPC-MISC` 迁 `0100-0111`、早前"`fence` 改 `0x00`/`swym 0x22`"）⇒ 合并为**一条**描述最终编码面（`OPC-MISC` = `opc 0x47`；`fence ha 0x20`、`swym 0x22`、`lr/sc` 布局、`ct*` `0x25–0x27`）。
   - `rela.si`：删除 → 恢复 → 改名 `aip.si` → 三点差异 = 4 条 ⇒ 合并为 1–2 条（直接写最终 `aip.si`）。
   - 术语：`major-op→opc`/`minor-op→opx`、`PC→IP`、0 号寄存器措辞 ⇒ 合并为一条「术语统一」。
   - 文档结构：分册重组 / 原子章迁入 / 标题章节号 / 附录新增 ⇒ 合并为 1–2 条。
2. **调整顺序**：按**主题**分组（ISA 指令增删 → 编码重排 → 语义订正 → 文档结构），组内按重要性，不按时间。
3. **不留交叉引用**：附录内不指向其它分册/手册（现有 3 处涉及 `SimRISC-12`/`SimRISC-00` 的措辞改为**不含分册号**的结构描述；`§` 类引用现为 0，保持 0）。
4. changelog 门控约束照旧：无任务号、无表格、版本逆序、互锁组一致。

**验收追加**：`grep -nE 'SimRISC-[0-9]|Toolchain-|Machine-|§' `（附录段）⇒ 0；条目数由 30 降至约 12–15（现场统计，不写死）；语义无损（每条仍可追溯到最终状态）。

## 完成区
（执行后填写，≤30 行）

## 审阅记录
