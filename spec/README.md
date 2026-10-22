# spec/ — 规范总索引

> **状态**：生效（2026-10-03，文档分层改造 `SPEC-084t`）
> **范围**：本目录是 DADAO-v5 的**技术规范（内容层 / 唯一真源）**——上游基线（`SimRISC-*`/`DADAO-*`）与 v5 自定**技术规范**（`Toolchain-01`/`Machine-01`）合一；**工程流程规范（`Process-0x`）归 `docs/`**（见 `docs/README.md`）；索引与投影表见本文。

## 定位说明

- **规范＝内容层 / 唯一真源**：描述"应当是什么"，面向人阅读，允许歧义与自然语言；v5 自定**技术规范**（`Toolchain-01`/`Machine-01`）属**持续修订**的活规范，由 spec 模块任务按变更流程修改（见 `ADR-0012 D4`）。工程流程规范（`Process-0x`）不属本目录，归 `docs/`。
- **投影＝实现依据**：投影把规范**归一化**为机器/agent 可精确消费的形态，是实现的直接依据。投影分两层：
  - `contracts/*`：**机器可读数据**（编码表/ABI/合法性规则等），供工具消费；
  - `.tao/contracts/contract-*.md`：**叙述型合约**（§ 编号 + `[spec §x]` 引用），供人/agent 阅读。
- **本目录同时含上游基线与 v5 自定技术规范**：`SimRISC-00…12`、`DADAO-11…23` 为**上游基线**（按 `ADR-0012 D4`，spec 模块任务可改上游并生成新版本）；`Toolchain-01`、`Machine-01` 为 **v5 自定技术规范**（工程流程规范 `Process-0x` 已迁 `docs/`）。二者同处一目录，取消历史上"原始规范 vs v5 规范层"的二分。
- **ADR 不在此目录**：架构决策记录（ADR）属**决策层**，落 `.tao/adr/`（见 `docs/Process-03-ADR编写规范.md`）；ADR 只记决策、理由、被否方案与指向规范章节的指针，**不承载规范正文**。

## 分册清单

### ISA

| 分册 | 职责 |
|------|------|
| [`SimRISC-00-指令系统设计.md`](SimRISC-00-指令系统设计.md) | 指令系统总览、格式类、QFC 主表与 MISC 子表 |
| [`SimRISC-01-取数存数.md`](SimRISC-01-取数存数.md) | 取数存数类指令 |
| [`SimRISC-02-寄存器复制.md`](SimRISC-02-寄存器复制.md) | 寄存器复制类指令 |
| [`SimRISC-03-16位立即数操作.md`](SimRISC-03-16位立即数操作.md) | 16 位立即数操作 |
| [`SimRISC-04-64位数据运算.md`](SimRISC-04-64位数据运算.md) | 64 位数据运算 |
| [`SimRISC-05-64位地址运算.md`](SimRISC-05-64位地址运算.md) | 64 位地址运算 |
| [`SimRISC-06-控制流.md`](SimRISC-06-控制流.md) | 控制流（跳转/分支/调用/返回） |
| [`SimRISC-07-浮点运算.md`](SimRISC-07-浮点运算.md) | 浮点运算 |
| [`SimRISC-08-32位数据运算.md`](SimRISC-08-32位数据运算.md) | 32 位数据运算 |
| [`SimRISC-09-16位数据运算.md`](SimRISC-09-16位数据运算.md) | 16 位数据运算 |
| [`SimRISC-10-8位数据运算.md`](SimRISC-10-8位数据运算.md) | 8 位数据运算 |
| [`SimRISC-11-其它.md`](SimRISC-11-其它.md) | 其它类指令（占位/非法/特权/原子） |
| [`SimRISC-12-待定.md`](SimRISC-12-待定.md) | 待定类指令（SRAM 块传输 `cfxld`/`cfxst`） |

**历史版本（已归档）**：每个 SimRISC 版本在 `.tao/archive/SimRISC-<ver>/` 各留一份**只读**快照（**只增不改**；来源、快照提交与逐文件 `sha256` 见各目录 `PROVENANCE.md`）。归档不参与实现、不参与 `spec/` 门控扫描，仅供对照与溯源；规则见 `docs/Process-06-spec目录保护规范.md §8`。

| 版本 | 快照提交 | 首次标记日期 | 分册数 | 归档目录 |
|------|----------|--------------|--------|----------|
| `0.4.0` | `c8861ec`（上游 wiki） | 2026-06-27 | 5 | `.tao/archive/SimRISC-0.4.0/` |
| `0.4.1` | `9f378f4`（上游 wiki，v5 同步基线） | 2026-06-28 | 5 | `.tao/archive/SimRISC-0.4.1/` |
| `0.5.0` | `fc3d814` | 2026-07-15 | 5 | `.tao/archive/SimRISC-0.5.0/` |
| `0.5.1` | `f77d158` | 2026-07-17 | 5 | `.tao/archive/SimRISC-0.5.1/` |
| `0.5.2` | `640b879` | 2026-07-18 | 5 | `.tao/archive/SimRISC-0.5.2/` |
| `0.5.3` | `86fdcc8` | 2026-07-19 | 5 | `.tao/archive/SimRISC-0.5.3/` |
| `0.5.4` | `7804abb` | 2026-09-28 | 13 | `.tao/archive/SimRISC-0.5.4/` |
| `0.5.5-rc` | `a04d34e`（升号时点快照） | 2026-10-12 | 13 | `.tao/archive/SimRISC-0.5.5-rc/` |

> `0.3` 及更早**无版本标记**（wiki 早期为单文件 `SimRISC.md`），无法按版本重建，不伪造快照。`0.4.0`/`0.4.1` 取自 `.cache/refs/DADAO.wiki`（锚点 `9f378f4`），其余取自本仓历史。机器可读清单：`python3 tools/spec/gen_spec_archive.py --list`；门控：`make check-spec-archive`。
>
> **同号冲突（只记录、不合并）**：`0.4.1` 在 wiki（`9f378f4`，归档采用）与本仓（`7dde864`，含 0.4.1 号期间的本地修订）内容不同；本仓该段修订随 `0.5.0` 一并发布，故 `0.5.0` 附录段覆盖其改动。

### 环境

| 分册 | 职责 |
|------|------|
| [`DADAO-11-AEE-应用程序运行环境.md`](DADAO-11-AEE-应用程序运行环境.md) | AEE，应用程序运行环境 |
| [`DADAO-12-SEE-主管系统运行环境.md`](DADAO-12-SEE-主管系统运行环境.md) | SEE，主管系统运行环境 |
| [`DADAO-13-HEE-超管系统运行环境.md`](DADAO-13-HEE-超管系统运行环境.md) | HEE，超管系统运行环境 |

### 测试机（v5 自定）

| 分册 | 职责 |
|------|------|
| [`Machine-01-测试机运行环境.md`](Machine-01-测试机运行环境.md) | v5 测试机（`dadao-m1`）运行环境与 semihosting 正文：内存映射/复位、运行模式、cfx/权限、`trap`/`escape`/异常进入、semihosting（tag/传参/25 服务/`SYS_EXIT`）、加载/bootrom、退出 |

### 二进制接口

| 分册 | 职责 |
|------|------|
| [`DADAO-21-ABI-应用程序二进制接口.md`](DADAO-21-ABI-应用程序二进制接口.md) | ABI，应用程序二进制接口 |
| [`DADAO-22-SBI-主管系统二进制接口.md`](DADAO-22-SBI-主管系统二进制接口.md) | SBI，主管系统二进制接口 |
| [`DADAO-23-HBI-超管系统二进制接口.md`](DADAO-23-HBI-超管系统二进制接口.md) | HBI，超管系统二进制接口 |

### 工具链

| 分册 | 职责 |
|------|------|
| [`Toolchain-01-汇编语言.md`](Toolchain-01-汇编语言.md) | DADAO 汇编语言规范（词法/记号/寻址/寄存器组/条件/格式类语法/伪指令/诊断/往返）；含 cfx 系列记法约定正文 |

> **工程流程规范不在此目录**：`Process-01…06`（组件补丁 / 合约 / ADR / 归档 / TDD / spec 目录保护）为**工程流程规范**，已迁至 `docs/`，索引见 `docs/README.md`——本目录只收**技术规范**（上游基线 + v5 自定技术册 `Toolchain-01`/`Machine-01`）。

## 投影表

**规则**（决策 8）：**每册规范都必须有投影**；投影类型 ∈ ①叙述合约 `contract-*.md` ②机器数据 `contracts/*` ③机械门控 ④可执行 lit/oracle/向量。逐格填**实际落点**，缺失写 **`缺口`**。

| 册 / 分组 | ①叙述合约 `contract-*.md` | ②机器数据 `contracts/*` | ③机械门控 | ④可执行 lit/oracle/向量 |
|-----------|---------------------------|--------------------------|------------|--------------------------|
| `SimRISC-00` | `contract-isa.md` | `contracts/opcodes.yaml`（QFC 主表 + MISC 子表） | `tools/spec/validate_encoding.py`、`check_qfc_coverage.py`、`check_d7_consistency.py`、`check_rule_refs.py`、`check_scope.py` | `tests/vectors/` |
| `SimRISC-01…06, 08…12` | `contract-isa.md` | `contracts/opcodes.yaml`、`contracts/legality_rules.yaml` | `tools/spec/check_asm_list_consistency.py`、`check_legality_drift.py`、`check_asm_prose.py`、`check_scope.py` | `tests/vectors/isa/*.yaml`、`tests/llvm/lit/MC/DADAO`、`tests/e2e` |
| `SimRISC-07`（浮点，`scope: fp`） | `contract-fp.md` | `contracts/fp_semantics.yaml`、`contracts/legality_rules.yaml` | `tools/spec/check_fp_contract.py`、`check_scope.py` | `缺口`（oracle/向量待建，见 `docs/fp-oracle-design.md`） |
| `DADAO-11`（AEE） | `contract-abi.md` | `contracts/abi.yaml` | `tools/integ/check_interface_alignment.py` | `tests/`（据实） |
| `DADAO-12`（SEE） | `contract-see.md`（运行模式/核内地址空间/cfx 权限/异常进入退出）；运行环境部分 M5 落地；`contract-sbi.md`（SBI 功能表）、`contract-mmu.md`（地址转换）仍 `deferred` | `缺口`（据实） | `tools/spec/check_cfx_aliases.py` | `缺口`（据实） |
| `DADAO-13`（HEE） | `contract-see.md`（cg3/hmon 运行环境部分）；`contract-exception.md`（完整系统态异常模型）仍 `deferred` | 据实 | `gen_cfx_aliases`（DADAO-13 源） | 据实 |
| `DADAO-21`（ABI） | `contract-abi.md` | `contracts/abi.yaml` | `check_interface_alignment` | 据实 |
| `DADAO-22`（SBI） | `contract-see.md`（`§5` SBI 调用约定、`§4` trap/escape 路由）；`contract-sbi.md`（SBI 功能表）仍 `deferred` | 据实 | 据实 | 据实 |
| `DADAO-23`（HBI） | `deferred`（`contract-exception.md`；归属 M3+，触发：HBI 消费方落地） | 据实 | 据实 | 据实 |
| `Machine-01`（测试机，v5 自定） | `contract-see.md`（运行环境/权限/异常进入）+ `contract-semihosting.md`（tag/传参/25 服务/`SYS_EXIT`） | `缺口`（据实；测试机约定无 `contracts/*`） | `tools/integ/check_interface_alignment.py` | `缺口`（据实；向量归 `TESTCASES-*`） |
| `Toolchain-01` | `contract-asm.md` + `contract-asm-list.md`（生成投影，已落位） | `contracts/opcodes.yaml`（format/汇编形式列） | `tools/spec/check_asm_prose.py`、`check_asm_list_consistency.py`、`check_asm_list_drift.py` | `tests/llvm/lit/MC/DADAO` |

> 工程流程规范 `docs/Process-0x` 不属本目录，故不在本表；其门控映射（`check_patch_tree` / `check_spec_drift` / `check_spec_readonly` 等）见各册正文与 `docs/README.md`。

**登记缺口（显式 deferred）**（决策 8；T2 `SPEC-085t` 定稿并同步 `docs/Process-02` 的合约清单；三类系统层缺口由 `SPEC-092t` 标显式 deferred）：

| 缺口（①叙述合约） | 来源册 | 状态 | deferred 理由 | 归属/触发 |
|-------------------|--------|------|---------------|-----------|
| `contract-sbi.md` | `DADAO-12`（SEE）/ `DADAO-22`（SBI） | **deferred（部分落于 `contract-see.md`）** | `contract-see.md` 已覆盖 SEE 运行环境与 SBI `§1` 调用约定（M5，`SPEC-114t`）；SBI **功能表**（`DADAO-22 §2–§12`：umon/jmon/smon/ptw/tlb/cache/hart/llc/pmem/timer/uart/power 功能调用）仍无 M5 消费方（M5 SEE 经 semihosting 服务，不经 `trap cfxha` 功能表），未冻结后果可控；上游 `spec/DADAO-22` 已存在，补齐不需新造正文。 | 归属 M5+；触发：`trap cfxha` SBI 功能表消费方落地（如 OS 经 SBI 调用 ptw/timer/uart）时须先补齐 `contract-sbi.md` 再实现。 |
| `contract-exception.md` | `DADAO-13`（HEE）/ `DADAO-23`（HBI） | **deferred（部分落于 `contract-see.md`）** | `contract-see.md` 已覆盖 HEE cg3/hmon 运行环境部分（M5，`SPEC-114t`）；**完整系统态异常模型**（cfx_hmon 异常进入/退出全流程、HBI 接口）仍无 M5 消费方，未冻结后果可控；上游 `spec/DADAO-13/23` 已存在，补齐不需新造正文。 | 归属 M5+；触发：系统态异常/HBI 消费方落地时须先补齐 `contract-exception.md` 再实现。 |
| `contract-mmu.md` | `DADAO-12`（SEE，地址转换） | **deferred** | M5 测试机 VA=PA、无地址转换消费方；M3 codegen 为 freestanding 单 TU，无 MMU，未冻结后果可控；上游 `spec/DADAO-12`（§2.2 虚实地址转换）已存在，补齐不需新造正文。`contract-see.md §3` 只提取 `NUPERM`/`NJPERM`/`NSPERM`/`NHPERM` 权限层次，不含页表步进/转换公式。 | 归属 M5+；触发：MMU/地址转换消费方落地时须先补齐 `contract-mmu.md` 再实现。 |

> 上述三项为**已登记、显式 deferred**（决策 8：缺失即登记，不臆造内容）；上游依据可回溯（`spec/DADAO-12/13/22/23`），触发条件满足后按 `docs/Process-02` 归一化补齐，再按轻量修订流程（见下）更新本表。

## 规范修订流程

轻量五步（不强制记 ADR）：

```text
1. 改规范（spec/）
2. 重算投影（重跑生成器：contracts/*、contract-*.md）
3. 门控查漂移（make check 相关目标）
4. 缺口登记（投影缺失者记入本文「投影表」缺口）
5. 不强制记 ADR —— 仅「多方案取舍 / 外部契约 / 取向改变」才记
```

> **前置（MUST）**：改 `spec/` 任何册（含 v5 自定册与 `spec/README.md`）须**用户事先授权**（见 `docs/Process-06`）；上游只读册另有 `sha256` 锁门控（`make check-spec-readonly`，已纳入 `make check`）。

## 册维护约定

> 本节只写 **`spec/` 目录特有**约定（标题编号 / 版本与变更记录）；**通用规范**（组件/合约/ADR/归档/TDD 等）见 `docs/Process-0x`，**不在此重复**。

- **标题编号**：`##`→`N`、`###`→`N.M`、`####`→`N.M.K`（最深 `####`）；同册**唯一、连续、父节逐级**；**禁单包装层**（正文 `##` 恰 1 个且其下 `###` ≥2 ⇒ 应拍平）。**册内引用**只写 `§<标题文本>`（不带节号）；**跨册引用只写手册名**（不带 `§`、不带节号）。机器可读数据（`contracts/*.yaml`、`tests/**`）的 `spec_cite` 用 `手册: 助记符`（指令类）或 `手册: 小节标题`（非指令类）。门控：`tools/spec/check_numbering.py` / `tools/spec/check_spec_cite_targets.py`。
- **无编号尾段（固定顺序）**：`## 附录 A：汇编指令速查` → `## 附录 B：合法性检查` → `## 附录：版本与变更记录`。A/B 为 `SimRISC-01`…`12` 的生成区（A 单表、无 `###` 子标题、无分类列；B 落合法性清单），**必在册尾**且 A 在 B 前；`SimRISC-00` 无 A/B。门控：`check_numbering.py` / `check-asm-list-consistency` / `check-legality-drift`。
- **纯净化**：`spec/SimRISC-*` 只写规范内容（指令定义 / 编码 / 格式 / 语义 / 异常 / revision）；**禁** `scope` 范围标注、里程碑号、任务号、`ADR-`/`ISS-` 号、`contract-*.md` 指针、`.tao/` 路径、按范围的条数总账、旧表名前缀。项目侧记账归 `.tao/contracts/contract-isa.md §0`「范围表」。门控：`tools/spec/check_spec_purity.py`。
- **`附录：版本与变更记录`**：二级标题、**不加编号**、**逆序**（最新在上）；三级标题 = `### <版本>（<发布日期>）`；顶部累积段 = `### <上一发布版本 z+1>-rc（未发布）`。**不用表格**；**变更记录集中于 `SimRISC-00`**（13 册条目按版本合并去重），`SimRISC-01`…`12` 不再单列；DADAO / Toolchain / Machine 各册仍各有一条。门控：`tools/spec/check_spec_changelog.py`。
- **发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期，再于其上方**新开空 `-rc` 段**。
- **版本号语义**：`x.y.z`——**`x=0` 表示尚未正式发布**（正式发布后 `x≥1`）；大改动 `y+1`、有影响的小改 `z+1`。
- **互锁组**：`SimRISC-00`…`SimRISC-12` 一组，`AEE↔ABI`、`SEE↔SBI`、`HEE↔HBI` 各一组；**组内版本必须一致**。
- **只读册纪律**：21 册以 `sha256` 锁定（`manifests/spec-readonly.lock.toml`）；改册须**用户事先授权原话** + **同一变更内更新锁**（见 `docs/Process-06`）。
- **改动记录粒度**：**聚合**（按版本段）、**不限条数**、**不带任务号 / ADR 号**（只写"改了什么"）；"加记录"动作本身不引发 `-rc`。

## Rationale

本改造成立的条件与取舍如下（不立 ADR，理由与被否方案记录于此）：

- **为何把 `docs/` 下的 spec 子目录合并进 `spec/`**：消除「原始规范 vs v5 规范层」的二义，使**单一目录＝单一真源**；引用不再需要在两处之间跳转或判断优先级。
- **为何 `SimRISC-*.md` / `DADAO-*.md` 不搬家**：保持与上游生成流程、以及 `ADR-0012 D4`「spec 模块任务可改上游规范」的名称对应关系；上游按本规定生成新版本文档时，文件名与目录不变。
- **为何取消拆分独立的 cfx 规范分册**：cfx 系列别名与 DADAO 汇编同属「汇编语言」这一主题，**不应拆分**；cfx 约定正文并入 `Toolchain-01`，而 cfx **别名表**属**投影层**（`.tao/contracts/contract-cfx-aliases.md`），不进 `spec/`。
- **为何生成物进 `contract-*`（投影层）**：生成的别名表/指令表是**实现的依据**，须与规范正文分离，才能被漂移门控（`make check-cfx-aliases` 等）机械校验；规范正文保持人工可读。
- **为何不立 ADR**：本改造属**文档组织与流程取向**（目录合并、命名、索引与投影表），不涉及不可逆的架构取舍或多方案外部契约；被否方案（如保留 `docs/` 下的 spec 子目录、把 cfx 拆为独立规范分册）已记录于本节，故不立 ADR。
