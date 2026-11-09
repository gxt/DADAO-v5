# QEMU-084t: QEMU user-mode guest rlimit 实现（ISS-343）

**模块**：qemu
**项目里程碑**：M11（P3；2026-11-06 用户裁定插在 M11 终验之前做，见「用户裁定」）
**依赖**：`TESTCASES-099t`（已验证；诊断与最小探针）
**状态**：已验证

## 用户裁定（2026-11-06）

> 「A：M11 终验前做（推荐）」——即 `INTEG-057t` 合并后立刻派本任务，做完再统一跑 L2/L3/夜跑与 M11 `m` 册，终验只跑一遍。

原任务书把它标为「M11 后/P3」是 architect 的归类错误：P3 是优先级，不等于里程碑归属；按 2026-11-05 的 4A「小项现在清」它本就属于本轮。本任务因此纳入 M11 期：改的是 L3/夜跑直接依赖的 QEMU，先改后验可避免「绿报告对应旧二进制」。

## 执行环境
本地；只改 QEMU user-mode 的 guest rlimit 记账，不改 spec。

## 背景

`ISS-343`：QEMU user-mode 对 guest `RLIMIT_AS/DATA/STACK` 是 no-op：

- guest `setrlimit(RLIMIT_DATA,0)` 返回成功
- `getrlimit` 仍返回 `RLIM_INFINITY`
- guest `mmap`/`brk` 不受限
- 与原生 Linux 不一致

`TESTCASES-099t` 最小探针已证明；根因在 `linux-user` 的 `setrlimit/prlimit64` 与 `do_brk()`/`target_mmap()` 未按 guest rlimit 记账。

## 目标

1. 实现 guest `RLIMIT_AS`/`RLIMIT_DATA`/`RLIMIT_STACK` 的记账：
   - guest `mmap`/`brk` 超过限制 ⇒ `ENOMEM`；
   - `getrlimit` 返回 guest 设置值；
   - 不改变 `RLIMIT_NOFILE`/`RLIMIT_CORE` 等既有语义。
2. 用 `TESTCASES-099t` 的最小探针验证：`RLIMIT_DATA=0` 后 RW mmap/brk 失败。
3. 不改变 Node/Tiny 正常路径；跑 QEMU user/system 代表测试。

## 验收标准

1. 最小探针：guest `setrlimit(RLIMIT_DATA,0)` 后 `getrlimit=0`、RW `mmap`/`brk` = `ENOMEM`。
2. 不设置 rlimit 时行为不变；Node/Tiny 测试不退化。
3. `make build-qemu`/`install-host`/`check-source-state`/`check-patch-tree`、L1 rc=0。
4. 反例：恢复 no-op ⇒ 探针 FAIL；还原回绿。
5. 完成区 ≤30 行；状态 `待验收`。

## 范围 / 非范围

**在范围内**：`components/qemu/patches/linux-user/{syscall.c,mmap.c,elfload.c}`（按现场）、`components/qemu/changelog.md`、`tools/qemu/user_mode_smoke.py`（新增 guest rlimit 探针用例，见「探针落点」）、本任务书、`milestones.md`、`ISS-343` 关闭。

**不在范围**：spec/contracts、gem5、tests 期望、其它 QEMU 语义。

## 探针落点

回归探针**入库**，不留在运行期临时目录：加进 `tools/qemu/user_mode_smoke.py`（QEMU 测试驱动，QEMU-081t 先例），沿用其 `compile_program`/`link_static` 与独立 oracle 风格。

探针至少断言：

1. `setrlimit(RLIMIT_DATA, 0)` 成功后 `getrlimit(RLIMIT_DATA)` 的 `rlim_cur == 0`；
2. 该状态下一次 RW `mmap`（一页 64 KiB 以上）返回 `-ENOMEM`；
3. 同位探针在**未设置** rlimit 时 `mmap` 成功（防「一律失败」假绿）；
4. 同上对 `RLIMIT_AS` 各一组。

补充判据须来自独立 oracle（原生 Linux 行为/契约），不读 QEMU 内部日志。

## 已知坑（来自 `TESTCASES-099t` 诊断，避免重复踩）

- musl DADAO 端口的公共 `brk()` 恒返回 `-ENOMEM`（`src/linux/brk.c`），**不能**用它判断 rlimit 记账；
- 公共 `syscall(SYS_brk, …)` 在该端口经 `va_arg` 传参异常（另见诊断记录），探针勿用；
- `mallocng` 走 `__syscall` 不受上述影响，可用 `malloc` 复核；
- 64 KiB 页：探针按页大小 65536 计算，不要写 4096。

## 说明

- 这是 P3 能力缺口；2026-11-06 用户裁定 A 插入 M11 终验之前，故属于 M11 期。
- 若实现需要跨平台通用改动，先做 DADAO target 最小路径，再评估通用化。
- 不把 no-op 写成“已支持”。

## 完成区

**测试结果**：`make build-qemu`/`make install-host` rc=0；`python3 tools/qemu/user_mode_smoke.py` **94/94**（rlimit 断言 **39** 条全 PASS：AS 5 + DATA 9 + 对照 6 + STACK 13 + raw syscall 6）；`check-source-state`/`check-patch-tree`（65 份）/`check-inst`（44/44 + node/tiny）/`check-arch`（16/16 runtime + 14/14 cfx）/`make check`（L1 PASS）全 rc=0。一键证据脚本默认模式 **13 项检查全 PASS**（并逐条打印 39 条 rlimit 断言），`--inject` 两种注入（整段 no-op / 仅 STACK 分支）均 PASS。
**修改文件**：`components/qemu/patches/linux-user/mmap.c.patch`（新增）、`components/qemu/patches/linux-user/user-mmap.h.patch`（新增）、`components/qemu/patches/linux-user/syscall.c.patch`（改）、`components/qemu/series`、`components/qemu/changelog.md`、`tools/qemu/user_mode_smoke.py`、`.tao/knowledge/milestones.md`（状态行）、本任务书。
**验收结果**：guest `RLIMIT_DATA={0,0}`/`RLIMIT_AS=0` 后 `getrlimit` 返回所设值 0，RW 匿名私有 `mmap` ⇒ `-ENOMEM`（errno=12，取自宿主 uapi 头）；`RLIMIT_AS` 恢复 `RLIM_INFINITY` 后同一映射成功；`RLIMIT_DATA={0,inf}` 按内核 cur=0 workaround 放行；`{0,0}` 下只读与 `MAP_SHARED` 写映射仍成功（限得准）。新增 STACK：`setrlimit(RLIMIT_STACK,128 KiB)` ⇒ `getrlimit` 读回 `0x20000`（max 仍 infinity）、`MAP_GROWSDOWN` 256 KiB ⇒ `-ENOMEM`(12)、128 KiB ⇒ 成功、普通 256 KiB 不受影响、恢复 infinity 后 256 KiB 成功；未设限时读回**映射主栈 8 MiB**（非 infinity）。新增 raw：`syscall(SYS_setrlimit/SYS_getrlimit, RLIMIT_DATA)` 往返 `0 → infinity` 正确（musl libc 走 `prlimit64`，故单列）。反例：整段记账改回 no-op ⇒ 6 条 FAIL（AS/DATA/STACK 的 rc+errno）；仅禁用 `MAP_GROWSDOWN` 分支 ⇒ **只**新增的 GROWSDOWN 断言 FAIL（无关联失败）；均 `cp`+`md5sum -c` 还原重建 ⇒ 39/39 回绿、组件工作树干净。
**F1 处置（改实现）**：未设限的 `RLIMIT_STACK` 改为报告 loader 实际映射的主栈 `max(guest_stack_size, 32×页=2 MiB)`（默认 8 MiB）。理由：宿主 `RLIMIT_STACK` 不是真实约束——宿主 unlimited 时区域仍是 8 MiB、宿主 2 MiB 时区域仍是 8 MiB 默认，两头都不等；读该值不影响 musl 启动（musl 不读 `getrlimit(RLIMIT_STACK)`），且仅 `TARGET_DADAO`。探针按 `max(8 MiB, 有限宿主 rlimit)` 独立推导期望（qemu 文档化的 `-s` 默认 + main.c 抬升规则）。
**已知限界**：主栈不受 guest `RLIMIT_STACK` 约束（loader 预映射后再设限不回收/不裁剪已映射区域）；未设限报告=映射区域大小，已设限报告=guest 设定值（可为 infinity），二者语义不同已在此写明。其余同前：data 总量含可写 `MAP_SHARED` 与预映射主栈（只更早触发）；`prlimit64` 仅 self；记账仅 `TARGET_DADAO`。
**新发现/坑**：① 内核 `may_expand_vm()` 对 `RLIMIT_DATA` 有「Workaround for Valgrind」——`cur=0` 而 `max` 未动时仍放行（宿主实测如此），故「DATA=0 ⇒ ENOMEM」只在 `{0,0}` 成立；`{0,0}` 不可逆故探针放最后。② 总量取 `walk_memory_regions()` 现读页表而非计数器（计数器会漂移）；页表无「私有/栈」标记，故保守多算。③ `RLIMIT_STACK` 只在 `MAP_GROWSDOWN` 处限长（qemu-user 主栈不能按需增长；原生内核把同一限额推迟到增长期，故 256 KiB 请求原生会成功——该条只断言 qemu-user 已文档化策略，注释明示）。④ libc-test 的 `runtest.c` 会 `t_setrlim(RLIMIT_STACK,100 KiB)` 后再 exec：限额不改变新映像的预映射栈（同上限界），`check-inst` 未退化。⑤ 证据脚本首版 `local name=$1 bak=…$name` 在 `set -u` 下解引用未赋值变量，已拆行修正。
**遗留问题**：① `ISS-343` 关闭与 `milestones.md` 行更新留 `/complete`；可关闭判据 = 39 条探针断言入库且绿 + 两种反例 FAIL→还原回绿 + 六项门控 rc=0。② 未做（已知、已注释）：跨 target 通用化；主栈随运行期 `RLIMIT_STACK` 收缩；`prlimit64` 其它 pid 查询；硬上限提升的 `EPERM` 权限检查。

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 首次实现把「是否记账」判据写成 `guest_rlimit_get()` 返回 true（= 已 set 过），首次 set 仍走宿主 no-op | ✅已修 | `guest_rlimit_get()` 对三项恒返回 true（未设过则回 `RLIM_INFINITY`），`set` 仅用于 mmap 快路径 | 探针 `as/data_getrlimit_cur=0`，20/20 PASS |
| F2 `mmap.c` 未 include `<sys/resource.h>` ⇒ `RLIMIT_*` 未声明 | ✅已修 | 顶部补 include | `make build-qemu` rc=0 |
| F3 探针 errno 期望用 int 与字符串结果比较 ⇒ 2 条假 FAIL | ✅已修 | `str(enomem)` | `75/75 checks passed` |
| F4 f-string 里 `{0,0}`/`{0,inf}` 单括号被当集合字面量求值 | ✅已修 | 双括号转义 | 标签逐条打印 `{0,0}`/`{0,inf}`，75/75 |
| F5 `guest_rlim[]` 跨 guest 线程读写无同步（mmap 侧持锁读、syscall 侧裸写） | ✅已修 | 存取器持 `mmap_lock()`（同线程可重入） | 重建后 smoke 75/75、证据脚本 `--inject` PASS |
| F6 data 总量含可写 `MAP_SHARED` 与预映射主栈（内核 `data_vm` 不含） | ⏸延后 | 页表只记可写性，无私有/栈标记；要精确需另建映射元数据（超出最小面） | 已在补丁注释与完成区披露方向（只更早触发） |
| F7 `RLIMIT_STACK` 只覆盖 `MAP_GROWSDOWN`，主栈不随运行期值重设 | ⏸延后 | loader 侧重设会偏离原生 exec 语义（原生也只在增长期限），且需改 elfload | 值可读回 + 映射限长已实现，限界明示 |
| F8 `prlimit64` 其它 pid / 硬上限提升无 `EPERM` 权限检查 | ❌不修 | qemu-user 无按 pid 的 guest 限额表；模拟器不是权限边界 | 注释写明；探针仅用 self 与合法 `{0,inf}` |

判决：F1–F5 已修并复验，F6–F8 为已披露的明确限界（非缺陷伪装），状态 `待验收`。

#### 第 1 轮 reviewer 验收

重跑记录（reviewer 亲自执行，rc=真实退出码；长输出 运行期日志）：
- 证据脚本 `run.sh`（默认模式）→ **rc=0**，`QEMU-084t evidence: PASS (0 failures)`；32 项 PASS = 6 门控 rc=0（source-state / patch-tree / install-host / check-inst / check-arch / L1）+ smoke `75/75 checks passed`；rlimit 断言 **20 发出 / 20 PASS / 0 FAIL**
- `run.sh --inject` → **rc=0**：把 `guest_rlimit_check_mmap()` 改回 no-op ⇒ 4 条 FAIL（AS/DATA 的 rc+errno），`cp`+`md5sum -c` rc=0、组件树 clean、回绿 20/20
- `make check`（L1）→ **rc=0**（`repository checks (L1): PASS`）；`make check-source-state` → **rc=0**（`qemu HEAD=5d900f7c36df count=1 clean=True`，即 base+1）；`make check-patch-tree` → **rc=0**（`7 component(s), 305 patches OK`；series=65 行、补丁=65 份）；`make check-inst` → **rc=0**（44/44 + node full + tiny）；`make check-arch` → **rc=0**（16/16 runtime + 14/14 cfx）；`make build-qemu`/`make install-host` → **rc=0**
- smoke 关键条目：`unset RW mmap ok`；`AS={0,inf}` set/get=0 → RW mmap `-1/errno=12`；AS 恢复 → `ffffffffffffffff` → mmap `ok`；`DATA={0,inf}` → `ok`；`DATA={0,0}` → `-1/12`；RO `ok`；SHARED `ok`

独立注入（reviewer 自做，不走 run.sh，全程 `cp`+md5、无 git 还原）：
- A 把 `guest_rlimit_exceeds()` 改为恒 `false` ⇒ build rc=0 → smoke **rc=1、4 FAIL**（as_mmap_rc/errno、data_zero_mmap_rc/errno）、71/75；还原 `md5sum -c` rc=0、组件树 0 行 → 重建 rc=0 → **rc=0、75/75、0 FAIL**
- B 在 fast-path 后恒 `return -TARGET_ENOMEM` ⇒ build rc=0 → smoke **rc=1、5 FAIL**（全部“放行”断言：AS/DATA 恢复、`{0,inf}`、RO、SHARED）、70/75；还原后 md5 复归 `e20a7d7f…`、重建 rc=0、回绿 75/75

语义核验（独立 oracle，不读 QEMU 日志/实现）：
- 宿主原生（Linux 6.8）同例实测：`AS={0,inf}→ENOMEM、恢复→ok`；`DATA={0,inf}→ok`（Valgrind workaround 属实）；`DATA={0,0} RW→ENOMEM、RO→ok、SHARED→ok` —— 与 20 条断言期望逐条一致；探针页大小 **65536** 写死
- ad-hoc 探针：`NOFILE` 读回 `0x100000`=宿主 `ulimit -n`、`CORE=0`，set 往返 `0xfffff`→恢复 ⇒ **透传成立**；`prlimit64(pid=1)` rc=-3 errno=3 `ESRCH` ⇒ **pid 取舍披露属实**；raw `SYS_getrlimit(RLIMIT_DATA)` 读回 0 ⇒ **libc 不走的 get/setrlimit 分支也正确**；`STACK` set `{0x20000,inf}` 读回 `0x20000`、`GROWSDOWN 256KiB→fail errno=12`、`GROWSDOWN 128KiB→ok`、非 GROWSDOWN `256KiB→ok`

约束核验：改动 = 6 改 + 2 新增补丁，**无 spec/contracts/gem5/tests 期望**；新代码 `TARGET_DADAO` 全包围（非 DADAO 仅注释文案变化）；完成区 7 行、无运行期路径；本轮 ≤40 行；断言均有可达 FAIL 路径（A/B 实证）、计数现取自日志不写死；未改 spec/测试凑绿。

findings（均不阻断）：F1 guest 未设限时 `getrlimit(RLIMIT_STACK)` 由宿主 8MB 变 `RLIM_INFINITY`，而 `guest_stack_size` 仍取宿主 rlimit —— 补丁注释有写、完成区未披露，供 architect 定夺；F2 20 条断言不含 STACK，完成区「STACK 可读回 + GROWSDOWN 限长」无入仓证据（我 ad-hoc 复跑为真），建议补 2–3 条入库；F3 raw `SYS_getrlimit/setrlimit` 分支无入仓断言（ad-hoc 复跑为真）；F4 `ISS-343` 仍 `open`（关闭留 `/complete`，判据已给足）；F5 我首轮 L1 rc=2 系自身日志名不合 `check-run-artifacts` 命名规约所致，改名后 rc=0（非交付物缺陷）。

**判决：Accepted** —— 验收标准 1–5 在我的重跑下全部满足、约束无违反；Accepted 仅为“工程师达标”，终审归 architect。

#### 第 2 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| R-F2（reviewer）20 条断言不含 STACK，STACK 只有 ad-hoc 证据 | ✅已修 | 探针新增 STACK 组 13 条：128 KiB set/get 往返、`MAP_GROWSDOWN` 256 KiB⇒ENOMEM / 128 KiB⇒成功、普通 256 KiB 不受影响、恢复后 256 KiB 成功 | smoke `94/94`，`static rlimit` 39/39 PASS |
| R-F3（reviewer）raw `SYS_setrlimit/SYS_getrlimit` 分支无入仓断言 | ✅已修 | 探针新增 raw 组 6 条（`RLIMIT_DATA` `{0,inf}` 往返 + 恢复） | `raw_getrlimit_cur=0`、`raw_restore_cur=ffffffffffffffff` PASS |
| R-F1（reviewer）未设限 `RLIMIT_STACK` 报 infinity 而主栈实际受限 | ✅已修（改实现 + 披露） | `guest_rlimit_get()` 对未设限的 STACK 返回 `max(guest_stack_size, 32×TARGET_PAGE_SIZE)`；补丁头注释 + `user-mmap.h` 同步；探针新增 3 条默认值断言 | `stack_default_cur=800000`（=8 MiB，与宿主 rlimit 推导一致）PASS |
| S1 证据脚本 `restore()` 里 `local name=$1 bak=…$name` 在 `set -u` 下报 `unbound variable`（首轮 `--inject` rc=1，现场为注入未还原） | ✅已修 | 拆成两行 `local`；并先按备份 `cp`+`md5sum -c` 手动还原被注入的源文件再重跑 | `--inject` rc=0；`restore(noop/stack): md5 matches backup` + 组件树 clean |
| S2 旧探针二进制（上一轮留的 `.elf`）不含新键，用安装根复跑时空输出 | ✅已修 | 从 `user_mode_smoke.py` 的 `RLIMIT_C` 重新编译探针后再复跑 | 安装根 `qemu-dadao` 输出 `stack_default_cur=800000`、`stack_growsdown_256k_errno=12`、`raw_getrlimit_cur=0` |
| S3 注入只覆盖「整段 no-op」，无法说明新断言各自敏感 | ✅已修 | `--inject` 增加第二种注入（仅 `want_stack=false`），断言「只该条 FAIL、其余不 FAIL」 | `inject(stack): the GROWSDOWN cap assertion FAILs`=1、`no unrelated rlimit assertion FAILs`=0 |

判决：R-F1/R-F2/R-F3 与 S1–S3 全部已修并复验，状态 `待验收`。

#### 第 2 轮 reviewer 验收

重跑（reviewer 亲自执行，rc=真实退出码；长输出 运行期日志）：
- 证据脚本 `run.sh` → **rc=0**、`QEMU-084t evidence: PASS (0 failures)`、**52 项 PASS**（1 构件 + 6 门控 + 6 smoke 计数 + 39 rlimit）；smoke **94/94、0 FAIL**（含 25 条 dynamic/musl 行）
- 六项门控逐条 **rc=0**：`check-source-state`（`qemu HEAD=2c93fed67cb9 count=1 clean=True` = base+1）/ `check-patch-tree`（`7 component(s), 305 patches OK`；series=65 行、补丁 65 份）/ `install-host` / `check-inst`（44/44 + node full + tiny）/ `check-arch`（16/16 runtime + 14/14 cfx）/ `make check` L1（`repository checks (L1): PASS`）
- `run.sh --inject` → **rc=0**：整段 no-op ⇒ **6 FAIL**（AS/DATA/STACK 各 rc+errno）；仅 `want_stack=false` ⇒ **2 个 FAIL 行**（同一条 GROWSDOWN 256 KiB 的 rc+errno；其口径计 1、无关联失败），两次均 md5 还原 rc=0、组件树 clean、回绿 39/39

F1 实现核验（自己读源，不采信自述）：`setup_arg_pages()` 的 `size = max(guest_stack_size, STACK_LOWER_LIMIT)`，而 `STACK_LOWER_LIMIT = 32*TARGET_PAGE_SIZE`（elfload.c:393、401-404）——与实现 `MAX(guest_stack_size, 32*TARGET_PAGE_SIZE)` **逐项相等**（guard 页 PROT_NONE 不计，与原生报 limit 不报 guard 一致）；`guest_stack_size` 默认 `8*1024*1024`（main.c:134）、宿主有限且更大时抬升（main.c:723-728）。新代码整体在 `#ifdef TARGET_DADAO`（mmap.c:171-390；`#include "loader.h"` 为无害通用 include）⇒ 非 DADAO 行为不变。Node/Tiny/musl 未退化：check-inst node full+tiny、L1、25 条 dynamic 断言全绿。

独立 oracle：`stack_default_cur` 的期望链在 smoke 内可见（`mapped_stack = 8<<20`，即 qemu 文档化 `-s` 默认；宿主值由驱动直读 `resource.getrlimit`，不经 guest）；本机 `ulimit -s`=8192 KB、原生 `getrlimit(RLIMIT_STACK)`=`800000` ⇒ 期望与原生一致。GROWSDOWN 256 KiB 一条注释明示「原生推迟到增长期会放行、此条不对照原生」，与我第 1 轮原生实测（native `gd_oversize=ok`）相符，非从 QEMU 日志/输出反推。

断言敏感度（reviewer 自注入，非 engineer 那两种）：
- **R2-A 把 GROWSDOWN 比较方向改反**（`guest_rlimit_exceeds(0,pages,…)` → `cur!=INF && pages < (cur>>16)`）⇒ build rc=0、smoke **rc=1、恰 2 FAIL**（仅 GROWSDOWN 256 KiB 的 rc+errno）、92/94；`cp`+`md5sum -c` rc=0、组件树 0 行、重建 rc=0 → **94/94**
- **R2-C 关掉 F1 默认值分支**（`if (i == GUEST_RLIM_STACK)` → `if (0)`）⇒ **恰 2 FAIL**（`stack_default_cur/max` 均 `actual=ffffffffffffffff`）、92/94；同法还原回绿 94/94、md5 复归 `ed6afafd…`

约束核验：完成区 **9 行**、无运行期路径；本轮 ≤40 行；改动仍 = 6 改 + 2 新增补丁，无 spec/contracts/gem5/tests 期望；状态 `待验收`；工作区快照 8 条与开工逐行一致、组件源树 clean。`ISS-343` 可关闭判据「39 条断言入库且绿 + 两种反例 FAIL→还原回绿 + 六项门控 rc=0」**三条我均已实测成立**（issue 仍 `open`，关闭留 `/complete`）。

**判决：Accepted** —— F1/F2/F3 三条返工在独立重跑与独立注入下全部闭环，验收标准满足、约束无违反；Accepted 仅为“工程师达标”，终审归 architect。

#### 收尾（architect，2026-11-06）

- F1：未设限 `RLIMIT_STACK` 改报主栈实际映射 `max(guest_stack_size, 2 MiB)`，与 `elfload.c` 的 `size = max(...)` 逐项一致；只影响 `TARGET_DADAO`。
- F2/F3：STACK 13 条、raw syscall 6 条断言入仓；rlimit 断言 39 条。
- F4：`ISS-343` 关闭（`resolved_by = QEMU-084t`）。
- F5：reviewer 首轮 L1 红系自致日志命名，已改名，非交付物缺陷。
- 已知限界：主栈不受 guest `RLIMIT_STACK` 约束（预映射后设限不回收/不裁剪）；`prlimit64` 其它 pid 查询未做；data 总量含共享映射与主栈。
- 判决 Accepted（第 2 轮），状态置 `已验证`。
