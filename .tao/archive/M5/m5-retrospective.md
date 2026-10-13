# M5 里程碑回顾（Retrospective）

> **定位**：面向 **M6 规划 / 新人上手 / 审计追溯**。本文件**聚合索引**既有材料，**不复制**其明细：
> 状态摘要见 `.tao/knowledge/MEMORY.md`；路线图见 `milestones.md`；变更流水见 `changelog.md`；
> 遗留台账见 `.tao/knowledge/issues.yaml`（issue/待决）与 `.tao/knowledge/lessons.md`（教训/方法论/过程记录）；
> **经验规则以 `AGENTS.md` 为唯一准绳**。
>
> **日期**：2026-10-08 ｜ **范围**：M5（SEE/HEE 运行环境 + semihosting）
> **归档**：2026-10-08 起本文件随 M5 任务书/台账落入 `.tao/archive/M5/`（历史快照，不再更新）；M5 原始任务书/台账明细见同目录 `README.md`、`issues-closed.md`。

---

## 1. M5 事实快照

### 1.1 定义与门槛

`milestones.md`：**M5 — SEE/HEE 运行环境 + semihosting**（用户裁定 2026-10-07；`k` = `INTEG-019k`，**M5 起里程碑由 INTEG 模块开闭**，`Process-04 §1` 用户 2026-10-06 裁定）。

目的：把 QEMU 从 M1–M4 的「裸机、无 OS、无 syscall、`exit port` 停机」升级为「**SEE/HEE 运行环境 + semihosting**」：实现四运行模式与 cfx（核芯功能扩展）寄存器的**权限/掩码/`switch_run_mode`/权限异常**；以**新 bootrom（自有工具链编）**完成初始权限/向量配置；让 guest 经 `trap`（semihosting tag = `immu18[17:16]==2'b11`）走 QEMU **共享层 `do_common_semihosting`** 服务（**ARM 号值**），并以 **`SYS_EXIT` 替代 `exit port`**；LLVM 实现 `trap`/`escape`/`cfx2rc`/`cfx2rd`（`SimRISC-11`）——**`SimRISC-12`（`cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*`）保持 deferred**。

**门槛**：`make test-semihost`（**非** `test-see`）**五组成全绿**：① 正向（**bootrom（`-bios`）+ bin 应用**经 `-semihosting`、console 捕获、`SYS_EXIT` 码）② **cfx 级权限反例**（`ILLI`〔mask 禁止 / reserved〕、`CFXREG`〔未实现 cfx / 不存在或超数量寄存器组合〕；`NUPERM/NJPERM/NSPERM/NHPERM` 出自 `DADAO-12 §2.2` PTBR 层、**不在 M5**，`ADR-0020 D9`）③ 服务表各条至少 1 例（25）④ 不回归（`test-elf` 5/5、`test-codegen` 15/15、`check`、`check-lit`）⑤ `INTEG` 开闭。

**范围简化（用户 2026-10-08 裁定，`INTEG-019k` §第 8 轮）**：**M5 只做「bootrom（`-bios`）+ bin」**；「**elf 加载**」随 **M6**（与完整 LLVM 任务一并）。连带：「`-bios`+ELF 组合语义 / ELF loader 扩展（`dadao_load_regions[]`+RAM@0）/ 组合加载 ADR」移 M6（`ISS-168`）；`RAM@0` C1 **step2**（旧向量迁移）随 M6（`ISS-165`）。

**明确不含**：FP/RF codegen、clang 前端、libc/OS、golden model、完整调用约定。

### 1.2 达成情况（达成状态）

**2026-10-08 达成**。6 个模块里程碑全部置 `里程碑`，`milestones.md` M5 = **✅ 达成**。

| 模块 | 里程碑 | 备注 |
|---|---|---|
| infra | `INFRA-049m` | `INFRA-047t`（install 落地）、`INFRA-048t`（生成物落点迁移） |
| spec | `SPEC-118m` | `SPEC-113t`/`114t`/`115t`/`116t`/`117t`/`119t`/`120t`/`121t` |
| llvm | `LLVM-061m` | `LLVM-060t`（`trap`/`escape`/`cfx2rc`/`cfx2rd` MC+编码） |
| qemu | `QEMU-048m` | `QEMU-044t`/`045t`/`046t`/`047t`/`049t` |
| testcases | `TESTCASES-035m` | `TESTCASES-033t`/`034t` |
| integ | `INTEG-021m` | `INTEG-019k`（M5 开启）、`INTEG-020t`（**门槛收口**） |

19 个 M5 `t` 任务 + `INTEG-019k` 全 `已验证`。

### 1.3 最终门槛实测（2026-10-08，真实输出；完整输出见 `.work/log/integ/INTEG-020t-*.log`）

| 门槛 | 命令 / 证据 | 结果 |
|---|---|---|
| `make test-semihost` | `make test-semihost`（实测 **59s**） | **EXIT=0**；五组成全绿 |
| 正向（bootrom+bin） | `tools/integ/run_m5_e2e.py` | **10/10**（5 semihosting + 4 cfx 级权限反例 + 1 一般 trap）；console 逐字节（`m5_semi_writec`=`41`、`m5_semi_write0`=`4f 4b 0a`） |
| cfx 级权限反例 | 同上 | **4/4**（`ILLI`：reserved / mask；`CFXREG`：unimpl / badcombo） |
| 服务表 25 | `tools/qemu/min_rom_probe_046t.py` 全量 | `service coverage: all 25 service ids exercised`；`distinct 25 / required 25` |
| 不回归 | `make` 前置链 | `test-elf` 5/5、`test-codegen` 15/15、`check`（含 `check-lit` 62/62）、`check-no-residue` 全 EXIT=0 |
| `make check` | `make check` | **EXIT=0**；`repository checks: PASS` |
| 补丁集一致 | `make check-patch-tree` | **EXIT=0**；`2 component(s), 92 patches OK`（llvm 58 + qemu 34） |
| 接口对齐 | `python3 tools/integ/check_interface_alignment.py` | **EXIT=0**；85 项 PASS（含 RAM@0 断言） |
| 台账干净 | `python3 tools/infra/check_issues.py` | **EXIT=0**；归档前 `39 open / 3 closed` → 归档梳理后 `39 open / 5 closed` → 归档后 `39 open / 0 closed` |

### 1.4 版本 / 组件基线

规范 **SimRISC 0.5.4**（`README.md` 版本表为唯一来源）；`Toolchain 1.1`。
组件锁 `manifests/components.lock.toml`（M5 未变）：`llvm-project` commit `6dfe1677ab8dffbc6ec13d53a1e0215d75147689`（llvmorg-23.1.1）；`qemu` commit `c3d48b7d1e89604920e5b81b91140c2ad39a1943`（v11.1.1）；`gem5` `enabled=false`。

---

## 2. 交付物 / 资产地图

| 类别 | 数量 | 位置 |
|---|---|---|
| M5 任务文件 | **27**（26 M5 终态 + `INTEG-022t` 自归档） | `.tao/archive/M5/<module>/`（2026-10-08 归档，原 `.tao/tasks/<module>/`） |
| ADR | **20**（M5 新增 1：`0020`；就地修订 1：`0004`（`R1`/`R2`/`R3`）；判**沿用** 1：`0016 S1`） | `.tao/adr/` |
| 合约叙述 | 新增 2（`contract-see.md`/`contract-semihosting.md`） | `.tao/knowledge/` |
| 规范正文 | 新增 1（`spec/Machine-01-测试机运行环境.md`，①–⑦）；改 v5 自定册 `Process-05 §6`/`Process-06 §5/§6`；经授权改上游只读册 `SimRISC-11`（LEGALITY 段）/`Toolchain-01`（`§1`/`§2.1`）+ 相应 `sha256` 锁同步 | `spec/` |
| spec 只读锁 | `manifests/spec-readonly.lock.toml`（上游 20 册 → 含 v5 自定册 `Machine-01` = **21**） | `manifests/` |
| LLVM 补丁 | **58**（M5 新增 1：`LLVM-060t` 的 cfx 指令链） | `components/llvm-project/patches/` |
| QEMU 补丁 | **34**（M5 新增 2：`QEMU-046t` 的 `common-semi-target.c` + `qemu-options.hx`） | `components/qemu/patches/` |
| 工具脚本 | 新增 `tools/integ/run_m5_e2e.py`、`tools/testcases/validate_m5_vectors.py`、`tools/qemu/min_rom_probe_{044t,045t,046t,047t,049t}.py`、`tools/llvm/gen_cfx_alias_table.py`、`tools/infra/check_spec_readonly.py` 等 | `tools/<module>/` |
| 测试向量 | L3 执行向量 `tests/llvm/codegen/m5/`（**10** 条 bin）；L1 MC 向量复用 `LLVM-060t` 的 `cfx2-trap-escape.s` | `tests/llvm/` |
| bootrom | `tests/scripts/bootrom.S` + `bootrom.lds` + `bootrom_app.S` + `Makefile::build-bootrom` | `tests/scripts/` |
| 独立 oracle | `tools/testcases/validate_m5_vectors.py`（**141 checks**；服务表机械解析 25） | `tools/testcases/` |
| 门控 | `Makefile::test-semihost`（五组成；不回归作 make 前置） | `Makefile` |
| 最小 ROM 探针 | M5 新增 5（`044t`/`045t`/`046t`/`047t`/`049t`） | `tools/qemu/` |
| 教训库 | `.tao/knowledge/lessons.md`（M5 新增 `§7.14–§7.24` / `§8.6–§8.18`） | `.tao/knowledge/` |

### 2.1 M5 新增 / 就地修订 / 沿用 ADR

| ADR / 决策 | 主题 | 状态 |
|---|---|---|
| `ADR-0020`（**新建**） | SEE/HEE 与 semihosting：`D1` 入口判定（`immu18[17:16]==2'b11`）/ `D2` 传参寄存器（号→`rd16`、块指针→`rb16`、返回→`rd31`）/ `D3` 服务集（完整 25）/ `D4` 返回机制 / `D5` 复用范式（共享层 `arm-compat-semi.c`）/ `D6` 位宽端序 / `D7` host 安全（`target=native` 须显式）/ `D8` `SYS_EXIT` 停机 / `D9` 权限粒度（只做 `cfx0/1/2/3/63`）/ `D10` 两条路（`trap` vs `escape`）/ `D11` `cfxha` 白名单 / `D12` bootrom / `D13` 承载位置 / `D14` 共享层适配 / `D15` 核内地址空间划分 + 越界访问与**取指**异常 | Accepted（用户 2026-10-07 逐条确认） |
| `ADR-0004`（就地修订，rev. 2026-10-07） | `R1` `-bios` bootrom 与 M4 ELF 路径**并存（非替代）**；`R2` **`SYS_EXIT` 取代 exit-port**（`D3` 由 `ADR-0020 D8` 取代）；`R3` **RAM 基址改全 0** + C1 双映射两步；受保护决策 `D1`/`D2.1`/`D3`/`D4`/`D5`/`D6` 正文**未改** | 就地修订（用户逐条确认，`SPEC-113t`） |
| `ADR-0016`（`S1` 判**沿用**） | install 布局 `D1–D11`（`.dadao/cross-toolchain` / target sysroot / `manifests/` 单一真源 / 门控改从 install 根取可执行 / `.work/` 仅作 build 区） | 沿用（`INFRA-047t` 落地） |
| `ADR-0011 D3`（被取代） | 原「可靠 halt（exit-port）」——`SYS_EXIT` 迁移后由 `ADR-0020 D8` 取代（`ADR-0004 R2`） | 由 `ADR-0020` 取代 |

### 2.2 补丁规模

| LLVM（58） | QEMU（34） |
|---|---|
| 树形补丁集（`Process-01`，一文件一补丁）；M5 新增：`DADAOInstrFormats.td`（`DADAOCrrr`/`DADAOCiii`）、`DADAO.h`（`FK_crrr`/`FK_ciii`）、`DADAOInstrInfo.td`（4 条 cfx def）、`DADAOAsmParser.cpp`、`DADAOMCInstPrinter.cpp`、`DADAOCfxAlias.inc`（生成器随产物入库） | 树形补丁集；M5 新增 `target/dadao/common-semi-target.c`（v5 钩子）+ `qemu-options.hx`（`QEMU_ARCH_DADAO` arch mask）；既有补丁改 `cpu.c`/`cpu.h`/`helper.c`/`trans_ctrl.c.inc`/`hw/dadao/dadao-machine.c`/`Kconfig`/`meson.build` |

---

## 3. 过程度量（画像）

> 统计方法：遍历 `.tao/archive/M5/**/*.md`，取「`#### 第 N 轮 reviewer 验收`」小节与「`**Accepted**`/`**Needs Revision**`」判决。

### 3.1 任务与状态

- 任务总数 **27**（`已验证` 20 + `里程碑` 6 + 自归档 `INTEG-022t`）；6 模块全部收敛，**无 `待开始`/`待返工`/`待验收` 残留**（含自归档任务，用户裁定 2026-10-05/`Process-04 §4.1`）。
- `INTEG-019k`（M5 开启）按 `Process-04 §1`「**M5 起由 INTEG 模块开闭**」归 M5（非 `SPEC-*k`；M1–M4 的 SPEC 开启做法为历史）。
- `SPEC-120t` 为 M5 期**新增任务**（用户裁定 3「`encode_cfx` 不应存在，属实现层面，单独建立任务」），`**项目里程碑**` 字段含「（architect 判断，列为待用户复核项：可移 M6/后续）」括注——本归档按任务书预期清单归 **M5**（字段值以 `M5` 起首），**该「待用户复核」括注随本归档一并留待用户裁定**（见 §7）。

### 3.2 审阅轮次与打回

| 指标 | 数值 |
|---|---|
| 有 ≥1 次 `Needs Revision` 的任务 | **5**（`SPEC-115t`、`SPEC-119t`、`SPEC-120t`、`QEMU-045t`、`QEMU-049t`） |
| 有 **2 轮** reviewer 验收的任务 | **6**（`INFRA-047t`、`INTEG-019k`、`SPEC-113t`、`SPEC-114t`、`SPEC-115t`、`SPEC-120t`） |
| 多数任务 | 1 轮 reviewer 验收即 Accepted |

**打回/返工（代表）**：

| 任务 | 问题 |
|---|---|
| `SPEC-115t` | round1 证据脚本 2 处裸 `git diff` 假 FAIL（提交后工作树空）→ round2 改用 `BASE_COMMIT..HEAD` 范围后 Accepted（教训 `lessons §7.9`/`§8.7`） |
| `SPEC-120t` | 同上：C10 由**工作树** `git status` 计算改动集 ⇒ 提交后必然为空 ⇒ 假 FAIL；**round1 `Accepted` 由主会话依 `lessons §8.7` 推翻改判 `Needs Revision`**（**首次推翻**），round2 修一类后 Accepted（教训 `§7.15`/`§8.7 rule 5`） |
| `SPEC-114t` | round1 无授权**擅改上游只读册** `DADAO-12`/`DADAO-22` ⇒ 用户裁定后 `cp`+md5 还原、正文改落 v5 自定册 `Machine-01`；触发 **`SPEC-119t`（spec 目录保护机制）**（教训 `§7.5`/`§8.5`） |
| `SPEC-119t` | 补强 `if errors` fail-closed + 6 类反例（含「锁残缺」类）后 Accepted（规范 `§5.6`） |
| `INFRA-047t` | `ADR-0016 D9` 点名清单被改述收窄、`run_qemu_test.py` 漏改 ⇒ architect 范围修正重开一轮（教训 `§7.10`/`§8.1`） |
| `QEMU-045t`/`QEMU-049t` | reviewer 独立注入有鉴别力（特异命中路径），`cp`+md5 还原含**重建**（教训 `§7.18`、`§7.16`） |

### 3.3 子代理 / 方法论事件统计

| 事件类型 | 处置 | 教训 / 规范 |
|---|---|---|
| 无授权擅改上游只读册 `spec/DADAO-12`/`DADAO-22`（`SPEC-114t`） | 用户裁定 + `cp`+md5 还原 + 机制化（`SPEC-119t`：哈希锁 + 门控 + `Process-06`） | `§7.5`/`§8.5` |
| 证据脚本依赖未提交工作树 ⇒ 提交后假 FAIL（`SPEC-115t`/`SPEC-120t`） | 改 `BASE_COMMIT..HEAD`；主会话推翻 round1 `Accepted` | `§7.9`/`§7.15`/`§8.7` |
| 下发前预检第 2 项窄化（`SPEC-115t` BLOCKED：`scope: excluded→m1` 撞 3 跨模块门控） | 重排（`LLVM-060t` 前置）+ 文件集扩至门控载体 | `§7.6` |
| 还原方式偏差：`git show HEAD:<path> > <path>`（`QEMU-047t`） | 记录偏差；禁用清单扩充 | `§7.20`/`§8.14` |
| 复用上游共享层「只写钩子」式范围低估（`QEMU-046t`：`translate_for_debug`/arch mask/Kconfig/meson 四处接入点） | 越界披露 + reviewer 判「最小必要接线」+ 提升为规范 | `§7.19`/`§8.13` |
| 门槛正向「路径 / 组合未定义」前置风险（`QEMU-047t` `-bios`+ELF） | 用户裁定「M5 只做 bootrom+bin」；缺口随 M6 | `§7.21`/`§8.15` |

### 3.4 新增机制（M5 固化的机制）

**M5 期间固化的机制**：「spec 目录保护」（`SPEC-119t`：`manifests/spec-readonly.lock.toml` + `check_spec_readonly.py` + `make check-spec-readonly` + `Process-06`）、「生成物默认落 `.dadao/tests/`」（`INFRA-048t`/`SPEC-117t`）、「复用上游共享层的接入点清单」（`§8.13`）、「证据脚本断言带 `BASE..HEAD`」（`§8.7`）、「规范委派/占位 ⇒ 实现口径落门控 + 缺口落台账并提请授权」（`§8.10`）、「伪代码为权威」（`§8.12`）。

---

## 4. 时间线 / 关键路径

### 4.1 分层

```
2026-10-07  M5 开启（INTEG-019k，Process-04 §1「M5 起由 INTEG 开闭」）+ ADR-0020/ADR-0004 R1–R3 裁定落地（SPEC-113t）
2026-10-07  W0 基础设施：INFRA-047t（install）→ INFRA-048t（落点迁移）、SPEC-117t（Process-05 §6）
2026-10-07  W1 规范/决策：SPEC-114t（Machine-01 正文）→ SPEC-119t（spec 保护）→ LLVM-060t（cfx 指令链）→ SPEC-115t（re-scope）
2026-10-08  W1 续：SPEC-116t（Toolchain-01 修订）→ SPEC-120t（encode_cfx 删除）→ SPEC-121t（Machine-01 §1 落地 + 入锁）
2026-10-08  W3 QEMU：QEMU-044t（运行模式/cfx/权限）→ 049t（RAM@0 双映射）→ 045t（trap/escape 深化）→ 046t（semihosting）→ 047t（bootrom）
2026-10-08  W4 向量：TESTCASES-033t（m5 向量 + run_m5_e2e）→ TESTCASES-034t（exit-port→SYS_EXIT 全量迁移）
2026-10-08  W5 收口：INTEG-020t（semihosting E2E + harness stdio + make test-semihost 门槛达成）
2026-10-08  M5 模块里程碑核验（6 个 m）+ M5 达成（INTEG-021m）→ 归档前置台账梳理 + 归档（INTEG-022t）
```

### 4.2 重大事件时间线

| 事件 | 说明 |
|---|---|
| **M5 开启（2026-10-07）** | INTEG 闭环（`INTEG-019k`）；ADR-0020 新建 + ADR-0004 `R1`/`R2`/`R3` 修订（`SPEC-113t`） |
| **install 落地（`INFRA-047t`）** | `.dadao/cross-toolchain` + target sysroot；门控/执行器改从 install 根取可执行（`ADR-0016 D1–D11`） |
| **生成物落点迁移（`INFRA-048t`/`SPEC-117t`）** | `test-codegen`/`test-elf`/lit 运行产物 → `.dadao/tests/`；`Process-05 §6` 补正 |
| **SEE/semihosting 规范正文（`SPEC-114t`）** | 新建 `spec/Machine-01`；上游只读册零改动 |
| **spec 目录保护（`SPEC-119t`）** | 哈希锁 + 门控 + `Process-06`（事故驱动，`SPEC-114t` round1 擅改） |
| **cfx 指令链（`LLVM-060t`→`SPEC-115t`）** | `trap`/`escape`/`cfx2rc`/`cfx2rd` MC+编码 → re-scope `excluded`→`m1` |
| **QEMU SEE 执行层（`QEMU-044t`/`045t`/`046t`）** | 运行模式/cfx/权限/异常进入；semihosting 译码层短路 + 共享层复用 + 25 服务 + `SYS_EXIT` |
| **RAM@0 双映射（`QEMU-049t`）** | C1 step1；越界路由 `umon⇒0x81`/其余⇒`0x87`；step2 随 M6 |
| **新 bootrom（`QEMU-047t`）** | `-bios` path B raw-bin；复位 PC 不变；hypv→user 直跳 |
| **exit-port→`SYS_EXIT` 全量迁移（`TESTCASES-034t`）** | 门控逐项相等；`ISS-147` 结案、`ISS-169` 登记 6 探针例外 |
| **M5 门槛达成（`INTEG-020t`）** | `make test-semihost` EXIT=0（五组成全绿，59s） |
| **M5 达成（2026-10-08）** | 6 模块里程碑，`milestones.md` M5 = ✅ 达成 |
| **归档（`INTEG-022t`）** | `Process-04 §3` 台账梳理 + §4 归档判据 + 自归档 |

### 4.3 M5 建议执行顺序（`INTEG-019k`）

Wave 0（install/落点）→ Wave 1（规范/决策/指令链，`LLVM-060t` 先于 `SPEC-115t`）→ Wave 3（QEMU：`049t` 先于 `047t`）→ Wave 4（向量）→ Wave 5（`INTEG-020t` 收口）。依赖/串行链见各任务书 `**依赖**` 字段。

---

## 5. 关键决策（决策的「为什么」）

| 决策点 | 采用 | 否决 | 理由 |
|---|---|---|---|
| semihosting 入口判定（`ADR-0020 D1`） | `trap cfxHA, immu18` 中 `immu18[17:16]==2'b11`（**与 `cfxha` 无关**） | 按 `cfxha` 选路 | 与共享层 tag 约定自洽；避免 `cfxha` 偶然取值干扰 |
| 传参寄存器（`ADR-0020 D2`） | 号→`rd16`、块指针→`rb16`、返回→`rd31` | 复用旧 exit-port「寄存器习惯」 | `rb16` 为块指针（地址）、`rd31` 为返回值；`TESTCASES-034t` 初版误用 `rb3` ⇒ 全 FAIL |
| 服务集（`ADR-0020 D3`） | **完整 25**（含 `SYSTEM`/`HEAPINFO`/D2 文件档） | 只做子集 | 与共享层 `arm-compat-semi.c` 表一致、覆盖完备 |
| 共享层复用（`ADR-0020 D5`） | **零改动复用** `semihosting/arm-compat-semi.c` + v5 钩子文件 | 自行重写服务逻辑 | 复用上游成熟实现；但须落地**接入点清单**（`§8.13`） |
| 停机协议（`ADR-0004 R2`/`ADR-0020 D8`） | **`SYS_EXIT` 取代 exit-port**（退出码忠实传 host `$?`） | 保留 exit-port | 统一 semihosting 路径；exit-port 过渡保留至迁移完成 |
| 权限粒度（`ADR-0020 D9`） | 只做 **cfx 级** `ILLI`/`CFXREG`；`NUPERM/NJPERM/NSPERM/NHPERM`（PTBR 层）不在 M5 | 一并做 PTBR 权限层 | M5 只实现 `cfx0/1/2/3/63`；PTBR 权限层另属后续 |
| RAM 基址（`ADR-0004 R3`） | **改全 0**（`0x0000_0000_0000`）+ C1 **双映射两步**（step1 保留旧 RAM 段） | 一次性切换 | step1 保既有测试不回归；step2 随 M6 |
| 越界路由（`ADR-0020 D15`） | `umon` 段越界 ⇒ `CFXMEM`（`0x81`）；其余含 `power` 63 ⇒ 测试机约定 `unmapped`（`0x87`） | 一律 `CFXMEM` | 与已冻结码表兼容量；`0x87–0x8D` 未重排 |
| 加载模型（`ADR-0004 D2.3` path B） | bootrom `-bios` + 应用 **raw-bin** `-kernel`；**组合（`-bios`+ELF）未定义** | 实现 `-bios`+ELF 组合 | 用户 2026-10-08 裁定「bootrom+bin 与 ELF 是两件事」；组合随 M6 |
| 生成物落点（`ADR-0016 D6`/`Process-05 §6`） | 默认 **`.dadao/tests/`**（能配置解决 ⇒ 必进 `.dadao/`） | 落源码/构建树 | 隔离运行产物、可重建 |
| spec 保护（`SPEC-119t`） | **只读哈希锁 + 门控 + `Process-06`**（`if errors` fail-closed） | 仅靠流程约定 | `spec/` 改动零告警 ⇒ 事故；机械门控兜底 |
| `encode_cfx` 归属（`SPEC-120t`） | **删除**（候选 A）——实现层语义误登记为编码合法性 | 降级保留 | 全仓 0 引用、无渲染变化；用户裁定「不应存在」 |

---

## 6. 死胡同 / 已关闭（避免重试）

| 项 | 处置 | 理由 |
|---|---|---|
| 无授权改上游只读册 | 禁止；改落 v5 自定册 + 走授权（`§8.5`/`Process-06`） | 用户裁定「所有针对 spec 目录的修改都须经我允许」 |
| 证据脚本用裸 `git diff` 断言「已提交变更」 | 改 `BASE_COMMIT..HEAD`（`§8.7`） | 提交后工作树空 ⇒ 假 FAIL |
| 注入还原用 `git checkout`/`restore`/`stash`/`show <commit>:<path>` | 禁；一律 `cp`+md5（`§8.14`） | 会静默丢弃未提交改动 |
| 门控注入判据硬编码 `== 1` | 改 `-ne 0`（`§8.18`） | GNU make 失败码 = 2 |
| 复用共享层「只写钩子」 | 列全接入点清单（`§8.13`） | 缺 `translate_for_debug` ⇒ SIGSEGV、缺 arch mask ⇒ CLI 拒绝 |
| `SYS_EXIT` 沿用 exit-port「寄存器习惯」 | 块指针 `rb16`、退出码在内存块（`§8.17`） | 协议不同 |
| `encode_cfx` 编码合法性规则 | 删除（`SPEC-120t`） | 属实现层语义、0 引用 |
| `-bios`+ELF 组合 | M5 不做（随 M6） | 未定义、用户裁定分开处理 |

---

## 7. 遗留登记 / 风险与假设台账（M6 会失效的前提）

| # | 假设 / 项 | 现状 | M6 影响 / 处置 |
|---|---|---|---|
| 1 | **无 MMU（VA = PA）** | 成立 | 引入地址空间需重评 |
| 2 | **RAM@0 双映射为过渡态**（旧 RAM 段保留） | C1 step1 成立 | **step2 迁移随 M6**（`ISS-165`）：旧向量/harness/crt0/e2e 迁 `0` + 删旧段 + 收紧断言 |
| 3 | **`-bios`+ELF 组合未定义/未实现**；ELF loader 未含 RAM@0 | 成立 | 随 M6（`ISS-168`）+ 组合加载 **须立 ADR 并逐条确认** |
| 4 | **完整调用约定未冻结**（`contract-abi.md §6` 5 项 `[OPEN]`） | M5 未扩展 | 归属 M6（`ISS-005`/`ISS-006`） |
| 5 | **6 个 M1/M2 期 QEMU 探针仍以 exit-port 为退出通道** | 成立（`ISS-169`） | 随 M6 重写为 `SYS_EXIT`（含重算分支偏移） |
| 6 | **cfx mask 屏蔽路径不可观测**（monitor cause 全不可屏蔽） | 跟踪（`ISS-164`） | 待后续实现带可屏蔽 cause 的 cfx 后补验 |
| 7 | **`Toolchain-01 §5/§11/§13` 旧口径未收口**（须授权） | 成立（`ISS-163`，用户「暂登记遗留」） | 另请授权后另立任务 + 锁同步 |
| 8 | **`DADAO-12 §5` prose/伪代码张力**（跨 cfx escape） | 跟踪（`ISS-167`，伪代码为权威） | 建议另立 spec 任务（须授权） |
| 9 | **golden model / FP 独立 oracle 未建** | M5 未含 | 归属里程碑**待裁定**（`ISS-019`/`ISS-026`/`ISS-081`） |
| 10 | **`process-06 §1`「上游只读册」括注因扩面字面略不精确** | 授权范围外未改 | 建议另授权一行措辞修正 |

### 7.1 归档前置 `Process-04 §3` 台账梳理——逐条判定表（M5-scope 13 条）

> `INTEG-022t`（2026-10-08）按 `Process-04 §3` 步骤 1–6 处置 `scope` 含 `M5` 的 **13 条**（12 open + 1 closed）；下表为**集中判定**（与 `.tao/knowledge/issues.yaml` 各条 `notes` 及任务书 `.tao/archive/M5/integ/INTEG-022t-M5归档与回顾.md` 审阅记录互证）。

| id | 动作 | 依据（`scope` 变更 / 备注） |
|---|---|---|
| `ISS-003` | **边界拆分**：交付部分 → 新增 `closed` `ISS-170`；未交付余项留 `open` | `scope` M5→M6；M5 交付「特权 cfx」，余「LR-SC 原子」 |
| `ISS-005` | `scope` 校正（未交付） | M5→M6；M6 显式含「完整调用约定」 |
| `ISS-006` | `scope` 校正（未交付） | M5→M6；5 项 `[OPEN]` 均属 ABI，M6 含「完整调用约定 + 欠账收口」 |
| `ISS-019` | **待裁定**（保持原 `scope`） | `[golden, M5]`；M6 定义未显式覆盖 golden model（未擅自定为 M6/closed） |
| `ISS-026` | **待裁定**（保持原 `scope`） | `[testcases, M5]`；同 `ISS-019` |
| `ISS-047` | **待裁定**（保持原 `scope`） | `[llvm, M5]`；`llvm-objdump -d` 需 `--triple`，归属待用户裁定 |
| `ISS-074` | **待裁定**（保持原 `scope`） | `[testcases, M5]`；`cs.*` 条件赋值 overlap（C-27），FP/条件赋值相邻 |
| `ISS-081` | **待裁定**（保持原 `scope`） | `[spec, golden, testcases, llvm, qemu, integ, M5]`；FP 不在 M6 显式范围 |
| `ISS-110` | **边界拆分**：交付部分 → 新增 `closed` `ISS-171`；未交付余项留 `open` | `scope` M5→M6；M5 交付 `trap`/`escape`/`cfx2rc`/`cfx2rd`，余 `cfxld`/`cfxst`（`SimRISC-12`）+ `crii` + `SPEC-075t` 别名缺口 |
| `ISS-163` | **待裁定**（保持原 `scope`） | `[spec, M5]`；`Toolchain-01 §5/§11/§13` 旧口径，须用户授权方可收口 |
| `ISS-164` | **待裁定**（保持原 `scope`） | `[qemu, M5]`；cfx mask 屏蔽路径（monitor cause 全不可屏蔽）不可观测 |
| `ISS-166` | **提取为 `closed`** → `.tao/archive/M5/issues-closed.md` | `resolved_by: SPEC-121t`（`resolved_by` 提交日 ≤ 达成日） |
| `ISS-167` | **待裁定**（保持原 `scope`） | `[spec, qemu, M5]`；`DADAO-12 §5` prose/伪代码张力（伪代码为权威），须授权方可收口上游只读册 |

> **结果**：边界拆分新增 `closed` `ISS-170`/`ISS-171`（§4.4 提取计数 **5** > 任务书「实测基线 3」，差值为边界交付项，非矛盾）；`ISS-005`/`ISS-006` 及 `ISS-003`/`ISS-110` 余项 `scope` 校正 M5→M6；**8 条归属存疑项**保持原 `scope` + 标「待裁定」（未擅自处置，提请用户裁定，见 §8.2 第 7 项）；§3 步骤 3（移出教训/过程记录）**无适用项**。

---

## 8. 对 M6 的交接 / 交接清单

### 8.1 M6 定义（用户 2026-10-07 已定边界 + 2026-10-08 追加）

**M6 = 完整调用约定（整数）+ 欠账收口 +「elf 加载」**。开启任务 = `INTEG-023k`（**已建案，草案**）。自 M5 范围简化转入 M6 的待办见 `milestones.md`「M6 待办」条。

### 8.2 前置阻塞项（M6 规划必须先行）

| # | 项 | Issue | 归属 |
|---|---|---|---|
| 1 | 完整调用约定（变参/聚合/多返回/sret/间接调用）+ ABI `[OPEN]` 收口 | `ISS-005`/`ISS-006` | M6（**已校正** scope） |
| 2 | 「`-bios`+ELF 组合语义」+ ELF loader 扩展 + 组合加载 ADR（**须逐条确认**） | `ISS-168` | M6 |
| 3 | `RAM@0` C1 step2（旧向量/harness 迁移 + 删旧段 + 收紧断言） | `ISS-165` | M6 |
| 4 | 6 探针 exit-port→`SYS_EXIT` 重写（含分支偏移重算） | `ISS-169` | M6 |
| 5 | `LR-SC` 原子（`SimRISC-12`） | `ISS-003`（余项） | M6（**已校正** scope） |
| 6 | `cfxld`/`cfxst`（`SimRISC-12`）+ `crii` + `SPEC-075t` 别名缺口 | `ISS-110`（余项） | M6（**已校正** scope） |
| 7 | **归属存疑（待用户裁定，未擅自定 M6）**：`ISS-019`/`ISS-026`/`ISS-081`（golden model / FP oracle）、`ISS-047`（objdump triple）、`ISS-074`（`cs.*` overlap）、`ISS-163`（`Toolchain-01` 旧口径）、`ISS-164`（cfx mask 可观测性）、`ISS-167`（`DADAO-12 §5` prose 张力） | 见左 | **待裁定** |
| 8 | `SPEC-120t` 的 `**项目里程碑**`「可移 M6/后续」括注（M5 归档时按 M5 归档，**待用户复核**） | —— | **待裁定** |

### 8.3 可复用资产

- **SEE/semihosting**：`spec/Machine-01-测试机运行环境.md` + `contract-see.md`/`contract-semihosting.md` + `ADR-0020`
- **semihosting 接入范式**：`components/qemu/patches/**/common-semi-target.c` + `arm-compat-semi.c`（零改动复用）+ 接入点清单（`§8.13`）
- **M5 E2E**：`tools/integ/run_m5_e2e.py` + `Makefile::test-semihost` + `tests/scripts/bootrom.S`/`bootrom.lds`
- **bootrom 构建**：`Makefile::build-bootrom`（`llvm-mc`+`ld.lld`+`llvm-objcopy`）
- **独立向量 + oracle**：`tests/llvm/codegen/m5/`（`validate_m5_vectors.py` 141 checks，**禁** LLVM/QEMU 反填）
- **RAM@0 双映射 + 越界路由**：`hw/dadao/dadao-machine.c` + `helper.c`；`check-interface` 断言
- **spec 保护**：`manifests/spec-readonly.lock.toml` + `tools/infra/check_spec_readonly.py` + `make check-spec-readonly`
- **CFX 生成器**：`tools/llvm/gen_cfx_alias_table.py`、`tools/spec/generate_opcodes.py`
- **一键证据脚本**：`.work/evidence/<任务ID>/run.sh`（`INFRA-031t` 规程）

### 8.4 建议分解顺序（草案）

1. M6 开启（`INTEG-023k`）：定义完整调用约定 + 欠账收口 + elf 加载；**先经用户裁定**归属存疑项（§8.2 第 7/8 项）
2. 「`-bios`+ELF 组合」+ ELF loader 扩展（**须立 ADR 逐条确认**）
3. `RAM@0` C1 step2 迁移（跨 testcases/integ/infra/qemu）
4. 完整调用约定（变参/聚合/多返回/sret/间接）+ ABI `[OPEN]` 收口
5. 6 探针 `SYS_EXIT` 重写；`LR-SC`/`cfxld`/`cfxst` 欠账
6. 归属存疑项（golden/FP/objdump/`cs.*`/spec 旧口径）按用户裁定归入或另立

---

## 9. 复现手册

### 9.1 一键命令序列

```bash
make check                    # manifest-check + 各 checker + lit + spec-readonly（21 册）
make check-patch-tree         # 92 patches OK
make test-semihost            # M5 门槛（五组成；前置 test-elf/test-codegen/check）
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
| 2 | GNU make recipe 失败返回 **2**（非子命令码） | 注入判据一律 `-ne 0`（`§8.18`） |
| 3 | 证据脚本裸 `git diff` 断言「已提交变更」⇒ 提交后假 FAIL | 用 `$BASE_COMMIT..HEAD`（`§8.7`） |
| 4 | 反例注入后未**重建** | 还原须含重建（源码还原 ≠ 二进制还原） |
| 5 | 用 `git checkout`/`restore`/`stash`/`show <commit>:<path>` 还原 | 禁；一律 `cp`+md5（`§8.14`） |
| 6 | `spec/` 改动无门控告警 | `check-spec-readonly`（哈希锁，纳入 `make check`） |
| 7 | `SYS_EXIT` 块指针在 `rb16`、退出码在内存块 | 勿沿用 exit-port 寄存器习惯（`§8.17`） |
| 8 | `-d cpu` 最后一次 dump 观测切点（`SYS_EXIT` 不在 trap 前切 TB） | exit 序列前置 no-op `jump` 强制 TB 边界（`§8.17`） |
| 9 | 复用上游共享层只写钩子 ⇒ SIGSEGV / CLI 拒绝 | 列全接入点清单（`§8.13`） |
| 10 | 门控「覆盖计数」靠目测 | 脚本 `--list`/`distinct N` 机器可判（`§8.18`） |
| 11 | 独立 oracle 黑绿灯 ≠ 语义 | 语义由 E2E 驱动承担（「覆盖 ≠ 语义」，`§8.16`） |
| 12 | 非 ASCII 路径 `git status` 被转义 | `git -c core.quotePath=false` |

### 9.3 门槛检查详情

| 门槛 | 复算方式 |
|---|---|
| `make test-semihost` | 五组成：`run_m5_e2e.py`（10/10）+ `min_rom_probe_046t.py`（25 服务）+ make 前置链（`test-elf`/`test-codegen`/`check`） |
| `make check` | `repository checks: PASS`；`check_issues: 39 open, 0 closed`（归档后） |
| `make check-lit` | `Total Discovered Tests: 62 / Passed: 62` |
| 补丁数 | `make check-patch-tree` → `2 component(s), 92 patches OK` |
| 台账 | `python3 tools/infra/check_issues.py`（归档后 `39 open / 0 closed`） |
| 过程度量 | 遍历 `.tao/archive/M5/**/*.md`，`re.findall(r"\*\*(Accepted|Needs Revision)\*\*", txt)` |

---

## 10. 术语表 + 文件地图

### 10.1 术语

| 术语 | 含义 |
|---|---|
| SEE/HEE | 监管执行环境 / 主管执行环境（`DADAO-12`/`DADAO-13`）；M5 主题 |
| semihosting | guest 经 `trap`（tag `immu18[17:16]==2'b11`）请求宿主服务（ARM 号值） |
| `SYS_EXIT` | semihosting 停机服务（取代 exit-port；退出码传 host `$?`） |
| cfx / cfxha | 核芯功能扩展寄存器 / 其地址（`cfx0/1/2/3/63` 为 M5 实现集） |
| `ILLI` / `CFXREG` | M5 可观测的 cfx 级权限异常（mask/reserved；未实现 cfx / 超数量组合） |
| `NUPERM/NJPERM/NSPERM/NHPERM` | PTBR 权限层异常（`DADAO-12 §2.2`，**不在 M5**） |
| `CFXMEM` / `unmapped` | 越界访问/取指异常：`umon` 段⇒`0x81`；其余⇒`0x87` |
| RAM@0 双映射 | C1 step1：`0x0`（16 MiB）+ 旧 `0xffff_0000_0000` 并存；step2 随 M6 |
| bootrom | `-bios` 加载的 SEE 固件（`bootrom.S`/`bootrom.lds`，复位 PC `0xffff_ffff_0000`） |
| `-bios`+bin | M5 加载模型（path B raw-bin；ELF 加载随 M6） |
| L1/L2/L3 | `Process-05` 三层测试（L1 编码 / L2 CodeGen 结构 / L3 执行） |
| 独立 oracle | 期望值由 `spec/`/`contracts/` 独立派生（禁从 `llc`/QEMU 反填） |

### 10.2 文件地图

| 路径 | 用途 |
|---|---|
| `AGENTS.md` | 项目规则（**经验规则的唯一准绳**） |
| `.tao/tasks/<module>/` | 任务书（M6 起新建；M5 已归档） |
| `.tao/archive/M5/` | M5 历史归档（任务书 + README + 本文件 + issues-closed） |
| `.tao/knowledge/` | `MEMORY.md` / `milestones.md` / `changelog.md` / `issues.yaml` / `lessons.md` / `contract-*.md` |
| `.tao/adr/` | 架构决策记录（决策层，含 `ADR-0020`） |
| `spec/` | 规范树（`Machine-01` + 上游 `SimRISC-*`/`DADAO-*`/`Toolchain-01` + `Process-0x`） |
| `manifests/` | 组件锁 + `spec-readonly.lock.toml`（spec 只读哈希锁） |
| `contracts/` | 机器可读合约（编码表/合法性/ABI/FP 语义） |
| `components/<name>/patches/` | 树形有序补丁集（llvm 58 / qemu 34） |
| `tools/<module>/` | 各模块工具脚本（含 `run_m5_e2e.py`/探针/生成器） |
| `tests/{llvm,e2e,scripts,qemu}/` | 向量/lit/harness/bootrom |
| `.dadao/` | 安装根 + 运行产物默认落点（`.dadao/tests/`，gitignored） |
| `.work/` | 一次性工作区（**整体不入库**） |

---

## 11. 审计追溯链

每个 M5 结论都可回溯到「任务 → 审阅轮次 → 命令/log」。指针表：

| 结论 | 任务 / 决策 | 审阅记录 | 证据（命令 / 日志） |
|---|---|---|---|
| SEE/HEE + semihosting 决策 | `ADR-0020` / `ADR-0004 R1–R3` / `SPEC-113t` | 用户逐条确认 | `.tao/adr/adr-0020-*` |
| install 落地 | `INFRA-047t` | 2 轮 | `make install-host`；`.work/log/` |
| 生成物落点 `.dadao/tests/` | `INFRA-048t` / `SPEC-117t` | 1 轮 | `test-codegen`/`test-elf`/lit 落点 |
| `Machine-01` 正文 | `SPEC-114t` | 2 轮 | `make check`/`check-spec-refs` |
| spec 只读保护 | `SPEC-119t` / `Process-06` | 2 轮 | `make check-spec-readonly`（21 册） |
| cfx 指令链 | `LLVM-060t` → `SPEC-115t` | 2 轮 | `check-patch-tree`（92）、oracle 14 供 |
| `Toolchain-01` 修订 | `SPEC-116t` | 1 轮 | 锁 `sha256` 同步 |
| `encode_cfx` 删除 | `SPEC-120t` | 2 轮（round1 被推翻） | 0 引用实测、渲染零差 |
| `Machine-01 §1` 落地 + 入锁 | `SPEC-121t` | 1 轮 | 锁 20→21 |
| SEE 执行层 | `QEMU-044t`/`045t`/`046t` | 1 轮 | 探针 `044t` 13/13、`045t` 14/14、`046t` 32/32 |
| RAM@0 双映射 | `QEMU-049t` | 1 轮 | 探针 `049t` 9/9；`check-interface` 85 |
| 新 bootrom | `QEMU-047t` | 1 轮 | 探针 `047t` 13/13；`-d cpu` 首块 PC |
| exit-port→`SYS_EXIT` | `TESTCASES-034t` | 1 轮 | 门控逐项相等；26 探针等价 |
| M5 门槛 10/10 | `INTEG-020t` | 1 轮 | `make test-semihost` EXIT=0（59s） |
| M5 达成 | 6 个 `m` | 核验记录 | `.work/log/integ/INTEG-020t-*`；`milestones.md` M5 = 达成 |
| 归档前置台账梳理 | `INTEG-022t`（本任务） | —— | `Process-04 §3`；`check_issues.py`（39 open/0 closed） |

> 历史日志：`.work/log/<module>/<任务ID>-<命令名>.log`（reviewer 重跑加 `-review-`）。

**M5 达成（2026-10-08，architect 代主会话核验）**：门槛 **`make test-semihost` EXIT=0**（**五组成全绿**：正向 10/10 / cfx 级权限反例 4/4 / 服务表 25/25 / 不回归〔`test-elf` 5/5、`test-codegen` 15/15、`check`〔含 `check-lit` 62/62〕、`check-no-residue`〕/ INTEG 开闭）；6 个模块 `m`（`INFRA-049m`/`SPEC-118m`/`LLVM-061m`/`QEMU-048m`/`TESTCASES-035m`/`INTEG-021m`）**全置 `里程碑`**；19 个 M5 `t` 任务 + `INTEG-019k` 全 `已验证`。核验命令/证据见各 `m` 文件「核验记录」与 `.work/log/integ/INTEG-020t-*.log`。**跨模块项**（`ISS-163`〔用户裁定暂登记〕/`ISS-164`〔跟踪〕/`ISS-165`〔M6〕/`ISS-166`〔closed〕/`ISS-167`〔登记 + 建议另立 spec 任务〕/`ISS-168`〔M6〕/`ISS-169`〔M6〕）均已处置、不阻断 M5 收敛；`ISS-170` 不存在（最大 id = `ISS-169`）。**归档前置**（`Process-04 §3` 遗留台账梳理，步骤 3–6）与 **M5 任务书归档**（预期 **26** 个 = `infra 3/spec 9/llvm 2/qemu 6/testcases 3/integ 3` + 自归档）待立归档任务（建议 `INTEG-022t`，范围见 `INTEG-021m` §核验记录「归档准备（评估）」）。**M6 待办**见下「M6 待办」条。
**归档（2026-10-08）**：M5 的 27 个任务书已归档至 `.tao/archive/M5/`（按模块子目录）；M5 时期 changelog（20 条）/MEMORY（1 行）内容见 `.tao/archive/M5/README.md`；**M5 回顾见 `.tao/archive/M5/m5-retrospective.md`**；`issues.yaml` 的 5 条 M5 阶段 closed 项（`ISS-147`/`ISS-157`/`ISS-166` + 边界交付项 `ISS-170`/`ISS-171`）见 `.tao/archive/M5/issues-closed.md`。归档前置 `Process-04 §3` 台账梳理（步骤 1–6）与本归档（`§4`）由归档任务 **`INTEG-022t`** 一并执行；台账指针已同步（`changelog.md`/`MEMORY.md`/`issues.yaml`/本文件）。
> **M5 起步待办（2026-10-06，用户裁定）**：**M5 阶段开始先处理 install 问题**——落地 `ADR-0016 D1–D11`：host 工具链 → `.dadao/cross-toolchain`（D3/D4/D11）、target sysroot → `.dadao/dadao-unknown-elf`（D5）、`manifests/` 单一真源定位（D7，禁硬编码）、**门控/执行器改从 install 根取可执行**、`.work/` **仅**作 build 区（D9）；并保留「从源码可重建」（D9）。**M4 阶段不强制**；落地任务编号待 M5 规划时再定（不预建任务书）。 **✅ 已落地（2026-10-07，`INFRA-047t`）**：host 工具链 `.dadao/cross-toolchain`（D3/D4/D11）、target sysroot `.dadao/dadao-unknown-elf`（D5）、`manifests/` 单一真源定位（D7，禁硬编码）、**门控/执行器改从 install 根取可执行**（D9，含 `D9` 点名的 `run_qemu_test.py`）、`.work/` 仅作 build 区（D9）均已实现；保留「从源码可重建」（`rm -rf .dadao/cross-toolchain && make install-host` 仍 EXIT=0）。

> **生成物落点口径（2026-10-06，用户明确）**：运行产物**默认为 `.dadao/tests/`**；**只有"难以放进 `.dadao/`"时**才退到**当前模块对应目录**；判据 = **"能否用配置选项解决"——能配置解决的一律不算"难"，必须放 `.dadao/`**。规范正文落 `spec/Process-05 §6`（M5 补正）。 **✅ 已落地（2026-10-07，`SPEC-117t`）**：§6 已改写为「默认 `.dadao/tests/` + 退让判据（能配置解决 ⇒ 必进 `.dadao/`）+ 定位机制（`ADR-0016 D7/D8`，禁硬编码）+ `.work/log`/`.work/evidence` 不算生成物、不受约束 + 自 M5 起生效 + 保留不强制留存」，单 hunk（+9/−2）仅 §6、其它节语义零改动；与 `INFRA-048t` 迁移后落点一致（`make check`/`check-spec-refs` EXIT=0）。

> **落点规则生效时点（2026-10-06，用户裁定）**：**M4 已完成/在做的测试落点一律不动**；**自 M5 起按新规则**。M5 起步须迁移（判据 = 能配置解决 ⇒ 必进 `.dadao/`）：① `test-codegen` 运行产物 `tests/llvm/codegen-e2e` → `.dadao/tests/codegen-e2e`；② `test-elf` 运行产物（`run_elf_e2e.py` 的 `DEFAULT_WORK_DIR` / `Makefile`）→ `.dadao/tests/elf-e2e`；③ lit 的 `test_exec_root`（现 `<build>/test-output/<name>`，在 `.work/build/llvm/` 内）→ `.dadao/tests/lit-output/<name>`。**`.work/log`（日志）与 `.work/evidence`（证据）不算"生成物"、不动**（2026-10-06 用户裁定）。 **✅ 已落地（2026-10-07，`INFRA-048t`）**：三处落点均已迁移——`test-codegen` → `.dadao/tests/codegen-e2e`、`test-elf` → `.dadao/tests/elf-e2e`、lit `test_exec_root` → `.dadao/tests/lit-output/<name>`（均经 `tools/infra/paths.py`〔D7〕解析，无硬编码）；清 `.gitignore` 旧规则 `tests/llvm/codegen-e2e/` 并**同删残留旧产物目录**（`tests/llvm/codegen-e2e/`、`.work/codegen-e2e-elf`）；语义零改动（15/15 + 5/5 + 60/60）。第 4 处占位 lit 配置 `tests/llvm/lit/tools/DADAO/lit.cfg.py` 无门控引用，按最小原则未改（登记遗留）。

**M5 — SEE/HEE 运行环境 + semihosting**（规划中；`k` = **`INTEG-019k`**）

> **开启（2026-10-07）**：依 `spec/Process-04 §1`（用户 2026-10-06 裁定「**M5 起由 INTEG 模块开闭**」），M5 由 **INTEG 模块的规划 `k`** 开启 ⇒ `.tao/tasks/integ/INTEG-019k-m5启动与分解.md`（**非** `SPEC-*k`；M1–M4 的 SPEC 开启做法为历史，不沿用）。本行为**规划中**（模块 `m` 尚未建立、`t`/`m` 任务书为草案）。

**目的**：把 QEMU 从 M1–M4 的「裸机、无 OS、无 syscall、`exit port` 停机」升级为「**SEE/HEE 运行环境 + semihosting**」：实现四运行模式与 cfx（核芯功能扩展）寄存器的**权限/掩码/`switch_run_mode`/权限异常**；以**新 bootrom（自有工具链编）**完成初始权限/向量配置；让 guest 经 `trap`（semihosting tag = `immu18[17:16]==2'b11`）走 QEMU **共享层 `do_common_semihosting`** 服务（**ARM 号值**），并以 **`SYS_EXIT` 替代 `exit port`**；LLVM 实现 `trap`/`escape`/`cfx2rc`/`cfx2rd`（`SimRISC-11`）——**`SimRISC-12`（`cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*`）保持 deferred**。

**范围**（用户裁定 2026-10-07，详见 `INTEG-019k` §已锁定边界 + §第 2 轮用户裁定）：① 基础设施：`ADR-0016 D1–D11` install 落地 + 生成物落点迁移（`.dadao/tests/`）+ `Process-05 §6` 补正；② SEE/HEE：运行模式/cfx 寄存器/掩码/权限/`switch_run_mode`/权限异常/异常进入流程（**权限范围 = 只做 `cfx0/1/2/3/63`**；**未实现 cfx ⇒ `CFXREG` 异常**，`DADAO-22:58`）；③ 新 bootrom（构建+链接+测试；**`-bios` 加载、复位向量不变 `0xffff_ffff_0000`、hypv→user 直跳、本版不启用 supv**）；④ LLVM 4 条指令（MC + 必要 CodeGen/内建）+ re-scope（`excluded`→已实现）；⑤ semihosting（tag 判定 + **服务表 = 完整 25 个**〔含 D2 文件档；`SYSTEM`、`HEAPINFO` 都做〕+ **共享层钩子按 `n` 选 bank**〔`n=0`→`rd16`、`n=1`→`rb16`、`set_ret`→`rd31`〕+ `SYS_EXIT` 替代 + exit-port 迁移〔**全部**〕 + harness stdio 捕获）；⑥ spec 正文（测试机/SEE/semihosting 调用表 + re-scope + 大小写敏感修订）；⑦ 门控收口。

**semihosting 传参/返回寄存器（用户裁定 2026-10-07）**：**号（标量）→ `rd16`（=`rda0`）**、**参数块指针（地址）→ `rb16`**、**返回值 → `rd31`**（`.tao/knowledge/contract-abi.md §4.1/§4.4`；指针返回才用 `rb31`，semihosting 不用）。

**门槛（用户裁定 2026-10-07 第 2 轮；**正向口径已于 2026-10-08 修订**，见下「M5 范围简化」）**：门控名 = **`make test-semihost`**（**不是** `test-see`——用户指出"没有 SEE"）。组成 = **正向**（**bootrom（`-bios`）+ bin 应用**经 `-semihosting`、console 捕获、`SYS_EXIT` 码；原「单/多 TU ELF」正向用例**移 M6**）/ **权限反例**（**M5 可观测 = cfx 级**：`ILLI`〔mask 禁止 / reserved〕、`CFXREG`〔未实现 cfx / 不存在或超数量寄存器组合〕；**`NUPERM/NJPERM/NSPERM/NHPERM` 出自 `DADAO-12 §2.2` PTBR 权限层、不在 M5**〔`ADR-0020 D9`〕）/ **服务表各条至少 1 例** / **不回归**（`test-elf` 5/5、`test-codegen` 15/15、`check`、`check-lit`）/ **`INTEG` 开闭**。

> **前置风险（2026-10-08，architect 实测）→ ✅ 已由用户裁定消解**：门槛正向「bootrom + 单/多 TU ELF 经 `-semihosting`」按**字面耦合读** ⇒ 曾需**「`-bios`+ELF」组合**，而 `QEMU-047t`（选 path B raw-bin）**未实现**该组合（`dadao_load_regions[]` 未含 RAM@0、ELF 分支忽略 `-bios`）⇒ 曾判**可能为 M5 门槛前置缺口**。**用户 2026-10-08 裁定（原话见 `INTEG-019k` §第 8 轮）**：**M5 只做 bootrom+bin**、**elf 加载随 M6** ⇒ **门槛正向口径改为「bootrom（`-bios`）+ bin 应用经 `-semihosting`」**，该缺口**不再是 M5 门槛前置**（「`-bios`+ELF 组合 / ELF loader 扩展 / 组合入口语义」移 M6，见下「M6 待办」+ `ISS-168`）。原评估/选项（历史记录）见 `.tao/tasks/integ/INTEG-020t-*.md`「审阅记录」architect 前置风险评估。

**范围外（边界声明）**：**M6 = 完整调用约定（整数）+ 欠账收口 +「elf 加载」**（已定，不在 M5；「elf 加载」= 用户 2026-10-08 裁定）。FP/RF codegen、clang 前端、libc/OS、golden model 不在 M5。

> **前置 ADR（待用户逐条确认）**：`ADR-0020`（新建，SEE/HEE 与 semihosting，D1–D14）、`ADR-0004` 修订（新 bootrom 与加载模型，R1–R3）、`ADR-0016`（落地范围，S1）。decision 提案与**已裁定项（10 项，2026-10-07 第 2 轮）**见 `INTEG-019k` §说明 / §第 2 轮用户裁定。**M5 开启于 `INTEG-019k`；`/plan` 交叉审查通过后再建 21 份 `t`/`m` 任务书。**
>
> **任务书已建（追加，2026-10-07）**：`INTEG-019k` §任务分解的 **21 份任务书（15 `t` + 6 `m`）已创建**（编号按 `INTEG-019k` 草案，无占用冲突、无顺延）：W0 `INFRA-047t`/`INFRA-048t`/`SPEC-117t`；W1 `SPEC-113t`/`SPEC-114t`/`SPEC-115t`/`SPEC-116t`；W2 `LLVM-060t`；W3 `QEMU-044t`/`QEMU-045t`/`QEMU-046t`/`QEMU-047t`；W4 `TESTCASES-033t`/`TESTCASES-034t`；W5 `INTEG-020t`；模块 `m` = `INFRA-049m`/`SPEC-118m`/`LLVM-061m`/`QEMU-048m`/`TESTCASES-035m`/`INTEG-021m`。依赖/串行链严格按 `INTEG-019k` §任务分解表（见各任务书 `**依赖**` 字段）。
>
> **落点裁定（追加，2026-10-07，用户确认）**：① **`QEMU-047t`（新 bootrom）**——**固件源码放 `tests/scripts/`**、**生成物放 `.dadao/` 下**（运行产物默认 `.dadao/tests/`；能靠配置解决的不算「难」，须放 `.dadao/`）。② **`SPEC-114t`（SEE/semihosting 规范正文）**——**正文落新建 `spec/Machine-01-测试机运行环境.md`**（`Machine` 前缀经用户确认），章节 ①内存映射/复位 ②运行模式 ③cfx/权限 ④`trap`/`escape`/异常进入 ⑤semihosting ⑥加载/bootrom ⑦退出，并**登记 `spec/README.md`**。两处落点已写入对应任务书（`QEMU-047t` 输出/约束、`SPEC-114t` 输出）。
>
> **`/plan` 通过（追加，2026-10-07）**：`INTEG-019k` 规划经 `/plan` 级交叉审查通过（第 2 轮 reviewer 复审的最小必改项已落实：`INTEG-019k` B9 现为 `SimRISC-11 L80`，与 `spec/SimRISC-11-其它.md:80` 一致）⇒ `INTEG-019k` 状态置 **`已验证`**。
>
> **ADR 逐条裁定落盘 + RAM@0 两步（追加，2026-10-07）**：用户对 `SPEC-113t` ADR 判定清单**逐条裁定**（原话见 `SPEC-113t` §待用户逐条判定清单「四、用户逐条裁定结果」）——**新增 `ADR-0020 D15`**（核内地址空间划分 + **越界访问/取指异常**：`CFXMEM` vs 测试机约定 `unmapped 0x87`，含取指路径；`ADR-0004 D5.8` 码表冻结不重排）；**`D1`** 决策保留、语义/理由说明移 **`spec/Machine-01-*`**（`SPEC-114t`）；**`R1`** = `-bios` bootrom 与 M4 ELF **并存（非替代）**；**`R2`** = `SYS_EXIT` 取代 exit-port；**`R3`** = **RAM 基址改为全 0**（`0x0000_0000_0000`）+ **C1 双映射两步**；**`D2–D14`/`S1` 按「未特别指出 = 保留」推定**，并经用户 **2026-10-07 明确确认**（原话「全部确认」）——**复核闭合**。
>
> - **C1 两步（`ADR-0004 R3`/`ADR-0020 D15`）**：**step1（M5）** = 新任务 **`QEMU-049t`**（QEMU 机器模型**同时映射 RAM@0〔新，供 bootrom/SEE〕+ 保留旧 RAM 段〔`0xffff_0000_0000`，供既有测试〕** + RAM@0 链接基址 + **`check-interface` 断言新增 RAM@0 段〔旧断言保留〕**），`QEMU-047t` 依赖之；**step2（另立，M5 之外）** = 既有向量/harness/`crt0`/e2e 迁到 `0` + 删旧 RAM 段 + 收紧断言。
> - **M5 门槛口径**：**以「RAM@0 双映射过渡态」收敛**——step1 保留旧 RAM 段 ⇒ 既有测试**不回归**（`test-elf`/`test-codegen`/`check`/`check-lit`）；**step2 不阻塞 M5 门槛**（编号/归属待 M6 规划或另立时确定）。M5 qemu 任务数 **4→5**（`QEMU-048m` 关联任务含 `QEMU-049t`）。
>
> **✅ ADR 决策落地完成（追加，2026-10-07，`SPEC-113t`）**：`ADR-0020`（新建，`D1–D15`）置 `Accepted`；`ADR-0004` 就地修订（`R1` `-bios` bootrom 与 M4 ELF 路径**并存** / `R2` `SYS_EXIT` **取代** exit-port / `R3` RAM 基址**改全 0** + C1 双映射两步），受保护决策 `D1`/`D2.1`/`D3`/`D4`/`D5`/`D6` 正文**未改**；`ADR-0016 S1` 判**沿用** `D1–D11`（不改正文）。reviewer `Accepted`、architect 交叉复核通过（证据脚本 51/51 + 独立注入有鉴别力；`make check` 80/80 EXIT=0）。
>
> **新规则：spec 目录保护（追加，2026-10-07，事故裁定）**：`SPEC-114t` 的 engineer **无授权擅改上游只读册** `spec/DADAO-12`/`spec/DADAO-22`（各插入 2 行），**已按用户裁定以 `cp`+`md5` 还原到 base `96f09f1`**（md5 `83dec5ea…`/`a3070bd4…`，逐字一致；未用 `git checkout/restore/stash`）。用户裁定（原话）：「**DADAO-21 和 DADAO-22 都不应该做修改**」「**所有针对 spec 目录的修改，都应该经过我的允许，不能擅自进行**」。**上游只读册清单（用户全选）** = `DADAO-1x`(11/12/13) + `DADAO-2x`(21/22/23) + `SimRISC-00..12` + `Toolchain-01`（**20 册**）。**机制落地 = 新建 `SPEC-119t`**（「spec 目录保护：只读哈希锁 + 门控 + 流程约束」）：`manifests/spec-readonly.lock.toml`（逐册 `sha256` 锁）+ `tools/infra/check_spec_readonly.py` + `make check-spec-readonly`（**纳入 `make check`**）+ 规则入新建 `spec/Process-06-spec目录保护规范.md`；`SPEC-115t`/`SPEC-116t`（将改上游只读册 `SimRISC-11`/`Toolchain-01`）加前置「**下发前须用户明确允许（原话落盘），否则 BLOCKED**，并同步更新哈希锁」。`SPEC-118m` 关联任务 5 → **6**（+= `SPEC-119t`）。M5 任务书 22 → **23**。
>
> **✅ spec 目录保护机制落地完成（追加，2026-10-07，`SPEC-119t`）**：`manifests/spec-readonly.lock.toml`（上游 20 册逐册 `sha256` 锁）+ `tools/infra/check_spec_readonly.py`（`if errors` **fail-closed**）+ `make check-spec-readonly`（**已纳入 `make check`**）+ 规则正文 `spec/Process-06-spec目录保护规范.md`（①–⑤ 均 MUST）均已落地；`SPEC-118m` 关联任务含 `SPEC-119t`。reviewer **`Accepted`**、architect 交叉复核通过（20 册 `sha256` 独立重算全等、`spec/` 变更仅 `Process-06`+`README.md`、6 类反例注入均 FAIL 且还原回绿、`make check` EXIT=0）。
>
> **✅ SEE/semihosting 规范正文落地完成（追加，2026-10-07，`SPEC-114t`）**：新建 **`spec/Machine-01-测试机运行环境.md`**（①–⑦ 七节：内存映射/复位〔核内地址空间划分表 + 越界访问/**取指**异常 `CFXMEM` vs 测试机约定 `unmapped 0x87`，`ADR-0020 D15`；`ADR-0004 R3` RAM 基址全 0 + C1 双映射两步〕、运行模式〔`hypv`/`user`，本版不启用 `supv`〕、cfx/权限〔**`cfx0/1/2/3/63` 明标测试机约定、不构成上游架构限制**；未实现 cfx ⇒ `CFXREG`；`NUPERM` 等两权限层次〕、`trap`/`escape`/异常进入〔两条路对照〕、semihosting〔判定 `immu18[17:16]==2'b11`、`D1` 语义说明、传参 `rd16`/`rb16`、返回 `rd31`、**完整 25 服务**、PC 步进无 `escape`、`SYS_EXIT` 取代 exit port、`SYS_SYSTEM` 风险登记〕、加载/bootrom、退出）；投影 **`contract-see.md`/`contract-semihosting.md`**（最小集合 = 2）+ 登记 `spec/README.md`。**上游只读册零改动**（`DADAO-12/13/21/22`、`SimRISC-*`、`Toolchain-01` 共 20 册 `git diff 96f09f1..HEAD -- spec/` 无交集、逐册 md5 与 base 逐字一致）；round1 擅改的 `DADAO-12`/`DADAO-22` 已还原。reviewer **`Accepted`**、architect 交叉复核通过（`make check`/`check-spec-refs` EXIT=0；证据脚本 35 PASS + 独立注入有鉴别力）。

> **M5 任务链重排（追加，2026-10-07，用户裁定 1/2/3）**：`SPEC-115t` 的 engineer **BLOCKED**（未实施、工作树零改动）——`scope: excluded → m1` 会撞 **3 个跨模块门控**（`validate-vectors` 的 `inventory.md` M1 行集 / `check-interface` 的 M1 计数 + 每 M1 `format` 族 lit `; OBJ:` / `check-instrinfo` 的每 M1 唯一 `.td` def，均在 `make check` 内），其中 `check-instrinfo` **必须** `LLVM-060t` 的 `.td` def；原分解把 `LLVM-060t` 置于其后 ⇒ 单发必红。**用户裁定（原话）**：①「**A 重排：先 LLVM-060t 再 SPEC-115t（推荐）**」；②「**改生成器并重跑（推荐）**」；③「**encode_cfx不应该存在，这个是实现层面的事情，不是汇编或者编码时需要处理的问题，单独建立一个任务解决该问题**」。
>
> - **重排（裁定 1）**：`LLVM-060t` **前置**（依赖仅 `INFRA-047t`；编码 `op`/`mask`/`value` 在 re-scope 前后不变）；`SPEC-115t` 依赖 += `LLVM-060t`，文件集 += `tests/vectors/inventory.md`（+4 行）/`tools/llvm/validate_instrinfo.py`（`MC_ONLY_EXCLUDED_IDS`：`LLVM-060t` 加入 4 条、`SPEC-115t` re-scope 后移除）；lit `crrr`/`ciii` 的 `; OBJ:` 由前置的 `LLVM-060t` 承接（`TESTCASES-033t` 复用/扩展）。Wave：Wave 1 增 `LLVM-060t`、Wave 2 改「re-scope 收口」+ `SPEC-115t`。归属裁定见 `SPEC-115t` 审阅记录（**待用户复核项**）。
> - **改生成器（裁定 2）**：`contracts/opcodes.yaml` 由 `tools/spec/generate_opcodes.py` 生成 ⇒ `SPEC-115t` **改生成器 + 重跑**（禁只手改 yaml）。`legality`/`rule_refs` **保持 `[]`**（**不引 `encode_cfx`**，裁定 3 口径）。
> - **另立 `SPEC-120t`（裁定 3）**：`encode_cfx` 定界与最小修正（汇编/编码层不应含实现期语义；先调研定界 → 最小修正〔候选 A 删除 / B 降级〕；**默认不触 `spec/`**）。`**项目里程碑** = M5`（**architect 判断，待用户复核**）；`SPEC-118m` 关联任务 6 → 7。**M5 任务书 23 → 24**（+`SPEC-120t`）。
> - **教训**：下发前预检第 2 项须核「本任务**验证手段**所需的全部前置」，非仅「任务书声明的依赖」——见 `lessons.md §7.6`。

> **✅ M5 指令链首发落地完成（追加，2026-10-07，`LLVM-060t`）**：`trap`/`escape`/`cfx2rc`/`cfx2rd`（MC + 编码）落 `llvm/lib/Target/DADAO/**`（`.td` def〔op/mask/value 与 `contracts/opcodes.yaml` 一致〕+ AsmParser〔`cfx<ha>`/`cfx_<name>` 等价、简化 regname 展开、`escape` 位宽〕+ InstPrinter + 生成别名表 `DADAOCfxAlias.inc`）；**5b 门控前置**（lit `crrr`/`ciii` 的 `; OBJ:` 覆盖 + `MC_ONLY_EXCLUDED_IDS` += 4 条，由 `SPEC-115t` re-scope 时移除）满足 ⇒ 解除 `SPEC-115t` BLOCKED 的 `.td`/lit 前置。reviewer **`Accepted`**、architect 交叉复核通过（独立重跑生成器 + `cmp` 复现 patch、`check-patch-tree` 90 patches〔断言⑥〕、oracle 14 向量 0 错、注入有鉴别力、未越界〔无 `spec/`〕）；`make build-mc`/`check`(62/62)/`check-lit` EXIT=0。生成器随产物入库（`tools/llvm/gen_cfx_alias_table.py`）——教训见 `lessons.md §7.7`、规范见 `lessons.md §8.6`。**M5 下一环** = `SPEC-115t`（re-scope 收口）。

> **✅ M5 指令链 re-scope 收口完成（追加，2026-10-08，`SPEC-115t`）**：`trap`/`escape`/`cfx2rc`/`cfx2rd` 由 `scope: excluded` re-scope 为 `m1`——**改 `tools/spec/generate_opcodes.py` + 重跑**产出 `contracts/opcodes.yaml`（4 条 `op`/`mask`/`value` **逐字段未变**、`decode: ILLI` 消失、`legality`/`rule_refs` 保持 `[]`〔用户裁定 3，`encode_cfx` 另立 `SPEC-120t`〕）；计数 `m1 151→155`/`excluded 15→11`/`total 227` 不变；门控载体 `tests/vectors/inventory.md`（+4 行 `deferred`）/`tools/llvm/validate_instrinfo.py`（`MC_ONLY_EXCLUDED_IDS` 移除 4 条）收口；**经用户授权**改上游只读册 `spec/SimRISC-11-其它.md`（仅 LEGALITY 段）+ 同步其 `sha256` 锁（其余 19 册零变动）。生成器重跑**幂等**（md5 `965feb70…` == 提交物）。reviewer **`Accepted`**（round1 `Needs Revision` = 证据脚本 2 处裸 `git diff` 假 FAIL，round2 改用 `BASE_COMMIT..HEAD` 范围后回绿）、architect 交叉复核通过（独立重跑 `check_scope`〔155/60/11/227〕/`validate-vectors` 155/155/`check-instrinfo` 155/155/`check-interface` 80/80/`check-spec-readonly` 20 册 OK；temp 注入改 scope ⇒ `check_scope` FAIL ⇒ 回绿，有鉴别力；`spec/` 变更仅 `SimRISC-11`）。`make check` EXIT=0。**M5 下一环** = `QEMU-044t`/`QEMU-045t`（4 条执行层）+ `TESTCASES-033t`（4 条 M1 语义向量；`inventory.md` 已 `deferred` 声明）。遗留：`Toolchain-01 §1` 仍写「9 种 M1 格式 / `crrr`/`ciii` excluded」旧口径，与 re-scope 后 `m1` 实含 11 类不符——属**授权范围外**，须另行取得用户授权后同步（并更新其 `sha256` 锁）。**〔2026-10-08 处置：用户授权原话「1、并入SPEC-116t」⇒ 该偏差事项 **并入 `SPEC-116t`**（由其 `§1` 格式类口径同步 + 锁同步收口）；`SPEC-116t` 另含 `§2.1` 授权「允许（撤销不敏感条款）」。〕**

> **✅ `SPEC-116t` 落地（追加，2026-10-08）**：上游只读册 `spec/Toolchain-01-汇编语言.md` **仅两处 hunk**——`§2.1` **撤销**「助记符与寄存器名大小写不敏感（`ADD.SI` ≡ `add.si`）」→ **大小写敏感**（用户授权「允许（撤销不敏感条款）」+ 裁定 `INTEG-019k D16`；`ISS-157` 以「**条款撤销**」结案，非实现缺口）；`§1` **9 种 → 11 类** M1 格式（`rrrr`…`oiii` + `crrr` + `ciii`；`crrr`/`ciii` **不再** `excluded`、`crii` 据实测仍 `excluded`；用户授权「1、并入SPEC-116t」）——**收口 `SPEC-115t` 遗留**「`Toolchain-01 §1` 旧口径」；同步该册 `sha256` 锁（`d00c0925…`→`3f53c89c…`，其余 19 册零变动）+ 投影 `contract-asm.md`（§1/§2.1/§11 表）。`make check`/`check-spec-readonly` EXIT=0；证据脚本 40/40 + I1/I2/I3 注入自检。reviewer **`Accepted`**、architect 交叉复核通过（独立实测 `m1` 集逐项相等、锁 `sha256` 相符、`spec/` 变更仅 `Toolchain-01` 两处 hunk；reviewer 独立注入 `§2.1`→「不敏感」⇒ 6 断言 FAIL ⇒ 还原回绿，有鉴别力）。遗留：`Toolchain-01` `§5`/`§11`/`§13` 仍含旧口径（**授权范围外**，须另请授权后另立任务 + 锁同步收口）——**已登记 `ISS-163`（`open`，用户 2026-10-08 裁定原话「暂登记遗留」）**。ADR 提醒：本任务属规范条款修订、涉**外部契约**（LLVM/QEMU 对助记符大小写的期望）且存在被否方案（`INTEG-019k D16`）⇒ 由主会话提请用户裁定是否立 ADR。**〔2026-10-08 用户裁定原话：「不立 ADR」⇒ 不创建 ADR。〕**

> **✅ `SPEC-120t` 落地（追加，2026-10-08）**：`encode_cfx` 规则**删除**（**候选 A**；用户裁定 3「这个是实现层面的事情，不是汇编或者编码时需要处理的问题」）——该规则把「执行期 reserved `cfxha` ⇒ ILLI」误登记为 `kind: static` **编码合法性**，实测**全仓 0 引用**（`opcodes.yaml` `rule_refs` 0 条引用它 ⇒ 不进任何 `LEGALITY` 渲染）⇒ 删除后**无渲染变化**、**未触 `spec/`**（`git diff df56a6f..HEAD -- spec/` 空）。`contracts/legality_rules.yaml` 删该规则块（16→15 条，`deferred` 1→0）+ `tools/spec/gen_legality_list.py` 移除 `SEMANTIC_MAP`/`RULE_SUMMARY` 条目 + docstring 计数 `16→15`；`check_rule_refs`(15 条)/`check_legality_drift`(12 章)/`gen_legality_list --verify`(12/12)/`make check`(62/62) EXIT=0。reviewer **`Accepted`**（**round1 `Accepted` 由主会话依 `lessons §8.7` 推翻改判 `Needs Revision`**〔C10 由工作树 `git status` 计算改动集 ⇒ 提交后假 FAIL；§8.7 同类，`SPEC-115t` 先例〕，round2 改 `$BASE_COMMIT..HEAD` 后 `Accepted`）、architect 交叉复核通过（0 引用独立实测、`spec/` 交集为空、注入有鉴别力）。遗留：`gen_legality_list.py` docstring `228 entries` vs 实况 `227`（**既有陈旧**，未改，仅登记）。见 `lessons.md §7.15`/`§8.7 rule 5`。

> **✅ `QEMU-044t` 落地（追加，2026-10-08）**：**SEE/HEE 运行模式 + cfx 寄存器文件/掩码/权限/异常进入流程**（`DADAO-12 §1/§3/§4/§5` + `DADAO-13 §1`，spec-first）。改 `.work/source/qemu/target/dadao/**`（5 补丁）：① 四运行模式 `inner_run_mode`（2 位，0/1/2/3）与 cfx **正交**；② cfx 寄存器文件 `cfx0/1/2/3/63` 的 cg0–cg7（含 `global_cfx_mask` **跨 cfx 全局共享**、`trap_num`/`excp_sync_num`/`escape_num` 计数、`scratch_regs`/SRAM；复位值依 `DADAO-12 §3`/`DADAO-13 §1`）；③ `inner_cfx_mask`/`inner_cfx_code` 判断逻辑；④ `DADAO-12 §5` 异常进入步骤 1–10 + 异常退出；⑤ `trap`/`escape`/`cfx2rd`/`cfx2rc` 由 ILLI 桩改为路由到流程（`cfxld`/`cfxst` 保持 ILLI）。权限反例（4 类）：reserved cfxha ⇒ `ILLI`；未实现 cfx（cfx4）⇒ `CFXREG`；scratch rc≥N ⇒ `CFXREG`；RO 写 ⇒ `CFXREG`。探针 `tools/qemu/min_rom_probe_044t.py`（**随产物入库**）**13/13**；`make build-qemu`/`make check`/`check-qemu-semantics`/`test-codegen`(15/15)/`test-elf`(5/5)/`check-patch-tree`（**90 patches**/断言⑥）EXIT=0；证据脚本 `run.sh` EVIDENCE: PASS（3 反例合并注入 ⇒ FAIL ⇒ `cp`+md5 还原+**重建** ⇒ 回绿）。reviewer **`Accepted`**（独立注入 `if (0 && …)` 关 trap mask ⇒ `mask_illi` FAIL ⇒ 还原+**重建** ⇒ 回绿，有鉴别力）、architect 交叉复核通过（独立核四模式编码 / `global_cfx_mask` 跨 cfx 共享 / 复位值逐项对 `DADAO-12 §3`+`DADAO-13 §1` / 权限反例 4 类 / `check-patch-tree` 90 patches·`--source-state` clean / `git diff dae34ee..HEAD` 11 文件、`spec/` 交集空）。**新发现**：`DADAO-12 §5` 步骤 2 使 **monitor（cfx0–3）的全部 listed cause 不可屏蔽** ⇒ 步骤 3/4/5 对 monitor 同步异常**一律跳过**；当前测试机可观测的「mask ⇒ ILLI」路径**仅为步骤 1 的指令类型 cfx mask**（探针 `mask_illi` 即证）。遗留：PTBR 权限层（`NUPERM` 等）不在 M5（`ADR-0020 D9`）；`excp_cause_mask`/inner·global mask 屏蔽路径不可观测 ⇒ **登记 `ISS-164`**；`escape`/`trap` 完整语义（负偏移回退、跨 cfx escape、全寄存器面）归 `QEMU-045t`（045t 已收缩为「044t 基线之上深化/验证 + 专探针」，M5 总范围不变）。`QEMU-048m` 关联任务保持（044t 已验证，045t/046t/047t/049t 待办）。

> **✅ `QEMU-049t` 落地（RAM@0 双映射，C1 step1；追加，2026-10-08）**：reviewer **`Accepted`**（证据脚本 `run.sh` 重跑 `EVIDENCE: PASS`；**独立注入**改 `DADAO_RAM0_SIZE` 16→8 MiB ⇒ `ram0_top` FAIL ⇒ `cp`+md5 还原 ⇒ **重建** ⇒ 9/9，有鉴别力、还原含重建）、architect 交叉复核通过（独立核**两段不重叠** / `check-interface` **80→86**〔6 新断言 + 旧断言保留〕/ 越界路由 `umon⇒0x81`·`其余⇒0x87` / `0x87–0x8D` 未重排 / `check-patch-tree` **90 patches** / `git diff 00c9540` **10 文件·`spec/` 交集空**）。step1 = 机器模型**同时映射 RAM@0（`0x0000_0000_0000`，16 MiB，cfxha 0 = `umon`）+ 保留旧 RAM 段（`0xffff_0000_0000`）** + 越界访问/取指异常语义（**umon 段越界 ⇒ `CFXMEM`〔`0x81`〕；其余含旧 `power` 段 63 ⇒ 测试机约定 `unmapped`〔`0x87`〕**，含取指路径）。探针 `tools/qemu/min_rom_probe_049t.py` **随产物入库** 9/9。**step2 迁移为跨模块待办（另立、M5 之外；登记 `ISS-165`）**：旧向量/harness/`crt0`/e2e 迁到 `0` + 删旧 RAM 段 + 收紧 `check-interface` 断言；**含「既有 `EA=0 ⇒ unmapped 0x87` 向量/探针在 R3 下失效」**——RAM@0 落在 `0` 后 `EA=0` 变为**合法 RAM**。**受影响对象类别** = `tests/vectors/**`（如 `isa/{mem-rd,mem-rb,mem-ra,ctrl-*}.yaml` 以 `EA=0` 作 unmapped 的用例）+ `tools/qemu/*.py` 探针（如 `min_rom_probe_010t.py` 的 T6/T18）。**当前不在任何 `make` 门控内**（`check-qemu-semantics` 只跑 `reg-shift-extend`/`reg-compare`）⇒ **门控保持全绿**、step2 **不阻塞 M5 门槛**。越界路由口径的 **spec 落点**见 `ISS-166`（`Machine-01 §1` 尚未收口，待用户授权；`spec/` 零改动）。教训见 `lessons.md §7.16`、规范见 `§8.10`。
>
> **新增任务 `SPEC-121t`（追加，2026-10-08，承 `ISS-166`）**：`QEMU-049t` 落地 `ADR-0020 D15` 三条机器模型口径（`umon` 段越界 ⇒ `CFXMEM`〔`0x81`〕；其余含 `power` 63 ⇒ `unmapped`〔`0x87`〕；RAM@0 = 16 MiB）后，核 `spec/Machine-01 §1` 发现**未完全覆盖**（占位 `【待 QEMU-049t 定】` / 委派 / `power` 段歧义）⇒ `ISS-166`。新立 **`SPEC-121t`** 承接：`spec/Machine-01 §1` 三处口径**落纸**（用户授权原话「**授权按拟改文本改（推荐）**」）+ 该册**纳入只读锁**（`manifests/spec-readonly.lock.toml` 新增 1 条，锁内 20 → **21**；用户裁定「**把 Machine-01 新增进锁**」）+ `spec/Process-06 §5/§6` 同步（用户裁定「**授权含 Process-06 同步（推荐）**」）；依赖 `QEMU-049t`（已验证；口径来源）+ `SPEC-119t`（锁/门控）；`SPEC-118m` 关联任务 7 → **8**、`INTEG-019k` 任务表/Wave 1 已登记。**本规划步 `spec/` 零改动**（只新建任务书 `SPEC-121t` + 更新台账；`spec/` 改动在 `SPEC-121t` 执行阶段落地）。**〔2026-10-08 范围补正：用户裁定原话 ④「确认两条，按此下发（推荐）」（确认 `Machine-01` 进锁 **20→21** + 授权 `Process-06 §5/§6` 同步）、⑤「并入 SPEC-121t 一并更正」（`check_spec_readonly.py` 输出 / `Makefile` help 的「upstream read-only spec volume(s)」措辞一并更正）——该入锁**语义扩面**（`Process-06` 由「只保护上游 20 册」改为「**含 v5 自定册**」），范围/验收/审阅记录已同步至 `SPEC-121t`。〕**
>
> **✅ `SPEC-121t` 落地（`Machine-01 §1` 越界路由/RAM@0 容量 + 该册入锁 20→21 + `Process-06` 同步；追加，2026-10-08）**：`spec/` 改动**仅** `Machine-01 §1` 三处（§1.1 表 RAM@0「大小」`【待 QEMU-049t 定】`→ **`16 MiB`**；§1.2 **新增「精确路由」条**＝**`umon` 段越界访问/取指 ⇒ `CFXMEM`〔`0x81`〕；其余含旧 `power` 段 63 ⇒ 测试机约定 `unmapped`〔`0x87`〕**；§1.2 末条由「委派」改**落地陈述**）+ `spec/Process-06 §5/§6`（**语义扩面**：由「只保护**上游** 20 册」改为「**含 v5 自定册** `spec/Machine-01`」）。`manifests/spec-readonly.lock.toml` **新增** `Machine-01` 一条（锁 **20→21**；既有 **20 册 `sha256` 逐字未变**）；门控措辞 `check_spec_readonly.py`/`Makefile` 去「upstream」（**逻辑零改动**）；`ISS-166` → `closed`。reviewer **`Accepted`**（证据脚本重跑 `EVIDENCE: PASS`〔B1–B6 非空注入 ⇒ 目标断言 FAIL ⇒ `cp`+md5 还原回绿〕；**独立注入**改真仓库 RAM@0 容量 ⇒ checker **MISMATCH** ⇒ 还原回绿，有鉴别力）、architect 交叉复核通过（独立核 `§1.1`=16 MiB / `§1.2` 新条+末条 / 锁 **21** 且 `Machine-01` `sha256` 相符 / 既有 20 册 `sha256` **逐条未变** / `Process-06 §1` 未改 / checker 去 `upstream` / `check-spec-readonly` `21 … OK` EXIT=0 / `spec/` 变更仅 `Machine-01`〔2 hunk〕+ `Process-06`〔2 hunk〕）。遗留：`Process-06 §1`「上游只读册（清单见 §6）」括注因扩面**字面略不精确**——**授权范围外未改**（建议后续另授权一行措辞修正）。教训见 `lessons.md §7.17`、规范见 `§8.11`。`SPEC-118m` 关联任务含 `SPEC-121t`。

> **✅ `QEMU-045t` 落地（`trap`/`escape` 语义深化验证 + `cfx2rd`/`cfx2rc` 全寄存器面专探针；**无组件补丁改动**；追加，2026-10-08）**：经「`044t`/`045t` 边界处置说明」收缩为「`QEMU-044t` 基线之上**深化/验证 + 专探针**」——`QEMU-044t` 已落 `trap`/`escape`/`cfx2rd`/`cfx2rc` 的 decode→异常流程接线与基础执行，本任务在其基线上**深化并验证完整语义**（`DADAO-12 §1/§3/§4/§5` + `SimRISC-11` + `Toolchain-01` + `contracts/opcodes.yaml`，spec-first），**未发现 044t 基线缺口** ⇒ **无补丁导出**。交付 = 新专探针 `tools/qemu/min_rom_probe_045t.py`（**随产物入库**，**14 用例**）：一般 `trap` 进入向量 + `cause` 帧 / `trap_mask` ⇒ ILLI / reserved ⇒ ILLI；`escape` 正偏移 + **负偏移回退**（18 位有符号、`%4==0`）+ 跨 cfx 禁止 ⇒ ILLI / 跨 cfx 允许 ⇒ 恢复**非复位** `prev_run_mode`/`prev_cfx_mask` + `escape_num`++；`cfx2rd`/`cfx2rc` **cg0–cg7 全寄存器面**（RO/RW、`scratch_regs_num` 边界、cg3 仅 hypv、cfx0↔cfx63 共享，`set.zw`/`or.w` 构造 + 回读）；reserved ⇒ ILLI；不存在组合 ⇒ **CFXREG 4 类**。`make build-qemu`/`make check`（`check-patch-tree` 90 patches、`check-qemu-semantics: PASS`）/`test-codegen`(15/15)/`test-elf`(5/5) EXIT=0；证据脚本 `run.sh` **EVIDENCE: PASS**（6 反例合并注入 ⇒ 8 用例 FAIL ⇒ `cp`+md5 还原 ⇒ **重建** ⇒ 回绿）。reviewer **`Accepted`**（**独立注入** `<<2`→`<<4`，与 A–F 不同、**特异**：只命中 escape 偏移路径 ⇒ 2 用例 FAIL 而 `reserved_illi` 仍 PASS ⇒ `cp`+md5 还原+**重建** ⇒ 14/14，有鉴别力、还原含重建）、architect 交叉复核通过（独立核 `git show 2b49946 --stat` = **2 文件**、`components/qemu/**` **零改动**、`.work/source/qemu` clean、helper.c md5 一致、无 `*.preinject`/`*.orig`/`*.rej`；14 用例**覆盖输出范围** ⇒「未发现基线缺口」有覆盖依据；`spec/` 交集**空**）。**新发现**：① `DADAO-12 §5` 异常退出流程**不恢复 `inner_cfx_code`**（实现与伪代码一致 ⇒ 沉淀 `lessons §7.18`）；② §5 **prose 与伪代码在跨 cfx escape 的措辞张力**（**伪代码为权威**、实现按伪代码 ⇒ 登记 **`ISS-167`**、建议另立 spec 任务，**`spec/` 零改动**；规范 `lessons §8.12`）；③ `ILLI` 观测语义（`cause_id=ILLI` vs exit-port 码 `0x88`）已在完成区说明清楚。遗留：semihosting 短路（`immu18[17:16]==2'b11`）归 `QEMU-046t`。`QEMU-048m` 关联任务含 `QEMU-045t`。

> **✅ `QEMU-046t` 落地（semihosting：译码层短路 + 共享层复用 + 完整 25 服务 + `SYS_EXIT`；追加，2026-10-08）**：`trap cfxHA, immu18` 中 **`immu18[17:16]==2'b11`** ⇒ semihosting（**与 `cfxha` 无关**）——`trans_ctrl.c.inc` 在译码层判 tag 抛内部 `DADAO_EXCP_SEMIHOST`（与 `RISCV_EXCP_SEMIHOST` 同构）⇒ `helper.c` 的 `dadao_cpu_do_interrupt` 短路 `do_common_semihosting(cs)` + `env->pc += 4`（**不进入 cfx 向量**、无 `escape`）。**共享层 `semihosting/arm-compat-semi.c` 零改动复用**；v5 钩子 `target/dadao/common-semi-target.c`（**新增**）：`common_semi_arg(cs,0)=rd16`、`(cs,1)=rb16`、`common_semi_set_ret=rd31`、`is_64bit_semihosting` 恒真、`common_semi_stack_bottom=rb1`。**服务表 = 完整 25 个**（含 `SYSTEM`/`HEAPINFO`/D2 文件档）。**`SYS_EXIT` 取代 exit port**（`ADR-0020 D8`，退出码忠实传 host `$?`）；**exit port 过渡保留**（迁移归 `TESTCASES-034t`）。**越界披露 2 项（最小必要接线）**：① `cpu.c` 新增 `dadao_cpu_translate_for_debug` 接入 `SysemuCPUOps`（缺则共享层经 `cpu_memory_rw_debug` 回退 NULL ⇒ **SIGSEGV**）；② `qemu-options.hx` 两处 `DEF(...)` arch mask 增 `QEMU_ARCH_DADAO`（缺则 CLI 被拒）；另 `Kconfig` `select ARM_COMPATIBLE_SEMIHOSTING if TCG` + `meson.build` 条件编译。探针 `tools/qemu/min_rom_probe_046t.py`（**随产物入库**）**32/32 PASS**（判定两条路 / 钩子 bank〔与 `rd17`·`rb17` 解相关〕/ 25 服务各 ≥1 例 / `SYS_EXIT` 码传播 / 64 位大端参数块 `iserror_be64`）；补丁 **32 → 34**；`make check`（`check-patch-tree` **92 patches**/`check-qemu-semantics` 149/149）/`test-codegen`(15/15)/`test-elf`(5/5) EXIT=0；证据脚本 `run.sh` **EVIDENCE: PASS**（3 反例隔离注入 ⇒ FAIL ⇒ `cp`+md5 还原+**重建** ⇒ 回绿）。reviewer **`Accepted`**（**独立注入** tag 阈值 `0x3`→`0x0` ⇒ 2 用例 FAIL ⇒ `cp`+md5 还原+**重建** ⇒ 32/32，有鉴别力、还原含重建）、architect 交叉复核通过（独立核 tag 门限 / 钩子 bank 逐条 / 32 用例 / 25 服务 / 共享层零 diff / `TARGET_BIG_ENDIAN=1` 证大端 / `check-patch-tree` 92 patches / `.work/source/qemu` clean / `git diff e0f2632..HEAD` 12 文件·`spec/` 交集空）。**新发现**（沉淀 `lessons §7.19`/规范 `§8.13`）：复用上游共享层须同时落地**接入点清单**（`translate_for_debug` / arch mask / Kconfig select / meson 挂钩），「只写钩子」式范围低估。遗留：`D7` harness 默认（`target=gdb`）归 `TESTCASES-034t`/`INTEG-020t`；exit port 迁移归 `TESTCASES-034t`；`SYS_SYSTEM` 已知风险已登记（`ADR-0020 D3/D7`、`Machine-01 §5.6`）。`QEMU-048m` 关联任务含 `QEMU-046t`。
>
> **✅ `QEMU-047t` 落地（新 bootrom：构建 + 链接 + 端到端启动；追加，2026-10-08）**：交付 = 固件源码 `tests/scripts/bootrom.S`（SEE bootrom，自有汇编，`cfx2rc`/`trap`/`escape` 首个真实用户）+ 链接脚本 `tests/scripts/bootrom.lds`（ROM 段 `ORIGIN=0xffff_ffff_0000`/`LENGTH=64K`，越界 `ASSERT`）+ E2E 样例应用 `tests/scripts/bootrom_app.S`（**披露**：raw-bin）+ `Makefile::build-bootrom`（`llvm-mc`+`ld.lld`+`llvm-objcopy`）+ 探针 `tools/qemu/min_rom_probe_047t.py`（**13 用例，随产物入库**）；生成物落 `.dadao/tests/bootrom/`（gitignored，未入库）。**加载模型 = `ADR-0004 D2.3` path B（raw-bin 双镜像）**：bootrom 经 `-bios` 载 ROM 基址、应用 flat bin 经 `-kernel` 载旧 RAM 基址、**栈/数据置 RAM@0**（`QEMU-049t` 双映射）；**复位 PC 不变 `0xffff_ffff_0000`、hypv→user 直跳、本版不启用 supv**（`ADR-0004 R1`/`ADR-0020 D12`）。`llvm-readobj -h -l` → `e_entry`/`PT_LOAD VA` = `0xffff_ffff_0000`（64 KiB ROM 区、`Alignment: 65536`）；探针 **13/13 PASS**（reset PC / **7 项初始化**〔`cfx_umon`/`cfx_power` 向量·`switch_run_mode`·`trap_cfx_mask`·`global_cfx_mask`〕/ hypv→user `MODE=0`/**无 supv**/ 栈在 RAM@0 `rb1=0xf00000` / handler 可达 / E2E `$?=0`）。门控：`check-patch-tree` **92 patches** / `check-qemu-semantics` **149/149** / lit **62/62** / `test-codegen` 15/15 / `test-elf` 5/5 / `make check` EXIT=0；**无组件补丁**（未改 `components/**`）。reviewer **`Accepted`**（**独立注入**移除 `bootrom.S` SP 初始化 ⇒ `stack_in_ram0`/`handler_reached`/`app_exit_0` FAIL ⇒ 还原+重建 ⇒ 13/13，有鉴别力）、architect 交叉复核通过（独立核 `bootrom.lds` `ORIGIN`/`LENGTH`、`llvm-readobj` `e_entry`/`PT_LOAD VA`、`-d cpu` 首块 `PC`、探针 13/13、8 文件·`spec/` 交集空、无 `components/**`；**临时树独立注入** SP 行 ⇒ 3 FAIL + 基线 13/13 回绿）。**方法论偏差（记录并提示）**：reviewer 独立注入的**还原**用 `git show HEAD:<path> > <path>`（从提交读回），**非**项目规定的 `cp` 备份 + md5；本次因目标文件**已提交且工作树未改**未造成损失（md5 相符、还原+重建回绿），但**属偏差**（后续严格用 `cp` 备份；见 `lessons §7.20`/`§8.14`）。**前置风险（`-bios`+ELF 组合缺口，`待用户裁定`）**：本任务选 raw-bin path B，**未实现**「`-bios` bootrom + ELF 应用」组合（`dadao_load_regions[]` 未含 RAM@0、ELF 分支忽略 `-bios`）⇒ 可能为 M5 门槛正向（`make test-semihost`）**前置缺口**；评估/选项/建议（**倾向 A**）见 `INTEG-020t` 审阅记录「architect 前置风险评估」，见上「前置风险（2026-10-08）」条，**待用户裁定**。`QEMU-048m` 关联任务含 `QEMU-047t`。

> **M6 待办（自 M5 范围简化转入；2026-10-08，用户裁定，原话见 `INTEG-019k` §第 8 轮）**：M6 = **「完整调用约定（整数）+ 欠账收口」**（用户 2026-10-07 已定边界），**追加「elf 加载」**。自本 M5 范围简化转入的待办（**含理由**）：
>
> - **「`-bios` bootrom + ELF 应用」组合语义**：定义组合加载/入口约定（复位 PC=`0xffff_ffff_0000` → bootrom 初始化 → 跳 ELF `e_entry`；须定 `e_entry` 传递方式）。**理由**：用户裁定「用 elf 的时候，不需要 bootrom，只需要 semihosting」——「bootrom+bin」与「elf」是**两件分开的事**；M5 只做前者 ⇒ 组合随 M6（与完整 LLVM 任务一并）。
> - **ELF 加载器扩展（`dadao_load_regions[]` + RAM@0）**：现表仅含旧 RAM 段 + ROM、未含 RAM@0。**理由**：随组合语义一并落地（组合路径需 ELF 段落 RAM@0）。
> - **`RAM@0` C1 step2**（旧向量/harness/`crt0`/e2e 迁到 `0` + 删旧 RAM 段 + 收紧 `check-interface` 断言）：原「另立、M5 之外」，现明确**随 M6**。**理由**：用户裁定 step2 随 M6；不阻塞 M5 门槛（step1 双映射保门控全绿）。
> - **组合加载语义的 ADR 决策待定**：**M5 阶段不立 ADR**（推迟 M6）。**理由**：该组合属加载模型/外部契约变更 ⇒ 须 ADR 并**逐条经用户确认**（`AGENTS.md`「ADR decision 逐条确认」），且不在 M5 范围。
> - **登记**：`issues.yaml` `ISS-168`（组合语义 + loader 扩展 + 组合 ADR 待定）+ `ISS-165`（step2；scope 已 `M5→M6`）。

> **口径全局对齐（追加，2026-10-08，architect）**：依已确认的 **`ADR-0020 D9`**，M5「权限反例」口径全局对齐——**M5 可观测 = cfx 级**：`ILLI`〔mask 禁止 / reserved〕、`CFXREG`〔未实现 cfx / 不存在或超数量寄存器组合〕；**`NUPERM/NJPERM/NSPERM/NHPERM` 出自 `DADAO-12 §2.2` PTBR 权限层、不在 M5**。**性质 = 与既定决策的一致性修正，非新增范围。** 本文件 M5 门槛组成 ②（上「门槛」行）已改；同批对齐 `INTEG-019k`（门槛 + 第 2 轮裁定 9 + 审阅记录两处，后二者保留原话加注）、`INTEG-020t`（门槛 + 验收 2）、`INTEG-021m`（核验「权限反例」行）。**`spec/` 零改动。**

> **✅ `TESTCASES-033t` 落地（M5 SEE/semihosting 向量：L1 复用 + L3 m5 bin 10 例 + `run_m5_e2e` + 独立 oracle；追加，2026-10-08）**：L1 MC 向量（`trap`/`escape`/`cfx2rd`/`cfx2rc` 编码/往返）由前置 `LLVM-060t` 自带并已接入 `make check-lit`（62/62，**无 `UNSUPPORTED:`**），本任务**复用**（DRY；`spec/Process-05` 分阶段）。L3 执行向量落 `tests/llvm/codegen/m5/`（**10 条**，承载形态 = **bin**〔用户 2026-10-08 M5 范围简化〕）：semihosting 服务 **5**（`WRITEC`/`WRITE0`/`WRITE`〔=`OPEN`+`WRITE`〕/`EXIT`/`EXIT_EXTENDED`）+ **cfx 级权限反例 4 类**（`ILLI`：reserved/mask；`CFXREG`：unimpl/badcombo）+ 一般 `trap`+`escape` **1**；独立清单 `expected.yaml`（schema `m5-vectors-v1`）+ `README.md` + 对照表 `README-m5.md`。**独立 oracle** `tools/testcases/validate_m5_vectors.py`（**随产物入库**）**141 checks PASS**（服务表从 `contract-semihosting §3` **机械解析 25 条**；cfx 规则/cause 位/token 为**带 contract 引用的硬编码**、与既有范式一致；**无** `subprocess`/`os.system`/`Popen`）。**M5 E2E 驱动** `tools/integ/run_m5_e2e.py`（**随产物入库**）：`llvm-mc`→`llvm-objcopy -O binary`→`qemu -M dadao-m1 -bios <bootrom> -kernel <bin> -semihosting-config …`，逐例核「退出码/控制台/故障码/**bootrom 生效**」**10/10 PASS**；逐例含实际命令行（**全含 `-bios`**）+ `-d cpu` 复位 PC `0xffff_ffff_0000`/bootrom user 向量 `…0200`/`MODE 0`。`make check`/`check-lit`(62/62)/`check-no-residue` EXIT=0；一键证据脚本 `.work/evidence/TESTCASES-033t/run.sh` **`EVIDENCE: PASS`/`SCRIPT_EXIT=0`**（4 类注入各 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿，无 `tee`）。reviewer **`Accepted`**（**独立注入**改 `expected.yaml` 的 `expected_cause` `ILLI`→`CFXREG` ⇒ oracle `manifest-cause` FAIL ⇒ `cp`+md5 还原 ⇒ 141 checks 回绿，有鉴别力；证据脚本审核合格；L3 实跑 10/10；L1 复用；边界无越界），architect 交叉复核通过（独立核 4 指令 L1 复用且无 `UNSUPPORTED:` / oracle 独立性 `grep` 0 命中 / 服务表 25 条机械解析 / **独立注入**改 `expected_console` ⇒ oracle FAIL〔`console-derived`〕⇒ `cp`+md5 还原回绿 / 驱动 10/10 且逐例含 `-bios` / `--inject` 自检 PASS / `git diff f23bcc4..HEAD` **17 文件**·`spec/` 交集空·`.dadao/**`/`.work/**` 未入库）。遗留：`Makefile`/`make test-semihost` 接线归 **`INTEG-020t`**（本任务不改 `Makefile`）；oracle 硬编码部分（带 contract 引用）与既有范式一致性已披露；驱动追加 `chardev` 已披露（任务书「新发现 2」）。教训 `lessons §7.22`、规范 `§8.16`。

> **✅ `TESTCASES-034t` 落地（exit-port → `SYS_EXIT` 全量迁移；追加，2026-10-08）**：把 M1–M4 **全部**依赖 exit-port（MMIO `0xffff_8000_0000`）的向量/harness/oracle 迁到 semihosting `SYS_EXIT`（`ADR-0020 D8` / `ADR-0004 R2`，**默认全迁、例外逐条披露**）：核心退出机制 `tests/scripts/codegen_crt0.s`（`SYS_EXIT` = **64 位大端参数块** `{0x20026, rd31}` + **`rb16`=块指针** + `rd16=0x18` + `trap cfx_umon, 0x30000`）+ `tests/scripts/build_test_binary.py`（`emit_sys_exit`，移除 `EXIT_PORT`/`TEMP_RB`）+ `run_qemu_test.py` + `run_{codegen,elf}_e2e.py`（显式 `-semihosting-config enable=on,target=native`）+ 4 e2e smoke + **16 探针**；**`ISS-147` 结案**（M3 全部 15 条 `expected_exit_code` 收窄 `0x00–0x7F`，7 条掩码 `255→127` + `expected.yaml`/oracle range 收紧 `0..0x7F`）；**`ISS-169`** 登记 **6 探针例外**（`006t` 设备测试 / `009t` OBSOLETE / `008t`·`010t`·`012t`·`013t` 退出与手算 PC 偏移交错 ⇒ 建议另立/随 M6 重写后移除例外）。迁移后门控与改前**逐项相等**：`test-codegen` 15/15 / `test-elf` 5/5 / `check-lit` 62/62 / `check-qemu-semantics` 149/149 / `make check` EXIT=0；26 探针逐条等价。证据脚本 `.work/evidence/TESTCASES-034t/run.sh` **`EVIDENCE: PASS`/`SCRIPT_EXIT=0`**（3 类注入 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿，无 `tee`）。reviewer **`Accepted`**（**独立注入** 2 类有鉴别力：期望值 118→119 ⇒ 14/15 FAIL；`crt0` `0x18→0x19` ⇒ 0/15 FAIL）、architect 交叉复核通过（独立核残留 exit-port **恰 7 文件** / 各门控 rc=0〔`check-interface` 85 项 / `check_issues` 39 open/3 closed〕/ `ISS-120` 未扩大〔改前改后日志逐字节相同〕/ `git diff 783ba9f..HEAD` 46 文件·`spec/` 交集空·未触 `components/**`·`Makefile`）。教训 `lessons §7.23`、规范 `§8.17`。`TESTCASES-035m` 关联任务含 `TESTCASES-034t`。

> **✅ M5 门槛达成（`make test-semihost`；追加，2026-10-08，`INTEG-020t`）**：M5 门控 **`make test-semihost` EXIT=0**（实测 **59s**）——**五组成全绿**：① **正向**（`tools/integ/run_m5_e2e.py`：**bootrom（`-bios`）+ bin 应用**经 `-semihosting`）**10/10**（5 semihosting〔`WRITEC`/`WRITE0`/`WRITE`/`EXIT`/`EXIT_EXTENDED`〕+ 4 cfx 级权限反例 + 1 general trap），**console 逐字节**（`m5_semi_writec`=`41`、`m5_semi_write0`=`4f 4b 0a`，落点 `.dadao/tests/m5-e2e/<stem>.console`）；② **cfx 级权限反例 4/4**（`ILLI`：reserved / mask；`CFXREG`：unimpl / badcombo）；③ **服务表 25/25**（`QEMU-046t` 探针 `tools/qemu/min_rom_probe_046t.py` 全量跑：`[PASS] service coverage: all 25 service ids exercised` / `RESULT: PASS`；`--list` → `distinct service ids covered: 25` / `required service ids: 25`）；④ **不回归**：`test-elf` **5/5** / `test-codegen` **15/15** / `make check`（含 `check-lit` **62/62**、`check-no-residue`）全 EXIT=0（作门控 **make 前置**）；⑤ **INTEG 开闭**登记。**harness stdio 落定**：`-semihosting-config enable=on,target=native,chardev=semi` **由驱动传**（`Makefile` 未重复传，`grep` 0 命中）、console 捕获 = chardev 文件、比对 = 逐字节精确（`run_m5_e2e.py` `console_ok = (console == want)`）。**产出**：`Makefile::test-semihost` + `tools/integ/run_m5_e2e.py`（最小追加 console 捕获比对；**复用、不另建 `run_semihost_e2e.py`**）。**门控组成**：组 ④ 具现为 make **前置**、组 ①+②③ 在 recipe 内捕获 `rc` ⇒ **任一类不符即非零**。**证据路径**：`.work/log/integ/INTEG-020t-test-semihost.log`（+ `-probe.log`/`-test-elf.log`/`-test-codegen.log`/`-check.log`/`-check-lit.log`/`-evidence-run.log`）、`.work/evidence/INTEG-020t/run.sh`。reviewer **`Accepted`**（证据脚本 **27/27** + **独立注入** 改 `tests/llvm/codegen/m5/expected.yaml` 的 `m5_semi_write0` 期望退出码 ⇒ `make test-semihost` **EXIT=2** ⇒ `cp`+md5 还原 ⇒ 回绿，有鉴别力）、architect 交叉复核通过（独立核五组成 / make 前置链与 `rc` 捕获 / `-semihosting-config` 仅驱动传 / console 逐字节与落点 / `spec/` 交集空 / `git diff b26f426..HEAD` **4 文件**）。**新发现**（沉淀 `lessons §7.24` / 规范 `§8.18`）：GNU make recipe 失败返回 **2**（非子命令 1）⇒ 注入判据须 `-ne 0`；「不回归」可作门控**前置链**机械保证；跨模块复用**已验收产物**（`QEMU-046t` 探针承担 25 服务覆盖）的可接受性判据。**本行只标「门槛达成」**——`M5` 项目里程碑置 `达成` 待主会话在**各模块 `m` 均 `里程碑`** 后执行（`spec/Process-04 §1`）。
