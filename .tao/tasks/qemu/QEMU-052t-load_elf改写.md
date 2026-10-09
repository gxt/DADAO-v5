# QEMU-052t: 改走 `load_elf()`（钉子②）

**模块**：qemu
**项目里程碑**：M6
**依赖**：无（M5 已验证态）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `components/qemu/patches/hw/dadao/**`（现自建 `dadao_load_regions[]` 白名单路径，以**实测**为准）。
  - QEMU 上游 `hw/core/loader.c`（`load_elf()` 标准 API；复用、不重写）。
  - `.tao/adr/adr-0004-test-machine.md`（加载/入口模型）、`.tao/adr/adr-0020-see-semihosting.md`（`-bios` bootrom 与 M4 ELF 路径**并存**）。
  - `.tao/knowledge/issues.yaml`：`ISS-168`（`-bios`+ELF 组合加载/ELF loader 扩展/组合 ADR）。
  - `spec/Process-01-组件补丁组织与构建编排.md`。
- **输出**：
  1. `components/qemu/patches/hw/dadao/**`：ELF 直载**改走 `load_elf()`**；**取消**自建 `dadao_load_regions[]` 白名单。
  2. **验证项**（作为验收）：多段 `PT_LOAD` / `RELA` / `e_entry` / 栈初始化由 `load_elf()` 提供 ⇒ 逐项验证；**`-bios` + ELF 组合不需要**。
  3. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - **复用上游标准 API**（不重写 loader）；不改变外部加载接口契约（用户仍经 `-kernel <elf>`）。
  - **`spec/` 交集为空**。
  - 与 `QEMU-053t` **同改 `components/qemu/patches` ⇒ 串行**。

## 硬约束

- **临时目录** `/tmp/opencode/QEMU-052t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/QEMU-052t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **重建成本申报**：改 `components/qemu/patches/**` ⇒ 开工前写明「重建 QEMU（增量），预计 N 分钟」；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/qemu/QEMU-052t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **走 `load_elf()`**：`grep`/代码证据证明 ELF 直载经 `load_elf()`；**自建白名单已移除**（`grep dadao_load_regions` 无残留，或给正当理由）。
2. **验证项逐条**：多段 `PT_LOAD`（≥2 段）/`RELA`/`e_entry`/栈初始化各 ≥1 例（给真实输出）。
3. **接口不变**：用户经 `-kernel <elf>` 加载的行为与改前**等价**（给真实输出）。
4. **不回归**：`make check`/`check-interface`/`check-patch-tree` EXIT=0（通过数与改前**逐项相等**）。
5. **`spec/` 交集为空**：`git diff --name-only | grep -E '^spec/'` → 无输出。
6. **一键证据脚本**：`.work/evidence/QEMU-052t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检，给真实输出与退出码。
7. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

> ⚠️ **停下报告（契约冲突）→ 未标 `待验收`，状态保持 `待开始`**：派遣要求「加载模型/机器接口须与 `contract-elf.md §5/§6` 对得上；若契约与 `load_elf()` 语义冲突 ⇒ **停下报告**，不擅自改契约」。实测确认**冲突成立**——改走**纯 `load_elf()`** 后，契约 §6.1.2 / `ADR-0004 D2.3` 的三类**加载期非零退出校验丢失**（详见「遗留问题」）。候选实现已完成且要求门控全绿，但据该句不做收尾/不改契约，留待裁定；候选留工作树（未提交）。

**测试结果**：`make test-elf` 5/5 PASS（EXIT=0）；`make check-qemu-semantics` 149/149 PASS（EXIT=0）；`check-patch-tree` 92 patches OK（EXIT=0）。日志 `.work/log/qemu/QEMU-052t-{build,test-elf,check-qemu-semantics}.log`。

**修改文件**（candidate，未提交）：`.work/source/qemu/hw/dadao/dadao-machine.c`（删自建 loader+白名单、改调 `load_elf()`）；`components/qemu/patches/hw/dadao/dadao-machine.c.patch`（`make_patch qemu` 重导出，359 行）。

**验收结果**（正例，真机）：path A 改调 `load_elf(kernel,NULL,NULL,NULL,&entry,NULL,NULL,NULL,ELFDATA2MSB,DADAO_EM_MACHINE,0,0)` + `cpu_set_pc(entry)`；`grep dadao_load_regions` 无残留；内存图（RAM@0 16 MiB / 旧 RAM / ROM / exit port）与 raw-bin path B **未改**。旧探针 042t 正例全绿：多段 `PT_LOAD`、`.bss` 零填充、`e_entry`（RAM base 放 `fence` poison）、exact RAM/ROM —— `.work/log/qemu/QEMU-052t-probe042t-post.log`。

**新发现/坑**：上游 `load_elf()` **不含** §6.1.2 要求的 `e_flags` 版本/保留位校验、`e_type==ET_EXEC` 校验、PT_LOAD「越出映射区域」校验；且以 **ROM blob** 装载、`rom_reset` **忽略**写错误 ⇒ 越界/超限段**静默不装载**，**不**「加载期非零退出」。

**遗留问题（⚠️ 契约冲突，待裁定）**：旧探针 042t（非门控）14 负例中 5 项在新实现下**由「非零退出」变为 `exit=0`（未拒）**：`neg_bad_flags_ver`/`neg_bad_flags_res`/`neg_bad_type`/`neg_seg_out_of_range`/`oversize_elf_seg`；另 6 项仍非零退出但消息改为上游文案（`Failed to load ELF`/`incorrect endianness`/`incompatible architecture`/`segments are too big to load`）。**选项**：(A) 采纳 `load_elf()` 语义 ⇒ **改契约**（`contract-elf §6.1.2` + `ADR-0004 D2.3`，属 spec 任务，非本任务）；(B) 补薄校验（如改调 `load_elf_ram_sym(...,load_rom=false)` 使越界写立即 MEMTX 失败，并另校验 `e_flags`/`e_type`）——但与「取消自建白名单」相抵。证据全文见上日志。**未标 `待验收`：待用户在 A/B 间裁定。**

> **【追加：用户裁定（2026-10-09，原话留痕）】** ① ②「**我们自己校验（推荐）**」、③「**用 `load_rom=false`（推荐）**」；用户原问「1/2不需要load_elf校验，简言之，就是不改load_elf」+「3我没看懂，到底是load_elf还是load_rom」。**裁定结论 = 不改上游 `load_elf`、不改契约**：①② 调用方在装载前**自校验**（`e_flags[7:0]==1`、`e_type==ET_EXEC`）；③ 改用 `load_elf_ram_sym(..., load_rom=false, ...)`。**文案不约束**（用户裁定）。据此**选项 A/B 均不采纳**，按上方案继续实现。

**子代理异常登记（2026-10-09，只追加）**：本任务 engineer 子代理被 **`cancelled`**（**非失败**；它主动停下等裁定，产出已落盘、WIP 保命提交 `5dfd311`）—— session `ses_ee1d85631ffe…`、异常类型 `cancelled`、**次数 1**、产出已落盘 ⇒ **无需重试**，改按上述用户裁定继续。同记 `milestones.md`「当前进度」。

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

> **范围**：`hw/dadao/dadao-machine.c` 的 loader 改写（自建 → `load_elf()`）。逐行审查 + 真机验证。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `load_elf()` 调用参数（endian/machine/entry/clear_lsb/data_swab）须正确 | ✅已修 | 传 `ELFDATA2MSB`、`DADAO_EM_MACHINE(0x0DA0)`、`&entry`、`0,0` | `neg_bad_data`/`neg_bad_machine` 仍非零退出；`elf_data_bss`（entry≠base）PASS |
| F2 VA=PA：`load_elf` 用 `p_paddr` 装载（契约要求 `p_vaddr`） | ✅核实 | 契约 §5.2 强制 `p_vaddr==p_paddr` ⇒ 等价；未改契约 | test-elf 5/5（ld.lld 产物 paddr==vaddr） |
| F3 自建白名单/loader 残留 | ✅已修 | 删 `dadao_load_regions[]`/`dadao_elf_rd*`/`dadao_region_contains`/`dadao_fill_zero`/`dadao_load_elf` | `grep -n 'dadao_load_regions\|DadaoLoadRegion\|dadao_load_elf'` 无输出；`check-patch-tree` ⑥绿 |
| F4 装配错误（缺 include/未用变量） | ✅核实 | `loader.h`/`elf.h` 已在；`cpu` 仍用于 `cpu_set_pc` | `make build-qemu` EXIT=0（无 error） |
| F5 **契约 §6.1.2 负例校验丢失**（`e_flags`/`e_type`/越界） | ⏸延后（**停下报告**） | 无（不擅自改契约/加校验） | 探针 042t：`neg_bad_flags_*`/`neg_bad_type`/`neg_seg_out_of_range`/`oversize_elf_seg` → exit=0 |

**结论**：F1–F4 已处置；**F5 为契约层冲突，据派遣「停下报告」未处置** ⇒ 任务**不标 `待验收`**，保持 `待开始`，返回主会话裁定（选项 A/B 见完成区「遗留问题」）。

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
