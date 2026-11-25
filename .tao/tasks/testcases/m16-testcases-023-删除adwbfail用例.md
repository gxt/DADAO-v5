# m16-testcases-023: 删除 ADWBFAIL 用例（页表必须在内存；`DIV-14`/`DIV-04` 收口）

**模块**：testcases
**项目里程碑**：M16
**依赖**：`m16-chipyard-018`（007 现状）、`m16-chipyard-022`（pmem）
**可并行分片**：否（共享 `tests/arch/ptw/`）
**预估**：1–2 h
**档位**：中改（复核 ≤40 min）
**状态**：待验收

## 背景（用户 2026-11-25 裁定）

1. **页表必须放在内存里，用的是内存的物理地址**（不能放 BootROM/只读镜像）。
2. **不构建 ADWBFAIL 的测试用例**。

据此，`arch-ptw-007` 的 `flush_adwbfail` 子项（槽 2/3）**在三个平台上都不成立**：QEMU/gem5 原来靠"页表放只读 BootROM"构造 A/D 回写失败，违反第 1 条；RTL 的 PA RAM 全可写，构造不出。`DIV-14`（RTL 不可观测）与 `DIV-04`（ADWBFAIL 不单列用例）随之收口。

## 要做

1. **删用例**：从 `tests/arch/ptw/` 的 `arch-ptw-007` 移除 `flush_adwbfail` 子项（`ptw_sig.S`/`ptw_carrier_tlb.py`/`ptw_sig` 生成器/`expected.yaml`/`rtl-coverage.yaml`），槽数由 4 降为 2（只留 `flush_ok`）；`expected.yaml`/`gen_*`/`--selfcheck` 双向一致。
2. **登记收口**：
   - 删除 `expected-divergences.yaml` 的 `DIV-14`；
   - `DIV-04` 改写为"ADWBFAIL 不做用例（用户裁定：页表必须在内存 + 不构建 ADWBFAIL 用例）"，状态 `closed`/`wont-fix`（按 schema 支持的方式）；
   - `ISS-515` 关闭（`wont-fix`，理由同上）；`tests/arch/README.md`/`vast-arch-inventory.md` 的未覆盖项同步。
3. **RTL `ptw_tlb.S` 的 `CASE_OR` 手工注入**：不再是"用例覆盖"来源；按新口径处置——**保留为实现的内部证据可、但不得在文档/完成区声称它覆盖 ADWBFAIL 用例**（若删除该注入段，需说明它对 `ptw_tlb` 其它检查点无影响）。
4. **不回归**：`arch-ptw-001/002/006` 其它 signature/guest 用例、`arch-ptw-013`（known-red 待 `m16-testcases-022`）、`014/015` gap；QEMU/gem5/RTL 逐槽。

## 不做

- 不改 spec/契约（第 1/2 条是用户裁定，已可由现有 §4.5/§2.2 解释）；
- 不改 RTL/spec 的 A/D 回写语义；
- 不新造 ADWBFAIL 用例。

## 约束

- 独立 `git worktree`；**不提交 git**；只动 `tests/arch/ptw/**`、`tests/arch.yaml`、`tests/arch/modes.yaml`、`expected-divergences.yaml`、`tests/arch/README.md`、`vast-arch-inventory.md`、`tests/arch/common/env-MIGRATION.md`（用户 2026-11-25 追加）、本任务书；
- 不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. `arch-ptw-007` 只剩 `flush_ok` 两槽，三方（QEMU/gem5/RTL）逐槽一致；
2. `DIV-14` 已删、`DIV-04` 改写并关闭、`ISS-515` 关闭、文档无"ADWBFAIL 用例覆盖"表述；
3. **可达 FAIL ≥2**：注入"把 `flush_adwbfail` 加回" ⇒ `--selfcheck`/run_arch 红；注入"页表放只读镜像" ⇒ 判据红（或在文档登记为何不再允许）；`cp`+md5 还原回绿；
4. `check-tests-index`、`check-tasks`、`check-knowledge-refs`、`run_arch --self-test`、`check_issues` 记录 rc。

## 完成区

**测试结果**：证据脚本（运行期证据目录内 `run.sh`）**82 PASS / 0 FAIL，rc=0**，flake 重试 0。分节：运行位置 1、A 删除面 9、B 登记收口 3、C 三方逐槽 48（8 case × 3 平台 + 逐槽/逐字节断言）、D 门控 5、E 注入 16（4 路）。`007` 三方 = `d00000006000ffed 99aabbccddeeff00` 逐字节（= 生成器现场 2 槽）；`002/006/013` 三方逐字节相同；`001/009/011` 0 槽；`015` QEMU/gem5 rc=0、RTL rc=77（gap 不变）。gem5 md5 `6e9b68e7…`（默认构建），Vast sim md5 `1260b0f0…`，每 RTL case ≈38 s。
**修改文件**：`tests/arch/ptw/{ptw_carrier_tlb.py,ptw_sig.S,ptw_tlb.S,expected.yaml,rtl-coverage.yaml,gen_ptw_sig_tables.py,check_ptw_rtl.py,check_tlb.py,README.md}`、`tests/arch.yaml`、`tests/arch/{expected-divergences.yaml,README.md,modes.yaml,vast-arch-inventory.md,common/env-MIGRATION.md}`、本任务书；运行期证据目录内的 `run.sh` / `check_no_rom_pt.py` / `check_slots.py`（gitignored）。未提交。
**验收结果**：① **case 15→14**：删 `arch-ptw-014`（`expected.yaml`/`arch.yaml`/`modes.yaml`/`rtl-coverage.yaml`），载体删 `_c014`/`_three_entries`/`ROM_L2*`/`Check.image_at` 与 `build_image` 的只读镜像接缝；`PTW_CASE=1..13` 对应 001–013，015 是 gap、无 RTL 镜像 ⇒ 编号无空洞（`ptw_sig.S` 头注明）。`rtl-coverage` 14 条 = signature 4 / guest 9 / **gap 1（只剩 015）**；三份 `--selfcheck` rc=0。② **007** 仍只 `flush_ok` 2 槽，qemu/gem5/RTL 逐字节相同；`flush_adwbfail`、`arch-ptw-014`、`DIV-14` 在用例代码/清单 0 命中；`DIV-04`=wont-fix、`ISS-515`=closed、无 chipyard 逐槽例外。③ **注入 4 路**（`cp`+md5，md5 均相等）：加回 `flush_adwbfail` ⇒ 静态+carrier selfcheck 双红；015 用 `image_at` 加回只读叶 PTE ⇒ `check_no_rom_pt` 红（ROM 叶 PTE 位置 `0x3ffff8` 非 0）；重登记 `DIV-14` ⇒ gen/check_ptw_rtl 双红；加回 `arch-ptw-014` ⇒ 静态+selfcheck+case 数（15）三红。④ 门控：`run_arch --self-test` 0、`check-tests-index` 0（503 条，较前 −1）、`check-tasks` 0、`check-knowledge-refs` 0、`check_issues` 0。⑤ 文档同步：`env-MIGRATION.md` 改「015 只读内存窗口；007/014 已删，载体不再有只读页表」；`modes.yaml`/两份 README/inventory 的 014 与只读页表表述清掉。
**新发现/坑**：① **共享 gem5 被并发重建**：22:57 时 `.work/source/gem5/build/DADAO/gem5.opt` 变成 41.8 MB 非 ELF/不可执行，gem5 腿一度全红（002/006/007 断言失败、009/011 偶发）——非本任务代码；22:58 完成后用默认路径复跑全绿（md5 `6e9b68e7…`），期间用同源 `gem5-m16-025` 完整构建（md5 `24d41d4f…`）跑通作对照。② `run.sh` 运行中改脚本会让 bash 读到半截（第 1 次 `unexpected EOF`）；不边跑边改。③ 静态删除面 grep 必须排除注释行（014 的「已删」叙述在注释里），否则误报。④ `check_ptw_rtl --selfcheck` 的「RTL 差异」核对只在生成器登记 case 时才比，`RTL_DIVERGED_SLOTS={}` 会漏「yaml 重登记 DIV-14」⇒ 已补反向检查。⑤ 新 worktree 缺 `.dadao`/`.work`（`install-dirs.lock.toml` 是相对路径），临时软链主仓安装根后门控才绿（未入库）。
**遗留问题**：① 共享 gem5 构建由其它会话改写（已恢复）；复核时若再遇非 ELF/部分文件，用 `GEM5=<完整构建>` 并记录 md5（脚本已支持）。② `run_arch --cfx 4 --platforms chipyard` 仍因 `ISS-m16-010`（缺 `--mode`）rc=1（属 024），本任务直调 `check_ptw_rtl.py` 绕开。③ inventory 的 010/019 基线注仍写「15 条」（历史快照不改写）；023 注已记录 15→14。④ `PTW_CASE` 编号：015 若将来提升为 signature，可取编号 14（当前 1..13 无空洞）。

## 审阅记录

### 第 1 轮 engineer 自审

范围：`git diff` 的 12 个文件 + 3 个证据脚本；逐行核对槽序/期望值/双重核对路径；三方逐槽与注入均实跑（第 3 次 `run.sh`，79 PASS / 0 FAIL）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 007 的槽序/槽数须与三方同一组值：`SIG_BEGIN`/`SIG_DUMP` 均 2、gen `expected_slots(7)` 2 槽、yaml 2 槽 | ✅已修 | `ptw_sig.S` case 7、`gen_ptw_sig_tables.py`、`expected.yaml` | 三份 `--selfcheck` rc=0；三方签名逐字节 = 现场 2 槽 |
| F2 删 `rom_at` 后须无残余调用方；`image_at` 仍被 014 使用，不能误删 | ✅已修 | carrier 删 `rom_at` + `_ROM_*`，保留 `image_at` | `grep "rom_at\|_ROM_"` 0 命中；`check_007` 建镜像绿；014 QEMU/gem5 rc=0、RTL rc=77 |
| F3 删 `DIV-14` 后「无差异却重登记」必须能被检出（原检查只在生成器登记 case 时才比） | ✅已修 | gen `selfcheck` 新增「`registered` 非空且 `RTL_DIVERGED_SLOTS` 为空 ⇒ FAIL」 | E3 注入 ⇒ gen + check_ptw_rtl selfcheck 双 rc=1；还原后 rc=0、md5 相等 |
| F4 用例名 `tlb_flush_adwb_fail` 仍暗示 ADWBFAIL 覆盖 | ✅已修 | carrier `@case` 名 + `expected.yaml` 的 `only:` → `tlb_flush_ad` | carrier selfcheck 双向核对 rc=0（名不符即 FAIL） |
| F5 文档同步：`DIV-14`（README/inventory/rtl-coverage/check_ptw_rtl docstring）与「007 要只读页表」（modes/ptw README/carrier 注释） | ✅已修 | 上述 8 处 | B2「覆盖」叙述 = 0；`DIV-14` 仅剩「已删除」叙述 |
| F6 `CASE_OR` 保留但不得声称覆盖用例 | ✅已修 | `ptw_tlb.S` 头部注明「实现层内部证据、不构成用例覆盖（DIV-04）」 | `check_ptw_tlb --self-test` 27/27；`check_ptw_walk --self-test` 19/19 |
| F7 证据脚本每条断言须可达 FAIL | ✅已修 | 三路注入（cp+md5、EXIT trap 还原） | E1a/E1b/E2/E3a/E3b 实测非零 rc，还原后回绿；md5 三次相等 |
| F8 014 的只读叶 PTE 属同口径冲突 | ⏸延后 | 未改（范围外，且要求 gap 不回归） | 完成区「遗留问题①」，待架构师/用户裁定 |
| F9 `env-MIGRATION.md:14` 陈旧表述 | ⏸延后 | 未改（不在允许文件清单） | 完成区「遗留问题②」 |

判决：F1–F7 已修并复验；F8/F9 为范围外延后项、已披露 ⇒ 状态 `待验收`。

### 第 2 轮 engineer 自审（用户追加裁定：014 同口径收口）

范围：本轮 16 个改动文件的 diff 逐行核对；`run.sh` 实跑 **82 PASS / 0 FAIL**（flake 0，默认 gem5 md5 `6e9b68e7…`、Vast sim md5 `1260b0f0…`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F8（上轮延后）014 用只读 ROM 叶 PTE 构造 ADWBFAIL，同口径必须删 | ✅已修 | 删 `_c014`/`_three_entries`/`ROM_L2*`/`L2C`/`DX..VZ`；`expected.yaml`/`arch.yaml`/`modes.yaml`/`rtl-coverage.yaml` 各删 014 | 14 条 case（001–013、015）；`check_ptw_rtl --selfcheck` 14 = sig 4 / guest 9 / gap 1；015 RTL rc=77 |
| F9（上轮延后）`env-MIGRATION.md:14` 陈旧 | ✅已修 | 改为「015 只读内存窗口；007/014 已删，载体不再有只读页表」 | `check-knowledge-refs` rc=0；已列入变更集 |
| F10 014 删后 `image_at`/`build_image` 的只读镜像接缝成孤儿 | ✅已修 | 删 `Check.image_at`、`build_image` 的 `image_at` 参数与重叠检查；`check_no_rom_pt` 断言源码无 `image_at/rom_at/ROM_L2` | 载体 grep 0；E2 注入 ⇒ rc=1 |
| F11 `PTW_CASE` 编号可能留空洞 | ✅已修（说明） | 1..13 = 001–013，015 是 gap、无 RTL 镜像 ⇒ 无空洞；`ptw_sig.S` 头注明 | `check_ptw_rtl --selfcheck` 14 条；`PTW_CASE` 定义未改 |
| F12 计数/文档一致性（15→14） | ✅已修 | 两份 README、inventory（含 023 注）、modes/carrier/expected/rtl-coverage 头 | A2 现场派生：yaml 14 / rtl-coverage 14 / arch.yaml 14；`check-tests-index` 503（−1） |
| F13 静态检查不得再把「014 仍用 ROM 叶 PTE」当合法；补注入 | ✅已修 | 新 `check_no_rom_pt.py`（14 case、无 014、无只读镜像面、007/015 的 ROM 叶 PTE 位置为 0）+ E4「加回 014」三断言 | E4a/E4b/E4c 注入后 rc=1；还原 md5 相等、回绿 |
| F14 gem5 腿受并发构建影响（共享 `.work`） | ⏸延后（环境） | 不改共享构建；脚本校验 `GEM5` 可执行并支持覆盖 | run7（`gem5-m16-025` md5 `24d41d4f…`）/ run8（默认 md5 `6e9b68e7…`）均 82/0 |
| F15 偶发 flake 未被记录 | ✅已修 | `run_sim` 失败重试 1 次并打印 flake 次数（ISS-m16-011 口径） | run8 flake=0；run6（并发构建期）曾记 3 次 |

判决：F8–F13、F15 已修并复验；F14 属共享环境、已绕行并披露 ⇒ 状态 `待验收`。

### 第 1 轮 reviewer 验收

范围：16 个改动文件逐行读 + 运行期证据目录内 `run.sh`/`check_slots.py`/`check_no_rom_pt.py` 审读；在任务 worktree **独立重跑 3 次**（不采信完成区）+ **独立注入 1 路**（改脚本未碰的 `rtl-coverage.yaml`）。

**重跑记录（我本人，仓库根，运行期证据目录内的 `run.sh`）**
- run1（23:11:12→23:16:24）：**82 PASS / 0 FAIL，rc=0，flake=0**。`007` 三平台二进制 md5 同为 `063c4fa0…`、槽值 `d00000006000ffed` / `99aabbccddeeff00`（三方逐字节）；`002/006/013` 三平台逐槽 = 现场期望且两两 `cmp` 相同；`001/009/011` 三平台 rc=0；`015` QEMU/gem5 rc=0、RTL rc=77；`check_ptw_rtl --selfcheck` = **14 条 = sig 4 / guest 9 / gap 1（只剩 015）**；D 段 `run_arch --self-test`、`check-tests-index`（**503** = inst274+arch39+unit187+tset3）、`check-tasks`、`check-knowledge-refs`、`check_issues` 全 rc=0；E 段 4 路注入全红 → `cp`+md5 相等 → 回绿。
- 独立注入（我，`rtl-coverage.yaml` 007 `signature→gap`，备份 `477f9ee9…`）：run.sh **rc=1**、5 条 FAIL（A2 结构 rc=1、A3 selfcheck rc=1、RTL 007 rc=77、slots 与 `qemu ≠ rtl`）；`cp`+md5 还原（`477f9ee9…` 相等）⇒ 第 3 次 run.sh **82 PASS / 0 FAIL / rc=0 / flake=0**。
- `run_arch --cfx 4 --platforms chipyard`：**rc=1**，14 条驱动均 rc=2，根因日志 `check_ptw_rtl.py: error: unrecognized arguments: --mode hmon` ⇒ **`ISS-m16-010`**（既有基线红，属 024），非本任务；头部 `cases=14`。

**删除面/计数**：007 仅 `flush_ok` 1 检查 2 槽；014 整条删除（`_c014`/`_three_entries`/`ROM_L2`/`image_at`/`rom_at`/`tlb_control_stop`/`tlb_flush_adwb_fail` 在 `tests/` 全 0 命中）；case **15→14**（`expected.yaml`/`arch.yaml`/`modes.yaml`/`rtl-coverage.yaml` 现算 14）；gap 只 015；`PTW_CASE` 1..13 无空洞且 `ptw_sig.S` 头注明；两份 README、inventory、`env-MIGRATION.md` 活动表述均 14。

**登记**：差异清单 `DIV-14` 0 命中；`DIV-04` = `wont-fix` + impact「不做用例」+ `user_ruling 2026-11-25`；`ISS-515` = `closed`/`won't-fix`；全仓无「`CASE_OR`/`CASE_ADWB` 覆盖 ADWBFAIL 用例」正向表述（仅「不构成用例覆盖」）；`ptw_tlb.S` 头写明实现层内部证据。

**约束核验**：16 个改动文件全在允许清单、无未跟踪文件、无注入残留（4 个被注入文件 md5 与开工快照逐一相等，`git status` md5 同 `701a62bb…`）；任务书无禁写运行期路径（唯一 `.work/` 引用在 `.work/source/**`，门控显式豁免）；无「银行」；未提交 git。

**发现（不阻断，请 architect 收尾改）**：① inventory 收口注「签名槽 10 → 8」与现场 13 → 11（`run_arch --self-test` 报 14 case/11 槽）不一致，疑只计 002/006/007；② `run.sh` 的 `[ -x "$GEM5" ]` 只校验可执行位，「可执行但截断的非 ELF」拦不住（现 `gem5.opt` 737 MB ELF、md5 `6e9b68e7…`）；③ flake 计数把注入导致的 rc=77 也当重试（我的注入轮 flake=1 即此），真实 flake 以干净轮为准 = 0。

**环境事件**：构建目录 mtime 22:47–22:56、`gem5.opt` 22:58:32 重写为 737 MB ELF（md5 `6e9b68e7…`）；工程师 run6（22:56 收）gem5 腿 9 FAIL/3 重试，run7/run8 全绿 flake=0；`run.sh` 支持 `GEM5=` 覆盖并校验可执行 ⇒ 事故记为共享环境、未计入本任务失败（完成区已披露；41.8 MB 非 ELF 的瞬时现场已恢复，无法复核该具体数字）。

**判决：Accepted**（验收命令在我自己的重跑下全绿、约束无违反；证据为我本人输出。供架构师终审）。
