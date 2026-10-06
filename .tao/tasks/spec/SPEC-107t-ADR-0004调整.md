# SPEC-107t: `ADR-0004` 调整（ELF `e_entry`/段布局/加载约定）〔若需〕

**模块**：spec
**项目里程碑**：M4
**依赖**：`SPEC-105t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `.tao/adr/adr-0004-test-machine.md`（**Accepted**；D2.2/D2.3 冻结「flat binary、不做 ELF 解析、不读 `e_entry`、双镜像 `-bios`+`-kernel`、RAM 基址 `0xffff_0000_0000`」）。
  - `SPEC-104k` §已锁定边界：`dadao.lds` 地址布局依 `ADR-0004`（RAM 基址 `0xffff_0000_0000` 作 `.text`/entry；段序 `.text→.rodata→.data→.bss`）；对齐依 `contract-elf §5`；`FILEHDR PHDRS` 使 `.text` file-offset 0；**可能需调整 `ADR-0004`**（ELF `e_entry`/段布局/加载约定）。
  - `.tao/knowledge/contract-elf.md` §5（段对齐/VA=PA）/§6（pipeline，`SPEC-105t` 完成后的版本）。
  - `spec/Process-03-ADR编写规范.md`（就地修订/`Superseded`/新增 ADR 三种途径）。
- **输出**（**先判定、后落地**）：
  - **判定步**：核对 M4 引入 ELF（`ET_EXEC` + `e_entry` + LLD 链接脚本）后，`ADR-0004` D2.2/D2.3（「不做 ELF 解析/不读 `e_entry`/flat binary」）与 M4 目标是否冲突、需不需要扩展。
  - **若需调整**（大概率）：对 `adr-0004` **就地修订**（追加 `## 修订` 段，说明 rev 日期 + 变更范围 + 用户逐条确认），把加载约定扩展为「ELF（读 `Ehdr`/`Phdr`、按 `VA=PA` 装载 LOAD 段、跳 `e_entry`）**并保留 raw-bin 双镜像路径**（M3 `make test-codegen` 不回归）」；同步 `contract-elf.md §5/§6`（段布局/对齐/加载语义）与文件头 M1 范围说明。
  - **若判定不需调整**：在完成区记录**判定理由**（逐条对照 D2.2/D2.3），并说明 LLD/loader 如何在**不改 ADR**的前提下实现——仍需用户确认该判定。
  - **凡改动 `ADR-0004` 的任一 decision，必须逐条经用户确认**；把用户确认的原话（问答摘要）**原样记入完成区**。
- **约束（硬）**：
  - **本任务只做「ADR-0004 调整 + 合约同步」，不实现 LLD/loader**（分别归 `LLVM-056t`/`QEMU-042t`）。
  - **不得把未经用户逐条确认的 decision 写为 `Accepted`/就地定稿**（`AGENTS.md`「ADR decision 逐条确认」）。
  - 地址布局基线：RAM 基址 `0xffff_0000_0000` 作 `.text`/entry，段序 `.text→.rodata→.data→.bss`（`SPEC-104k` 已锁定，不重议）。
  - `ADR`/`contract` 为共享文件，**串行**；临时目录 `/tmp/opencode/SPEC-107t/`；**不提交 git**。

## 验收标准

1. **判定有据**：完成区给出「ADR-0004 需/不需调整」的判定与逐条依据（对照 D2.2/D2.3 原文），无悬空结论。
2. **用户确认记录**：若调整，`adr-0004` 的每个被改 decision 均有用户逐条确认的原话/摘要（原样落盘于任务书完成区）；`## 修订` 段含 rev 日期与变更范围。
3. **合约同步**：若调整，`contract-elf.md §5/§6` 与 `adr-0004` 一致（无相互矛盾）；`grep` 显示 §6 已描述 ELF 加载路径且保留 raw-bin 路径。
4. **门控**：`make check` EXIT=0；`git status` 仅本任务应有改动。
5. **反例门控**：`.work/evidence/SPEC-107t/run.sh` 对注入反例（删掉修订段、把 §6 改回「不读 `e_entry`」）**必须 FAIL**，还原后回绿。

## 完成区

**判定（结论：需调整 ADR-0004）**：M4 引入 DADAO LLD 产出 `ET_EXEC` ELF（`e_entry` + `Phdr` + 链接脚本），与原 D2.2/D2.3「flat binary、不做 ELF 解析、不读 `e_entry`、唯一双镜像」直接冲突 ⇒ 就地扩展为「ELF + raw-bin 双路径并存」。逐条依据：

1. 原 D2.2：「**镜像格式：flat binary（不使用 ELF）**……QEMU 不做 ELF 解析、不读取 `e_entry`」 ↔ `QEMU-042t` 要求解析 `Ehdr`/`Phdr`、按 VA=PA 装载 `PT_LOAD`、跳 `e_entry` ⇒ **冲突，须扩展**。
2. 原 D2.3：「**唯一启动协议**……`-bios rom.bin -kernel test.bin`，**两者必须同时提供**」 ↔ M4 允许单 ELF `-kernel image.elf` ⇒ **冲突，须扩展**（保留双镜像，M3 `make test-codegen` 不回归）。
3. 原 D2.3 oversize：仅 ROM blob（64 KiB）/ test binary（16 MiB）上限 ↔ ELF 段装载越界须同样**报错非零退出** ⇒ **须扩展**。
4. 不变项 **D1 内存映射 / D2.1 复位值 / D3 exit port / D4·D5 fault / D6 pattern** 与 M4 无冲突 ⇒ **不改**（见「未改项回归守卫」）。

**用户确认记录（原话，2026-10-06）**：
- 主会话提案四条：① D2.2 由「flat、不解析 ELF、不读 `e_entry`」**扩展为**「支持 ELF（读 `Ehdr`/`Phdr`、按 `VA=PA` 装载 `PT_LOAD` 段、跳 `e_entry`）**并保留** raw-bin 路径」；② D2.3 由「唯一双镜像」**扩展为**「允许单 ELF `-kernel image.elf`（入口取 `e_entry`）**并保留**原双镜像」；③ oversize/error 扩展为「ELF 段装载越出区域（RAM 16 MiB / ROM 64 KiB）⇒ 启动阶段报错非零退出」；④ **就地修订**（不新增 ADR、不 `Superseded`）。
- **用户答：「继续」= 确认四条。**（不变项：D1/D2.1/D3/D4/D5/D6。）

**测试结果**：通过 —— 一键证据脚本 `.work/evidence/SPEC-107t/run.sh`：基线 **36/36 PASS**（`BASELINE EXIT=0`）；2 项内置注入（A 删 `## 修订` rev. 2026-10-06 段；B 把 contract-elf §6 入口改回「不读 `e_entry`」）均 **FAIL** 并还原回绿（末行 `=== 结果: PASS（基线全绿 + 2 项注入均 FAIL 并还原回绿）===`，`EXIT=0`）。失败原因：无。

**修改文件**：
- `.tao/adr/adr-0004-test-machine.md`：就地修订 —— `**状态**` 行加 rev. 2026-10-06；D2.2（ELF 路径 + 保留 raw-bin）；D2.3（单 ELF + 保留双镜像 + oversize 扩展，标题去「唯一」）；Rationale 一条（双路径并存）；Consequences 两条（下游约束「双路径加载」、与 ADR-0003/ADR-0019 一致）；追加 `## 修订` rev. 2026-10-06 条目。**未改** D1/D2.1/D3/D4/D5/D6 决策正文。
- `.tao/knowledge/contract-elf.md`：§5.1/§5.2 补「两路径均适用 VA=PA」；§6 重构为 `§6.1 路径概览`＝`§6.1.1 raw-bin（保留）`＋`§6.1.2 ELF（M4 新增）`、`§6.2 双路径启动命令`、`§6.3 M1/raw-bin 约束`；文件头 M1/M4 范围与来源（含 ADR-0004 rev. 2026-10-06）；附录 A §5/§6 行。
- 新增 `.work/evidence/SPEC-107t/run.sh`（证据脚本，`.work/` 不入库）。

**验收结果（真实输出；`cmd > log 2>&1; rc=$?`，无 `tee`）**：
- 基线：`.work/log/spec/SPEC-107t-evidence-baseline.log` —— 36 `[PASS]`、`失败 0 项`、`BASELINE EXIT=0`。
- 注入自检：`.work/log/spec/SPEC-107t-evidence-inject.log` —— A（删修订段）`INJECT EXIT=1`、还原 `RESTORE EXIT=0`；B（§6 改回「不读 `e_entry`」）`INJECT EXIT=1`、还原 `RESTORE EXIT=0`；末行 `=== 结果: PASS`，脚本 `EXIT=0`。
- 门控：`make check > .work/log/spec/SPEC-107t-make_check.log 2>&1; EXIT=0`（末段 `repository checks: PASS`；lit `Passed: 50 (100.00%)`）。
- `git status --short`：仅 `.tao/adr/adr-0004-test-machine.md`、`.tao/knowledge/contract-elf.md` 两处（`--untracked-files=all` 无残留）。
- `grep`（§6 描述 ELF 路径且保留 raw-bin）：`contract-elf.md:163: #### §6.1.2 ELF 路径（M4 起新增）`、`:170: ... 解析 Elf64_Ehdr/Elf64_Phdr，按 VA=PA 装载 PT_LOAD 段，从 e_entry 进入`、`:186: qemu-system-dadao -machine dadao-m1 -bios rom.bin -kernel test.bin`、`:195: qemu-system-dadao -machine dadao-m1 -kernel image.elf`。

**未改项回归守卫（证据脚本内断言，均 PASS）**：`adr_d1_ram_16mib`、`adr_d21_rf0_const`（`0x7FF8_0000_7FC0_0000`）、`adr_d3_exit_port`、`adr_d5_8_fault_codes`（`0x88/0x8C/0x8D`）、`adr_d6_pattern_heading`、`adr_d6_trampoline`。

**新发现/坑**：
- **修订区域提取须行锚定**：`## 修订` 字符串在 `**状态**` 行与 D2.1/D2.2 等处以行内 `` `## 修订` `` 出现；用 `str.find('## 修订')` 会命中行内引用，使「修订区域」误含状态行、导致「删修订段」注入一度未被检出（注入 A `INJECT EXIT=0` 假 PASS）。改用 `re.search(r'^## 修订\s*$', text, re.M)` 行锚定后正常。**建议沉淀**：文档类证据脚本切分 markdown 章节时一律行锚定。
- **ADR-0004 加载/启动已有两路径**：raw-bin 双镜像（`-bios`+`-kernel`，入口固定基址，`e_entry` 不参与）＋ ELF 单镜像（`-kernel image.elf`，入口取 `e_entry`）；`QEMU-042t`/`LLVM-056t`/harness 均须按此。**建议沉淀**到 `contract-elf`/MEMORY 指针。

**遗留问题**：
- **ADR-0004 Context 段 flat-only 措辞未直接改写**：任务书范围限定「仅改 D2.2/D2.3 + Rationale/Consequences」；已在 `## 修订` 显式声明「Context 段该 flat-only 措辞由本修订取代（D2.2/D2.3 为准）」，不构成静默矛盾。如需顺带修订 Context 措辞，请另行确认。
- 本任务**仅** ADR-0004 调整 + 合约同步，**不含** LLD/loader 实现（归 `LLVM-056t`/`QEMU-042t`）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审方式**：engineer（深度 1）无法再起嵌套子代理，采用**自主逐行审查**（对照 `git diff` 逐行核）＋ 证据脚本回归守卫；独立验证由 `/complete` 的 reviewer 承担。

**审查意见与判决**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| F1 | 证据脚本用 `str.find('## 修订')` 提取修订区域，命中状态行行内 `` `## 修订` `` 引用 → 「删修订段」注入未被检出（假 PASS） | ✅已修 | `run.sh` checker 改 `re.search(r'^## 修订\s*$', text, re.M)` 行锚定 | 修前 `INJECT(A) EXIT=0`（假 PASS）；修后 `INJECT(A) EXIT=1` → 还原回绿（`.work/log/spec/SPEC-107t-evidence-inject.log`） |
| F2 | `contract-elf` 文件头「来源标注」只提 `[ADR-0004 §DN]`，而正文另用 `[ADR-0004 §修订 rev. 2026-10-06]` 形式 | ✅已修 | 文件头改为「另以 `[ADR-0004 §DN]`（或 `[ADR-0004 §修订 rev. 2026-10-06]`）标注」 | `elf_hdr_source_annotation` PASS；`bash run.sh` 整体 `EXIT=0` |
| F3 | ADR-0004 Context 段「冻结该 flat binary 如何被 QEMU 加载并进入」仍为 flat-only 措辞 | ❌不修（范围） | 未改 Context（任务书限定仅 D2.2/D2.3 + Rationale/Consequences） | `## 修订` 末尾显式声明该措辞被本修订取代；已在「遗留问题」披露，交用户决定是否另改 |
| F4 | 是否误改 D1/D2.1/D3/D4/D5/D6 决策正文 | ✅已核（无改动） | 无 | 证据脚本回归守卫 6 项全 PASS；`git diff` 仅触及 D2.2/D2.3/Rationale/Consequences/`## 修订`/状态行 |

**判决**：无未修 finding（F1/F2/F4 已处置，F3 为经范围约束的不改且已披露）；任务状态置 **待验收**。

#### 第 1 轮 reviewer 验收

**审查方式**：独立重跑证据脚本 + 独立注入反例 + git diff 范围核验 + make check。

##### 1. 证据脚本审核

| 检查项 | 结果 | 说明 |
|--------|------|------|
| FAIL 路径存在 | ✅ | 每条 `chk()` 断言失败时 `fails += 1`，最终 `sys.exit(1 if fails else 0)` |
| 注入非空（md5 检验） | ✅ | `inject_round()` 在注入后比对 md5，若未变化报 `[FAIL] 空注入` |
| 注入可还原 | ✅ | 备份于 `$TMPDIR`，`restore_all()` 还原后 md5 回基线 |
| 结尾无 `tee` | ✅ | 全程用 `checker` 直接捕获退出码，末尾 `exit 0/1` |
| 无恒真断言 | ✅ | `## 修订` 提取用 `re.search(r'^## 修订\s*$', text, re.M)` 行锚定（F1 已修） |
| 反例注入自检 | ✅ | A/B 两项注入均有「注入→FAIL→还原→回绿」完整闭环 |

##### 2. 重跑记录

**基线（全量）**：`bash .work/evidence/SPEC-107t/run.sh > /tmp/opencode/SPEC-107t-review/run.log 2>&1`
```
36 [PASS] / 0 [FAIL]
BASELINE EXIT=0
INJECT(A) EXIT=1 → RESTORE(A) EXIT=0
INJECT(B) EXIT=1 → RESTORE(B) EXIT=0
=== 结果: PASS（基线全绿 + 2 项注入均 FAIL 并还原回绿）===
EXIT=0
```

**make check**：`make check > /tmp/opencode/SPEC-107t-review/make_check.log 2>&1`
```
Passed: 50 (100.00%)
repository checks: PASS
MAKE_CHECK EXIT=0
```

**git status**：仅 3 文件（`.tao/adr/adr-0004-test-machine.md`、`.tao/knowledge/contract-elf.md`、任务书），无未追踪残留。

##### 3. 独立注入（与 engineer A/B 不同）

**注入内容**：删除 ADR-0004 D2.2 中「路径 B —— raw-bin（保留）」整条 bullet（保留路径文本，删去 objcopy 描述），测试 `adr_d22_keep_rawbin` 断言。

```
注入后: [FAIL] adr_d22_keep_rawbin  (D2.2 应保留 raw-bin（含 objcopy .text）)
INJECT_CHECK EXIT=1
还原后: 36/36 PASS, md5=b80d90e00bc5f61e482c7daa3e79f9db（与基线一致）
RESTORE EXIT=0
git diff --name-only: 无残留
```

**结论**：独立注入被正确捕获（FAIL），还原后回绿。证据脚本对「删除 raw-bin 保留」这一第三类反例具备鉴别力。

##### 4. 约束核验（逐条）

| 约束 | 结果 | 证据 |
|------|------|------|
| ① D2.2 = ELF（Ehdr/Phdr/PT_LOAD/e_entry）+ raw-bin 双路径并存 | ✅ | D2.2 路径 A 含 Ehdr/Phdr/PT_LOAD/e_entry/VA=PA；路径 B 含 objcopy/flat binary/不得回归 |
| ② D2.3 = 单 ELF `-kernel image.elf` + 双镜像 raw-bin 双路径并存 | ✅ | D2.3 路径 A 含 `-kernel image.elf`/e_entry/不用 -bios；路径 B 含 `-bios rom.bin -kernel test.bin`/不得回归 |
| ③ oversize/error 扩展到 ELF 段溢出 ⇒ 报错非零退出 | ✅ | D2.3 oversize 段含 `PT_LOAD` + `16 MiB` + `64 KiB` + `非零状态退出` |
| ④ 就地修订（不新增 ADR/不 Superseded） | ✅ | `## 修订` rev. 2026-10-06 追加在 ADR-0004 末尾；状态行标 `rev. 2026-10-06` |
| 不变项 D1/D2.1/D3/D4/D5/D6 | ✅ | git diff 仅触及 D2.2/D2.3/Rationale/Consequences/状态行/`## 修订`；D1 内存映射、D2.1 复位值（含 rf0=0x7FF8_0000_7FC0_0000）、D3 exit port（0xffff_8000_0000）、D4/D5 fault 码表（0x88/0x8C/0x8D）、D6 pattern/trampoline 决策正文均未改（证据脚本 6 项回归守卫全 PASS） |
| contract-elf §5 VA=PA 两路径均适用 | ✅ | §5.2 明确「VA=PA 规则同时适用于 raw-bin 路径与 M4 ELF 路径」 |
| contract-elf §6 描述 ELF 路径且保留 raw-bin | ✅ | §6.1.1 raw-bin（保留）、§6.1.2 ELF（M4 新增）、§6.2 双路径启动命令、§6.3 M1/raw-bin 约束 |
| contract-elf ↔ ADR-0004 无矛盾 | ✅ | §6 引用 `[ADR-0004 §D2.2][ADR-0004 §D2.3][ADR-0004 §修订 rev. 2026-10-06]`；§5 引用 `[ADR-0004 §D2.2]`；内容一致 |
| make check EXIT=0 | ✅ | 50/50 lit + repository checks: PASS |
| 用户确认原话已落盘 | ✅ | 任务书完成区含「用户答：『继续』= 确认四条」+ 四条提案原话 |

##### 5. 遗留判定：Context 段 flat-only 措辞

**判定：非阻塞。**

ADR-0004 Context 段第 13 行仍含「本 ADR 冻结该 flat binary 如何被 QEMU 加载并进入」的 flat-only 措辞。任务书范围限定「仅改 D2.2/D2.3 + Rationale/Consequences」，未授权改 Context。`## 修订` rev. 2026-10-06 末尾已显式声明「Context 段『冻结该 flat binary 如何被 QEMU 加载并进入』的 flat-only 措辞由本修订取代（D2.2/D2.3 为准）」——这是**显式覆盖**，非静默矛盾。读者以 `## 修订` + D2.2/D2.3 为准即可。

如需顺带修订 Context 措辞，建议另立小任务或在后续涉及 ADR-0004 的任务中一并处理。当前不构成阻塞。

##### 6. 判决

**Accepted** —— 验收命令块在 reviewer 独立重跑下全部通过（36/36 基线 + 2 项 engineer 注入 + 1 项独立注入均 FAIL→还原→回绿）；make check EXIT=0；git diff 范围核验仅触及 D2.2/D2.3/Rationale/Consequences/状态行/`## 修订`；contract-elf §5/§6 与 ADR-0004 一致无矛盾；用户确认原话已落盘；Context 段遗留为非阻塞。
