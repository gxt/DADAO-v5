# m20-gem5-004: gem5 SE 输出差异（`neural` / `pcompress2`）定位与修复（ISS-362 + ISS-367）

**模块**：gem5
**项目里程碑**：M20
**依赖**：`m16-gem5-026` 完成后再派（同组件写者）；可与 `m20-gem5-003` 串行
**可并行分片**：否（同改 gem5 SE 输出路径；两例合并处理）
**预估**：4–8 h（`pcompress2` 单例历史约 4408 s，长跑另计）
**档位**：大改（复核 ≤60 min）
**状态**：已验证

## 背景（M20 分诊，2026-11-25）

`ISS-362`/`ISS-367` 是同类问题：gem5 SE 跑完但输出与参考不同，qemu 侧通过。
- `ISS-362`：dynamic `MultiSource/Benchmarks/FreeBench/neural`，输出长度相同
  （358 B vs 358 B）但内容不同，首行 `Matrix size is 20x28` 一致。
- `ISS-367`：static `MultiSource/Benchmarks/FreeBench/pcompress2`，gem5 约
  4408 s 跑完、exit=0，但输出与参考不同，qemu 通过，比值 404×。

两例疑似同源（浮点舍入/格式化或 SE 输出通道），合为一个任务定位，避免重复。

## 目标

1. 先取 `neural` 单例（较短）做逐字节 diff，定位首个差异列，再判断是 FP
   语义、printf/格式化还是 SE 输出截断。
2. 期望值以 `neural.reference_output` / 程序语义为 oracle，**不得**用 gem5 或
   qemu 的输出反推；若发现参考输出本身有误，须先登记并停下问主会话。
3. 修复后 `neural` 与 `pcompress2` 输出均与参考逐字节一致（或按契约规定的
   格式差异显式登记 GAP，不得静默放过）。
4. `pcompress2` 单例长跑排节点或主控机空闲窗口；不得与其它 gem5 FS 跑批抢
   资源。

## 验收（逐条贴真实 rc）

1. `neural` 复现：修复前逐字节 diff 非空，给出首个差异列；修复后 `cmp` 为空。
2. `pcompress2` 复现/回归：修复后 `cmp` 为空；给出实际耗时与 rc。
3. 差异归因链：如果是 FP 舍入，引用 `spec/SimRISC-07`/IEEE-754 2019 的对应条；
   如果是格式化/输出，引用 `contract-semihosting` 或 libc 行为；不得只写「改了
   就好」。
4. 至少一条可达 FAIL：回退修复 ⇒ 同一 diff 复现；`cp` + md5 还原后回绿。
5. `check-gem5-decode`、`check-patch-tree` gem5 段 0 problem；长跑日志 + `*_EXIT`。

## 约束

独立 `git worktree`（分支 = `m20-gem5-004`）；不提交 git；只改
`components/gem5/**`、必要测试/探针与本任务书；不改 `spec/`、契约、`Makefile`。
任务书不写构建树/安装树/临时目录路径；证据落在「运行期证据目录内的 `run.sh`」。

## 完成区

**测试结果**：`run.sh` 29/29 PASS（rc=0，含门控与独立 oracle）；`--inject bytes|size|order|oracle` 均 rc=1（目标检查变红，原始证据 md5 不变），随后默认 26/26 PASS rc=0。`check-gem5-decode` rc=0（263/263 + 391/391 + 28/28，failures 0）；`check-patch-tree` gem5 段 0 problem（tree-wide rc=2 = llvm-project 2 + musl 2，均在途/既有，分段披露）。失败原因：无。

**修改文件**：`components/gem5/README.md`（订正 GEM5-023t「驱动再拼接」过期说法，写明分通道判据与两例结论）；本任务书。**未改 gem5 实现**——现场判定无实现缺陷（`src/sim/fd_array.cc:71-101` 两个独立 fd + `se_workload.cc:doWrite` 逐次透传）；运行期证据在运行期证据目录（不入 git）。

**验收结果**：
1. `neural`（dynamic，本机单例）：旧口径（stdout 在前 + `exit 0\n`）对单流参考长度 358 B 相等、`cmp` = `differ: byte 1, line 1`（`0x4d 'M'` vs `0x43 'C'`）；分通道两路 `cmp` 均为空（311 B sha256 `eb219347…` + 40 B `04358eab…`），`klass=pass`、exit 0、603.1 s / 844,431,128 inst。
2. `pcompress2`（static）：旧口径 82339 B 相等、`cmp` = `differ: byte 1, line 1`（`0x50 'P'` vs `0x43 'C'`）；分通道两路 `cmp` 为空（82292 B `97392e62…` + 40 B `04358eab…`），`klass=pass`、exit 0、1115.84 s / 1,586,821,182 inst。独立 oracle：`ref.stdout` 与其自身输入 `test.in` 逐字节相等（round-trip）。
3. 归因链：① 两例唯一 stderr 是 `main` 开头两行 `fprintf(stderr,…)`（`pcompress2.c:34-35`、`neural.c:107-108`），先于任何 stdout；上游 `RunSafely.sh` 单流参考因此是「stderr 块 + stdout 块 + `exit N`」（`stderr+stdout+exit 0\n` 与参考 `cmp` 为空，已验）。② gem5 SE 的 fd1/fd2 是两个独立宿主文件（仅 `output==errout` 才共用），无交织、无截断（字节数/sha256 全等）。③ 旧驱动 `095453ed` 取 `stdout+stderr` 再对单流参考，顺序相反 ⇒ 同长度、首字节即差；**非 FP 舍入/格式化/截断**（输出无计算值；`pcompress2` 的 `1.60563e+08 op.` 来自输入 `test.in`）。判据依据 `docs/Process-09 §17`；libc 侧 musl `stdio/stdout.c`/`__stdout_write.c`/`stdio/stderr.c`。
4. 可达 FAIL：`--inject bytes`（同长改 1 字节）⇒ `neural_stdout_cmp` 红；`--inject size`（截 1 字节）⇒ 尺寸/`cmp` 4 项红；`--inject order`（旧顺序当参考）⇒ 反向验证红；`--inject oracle`（篡改期望文档）⇒ 独立 oracle 红；四者 rc=1，原始证据 md5 不变，随后默认全绿。

**新发现/坑**：ISS-362/367 的症状在 `m13-testcases-006`（分通道判据）后已消失，本次是**复验**而非新修；issue 文字「首行 `Matrix size is 20x28` 一致」不准确——单流参考第 1 行是 `Compile date: today`，gem5 旧口径第 1 行才是 `Matrix size`。历史 2972/4408 s 是 48 并发节点数据，本机单例 603.1/1115.8 s，不可直接比。建议沉淀：输出类 oracle 必须分通道，单流顺序不作判据。

**遗留问题**：无（`pcompress2` dynamic 未复验，任务只要求 static）。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| repro 检查初版用 `ref.stdout+ref.stderr` 构造「单流参考」，与旧口径同序 ⇒ 恒真、不可失败 | ✅已修 | 改为直接对驱动 run 目录的 `*.reference_output`（上游单流文件）比较，并保留 `exit N` 尾 | `--inject order` ⇒ `neural_reference_order_cmp` FAIL、rc=1；默认该检查 PASS |
| 证据脚本 artifact 路径少一层 `runtime/`，首次运行 rc=2 MISSING | ✅已修 | `NEURAL_DIR/PCOMP_DIR/JSON` 加 `runtime/` 前缀 | 修正后首轮 27/27 PASS；最终 29/29 PASS rc=0 |
| 独立 oracle 初版 `print` 污染 `$?`，检查会读错退出码 | ✅已修 | 去掉 `print`，仅以退出码判定 | `oracle_from_source_and_input` PASS；`--inject oracle` FAIL、rc=1 |
| 任务前提与现场不符（两例在 M13 已由分通道判据转绿），是否需要造 gem5 代码改动 | ❌不修 | 无实现改动；在完成区如实记录「复验 + 文档订正」，README 订正过期说法 | 两例分通道 `cmp` 为空；`fd_array.cc`/`doWrite` 证明两 fd 独立、逐次透传；全量检查 29/29 |
| `pcompress2` dynamic 档未复验 | ⏸延后 | 无（任务只要求 static；同一二进制、同一参考拆分） | 任务书验收 2 限定 static |
| 还原纪律：本任务无 gem5 实现改动，不存在源码注入 | ✅已按纪律 | 注入只落 `tmp-inject/` 副本；脚本对 4 个原始证据文件做 md5 前后对账（不用 git 还原） | 四模式注入后均打印 `OK evidence artifacts untouched (md5 identical)`，随后默认 26/26 PASS rc=0 |

**判决**：无未修 finding；任务状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-25）

**重跑（我自己的终端；证据脚本 = 运行期证据目录内的 `run.sh`，workdir 仓库根）**
- 默认 `REPO_ROOT=<worktree> ./run.sh` → `SUMMARY checks=29 fails=0`，rc=0；`--skip-gates` → 26/26，rc=0。
- `--inject bytes|size|order|oracle` → rc=1，分别 2/4/1/2 项 FAIL（`neural_stdout_cmp`；+`neural_stdout_bytes`/尺寸；`neural_reference_order_cmp`；两个 oracle 检查），四次均打印 `OK evidence artifacts untouched by injection`；随后默认复跑 rc=0。
- `make check-gem5-decode` → rc=0（positive 263/263、negative 391/391、legality 28/28、legacy 2/2、failures 0）；`make check-patch-tree` → rc=2（llvm-project 2 + musl 2 条 assertion，均非 gem5），gem5 段 `106 patch(es)`、`gem5: assertion` 0 条。

**独立核验（我自己 cmp / 读产物，不采信完成区转述）**
- 分通道：neural 311 B + 40 B、pcompress2 82292 B + 40 B 与 `refs/*.ref.*` `cmp` 全 rc=0，sha256 与完成区一致（`eb219347…`/`04358eab…`/`97392e62…`）。
- 旧拼接口径复现：stdout 在前 + `exit 0\n` → 358 B / 82339 B 与单流参考等长，`cmp` 均 `differ: byte 1, line 1`，首字节 `M`(0x4d)/`P`(0x50) vs 参考 `C`(0x43)；改为 stderr 在前 → 两例 `cmp` rc=0。
- 旧驱动取证：commit `095453ed` 的 `tools/testcases/tset/llvm-ts/run_llvm_ts_user.py` L2443 `stdout = se["stdout"] + se["stderr"]`、L2533 `actual_doc = stdout + (b"exit %d\n" % rc)`，确与单流参考顺序相反。
- 独立 oracle：`pcompress2` 的 `ref.stdout` == 输入 `test.in`（82292 B，`cmp` rc=0）；`neural` 期望由 `neural.c` 字面量（L131/174/176/180/189/454/485）+ 输入前三行 20/28/10 重建，与 `ref.stdout` 逐字节相等；两例 stderr 仅 `pcompress2.c:34-35` / `neural.c:107-108` 两行横幅（40 B）。期望不取自 gem5 输出。
- README 订正与 `docs/Process-09 §17` 一致（分通道、禁拼接、拆分器按源码 stderr 格式串拆两路）；`--guest-stdout/--guest-stderr` 是现行 gem5 CLI（`tools/testcases/lib/gem5_se_engine.py:389` 在用）；`fd_array.cc` 两 fd 独立（仅 `output==errout` 共用）、`arch/dadao/se_workload.cc:1373 doWrite` 每次 `::write` 逐次透传。

**独立注入（我自己的 cp + md5，非采信 engineer 自检）**
- `cp` 备份 neural `guest.stdout` + 记 md5 `daadfcb8…` → 翻转第 100 字节 → `run.sh` rc=1（`neural_stdout_cmp` FAIL）→ `cp` 还原、md5 相等（`md5sum -c` OK）→ 复跑 rc=0（29/29）。

**范围核验**：`git status --porcelain -uall` 仅 `components/gem5/README.md` + 本任务书；`git diff --name-only HEAD` 无 `components/gem5/{src,patches}`；gem5 源树 clean（HEAD `c7f9be6`，与证据 README 身份一致）；未碰 m20-llvm-003。

**遗留（文档级，不阻断）**：① 完成区写「`se_workload.cc:doWrite`」，实际文件为 `src/arch/dadao/se_workload.cc:1373`；② 完成区「随后默认 26/26」实为 `--skip-gates` 档（默认含门控为 29）；③ 门控计数省略 legacy 2/2。建议 architect 收尾时顺手订正。

**判决**：**Accepted**——验收命令在我自己的重跑下全部通过，四条硬约束无违反；遗留仅文档级小错。
