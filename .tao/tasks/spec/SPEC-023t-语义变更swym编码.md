# SPEC-023t: 语义变更：swym 编码修改

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：`SPEC-014t`
**状态**：已验证

## 问题描述

0.5.3 中，`swym` 指令编码为 `iiii` 格式，`immu24` 为时延参数。0.5.4 修改 swym 的编码格式和立即数位宽。

## 已确认方案（用户 2026-09-27）

- **格式**：从 `iiii` 改为 `oiii`
- **编码位置**：MISC-AMO 中的 `000-010`
- **立即数**：从 `immu24`（24 位）改为 `immu18`（18 位）
- **nop 伪指令**：仍为 `swym 0`，不受影响
- **illi 指令**：维持原样，不受影响

## 变更详情

| 项目 | 0.5.3 | 0.5.4 |
|------|-------|-------|
| 格式 | `iiii` | `oiii` |
| 编码 | MISC-AMO `000-010` | MISC-AMO `000-010`（不变） |
| 立即数 | `immu24`（0..16777215） | `immu18`（0..262143） |
| 时延参数 | N 为 24 位 | N 为 18 位 |
| nop | `swym 0` | `swym 0`（不变） |

## 涉及文件

- `spec/SimRISC-11-其它.md`：更新 swym 的格式描述和立即数位宽
- `spec/SimRISC-00-指令系统设计.md`：如有 swym 的 QFC 表条目，更新格式字段

## 验收标准

1. `spec/SimRISC-11-其它.md` 中 swym 的格式从 `iiii` 改为 `oiii`
2. 立即数从 `immu24` 改为 `immu18`
3. 时延参数说明中的位宽从 24 改为 18
4. nop 伪指令定义不变（`swym 0`）
5. illi 指令未改动
6. 其他内容未改动

## 完成区
**测试结果**：N/A（纯文档修改，无构建/测试步骤）
**修改文件**：
- `spec/SimRISC-11-其它.md`：swym 操作数类型 `iiii`→`oiii`，时延参数位宽 `后24位`→`后18位`
- `spec/SimRISC-00-指令系统设计.md`：QFC 表 swym 条目 `swym-iiii`→`swym-oiii`
**验收结果**：
1. ✅ swym 格式已从 `iiii` 改为 `oiii`（SimRISC-11 第12行）
2. ✅ 立即数位宽已从 24 改为 18（SimRISC-11 第19行：`后18位立即数`）
3. ✅ QFC 表已同步更新（SimRISC-00 第279行：`swym-oiii`）
4. ✅ nop 伪指令定义未变（SimRISC-11 第23-29行：仍为 `swym 0`）
5. ✅ illi 指令未变（SimRISC-11 第31-44行：仍为 `oiii`，后18位立即数）
6. ✅ 其他内容未改动
**新发现/坑**：无
**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收

**审查范围**：`spec/SimRISC-11-其它.md`（全文）、`spec/SimRISC-00-指令系统设计.md`（QFC 主表 + MISC 子表）、对照基线 `spec/SimRISC-0.5.3/SimRISC-04-系统类指令.md` 与 `spec/SimRISC-0.5.3/SimRISC-00-指令系统设计.md`。所有判决基于**本会话自行执行**的命令，未采信完成区叙述。

**重跑记录**（命令 + 真实输出/退出码）

1) 关键行核对
```
$ sed -n '12p;19p;35p' spec/SimRISC-11-其它.md
操作数类型为 `oiii`：
- `swym N` 可作为硬件时延指令，后18位立即数为时延参数：具体时延由硬件实现确定，其时延约为 `swym 0` 的 N+1 倍。
操作数类型为 `oiii`：
```

2) grep 核验（SimRISC-11）
```
$ grep -n "immu24" spec/SimRISC-11-其它.md      → 无命中，exit=1（=0 处）
$ grep -n "oiii"   spec/SimRISC-11-其它.md      → 命中 2 处：第12行(swym)、第35行(illi)
$ grep -n "iiii"   spec/SimRISC-11-其它.md      → 无命中，exit=1（=0 处）
$ grep -n "后24\|24位" spec/SimRISC-11-其它.md  → 无命中，exit=1（=0 处）
```

3) 与 0.5.3 基线逐段 diff（证明「其他内容未改动」）
```
$ diff <(sed -n '5,29p' .../SimRISC-0.5.3/SimRISC-04-系统类指令.md) \
       <(sed -n '6,30p' spec/SimRISC-11-其它.md)
7c7   < 操作数类型为 `iiii`：      > 操作数类型为 `oiii`：
14c14 < …后24位立即数为时延参数   > …后18位立即数为时延参数
（swym 段仅此 2 处，nop 段逐字节一致）
$ diff <(sed -n '31,44p' 0.5.3/SimRISC-04) <(sed -n '31,44p' SimRISC-11)   # illi 段
→ 内容一致（仅切口空行差异）
$ diff <(sed -n '98,169p' 0.5.3/SimRISC-04) <(sed -n '46,116p' SimRISC-11) # 特权指令段
→ 内容一致（仅末行换行差异）
```

4) SimRISC-00 QFC 条目（git 基线对照）
```
$ git diff --stat -- spec/SimRISC-00-指令系统设计.md
 1 file changed, 1 insertion(+), 1 deletion(-)
$ git diff -- spec/SimRISC-00-指令系统设计.md
-| 0111-0xxx | … | ret-riii | swym-iiii |
+| 0111-0xxx | … | ret-riii | swym-oiii |      ← 第279行，唯一改动
$ git show HEAD:spec/SimRISC-00-指令系统设计.md | grep swym → swym-iiii（改前）
```

5) 仓库级检查（确认未破坏结构校验）
```
$ python3 tools/spec/check_qfc_coverage.py
  OK: QFC 表与 opcodes.yaml 双向完全一致
  EXIT=0   （该脚本按 (op,ha) 比对并剥离格式后缀，格式 iiii→oiii 不影响）
$ make check
  validate_vectors: 178/178 M1 identities covered OK
  spec drift check: PASS
  repository checks: PASS
  EXIT=0
```

**反例验证（确认检查方法能检出问题）**
把 SimRISC-11 复制到 `/tmp/opencode/SPEC-023t-review/` 并注入回归（`oiii`→`iiii`、`后18位`→`后24位`）：
```
iiii   命中数 = 2   （检出）
oiii   命中数 = 0   （原为 2，检出）
后24位 命中数 = 1   （检出）
diff 非空 → 注入确实改动了目标文件
```
临时目录已清理（`rm -rf`）。→ grep 判据具备**可达的 FAIL 路径**，非恒 PASS。

**约束核验（逐条）**

| # | 验收标准 | 结论 | 证据 |
|---|---------|------|------|
| 1 | swym 格式 `iiii`→`oiii` | ✅ | SimRISC-11 第12行 `oiii` |
| 2 | 立即数 24→18 | ✅ | 第19行「后18位立即数」；SimRISC-11 `immu24`=0 处 |
| 3 | 时延参数位宽 24→18 | ✅ | 第19行 |
| 4 | nop 伪指令不变（`swym 0`） | ✅ | 第23-29行，与 0.5.3 逐字节一致 |
| 5 | illi 未改动 | ✅ | 第31-44行与 0.5.3 基线逐字节一致 |
| 6 | 其他内容未改动 | ✅ | 分段 diff 仅 2 处预期改动；SimRISC-00 git diff 仅 1 行 |

**完成区数字核对**：完成区所列行号（第12/19/23-29/31-44行、SimRISC-00 第279行）全部与实测一致；无转述失真。

**判决：Accepted**

**待架构师裁定的标注（非阻断本次交付）**

1. **任务书与规范不一致（供架构师核实）**：任务书「已确认方案」称 swym「编码位置：MISC-AMO 中的 `000-010`」。实测不符——swym 实际位于 QFC **主表** `0111-0xxx` 行、列 `x111`（op=0x77，与 `contract-isa.md` L1038 一致）；而 MISC-AMO 子表 `000-010` 单元格为**空**（0.5.3 与当前均如此，`000-000`=illi、`000-001`=fence）。该表述在 0.5.3 即已存在，非本任务引入；验收标准 1–6 不含编码位置，故**不阻断**。建议核实：是任务书措辞有误，还是存在将 swym 迁入 MISC-AMO 的意图（若为后者，需另立任务）。
2. **下游产物遗留旧描述（预期，非本任务范围）**：`.tao/knowledge/contract-isa.md`（§7.1「swym（iiii 格式）」、L835「后 24 位」、L1038 format=`iiii`）、`contracts/opcodes.yaml`（`immu24_b*`）、`docs/assembly-list.md`（`swym | iiii | swym immu24`）、LLVM TableGen（`swym_iiii`/`immu24`）仍为旧编码。任务仅列两个 spec 文件，且 SPEC-012k/024t 明确将 opcodes.yaml 等同步作为后续任务，故属预期遗留，需后续任务处置。
3. **说明（判别力诚实标注）**：验收要点「grep `immu24` 应为 0」在 SimRISC-11 中天然成立（该文件从无 `immu24` 字面量），其真实判别力来自「`oiii` 有命中」+「`后24位` 归零」两条；反例注入已证明后者可失败。