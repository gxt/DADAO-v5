# m19-gem5-002: gem5 Tiny 新几何与装载（8K ROM / 8K hmon / 256K SRAM）

**模块**：gem5
**项目里程碑**：M19
**依赖**：`m19-spec-002`
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：已验证

## 背景

gem5 的 Tiny profile 仍按 64 KiB BootROM / 8 MiB SRAM / 64 KiB hmon。Tiny 新几何（`m19-spec-002`）为：ROM 8 KiB、SRAM 256 KiB、hmon 8 KiB、entry `MAIN_SRAM_BASE+0x2000`、raw 基址 `0x2000`、DUMP 0x800（pt_regs）、SIGNATURE 0x1000、EXIT 0x30、MAILBOX 0x20、STACK 0x39000–0x3F000、MemRAS 0x3F000–0x40000。

## 目标

1. `configs/dadao/fs.py --profile tiny`：BootROM 8 KiB、RAM 256 KiB、hmon 8 KiB、reset/entry/raw 基址按新几何。
2. 装载：BootROM 镜像 8 KiB；应用 ELF/raw 只落 `0x2000` 起 SRAM；`e_entry=0x2000`；禁止写 header/BootROM/hmon。
3. 头区与 DUMP：`VERSION/MAILBOX/EXIT` 地址；DUMP 0x800 四组 `rd/rb/ra/rf` 按 `pt_regs` 顺序，`rd0=status`、`rb0=ip`。
4. 同步 gem5 侧探针/配置中的旧地址；不改 QEMU/chipyard。
5. 不影响既有 `m19-gem5-001`（swym）范围。

## 验收（逐条贴真实 rc）

1. `make build-gem5` rc=0；`check-gem5-decode` / `check-wuming-cycles` 真实 rc（基线红逐行对照）。
2. gem5 FS Tiny 跑通 power→hmon→应用；`tests/inst` 代表例通过，地址类期望按新几何。
3. DUMP 0x800 读回四组，`rd0/status`、`rb0/ip` 正确。
4. **可达 FAIL ≥2 路**：① RAM 写回 8 MiB ⇒ 边界/尺寸用例红；② entry 写回 0x10100 ⇒ 装载用例红。
5. 不改 QEMU/chipyard；不接板。

## 约束

独立 `git worktree`；**不提交 git**；只动 gem5 组件/补丁与 profile；完成区不写具体 `.work/**` 路径。

## 完成区

**测试结果**：`make build-gem5` rc=0；`make check-gem5-decode` rc=0（positive 263/263、negative 391/391、legality 28/28、legacy 2/2）；`make check-wuming-cycles` rc=2 —— **基线红**：`artifact-up-to-date: contracts/wuming-cycles.yaml` 一行，在基线 `71fdf6fe` 同源跑同样 FAIL（rc=1），错误集逐字相同；`check-patch-tree` 的 gem5 段 0 problem（总 56 = 46 linux + 2 musl + 8 qemu；后两者为他任务/并行会话既有红）；运行期证据 `run.sh` **23/23 checks passed, rc=0**。共享源树 `.work/source/gem5` 的本地提交 `dadao: gem5 patch series`（base+1）是 `apply_series` 的常规产物，其内容与本补丁集逐路径一致（断言⑨ gem5 段 0 problem）。
**修改文件**：`components/gem5/patches/{configs/dadao/fs.py, src/arch/dadao/DadaoFsTlb.py, DadaoFsWorkload.py, fs_tlb.cc, fs_tlb.hh, fs_workload.cc, fs_workload.hh}.patch`、`components/gem5/changelog.md`（8 文件）。
**验收结果**：
1. `--dump-geometry` 25 项与 spec/Kaiwu §1.1/§6.2.1 逐项相等：ROM `0x2000`、SRAM `0x40000`、hmon `0x2000`、`kernel_base=entry=0xffffff002000`、`kernel_reserved=0`、`sp=0xffffff03f000`、`image_window=0x20000`、`version@0/mailbox@0x20/exit@0x30/dump@0x800(0x800)/signature@0x1000(0x800)/guard@0x38000/stack@0x39000/memras@0x3f000`。
2. gem5 FS Tiny 用独立打包的 8 KiB ROM 跑通 power→hmon→app：guest `SYS_EXIT`=0x21（gem5 进程 rc=33），`EXIT_BLOCK +0x30=0x20026`、`+0x38=0x21`；`DUMP 0x800` 四组 rd/rb/ra/rf（步长 0x200）标记 0x1111/0x2222/0x3333/0x4444，`rd0` 与 guest 自拷贝状态一致，`rb0` == `llvm-nm ip_probe` `0xffffff002058`。
3. 边界：`+0x40000`（越过 256 KiB）与 guard_lo `+0x38000` 两处 store 均 `CFXMEM`，经 hmon 返回槽续跑到签名 0xfa。
4. 可达 FAIL：注入 `ram_size=0x80_0000`（8 MiB）⇒ 同一 dump 断言在 `SRAM boundary +0x40000` 行 FAIL（actual 0x0），还原后回绿；`e_entry` 写回 `0x10100` ⇒ loader fatal；另 64 KiB ROM、raw 0x20001 B、PT_LOAD 落头区三例均 fatal rc=1。
5. 未改 QEMU/chipyard/tests；`git status` 仅上述 8 文件 + 本任务书。
**新发现/坑**：① lld 默认生成 64 KiB 页对齐的 header `PT_LOAD`，新几何下落在 `0xffffff000000`（ENTRY 之下）会被本 loader 正确拒绝——测试资产链接脚本须显式 `PHDRS` 只留 app 段；② `or.w` 是「按 wyde 或、保留其余位」，构造常量须用 `set.rd/set.zw/set.rb`（本任务 evidence app 曾因此得到 `0xffffff002222`/`0x7e0c…00fa`）；③ `check-wuming-cycles` 基线红需另立 issue；④ 8 KiB ROM 下 power/hmon 段上限（2 KiB/3 KiB）与表 48 B 由 testcases 构建器落实，gem5 只校验整镜像 8192 B。
**遗留问题**：`tests/unit/gem5/check_tiny_hmon.py`（旧 64 KiB/`0x10100`/8 MiB 期望）无法先绿——它复用 `tools/testcases/arch/build_tiny_bootrom.py`（m19-testcases-003）与 `tests/ee-tiny` 链接布局（m19-testcases-002）；`tests/inst` 代表例同因 `tests/ee-tiny/runtime.yaml` 未迁而无法在本任务内验收（loader 会按新规拒绝旧 entry）。
**待裁定**：
- `check_tiny_hmon` 的迁移归属——由 gem5 侧后续任务在 testcases-002/003 落地后重写，还是并入 testcases-003？本任务未改（避免产出第二种红）。
- `VERSION` 的写入方：spec/Kaiwu §6.2.1 规定 loader 写 `VERSION=1`，但 gem5 的 host loader 按「头区 guest-owned」不写、QEMU 侧亦无写者；本任务不改实现与 spec，待 architect/用户裁定归属。

## 审阅记录

### 第 1 轮 reviewer 验收

**重跑（本人执行，命令与真实 rc）**
1. 运行期证据目录内 `run.sh`：`== summary: 23/23 checks passed, 0 failed ==`、`EXIT=0`。关键实测：`BootROM size 8192`、`GEO_BAD=0 GEO_KEYS=25`（entry/raw 0x2000、DUMP 0x800(0x800)、SIGNATURE 0x1000(0x800)、EXIT 0x30、MAILBOX 0x20、guard 0x38000(0x1000)、stack 0x39000(0x6000)、memras 0x3f000(0x1000)、hmon 0x2000、SRAM 0x40000、ROM 0x2000 与 spec 逐项相等）、guest `rc=33` + `semi:ADP_Stopped_ApplicationExit`、DUMP 四组 0x1111/0x2222/0x3333/0x4444、`rb0=0xffffff002058 == llvm-nm ip_probe`、`+0x40000`/`guard +0x38000` 均 0xfa。
2. 脚本内两处注入均真实翻红：8 MiB 档 ⇒ `[FAIL] SRAM boundary +0x40000: expected=0xfa actual=0x0` 后还原回绿；`e_entry 0xffffff010100` ⇒ `rc=1` + `e_entry 0xffffff010100` 诊断。四例 negative（64 KiB ROM / raw 0x20001 / PT_LOAD 0x800 头区-DUMP）均 `rc=1` 且点名 8192、image window、below entry。
3. **独立注入（非脚本自检）**：以 `CONFIG=` 指向 `fs.py` 副本、`entry` 改回 `0x10100` 重跑同一 `run.sh` ⇒ `11/23 checks failed`、`EXIT=1`（geometry entry FAIL、guest rc FAIL 等）；被测原件 md5 前后均 `a648fdcf…` 未动；去掉注入重跑 ⇒ `23/23, EXIT=0`（注入→FAIL→还原→回绿闭环）。
4. **补测栈/MemRAS 落点**：PT_LOAD 改 `0xffffff039000` ⇒ `fatal … is outside the Tiny image window [0xffffff002000, 0xffffff022000)`、`rc=1`（与 MemRAS 0x3f000 同一窗口分支；头区/DUMP/签名同走 `ppaddr < entry` 分支，脚本已覆盖 DUMP 0x800）。
5. `make build-gem5` `RC=0`（`build-gem5: PASS`）；任务 worktree 内 `make check-gem5-decode` `RC=0`，`positive 263/263, negative 391/391, legality 28/28, legacy 2/2`（与完成区一致）。
6. `make check-wuming-cycles` `RC=2`，唯一 FAIL 行 `artifact-up-to-date: contracts/wuming-cycles.yaml 与现解析结果不一致`；基线 `71fdf6fe` 只读归档树同命令 `RC=1`，两份输出 17 行、`diff` 退出码 0（**逐行相同**）。
7. 任务 worktree 内 `make check-patch-tree`：`56 problem(s)` = linux 46 + musl 2 + qemu 8，**gem5 段 0 problem**（106 patch）。主仓跑同门控为红（70 problem）——主仓补丁文件仍旧版且 `contracts/opcodes.yaml` 已被 `d55a1d80`（m19-spec-001 合入）改动，基线归档树 `gen_decode_table --check` 为 `OK` ⇒ 该红归因他任务，非本任务。

**约束核验**：`git show --stat` 仅 gem5 7 份补丁 + changelog + 本任务书，未动 QEMU/chipyard/tests ✓；独立 worktree、分支停在 `fa3cbc91` 未提交 ✓；完成区无具体 `.work/**` 路径 ✓；共享源树本地提交 `dadao: gem5 patch series` 是 `apply_series` 常规产物，断言⑨ gem5 段 0 ⇒ 与新补丁集一致。

**findings（不阻断）**：① 完成区「56 = 52 linux/musl + 4 qemu」分解笔误（实测 46+2+8，总数与 gem5 段 0 无误）；② 完成区未披露共享源树该本地提交；③ spec「VERSION=1 由 loader 写」而 gem5 loader 明示头区 guest-owned 不写、QEMU 侧亦无写者 —— 归属待裁定；④ **设计层冲突（供 architect 定夺）**：验收 2 的 `tests/inst`（gem5 平台）半项与约束「只动 gem5 组件/补丁与 profile」互斥，`tests/ee-tiny/runtime.yaml` entry 仍 `0x10100`（归 testcases-002/003），本任务内不可达成，engineer 已披露并挂待裁定。

**判决：Accepted** —— 验收命令块在本人重跑下全部通过、两处可达 FAIL 与独立注入闭环真实、约束无违反；findings ①②③ 由 architect 收尾处置，④ 为任务书范围/验收冲突，若 architect 裁定须本任务自带迁移，则最小返工点 = 迁 `tests/ee-tiny` entry/布局并跑 `run_inst_tiny.py --platforms gem5`。

### 第 1 轮 engineer 自审

逐行审查 7 份补丁 diff（fs.py/`fs_workload.{cc,hh}`/`fs_tlb.{cc,hh}`/两份 `.py` 参数）+ 证据脚本：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| guard 洞只做 contain 判定，未判区间重叠 | ❌不修 | — | 8 字节对齐访问（guard 4 KiB 对齐）不可能跨入 guard；4 B 取指同理；未对齐访问先按 MALIGN 处理 |
| image_window 上限只比 SRAM 大小，未扣 kernel_base 偏移 | ✅已修 | 构造期 `p_image_window > p_sram_size - (kernel_base-sram_base)` 即 fatal | build rc=0；clean 档 `image_window=0x20000` 正常实例化 |
| `loadRaw` 注释仍写 "BootROM trampoline" | ✅已修 | 改为 power stub 移交后跳入口 | 重新生成 patch 后 `check-patch-tree` gem5 段 0 problem |
| 证据脚本用 `md5sum`/`cut` 与自身比较 | ✅已修 | 注入前记 `config_md5_before`，第 9 节与注入后值比较 | `run.sh` rc=0，该行 PASS |
| app 用 `or.w` 造常量得到高位污染 | ✅已修 | 改用 `set.rd/set.rb` 写全 64 位；期望值回读校验 | DUMP rb1=0x2222、签名 0xfa 通过 |
| `check-wuming-cycles` 红 | ⏸延后 | 未改（契约/文档非本任务范围） | 基线 `71fdf6fe` 同源复现同一 FAIL 行，rc=1 |
| `check_tiny_hmon` 旧地址 | ⏸延后（依赖） | 未改 | 见「遗留/待裁定」，依赖 testcases-002/003 |
