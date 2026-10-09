# QEMU-052t: 改走 `load_elf()`（钉子②）

**模块**：qemu
**项目里程碑**：M6
**依赖**：无（M5 已验证态）
**状态**：已验证

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

**用户裁定原话留痕（2026-10-09，`lessons §7.3`）**：主会话问「其它 ISA 是怎么判断越界的？」，答「Linux = loader 只做一致性/溢出检查 + 让映射器拒绝；QEMU 上游 `load_elf()` 不查范围、关心的机器在机器代码里自己查；裸机 bootloader 同」。用户据此选定 **「B′ 一致性/范围检查（推荐）」** ⇒ **`load_elf()` 保持上游 ROM 装载（回退 `load_rom=false`，消除 ROM 段回归）+ 在调用前做一致性/范围检查**；契约不变；并修正探针为真越界。① ② 由**我们自校验**（不改上游 `load_elf`）仍有效；文案不约束。**不改上游 `load_elf`/`loader.c`、不恢复 `dadao_load_regions[]` 白名单、不改契约正文（仅 §6.1.2 追加一句，上一轮已加，本轮确认存在）。**

**测试结果/门控（全 EXIT=0）**：`make test-elf` 5/5；`check-qemu-semantics` 149/149；`check-patch-tree` 92 patches OK；`make check` 全绿。042t 探针 **21/21 PASS**（`.work/log/qemu/QEMU-052t-probe-full.log`）。

**修改文件**：`.work/source/qemu/hw/dadao/dadao-machine.c`（回退 `load_elf_ram_sym(...,false,...)` → `load_elf(...)`；+`dadao_elf_check_segments`/`dadao_mapped_regions[]`/大端读取器）；`components/qemu/patches/hw/dadao/dadao-machine.c.patch`（`make_patch qemu` 重导出，585 行）；`components/qemu/changelog.md`；`tools/qemu/min_rom_probe_042t.py`（`neg_seg_out_of_range` 真越界 + 4 例文案断言放宽）；`.work/evidence/QEMU-052t/run.sh`。

**验收结果**（042t 五负例逐例真实 QEMU exit，`QEMU-052t-probe-full.log`）：`neg_bad_flags_ver`→1；`neg_bad_flags_res`→1；`neg_bad_type`→1；`neg_seg_out_of_range` 0→**1**；`oversize_elf_seg` 0→**1** ⇒ **5/5 非零退出** ✅。另 `neg_filesz_gt_memsz`→1。**回归项**：`elf_fill_rom_exact` 上轮 exit=1 → **本轮 exit=0（恢复绿）** ✅。证据脚本 **RUN_EXIT=0**（注入：禁用 `dadao_elf_check_header`+`dadao_elf_check_segments` 调用点 ⇒ `neg_bad_type`/`oversize_elf_seg` 不再被拒 ⇒ 检出 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿；`QEMU-052t-evidence.log`）。

**新发现/坑**：① 上游按 **`p_paddr`** 装载、并把与后段重叠的 `p_memsz` **截断到 `p_filesz`**（`hw/elf_ops.h.inc`）⇒ 越界/超限须**调用前**查、不能依赖 loader；② `load_rom=false` 经 `address_space_write` 写只读 ROM 必失败 ⇒ ROM 段回归，故须回上游默认 `load_elf()`（ROM blob 路径）；③ 契约「不约束文案」⇒ 由上游 loader 承担文本的负例只能断言非零退出。

**遗留问题**：无（① ② ③ 全部调用前自校验；5 负例全非零退出；ROM 段回归已消除）。

## 完成区（D 收窄 · 2026-10-09）

**用户裁定原话留痕（`lessons §7.3`）**：用户指出「我们现在要测的是 **elf 文件的执行，都是装载到 ram 中，没有 rom 的事**」⇒ 追问后选定 **「D 收窄为只允许 RAM（推荐）」**。语义 = **ELF 段只允许落在 RAM**；**落 ROM 窗口的段 ⇒ 加载期非零退出**。①（`e_flags[7:0]==1`）②（`e_type==ET_EXEC`）仍**由我们调用前自校验**（不改上游 `load_elf`）；`load_rom` 之争作废（ROM 段在调 `load_elf` 前就被拒）。

**允许集合（区间 + 依据）**：**仅旧 RAM 段 `0xffff_0000_0000` .. `0xffff_00ff_ffff`（16 MiB）**。依据：`contract-elf §6.1.2` 装载语义 + §6.2「RAM 16 MiB」（来源 `ADR-0004 D2.2/D2.3` rev. 2026-10-06，其时 RAM 只有此窗）；`tests/scripts/dadao.lds` 把 ELF 链到该基址；**实测**：`elf_fill_ram_exact`/`elf_data_bss` 在该窗 exit=0、`test-elf` 5/5。**RAM@0（`0x0`，16 MiB）不纳入**：其为 `ADR-0004 R3`/`QEMU-049t` 引入「供 bootrom/SEE」的 RAM，`-kernel` ELF 路径迁 `0` 属 **R3 step2（未做）**；本任务保持现状（保留旧 RAM 窗、不新增窗，避免引入未测试语义）。**ROM 窗口 `0xffff_ffff_0000`/64 KiB 已从允许集合移除**。

**修改文件**：`.work/source/qemu/hw/dadao/dadao-machine.c`（`dadao_mapped_regions[]` 删 ROM 项 + 注释/错误文案改「仅 RAM」）；`components/qemu/patches/hw/dadao/dadao-machine.c.patch`（`make_patch qemu` 重导出，594 行）；`.tao/knowledge/contract-elf.md`（§6.1.2 装载语义改「仅 RAM；落 ROM 窗口 ⇒ 加载期错误并非零退出」+ §6.1.2/§6.2 两处 over-size 文案同步删 ROM）；`components/qemu/changelog.md`（本任务条目改 D 口径）；`tools/qemu/min_rom_probe_042t.py`（`elf_fill_rom_exact` 改为期望**被拒**）；`.work/evidence/QEMU-052t/run.sh`。

**验收结果（真实）**：`elf_fill_rom_exact` exit **1（被拒，预期）**；`elf_fill_ram_exact` exit 0（仍可运行）；5 负例逐例 exit：`neg_bad_flags_ver`=1、`neg_bad_flags_res`=1、`neg_bad_type`=1、`neg_seg_out_of_range`=1、`oversize_elf_seg`=1（另 `neg_filesz_gt_memsz`=1）。**「ROM 段被拒（预期）」vs「ROM 段装载失败（回归）」区分**：D 下 ROM 段在 `load_elf` 前被我们拒（exit=1）；注入（允许集合改回含 ROM）时该 ROM ELF **运行 exit=0** ⇒ 上游 loader 的 ROM 装载路径仍可用，B′ 的「ROM 段装载失败」回归已消除（`QEMU-052t-evidence.log` 注入段）。门控：`make test-elf` EXIT=0（5/5）、`make check-qemu-semantics` EXIT=0（149/149）、`make check-patch-tree` EXIT=0（92 patches）、`make check` EXIT=0；042t 探针 **21/21**。证据脚本 **RUN_EXIT=0**（注入：允许集合加回 ROM + 禁用两处 callsite ⇒ `elf_fill_rom_exact`/`neg_bad_type`/`oversize_elf_seg` 不再被拒 ⇒ 检出 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿）。

**新发现/坑**：① 上游 `load_elf()` 按 `p_paddr` 装载、并把与后段重叠的 `p_memsz` 截断到 `p_filesz` ⇒ 越界/超限须**调用前**查；② `load_rom=false` 会致 ROM 段装载失败（B′ 回归），故保持上游默认 `load_elf()`；D 下 ROM 段被调用前拒，不再触及该路径；③ 契约「不约束文案」⇒ 上游 loader 承担文本的负例只断言非零退出。

**遗留问题**：无。RAM@0 是否应纳入 `-kernel` ELF 允许集合，留待 `ADR-0004 R3` **step2**（RAM 基址迁 `0`）一并裁定。

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

#### 第 2 轮 engineer 自审（用户裁定后收口）
> **范围**：`dadao_elf_check_header()`（新增）+ `load_elf_ram_sym(...,false,...)` 调用 + run.sh 注入自检。逐行审查 + 真机复验。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F5（上轮延后）`e_flags`/`e_type` 校验 | ✅已修 | 新增 `dadao_elf_check_header()` 于装载前（`offsetof`+大端逐字节，无新依赖）；契约仅追加「文案不约束」一句 | `neg_bad_flags_ver/res`/`neg_bad_type` 均 exit=1；run.sh 断言 rc=0 |
| F6 越界段「立即失败」 | ⚠️部分 | 改 `load_elf_ram_sym(...,&address_space_memory,false,NULL)`；真·越界/单段超限 exit=1 | rootcause.log；但 042t 两例仍不拒（上游 `p_paddr`/截断语义，见遗留） |
| F7 `offsetof`/`address_space_memory`/`load_elf_ram_sym` 可用 | ✅核实 | `osdep.h` 带 `<stddef.h>`；`system/address-spaces.h` 已 include；`loader.h` 已 include | `make build-qemu` EXIT=0 |
| F8 注入自检真实可失败且可还原 | ✅已修 | run.sh `sed` 禁用 callsite（非空注入）→ probe rc≠0 检出 → `cp`+md5 还原 → 回绿 | evidence.log：`inject_effective`/`inject_header_off_detected`/`restore_md5_match`/`restored_green` 全 PASS |
| F9 ROM 段 ELF 回归（新发现） | ⏸延后 | 未改（用户已裁定 `load_rom=false`，取舍超本任务权限） | probe `elf_fill_rom_exact` exit=1；run.sh 标 `[KNOWN]`；完成区遗留③ |

**结论**：F5/F7/F8 已处置；**F6 部分、F9 为上游语义/用户裁定下的已知取舍**，如实记入完成区遗留（未隐瞒）。据派遣「如实报告」⇒ 标 `待验收`。

#### 第 3 轮 engineer 自审（用户裁定 B′ 后收口）
> **范围**：`load_elf()` 调用回退 + `dadao_elf_check_segments()` + 探针 `neg_seg_out_of_range` 修正/文案放宽 + run.sh 注入。逐行审查 + 真机复验。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F10（上轮遗留③）ROM 段回归 | ✅已修 | 回退 `load_rom=false` → 上游默认 `load_elf()`（ROM blob 路径） | probe `elf_fill_rom_exact` exit 1→**0** |
| F11（上轮遗留①②：越界/超限不拒） | ✅已修 | 新增 `dadao_elf_check_segments`：`p_filesz<=p_memsz`/`p_vaddr==p_paddr`/区间∈{RAM,ROM}/无溢出，调前执行 | `neg_seg_out_of_range`/`oversize_elf_seg`/`neg_filesz_gt_memsz` 均 exit=1 |
| F12 探针 `neg_seg_out_of_range` 非真越界（只改 `p_vaddr`，上游按 `p_paddr`） | ✅已修 | 同改 `p_vaddr`(ph1+16) 与 `p_paddr`(ph1+24) 为 `0xFFFF_0200_0000` | probe PASS（`outside the mapped regions`） |
| F13 4 例文案断言与「文案不约束」冲突（文本由上游 loader 承担，非我方可控） | ✅已修 | 新增 `_expect_reject`（只断言非零退出），EI_CLASS/EI_DATA/e_machine/Phdr-oob 改用 | 探针 21/21 PASS；4 例均 exit=1 |
| F14 注入自检须覆盖新 ③ 且可还原 | ✅已修 | run.sh 同时禁用两个调用点 | `inject_effective` + 两例 FAIL + `restore_md5_match`(09e1e988…) + 回绿（`QEMU-052t-evidence.log`） |
| F15 `phentsize`/`offsetof`/大端读取正确、无越界读 | ✅核实 | `offsetof(Elf64_*)` + BE 读取器；`phentsize!=56` 交上游 | `build-qemu`/`make check` EXIT=0；`test-elf` 5/5 |

**结论**：F10–F15 全部处置；5 负例全非零退出、ROM 回归恢复绿、四门控 EXIT=0 ⇒ 标 `待验收`。

#### 第 4 轮 engineer 自审（用户裁定 D 后收口）
> **范围**：`dadao_mapped_regions[]` 收窄为仅 RAM + 相关注释/错误文案 + 契约 §6.1.2 + 探针 `elf_fill_rom_exact` + run.sh。逐行审查 + 真机复验。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F16（用户裁定 D）允许集合须「仅 RAM」 | ✅已修 | `dadao_mapped_regions[]` 删 ROM 项；错误文案改「only RAM … the boot ROM window is rejected」 | `elf_fill_rom_exact` exit=1；`elf_fill_ram_exact` exit=0；门控全绿 |
| F17 探针 `elf_fill_rom_exact` 期望须翻转为「被拒」 | ✅已修 | `c_elf_fill_rom_exact` rc==0 ⇒ FAIL（附 D 依据注释）；docstring 同步 | 探针 21/21；run.sh `probe_assert elf_fill_rom_exact 0` PASS |
| F18 契约 §6.1.2 语义须改「仅 RAM」 | ✅已修 | §6.1.2 装载语义改「仅 RAM；落 ROM 窗口 ⇒ 加载期错误并非零退出」；§6.1.2/§6.2 两处 over-size 文案同步删 ROM（同一语义，为一致性） | 目视三处一致；`make check` EXIT=0 |
| F19 ROM 段「被拒」vs「装载失败回归」须区分 | ✅已修 | 保留上游默认 `load_elf()`；D 下 ROM 段调用前拒；注入（ROM 加回允许集合）演示 ROM 段运行 exit=0 | evidence.log 注入段 `elf_fill_rom_exact … exit=0`（装载路径可用）→ 检出 FAIL → 还原回绿 |
| F20 证据脚本注入须真实可失败且可还原（`cp`+md5） | ✅已修 | run.sh 注入 =「允许集合加回 ROM + 禁用两处 callsite」；`cp`+md5 还原 | `inject_effective`/`inject_rom_readded`/`restore_md5_match`(37784cf1…)/恢复回绿 全 PASS；RUN_EXIT=0 |

**结论**：F16–F20 全部 ✅已修；5 负例全非零退出、`elf_fill_rom_exact` 被拒、`elf_fill_ram_exact` 仍可运行、四门控 EXIT=0、探针 21/21、证据脚本 RUN_EXIT=0 ⇒ 标 `待验收`。

#### 第 1 轮 reviewer 验收

**判决：Accepted**

**证据脚本审核**：`run.sh` 结构合规——`set -u`；`verdict()` 逐项打印期望/实际/rc；`probe_assert()` 捕获 `$rc`（非 `$?` after pipe）；注入用 `sed` 改 callsite（非空）+ `cp`+md5 还原；无 `tee`；结尾 `$FAILED` 判定退出码。负例断言体：`_expect_reject` 检 `rc==0 ⇒ bad("exit=0 (expected non-zero exit)")`——非恒真，FAIL 路径可达。

**重跑**：`bash .work/evidence/QEMU-052t/run.sh` EXIT=0。逐项全 PASS（见 `/tmp/opencode/QEMU-052t-review/run.log`）。

**独立注入反例**：禁用 `dadao_elf_check_segments` 调用 ⇒ `oversize_elf_seg`→FAIL（exit=0, expected non-zero）、`neg_seg_out_of_range`→FAIL → 还原 `cp`+md5=`37784cf1f56ec386ae14dd96901449d7`（相等）→ 重建 → 两探针均回绿 PASS。

**约束逐条核验**：
| 约束 | 结果 |
|---|---|
| ① 改走 `load_elf()` | ✅ `grep 'load_elf('` 存在、`load_elf_ram_sym` 不存在 |
| ② 白名单已移除 | ✅ `grep 'dadao_load_regions'` 无输出（源码+补丁） |
| ③ 允许集合仅 RAM | ✅ `dadao_mapped_regions[]` 只含 `{DADAO_RAM_BASE, DADAO_RAM_SIZE}`，无 ROM 项 |
| ④ `elf_fill_rom_exact` 被拒 | ✅ exit=1（rejected） |
| ⑤ `elf_fill_ram_exact` 仍可运行 | ✅ exit=0 |
| ⑥ 五负例全非零退出 | ✅ `neg_bad_flags_ver`=1, `neg_bad_flags_res`=1, `neg_bad_type`=1, `neg_seg_out_of_range`=1, `oversize_elf_seg`=1 |
| ⑦ 三方一致性（代码注释/契约/探针） | ✅ 代码 L482-492 写「RAM image…ROM window is rejected (user decision D)」；契约 §6.1.2 写「仅 RAM；落 ROM ⇒ 加载期错误」；探针 `elf_fill_rom_exact` 期望被拒。三者一致，无 `ROM blob` 残留 |
| ⑧ 上游 `loader.c` 未改 | ✅ `components/qemu/patches/hw/core/loader.c*` 不存在 |
| ⑨ `git status` | ✅ 仅任务文件（5项），无 `_tmp/_orig/_rej/_preinject` |
| ⑩ 门控 | ✅ `make test-elf`=0, `check-qemu-semantics`=0, `check-patch-tree`=0, `check`=0 |

#### architect 提交留痕（2026-10-09）
- **档位**：正常提交（reviewer 判决 `Accepted`）。
- **提交号**：`4996fd4`（5 files changed, 369(+)/39(−)）。
- **文件集对账（显式 staging，禁 `git add -A`）**：`git diff --cached --name-only` = `contract-elf.md` / `QEMU-052t-load_elf改写.md` / `components/qemu/changelog.md` / `dadao-machine.c.patch` / `min_rom_probe_042t.py`，与任务书「修改文件」可提交项逐条一致；`.work/source/...`、`.work/evidence/...` 为 gitignore 工作产物、不入库。**无漏提 / 多提 / 越界**。
