# GEM5-022t: gem5 SE heap/VMA（brk + mmap/munmap/mprotect）

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-021t`（已验证基线：SE 能跑 tset，缺 syscall 面）
**状态**：已验证

## 执行环境
本地；只扩展 gem5 SE 的 guest 内存管理 syscall，不改 QEMU、不改测试用例/期望。

## 背景与事实（`GEM5-021t` 基线）

- gem5 SE 现有 syscall 面只有 `ioctl/write/writev/exit/exit_group/set_tid_address`
- static tset 基线（QEMU 587 pass / gem5 310 pass / blocked 270）中，**`brk` 是最大单一缺口：114 例**，`mmap` 21 例；代表：`libc-test:functional/{env,mbc,memstream,search_hsearch,search_insque}`、`libc-test:malloc-oom` 等
- 失败形态：malloc 一进入堆就 `fatal: syscall 214 not implemented (brk)`（或 mmap 号）
- SE 侧已有 `Process` 的 `brk_point` 与初始栈/映像布局，缺 syscall 表项与 VMA 映射路径

## 目标

1. **`brk`（214）**：实现 grow/shrink；缩小到 `brk_point` 以下按现场允许值处理；超出可映射范围 ⇒ 返回原 brk（Linux 语义）或 `ENOMEM`（按 `contract-syscall` 口径，先查契约再定）；新增/拆除匿名 VMA，页大小 64 KiB、大端。
2. **`mmap`（222）/`munmap`（215）/`mprotect`（226）**：至少支持 `MAP_PRIVATE|MAP_ANONYMOUS` 与 `MAP_FIXED` 语义；文件映射若 tset 静态用例需要再做（`MAP_SHARED`/`MAP_ANONYMOUS` 视现场）；
3. **VMA 管理**：地址区间注册/查找/拆除，与 `SETranslatingPortProxy`/页表一致；`munmap` 后访问按 fault 处理；
4. **不改测试**：`tests/tset/**`、`tests/**` 的用例与期望不动。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{se_workload.cc,se_workload.hh,process.cc,process.hh,...}`（按现场）、`components/gem5/changelog.md`、本任务书、`milestones.md`。

**不在范围**：文件 I/O、时钟、信号、线程/futex（后续任务）、`convert_f2i` 语义（用户待裁定）、QEMU 实现、测试用例与期望、`docs/TestReports/M11-三平台一致矩阵.md`。

## 验收标准

1. 两引擎同一 static 产物：`brk`/`mmap` 相关 blocked 案例（基线 114 + 21）全部**不再 blocked**；转为 PASS 或真实 FAIL（失败须给最小复现与归属，不得回填 BLOCKED）。
2. 重跑 `GEM5-021t` 基线驱动（static）：`qemu_only_fail` 仍为 0；`gem5_only_fail` 只剩已知 `convert_f2i` 相关 9 例（用户裁定前不修）；其余套件数逐项记录。
3. 稳定性：受影响的代表案例各跑 ≥3 次，结果一致。
4. `make check-inst`、`make check-arch`、`make check`（L1）rc=0；gem5 源树 base+1 clean、`check-patch-tree` rc=0。
5. 反例：把 `brk` 改回未实现（或返回 0）⇒ 代表案例回到 blocked/fail；`cp`+`md5sum -c` 还原重建后回绿（禁 git 还原）。
6. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 优先做 `brk`（114 例）再做 `mmap`（21 例）；每完成一项即用基线驱动复测，别攒到最后。
- `mmap` 的 `MAP_SHARED`/文件映射先测量再决定是否本轮做；若 tset 静态用例不需要，登记为后续。
- 页大小固定 64 KiB；地址范围与 `machine-profiles.yaml` 的 SE 布局一致。

## 完成区

**测试结果**：`GEM5-021t` static 基线重跑（QEMU 侧 587 例沿用同一基线 JSON）gem5 SE 通过 **361/589**（基线 310），both_pass 361（基线 310），blocked **217**（基线 270）；`qemu_only_fail=0`；`gem5_only_fail=10` = 已知 convert_f2i 9 例 + 新解阻 `llvm-ts:Olden/power`（同根因）；`heap/VMA (brk|mmap|munmap|mremap)` blocked **全 0**（基线 brk 114 + mmap 21）；libc-test pass 245→263、llvm-ts pass 27→60、embench 38/38。证据脚本（本任务证据目录 `run.sh`）默认模式 rc=0：heap/mmap/mremap 探针各 3 次（rc+stdout 双判）、munmap 后访问真 fault rc=134、3 个 libc 自检案例 rc=0×3、`llvm-hello` 非空 stdout×3、`malloc-oom` 转 `prlimit64`；`INJECT=1` rc=0：brk 回 `fatal` ⇒ blocked **且** mremap 重叠检查注入 `if (false && …)` ⇒ 探针 FAIL，`cp`+源文件 md5 还原重建后两探针回绿（判据 = 源 md5 + rc/stdout，不用二进制 md5）。

**修改文件**：`components/gem5/patches/src/arch/dadao/{se_workload.cc.patch,process.cc.patch,process.hh.patch}`（`make_patch.py gem5` 重导出）、`components/gem5/changelog.md`、`components/gem5/README.md`（SE 边界，越界已披露）、本任务书、`milestones.md` 行。

**验收结果**：`check-patch-tree` rc=0（7 components/305 patches）；`check-source-state` rc=0（gem5 `2f95184` count=1 clean=True）；`check-inst` rc=0（44/44）；`check-arch` rc=0（14/14）；L1 `make check` rc=0；`build-gem5` rc=0。共享 gem5 二进制 md5 `ee6eb41bd475089b32e1dce3ecece158`（构建 `2026-11-06T06:46:48Z`；仅作标识——重编有 `__TIME__`/build-id 差异，回绿按上述功能判据）。

**新发现/坑**：① `MemState::extendMmap` 语义须由调用方维护 `mmapEnd`，且 `munmap` 要交还释放的窗口顶部；否则 libc-test `t_vmfill` 探测序列泄漏区间，实测把 `malloc-brk-fail` 打成真实 FAIL。② mallocng `realloc` 走 `mremap`(216)；`MREMAP_FIXED` 目标与旧区间重叠（同起址/包含/被包含）必须 `EINVAL`，否则 `MemState::remapRegion` 触发 `isUnmapped` 断言或把旧区间拆掉。③ 第 10 个 `gem5_only_fail` 定位为 convert_f2i 同根因：`(int)((0.7-0.65)/0.01)`，真值 `0x1.3fffffffffff8p+2` = 5 − 2⁻⁴⁷ = 4.999999999999993（截断 4 / 舍入 5），trace `CAST_R` 行与 `iR=4(QEMU)/5(gem5)` 可复算。④ 探针口径：musl `brk()/sbrk()` 是 `-ENOMEM` 桩、`mprotect` 自行 64 KiB 对齐、非 FIXED 的非对齐 hint 由内核取整——必须用 `syscall(SYS_*)`/多分支断言直测。⑤ 运行期日志目录的 `.rc` 后缀触发 `check-run-artifacts` A3，已改 `.log`/`-rc.txt`。

**遗留问题**：① `gem5_only_fail` 10（=9+1）全部属用户待裁定的 convert_f2i，裁定后复核 `Olden/power`。② **`mprotect` 仅接受不建模权限**：未来任何「写只读页 / 访问 `PROT_NONE` 页应 fault」的用例在 SE 上**不可信**（会静默成功）；当前 589 例无此类 oracle，无假绿。③ 文件映射 mmap 未实现（`ENODEV`），静态 tset 无需要，登记后续。④ 解阻后暴露的后续能力缺口（不在本任务范围）：resource limits 7（`prlimit64`）、file I/O 66（`read`/`readv`/`openat`…）、time budget 80、time/clocks 29、signals 22、IPC 6、threads 4、process creation/info 各 1。

### 审阅记录 → 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `extendMmap` 未回写 `MemState::mmapEnd`，后续映射与前次探测区间重叠 | ✅已修 | 成功分支 `setMmapEnd(start)` | mremap 探针原地/搬移/固定三条路径均按预期；基线全量 |
| F2 `MREMAP_FIXED` 误走原地增长分支，返回旧地址 | ✅已修 | 原地增长排除 `MREMAP_FIXED`；FIXED 恒走搬移（含 shrink 的 FIXED 路径） | `probe:mremap` rc=0（fixed/in-place/move/shrink 全断言） |
| F3 `munmap` 释放的窗口顶部不复用，`t_vmfill` 探测序列失败 ⇒ `malloc-brk-fail` 真实 FAIL | ✅已修 | `doMunmap` 在 `start+mapped` 不超窗口时回写 `mmapEnd` | `malloc-brk-fail` 转 blocked(261)；基线 gem5_only_fail 只剩 f2i 组 |
| F4 探针口径错误（musl `brk/sbrk` 桩；`mprotect` 自行对齐） | ✅已修 | 探针改 `syscall(SYS_brk/SYS_mprotect)` 直测；`mremap` 覆盖 fixed/in-place/move/shrink | heap/mmap/mremap 探针 PASS ×3 |
| F5 探针 stdout 与 gem5 banner 混写（同一 host 文件双 fd 偏移） | ✅已修 | 改用 `--guest-stdout/--guest-stderr`，sim 日志独立 | 探针输出逐字节干净、sha 可复现 |
| F6 运行期日志目录下 `.rc` 后缀触发 A3 | ✅已修 | 删除 `.rc`，改 `.log`/`-rc.txt`；共享二进制 md5/注入窗口另立 `.txt` | L1 `check` rc=0（含 check-run-artifacts） |

判决：全部 finding 已修，状态 `待验收`。

### 审阅记录 → 第 1 轮 reviewer 验收

**判决：Needs Revision**（阻断 1 条：`mremap FIXED` 重叠输入可崩宿主；验收标准 1–5 与全部门控经 reviewer 亲跑复核通过）

**重跑记录（reviewer 独立执行，本分支工作树，贴真实退出码；原始输出留审查会话，未提交 git）**
- `make check-patch-tree` rc=0（7 components/305 patches OK）；`make check-source-state` rc=0（gem5 `0d811d35b076` count=1 clean=True）；`make build-gem5 JOBS=32` rc=0；`make check-inst` rc=0（44/44）；`make check-arch` rc=0（14/14）；`make check` rc=0（31 s，末行 `repository checks (L1): PASS`）；注入还原后复跑 `check-patch-tree`/`make check` 仍 rc=0
- 主工作树（master，未含本任务补丁）`make check-patch-tree` rc=2：`6 problem(s)` **全部** `check-patch-tree: gem5:`（断言⑥/⑨，只涉本任务 3 个补丁）⇒ 红点确属本任务未合入，非其它组件
- 证据脚本（完成区所指 `run.sh`）默认模式 rc=0，22 PASS / 0 FAIL：heap/mmap/mremap 探针 ×3 sha 一致、fault 探针 rc=134、3 个代表案例 ×3 一致、`malloc-oom` 落到 `syscall 261`、baseline 六断言全 0/subset、两门控 rc=0
- 基线全量重跑（`GEM5-021t` 驱动、双引擎 fresh；reviewer 用原始 per-case JSON **自行重算**，非采信聚合器）：`qemu_pass=587 gem5_pass=361 both_pass=361 blocked=217 qemu_only_fail=0 gem5_only_fail=10`；`--aggregate-only` rc=0 同值；gaps 合计 217（80/66/29/22/7/6/4/1/1/1）、**heap/VMA 桶与含 brk/mmap 号的 blocked 均 0**；`gem5_only_fail` 10 条 = 9 math + `Olden/power`（与脚本 `known` 集合逐条相同）；`GEM5-021t` refs 现场重算 310/270/brk114/mmap21 ⇒ 310→361、270→217 属实
- 反例（reviewer 自写注入，`cp`+`md5sum -c`，全程未用 git 还原）：15 PASS；注入后 heap 探针与 `functional/env` 均 rc=1 且含注入串，还原后 stdout sha 与注入前逐字节一致（heap `8578fc5f…`、env `e3b0c442…`）
- 独立边界用例（reviewer 自写，期望值取宿主 Linux 6.8 实测 + `contract-syscall §5`）：**46 PASS / 0 FAIL，rc=0** —— brk 16 条：查询、越界/低于映像回旧 brk 且不回 `-ENOMEM`、非对齐跨页返回请求值、映像 marker 不被吞、精确 8 GiB 接受更高回旧、堆吃满窗口后 mmap=`ENOMEM`；mmap `EINVAL×5`+`ENOMEM×3`+`EBADF×2`+`EEXIST`+`ENODEV`；munmap `EINVAL×2`、mprotect `EINVAL×2`+`len=0→0`；mremap `EINVAL×3`+`ENOMEM`+`EFAULT`+原地收缩与 MAYMOVE 保数据，均与 Linux 实测一致

**阻断（返工指名）**：`mremap(MREMAP_MAYMOVE|MREMAP_FIXED)` 目标与旧区间重叠（宿主 Linux 实测 `EINVAL`）时 —— 目标区严格大于 `old_size` ⇒ 宿主断言 `src/sim/mem_state.cc:182: Assertion 'isUnmapped(start_addr, length)' failed`、rc=134（连跑 2 次一致）；等于 `old_size` ⇒ 返回成功但旧区间被拆除、随后访问即 fault（数据丢失）。589 例语料不触发（各套件 `reason` 含 `Assertion` 者为 0）⇒ 计数不受影响；但 README/changelog 已声明 `MREMAP_FIXED` 能力、§5 以 Linux 为 oracle、且证据脚本对该分支无可达 FAIL，属「代码行为/语义」阻断面。**返工**：`doMremap` 对重叠返回 `-EINVAL`（或按现场口径另定并在 README 披露）+ 证据脚本补该断言（须含 注入→FAIL→还原→回绿）+ 复跑 `run.sh` 与门控 rc=0 + 完成区同步；改动仅限该分支时计数应不变，不需全量重跑。

**非阻断 findings（architect 定夺，可随返工一并处理）**
- F1 非页对齐**非 FIXED** hint：Linux 成功并取整（宿主实测），SE 回 `-EINVAL`（更严）；F2 未打开但落在 `FDArray[1024)` 内的 fd（如 3）回 `-ENODEV`、Linux 回 `-EBADF`（`fd<0`/`≥1024` 已正确回 EBADF）
- F2b `mprotect` 无按页权限已在 README/changelog/遗留三处如实披露 ✓；**不可信用例面**：589 例中无任何用例断言「写只读/`PROT_NONE` 页应 fault」（libc-test 仅 `api/sys_mman` 取 `mprotect` 函数地址；`vmfill/memfill` 只用 `mmap(PROT_NONE)` 占地址、从不触页）⇒ 当前**无假绿**；含该断言的未来用例（含 signals 组）在权限模型落地前不可信（reviewer 实测写 `PROT_READ` 页成功，已记 OBS）
- F3 任务书含运行期路径（完成区 `run.sh` 全路径、审阅记录 `work/log` 引用）违反「任务书不写运行期路径」
- F4 完成区 `(int)((0.7-0.65)/0.01)` 真值写作 `4.9999999999999996`，与其所引 hex `0x1.3fffffffffff8p+2`（复算 `4.999999999999993`）不符；且「hex 证据见审阅记录」在审阅记录中并不存在（悬空引用）
- F5 reviewer 侧还原后二进制 md5 为 `03da8c10…`（记录值 `4c6b1b97…`，注入前快照实测确为该值）：`cmp` 仅 24 字节差 = `base/date.cc` 重编嵌入 `__TIME__` 的 4 字节 + `.note.gnu.build-id` 20 字节 ⇒ **二进制 md5 不是可复原的回绿判据**，回绿请以 stdout sha + 门控为准
- F6 `run.sh` 小瑕疵：corpus stdout 全空（sha 恒为 `e3b0c442…`）⇒「×3 identical」恒真；探针 run2/run3 的 rc 未判（rc=0 主判据仍有效）

**约束核验**：改动 7 文件与完成区「修改文件」逐条一致、未动 `tests/**` ✓；完成区 12 行 ≤30 ✓、状态 `待验收` ✓；reviewer 改前/改后快照对账：`git status` 7 行不变、7 文件 md5 与 gem5 源树 3 文件 md5 全等、未提交 ✓；验收标准 1/2/3/4/5 以 reviewer 亲跑为准全部通过，标准 6 的 `mremap FIXED` 能力声明不成立 ⇒ **Needs Revision**。

### 审阅记录 → 第 2 轮 engineer 自审（reviewer Needs Revision 返工）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R1（阻断）`mremap(MAYMOVE\|FIXED)` 目标与旧区间重叠：> old_size 触发 `mem_state.cc` 断言 rc=134；= old_size 返回成功但旧区间被拆/数据丢失 | ✅已修 | `doMremap` 固定分支新增区间相交判定（同起址/包含/被包含）⇒ `-EINVAL`，旧映射不动 | 探针新增 4 条重叠断言（含 same-start shrink）+ 旧映射仍可读；`INJECT=1` 注入 `if (false && …)` ⇒ 探针 FAIL，还原重建回绿 |
| R2（F1）非 FIXED 的非对齐 hint 回 `EINVAL`，Linux 为取整成功 | ✅已修 | 非 FIXED 分支 `hint &= ~(page-1)`；FIXED 仍 `EINVAL` | mmap 探针新增「非对齐 hint 成功且页对齐」断言 |
| R3（F2）未打开但落在 `FDArray[1024)` 的 fd 回 `ENODEV`（Linux `EBADF`） | ✅已修 | 未打开 fd ⇒ `EBADF`，已开但不可映射 ⇒ `ENODEV` | mmap 探针新增 fd=1023 ⇒ `EBADF` 断言 |
| R4（F2b）`mprotect` 不建权限模型需写明不可信用例 | ✅已修 | 完成区遗留 ② 明确「写只读/PROT_NONE 页应 fault」不可信；当前 589 例无此类 oracle | 无假绿（基线对照 JSON） |
| R5（F4）4.9999999999999996 与 hex 不符 + 证据悬空 | ✅已修 | 改为 5 − 2⁻⁴⁷ = 4.999999999999993，并给出 trace `CAST_R` 行与 `iR` 值 | 一次性复算核对（截断 4 / 舍入 5） |
| R6（F5）回绿判据用二进制 md5 | ✅已修 | 判据改「源文件 md5 + 探针 rc/stdout + 门控」；二进制 md5 仅标识 | `INJECT=1` 输出逐项显示 source md5 + 两探针回绿 |
| R7（F6）corpus stdout 全空致「×3 identical」恒真；探针 run2/run3 rc 未判 | ✅已修 | 探针判 `rc=0×3 + stdout 相同`；libc 自检案例判 `rc=0×3`；新增 `llvm-hello` 非空 stdout ×3 | 证据输出显示 `rc=0/0/0` 与 `bytes=13` |
| R8（F3）任务书运行期路径 | ✅已修 | 删除具体运行期路径，只留「本任务证据目录 `run.sh`」与通用日志区描述 | 全文检索无具体运行期路径 |

判决：阻断项与全部非阻断项已修，状态保持 `待验收`（复跑 rc 见上）。

### 审阅记录 → 第 2 轮 reviewer 验收

**判决：Accepted**（阻断项经 reviewer 独立注入复现并确认已修；验收标准 1–6 与全部门控以 reviewer 亲跑为准通过）

**重跑与独立核验（真实输出/退出码）**
1. **我自写四类重叠边界用例**（同起址 4p→8p / shrink 4p→2p dest=old+1p / inside 4p→1p dest=old+2p / containing 4p→8p dest=old-4p）+ 非重叠 FIXED + F1/F2：**21 PASS / 0 FAIL、rc=0，连跑 2 次 stdout sha 同为 `9df8a89c…`** —— 四类全部 `EINVAL(22)` 且旧映射**逐字节不变、仍可写**；非重叠 FIXED 落在目标地址且 2 页数据完整
2. **宿主 Linux 6.8 同批 case 实测**：四类重叠全 `EINVAL(22)`、非重叠 FIXED 成功保数据；F1a 非对齐非 FIXED hint 成功且页对齐（`0x10001→0x10000`）、F1b hint 落已占页仍成功另址、FIXED 非对齐 `EINVAL`；F2a 关闭 `fd=3` `EBADF(9)`、F2b 已开 pipe `ENODEV(19)`、F2c `fd=1000000` `EBADF(9)` ⇒ **与 DADAO 侧逐条一致**（唯一差异是 SE 布局：`< 映像末` 的 hint 回退到窗口顶部，语义同为「成功 + 取整」）
3. **独立注入（非 engineer 的 `false &&`）**：把相交判定改成只判同起址 ⇒ 我的用例出现 `FAIL mremap FIXED overlap EINVAL … [shrink 4p→2p …]`、**rc=134**；`cp` + `md5sum -c` 还原（源 md5 复原 `11496090…`）、重建 rc=0 ⇒ 回绿 **rc=0 / 0 FAIL / sha 与注入前相同**；脚本 **11/11 PASS、rc=0**
4. **基线全量重跑（双引擎 fresh）+ reviewer 按原始 per-case JSON 自算**：`qemu_pass=587 gem5_pass=361 both_pass=361 blocked=217 qemu_only_fail=0 gem5_only_fail=10`；gaps 合计 217（80/66/29/22/7/6/4/1/1/1）、**heap/VMA 桶 0**、`gem5_only_fail` 仍为 9 math + `Olden/power` ⇒ 与完成区逐项一致
5. **证据脚本**：默认 **rc=0（20 PASS/0 FAIL**：探针 `rc=0×3`、`llvm-hello` 非空 stdout 13B×3、corpus `rc=0×3`、baseline 六断言、两门控**）**；`INJECT=1` **rc=0（12 PASS/0 FAIL**：brk 分支 blocked、重叠判定注入 ⇒ 探针 rc=1 FAIL、还原后两探针 sha 复原**）**
6. **门控**：`check-patch-tree` rc=0（305 patches）、`check-source-state` rc=0（gem5 `2f951846c50d` count=1 clean=True）、`build-gem5` rc=0、`check-inst` rc=0（44/44）、`check-arch` rc=0（14/14）、`make check` rc=0（`repository checks (L1): PASS`）
7. **披露落实**：F2b 已写入完成区遗留②（不可信用例面明示、并注明当前 589 例无此类 oracle）✓；F4 `5 − 2⁻⁴⁷ = 4.999999999999993` 我复算一致，hex 链 `0x1.999999999999p-5 / 0x1.47ae147ae147bp-7 = 0x1.3fffffffffff8p+2` 在证据 trace 中实存 ✓；F5 回绿判据已改「源 md5 + 探针 rc/stdout + 门控」（二进制 md5 仅标识，我侧 `ee6eb41b`→`d766c1b5` 属 `__TIME__`/build-id，按该口径处理）✓；F6 探针 `rc=0×3 + stdout 相同`、新增 `llvm-hello` 非空案例 ✓；F3 全文检索运行期路径（工作区临时目录、家目录、宿主绝对路径、证据/日志工作区路径）**均为空** ✓
8. **快照对账**：改前/改后 `git status` 同为 7 文件（与完成区「修改文件」一致）、7 份交付文件与 gem5 源树 3 文件 md5 前后全等、无未跟踪残留、reviewer 全程未提交 ✓（本轮我只新增本段）

**遗留（不阻断，architect 收尾可处置）**：R-a `CAST_R` trace 只在运行期目录，任务书仅写「可复算」——数字本身已复算一致，任务收尾清理前如需留证请落非易失位置；R-b 非对齐非 FIXED hint 落在 `< 映像末` 时 DADAO 回退到窗口顶部（Linux 可用低址）——SE 地址空间口径使然，README 已声明该布局，语义同为成功取整。

#### 收尾（architect，2026-11-06）

- 第 1 轮阻断（`mremap(MAYMOVE|FIXED)` 重叠）已修：四类重叠边界 ⇒ `-EINVAL`、旧映射可读；reviewer 独立注入可达 FAIL 并回绿。
- 非阻断 F1/F2 已与宿主对齐（非对齐 hint 取整、`EBADF`/`ENODEV`）；F2b `mprotect` 不可信面已披露；F4/F5/F6 已落实。
- 遗留：R-a `CAST_R` trace 仅在运行期目录（数字已复算）；R-b 非对齐 hint 落映像末以下的地址回退差异（README 已声明 SE 布局）。
- 基线：gem5 pass 310→361、blocked 270→217，heap/VMA（brk/mmap/munmap/mremap）阻塞清零；`qemu_only_fail` 0。
- 判决 Accepted（第 2 轮），状态置 `已验证`。
