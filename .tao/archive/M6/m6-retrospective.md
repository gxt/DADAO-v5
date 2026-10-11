# M6 里程碑回顾（Retrospective）

> **定位**：面向 **M7 规划 / 新人上手 / 审计追溯**。本文件**聚合索引**既有材料，**不复制**其明细：
> 状态摘要见 `.tao/knowledge/MEMORY.md`；路线图见 `milestones.md`；变更流水见 `changelog.md`；
> 遗留台账见 `.tao/knowledge/issues.yaml`（issue/待决）与 `.tao/knowledge/lessons.md`（教训/方法论/过程记录）；
> **经验规则以 `AGENTS.md` 为唯一准绳**。
>
> **日期**：2026-10-11 ｜ **范围**：M6（整数完整调用约定 + LLVM 欠账收口 + ELF 直载 + clang target + Embench 接入）
> **归档**：2026-10-11 起本文件随 M6 任务书/台账落入 `.tao/archive/M6/`（历史快照，不再更新）；M6 原始任务书明细见同目录 `<模块>/`、`README.md`、`issues-closed.md`。

---

## 1. M6 事实快照

### 1.1 定义与门槛

`milestones.md`：**M6 — 整数完整调用约定 + 12 条 LLVM 欠账收口 +「elf 加载」**（用户 2026-10-08 逐条裁定；`k` = `INTEG-023k`，M5 起里程碑由 INTEG 模块开闭，`Process-04 §1`）。

目的：把 LLVM 后端从 M5 的整数基本 codegen 升级为**完整整数调用约定**（变参 / 聚合 / `sret` / 多返回 / 间接调用），收口 12 条 LLVM 欠账，打通 **DADAO clang target**（**仅 freestanding**，钉子①）；QEMU 侧**改走 `load_elf()`**（钉子②）取代 M5 的 raw-bin 加载；接入 **Embench**（钉子③）；并落 reloc 体系（`REL12`/`ABS12`）、ABI 寄存器布局重排、lit 量产与 `lli` 值级对拍。

**门槛**：`make check`（不回归）+ 新增**opt-in** `make test-m6`（**不进** `make check` 依赖链）——组成 = `check-lit-full`（12/12）+ `diff_ir_lli` 值级对拍（19/19）+ Embench（`-O0`/`-O2` 各 19 基准，判据 guest exit 0）。

**范围简化 / 明确不含**：`ISS-003`（LR-SC 原子）**M6 显式排除**；不引 libc / 无 OS/syscall；golden model / fuzz 后置 M7。

### 1.2 达成情况（达成状态）

**2026-10-11 达成**。6 个模块里程碑全部置 `里程碑`，`milestones.md` 项目里程碑 M6 = **达成**（`INTEG-026m` 整体收敛）。

| 模块 | 里程碑 | 关联任务 |
|---|---|---|
| infra | `INFRA-052m` | `INFRA-050t`/`051t` + 新增 `053t`/`054t` |
| spec | `SPEC-125m` | `SPEC-122t`/`123t`/`124t`/`126t` + `127t`/`128t`/`129t`/新增 `130t` |
| llvm | `LLVM-067m` | `LLVM-062t`–`066t`/`068t` + 新增 `069t`–`078t` |
| qemu | `QEMU-054m` | `QEMU-052t`/`053t`/`055t` |
| testcases | `TESTCASES-040m` | `TESTCASES-036t`–`039t`/`041t` |
| integ | `INTEG-026m` | `INTEG-023k`（开启 `/` 分解）、`024t`、`025t`（门槛收口）；另有 `027t`（进程/工具类） |

**M6 任务书 46 份 = 39 `t` + 1 `k` + 6 `m`**（`infra 5 / spec 9 / llvm 17 / qemu 4 / testcases 6 / integ 5`）全终态（`已验证` / `里程碑`）。

### 1.3 最终门槛实测（2026-10-11，真实输出；完整输出见 `.work/log/integ/INTEG-026m-*.log`）

| 门槛 | 命令 / 证据 | 结果 |
|---|---|---|
| `make check` | `make check` | **EXIT=0**；`repository checks: PASS`；`check-lit` 89/89；`check_issues` 24 open / 18 closed |
| `make test-m6` | `make test-m6` | **EXIT=0**；见下三组成 |
| 组成① lit 全量档 | `check-lit-full` | **12/12** |
| 组成② `lli` 值级对拍 | `diff_ir_lli`（host X86 vs DADAO target） | hits **19/19**，matched **19/19** |
| 组成③ Embench E2E | `run_embench_e2e.py` | **38/38**（= 现场发现 19 基准 × `-O0`/`-O2`，判据 guest exit 0），0 FAIL |
| 补丁集一致 | `make check-patch-tree` | **EXIT=0**；`3 component(s), 109 patches OK` |

### 1.4 版本 / 组件基线

规范 **SimRISC 0.5.4**；`Toolchain 1.1`。
组件锁 `manifests/components.lock.toml`：`llvm-project` `6dfe1677ab8dffbc6ec13d53a1e0215d75147689`（llvmorg-23.1.1）；`qemu` `c3d48b7d1e89604920e5b81b91140c2ad39a1943`（v11.1.1）；**`embench-iot` `09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`（M6 新增，`enabled=true`，`ADR-0022 D2`）**；`gem5` `enabled=false`。

---

## 2. 交付物 / 资产地图

| 类别 | 数量 | 位置 |
|---|---|---|
| M6 任务文件 | **46**（自归档 `INTEG-026m` 在内） | `.tao/archive/M6/<module>/`（2026-10-11 归档） |
| ADR | 就地修订 1（`0018`：`§C7 D4` 四形态 + `§C7 D6` 条件保留）；新建 2（`0021` reloc / `0022` Embench） | `.tao/adr/` |
| 合约叙述 | `contract-elf.md §2–§4`（`REL12`/`ABS12`/`ABS48` 数据 8B）、`contract-abi.md §6` 三 `[OPEN]` 消解 | `.tao/knowledge/` |
| 规范正文 | 改 v5/上游册：`Toolchain-01 §6.1`（`set.fo` 口径）、`§7`（数据指示符唯一集）；同步 `spec-readonly.lock.toml` `sha256` | `spec/`、`manifests/` |
| LLVM 补丁 | `llvm 27+.patch` + `lld` + `clang`（`Basic`/`Driver`/`CodeGen`）= **3 component(s) 合计 109 patches** | `components/llvm-project/patches/` |
| QEMU 补丁 | **34**（`load_elf()` 改走 + `common-semi-target.c` / `qemu-options.hx` 等） | `components/qemu/patches/` |
| Embench 骨架 | `components/embench-iot/{patches,series,changelog.md}`（含用户裁定的 1 个最小占位补丁） | `components/embench-iot/` |
| 工具脚本 | `tools/integ/run_embench_e2e.py`、`run_*_e2e.py`、`tools/testcases/validate_m6_vectors.py`、`tools/llvm/**` 等 | `tools/<module>/` |
| 测试向量 | L1 编码 `tests/llvm/lit/MC/DADAO/m6-*.s`、L3 执行 `tests/llvm/codegen/m6/**`（raw-bin 7 + ELF 1）、lit 量产快档/全量档 | `tests/` |
| 门控 | `Makefile::test-m6`（opt-in；`check-lit-full` + `diff_ir_lli` + Embench） | `Makefile` |
| 教训库 | `.tao/knowledge/lessons.md`（M6 新增约 `§7.27–§7.34` / `§8.21–§8.51`） | `.tao/knowledge/` |

### 2.1 M6 新增 / 就地修订 ADR

| ADR / 决策 | 主题 | 状态 |
|---|---|---|
| `ADR-0018`（就地修订） | `§C7 D4` 大帧寻址改**四形态 + 代价驱动**；`§C7 D6` 保留策略改 **`rb63` 条件式保留**（FP 由 `rb2` 迁 `rb63`） | Accepted（rev. 2026-10-08 / 10-09） |
| `ADR-0021`（**新建**） | `ld/st` 符号偏移 reloc 体系：`D1` 由「引入 `REL12`」扩为「`REL12` + `ABS12` 双类型」 | Accepted（rev. 2026-10-09） |
| `ADR-0022`（**新建**） | Embench 上游选择 + 精确 commit（`09c2ed8c…`） | Accepted |

### 2.2 补丁规模

| LLVM（3 component(s) / 109 patches） | QEMU（34） |
|---|---|
| 新增 `lib/Target/DADAO/**`（`AsmParser`/`MCTargetDesc`/`Disassembler`/`ISel`/`FrameLowering`/…）、`lld/ELF/Arch/DADAO.cpp`、clang `DADAO.{h,cpp}`（`TargetInfo`/`driver`/`CodeGen`） | `target/dadao/**` + `hw/dadao/**`；`load_elf()` 改走 + `DADAO_SEMI_RET_REG=8` + RAM@0 收口 |

---

## 3. 任务与过程

### 3.1 计划基线 + 过程中新增

- **规划基线**：`INTEG-023k` `/plan` 通过（reviewer 交叉审查「通过 + 4 项非阻塞修正」），任务书按 §C 表建立、按 §D Wave 串行链推进。
- **过程中新增（15 份）与为何新增**：
  - `LLVM-069t`（整数 `setcc`/`select_cc` lowering，`ISS-173`）、`INFRA-054t`（clang 内置头安装，`ISS-174`）——**`TESTCASES-039t` 停工**暴露：交付工具链无一基准可编译（真实 C 阻塞）。
  - `LLVM-070t`（G6/`ISS-180` 缺陷·`-O2` 静默错码）、`071t`（G1+G5）、`072t`（G3 跳转表）、`073t`（G2 128 位乘高半）、`074t`（G4 尾调用）——`TESTCASES-039t` **首验收达标后**暴露 **6 类后端缺口 G1–G6**（见 `ISS-175`–`180`）。
  - `LLVM-075t`（`ISS-182` `.p2align` 崩溃）、`076t`（`ISS-185` 有符号乘高半）、`077t`（`ISS-186` i1 zext-load）、`SPEC-130t` + `LLVM-078t`（`ISS-181` 数据指示符口径拆分：spec 正文 + 生成/受理侧）——用户 2026-10-10 裁定 4 缺口全入 M6。
  - `INFRA-053t`（`ISS-172` `install-host` 幂等性缺陷，`QEMU-053t` 复验发现）。
  - `INTEG-024t`（issues 台账按性质分流）、`INTEG-027t`（项目 agent 配置与规则重构，进程/工具类）。
- **早期裁定增补**（并入规划基线）：`SPEC-126t`/`QEMU-055t`/`TESTCASES-041t`（返回寄存器统一 `rd8`）、`SPEC-127t`（HFA/HPA 槽位 4→8 = 64 B）、`SPEC-128t`/`LLVM-068t`（ABI 寄存器布局重排）、`SPEC-129t`（`Toolchain-01` 旧口径消除，`ISS-163` 收口）。

### 3.2 审阅轮次与打回（代表）

| 任务 | 事项 |
|---|---|
| `INTEG-027t` | 第 1 轮 reviewer **Needs Revision**（F01：删 `instructions/` 后 4 份通用细则致**静默丢规则**）→ 返工补回 10 / 显式不适用 4 → 第 2 轮 Accepted |
| `LLVM-071t`/`LLVM-072t` | reviewer 首次下发 `Too Many Requests`、产出未落盘 ⇒ **重试 1 次成功**（登记 `ISS-183`/`ISS-184`；`AGENTS.md`「子代理返回异常处理」首次生效） |
| `TESTCASES-036t` | 第 1–3 轮：修 reloc 死断言（F-A）+ 结构断言缺口（F-D） |
| `TESTCASES-039t` | engineer **诚实停工**（判据未降级）⇒ 立 `LLVM-069t`/`INFRA-054t`；首验收达标后再立 G1–G6 收口任务 |
| `QEMU-053t` | reviewer 第 2 轮补正：`git diff ... \| grep '^spec/'` 假阴性（`spec/Machine-01` 实有改动）⇒ `lessons §8.31` |

### 3.3 M6 固化的机制 / 教训（指针 `lessons §7/§8`）

「失败不再即停：保留现场 + 自行处置 + 继续推进」（§8.49，用户 2026-10-10 裁定）、「真实语料 E2E + 逐优化级带超时退出码」（§8.39/§8.42）、「测试断言须能区分被测属性」（§8.46）、「证据脚本还原以 clean baseline 为锚」（§8.51）、「长构建脱离 opencode 生命周期」（§8.21）、「每任务一分支」（§8.26）、「任务开工分支须从最新 `master` 拉」（§7.33）。

---

## 4. 时间线 / 关键路径

```
2026-10-08  M6 开启（INTEG-023k，用户逐条裁定 20 内涵 + 12 欠账）+ 台账搬迁（INTEG-024t）
2026-10-08  Wave0/Wave1 起步：INFRA-050t（一次构建双落点）→ 051t（Embench 接入）；SPEC-122t（ADR）→ 123t/124t
2026-10-09  Wave1 续（rd8/聚合/寄存器重排）：SPEC-126t→127t→128t→129t；Wave2 llvm：LLVM-062t→068t→063t→064t→065t→066t
2026-10-09  Wave3 qemu：QEMU-052t（load_elf）→ 053t（RAM@0 step2）→ 055t（半托管 rd8）；INFRA-053t/054t（缺陷/装头）
2026-10-10  Wave4 testcases：TESTCASES-036t–039t/041t；Embench 暴露 G1–G6 ⇒ 新增 LLVM-070t–078t + SPEC-130t 收口
2026-10-10  INTEG-027t（agent 配置与规则重构，进程/工具类）
2026-10-11  Wave5 收口：INTEG-025t（make test-m6 opt-in）→ 6 模块 m → INTEG-026m（整体收敛 + 归档）
```

**关键路径**：`SPEC-122t` → `SPEC-124t` → `LLVM-062t` → `LLVM-064t`/`066t` → `TESTCASES-036t` → `INTEG-025t` → `INTEG-026m`。

### 4.1 历史事故登记（原 `milestones.md`「当前进度」，M5 末 ~ M6 期；审计链保留）

| 项 | 内容 |
|---|---|
| 历史瑕疵（已解决） | 提交 `815d854` 内容 = `SPEC-122t`、消息曾误写为 `INFRA-050t: …`；用户 2026-10-09 批准修正，已 `commit --amend` 改写为 `eb10259`（**只改消息、内容未变**，对 `backup/pre-push-squash` 与旧 `origin/master` 两级校验 0 行差异），`--force-with-lease` 推送**由用户本人执行**；备份分支 `backup/pre-push-squash`/`before-msgfix`/`pre-msgfix2` |
| WIP 入史（用户裁定） | 已推送历史含 `5dfd311 WIP: QEMU-052t 候选实现…+ 停下报告`（子代理 `cancelled`、卡裁定）；用户 2026-10-09 裁定「**选 b，保留现状**」⇒ 不改写已推送历史，`QEMU-052t` 最终交付叠加其后 |
| `SPEC-129t` 双提交 | `82280d9`（内容）+ `98c2dbc`（收尾）均 push、未 squash——主会话 squash **base 写错**且用 `;` 无条件串接 push（`lessons §8.25`）；按「已 push 不得改写历史」保留现状（`git diff` 前后 0 行） |
| 每任务一分支工作流 | 用户 2026-10-09 裁定生效（`lessons §8.26`）：开工建分支、WIP/返工/reviewer 修改提交在该分支、**一次性落地 `master`**、`master` 永不改写已推送历史；已落 `AGENTS.md` |

### 4.2 三根钉子（M6 前三项具体交付）

| 钉子 | 任务 | 结果 |
|---|---|---|
| ① clang target | `LLVM-063t` | `--print-targets` 含 `dadao`；DL 与后端逐字符一致；E2E `clang→llvm-mc`+`ld.lld`→QEMU `exit=42` |
| ② QEMU `load_elf()` | `QEMU-052t` | 改走上游 `hw/core/loader.c`；取消自建白名单；多段 `PT_LOAD`/RELA/`e_entry` 作验证项 |
| ③ Embench | `TESTCASES-039t` + `LLVM-070t`–`078t` | **`-O0`/`-O2` 双 19/19**（guest exit 0） |

---

## 5. 关键决策（决策的「为什么」）

| 决策点 | 采用 | 否决 | 理由 |
|---|---|---|---|
| 停机/加载 | QEMU **改走 `load_elf()`**（复用上游） | 自建 `dadao_load_regions[]` 白名单 | 复用成熟加载器；组合加载 ADR「不立」（`SPEC-122t` 落「不立 + 理由」） |
| reloc 体系（`ADR-0021`） | 引入 **`REL12` + `ABS12`** 双类型 | 复用既有 `REL20` | 同一 reloc 类型不得承载两种语义（§7.27） |
| ABI 寄存器布局（`ADR-0018 §C7 D6`） | `rb2`=GP / `rb3`=TP / `rb63`=FP **条件保留** | `rb2` 始终保留 FP | GP/TP 需预留；FP 条件占用（§7.30 保留/使用同源） |
| 返回寄存器 | 函数/系统调用/半托管统一 **`rd8`**（`rd8–rd15`，K=8） | 保留 `rd31` | 逐域分类（§7.28），实现/向量同批（§8.33） |
| 数据指示符（`SPEC-130t`/`LLVM-078t`） | 唯一集 `.dd.b08/w16/t32/o64`；拒 `7` 个 GAS 名；删 `.align` 留 `.p2align` | 保留 GAS 名 | 消除口径歧义；**受理侧 target 级 shadow**（不改通用 MC） |

---

## 6. 死胡同 / 已关闭（避免重试）

| 项 | 处置 | 理由 |
|---|---|---|
| 尾调用静默无限重入（G6） | 清零 `CLI.IsTailCall` 发 `call`+`ret`；真尾跳留 `LLVM-074t` | 后端未处理尾调用 ⇒ 有 call 无 ret |
| `setcc`/`select_cc` 缺 lowering | `Custom` `LowerCmpSelect`（10 谓词） | `SETCC` 按操作数类型 / `SELECT_CC` 按结果类型（§8.40） |
| `.p2align` 使 `llvm-mc` abort | `writeNopData` 精确写 `Count` 字节（§8.48） | 定长 ISA 不可向上取整到指令宽度 |
| Embench 判据用 trivial 程序 | 真实语料 + 逐优化级带超时退出码（§8.39/§8.42） | 编译 rc=0 ≠ 可运行 |
| 证据脚本以运行现场为还原锚 | 以 clean baseline 为锚（§8.51） | 注入态运行会还原到注入态 |

---

## 7. 遗留登记 / 风险（M7 会失效的前提）

> 均为**已登记 = 已处置**（跨模块影响无未处置项）；详情见 `issues.yaml` / 各任务书「遗留问题」。

| # | 项 | 类别 | 处置 |
|---|---|---|---|
| 1 | `ISS-187` 窄位指令利用不足（8/16/32 位算术未用；`mul32` 用 `mul.uo` 而非 `mul.ut`） | llvm 优化候选（非缺陷） | M7（用户 2026-10-10「先只登记，暂不改」） |
| 2 | `ISS-188` FP 完备性缺口（`fcmp` 取值 / `fabs`/`frem`/`copysign` / `fma`/`fminnum`/… / `fpclass` / `f16` / `bitcast`；**全部显式失败**） | llvm 能力缺口 | M7（同上） |
| 3 | `ISS-189` 其它 LLVM 内建数据指导符（`.2byte/.4byte/.8byte/.value/…`）仍受理 | 口径未覆盖（未授权扩大） | M7（`spec/Toolchain-01 §7` 唯一集口径收口） |
| 4 | `check-spec-refs` 违规（`contract-asm.md` 引 `Toolchain-01 §7.2` 被误判） | 工具缺口 | M7：`SPEC_PREFIX_MAP` 补 `Toolchain-01` 前缀 + 匹配器改数值节号解析（`tools/infra` 任务） |
| 5 | `components/qemu/README.md:10` 旧述（「31 份 = 新增 25 + 修改 6」） | 文档陈旧 | M7：随 qemu 补丁规模刷新（实 34） |
| 6 | `LLVM-074t` 遗留：`tailjmp` 不参与 `BranchRelaxation` ⇒ 远距离尾调用由 `lld` 报 relocation overflow（非静默）；栈实参/变参尾调用未优化 | llvm 优化项 | M7（可选增强） |
| 7 | `ISS-108` 大文件（`DADAOInstrInfo.td` 1502 / `DADAOAsmParser.cpp` 2349 行）未拆分 | llvm 重构（非功能性） | M7（用户 2026-10-09 裁定推迟） |
| 8 | `ISS-164` cfx mask 屏蔽路径不可观测 | qemu 跟踪 | 挂账（待带可屏蔽 cause 的 cfx 实现后补验） |
| 9 | `ISS-074` `cs.*` 条件赋值 overlap 语义未定 | 待裁定 | 挂账（后端当前不发 `cs.*`；待实现/发射时定） |
| 10 | `ISS-167` `DADAO-12 §5` prose 与伪代码张力 | spec（须授权改上游只读册） | 挂账（用户 2026-10-09「需要时提出问题我来判定」） |
| 11 | `ISS-043`/`045`/`138`/`148`/`156`/`159`/`162` 七条：M6 任务完成区**声称已修/已收口**，但台账 `resolved_by` 未回填、仍 `open` | **台账待收敛** | M7：归档前置 `Process-04 §3` 梳理时回填 `closed`（或经用户裁定）——见 `issues-closed.md`「待收敛」 |

### 7.1 M6 达成（2026-10-11，architect 代主会话核验）

门槛 **`make check` EXIT=0** + **`make test-m6` EXIT=0**（opt-in：`check-lit-full` 12/12 + `diff_ir_lli` 19/19 + Embench 38/38）；6 个模块 `m`（`INFRA-052m`/`SPEC-125m`/`LLVM-067m`/`QEMU-054m`/`TESTCASES-040m`/`INTEG-026m`）**全置 `里程碑`**；46 份 M6 任务书全终态；ADR 前置（`0018`/`0021`/`0022`）均 `Accepted`。核验命令/证据见各 `m` 文件「核验」与 `.work/log/integ/INTEG-026m-*.log`。

---

## 8. 对 M7 的交接

### 8.1 可复用资产

- **clang target + driver/sysroot**（`LLVM-063t`）：`lib/Basic/Targets/DADAO.{h,cpp}` + `lib/Driver/ToolChains/DADAO.{h,cpp}`（仅 freestanding）。
- **ELF 直载**（`QEMU-052t`）：复用 `hw/core/loader.c`。
- **Embench E2E**（`TESTCASES-039t`/`INTEG-025t`）：`components/embench-iot/**`（锁 `enabled=true`）+ `tools/integ/run_embench_e2e.py` + `make test-m6`。
- **值级对拍**（`TESTCASES-038t`）：`diff_ir_lli`（host `lli` × DADAO/QEMU，仅值级）。
- **独立向量 + oracle**：`tests/llvm/{lit,codegen}/m6/**` + `tools/testcases/validate_m6_vectors.py`（**禁** LLVM/QEMU 反填）。
- **reloc / ABI 契约**：`contract-elf §2–§4` + `contract-abi §6` + `ADR-0021` + `ADR-0018 §C7 D4/D6`。

### 8.2 M7 待办（分类见 §7）

FP 完备性（`ISS-188`）→ 窄位指令利用（`ISS-187`）→ 数据指示符剩余面（`ISS-189`）→ 工具门控（`check-spec-refs` 前缀/匹配器）→ 文档（`components/qemu/README.md:10`）→ 尾调用优化（`LLVM-074t` 遗留）→ 大文件重构（`ISS-108`）→ 台账收敛（§7 #11）→ 既有挂账（`ISS-164`/`ISS-074`/`ISS-167`）。**下一阶段主题（golden model / libc/OS / fuzz / 门控分层）由 M7 规划 `k` 裁定**（见 `milestones.md`「规划中」）。

---

## 9. 复现手册

### 9.1 一键命令序列

```bash
make check                    # manifest-check + 各 checker + lit 89/89 + spec-readonly
make check-patch-tree         # 109 patches OK
make test-m6                  # M6 门槛（opt-in：check-lit-full + diff_ir_lli + Embench）
make test-codegen             # raw-bin E2E
make test-elf                 # ELF E2E
make test-semihost            # 半托管
python3 tools/infra/check_issues.py
python3 tools/integ/check_interface_alignment.py
```

### 9.2 环境坑（血泪清单，M6 增补）

| # | 坑 | 规避 |
|---|---|---|
| 1 | 真实语料 E2E 仅看编译 rc | 须含**运行期带超时退出码** + 优化级矩阵（§8.42） |
| 2 | 定长 ISA `writeNopData` 向上取整到指令宽 | 精确写 `Count` 字节（§8.48） |
| 3 | 证据脚本以运行现场为还原锚 | 以 clean baseline 为锚（§8.51） |
| 4 | 交叉工具链 `clang` 与 `llc` 独立静态链接后端库 | 二者行为不一致易误判后端 bug（§8.47） |
| 5 | 任务开工分支从过期 `master` 拉 | 从**最新** `master` 拉（§7.33） |
| 6 | 同一工作树并发切分支/写工作树子代理 | 串行或独立 `git worktree`（§7.32） |

### 9.3 门槛检查详情

| 门槛 | 复算方式 |
|---|---|
| `make check` | `repository checks: PASS`；`check-lit` 89/89 |
| `make test-m6` | `check-lit-full` 12/12 + `diff_ir_lli` 19/19 + Embench 19×2=38/38 |
| 补丁数 | `make check-patch-tree` → `3 component(s), 109 patches OK` |
| 台账 | `python3 tools/infra/check_issues.py`（归档后 open 24 / closed 0） |

---

## 10. 审计追溯链

| 结论 | 任务 / 决策 | 证据（命令 / 日志） |
|---|---|---|
| clang target（钉子①） | `LLVM-063t` | `--print-targets` 含 `dadao`；E2E `exit=42` |
| `load_elf()`（钉子②） | `QEMU-052t` | `make check-qemu-semantics` |
| Embench（钉子③） | `TESTCASES-039t` + `LLVM-070t`–`078t` | `make test-m6`（Embench 38/38） |
| reloc 体系 | `ADR-0021` / `SPEC-123t` / `LLVM-065t` | `check-lit`；`llvm-mc rc=0` |
| ABI 寄存器重排 | `ADR-0018 §C7 D6` / `SPEC-128t` / `LLVM-068t` | lit 期望；重建 |
| M6 门槛 | `INTEG-025t` | `make test-m6` EXIT=0 |
| M6 达成 | 6 个 `m` + `INTEG-026m` | `milestones.md` M6 = 达成；`.work/log/integ/INTEG-026m-*.log` |
| 归档 | `INTEG-026m`（本任务） | `git status` R；`issues.yaml` 提取 18 条 |

> 历史日志：`.work/log/<module>/<任务ID>-<命令名>.log`（reviewer 重跑加 `-review-`）。
