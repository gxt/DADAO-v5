# M7 里程碑回顾（Retrospective）

> **定位**：面向 **M8 规划 / 新人上手 / 审计追溯**。本文件**聚合索引**既有材料，**不复制**其明细：
> 状态摘要见 `.tao/knowledge/milestones.md`（唯一真源）；变更流水见 `milestones.md`「任务流水」；
> 遗留台账见 `.tao/knowledge/issues.yaml`（issue/待决）与 `.tao/knowledge/lessons.md`（教训/方法论/过程记录）；
> **经验规则以 `AGENTS.md` 为唯一准绳**。
>
> **日期**：2026-10-13 ｜ **范围**：M7（**picolibc 移植（自带 test）+ FP 后端完备（P0/P1）+ ISA↔后端覆盖矩阵 + 过渡 oracle**）
> **归档**：2026-10-13 起本文件随 M7 任务书/台账落入 `.tao/archive/M7/`（历史快照，不再更新）；M7 原始任务书明细见同目录 `<模块>/`、`README.md`、`issues-closed.md`。
>
> **更正说明（2026-10-13）**：本文件 §1.2「**项目里程碑 M7 尚未标记「达成」**」及 §5.1「`SPEC-136m` 未通过」、§7 #1、§10「M7 达成 = 待 `ISS-201` 用户裁定」等相关表述**均随口径纠正失效** ⇒ **更正为「项目里程碑 M7 = 达成（2026-10-13）」**。**理由**：`AGENTS.md`「不得置里程碑」**只针对未处置的*跨模块*影响**；`ISS-201`（规范是否补记未定义弱符号**防御分支**）属 **spec 模块内 backlog**、**不阻断** ⇒ `SPEC-136m`/`INTEG-034m` 置 `里程碑`、项目 M7 达成。**用户指正原话**（2026-10-13）：「M7都已经归档了，你留着ISS-201是有什么意义？」。**原述保留不改写**（归档时快照）；另 §2「M7 任务文件 **37**」随 `归档补齐` 增至 **40**（见 `README.md §1`）。

---

## 1. M7 事实快照

### 1.1 定义与门槛

`milestones.md`：**M7 — picolibc 移植（自带 test 100%）+ FP 后端完备（P0/P1）+ ISA↔后端覆盖矩阵 + 过渡 oracle**（用户 2026-10-11 逐条裁定；`k` = `INTEG-033k`，M5 起里程碑由 INTEG 模块开闭，`Process-04 §1`）。

目的：把 v5 从 M6 的「整数完整调用约定 + ELF 直载 + clang target + Embench」升级为**可跑真实 C 程序（picolibc 自带 test）**——补齐 **FP 后端 P0/P1**（比较取值/`bitcast`/`select_cc`/`cttz`/取整/`fmin-fmax`/`fabs`/`copysign`）、移植 **picolibc**（cross file / machine dir / syscall stub / 构建集成）并以**自带 test** 为门控（验收 = **100%**）、立**生成式 ISA↔后端覆盖矩阵**（两层分列）、采**过渡 oracle**（宿主机参照 + 明确边界，登记「非判据真源」）。

**M7 明确排除**（`INTEG-033k §排除项`）：动态链接 / linux-user / pk / Chipyard / golden / musl。**执行环境 `hypv`**；**RAM 基址改 `0xFC00_0000_0000`**（cfx63 段）；`adr-0023`（picolibc 上游 `1.8.12`，commit `2ae376c6…`）已 `Accepted`。

### 1.2 达成情况（**如实，不得误读为「已达成」**）

**项目里程碑 M7 尚未标记「达成」**。逐项现状（来源 = `.tao/knowledge/milestones.md` 现场取证 + 各模块 `m`）：

| 项 | 现状 | 依据 |
|---|---|---|
| `infra` `m` | **`里程碑`** ✓ | `INFRA-072m`（2026-10-13 02:00） |
| `llvm` `m` | **`里程碑`** ✓ | `LLVM-090m`（2026-10-13 01:32） |
| `qemu` `m` | **`里程碑`** ✓ | `QEMU-059m`（2026-10-13 01:50） |
| `testcases` `m` | **`里程碑`** ✓ | `TESTCASES-043m`（2026-10-13 01:13，含用户裁定「记为达成」+ 现场四数） |
| `spec` `m` | **未通过（`待开始`）** ✗ | `SPEC-136m`——`ISS-201`（open，`scope: spec`）待用户逐条确认 |
| `integ` `m`（整体收敛） | **未通过（`待开始`）** ✗ | `INTEG-034m`——L3 `make check-full` 已绿（manifest 补 13 条 exclude 后 `rc=0`），**唯一残项 = `ISS-201`** ⇒ 项目 M7 达成待裁定 |

**picolibc 自带 test 达成（用户裁定 + 现场四数，原样引用、不扩写）**：
- 用户 **2026-10-12** 裁定「**记为达成（推荐）**」；
- 现场：`total 235 / pass 213 / fail 0 / excluded 22 / blocked 0`（来源：`QEMU-058t` 完成区 + `components/qemu/changelog.md`；`make check-picolibc-tests-full` 现场统计）。

### 1.3 最终门槛实测（2026-10-13，真实输出）

| 门槛 | 命令 / 证据 | 结果 |
|---|---|---|
| L1 | `make check` | **rc=0**（`repository checks (L1): PASS`；`check-patch-tree: 4 component(s), 127 patches OK`） |
| L2 | `make check-modules` | **rc=0**（`check-lit` **107/107**、`check-qemu-smoke` **86/86**、`check-interface` **83/83**、`check-picolibc-tests` 快档 20/18pass/0fail/2excluded/0blocked） |
| L3 | `make check-full` | **rc=0**（`check-qemu-semantics` **149/149** + `test-m6`：`check-lit-full` 12/12 + `diff_ir_lli` 19/19 + Embench **38/38**）；**修复项见 §5.1** |
| 台账 | `check_issues.py` | **rc=0**（归档后 **25 open / 0 closed**） |

### 1.4 版本 / 组件基线

规范 **SimRISC 0.5.4**；`Toolchain-01`/`Machine-01` 设 `0.x.y` 版本号。组件锁 `manifests/components.lock.toml`：`llvm-project` `6dfe1677…`（llvmorg-23.1.1）、`qemu` `c3d48b7d…`（v11.1.1）、`embench-iot` `09c2ed8c…`、**`picolibc` `2ae376c6…`（= tag `1.8.12`，M7 新增，`enabled=true`，`adr-0023`）**；`gem5` `enabled=false`。

---

## 2. 做了什么（交付物 / 资产地图）

| 类别 | 数量 / 位置 |
|---|---|
| M7 任务文件 | **37**（终态）→ 本目录 `<模块>/`；归档任务 `INTEG-035m` **未自归档**（保留 `.tao/tasks/`，待置 `里程碑` 后执行） |
| ADR | 新建 1（`adr-0023` picolibc 上游 + 精确 commit）；就地修订 1（`ADR-0004` RAM 基址 `0 → 0xFC00_0000_0000`）；就地追加 1（`ADR-0019 D9` 未定义弱符号口径） |
| 组件 | **`components/picolibc/**`（新组件，补丁 18）**；`qemu` 补丁 **34**（无新增）；`llvm-project` 补丁树 71（新增/改 `lib/Target/DADAO/**` + `lld/ELF/Arch/DADAO.cpp`）；`embench-iot` 4 |
| 门控 | `check-patch-tree` **4 component(s) / 127 patches**；**门控分层 L1/L2/L3**（`INFRA-058t`，`docs/Process-07`）+ `check-knowledge-refs`/`check-knowledge-dir`/`check-qemu-smoke` |
| 工具 | `tools/llvm/gen_isa_coverage.py`（矩阵生成式）、`tools/testcases/picolibc_tests.py`（自带 test harness）、`tools/infra/{build_picolibc,check_knowledge_*}.py`、各 `m` 探针 |
| 规范/合约 | `spec/Machine-01`（地址图/RAM 基址）、21 册标题章节号统一 + 附录变更记录（`SPEC-133t`/`134t`）、`contract-elf §3.3` + `ADR-0019 D9`（未定义弱符号）、`contract-semihosting §1`（`cfxha` 口径） |
| 矩阵 | `.tao/knowledge/llvm-isa-backend-matrix.{tsv,md}`（227 条：①受理 217/拒 10；②ISel yes 86 / no 141） |

---

## 3. 关键决策（决策的「为什么」）

| 决策点 | 采用 | 理由 |
|---|---|---|
| picolibc 上游（`adr-0023`） | tag `1.8.12`（commit `2ae376c6…`）、`shallow_ref` 用 tag | 用户 2026-10-11 裁定「保持 1.8.12」 |
| libc 路线 | **picolibc 先行**（musl 后置；semihosting 而非 pk/SEE `trap`） | 用户裁定 + `DADAO-0628 ADR-0014` 溯源（小 libc 先趟后端） |
| FP 缺口收口 | P0/P1 分任务（`LLVM-079t`/`080t`）+ 谓词/`"r"`/f32/截断存储分批（`084t`–`089t`） | 每类可独立验收；消费侧过滤表**同步删条目**（逐条对账） |
| 2-NaN 传播规则 | **`float_2nan_prop_ab`**（宿主 x86_64 SSE 实测） | 用户 2026-10-12 裁定「参照宿主机实现」；**排除** IEEE 754-2019 推荐的 `s_ab` |
| 未定义弱符号 | PC 相对分支/`call` → **本位自循环**（`call-iiii`→`jump-iiii`） | 用户 2026-10-12 裁定原话「此处应改为 jump 指令，即 jump [rb0, 0]」 |
| 过渡 oracle | 宿主机结果**参照** + 边界（端序/`long double`=f64 vs 80-bit/`fenv`/UB） | 登记「**非判据真源**」，将来 `GOLDEN-*` 替换（用户裁定 #7） |
| `trap` 的 `cfxha` | **任意 `cfxha` 等效**（判定只查 `immu18[17:16]`） | 用户 2026-10-11「写成任意 cfxha」；不改实现 |

---

## 4. 时间线 / 关键路径

```
2026-10-11  M7 开启（INTEG-033k，10 条裁定落纸 + 参考检索）+ 门控分层设计（INFRA-058t）
2026-10-11  infra：picolibc 组件接入（INFRA-055t）→ clang++（056t）→ 真移植（057t）；台账/文档减重（061t–064t）
2026-10-11  qemu：RAM 基址 → 0xFC00_0000_0000（QEMU-056t）；llvm：P0（LLVM-079t）
2026-10-12  llvm：P1（080t）→ 矩阵（081t）→ 欠账（082t）→ 谓词（084t）→ 弱符号（085t）→ "r"（086t）→ f32（087t/089t）→ 截断存储（088t）
2026-10-12  infra：libm 恢复（066t）→ __muldc3（067t）→ setjmp（068t）→ changelog/三检查（069t）；qemu：2-NaN（QEMU-058t）
2026-10-12  testcases：picolibc 自带 test 接入（TESTCASES-042t，100% 目标 → 现场 blocked 0）
2026-10-13  6 模块 m 核验（INFRA-072m/LLVM-090m/QEMU-059m/TESTCASES-043m=里程碑；SPEC-136m=未通过）+ INTEG-034m（L3 修复后绿）
2026-10-13  **M7 收尾归档**（INTEG-035m，本任务）
```

**关键路径**：`INFRA-058t`（门控口径）→ `QEMU-056t`（RAM 基址）→ `INFRA-057t`（移植）→ `LLVM-079t`→`080t`（FP）→ `TESTCASES-042t`（自带 test）→ 模块 `m` → `INTEG-034m`。

---

## 5. 踩的坑与程序教训

### 5.1 过程事故（代表，均已处置）

| 项 | 教训 / 处置 |
|---|---|
| **L3 `diff_ir_lli` 结构性失败**（`INTEG-034m` 首次核验 `rc=1`） | M7 七个 LLVM 任务新增 **13** 个 `llc\|FileCheck` 结构测试**无 `i64 @main()` 值通道**，未入 `tests/llvm/ir-lli/manifest.yaml`（目录扫描 + **闭划分** 要求 `include ∪ exclude == 磁盘集`）⇒ `unclassified=13`。**处置**：`exclude` 追加 13 条（判定逻辑零改动）→ L3 回绿（`lessons`：**新增 lit 文件须同步登记 ir-lli manifest**）。 |
| **`SPEC-136m` 未通过** | `ISS-201`（`R_DADAO_REL26` 落点非 `call`/`jump` 时的防御分支未入规范）属**修改已用户确认的 `ADR-0019 D9`** ⇒ 须**逐条确认**，engineer/reviewer 未自拟自答（正确）⇒ **待裁定**。 |
| **台账待收敛（`INTEG-028t`）** | M6 任务完成区**声称已修**但 `resolved_by` 未回填的 7 条（`ISS-043/045/138/148/156/159/162`）在 M7 期独立核实后回填 `closed`（`Process-04 §3` 步骤 1）。教训：**完成区「已修」≠ 台账已关**，收尾须回填。 |
| **计数多次更正**（`ISS-193`/`194`/`195`/`196`） | 过滤表逐批删条目后，各类 blocked 计数随暴露面**动态变化**（如 `ISS-195` 1→5、`ISS-194` 26→27、`ISS-196` 6→7）⇒ 教训：**计数现场统计、不写死**（`INTEG-023k §E-4`）；before/after 须**逐条对账**。 |
| **消费侧过滤表与后端缺口耦合** | picolibc `meson.build` 源过滤表须**随后端缺口收口同步删条目**（41→11→9→5→3→2）；漏删 ⇒ 静默漏测（`lessons §2.11` 类）。 |

### 5.2 程序教训（M7 固化，指针 `lessons.md`）

- **门控分层落地**（`INFRA-058t`/`docs/Process-07`）：L1 秒~几十秒 / L2 几十~几百秒 / L3 几百~几千秒；**每层「能失败 + 结构断言」**。
- **被引用材料不得只放 `.work/`**：新增门控 `check-knowledge-refs`（悬空即红）。
- **子代理 workdir 作用域**（`INFRA-065t`）：规则层钉 workdir 已落地；**权限层（出界 `cd` fail-fast）当前服务未生效**（`ISS-199`）。
- **`.tao/knowledge/` 顶层白名单门控**（`INFRA-070t`/`check-knowledge-dir`）。

---

## 6. 遗留登记 / 风险

> 均为**已登记 = 已处置**；详情见 `.tao/knowledge/issues.yaml` / `milestones.md`「当前进度」/ 各归档任务书「遗留问题」。

| # | 项 | 类别 | 处置 |
|---|---|---|---|
| 1 | `ISS-193` picolibc 剩余 LLVM 缺口（(c) i64 `bswap`、(f) `long double` strtod；过滤表仅余 2 条） | llvm 能力缺口 | 保持 `open`（M7 收口未全清；blocked=0） |
| 2 | `ISS-198` 2-NaN payload 选择无测试覆盖（判别性错误规则注入不触发 FAIL） | 测试覆盖缺口 | 转遗留（建议补 1 条 payload 断言向量） |
| 3 | `ISS-187` 窄位指令利用不足 | llvm 优化候选（非缺陷） | 保持 `open`（用户「先只登记，暂不改」） |
| 4 | `ISS-188` FP 完备性剩余非 P0/P1 项（`fma`/`fpclass`/`f16` 等；均显式失败） | llvm 能力缺口 | 保持 `open` |
| 5 | `ISS-197` 内联汇编 `"m"` 约束触发 ISel 硬崩溃（rc=134） | 健壮性缺陷（非 M7 引入、非阻塞） | 保持 `open` |
| 6 | `ISS-079`/`108`/`164`/`074`/`167` 等既有挂账 | 挂账 | 保持登记（待相应实现/授权） |
| 7 | `INTEG-028t` 任务书（`**项目里程碑**：M6`）仍在 `.tao/tasks/` | M6 归档遗漏 | 待 M6 历史遗漏回溯补入或用户裁定（见 §8） |

---

## 7. **待用户裁定 / 操作清单**（汇总；**逐条**）

> 本清单为 M7 收尾**未决项**，均**不得**由子代理自拟自答；裁定后由主会话 `/dispatch`。

1. **`ISS-201`（决定 `SPEC-136m` 与项目 M7 达成）**：是否把未定义弱符号的**防御分支**（`R_DADAO_REL26` 落点**既非 `call-iiii`(0x74) 也非 `jump-iiii`(0x70)** 时实现显式报错）补入 **`ADR-0019 D9`** / **`contract-elf §3.3`**？——该点属**修改已用户确认的 `D9`** ⇒ 须**逐条确认**（`AGENTS.md`「ADR decision 逐条确认」）。**裁定通过** ⇒ `SPEC-136m` 可置 `里程碑`、`INTEG-034m` 可置 `里程碑` ⇒ **项目里程碑 M7 = 达成**；**否决/不改** ⇒ 明确「不入规范」并据此收敛。
2. **`ISS-199`（用户操作）**：出界 `cd` fail-fast 的**权限层**（agent frontmatter `external_directory` deny）在当前服务下**未生效** ⇒ **用户操作** `opencode service restart` → 越界 `cd` canary 复验（期望：不弹询问、命令未执行 = 生效）；**规则层已落地**。
3. **`ISS-202` / `INFRA-071t`（用户授权，3 项）**：`contract-*.md` → `contracts/` 迁移（`INFRA-070t` Phase B）是否授权——① 是否授权改**只读锁册** `spec/Toolchain-01`（及是否重算 `sha256`）；② `contracts/*.yaml` 内嵌旧路径字段如何处理（改/加映射/不动）；③ 范围是否扩到 `tools/**`/`components/**`/`tests/**`。
4. **`ISS-198`（建议）**：是否补 **1 条 2-NaN payload 断言向量**（构造 `(qNaN_a, sNaN_b)` 的 add/sub/mul/div，断言结果 payload = a 且 sNaN 被 quiet；须**独立派生**）。
5. **`ISS-200`（建议）**：pre-M6 LLVM 组件 changelog 历史缺口（`LLVM-013t`/`014t`/`019t`–`025t`/`028t`/`060t`）——**补录**还是**明确「历史不补」**（二者择一，勿悬空）。
6. **`INTEG-028t` 归属（建议）**：该任务书字段为 `M6`、提交晚于 M6 归档 ⇒ 是否**历史遗漏回溯补入 `.tao/archive/M6/`**（含更新 `M6/README.md` 计数）或**保留在 `.tao/tasks/`**。
7. **`ISS-193` 剩余面（可选）**：是否继续收敛 `bswap`（`libc/search/hash_page.c`）与 `long double` strtod（`libc/stdio/atold_engine.c`）——当前**无 test 暴露**（0 条）。
8. **M7 主题排期（可选）**：M7 排除项（动态链接 / linux-user / pk / golden）与候选（musl / `GOLDEN-*` 里程碑）**纳入 M8 的取舍**（用户 2026-10-11「须分层、不混」）。

---

## 8. 对 M8 的交接

### 8.1 可复用资产

- **picolibc 移植**：`components/picolibc/**`（cross file / machine dir / semihost stub）+ `make build-picolibc` + `make check-picolibc-tests[-full]`（`tools/testcases/picolibc_tests.py`）。
- **FP 后端**：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（P0/P1 + 谓词 + f32 libcall + 截断存储）+ `contracts/opcodes.yaml`/`contract-fp.md`。
- **ISA↔后端矩阵**：`tools/llvm/gen_isa_coverage.py` + `.tao/knowledge/llvm-isa-backend-matrix.{tsv,md}`（`check-isa-coverage` 已入 L1）。
- **门控分层**：`docs/Process-07` + `make check[-modules|-full]`。
- **过渡 oracle**：`docs/Process-05 §2.1`（边界 + 「非判据真源」）。
- **未定义弱符号口径**：`ADR-0019 D9` + `contract-elf §3.3`。

### 8.2 M8 待办（摘要）

FP 缺口剩余面（`ISS-193`/`188`）→ 2-NaN oracle（`ISS-198`）→ 权限 fail-fast 复验（`ISS-199`）→ contract 迁移（`ISS-202`）→ changelog 历史面（`ISS-200`）→ 台账收敛（§6 #7）→ 用户裁定的 M7 主题（§7 #8）。**下一阶段主题由 M8 规划 `k` 裁定**（`Process-04 §1`）。

---

## 9. 复现手册

```bash
make check                    # L1（含 check-patch-tree 4 comp/127、check-knowledge-refs/dir、check_issues）
make check-modules            # L2（check-lit 107/107 + check-qemu-smoke 86/86 + check-interface 83/83 + picolibc-tests fast）
make check-full               # L3（check-qemu-semantics 149/149 + test-m6：lit-full + diff_ir_lli + Embench 38/38）
make check-picolibc-tests-full  # picolibc 自带 test 全量（total/pass/fail/excluded/blocked）
python3 tools/infra/check_issues.py
python3 tools/infra/check_knowledge_refs.py
```

---

## 10. 审计追溯链

| 结论 | 任务 / 决策 | 证据（命令 / 日志） |
|---|---|---|
| picolibc 上游锁定 | `adr-0023` / `INFRA-055t` | `manifests/components.lock.toml`（`2ae376c6…`） |
| picolibc 移植 + 100% test | `INFRA-057t` / `TESTCASES-042t` / `TESTCASES-043m` | `make check-picolibc-tests-full`（235/213/0/22/0） |
| FP P0/P1 + 剩余面 | `LLVM-079t`–`089t` / `LLVM-090m` | `check-lit` 107/107；`check-isa-coverage` |
| ISA↔后端矩阵 | `LLVM-081t` | `.tao/knowledge/llvm-isa-backend-matrix.{tsv,md}` |
| RAM 基址 / 2-NaN | `QEMU-056t` / `QEMU-058t` / `QEMU-059m` | `check-interface` 83/83；`check-picolibc-tests-full` |
| 门控分层 | `INFRA-058t` / `docs/Process-07` | `make check-modules`/`check-full` |
| L3 修复 | `INTEG-034m` | `make check-full` rc=0（`.work/log/integ/INTEG-034m-*.log`） |
| **M7 达成** | **待 `ISS-201` 用户裁定** | `SPEC-136m`（未通过）+ `INTEG-034m`（残项 `ISS-201`） |
| 归档 | `INTEG-035m`（本任务） | `git status` R；`issues.yaml` 提取 12 条 |

> 历史日志：`.work/log/<module>/<任务ID>-<命令名>.log`（reviewer 重跑加 `-review-`）。
