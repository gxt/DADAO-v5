# 项目里程碑

> 只承载**当前进度**；历史见 `.tao/archive/M<1..7>/m<i>-retrospective.md`。
>
> **M7 收尾归档（2026-10-13，`INTEG-035m`）**：M7 期（2026-10-11 ~ 2026-10-13）任务书/回顾/已关 issue **收尾归档**至 `.tao/archive/M7/`（`README.md` / `m7-retrospective.md` / `issues-closed.md`）；**项目里程碑 M7 = 达成**（2026-10-13 口径纠正：`AGENTS.md`「不得置里程碑」**只针对未处置的*跨模块*影响**，`ISS-201` 属 spec **模块内 backlog**、**不阻断** ⇒ `SPEC-136m`/`INTEG-034m` 置 `里程碑`）。**未决项**（`INFRA-071t` **已验证 2026-10-15**；后随 M8 收尾归档入 `.tao/archive/M8/infra/`）见本页「任务流水」。
>
> **M6 达成（2026-10-11，architect 实测核验）**：门槛 `make check` **EXIT=0** + **opt-in** `make test-m6` **EXIT=0**（`check-lit-full` 12/12 + `diff_ir_lli` 19/19 + Embench 38/38）；6 个模块 `m` 全置 `里程碑` ⇒ **项目里程碑 M6 = 达成**。M6 任务书/回顾/已关 issue 已归档至 `.tao/archive/M6/`（回顾 `m6-retrospective.md`、清单 `README.md`、快照 `issues-closed.md`）。核验命令/证据见各 `m`「核验」与 `.work/log/integ/INTEG-026m-*.log`。
>
> **M8 收口归档（2026-10-19，`INTEG-036m`）**：项目里程碑 **M8 = 达成**；M8 期 **68 册**任务书/回顾/**52 条**已关 issue 已归档 `.tao/archive/M8/`（`README.md` / `m8-retrospective.md` / `issues-closed.md`）。本页「任务流水」只保留未归档项（`LLVM-100t` = `M9`；`SPEC-141t` = 只读预研待开工）。


## 体例约定（硬约束）

1. **任务流水用表格**：列 = `| 编号 | 状态 | 完成时间 | 一句改动 |`；**一句改动 ≤120 字符**（中文按 1 字符计）；细节写各任务书，本文只做**索引**（与 `lessons §1.4` 一致）。
2. **按完成时间倒序**（最新在上）；**未完成任务也必须列**，其时间列 = **登记时间**并加注 `（登记）`；同一时间按任务编号升序。
3. **状态以任务书头部「状态」字段为准**；本文与任务书不一致 ⇒ L1 门控 `check-milestones-fresh` 红。
4. **表格之后的当前进度 / M8 规划区 / 状态快照 / M9 规划须随任务与产物同步更新**；计数一律**现场派生**，不写死。

> 机械校验：`make check-milestones-fresh`（L1；状态一致 / 覆盖 / 长度 / 次序 / 格式五断言，`--self-test` 内置五类反例）。

## 项目里程碑

> 项目里程碑（M1–M7 及达成日/主题/成就）见 README.md「项目里程碑」。

**项目里程碑 = M9 达成（2026-10-24）**：核验册 `INTEG-037m`（判据见该册）；本期 67 册 `t` 全验证、终局复跑 0 fail、open issue 11 条（全部 M10 登记项）。

**M6 模块里程碑**（均已 `里程碑`）：`INFRA-052m` / `SPEC-125m` / `LLVM-067m` / `QEMU-054m` / `TESTCASES-040m` / `INTEG-026m`。

**M8 模块里程碑**：仅 **`INTEG-036m`**（整体收敛点，已 `里程碑`，2026-10-19；M8 期未设各模块 `m`，由 68 册任务终态 + 本册判据收敛承担）。

**M7 模块里程碑**（**均 `里程碑`**：`INFRA-072m`/`SPEC-136m`/`LLVM-090m`/`QEMU-059m`/`TESTCASES-043m`/`INTEG-034m`〔整体收敛点〕）：`INFRA-072m` / `SPEC-136m` / `LLVM-090m` / `QEMU-059m` / `TESTCASES-043m` / `INTEG-034m`（整体收敛点）+ `INTEG-035m`（M7 收尾归档，`Process-04`；任务书**已自归档**入 `.tao/archive/M7/integ/`）。

## M10 规划（2026-10-26，用户裁定）

**当前里程碑 = CFX 完善与验证**；**Linux 内核支持推到下一里程碑**（本里程碑不排 Linux 任务）。

**Linux 7.2.10 × 当前 LLVM 兼容性评估**（architect 实测；源码 `.work/source/linux`）：
- 可用：64 位/大端代码生成、原子（LR/SC + fence，1/2/4/8B）、inline asm `r/m/i/n`、`asm goto`（无输出）、builtins（clz/ctz/popcount/bswap/overflow）、section/attribute、TLS、`default`/`large` code model、DWARF、`.S` 宏与 `.rept`、lld 内核式脚本（KEEP/PROVIDE/ALIGN/LONG/QUAD/ASSERT）/高地址/`R_DADAO_ABS48`、`llvm-readelf/nm/objdump/objcopy`。
- 缺口（阻断序）：① `arch/dadao` 不存在（首要）；② 缺 `llvm-ar`/`llvm-ranlib`/`llvm-strip`（`LLVM=1` 直调；GNU ar 可临时顶）；③ `asm goto` + 输出必现 SelectionDAGBuilder 断言（`CC_HAS_ASM_GOTO_OUTPUT` 探针失败）；④ 栈保护无法 lowering（`-mstack-protector-guard=global` 不支持）；⑤ 汇编器拒 `.quad/.long/.short/.byte`（只认 `.dd.*`；`CC_HAS_ASM_GOTO_TIED_OUTPUT` 探针失败）；⑥ inline asm 约束仅 `r/m/i/n`；⑦ `-mcmodel=kernel` 不支持（用 default/large）。
- **兼容性 spike（定义）**：一次性时间盒实验——在 `/tmp/opencode/M10-COMPAT/` 造**丢弃式**最小 `arch/dadao` 桩（仅够 Kconfig/头文件），用现有 clang/lld 编 20–30 个代表性 generic 文件 + Kconfig 探针，产出「编译器缺口 + 规避法」清单；**只做编译/链接、不运行**。与 QEMU **正交**：QEMU 是运行侧（机器模型/启动/设备/MMU），不参与 spike；spike 的桩不是端口交付物。
- **下一里程碑入口判据（建议）**：spike 清单归零或有规避法 + `llvm-ar/ranlib/strip` 就位 + `arch/dadao` 最小骨架能 `make ARCH=dadao` 出 vmlinux。

## 任务流水

> 本表 = **未归档任务流水**（M9 及留活项）；M8 已终态流水（68 条）见 `.tao/archive/M8/README.md §2`，M7 及以前见 `.tao/archive/M*/README.md`。列 = `| 编号 | 状态 | 完成时间 | 一句改动 |`；**按完成时间倒序**（最新在上）；**未完成任务也列**（时间 = **登记时间**，加注 `（登记）`；同一时间按任务编号升序）。**一句改动 ≤120 字符**，只写「做了什么 + 关键数字/结论」；细节一律写各任务书（本表只做索引）。**新立任务（任务书落盘）时即加行**。

> **未完成任务册（现场派生，清单见下）**
> - 缺陷修复批（2026-10-20 立册，`ISS-302`；`LLVM-118t`/`119t`/`120t`、`INFRA-096t`/`INFRA-097t` 已 `已验证`）：`INFRA-098t`（`ISS-261` + `ISS-301`）、`INFRA-099t`（`ISS-229` 门控互斥）、`TESTCASES-053t`（`ISS-270`/`273`/`282`/`288` 陈旧证据脚本族）
> - `SPEC-141t`：`M9` / ISA 扩展预研 —— **结册未执行**（2026-10-21；未定项见下「ISA 扩展预研遗留」）
> - `ADR-0034`（2026-10-20 定案 / 2026-10-21 转正）：原子编码定案（`fence` `0x20`、`lr/sc` 24 条），规范面/合约/生成面已落；**实现 4 册全部 `已验证`**（`ISS-307` `closed`，2026-10-21）
> - **原子链 4 册（`ISS-307`）现状**：① `LLVM-121t`（返工修复 `ISS-312`/`ISS-313`，reviewer 第 3/4 轮 `Accepted`，20 条 XFAIL 已转 PASS）、② `QEMU-067t`、③ `INFRA-100t`、④ `TESTCASES-056t`（reviewer 第 2 轮 `Accepted`；两档 711/711、0 xfail）= **全部 `已验证`** ⇒ `ISS-307` `closed`，`ISS-294` 随 ③/④ 收口。
> - 说明：`M8` 已于 2026-10-19 达成；`LLVM-116t`/`QEMU-064t`/`SPEC-152t` = `已验证`（ISA 链收口）、`INFRA-095t`/`TESTCASES-052t` = `已验证`（线程链 T1/T3 收口，19 目标两档 19/19）；未解 `issue` 见 `issues.yaml`（不在此重复）。

| 编号 | 状态 | 完成时间 | 一句改动 |
| --- | --- | --- | --- |
| LLVM-135t | 已验证 | 2026-10-26 17:27 | cfx 别名运行时表：源码/反汇编共用名字，数据更新不重建 LLVM |
| TESTCASES-067t | 已验证 | 2026-10-26 14:05 | 测试框架调研与 tests 组织方案（主流 ISA 对照 + 生成物 A/B + 确定性） |
| QEMU-076t | 已验证 | 2026-10-26 13:18 | semihosting 调用点迁至 0x3FFxx（QEMU 译码 + bootrom/测试/探针 + picolibc/embench/musl 组件） |
| SPEC-176t | 已验证 | 2026-10-26 11:20 | semihosting 判定迁至 0x3FF00–0x3FFFF（ADR-0038）；HBI INIT 0x30001 解冲突 |
| SPEC-175t | 已验证 | 2026-10-26 09:47 | C1–C11 落实 + 六册发布 0.9.3/0.7.2/0.1.3（去 -rc）+ cfx_timer→cfx_time + HBI 启动移交重写 + 同步不可屏蔽门控 |
| TESTCASES-063t | 已验证 | 2026-10-26 06:45 | harness ret 路由/宽度修正；`ctrl-ret[0..3,8]`、`ctrl-call[5]` 转绿 |
| SPEC-174t | 已验证 | 2026-10-26 05:10 | DADAO 六册自洽性：机械修正 39 行；语义冲突 C1–C11 待裁定 |
| QEMU-075t | 已验证 | 2026-10-26 04:43 | 宿主信号族诊断：三组不同源（VA 耗尽 / 语料 / 未定）；`-R 4G` 可解 OOM 组 |
| INFRA-108t | 已验证 | 2026-10-26 04:23 | PIC libc 归档（`libc_pic.a`）+ 驱动 `-static-pie` 自动选 |
| LLVM-134t | 已验证 | 2026-10-26 03:41 | 去冗余 `ext.so`（6→0）+ ABS48 显示偏移 + cc1as/llvm-mc DWARF64 默认 |
| TESTCASES-064t | 已验证 | 2026-10-26 02:27 | picolibc `%p` 改 `va_arg(void*)`（bank 不匹配）；8 个 printf 变体转绿 |
| LLVM-132t | 已验证 | 2026-10-25 23:08 | fixup 元数据大端修正（`PCREL_HI 14` / `PCREL_LO 20`），`--show-encoding` 不再断言 |
| INFRA-109t | 已验证 | 2026-10-25 20:09 | 归档门控（结构 + `--verify`）移到 `check-milestone`，退出 L1 |
| LLVM-133t | 已验证 | 2026-10-25 19:45 | `cmp.u*` 语义核对（零代码改动）+ `cmp.ut→br.n` lit 断言 |
| TESTCASES-065t | 已验证 | 2026-10-25 19:28 | `cmp.{ut,uw,ub}` 向量期望改为 64 位全 1；生成器同步 + `cmp.ut→br.n` 序列 |
| QEMU-074t | 已验证 | 2026-10-25 18:33 | `cmp.{ut,uw,ub}` 去掉结果零扩展（-1 = 64 位全 1） |
| SPEC-173t | 已验证 | 2026-10-25 17:20 | `cmp.u*` 的 -1 改 64 位全 1；13 册 0.5.6-rc；00 第 255 行去版本号 |
| INFRA-107t | 已验证 | 2026-10-25 16:46 | 补 0.5.3 PROVENANCE 组合 sha + 逐文件表；`--verify` 跳过 `-rc`（ISS-333） |
| LLVM-131t | 已验证 | 2026-10-25 15:56 | 代码模型 default/large：驱动 `-mcmodel` 口径 + large 间接调用序列 + 远距布局用例 |
| INFRA-106t | 已验证 | 2026-10-25 13:48 | 代码跨度门控：REL26/20/14 余量报告 + 单 DSO 可执行区 <30 MiB（L2） |
| LLVM-130t | 已验证 | 2026-10-25 12:15 | 64 位缺省：CodePointerSize/CalleeSaveStackSlotSize=8 + 默认 DWARF64 + 位宽探针 |
| INTEG-037m | 已验证 | 2026-10-25 00:00 | M9 整体核验：67 册全验证、终局复跑 0 fail、open issue 10（M10 登记） |

## 当前进度（2026-10-22）

- **M9 进行中**：进度**只以本页任务流水为准**；细节写各任务书，计数以现场门控输出为准。
- **已收口（本批）**：ISA 链（`rol`）、线程链 T1–T5、原子链 4 册、门控互斥（`INFRA-099t`）、
  `fcls` 位序（`SPEC-156t`/`QEMU-069t`）、`clmul` 4 册、取整 5 册、`min/max`（进行中）。
- **队列**：`min/max` 剩余 → FMA 5 册 → `TESTCASES-057t` → `LLVM-126t` → `TESTCASES-053t` → 终局全量复跑。
- **M8 已归档**（2026-10-19）：`.tao/archive/M8/`（`README.md` / `m8-retrospective.md` / `issues-closed.md`）。
- **计数类口径**（用户 2026-10-22 裁定）：`contract-isa.md` 等分桶计数在**里程碑收尾**统一同步，不随单任务改。

### ISA 候选（`SPEC-141t` 结册）

> 判据（用户 2026-10-21 原话）：**目标应用域能力需求 + 软硬件代价比**；语料频次只回答"今天能否验证"。

- `f16`：**不做**（C23 可选、零语料、硬报错不静默）。
- `mulhu`：**已具备**（`mul.uo` 双目的出全 128 位），撤回候选。
- `fshl`/`fshr`：**保留候选（中）**；后端可先去冗余 mask（实测 9→4 条），将来加指令则 1 条。
- `clmul`：**已定案**（`ADR-0035`，已实现并验证）。
- `crc32c`：**候选（高）**，未立册。
- 未定：`bswap64` 用 `rev.o`；"hw 特化后置"分界（`ADR-0027 D3`）。

## M9（规划）

- 决策载体：`ADR-0030`（`long double`=binary128，排 M9）、`ADR-0031`（变参 ABI）、`ADR-0032`（`rol`，已落）、
  `ADR-0034`（原子）、`ADR-0035`（`clmul`）。
- 实现/排期细则**不在此重复**：见对应任务书与 `issues.yaml`；本段只作导航。
