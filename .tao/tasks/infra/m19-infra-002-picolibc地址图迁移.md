# m19-infra-002: picolibc Tiny 地址图迁移（组件补丁）

**模块**：infra
**项目里程碑**：M19
**依赖**：`m19-spec-002`
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：已验证

## 背景

picolibc 安装根/cross 链接脚本仍按旧 Tiny 布局（entry `0x10100`、SP `0x7eff00`、8 MiB SRAM）。新几何为 entry `0x2000`、SP `0x3F000`、SRAM 256 KiB、EXIT `0x30`、signature `0x1000`；不改则 `check-picolibc-tests` 在新 QEMU/gem5/chipyard 下必红。

## 目标

1. 更新 `components/picolibc` 的 Tiny 链接脚本/补丁：`picolibc-tiny.ld` 的 RAM/entry/SP/EXIT/heap；按 256 KiB、`0x2000` 入口、`0x3F000` SP。
2. 更新 series/patches/changelog；重建安装根；确认 `make build-picolibc`（或等价）可重跑。
3. 版本号/组件补丁集变更**待用户确认**；未确认前只落内容，不擅自升号。
4. 不改 `tests/inst`/`tests/arch`（归 testcases-002/004）。

## 验收（逐条贴真实 rc）

1. picolibc 安装根重建成功；Tiny smoke/代表测试在新几何 QEMU 下跑通。
2. `check-patch-tree` picolibc 段 0 problem；`check-component-changelog` rc=0。
3. **可达 FAIL ≥2 路**：① 链接脚本 entry 写回 0x10100 ⇒ 装载红；② SP 写回 0x7eff00 ⇒ 栈越界/红。
4. 版本号未升级（除非用户当轮确认）；不接板。

## 约束

独立 `git worktree`；**不提交 git**；只动 `components/picolibc` 与必要清单/索引；不改 QEMU/gem5/chipyard/testcases；完成区不写具体 `.work/**` 路径。

## 完成区

**测试结果**：证据脚本 31/31 通过（rc=0）；`make build-picolibc` rc=0（`libc.a` 2053170 B、`libsemihost.a` 71924 B）；链接探针 rc=0（`_start=0xffffff002000`、`__stack=0xffffff03f000`、`__heap_end=__stack_bottom=0xffffff038000`、`__exit_block=0xffffff000030`、`PT_LOAD memsz=0x000a78`）。
**修改文件**：`components/picolibc/patches/scripts/cross-dadao.txt.patch`、`components/picolibc/patches/picolibc.ld.in.patch`、`components/picolibc/{README.md,changelog.md}`（`series` 17 不变）。
**验收结果**：
- 安装根重建 rc=0；生成 `picolibc_noflash.ld`：flash `0xffffffff0000`/`0x2000`、ram `0xffffff002000`/`0x3d000`、栈预留 `0x7000`（guard 4 KiB + STACK 24 KiB）。
- `check-patch-tree` rc=0（picolibc 17 patches，0 problem）；`check-component-changelog` rc=0；`apply-series` 幂等 rc=0。
- 可达 FAIL ①（entry）：注入 `0xffffff010100` ⇒ `_start` 断言红（观测 `0xffffff010100`）；还原后回 `0xffffff002000` 绿。②（SP）：注入 `0xffffff7eff00` ⇒ 不在 256 KiB SRAM（`0x7eff00 < 0xffffff000000`）且 crt0 立即数序列不含 `0xff03/0xf000`，断言红；还原回绿。
- 版本号未升级：`manifests/`、`spec/`、`contracts/` 无改动（待用户确认）。
- 新几何 QEMU smoke 未执行：依赖 `m19-qemu-001`/`m19-testcases-002/003` 未合入；旧 QEMU 试跑 rc=1（拒绝 `e_entry 0xffffff002000`，期望旧 `0xffffff010100`），现场已留。
**新发现/坑**：picolibc 的 `__heap_end`/`__stack_bottom` 由 `DEFAULT_STACK_SIZE` 派生；新几何取 `0x7000`（guard 4 KiB + 24 KiB 栈）使 `__heap_end=0x38000` 不进入未映射 guard、`__stack=0x3F000`。`PROVIDE` 符号无引用不进 symtab，证据用 `ld.lld -u <sym>` 强制保留后 `llvm-nm` 对账。任务书不在 `m19-spec-002` 基线（另一提交），已复制进 worktree 填写完成区。
**遗留问题**：新几何 QEMU smoke 待 `m19-qemu-001` + `m19-testcases-002/003` 合入后补跑；本分支未改这些文件。
**待裁定**：picolibc 组件/上游版本号是否升级（本笔未升，只落内容）。

## 审阅记录

### 第 1 轮 engineer 自审

- 审查范围：`cross-dadao.txt.patch`（默认内存图/栈预留）、`picolibc.ld.in.patch`（`__exit_block` 绝对符号）、README/changelog、安装版 lds 与链接探针。
- 逻辑核对：`ORIGIN(ram)+LENGTH(ram)=0xffffff03f000` 即 SP；`__heap_end=__stack-0x7000=0x38000` 即 guard 下界，`.stack` NOLOAD 覆盖 guard+24 KiB 栈、不进 PT_LOAD；`__exit_block=0xffffff000030` 在绝对头区，不占装载段；entry 由 `.text.start` 首段 + ram origin `0x2000` 保证。
- 边界核对：guard/栈/MemRAS 三段无重叠（`0x38000–0x39000` / `0x39000–0x3F000` / `0x3F000–0x40000`）；镜像窗口 128 KiB 由测试侧 `image_window` 约束，不在 lds 改。
- 防造假：`PROVIDE` 无引用不进 symtab，故探针用 `ld.lld -u` 强制保留；entry/SP 两支注入均真实触发断言红，均由独立命令观测（`llvm-nm` / `llvm-objdump`）。
- finding：无代码级未修项。备注：`git diff --check` 对 patch 文本的 context 行报 space-before-tab，这是 unified diff 的固有形态（非门控项，`check-patch-tree` 断言 ④⑥⑨ rc=0）；QEMU E2E 依赖见「遗留问题」。
- 判决：通过，状态转「待验收」。

### 第 1 轮 reviewer 验收

- **重跑证据脚本**（仓库根执行运行期证据目录内的 `run.sh`，共 3 轮：初跑 / 独立注入还原后 / `make build-picolibc` 重建后）：均 `checks=31 fails=0`、rc=0。
- **`make build-picolibc`**：rc=0，`build-picolibc: PASS`，`libc.a` 2053170 B、`libsemihost.a` 71924 B，与完成区逐字一致；重建后安装版 lds md5 仍 `7bdbd01e…`（可重复）。
- **几何现场核验**：flash `0xffffffff0000`/`0x00002000`（8 KiB）、ram origin(entry) `0xffffff002000`、ram size `0x0003d000` ⇒ `__stack=0xffffff03f000`、`__stack_size=0x7000` ⇒ `__heap_end=__stack_bottom=0xffffff038000`、`__exit_block=0xffffff000030`；与 `spec/Kaiwu` §1.1/§6.2.1 新几何逐值一致（spec-first）。
- **门控**：`check-patch-tree` rc=0（picolibc 17 patch(es)，源树在位、断言全跑，全表无 problem 行）；`check-component-changelog` rc=0（11 文件 ×4 断言 = 44 项 PASS）；`apply_series --component picolibc` 幂等 rc=0；`series` 17 行且本提交未改。
- **独立注入（`cp` 备份 + md5 对账，注入被测产物 = 安装版 lds）**：① entry 写回 `0xffffff010100` ⇒ rc=1、9 处 FAIL（ram origin / `_start` / SP / heap_end / MemRAS 等）→ `cp` 还原 md5 `7bdbd01e…` 相等 → 重跑 rc=0；② `PROVIDE(__stack)` 写回 `0xffffff7eff00` ⇒ rc=1、4 处 FAIL（`__stack (SP)` / `__heap_end` / guard / MemRAS）→ 还原回 rc=0；无 `.preinject` 残留，`git status` 干净。
- **版本号未升**：提交仅动 4 个 `components/picolibc` 文件 + 任务书；`git diff --name-only <父>..HEAD -- manifests spec .tao/contracts` 空；lock 中 picolibc `1.8.12`/`2ae376c6` 未变（按待裁定处理）。
- **BLOCKED 披露属实**：`m19-qemu-001`/`m19-testcases-002`/`m19-testcases-003` 各在独立分支（`9d9c984a`/`5b5b4a41`/`7789e747`），`git branch --merged master` 无 m19 分支 ⇒ 确未合入；新几何 QEMU smoke 未跑、旧 QEMU 拒 `e_entry` 的处置与依赖链披露一致。
- **约束逐条核**：只动 `components/picolibc` + 任务书；未触 `tests/inst`/`tests/arch`、QEMU/gem5/chipyard；独立 worktree；reviewer 本轮未提交 git、注入全部还原（md5 为证）。
- **findings（非阻断）**：① 证据脚本 SP 注入支改的是脚本自写探针 crt0（同源自比倾向），产品级 SP 可 FAIL 已由本轮独立注入补证；② 完成区「旧 QEMU 试跑 rc=1」无留存日志、无法复核（机制与 spec §6.2.2 `e_entry` 校验一致，采信）；③ 安装版 `crt0-semihost.o` 不引用 `__stack`（`llvm-nm` 无 `U __stack`），运行期 SP 由 `tests/ee-tiny` 的栈桩设置，归 `m19-testcases-002`，E2E 补跑时一并核。
- **判决：Accepted**。验收命令块在 reviewer 自己的重跑下全绿、两路注入均真实 FAIL 且 `cp`+md5 还原回绿、版本号未升、BLOCKED 披露属实；遗留 QEMU smoke 按依赖如实披露，待 `m19-qemu-001` + `m19-testcases-002/003` 合入后补跑（非本任务阻断项）。
