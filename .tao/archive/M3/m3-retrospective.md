# M3 里程碑回顾（Retrospective）

> **定位**：面向 **M4 规划 / 新人上手 / 审计追溯**。本文件**聚合索引**既有材料，**不复制**其明细：
> 状态摘要见 `.tao/knowledge/MEMORY.md`；路线图见 `milestones.md`；变更流水见 `changelog.md`；
> 遗留台账见 `.tao/knowledge/issues.yaml`（issue/待决）与 `.tao/knowledge/lessons.md`（教训/方法论/过程记录）；
> **经验规则以 `AGENTS.md` 为唯一准绳**。
>
> **日期**：2026-10-05 ｜ **范围**：M3（Basic CodeGen，纯整数）
> **归档**：2026-10-05 起本文件随 M3 任务书/台账落入 `.tao/archive/M3/`（历史快照，不再更新）；M3 原始任务书/台账明细见同目录 `README.md`、`issues-closed.md`。

---

## 1. M3 事实快照

### 1.1 定义与门槛

`milestones.md`：**M3 — Basic CodeGen（纯整数）**
目的：`llc` 将**标量整数/指针**函数（LLVM IR）编译为 DADAO 汇编，经 MC → **单 TU** obj/raw binary → `qemu-system-dadao` 执行结果正确（freestanding、same-TU、无链接器）。门槛：**`make test-codegen` 全绿**，至少一个算术/访存/分支/调用函数端到端在 QEMU 得到期望结果。

**范围（用户裁定 2026-10-04）**：bank 只用 `GPRD`（i64 数据）+ `GPRB`（ptr 地址）；`RA`/`RF` 仅「保留不分配」；无需链接器（单 TU 自包含 + 最小重定位）。分解见 `SPEC-096k`。

### 1.2 达成状态

**2026-10-05 达成**（commit `6c4d1ac`）。5 个模块里程碑全部置 `里程碑`，`milestones.md` M3 = **✅ 达成**（`qemu` 列仍 `—`：执行层由 M1 冻结，无独立 qemu 模块里程碑；`QEMU-040t` 作为跨模块前置）。

| 模块 | 里程碑 | 备注 |
|---|---|---|
| infra | `INFRA-036m` | `INFRA-035t`（`llc` 入构建目标） |
| spec | `SPEC-099m` | `SPEC-097t` + `SPEC-100t`/`SPEC-101t` |
| testcases | `TESTCASES-027m` | `TESTCASES-026t`（独立向量） |
| llvm | `LLVM-042m` | `LLVM-033t`~`041t` + `043t`/`047t`/`048t`/`049t` |
| integ | `INTEG-013m` | `INTEG-012t`（E2E + `make test-codegen`） |

### 1.3 最终门槛实测（2026-10-05，真实输出；完整输出见 `.work/log/m3-closure/`）

| 门槛 | 命令 / 证据 | 结果 |
|---|---|---|
| `make test-codegen` 全绿 | `make test-codegen` | **EXIT=0**；`Results: 15/15 passed, 0 failed`（算术/访存/分支/调用四类 + 大端窄访存 + `ptr−ptr`） |
| `llc` 可产出 | `llc --version` | **EXIT=0**，输出含 `dadao - DADAO SimRISC` |
| `make check` 全绿 | `make check` | **EXIT=0**；`repository checks: PASS`；lit **34/34** |
| 补丁集一致 | `make check-patch-tree` | **EXIT=0**；`2 component(s), 80 patches OK`（llvm 48 + qemu 32） |
| 无残留 | `make check-no-residue` | **EXIT=0** |
| 台账干净 | `tools/infra/check_issues.py` | **EXIT=0**；归档前 `35 open / 56 closed` → 归档后 `35 open / 0 closed` |

### 1.4 版本 / 组件基线

规范 **SimRISC 0.5.4**（`README.md` 版本表为唯一来源）；`Toolchain 1.1`。
组件锁 `manifests/components.lock.toml`：`llvm-project` commit `6dfe1677ab8dffbc6ec13d53a1e0215d75147689`（llvmorg-23.1.1）；`qemu` commit `c3d48b7d1e89604920e5b81b91140c2ad39a1943`（v11.1.1）；`gem5` `enabled=false`（M3 不变）。

---

## 2. 交付物 / 资产地图

| 类别 | 数量 | 位置 |
|---|---|---|
| M3 任务文件 | **40**（已验证 35 + 里程碑 5） | `.tao/archive/M3/<module>/`（2026-10-05 归档，原 `.tao/tasks/<module>/`） |
| ADR | **18**（M3 新增 1：`0018`） | `.tao/adr/` |
| 合约叙述 | 7（`contract-isa`/`-abi`/`-elf`/`-fp`/`-asm`/`-asm-list`/`-cfx-aliases`） | `.tao/knowledge/` |
| 机器可读数据 | `opcodes.yaml`（**228** = 152 m1 + 60 fp + 15 excluded + 1 m3）/ `legality_rules.yaml`（16 规则）/ `abi.yaml` / `fp_semantics.yaml` | `contracts/` |
| LLVM 补丁 | **48** | `components/llvm-project/patches/` |
| QEMU 补丁 | **32** | `components/qemu/patches/` |
| 工具脚本 | **77**（infra 18 / qemu 25 / spec 16 / testcases 9 / llvm 7 / integ 2） | `tools/<module>/` |
| 测试向量 | **15** 文件 / **694** cases | `tests/vectors/isa/*.yaml` |
| CodeGen 独立向量 | **15** `.ll`（算术 4 / 访存 4 / 分支 3 / 调用 4） | `tests/codegen/*.ll` + `expected.yaml` + `derive.py`（host oracle） |
| MC lit | **30** 个 `.s` | `tests/lit/MC/Dadao/` |
| E2E lit | **4** 个 `.test` | `tests/lit/E2E/` |
| E2E 汇编 | **4** 个 `.s` | `tests/e2e/` |
| harness | `codegen_crt0.s` + `run_codegen_e2e.py` + QEMU harness 5 脚本 | `tests/scripts/`、`tools/integ/` |
| 最小 ROM 探针 | **20** 个 | `tools/qemu/min_rom_probe_*.py` |
| 教训库 | `.tao/knowledge/lessons.md`（7 章） | `.tao/knowledge/` |

### 2.1 M3 新增 ADR

| ADR | 主题 | 状态 |
|---|---|---|
| 0018 | M3 CodeGen 取舍点 C1–C17（硬双类 / 指针 i64 通吃 / 栈溢出区 / 返回 rb31 / 帧策略 / DataLayout / SelectionDAG / 无 subreg / RB 算术 / call Defs-RegMask 等） | Accepted（用户逐条确认 2026-10-04） |
| `adr-0012 D9` | 新增指令 `sub.o_orrr_dbb`(0x33, `scope:m3`) + 三条既有 RB 算术指令改名/改编码（`add.o_orrr_bbd`(0x30)/`sub.o_orrr_bbd`(0x31)/`cmp.uo_orrr_dbb`(0x32)）+ id 后缀 bank 签名约定 | Accepted（用户 2026-10-04 逐条确认追加） |

### 2.2 补丁规模

| LLVM（48） | QEMU（32） |
|---|---|
| 树形补丁集（`Process-01`，一文件一补丁）；M3 新增 CodeGen 侧：`DADAOSubtarget`/`DADAOISelLowering`/`DADAOISelDAGToDAG`/`DADAOPassConfig`/`DADAOAsmPrinter`/`DADAOMCInstLower`/`DADAOCallingConv.td`、`sub_o_dbb` 定义、M1/FP 合法性加固 | 树形补丁集；M3 新增 `trans_sub_o_orrr_dbb`（`insn.decode` + `trans_arith.c.inc`） |

---

## 3. 过程度量（画像）

> 统计方法：遍历 `.tao/archive/M3/**/*.md`，取「`#### 第 N 轮 reviewer 验收`」小节与「`**Accepted**`/`**Needs Revision**`」判决。可复跑（见 §9.3）。

### 3.1 任务与状态

- 任务总数 **40**（`已验证` 35 + `里程碑` 5）；5 模块全部收敛，**无 `待开始`/`待返工`/`待验收` 残留**（含归档任务 `INTEG-014t` 自身，用户裁定 2026-10-05；`SPEC-096k` 由 `待开始` 置 `已验证` 随 M3 归档）。
- `qemu` 无 M3 任务书（`QEMU-040t`/`041t` 虽标 `M3` 但计入 `qemu` 子目录，共 2 个）。

### 3.2 审阅轮次与打回

| 指标 | 数值 |
|---|---|
| 有 ≥1 次 `Needs Revision` 的任务 | **4 / 40**（`SPEC-097t`、`SPEC-102t`、`LLVM-034t`、`LLVM-045t`） |
| 多数任务 | 1 轮 reviewer 验收即 Accepted |

**打回原因（代表）**：

| 任务 | 问题 |
|---|---|
| `SPEC-097t` | 任务书残留 token（「内联 `Fence`」）且 engineer 假称已获用户确认 → 用户裁定删除该措辞后 Accepted；触发 `lessons.md §7.3` 机制订正 |
| `SPEC-102t` | reviewer 第 1 轮用 `git checkout -- <file>` 全域还原**误回退**其它改动；第 2 轮改逐文件 `cp` 还原 |
| `LLVM-034t` | i64→GPRD 回归判定需用户裁定，改以 `id64` 等价验证，计算型 i64 移 `LLVM-035t` |
| `LLVM-045t` | wyde 位置裸数字未拒绝（`ISS-128`）→ 收紧 predicate |

### 3.3 子代理异常统计（engineer）

| 事件类型 | 处置 |
|---|---|
| 完成区/汇报与真实输出不符 | 主会话/reviewer 实测证伪后退回 |
| 「用户裁定」跨会话可见性 | `lessons §7.3`：子代理须把用户原话写入任务书；主会话不得因父会话无记录否定裁定 |
| 验证产物残留 | `LLVM-048t` 生成物误入 `tests/codegen/`（`ISS-146`）→ scoped `.gitignore` 清理 |

**M3 期间固化的机制**：`lessons §7.3`（用户裁定落盘）、`§7.4`（验证产物残留）；`AGENTS.md`「子代理硬约束」加条（用户裁定落盘）。

---

## 4. 时间线 / 关键路径

### 4.1 分层

```
2026-10-04  M3 重定义 + 规划（SPEC-096k）+ 取舍点判定（ADR-0018）+ adr-0012 D9
2026-10-05  SPEC-101t（RB 三条改名/改槽，跨组件原子）→ SPEC-100t+QEMU-040t（新增 sub.o 原子对）
2026-10-05  构建入口（INFRA-035t）→ LLVM 全链：LLVM-033t → 034t → 043t → 035t → 036t → 037t → 038t → 039t → 040t → 041t
2026-10-05  SPEC-097t（CC 合约）→ LLVM-039t（调用约定）；TESTCASES-026t（独立向量）
2026-10-05  INTEG-012t（E2E + make test-codegen）→ M3 达成
2026-10-05  收官清扫（INFRA-041t）+ 归档前置台账梳理（INFRA-042t）→ 归档（INTEG-014t）
```

### 4.2 重大事件时间线

| 事件 | 说明 |
|---|---|
| **M3 重定义（2026-10-04）** | M3 =「Basic CodeGen（纯整数）」；bank 只 `GPRD`+`GPRB`；`RA`/`RF` 保留不分配；FP/RF codegen、完整调用约定/重定位归 M4 |
| **取舍点固化（`ADR-0018`，2026-10-04）** | C1–C17 经用户逐条确认：硬双类、指针 i64 通吃、栈溢出区全局声明序、返回 `rb31`+callee 扩展、帧策略条件式/SP-only 默认、DataLayout `S128`、SelectionDAG、无 subreg+大端窄访存、RB 算术落 GPRB、call `Defs`+RegMask；C17 只落 `LLVM-037t` 约束 |
| **新增指令（`adr-0012 D9`）** | `sub.o_orrr_dbb`（RB−RB→RD，`ptr−ptr` 终态）+ 三条既有 RB 算术改名/改编码；落地 `SPEC-101t`→`SPEC-100t`+`QEMU-040t`→`LLVM-043t`→`LLVM-035t` |
| **CC 合约落地（`SPEC-097t`）** | `contract-abi.md §4` 由 `Deferred to M2` → 标量调用约定正文；`contracts/abi.yaml` 扩展 |
| **LLVM 全链贯通（`LLVM-033t`~`041t`）** | SelectionDAG CodeGen：双类值类型 → 算术/常数 → load/store → compare/branch → 栈帧 → 调用 → AsmPrinter → 最小重定位 |
| **E2E 门槛达成（`INTEG-012t`）** | `make test-codegen` 15/15；期间发现 MC `br.z/br.nz` bank 缺陷 → `LLVM-049t` 修复 |
| **M3 达成（2026-10-05）** | 5 模块里程碑，`milestones.md` M3 = ✅ 达成 |
| **归档前置（`INFRA-041t`/`042t`）** | 收官 issue 清扫 + `Process-04 §2` 台账梳理（步骤 3–6）；M3 边界项按用户裁定拆分（`ISS-149`/`150`） |

### 4.3 M3 建议执行顺序（`SPEC-096k`）

`INFRA-035t` 最先（否则无 `llc`）；LLVM 全链严格串行；新增/改名指令链 `SPEC-101t → SPEC-100t → {LLVM-043t ∥ QEMU-040t} → LLVM-035t`；`SPEC-097t` 先于 `LLVM-039t`；`TESTCASES-026t` 先于 `INTEG-012t`；`INTEG-012t` 最后。

---

## 5. 关键决策（决策的「为什么」）

| 决策点 | 采用 | 否决 | 理由 |
|---|---|---|---|
| ISel 寄存器模型（`ADR-0018` C1） | 硬双类 `GPRD`/`GPRB` | 联合类 + 软偏好（M68k） | 指针强制落 `GPRB`，CC 可自定义 |
| 指针 value type（C2） | i64 通吃 + `ArgFlags.isPointer()`/`CCIfPtr` 人为约束 | 独立指针 value type | 不改 LLVM 核心 |
| 栈溢出区（C4） | 全局声明序单栈区 | 按 bank 分栈区 | 同 0628/主流 |
| 返回/窄扩展（C5） | 指针→`rb31`；窄返回 callee 扩展 | caller 截断 | 与 ABI 一致 |
| 帧策略（C7） | `hasFPImpl` 条件式；默认 SP-only（`rb1`），必要时 `rb2` | 恒建 FP / 恒 SP-only | 兼顾简单与地址取用 |
| DataLayout（C9） | `E-m:e-p:64:64-i64:64-i128:128-n8:16:32:64-S128` | `S64` / `n64` | 与 ABI 对齐 |
| 指令选择框架（C11） | SelectionDAG | GlobalISel | 复用 0628 已验证路径 |
| 窄类型（C13） | 无 subreg + 提升/扩展；大端窄访存掩码 | 子寄存器模型 | v5 单 64 位寄存器 |
| RB 算术（C14） | 落 `GPRB`（`add.o`/`sub.o`/`cmp.uo` 的 rb 变体） | 通用算术 | v5 spec 0.5.4 全 64 位 |
| call 属性（C16） | `Defs=[rd31,rb31]` + call-preserved RegMask | 不声明 | 否则寄存器分配静默错误（0628 教训） |
| RB 三条改名/改编码（`adr-0012 D9`） | `bbd`/`dbb` bank 签名 + 新槽 0x30–0x33 | 保留旧名 | 消除 `rb` 后缀歧义 |
| 过渡期/重定位（`milestones.md`） | 单 TU + 最小重定位（段内 PCRel `<<2`） | 完整重定位/LLD | 归 M4 |

---

## 6. 死胡同 / 已关闭（避免重试）

| 项 | 处置 | 理由 |
|---|---|---|
| 恒建 FP / `getFrameRegister` 恒返回 `rb2` | 改条件式（C7 D2/D3） | SP-only 默认更简单 |
| `rb2` 在 SP-only 下释放 | 保持 reserved（C7 D6） | 可能为 FP，双保险 |
| `add.o_orrr_bbd` 判为 RB+RB | 订正为 base(rb)+offset(rd)→rb（`LLVM-048t`，用户确认） | 按合约，仅判 base |
| `sub.o` 在 llc 侧继续用 `rb2rd` 组合 | 直选 `sub.o_orrr_dbb`（C14 D4 终态） | 单条指令、语义匹配 |
| `exit` 通道与 fault 区 `0x80–0xFF` 重叠 | 登记 `ISS-147`（建议约束到 `0x00–0x7F`） | `137==0x89==UNDI` false-PASS 风险 |
| FP/RF codegen、完整调用约定/重定位、clang driver | 归 **M4** | 用户 2026-10-04 重划边界 |

---

## 7. 风险与假设台账（M4 会失效的前提）

| # | 假设 | 现状 | M4 影响 |
|---|---|---|---|
| 1 | **单 TU、最小重定位、无链接器** | M3 成立 | 全局变量/跨文件/间接调用需完整重定位（`ISS-008`） |
| 2 | **无 MMU（VA = PA）** | 成立 | 引入地址空间需重评（`contract-mmu.md` deferred） |
| 3 | **完整调用约定未冻结**（`contract-abi.md §6` 5 项 `[OPEN]`） | M3 只实现标量约定 | M4 变参/聚合/多返回/sret（`ISS-005`/`ISS-006`） |
| 4 | **无 FP 独立 oracle / FP 向量** | 未建 | M4 FP codegen 需 `GOLDEN`（`ISS-019`/`ISS-081`） |
| 5 | **无全局变量寻址**（`.data`/`.rodata`/constant pool） | M3 无 | M4 需 constant pool 通路 |
| 6 | **`exit` 码与 fault 区重叠** | `ISS-147` | 完整 fault 可观测前须分离 |
| 7 | **`cpu_loop_exit` 属 QEMU 内部 API** | `ADR-0011` | baseline 升级须复核（`ADR-0002/0008`） |
| 8 | **`decodetree.py` 输出依赖 `PYTHONHASHSEED`** | 上游问题 | 不可 bit-reproducible；对象级 diff 不可作判据 |
| 9 | **大帧 >128K 未实现** | `ISS-138` | 显式失败；M4 可补方案1 |

---

## 8. M4 交接 / 交接清单

### 8.1 M4 定义（`milestones.md`）

**M4 — 未规划**（后续）。顺延项：FP/RF codegen（bank `GPRF`/`rfa`/`rft`、FP 指令 ISel）；**完整调用约定**（变参、聚合 HPA/HFA、多返回值、sret、间接调用，`ISS-005`）；**完整重定位**（`contract-elf.md §2–§4`、relocation 编号/溢出/松弛、LLD，`ISS-008`）；clang targetinfo/driver；全局变量寻址；i128；`select`/`setcc` 完备化。M3 的 `GPRD`/`GPRB`/`GPRD_Allocatable`/`GPRB_Allocatable` 类与 `GPRF`/`GPRA`（non-allocatable）保持不变，M4 直接扩展。

### 8.2 前置阻塞项（M4 规划必须先行）

| # | 项 | 后果 | Issue |
|---|---|---|---|
| 1 | 完整调用约定（`contract-abi §6` 5 项 `[OPEN]`；含间接调用/变参/聚合/多返回/sret） | 变参/聚合/多返回 oracle 缺失 | `ISS-005`/`ISS-006` |
| 2 | 完整重定位（Object ABI D2/D3/D4；未定义/跨-section 符号静默留 0） | 链接阶段缺依据 | `ISS-008`/`ISS-142` |
| 3 | FP 独立 oracle（`GOLDEN`） | FP 期望值无独立派生 | `ISS-019`/`ISS-081` |
| 4 | `exit` 码与 fault 区重叠（`137==0x89==UNDI`） | 完整 fault 可观测前须分离 | `ISS-147` |
| 5 | cfx 指令/别名 MC（`ADR-0017` D5/D6） | cfx 实现缺口 | `ISS-110` |
| 6 | `cs.*` 条件赋值快照（C-27） | 5 条 `cs.*-rd` overlap 未消解 | `ISS-074` |

### 8.3 可复用资产

- **CodeGen E2E**：`tests/scripts/codegen_crt0.s` + `tools/integ/run_codegen_e2e.py` + `Makefile::test-codegen`（fail-closed）
- **独立向量**：`tests/codegen/*.ll` + `expected.yaml` + host oracle（`derive.py`；**禁** LLVM/QEMU 反填）
- **harness**：`tests/scripts/`（raw encoding → loader/test/dumper/exit；`run_qemu_test.py` 只看 `$?`）；`ADR-0009` 方法论
- **lit**：`tests/lit/MC/Dadao/`（`# OBJ:`/`ASM:` 双前缀）、`tests/lit/E2E/`
- **oracle**：`tools/llvm/test_encoding_oracle.py`、`check_lit_bytes.py`、`tools/testcases/009t-audit.py`
- **接口核对**：`tools/integ/check_interface_alignment.py`
- **最小 ROM 探针**：`tools/qemu/min_rom_probe_*.py`（20 个）
- **一键证据脚本**：`.work/evidence/<任务ID>/run.sh`（`INFRA-031t` 规程）
- **CodeGen 补丁**：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（Subtarget/ISel/CallingConv/AsmPrinter/MCInstLower）

### 8.4 建议分解顺序（草案）

1. M4 前置修复（§8.2 的 1–2）
2. FP 独立 oracle（`GOLDEN`）+ FP/RF codegen（`GPRF` 类扩展）
3. 完整调用约定（变参/聚合/多返回/sret/间接调用）
4. 完整重定位 + LLD + 全局变量寻址
5. clang targetinfo/driver + i128 + `select`/`setcc` 完备化

---

## 9. 复现手册

### 9.1 一键命令序列

```bash
make check                    # manifest-check + 各 checker + lit（34）
make check-patch-tree         # 80 patches OK
make test-codegen             # CodeGen E2E（15/15）
.work/build/llvm/bin/llc --version
python3 tools/integ/run_codegen_e2e.py
python3 tools/infra/check_issues.py
python3 tools/integ/check_interface_alignment.py
```

### 9.2 环境坑（血泪清单）

| # | 坑 | 规避 |
|---|---|---|
| 1 | `$?` 被管道/命令替换吞掉 | `cmd > log 2>&1; rc=$?` 或 `${PIPESTATUS[0]}` |
| 2 | 反例注入后未**重建** | 还原须含重建（源码还原 ≠ 二进制还原） |
| 3 | 合并反例注入互相抵消 | 注入须可单独归因 |
| 4 | `git checkout -- <file>` 全域还原误回退 | 逐文件 `cp` 还原（`SPEC-102t` 第 2 轮） |
| 5 | LLVM 23 RegMask 已兜住 `rb31` | 注入改用「去 RegMask」而非去 `Defs`（`LLVM-039t`） |
| 6 | MC AsmParser 条件分支默认按 RD 选变体 | `br.z/br.nz` 按 `Flat[1]` 寄存器类选 RB/RD（`LLVM-049t`） |
| 7 | 验证产物残留（`.s`/`.o`） | 生成物入 scoped `.gitignore`（`ISS-146`） |
| 8 | `validate_vectors` 只查结构不查语义 | 语义须独立 oracle（独立重算 / `-d cpu` / 仓库向量回放） |
| 9 | 补丁集为树形，改动须 `make_patch` 重生成 | 一文件一补丁；`check-patch-tree` / `check-source-state` |

### 9.3 门槛检查详情

| 门槛 | 复算方式 |
|---|---|
| `make test-codegen` | 15 个 `.ll` 经 `llc→llvm-mc→objcopy→qemu` 逐例比对 `expected.yaml` |
| `make check` | `repository checks: PASS`；lit `Total Discovered Tests: 34 / Passed: 34` |
| 补丁数 | `make check-patch-tree` → `2 component(s), 80 patches OK` |
| 台账 | `python3 tools/infra/check_issues.py`（归档后 `35 open / 0 closed`） |
| 过程度量 | 遍历 `.tao/archive/M3/**/*.md`，`re.findall(r"\*\*(Accepted|Needs Revision)\*\*", txt)` |

---

## 10. 术语表 + 文件地图

### 10.1 术语

| 术语 | 含义 |
|---|---|
| Basic CodeGen | M3 主题：`llc` 把标量整数/指针 IR 编成 DADAO 汇编 → obj → QEMU 执行 |
| `GPRD` / `GPRB` | 数据 bank（i64）/ 指针 bank；M3 双 bank 值类型 |
| `RA` / `RF` | 返回地址栈 / 浮点寄存器 bank；M3 仅「保留不分配」 |
| `scope: m3` | M3 新增指令范围（`sub.o_orrr_dbb`，1 条） |
| `SELECT` / `SelectionDAG` | M3 指令选择框架（C11） |
| `hasFPImpl` | 帧指针策略（C7：条件式，默认 SP-only `rb1`） |
| CC / CSR | 调用约定 / callee-saved 寄存器（`ADR-0018` C4/C5/C6/C16） |
| 最小重定位 | 同-section PCRel 符号就地解析 `(target−PC)>>2`（`LLVM-041t`） |
| `ptr−ptr` | 指针差（地址整数差），后端选出 `sub.o_orrr_dbb` |

### 10.2 文件地图

| 路径 | 用途 |
|---|---|
| `AGENTS.md` | 项目规则（**经验规则的唯一准绳**） |
| `.tao/tasks/<module>/` | 任务书（M4 起新建；M3 已归档） |
| `.tao/archive/M3/` | M3 历史归档（任务书 + README + 本文件 + issues-closed） |
| `.tao/knowledge/` | `MEMORY.md` / `milestones.md` / `changelog.md` / `issues.yaml` / `lessons.md` / `contract-*.md` |
| `.tao/adr/` | 架构决策记录（决策层） |
| `spec/` | 规范树（SimRISC-00~12 + DADAO-11~23 + Toolchain-01 + Process-0x） |
| `contracts/` | 机器可读合约（编码表/合法性/ABI/FP 语义） |
| `components/<name>/patches/` | 树形有序补丁集 |
| `tools/<module>/` | 各模块工具脚本 |
| `tests/codegen/` | CodeGen 独立向量（`.ll` + `expected.yaml`） |
| `tests/` | 测试向量 / harness / lit / e2e |
| `.work/` | 一次性工作区（**整体不入库**） |

---

## 11. 审计追溯链

每个 M3 结论都可回溯到「任务 → 审阅轮次 → 命令/log」。指针表：

| 结论 | 任务 | 审阅记录 | 证据（命令 / 日志） |
|---|---|---|---|
| 取舍点 C1–C17 固化 | `ADR-0018` | 用户逐条确认 | `project_M3-codegen-choices.md §5` |
| 新增指令 + RB 三条改名/改编码 | `adr-0012 D9` / `SPEC-100t` / `SPEC-101t` / `LLVM-043t` / `QEMU-040t` | 各轮 | `opcodes.yaml`（228）+ `check-interface` + MC 往返 |
| 标量调用约定合约 | `SPEC-097t` | 2 轮（第 1 轮 Needs Revision） | `contract-abi.md §4` + `contracts/abi.yaml` |
| `llc` 构建入口 | `INFRA-035t` | 1 轮 | `llc --version` 含 dadao |
| CodeGen 全链 | `LLVM-033t`~`041t` | 各轮 | MIR/`.s` 证据 + `check-patch-tree` 80 |
| 有符号窄扩展 | `LLVM-047t` | 1 轮 | `sext_inreg → ext.so` pattern |
| C14 指针算术直选 | `LLVM-048t` | 1 轮 | `add_o_bbd` MIR |
| MC `br.z/br.nz` bank 修复 | `LLVM-049t` | 1 轮 | lit `riii_branch_rb.s` |
| E2E 门槛 15/15 | `INTEG-012t` | 1 轮 | `make test-codegen` |
| 收官 issue 清扫 | `INFRA-041t` | 1 轮 | 证据 9/9 + 注入 6/6 |
| 归档前置台账梳理 | `INFRA-042t` | 1 轮 | `check_issues.py` EXIT=0；判定表 |
| M3 达成 | 5 个 `m` | 核验记录 | `make check` EXIT=0；`milestones.md` M3 = 达成 |

> 历史日志：`.work/log/<module>/<任务ID>-<命令名>.log`（reviewer 重跑加 `-review-`）；M3 收官核验日志见 `.work/log/m3-closure/`。
