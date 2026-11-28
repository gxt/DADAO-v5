# m19-testcases-006: hmon 数据槽消费者迁移（0xD8–0xF8 → 0xC00 页）

**模块**：testcases
**项目里程碑**：M19
**依赖**：`m19-testcases-005`、`m19-testcases-004`、`m19-testcases-002`
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：待验收

## 背景

`m19-testcases-005` 已把固件 hmon 的数据槽从 `HMON_BASE + 0xD8/0xE0/0xE8/0xF0/0xF8` 迁到 spec §6.2 的 `0xC00` 数据页：

- `+0x00` cause_id、`+0x08` cause_ip、`+0x10` cause_info、`+0x18` 返回地址、`+0x20` 保存 rd63、`+0x28` 保存 rb63。

但所有**消费者**仍按旧槽读：`tests/inst` 宏与部分用例、`tests/arch/{ptw,umon,time,power}`、`tools/chipyard/excp/*`、`tools/testcases/arch/min_rom_probe_integ007t.py`。不迁会让这些用例读到全零（或读到代码区），`check-arch` 的 `integ007t` 等会转红。

## 目标

1. 统一槽位常量：优先收敛到一处（`tests/shared/asm/machine-tiny.inc` 或等价头），消费者引用常量而不是硬写 `0xE0/0xE8/0xF0/0xF8/0xD8`。
2. 迁 `tests/inst`（宏 `inst_test.inc` 与所有读 hmon 帧的用例）、`tests/arch/**`、`tools/chipyard/excp/**`、`tools/testcases/arch/min_rom_probe_integ007t.py`。
3. 地址按 `HMON_BASE + 0xC00 + 页内偏移`；注意 `rb0` 相对寻址的 `imms12` 限制（必要时用第二基址寄存器或先算地址）。
4. 运行验证：新固件 8 KiB 镜像下，至少覆盖 `ptw`、`umon`、`time`、`inst` 各 1 个用例在 QEMU（与 gem5，若可用）跑通；`check-arch` 的 `integ007t` 不再因槽位失败。

## 验收（逐条贴真实 rc）

1. 全仓 `grep` 不再有「hmon 帧槽」形式的旧偏移（`HMON_BASE + 0xD8/0xE0/0xE8/0xF0/0xF8`）；若有历史说明性引用，须逐条列出并说明不动的原因。
2. 代表用例：`tests/inst` 2 个、`tests/arch` 4 个（ptw/umon/time/power 各 1）在 QEMU 下 rc=0，签名/退出码与期望一致。
3. `make check-arch`（或分模块子集）+ `check-inst-asm` 真实 rc；基线红逐行对照，`integ007t` 的失败若消失须给出前后对照。
4. **可达 FAIL ≥2 路**：① 把某消费者槽位写回 `0xE0` ⇒ 该用例读错、红；② 把固件 `HMON_SLOT_CAUSE_ID` 改 `+0x08` ⇒ 消费者红；均 `cp`+md5 还原回绿。
5. 不改 QEMU/gem5/chipyard 源码；不接板；版本号未升。

## 约束

独立 `git worktree`；**不提交 git**；只动 `tests/**`、`tools/chipyard/excp/**`、`tools/testcases/arch/min_rom_probe_integ007t.py` 与必要索引；完成区不写具体 `.work/**` 路径。

## 范围补充（用户 2026-11-28）

`tests/unit/gem5/tiny_hmon/tiny_hmon_min.S`（`m19-gem5-003` 的遗留，未被其改动）一并迁到 `0xC00` 页；与 `tiny_hmon_layout.inc` 的一致性以 `min_rom_probe_integ007t.py` 的逐值对账表达（该文件在 master 尚无 `HMON_*` 常量，合入后自动生效）。同时修掉该文件阻碍最小路径的保留 rc：`cfx2rd cfx_hmon, cg3, rc10`→`rc15`（ADR-0061 D5）。

## 完成区

**测试结果**：运行期证据目录 `run.sh` PASS=35 FAIL=0；`run.sh --inject` PASS=47 FAIL=0（2 路注入真红 + `cp`+md5 还原回绿）。`run_inst_tiny`（`check-inst-asm` 同驱动）266/274，8 例红与 HEAD 基线**逐行相同**；integ007t PASS（67 checks）；arch ptw/umon/time 各 1 例 rc=0，arch-power-001/002 既有红。

**修改文件**：`tests/inst/` 11（`macros/inst_test.inc`、`01-load-store/*.inc`、`11-cfx/*.S`×7、`12-misc/12-misc.inc`、`MIGRATION.md`）、`tests/arch/` 16（ptw 4、umon 3、time 3、power 3、cache 3）、`tests/shared/asm/machine-tiny.inc`、`tests/unit/gem5/tiny_hmon/tiny_hmon_min.S`、`tests/case-ledger.tsv`、`tests/data/inst-signature/{expected.tsv,inputs.sha256}`、`tools/testcases/{arch/gen_machine_inc.py,arch/min_rom_probe_integ007t.py,lib/machine_profile.py,lib/build_test_binary.py}`、`tools/chipyard/{excp/causeid.S,excp/prevcfx.S,dcache/vastdcache.S}`。

**验收结果**：
1. 旧槽引用 226 处/27 文件 → 0（帧槽形式 grep；见 `run.sh` 的两条断言）。未动的两处已列明：`tests/ee-vast/power_vast.S:85`（Vast 固件死写，Vast hmon 走 `rc10`/`FAULT_RECORD`；不改固件）与 `tests/unit/gem5/tiny_hmon/tiny_hmon.S`（`m19-gem5-003`）。
2. 常量单点：数值源 `machine_profile.HMON_DATA_OFF/HMON_DATA_BASE/HMON_FRAME`；`gen_machine_inc.py` 生成 `machine-tiny.inc` 的 `HMON_DATA_BASE`/`HMON_FRAME_*`（`--check` rc=0）；asm 消费者一律引用（`HMON_BASE+0xC00` 越 `imms12` ⇒ 消费者改用数据页基址寄存器 + 页内小立即数）。
3. 代表 rc：`trap_ciii_cfx`/`cfxtrap_deny_cfxperm`/`cfx2rc_crrr_cfx`=0；`arch-ptw-001`/`arch-umon-001`/`arch-time-001`=0；`arch-power-001` 红因驱动 `-d cpu` dump 超上限（MEMORY 已登记基线红）。
4. 注入：① `trap_ciii_cfx.S` 的 `__CHECK_MEM 2` 改读 `HMON_BASE,0xE0` ⇒ rc=2（checkpoint 2）红；② 固件 `HMON_SLOT_CAUSE_ID 0x00→0x08`（构建器同常量随动，否则构建期先拒）⇒ rc=2 红；两次 `cp` 还原 md5 相等且回绿。
5. 静态门控：`check-case-ledger`/`check-inst-macro-scope`/`check-tests-index`/`check-inst-sig --data-only`/`run_arch --self-test` rc=0。`make check-inst-asm` 实测 rc=2（0/274）：该目标用**共享安装根**的 qemu，而安装根仍是 M19 前旧二进制（`-M help` 自述 64 KiB），见待裁定 1。

**新发现/坑**：① 安装根 qemu 未随 `m19-qemu-001` 重建 ⇒ 所有用安装根的门控/M19 用例在旧二进制上假红（本任务改用任务内 8 KiB qemu，md5 `0b22a516…`）。② llvm-mc 对 `.equ` 重定义**静默接受**（异值也接受、后定义生效）⇒ Vast-only 探针可 include `machine-tiny.inc` 而不删局部 `.equ`，但此类覆盖无告警。③ integ007t 应用腿原红两层：槽（本任务）+ `tiny_hmon_min.S` 读 `cg3 rc10`（ADR-0061 D5 后保留 ⇒ CFXREG）。④ 槽迁移不改签名语义：`check_inst_sig --write` 只改 `inputs.sha256` 11 行。⑤ `cfx2rd_crrr_cfx` 的 hmon/power `cg7 rc2` 仍按 64 KiB（M19 几何遗留），按 spec 改 `0x2000`（4 个期望值）。⑥ `run_inst_tiny --id` 收 `.S` stem，不是 `tests/inst.yaml` 的 id。

**遗留问题**：① 8 例 `stm.*_rrri_*` 挂死（rc=-2）：HEAD 基线**同 checkpoint/同 rc**，非本任务引入（多元素 store，需另立任务）。② `arch-power-001/002` QEMU 红（dump 上限）。③ `gen_ptw_sig_tables --selfcheck` 既有红（`expected-divergences.yaml` 登记未清，HEAD 同）。④ `tools/chipyard/excp/prevcfx.S` 用旧 `escape cfx_hmon, [excp_cause_ip,0]` 语法，llvm-mc 拒绝（HEAD 同）⇒ 该 RTL 探针不可汇编。⑤ `tests/unit/gem5/tiny_hmon/{tiny_hmon.S,expected.yaml}` 仍旧槽（`m19-gem5-003`）。

## 待裁定

1. **共享安装根 qemu 重建**：本任务只在任务内用自编 8 KiB qemu 验证、未改 `.dadao` 安装根，故 `make check-inst-asm` rc=2。是否由主会话按 AGENTS §4「组件补丁重建」重建 qemu 并 `install-host`（影响所有 M19 会话的 L2/L3）。
2. **`tiny_hmon_layout.inc` 的 `HMON_*` 常量**：master 版无这些常量（`m19-gem5-003` 分支有，值 `0xC00`/`0x00…0x28` 与本任务一致）；`min_rom_probe_integ007t.py` 已内置逐值对账，该文件合入后自动生效。
3. **`stm` 挂死 / power dump 上限**：属 M19 几何/性能类遗留，本任务只登记；是否另立任务承接。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审阅全部改动 + 复跑证据脚本。findings（全部有真实复验）：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 生成器把 `FAULT_RECORD` 挪到 `HMON_BASE` 之后 ⇒ `machine-vast.inc` 无谓 churn | ✅已修 | Vast 分支保持原位置，帧槽只在 `fault_record is None`（Tiny）时追加 | `git diff --stat tests/shared/asm/machine-vast.inc` 为空；`--check` rc=0 |
| F2 `run.sh` 用 `git diff --numstat` 判"注入生效"（文件本就有未提交改动 ⇒ 恒真） | ✅已修 | 改为「注入后 md5 ≠ 备份 md5」 | `--inject` 两条 `injected content differs` PASS |
| F3 `run.sh` 调 `make build-bootrom` 会抢共享 gate 锁（与并行会话串行、长时间阻塞） | ✅已修 | 改为直接跑 make 配方里的底层命令（`build_step5`） | `run.sh` 35/35 PASS，零 gate 等待 |
| F4 asm 列表含需生成表的载体（ptw_sig/ptw_walk/cache_rtl/vastdcache），首版假红 | ✅已修 | 先跑 4 个表的生成器，再把生成目录加进 `-I` | `representative carriers assemble` PASS |
| F5 `power_vast.py` 的 `slot_asm` 也写旧槽（首轮漏改） | ✅已修 | 同改常量（该函数只被 RTL 生成器使用） | `check_power_rtl --selfcheck` PASS |
| F6 integ007t 的槽位指令字表是手写常量（改槽即漂） | ✅已修 | 改为由 `bld.HMON_DATA_BASE/HMON_SLOT_*` 计算（`_ldst` 带 `imms12` 掩码）+ 逐条注释 | 9 条 `layout word` PASS；注入②使其红 |
| F7 `tiny_hmon_min.S` 读 `cg3 rc10`（ADR-0061 D5 后保留）⇒ 应用挂死、integ007t 应用腿红 | ✅已修 | `rc10`→`rc15`（向量寄存器重编号） | integ007t 67 checks PASS；HEAD 版同参数仍挂死 |
| F8 `cfx2rd_crrr_cfx` 的 4 处 `0x10000` 期望按旧 64 KiB 几何 | ✅已修 | 改 `0x2000`（`spec/Kaiwu §1.1/§6.2`）+ 重生成 `expected.tsv`/ledger | 该用例 rc=0；`check-inst-sig --data-only` PASS |
| F9 `prevcfx.S` 用旧 `escape cfx_hmon, [excp_cause_ip,0]`（llvm-mc 拒绝） | ⏸延后 | —（HEAD 同样失败，属 m16-chipyard-023 资产，RTL 专用） | `git show HEAD:…` 汇编同样报错 |
| F10 8 例 `stm.*_rrri_*` 挂死 | ❌不修 | — | HEAD 基线同 checkpoint/同 rc（逐行对照） |

边界与未测输入复核：`layout_inc_slots` 对缺文件/缺 `HMON_*` 常量都会退化为 SKIP（不假绿）；`_ldst` 对 `imm` 取 `&0xFFF` 防越 `imms12`；数据页基址一律经 `set.rb`（48 位）而非 `rb0+imms12`。
判决：findings F1–F8 已修并复验，F9/F10 有证据延后/不修 ⇒ 状态置「待验收」。

### 第 1 轮 reviewer 验收（2026-11-28）

**重跑记录（reviewer 亲自执行，退出码如标）**：
1. 仓库根执行运行期证据目录内 `run.sh` ⇒ `PASS=35 FAIL=0` rc=0；`run.sh --inject` ⇒ `PASS=47 FAIL=0` rc=0（`cons/fw: consumer must go red actual=1`、两路 `cp restore md5` 相等且回绿）。
2. 独立注入（非脚本内置两路）：`tests/arch/ptw/ptw_regs.S` 的 `d1_resume` 槽读改回 `[rb20,0xE0]` ⇒ 同一脚本 `FAIL old-slot offset references expected=0 actual=1` rc=1；`cp` 还原 md5 `7718ad3e…` 相等 ⇒ 重跑回 `PASS=35` rc=0。
3. 旧槽 grep（`HMON_BASE+0xD8..` 与 `[rb20|21|22|25,0xD8..]` 两形式）：父 8030a321b `226 处/27 文件` → 当前 `0`；余 `tests/ee-vast/power_vast.S:85`（Vast 固件死写，`hmon_vast.S` 走 FAULT_RECORD/rc10 不读该槽）与 `tests/unit/gem5/tiny_hmon/tiny_hmon.S`（m19-gem5-003 的 7646279ba 改该文件但**未合入**本分支，`merge-base --is-ancestor`=NO）——两处理由成立。
4. `gen_machine_inc.py --check` rc=0；跑生成器重写后 `git status` 空、`machine-tiny.inc` md5 未变 ⇒ 无手改生成物。
5. 全量 inst（任务内 8 KiB qemu + 8 KiB bootrom，jobs=62）：本分支 `266/274`、8 红全为 `stm.*_rrri_*` rc=-2；父 commit 对照树同参数 `10/274`，其中 stm 8 行与本分支 **diff 逐行相同**（同 checkpoint 同 rc）⇒ 8 例非本任务引入。
6. integ007t：父树 rc=1（layout 8 FAIL + QEMU timeout，13 checks 中 5 PASS）→ 本分支 `PASS (67 checks)` rc=0；「前 11/16 FAIL」口径复现不出（实测 5 PASS/8 FAIL+timeout），前红后绿方向成立。
7. `make check-inst-asm` rc=**2**、0/274；writer-guard 显示安装根 qemu md5 `e470dc5619…`（`-M help` 自述 64 KiB）+ bootrom `f8ef553e…`（8192 B，与任务内同）⇒ 全红确因旧 qemu，归因成立。
8. `arch-power-001`：本分支与父树同红（`-d cpu` dump 超上限，135142202/135266304 仅波动；MEMORY 2026-11-27 已登记）⇒ 豁免有据。
9. `prevcfx.S`：当前/HEAD/父三者 llvm-mc 同 3 error、rc=1、错误集仅文件名差异 ⇒ 与 HEAD 同红。

**约束核验**：commit 40 文件 = 39 在册 + 任务书；39 个全落 `tests/**`、`tools/testcases/**`、`tools/chipyard/**`；未改 `tests/ee-tiny|ee-vast`、QEMU/gem5/chipyard 上游源码、`spec/`、`.tao/contracts/`（版本号未升）；验收前后 `git status` 均空、注入文件 md5 全部还原。

**Findings（不阻断，architect 收尾处置）**：
- F-a：约束字面清单窄于实际 4 文件（`tools/chipyard/dcache/vastdcache.S`、`tools/testcases/{arch/gen_machine_inc.py, lib/machine_profile.py, lib/build_test_binary.py}`），均为验收 2 常量单点/消费者迁移必需且完成区已披露 ⇒ 建议 architect 补一句范围修订。
- F-b：完成区「ADR-0061 D5」应为 **R3**（`excp_vector rc10→rc15`、原 rc10 reserved ⇒ CFXREG；D5 是掩码归 monitor）——依据本身成立。
- F-c：「前 11/16 FAIL」复现为 5 PASS/8 FAIL + QEMU timeout（对话口径，非完成区判据）。

**判决：Accepted**——验收 1–5 在 reviewer 独立重跑下全部达成（两路脚本注入 + 一路独立注入均真 FAIL 后 `cp`+md5 回绿）；8 例 stm 红经父树逐行对照确认非本任务引入；无凑绿（`expected.tsv` 4 处 `0x10000→0x2000` 有 `spec/Kaiwu §1.1/§6.2` 8 KiB 几何依据，且该例基线本红 rc=10）。
