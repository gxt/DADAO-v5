# M17 回顾（IDL 可执行参考模型 + 四方差分）

> **达成**：2026-11-27 ｜ **册数**：46（见 `README.md` §1）｜ **关闭 issue**：21（见 `issues-closed.md`）

## 1 目标与范围

- **目标（用户 2026-11-20）**：把 M15 结构化的 `.idl` **跑起来**，作为 IDL / QEMU / gem5 / RTL 四方差分的**参考模型（golden = IDL）**；执行器用 **Python**，不依赖 Ruby/`idlc`。
- **差分底座（用户 2026-11-22）**：`tests/inst` **274** 镜像（Kaiwu-Tiny）；判据 = **签名槽 + 退出码**四方一致；逐指令 trace 只在红后归因；picolibc(fast)/embench 只抽样、不进判据。
- **分阶段**：阶段一非 FP **222** 镜像（`m17-idl-005`–`009`）；阶段二 FP **50** 镜像（`m17-idl-013`）；差异一律归因，清单外差异零红。
- **边界**：多 hart **不在范围**（用户 2026-11-27：不实现、不登记；`ISS-459` 删除）；Linux/`ee-user`/`ee-vast`/arch probes 不在底座。

## 2 实际交付（四阶段）

- **阶段 0：可执行基础（`m17-idl-001`–`004`）**：语法子集 66 类 + 宽度规则 28 条 + 未定义 10 条（263 operation 三处自洽）；Python 解析器（263 全量、拒绝集 13/13、独立 oracle）与 L1 `check-idl-parse`；执行器核心（四寄存器组/ELF/最小 trap，28/28 与 QEMU 最终状态全等）；逐指令 trace 与 QEMU 比对（24790 条记录全等）。
- **阶段 1：非 FP 四方零红（`m17-idl-005`–`012`）**：四方差分驱动与 `check-idl` 进 L2（28 例起步）；补齐访存/寄存器复制/控制流/异常、八元算术与原子、窄位宽 ALU（累计 222 例）；阶段一收口 **222/222 四方零红、pending 0**；`pending` 空集硬断言（`010`，堵静默降覆盖）；IDL 语言语义 U04–U10 补齐（`011`）；脚本归拢 `idl/{tools,data,docs}` + `idl_` 前缀（`012`）。
- **阶段 2：FP 与常驻化（`m17-idl-013`–`019`）**：FP 50 镜像纳入四方（272/272、4539 槽，复用 `idl_fp`）；全四方进 `night-run`（第 9 成员 `idl:four-way` → `make check-idl-full`，L2 仍两方）；manifest `ignore`（`__pycache__`）、spec 生成注记路径、执行器依据锁（263 op + `idl/lib/*.idl` sha，L1）、trace 清单键兼容。
- **阶段 3：收口加固（`m17-idl-020`–`026` + 平台/测试/规范/基础设施册）**：cfx 权限轴 `cfxreg`/`cfxexe` + 两条拒绝路径（272→**274**）；复核遗留清理；trace 跳过集对称化；RegRAS 统一环形缓冲（去搬移）；trace 全 64 槽按值比；入口态 seed cfx 计数/掩码（**274/274**、249995 条）；`expected-divergences` 逐槽例外（`DIV-18`）。同期：ADR-0062 扁平位图与 spec/契约/QEMU/gem5/RTL 落地（spec 7 + 平台 4 册）；`tests/inst` 签名区槽级比对、注释订正、`check-inst-sig` 退役、测试向量去内存实现术语、`stm` 边界、Tiny `escape` 条件化（testcases 7 册）；`check-spec-refs` 章号/前缀加严（infra 2 册）。

## 3 关键裁定（最终口径）

| 主题 | 裁定 |
| --- | --- |
| 权限异常编码 | **ADR-0062 扁平位图**：PTW 权限拒绝只置 `[32..38]`、访存/页缺失只置 `[48..56]`；`CFXPERM` 只表示 cfx 来源掩码、`CFXMEM` 只表示非 PTW 访存；删除 `[39]`/`[57]`，不新增 cause 位；`cause_info` 按 ADR D4 |
| `opcodes.yaml` 维护 | **ADR-0063**：yaml 是机器数据真源、`generate_opcodes.py` 是**唯一写者**；L1 `check-opcodes-repro` 只防漂移；改生成器 → 重跑 → 评审 diff |
| RegRAS 布局 | 四平台统一**环形缓冲**：物理槽 0 = `ra0` 元数据，`1..63` 为数据槽；`phys(i)=1+((base+i)%63)`，`base ∈ 0..62` 隐藏；`call` 推进、`ret` 回退；C1（`RACNT=0`）不推进 base（与 QEMU `ra_phys()` 一致） |
| trace 计数 | 入口态必须 seed 各 cfx 的 `cg4`/`cg15` 计数与掩码；**确定性计数严格相等**，当前无阈值例外；平台缺失寄存器归用例/DIV，不在 trace 里跳过 |
| Tiny `DIV-18` | 用户 2026-11-27 裁定 **1**：不造假常量、不跳过；用例在 Tiny 上验证「访问 ⇒ CFXREG」，`expected-divergences.yaml` 按槽声明 chipyard 期望；其它平台仍按规范值；例外未生效必红 |
| 多 hart | **不在范围**（2026-11-27）：不实现、不登记；将来明确支持时重提 |
| 期望差异清单 | **不建**（2026-11-22）：阶段一 222/222、FP 272/272 实测 0 差异；真出现再立；`DIV-18` 是逐槽例外、不是全局豁免 |

## 4 收尾状态（2026-11-27）

- **任务**：45 册 `已验证` + 本归档册 `里程碑`；M17 台账「待开始 / 进行中」为空。
- **issue**：`closed_in: M17` 共 **21** 条（`issues-m17.yaml` 20 + `issues-left.yaml` 的 `ISS-left-003`）；M17 无 open 项。
- **门控**：`check-idl-full` **274/274 rc=0**；trace **274/274**；L1 `make check` **rc=2**（`check-patch-tree` 52 problem，linux 51/musl 1，`ISS-left-004`）；L3 `make check-full` **rc=2**（`arch` rc=0；`unit:full`/`tset:m6` 的 `stack-protector*.ll` 未归类，`ISS-left-005`）。两处均为既有基线红，非 M17 引入，归档不修。

## 5 门控演进

- `check-idl-parse` 与 `check-idl-exec-anchor` 进 **L1**：前者守 263 operation 可解析，后者锁 op 正文 + `idl/lib/*.idl` sha，改 `.idl` 必须 `--update` 并复核实现。
- `check-idl` 进 **L2**：IDL+QEMU 274 镜像，约 20–40 s；`check-idl-full` 为 **nightly** 成员（全四方），缺引擎/固件 rc=2 可见、不静默跳过。
- `check-opcodes-repro` 进 **L1**：生成器重渲染 == 入库 yaml 逐字节，收口「yaml 单一写者」。
- `check-inst-sig` **退役**：`check-idl` 对每一方都比同一份 `expected.tsv` 且含四方互比，签名槽级比对为超集；保留 `inst-signature-data` 生成器。
- `expected-divergences` 从 `tests/arch` 承载扩展到 `idl_four_way`：只对声明平台/槽生效，其它平台判据不变，未生效即红。

## 6 经验与坑（供后续里程碑复用）

1. **golden 必须独立**：期望值从 `.S`/`spec` 派生，不从 QEMU/gem5/RTL 反推；IDL 自身也要有独立 oracle（解析器 fixture、fp 库 oracle），否则「四方一致」可能是同源自比。
2. **trace 入口态漏 cfx 计数会制造假红**：`escape_ciii_cfx` 第 26 条 `cg4 rc5` exec 0 vs QEMU 1，根因是入口态只 seed `{ip,mode,cfx,banks}`；补 `cfx_regs`（复用 `parse_cfx_regs` 单一真源）后 274/274（`ISS-left-003`）。
3. **环形缓冲必须四平台统一后再比全槽**：搬移/环形混合期只能比有效窗口并做对称剔除；统一为 `1+((base+i)%63)` 后，全 64 槽按值比更强、规则更简单（`m17-idl-023/024`）。
4. **逐槽例外要 fail-closed**：声明值不符、条目未生效、重复登记都判红；否则例外会变成静默逃逸（`m17-idl-026`）。
5. **测试载体也会漂移**：`testcases-005` 去除 `beat`/`拍`/字节通道等内存实现术语，272 镜像 `.text` 零漂移、`expected.tsv` 零变化；改注释/命名后用 md5 对账，不靠「看起来一样」。
6. **归档快照按 `closed_in` 跨分册取集**：本轮 `issues-m17.yaml` 20 条之外，`issues-left.yaml` 还有 `ISS-left-003`（`closed_in: M17`）⇒ 快照 21 条；只删 `issues-m17.yaml` 会漏，必须按 `archive_issues.py` 的全局取集核对。
7. **基线红只记录、不在归档里修**：L1/L3 的 linux/musl 与 `stack-protector*.ll` 均非 M17 面，归档只贴真实 rc 与 issue 指针（`ISS-left-004/005`），避免把归档变成跨里程碑修复。

## 7 遗留（不属 M17 收口阻断）

- `ISS-left-004`（P2）：`check-patch-tree` linux 51 / musl 1 problem，由 linux/musl 侧按 `Process-01` 重导补丁。
- `ISS-left-005`（P3）：L3 `unit:full`/`tset:m6` 的 `stack-protector*.ll` 未归类，由 LLVM 侧归入 include/exclude。
- 三方 cfx 一致性实测与差分收口归 M20（`m20-integ-001/002`）。
