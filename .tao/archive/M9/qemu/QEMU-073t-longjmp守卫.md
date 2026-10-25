# QEMU-073t: `cpu_loop_exit` 的 longjmp 泄漏 MMIO 重入守卫（`ISS-064`）

**模块**：qemu
**项目里程碑**：M9（收尾前）
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地

## 立项来源 / 现象（`ISS-064` 原文，执行前现场复核）

`cpu_loop_exit` 走 `longjmp` 跳出时，**MMIO 重入守卫 `engaged_in_io` 未复位**；
下一次进入 MMIO 路径时守卫仍为"忙" ⇒ 后续访问被误判为重入（可能直接 abort / 返回错误）。

## 目标

1. 找到 `engaged_in_io` 的置位/复位路径与 `cpu_loop_exit` 的 `longjmp` 落点（`accel/tcg` / `softmmu` / `exec`）。
2. 在**所有** `longjmp` 出口（不止一处）保证守卫被复位；优先用"`sigsetjmp` 返回后统一复位"这类**结构化**修法，而非逐点打补丁。
3. 给出触发路径：能构造一个"MMIO 访问 → 异常/退出 → 再次 MMIO"的用例，证明修复前会误判、修复后正常。

## 验收

1. **复现用例**：构造 1 个最小 guest 程序（或 qemu 内部测试）走"MMIO → `cpu_loop_exit` → 再 MMIO"，贴**修复前失败、修复后通过**的真实输出。
2. `make check`(L1) rc=0；`make check-modules`(L2) rc=0；`check_qemu_trans --strict` 266/266；`check_patch_tree` 绿。
3. **可达 FAIL**：注入"去掉复位" ⇒ 复现用例再次失败。
4. 证据 `.work/evidence/<任务ID>/run.sh`（rc 落盘、禁 `| tee`）。

## 接口规范

- **输入**：`components/qemu/patches/**`（`accel/tcg` / `softmmu` / `include/exec`）。
- **输出**：守卫复位修复 + 复现用例 + 证据。
- **约束**：不改 ISA/spec/contracts；不 commit/push；临时目录 `/tmp/opencode/QEMU-073t/`。

## 完成区

**用户裁定**（2026-10-24，执行前现场复核后）：问「ISS-064 的原始复现载体（exit-port MMIO 设备）已删除，dadao-m1 现在没有任何 MMIO 设备。要满足验收 #1/#3…选哪条路？」→ 答：**「不做复现，只修」**。⇒ 验收 #1（复现用例）、#3（注入去掉复位→复现失败）**按用户裁定豁免**；交付 = 结构化修复 + 门控 + 可达 FAIL 证据脚本。

**测试结果**：证据 `.work/evidence/QEMU-073t/run.sh` **9/9 PASS**（`--inject` 模式；普通模式 6/6）；`make check`(L1) rc=0；`make check-modules`(L2) rc=0（6m35s）；`check_qemu_trans --strict` 266/266；`check_patch_tree` 198 patches OK + `--source-state` 全 OK；`build-qemu` rc=0。
**修改文件**：`.work/source/qemu/{system/memory.c, include/system/memory.h, accel/tcg/cpu-exec-common.c}`；`components/qemu/patches/{system/memory.c.patch, include/system/memory.h.patch, accel/tcg/cpu-exec-common.c.patch}`（新增 3 份）、`components/qemu/series`、`components/qemu/changelog.md`、`.work/evidence/QEMU-073t/{run.sh,check_wiring.py,guest_smoke.py}`、本册。
**验收结果**：
- 落点：`cpu-exec-common.c::cpu_loop_exit()` → `mem_reentrancy_guard_abort()`（**全树唯一** `siglongjmp(cpu->jmp_env)`，天然覆盖 `cpu_exec_setjmp` 与 `cpu_exec_step_atomic` 两个 `sigsetjmp` 落点）；`system/memory.c` 线程级栈上节点链（engage 压入 / 正常路径弹出）+ abort 整链复位。
- 现场（与 ISS-064 原描述不符）：`dadao_cpu_tlb_fill` 只映射 RAM/ROM，非 RAM/ROM 一律 UNMAPPED(0x87) ⇒ **MMIO 无任何可达路径**（比"无设备"更强）；exit-port 载体已随 ADR-0020 D8 删除。
- 本地临时实验（测试 MMIO 设备 + tlb_fill 放行；**未入交付物**，`cp`+md5 还原）：修复前 `rc=2` + `qemu-system-dadao: warning: Blocked re-entrant IO on MemoryRegion: dadao-testio at addr: 0x0`；修复后 `rc=0`、stderr 空。
- 还原对账：`dadao-machine.c b67d6cb3…`、`helper.c 23b785b9…`、`cpu-exec-common.c 0697565d…` 与备份一致；`git -C .work/source/qemu status --porcelain` 空。
**新发现/坑**：① 复位必须在 longjmp **之前**（`cpu_loop_exit`）——`sigsetjmp` 落点处节点栈帧已失效，遍历会读悬空栈；② 守卫链出栈用链查找而非 `g_assert`，避免协程交错致 emulator abort；复位仅覆盖**同线程**（MMIO 回调在 vCPU 线程、BQL 串行；跨线程 longjmp 不在语义内）；③ 将来引入 MMIO 设备须同时扩 `dadao_cpu_tlb_fill`，届时复验 ISS-064 可达性；④ 本修法让"所有 longjmp 出口"由唯一产生点覆盖，优于逐落点打补丁。
**遗留问题**：ISS-064 可达性复验随「引入 MMIO 设备（含 tlb_fill 扩展）」任务进行；不改 ISA/spec/contracts。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 复位点与任务书字面「sigsetjmp 返回处」不同 | ✅已修（按更优等价结构） | 复位放 `cpu_loop_exit`（唯一 `siglongjmp(cpu->jmp_env)`），覆盖两个落点；理由：落点处链节点栈帧已失效 | `grep -rn "siglongjmp(cpu->jmp_env" .work/source/qemu` 仅 cpu-exec-common.c；wiring 检查 `call=2563 < siglongjmp=2604` |
| F2 守卫出栈用 `g_assert` 会在协程交错时 abort | ✅已修 | `mem_reentrancy_guard_release()` 改为沿链查找并摘除，不 abort | `run.sh` 9/9 PASS；`check_wiring.py` 8/8 |
| F3 `__thread` 链的协程/TLS 假设未声明 | ✅已修 | `system/memory.c` 注释写明"同步访问帧 LIFO；交错时按链查找仍安全" | 同 F2 |
| F4 证据脚本 `printf '--- …'` 被 printf 当选项 | ✅已修 | 改为 `printf '=== … ==='` | `run.sh` 输出无 printf 报错 |
| F5 验收 #1/#3 无法满足 | ✅已处置 | 用户裁定「不做复现，只修」原话落盘完成区 | 本册「用户裁定」段 |
| F6 user-mode 变体未单独验证 | ❌不修（已覆盖） | `dadao-softmmu` + `dadao-linux-user` 同树构建；`#if !defined(CONFIG_USER_ONLY)` 两侧均编译 | `build-qemu` rc=0 |

### 第 1 轮 reviewer 验收

**重跑记录（reviewer 本人执行，rc 均为实测）**
- `./.work/evidence/QEMU-073t/run.sh --inject` → `EXIT=0`，`== result: 9/9 PASS ==`（build-qemu/wiring 8 8/check-patch-tree 198 patches OK/`--source-state` 5 组件 clean=`True`/`check_qemu_trans --strict` 266 266/guest-smoke `(0,'')`/注入→wiring rc=1→还原 md5 0697565d… 一致→回绿 8 8）。
- `make check`(L1) `L1_RC=0`；`make check-modules`(L2) `L2_RC=0`（`module checks (L2): PASS`）；`components/qemu/series` 63 行。
- **独立注入①**：`sed` 去掉 `cpu-exec-common.c` 的 `mem_reentrancy_guard_abort();` → `check_wiring.py` 5/8 PASS、rc=1 → `cp`+md5（0697565d…）还原 → 8/8、rc=0。
- **独立注入②（改前基线对比）**：`patch -R` 反打 3 份补丁（源树回修复前）→ `build-qemu` rc=0 → `guest_smoke.py` `(0,'')`；还原后同一程序同为 `(0,'')` ⇒ 正常 MMIO-less 路径行为不变（静态核对：正常路径仅增链压入/摘除，`engaged_in_io` 置/清点与顺序未变）。
- **快照对账**：审前/审后 `git status --porcelain -uall` 均为空且逐行一致；`.work/source/qemu` 空树；3 文件 md5 与备份一致。

**修法核验**：全树 `siglongjmp` 共 30 处，`siglongjmp(cpu->jmp_env` 仅 `accel/tcg/cpu-exec-common.c:86`（`jmp_env` 全树仅该 2 处 `sigsetjmp` 落点 + cpu.h 声明）；`cpu_loop_exit_noexc/_restore/_atomic` 均汇入 `cpu_loop_exit`，`cpu_abort` 走 `abort()` 不 longjmp ⇒ 唯一出口覆盖成立。复位在 longjmp **之前**、`node` 为栈上有效帧，无悬空读；`abort` 置空链头后，延迟 release 只做指针比较不解引用，无 UAF。用户裁定「不做复现，只修」（2026-10-24）已落盘完成区，与 commit 一致。

**非阻断备注**：同线程协程交错时 `abort` 会顺带清掉挂起协程的守卫（保护窗口短暂变弱，无悬空/无崩溃）；随「引入 MMIO 设备」任务复验 ISS-064。

**判决：Accepted**（阻断项逐条：无出口遗漏 / 无生命周期错误 / 补丁树绿 / L1+L2+266/266 绿 / 注入可红）。

