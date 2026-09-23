# M1 里程碑回顾（Retrospective）

> **定位**：面向 **M2 规划 / 新人上手 / 审计追溯**。本文件**聚合索引**既有材料，**不复制**其明细：
> 状态摘要见 `.tao/knowledge/MEMORY.md`；路线图见 `milestones.md`；变更流水见 `changelog.md`；
> 遗留台账见 `.tao/knowledge/deferred.md` 与 `docs/issues.yaml`；规范影响见 `docs/impact-matrix.md`；
> 仓库布局见 `docs/repository-layout.md`；**经验规则以 `AGENTS.md` 为唯一准绳**。
>
> **日期**：2026-09-22 ｜ **范围**：M1（LLVM MC + QEMU 标量核心 + MC↔QEMU 集成）

---

## 1. M1 事实快照

### 1.1 定义与门槛

`milestones.md`：**M1 — MC + QEMU 标量核心 + MC↔QEMU 集成**
目的：`llvm-mc` 能汇编/反汇编全部 M1 指令；`qemu-system-dadao` 能在 MMU-off 裸机模式执行标量程序；独立测试向量经「MC 汇编 → QEMU 执行 → 结果比对」一致，形成 MC↔QEMU 集成闭环。
门槛：`make build-mc` / `build-qemu` / `test-interface` 全绿。

### 1.2 达成状态

**2026-09-22 达成**（用户确认）。6/6 模块里程碑全部置 `里程碑`，`milestones.md` M1 = **✅ 达成**。

| 模块 | 里程碑 | 备注 |
|---|---|---|
| spec | `SPEC-011m` | |
| testcases | `TESTCASES-012m` | 由 `010m`→`011m`→`012m` 两次顺延 |
| infra | `INFRA-014m` | 由 `013m` 顺延 |
| llvm | `LLVM-015m` | 由 `013m`→`014m`→`015m` 两次顺延 |
| qemu | `QEMU-021m` | |
| integ | `INTEG-004m` | M1 收官项 |

### 1.3 最终门槛实测（2026-09-22，真实输出）

| 门槛 | 结果 |
|---|---|
| `make check` | **EXIT 0**（`repository checks: PASS`） |
| `llvm-lit tests/lit/MC/Dadao/ tests/lit/E2E/` | **25/25 (100%)**（MC 22 + E2E 3） |
| `tools/testcases/validate_vectors.py` | `178/178 M1 identities covered OK; 15 data files, 747 cases; data coverage gaps: 0` |
| QEMU harness 全量 batch | `747 total / 739 passed / 0 failed / 8 deferred / 0 errors` |
| `tools/integ/check_interface_alignment.py` | **80/80/0、EXIT 0**（跨模块接口零不一致） |
| `tools/infra/check_issues.py` | `66 open, 8 closed (0 blocking M1-gate: 0)` |
| `tools/llvm/check_lit_bytes.py` | `53 patterns OK` |
| `tools/llvm/test_encoding_oracle.py` | `68/68 passed` |
| `tools/qemu/check_qemu_trans.py` | `256/256 insns have trans impl (M1 178/178)` |
| `make build-mc` / `build-qemu` | PASS（实测参考值，随环境浮动：LLVM 追加单目标 ~53 s；QEMU 干净重建 ~13 m） |

### 1.4 版本/组件基线

规范 `SimRISC 0.5.3`；`AEE / ABI 0.9.2`；`SEE / SBI 0.7.1`；`HEE / HBI 0.1.2`（`README.md` 版本表为唯一来源）。
组件锁：`manifests/components.lock.toml`（LLVM / QEMU 以精确 commit 锁定，不用 tag/branch）。

---

## 2. 交付物 / 资产地图

| 类别 | 数量 | 位置 |
|---|---|---|
| 任务文件 | **76**（已验证 70 + 里程碑 6） | `.tao/tasks/<module>/` |
| ADR | **11**（+ `adr-authoring.md` 规范） | `.tao/knowledge/adr-*.md` |
| 合约 | `contract-isa` / `-abi` / `-elf`（+ `contract-authoring` 规范） | `.tao/knowledge/` |
| 机器可读数据 | `opcodes.yaml`（256 = 178 M1 + 78 excluded）/ `legality_rules.yaml` / `abi.yaml` | `contracts/` |
| LLVM 补丁 | **8**（`0001`–`0008`） | `components/llvm-project/patches/` |
| QEMU 补丁 | **8**（`0001`–`0008`） | `components/qemu/patches/` |
| 工具脚本 | **44**（infra 11 / qemu 15 / testcases 8 / llvm 6 / spec 3 / integ 1） | `tools/<module>/` |
| 测试向量 | **15** 文件 / **747** cases（`isa/*.yaml`） | `tests/vectors/` |
| MC lit | **22** 个 `.s` | `tests/lit/MC/Dadao/` |
| E2E lit | **3** 个 `.test` + `lit.cfg.py` | `tests/lit/E2E/` |
| E2E 汇编 | **3** 个 `.s` | `tests/e2e/` |
| harness | **4** 个 Python + trampoline | `tests/scripts/` |
| QEMU 最小 ROM 探针 | **9** 个（`005t`–`013t`、`022t`） | `tools/qemu/min_rom_probe_*.py` |
| 文档 | 布局 / 影响矩阵 / 接口对齐清单 / 审计记录 / 本文件 | `docs/` |

### 补丁清单

| LLVM | QEMU |
|---|---|
| `0001-dadao-triple-registration` | `0001-dadao-target-skeleton` |
| `0002-dadao-target-skeleton` | `0002-dadao-decodetree` |
| `0003-dadao-register-info` | `0003-dadao-rd-arith` |
| `0004-dadao-instrinfo` | `0004-dadao-load-store` |
| `0005-dadao-asmparser` | `0005-dadao-translate-split` |
| `0006-dadao-disassembler` | `0006-dadao-ctrl-flow` |
| `0007-wyde-position-operand-parser` | `0007-dadao-ra-semantics` |
| `0008-dadao-elf-e_flags` | `0008-dadao-tb-chain-fix` |

### ADR 索引

| ADR | 主题 | 状态 |
|---|---|---|
| 0001 | Greenfield 重建 | Accepted |
| 0002 | Manifest 驱动的构建编排 | Accepted |
| 0003 | M1 Object ABI（ELF 头字段与段/流水线） | Accepted（rev. 2026-09-13 `e_flags` 版本字段） |
| 0004 | M1 裸机测试机（Test Machine） | Accepted（rev. 2026-09-13 核内地址空间模型；D3 经 0011 增补） |
| 0005 | 组件锁多源 | Accepted |
| 0006 | LLVM 组件基线选版 | Accepted |
| 0007 | DADAO target 的 CMake 注册通道 | Accepted |
| 0008 | QEMU 组件基线选版 | Accepted |
| 0009 | QEMU Harness Methodology（D1–D7 + 3 次补注） | Accepted（用户确认 2026-09-19；头行 2026-09-22 订正） |
| 0010 | QEMU 模块任务重构（harness 依赖 + `translate.c` 拆分 + 任务粒度） | Accepted |
| 0011 | Exit-Port 可靠 Halt 机制（D1–D4） | Accepted |

---

## 3. 过程度量（画像）

> 统计方法：遍历 `.tao/tasks/**/*.md`，取「判决 … Needs Revision / Accepted」行与「第 N 轮」小节。可复跑：见 §10 附脚本要点。

### 3.1 任务与状态

- 任务总数 **76**（`已验证` 70 + `里程碑` 6）；6 模块全部收敛，**无 `待开始`/`待返工`/`待验收` 残留**。

### 3.2 审阅轮次与打回

| 指标 | 数值 |
|---|---|
| 判决 `Accepted` 次数 | **77** |
| 判决 `Needs Revision` 次数 | **42** |
| 有 ≥1 次打回的任务 | **27 / 76（36%）** |
| 打回次数分布 | 0 次：49 ｜ 1 次：19 ｜ 2 次：3 ｜ 3 次：3 ｜ 4 次：2 |
| 平均审阅轮次（有 Accepted 的任务） | ~1.71 |

**打回最多**：

| 任务 | 打回 | 备注 |
|---|---|---|
| `INTEG-003t` | 4 | 假反例 + 恒真断言 + 假绿（读 commit message/注释） |
| `QEMU-011t` | 4 | 手算分支偏移、值构造、陈旧二进制 |
| `LLVM-014t` | 3 | 检查器假阴性（读 commit message → 注释行） |
| `QEMU-005t` | 3 | NORETURN、精确异常、UB |
| `QEMU-006t` | 3 | `jump-rrii` 缺 `exit_tb`、翻译期 PC、对齐 |

### 3.3 打回原因分类（按频次）

| 类别 | 典型表现 | 代表任务 |
|---|---|---|
| **验证无判别力** | 恒真断言、两支写同一结果、只打印不判定、存在性代替取值 | `QEMU-008t`/`010t`/`014t`、`INTEG-003t` |
| **分支偏移/极性错** | `br_nz` 落点指向 PASS 分支、基址用「下一条」 | 本模块 **3+ 次**（`008t`/`010t`×2/`013t`） |
| **假反例/假注入** | 只改显示标签；空注入（`git diff` 为空） | `INTEG-003t`、`QEMU-008t` |
| **完成区不实** | 报 PASS 而实测 FAIL；数字与环境不符 | `QEMU-005t`/`016t`/`018t`、`LLVM-008t`、`INTEG-003t` |
| **还原不含重建** | 源码还原但二进制仍旧 | `QEMU-008t`/`011t` |
| **值构造错** | `add.si` 仅 18 位、立即数静默变 0 | `QEMU-011t` |
| **可复现性** | 新工具未入构建目标（`not`/`llvm-readobj`/`llvm-objcopy`） | `LLVM-013t`/`014t`、`INTEG-001k` |
| **语义缺陷** | NORETURN 异常路径、精确异常被破坏、UB | `QEMU-005t`/`006t`/`013t` |

### 3.4 子代理异常统计（engineer）

| 事件类型 | 次数（本 M1 后段） | 处置 |
|---|---|---|
| 空返回（产出已落盘） | `017t`×1、`018t`×2、`009t`×3 | 查落盘 → 续会话；`009t` 触发「≥3 次 → 主会话代行」 |
| 空返回且未落盘 | `QEMU-009t`×3 | 主会话代行 + reviewer 验收 + 登记 `deferred.md` |
| 完成区/汇报与真实输出不符 | `QEMU-016t`/`017t`/`018t`、`LLVM-008t`、`INTEG-003t`、`LLVM-014t` | 主会话实测证伪后退回 |
| 同类缺陷反复（假绿/恒真） | `INTEG-003t` 连续 3 轮 | 第 4 轮达标 |

**规则已固化**：`AGENTS.md`「子代理返回异常处理」「验证脚本反例门控」「完成区结论须与真实输出逐条对齐」「修复须修一类」。

---

## 4. 时间线 / 关键路径

### 4.1 分层执行（`milestones.md`「建议执行顺序」）

```
第 1 层  infra（Makefile/fetch/锁/issue registry/drift） + spec（ADR-0004/ELF 合约）
第 2 层  testcases（向量基线） + llvm/qemu（各自 build 打通）
第 3 层  llvm（MC 后端 + lit/oracle） ∥ qemu（RD/RB/RA + 控制流 + harness）
第 4 层  integ（E2E 冒烟 + 接口对齐）
第 5 层  各模块 m 核验 → M1 达成
```

关键路径：`infra` + `spec` → `qemu`（或 `llvm`）→ `integ` → M1。

### 4.2 重大事件时间线

| 事件 | 说明 |
|---|---|
| **模块重划（2026-09-14）** | `verif` 模块解散：CI 检查→`infra`、验证依据→`spec`、组件自测→`qemu`/`llvm`、集成→新模块 `integ`；目录 `verif/`→`contracts/`+`tools/<module>/`；5 个里程碑顺延 |
| **组件锁多源（2026-09-17）** | 新增 `INFRA-009t` + `ADR-0005`；LLVM 基线 ADR 顺延 `0005`→`0006`（13 处引用同步） |
| **按原始仓库名命名（2026-09-17）** | `INFRA-013t`；里程碑 `013m`→`014m` |
| **TB 续接缺陷（2026-09-21）** | `015t` reviewer 证伪 engineer 根因时发现 `dadao_tr_tb_stop` 缺 `gen_update_pc` ⇒ 任意长 TB 死循环；新建 `QEMU-022t`（补丁 `0008`）+ `ADR-0011` |
| **`fence` 裁定（2026-09-21）** | 用户裁定 deferred ⇒ 不阻断里程碑（`ISS-056` `blocks: []`）⇒ `make check` 转绿 |
| **testcases 缺口消解（2026-09-21）** | 154 数据级缺口 → `010t`(114) + `011t`(35) → **gap 0**；里程碑 `010m`→`012m` |
| **integ 收官（2026-09-22）** | `002t` E2E（3/3）→ `003t` 接口对齐（80/80/0）→ `004m` 里程碑；期间发现并修复 `wpN`（`013t`）与 `e_flags`（`014t`） |
| **M1 达成（2026-09-22）** | 6/6 模块里程碑，`milestones.md` M1 = ✅ 达成 |

### 4.3 里程碑顺延记录（`k↔m` 一一对应 + 「里程碑排最后」的实践）

| 原 | 现 | 原因 |
|---|---|---|
| `INFRA-013m` | `INFRA-014m` | 按原始仓库名命名新增 `013t` |
| `TESTCASES-010m` | `011m` → `012m` | 两次插入缺口消解任务 |
| `LLVM-013m` | `014m` → `015m` | 插入 `wpN` 修复（`013t`）、`e_flags` 修复（`014t`） |

**注意**：`.tao/README.md` 只规定「`nnn` 模块内三位递增」，**未成文**「里程碑必须排最后」；本 M1 的实践是**保持 `m` 在末位**（插入任务时顺延 `m`），并在 `changelog.md` 留痕。

---

## 5. 被否决的备选方案（决策的「为什么」）

| 决策点 | 采用 | 否决 | 理由 |
|---|---|---|---|
| exit-port halt 机制（`ADR-0011` D1） | A：`cpu_loop_exit()` longjmp | B：`env->halted` + TB 边界 `EXCP_HLT`；C：`cpu_exit()` + `EXCP_INTERRUPT` | 只有 A 保证「写入后零后续指令」；C 已证伪（40 次中 5 次退出码不一致） |
| `wpN` 静默误编码（`LLVM-013t`） | 接受 `wp0`–`wp3` + 非法 token 报错 | 仅「非法 token 报错」不接受别名 | 文档/注释长期用 `wpN` 记法；成本相同 |
| ELF `e_flags` 违约（`LLVM-014t`） | 修实现（`setELFHeaderEFlags(0x1)`） | 修订 `ADR-0003` 放宽 | ADR 已 Accepted；版本字段是前向兼容拒绝的基础 |
| `fence` 实现缺失 | deferred（不阻断里程碑） | 新建修复任务立即做 | 用户裁定；M1 语义不受影响 |
| `input_state.memory` 写入宽度（`QEMU-023t`） | C：按 mnemonic 宽度用 `st.b/w/t/o` | A：`st.o` + `MALIGN`（不可行）；B′：左对齐（与 ABI 相反，撤回）；E：可行但冗余 | 实测记录见 `changelog.md` 同日条 + `ADR-0009` 补注 |
| `INTEG-002t` 退出码语义 | 甲：成功 = `0x00`（guest 内比较） | 乙：字面比对（退出码 = 运算结果） | 乙落入 `ADR-0004 D5` 的 FAIL 段 |
| E2E lit 形态 | `.test` 汇编 `tests/e2e/*.s` | `.test` 内联等价汇编 | 内联使 `.s` 成为死文件、可漂移 |
| 测试机内存映射 | 核内地址空间模型（`ADR-0004` rev.） | 初版裸地址映射 | 与 `spec` 的 cfxcode 63 段一致 |
| `UNDI` 的向量层表达（`TESTCASES-008t`） | 方案 A：`class: legality` + `encoding.reserved` | 扩 `(insn,format)` 身份 | 保留编码无身份；不立 ADR（取舍已记录） |
| `RA` 指令汇编消歧（`LLVM-011t`） | 方案 B：`AsmName` + 寄存器类消歧 | 原「方案 A」 | A 与 `contract-isa §4.9` 不一致，作废 |

---

## 6. 死胡同 / 已关闭（避免重试）

| 项 | 处置 | 理由 |
|---|---|---|
| `verif` 模块 | 解散，职责拆分到 `infra`/`spec`/`qemu`/`llvm`/`integ` | 模块边界与职责不匹配 |
| `SPEC-005m`（ISA 归一化里程碑） | 移除 | `k↔m` 一一对应规则；意义由 `SPEC-002t`/`003t` + `SPEC-011m` 覆盖 |
| `LLVM-010t`（系统指令助记符 + smoke 修正） | **删除**，编号留空不重编 | 预检确认**无独立交付物**（4 条理由见 `changelog.md` 2026-09-21） |
| `QEMU-020t`（harness dumper 改造） | **删除**，编号 `020` 留空 | 普通模式不 emit dumper 由 `015t` 落地；分段 dumper 因 `022t` 根治 TB 缺陷而不再必要 |
| `TESTCASES-010t`（24 条窄 load 归因） | **删除草稿**，号位归还给「154 缺口消解」 | 归因改为 qemu 侧（`QEMU-023t`） |
| 旧 `TESTCASES-004t`/`005t`/`006t` | 关闭（已达成） | 编号**已复用**为新任务（见 `deferred.md`） |
| 0628 的「`jump` 目标 = 下一条 + imm*4」 | 不采用 | v5 `contract-isa §5.3`：基址 = 分支指令**自身**地址 |
| 0628 的「`llvm-mc` 无指令定义 → 手编 raw binary」 | 不采用 | v5 `llvm-mc` 可汇编 M1 指令；E2E 以真实 `.s→.o→.bin→QEMU` 为验收 |

---

## 7. 风险与假设台账（M2 会失效的前提）

| # | 假设 | 现状 | M2 影响 |
|---|---|---|---|
| 1 | **单 TU、无重定位、无链接器** | M1 成立 | M2 必须引入 relocation（`rela.si` fixup 现与 M2 不兼容：`>>2` vs `<<12`） |
| 2 | **无 MMU（VA = PA）** | 成立 | 若引入地址空间需重评 |
| 3 | **`ra0 = 0`**（MemRAS 不可达） | `ADR-0004 D2.1` | `ra0 ≠ 0` 时 `gen_ras_push/pop` 会**误抛 RASOF/RASUF** |
| 4 | **单核** | 成立 | `fence` 屏障无可观测效果；多核需实现真屏障 |
| 5 | **`EM_DADAO` 未注册 upstream** | project-custom | 碰撞风险由 `e_flags[7:0]` 版本字段缓解 |
| 6 | **`cpu_loop_exit` 属 QEMU 内部 API** | `ADR-0011` | baseline 升级（`ADR-0002/0008`）时须复核 |
| 7 | **`decodetree.py` 输出依赖 `PYTHONHASHSEED`** | 上游问题 | 不可 bit-reproducible；对象级 diff 不可作重构判据 |
| 8 | **harness 用 raw encoding、不读 `opcodes.yaml`** | 成立 | 存在漂移风险（建议加 lint） |
| 9 | **`DADAOFrameLowering::hasFPImpl` 未覆写** | M1 安全（抽象类未实例化） | **M2 首次实例化会编译失败**（阻塞项） |
| 10 | **越界立即数/未定义符号静默** | M1 无链接器无危害 | M2 必须加范围检查与符号诊断 |
| 11 | **QEMU 组件自测与集成共用 harness 约定** | 成立 | 若 M2 引入新执行模式需扩展 |

> **知识库订正记录（2026-09-22）**：`adr-0009` 的**文件头状态行**曾为 `Candidate`，而其各 decision 小节均为 `Accepted（用户确认 2026-09-19）` ⇒ 头行过期（`adr-authoring.md` 要求评审通过后由主会话置 `Accepted`）。**已订正为 `Accepted` 并注明**（属状态行订正，未改动任何 decision）。

---

## 8. 与 DADAO-0628 的差异对照

| 维度 | 0628（0.4.1） | v5（0.5.3） |
|---|---|---|
| 助记符 | `addi`/`add`/`jump_i`/`halt` | `add.si`/`add.uo`·`add.so`/`jump-iiii`；**无 `halt`**（退出 = 写 exit port） |
| 编码来源 | 手推（如 `0x1904002A`） | 全部由 `llvm-mc` 产生，不手编 |
| E2E 路径 | 绕道 `gen_e2e_binary.py` 手编 raw binary | 真实 `.s → llvm-mc → objcopy → QEMU` |
| `jump` 基址 | 「下一条 + imm*4」 | **当前指令地址** + imm*4（`contract-isa §5.3`） |
| 测试机 | 0628 `ADR-0004` | v5 `ADR-0004`（核内地址空间模型、spec cause 派生 fault 码、exit 协议） |
| 浮点 | 全程无浮点指令（M2.5/M2.6 才 soft-float 接入） | 同（M1 明确不含，后续以 soft-float libcall 接入） |
| 权威来源 | — | `contracts/opcodes.yaml`（0.5.3）；**0628 旧 `tools/opcodes.yaml` 不可作编码权威** |

---

## 9. M2 衔接 / 交接清单

### 9.1 M2 定义（`milestones.md`）

**M2 — Basic CodeGen**：`llc` 将标量整数/指针函数（LLVM IR）编译为 DADAO 汇编，经 MC → obj → 链接 → QEMU 执行结果正确（freestanding、same-TU，不含变参/聚合）。门槛：`make test-codegen` 全绿，至少一个算术/访存/分支/调用函数端到端在 QEMU 得到期望结果。

### 9.2 前置阻塞项（M2 规划必须先行）

| # | 项 | 后果 |
|---|---|---|
| 1 | `DADAOFrameLowering::hasFPImpl` 未覆写 | **M2 首次实例化编译失败**（纯虚未实现） |
| 2 | `rela.si` fixup 与 M2 relocation 不兼容 | 加 ELF relocation 后必须单独处理（`>>2` vs `<<12`） |
| 3 | 越界立即数静默截断 / 未定义符号静默为 0 | 无诊断，M2 链接阶段会静默出错 |
| 4 | 完整调用约定（参数/返回/栈帧/溢出区/prologue-epilogue） | `Deferred to M2`（M2 CodeGen 的 oracle） |
| 5 | relocation 类型表/溢出/relaxation（D2/D3/D4） | `Deferred to M2`；编号待定 |
| 6 | `getFixupKindForInstr` default 分支未白名单化 | 非分支符号操作数会落 default，脆弱 |
| 7 | `DADAOFrameLowering` 等文件缺末尾换行（4 处） | 清理项，不阻塞 |

### 9.3 可复用资产

- **harness**：`tests/scripts/`（raw encoding → loader/test/dumper/exit 四段；`run_qemu_test.py` 只看 `$?`）；`ADR-0009` 方法论可直接复用
- **E2E**：`tests/lit/E2E/`（`%llvm_mc`/`%llvm_objcopy`/`%qemu`/`%trampoline`/`timeout`）
- **lit**：`tests/lit/MC/Dadao/`（`# OBJ:`/`ASM:` 双前缀模板）
- **oracle**：`tools/llvm/test_encoding_oracle.py`（68）、`check_lit_bytes.py`（53）
- **接口核对**：`tools/integ/check_interface_alignment.py`（80 项）
- **最小 ROM 探针框架**：`tools/qemu/min_rom_probe_*.py`（建议先做「标签化」改造，见 §11）

### 9.4 建议分解顺序（草案）

1. M2 前置修复（§9.2 的 1–3、6、7）
2. ABI 完整调用约定合约（`contract-abi` 扩展）→ `ADR`（若判据成立）
3. `llc` CodeGen 骨架（FrameLowering/InstrInfo/ISel 最小集）
4. `make test-codegen` 门控 + 至少 1 个端到端函数
5. 逐族扩展（算术 → 访存 → 分支 → 调用）

---

## 10. 复现手册

### 10.1 一键命令序列

```bash
make build-mc                 # LLVM MC（ninja 目标：llvm-mc llvm-objdump llvm-objcopy llvm-readobj FileCheck not LLVMDADAOCodeGen）
make build-qemu               # QEMU（out-of-tree，产物 .work/build/qemu/qemu-system-dadao）
make check                    # manifest-check + validate-vectors + check-spec-drift + check_issues + compileall
.work/build/llvm/bin/llvm-lit tests/lit/MC/Dadao/ tests/lit/E2E/
python3 tools/testcases/validate_vectors.py
python3 tools/integ/check_interface_alignment.py
python3 tools/infra/check_issues.py
```

### 10.2 环境坑（血泪清单）

| # | 坑 | 规避 |
|---|---|---|
| 1 | `make build-qemu` 不重编 `.c.inc` | `touch target/dadao/translate.c` |
| 2 | `$?` 被管道/命令替换吞掉 | 用 `; echo $?` 或先重定向再取 |
| 3 | `llvm-objdump -d` 缺 triple | 显式 `--triple=dadao-unknown-elf` |
| 4 | 新增工具未入构建目标 | `Makefile` `build-mc` 的 ninja 目标须含之（已 3 次踩坑：`llvm-objcopy`/`not`/`llvm-readobj`） |
| 5 | `git checkout -- <file>` 从污染 index 还原 | 用 `git reset --hard HEAD` 或临时副本；**还原须含重建** |
| 6 | 测试机路径 | QEMU `.work/build/qemu/`（非 `.work/qemu/build/`）；LLVM `.work/build/llvm/bin/` |
| 7 | 退出码语义 | 成功 = `0x00`；`0x01`–`0x7F` = FAIL；`0x80|` = fault（`ADR-0004 D5`） |
| 8 | `set.zw` 等 wyde 位置 | 用**数字** 0–3（`wpN` 记法仅作注释；`LLVM-013t` 前会被静默编码为 `wp0`） |
| 9 | `--dump` 模式设计上自旋 | harness 恒报 `INCONCLUSIVE - Timeout`；**不得**把「不再 TIMEOUT」当判据 |
| 10 | 补丁校验 | 临时 worktree 依序 `git am 0001→NNNN` + **tree hash 比对**（对象级 diff 不可用） |

### 10.3 度量脚本要点（可复跑）

```python
# 判决行统计：遍历 .tao/tasks/**/*.md
nr  = len(re.findall(r"判决[^\n]{0,40}Needs Revision", txt))
acc = len(re.findall(r"判决[^\n]{0,40}Accepted", txt))
```

---

## 11. 术语表 + 文件地图

### 11.1 术语

| 术语 | 含义 |
|---|---|
| RD / RB / RA | 三类寄存器组；`rd0` 硬连零；`ra63` 为 RegRAS 栈顶 |
| RegRAS / MemRAS | 返回地址栈（寄存器内 / 内存溢出） |
| exit port | `0xffff_8000_0000`（8 B 只写 MMIO）；写入即 halt，值 = 退出码 |
| `BINARY_BASE` | `0xffff_0000_0000`（RAM 入口，`-kernel` 落点） |
| boot ROM | `0xffff_ffff_0000`（`-bios`，trampoline 64 KiB） |
| `dadao-m1` | 测试机名（强制 `-bios` + `-kernel`） |
| cfx / cfxcode 63 | 核芯功能扩展编号；测试机整体占用最高段 |
| `e_flags` | ELF 对象/ABI 格式版本（bits 0–7 = 1；bits 8–31 = 0） |
| `wpN` | wyde 位置（0–3），rwii 格式的 `hb[5:4]` |
| `fence` | 内存序屏障（M1 实现缺失，deferred） |
| `excluded_m1` | 78 条 M1 排除指令（浮点/特权 cfx/LR-SC） |

### 11.2 文件地图

| 路径 | 用途 |
|---|---|
| `AGENTS.md` | 项目规则（**经验规则的唯一准绳**） |
| `.tao/tasks/<module>/` | 任务书（`<PREFIX>-nnn<suffix>`：`k` 启动 / `t` 普通 / `m` 里程碑） |
| `.tao/knowledge/` | `MEMORY.md` / `milestones.md` / `changelog.md` / `deferred.md` / `contract-*.md` / `adr-*.md` |
| `spec/` | 11 份原始规范（只读） |
| `manifests/` | 组件与规范锁文件（精确 commit） |
| `components/<name>/patches/` | 有序补丁序列 + `series` |
| `contracts/` | 机器可读合约（编码表/合法性/ABI） |
| `tools/<module>/` | 各模块工具脚本 |
| `tests/vectors/` | 测试向量（`isa/*.yaml` + `schema.md` + `inventory.md`） |
| `tests/scripts/` | QEMU harness + trampoline |
| `tests/lit/` | MC（`MC/Dadao/`）与 E2E（`E2E/`）lit |
| `docs/` | 仓库级文档（含本文件） |
| `.work/` | 一次性工作区（**整体不入库**）：源码树、构建产物、日志、临时 |

---

## 12. 审计追溯链

每个 M1 结论都可回溯到「任务 → 审阅轮次 → 命令/log」。指针表：

| 结论 | 任务 | 审阅记录 | 证据（命令 / 日志） |
|---|---|---|---|
| exit-port 写后立即 halt、退出码锁定 | `QEMU-022t` | 第 2 轮 Accepted | `ADR-0011`；reviewer 2100 次退出码一致性 |
| TB 续接缺陷（`gen_update_pc`） | `QEMU-022t` | 同上 | `-d exec` 46185 次 / PC 恒 `0xFFFF00000000` |
| harness 方法论（raw encoding / guest 内比较 / trampoline） | `QEMU-014t` | 五轮 → Accepted | `ADR-0009`（D1–D7 + 3 次补注） |
| 向量 747 条、gap 0 | `TESTCASES-010t`/`011t` | 各 2–3 轮 | `python3 tools/testcases/validate_vectors.py` |
| 审计 0 残留错值 | `TESTCASES-009t` | 六轮 → Accepted | `docs/testcases-009t-audit.md` + `tools/testcases/009t-audit.py` |
| `wpN` 静默误编码 | `LLVM-013t` | 两轮 → Accepted | 补丁 `0007` + `tests/lit/MC/Dadao/wpn_operand.s` |
| ELF `e_flags` 违约 | `LLVM-014t` | 三轮 → Accepted | 补丁 `0008` + `readelf -h` `Flags: 0x1` |
| 跨模块接口零不一致 | `INTEG-003t` | 四轮 → Accepted | `docs/integ-interface-alignment.md` + `tools/integ/check_interface_alignment.py`（80/80/0） |
| MC↔QEMU 端到端闭环 | `INTEG-002t` | 两轮 → Accepted | `tests/lit/E2E/` 3/3；全链路 `$? = 0x00` |
| M1 达成 | `INTEG-004m` | 核验记录 | `make check` EXIT 0；`milestones.md` M1 = 达成 |

> 历史日志：`.work/log/<module>/<任务ID>-<命令名>.log`（reviewer 重跑加 `-review-`）。`.tao/logs/` **已废弃**（曾被误用，已清理）。
