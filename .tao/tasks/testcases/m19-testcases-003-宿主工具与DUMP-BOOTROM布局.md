# m19-testcases-003: 宿主工具与 DUMP/BOOTROM 布局迁移（pt_regs 0x800、ROM 8 KiB）

**模块**：testcases
**项目里程碑**：M19
**依赖**：`m19-spec-002`、`m19-testcases-002`
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：待验收

## 背景

`m19-testcases-002` 改了测试侧地址；宿主工具仍按旧 `DUMP_SIZE=0x408`、旧偏移和 64 KiB BootROM 工作。本任务把 DUMP 改成 `pt_regs` 0x800 布局，并把 BootROM 构建器改成 8 KiB 新布局。

## 目标

1. `tools/testcases/lib/build_test_binary.py`：`DUMP_SIZE=0x800`；四段偏移 `rd@0x000`、`rb@0x200`、`ra@0x400`、`rf@0x600`；`rd[0]=status`、`rb[0]=ip`；`EXIT_BLOCK=0x30`。
2. `verify_harness_dump.py` / `run_qemu_test.py`：pmemsave 大小/偏移与 0x800 布局一致；旧 `0x408` 偏移删除。
3. `machine_profile.py`：`REQUIRED_RUNTIME_FIELDS` 增 `dump_size`、`signature_base`（若 `m19-testcases-002` 已加字段）；交叉核对 `runtime.yaml`。
4. `check_tests_index.py`：假布局改 entry 0x2000、signature 0x1000、EXIT 0x30、DUMP 0x800、stack/MemRAS 新地址。
5. `tools/testcases/arch/build_tiny_bootrom.py`：`BOOTROM_SIZE=0x2000`；power@0–0x7FF、hmon@0x800–0x13FF、table@0x1F00；更新 hex 输出 `bootrom.tiny.hex`（8 KiB 稀疏 hex）。
6. 同步引用旧 `0x408`/64 KiB/`0x10100` 的注释与断言；不改 QEMU/gem5/chipyard 源码。

## 验收（逐条贴真实 rc）

1. QEMU `--dump` 读回 0x800：`rd0=status`、`rb0=ip`、四组顺序正确；旧偏移不再命中。
2. `build_tiny_bootrom.py` 产出的镜像 **恰好 8192 B**；power/hmon/table 偏移与 `m19-spec-002` 一致；`--check-hex` 通过。
3. **可达 FAIL ≥2 路**：① 把 `DUMP_SIZE` 写回 0x408 ⇒ dump 断言红；② 把 `BOOTROM_SIZE` 写回 0x10000 ⇒ 镜像大小/装载红。
4. `check-tests-index` / `check-run-artifacts` 真实 rc=0（基线红逐行对照）。

## 约束

独立 `git worktree`；**不提交 git**；只动 `tools/testcases`、`tools/qemu` 中宿主工具与 bootrom 构建器；不改 QEMU/gem5/chipyard 源码；完成区不写具体 `.work/**` 路径。

## 待裁定

1. **hmon SRAM 数据槽 `0x0C00` 与 handler 寻址冲突**（交叉发现，m19-qemu-001 提出；本任务不修）：
   - 事实：`spec/Kaiwu §6.2` 把 hmon 数据区定在 `0x0C00–0x0CFF`（代码区 `0x0000–0x0BFF`），但 handler 只有 `rd63` 一个 scratch，`st.o/ld.o` 的基址只能取 RB 组、立即数为**有符号 12 位**（`[−0x800, 0x7FF]`，`spec/SimRISC-01` 地址公式 `rb[hb] + $signed(imms12)`）；`rb0` 为只读 IP，单条 `rb0` 相对指令**无法到达 `0x0C00`**。
   - 影响面：固件 `tests/ee-tiny/cfx_hmon_tiny.S` 与消费者（`tests/inst/macros/inst_test.inc`、`tests/inst/11-cfx`/`12-misc`、`tests/arch/*`、`tests/unit/gem5/tiny_hmon`）仍全用 `0xD8–0xF8`；若只改 spec/一方会单边破红。
   - 可选处置（需 spec 决策，非本任务范围）：(a) 数据区留在 `≤0x7FF`（如维持 `0xD8`，代价：hmon 代码上限从 spec 的 3 KiB 降到 `0xD8`）；(b) 数据区改到 `0x7C0` 类可达位置（代码上限 1984 B）；(c) 在 hmon 契约上追加一个 RB 组 scratch/base 寄存器（保留代码 3 KiB，但要改寄存器保存约定与全部消费者）；(d) 收回 spec 的 3 KiB 代码/`0x0C00` 数据分区。
   - 本任务处置：构建器保留 `0xD8` 槽并在**超限报错信息**中写明该冲突（不静默沿用）；BootROM 镜像偏移（power@0 / hmon 源@0x800 / 表@0x1F00）与此无关，已按 spec 落地。
2. **Vast 是否登记 `dump_size`/`signature_base`**：`machine_profile` 目前只对 `tiny` 强制这两项（`tests/ee-vast/runtime.yaml` 未登记）；`build_test_binary.DUMP_SIZE` 对未登记环境回落到同一 pt_regs `0x800`。请确认 Vast 的 dump 是否也按 pt_regs 四段定义（若是，需在 Vast runtime 登记并由后续任务迁移其消费者）。

## 完成区

**测试结果**：运行期证据目录 `run.sh` = **7 PASS + 0 BLOCKED，EXIT=0**；`run.sh --inject` = **2/2 PASS，EXIT=0**（① `DUMP_SIZE` 回 0x408 ⇒ `0x408 vs 0x800` 红；② `BOOTROM_SIZE` 回 0x10000 ⇒ `image ... 65536` 红；均 cp+md5 还原回绿）。门控真实 rc：`check-tests-index` 0、`check-run-artifacts` 0、`check_tests_index --self-test` 0。`verify_harness_dump.py` 在当前 QEMU 下 rc=2 BLOCKED（旧 QEMU 以 `reserved prefix byte…the first 256 bytes must be zero` 拒绝新几何 raw `-kernel`，属 m19-qemu-001）。
**修改文件**：`tools/testcases/lib/{build_test_binary.py,machine_profile.py,run_qemu_test.py,verify_harness_dump.py,test_harness_exit_path.py,README.md}`；`tools/testcases/arch/build_tiny_bootrom.py`；`tools/testcases/check_tests_index.py`；`tools/testcases/diff_ir_lli.py`；`tools/testcases/unit/{run_codegen_e2e.py,run_elf_e2e.py}`；`tools/qemu/semantics_gate.py`。
**验收结果**：DUMP 逐字解码 = `set.zw/or.w rb62=0xffff_ff00_0800` + **257** 条写（rd[0..63]@0x000、rb2rd+ip@0x200、rb[1..63]@0x208、ra[0..63]@0x400、rf[0..63]@0x600），覆盖集合恰为四段各 64×8 B，无旧 pc@0x400/0x408 命中；QMP `pmemsave DUMP_BASE 0x800` 读回 2048 B 与四段 pattern **逐字节相同**（rd0/rb0/ra0/rf0 = 0xDDCCBBAA…/0xBBAA9988…/0xAABBCCDD…/0xCCDDEEFF…）。BootROM：镜像恰 **8192 B**，`power@0x0000`(292 B)、`hmon 源@0x0800`(44→48 B)、`reserved 0x1400–0x1EFF` 全零、表 `@0x1F00`(magic/ver/count 0x44424F54/1/1，entry type=1 flags=0x3 offset=0x800 size=48)、尾 `0x1F30–0x1FFF` 全零；`--check-hex` 0、`--dump` 0、`--self-test` 0（含 4 类注入拒绝）。
**新发现/坑**：① hmon 数据槽 `0x0C00` 在单 scratch + `signed imms12` 下不可达（见待裁定 1）；② `verify_harness_dump.py` 原先引用的 `tests/inst/base/misc.yaml` 早已随 YAML 退场删除 ⇒ 改为内置 ILLI 探针 case，并修掉写死的构建树 QEMU 路径与旧 `-device loader` 地址；③ `build_tiny_bootrom` 的 `HMON_DATA_BASE` 仍是固件布局（0xD8），与镜像偏移无关，超限报错已写明冲突；④ Vast 未登记 `dump_size` ⇒ DUMP_SIZE 回落 0x800（诊断用），其 dump 语义待裁定 2；⑤ 旧 QEMU 对 raw `-kernel` 的 256 B 前缀/固定入口检查是「新几何已落地」的旁证。
**遗留问题**：① QEMU 侧的 `rd0=status`/`rb0=ip` 实机读回（guest 真实执行 dumper）待 `m19-qemu-001`；本任务证到通道级 0x800 与指令级布局；dumper 写指令由 ~130 条增至 257 条（仅 dump 模式），其 TCG 代码量需在新 QEMU 实测。② `tests/ee-tiny/cfx_power_tiny.S` 仍读表@0xE000、复制 hmon@0x2000、跳 0x10100 ⇒ 现构建出的 8 KiB 镜像**结构合法但不可启动**，启动固件源迁移归 `m19-testcases-005-启动固件迁移`（本任务只迁构建器）。③ `Makefile` build-bootrom 注释仍写「8 KiB 段/64 KiB 镜像」（共享文件，超出本任务文件集）。④ `check-interface` rc=2：与基线 `m19-testcases-002` 失败集**逐行相同**（`DADAO_TINY_RAM_SIZE QEMU 8388608 != 0x40000`、`QEMU 65536 != 0x2000`、`N 294 != 309`），属 m19-qemu-001/llvm 的 KNOWN-RED。⑤ `tests/arch` tiny 探针、picolibc 安装版地址图仍未迁移（继承 m19-testcases-002 待裁定 2/3）。⑥ 审阅记录 F4 的旧构建树路径措辞保留在审阅记录内（按 reviewer finding ③ 不改写审阅记录）；门控 `check-knowledge-refs` rc=0 未拦。

## 审阅记录

### 第 1 轮 engineer 自审（逐行审查改动 + 证据脚本反例门控）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `machine_profile` 若把 `dump_size` 无条件加入必填，Vast（未登记）会整体加载失败 | ✅已修 | 改为仅 `tiny` 强制、成对校验 | `checks.py profile` PASS；`all_profiles()` 两 profile 可加载 |
| F2 dumper 解码初版未处理 `emit_load_imm64_rb` 省略零 wyde（base 只有 3 词） | ✅已修 | 解码循环按 `set.zw/or.w` 动态取词 | dump-layout 15/15 PASS |
| F3 `rb0=ip` 经 `rb2rd→st.o-rd` 写 0x200，解码需与普通 rd 写区分 | ✅已修 | 特判 `op=0x21 ha=63 imm=0x200` → rb[0] | 覆盖集无缺口 |
| F4 `verify_harness_dump` 的 YAML 源已删除、QEMU 路径写死 `.work/build`、loader 地址旧 | ✅已修 | 内置探针 case + `paths.py` + `addr=DUMP_BASE` | 旧 QEMU 下 rc=2 BLOCKED（明确信息，非 traceback） |
| F5 证据脚本 QMP socket 路径超过 AF_UNIX 108 B 上限 | ✅已修 | socket 落 `/tmp/opencode/<任务>/` | dump-channel 3/3 PASS |
| F6 注入 ① 的 `DUMP_SIZE` 行出现两次（模块级 + `set_profile`） | ✅已修 | 注入模式带上 `RD_DUMP_OFF` 上下文 | inject-dumpsize rc_red=1→green=0，md5 三段一致 |
| F7 `check_tests_index` 假布局同时要覆盖 entry/signature/EXIT/DUMP/栈/MemRAS | ✅已修 | 假 picolibc lds 换 8 KiB/256 KiB 新图并登记各符号 | `--self-test` rc=0 |

### 第 1 轮 reviewer 验收（只读复核；判决基于本人命令输出，未提交 git）

**重跑记录（全部本人执行）**
- 仓库根运行期证据目录内 `run.sh` ⇒ **7 PASS / 0 BLOCKED、FAIL=0、EXIT=0**：dump-layout / profile / bootrom / dump-channel / check-tests-index / check-run-artifacts / check-tests-index-selftest 全部 actual rc=0。
- `run.sh --inject` ⇒ **2/2、EXIT=0**：`inject-dumpsize: injected rc=1 (FAIL as expected) → restored rc=0; md5 d2ca4cd1… → 8b87cdef… → d2ca4cd1…`；`inject-bootromsize: injected rc=1 → restored rc=0; md5 50e2fc58… → acd18ba1… → 50e2fc58…`。
- **独立反例注入（reviewer 自做，非 engineer 自检）**：`RB_DUMP_OFF 0x200→0x208`（注入前 cp+md5）⇒ 同一 `run.sh` 打出 `[FAIL] dump-layout rc=1`、`[FAIL] dump-channel rc=1`、`FAIL=2 / RESULT: FAIL`、EXIT=1；`cp` 还原后 `md5sum -c` 两目标文件 OK、`git status --porcelain -uall` 为空，`run.sh` 回绿 EXIT=0。
- `verify_harness_dump.py` ⇒ **EXIT=2**，真实 QEMU 输出 `reserved prefix byte 0 is 0x79, the first 256 bytes must be zero` + BLOCKED 指向 m19-qemu-001（与完成区一致，非 traceback）。
- `make check-interface`：本分支 EXIT=2 与 `m19-testcases-002` 分支 EXIT=2 的完整输出 `diff` ⇒ **rc=0**（失败集 3 项逐行相同：RAM 8388608≠0x40000、ROM 65536≠0x2000、lit 294≠309）。
- `make check-patch-tree` EXIT=0（464 patches OK）、`make check-component-changelog` EXIT=0（44 项）、`make check-knowledge-refs` EXIT=0（0 具体 `.work` 引用）。

**关键项独立核对（源码 + spec + 产物，非采信完成区）**
- `DUMP_SIZE=0x800`、`RD/RB/RA/RF=0x000/0x200/0x400/0x600`、`EXIT_BLOCK=…0030`、`rd0=status`/`rb0=ip`：与 `spec/Kaiwu` §6.2.1（DUMP 0x800 四组、SIGNATURE+0x1000、EXIT_BLOCK 0x30、ENTRY 0x2000、MemRAS 0x3F000/MRPTR 0x40000）逐条对上；dumper **257 条写**断言在本人重跑 PASS，四段覆盖集无缺口、旧 pc@0x400/0x408 不再命中；目标文件中 `0x408`/`0x10100` 残留 0 处。
- BootROM：本人独立读回镜像 **恰 8192 B**；power `.text=0x124=292 B`@0x0000、hmon `.text=0x2c=44 B`→段 48 B@0x0800、`0x1400–0x1EFF` 与 `0x1F30–0x1FFF` 全零、表@0x1F00 = magic/ver/count `0x44424F54/1/1`、entry type=1 flags=0x3 offset=0x800 size=48，与 spec §6.1/§6.2（power≤2 KiB、hmon≤3 KiB、表 48 B）一致；`--check-hex`/`--dump`/`--self-test` rc=0。
- `machine_profile`：tiny 强制 `dump_size`+`signature_base` 成对登记，且非 0x800 / 重叠 / 未对齐 / 缺一 均 `ProfileError`（脚本内负例可达）；Vast 未登记、回落 0x800 已披露（待裁定 2）。`verify_harness_dump`/`run_qemu_test` pmemsave 一律 `DUMP_BASE+DUMP_SIZE(0x800)`。

**gap 与披露**
- `tests/ee-tiny/cfx_power_tiny.S` 仍读表 `BOOTROM_BASE+0xe000`（本人 grep 确认；本 commit `tests/` 零改动）⇒ 「8 KiB 镜像结构合法但不可启动」属实，全文无「可启动已验」表述；固件不在本任务文件集内，归属见 finding 1。
- hmon `0x0C00` 与 signed-12-bit（单 scratch、`rb0+imms12` 到不了 0x0C00）冲突已写入「待裁定 1」并给出 (a)–(d) 四个处置选项，构建器超限报错文案含该冲突（非静默沿用）。
- 采信项（跨任务阻塞，非本任务产出缺陷）：guest 真实执行 dumper 的 `rd0/status`、`rb0/ip` 实机读回待 `m19-qemu-001`（旧 QEMU BLOCKED 已由本人复现）。

**findings（文档级，不阻断，交 architect 收尾修正）**
1. 遗留②写「固件迁移归 `m19-qemu-001`/`m19-integ-001`」，实际已有专任务 `m19-testcases-005-启动固件迁移`（依赖本任务），任务号归属应更正。
2. 遗留④括号只列 2 项，漏 `DADAO_TINY_RAM_SIZE QEMU 8388608 != 0x40000`；「失败集逐行相同」本身实测成立（diff rc=0）。
3. 审阅记录 F4 出现具体 `.work/build` 措辞，建议改「运行期构建目录」（`check-knowledge-refs` rc=0 未拦）。

**判决：Accepted** —— 验收命令块在本人重跑下全绿、两条注入均真 FAIL 并回绿、独立反例注入确认脚本可失败；硬约束（只动 tools/testcases+tools/qemu 宿主工具与构建器、不改 QEMU/gem5/chipyard 源码、修改文件与完成区 13 项逐一对账一致、完成区无运行期路径、不提交 git）逐条守住；3 条文档级 finding 不属阻断面。

