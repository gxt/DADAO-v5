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

---

## 附录：M7 期补充记录（2026-11-01 由 `.tao/archive/M7/notes/` 全文并入）

> 原 `notes/` 5 份文件（合计 **746** 行）按主题分节全文保留；仅新增标题与来源行，正文不改。
> **编号说明**：附录 A–E 为本次并入的**顶层**编号；附录 B 内 embench 原文自带「附录 A/B」两个小节，沿用原文、不重编号。

---

## 附录 A：门控分层设计

> **来源**：原 `.tao/archive/M7/notes/gate-tiering-design.md`（48 行，全文；2026-11-01 并入）。

> **升格指针**（INFRA-058t，用户 2026-10-11 裁定「被引用材料不得只放 `.work/`」）：本文档由 `.work/log/integ/` 下同名文件升格至 `.tao/knowledge/`（原 `.work/` 副本已移出，该目录 gitignored、不再保留）。
# 门控分层设计（**用户 2026-10-09 裁定：推到 M7**）

> 用途：M7 规划时落地。**本轮不改 `Makefile`**。事实来源 = `Makefile` 现文 + `TESTCASES-037t` 现场数据。

## 一、用户提出的划分（原话要点）

- **最低层**：仓库完整性 + 各部分可用性；**几秒 ~ 几十秒**。
- **中层**：各模块功能；**不必过于全面，但各种类别都有**；**几十秒 ~ 几百秒**。
- **顶层**：较完整的检查；**几百秒 ~ 几千秒**。
- **每模块完整测试**：需要时单独调用。

**主会话评估**：划分**合适**，且与现状天然吻合（现 `make check` 已是"静态完整性 + 部分功能"混合体，只是没分层）。

## 二、现状事实（`Makefile`，2026-10-09 取得）

`check:`（`Makefile:348`）= 23 项，其中：

- **静态（不看执行行为）**：`manifest-check`、`check-patch-tree`、`check-index-blobs`、`check-spec-drift`、`check-spec-readonly`、`validate-encoding`、`validate-vectors`、`check-asm-list`/`-drift`/`-prose`、`check-spec-codeblocks`、`check-legality-drift`/`-invariants`、`check-scope`、`check-rule-refs`、`check-fp-contract`、`check-instrinfo`、`check-cfx-aliases`、`check-dirs`、`check-no-residue` + `check_issues.py` + `compileall tools`
- **功能**：`check-qemu-semantics`（**149 用例，跑 QEMU**）、`check-lit`（76 用例，≈1 s）
- **不在 `check` 里**：`test-codegen`(15)/`test-elf`(5)/`test-semihost`(10)/`check-lit-full`(227，**已 opt-in 雏形**)

**⚠️ 部分实测**：`TESTCASES-038t` 现场记录 **`make check` ≈ 32 s**（含 `check-qemu-semantics` 149 + `check-lit` 76 + 23 项静态）⇒ **现规模已在用户 L1 目标带（几秒~几十秒）边缘**；"庞大"是**增长趋势**问题（`check-lit-full` 227 / Embench / `test-m6` 待接入）。**M7 落地第 0 步仍须逐门控计时**（定位最重的那个，判断是否值得拆）。

## 三、建议映射（用现有真实目标名；M7 定稿时再调）

| 层 | 目标 | 内容 | 目标耗时 |
|---|---|---|---|
| L1 完整性/可用性 | **`make check`**（默认） | 上列**全部静态检查** + **组件可用性冒烟**（`llc`/`clang --print-targets`/`qemu` 可执行且含 `dadao`；**不跑被测语义**） | 秒 ~ 几十秒 |
| L2 模块功能代表集 | **`make check-modules`**（新） | `check-lit`(76) + `check-interface` + **`check-qemu-smoke`**（149 条**按语义类别各抽 1–2 条**）+ `test-codegen`/`test-elf`/`test-semihost`（现各 15/5/10） | 几十 ~ 几百秒 |
| L3 较完整 | **`make check-full`**（新） | `check-qemu-semantics` **全量** + `check-lit-full`(227) + Embench(`test-m6`) + 全量向量回放 | 几百 ~ 几千秒 |
| 按需（模块完整） | 各 `test-*`/`check-*` 单独调 | 模块全量、profiling | 不定 |

## 四、四条必须同时定的规则（否则分层会退化）

1. **默认 `make check` 只留 L1**（把 `check-qemu-semantics` 移出、新增 `check-qemu-smoke`）——这是让默认门控变快的**唯一**实质动作。
2. **每层都要"能失败 + 有结构断言"**（引 `lessons §2.20`（正则须证"确有命中"）、`§2.21`（须断言"结构"：成对/条数））——层越多，"空转绿灯"越多。
3. **L2 的"各类别都有"必须由类别清单机械派生**（按 `contracts/` 格式类/指令 `scope`、QEMU 语义类别），**不许手工挑**；**层间不重复**（同一检查只在一层跑）。
4. **触发点写进 `AGENTS.md`（≤2 行 + 门控名）**：任务收尾跑 **L2**、里程碑/`/complete` 跑 **L3**；否则"按需层"**必腐烂**。
   **风险**：分层后"L1 绿、L2/L3 红"会成常态 ⇒ 第 4 条是**前提**，非可选项。

## 五、待办（M7）

- [ ] 第 0 步：**逐门控计时**（`make -n` 不适用；逐目标 `time`），据实测确定 L1/L2/L3 边界与是否值得拆。
- [ ] 新增 `check-qemu-smoke`（类别代表子集，**机械派生**）。
- [ ] 新增 `check-modules` / `check-full`；`check` 收缩为 L1。
- [ ] `AGENTS.md` 写触发点（≤2 行 + 门控名）。
- [ ] 关联遗留（`TESTCASES-037t` reviewer 标注）：`MC/DADAO-gen`（227 条全量档）**仅 opt-in 校验** ⇒ `contracts/` 漂移在 `make check` 中**不报警**；M7 分层时决定它进 L2 还是 L3。

---

## 附录 B：Embench-IoT 接入分析

> **来源**：原 `.tao/archive/M7/notes/embench-analysis.md`（355 行，全文；2026-11-01 并入）。

> **升格指针**（INFRA-058t，用户 2026-10-11 裁定「被引用材料不得只放 `.work/`」）：本文档由 `.work/log/integ/` 下同名文件升格至 `.tao/knowledge/`（原 `.work/` 副本已移出，该目录 gitignored、不再保留）。
# Embench-IoT → DADAO 接入分析

> 分析对象：`.cache/embench-iot/`（浅克隆，只读；HEAD = `09c2ed8 "Remove CPU_MHZ references"`，分支 `master`，工作树干净）。
> 分析者：subagent（只读分析）。全程未修改 `.cache/embench-iot/`；临时产物在 `/tmp/opencode/embench-analysis/`；未提交 git。
> 结论证据：文件+行号 / 命令输出。事实与推测分开标注（"实测"= 本次跑出；"推理"= 未在本环境跑出）。

---

## 0. 结论摘要

| 维度 | 结论 | 关键证据 |
|------|------|----------|
| **平台接入面** | 极窄：平台只需实现 **3 个函数**（`initialise_board`/`start_trigger`/`stop_trigger`）；无 `uart_*`/`timer_*`/`power_*`/`exit` 要求 | `support/support.h:35-37`；`doc/README.md:277-284,686-690` |
| **端序** | 仅 **`md5sum` 1 个**基准有端序假设（`uint32_t*` 重解释），大端下会 **verify 失败**；其余 18 个与端序无关 | `src/md5sum/md5.c:101`（仅此一处重解释，全仓 `grep` 仅此命中）；实测见 §4 |
| **varargs / printf** | **不需要**。所有 `printf/puts` 均在 `DEBUG`/`ROUNDS`/`SLRE_DEBUG`/`DO_TRACING` 宏内，默认不编译 | `md5.c:103,121`；`nsichneu:43-46`；`slre:34-38` |
| **malloc** | **不用 libc malloc**；BEEBS 自带 bump 分配器（`beebsc.c`），堆是**静态数组** ≤ **8 KiB** | `support/beebsc.c:93-181`；`sglib/huff/qrduino HEAP_SIZE=8192` |
| **浮点** | 基准集**纯整数**（`statemate #define float int`、`depthconv` 的 `float` 字段未被使用）；但 **`wikisort` 调 `sqrt()`** ⇒ 需一个 double `sqrt`（libm 或自备） | `statemate:54`；`depthconv:66-67`；`wikisort:386` |
| **最小运行时** | `memcpy/memset/memmove/memcmp/strlen/strchr` + ctype(`tolower/isspace/isdigit/isxdigit`) + `sqrt` + 可能 `abort` | §3 逐基准 `nm -u` 实测 |
| **(B) 内存** | 单最大基准 ≈ **43 KB** 静态（xgboost）+ 栈 ≤ **~13 KB** + 堆 ≤ 8 KB ⇒ **≈ 64 KB**；全量 19 个**一次性常驻**合计 **267.7 KB** 静态。**当前 16 MiB RAM 远远够用（≥ 250× 余量）** | §5 |
| **最大缺口（工具链）** | **无 C 前端可用的 clang**：`.work/build/llvm/bin/` 只有 `llc/llvm-mc/ld.lld/llvm-objcopy`，**无 clang**；且 `components/llvm-project/patches/` **无任何 clang 侧补丁**（无 DADAO `TargetInfo`） | §6① |
| **OS/syscall** | **不需要 OS**。Embench 是 freestanding；停机/输出由 crt0 走 semihosting `SYS_EXIT` 完成 | `codegen_crt0.s`；`contract-semihosting.md §3/§5` |

> **重要澄清（与任务描述的目标用语）**：Embench 框架**不打印 "correct" 字符串**——`support/main.c` 完全不输出，正确性由 **进程退出码** 表达（`main` 返回 `!correct` ⇒ exit code 0 = 正确）。`"correct"` 字样属 **Dhrystone**（Embench `src/` 里**没有** Dhrystone，见 §1 末）。所以"在 QEMU 打出 correct"是 Dhrystone 的说法；对 Embench，等价判据是 **exit code == 0**。

---

## 1. 仓库结构与构建方式

### 1.1 官方推荐的新平台接入流程

事实（`doc/README.md`「Adding a new board to Embench」，行 667-723）：

1. 在 `examples/<arch>/<board>/` 下建 **两个文件**：`boardsupport.h`（可为空）+ `boardsupport.c`（行 674-679）。
2. `boardsupport.c` **只需实现 3 个 `void` 函数**（行 686-690）：
   - `void initialise_board (void)` — 板级初始化；
   - `void start_trigger (void)` — 计时开始；
   - `void stop_trigger (void)` — 计时结束。
3. 用时序无关（GDB 设断点计时）时，`start/stop_trigger` 可为空体（行 700-712）。
4. 可选放链接脚本等板级文件（行 721-723）。
5. 用 **SCons** 构建（行 312-315），关键命令行变量（行 288-306）：`cc`、`ld`、`cflags`、`ldflags`、`user_libs`、`gsf`、`warmup_heat`；选项 `--build-dir`、`--config-dir`（**必须**）。

### 1.2 构建系统：SCons 为主，`examples/` 无手写 Makefile

- `sconstruct.py` **是唯一的构建脚本**（行 1-97）。它：
  - 收集 `src/*/` 下每个基准目录（行 16-18）；
  - 编译支持对象 `support/main.c`、`support/beebsc.c`、`<config>/boardsupport.c`（行 59-65）；
  - 每个基准 `Glob(src/<bench>/*.c)`（行 89）并 `Program()` 链接（行 96）。
  - 变量：`cc`（默认 `$CC`）、`cflags`（默认 `$CCFLAGS`）、`ld`（默认 `$LINK`）、`ldflags`（默认 `$LINKFLAGS`）、`user_libs`、`warmup_heat`、`gsf`（行 30-38）。
  - 预处理宏：`WARMUP_HEAT`、`GLOBAL_SCALE_FACTOR`（行 49-50）；`CPPPATH=['support', config_dir]`（行 51）。
  - **不使用 `OBJCOPY`**；`ld` 默认 = `cc`。
- 实测：`examples/**` 下**没有任何构建用 Makefile**（唯一的 `doc/Makefile` 用于文档）；每个 `examples/<board>/README.md` 只给一行 `scons ...` 命令。例：
  - `examples/native/speed/README.md:6`：
    `scons --config-dir=examples/native/speed/ cflags="-O2 -fdata-sections -ffunction-sections" ldflags="-O2 -Wl,-gc-sections" user_libs=-lm`
  - `examples/riscv32/rv32wallyverilog/README.md:7-9`：
    `scons --config-dir=... user_libs=-lm cc=riscv32-unknown-none-elf-gcc cflags='-fdata-sections -ffunction-sections -mabi=ilp32d' ldflags='-Wl,-gc-sections -mabi=ilp32d -nostartfiles -T${CONFIG_DIR}/link.ld'`
  - `doc/README.md:336-351` 给出同一 RISC-V 例子逐项解释（`-nostartfiles -T${CONFIG_DIR}/link.ld`，`-ffunction-sections/-fdata-sections` + `-Wl,-gc-sections`，`user_libs=-lm`）。

**结论**：接入 DADAO 有两条路——(a) 用 SCons + `--config-dir=examples/dadao/<board>/`（最省事，但要提供 `cc`=dadao clang、`ld`=ld.lld、`ldflags=-T dadao.lds -nostdlib`、`user_libs` 含最小运行时与 `-lm`）；(b) 手写一个 `Makefile`（仓库**未**提供，需自建），逐基准 `cc -c` + `ld`。SCons 的路更贴合官方，但需要`cc` 可执行；由于我们**没有可用 clang**（§6），任一路都先卡在工具链。

### 1.3 19 个基准与"有没有 Dhrystone"

`src/` 下 19 个（实测 `ls`）：`aha-mont64, crc32, depthconv, edn, huffbench, matmult-int, md5sum, nettle-aes, nettle-sha256, nsichneu, picojpeg, qrduino, sglib-combined, slre, statemate, tarfind, ud, wikisort, xgboost`。**没有 Dhrystone**——Dhrystone 需另行准备（属另一条链，不在本仓库）。每个基准一个目录，源文件数 1–3 个（如 `picojpeg`=3、`qrduino`=5）。

---

## 2. `support/` 接口面

### 2.1 逐文件职责

| 文件 | 职责 | 关键行 |
|------|------|--------|
| `support/support.h` | 框架接口声明（平台 + 基准两侧）+ 引入 `beebsc.h` | 31,35-59,63 |
| `support/board.c` | **只是包装**：`#include "boardsupport.c"`（scons **不编译**它） | 14 |
| `support/chip.c` | 芯片相关包装：`#include "config.h"`；`HAVE_CHIPSUPPORT_H` 时含 `chipsupport.c`；否则空 TU | 14-25 |
| `support/main.c` | 基准驱动 `main()`（调用序列，见 2.3） | 17-39 |
| `support/beebsc.c` | BEEBS 本地库：`rand_beebs/srand_beebs`、bump 堆 `init/check/malloc/calloc/realloc/free_beebs` | 42-181 |
| `support/beebsc.h` | 上述声明 + `RAND_MAX=2^15-1`、`assert_beebs`、浮点比较宏 | 22,39,41-44,48-56 |
| `support/dummy-benchmark/dummy.c` | 基准桩（返回值 `0xBE`），供构建冒烟 | 11-35 |

> 注意：`scons` 编译的是 `<config>/boardsupport.c`，**不是** `support/board.c`（`sconstruct.py:63`）。`board.c`/`chip.c` 是给别的构建流/芯片层用的包装。

### 2.2 必须由"平台"实现的函数清单（原型 + 行号）

来源 `support/support.h`：

```
void initialise_board (void);      // 行 35  —— 平台实现
void start_trigger   (void);       // 行 36  —— 平台实现
void stop_trigger    (void);       // 行 37  —— 平台实现
```

仅这 3 个。**不存在** `uart_*` / `timer_*` / `power_*` / `exit` 等平台钩子（全仓 `grep` 无）。计时/打印是**平台自选项**，不是框架要求。

**由基准实现**（行 31,43,49,54,59）：`initialise_benchmark`、`warm_caches(int)`、`benchmark()`、`verify_benchmark(int)`。

**由支持库实现**（`beebsc.c/h`）：`rand_beebs`、`srand_beebs`、`init_heap_beebs`、`check_heap_beebs`、`malloc_beebs`、`calloc_beebs`、`realloc_beebs`、`free_beebs`（行 48-56）。

### 2.3 `main()` 调用序列（`support/main.c:25-37`，实测逐行）

```
initialise_board();          // 25  平台
initialise_benchmark();      // 26  基准
warm_caches(WARMUP_HEAT);    // 27  基准
start_trigger();             // 29  平台
result  = benchmark();       // 30  基准
stop_trigger();              // 31  平台
correct = verify_benchmark(result);  // 35  基准（返回 -1=不做校验；否则非 0=正确）
return (!correct);           // 37  ⇒ 正确时返回 0
```

`result` 声明为 `volatile int`（行 22），防优化。`verify_benchmark` 语义见 `support.h:28-31`（返回 -1 表示"未做校验"）。

---

## 3. 需要哪些 libc / 运行时

### 3.1 实测方法

用宿主 `gcc -Os -ffreestanding -fno-builtin -c` 逐基准编译（含 `support/main.c`+`support/beebsc.c`），再 `nm -u` 列**未定义符号**（脚本 `/tmp/opencode/embench-analysis/free_syms.sh`）。去掉基准内部/框架符号后，**真正的外部运行时符号**如下：

| 基准 | 需要的外部运行时符号 |
|------|----------------------|
| aha-mont64, depthconv, netttle-aes, nettle-sha256, nsichneu, statemate | （无）|
| crc32, tarfind | `rand_beebs`,`srand_beebs`（beebsc 提供）|
| edn, matmult-int, ud | `memcmp` |
| huffbench | `malloc_beebs`,`free_beebs`,`init_heap_beebs`,`memcmp` |
| md5sum | `malloc_beebs`,`calloc_beebs`,`free_beebs`,`init_heap_beebs` |
| picojpeg | `memcmp` |
| qrduino | `malloc_beebs`,`calloc_beebs`,`free_beebs`,`check_heap_beebs`,`init_heap_beebs`,`memcmp`,`memmove`,`strlen` |
| sglib-combined | `malloc_beebs`,`check_heap_beebs`,`init_heap_beebs`,`memcmp` |
| slre | `memcmp`,`memmove`?,`strchr`,`strlen`,`tolower`（+ctype 内建 `isspace/isdigit/isxdigit`）|
| wikisort | `memcmp`,`memmove`,`sqrt`,`rand_beebs`,`srand_beebs` |
| xgboost | （无外部，仅内部 `predict` 等）|

（说明：`memcpy/memset` 在 gcc 下被内联/展开而未出现在未定义表；**clang 会发出对 `memcpy/memset/memmove` 的调用**，必须自备——见下。）

### 3.2 最小运行时清单（freestanding libc 子集）

必须提供（**至少**）：
- `memcpy`、`memset`、`memmove`、`memcmp`（编译器生成 + 基准显式调用；`-ffunction-sections -Wl,--gc-sections` 可裁掉未用者）
- `strlen`、`strchr`（`qrduino`/`slre`）
- ctype：`tolower`（`slre:184,213,214`），及其依赖的 `isspace`(`:143,148`)、`isdigit`(`:153`)、`isxdigit`(`:499`)；注意 `slre` 用 `<ctype.h>`，宿主 glibc 用表宏 `__ctype_b_loc`/`__ctype_tolower_loc`（**非可移植**，需自备一组简单 ctype）
- `sqrt`（**double**，`wikisort:386`）——需 libm 或自备 double `sqrt`
- （条件）`abort`（`nettle-sha256:152` 的不可达 `default` 分支；开 `--gc-sections` 时通常被丢弃，否则需桩）

### 3.3 三项关键判定（任务重点）

**(a) 是否依赖变参 `printf`？→ 不需要。**
逐一核对所有 `printf/puts/fprintf` 出现点，**全部在调试宏内**，默认构建**不编译**：
- `md5.c`：`:103` 在 `#ifdef DEBUG`、`:121` 在 `#ifdef ROUNDS`、`:161/224` 在 `#ifdef DEBUG/ROUNDS`（`md5.c:103,121,155,161,224`）。
- `nsichneu/libnsichneu.c`：`:51` 在 `#ifdef DO_TRACING`，且 `:35` 该宏被注释掉。
- `slre/libslre.c`：`:35` `#define DBG(x) printf x` 仅在 `#ifdef SLRE_DEBUG` 下（`:34-38`）。
- `aha-mont64:189/205/208`、`huffbench:341-342` 均为注释。
- 其余基准无 `stdio.h` 使用（`tarfind.c` 含 `stdio.h` 但无 printf 调用，实测 `grep` 无命中）。

⇒ 框架与基准集**不需要 varargs 调用约定**。这对 DADAO 尤其重要，因为 `contract-abi.md` 明确 **`varargs` 属 `Excluded from M3`**（§开头 "Excluded" 清单）。**唯一需要 varargs 的场景**是"你想让 board shim 打印诊断字符串"——那也**不必**用 `printf`，用 semihosting `SYS_WRITE0` 直接写串即可（见 §6②）。

**(b) 是否用 `malloc`？→ 不用 libc malloc，但用 BEEBS 自带堆。**
- 使用方（实测 `grep malloc_beebs`）：`sglib-combined`、`md5sum`、`huffbench`、`qrduino`、`tarfind`；调用者共 5 个基准。
- 实现：`beebsc.c:93-125` `malloc_beebs` = 单调 bump 指针（`heap_ptr += size`，不 free）；`free_beebs` 空实现（`:178-181`）；`calloc_beebs`=`malloc_beebs`+`memset`（`:132-144`）。
- 堆**不是从 libc 拿**，而是一个**静态数组**，由各基准用 `init_heap_beebs((void*)heap, HEAP_SIZE)` 注册：
  - `sglib-combined/combined.c:24-25` `HEAP_SIZE 8192`
  - `huffbench/libhuffbench.c:59-60` `HEAP_SIZE 8192`
  - `qrduino/qrtest.c:27-28` `HEAP_SIZE 8192`
  - `md5sum/md5.c:22,30` `HEAP_SIZE (2000+1016+64)=3080`
  - `tarfind/tarfind.c:40-41` `HEAP_SIZE roundup(sizeof(tar_header_t)*ARCHIVE_FILES, sizeof(void*))`
- ⇒ **无需 libc 的 `malloc/free`，也无需 OS `brk`**；只需一块 ≤ 8 KiB 的静态 RAM（已计入 §5 的 `.bss`）。

**(c) 是否需要浮点？→ 基准集是纯整数；但有 1 处 `sqrt`。**
- `statemate`：源码里 `#define float int`（`libstatemate.c:35-54`），注释明说 "so we don't need a floating point library"。
- `depthconv`：结构体里有 `float float_activation_min/max`（`:66-67`），但**全文件无对它们的读写**（实测 `grep` 仅声明）——量化 int8 路径。
- `ud`：`fabs` 在注释中（`:101,191`）。
- `wikisort`：`:386` `long block_size = sqrt (decimal_step);` **非注释、会编译**，且 `#include <math.h>`（`:29`）。⇒ 需要 `sqrt`（double）。
- `support/beebsc.h:41-44` 提供 `float_eq_beebs/double_eq_beebs`，但**无任何基准使用**（实测 grep 仅声明）。
⇒ **不需要 FP 指令/FP ABI**；只需链接一个 double `sqrt`（或改 `wikisort` 用整数 sqrt——但那是改基准，不建议）。

---

## 4. 端序 / 类型假设

### 4.1 端序

实测全仓搜索 `__BYTE_ORDER__|_LITTLE_ENDIAN|__CHAR_UNSIGNED__|htonl|bswap`：`src/` 与 `support/` **零命中**（`examples/arm/...` 的 CMSIS 头有，但**不参与**构建）。

- `nettle-sha256`：用**逐字节**宏 `READ_UINT32/WRITE_UINT32`（大端，`nettle-sha256.c:112-129`）与 `_nettle_write_be32`（`:131`）——**端序无关**。
- `nettle-aes`：用**逐字节** `LE_READ_UINT32/LE_WRITE_UINT32`（`nettle-aes.c:27-40`）——**端序无关**。
- **唯一风险点 `md5sum`**：`md5.c:101`
  ```c
  uint32_t *w = (uint32_t *) (msg + offset);
  ```
  这是**唯一**一处 `char*`→`uint32_t*` 重解释（全仓 `grep` 仅此命中，实测）。MD5 规范要求**小端**字序；在大端机上该读入会产生不同的字，且 `md5.c:93` 的长度写入 `memcpy(...,&bits_len,4)` 也是本机字序。此外 `verify_benchmark` 硬编码 `RESULT 0x33f673b4`（`:28,247`）——该值在 x86（小端）上得出。
- **实测反证（临时树，不改仓库）**：把 `md5.c` 的 `uint32_t*` 读改写为**显式大端**读（`/tmp/opencode/embench-analysis/be/md5.c`），宿主 gcc 重编运行：
  ```
  大端字序模拟 exit=1  (0=正确, 非零=verify 失败)
  ```
  ⇒ 证实 **md5sum 的正确性依赖小端**。**大端 DADAO 上 md5sum 会 FAIL**（推理：DADAO 为 `ELFDATA2MSB`/`E` DataLayout，见 §6；未在大端实机跑，属高置信推理）。

### 4.2 类型宽度（32 位 vs 64 位）

- `crc32/crc_32.c:44` `typedef unsigned long DWORD;`、`huffbench:64` `typedef unsigned long bits32;` —— 在 LP64 / DADAO(64 位)下 `unsigned long` = 64 位。
- **实测**：以宿主 `gcc`（x86-64 **LP64**，`long`=64）链接并运行**全部 19 个基准**，**19/19 exit=0（PASS）**（命令见 §5.1）。
  - `crc32` 之所以 64 位安全：`crc32pseudo` 返回 `~oldcrc32`，但 `benchmark_body` 取 `(int)(r % 32768)`（`:203`），`32768=2^15` 取模只保留低 15 位，高位垃圾不影响结果（`crc32:160-163,203,210`）。
  - ⇒ **`long`=64 位不会破坏基准集**（有实测）。端序才是唯一坑。
- `__CHAR_UNSIGNED__`：无依赖。

---

## 5. (B) 内存需求（实测估算）

### 5.1 静态 footprint（宿主 `gcc -Os`，每基准 + 框架，单位字节）

命令：`gcc -Os -DWARMUP_HEAT=1 -DGLOBAL_SCALE_FACTOR=1 -I support -I src/<b> -I . support/main.c support/beebsc.c examples/native/speed/boardsupport.c src/<b>/*.c -lm -o out` 然后 `size out`（脚本 `/tmp/opencode/embench-analysis/build_size.sh`）。

| 基准 | .text | .data | .bss | 合计 |
|------|------:|------:|-----:|-----:|
| aha-mont64 | 3062 | 600 | 64 | 3726 |
| crc32 | 4377 | 544 | 40 | 4961 |
| depthconv | 2754 | 1200 | 224 | 4178 |
| edn | 6962 | 608 | 2512 | 10082 |
| huffbench | 5027 | 608 | 8768 | 14403 |
| matmult-int | 6256 | 608 | 16072 | 22936 |
| md5sum | 3548 | 600 | 3176 | 7324 |
| nettle-aes | 15242 | 1104 | 1088 | 17434 |
| nettle-sha256 | 8159 | 752 | 96 | 9007 |
| nsichneu | 24034 | 608 | 200 | 24842 |
| picojpeg | 13514 | 608 | 2560 | 16682 |
| qrduino | 11490 | 624 | 8320 | 20434 |
| sglib-combined | 13012 | 608 | 8848 | 22468 |
| slre | 6430 | 760 | 40 | 7230 |
| statemate | 7549 | 600 | 384 | 8533 |
| tarfind | 2462 | 544 | 9040 | 12046 |
| ud | 3284 | 608 | 3616 | 7508 |
| wikisort | 13179 | 736 | 3264 | 17179 |
| **xgboost** | **42460** | **600** | **40** | **43100 ← 最大** |
| **合计（全 19）** | 192801 | 12920 | 68352 | **274073 (267.7 KiB)** |

> 口径说明：宿主 64 位 LP64 + glibc，`-Os`。链接结果可能含少量 glibc/启动代码（如 `sqrt`/`abort`），使 `.text` 略偏大；DADAO 的实际值会有差异，但**量级与"≤ 64 KB/基准"结论稳健**。DADAO 为 64 位（指针 8B），与宿主一致，故可比性较好。

### 5.2 栈深度（`-fstack-usage` 单帧最大值，宿主 gcc）

| 基准 | 最大单帧 | 函数 |
|------|--------:|------|
| **huffbench** | **12896** | `compdecomp`（`freq[512]/heap[256]/link[512]/code[256]/clen[256]` 全在栈上） |
| wikisort | 4496 | `WikiSort`（非递归，见下） |
| slre | 4112 | `slre_match`（对 regex 列表逐项调用，深度小） |
| matmult-int | 3216 | `verify_benchmark`（期望值常量数组） |
| sglib-combined | 1824 | `benchmark_body` |
| edn | 1616 | `verify_benchmark` |
| 其余 | ≤ 744 | — |

- 递归核对：`wikisort` 的 `WikiSort` 定义在 `:332`，**无自递归**（`:1105` 是外层调用）；`slre_match`（`:605`）对子 regex 递归，深度受 regex 数量限制（小）；`sglib` 明说"handle recursive calls without recursion"（`sglib.h:131-133`，显式数组栈）。
- ⇒ **栈高水位 ≈ 13 KiB**（huffbench）。为安全建议**预留 ≥ 64 KiB 栈**（考虑中断/实现差异与 slre/wikisort 的有限递归）。

### 5.3 堆需求

- BEEBS bump 堆 = 静态 `heap[]`，`HEAP_SIZE` 最大 **8192 B**（sglib/huffbench/qrduino），已计入上表 `.bss`；`md5=3080`、`tarfind≈9040`（起 `.bss` 中）。
- `check_heap_beebs` 会校验是否溢出（`beebsc.c:77-81`）——若 RAM 配置过小导致堆溢出，基准会返回错误，故堆**必须**完整放下。

### 5.4 (B) 结论

| 情形 | RAM 需求（代码 + 数据 + 栈 + 堆） | 说明 |
|------|-----------------------------------|------|
| **单个最大基准** | **≈ 64 KiB**（43 KB 静态 + ≤13 KB 栈 + ≤8 KB 堆；且栈/堆多在 `.bss` 内已计） | 峰值来自 **xgboost**（静态 43 KB）；huffbench 栈最高但静态仅 14 KB |
| **全量 19 个"逐个跑"** | **≈ 64 KiB**（一次只驻留一个） | 顺序执行，各基准独立加载 |
| **全量 19 个"一次性常驻"** | **≈ 268 KiB** 静态 + 每任务各自栈/堆（若并发） | 合计 274073 B |

**当前 16 MiB RAM@0 是否够？→ 远远够（余量 ≥ 250 倍）。**
- 事实：RAM@0 = `[0, 16 MiB)`，另一段旧 RAM = `0xffff_0000_0000`（16 MiB）（`components/qemu/patches/target/dadao/cpu.h.patch:66-72`；`dadao-machine.c.patch:485-495`）。
- 即使用户要求的 1 GiB 也"远超"（与 `INTEG-023k §D.0 实测①` 的结论一致：现最大单程序 `.o` 仅 1128 B）。**16 MiB 对 Embench 绰绰有余**。

---

## 6. 对 DADAO 的接入点清单

### ① 工具链需要什么

**事实（实测 `.work/build/llvm/bin/` 与补丁集）**：
- 已有：`llc`（`llc --version` 列出 `dadao - DADAO SimRISC`）、`llvm-mc`、`ld.lld`、`llvm-objcopy`、`llvm-objdump`。
- **缺失且关键：没有可用的 C 前端 `clang`**（`.work/build/llvm/bin/` 无 `clang*`；`command -v clang` 只命中宿主 `/usr/bin/clang 18.1.3`，**非 dadao target**）。
- **更关键：`components/llvm-project/patches/` 58 个补丁里，`grep clang` 零命中**——**没有** clang 侧 DADAO `TargetInfo`（`clang/lib/Basic/Targets/DADAO.*`）、没有 driver/triple 接入。仅 `Triple.cpp/Triple.h`（LLVM 层）认识 `dadao`。

⇒ 要把 Embench（C 源码）编成 DADAO 目标码，**必须新增 clang 前端支持**（`clang -target dadao-unknown-elf` 的 `TargetInfo`：端序=big、指针=64、`long`=64、`char` 默认 signed/unsigned、对齐等），或采用等价的 C→LLVM-IR 通道。**仅构建 clang 二进制还不够**——需补 clang TargetInfo 补丁。这与 `INTEG-023k §D.1 #5`（clang 建议不纳入 M6）冲突：**Embench 目标事实上要求 C 前端**。
- 其它工具用途：`llc -march=dadao`（IR→asm）、`llvm-mc --triple=dadao -filetype=obj`（asm→obj）、`ld.lld -T tests/scripts/dadao.lds`（链接，产出 `ET_EXEC`/`EM_DADAO`/`ELFDATA2MSB`/`e_flags=1`）、`llvm-objcopy`（raw-bin 路径 `--only-section=.text -O binary`）、`llvm-size/llvm-objdump`（量 footprint）。
- DataLayout（后端已定）：`E-m:e-p:64:64-i64:64-i128:128-n8:16:32:64-S128`（`components/.../TargetDataLayout.cpp.patch:11`）——**大端 `E`、指针 64**。clang TargetInfo 需与此一致。

### ② board shim 需实现哪些函数（映射到 semihosting）

只需 `examples/dadao/<board>/boardsupport.{c,h}` 里的 3 个函数：

| 函数 | 建议实现 | 映射的 semihosting 服务（`contract-semihosting.md §3`） |
|------|----------|--------------------------------------------------------|
| `initialise_board(void)` | 空（或做一次性板级初始化） | 无（可选 `SYS_HEAPINFO 0x16`） |
| `start_trigger(void)` | 计时开始：记录 tick | `SYS_ELAPSED 0x30`（64 位 target ticks）或 `SYS_CLOCK 0x10`（百分秒，太粗） |
| `stop_trigger(void)` | 计时结束：读回 tick | 同上 |
| （可选）打印诊断 | 直接写串，**无需 printf/varargs** | `SYS_WRITE0 0x04`（0 结尾串）/ `SYS_WRITEC 0x03`（单字符） |
| （停机） | 由 crt0 完成，**基准/板级不实现** | `SYS_EXIT 0x18`（或 `SYS_EXIT_EXTENDED 0x20`）|

调用约定：`rd16`=服务号、`rb16`=参数块指针、`rd31`=返回值；`trap cfx_umon, 0x30000`（`immu18[17:16]==2'b11`）触发（`contract-semihosting.md §1-§2`；`common-semi-target.c.patch`）。

**仅做正确性（不测速）时**，`start/stop_trigger` 可照搬官方样板（volatile asm clobber memory，`doc/README.md:700-712`）。exit code = `main` 返回值低字节（`codegen_crt0.s` 注释；`contract-semihosting.md §5`），故 Embench 的 pass 判据 = **QEMU 进程退出码 0**。

### ③ crt0 / 链接脚本需满足什么

**已有**：`tests/scripts/codegen_crt0.s`、`tests/scripts/dadao.lds`。
- `dadao.lds`：`ENTRY(_start)`；`MEMORY{RAM 0xffff00000000 LEN 16M; ROM 0xffffffff0000 LEN 64K}`；段序 `.text→.rodata→.data→.bss`；`ASSERT` 防超界（脚本行见文件）。**段布局已满足 Embench 需求**（read-only 常量进 `.rodata`，可变数据进 `.data`/`.bss`）。
- `codegen_crt0.s`：`_start` 设 `SP=rb1=0xffff_00ff_0000`、`call main`、把 `rd31` 经 `SYS_EXIT` 传给宿主。
- **`.bss` 清零**：crt0 **不做**；由 **QEMU 加载器**完成——`dadao_load_elf` 对每个 `PT_LOAD` 做"`p_filesz` 数据 + `p_memsz-p_filesz` 零填充"（`dadao-machine.c.patch:398-422`）。⇒ Embench 的静态零初始化（各 `heap[]`、`.bss` 数组）由加载器保证。**前提**：`.bss` 必须与 `.data` 处于同一 `PT_LOAD` 且 `p_memsz>p_filesz`（`dadao.lds` 正是如此）。
- **不需要** `__attribute__((constructor))` / `.init_array`：Embench 无 C++ 全局构造、无 `__libc_init`。只要 `_start→main` 即可。
- **栈**：`SP` 上方到 RAM 顶（`0xffff_0100_0000`）约 **64 KiB** 可用；下方到 `_end` 也充裕，对 §5.2 的 ~13 KiB 高水位足够。

### ④ 是否需要 OS / syscall

**不需要。** Embench 是 freestanding、无 OS 假设（`README.md:3-6`：assumes "no OS, minimal C library support, no output stream"）；唯一"系统"交互是**停机**（`return` 出 `main`），由 crt0 用 semihosting `SYS_EXIT` 完成。无 `open/read/write/brk/sbrk` 需求（输出流本就不需要；BEEBS 堆自带）。

---

## 7. 不确定项 / 未验证事项（诚实列出）

1. **大端实机未跑**：本环境**无**大端交叉编译器/`qemu-user`（`command -v qemu-s390x powerpc-linux-gnu-gcc ...` 全空）。`md5sum` 在大端失败由"临时树显式大端字序模拟"反证（exit=1）＋代码事实推出，**未在 DADAO/QEMU 上实跑**。
2. **DADAO 侧真实 footprint 未知**：§5 表为**宿主 gcc x86-64** 值，非 DADAO clang 值。二者指针宽度一致（64 位），但指令编码/对齐/libcall 差异会使数值变化；**量级结论稳健，精确值待 clang 就位后重测**。
3. **clang TargetInfo 缺失的确切后果未实测**：因无 clang 二进制，未实际执行 `clang -target dadao-unknown-elf`（预期报 unknown target triple）。"构建 clang 后仍不能编 dadao C"是基于"补丁集无 clang 侧改动"的推理。
4. **`abort` 是否真被链接**：取决于 `--gc-sections` 与 nettle-sha256 的不可达分支；未在 DADAO 链接层验证。
5. **`sqrt` 的来源未定**：可用 DADAO 版 libm（不存在）或自备 double `sqrt`（编译器内建 `__builtin_sqrt` 仍需 runtime）；具体落点未决。
6. **Embench `scons` 全套脚本**（`benchmark_speed.py` 需一个 `pylib/run_dadao.py` target 模块）未深究——若走官方测速脚本，需自建 target 模块解析 QEMU 输出/退出码。
7. **Dhrystone 不在本仓库**：任务"先 Dhrystone 打出 correct"的 Dhrystone 来源未在本次分析范围内（`.cache/embench-iot/src/` 无 Dhrystone）。
8. **RAM@0 vs 旧 RAM 的最终链接地址**：`dadao.lds` 链到旧 RAM `0xffff_0000_0000`（在加载白名单内）；若 M6 改为"RAM 从 0 起"，则 `dadao_load_regions[]` 需扩 `RAM@0`（`dadao-machine.c.patch:184-187` 现**不含** RAM@0）——本分析按**现状 16 MiB 够用**给结论，不预判 M6 地址迁移。

---

## 附录 A：证据脚本与临时产物

均在 `/tmp/opencode/embench-analysis/`（非易失证据按需再留 `.work/log/`）：

- `build_size.sh` / `footprint.txt`：逐基准 `gcc -Os` 链接 + `size`（§5.1 表）。
- `free_syms.sh` / `free/`：`-ffreestanding -fno-builtin` 逐基准 + `nm -u`（§3）。
- `be/md5.c`：md5 大端字序模拟（§4.1 反证）。
- 栈：`gcc -fstack-usage`（§5.2）。

## 附录 B：关键文件索引

| 主题 | 文件:行 |
|------|--------|
| 三平台函数 | `support/support.h:35-37`；`doc/README.md:686-690` |
| main 调用序列 | `support/main.c:25-37` |
| 变参 printf 均被宏屏蔽 | `md5.c:103,121`；`nsichneu:43-46`；`slre:34-38` |
| BEEBS 堆 | `support/beebsc.c:93-181`；`sglib:24-25`；`huff:59-60`；`qrduino:27-28` |
| 端序唯一坑 | `md5.c:101` |
| sqrt | `wikisort/libwikisort.c:386` |
| ctype | `slre/libslre.c:24,143,153,184` |
| SCons 变量 | `sconstruct.py:30-38,49-51,59-65,89,96` |
| 加载器零填 .bss / 白名单 | `components/qemu/patches/hw/dadao/dadao-machine.c.patch:184-187,398-422` |
| RAM 尺寸 | `components/qemu/patches/target/dadao/cpu.h.patch:66-72` |
| semihosting 服务表/停机 | `.tao/knowledge/contract-semihosting.md §1-§3,§5` |
| DataLayout | `components/llvm-project/patches/llvm/lib/TargetParser/TargetDataLayout.cpp.patch:11` |

---

## 附录 C：LLVM-070t 根因诊断报告

> **来源**：原 `.tao/archive/M7/notes/LLVM-070t-rootcause.md`（86 行，全文；2026-11-01 并入）。

> **升格指针**（INFRA-058t，用户 2026-10-11 裁定「被引用材料不得只放 `.work/`」）：本文档由 `.work/log/llvm/` 下同名文件升格至 `.tao/knowledge/`（原 `.work/` 副本已移出，该目录 gitignored、不再保留）。
# LLVM-070t — `-O2` 误编译致死循环：根因诊断报告（G6 / ISS-180）

> 判据：`-O2` 产物在 QEMU 下 `GUEST_EXIT=124`（超时）而 `-O0`/`-O1` `exit=0`。

## 1. 现象与最小复现

- 最小复现：`.work/source/embench-iot/src/matmult-int/matmult-int.c` 仅把
  `LOCAL_SCALE_FACTOR 39` 改 `3`（副本 `/tmp/opencode/TESTCASES-039t/red/mm.c`）。
- `-O2` 死循环（QEMU 输出仅 `[board:init]`，无 `[board:start]`）；`-O0`/`-O1` **exit=0**。
- 现场：`/tmp/opencode/LLVM-070t/red/`（`mm.elf` = `-O2`；`mm_O0.elf`/`mm_O1.elf`）。
- 证据：`.work/log/llvm/LLVM-070t-e2e-O2.log`（修复后 4 例 exit=0）。

## 2. 定位过程（逐层收窄）

1. **执行轨迹**（`qemu -d exec,nochain`）：死循环在 `memcpy`（ELF `0x1474`/`0x1488`）
   反复自转；`benchmark_body` 每次迭代都重新调用 `memcpy` ⇒ 是 **`benchmark_body` 的
   循环不退出**，不是 `memcpy` 本身（`memcpy` 是 `-O0` 编译，各优化级相同）。
2. **IR 隔离**：`clang -O2 -emit-llvm` 的 IR 语义正确（循环控制正确）；
   把该 IR 用 `llc -O0/-O1/-O2` 再编译**均死循环** ⇒ 与 llc 优化级无关（IR 已足够）。
3. **尺寸二分**：把 `UPPERLIMIT` 从 20 降到 18 ⇒ **exit=0**（终止）；19/20 ⇒ 死循环。
   二分发现差异是 **`Test()`→`Multiply()` 是否被内联 + 内层循环是否被完全展开**：
   - `-O2 -mllvm -unroll-threshold=0`（禁展开）⇒ **exit=0**；
   - 删除 IR 中的展开乘法块（`for.cond1.preheader.i.i`…`for.inc9.i.i`）⇒ 终止（exit=1）。
4. **反汇编对比**（`llvm-objdump -d`）：`benchmark_body` 的 gsf/lsf 循环控制指令
   （`cmp`/`br.eq`/`add.si`）在 `-O1` 与 `-O2` **逐字节相同**，且循环计数器
   （`rd32`=gsf、`rd33`=lsf、`rd35`=lsf_cnt、`rd36`=gsf_cnt）**未被内联乘法触碰**、
   所有分支目标均落在指令边界 ⇒ 循环控制本身正确。⇒ 退出测试**确实通过**。
5. **判定环在调用者**：`qemu -d exec,nochain` 的 PC 序列显示
   `benchmark_body`（epilogue `0x978`）→ **`0x4e0`（= `benchmark_body` 入口）** →
   `memcpy`。即 `benchmark_body` 返回到了**它自己的入口**，被反复重入。
6. **根因**：`warm_caches` 的 IR 是 `tail call fastcc void @benchmark_body(1, %heat)`，
   反汇编为
   ```
   warm_caches:
     ... save rbfp, set rbfp ...
     set.zw rd16, wp0, 0x1
     call [rb0, 4]        ; call benchmark_body
     <函数结束，无 ret>
   ```
   `call` 在 RegRAS（`ra63`）压入**返回地址 = `call` 的下一条指令 = benchmark_body 入口**；
   `benchmark_body` 的 `ret` 弹回该地址 ⇒ **无限自重入**（`-O2`）/ 直至参数被 clobber 后
   偶然退出（`-O1`，故 `-O1` 侥幸在 ~4.9s 终止）。
   ⇒ **根因 = DADAO 后端未处理尾调用**：`tail call` 被当作普通 `call` 发射，且调用者
   因 `IsTailCall` 为真**不再发射 `ret`**（`SelectionDAGBuilder` 在 `CLI.IsTailCall` 时
   跳过返回 lowering），二者叠加产生静默错码。DADAO 无尾调用指令（`contract-abi §2.3`：
   `call` 恒压栈），故属**后端能力边界**。

## 3. 差异证据

| 观测 | `-O0`/`-O1`（正常） | `-O2`（死循环） |
|---|---|---|
| `warm_caches` 反汇编 | 与 `-O2` **相同**（尾调用形态） | `call` + 无 `ret` |
| `benchmark_body` 循环控制 | 同 | 同（逐字节相同） |
| `benchmark_body` 返回目标 | 正常返回调用者 | 返回自身入口（`0x4e0`） |
| 去掉 IR `tail` 标记 | — | **exit=0**（`warm_caches` 变 `call`+`ret`） |

- 关键对照实验：`sed 's/tail call/call/g' mm_O2.ll; llc -O0` ⇒ `warm_caches` 出现
  `call` + `ld.o` + `ret` ⇒ **exit=0**。
- 反例最小程序（`/tmp/opencode/LLVM-070t/red/tc2.c`）：
  `void h(int x){ g(x); }`（`g` noinline）⇒ `h` 发射 `call g; <无 ret>` ⇒
  `main→h→g→main` 死循环。

## 4. 修复

`DADAOTargetLowering::LowerCall`（`DADAOISelLowering.cpp`）开头：
```cpp
if (CLI.IsTailCall) {
  if (CLI.CB && CLI.CB->isMustTailCall())
    report_fatal_error("DADAO: 'musttail' calls are not supported ...");
  CLI.IsTailCall = false;
}
```
- 依 `TargetLowering::CallLoweringInfo::IsTailCall` 文档（"should be modified by
  implementations of LowerCall"）清零 ⇒ 调用者发射普通 `call` + `ret`（**正确代码**，
  仅放弃尚不支持的尾调用优化）。
- `musttail` 不可合法降级 ⇒ `report_fatal_error`（**显式失败**，不静默错码）。

## 5. 验证（真实输出见 `.work/log/llvm/LLVM-070t-evidence.log`）

- 4 基准 `-O2`：`huffbench`/`matmult-int`/`nettle-sha256`/`statemate` **exit=0**。
- `-O0` 首验收集 10 例 **exit=0**（不下降）。
- `make check` / `make check-patch-tree` / `make check-lit`（78/77/1）/ `make build-mc` **EXIT=0**。
- 一键证据脚本 `.work/evidence/LLVM-070t/run.sh`：`fail=0 detected=1`，`EVIDENCE_EXIT=0`；
  注入（`if (CLI.IsTailCall)`→`if (false)`）⇒ `llc` 重建后尾调用复现、断言 FAIL
  （`inject-detected`）⇒ `cp`+md5 还原 ⇒ 重建 ⇒ 回绿。

---

## 附录 D：SPEC-129t 写死计数判定表

> **来源**：原 `.tao/archive/M7/notes/SPEC-129t-count-table.md`（40 行，全文；2026-11-01 并入）。

> **升格指针**（INFRA-058t，用户 2026-10-11 裁定「被引用材料不得只放 `.work/`」）：本文档由 `.work/log/spec/` 下同名文件升格至 `.tao/knowledge/`（原 `.work/` 副本已移出，该目录 gitignored、不再保留）。
# SPEC-129t 写死计数判定表（可机械核对者 → 去数字/指向真源；示例性说明 → 保留）

判据（任务书约束 line 66 + 用户裁定「消除写死」）：
- **改**：以数字陈述 **M1 格式类数 / M1 指令条数** 者（可从 `contracts/opcodes.yaml` 机械核对）；
- **保留**：示例性说明 / 展开长度 / ISA 固定定义 / 非 M1 硬件指令条数（伪指令冻结于 `ADR-0013 D11`）。

## Toolchain-01-汇编语言.md

| 行(约) | 旧值 | 判定 | 依据 |
|---|---|---|---|
| 引言「依赖」 | `228 条指令全表` | **改** → 去数字 + 指向 `contracts/opcodes.yaml` / 生成投影 | 全表条数，且旧值已陈旧（实 227） |
| §1 | `11 类 M1 格式` | **改** → 去数字 + 指向 `contracts/opcodes.yaml` | M1 格式类数 |
| §4.2 | `6 条指令`（双目的） | **改** → 去数字（保留助记符枚举） | 子族指令条数，可机械核对 |
| §4.2 | `8 条` 寄存器复制 / `20 条` 浮点格式转换 | **改** → 去数字（保留枚举） | 子族指令条数，可机械核对 |
| §11 | `9 个 M1 格式类与 152 条 M1 指令` | **移除**（内容移出至 `contract-asm.md §11`） | 旧口径（实 11/155） |
| §6.1 / §6.2 | `8 条合成型` / `10 条`（伪指令） | **保留** | 伪指令集，非 M1 硬件指令条数；冻结 `ADR-0013 D11` |
| §6.1 | `≤4 条` / `3 片` / `2 条 set.w` / `1 条` | **保留** | 展开长度（示例性） |
| §7 | `4 条数据指导符` | **保留** | ISA 固定定义（非 M1 指令条数） |
| §6 | `18 条口径`（上游历史） | **保留** | 上游历史说明（示例性） |
| §4.1/§4.2/§4 速查 | `恰好 2 个` | **保留** | 语法定义（双目的恰好 2 个），非指令条数 |

## contract-asm.md

| 行(约) | 旧值 | 判定 | 依据 |
|---|---|---|---|
| §指令全表 | `227 条指令表` | **改** → 去数字 + 指向生成投影/`opcodes.yaml` | 全表条数 |
| §1 | `11 类 M1 格式类` | **改** → 去数字 + 指向 `opcodes.yaml` | M1 格式类数 |
| §4.2 | `6 条指令` | **改** → 去数字（保留枚举） | 子族指令条数 |
| §4.2 | `8 条`/`20 条` | **改** → 去数字（保留枚举） | 子族指令条数 |
| §11 首行 | `11 类 M1 格式类与 155 条 M1 指令` | **改** → 去数字 + 指向 `opcodes.yaml` | M1 格式类数/指令条数（唯一 home 不写死计数） |
| §11 | `伪指令 8 条（合成型）` / `.dd.* 指导符 4 条` | **改** → 去数字 | 验收 4 要求 §11「不写死计数」 |
| §6 | `保留 8 条合成型` / `2 条 set.w` / `4 条 set.w` / `删除 10 条` | **保留** | 伪指令/展开长度，非 M1 条数 |
| §7 | `4 条数据指导符` | **保留** | ISA 固定定义 |
| §4 速查 | `恰好 2 个` | **保留** | 语法定义 |

## 未改（其它册/ADR）

- `spec/DADAO-22`：**仅**改 5 处示例 scratch 寄存器（`rb3`→`rb8`），无计数问题。
- `ADR-0013`：仅追加指向句；其 D11 的 `8 条/10 条`（伪指令）未动（本任务不授权改 ADR 正文）。

---

## 附录 E：INTEG-027t 报告（agent 配置与规则重构）

> **来源**：原 `.tao/archive/M7/notes/INTEG-027t-report.md`（217 行，全文；2026-11-01 并入）。

> **升格指针**（INFRA-058t，用户 2026-10-11 裁定「被引用材料不得只放 `.work/`」）：本文档由 `.work/log/integ/` 下同名文件升格至 `.tao/knowledge/`（原 `.work/` 副本已移出，该目录 gitignored、不再保留）。
# INTEG-027t 报告（agent 配置与规则重构）

> 本工作包**非 `.tao/tasks` 任务**（无任务文件），按用户 2026-10-10 逐条裁定执行；分支 `INTEG-027t`；不提交 git。
> 对账清单来源：`.work/log/integ/agent-config-audit.md`（A01–F02，共 30 条）。

## 完成区

**状态**：待验收
**测试结果**：`.work/evidence/INTEG-027t/run.sh` **9/9 全绿、EXIT=0**（含「悬空引用注入→FAIL→cp+md5 还原→回绿」自检）；`make check-no-residue` EXIT=0。
**修改文件**：
- 迁移/新增：`.opencode/opencode.jsonc`、`.opencode/agents/{architect,engineer,reviewer}.md`、`.opencode/commands/{plan,dispatch,complete,status}.md`
- 删除：`.opencode/agent/`、`.opencode/command/`（单数→复数）、`.opencode/instructions/`（5 文件）
- 修改：`AGENTS.md`（216→169 行）、`.tao/README.md`
- 证据/台账：`.work/evidence/INTEG-027t/run.sh`、`.work/log/integ/INTEG-027t-{report,slim-map}.md`
**验收结果**：悬空引用扫描 悬空=0（引用总数 34）；lessons §引用缺失=0；命名章节引用 10/10；过时 token 命中=0；`git status` 见下。
**新发现/坑**：
- 原 `instructions/` 的 3 条「探针」细则（回读校验／双向验证／注入非空）在 `lessons.md` **无对应条目**，AGENTS 压缩后须显式落 `.opencode/agents/engineer.md` 以免丢规则（本包已落）。
- `.opencode/**` 未被任何 `.gitignore`/exclude 忽略 ⇒ F02「入库」**无需改 `.gitignore`**。
**遗留问题**：工作树含 **pre-existing** `TESTCASES-041t` 未提交改动（`tests/llvm/codegen/*`、`tools/integ/run_codegen_e2e.py`），**非本包产生、未触碰**（禁 `git checkout/restore`）。

## 一、30 条对账（状态 + 落点）

| 编号 | 状态 | 落点 |
| --- | --- | --- |
| A01 | 改 | `.tao/README.md` L4/L94 → 项目 `.opencode/agents|commands/`，删「工作仓库不包含 agent 文件」 |
| A02 | 改 | `commands/{plan,dispatch,complete,status}.md` 「交互目录」引用 → `.tao/README.md` |
| A03 | 改 | `AGENTS.md` L3 删「交互目录定位」，改指 `.tao/README.md` |
| A04 | 改 | `AGENTS.md` 全局指针 → 项目 `.opencode/agents|commands/`（角色与流程/任务收尾/硬约束10·11） |
| A05 | 改 | `.opencode/agents/engineer.md`：`rule-engineer` → `engineer` |
| A06 | 改 | `.opencode/commands/complete.md` §5 → 分支→落地 master→push |
| A07 | 改 | `.tao/README.md` 删 `/translate` 行 |
| B01 | 改 | `complete.md` §5 删 `reset --soft`/`amend`，改 `merge --squash` → FF push |
| B02 | 改 | `complete.md` §3C + `.tao/README.md` L42：`feedback_*.md` → `lessons.md` |
| B03 | 改 | push 归主会话：`AGENTS.md`「推送范围」+「分支—提交—push」（原 `git-push.md` 通用项并入） |
| B04 | 改 | 提交须确认在 `AGENTS.md` L11；architect 授权提交注明（`AGENTS.md` L11 + `architect.md` 提交节） |
| B05 | 改 | `engineer.md` `~/NNNa-progress.md` → `/tmp/opencode/<任务ID>/progress.md` |
| C01 | 改 | 分支链单一真源 `AGENTS.md`；`D §5`/`C §5`/`AR` 提交节留指针 |
| C02 | 改 | `engineer.md`/`architect.md` 补 `cp`+md5 还原纪律（`reviewer.md` 原有） |
| C03 | 改 | `engineer.md`「证据脚本与还原纪律」+ `reviewer.md`「证据脚本审核与独立注入」+ `§8.34/§8.35` |
| C04 | 改 | `engineer.md`「探针/长命令」+ `AGENTS.md`「长任务」（setsid/`core.quotepath=false`） |
| C05 | 改 | `architect.md` 模板限长注 + `complete.md` + `AGENTS.md`「任务书限长」 |
| C06 | 改 | `.opencode/commands/dispatch.md` §2.5 四项预检 |
| C07 | 改 | `.opencode/commands/dispatch.md` §6 硬约束 1–11 内联 |
| C08 | 改 | `dispatch.md` §2.5 并发约束 + `AGENTS.md`「并行任务上限」「长任务」 |
| D01 | 改 | 状态机单一真源 `architect.md`；`README` 只留指针；流程/收尾单一真源 `AGENTS.md`+commands |
| D02 | 改 | `complete.md` §5 只留项目侧要点 + 指针；`README` 限长 → `AGENTS.md` |
| D03 | 改 | `dispatch.md` §5 统一「每次 engineer / reviewer 返回后 architect 提交」 |
| D04 | 改 | `dispatch.md` §5 + `complete.md` §5：分支内 commit；主会话 `/complete` 后落地+push |
| E01 | 改 | 目录迁移复数：`.opencode/agents/`、`.opencode/commands/`，全部引用同步 |
| E02 | 改 | 删除 `.opencode/instructions/`（bazel/Vivado/fpga/coralnpu/CTAO 等其它项目内容随之消失） |
| E03 | 改 | `architect.md` frontmatter `permission.bash."git push *": deny` |
| E04 | 改 | `dispatch.md` §5 用全路径 `.opencode/commands/complete.md` |
| F01 | 改 | `instructions/` 通用必需项并入 `AGENTS.md`「命令与任务执行纪律」；目录删除 |
| F02 | 改 | `.opencode/**` 入库（本未被忽略，无需改 `.gitignore`）；`AGENTS.md`「角色与流程」改表述 |

**合计**：改 **30**／不改 **0**（逐条落实）。

## 二、精简对账（规则不丢）

见 `.work/log/integ/INTEG-027t-slim-map.md`：`AGENTS.md` 56 条原条目 + 其它文件 14 条原条目**全部有落点**（含原先只在 AGENTS 出现的 3 条探针细则 → `engineer.md`）。

## 三、证据输出（真实）

### 3.1 一键证据脚本

命令：`bash .work/evidence/INTEG-027t/run.sh > /tmp/opencode/INTEG-027t/run.out 2>&1; echo EXIT=$?`

```
[PASS] C1 .opencode 结构                期望=8文件/无旧目录 实际=ok rc=0
[PASS] C2 opencode.jsonc                  期望=合法JSON+3 ignore 实际=ok rc=0
  引用总数=34 悬空=0
[PASS] C3 悬空文件引用扫描        期望=悬空=0 实际=见上 rc=0
  §引用共 13 个，缺失=0
[PASS] C4 lessons 章节引用            期望=缺失=0 实际=见上 rc=0
[PASS] C5 命名章节引用              期望=缺失=0 实际=10项ok rc=0
[PASS] C6 过时token/translate           期望=命中=0 实际=0 rc=0
[PASS] C7 architect deny git push         期望=命中 实际=命中 rc=0
[PASS] C8 无 _tmp/_orig/_rej             期望=残留=0 实际=0 rc=0
--- 注入自检（悬空引用） ---
  [悬空] .opencode/does-not-exist/nope.md
md5 before=f0c51f873cfd8a1d6f4504993ce20edc after=f0c51f873cfd8a1d6f4504993ce20edc restore_ok=1
[PASS] 注入自检(FAIL→还原→回绿) 期望=注入FAIL/还原/回绿 实际=OK rc=0
AGENTS.md 行数（现场统计）=169
总失败项=0
RESULT: ALL PASS
EXIT=0
```

### 3.2 门控

`make check-no-residue` → `check-no-residue: PASS`，EXIT=0（文档类改动，`make check` 按规则豁免）。

## 四、engineer 自审（第 1 轮，自主逐行）

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 L128 嵌套粗体 `**…（**单一真源**…）**` | ✅已修 | 去内层星号 | run.sh 全绿（含 C5） |
| F2 指针名「每任务一分支」已无对应标题 | ✅已修 | L11 改指「任务收尾·分支—提交—push」 | C5 命名引用 10/10 |
| F3 硬约束 3 指针后半指向不存在的具名子条目 | ✅已修 | 改为只指「验证脚本反例门控」 | grep 复核 |
| F4 `§` 置于反引号内（`.md §1` 等） | ✅已修 | `§` 移出反引号 | C3 引用总数 34/悬空 0 |
| F5 3 条探针细则在 `lessons.md` 无条目 ⇒ 压缩后规则丢失风险 | ✅已修 | 落 `engineer.md`「探针须真能失败」(QEMU-008t/010t/011t) | slim-map 第 22–24 行 |
| F6 C3 扫描初版假阳性（示例/历史/占位路径；`§` 在反引号内） | ✅已修 | 加 `EXCLUDE_RE` + `sed 's/ .*//'` | run.sh C3 悬空 0（修正前 11） |

**判决**：全部 finding 已修 → 状态置 **待验收**。

## 审阅记录 → 第 1 轮 reviewer 验收（2026-10-10，独立重跑）

**判决：Needs Revision** —— 阻断 1 项（F01 丢规则，见下）；其余 29 条与全部重跑通过。证据全文：`.work/log/integ/INTEG-027t-review-evidence.log`。

### 重跑记录（真实输出/退出码）
- `bash .work/evidence/INTEG-027t/run.sh` → **RUN_EXIT=0，9/9 PASS**（引用总数=34/悬空=0、§引用=13/缺失=0、AGENTS.md=169 行）——与完成区数字一致；脚本审：C1–C8 各有可达 FAIL 路径、注入非空、`cp`+md5 还原、无 `tee`、自捕获 rc ✅
- 独立悬空扫描（reviewer 自写 refscan.py，不限反引号）：76 条路径引用、**真悬空=0**（3 命中均假阳性：`spec/llvm/qemu/testcases` 目录树注释、`契约/spec/测试` 散文、`如 §20.10` 示例）；§引用=15/缺失=1（同为示例）
- `.opencode/opencode.jsonc`：`python3 json.load` **rc=0**；`$schema=https://opencode.ai/config.json`；`watcher.ignore=[.work/**,.cache/**,.dadao/**]` ✅；`find .opencode -type f`=8、`test -e .opencode/{agent,command,instructions}` rc=1（旧目录已删）✅
- `make check-no-residue` → `check-no-residue: PASS`，**EXIT=0**

### 独立注入→FAIL→还原→回绿（cp+md5，未用 git 还原）
- 注入：AGENTS.md 追加指向 `docs/Process-9X-不存在的规范.md`（与 engineer 的悬空目录指针不同）；`git diff --name-only AGENTS.md` 非空 → 重跑**同一脚本** **INJECT_RUN_EXIT=1**（`[FAIL] C3 … 悬空=1`、RESULT: FAIL）
- 还原：`cp /tmp/opencode/INTEG-027t-review/AGENTS.md.preinject AGENTS.md`；md5 前后均 `8cded70ec977a0a6b0ba7ac6334b7070` **相等** → 再重跑 **POST_RESTORE_EXIT=0**（RESULT: ALL PASS，回绿）

### 规则不丢抽查（12 条；原位置 → 新落点，均 grep 实证）
1. 中间验证①-④+数据类（独立全量重算/validator≠语义/错值当场修）→ `AGENTS.md` L86-88 + lessons §1｜2. 下发前预检①-④（QEMU-014t/005t、BLOCKED+替代验证）→ `dispatch.md` §2.5｜3. 一键证据脚本五项要求 → `engineer.md` L77｜4. reviewer 审脚本+重跑+独立注入 → `reviewer.md` L74-77｜5. 留证捕获自身退出码/禁 tee → `AGENTS.md` L99 + `engineer.md` L77⑤｜6. 可达 FAIL/禁恒真/两支同结果 → `engineer.md` L77 + `reviewer.md` L76｜7. 覆盖≠语义（独立 oracle）→ `AGENTS.md` L99｜8. 探针三细则（回读校验/双向验证/注入非空）→ `engineer.md` L79｜9. 子代理异常处理（重试≤1/拆分/代行须同意）→ `AGENTS.md` L105-106 + lessons §3｜10. 提交分档/每任务一分支 → `AGENTS.md` L120-124（B01 已删 reset/amend）｜11. 硬约束 10/11（merge--squash、还原纪律指针）→ `AGENTS.md` L168-169 + `architect.md` L210｜12. 收尾检查①-④+步骤细节/限长/状态机 → `AGENTS.md` L135/L137 + `complete.md` + `architect.md`「任务状态机」L125。
**结论：AGENTS.md（56 条）/README 压缩项全数有落点，12 抽查全中。**

### 约束核验
B01 grep `reset --soft|--amend|squash/amend` **rc=1 无命中** ✅；B02 `feedback_` 仅 2 处禁止语 ✅；E03 `permission.bash."git push *": deny` ✅；C03 §8.34/§8.35+计数不写死落 engineer/reviewer ✅；A01/A05/A07/B05/C06/C07/D03/D04/E01/E04 逐条实证 ✅。边界：本包=AGENTS.md/.tao/README.md/.opencode 8 文件；**披露**：工作树含 TESTCASES-041t 既存未提交改动（`tests/llvm/codegen/*` 4 件 + `tools/integ/run_codegen_e2e.py`），非本包、未触碰；`git diff origin/master...HEAD` 空（未提交，落地归 architect/主会话）；无 `_tmp/_orig/_rej`。

### 阻断问题（需返工）：F01 仅部分落实 —— 删 `instructions/` 后**通用细则丢规则**（全仓 + 全局 `~/t.a.o/opencode/AGENTS.md` + `spec/` grep 零命中、无落点）
- `git-commit.md`：提交信息中文/`<type>: <subject>`/type 取值/「一个提交只做一件事，禁止混合改动」/子模块先行提交
- `git-push.md`：推送前向用户列分支+commit 清单、`git remote -v` 归属检查、`git pull --rebase` 同步、推送后验证、子模块先行推送
- `remote-tasks.md`：快/慢速任务时间估计与协作、实测耗时基准、远程脚本纳入仓库、日志落 `<taskdir>/build.log`、网络/环境差异先确认；`discipline.md`：长命令超时保护
- 减轻情形：`<type>: <subject>` 与本仓库 `<任务ID>:` 约定（`architect.md` L207）冲突、子模块细则与本仓库无 submodule——删除本身合理，但**未逐条披露「有意删除+依据」**，`slim-map` 第 85 行以 1 行笼统覆盖 5 文件 = 静默丢规则。
- **修法（二选一或并用）**：① 仍适用细则补回落点（提交纪律→`architect.md`「提交与文件集审核」/`AGENTS.md`；push 前后检查→`AGENTS.md`「推送范围」/`complete.md` §5；remote-tasks→`AGENTS.md`「远端任务」；超时保护→「长任务」）；② 报告内列「有意删除清单+理由」交用户逐条裁定。改后复审重跑 `run.sh`。

### 非阻断观察
- engineer 贴的 run.sh 输出为删节版（缺「文件数=8」行、untracked 列表段与分隔行）；数字与本审查重跑一致，建议补全原文。
- F02「入库」：`.opencode/**` 8 文件现 `??` 未跟踪（`.gitignore` 未忽略，已核实）——须 architect 提交时显式 staging 落地。
- 落点说明：本工作包无 `.tao/tasks` 任务文件（engineer 已注明），本审阅记录按「只追加」写入本报告文件。
- 快照对账：审查前后 `git status --porcelain` 逐行比对——本包文件零变动（AGENTS.md md5=`8cded70e…` 与注入前相等，还原确认）；**新增差异 1 项非我所为**：` M .tao/tasks/testcases/TESTCASES-041t-返囘寄存器rd8向量收口.md`（审查期间由并行的 TESTCASES-041t 工作流改动，我全程只读未触碰）；我足迹仅 `.work/log/integ/INTEG-027t-{review-evidence.log,report.md}`（`.work` 为忽略目录）。

---

## 返工段（第 1 轮 reviewer Needs Revision → F01 丢规则处置；2026-10-10）

**返工范围**：仅修 F01（唯一阻断）；不改其它已通过项。改动文件：`AGENTS.md`、`.opencode/agents/architect.md`、`.work/log/integ/INTEG-027t-slim-map.md`、`.work/evidence/INTEG-027t/run.sh`（本报告）。`AGENTS.md` 169 → **172** 行（+3）。

### F01 四条细则逐条处置（补回 or 显式不适用 + 落点）

| # | 原细则（instructions/） | 处置 | 落点 |
| --- | --- | --- | --- |
| 1a | git-commit：`<type>: <subject>` 格式 | **不适用**（与本仓库 `<任务ID>:` 约定冲突） | `architect.md`「提交与文件集审核」`> 提交信息与粒度` 注 |
| 1b | git-commit：type 取值清单（feat/fix/…） | **不适用**（同上，随 1a 一并声明） | 同上 |
| 1c | git-commit：一个提交只做一件事 | **补回** | 同上（「一个提交只做一件事（一个任务/分支），禁混合无关改动」） |
| 1d | git-commit：子模块提交顺序 | **不适用**（本仓库无 submodule） | 同上（「本仓库无 submodule，子模块先行提交不适用」） |
| 2a | git-push：推送前列分支+commit 清单 | **补回** | `AGENTS.md`「推送范围」`push 检查` 行 |
| 2b | git-push：`git remote -v` 归属检查 | **补回** | 同上 |
| 2c | git-push：`git pull --rebase` 同步 | **补回** | 同上 |
| 2d | git-push：推送后验证 | **补回** | 同上 |
| 2e | git-push：子模块先行推送 | **不适用**（本仓库无 submodule） | 同上 |
| 3a | remote-tasks：快/慢速时间估计 + 实测耗时基准 | **补回** | `AGENTS.md`「命令与任务执行纪律」远端任务行 |
| 3b | remote-tasks：脚本纳入仓库 | **补回** | `AGENTS.md`「命令与任务执行纪律」远端环境行 |
| 3c | remote-tasks：日志 `build.log` | **补回** | 同上 |
| 3d | remote-tasks：先确认网络/环境 | **补回** | 同上 |
| 4 | discipline：长命令超时保护 | **补回** | `AGENTS.md`「长任务」超时保护行 |

**合计**：补回 **10** 条 / 显式不适用 **4** 条（1a/1b/1d/2e，均由 submodule 或 `<任务ID>:` 约定决定），**零静默丢弃**；`slim-map` 第 85 行「1 行覆盖 5 文件」已改为**逐文件逐条**（见 `INTEG-027t-slim-map.md` §二）。

### 返工验收证据（真实输出/退出码）

- **`bash .work/evidence/INTEG-027t/run.sh` → `RUN_EXIT=0`，**10/10 PASS**（新增 C9 通过）；`AGENTS.md 行数=172`；C3 悬空引用扫描 `悬空=0`（rc=0）。
- **C9 可达 FAIL 自证（cp+md5 还原，禁 git 还原）**：perl 把 `architect.md`「一个提交只做一件事」→「一个提交可以做多件事」⇒ 重跑 `INJECT_RUN_EXIT=1`（`[FAIL] C9 F01 四细则落点（丢规则） rc=1`，`RESULT: FAIL`）；`cp` 还原后 md5 `774eb08e…` 前后相等 ⇒ 重跑 `POST_RESTORE_EXIT=0`（`[PASS] C9 …`，`RESULT: ALL PASS`）。

### 约束核验

只动 `.opencode/**`、`AGENTS.md`、`.work/**`（报告/脚本/slim-map）；未触碰 `spec/`/`contracts/`/`components/`/`.tao/knowledge/**`/`tests/**`/`tools/**`；未切分支、未提交 git；未触碰 `TESTCASES-041t` 既存改动。

### 第 2 轮 engineer 自审（返工，自主逐行）

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| R1 slim-map 补回行尾 typo「（`patch` 复）」 | ✅已修 | 去杂串，改「补回」 | slim-map L87 复读 |
| R2 新增 C9 须有可达 FAIL 路径（防「只会报 PASS」） | ✅已修 | `run.sh` 增 C9（12 条 land 断言） | perl 注入→`INJECT_RUN_EXIT=1`（C9 FAIL）→`cp`+md5 还原（`774eb08e…` 相等）→`POST_RESTORE_EXIT=0` |
| R3 push 检查含 `git pull --rebase` 是否与「master 永不改写已推送历史」冲突 | ❌不修 | 无 | `git symbolic-ref refs/remotes/origin/HEAD`→`origin/master` 存在；`--rebase` 仅「同步确认无冲突」，不 force、不改写已推送历史 |
| R4 `AGENTS.md` 行数增幅须受控 | ✅已修 | 仅 +3 行（169→172） | `wc -l`=172（现场统计） |

**判决**：全部 finding 已处置（R3 判不修并附证据）→ 状态维持 **待验收**。

## 审阅记录 → 第 2 轮 reviewer 验收（2026-10-10，独立重跑；针对 F01 返工）

**判决：Accepted** —— F01 阻断已消除（补回 10 条 / 显式不适用 4 条逐条核验），验收命令块全部在我重跑下通过，约束无违反。证据：`/tmp/opencode/INTEG-027t-review2/`（rerun/inject/postrestore/refscan.out + md5 快照）。

### 重跑记录（真实输出/退出码）
- `bash .work/evidence/INTEG-027t/run.sh` → **RUN_EXIT=0，10/10 PASS**（C3 引用总数=34/悬空=0；C4 §引用=13/缺失=0；C9 F01 四细则落点 PASS；`AGENTS.md 行数=172`）；脚本审：C9 12 条 `land` 断言各有可达 FAIL 路径（grep -qF 单支、非恒真），注入非空、`cp`+md5 还原、自捕获 rc、无 `tee` ✅
- 独立悬空扫描（自写 refscan.py，与 engineer 实现不同）：76 条路径引用、**真悬空=0**（3 命中同第 1 轮假阳性：`spec/llvm/qemu/testcases` 树注释、`spec/测试来强制通过` 散文）；§引用=15/缺失=1（`§20.10` 示例），rc=1 仅由假阳性所致
- 原文对照：`git show '9f85f5b^:./instructions/{git-commit,git-push,remote-tasks,discipline}.md'`（`~/t.a.o/opencode` 仓库，只读管道）取回 4 原文（14/55/17/14 行）存 `/tmp/opencode/INTEG-027t-review2/orig-*.md`

### F01 四组逐条核验（原文 → 落点，grep 命中行）
1. **git-commit**：`architect.md` L210 命中「**一个提交只做一件事**（一个任务/分支），禁混合无关改动」＝补回 ✅；同命中「本仓库用 **`<任务ID>: <subject>`** …**不用**全局 `<type>: <subject>`（`feat`/`fix`/…）——该约定与本仓库任务号冲突，**不适用**」（1a/1b 理由=冲突）✅、「本仓库**无 submodule**，「子模块先行提交」**不适用**」（1d 理由=无 submodule）✅；原文「提交信息用中文」等价命中 L210「中文短语」✅
2. **git-push**：`AGENTS.md` L13 一行命中 4 条补回——「列待推分支 + commit 清单（`git log origin/master..HEAD --oneline`）」「核查 `git remote -v` 归属」「`git pull --rebase` 同步远端确认无冲突」「**push 后**验证（`git status` up-to-date 或 `git log origin/master..HEAD` 为空）」✅；2e「子模块『先子后主』提交/推送序 **不适用**」+理由「本仓库**无 submodule**」✅；原文「只推送 gxt」= L12「推送范围」、判定表/失败不重试= L12 + 全局「最小安全设计」，语义等价 ✅
3. **remote-tasks**：`AGENTS.md` L80 命中「快速任务（预计 ≤5min）本地等待取结果；**慢速任务（>10min）** `nohup` 后台启动 + 落 PID 文件、**不等待**、告知用户预计耗时（记录实测耗时供后续估计）；等待完成用远端阻塞命令（`while kill -0 $(cat pid); do sleep 15; done`），查询状态非阻塞」✅；L81 命中「执行脚本**纳入仓库**（防漂移，从仓库副本调用）、日志落 `<taskdir>/build.log`；涉及 license / 依赖 / 路径时**先确认网络与环境差异**再执行」✅ —— 3a/3b/3c/3d 全覆盖，与原文逐项等价
4. **discipline**：`AGENTS.md` L151 命中「**超时保护**：bazel/Vivado 类长命令须设充足 `timeout`，避免中途被杀掩盖真实问题」＝原文第 6 条等价 ✅（其余 5 条已在 L76-77/全局规则，第 1 轮已核）

### 零静默丢弃（slim-map 逐文件逐条）
`INTEG-027t-slim-map.md` §二已由「1 行覆盖 5 文件」改为**逐文件逐条**（discipline 2 行、git-commit 3 行、git-push 5 行、remote-tasks 4 行，各带「补回/不适用」标注）。抽查 8 条「原条目→新落点」全部 grep 实证：① 一个提交只做一件事→architect L210 ② `<type>:` 不适用→architect L210 ③ git remote -v→AGENTS L13 ④ git pull --rebase→L13 ⑤ 推送后验证→L13 ⑥ ≤5min/>10min 协作→L80 ⑦ build.log→L81 ⑧ 超时保护→L151。**零丢弃确认**。

### 独立注入→FAIL→还原→回绿（与 C9/C3 自检均不同：坏 `§` 指针）
- 注入：`perl -pi` 把 `AGENTS.md` L148 `（\`lessons\` §8.21）`→`（\`lessons\` §9.99）`（md5 `2a0c7c16…`→`d7ecacf2…`，grep `§9.99`=1）⇒ 重跑**同一脚本** **INJECT_RUN_EXIT=1**：`§9.99 在 lessons.md 无对应标题`、`[FAIL] C4 lessons 章节引用 rc=1`、`RESULT: FAIL`
- 还原：`cp /tmp/opencode/INTEG-027t-review2/AGENTS.md.preinject AGENTS.md`（**禁 git 还原**）⇒ md5 回 `2a0c7c168c74860c21d81d090b9f35e8`（与注入前**相等**）⇒ 重跑 **POST_RESTORE_EXIT=0**：`§引用共 13 个，缺失=0`、`RESULT: ALL PASS`（回绿）

### 未引入新问题 + 约束核验
- `wc -l AGENTS.md`=**172**（现场统计，与声明一致）；`git status --porcelain -uall` 前后快照 **diff rc=0 零变动**，10 文件 md5 全 OK；内容=本包（`.opencode/**` 8 + `AGENTS.md` + `.tao/README.md`）+ **TESTCASES-041t 既存改动 6 件（task书/tests/llvm/codegen×4/tools/integ/run_codegen_e2e.py）——披露：非本包、全程未触碰、不因之判问题** ✅
- `git status` 与 `spec/|contracts/|components/` 交集**空**（grep rc=1）；包内无 `_tmp/_orig/_orig/_rej` 残留（rc=1 无命中；`.work/source/llvm-project` 内 origin 类文件为上游源码、非残留）；`make check-no-residue` 第 1 轮已验、本轮 C8 覆盖 `.opencode`；未切分支、未提交 git、只审未改产物（我足迹仅 `.tao/knowledge/INTEG-027t-report.md` + `/tmp/opencode/INTEG-027t-review2/`）

### 非阻断观察
- run.sh 输出本轮已含「文件数=8」与 untracked 列表（第 1 轮删节问题已消）。
- refscan 3 命中/§20.10 仍为已判定假阳性（同第 1 轮），建议后续把树注释改写成非路径形式以消噪（不阻断）。
- F02 落地提醒：`.opencode/**` 8 文件仍 `??` 未跟踪，须 architect 提交时显式 staging 落地。
