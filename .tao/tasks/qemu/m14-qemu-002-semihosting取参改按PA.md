# m14-qemu-002: semihosting 取参/取串改按 PA（`ISS-450`）

**模块**：qemu
**项目里程碑**：M14
**依赖**：`spec/Machine-v5 §5.2`（2026-11-15 已定「指针一律为 PA、不经页表翻译」）、`contract-semihosting §2`（0.7.2，同口径）；`m14-qemu-001`（Vast 最小 smon，PTW 已开）；`m14-linux-003`（内核 semihosting 早控制台，按 PA 调用）
**可并行分片**：否（qemu 组件单写者）
**预估**：2–3 h（含 QEMU 重建 + 安装根刷新 + 4 路注入）
**档位**：大改（触及上游共享 semihosting 层 + 需重建 + 门控加严；复核 ≥4 路注入 + 独立重跑）
**状态**：已验证

## 背景（`ISS-450`）

用户 2026-11-15 裁定「semihosting 参数指针 = PA」，已写入 `spec/Machine-v5 §5.2` 与 `contract-semihosting §2`：「参数块指针与 `SYS_WRITEC`/`SYS_WRITE0` 的指针**都是物理地址**，**不经页表翻译**」。

但 QEMU 现状与之一致性不足：

- `SYS_WRITEC` / `SYS_EXIT` 取参走 `translate_for_debug`（identity，仅 `[0, 2 GiB)`∪ROM∪SRAM）；
- **`SYS_WRITE0` 先 `target_strlen`、再经 `semihost_sys_write_gf` → uaccess（`probe_access_flags`）走页表**；`SYS_WRITE`/`SYS_READ` 的缓冲区同样走 uaccess；
- 开 PTW 后 identity 窗口与页表窗口不相交 ⇒ **同一指针无法同时满足两条路径**；传 PA 时 `SYS_WRITE0` 取串失败（`EFAULT`）。
- `translate_for_debug` 注释仍写「DADAO has no MMU」（Vast + PTW 下已过时）。

M14 K1 自决「传 PA + 只用 `SYS_WRITEC`」绕过了该缺陷，但规范既定 PA，实现必须跟上（否则 K2/K3 后的控制台与文件类服务都会踩）。

## 目标

1. **取参/取串/读写缓冲一律按 PA**：dadao（system 模式）下 semihosting 对 guest 内存的访问**不得经页表翻译**；覆盖 `SYS_WRITEC`、`SYS_WRITE0`、`SYS_WRITE`、`SYS_READ`、`SYS_GET_CMDLINE`、`SYS_TMPNAM` 等所有带指针的服务。
2. **不改变其它 target 行为**：共享层（`semihosting/**`）的默认路径对其它架构逐字节不变；dadao 侧改动只经**本 target 的钩子/分支**生效。
3. **注释订正**：`translate_for_debug` 的「DADAO has no MMU」改为符合 Vast + PTW 现状的表述（说明 identity 窗口用途与 PTW 关系）。
4. **加门控（先红后绿）**：在 K1 门控里新增一条 **Vast + PTW 开启**下的 semihosting 断言：字符（`SYS_WRITEC`）与字符串（`SYS_WRITE0`）都能从**未映射 VA 对应的 PA** 正确取出并输出（取串成功即可证明不经页表）。

## 验收（逐条贴真实 rc 与输出）

1. **先红后绿**：在**未修复**的基线上，新断言 **FAIL**（贴真实红色输出：`SYS_WRITE0` 取串失败/输出为空）；修复后 **PASS**。
2. `make build-qemu` rc=0（必要时 `build-qemu-reconfig`），**`make install-host`** rc=0（组件改动后必须刷新安装根，否则门控读到旧二进制）；贴 `qemu-system-dadao` 改前/改后 md5。
3. 门控全绿：`check-linux-k0`、`check-linux-k1`、`check-qemu-forms`、`make linux-semihosting-smoke`、L1 `make check` 均 rc=0；**Tiny 路径行为不变**（贴 smoke 输出与退出码）。
4. **≥4 路可达 FAIL 注入**（`cp` 备份 + md5 还原 + 重建）：① 把 PA 助手改成走页表（回到 bug 状态）⇒ 新断言红；② 只修 `SYS_WRITE0` 不修 `SYS_WRITEC`（或反之）⇒ 另一条断言红；③ 让 PA 助手用错宽度（如按 4 字节读串）⇒ 输出字节不符 ⇒ 红；④ 让 `SYS_WRITE0` 返回长度错（+1）⇒ 输出多一字节 ⇒ 红。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只动 `components/qemu/**`（补丁 + `series`）与 qemu 组件源树（运行期检出）、`tools/linux/`（门控断言）；
- **不改** `spec/`、`contracts/`（口径已定，本次是实现对齐）；不改 `tests/`（除门控所需的既有探针复用）；
- 一文件一补丁（`docs/Process-01`）；`make apply-series` / `check-source-state` / `check-patch-tree` 必须 rc=0；
- **共享层最小化**：若必须改 `semihosting/**`，改动只允许是"加 target 钩子"，不得改共享层对其它 target 的语义；在完成区说明为何无法只在 `target/dadao/` 内完成；
- 构建与跑批不得同时；`JOBS=32`；不提交 git；注入还原用 `cp`+md5（禁 `git checkout/restore`）。

## 审阅记录

### 第 1 轮 engineer 自审

**判决**：可交付（5 条 finding 全部处置完毕，无未修项）。

**改动落点与理由（PA 助手所在层）**：助手放 **target 层**（`target/dadao/common-semi-target.c`），共享层只加**一个 target 钩子** `common_semi_strlen()`——弱默认仍是原来的 `uaccess_strlen_user`（MMU 走法），dadao 用强定义在链接期覆盖。无法只在 `target/` 内完成的原因：长度探测的调用点在共享层（`semihosting/arm-compat-semi.c` 的 `SYS_WRITE0`、`semihosting/syscalls.c` 的 `validate_strlen`），必须有个可覆盖的出口。`SYS_WRITEC` 与全部缓冲类服务（`SYS_WRITE`/`SYS_READ`/`SYS_GET_CMDLINE`/`SYS_TMPNAM`/路径类）本来就走 `lock_user`/`get_user_*` → `cpu_memory_rw_debug` → `dadao_cpu_translate_for_debug`（identity = PA，**不经页表**），故**无需改动**；这条路径由 K14 的 `SYS_WRITEC` 断言现场证成（它的取字正是经 `lock_user`）。唯一走页表的是 `target_strlen` → `probe_access_flags`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 共享层 `common-semi.h` 新增 `#include "exec/vaddr.h"`（钩子参数用 `vaddr`）会影响其它 target 的编译，而本仓库 target-list 只有 dadao | ✅已修（保留并按依赖安全性论证） | 该头是纯 typedef、自带 guard、无 CONFIG 分支；首次不带头时 `syscalls.c` 编译失败（`unknown type name 'vaddr'`）已复现，加头后 softmmu + linux-user 两个目标均编译并链接通过 | `make build-qemu` rc=0（含 `qemu-dadao` 用户态链接） |
| F2 弱符号默认在静态库中能否被 target 强定义覆盖（若不能，改动等于无效） | ✅已修（以注入 ① 反证） | 注入 ① 把 dadao 强定义改名 ⇒ 实际回落到弱默认（MMU 走法）⇒ K14 变红 | 一键脚本 `inject:pa-via-page-table` 各项 PASS |
| F3 串长助手的边界：256 B 分块读越界、无 NUL、超长串 | ✅已修 | 块读失败回落逐字节（真 fault 仍 `-1`）；`INT32_MAX` 上限保护；无 NUL 继续下一块 | 探针串落在页边界前仍取到全串（console 与 oracle 一致） |
| F4 注入还原若 `cp -p`（保旧 mtime）会让 ninja 跳过重编，安装根仍是注入版 ⇒ 假红/假回绿 | ✅已修 | 首轮注入确实踩到（4 路「还原后回绿」全 FAIL）；脚本改 `cp`（新 mtime）+ 断言「重编该目标文件」+「K14 回绿」 | 重跑 51/51 PASS；`还原后重建重编了 …` 各项 PASS |
| F6 selfcheck 汇总分母少算 1（`len(TEXT_MUTATIONS)+5` = 13，实际翻转 14 组）——计数口径错会让「组数」失真 | ✅已修 | 改为 `len(TEXT_MUTATIONS)+4+2`（K5/K2/K3/K4 + K14 两路） | `--selfcheck` 现报 `PASS (14/14 组可翻转)`，15 条 PASS（1 基准 + 14 翻转） |
| F5 注入 ②「只修 WRITE0 不修 WRITEC」无法照字面复现（基线 WRITEC 本就非页表路径，不会红） | ✅已修（等价注入 + 披露） | 注入 ② 改为「WRITEC 仍走页表探测、WRITE0 已走 PA 助手」——即「WRITEC 侧未修」的状态；两路断言互不牵连已现场证明 | `inject:writec-via-page-table`：WRITEC 红、`另一条断言仍绿（SYS_WRITE0…）` PASS |

**越界与残留**：仅 `components/qemu/**` + `tools/linux/**` + 本任务书；`spec/`、`contracts/`、`.tao/contracts/`、`tests/` 0 改动。自查中曾用 `git apply --directory=.` 误把组件补丁打进了工作仓库根（49 个未跟踪文件），已就地删除并 `git status` 复核干净（记入新发现）。

### 第 1 轮 reviewer 验收

**判决：Needs Revision**——阻断点：`SYS_OPEN` 取路径仍走页表，完成区关键断言「**路径类**…本就经 `lock_user`/`get_user_*` → `cpu_memory_rw_debug`」不成立，任务目标 1「semihosting 对 guest 内存的访问不得经页表翻译…所有带指针的服务」未达成（该缺口未在「新发现/坑」披露，已披露的只有 `SYS_READC`）。

**重跑（我本人执行，退出码附后）**：`make check-linux-k0` → 119/119 rc=0；`make check-linux-k1` → **107/107 rc=0**（其中 `[PASS] K14`=5、`[FAIL]`=0 ⇒ 原 102 条全绿）；`make check-qemu-forms` rc=0；`make linux-semihosting-smoke` rc=0（1136 B，sha 全等）；证据脚本（运行期证据目录 `run.sh`） **第 1 次 51 项 2 失败**——根因是我把 reviewer 日志 `rev-*.log` 写进运行期日志目录 撞 `check-run-artifacts` A3 命名规则（5 条点名全是我的文件），属**审查侧干扰**，移出后**第 2 次 51/51 PASS rc=0**（重试 1 次，已记录）；`check_k1.py --selfcheck` rc=0 **14/14 组可翻转**；`check-source-state` rc=0（qemu clean）；`check-patch-tree` rc=2，**8 problem 全 chipyard**、qemu 69 份 0 problem；`apply_series.py --component qemu` rc=0（already applied）。全量 `apply-series` **未跑**（会写并发写者 `m16-chipyard-002` 的组件树），采信旁证：qemu 单组件 rc=0 + 上述 8 项全 chipyard。

**先红后绿（独立复现）**：改名去掉 `common_semi_strlen` 强定义 → `build-qemu`/`install-host` rc=0 → `k14_probe.py` **rc=1、K14 红 ≥2 条（`SYS_WRITE0` 缺串）**；`cp` 还原（源 md5 `25aad4c3…` 复原）→ 重建 rc=0 → **rc=0、5/5 回绿**（qemu 侧还原以行为判，不用二进制 md5）。

**自设计注入 4 路（`cp`+md5 源还原 + 重建，脚本 51/51 PASS rc=0，均红→还原→回绿）**：① 强定义恒返 0 → 红在 `SYS_WRITE0`；② 串长 +1 → 红在「控制台字节」；③ 按 2 字节步进扫（payload 7 字节奇数）→ 红在「控制台字节」；④ `SYS_WRITEC` 读 `args+7`（取错端）→ 红在 `SYS_WRITEC`。

**PA 语义逐路径核对**：`SYS_WRITEC/WRITE/READ/GET_CMDLINE/TMPNAM`、参数块（`GET_ARG`）、`SYS_REMOVE/RENAME/SYSTEM`（显式长度）→ `lock_user`/`get_user_*` → `cpu_memory_rw_debug` → `dadao_cpu_translate_for_debug`（identity=PA，**通过**）；**`SYS_OPEN` 不通过**——`semihosting/arm-compat-semi.c:431 lock_user_string → uaccess_strlen_user → probe_access_flags` 走页表。我自设计探针（同一路径 `":tt"`、同一 PA=`0x100860`、Vast+PTW、探针自检 A/B 通过）：`SYS_OPEN` → console `OPENFAIL`、`SYS_ERRNO=14(EFAULT)`；同一 PA 改走 `SYS_REMOVE` → `errno=2(ENOENT)`（读到）⇒ 差异唯在 `lock_user_string`。另 `SYS_READC/SYS_FLEN` 内部缓冲喂给 identity 的是 `SP-1/-64`（VA），完成区只披露了 READC。

**共享层最小化**：`git diff c3d48b7` 对 `common-semi.h`/`arm-compat-semi.c`/`syscalls.c` 仅 `+include exec/vaddr.h`、`+弱默认钩子`、`SYS_WRITE0` 与 `validate_strlen(tlen==0)` 改调钩子（弱默认 == 原 `target_strlen`，`validate_strlen` 其余分支未动）⇒ **通过**；`target/dadao` 强定义覆盖经注入①/独立红反证有效。

**K14 判别力**：探针自检 `0xE1`（PA 当 VA 的 PTE≠0 ⇒ 前提不成立）/`0xE2`（VA 未映射）先于任何 I/O，失败即 `rc≠0` ⇒ 红；oracle 由探针 `.ascii` 推导（恰 2 个 payload），不读 QEMU 输出；5 条断言覆盖 WRITE0/WRITEC/逐字节全等/guest rc。

**越界**：`git diff 7880a101..b3ea33a3` 共 10 文件，全在 `components/qemu/**`+`tools/linux/**`+本任务书，范围外 **0**；工作树与 qemu 源树均 `git status` 干净，交付物 md5 与开工快照逐项全等（`check_k1.py` `267f535d…`、`semihost_pa_probe.S` `34493440…`、`.lds` `a3f70c62…`、`series` `508c169a…`）。chipyard `.inj-bak`（`GewuFile.scala`/`WumingParams.scala`，mtime 11-15 22:46/23:17）**非本任务**：本任务 diff 与 `.work/evidence/m14-qemu-002/*` 中 `chipyard` 引用 **0**，且属 `m16-chipyard-002`。

**ISS-451「qemu 非位可复现」不成立**：同源码 `touch` 重编 2 次 + 还原后重编 1 次，安装根 md5 **三次全等 `72bc2b04…`**；追加注释（源树变脏）两次均 `4091db00…`——差异来自 `scripts/qemu-version.sh` 的 `git describe --dirty`，非链接不确定。⇒ 完成区②应改为「同源码重编 md5 稳定，可作还原证据」。
**返工要求**：① `SYS_OPEN` 的 `lock_user_string` 改走 `common_semi_strlen` + `lock_user`（user 模式行为等价），并在 K14 增一条 `SYS_OPEN` 断言（先红后绿）；② 修正完成区「路径类」断言与 `include/semihosting/common-semi.h` 注释（其称钩子测 `SYS_OPEN` 的无长度路径，实际 `SYS_OPEN` 不经该钩子）；③ `SYS_FLEN` 的 `SP-64` 与 `ISS-451` 措辞一并披露/订正。
### 第 2 轮 engineer 自审（返工，对应第 1 轮 reviewer Needs Revision）

**判决**：可交付（3 条「必须修」+ `ISS-451` 订正全部处置，无未修项）。

| finding（来源） | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1 `SYS_OPEN` 的无长度文件名仍走页表（reviewer 阻断项） | ✅已修 | `semihosting/arm-compat-semi.c` 的 `SYS_OPEN`：`lock_user_string(arg0)` → `common_semi_strlen(cs, arg0)` + `lock_user(VERIFY_READ, arg0, len+1, 1)`（用户态 `lock_user_string` 的系统态等价式）；共享层其它路径未动 | 基线B `K14 SYS_OPEN … 期望=True 实际=False`、console `b'W0PAOK\nXYZ-'` → 修复后 `b'W0PAOK\nXYZ+'`、`K14: PASS (6/6)` |
| R2 门控缺 `SYS_OPEN` 断言 | ✅已修 | 探针增 `SYS_OPEN`（块{名指针=PA, mode 0, len 0}，名 `":tt"` 亦在 PA）；成功打 `+`、失败打 `-`（两标记必须不在 payload 内，oracle 现场校验）；`check_k1.py` 增第 4 条断言并改 oracle 为 5 段 `.ascii`（串/字/ok/bad/名），另校验链接后 `sp_path` 字节 == `:tt\0` | `check-linux-k1` 108/108；`--selfcheck` 15/15（K14 三路独立翻转） |
| R3 完成区「路径类本就经 `lock_user`/`get_user_*`」错误断言 + `common-semi.h` 注释与实际不符 | ✅已修 | 完成区改为「仅 `SYS_WRITE0` 取串与 `SYS_OPEN` 无长度名走长度探测（两处均已改走钩子），其余 guest 传入指针走 `lock_user`/`get_user_*`」；`common-semi.h` 钩子说明改为只列 `SYS_WRITE0` 与 `SYS_OPEN` 两处 | 见本任务书完成区；`check-knowledge-refs` 对「完成区」段自检 0 具体 `.work/` 路径 |
| R4 `SYS_FLEN` 内部缓冲 `SP-64` 未披露（与 `SYS_READC` 的 `SP-1` 同族，`ISS-452`） | ✅已修（披露） | 完成区「新发现/坑④」+「遗留问题①」显式登记；本任务不改 | 本任务书完成区 |
| R5 `ISS-451` 判断错误：qemu **并非**「非位可复现」 | ✅已修（订正） | 完成区改为「同源码且源树干净时 md5 稳定（连续两次 build+install 均 `9750c139…`），可作还原证据；源树脏因 `git describe --dirty` 变」；注入脚本增「还原后源树干净 + 二进制 md5 == 基线」两条 | 5 路注入的「还原后 qemu md5 == 基线」均 PASS |

**自审补充（本轮新发现，已修）**：`_elf_file_offset()` 首次实现用了 `p_vaddr - p_offset` 而漏了下标换算（`sp_path` 字节校验误报），改为按 PT_LOAD 的 `p_offset + (addr - p_vaddr)` 取址后通过——该校验存在的意义正是防止「探针符号跑偏后仍假绿」。

### 第 2 轮 reviewer 验收

**判决：Accepted**——第 1 轮阻断项 `SYS_OPEN` 已真修；全量页表路径扫描**无漏项**；余下 4 条均为文档级小错，按「文档级不阻断」记 finding。

**重跑（我本人执行，退出码附后）**：证据脚本 `run.sh`（运行期证据目录）**74/74 PASS rc=0**；`make check-linux-k1` **108/108 rc=0**（K14 六条全 `[PASS]`、`[FAIL]`=0 ⇒ 原 102 条仍绿）、`check-linux-k0` 119/119、`check-qemu-forms` rc=0、`linux-semihosting-smoke` rc=0（1136 B sha 全等）、`check_k1.py --selfcheck` rc=0 **15/15 组可翻转**、`check-knowledge-refs` rc=0；`check-source-state` **qemu OK（clean、base+1）**、整体 rc=2 仅因 chipyard（并发写者）；`check-patch-tree` rc=2、**9 problem 全 chipyard**、qemu 69 份 0 problem。全量 `apply-series` 按约束未跑，采信旁证为「qemu 单组件 rc=0（上轮已验）+ 上述 9 项全 chipyard」。

**`SYS_OPEN` 路径核对（通过）**：`TARGET_SYS_OPEN` 现为 `common_semi_strlen(cs, arg0)` → `lock_user(VERIFY_READ, arg0, name_len+1, 1)`；system 模式 `lock_user` 宏展开为 `uaccess_lock_user` → `cpu_memory_rw_debug(..., is_write=0)` → `dadao_cpu_translate_for_debug`（identity=PA，**不经页表**）；`lock_user_string` 在 `semihosting/` 已**零调用点**（只剩注释与宏定义）。与 `linux-user/uaccess.c:46` 的 `lock_user_string` = `target_strlen` + `lock_user(VERIFY_READ, …, len+1, 1)` **逐参等价**，且每次构建都链接 `qemu-dadao` ⇒ 其它 target 与用户态行为不变（`common_semi_strlen` 弱默认 == 原 `target_strlen`）。

**全量页表路径扫描（无漏项）**：`semihosting/` 内唯一走页表的原语是 `probe_access_flags`，仅由 `uaccess_strlen_user` 调用，其调用方只剩 ① `lock_user_string`（**0 调用点**）② `target_strlen` = `common_semi_strlen` 弱默认（dadao 被强定义覆盖，第 1 轮独立红已反证）③ `syscalls.c` 的 `target_strlen`（`#ifdef CONFIG_USER_ONLY`，任务目标 1 明限 system 模式）。其余 guest 内存访问全是 `lock_user/unlock_user/get_user_*/put_user_*/cpu_memory_rw_debug`（identity=PA）；`gdb_write/read` 走 `gdbstub/system.c` 的 `cpu_memory_rw_debug` 且仅 `use-gdb-abi` 开启时；`address_space_to_flatview` 只枚举 host FlatView 找 RAM 基址、不涉 guest 指针。**遗留仅 `SYS_READC(SP-1)`/`SYS_FLEN(SP-64)` 的地址空间问题（把内核 VA 当 PA，非页表），已披露 `ISS-452`、本任务不修**。

**K14 第 6 条判别力（通过）**：名 `":tt"` 在 `ENTRY_VA+0x980`（PA≈0x100980），与 payload 同一 L1 索引 0；探针自检 `0xE1`（PTE[0]==0 ⇒ PA 当 VA 未映射）/`0xE2`（VA 已映射）先于任何 I/O；oracle = 源文件 5 段 `.ascii` 按序拼接，构建期拒绝断言（payload 数≠5、名 ≠ `":tt"`、标记非单字节或落进 payload、两标记相同、`--defsym` 后符号偏移漂移、`sp_path` 字节 ≠ `":tt"\0`）任一即 `SystemExit`；`+`/`-` 不可能被 payload 污染（`W0PAOK\n`/`XYZ` 不含该字节，且断言要求 `mark_bad not in console`）。

**独立先红后绿（复现完成区基线 B）**：把 `SYS_OPEN` 打回 `lock_user_string` → 重建/安装 → `k14_probe.py` rc=1、**`K14: FAIL (4/6)`、console=`b'W0PAOK\nXYZ-'`**（第 6 条 + 逐字节两条红，WRITE0/WRITEC/EXIT 仍绿），与完成区基线 B 逐字节一致；`cp` 还原（源 md5 `aa2e2c67…` 复原 + 源树 `git status` 空）→ 重建 → **二进制 md5 回 `9750c139…`、K14 6/6 绿**（还原证据 = 源树干净时 md5 相等 + 行为回绿）。

**自设计注入 2 路（均红→还原→回绿，脚本 41/41 PASS rc=0）**：① `lock_user` 指针 `arg0 → arg0+1`（错端：仍复制到名串 ⇒ `strcmp` 必不匹配 ⇒ `EINVAL`）→ **`K14: FAIL (4/6)`、console `…XYZ-`**，`SYS_WRITE0/WRITEC` 两条仍绿；② 测长指针 `arg0 → arg0+0x40000000`（PA 超出 RAM ⇒ identity 取不到 ⇒ `-1` → `do_fault`）→ 同样 4/6 红、另两条绿。**建议的两路我核为恒等变换、判不出**：①「返回 3」——`common_semi_strlen` 对 `":tt"` 的**正确**值就是 3（不含 NUL）；②「改 `VERIFY_WRITE`」——`#define lock_user(type,p,len,copy) uaccess_lock_user(env,p,len,copy)` **丢弃 `type`**，且 `uaccess_lock_user` 硬编码 `cpu_memory_rw_debug(..., 0)`，预处理结果不变 ⇒ 不可达。

**越界与状态**：`git diff 7880a101..HEAD` 共 10 文件，全在 `components/qemu/**` + `tools/linux/**` + 本任务书，范围外 **0**；`spec/`、`contracts/`、`.tao/contracts/`、`tests/`、其它组件 0 改动；qemu 源树 `git status` 空、交付物 md5 与本轮开工快照逐项全等、安装根 `9750c139…`、K14 终态 6/6。**同源码 + 源树干净时二进制 md5 稳定**（本轮 4 次还原全部回 `9750c139…`）⇒ 上轮对 `ISS-451`「非位可复现」的否定成立、完成区订正措辞正确。

**记 finding（均文档级，不阻断 Accepted）**：① `check_k1.py` 第 438 行注释仍写「`SYS_OPEN` 经 `lock_user_string` 取名」，与返工后实现相反；② 完成区「遗留②」列的 `check-knowledge-refs`/`check-temp-dirs` 现均已 PASS——前者因**我**修掉自己第 1 轮记录里 2 处具体运行期路径（改为占位），属审查侧订正，已体现在本工作树；③ `ISS-451`/`ISS-452` 仅在任务书引用、`issues.yaml` 现只登记 `ISS-450` ⇒ 悬空编号，建议 architect 补登或去号。

## 完成区

**结论**：semihosting 对 guest 内存的访问现已**全部**按 PA。页表路径只有两处，均已改走 target 钩子 `common_semi_strlen()`（弱默认 = 原 `target_strlen`/`uaccess_strlen_user`，其它 target 逐字节不变）：① `SYS_WRITE0` 取串；② `SYS_OPEN` 的无长度文件名（原 `lock_user_string` → `uaccess_strlen_user`，现「钩子 + `lock_user`」，等价用户态 `lock_user_string`）。其余**guest 传入**指针（`SYS_WRITEC`/`WRITE`/`READ`/`GET_CMDLINE`/`TMPNAM`、`REMOVE`/`RENAME`/`SYSTEM` 的显式长度、参数块）经 `lock_user`/`get_user_*` → `cpu_memory_rw_debug` → `translate_for_debug`（identity = PA）。上一轮「路径类本就经 `lock_user`」的说法有误（`SYS_OPEN` 是例外），已删。

**先红后绿**（Vast + PTW 开；探针数据全在「PA 当作 VA 时未映射」的 RAM，把 PA 喂给 semihosting）：
- 基线A（未修，md5 `10291d6b…`）：`SYS_WRITE0` FAIL，console=`b'XYZ'`，`K14: FAIL (3/5)`
- 基线B（只修串长、未修 `SYS_OPEN`，md5 `72bc2b04…`）：`[FAIL] K14 SYS_OPEN：无长度文件名的指针经 PA 取出… | 期望=True 实际=False`，console=`b'W0PAOK\nXYZ-'`，其余 4 条 PASS ⇒ `K14: FAIL (4/6)`
- 修复后：console=`b'W0PAOK\nXYZ+'` == oracle，`K14: PASS (6/6)`

**构建/安装**：`make build-qemu` rc=0、`make install-host` rc=0；安装根 md5 改前 `10291d6b5b99d90f443958ed17963e33`、改后 `9750c139f24a7bcebca37909c287b67c`。**同源码且源树干净时 md5 稳定、可作还原证据**（连续两次 build+install 均 `9750c139…`）；源树脏会因 `scripts/qemu-version.sh` 的 `git describe --dirty` 改变二进制（订正上轮「非位可复现」的错误结论，`ISS-451`）。

**门控**：`check-linux-k1` PASS 108/108（K14 6 条）、`check-linux-k0` PASS 119/119、`check-qemu-forms` rc=0、`linux-semihosting-smoke` rc=0（Tiny 控制台 1136 B sha256 与 oracle 全等）、`--selfcheck` PASS 15/15（K14 三路独立翻转）、`check-source-state` 中 qemu OK（clean、base+1）、`check-patch-tree` 中 qemu 69 份 0 problem。

**5 路注入**（`cp`+md5+重建+重装，一键脚本 74/74 PASS）：① PA 助手改回 MMU 默认 ⇒ `SYS_WRITE0` 红；② `SYS_WRITEC` 仍走页表 ⇒ WRITEC 红、WRITE0 绿；③ 串长按 4 字节宽度取 ⇒ console `W0PA` 红；④ `SYS_WRITE0` 长度 +1 ⇒ console 多一 NUL 红；⑤ `SYS_OPEN` 打回 `lock_user_string` ⇒ SYS_OPEN 红、WRITEC 绿。五路均「注入→红→`cp` 还原（源 md5 一致 + 源树干净 + 二进制 md5 回基线）→重编该文件→回绿」。

**修改文件**：`components/qemu/patches/{include/semihosting/common-semi.h,semihosting/arm-compat-semi.c,semihosting/syscalls.c}.patch`（新增）、`components/qemu/patches/target/dadao/{common-semi-target.c,cpu.c}.patch`、`components/qemu/series`、`tools/linux/check_k1.py`、`tools/linux/semihost_pa_probe.{S,lds}`（新增探针）、本任务书。

**证据**：一键脚本 `run.sh`（+`k14_probe.py`/`inject.py`/`inj/*`）在运行期证据目录，落 `run-full.log`（74/74 PASS）；构建/门控日志在运行期日志目录。

**新发现/坑**：① 注入还原**禁 `cp -p`**（旧 mtime ⇒ ninja 跳过重编 ⇒ 假红/假回绿）；② qemu 二进制在**源树干净时可复现**、脏树因 `git describe --dirty` 变（`ISS-451`）；③ `git apply --directory=.` 在仓库根 cwd 下会把组件补丁打进工作仓库；④ `SYS_READC`（`SP-1`）与 `SYS_FLEN`（`SP-64`）把内核 VA（SP）当 PA 喂给 identity 缓冲 —— 同族问题，均登记 `ISS-452`，**本任务不修**（K1 未用）。

**遗留问题**：① `SYS_READC`/`SYS_FLEN` 内部缓冲未 PA 化（`ISS-452`，见新发现④）；② L1 既有红灯均非本任务：`check-spec-drift`（`contract-semihosting.md` 0.7.2 vs `.tao/contracts/README.md` 0.7.1，属 spec 变更流程）、`check-patch-tree`（chipyard，另一写者）、`check-temp-dirs`（`m14-linux-005`/`m14-k2-plan` 他人目录）、`check-knowledge-refs`（命中在本任务书**第 1 轮 reviewer 段落**的两处具体运行期路径，非本任务措辞；建议改写为 `<任务ID>`/`<module>` 占位形式）。
