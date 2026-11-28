# m19-testcases-005: 启动固件 power/hmon 迁移（8 KiB ROM 可启动）

**模块**：testcases
**项目里程碑**：M19
**依赖**：`m19-spec-002`、`m19-testcases-002`、`m19-testcases-003`、`m19-qemu-001`
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：已验证

## 背景

`m19-testcases-003` 已把 BootROM **构建器**改成 8 KiB 布局，但 `tests/ee-tiny/cfx_power_tiny.S` / `cfx_hmon_tiny.S` 仍是旧固件：

- power 读表 `0xE000`、复制 hmon 源 `0x2000`、跳 `0x10100`；
- hmon 数据槽 `0xD8–0xF8`，与 spec 新 `0xC00–0xCFF` 不一致；且 `rb0 + signed imms12` 到不了 `0xC00`（hmon 仅 `rd63` 一个 scratch）。

结果：新 8 KiB 镜像**结构合法但不可启动**。本任务把固件迁到新布局，并用新 QEMU/gem5/chipyard 验证 `power → hmon → 应用`。

## 目标

1. `cfx_power_tiny.S`：表偏移 `0x1F00`、hmon 源 `0x800`、复制目标 `HMON_SRAM_BASE`、跳 `ENTRY=0x2000`；校验/复制长度/边界按 8 KiB。
2. `cfx_hmon_tiny.S`：数据槽布局定案（`0x0C00` 可行方案 / `0x7C0` / 追加 RB scratch / 收回 spec 分区）；若需改 spec 分区，写入「待裁定」并说明影响。
3. `cfx_power_tiny.lds` / `cfx_hmon_tiny.lds` 与新 BootROM 布局一致；`build_tiny_bootrom.py` 的断言/表项同步。
4. 新 QEMU（qemu-001）、gem5（gem5-002）、chipyard（chipyard-004）跑通同一 8 KiB 镜像：`power → hmon → 应用`，`SYS_EXIT`/签名一致。
5. 不接板；不改 picolibc/arch（归其它任务）。

## 验收（逐条贴真实 rc）

1. 8 KiB BootROM 镜像在新 QEMU 下启动到应用；`power` 的复制/表校验/跳转均有真实日志或探针。
2. hmon 数据槽读写正确；若采用 `0xC00` 之外方案，给出 spec/任务书待裁定与理由。
3. **可达 FAIL ≥2 路**：① 表偏移写回 `0xE000` ⇒ 启动失败；② 跳转写回 `0x10100` ⇒ 启动失败；均需还原回绿。
4. gem5/chipyard 同一镜像跑通；签名/退出码一致（或记录跨任务阻塞）。
5. `check-inst-asm`/`check-tests-index` 真实 rc；基线红逐行对照。

## 约束

独立 `git worktree`；**不提交 git**；只动 `tests/ee-tiny/cfx_power_tiny.*`/`cfx_hmon_tiny.*` 与 `build_tiny_bootrom.py` 必要断言；不改 QEMU/gem5/chipyard 源码；不接板；完成区不写具体 `.work/**` 路径。

## 待裁定

1. **power 未实现 §6.2 第 2 步放核握手（`VERSION`+`MAILBOX`）**：`MAILBOX` magic 仍是 `[OPEN]`（§6.2.1）⇒ 无值可比；QEMU/gem5 装载器也未写 `VERSION`/`MAILBOX`（本任务实测 QEMU 侧无写）。固件保持「不检查」（与迁移前一致）。请裁定 magic 取值 + loader 写入口径 + 归属（本任务补 / 新任务）。
2. **hmon 数据页页内偏移定案（固件↔框架契约）**：`0xC00` cause_id、`+0x08` cause_ip、`+0x10` cause_info、`+0x18` 返回地址（power 写默认、框架可覆盖）、`+0x20` 保存 rd63、`+0x28` 保存 rb63。spec §6.2 只定 `0x0C00–0x0CFF` 页面 ⇒ 页内偏移须同批落到全部消费者；`tests/inst`、`tests/arch`、`tools/chipyard`、`tools/testcases/arch/min_rom_probe_integ007t.py` 仍用 `0xD8–0xF8`（本任务文件集外），归属待定（`m19-gem5-003` 只覆盖 gem5 harness）。
3. **hmon 处理体从 `0x500` 开始（段内 0x004–0x4FF 填充零）**：`rb0` 相对即时数是有符号 12 位（`IP+0x7FF` 上限），而「保存 rb63」的引导指令必须 IP 相对落在 `0xC28` ⇒ 处理体须在 `IP ≥ 0x401`；故入口一条相对 `jump` 跳到 `0x500`。备选（若要求代码从 0 连续）：借 `cfx_hmon cg6` scratch 寄存器做引导（QEMU/gem5/RTL 均实现 cg6 scratch≥2），代价是把 `cg6 rc0` 变成 hmon 私有资源。请裁定留用填充方案还是改用 cg6。
4. **返回槽（`+0x18`）是否写回 spec 正文**：新 §6.2 第 8 步只写「返回前把 `cg5 rc10` 写为 `excp_cause_ip + 4`」，不再提返回槽；固件仍保留「power 写默认值 + 框架可覆盖」的槽（`tests/inst` 的异常落点机制依赖它）。请裁定是否在 spec 补一句该槽语义。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` = **16 checks / 0 failed / 1 blocked，rc=0**（无 gem5 环境时 10/0/2，rc=0）；`run.sh --inject` = **77 checks / 0 failed / 1 blocked，rc=0**（6 路注入均真红、`cp`+md5 还原回绿）。门控真实 rc：`check-tests-index` **0**（基线 rc=0，逐行相同）；`check-inst-asm` **rc=2**（`0/274`，与基线 `50ff6f34` 输出归一化后 `diff` 为空）；`make build-bootrom` rc=0（镜像恰 8192 B）。
**修改文件**：`tests/ee-tiny/cfx_power_tiny.S`、`tests/ee-tiny/cfx_power_tiny.lds`、`tests/ee-tiny/cfx_hmon_tiny.S`、`tests/ee-tiny/cfx_hmon_tiny.lds`、`tools/testcases/arch/build_tiny_bootrom.py`（`git status` 仅此 5 项 + 本任务书；无越界改动）。
**验收结果**：
1. 镜像：**8192 B**；power 段 360 B（≤2 KiB）、hmon 段 1340 B→表项 1344 B（≤0xC00）、保留区 `0x1400–0x1EFF`/`0x1F30–0x1FFF` 全零、表 `@0x1F00`（magic/ver/count/boot_magic = `0x44424F54`/1/1/`0x30001`，entry type=1 flags=0x3 offset=0x800）。新 QEMU（8 KiB 几何，`-M help` 自述 8 KiB ROM + 256 KiB SRAM + 8 KiB hmon）跑通 `power → hmon → 应用`：应用在 `0xffff_ff00_2000` 取指（in_asm 命中）、park 循环未执行、`SYS_EXIT(0)` ⇒ 宿主 rc=0。power 复制/校验/跳转的可观测证据 = 签名槽 [1]/[2]/[3]（cause_ip = `BOOTROM+0x134`（trap 地址）、cause_info = `0x7f0f0001`（trap 编码）、返回 = trap+4）。
2. hmon 数据页：两次移交后 6 槽逐槽相等——`+0x00` cause_id=1、`+0x08` cause_ip、`+0x10` cause_info、`+0x18` 返回地址（探针自装落点被 hmon 采用 ⇒ `escape` 落在 `app_trap+4`）、`+0x20` 保存的 rd63、`+0x28` 保存的 rb63（power 与探针各自设定已知值，`escape` 后两个寄存器原值完好）。页内偏移见「待裁定 2」。
3. 可达 FAIL 6 路（要求 ≥2）：① 表偏移 `0xE000` ⇒ 构建 PASS 但 QEMU 20 s 未到应用、无签名、in_asm 显示停在 park（`0xffffffff0164`）；② 跳转 `0xffffff010100` ⇒ 超时、无签名、旧入口被执行、应用入口从未取指；③ 探针 cause_info 期望值错 ⇒ guest `SYS_EXIT(5)`；④ 探针 rd63 期望值错 ⇒ `SYS_EXIT(1)`；⑤ hmon 体偏移 `+0x10` ⇒ 构建器拒（`bootstrap at 0x0510 reaches 0xc38`）；⑥ 入口 jump `+4` ⇒ 构建器拒（`entry jump target 0x504 is not the bootstrap`）。六路均 `cp`+md5 三段对账（注入前=还原后）并回绿。
4. 三平台：**gem5 FS Tiny 用同一 8 KiB 镜像 + 同一探针 PASS**（`GEM5_EXIT_CAUSE=semi:ADP_Stopped_ApplicationExit`、`GEM5_EXIT_CODE=0`），**16 槽签名与 QEMU 逐字节相同**；**chipyard BLOCKED**——依赖 `m19-chipyard-004`（`WumingTinyConfig` 8 KiB 几何 + 重生成签入 `bootrom.tiny.hex`）与 RTL 仿真/板卡，本任务不接板、不冒充通过。
5. 门控：见上（`check-tests-index` 0；`check-inst-asm` rc=2 与基线逐行相同，失败点在旧版已装 QEMU 的应用装载校验）。
**新发现/坑**：① `rb0` 相对访存上限 = `IP+0x7FF`（`imms12`）⇒ `0xC00` 数据页**必须**抬高 IP 或借 scratch；② `add.o` 只有 `bbd`、`cmp.uo` 只有 `dbb`/`rd` 形 ⇒ rd+rd 相加先落 rb、rb 与符号地址比较经 rd；③ QEMU semihosting 输出默认走 **stderr**（证据改用 `-chardev file`+`-semihosting-config` 才不被日志污染）；④ gem5 把 semihosting 输出接在自身 banner 之后（取 stdout 末 128 B）；⑤ 构建器两条新判据（入口目标 == 引导指令偏移、唯一条 rb0 相对访存目标 == `0xC28`）均验证可红；⑥ chipyard 签入的 `bootrom.tiny.hex` 仍是旧固件（组件补丁），`m19-chipyard-004` 必须用 `--hex-out` 重生成；⑦ `tools/testcases/arch/min_rom_probe_integ007t.py` 仍写死 `0xD8` 槽与旧布局 ⇒ `check-arch` 的 `integ007t` 会因本次迁移转红（文件集外）。
**遗留问题**：① 消费者迁移（`tests/inst` 宏与 11-cfx/12-misc、`tests/arch`、`tools/chipyard/excp/*`、`tools/testcases/arch/min_rom_probe_integ007t.py`）归跨任务，见「待裁定 2」；② chipyard 腿 BLOCKED（见验收 4）；`make check-arch`（L3）未跑（依赖新几何合入 + `integ007t` 迁移）；③ `Makefile` 的 `build-bootrom` 注释仍写「8 KiB 段/64 KiB 镜像」（共享文件，`m19-testcases-003` 已登记）；④ 放核握手未实现，见「待裁定 1」。

## 审阅记录

### 第 1 轮 engineer 自审（逐行审查 5 个改动文件 + 证据脚本反例门控）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 构建器/`check_image` 把入口 jump 目标算成 `4+imms24<<2`（入口指令 IP 自身即段内偏移 0）⇒ 目标恒偏 4，实际 `0x504` 却判 PASS | ✅已修 | 两处改 `target = imms24<<2`；构建器新增「入口目标 == 引导指令偏移」判据 | 注入 `jump +4` ⇒ 构建器报 `entry jump target 0x504 is not the bootstrap at 0x500`；`check_image` 的 `target == 0x500` PASS |
| F2 hmon 段上限误用未补齐长度（表项用补齐后 size） | ✅已修 | 改回对 `hmon_size` 判限 | `build-bootrom` rc=0；self-test 的 `--max-segment-size` 注入仍被拒 |
| F3 `HMON_DATA_SIZE` 定义后未使用（死常量） | ✅已修 | 增数据页槽位「8 字节对齐且在页内」断言 | builder PASS（当前 6 槽全过） |
| F4 `verify_image` 用补齐后的段，段尾是零填充 ⇒ 「末指令 = escape」假红 | ✅已修 | 剥尾零字后再判 | `--self-test` rc=0 |
| F5 证据脚本 3 处假红：`"!= 0"` 当期望字符串；用 `git diff` 判「已还原」（本任务本就有未提交改动）；构建注入的错误文案在子日志未被 grep | ✅已修 | 加 `assert_ne`；改比「注入前变更集」；grep `builder.log` | 6 路注入 77/0 PASS |
| F6 `edit_once` 用单引号 `'\t…'` 不匹配真实制表符 ⇒ 两路构建注入「edit failed」 | ✅已修 | 改 `$'\t…'` | `hmon-body-offset`/`hmon-entry-target` 注入真红、还原回绿 |
| F7 签名取错通道（QEMU semihosting 默认 stderr）⇒ green 签名 0 B | ✅已修 | `-chardev file,id=semi` + `-semihosting-config chardev=semi` | green 恰 128 B；注入路径签名 0 B |
| F8 探针用 `ld.o`（8 B）读 hmon 首字，期望按 4 B 写 ⇒ 槽 [15] 假红 | ✅已修 | `check_slots` 按 `>Q` 取镜像首 8 B | 槽 [15] PASS |
| F9 探针的 rd63/rb63 期望值与设定值同源 ⇒ 注入「期望值」不能证明断言可失败 | ✅已修 | 拆 `RD63_EXP`/`RB63_EXP` 与 `RD63_VAL`/`RB63_VAL` | 注入 `RD63_EXP` ⇒ `SYS_EXIT(1)` |
