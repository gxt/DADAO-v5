# M4 里程碑回顾（Retrospective）

> **定位**：面向 **M5 规划 / 新人上手 / 审计追溯**。本文件**聚合索引**既有材料，**不复制**其明细：
> 状态摘要见 `.tao/knowledge/MEMORY.md`；路线图见 `milestones.md`；变更流水见 `changelog.md`；
> 遗留台账见 `.tao/knowledge/issues.yaml`（issue/待决）与 `.tao/knowledge/lessons.md`（教训/方法论/过程记录）；
> **经验规则以 `AGENTS.md` 为唯一准绳**。
>
> **日期**：2026-10-07 ｜ **范围**：M4（ELF 文件支持 + LLD 链接 + 汇编器遗留收口）
> **归档**：2026-10-07 起本文件随 M4 任务书/台账落入 `.tao/archive/M4/`（历史快照，不再更新）；M4 原始任务书/台账明细见同目录 `README.md`、`issues-closed.md`。

---

## 1. M4 事实快照

### 1.1 定义与门槛

`milestones.md`：**M4 — ELF 文件支持 + LLD 链接 + 汇编器遗留收口**（用户裁定 2026-10-05）。
目的：把工具链从 M3 的「**raw-bin 单 TU 捷径**」升级为「**规范 ELF 产出 + 真实链接**」：
`llc → llvm-mc → ld.lld → ET_EXEC → qemu 直接加载执行`；同时清掉 M1/M2 遗留的**汇编层欠账**。

**四块范围**：① **汇编器遗留**（伪指令〔重定后〕/`.dd.{b08,w16,t32,o64}` 指导符/`-multiple-to-single`/越界立即数**报错**/ABI 寄存器别名）；② **ELF 产出规范**（`ELFObjectWriter` 注册/`e_flags=1`/`e_machine`→dadao/段布局对齐/**全局数据 `.data`/`.rodata`**）；③ **LLD 链接器**（新增 DADAO LLD target：`lld/ELF/Arch/DADAO.cpp`+`Target.{cpp,h}`+`EM_DADAO`/reloc，产 `ET_EXEC`）；④ **QEMU ELF 加载**（解析 `Ehdr`/`Phdr`、按 `VA=PA` 装载 `PT_LOAD`、跳 `e_entry`，替代 `objcopy`+trampoline）。

**门槛**：多 TU `ld.lld → ET_EXEC → qemu` 跑对 + ELF 结构断言（`readelf`/`readobj`）+ 汇编层 MC 用例 + M3 15 向量/多段/多文件经新链路 + 差分 + 负例（畸形 ELF 拒绝、reloc 溢出 link-time error）。`make test-elf` 与 `make test-codegen` **并存**。

**参考基线（用户 2026-10-05 裁定）**：主对标 **RISC-V 64**；次要 **x86-64/AArch64**（LLD/ELF 基础设施与测试组织）；端序参考 **PPC64 BE（+ s390x）**；双 bank 历史参考 **M68K**（退居次要）。
**TDD（自 M4 起）**：先立测试向量/门控、再实现（`spec/Process-05`）；「一能力一向量」、期望值**独立派生自 `spec/`/`contracts/`**。
**明确不含（留后）**：完整调用约定（变参/聚合/sret/多返回/间接）、**FP/RF**、clang 前端、libc/OS/syscall、semihosting 字符输出、golden model。

### 1.2 达成状态

**2026-10-07 达成**（commit `cfcb64d`）。6 个模块里程碑全部置 `里程碑`，`milestones.md` M4 = **✅ 达成**。

| 模块 | 里程碑 | 备注 |
|---|---|---|
| infra | `INFRA-044m` | `INFRA-043t`（LLD 入构建）、`INFRA-045t`（tests 重排）、`INFRA-046t`（产物落点） |
| spec | `SPEC-108m` | `SPEC-105t`/`106t`/`107t`/`109t`/`110t` |
| testcases | `TESTCASES-031m` | `TESTCASES-029t`/`030t`/`032t` |
| llvm | `LLVM-057m` | `LLVM-050t`~`056t`/`058t`/`059t` |
| qemu | `QEMU-043m` | `QEMU-042t`（ELF 加载器） |
| integ | `INTEG-017m` | `INTEG-016t`（多 TU/多段 E2E + `make test-elf`，**M4 门槛达成**） |

### 1.3 最终门槛实测（2026-10-07，真实输出；完整输出见 `.work/log/integ/m4-closure/`）

| 门槛 | 命令 / 证据 | 结果 |
|---|---|---|
| `make test-elf` | `make test-elf` | **EXIT=0**；`Results: 5/5 passed, 0 failed`（多 TU + 多段 + 跨 TU call/全局地址/loop/eq guard/`ptr−ptr`） |
| M3 链不回归 | `make test-codegen` | **EXIT=0**；`Results: 15/15 passed, 0 failed`（raw-bin 并存） |
| `make check` 全绿 | `make check` | **EXIT=0**；`repository checks: PASS`；`check_issues: 34 open, 12 closed` |
| lit | `make check-lit` | **EXIT=0**；`Total Discovered Tests: 60` / `Passed: 60 (100.00%)`（含 CodeGen/DADAO 两条） |
| 补丁集一致 | `make check-patch-tree` | **EXIT=0**；`2 component(s), 89 patches OK`（llvm 57 + qemu 32） |
| QEMU 语义 | `make check-qemu-semantics` | **EXIT=0**；`149 total, 149 passed, 0 failed` |
| 无残留 | `make check-no-residue` | **EXIT=0**；`check-no-residue: PASS` |
| ELF 差分 | M3 15 向量经新 ELF 链 vs raw-bin | **0 分歧** |
| 负例 | 畸形 ELF / reloc 溢出 | 非零退出（link-time error） |
| 台账干净 | `tools/infra/check_issues.py` | **EXIT=0**；归档前 `34 open / 12 closed` → 归档后 `34 open / 0 closed` |

### 1.4 版本 / 组件基线

规范 **SimRISC 0.5.4**（`README.md` 版本表为唯一来源）；`Toolchain 1.1`。
组件锁 `manifests/components.lock.toml`：`llvm-project` commit `6dfe1677ab8dffbc6ec13d53a1e0215d75147689`（llvmorg-23.1.1）；`qemu` commit `c3d48b7d1e89604920e5b81b91140c2ad39a1943`（v11.1.1）；`gem5` `enabled=false`（M4 不变）。

---

## 2. 交付物 / 资产地图

| 类别 | 数量 | 位置 |
|---|---|---|
| M4 任务文件 | **32**（30 M4 终态 + `SPEC-111t` 改判 + `INTEG-018t` 自归档） | `.tao/archive/M4/<module>/`（2026-10-07 归档，原 `.tao/tasks/<module>/`） |
| ADR | **19**（M4 新增 1：`0019`；就地修订 4：`0003`/`0004`/`0012`/`0013`） | `.tao/adr/` |
| 合约叙述 | 8（`contract-isa`/`-abi`/`-elf`/`-fp`/`-asm`/`-asm-list`/`-cfx-aliases`/`contract-*`） | `.tao/knowledge/` |
| 机器可读数据 | `opcodes.yaml`（**227** = 151 m1 + 60 fp + 15 excluded + 1 m3）/ `legality_rules.yaml` / `abi.yaml` / `fp_semantics.yaml` | `contracts/` |
| LLVM 补丁 | **57**（M4 新增 9） | `components/llvm-project/patches/` |
| QEMU 补丁 | **32**（数量不变，`QEMU-042t` 改既有 `dadao-machine.c`） | `components/qemu/patches/` |
| 工具脚本 | **81**（infra 18 / integ 3 / llvm 7 / qemu 26 / spec 16 / testcases 11） | `tools/<module>/` |
| 测试向量 | **15** 文件 / 694 cases（M1 标量 + FP） | `tests/vectors/isa/*.yaml` |
| CodeGen 独立向量 | **25** `.ll`（M3 15 + M4 `m4/` 10：`TESTCASES-030t` 6 + `032t` 4） | `tests/llvm/codegen/`（+`expected.yaml`/`README.md`） |
| MC lit | **54** 个 `.s`（含 M4 7 条 `m4-*.s`） | `tests/llvm/lit/MC/DADAO/` |
| CodeGen lit | **2**（`branch-fold-insert.ll`/`branch-fold-two-way.mir`） | `tests/llvm/lit/CodeGen/DADAO/` |
| E2E lit | **4** 个 `.test` | `tests/e2e/lit/` |
| 独立 oracle | `tools/testcases/validate_mc_vectors.py`（L1）、`validate_elf_vectors.py`（L3）等 | `tools/testcases/`、`.work/evidence/` |
| ELF E2E | `run_elf_e2e.py` + `Makefile::test-elf` + `dadao.lds` + `crt0` | `tools/integ/`、`tests/scripts/` |
| 最小 ROM 探针 | **21** 个（含 `min_rom_probe_042t.py`） | `tools/qemu/` |
| 教训库 | `.tao/knowledge/lessons.md` | `.tao/knowledge/` |

### 2.1 M4 新增 ADR / 就地修订

| ADR / 决策 | 主题 | 状态 |
|---|---|---|
| `ADR-0019` | DADAO M4 重定位类型（**RELA**；`ABS48=0`/`REL26=1`/`REL20=2`/`REL14=3`；`(S+A−P)>>2` **无 −4**；`ABS48` ≤3 片/一律 max 3 片；溢出=link-time error；**禁用 relaxation**） | Accepted（用户逐条确认 2026-10-05） |
| `ADR-0013 D11` | 汇编伪指令集收缩（留 8 条合成型 `set.*`，删 10 条 1:1 别名；`ret` 不加无参；反汇编只显真实指令） | Accepted（用户逐条确认 2026-10-06） |
| `ADR-0012 D3.5` | MISC-AMO 编码调整（删 `illi`；`fence ha 0x01→0x00`；`swym ha 0x02→0x22`；`total 228→227`/`m1 152→151`） | Accepted（用户逐条确认 2026-10-06） |
| `ADR-0004`（rev. 2026-10-06） | `D2.2`/`D2.3` ELF（读 `Ehdr`/`Phdr`、`VA=PA` 装载 `PT_LOAD`、跳 `e_entry`）**+ raw-bin 双路径并存**；段溢出⇒启动报错 | 就地修订（用户逐条确认，`SPEC-107t`） |
| `ADR-0003 §D5`（rev. 2026-10-06） | M4 裸机路径 `dadao.lds` **不使用 `FILEHDR PHDRS`**；`p_offset` 不做要求；`p_align` **目标默认 64 KiB**（可被 `-z max-page-size` 覆写） | 就地修订（用户逐条确认，`SPEC-112t`） |
| `ADR-0016 D6` | 测试产物落点（M4 模块固定路径口径） | 沿用（`INFRA-046t` 落地） |

### 2.2 补丁规模

| LLVM（57） | QEMU（32） |
|---|---|
| 树形补丁集（`Process-01`，一文件一补丁）；M4 新增：`DADAOELFObjectWriter` RELA + 4 类 `getRelocType`；`AsmParser` 伪指令/指导符/`-multiple-to-single`/越界诊断；`GLOBAL_ADDR` 伪指令 + `ABS48` fixup；`lld/ELF/Arch/DADAO.cpp` + `Target.{cpp,h}`；`DADAOInstrInfo` 分支分析 | 树形补丁集；M4 改 `hw/dadao/dadao-machine.c`（ELF 加载 + raw-bin 保留 + over-size 守卫）；`SPEC-109t` 同步 `insn.decode`/`trans_ctrl` |

---

## 3. 过程度量（画像）

> 统计方法：遍历 `.tao/archive/M4/**/*.md`，取「`#### 第 N 轮 reviewer 验收`」小节与「`**Accepted**`/`**Needs Revision**`」判决。

### 3.1 任务与状态

- 任务总数 **32**（`已验证` 26 + `里程碑` 6）；6 模块全部收敛，**无 `待开始`/`待返工`/`待验收` 残留**（含归档任务 `INTEG-018t` 自身，用户裁定 2026-10-07）。
- `SPEC-111t`：`项目里程碑` 由 `M3` 改判为 `M4`（用户裁定 2026-10-07），随 M4 归档（`RM`）。

### 3.2 审阅轮次与打回

| 指标 | 数值 |
|---|---|
| 有 ≥1 次 `Needs Revision` 的任务 | **1 / 32**（`INFRA-046t`） |
| 有 **2 轮** reviewer 验收的任务 | **3**（`INTEG-016t`〔第 1 轮验收**作废**〕、`LLVM-058t`、`SPEC-112t`） |
| 多数任务 | 1 轮 reviewer 验收即 Accepted |

**打回/返工（代表）**：

| 任务 | 问题 |
|---|---|
| `INTEG-016t` | 第 1 轮验收因 reviewer 用 `git checkout` 还原注入、清掉 `m4-pseudo-set.s` **未提交改动**而**作废**；engineer 重做后第 2 轮重新验收 Accepted（触发 2026-10-06 流程规则） |
| `INFRA-046t` | 证据脚本 `git status` 中文路径转义 → 改 `-c core.quotePath=false` 后 Accepted |
| `SPEC-112t` | 引用须带完整标题方可过 `check-spec-refs`（64 KiB 普通页实为 `DADAO-12 §2.2.2`） |

### 3.3 子代理异常统计（engineer/reviewer）

| 事件类型 | 处置 |
|---|---|
| 反例注入用 `git checkout` 还原致未提交改动被清 | **2026-10-06 流程规则**：禁 `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账，或临时树注入；`git status` 干净**不作**「已还原」证据 |
| 「用户裁定」跨会话可见性 | `lessons §7.3`：子代理须把用户原话写入任务书；主会话不得因父会话无记录否定裁定 |

**M4 期间固化的机制**：「提交分档」（architect 本地提交 / 主会话 `squash` 后 push）、「反例注入还原纪律」（`AGENTS.md` 子代理硬约束 +10/+11、`command/{dispatch,complete}.md`）。

---

## 4. 时间线 / 关键路径

### 4.1 分层

```
2026-10-05  M4 定义（ELF + LLD + 汇编器遗留收口，用户裁定）+ ADR-0019（reloc：RELA）
2026-10-06  M4 规划（SPEC-104k，21 任务书）+ Process-05（TDD）+ ADR-0013 D11 + ADR-0012 D3.5
2026-10-06  M4 链首 SPEC-109t（删 illi / fence→0x00 / swym→0x22，跨组件原子）
2026-10-06  spec 层：SPEC-105t（reloc 正文）→ SPEC-106t（伪指令收缩）→ SPEC-110t（落点路径）→ SPEC-107t（ADR-0004 调整）
2026-10-06  LLVM 全链（严格串行）：050t→051t→052t→053t→054t→055t→056t→058t→059t
2026-10-06  infra：INFRA-043t（LLD 入构建）→ INFRA-045t（tests 重排）→ INFRA-046t（落点）；QEMU-042t（ELF 加载器）
2026-10-06  向量：TESTCASES-029t（L1）→ 030t（L3）→ 032t（not/neg）
2026-10-06  INTEG-016t（多 TU/多段 E2E + make test-elf）→ M4 门槛达成
2026-10-07  归档前置台账梳理（bdbcfd2）+ SPEC-111t（SimRISC 0.5.3 归档收口）→ M4 达成（cfcb64d）→ 归档（INTEG-018t）
```

### 4.2 重大事件时间线

| 事件 | 说明 |
|---|---|
| **M4 定义（2026-10-05）** | M4 =「ELF 文件支持 + LLD 链接 + 汇编器遗留收口」；主对标 RISC-V 64；TDD 起用 |
| **重定位类型固化（`ADR-0019`）** | RELA + `ABS48/REL26/REL20/REL14`、无 −4、禁用 relaxation；落地 `SPEC-105t`（正文）→ `LLVM-050t`（writer）→ `LLVM-056t`（LLD） |
| **MISC-AMO 编码调整（`ADR-0012 D3.5`）** | 删 `illi`、`fence`→`0x00`、`swym`→`0x22`；跨组件原子 `SPEC-109t`（M4 链首） |
| **汇编器遗留落地** | `LLVM-051t`（伪指令展开）、`052t`（`.dd.*`）、`053t`（`-multiple-to-single`）、`054t`（越界立即数报错） |
| **全局数据 + ELF 产出** | `LLVM-055t`（`.data`/`.rodata` lower + `ABS48`/RELA fixup） |
| **LLD 链接器贯通** | `INFRA-043t`（入构建）→ `LLVM-056t`（DADAO LLD target + `dadao.lds`）→ `LLVM-058t`（去 `FILEHDR PHDRS` + 64 KiB 页） |
| **QEMU ELF 加载（`QEMU-042t`）** | `Ehdr`/`Phdr` 解析 + `VA=PA` 装载 + `e_entry`；raw-bin 路径保留 |
| **E2E 门槛达成（`INTEG-016t`）** | `make test-elf` 5/5；期间修复 L1 向量接入 + `ISS-152` |
| **M4 达成（2026-10-07）** | 6 模块里程碑，`milestones.md` M4 = ✅ 达成 |
| **归档前置（bdbcfd2）** | `Process-04 §3` 台账梳理：6 结案 + 8 rescale M5 + 3 moot + `ISS-149/150`→`160/161` + `ISS-047`→M5 |

### 4.3 M4 建议执行顺序（`SPEC-104k`）

`SPEC-109t` 最先（编码原子，跨组件）；LLVM 链严格串行 `050t→051t→052t→053t→054t→055t→056t`；`SPEC-105t`/`106t` 先于 LLVM；`INFRA-045t` 先于 `TESTCASES`/`INFRA-046t`；`QEMU-042t` 可并行；`INTEG-016t` 最后。

---

## 5. 关键决策（决策的「为什么」）

| 决策点 | 采用 | 否决 | 理由 |
|---|---|---|---|
| 重定位模型（`ADR-0019`） | **RELA**（`SHT_RELA`，显式 `r_addend`） | `SHT_REL`（隐式 addend） | 显式 addend 无歧义、便于大端与分片核对；0628 先例 |
| PCRel 公式（`ADR-0019`） | `(S+A−P)>>2`，**v5 无 −4** | 沿用 RISC-V 的 `−4` 偏置 | v5 指令语义无该偏置；实现与 `LLVM-056t` 独立手算一致 |
| `ABS48` 表示 | 指令 3×`immu16` / **数据 8 字节字段**两编码，一律 max 3 片 | 区分指令/数据不同编号 / 启用 relaxation | 用户 2026-10-06 澄清「不区分指令/数据」；relaxation 留后禁用 |
| reloc 溢出 | **link-time error**（不截断） | 静默截断 / 环绕 | 静默截断会掩盖错误 |
| reloc 0 号哨兵（`ISS-153`） | DADAO ctor 显式设 `iRelSymbolicRel=R_DADAO_NUM` | 沿用 LLD 默认 0 | `R_DADAO_ABS48=0` 与默认哨兵冲突 ⇒ 被误判 IRELATIVE 拒绝 |
| 伪指令集（`ADR-0013 D11`） | 留 8 条合成型，删 10 条 1:1 别名 | 保留全部 18 条 | 别名无信息量；反汇编只显真实指令 |
| `FILEHDR PHDRS`（`ADR-0003 §D5`） | **不用**（头/程序头表只在文件中） | 加 `FILEHDR PHDRS` / 加载器放行头部页 / `.text` 抬 64 KiB | 去之则首段回 RAM 内，根除「头部页落 RAM 之下」问题；LLD 能力原样保留 |
| `p_align`（`ADR-0003 §D5`） | **目标默认 64 KiB**（可 `-z max-page-size` 覆写） | 硬编码不变式 | 目标默认、非硬约束 |
| ELF 加载（`ADR-0004` rev） | ELF（`Ehdr`/`Phdr`/`e_entry`）**+ raw-bin 双路径并存** | 仅 ELF（弃 raw-bin） | 保 M3 `test-codegen` 不回归 |
| tests 组织（`INFRA-045t`） | 组件先行（`tests/llvm/{lit,codegen}` + `tests/e2e` + `tests/qemu`） | 保持扁平 `tests/lit`/`tests/codegen` | 对齐上游 `llvm/test/{MC,CodeGen,tools}` |
| 产物落点（`INFRA-046t`） | 模块固定路径 `tests/llvm/codegen-e2e/`（`ADR-0016 D6`） | `.work/log/integ/` | M4 口径；M5 起迁 `.dadao/tests/` |

---

## 6. 死胡同 / 已关闭（避免重试）

| 项 | 处置 | 理由 |
|---|---|---|
| `SHT_REL`（隐式 addend） | 改 **RELA** | 显式 addend 无歧义（`ADR-0019`） |
| `FILEHDR PHDRS` 保留头进 guest | 去之（`SPEC-112t`/`LLVM-058t`） | 头/程序头表不必进内存；首段回 RAM |
| LLD 默认 0 值哨兵直接吃 `ABS48=0` | 显式设 `iRelSymbolicRel` 哨兵（`ISS-153`） | 否则 abs48 被误拒 |
| `TargetInstrInfo::insertBranch` 缺席 | 补齐（`LLVM-059t`，修 `ISS-158`） | 否则 loop+eq-guard 组合 `llc` SIGABRT 134 |
| 用 `git checkout` 还原注入 | 禁；改 `cp`+md5（2026-10-06 规则） | 会清掉未提交改动，致验收作废（`INTEG-016t`） |
| 未定义/跨 section 引用静默留 0 | 落 relocation（`LLVM-050t`，`ISS-008`/`142`） | 静默 0 掩盖错误 |
| M4 后端 lower `not`/`neg` 未走 `xnor.o`/`sub.sX` | 登记 `ISS-159`（不阻断） | 语义正确、编码路径不同；属优化/后端议题 |

---

## 7. 风险与假设台账（M5 会失效的前提）

| # | 假设 | 现状 | M5 影响 |
|---|---|---|---|
| 1 | **无 MMU（VA = PA）** | 成立 | 引入地址空间需重评（`contract-mmu.md` deferred） |
| 2 | **裸机、无 libc/OS/syscall** | 成立 | semihosting/系统调用需另建（M4 不含） |
| 3 | **完整调用约定未冻结**（`contract-abi.md §6` 5 项 `[OPEN]`） | M4 未扩展 | 变参/聚合/多返回/sret/间接调用（`ISS-005`/`006`，M5） |
| 4 | **FP/RF codegen 未做 / 无 FP 独立 oracle** | M4 未含 | FP/RF ISel + `GOLDEN`（`ISS-019`/`081`，M5） |
| 5 | **`exit` 码与 fault 区重叠**（`137==0x89==UNDI`） | `ISS-147` open | 完整 fault 可观测前须分离 |
| 6 | **`decodetree.py` 输出依赖 `PYTHONHASHSEED`** | `ISS-058` open | 对象级 diff 不可作判据 |
| 7 | **`REL12`（load/store 相对寻址）未加** | `ISS-151`/`161` open | 需新增第 5 类 reloc（须 ADR 逐条确认） |
| 8 | **`contract-isa` 投影层残留已删伪指令 + `impact-matrix` 悬空 + `check_spec_codeblocks` 陈旧** | `ISS-160` open | 建议另立 spec/tools 任务刷新 |
| 9 | **M4 后端 `not`/`neg` 优化路径缺口** | `ISS-159` open | 优化/CSE 议题 |
| 10 | **安装布局（install）尚未落地**（`ADR-0016`） | M5 起步待办 | M5 起按 install 根取可执行；生成物迁 `.dadao/` |

---

## 8. M5 交接 / 交接清单

### 8.1 M5 起步待办（用户裁定 2026-10-06）

1. **install 落地**：`ADR-0016 D1–D11`——host 工具链 → `.dadao/cross-toolchain`（D3/D4/D11）、target sysroot → `.dadao/dadao-unknown-elf`（D5）、`manifests/` 单一真源定位（D7，禁硬编码）、门控/执行器改从 install 根取可执行、`.work/` 仅作 build 区（D9）；保留「从源码可重建」。
2. **生成物落点迁移**（判据：能配置解决 ⇒ 必进 `.dadao/`）：① `test-codegen` 产物 `tests/llvm/codegen-e2e` → `.dadao/tests/codegen-e2e`；② `test-elf` 产物 → `.dadao/tests/elf-e2e`；③ lit `test_exec_root` → `.dadao/tests/lit-output/<name>`。**`.work/log`/`.work/evidence` 不动**。

### 8.2 前置阻塞项（M5 规划必须先行）

| # | 项 | 后果 | Issue |
|---|---|---|---|
| 1 | 完整调用约定（`contract-abi §6` 5 项 `[OPEN]`；变参/聚合/多返回/sret/间接调用） | 变参/聚合 oracle 缺失 | `ISS-005`/`ISS-006` |
| 2 | FP/RF codegen + FP 独立 oracle（`GOLDEN`） | FP 期望值无独立派生 | `ISS-019`/`ISS-081` |
| 3 | `exit` 码与 fault 区重叠（`137==0x89==UNDI`） | 完整 fault 可观测前须分离 | `ISS-147` |
| 4 | 特权 cfx 指令/别名 MC（`ADR-0017` D5/D6） | cfx 实现缺口 | `ISS-110` |
| 5 | `cs.*` 条件赋值快照（C-27） | 5 条 `cs.*-rd` overlap 未消解 | `ISS-074` |
| 6 | 结果级/imm 语义独立 oracle（golden model） | imm 语义无守卫 | `ISS-019`/`ISS-026` |

### 8.3 可复用资产

- **ELF E2E**：`tools/integ/run_elf_e2e.py` + `Makefile::test-elf` + `tests/scripts/dadao.lds`（fail-closed：`llc→llvm-mc→ld.lld→qemu -kernel`，逐例比对）
- **CodeGen E2E**：`tools/integ/run_codegen_e2e.py` + `Makefile::test-codegen`（raw-bin，M3 起步）
- **独立向量 + oracle**：`tests/llvm/lit/MC/DADAO/m4-*.s`（`validate_mc_vectors.py` 65 条）、`tests/llvm/codegen/m4/`（`validate_elf_vectors.py`；**禁** LLVM/QEMU 反填）
- **LLD target**：`components/llvm-project/patches/lld/ELF/{Arch/DADAO.cpp,Target.cpp,Target.h}` + `tests/scripts/dadao.lds`
- **QEMU ELF 加载**：`components/qemu/patches/hw/dadao/dadao-machine.c` + `tools/qemu/min_rom_probe_042t.py`
- **lit**：`tests/llvm/lit/{MC,CodeGen,tools}/DADAO/`（`%llc`/`%FileCheck`）、`tests/e2e/lit/`
- **oracle**：`tools/llvm/test_encoding_oracle.py`、`check_lit_bytes.py`
- **接口核对**：`tools/integ/check_interface_alignment.py`
- **一键证据脚本**：`.work/evidence/<任务ID>/run.sh`（`INFRA-031t` 规程）

### 8.4 建议分解顺序（草案）

1. M5 起步：install（`ADR-0016`）+ 生成物落点迁移
2. 完整调用约定（变参/聚合/多返回/sret/间接调用）+ ABI `[OPEN]` 收口
3. FP/RF codegen + `GOLDEN` 独立 oracle
4. cfx / LR-SC / `cs.*` 快照 + `REL12` reloc
5. clang 前端 / libc·OS·syscall / semihosting

---

## 9. 复现手册

### 9.1 一键命令序列

```bash
make check                    # manifest-check + 各 checker + lit（60）
make check-patch-tree         # 89 patches OK
make test-elf                 # ELF E2E（5/5）
make test-codegen             # raw-bin E2E（15/15）
make check-qemu-semantics     # QEMU 语义（149/149）
make check-no-residue
python3 tools/infra/check_issues.py
python3 tools/integ/check_interface_alignment.py
```

### 9.2 环境坑（血泪清单）

| # | 坑 | 规避 |
|---|---|---|
| 1 | `$?` 被管道/命令替换吞掉 | `cmd > log 2>&1; rc=$?` 或 `${PIPESTATUS[0]}` |
| 2 | 反例注入后未**重建** | 还原须含重建（源码还原 ≠ 二进制还原） |
| 3 | `git checkout -- <file>` 全域还原误回退 / 清掉未提交改动 | 逐文件 `cp` + md5 对账（`INTEG-016t` 教训） |
| 4 | 自定义 reloc 含 0 编号 | 显式设 `iRelSymbolicRel` 哨兵（`ISS-153`） |
| 5 | `FILEHDR PHDRS` 使头落 RAM 下方 | 去之（`ADR-0003 §D5`/`LLVM-058t`） |
| 6 | LLVM 23 `RegMask` 已兜住 `rb31` | 注入改用「去 RegMask」而非去 `Defs` |
| 7 | `decodetree.py` 输出依赖 `PYTHONHASHSEED` | 不可 bit-reproducible；对象级 diff 不可作判据 |
| 8 | `validate_*` 只查结构不查语义 | 语义须独立 oracle（独立重算 / `-d cpu` / 仓库向量回放） |
| 9 | 补丁集为树形，改动须 `make_patch` 重生成 | 一文件一补丁；`check-patch-tree` / `check-source-state` |
| 10 | 源码引用须带完整小节标题 | `check-spec-refs`（如 `DADAO-12 §2.2.2`） |

### 9.3 门槛检查详情

| 门槛 | 复算方式 |
|---|---|
| `make test-elf` | 多 TU 经 `llc→llvm-mc→ld.lld→qemu -kernel` 逐例比对 guest 退出码（5 例） |
| `make check` | `repository checks: PASS`；`check_issues: 34 open, 12 closed`（归档后 0 closed） |
| `make check-lit` | `Total Discovered Tests: 60 / Passed: 60` |
| 补丁数 | `make check-patch-tree` → `2 component(s), 89 patches OK` |
| 台账 | `python3 tools/infra/check_issues.py`（归档后 `34 open / 0 closed`） |
| 过程度量 | 遍历 `.tao/archive/M4/**/*.md`，`re.findall(r"\*\*(Accepted|Needs Revision)\*\*", txt)` |

---

## 10. 术语表 + 文件地图

### 10.1 术语

| 术语 | 含义 |
|---|---|
| ELF E2E | M4 主题：多 TU `llc→llvm-mc→ld.lld→ET_EXEC→qemu` 端到端 |
| `R_DADAO_ABS48` / `REL26` / `REL20` / `REL14` | M4 四类重定位（`ABS48=0` 等） |
| `SHT_RELA` | 带显式 addend 的重定位节（vs `SHT_REL`） |
| `dadao.lds` | DADAO 链接脚本（地址布局依 `ADR-0004`；段序 `.text→.rodata→.data→.bss`） |
| `GLOBAL_ADDR` | 全局地址材料化伪指令（展开为 3 片 `set.zw_rb`/`or.w_rb` + `ABS48`） |
| `-multiple-to-single` | 汇编器把 `ldm.*`/`stm.*` 拆为单寄存器序列的选项 |
| `FILEHDR PHDRS` | LLD 使头/程序头表占用首段地址空间的选项；M4 裸机路径不用 |
| `p_align` | 段对齐；M4 目标默认 64 KiB |
| L1/L2/L3 | `Process-05` 三层测试（L1 编码 / L2 CodeGen 结构 / L3 执行） |
| 独立 oracle | 期望值由 `spec/`/`contracts/` 独立派生（禁从 `llc`/QEMU 反填） |

### 10.2 文件地图

| 路径 | 用途 |
|---|---|
| `AGENTS.md` | 项目规则（**经验规则的唯一准绳**） |
| `.tao/tasks/<module>/` | 任务书（M5 起新建；M4 已归档） |
| `.tao/archive/M4/` | M4 历史归档（任务书 + README + 本文件 + issues-closed） |
| `.tao/knowledge/` | `MEMORY.md` / `milestones.md` / `changelog.md` / `issues.yaml` / `lessons.md` / `contract-*.md` |
| `.tao/adr/` | 架构决策记录（决策层） |
| `spec/` | 规范树（SimRISC-00~12 + DADAO-11~23 + Toolchain-01 + Process-0x） |
| `contracts/` | 机器可读合约（编码表/合法性/ABI/FP 语义） |
| `components/<name>/patches/` | 树形有序补丁集 |
| `tools/<module>/` | 各模块工具脚本 |
| `tests/llvm/{lit,codegen}/` | MC/CodeGen 向量；`tests/e2e/`、`tests/scripts/`（harness/`dadao.lds`） |
| `.work/` | 一次性工作区（**整体不入库**） |

---

## 11. 审计追溯链

每个 M4 结论都可回溯到「任务 → 审阅轮次 → 命令/log」。指针表：

| 结论 | 任务 / 决策 | 审阅记录 | 证据（命令 / 日志） |
|---|---|---|---|
| 重定位类型（RELA/编号/无 −4） | `ADR-0019` / `SPEC-105t` | 用户逐条确认 | `contract-elf §2–§4` |
| ELF writer RELA + 4 类 reloc | `LLVM-050t` | 1 轮 | `.rela.text`=`SHT_RELA`；`readobj -r` |
| LLD target + `dadao.lds` | `LLVM-056t` | 1 轮 | `readobj -h`（`ET_EXEC`/`0xDA0`/`flags=1`） |
| 去 `FILEHDR PHDRS` + 64 KiB 页 | `SPEC-112t` / `LLVM-058t` | 2 轮 | 无 `PT_LOAD` 越界；`p_align=0x10000` |
| MISC-AMO 编码调整 | `ADR-0012 D3.5` / `SPEC-109t` | 1 轮 | `swym 0`=`77 88 00 00`；`check-interface` |
| 伪指令收缩 | `ADR-0013 D11` / `SPEC-106t` / `LLVM-051t` | 1 轮 | `Toolchain-01 §6`；`check-asm-*` |
| QEMU ELF 加载 | `QEMU-042t` | 1 轮 | 探针 22/22；`cpu_set_pc(e_entry)` |
| L1 MC 向量 + oracle | `TESTCASES-029t` | 1 轮 | oracle 65/65；`validate_mc_vectors.py` |
| L3 执行向量 + oracle | `TESTCASES-030t` | 1 轮 | 42/30/126 三方一致 |
| `not`/`neg` 功能向量 | `TESTCASES-032t` | 1 轮 | L1 5 条 + L3 108/8 |
| 分支分析/插入/删除（修 `ISS-158`） | `LLVM-059t` | 1 轮 | `llc` 134→0；执行级 30/1/30 |
| E2E 门槛 5/5 | `INTEG-016t` | 2 轮（第 1 轮作废） | `make test-elf` |
| M4 达成 | 6 个 `m` | 核验记录 | `.work/log/integ/m4-closure/`；`milestones.md` M4 = 达成 |
| 归档前置台账梳理 | bdbcfd2（主会话） | —— | `Process-04 §3`；`check_issues.py` |

> 历史日志：`.work/log/<module>/<任务ID>-<命令名>.log`（reviewer 重跑加 `-review-`）；M4 收官核验日志见 `.work/log/integ/m4-closure/`。

**M4 重定义（2026-10-05，用户裁定）**：M4 定为 **「ELF 文件支持 + LLD 链接 + 汇编器遗留收口」**——把工具链从 M3 的「raw-bin 单 TU 捷径」升级为**规范 ELF 产出 + 真实链接**，并清掉 M1/M2 遗留的汇编层欠账。**四块范围**：① **汇编器遗留**（伪指令〔**重定后**〕/`.dd.{b08,w16,t32,o64}` 指导符/`-multiple-to-single`/越界立即数**报错**/ABI 寄存器别名，见 `contract-asm §6/§7/§8/§11`）；② **ELF 产出规范**（`ELFObjectWriter` 注册/`e_flags=1`/`e_machine`→dadao/段布局对齐/**全局数据 `.data`/`.rodata`**，`ISS-038/039/047/117`）；③ **LLD 链接器**（新增 DADAO LLD target：`lld/ELF/Arch/DADAO.cpp`+`Target.{cpp,h}`+`EM_DADAO`/reloc，产 `ET_EXEC`；`ISS-008`；0628 先例）；④ **QEMU ELF 加载**（解析 `Ehdr`/`Phdr`、按 `VA=PA` 装载 LOAD 段、跳 `e_entry`，替代 `objcopy`+trampoline；`ADR-0004` 扩展）。**门槛**：多 TU `ld.lld → ET_EXEC → qemu` 跑对 + ELF 结构断言（`readelf`/`readobj`）+ 汇编层 MC 用例 + M3 15 向量/多段/多文件经新链路 + 差分 + 负例（畸形 ELF 拒绝、reloc 溢出 link-time error）。**参考基线（2026-10-05 用户裁定）**：**主对标 RISC-V 64**（完整工具链/软件系统总纲）；**次要 x86-64/AArch64**（LLD/ELF 基础设施与测试组织）；**端序参考 PPC64 BE（+ s390x）**（64 位大端完整栈）；**双 bank 历史参考 M68K**（BE、32 位，退居次要）。**TDD**：本里程碑起采用**测试驱动开发**（先测试向量/门控、再实现），并需**完善测试向量**（MC 向量 + CodeGen 向量 + 执行向量；**移植对象 = 上述参考**：借鉴其测试**结构**，编码/期望值按 DADAO spec **独立派生**）。**前置（待判）**：重定位类型（`contract-elf §2–§4`）→ **ADR**；伪指令重定 → **spec 修订**；测试向量范围 → **待细化**。**明确不含（留后）**：完整调用约定（变参/聚合/sret/多返回/间接）、**FP/RF**、clang 前端、libc/OS/syscall、semihosting 字符输出、golden model。分解待立（`SPEC-1xxk` 规划任务）。
**M4 达成（2026-10-07，主会话实测核验）**：门槛 `make test-elf` **5/5**；6 个模块 `m`（`SPEC-108m`/`INFRA-044m`/`LLVM-057m`/`QEMU-043m`/`TESTCASES-031m`/`INTEG-017m`）全部置 `里程碑`；`make check`/`check-lit`(60/60)/`test-codegen`(15/15)/`test-elf`/`check-no-residue`/`check-patch-tree`(89)/`check-qemu-semantics` 全 EXIT=0（`.work/log/integ/m4-closure/`）。前置 `SPEC-105t` 补置已验证；`SPEC-111t` 归档收口。M4 任务书归档见下（`Process-04 §3`，同 M1–M3 体例）。
**归档（2026-10-07）**：M4 的 32 个任务书已归档至 `.tao/archive/M4/`（按模块子目录）；M4 时期 changelog（28 条）/MEMORY（1 行）内容见 `.tao/archive/M4/README.md`；**M4 回顾见 `.tao/archive/M4/m4-retrospective.md`**；`issues.yaml` 的 12 条 M4 阶段 closed 项见 `.tao/archive/M4/issues-closed.md`。
**M4 — ELF 文件支持 + LLD 链接 + 汇编器遗留收口**（规划中）

目的：把工具链从 M3 的「**raw-bin 单 TU 捷径**」升级为「**规范 ELF 产出 + 真实链接**」：`llc → llvm-mc → ld.lld → ET_EXEC → qemu 直接加载执行`；同时清掉 M1/M2 遗留的**汇编层欠账**（伪指令/指导符/汇编器选项/诊断）。

范围：① 汇编器遗留；② ELF 产出规范（含全局数据段）；③ LLD 链接器（**含链接脚本 `dadao.lds`**：地址布局依 **`ADR-0004`**〔RAM 基址 `0xffff_0000_0000` 作 `.text`/entry；段序 `.text→.rodata→.data→.bss`〕、段对齐依 `contract-elf §5`、M4 路径 `dadao.lds` **不使用 `FILEHDR PHDRS`**（头/程序头表只在文件中，不进 guest 内存）、`p_align` **目标默认 64 KiB（可被 `-z max-page-size` 覆写）**）；④ QEMU ELF 加载。**参考**：主对标 **RISC-V 64**；端序参考 **PPC64 BE（+ s390x）**；双 bank 历史参考 **M68K**。

门槛：多 TU `ld.lld → ET_EXEC → qemu` 跑对；ELF 结构断言；汇编层 MC 用例；M3 向量 + 多段 + 多文件经新链路通过 + 差分；负例（畸形 ELF / reloc 溢出）。

**范围外（留 M5+）**：完整调用约定（变参/聚合/sret/多返回/间接）、FP/RF codegen、clang 前端、libc/OS/syscall、semihosting 字符输出、golden model（结果级独立 oracle）。

**前置 ADR**：重定位类型（`contract-elf §2–§4`，`e_flags[7:0]=1` namespace）。**可能需调整 `ADR-0004`**（ELF 的 `e_entry` / 段布局 / 加载约定；当前为 flat-binary 双镜像）。

**reloc/fixup 坑预防（M4 硬约束，源自 `DADAO-0628` 实录）**：① fixup **必须尊重 `IsResolved`**（禁写预链接原始值）；② same-section「快速路径」不可靠则**删掉、退回真重定位**；③ **`rb0`（= 当前 PC）禁作基址/零**；④ 跳转表/间接跳转目标标签**必须显式发射**；⑤ 大常量**不得折入**受限立即数/relocation 字段（先材料化）。

**测试策略（`spec/Process-05` TDD）**：**L1（MC）+ L3（执行）为主、L2（CodeGen 结构）极简**；「**一能力一向量**」（规模 ∝ 能力）；移植**只借结构**、期望值**独立派生自 `spec/`**、**手写少量不批量迁移**；每条向量须能对反例失败。**已定前置**：重定位类型 = `ADR-0019`（Accepted；RELA，`ABS48/REL26/REL20/REL14`，v5 无 −4，一律 max 3 片，禁用 relaxation）；伪指令集收缩 = `ADR-0013 D11`（只留合成型 8 条，删 10 条别名）。
