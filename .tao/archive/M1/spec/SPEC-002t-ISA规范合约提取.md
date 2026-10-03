# SPEC-002t: ISA 规范合约提取

**模块**：spec
**项目里程碑**：M1
**依赖**：无
**状态**：已验证

> **重排说明（2026-09-12）**：spec 重排后本任务状态重置；产出 `contract-isa.md` 需**重新生成**，旧文件暂作参考（见 `.tao/knowledge/deferred.md`）。
> **范围变更（2026-09-12）**：M1 **加入 RA 相关指令**（§4.9 RA 存取/块赋值不再 `Excluded`）；**RF 全部（含存取与运算）仍 `Excluded`**。需重新生成 `contract-isa.md`，把 RA 提取进来。

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：spec/ 规范文档（见下方清单）
- 输出：`.tao/knowledge/contract-isa.md`
- 约束：基于 SimRISC 0.5.3，**M1 范围**（标量整数 + 地址/内存 RD/RB/**RA** + 控制流 + 测试机所需系统/异常）；每条断言标注来源；M1 范围外（浮点 RF 全部 / 特权 cfx / LR-SC 原子等）标 `Excluded from M1`

## 输入文件清单

| 文件 | 用途 |
|------|------|
| `SimRISC-00-指令系统设计.md` | 指令编码设计、QFC 编码表 |
| `SimRISC-01-数据类指令.md` | RD 寄存器组指令语义 |
| `SimRISC-02-地址类指令.md` | RB/RA 寄存器组指令、控制流 |
| `SimRISC-03-浮点类指令.md` | RF 指令语义（**M1 Excluded**，仅用于确认边界） |
| `SimRISC-04-系统类指令.md` | 系统指令 |
| `SimRISC-00-指令系统设计.md` | 指令编码设计、QFC 编码表、数据表示、寄存器模型 |

## 验收标准

1. 版本号为 SimRISC 0.5.3
2. 包含 **M1 所需**章节：
   - §1 寄存器模型
   - §2 指令编码
   - §3 标量整数指令
   - §4 地址/内存指令（RD/RB/**RA**）
   - §5 控制流（含 `call`/`ret`、RegRAS）
   - §7 系统指令中 **M1 所需**（测试机所需 `swym`/`illi`/`fence` 等；**不含**特权 cfx 系统指令）
   - §8 NOP 与保留编码
   - §9 异常总结（MALIGN/ILLI/UNDI/IALIGN/RASOF/RASUF）
   - 附录 A：M1 指令编码清单
   - 附录 B：条件标志参考
3. **M1 范围外**（浮点 RF 全部、特权 cfx 系统指令、LR-SC 原子等）标 `Excluded from M1`，不提取其规范内容
4. 每条规范性断言标注来源 spec/ 章节（如 `[SimRISC-01 §3.5]`）

## 参考

- DADAO-0628：`code-agent/tasks/DL-001a-isa-contract.md`、`DL-001b-spec-revision.md`
- 合约编写规范：`.tao/knowledge/contract-authoring.md`

---

## 完成区

**测试结果**：文档生成任务，无可执行验收命令；以 `/tmp/opencode/SPEC-002t/verify.py`（结构/范围/RA 纳入/来源核对）、`/tmp/opencode/SPEC-002t/crosscheck_encoding.py`（§2.7 QFC 主表 + MISC 子表与 spec 逐条比对）、`/tmp/opencode/SPEC-002t/crosscheck_a1.py`（附录 A.1 op-hex/bits/insn 与 spec QFC 主表逐格比对）核对，三者均 `RESULT: ALL PASS`（退出码 0）。日志：`.tao/logs/SPEC-002t-rework-verify.log`、`.tao/logs/SPEC-002t-rework-encoding-crosscheck.log`、`.tao/logs/SPEC-002t-rework-a1-crosscheck.log`。
**修改文件**：`.tao/knowledge/contract-isa.md`（按 M1 新范围重新生成：RA 进 M1、RF 全部 Excluded；1247 行）
**验收结果**：
  1. ✅ 版本号 SimRISC 0.5.3；M1 章节齐备：§1/§2/§3/§4（RD/RB/**RA**）/§5/§6（浮点 Excluded）/§7（`swym`/`illi`/`fence`）/§8/§9 + 附录 A/B
  2. ✅ **RA 进 M1**：§4.9 提取 `ld.o`/`st.o`/`ldm.o`/`stm.o`（RA，rrii/rrri）与 `ra2rd`/`rd2ra`（orri）的语义/格式/操作数/异常；`set.rd rd, ra` 展开为 `ra2rd`（§3.8）；§1.3.4 ra0–ra63 MemRAS/RegRAS 保留为 M1 语义
  3. ✅ RA 异常：8 字节对齐未对齐 → MALIGN；`ra0` 可读写不触发异常；`immu6 = 0` → ILLI；`raha + immu6 > 64` → ILLI；块赋值 `immu6 = 0`/起始寄存器 + immu6 > 64/`ra2rd` 目的 `rd0` → ILLI（来源标注 `[SimRISC-02 §存取RA寄存器]`/`[SimRISC-02 §寄存器组之间块赋值]`）
  4. ✅ **RF 仍 Excluded**：§6 整体 Excluded；RF 存取（`ld.t-rf`/`st.t-rf`/`ld.o-rf`/`st.o-rf`/`ldm.*-rf`/`stm.*-rf`）、`rf2rd`/`rd2rf`/`set.w`、MISC-RF 浮点运算、FCSR/rf0 指令语义均未提取；rf0 仅在 §1.3.3 保留寄存器模型/位布局/复位值（供 `SPEC-006t`）
  5. ✅ 特权 cfx（trap/escape/cfx2rd/cfx2rc/cfxld/cfxst）与 LR-SC 原子仍标 `Excluded from M1`
  6. ✅ 来源标注齐全：525 处 `[SimRISC-0X §章节名]`，全部落在 SimRISC-00~04；无 DADAO-11/12 引用；不写行号
  7. ✅ 附录 A 编码逐条核对：§2.7 QFC 主表 16 行 diffs=0；MISC 子表 spec 非空 119 条 diffs=0；A.1 op-hex/bits/insn 74 条与 spec 主表逐格 diffs=0（spec 主表非空 97 = A.1 M1 74 + A.7 主表排除 23）
  8. ✅ 附录 A 计数：QFC 主表 M1=74、MISC-octa=29/tetra=26/wyde=26/byte=26/AMO=2、A.7 排除=27；A.7 无 RA 条目、A.1/A.2 含全部 RA 编码
**新发现/坑**：
  - **M1 范围变更（RA）计数变化**：MISC-octa M1 条目 27 → **29**（新增 `rd2ra`=101-101、`ra2rd`=101-110）；A.7 排除清单 33 → **27**（移除 RA 存取 4 行 `0x24`/`0x25`/`0x3C`/`0x3D` 与 RA 块赋值 2 行）；A.1 QFC 主表 M1 行数 70 → **74**。
  - **`ra2rd` 目的 `rd0` → ILLI** 系由 SimRISC-01 通用「目的为 rd0 触发 ILLI」规则推导（SimRISC-02 §寄存器组之间块赋值 未就 RA 重述），已在 §4.9.3 标注来源；`rd2ra` 目的为 RA，无 rd0/rb0 约束。
  - **RA 与 RB 的 0 号寄存器语义相反**：`ra0` 可读写、不触发异常（SimRISC-02 §存取RA寄存器）；`rb0` 只读、为目的 → ILLI。`SPEC-006t` 复位值推导依赖 `ra0`。
  - RA 单/多存取与 RB 同为 8 字节对齐；`immu6` 有效范围 1–63、越界（起始 + immu6 > 64）→ ILLI。
  - 临时脚本 `crosscheck_a1.py` 新增：spec QFC 主表行标签为 8 位（高 5 位 + 低 3 位列索引），比对时需按键归一化；`jump`/`call` 在 A.1 的 insn 列带格式后缀（`jump-iiii`/`call-rrii`），比对前需按格式后缀归一。
  - `rf0`（FCSR）位布局保留在 §1.3.3（`SPEC-006t` 依赖），但 FCSR 指令语义随浮点整体 Excluded。
**遗留问题**：无

---

## 审阅记录

> **说明**：本任务于 2026-09-12 重排后按 M1 范围重新生成产出。重排前的 reviewer 记录针对旧版全文合约（引用 `spec.md`、含浮点 §6），已失效，随本次重新生成移除。
>
> **范围变更（2026-09-12 二次）**：M1 加入 RA 相关指令（§4.9 不再 Excluded），RF 全部（含存取与运算）仍 Excluded。下方「第 1 轮 engineer 自审」「第 1 轮 reviewer 验收」「交叉复核（architect）」均针对**变更前**（RA 未纳入）的 M1 版本，已失效；本轮重新生成后的自审见「第 2 轮 engineer 自审」。

#### 第 1 轮 engineer 自审（自主自审（嵌套受限））

**说明**：本任务为文档生成，改动仅 `.tao/knowledge/contract-isa.md`。按 engineer 规则优先尝试开 `general` subagent 做代码级 review，因嵌套深度受限（返回 `Subagent depth limit reached (1)`），降级为自主自审。

**审查要素**：

| # | 审查项 | 方法 | 结论 |
|---|--------|------|------|
| 1 | 逻辑正确性（语义/操作数顺序/边界） | 对照 spec/ 逐节复核：`add.uo/so`、`sub.uo/so` 进位/借位语义；`cs.eq/cs.ne` 目的为第 3 操作数 `rdhc`；`cmp.uo-rb` 目的为 `rdhb`；`ret` 返回值+弹栈；`rela.si` 左移 12 位；`rd0`/`rb0` 约束；`ldm/stm` 的 `immu6` 范围与 ILLI 条件；RegRAS 压栈/弹栈三分支 | ✅ 与 spec 一致 |
| 2 | 编码正确性 | 附录 A 与 spec QFC 主表/MISC 子表逐条机读比对（`crosscheck_encoding.py`） | ✅ QFC 16 行 diffs=0；MISC 119 条 diffs=0 |
| 3 | 设计/惯用法 | 章节编号、bit 域写法 `[7:0]`、表格风格、来源标注格式统一 | ✅ 一致 |
| 4 | 防造假 | 核对命令真实执行、日志落盘、退出码 | ✅ 真实（`ALL PASS`，日志见完成区） |
| 5 | 范围正确性 | 检查浮点/cfx/LR-SC/RA 内容仅出现在 Excluded 段落；正文无其规范语义 | ✅ 通过 |

**finding 处置表**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| §2.7 QFC 表用 `⛔`、§1.1 用 `✅`（违反"不主动加 emoji"约定） | ✅已修 | 替换为文字标记 `Excl.` 与 `是`，并更新图例 | emoji 扫描：no emoji found；`verify.py` 复跑 ALL PASS |
| §3.8 `set.rd rdxx, rs` 列为 M1，但其 `ra2rd`/`rf2rd` 展开属 Excluded，边界不清 | ✅已修 | 表格说明与注脚明确"M1 仅 rb/rd 源；rf/ra 源 Excluded" | `verify.py` 复跑 ALL PASS |
| 附录 B.3 措辞笔误"（rb 无条件赋值对应指令）" | ✅已修 | 改为"（rb 无对应的条件赋值指令）" | 复读确认 |
| 校验脚本自身 3 处误报（`§<数字>` 匹配到章节标题；附录 A 行数期望误算） | ✅已修（脚本，非产出） | 修正引用正则与行数期望（QFC 70、A.7 33、MISC 27/26/26/26/2） | `verify.py` 复跑 `RESULT: ALL PASS` |

**判决**：产出无未修 finding，满足全部验收标准，状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**审查方法**：独立重跑验收命令 + 人工抽查语义/编码/来源。

**重跑记录**：

| 命令 | 退出码 | 日志 |
|------|--------|------|
| `python3 /tmp/opencode/SPEC-002t/verify.py` | 0 | `/tmp/opencode/SPEC-002t-review/verify-final.log` |
| `python3 /tmp/opencode/SPEC-002t/crosscheck_encoding.py` | 0 | `/tmp/opencode/SPEC-002t-review/encoding-crosscheck-final.log` |

**verify.py 真实输出**（退出码 0）：
```
file lines = 1212
file bytes = 73091
PASS 版本号为 SimRISC 0.5.3
PASS 章节存在: ## §1 寄存器模型
PASS 章节存在: ## §2 指令编码
PASS 章节存在: ## §3 标量整数指令
PASS 章节存在: ## §4 地址/内存指令（RD/RB）
PASS 章节存在: ## §5 控制流
PASS 章节存在: ## §6 浮点指令 — Excluded from M1
PASS 章节存在: ## §7 系统指令（M1 所需）
PASS 章节存在: ## §8 NOP 与保留编码
PASS 章节存在: ## §9 异常总结
PASS 章节存在: ## 附录 A：M1 指令编码清单
PASS 章节存在: ## 附录 B：条件标志参考
PASS 存在 Excluded from M1 标记（浮点 边界）
PASS 存在 Excluded from M1 标记（特权 cfx 边界）
PASS 存在 Excluded from M1 标记（LR-SC 边界）
PASS 存在 Excluded from M1 标记（RA 寄存器存取 边界）
PASS Excluded from M1 出现 27 次 (>=6)
PASS 来源引用条数 = 514 (>100)
PASS 所有 SimRISC 引用在 00-04 范围内 (异常: [])
PASS 无 DADAO-11 引用
PASS 无 DADAO-12 引用
PASS 引用使用章节名而非编号/行号 (异常: [])
PASS 头部声明不写行号
PASS SimRISC-03 仅用于确认浮点边界
PASS §9 异常覆盖: ILLI
PASS §9 异常覆盖: MALIGN
PASS §9 异常覆盖: UNDI
PASS §9 异常覆盖: IALIGN
PASS §9 异常覆盖: RASOF
PASS §9 异常覆盖: RASUF
PASS CFXREG 标注为排除
附录 A：QFC 主表 M1=70；MISC-octa=27 tetra=26 wyde=26 byte=26 AMO=2；排除清单=33
PASS QFC 主表 M1 行数 = 70 (期望 70)
PASS MISC M1 行数 = (27, 26, 26, 26, 2) (期望 (27,26,26,26,2))
PASS A.7 排除清单行数 = 33 (期望 33)
PASS M1 事实存在: rd0 固定为 0
PASS M1 事实存在: rb0 为 PC
PASS M1 事实存在: ra63 栈顶
PASS M1 事实存在: 大端序
PASS M1 事实存在: RASOF 精确异常
PASS M1 事实存在: MALIGN 对齐
PASS M1 事实存在: ret rd0, 0
PASS M1 事实存在: call 压栈
PASS M1 事实存在: swym 0
PASS M1 事实存在: illi 全零
PASS M1 事实存在: fence 屏障位
PASS M1 事实存在: rela.si 左移 12
PASS M1 事实存在: immu6 1-63
RESULT: ALL PASS
```

**crosscheck_encoding.py 真实输出**（退出码 0）：
```
QFC 主表：spec 16 行 / contract 16 行，diffs=0
MISC 子表：spec 非空条目 119，M1 比对 diffs=0（排除 LR-SC / RA / RF）
RESULT: ALL PASS
```

**约束核验**：

| 约束 | 结论 | 证据 |
|------|------|------|
| 版本 0.5.3 | ✅ | 文件头 `> **版本：0.5.3** [SimRISC-00 §版本]` |
| M1 章节齐备（§1/2/3/4/5/7/8/9 + 附录 A/B） | ✅ | verify.py 全部 PASS |
| §6 浮点标 Excluded 且未提取规范内容 | ✅ | §6 仅含名称/边界说明，无编码/语义详情；`Excluded from M1` 在标题 |
| 特权 cfx 标 Excluded | ✅ | §7.5 + A.7 排除清单；cfx 指令仅在 Excluded 上下文中出现 |
| LR-SC 原子标 Excluded | ✅ | §7.4 + A.7 排除清单；LR-SC 仅在 Excluded 上下文中出现 |
| 来源标注 `[SimRISC-0X §章节名]` | ✅ | 514 处引用，全部在 SimRISC-00~04 范围内 |
| 无 DADAO-11/12 误引 | ✅ | verify.py 扫描通过 |
| 无行号引用 | ✅ | verify.py 扫描通过 |
| QFC 主表编码正确 | ✅ | crosscheck_encoding.py diffs=0 |
| MISC 子表编码正确 | ✅ | crosscheck_encoding.py diffs=0（119 条比对） |

**独立语义抽查**（人工复核 spec/ 原文）：

| 指令 | 核对内容 | 结论 |
|------|---------|------|
| `add.so` | SX 至 128 位，`rdha:rdhb = rdhc + rdhd`，`rdha` 为高 64 位 | ✅ 与 spec SimRISC-01 §加减操作一致 |
| `sub.uo` | ZX 至 128 位，`rdha` 为借位（0 或 1） | ✅ 一致 |
| `cs.eq`/`cs.ne` | 条件赋值，目的为第 3 操作数 `rdhc`；RF 变体 Excluded | ✅ 一致 |
| `cmp` | 比较结果 −1/0/1 写入目的全 64 位 | ✅ 与 spec SimRISC-01 §比较操作一致 |
| `ret` | 从 `ra63` 弹栈，支持返回值赋值 `rdha, imms18` | ✅ 与 spec SimRISC-02 §函数返回一致 |
| `rela.si` | 18 位有符号立即数左移 12 位 + PC 低 12 位清零 | ✅ 与 spec SimRISC-02 §PC相对寻址一致 |
| `call` | 压栈 ra63，高 16 位引用计数，低 48 位返回地址 | ✅ 与 spec SimRISC-02 §函数调用一致 |
| `ldm`/`stm` | immu6 有效范围 1–63，rd0/immu6=0/越界→ILLI | ✅ 与 spec SimRISC-01 §存取RD寄存器一致 |
| rd0 约束 | 固定为 0，只读；rrrr 允许一个为 rd0 | ✅ 与 spec SimRISC-00 §数据寄存器 + SimRISC-01 §rd0 为目的寄存器约定一致 |
| rb0 约束 | 为 PC，只读；显式目的→ILLI | ✅ 与 spec SimRISC-00 §基址寄存器 + SimRISC-02 §rb0 为目的寄存器约定一致 |
| RegRAS | ra1–ra63 构成，ra63 栈顶，压栈/弹栈三分支 | ✅ 与 spec SimRISC-00 §返回地址栈一致 |
| 端序 | 大端序 | ✅ 与 spec SimRISC-00 §指令设计一致 |
| fence | 低 4 位屏障类型，bits[17:4] SBZ | ✅ 与 spec SimRISC-04 §fence指令一致 |

**git status 核验**：
```
 modified:   .tao/knowledge/contract-isa.md
 modified:   ".tao/tasks/spec/SPEC-002t-ISA规范合约提取.md"
```
仅交付物 + 任务文件变动，无意外文件。

**与完成区自审结论的差异**：无差异。自审结论准确，独立重跑全部通过。

**判决**：**Accepted** — 验收命令块在独立重跑下全部通过（退出码 0），M1 范围齐备，Excluded 边界正确，来源标注/编码/语义经抽查与 spec 一致。

### 交叉复核（architect）

**复核者**：architect
**时间**：2026-09-12
**结论**：确认 reviewer 的 **Accepted**；交付物满足任务书全部验收标准与约束。

**独立核对**：重跑 `verify.py`/`crosscheck_encoding.py`（ALL PASS）；自建脚本补核**附录 A.1 的 op-hex 列与 A.7 主表排除项**（spec QFC 主表非空 97 = A.1 M1 70 + A.7 排除 27，逐条匹配；MISC spec 非空 119 = A.2 27 + A.3 26 + A.4 26 + A.5 26 + A.6 2 + 排除 12）；人工对照 spec 抽查 `add/sub/mul/div/cs.*/cmp/ld-st 对齐/ldm-stm/rela.si/call/ret/§5.6/rf0/fence/§9` 均一致；范围判定合理（`rf0` 保留 §1 必要——`SPEC-006t` 复位值依赖；RA 显式存取排除不影响 `call`/`ret`）。

**补充发现（非交付物）**：

- 审阅记录（第 197 行）笔误：`cs.eq`/`cs.ne` 的目的应为第 3 操作数 `rdhc`（交付物 §3.5 正确）——已更正记录。
- reviewer 自建 `crosscheck_v2.py` 有误报（字典重复/表头误判），未用于验收依据，建议后续清理。

**统一判决**：**Accepted**。

---

#### 第 2 轮 engineer 自审（自主自审（嵌套受限））

**说明**：本轮为 **M1 范围变更返工**（RA 进 M1、RF 全部仍 Excluded）。按 engineer 规则优先尝试开 `general` subagent 做代码级 review，因嵌套深度受限（返回 `Subagent depth limit reached (1)`），降级为自主自审。

**审查要素**：

| # | 审查项 | 方法 | 结论 |
|---|--------|------|------|
| 1 | RA 语义正确性 | 对照 `SimRISC-02 §存取RA寄存器` / `§寄存器组之间块赋值` 逐条复核 §4.9 的操作数顺序、语义、异常 | ✅ 一致 |
| 2 | RA 编码正确性 | `crosscheck_a1.py` 独立核对 A.1 op-hex/bits/insn 与 spec QFC 主表逐格 | ✅ 74 条 diffs=0 |
| 3 | 边界正确性 | 扫描 RA 是否仍 Excluded、RF/cfx/LR-SC 是否仍 Excluded 且未提取规范语义 | ✅ RA 无 Excluded；RF/cfx/LR-SC 均 Excluded |
| 4 | 来源标注 | 引用 525 处全在 SimRISC-00~04；无行号、无 DADAO-11/12 | ✅ 通过 |
| 5 | 防造假 | 三个核对脚本真实执行、日志落盘、退出码 0 | ✅ 真实 |

**finding 处置表**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| §4.9.2 多存取未列「`raha` 为 `ra0` 不触发异常」（spec 对 4 条 RA 存取为集合约束） | ✅已修 | §4.9.2 异常条件补 `ra0` 可读写 | `verify.py` 复跑 ALL PASS（`.tao/logs/SPEC-002t-rework-verify.log`） |
| 自建 `crosscheck_a1.py` 两处解析 bug（spec 行只取 4 位高位、8 位 op 键含连字符未归一） | ✅已修（脚本，非产出） | 修正行标签取高 5 位、op 键去连字符、`jump`/`call` 按格式后缀归一 | 复跑 `A.1 diffs=0`（`.tao/logs/SPEC-002t-rework-a1-crosscheck.log`） |

**判决**：产出无未修 finding，满足全部验收标准，状态置 `待验收`。

#### 第 2 轮 reviewer 验收

**审查方法**：独立重跑三个验收脚本 + 人工对照 spec 原文逐条核验 RA 语义/编码/异常 + 范围边界检查。

**重跑记录**：

| 命令 | 退出码 | 日志 |
|------|--------|------|
| `python3 /tmp/opencode/SPEC-002t/verify.py` | 0 | `/tmp/opencode/SPEC-002t-review2/verify.log` |
| `python3 /tmp/opencode/SPEC-002t/crosscheck_encoding.py` | 0 | `/tmp/opencode/SPEC-002t-review2/encoding-crosscheck.log` |
| `python3 /tmp/opencode/SPEC-002t/crosscheck_a1.py` | 0 | `/tmp/opencode/SPEC-002t-review2/a1-crosscheck.log` |

**verify.py 真实输出**（退出码 0）：
```
file lines = 1247
file bytes = 75130
PASS 版本号为 SimRISC 0.5.3
PASS 章节存在: ## §1 寄存器模型
PASS 章节存在: ## §2 指令编码
PASS 章节存在: ## §3 标量整数指令
PASS 章节存在: ## §4 地址/内存指令（RD/RB/RA）
PASS 章节存在: ## §5 控制流
PASS 章节存在: ## §6 浮点指令 — Excluded from M1
PASS 章节存在: ## §7 系统指令（M1 所需）
PASS 章节存在: ## §8 NOP 与保留编码
PASS 章节存在: ## §9 异常总结
PASS 章节存在: ## 附录 A：M1 指令编码清单
PASS 章节存在: ## 附录 B：条件标志参考
PASS 存在 Excluded from M1 标记（浮点 RF 边界）
PASS RF 存取与运算标 Excluded
PASS MISC-RF 子表标 Excluded
PASS 特权 cfx 标 Excluded
PASS LR-SC 标 Excluded
PASS Excluded from M1 出现 20 次 (>=6)
PASS RA 在 M1: RA 单存取 ld.o
PASS RA 在 M1: RA 单存取 st.o
PASS RA 在 M1: RA 多存取 ldm.o
PASS RA 在 M1: RA 多存取 stm.o
PASS RA 在 M1: RA 块赋值 ra2rd
PASS RA 在 M1: RA 块赋值 rd2ra
PASS §4.9 标题为 M1 规范内容（无 Excluded 后缀）
PASS 头部/正文不再把 RA 列为 M1 范围外
PASS RA 不再标 Excluded
PASS RA ra0 可读写（不触发异常）
PASS RA 越界 ILLI 条件存在
PASS 来源引用条数 = 525 (>100)
PASS 所有 SimRISC 引用在 00-04 范围内 (异常: [])
PASS 无 DADAO-11 引用
PASS 无 DADAO-12 引用
PASS 引用使用章节名而非编号/行号 (异常: [])
PASS 头部声明不写行号
PASS SimRISC-03 仅用于确认浮点边界
PASS §9 异常覆盖: ILLI
PASS §9 异常覆盖: MALIGN
PASS §9 异常覆盖: UNDI
PASS §9 异常覆盖: IALIGN
PASS §9 异常覆盖: RASOF
PASS §9 异常覆盖: RASUF
PASS CFXREG 标注为排除
附录 A：QFC 主表 M1=74；MISC-octa=29 tetra=26 wyde=26 byte=26 AMO=2；排除清单=27
PASS QFC 主表 M1 行数 = 74 (期望 74)
PASS MISC M1 行数 = (29, 26, 26, 26, 2) (期望 (29,26,26,26,2))
PASS A.7 排除清单行数 = 27 (期望 27)
PASS A.7 无 RA 存取排除项
PASS A.7 无 RA 块赋值排除项
PASS A.1 含 RA 编码 0x24
PASS A.1 含 RA 编码 0x25
PASS A.1 含 RA 编码 0x3C
PASS A.1 含 RA 编码 0x3D
PASS A.2 含 rd2ra(101-101)/ra2rd(101-110)
PASS M1 事实存在: rd0 固定为 0
PASS M1 事实存在: rb0 为 PC
PASS M1 事实存在: ra63 栈顶
PASS M1 事实存在: 大端序
PASS M1 事实存在: RASOF 精确异常
PASS M1 事实存在: MALIGN 对齐
PASS M1 事实存在: ret rd0, 0
PASS M1 事实存在: call 压栈
PASS M1 事实存在: swym 0
PASS M1 事实存在: illi 全零
PASS M1 事实存在: fence 屏障位
PASS M1 事实存在: rela.si 左移 12
PASS M1 事实存在: immu6 1-63
PASS M1 事实存在: set.rd ra 源
RESULT: ALL PASS
```

**crosscheck_encoding.py 真实输出**（退出码 0）：
```
QFC 主表：spec 16 行 / contract 16 行，diffs=0
MISC 子表：spec 非空条目 119，M1 比对 diffs=0（排除 LR-SC / RF）
RESULT: ALL PASS
```

**crosscheck_a1.py 真实输出**（退出码 0）：
```
A.1：contract 条目 74；spec 非空主表条目 97；diffs=0
RESULT: ALL PASS
```

**约束核验**：

| # | 约束 | 结论 | 证据 |
|---|------|------|------|
| 1 | 版本 0.5.3 | ✅ | 文件头 `> **版本：0.5.3** [SimRISC-00 §版本]` |
| 2 | M1 章节齐备（§1/2/3/4/5/7/8/9 + 附录 A/B） | ✅ | verify.py 全部 PASS（§4 标题含 RA） |
| 3 | RA 进 M1：§4.9 不再 Excluded | ✅ | §4.9 标题无 Excluded 后缀；6 条 RA 指令语义完整提取；A.1 含 0x24/0x25/0x3C/0x3D；A.2 含 101-101/101-110；A.7 无 RA 条目 |
| 4 | RA 语义与 spec 一致 | ✅ | 人工逐条对照 SimRISC-02 §存取RA寄存器（4 条）+ §寄存器组之间块赋值（2 条），操作数顺序/语义/异常条件一致（详见下方独立语义抽查） |
| 5 | RF 全部仍 Excluded | ✅ | §6 整体 Excluded；RF 存取/运算/FCSR 指令语义未提取；rf0 仅 §1.3.3 保留寄存器模型/位布局/复位值 |
| 6 | 特权 cfx 仍 Excluded | ✅ | §7.5 + A.7 含 6 条 cfx 指令（cfx2rd/cfx2rc/cfxld/cfxst/escape/trap） |
| 7 | LR-SC 仍 Excluded | ✅ | §7.4 + A.7 含 8 条 lr/sc 条目（010-xxx/011-xxx） |
| 8 | §1.3.4 ra0-ra63 MemRAS/RegRAS 在 M1 | ✅ | §1.3.4 完整保留 ra0-ra63 寄存器模型、RegRAS/MemRAS 结构、压栈弹栈三分支语义 |
| 9 | rf0 仅 §1.3.3 保留 | ✅ | §1.3.3 仅保留位布局/复位值（供 SPEC-006t）；指令语义标 Excluded |
| 10 | 来源标注 `[SimRISC-0X §章节名]` | ✅ | 525 处引用，全部在 SimRISC-00~04；无行号；无 DADAO-11/12 |
| 11 | QFC 主表编码正确 | ✅ | crosscheck_encoding.py diffs=0（16 行） |
| 12 | MISC 子表编码正确 | ✅ | crosscheck_encoding.py diffs=0（119 条） |
| 13 | A.1 op-hex/bits/insn 与 spec 主表一致 | ✅ | crosscheck_a1.py diffs=0（74 条 vs spec 97 条非空） |
| 14 | 附录 A 计数：QFC M1=74、MISC-octa=29/tetra=26/wyde=26/byte=26/AMO=2、A.7=27 | ✅ | verify.py PASS；A.7 分类：RF 存取 8 + 浮点 9 + 特权 cfx 6 + RF 块赋值 2 + LR-SC 2 = 27 |
| 15 | git status 仅交付物 + 任务文件 | ✅ | `modified: .tao/knowledge/contract-isa.md` + `modified: .tao/tasks/spec/SPEC-002t-ISA规范合约提取.md` |

**独立语义抽查**（人工对照 spec SimRISC-02 原文）：

| 指令 | spec 来源 | 合约 §4.9 内容 | 核对 |
|------|----------|---------------|------|
| `ld.o raha, rbhb, imms12` | SimRISC-02 §存取RA寄存器 | `raha = mem64[rbhb + imms12]` | ✅ 一致 |
| `st.o raha, rbhb, imms12` | SimRISC-02 §存取RA寄存器 | `mem64[rbhb + imms12] = raha` | ✅ 一致 |
| `ldm.o raha, rbhb, rdhc, immu6` | SimRISC-02 §存取RA寄存器 | 多寄存器加载（连续 RA） | ✅ 一致 |
| `stm.o raha, rbhb, rdhc, immu6` | SimRISC-02 §存取RA寄存器 | 多寄存器存储（连续 RA） | ✅ 一致 |
| `ra2rd rdhb, rahc, immu6` | SimRISC-02 §寄存器组之间块赋值 | RA→RD 块复制 | ✅ 一致 |
| `rd2ra rahb, rdhc, immu6` | SimRISC-02 §寄存器组之间块赋值 | RD→RA 块复制 | ✅ 一致 |
| RA 8 字节对齐 → MALIGN | spec: "均需8字节地址对齐，未对齐触发MALIGN异常" | §4.9.1/§4.9.2 均列出 | ✅ 一致 |
| `ra0` 可读写 | spec: "`raha`为`ra0`时不触发异常（ra0可读写）" | §4.9.1/§4.9.2 均列出 | ✅ 一致 |
| `immu6=0` → ILLI | spec: "`immu6`=0时触发ILLI异常" | §4.9.2/§4.9.3 均列出 | ✅ 一致 |
| `raha+immu6>64` → ILLI | spec: "`raha+immu6>64`时触发ILLI异常" | §4.9.2 列出 | ✅ 一致 |
| 任一起始+immu6>64 → ILLI | spec: "任一起始寄存器+immu6>64时触发ILLI异常" | §4.9.3 列出 | ✅ 一致 |
| `ra2rd` 目的 `rd0` → ILLI | spec 通用规则：目的为 rd0 触发 ILLI（§1.3.1） | §4.9.3 标注来源 [SimRISC-01 §rd0 为目的寄存器约定] | ✅ 合理推导，来源已标注 |
| rb/rf/ra 之间不能直接赋值 | spec: "rb/rf/ra之间不能进行直接赋值，ra与ra之间不能相互赋值" | §4.9.3 复述 | ✅ 一致 |
| `ra1-ra63` 构成 RegRAS，`ra63` 栈顶 | spec §返回地址栈 | §1.3.4 完整保留 | ✅ 一致 |
| `ra0` MemRAS 引用计数/指针 | spec §返回地址栈 | §1.3.4 完整保留 | ✅ 一致 |

**附录 A 编码抽查**（人工核对 spec QFC 主表 + MISC-octa 子表）：

| 编码 | contract 条目 | spec QFC 对应 | 核对 |
|------|--------------|--------------|------|
| 0x24 (0010-0100) | ld.o-ra, rrii | QFC 表 row 0010-0xxx col 100 = ld.o-ra | ✅ |
| 0x25 (0010-0101) | st.o-ra, rrii | QFC 表 row 0010-0xxx col 101 = st.o-ra | ✅ |
| 0x3C (0011-1100) | ldm.o-ra, rrri | QFC 表 row 0011-1xxx col 100 = ldm.o-ra | ✅ |
| 0x3D (0011-1101) | stm.o-ra, rrri | QFC 表 row 0011-1xxx col 101 = stm.o-ra | ✅ |
| MISC-octa 101-101 | rd2ra, orri | spec MISC-octa 表 101-101 = rd2ra | ✅ |
| MISC-octa 101-110 | ra2rd, orri | spec MISC-octa 表 101-110 = ra2rd | ✅ |

**与完成区自审结论的差异**：

无实质性差异。自审结论准确。唯一注意点：verify.py 报告 "Excluded from M1 出现 20 次"，而第 1 轮 reviewer 记录为 27 次——差异因 RA 相关条目从 Excluded 移至 M1 所致（旧版 A.7 排除清单 33 行含 6 条 RA，新版 27 行不含 RA；QFC 主表中 RA 相关 Excl. 标记也已移除），计数正确。

**判决**：**Accepted** — 三个验收脚本在独立重跑下全部通过（退出码 0），RA 指令语义/编码/异常经人工逐条对照 spec 一致，RF/cfx/LR-SC 仍 Excluded，§1.3.4 ra0-ra63 模型完整保留，附录 A 编码与 QFC/MISC 表逐条匹配，git status 仅含交付物与任务文件。

### 交叉复核（architect，返工后）

**复核者**：architect
**时间**：2026-09-12
**结论**：确认 reviewer 的 **Accepted**；交付物满足范围变更后的全部验收标准。

**独立核对**：自建覆盖性脚本断言「spec 非空 = M1 ∪ 排除」且不相交（主表 97 = A.1 74 + A.7 23；MISC 各子表均配平）；RA 4 条存取在 A.1 不在 A.7、`rd2ra`/`ra2rd` 在 A.2、RF/cfx/LR-SC 全在 A.7；复跑 verify/crosscheck 脚本 ALL PASS；语义逐条对照 `spec/SimRISC-02 §存取RA寄存器`/§寄存器组之间块赋值 一致；来源 525 处无行号。

**补充发现（非阻断，已顺手修正）**：

1. §4.9.3 的 `ra2rd` 目的 rd0 → ILLI 来源补 `[SimRISC-00 §数据寄存器][SimRISC-01 §rd0 为目的寄存器约定]`；§9.1 同步。
2. `§各类操作对高 16 位（bits[63:48]）的处理规则` 与 spec 原文措辞对齐（3 处）。

**统一判决**：**Accepted**。
