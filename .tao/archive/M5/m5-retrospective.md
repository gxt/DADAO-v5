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
