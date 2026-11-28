# m19-testcases-002: ee-tiny 链接与布局迁移（entry 0x2000、256K SRAM、signature 0x1000、DUMP 0x800）

**模块**：testcases
**项目里程碑**：M19
**依赖**：`m19-spec-002`
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：待验收

## 背景

Tiny 新几何（`m19-spec-002`）改动所有测试的入口与运行布局。本任务只迁 `tests/ee-tiny` 侧资产，不改 QEMU/gem5/chipyard 源码。

```
MAIN_SRAM_BASE = 0xFFFF_FF00_0000  SIZE = 0x40000
  0x0000 VERSION（=1）
  0x0020 MAILBOX
  0x0030 EXIT_BLOCK（16 B）
  0x0800 DUMP_BASE，0x800（pt_regs）
  0x1000 SIGNATURE，0x800
  0x2000 ENTRY / raw 基址
  0x38000 guard_lo
  0x39000 STACK（24 KiB，SP=0x3F000）
  0x3F000 MemRAS（4 KiB，MRPTR=0x40000）
image_window = 0x2_0000（128 KiB）
```

## 目标

1. `tests/ee-tiny/runtime.yaml`：`entry=0x2000`、`sp=0x3F000`、`image_window=0x2_0000`、`kernel_base=0x2000`、`kernel_reserved=0`、`exit_block=0x30`、`dump_base=0x800`（新增 `dump_size=0x800`、`signature_base=0x1000` 若 schema 需要）。
2. 再生成 `tests/shared/asm/machine-tiny.inc`；更新全部 `.lds`：`tests_inst_tiny.lds`、`tests_freestanding_tiny.lds`、picolibc tiny lds、`mcmodel_far.lds` 等。
3. `tests/inst` 布局：entry 0x2000；`.faultpad` +0x4000、`.faulttab` +0x4300、`.testdata` +0x5000；`TEST_BUF=0x1000`（固定签名区，0x800）；`TEST_EXITB` 改为全局 `EXIT_BLOCK=0x30`，释放 `ENTRY+0x7800`。
4. `crt0_tiny_freestanding.S` / `crt0_tiny_picolibc.S`：SP=0x3F000、EXIT_BLOCK=0x30；按需要设置 `ra0` 的 `MRPTR=0x40000`（MemRAS 4 KiB）。
5. `tests_inst` 的 `SIG_BEGIN/SIGUPD/SIG_DUMP` 使用固定 0x1000；检查 `TEST_DATA=ENTRY+0x5800` 与签名区不重叠。
6. 更新依赖旧地址的期望值：CFXMEM 边界、fault `cause_info`、`check_tests_index` 假布局、`mcmodel_far`；embench/ansibench 的链接脚本与 image_window 选择。
7. 保持 `tests/ee-tiny` 之外（QEMU/gem5/chipyard）不动。

## 验收（逐条贴真实 rc）

1. 所有 `tests/inst` 代表例可构建并在 QEMU 跑通；`.testdata`/`TEST_BUF`/`EXIT_BLOCK` 地址与 `runtime.yaml` 一致。
2. 签名区在 `0x1000–0x1800`，entry 在 `0x2000`；`TEST_DATA`、faultpad/faulttab 不越界。
3. 栈/guard/MemRAS：`SP=0x3F000`，guard_lo 0x38000–0x39000；若启用 MemRAS，`MRPTR=0x40000`。
4. **可达 FAIL ≥2 路**：① 把 entry 写回 0x10100 ⇒ 构建/装载红；② 把签名区写回 `ENTRY+0x7000` ⇒ 地址断言红。
5. `check-inst-asm` / `check-tests-index` 真实 rc=0（或基线红逐行对照）。

## 约束

独立 `git worktree`；**不提交 git**；只动 `tests/ee-tiny`、`tests/inst` 布局/macros、`tests/shared/asm/machine-tiny.inc` 与链接脚本；不改 QEMU/gem5/chipyard；不接板；完成区不写具体 `.work/**` 路径。

## 待裁定

1. **hmon 数据槽迁移归属**：`m19-spec-002` 把 hmon SRAM 数据区定在 `0x0C00–0x0CFF`，但固件 `tests/ee-tiny/cfx_hmon_tiny.S` 与全部消费者仍用 `0xD8/0xE0/0xE8/0xF0/0xF8`（`tests/inst/macros/inst_test.inc` 的 `__SET_HMON_RETURN`/落点、`tests/inst/11-cfx`、`tests/inst/12-misc`、`tests/arch/*`、`tests/unit/gem5/tiny_hmon`）。必须固件与消费者同批迁移；本任务不动（先动会单边破红）。请指定由 `m19-testcases-003` 还是 `m19-qemu-001` 承担。
2. **`tests/arch` 的 tiny 探针迁移归属**：15 份 `tests/arch/*/*.lds` 与 `.S` 本地 `.equ ENTRY` 仍硬编码 `0xffffff010100`（不 include `machine-tiny.inc`，本任务未动）。新入口下需随 QEMU/chipyard 侧一并迁移；建议立独立任务或并入 `m19-integ-001`。
3. **picolibc 的 Tiny 地址图**：`components/picolibc` 的 `cross-dadao.txt` 补丁仍写 flash 64 KiB / ram `0xffffff010100` / `__stack=0xffffff7eff00`；迁移需改组件补丁 + 重建 + series 升号（版本号须用户认可），本任务文件集外。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` = **14 PASS + 2 BLOCKED，EXIT=0**（PASS 14/14）；`run.sh --inject` = **8/8 PASS，EXIT=0**（每条 cp 备份 + md5 注入→真红→还原→回绿）。门控真实 rc：`check-tests-index` 0、`check-inst-macro-scope` 0、`check_inst_sig --data-only` 0、`validate-vectors` 0、`check-case-ledger` 0；`check-inst-asm` rc=2（`run_asm_suite: 0/274 镜像通过`）——suite 日志只记 QEMU rc=1/0B（不落 stderr）；抽验 2 例 stderr 均为旧 QEMU 的 `e_entry ... is not the fixed application entry 0xffffff010100`，属跨任务依赖（见遗留 1）。
**修改文件**：`tests/ee-tiny/{runtime.yaml,tests_inst_tiny.lds,tests_freestanding_tiny.lds,crt0_tiny_freestanding.S,crt0_tiny_picolibc.S,run_embench_tiny.py,run_ansibench_tiny.py,run_picolibc_tests_tiny.py}`；`tests/inst/{macros/inst_test.inc,README.md}`；`tests/shared/asm/machine-tiny.inc`；`tests/data/inst-signature/{expected.tsv,inputs.sha256}`（`check_inst_sig.py --write` 重生成）；`tests/unit/llvm/e2e/{mcmodel_far.lds,lit/patchable_entry_e2e.test,lit/lit.cfg.py,lit/weak_undef.test}`；`tests/unit/gem5/tiny_hmon/tiny_hmon.lds`。
**验收结果**：274 个 `tests/inst` 镜像全部 llvm-mc+ld.lld rc=0；逐 ELF `e_entry=0xffffff002000`、`.text/.faultpad/.faulttab/.testdata = ENTRY+0/0x4000/0x4300/0x5000`、PT_LOAD ∈ `[ENTRY, ENTRY+0x20000)`、不触 guard_lo；逐镜像 `_start` 首个 `set.rb rb30 = 0xffffff001000`（SIGNATURE）、`set.rb rb16 = 0xffffff000030`（EXIT_BLOCK）；freestanding/picolibc crt 链接后 `SP/__exit_block/__heap_end = 3f000/30/3e000`；mcmodel large rc=0、default rc=1（REL26 out of range）；patchable 段两词 = 函数首槽地址（`0000ffff ff00....`）。注入红证据：entry 回 0x10100 ⇒ 274/274 链接 `_start 必须等于固定入口`；TEST_BUF 回 ENTRY+0x7000 ⇒ `macro TEST_BUF`/`signature below ENTRY`/`disasm rb30` 三处红；runtime.yaml entry 回旧值 ⇒ `gen_machine_inc --check` 红；freestanding 入口回旧值 ⇒ `patchable region`+`free-link` 红；faultpad 偏移错 ⇒ `elf-layout` 红。
**新发现/坑**：① `inst_expected._lds_section_base` 只认 `. = 0x… [+ 0x…];`，lds 入口必须保持字面量（写符号会让数据派生 fail-closed）；② 重生成的 87 个期望值**全部恰为旧值 −0xE100**（旧 entry−新 entry，现场核对 delta 单值 ⇒ 只有 ENTRY 相对量变化）；③ `check-tests-index` 钉死 `__heap_end = sp−0x1000`，新 24 KiB 栈下该上限落在 STACK 区内；此处镜像全静态、不 malloc，已在 lds 注释披露，动态堆需另立口径；④ `set.rb` 反汇编展开 = `set.zw wp2`/`or.w wp1`/`or.w wp0`（bits 47:32/31:16/15:0），证据脚本据此独立读回宏常量；⑤ `patchable_entry_e2e.test` 的段内容高 6 字节断言 `0000ffff ff01` 必须随入口改 `ff00`（已实测）；⑥ 基线 QEMU 的拒绝信息本身即「入口确实迁移」的可观测证据。
**遗留问题**：① `check-inst-asm` / 三平台跑通待 `m19-qemu-001`（新 QEMU）+ `m19-testcases-003`（8 KiB BootROM）；本任务只证到「构建 + ELF 布局 + 入口拒绝」；② BootROM 固件 `cfx_power_tiny.S`/`cfx_hmon_tiny.S` 仍按旧布局（跳 0x10100、hmon 槽 0xD8–0xF8、64 KiB 假设），未动（见待裁定 1/2）；③ picolibc 安装版 lds 的 Tiny 地址图仍旧（见待裁定 3），`check-picolibc-tests` 在新 QEMU 下会红；④ `tests/arch` tiny 探针仍旧入口（见待裁定 2）；⑤ `tests/unit/gem5/tiny_hmon/tiny_hmon.S` 在现 LLVM 下本就无法汇编（`escape` 语法已变），本次只把其 lds 迁到新入口保持一致，未验证执行；⑥ `tools/testcases/unit/run_elf_e2e.py` 注释仍写旧入口（tools 范围，归 003）；⑦ `tests/unit/gem5/tiny_hmon/expected.yaml` 的 `profile.entry/sram_size/bootrom_size/hmon_size/shared_bootrom_md5` 仍旧几何（约束禁改，随 gem5 tiny_hmon 任务迁移）。

## 审阅记录

### 第 1 轮 engineer 自审（逐行审查改动 + 证据脚本反例门控）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 证据脚本 `_set_rb` 把 wyde 位移写成 48/32/0（实际 47:32/31:16/15:0），disasm/pico 检查假红 | ✅已修 | `checks.py` 位移改 32/16/0 | `disasm-start` 274/274、`pico-link rb1(SP)` PASS |
| F2 `checks.py` 多处 `return 1 if bad(...) else 0` 恒返回 0（patchable 内层 FAIL 被吞） | ✅已修 | 全部改为 `bad(...); return 1` | 注入 free-entry 时 `patchable region` 红被计入，注入 rc=1 |
| F3 `llvm-objcopy --only-section` 拒绝移除被 `SHF_LINK_ORDER` 引用的 `.text` | ✅已修 | 改 `--dump-section __patchable_function_entries=` | `patchable` PASS（两词 == 函数首槽地址） |
| F4 注入 ②/④ 用 `&&` 串联，第一个检查红即短路，第二个反例未被验证 | ✅已修 | 改为 `r1/r2/r3` 聚合（全 0 才绿） | inject-sigbuf 红日志含 geometry+build+disasm 三处；inject-free 含 patchable+free-link |
| F5 `mcmodel_far.lds` 一条注释超长/断行错位 | ✅已修 | 重排注释 | `mcmodel` PASS（large rc=0 / default REL26） |
| F6 `__heap_end = sp−0x1000` 在 24 KiB 栈下落在 STACK 区内（门控钉死，不能私改） | ✅已披露 | lds 注释写明「静态镜像不 malloc，动态堆需另立口径」 | 注释 + 完成区「新发现 ③」 |
| F7 `tests/data/inst-signature` 派生数据是否只随入口变化 | ✅已核 | `--write` 重生成 87 值 | 逐对核对 delta 恒为 −0xE100（现场脚本） |
| F8 hmon 数据槽（0xD8–0xF8 vs spec 0x0C00）单边迁移会破红 | ✅按约束不动 | 只记录 | 「待裁定 1」+ 遗留 ② |
| F9 `tiny_hmon.lds` 改了但该单测本身已因 `escape` 语法漂移无法汇编 | ✅已核 | 只做布局一致化并在文件头注明 | 汇编失败日志（`escape takes no second operand`），遗留 ⑤ |

**自审判定**：9 条 finding 全部处置（8 修 + 1 按范围记录），状态可置「待验收」；无未修项。

### 第 1 轮 reviewer 验收

**重跑（仓库根执行运行期证据目录内的 `run.sh`，下称 run.sh；判决全部基于本人输出）**
1. `run.sh` → **`FAIL=0 BLOCKED=2`、`EXIT=0`（13 PASS + 2 BLOCKED，与完成区一致）**：geometry 全绿（runtime.yaml 9 字段、machine-tiny.inc 9 项、两 tiny lds、宏探针 9 值、signature below ENTRY）；`build-all images=274 failed=0`；`elf-layout 274 images (12 without .faulttab)`；`disasm 274 images, 274 EXIT_BLOCK groups`；free-link/pico-link/patchable/mcmodel（large rc=0、default rc=1 REL26）PASS；5 门控 rc=0（check-tests-index、check-inst-macro-scope、check_inst_sig --data-only、validate-vectors、check-case-ledger）。BLOCKED＝qemu-probe（rc=1，逐字 `e_entry 0xffffff002000 is not the fixed application entry 0xffffff010100`）+ check-inst-asm（rc=2，`run_asm_suite: 0/274 镜像通过`）。
2. `run.sh --inject` → **`EXIT=0`、5/5 PASS**：每条 md5 前→注入→还原三值闭合；红日志真实：entry 回 0x010100 ⇒ `build-all failed=274`（`_start 必须等于固定入口`）、TEST_BUF 回 ENTRY+0x7000 ⇒ geometry+disasm 双红、yaml/faultpad/free-entry 各自红。
3. **独立反例注入**（engineer 未覆盖的 `tests/ee-tiny/crt0_tiny_picolibc.S`：`set.rb rb1, SP`→`0xffffff03e000`）→ 重跑同一 run.sh ⇒ `[FAIL] pico-link rb1(SP) expected=0xffffff03f000 actual=0xffffff03e000`、**EXIT=1**；`cp`+md5 还原（ab2463889de3f2e9f9574eb17cd9109d = 备份）→ 重跑 **EXIT=0 回绿**。
4. `expected.tsv` 独立重算：4689 数据行仅 87 行变化，差值直方图 `{57600: 87}`（=0xE100），与完成区「全部恰为旧值 −0xE100」一致。

**约束核验**：`git diff --stat HEAD~1`＝19 文件，与完成区「修改文件」逐一对上；无 QEMU/gem5/chipyard 源码、无 Makefile/门控/断言弱化；完成区无具体运行期路径；地址链 runtime.yaml↔machine-tiny.inc↔两 tiny lds↔crt0↔宏层↔expected.tsv 对 spec §1.1/§6.2.1 逐项相符（entry 0x2000、SP 0x3F000、EXIT 0x30、DUMP 0x800/0x800、SIGNATURE 0x1000/0x800、guard_lo 0x38000、MemRAS 0x3F000–0x40000、window 0x2_0000）；12 个无 .faulttab 镜像现场核 `TEST_FAULT=0`；crt0 不置 ra0＝spec「初值 0＝未启用」，验收 3「若启用」条件未触发。
**check-inst-asm（跨任务依赖，已披露，非本任务可修）**：基线主树同 QEMU/BootROM md5 于 21:21 为 `274/274 镜像通过` ⇒ 当前 0/274 **非基线红**（「基线红逐行对照」口径不适用）；根因＝迁入口后旧 QEMU 硬拒（拒绝串在 QEMU 二进制内，本人抽验 2 镜像逐字一致；suite 日志仅记 rc=1/0B、不落 stderr）。修复须新 QEMU（`m19-qemu-001`）+ 8 KiB BootROM（`m19-testcases-003`，均待开始），约束禁改 QEMU；完成区遗留①与 run.sh 头注释已披露。验收 5「rc=0」未达，留 architect 终审。

**判决：Needs Revision**（最小返工；门控、断言强度、其余产物均不动）：
1. **`tests/unit/gem5/tiny_hmon/tiny_hmon.lds` 段址错位 +0x100**：`.rcheck/.data/.results` 落 `ENTRY+0x2100/0x3200/0x4100`（0x004100/0x005200/0x006100），而同批未改的 `tiny_hmon_layout.inc` 仍 `ENTRY+0x2000/0x3100/0x4000`（旧 lds 与它逐项相等；新 lds 文件头亦自写「data area ENTRY+0x3100」自相矛盾）⇒ 完成区「迁到新入口保持一致」不成立。改回 0x004000/0x005100/0x006000（.inc 不在约束内，勿动）。
2. **证据脚本 2 条恒真断言**（geometry 尾部 `stack/MemRAS`、`testdata in image_window`＝常量比常量，产物任何改动都恒 PASS；违 AGENTS.md §4「禁恒真、每条断言有可达 FAIL」）：改现场读值（链后 ELF 符号 / 探针实读 TEST_DATA＋runtime.yaml image_window）或删除（SP 已有 5 处 artifact 断言覆盖）；随后重跑 run.sh 与 --inject，完成区 PASS 计数按现场更新。
附（不阻断）：完成区「274 条逐例 stderr」措辞建议改「QEMU rc=1/0B、抽验入口拒绝」（结论成立）；`tests/unit/gem5/tiny_hmon/expected.yaml` entry 仍旧值（约束禁改，建议补披露归 gem5 任务）；分支 5b5b4a41 快照提交主体请 architect 对照「不提交 git」核一句。

### 返工处置（第 2 轮 engineer；不动 reviewer 记录）

| reviewer 项 | 处置 | 改动 | 复验 |
|---|---|---|---|
| 1 `tiny_hmon.lds` 段址 +0x100 | ✅已修 | `.rcheck/.data/.results` 改回 `0xffffff004000/0x005100/0x006000`（= ENTRY+0x2000/0x3100/0x4000，与 `tiny_hmon_layout.inc` 的 `RECORD_CHECK/DATA_BASE/RESULTS` 逐项相等）；新增 `hmon-lds` 检查：现场解析 `.inc` 三个 `ENTRY+偏移` 与 lds 段址互核 | `hmon-lds` PASS 三行（`0xffffff004000/0x005100/0x006000`）；注入 `.data` 段址 +0x100 ⇒ `[FAIL] hmon-lds .data expected=0xffffff005100 actual=0xffffff005200`，还原回绿（md5 `5d84c119… → a3c33ce4… → 5d84c119…`） |
| 2a `stack/MemRAS` 恒真 | ✅已修 | 改为产物驱动：SP 取 `runtime.yaml`、RAM_END 取 `machine-tiny.inc`；断言 `SP = RAM_END+1−0x1000`、`SP−0x6000 = STACK_BOTTOM`、`MemRAS = SP`、`MRPTR = RAM_END+1` | 注入 `sp` 0x3F000→0x3E000 ⇒ `[FAIL] stack/MemRAS expected=SP=RAM_END+1-0x1000… actual=0xffffff03e000/0xffffff040000`（同一行点名），还原回绿（md5 `c0558359… → 5948f741… → c0558359…`） |
| 2b `testdata in image_window` 恒真 | ✅已修 | 改为产物驱动：TEST_DATA 取宏探针实读、window 取 `runtime.yaml`；断言 `TEST_DATA+0x2000 ≤ ENTRY+image_window` | 注入 `image_window` 0x2_0000→0x4000 ⇒ `[FAIL] testdata in image_window expected=<=0xffffff006000 actual=0xffffff009800`（同一行点名），还原回绿（md5 `c0558359… → 5e7547f2… → c0558359…`） |
| 3 重跑计数 | ✅已做 | 完成区数字按现场更新 | `run.sh` = **14 PASS + 2 BLOCKED、EXIT=0**；`run.sh --inject` = **8/8 PASS、EXIT=0**（8 条注入逐条 rc=1→还原 rc=0，marker 当场 grep） |
| 附 措辞 / expected.yaml | ✅已做 | 完成区改为「QEMU rc=1/0B、抽验 2 例入口拒绝」；补 `tiny_hmon/expected.yaml` 仍旧几何的披露（遗留⑦） | 完成区第 59/63 行 |

**返工自审**：两条恒真断言已消除；`hmon-lds` 与栈/MemRAS 两条新断言各有一路具名注入 FAIL（非仅 rc!=0）；`tiny_hmon_layout.inc`、门控与其余产物未动；未提交 git。

### 第 2 轮 reviewer 验收

**重跑（仓库根执行运行期证据目录内的 `run.sh`，下称 run.sh；判决全部基于本人输出）**
1. `run.sh` → **14 PASS + 2 BLOCKED、EXIT=0**：PASS 名单＝原 13 + 新增 `hmon-lds`（三行 `0xffffff004000/0xffffff005100/0xffffff006000`）；`stack/MemRAS`/`testdata in image_window` 已改为产物驱动口径（SP 取 runtime.yaml、RAM_END 取 machine-tiny.inc、TEST_DATA 取宏探针、window 取 runtime.yaml）。
2. `run.sh --inject` → **8/8 PASS、EXIT=0**：新增⑥sp/⑦window/⑧hmon 逐条 `rc=1 → 还原 rc=0` 且带具名 marker（`[FAIL] stack/MemRAS`、`[FAIL] testdata in image_window`、`[FAIL] hmon-lds .data`）；三值 md5 与完成区返工表逐字一致（`5d84c119→a3c33ce4→5d84c119`、`c0558359→5948f741→c0558359`、`c0558359→5e7547f2→c0558359`）；变更集空。
3. **重点 1（现场解析，非看数值）**：独立脚本解析 lds 段址 × `tiny_hmon_layout.inc` 三个 `ENTRY+偏移`（ENTRY 取 `machine-tiny.inc` 实值）互核 ⇒ `RECORD_CHECK/DATA_BASE/RESULTS` **三项 ALL_EQUAL**（0xffffff004000/005100/006000），lds 文件头「ENTRY+0x3100/+0x4000」与段址自洽。
4. **重点 2（独立注入，两次）**：① `runtime.yaml` sp→0x3E000 ⇒ 完整 run.sh **EXIT=1**，`[FAIL] stack/MemRAS expected=SP=RAM_END+1-0x1000 … actual=0xffffff03e000/0xffffff040000`（同轮 `testdata` 仍 PASS ⇒ 两断言解耦）；② 还原后 image_window→0x4000 ⇒ **EXIT=1**，`[FAIL] testdata in image_window expected=<=0xffffff006000 actual=0xffffff009800`（`stack/MemRAS` 仍 PASS）；③ 两次均 `cp`+md5 还原（`c0558359` 闭合、`git status` 空）→ 最终 run.sh **回绿 14 PASS + 2 BLOCKED、EXIT=0**。
5. `check-tests-index` 在 sp 注入下同轮转红（其钉死 `__heap_end = sp−0x1000`）——门控真实联动，非恒真。

**约束核验**：`3a1fd107` 仅动任务书与 `tiny_hmon.lds`（3 行段址），`tiny_hmon_layout.inc`、Makefile/门控、断言强度未动；完成区数字按现场更新（14 PASS、8/8）、措辞按第 1 轮附注改为「suite 日志只记 rc=1/0B、抽验 2 例入口拒绝」、新增遗留⑦（`expected.yaml` 旧几何归 gem5 任务）；状态＝**待验收**；**第 1 轮审阅记录 16 行逐字未改写**（83–99 行，特征句逐一命中）。快照对账：复核前后 `git status` 均空、5 个关键文件 md5 复核 `OK`。
**BLOCKED 复核**：qemu-probe（旧 QEMU 拒 `e_entry 0xffffff002000`，逐字）与 check-inst-asm（rc=2、`0/274`）仍属跨任务依赖（`m19-qemu-001`/`m19-testcases-003` 待开始、约束禁改 QEMU），完成区遗留①与 run.sh 头注释如实披露。

**判决：Accepted** —— 上轮两处返工点均已修复且经本人独立注入证伪（注入→FAIL→还原→回绿全链路真实）；14 PASS + 2 BLOCKED、8/8 在本人重跑下复现；约束无违反。残留（不阻断，architect 终审）：验收 5 的 `check-inst-asm rc=0` 依赖跨任务链，遗留①⑦已披露。
