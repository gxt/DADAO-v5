# SPEC-191t: 退出码旧码残留清理（ADR/DDLN/Machine-00）

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-187t`（已验证；Machine-v5 三段退出码表、ADR-0004 D5.8 指针化）
**状态**：已验证

## 执行环境
本地；只清理旧退出码字面，不改决策语义；ADR decision 改动须用户逐条确认。

## 用户裁定（2026-11-05，逐项）

> 「A：`ADR-0004` 所有活 decision 文本（D1/D3/D4/D5.1–D5.6/D6.2/D6.3/Rationale/Consequences）的旧退出码字面指针化；`## 修订` 历史段不改。」
> 「A：`ADR-0009` 表删除旧码列，改指针；`ADR-0041` D7/D10 的 `PTWERR` 改为 `CFXMEM` 当前 monitor + 指针；两册 `## 修订` 历史段不改。」
> 「A：DDLN `D-D002`/`TT-D002` Q4 按新模型改写（不再区分 CFXMEM/unmapped）；`Machine-00` 的 `0x81–0x8D` 改三段式描述；不改规范语义。」
> 「无需另立任务，原地修订 `ADR-0009 D5`。」（2026-11-05，用户原话）
> 「A：`ADR-0004 D3` 与 Consequences 原地修订为三段式 guest 分区；`## 修订` 历史段不改。」（2026-11-05）

## 背景

`SPEC-187t` 已把 `Machine-v5 §1.2` 改为完整三段表，`ADR-0004 D5.8` 指针化。但以下地方仍有旧码字面：

- `ADR-0004` 其它 decision：
  - D1 / D3 / D4 / D6.2 / D6.3 / Rationale / Consequences 仍有 `0x87`/`0x88`/`0x8C` 等旧码
- `docs/DDLN/D-运行平台/DD-D002` 与 `TT-D002`
- `docs/Machine-00`
- `ADR-0009`
- `ADR-0041`

这些与 `D5.8` 的新指针并存，读者会看到两套码。

## 目标

1. 把上述位置的旧码字面改为指针：“退出码分段/逐码见 `spec/Machine-v5 §7.1`”；不复制逐码表。`ADR-0004` 的 D1/D3/D4/D5.1–D5.6/D6.2/D6.3/Rationale/Consequences 全部纳入；`## 修订` 历史段不改。
2. `ADR-0004` 其它 decision 只做**指针化修订**，不改决策结论；每处追加 `rev. 2026-11-05` 或集中“修订”注记。
3. DDLN `D-D002`/`TT-D002` 的 Q4 按新模型改写；`Machine-00` 的 `0x81–0x8D` 改三段式；`ADR-0009 D5`、`ADR-0004 D3`/Consequences 原地修订为三段式分区；只改旧码解释，不改技术结论。
4. 不改 QEMU/gem5/tests/contracts；不改 Machine-v5（已由 187t 定稿）。

## 范围 / 非范围

**在范围内**：`.tao/adr/adr-0004-test-machine.md`（仅旧码字面/指针）、`.tao/adr/adr-0009-*`、`.tao/adr/adr-0041-*`、`docs/DDLN/D-运行平台/DD-D002`、`docs/DDLN/D-运行平台/TT-D002`、`docs/Machine-00`、本任务书、`milestones.md`。

**不在范围内**：`spec/Machine-v5`（已定稿）、`DADAO-12/13/22/23`、QEMU/gem5/tests、`contracts/**`、DDLN 其它册。

## 验收标准

1. 上述活文件旧码/`PTWERR`/`unmapped` 字面 0 命中（历史/修订段除外）。
2. 全部改为指针，不复制逐码表；决策结论不变。
3. ADR 修订有 `rev. 2026-11-05` 或集中注记；用户逐条确认记录在任务书 §用户裁定。
4. 门控：`check-spec-refs`/`check-spec-purity`/`check-knowledge-refs`/`check-milestones-fresh`/`make check`（L1）rc=0。
5. 反例可达 FAIL；完成区 ≤30 行；状态 `待验收`。

## 未决（已裁定）

1. ADR decision：`ADR-0004`/`ADR-0009`/`ADR-0041` 均选 A（活 decision 指针化，`## 修订` 不改）。
2. `docs/Machine-00`：按讲义处理，只改 `0x81–0x8D` 旧码说明，不改技术结论。
3. DDLN：只改 `D-D002`/`TT-D002`，其它册不动。

## 完成区

**测试结果**：运行期证据脚本 → `RESULT: PASS（失败项 0）`；C1 旧码/`PTWERR`/`unmapped` 及旧 guest 分区（`0x01–0x7F`/`0x01–0x3F`）命中 0（6 文件）；C1b D3/Consequences 三段式通过；C2 §7.1 指针 6/6；C3 `rev. 2026-11-05` 3/3；C4 `## 修订` 段与 HEAD 逐字节一致（14580 B）；C4b ADR-0009 D5 三段式通过；C5 门控 5/5 rc=0；S1 在 D3 注入旧 guest 分区 → rc=1 → cp+md5 还原 → rc=0。
**修改文件**：`.tao/adr/adr-0004-test-machine.md`、`.tao/adr/adr-0009-qemu-harness-methodology.md`、`.tao/adr/adr-0041-tlb-ad.md`、`docs/DDLN/D-运行平台/DD-D002-运行平台--测试机运行环境.md`、`docs/DDLN/D-运行平台/TT-D002-运行平台--测试机运行环境.md`（gitignored，已同步主工作树，md5 `2927be3f…`）、`docs/Machine-00-执行环境分层-Draft.md`、`.tao/knowledge/milestones.md`；证据 运行期证据脚本。
**验收结果**：`check-spec-refs`/`check-spec-purity`/`check-knowledge-refs`/`check-milestones-fresh`/`make check` 均 rc=0（日志 运行期日志）；ADR-0004 `## 修订` 历史段与 HEAD 逐字节一致；ADR 三册均加 `rev. 2026-11-05`；ADR-0009 D5 与 `Machine-v5 §7.1` 三段式一致；ADR-0004 D3/Consequences 的 guest 分区已同步。
**新发现/坑**：1) 用户裁定**原地修订 `ADR-0004 D3` 与 Consequences，未另立任务**：guest 分区改为 `0x00–0x3F` PASS / `0x40–0x7F` FAIL / `0x80–0xFF` 机器 fault，D3 零 host 行同步，地址/宽度/编码机制不变。2) 用户裁定**原地修订 `ADR-0009 D5`，未另立任务**：旧分区改为三段式 + §7.1 指针。3) `ADR-0004` 的 `unmapped`/`0x87` 语义已过时，本次按新模型统一改为 monitor `CFXMEM`（与裁定 4 一致）。4) TT-D002 为 gitignored 草稿，已 `cp` 同步主树并用 md5 对账。
**遗留问题**：无。

## 审阅记录

#### 第 1 轮 engineer 自审

- 逐行核对 `ADR-0004` 活区（L3–L344）：D1/D3/D4/D5.1–D5.6/D6.1/D6.3/Rationale/Consequences 的旧码全部指针化；`## 修订` 段零改动（diff 最大旧行 328 < 345）。
- 逐行核对 `ADR-0009`/`ADR-0041`/`DD-D002`/`TT-D002`/`Machine-00`：旧码列、`PTWERR`、`unmapped` 均清零；指针与 `rev. 2026-11-05` 注记存在。
- 用户裁定追加：`ADR-0009 D5` 原地修订为三段式（guest/其它 cfx/monitor）+ §7.1 指针，未另立任务；Fault Codes 表与 D5 无旧码冲突。
- 用户裁定追加：`ADR-0004 D3` 表与 Consequences 的 guest 分区原地修订为 `0x00–0x3F`/`0x40–0x7F`/`0x80–0xFF`，未另立任务；地址/宽度/编码机制未动；`## 修订` 段与 HEAD 逐字节一致（14580 B）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| ADR-0004 D6.1 仍有 `ILLI（0x88）`（任务列举未列但属活 decision） | ✅已修 | 改为 `ILLI` | C1 hits=0 |
| ADR-0004 D1/D5.6 `unmapped`+`0x87` 语义过时 | ✅已修 | 改为「未映射 → 当前 monitor `CFXMEM`」+ §7.1 指针 | C1/C2 |
| ADR-0009 表含 `UNMAPPED` 故障名与旧码列 | ✅已修 | 删码列，`UNMAPPED` 行改 `CFXMEM` | C1/C2 |
| ADR-0041 Consequences/状态说明 仍有 `PTWERR` | ✅已修 | 同步为当前 monitor `CFXMEM` | C1 |
| TT-D002 gitignored，worktree 无此文件 | ✅已修 | 从主树拷入、编辑后回写主树 | md5 双方一致 |
| ADR-0009 D5 `0x01–0x7F=FAIL` 与 §7.1 分区不一致 | ✅已修（用户裁定原地修订 D5，未另立任务） | 改为三段式 + §7.1 指针；D5 局部 `rev. 2026-11-05` | C4b / C5 |
| ADR-0004 D3 表/零 host 行/Consequences 仍为旧 guest 分区 | ✅已修（用户裁定原地修订 D3，未另立任务） | D3 表与零 host 行改 `0x00–0x3F`/`0x40–0x7F`/`0x80–0xFF`；Consequences 同步；机制不动 | C1b / S1 / C4 |

- 防造假自检：证据脚本在 D3 真实注入旧 guest 分区 `0x01`–`0x7F` 得 rc=1，`cp` 还原后 md5 一致且回绿；C4 改用 `## 修订` 段与 HEAD 逐字节比较；门控均取真实退出码，无 `tee` 吞码。

#### 第 1 轮 reviewer 验收

**重跑记录（reviewer 亲自执行，workdir=任务 worktree，未 commit/push）**

- 运行期证据脚本 → `RUN_RC=0`，`RESULT: PASS（失败项 0）`；C1 六文件 hits 全 0；C2 实测 21/4/4/1/1/1；C3 实测 3/2/1；C4 `328 ≤ 345`；C4b 满足；C5 五门控 rc=0；S1 注入 rc=1 → 还原 → rc=0。
- 独立门控（不经脚本、直接取 rc）：`make check-spec-refs`=0（`PASS (0 violations)`）、`check-spec-purity`=0（`hits=0`）、`check-knowledge-refs`=0（`悬空 0`）、`check-milestones-fresh`=0（`PASS 62 行`）、`make check`（L1）=0（`repository checks (L1): PASS`）。
- 独立反例注入①：adr-0004 `#### D5.4` 前插 `0x87`（md5 `6351b407→588ed2e5`）→ 重跑同一脚本 `INJECT_RC=1`（`合计违规: 1`、`[FAIL] C1`）→ `cp` 还原 md5=`6351b407` match=YES → 重跑 `RESTORE_RC=0`（`RESULT: PASS`）。
- 独立反例注入②：adr-0009 D5 换回旧分区（md5 `92f5db49→e1750885`）→ `INJECT_RC=1`（`[FAIL] C4b 缺 token` ×2 + `仍有旧分区 0x01–0x7F`）→ 还原 md5=`92f5db49` → `RESTORE_RC=0`。
- 快照对账：注入前/后 7 改动文件 + run.sh md5 全等（`6351b407 / 92f5db49 / 35aa806f / 2927be3f / 2927be3f / 17922d82 / d7f7a391 / a10ecea4 / 52b4e9f9`）；`git status --porcelain -uall` 与注入前逐行一致（7 行）。还原只用 `cp`+md5，未用 git checkout。

**约束核验（逐条）**

1. 旧码清零：6 文件活正文逐处核 `0x87/0x88/0x8A–0x8D/PTWERR/unmapped` = 0（`0x80`–`0x86` 亦无旧义残留）；仅 adr-0004 `## 修订` L358/L397 命中，属历史段豁免。
2. ADR-0004：`## 修订` 段与 HEAD **字节全等**（两段 9148 B），diff 最大旧行 328 ≤ 345；D5.6 优先级 1→4 次序、D3/D4/D5/D6 结论未变，旧码字面一律改故障名 + `spec/Machine-v5 §7.1` 指针。
3. ADR-0009：D5 三段式与 `§7.1` 逐行一致（guest `0x00–0x3F` PASS / `0x40–0x7F` FAIL、其它 cfx `0x80–0xBF` `bit5:0=cfxHA`、monitor `0xC0–0xFF` `bit5:4/bit3:0`），旧 `0x01–0x7F=FAIL` 已清，「判定只看 `$?`」保留；Fault Codes 表删码列、`UNMAPPED`→`CFXMEM`（合 `§7.1`「未映射归当前 monitor `CFXMEM`」）、表头带指针；全册无 `## 修订` 段，头行/状态历史原句保留、仅追加 `rev. 2026-11-05`。
4. ADR-0041：D7/D10/Consequences/状态说明四处 `PTWERR`→当前 monitor `CFXMEM` + 指针，diff 仅 5 hunks，头行 `Accepted` 原文保留。
5. DDLN/Machine-00：D-D002 Q4 改「统一归 `CFXMEM`（不再区分 unmapped）」；DD/TT md5 全等 `2927be3f`，主树 TT 同 md5（后续 INFRA-123t 删除，本任务只确认同步）；Machine-00 `0x81–0x8D` 改三段式 + 指针。
6. 范围/体例：`git status` 仅 7 文件（3 ADR + DD-D002 + Machine-00 + milestones + 本任务书），无 `spec/`、QEMU、gem5、`tests/`、`contracts/` 改动；完成区 5 行、无运行期路径；三册均有 `rev. 2026-11-05`；milestones/任务书状态 `待验收`。

**finding（非阻断，交 architect 定夺/收尾处置）**

- F1（设计层残留，建议用户裁定原地修订或另立任务）：`ADR-0004` D3 exit-port 值表（L105–108：`0x01`–`0x7F` = FAIL）与 Consequences（L333：按 `0x00`/`0x01`–`0x7F`/`0x80`–`0xFF` 断言）仍与**同册 D5.7/D5.8**（`0x00–0x3F` PASS / `0x40–0x7F` FAIL）、`Machine-v5 §7.1` 及本轮改后的 ADR-0009 D5 冲突——guest 写 `0x01`–`0x3F` 到底算 PASS 还是 FAIL 歧义。系 SPEC-187t 遗留、超出本任务裁定（改它＝改 D3 决策结论，须逐条确认）；完成区「遗留问题：无」宜补登记本条。
- F2：C1 正则不覆盖 guest 分区类残留，C4b 只盯 ADR-0009；若 ADR-0004 旧分区回潮脚本不会红。
- F3：C4 依赖未提交工作树的 `git diff`，改动一旦提交即恒真（`maxold=0`）；建议改为直接比对 `## 修订` 段与 HEAD 字节。

**判决：Accepted** —— 验收标准 1–5 在 reviewer 自己的重跑（含两次独立注入→FAIL→还原→回绿）下全部满足，约束无违反；F1–F3 为范围外残留/脚本加固项，须 architect 定夺，不作本轮返工理由。

#### 第 2 轮 reviewer 验收（D3/Consequences 原地修订 + 脚本加固复验）

**重跑记录（reviewer 亲自执行，workdir=任务 worktree，未 commit/push）**

- 运行期证据脚本 → **`RUN_RC=0`**，`RESULT: PASS（失败项 0）`；C1 六文件 `hits=0`（正则已含 `0x01–0x7F`/`0x01–0x3F` 旧 guest 分区）；C1b 通过；C2 实测 `22/4/4/1/1/1`；C3 实测 `5/2/1`；C4 `当前修订段 14580 B / HEAD 修订段 14580 B` rc=0；C4b 通过；C5 五门控 0；S1 rc=1→还原→0。
- 独立门控（不经脚本、直接取 rc）：`make check-spec-refs`=0、`check-spec-purity`=0、`check-knowledge-refs`=0、`check-milestones-fresh`=0、`make check`（L1）=0。
- 独立反例注入（reviewer 自选位置，非脚本 S1 的 D3 标题行）：把 D3 表两行改回 `0x00` / `0x01`–`0x7F`（md5 `7679aa3e→6ebbeac8`）→ 同一脚本 `INJECT_RC=1`（`L107: 0x01`–`0x7F`、`合计违规: 1`、`[FAIL] C1`、`[FAIL] C1b 仍有旧 guest 分区`）→ `cp` 还原 md5 `7679aa3e` match=YES → `RESTORE_RC=0`（`RESULT: PASS`）。
- 快照对账：注入前/后 `git status --porcelain -uall` 逐行一致（7 行）；受检文件 md5 全部回原值（ADR-0004 `7679aa3e`、ADR-0009 `92f5db49`、ADR-0041 `35aa806f`、DD/TT `2927be3f`、Machine-00 `17922d82`、milestones `d7f7a391`、run.sh `764f3acb`）；主树 TT 同 `2927be3f`、主树 `git status` 干净。还原全程 `cp`+md5，未用 git checkout。

**逐条复核**

1. D3 表 / 零 host 依赖行 / Consequences 均为 `0x00`–`0x3F` PASS、`0x40`–`0x7F` FAIL、`0x80`–`0xFF` 机器 fault，与同册 D5.7/D5.8、`Machine-v5 §7.1` 逐字一致；地址 `0xffff_8000_0000`、8 B 宽度、`st.o` 编码与 QEMU 行为 1–4 机制未动；D3 增局部 `rev. 2026-11-05` 注记。
2. 六文件活区扫描（`0x01–0x7F`/`0x01–0x3F`、`0x87/0x88/0x8A–0x8D`、`PTWERR`、`unmapped`，含小写）= 0；`## 修订`（现 L347 起）与 HEAD **逐字节相同**（14580 B），diff 最大旧行 333 ≤ 347；D5.6 优先级与各 decision 结论未变。
3. F1 闭环（D3/Consequences 与 D5.7/D5.8/§7.1/ADR-0009 D5 一致，冲突消除）；**F2 已修**（C1 纳入 guest 旧分区 + 新增 C1b 分节断言，均经我注入证伪可达 FAIL）；**F3 已修**（C4 改 `git show HEAD:` 与工作树字节比对，不再依赖未提交 `git diff`，提交后仍有效）。
4. 范围/体例：`git status` 仅 7 文件，无 `spec/`、QEMU、gem5、`tests/`、`contracts/` 改动；完成区 5 行、无运行期路径；三册 `rev. 2026-11-05`；任务书/milestones 状态 `待验收`。

**finding（非阻断）**

- N1：C1 正则 `0x8[789A-D]` 只匹配大写字母、且不含 `0x80`–`0x86`（如小写 `0x8a`、残留 `0x81` 不会命中）；reviewer 另跑含小写与 `0x80`–`0x86` 的全字模扫描，活区实测 0 命中，故不阻断，建议后续收紧正则。
- N2：D3 Superseded 注记现作「本节点内正文未改写（rev. 2026-11-05 仅同步 guest 写入值分区，见下）」——历史结论与原句均保留、已披露本轮改动，措辞略拗，architect 收尾可酌情润色（不得改历史语义）。

**判决：Accepted** —— 验收标准 1–5 在本轮 reviewer 自己的重跑（脚本 PASS rc=0、五门控 rc=0、独立注入 D3 旧分区→`INJECT_RC=1`→还原→`RESTORE_RC=0`）下全部满足；F1–F3 已闭环/修复；N1、N2 为非阻断加固/措辞项。

#### 收尾（architect，2026-11-05）

- N1：C1 正则未覆盖小写/`0x80–0x86`；reviewer 另跑全字模扫描活区 0 命中，不阻断；记入证据脚本后续收紧。
- N2：D3 的 Superseded 注记措辞略拗，未改历史语义；记入遗留，可后续润色。
- D3/Consequences 与 D5.7/D5.8、§7.1、ADR-0009 D5 已一致；`## 修订` 历史段字节未改。
- 判决 Accepted（第 2 轮），状态置 `已验证`。
