# SPEC-118m: M5 spec 里程碑

**模块**：spec
**项目里程碑**：M5
**状态**：里程碑
**目标**：规范层支持 M5——① **ADR 决策落地**：`ADR-0020`（SEE/HEE 与 semihosting，D1–D14）新建、`ADR-0004` 修订（新 bootrom 与加载模型，R1–R3，含 **R3「RAM 基址是否随 bootrom 调整」判定/记录**）、`ADR-0016` 范围判定（S1）——**每个 decision 逐条经用户确认**；② **SEE/HEE + semihosting 规范正文入 `spec/`** + 投影（`contract-sbi.md`/`contract-see.md`/`contract-semihosting.md`）+ `spec/README` 投影表；③ **re-scope**：`trap`/`escape`/`cfx2rc`/`cfx2rd` 由 `excluded`→已实现（`contracts/*` + 投影 + `check_scope` 计数 155/11/227；`SimRISC-12` 保持 deferred）；④ **大小写敏感修订**（`Toolchain-01 §2.1` + `contract-asm §2.1` 撤销「不敏感」；`ISS-157` 以「条款撤销」结案）；⑤ **`Process-05 §6` 落点规则补正**（`.dadao/tests/` 口径）；⑥ **`encode_cfx` 定界/最小修正**（用户裁定 3：汇编/编码层不应含实现期语义）；⑦ **`Machine-01 §1` 越界路由与 RAM@0 容量落纸**（`umon` 段越界 ⇒ `CFXMEM`〔`0x81`〕、其余含 `power` 段 63 ⇒ `unmapped`〔`0x87`〕、RAM@0 = 16 MiB）+ **`spec/Machine-01` 纳入只读锁**（锁内 20→21；**含 v5 自定册**）+ `Process-06 §5/§6` 同步 + 门控措辞去「upstream」（用户授权；承 `ISS-166`）。
**关联任务**：`SPEC-113t`、`SPEC-114t`、`SPEC-115t`、`SPEC-116t`、`SPEC-117t`、`SPEC-119t`、`SPEC-120t`、`SPEC-121t`（8 个；`SPEC-119t` = **`spec/` 目录保护机制**，跨切面流程任务；`SPEC-120t` = **`encode_cfx` 定界/最小修正**〔用户裁定 3〕，2026-10-07 追加；`SPEC-121t` = **`Machine-01 §1` 越界路由/RAM@0 容量落纸 + 该册入只读锁 + `Process-06` 同步**〔承 `ISS-166`；用户授权〕，2026-10-08 追加）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`.tao/adr/adr-0020-see-semihosting.md`（`Accepted`）、`adr-0004` 修订、`adr-0016` 范围判定；`spec/DADAO-12`（+`DADAO-13/21/22` 相关）semihosting 正文；投影 `contract-sbi.md`/`contract-see.md`/`contract-semihosting.md`；`contracts/opcodes.yaml` 4 条 re-scope；`check_scope.py` 计数
- 用户逐条确认记录：`ADR-0020` D1–D14、`ADR-0004` R1–R3、`ADR-0016` S1 **逐条**已确认（完成区原话/摘要）；无「未确认即 `Accepted`」
- **R3 归属**：判定结论 + 「仅判定/记录、实现另立任务」已登记
- **组合加载 ADR 推迟 M6（用户 2026-10-08 裁定）**：「`-bios`+ELF 组合」加载/入口语义的 ADR 决策**不在 M5**（M5 不立 ADR；推迟 M6，见 `INTEG-019k` §第 8 轮、`ISS-168`）——`ADR-0020`/`ADR-0004`/`ADR-0016` 的 M5 落地不受影响（本 `m` 核验不含组合 ADR）
- `python3 tools/spec/check_scope.py` EXIT=0（`m1=155`/`excluded=11`/`total=227`）；`make check` EXIT=0（`check-spec-refs`/`check-legality-drift`/`check-asm-*` 绿）
- `ISS-157` 以「条款撤销」`closed`；`ISS-110` 部分收口登记
- `spec/README.md` 投影表 `DADAO-12/13/22/23` 行更新（`deferred`→实际落点）
- `make check-no-residue` 干净
- **`encode_cfx` 处置（`SPEC-120t`）**：汇编/编码层不再含实现期语义（用户裁定 3）；调研定界结论 + 所选候选（删除/降级）已落纸；`check-rule-refs`/`check-legality-drift` 绿（**默认不触 `spec/`**）
- **`Machine-01 §1` 口径落纸 + 该册入锁（`SPEC-121t`）**：`§1.1` RAM@0 = 16 MiB、`§1.2` 含「精确路由」条（`umon` ⇒ `0x81`、其余含 `power` 63 ⇒ `0x87`）；`spec/Machine-01` 已入 `manifests/spec-readonly.lock.toml`（锁内 **21** 条 = 上游 20 + `Machine-01`，其余 20 册零变动）；`Process-06 §5/§6` 同步（语义由「只保护上游 20 册」扩为「**含 v5 自定册**」）+ 门控措辞去「upstream」（`check_spec_readonly.py`/`Makefile` help）；`make check-spec-readonly` EXIT=0；`ISS-166` `closed`（用户授权原话落 `SPEC-121t` 文件头）

## 核验记录（主会话）

**M5 spec 里程碑核验（2026-10-08，architect 代主会话）**　**判决：满足，置 `里程碑`**

证据来源（既有日志 + 独立只读复核）：`SPEC-113t`/`114t`/`115t`/`116t`/`117t`/`119t`/`120t`/`121t` 完成区与审阅记录、`.work/log/spec/`、`.work/log/integ/INTEG-020t-check.log`；本次独立跑只读 checker `tools/spec/check_scope.py`、`tools/infra/check_spec_readonly.py`、`tools/infra/check_dirs.py --residue`。

| # | 核验项 | 证据（真实） | 结论 |
| --- | --- | --- | --- |
| 1 | 关联任务 8 个均 `已验证` | `SPEC-113t/114t/115t/116t/117t/119t/120t/121t` 头部均 `**状态**：已验证` | ✅ |
| 2 | `ADR-0020`（`Accepted`） | `.tao/adr/adr-0020-see-semihosting.md:3 **状态**：Accepted`（`D1–D15`） | ✅ |
| 3 | `ADR-0004` 修订 | 同册 `**状态**` 行含 `rev. 2026-10-07`；`## 修订` 有 `rev. 2026-10-07` 条目 `R1`（`-bios` 与 ELF 路径**并存**）/`R2`（`SYS_EXIT` 取代 exit-port，`D3` 节内已标 `Superseded by ADR-0020 D8`）/`R3`（RAM 基址改全 0 + C1 双映射两步） | ✅ |
| 4 | `ADR-0016 S1` 范围判定 | `SPEC-113t` §四：`S1` =「沿用 `D1–D11`（不改正文）」；`ADR-0016` 仍 `Accepted` | ✅ |
| 5 | 正文落 `spec/` + 投影 | 新建 **`spec/Machine-01-测试机运行环境.md`**（①–⑦ 七节）+ `spec/README.md:49` 索引行；投影 **`.tao/knowledge/contract-see.md`、`contract-semihosting.md`** 存在 | ✅（**落点相对本 `m` 原措辞「`spec/DADAO-12`」有变更**，见下「口径/落点变更」） |
| 6 | 用户逐条确认记录 | `SPEC-113t` §四：`D1`/`D15`/`R1`/`R2`/`R3` 逐条裁定 + `D2–D14`/`S1`「未特别指出=保留」推定并经用户「**全部确认**」⇒ 复核闭合；无「未确认即 `Accepted`」 | ✅ |
| 7 | `R3` 归属登记 | `SPEC-113t` §四：`R3` = 判定 + `step1`（M5，`QEMU-049t`）/`step2`（另立、M5 之外→后改 M6） | ✅ |
| 8 | 组合加载 ADR 推迟 M6 | `milestones.md` M6 待办 + `ISS-168`（`scope: M6`）；`SPEC-118m` 核验不含组合 ADR | ✅ |
| 9 | `check_scope.py` EXIT=0（155/11/227） | 本次独立跑：`m1=155`/`fp=60`/`excluded=11`/`m3=1`/`total=227` 全 PASS，`check-scope: PASS` | ✅ |
| 10 | `contracts/opcodes.yaml` 4 条 re-scope `scope: m1` | `cfx2rd_crrr_cfx`/`cfx2rc_crrr_cfx`/`escape_ciii_cfx`/`trap_ciii_cfx` 均 `scope: m1` | ✅ |
| 11 | `ISS-157` 以「条款撤销」`closed`；`ISS-110` 部分收口登记 | `issues.yaml`：`ISS-157` `status: closed`/`resolved_by: SPEC-116t`；`ISS-110` 仍 `open`（剩余 `cfxld`/`cfxst` = `SimRISC-12` 保持 `excluded`，M5 明列范围外） | ✅ |
| 12 | `spec/README.md` 投影表 `DADAO-12/13/22/23` 行更新 | `spec/README.md:86-89` 已写 `contract-see.md`（运行环境/权限/异常）实际落点；`contract-sbi/mmu/exception` 显式 `deferred`（`:103-105`） | ✅（`contract-sbi.md` **未建** = 显式 `deferred`，见下） |
| 13 | `encode_cfx` 处置（`SPEC-120t`） | 规则删除（候选 A）；`grep -rn encode_cfx` 0 命中；`contracts/legality_rules.yaml` 16→15 条、`deferred` 1→0；`spec/` 交集空 | ✅ |
| 14 | `Machine-01 §1` 口径 + 该册入锁（`SPEC-121t`） | `§1.1` RAM@0 = `16 MiB`；`§1.2`「精确路由」条（`umon` 越界 ⇒ `0x81`、其余含 `power` 63 ⇒ `0x87`）；`manifests/spec-readonly.lock.toml` 21 条（含 `Machine-01`）；本次跑 `check-spec-readonly: 21 read-only spec volume(s) OK` | ✅ |
| 15 | `make check` EXIT=0 | `INTEG-020t-check.log` `repository checks: PASS`（含 `check-spec-refs`/`check-legality-drift`/`check-asm-*`） | ✅ |
| 16 | `make check-no-residue` 干净 | 本次跑 `check_dirs.py --residue` → `check-no-residue: PASS`（rc=0） | ✅ |

**口径/落点变更（相对本 `m` 原措辞，均经用户裁定，非缺口）**：
1. **正文落点**：本 `m` 原写「`spec/DADAO-12`（+`DADAO-13/21/22` 相关）semihosting 正文」；实际按 **2026-10-07 落点裁定**（用户确认）落**新建 `spec/Machine-01-测试机运行环境.md`**（`SPEC-114t`）。上游只读册零改动（`DADAO-12/13/21/22` 均未改）。
2. **`contract-sbi.md` 未建**：本 `m` 原列 `contract-sbi.md` 为产出；`spec/README.md §deferred` 表（`:103`）显式判其 **`deferred`（部分落于 `contract-see.md`）**——M5 消费方（SEE 经 semihosting）不经 `trap cfxha` SBI 功能表，未冻结后果可控，触发条件已记（SBI 功能表消费方落地时补齐）。属**显式 deferred 处置**，非缺口。

**跨模块影响处置（逐条）**：

| 项 | 性质 | 处置 | 是否阻断本模块 |
| --- | --- | --- | --- |
| `ISS-163`（`Toolchain-01 §5/§11/§13` 旧口径，`scope[spec,M5]`） | 上游只读册文案与 `contracts/opcodes.yaml` 事实不符（不影响实现） | **用户 2026-10-08 裁定「暂登记遗留」** ⇒ 已登记（登记即用户的处置选择）；收口须另行授权 + 锁同步 | 否（文案层，实现口径由 `contracts/` 权威且门控绿） |
| `ISS-166`（`Machine-01 §1` 未覆盖） | spec 正文待落纸 | **closed by `SPEC-121t`** | 否 |
| `ISS-167`（`DADAO-12 §5` prose/伪代码张力，`scope[spec,qemu,M5]`） | 文档措辞张力（判据=伪代码权威，实现按伪代码） | 已登记 + 判据明确 + **建议另立 spec 任务**（未立，待授权）；`spec/` 零改动 | 否（实现正确且已验收） |
| `ISS-110`（cfx 指令/别名，`scope[llvm,M5]`） | 跨模块（llvm） | **部分收口**：`trap`/`escape`/`cfx2rd`/`cfx2rc` 已实现；剩余 `cfxld`/`cfxst` = `SimRISC-12`，M5 明列范围外 | 否 |
| `ISS-168`（`-bios`+ELF 组合 / loader 扩展 / 组合 ADR） | `scope: M6` | 用户 2026-10-08 裁定移 M6 | 否（M6） |

**结论：关联任务全 `已验证`、16 项核验满足、跨模块项均已处置（登记/结案/M6）⇒ 置 `里程碑`。**

## 审阅记录

#### M5 模块里程碑核验（architect，2026-10-08）

**判决**：**满足 ⇒ `**状态**` 置 `里程碑`**。逐条证据见上「核验记录（主会话）」。

**两点落点/产出偏差（均经用户裁定处置，非缺口，如实登记）**：① 正文落点由本 `m` 原措辞 `spec/DADAO-12` 改为新建 `spec/Machine-01-测试机运行环境.md`（2026-10-07 落点裁定）；② `contract-sbi.md` 未建 = `spec/README.md §deferred` 显式 `deferred`。

**跨模块项**：`ISS-163`（用户裁定「暂登记遗留」）、`ISS-167`（登记 + 建议另立 spec 任务）、`ISS-110`（部分收口，剩余属 `SimRISC-12`，M5 范围外）、`ISS-166`（closed）、`ISS-168`/`ISS-165`（M6）——**无未处置跨模块项**。

**边界**：本次仅改本文件（`**状态**` 字段 + `## 核验记录（主会话）` + 本记录）；**`spec/` 交集为空**；未触 `contracts/**`/`components/**`/`Makefile`/`tools/**`；未新增/删除任务。
