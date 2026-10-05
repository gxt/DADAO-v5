# SPEC-105t: `contract-elf §2–§4` 重定位正文（按 ADR-0019）

**模块**：spec
**项目里程碑**：M4
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**（自包含；决策已定，本任务只落正文）：
  - `.tao/adr/adr-0019-dadao-relocation-types.md`（**Accepted**，用户 2026-10-05 逐条确认 D1–D8）——本任务**唯一决策来源**（类型/编号/公式/溢出/RELA/ABS48/禁用 relaxation）。
  - `.tao/knowledge/contract-elf.md`：§1（ELF 头字段，`e_flags[7:0]=1` namespace）、§2–§4（当前标题为 `` `Deferred to M2`：… ``，**待改写为规范正文**）、文件头「M1 范围 / `Deferred to M2`」说明、`## 附录 A：来源对照`。
  - `.tao/knowledge/contract-isa.md` §2.3–§2.4（指令格式/字段位置/位宽）、§1.3.2（`rb0` = 当前指令地址）；`contracts/opcodes.yaml`（`imms12`/`imms18`/`imms24`、`rwii` 的 `immu16` + `wyde-position wp0–wp3`）——**仅核对字段**，不重定义。
  - `spec/Process-02-合约编写规范.md`（合约编写/来源标注格式）。
- **输出**：`.tao/knowledge/contract-elf.md` 的 **§2（重定位类型）、§3（重定位溢出策略）、§4（重定位松弛）由 `Deferred to M2` 转为规范正文**，内容严格等于 `ADR-0019` D1–D8：
  - **§2 类型与编号**（`e_flags[7:0]=1` namespace 内独立编号，**不复用** legacy `Dadao.def`）：
    | 编号 | 名 | 场景 | 编码字段 |
    |---|---|---|---|
    | 0 | `R_DADAO_ABS48` | `set.zw`/`or.w`/`andn.w` 序列（≤3 片 wyde） | 3×`immu16`（按 `wyde-position`） |
    | 1 | `R_DADAO_REL26` | `call`/`jump`（iiii） | `imms24`（有效 26 位） |
    | 2 | `R_DADAO_REL20` | `br.n/nn/z/nz/p/np`（riii） | `imms18`（有效 20 位） |
    | 3 | `R_DADAO_REL14` | `br.eq`/`br.ne`（rrii） | `imms12`（有效 14 位） |
    | 4 | `R_DADAO_NUM` | 计数 | — |
    - ELF 记录类型 = **`SHT_RELA`**（`.rela.*`，显式 `r_addend`）；reloc **逐指令**挂载，linker 依指令内 `wyde-position`（`wp`）判定该片对应地址的哪 16 位。
  - **§3 公式**（`S`=符号值、`A`=addend、`P`=重定位处地址；v5 **无 −4**，与 0628 `(val-4)>>2` 不同，因 `rb0` 读出为当前指令地址）：
    - `REL26/REL20/REL14`：`field = (S + A − P) >> 2`（字偏移）。
    - `ABS48`：`value = S + A`（48 位，按 `wyde-position` 分片写入 3×`immu16`）。
    - 溢出策略：越界 ⇒ **link-time error**（不截断、不 wrap）。
  - **§4 松弛**：`ABS48` 最多 **3 片**且**一律发射固定 max 3 片**（禁用 relaxation）；`RELA_PAGE`/`RELA_LO`（`rb0`/数据段相对寻址）**本期不实现、留后**；不做 `ABS32`（地址空间 48 位）。
  - 同步更新：文件头「`Deferred to M2`」清单（移除 §2–§4）与 M1 范围说明；`## 附录 A：来源对照` 中 §2/§3/§4 行的 ADR 指针改为 `ADR-0019 §D1–D8`；每条规范断言句末保留来源标注（`[ADR-0019 §DN]` / `[contract-isa.md §N]`）。
  - **门控对齐**：若 `spec/README.md` 投影表或任何 checker/注释含 `contract-elf §2–§4 = Deferred/缺口` 表述，同步更新；`make check` 全绿。
- **约束**：
  - **只落正文、不重新决策**：`ADR-0019` 已 `Accepted`；**不得**新增/修改任何 relocation 决策。发现与 ADR-0019 表述冲突时**阻断并报告**，不自行改契约。
  - **不改** `ADR-0003`、`ADR-0019`；**不改** `contract-elf` §1/§5/§6（§5/§6 调整归 `SPEC-107t`）；**不改** `contracts/opcodes.yaml`；**不实现** LLVM/LLD/QEMU。
  - `spec/`、`contracts/`、`.tao/knowledge/` 为共享文件，**串行**（`AGENTS.md`「同改共享文件一律串行」）。
  - 临时目录 `/tmp/opencode/SPEC-105t/`；**不提交 git**。

## 验收标准

1. **正文落地**：`grep -n "Deferred to M2" .tao/knowledge/contract-elf.md` 对 **§2–§4 无命中**；§2 含完整 5 行类型表（`ABS48=0`/`REL26=1`/`REL20=2`/`REL14=3`/`NUM=4`）与 `SHT_RELA`；§3 含 `S + A − P`、`>> 2`、`ABS48` 公式与 **link-time error**；§4 含「≤3 片 / 一律 max 3 片 / 禁用 relaxation / `RELA_PAGE`+`RELA_LO` 留后 / 不做 ABS32」。
2. **无 −4**：`grep -n "− 4\|- 4\|−4\|-4"` 对 §2–§4 无「相对类公式含 −4」的表述（"无 −4" 的说明本身允许出现）。
3. **来源标注**：§2–§4 每条规范断言句末有 `[ADR-0019 §DN]` 或 `[contract-isa.md §N]`；人工逐条与 `ADR-0019` D1–D8 对照**无矛盾**（完成区给出对照表）。
4. **反例门控**：任务自带可复跑检查脚本（`.work/evidence/SPEC-105t/run.sh`）逐条断言上列文本/编号/公式；对注入反例（改 `REL26` 编号、删「无 −4」、把「link-time error」改成「截断」）**必须 FAIL**，还原后回绿；完成区贴真实输出（`cmd > log 2>&1; rc=$?`，**无 `tee`**）。
5. **门控**：`make check` EXIT=0（含 `check-spec-refs`）；`git status --untracked-files=all` 仅本任务应有改动；未改 `ADR-*`/`contracts/**`/实现。

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
（审查者独立验证的重跑记录、约束核验、判决）
