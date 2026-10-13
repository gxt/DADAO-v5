# M2 里程碑回顾（Retrospective）

> **定位**：面向 **M3 规划 / 新人上手 / 审计追溯**。本文件**聚合索引**既有材料，**不复制**其明细：
> 状态摘要见 `.tao/knowledge/MEMORY.md`；路线图见 `milestones.md`；变更流水见 `changelog.md`；
> 遗留台账见 `.tao/knowledge/issues.yaml`（issue/待决）与 `.tao/knowledge/lessons.md`（教训/方法论/过程记录）；
> **经验规则以 `AGENTS.md` 为唯一准绳**。
>
> **日期**：2026-10-04 ｜ **范围**：M2（规范与接口冻结 / Normative Freeze）
> **归档**：2026-10-04 起本文件随 M2 任务书/台账落入 `.tao/archive/M2/`（历史快照，不再更新）；M2 原始任务书/台账明细见同目录 `README.md`、`issues-closed.md`。

---

## 1. M2 事实快照

### 1.1 定义与门槛

`milestones.md`：**M2 — 规范与接口冻结（Normative Freeze）**
目的：`spec/`（0.5.4）→ 投影（`contracts/*`、`contract-*.md`）→ checker 三层**机械一致**；FP **实现侧**收口（执行层 + 合法性）；偏离台账成型。为 M3 codegen 提供稳定契约。

门槛：① `make check` 全绿（所有 checker + 反例门控）；② 投影表「缺口」清零或显式 deferred；③ `spec_cite`/引用/计数全对齐；④ FP = 执行层 60/60 + `dst_rd0@FP` + **最小 FP smoke**；⑤ 偏离台账（6 项，见 `MEMORY.md`）。

**范围外（归 M3）**：FP 独立 oracle（`GOLDEN`）、FP 向量（`TESTCASES-024t`）、完整语义 E2E。

### 1.2 达成状态

**2026-10-04 达成**（commit `4753fe2`）。6/6 模块里程碑全部置 `里程碑`，`milestones.md` M2 = **✅ 达成**。

| 模块 | 里程碑 | 备注 |
|---|---|---|
| spec | `SPEC-095m` | M2 收官项之一 |
| testcases | `TESTCASES-025m` | |
| infra | `INFRA-034m` | |
| llvm | `LLVM-032m` | |
| qemu | `QEMU-039m` | |
| integ | `INTEG-011m` | M2 收官项之一 |

> **M2 重定义（2026-10-04，用户裁定）**：M2 定为「规范与接口冻结」，原「Basic CodeGen」顺延为 **M3**；**取消「过渡期任务 `M<i>→M<i+1>`」类别**——原 `M1→M2` 任务一律提升为 `M2`（推翻 2026-09-25 决议；不立 ADR）。故 M2 任务书含 2026-09-23 起的「过渡期」任务，共 **150 个**。

### 1.3 最终门槛实测（2026-10-04，真实输出；完整输出见 `.work/log/integ/INTEG-010t-*.log`）

| 门槛 | 命令 / 证据 | 结果 |
|---|---|---|
| ① `make check` 全绿 | `make check` | **EXIT=0**；`repository checks: PASS`；lit **31/31** |
| ② 投影表「缺口」清零或显式 deferred | `spec/README.md` 投影表：`Toolchain-01`①=`contract-asm.md`（`SPEC-091t`）；`DADAO-12/13/22/23`①=`deferred`（`SPEC-092t`）；`Process-02` 三者 =`deferred` | **满足**（4 项，见 §9.3） |
| ③ `spec_cite` / 引用 / 计数全对齐 | `make check-spec-refs` | **EXIT=0**；Check1 680 引用 / 0 失败、Check2 0（76→0，`SPEC-094t`） |
| ④ FP = 执行层 60/60 + `dst_rd0@FP` + 最小 smoke | `min_rom_probe_03{4,5,6,7}t` = 59/77/113/91 全 PASS；`_038t` = 42/42；`smoke_fp.test` PASS | **满足** |
| ⑤ 偏离台账 6 项 | `.tao/knowledge/MEMORY.md` `## 上游 ↔ v5 偏离台账` | **恰好 6 行**（`SPEC-093t`） |

### 1.4 版本 / 组件基线

规范 **SimRISC 0.5.4**（`README.md` 版本表为唯一来源）；`Toolchain 1.1`（汇编语言，`SPEC-091t`）。
组件锁 `manifests/components.lock.toml`：`llvm-project` commit `6dfe1677ab8dffbc6ec13d53a1e0215d75147689`（llvmorg-23.1.1）；`qemu` commit `c3d48b7d1e89604920e5b81b91140c2ad39a1943`（v11.1.1）；`gem5` `enabled=false`。

---

## 2. 交付物 / 资产地图

| 类别 | 数量 | 位置 |
|---|---|---|
| M2 任务文件 | **150**（已验证 142 + 里程碑 8） | `.tao/archive/M2/<module>/`（2026-10-04 归档，原 `.tao/tasks/<module>/`） |
| ADR | **17**（M2 新增 6：`0012`~`0017`） | `.tao/adr/` |
| 合约叙述 | 7（`contract-isa`/`-abi`/`-elf`/`-fp`/`-asm`/`-asm-list`/`-cfx-aliases`） | `.tao/knowledge/` |
| 机器可读数据 | `opcodes.yaml`（227 = 152 m1 + 60 fp + 15 excluded）/ `legality_rules.yaml`（16 规则）/ `abi.yaml` / `fp_semantics.yaml` | `contracts/` |
| LLVM 补丁 | **37** | `components/llvm-project/patches/` |
| QEMU 补丁 | **32** | `components/qemu/patches/` |
| 工具脚本 | **79**（infra 18 / qemu 27 / spec 15 / testcases 9 / llvm 8 / integ 2） | `tools/<module>/` |
| 测试向量 | **15** 文件 / **694** cases | `tests/vectors/isa/*.yaml` |
| MC lit | **27** 个 `.s` | `tests/lit/MC/Dadao/` |
| E2E lit | **4** 个 `.test` | `tests/lit/E2E/` |
| E2E 汇编 | **4** 个 `.s` | `tests/e2e/` |
| harness | 5 个 Python + trampoline | `tests/scripts/` |
| 最小 ROM 探针 | **19** 个 | `tools/qemu/min_rom_probe_*.py` |
| `make` 目标 | **39** | `Makefile` |
| 教训库 | `.tao/knowledge/lessons.md`（7 章 / 27 节） | `.tao/knowledge/` |

### 2.1 M2 新增 ADR

| ADR | 主题 | 状态 |
|---|---|---|
| 0012 | SimRISC 0.5.4 更新落地（含 D7 RA 语义） | Accepted（rev. 2026-09-30） |
| 0013 | 汇编语法（双目的 / 多寄存器块） | Accepted |
| 0014 | `fence` 移出 M1 | Accepted |
| 0015 | 0 号寄存器作源语义 | Superseded by ADR-0012（并入 D3.1/D5） |
| 0016 | DADAO 安装布局 | Accepted |
| 0017 | cfx 汇编别名 | Accepted |

### 2.2 补丁规模

| LLVM（37） | QEMU（32） |
|---|---|
| 树形补丁集（`Process-01`，一文件一补丁）；含 FP 编码层 `DADAOInstrInfoFP.td`、AsmParser 静态合法性、反汇编器等 | 树形补丁集；`target/dadao/insn_trans/` 10 个 `.c.inc`（M1）+ `trans_fp.c.inc`（M2，60 条 FP）；`helper.c` 接入上游 softfloat |

---

## 3. 过程度量（画像）

> 统计方法：遍历 `.tao/archive/M2/**/*.md`，取「判决 … Needs Revision / Accepted」行与「第 N 轮」小节（可复跑，见 §9.3）。

### 3.1 任务与状态

- 任务总数 **150**（`已验证` 142 + `里程碑` 8）；6 模块全部收敛，**无 `待开始`/`待返工`/`待验收` 残留**（含归档任务 `INTEG-010t` 自身，用户裁定 2026-10-05）。

### 3.2 审阅轮次与打回

| 指标 | 数值 |
|---|---|
| 判决 `Accepted` 次数 | **89** |
| 判决 `Needs Revision` 次数 | **45** |
| 有 ≥1 次打回的任务 | **28 / 150（19%）** |
| 打回次数分布 | 0 次：122 ｜ 1 次：19 ｜ 2 次：6 ｜ 4 次：2 ｜ 6 次：1 |

**打回最多**：

| 任务 | 打回 | 备注 |
|---|---|---|
| `SPEC-069t` | 6 | 窄位宽精简 + 高位值语义 |
| `SPEC-068t` | 4 | MISC-AMO 编码变更 |
| `TESTCASES-020t` | 4 | RA 向量重写（推翻 M1 已验收期望值） |
| `QEMU-030t` / `QEMU-031t` / `SPEC-016t` / `SPEC-039t` / `SPEC-076t` | 2 | 各含返工 |

### 3.3 打回原因分类（按频次）

| 类别 | 典型表现 | 代表任务 |
|---|---|---|
| **验证无判别力** | 恒真断言、两支写同一结果、只打印不判定 | `QEMU-033t`（三类注入）、`TESTCASES-023t`（validator 只查结构不查语义） |
| **完成区/汇报不实** | 报 PASS 而实测 FAIL；数字与环境不符 | `SPEC-068t`/`069t`、`SPEC-089t` |
| **反例注入无效/抵消** | 注入未落点、合并注入互相抵消 | `QEMU-035t`（合并注入） |
| **状态/结构与门控错** | 生成器死代码、门控假阴性 | `SPEC-094t`（rule b/c 放宽致假阴性） |
| **还原不含重建** | 源码还原但二进制仍旧 | `LLVM-031t`（规则已固化：还原须含重建） |

### 3.4 子代理异常统计（engineer）

| 事件类型 | 处置 |
|---|---|
| 空返回（产出已落盘） | 查落盘 → 续会话 |
| 完成区/汇报与真实输出不符 | 主会话实测证伪后退回 |
| 同类缺陷反复（假绿/恒真） | 规则固化入 `AGENTS.md`「验证脚本反例门控」「修复须修一类」 |

**M2 期间固化的规则**：一键证据脚本规程（`INFRA-031t`）、reviewer 审阅记录三要素（`INFRA-029t`）、「留证须捕获被检命令自身退出码」「还原须含重建」「探针值构造须回读校验」「反例注入须可复原+注入有效性」。

---

## 4. 时间线 / 关键路径

### 4.1 分层

```
2026-09-23  补丁集树形化（Process-01）           ── infra 基础
2026-09-28  contract-isa 重组（SPEC-016t/018t/019t）── spec 基线
2026-09-29~30  新汇编格式落地 + cfx 记法 + RA 语义（ADR-0012）── spec 冻结
2026-10-01  编码/语义收口（div/rem、AMO、窄位宽→227）
2026-10-02  门控化（rule_refs、合法性清单/漂移）+ 文档分层（ADR-0017）
2026-10-03  FP 范围口径 + 合约层 + 合法性归并（SPEC-086t~088t）
2026-10-04  FP 执行层收口（LLVM/QEMU/SPEC）+ check-spec-refs 消解 + 偏离台账 + 最小 FP E2E → M2 达成
```

### 4.2 重大事件时间线

| 事件 | 说明 |
|---|---|
| **补丁集树形化（2026-09-23）** | `Process-01` 生效：树形补丁集 + 一文件一补丁 + `git apply`；`check-patch-tree` 入 `make check` |
| **新汇编格式落地（2026-09-29~30）** | `SimRISC-01~12` 正文改新汇编格式；双目的/多寄存器块；cfx 记法（ADR-0013/0017） |
| **RA 语义修订（2026-09-30）** | `ADR-0012 D7`：`ra0` = `RACNT`+`MRPTR`；`TESTCASES-020t` 重写 RA 向量；`ADR-0015` 并入 |
| **编码收口（2026-10-01）** | 编码 251→**227**（`SPEC-069t`）；MISC-AMO `0000-0000`→`0111-0111`（`SPEC-068t`） |
| **FP 范围口径（2026-10-03）** | `scope ∈ {m1,fp,excluded}`（227 = 152+60+15）；`check-scope` 门控；原生浮点路线（否决 soft-float libcall） |
| **文档分层（2026-10-03）** | `spec/`＝规范树、`.tao/adr/`＝决策层、`.tao/knowledge/`＝投影+台账；`spec/README.md` 投影表 |
| **FP 执行层 60/60（2026-10-03~04）** | QEMU `trans_fp.c.inc` 60 条真实 TCG（16+10+20+14）；LLVM 编码层+汇编期合法性；运行期 `dst_rd0` ILLI |
| **M2 重定义（2026-10-04）** | M2=规范与接口冻结；取消过渡期任务类别；107 原 `M1→M2` 任务提升为 M2 |
| **M2 达成（2026-10-04）** | 6/6 模块里程碑，`milestones.md` M2 = ✅ 达成 |

### 4.3 M2 建议执行顺序（`milestones.md`）

按门槛收口：② `SPEC-091t`（asm 合约）+ `SPEC-092t`（三缺口 deferred）→ ③ `SPEC-030t`/`SPEC-033t`/`TESTCASES-014t` + `SPEC-094t` → ④ `INTEG-009t`（最小 FP smoke）→ ⑤ `SPEC-093t`（偏离台账）→ ①/归档 `INTEG-010t`。

---

## 5. 被否决的备选方案（决策的「为什么」）

| 决策点 | 采用 | 否决 | 理由 |
|---|---|---|---|
| 浮点实现路线（`SPEC-086t`，用户 2026-10-03 裁定） | 原生浮点（`scope: fp` 60 条，全工具链） | soft-float libcall（0628 路线） | 需端到端浮点语义；soft-float 依赖 libcall 语义且不注册 FP 寄存器类 |
| 过渡期任务类别（2026-10-04，用户裁定） | 取消，原 `M1→M2` 任务提升为 M2 | 保留独立 `M1→M2` 类别 | 里程碑只是大任务标志，非推进阻碍 |
| FP 合法性规则（`SPEC-088t`） | 归并**共享 `mreg_*`**（RF 28 条、源+目的双侧） | `SPEC-087t` 的独立 `fp_mreg_*`（漏源侧、与 M1 规则重复） | 单一真源、重叠禁则统一为「有交集 ⇒ ILLI」 |
| FP `decode` 语义（`SPEC-089t` R1） | 方案 B：`scope: fp` 不携带 `decode` | 保留 `decode: fp` | 收缩为仅 `excluded` 保留 `decode: ILLI`（15 条） |
| FP rd-目的 `dst_rd0`（`SPEC-089t` R2b） | 方案 A：全补 15 条（含 `rf2rd`） | 仅补部分 | 与汇编期/运行期实现对齐（`LLVM-031t`/`QEMU-038t`） |
| cfx 记法投影（`SPEC-085t` T2） | cfx 约定入 `Toolchain-01 §13`；取消 Toolchain-02 | 新建独立 Toolchain-02 | 复用现有册，减少文档分册 |
| 文档分层 ADR 落点（`SPEC-084t`） | `.tao/adr/`（决策层） | 留 `.tao/knowledge/`（投影层混放） | 决策与投影分层清晰 |
| 窄位宽精简（`SPEC-069t`） | 编码 251→227（M1 176→152） | 保留冗余编码 | 精简 + 高位值语义统一 |

---

## 6. 死胡同 / 已关闭（避免重试）

| 项 | 处置 | 理由 |
|---|---|---|
| 过渡期任务 `M<i>→M<i+1>` 类别 | **取消**（2026-10-04） | 里程碑不是推进阻碍；原任务提升为 M2 |
| `LLVM-016t`（汇编 MC 语法支持） | **关闭删除**（2026-10-04，用户裁定） | 已由 `LLVM-017t`~`020t` 覆盖；沿用 `LLVM-010t` 先例「删文件、编号留空」 |
| `SPEC-032t` | **关闭删除**（2026-10-04，用户裁定） | 已由前置任务消解 |
| `ADR-0015`（0 号寄存器作源） | **Superseded** | D1–D4 并入 `ADR-0012` D3.1/D5 |
| `fp_mreg_*` 独立规则 | 删除，改共享 `mreg_*` | 与 M1 规则重复且漏源侧 |
| `deferred.md`（散文台账） | 并入 `issues.yaml` / `lessons.md`，删除（`INFRA-032t`） | 台账结构化，教训分离 |
| 0628 的「`jump` 目标 = 下一条 + imm*4」 | 不采用 | v5 `contract-isa §5.3`：基址 = 分支指令**自身**地址 |

---

## 7. 风险与假设台账（M3 会失效的前提）

| # | 假设 | 现状 | M3 影响 |
|---|---|---|---|
| 1 | **单 TU、无重定位、无链接器** | M2 成立 | M3 codegen 仍为 freestanding 单 TU；完整重定位/链接属后续（`ISS-008`） |
| 2 | **无 MMU（VA = PA）** | 成立 | 引入地址空间需重评（`contract-mmu.md` deferred） |
| 3 | **`DADAOFrameLowering::hasFPImpl` 未覆写** | M2 未实例化故安全 | **M3 codegen 首次实例化会编译失败**（`ISS-040`，阻塞项） |
| 4 | **完整调用约定未冻结** | `contract-abi.md §6` 5 项 `[OPEN]` | M3 codegen 的 oracle（`ISS-005`/`ISS-006`） |
| 5 | **无 FP 独立 oracle** | FP 执行层 60/60 已实现，但期望值无独立派生 | M3 前须建 `GOLDEN` 独立 oracle（`ISS-019`/`ISS-081`） |
| 6 | **无 FP 向量 / 完整语义 E2E** | 仅最小 `smoke_fp` | M3 含（`TESTCASES-024t`、`ISS-081`） |
| 7 | **`cpu_loop_exit` 属 QEMU 内部 API** | `ADR-0011` | baseline 升级时须复核（`ADR-0002/0008`） |
| 8 | **`decodetree.py` 输出依赖 `PYTHONHASHSEED`** | 上游问题 | 不可 bit-reproducible；对象级 diff 不可作判据 |

---

## 8. M3 交接 / 交接清单

### 8.1 M3 定义（`milestones.md`）

**M3 — Basic CodeGen**：`llc` 将标量整数/指针函数（LLVM IR）编译为 DADAO 汇编，经 MC → obj → 链接 → QEMU 执行结果正确（freestanding、same-TU，不含变参/聚合）。门槛：`make test-codegen` 全绿，至少一个算术/访存/分支/调用函数端到端在 QEMU 得到期望结果。**含**（自 M2 顺延）：FP 独立 oracle、FP 向量、完整语义 E2E。

### 8.2 前置阻塞项（M3 规划必须先行）

| # | 项 | 后果 | Issue |
|---|---|---|---|
| 1 | `DADAOFrameLowering::hasFPImpl` 未覆写 | M3 首次实例化编译失败 | `ISS-040` |
| 2 | 完整调用约定（`contract-abi §6`） | CodeGen oracle 缺失 | `ISS-005`/`ISS-006` |
| 3 | 重定位（Object ABI D2/D3/D4） | 链接阶段缺依据 | `ISS-008` |
| 4 | FP 独立 oracle（`GOLDEN`） | FP 期望值无独立派生 | `ISS-019`/`ISS-081` |
| 5 | LLVM MC 的 cfx 指令/别名（`ADR-0017` D5/D6） | cfx 实现缺口 | `ISS-110` |
| 6 | `cs.*` 条件赋值快照（C-27） | 5 条 `cs.*-rd` overlap 未消解 | `ISS-074` |

### 8.3 可复用资产

- **harness**：`tests/scripts/`（raw encoding → loader/test/dumper/exit；`run_qemu_test.py` 只看 `$?`）；`ADR-0009` 方法论
- **E2E**：`tests/lit/E2E/`（`%llvm_mc`/`%llvm_objcopy`/`%qemu`/`%trampoline`/`timeout`）
- **lit**：`tests/lit/MC/Dadao/`（`# OBJ:`/`ASM:` 双前缀模板）
- **oracle**：`tools/llvm/test_encoding_oracle.py`、`check_lit_bytes.py`、`tools/testcases/009t-audit.py`
- **接口核对**：`tools/integ/check_interface_alignment.py`
- **最小 ROM 探针框架**：`tools/qemu/min_rom_probe_*.py`（19 个）
- **一键证据脚本**：`.work/evidence/<任务ID>/run.sh`（`INFRA-031t` 规程）
- **FP 合约/门控**：`contract-fp.md`、`contracts/fp_semantics.yaml`、`check_fp_contract.py`

### 8.4 建议分解顺序（草案）

1. M3 前置修复（§8.2 的 1–3）
2. FP 独立 oracle（`GOLDEN-001t` 起，按 `docs/fp-oracle-design.md`）+ FP 向量（`TESTCASES-024t`）
3. `llc` CodeGen 骨架（FrameLowering / InstrInfo / ISel 最小集）
4. `make test-codegen` 门控 + 至少 1 个端到端函数
5. 逐族扩展（算术 → 访存 → 分支 → 调用）+ 完整语义 E2E

---

## 9. 复现手册

### 9.1 一键命令序列

```bash
make check                    # manifest-check + validate-vectors + 各 checker + lit（31）
make check-spec-refs          # spec 引用审计（Check1/Check2）
.work/build/llvm/bin/llvm-lit tests/lit/MC/Dadao/ tests/lit/E2E/
python3 tools/qemu/min_rom_probe_034t.py   # FP 执行层探针（034~038）
python3 tools/integ/check_interface_alignment.py
python3 tools/infra/check_issues.py
```

### 9.2 环境坑（血泪清单）

| # | 坑 | 规避 |
|---|---|---|
| 1 | `$?` 被管道/命令替换吞掉 | `cmd > log 2>&1; rc=$?` 或 `${PIPESTATUS[0]}` |
| 2 | 反例注入后未**重建** | 还原须含重建（源码还原 ≠ 二进制还原） |
| 3 | 合并反例注入互相抵消 | 注入须可单独归因 |
| 4 | `add.si` 仅 18 位，不能构造任意 64 位值 | 用 `set.zw` + `or.w`，并回读校验 |
| 5 | 分支偏移/极性易错（本模块多次事故） | 「目标 = 分支指令 + 偏移」全文件逐条核对 + 令比较值错 → FAIL 的实测 |
| 6 | `validate_vectors` 只查结构不查语义 | 语义须独立 oracle（独立重算/`-d cpu`/仓库向量回放） |
| 7 | 补丁集为树形，改动须 `make_patch` 重生成 | 一文件一补丁；`check-patch-tree` / `check-source-state` |

### 9.3 门槛检查详情

| 门槛 | 复算方式 |
|---|---|
| ② | `grep -n '缺口\|deferred' spec/README.md`；4 项清单：`Toolchain-01`① / `DADAO-12`① / `DADAO-13`① / `DADAO-22/23`① = `deferred` |
| ③ | `make check-spec-refs`（Check1 680/0、Check2 0） |
| ⑤ | `awk`/`grep` 统计 `MEMORY.md` `## 上游 ↔ v5 偏离台账` 数据行 = 6 |
| 过程度量 | 遍历 `.tao/archive/M2/**/*.md`，`re.findall(r"判决[^\n]{0,60}(Accepted|Needs Revision)", txt)` |

---

## 10. 术语表 + 文件地图

### 10.1 术语

| 术语 | 含义 |
|---|---|
| 规范与接口冻结 | M2 主题：`spec/` → 投影 → checker 三层机械一致 |
| `scope` | 指令范围：`m1` / `fp` / `excluded`（227 = 152+60+15） |
| `rule_refs` / `dst_rd0` / `mreg_*` | 合法性规则与引用（`contracts/legality_rules.yaml`） |
| FP 执行层 60/60 | `scope: fp` 60 条指令在 QEMU 全实现（`trans_fp.c.inc`） |
| 投影表 | `spec/README.md`：每册规范 → ①叙述合约 ②机器数据 ③门控 ④可执行 |
| 树形补丁集 | `Process-01`：一文件一补丁，路径化（非按序编号堆叠） |
| 偏离台账 | `MEMORY.md` 的 6 项上游↔v5 规范偏离登记 |

### 10.2 文件地图

| 路径 | 用途 |
|---|---|
| `AGENTS.md` | 项目规则（**经验规则的唯一准绳**） |
| `.tao/tasks/<module>/` | 任务书（M3 起新建；M2 已归档） |
| `.tao/archive/M2/` | M2 历史归档（任务书 + README + 本文件 + issues-closed） |
| `.tao/knowledge/` | `MEMORY.md` / `milestones.md` / `changelog.md` / `issues.yaml` / `lessons.md` / `contract-*.md` |
| `.tao/adr/` | 架构决策记录（决策层） |
| `spec/` | 规范树（SimRISC-00~12 + DADAO-11~23 + Toolchain-01 + Process-0x） |
| `contracts/` | 机器可读合约（编码表/合法性/ABI/FP 语义） |
| `components/<name>/patches/` | 树形有序补丁集 |
| `tools/<module>/` | 各模块工具脚本 |
| `tests/` | 测试向量 / harness / lit / e2e |
| `.work/` | 一次性工作区（**整体不入库**） |

---

## 11. 审计追溯链

每个 M2 结论都可回溯到「任务 → 审阅轮次 → 命令/log」。指针表：

| 结论 | 任务 | 审阅记录 | 证据（命令 / 日志） |
|---|---|---|---|
| 编码收口 227 = 152+60+15 | `SPEC-069t`/`SPEC-086t` | 多轮 | `contracts/opcodes.yaml` + `check-scope` |
| RA 语义修订 | `SPEC-062t`/`TESTCASES-020t` | 多轮 | `ADR-0012 D7` + RA 向量重写 |
| FP 范围口径与门控 | `SPEC-086t` | `SPEC-086t` | `check_scope.py` |
| FP 语义合约 | `SPEC-087t` | ± | `contract-fp.md` + `contracts/fp_semantics.yaml` |
| FP 合法性归并 | `SPEC-088t` | ± | `legality_rules.yaml` 16 规则 + `check_fp_contract` |
| FP 合法性 `rule_refs` 回填 | `SPEC-089t` | ± | `opcodes.yaml`（310/190） |
| `check-spec-refs` 76→0 | `SPEC-094t` | 2 轮 | `make check-spec-refs`（680/0） |
| 偏离台账 6 项 | `SPEC-093t` | ± | `MEMORY.md` 偏离台账节 |
| FP 执行层 60/60 | `QEMU-034t`~`037t` | 各轮 | 探针 59/77/113/91 |
| FP 汇编期合法性 | `LLVM-030t`/`031t` | 各轮 | lit + `.work/evidence/` |
| FP 运行期 `dst_rd0` | `QEMU-038t` | ± | 探针 42/42 |
| 最小 FP E2E | `INTEG-009t` | ± | `smoke_fp.test`（E2E 4/4） |
| M2 达成 | `INTEG-011m` 等 6 `m` | 核验记录 | `make check` EXIT 0；`milestones.md` M2 = 达成 |

> 历史日志：`.work/log/<module>/<任务ID>-<命令名>.log`（reviewer 重跑加 `-review-`）；`.tao/logs/` **已废弃**。

**M2 重定义（2026-10-04，用户裁定）**：M2 定为「**规范与接口冻结（Normative Freeze）**」，原「Basic CodeGen」顺延为 **M3**；并**取消「过渡期任务 `M<i>→M<i+1>`」类别**——原 `M1→M2` 任务一律提升为 `M2`（**推翻** 2026-09-25 决议；不立 ADR）。
**M2 达成（2026-10-04，architect 实测核验）**：M2 门槛 5 条全部满足、各模块 M2 任务均终态 ⇒ 6 个模块 `m` 置 `里程碑`、M2 置 `达成`。核验记录见下「M2 达成核验记录」。
**归档（2026-10-04）**：M2 的 150 个任务书已归档至 `.tao/archive/M2/`（按模块子目录）；M2 时期 changelog（61 条）/MEMORY（45 行 + 2 段落）内容见 `.tao/archive/M2/README.md`；**M2 回顾见 `.tao/archive/M2/m2-retrospective.md`**；`issues.yaml` 的 41 条 M2 阶段 closed 项见 `.tao/archive/M2/issues-closed.md`。
## M2 达成核验记录

**日期**：2026-10-04　**执行**：architect 实测（命令原样 + 退出码；完整输出见 `.work/log/integ/M2-milestone-make-check.log`、`.work/log/spec/M2-milestone-check-spec-refs.log`、`.work/log/qemu/M2-milestone-probe-03{4..8}t.log`）

| # | 门槛 | 命令 / 证据 | 结果 |
|---|------|-------------|------|
| ① | `make check` 全绿（所有 checker + 反例门控） | `make check` | **EXIT=0**；`repository checks: PASS`；lit 31/31 |
| ② | 投影表「缺口」清零或显式 deferred | `contract-asm.md` 已补齐（`SPEC-091t`）；`DADAO-12/13/22/23` ①列 = `deferred`（`SPEC-092t`）；`Process-02` 三者 = `deferred` | **满足**（4 项） |
| ③ | `spec_cite` / 引用 / 计数全对齐 | `make check-spec-refs` | **EXIT=0**；Check1 680 引用 / 0 失败、Check2 0（76→0，`SPEC-094t`） |
| ④ | FP = 执行层 60/60 + `dst_rd0@FP` + 最小 smoke | `min_rom_probe_03{4..7}t` = 59/77/113/91 全 PASS；`_038t` = 42/42；`smoke_fp.test` PASS | **满足** |
| ⑤ | 偏离台账 6 项 | `.tao/knowledge/MEMORY.md` `## 上游 ↔ v5 偏离台账` | **恰好 6 行**（`SPEC-093t`） |

**各模块 M2 `m`**：`INFRA-034m`、`SPEC-095m`、`TESTCASES-025m`、`LLVM-032m`、`QEMU-039m`、`INTEG-011m`。

**M2 任务终态**：wave 1/2 全部 `已验证`；唯一非终态 M2 任务 = `INTEG-010t`（M2 达成**后**执行的归档收尾，非达成分解）。

**归档前置**：`INFRA-033t`（`Process-04 §3` 台账梳理；原 §2，2026-10-06 顺延）`已验证`；M2 任务书归档由 `INTEG-010t` 在 M2 达成后执行。

> **caveat（非阻断，交主会话复核）**：投影表仍存 3 处字面 `缺口`——`SimRISC-07` 行 ④列 `缺口`（FP oracle/向量待建，2026-10-04 M3 重定义后属 **M4**，未加 `deferred` 字样）、`DADAO-12` 行 ②④列 `缺口（据实）`（据实、无需独立投影）。按 `SPEC-090k` 对门槛②的 4 项界定为满足；若要字面清零，建议将 `SimRISC-07 ④` 改标 `deferred（M3）`（需改 `spec/README.md`，超出本次核验写范围）。
**M2 — 规范与接口冻结（Normative Freeze）**

目的：`spec/`（0.5.4）→ 投影（`contracts/*`、`contract-*.md`）→ checker 三层**机械一致**；FP **实现侧**收口（执行层 + 合法性）；偏离台账成型。为 M3 codegen 提供稳定契约。

门槛：① `make check` 全绿（所有 checker + 反例门控）；② 投影表「缺口」清零或显式 deferred；③ `spec_cite`/引用/计数全对齐；④ FP = 执行层 60/60 + `dst_rd0@FP` + **最小 FP smoke**；⑤ 偏离台账（6 项，见 `MEMORY.md`）。

**范围外（2026-10-04 M3 重定义后改归 M4）**：FP 独立 oracle（`GOLDEN`）、FP 向量（`TESTCASES-024t`）、完整语义 E2E。
