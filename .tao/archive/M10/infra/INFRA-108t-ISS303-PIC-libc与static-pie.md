# INFRA-108t: PIC libc 归档与 `-static-pie` 支持（ISS-303）

**模块**：infra
**项目里程碑**：M10
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地（需 `build-musl-shared` / 安装集；无 LLVM 重建）

## 接口规范

### 背景（ISS-303，实测 2026-10-20）
- `clang -static-pie` 用**非 PIC** 的 `libc.a` ⇒ lld 逐条拒绝 `R_DADAO_ABS48`（`recompile with -fPIC`），仓库**未提供 PIC 版 `libc.a`**。
- `build-musl-shared` 已产 `.lo`（PIC 档）但**未归档、未入安装集**。

### 输出（**方案 B 已定**，用户 2026-10-25「可以」）
1. 由 musl 的 PIC `.lo` 归档 `libc_pic.a`（命名/落点按安装约定），**入安装集**；
2. 驱动在 `-static-pie`（以及 `-pie` + 静态 libc）时**自动选** `libc_pic.a`；普通 `-static` 仍用现有非 PIC `libc.a`；
3. `components/musl/README.md`（或安装说明）写明用法与边界；
4. 不改变默认静态链接（非 PIE）的产物；
5. **理由（主流做法）**：glibc 用单一 `libc.a` 编 `-fPIE`；musl 默认非 PIC，发行版用 specs/归档选择（方案 B）——保留非 PIE 静态性能。

### 约束
- 不改 musl 上游源码；不改 LLVM target 行为；
- 归档内容与 `.lo` 一致（md5/成员清单可核）；
- 若发现驱动无法可靠区分「静态 PIE」与「动态 PIE」（需要额外标志），停下报告口径选项。

## 验收标准
1. `clang -static-pie` 链接 rc=0，并在 `qemu-dadao` 运行得到预期退出码（贴命令/输出）。
2. 普通 `-static` 产物与改动前**逐字节一致**（md5）。
3. 反例注入（去掉 PIC 归档选择）⇒ `-static-pie` 复现链接失败 ⇒ `cp` 还原 ⇒ 绿。
4. L1 / L2 绿。
5. 完成区贴真实输出与退出码。

## 完成区
**测试结果**：证据脚本 `.work/evidence/INFRA-108t/run.sh` **37/37 PASS（rc=0）**、`--inject` **12/12 PASS（rc=0）**；`make check`(L1) **rc=0**、`make check-modules`(L2) **rc=0**、`check-install-tools` **PASS（48 项）**、`check-musl-freshness --self-test` **rc=0（7 注入）**。核心：`-static-pie` 链接 rc=0 → ET_DYN / 无 PT_INTERP / 有 PT_DYNAMIC → `qemu-dadao` 退出码 **7**、stdout **`PIE OK`**；`libc_pic.a` **1349** 成员（与 `libc.a` 成员名逐序一致、逐成员 sha256 == 源 `.lo`）；注入（移走 `libc_pic.a`）→ 驱动回退 `libc.a` → 链接失败并逐条 `R_DADAO_ABS48 ... recompile with -fPIC`（多条）→ `mv` 还原 md5 一致 → 回绿。
**修改文件**：`components/llvm-project/patches/clang/lib/Driver/ToolChains/DADAO.cpp.patch`（驱动：`-static-pie` 转发 + PIC 归档选择）；`tools/infra/build_musl.py`（产/验/装 `lib/libc_pic.a`）；`tools/infra/check_musl_freshness.py`（L1 增装拷新鲜度 + 自测注入）；`components/musl/README.md`（用法/边界）；`Makefile`（仅 `build-musl-shared` 的 help 文案，共享文件单列理由：安装集新增 `libc_pic.a` 需在用户入口可见）；`.tao/tasks/infra/INFRA-108t-*.md`、`.tao/knowledge/milestones.md`（状态/流水）。证据：`.work/evidence/INFRA-108t/`（run.sh + baseline 夹具 + 两个 helper）。
**验收结果**：① `clang --target=dadao-unknown-elf -static-pie probe.o <musl>/lib/rcrt1.o <musl>/lib/libc.a` → rc=0，`Type: SharedObject (0x3)`、无 `PT_INTERP`、`PT_DYNAMIC (0x2)`；`qemu-dadao` rc=**7**、stdout=`PIE OK`。② 普通 `-static`：**同一 lld/对象、仅换驱动**（build-tree 新 clang 驱动 + 旧 lld）产物 md5 `52a6e3fff7f06658ca8568c405e1e864` == 改动前（`cmp` 全等）；`install-host` 后 lld 自身 VCS 字符串变化，产物仅 `.comment` 的 VCS 字样不同，掩蔽后 sha256 全等（`2236bd81…`，见 `baseline/`）。③ 驱动决策（`-###`）：`-static-pie` ⇒ `-static -pie --no-dynamic-linker` + `libc_pic.a`；`-pie` + `libc.a` ⇒ `libc_pic.a`；`-static` ⇒ 仍 `libc.a`、从不选 PIC。④ 日志：`.work/log/infra/INFRA-108t-{evidence,evidence-inject,check-L1,check-L2,check-install-tools,build-mc,install-host,build-musl-shared}.log`。
**新发现/坑**：① 改前 `-static-pie` **不是链接失败而是静默失效**：驱动丢弃该 flag（仅 `-Wunused-command-line-argument`）⇒ 产出 ET_EXEC；真正的 ABS48 拒绝只在 `-pie` 生效时出现（ISS-303 现象须用 `-Wl,-pie` 复现）。② `ar` 成员名按**输入 basename** 存（PIC 归档内是 `.lo`，`libc.a` 内是 `.o`），比对须做后缀归一。③ musl `LOBJS` 有**重复 basename**（`clone/free/realloc`）⇒ `ar p <name>` 无法定位第二个，故自写 GNU ar 解析器按**成员顺序**逐字节比对。④ 改组件补丁 = amend 组件 commit ⇒ `VCSRevision.h` 变 ⇒ clang/lld/所有对象 `.comment` 变；「逐字节一致」只能在「同一 lld + 同一对象、仅换驱动」下严测（本册已做），装根后须掩蔽 VCS 字样（证据脚本固化）。⑤ **执行环境与派单不符**：本册落在 `clang/lib/Driver`，必须 `make build-mc`（增量 ≈6 min）+ `install-host`（≈3.5 min）+ `build-musl-shared`，无法「无 LLVM 重建」；已如实执行并保留日志。⑥ sysroot `lib/` 同时有 picolibc 的 `libc.a` 与 musl 的 `libc_pic.a`：`-pie` + picolibc `libc.a` 会按 musl 口径替换（picolibc 无 `rcrt1.o`，不在支持面；已在 README 边界注明）。
**遗留问题**：① 归档选择只覆盖**显式路径** `libc.a`（`-lc` 隐式查找不替换，README 已注明）；② `-static-pie` 不自动加 `-fPIE`（编译选项仍由用户给，README 已注明）；③ 未把 `-static-pie` 纳入 `ADR-0025 D6` 的 P2/P3 交付口径（口径归用户，未改 ADR）。

## 审阅记录

#### 第 1 轮 engineer 自审
自审对象：驱动补丁（`DADAO.cpp` 新档全文）、`build_musl.py` 新增 178 行、`check_musl_freshness.py` 新增 63 行、README/help。
逐行检查点：`InputInfo` 替换保留 `Action`/`BaseInput`（`AddLinkerInputs` 只取 filename/type）；`-shared`/`-r` 排除；`-static-pie` 显式 `ClaimAllArgs`（无 unused 警告）；PIC 兄弟不存在时不替换（fail-closed）；ar 长名表/重复 basename；成员顺序；装拷 sha256。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 证据脚本 `compare_static.py` 只匹配到 1 个版本注记（LLD 行是 `Linker: LLD 23.1.3`，无 `version` 一词） | ✅已修 | 正则改 `(?:clang version\|Linker: LLD) …`，并要求两类注记都存在（防空掩蔽） | run.sh 4 段 2/2 PASS；`masked sha256 2236bd81…` |
| F2 注入断言用 `grep -c` 期望 1，实际 20 行（逐条 ABS48） | ✅已修 | 断言改为「≥1 行即 yes」（`grep -c` 现场计数） | `--inject` 12/12 PASS，日志留 2 条样例 |
| F3 首次归档比对把 PIC 成员名当 `.o`（`ar` 存输入 basename，实际 `.lo`） | ✅已修 | 成员名直接对 `LOBJS` basename；与 `libc.a` 比对时 `.lo→.o` 归一 | `build-musl-shared` 5/5 PASS（1349 成员） |
| F4 `archive_check.py` 首行计数在归档缺失时先打 `MEMBERS=0` 再覆盖 | ✅已修 | 先判存在再打印，缺失直接 FAIL | `run.sh` 1 段 3/3 PASS |
| F5 跨 `install-host` 后 lld 自身 VCS note 变，无法用「原始 md5」直接比对 `-static` | ❌不修（方法已加固，非缺陷） | 严测改为「同一 lld + 同一对象、仅换驱动」求 md5 全等；装根后用掩蔽 VCS 的独立 oracle 复验 | 严测 md5 双方 `52a6e3ff…`、`cmp` 全等；oracle 掩蔽后全等 |
| F6 sysroot `lib/` 中 picolibc `libc.a` 与 musl `libc_pic.a` 同目录，`-pie` + picolibc 会被按 musl 口径替换 | ❌不修（任务指定落点；越界改造无据） | README 边界段明写；picolibc 无 `rcrt1.o`，静态 PIE 不在其支持面 | README「边界」条；`check-picolibc-tests` 在 L2 绿 |

**判决**：全部可修项已修并复验；两条 ❌不修均附理由与当前门控证据。状态可置 `待验收`。

#### 第 1 轮 reviewer 验收
**重跑（reviewer 独立执行；日志 `.work/log/infra/INFRA-108t-reviewer-*.log`）**
- `bash .work/evidence/INFRA-108t/run.sh` → `EVIDENCE_RESULT: PASS (37 checks)`，`RUN_RC=0`；`--inject` → `PASS (12 checks)`，`INJECT_RC=0`。脚本逐条断言均有可达 FAIL 路径（无恒真、无双写同果），计数取现场值。
- `make check`(L1) `L1_RC=0`（含 `check-patch-tree: 5 component(s), 202 patches OK`、`check-musl-freshness: PASS`）；`make check-modules`(L2) `L2_RC=0`（`module checks (L2): PASS`）；`make check-install-tools` `CIT_RC=0`（`PASS (48 check(s))`，与完成区「48 项」一致）。
- `check_musl_freshness.py --self-test` → `SELFTEST_RC=0`，`baseline + 7 injections`；inject-7（篡改已装 `libc_pic.a`）实测 `actual=1` 失败 + 还原 md5 复核 ⇒ 新检查有可达 FAIL。
- 手工：`clang -static-pie` 链接 `rc=0` → `Type: SharedObject (0x3)` / 无 `PT_INTERP` / 有 `PT_DYNAMIC`；`qemu-dadao` `rc=7`、stdout `PIE OK`。`-###` 决策逐条实测：`-pie`+显式 `libc.a` ⇒ `libc_pic.a`；`-static`/`-shared`/`-r`/`-no-pie` ⇒ 仍 `libc.a`；`-lc` 保持 `-lc` 不替换（README 边界属实）。
**独立反例（`cp -p` 备份 + md5，未用 git checkout/restore）**：`mv` 走 `.work/source/musl/lib/libc_pic.a` ⇒ `-static-pie` 链接 `rc=1`、`grep -c 'recompile with -fPIC'`=20 条 `R_DADAO_ABS48`；`mv` 还原后 `cmp` rc=0、md5 `a4224982…` 一致 ⇒ 回绿 `rc=0` + qemu `7`。
**归档/驱动核对**：`ar t` 1349 成员顺序逐名 == `LOBJS` 1349；`ar p` 独立抽查 15 成员 sha256 == 源 `.lo`（0 失配；重复 basename `clone/free/realloc` ×2 属实）；构建树 `DADAO.cpp` 254 行与补丁**逐行全等**；替换只在 PIE 且非 `-shared/-r`、按「显式 `libc.a` 的同目录兄弟」，兄弟缺失即保持原输入（非破坏性临时树实测：20 条 ABS48 失败，不静默）。
**`-static` 逐字节**：同输入（baseline 夹具）+ 当前驱动/lld 重链，与改前 ELF 仅差 99 B 且**全部**落在 `Linker: LLD …` VCS 串内；`llvm-objcopy --remove-section .comment` 后双方 md5 `68cbaf92…`、`cmp` rc=0；`-###` 参数序列与改前驱动逐 token 相同 ⇒ 驱动改动未触碰 `-static`。改用当前 musl `libc.a/crt1.o` 链接大 104 B：1349 成员与 baseline 夹具差异**全部**仅为嵌入的工具链版本串（crt1.o 去 `.comment` 后 md5 相等），属 musl 重建工件、非驱动效应（记 finding，不阻断）。
**完成区一致性**：37/37、12/12、掩蔽 sha `2236bd81…`、1349、退出码 7/`PIE OK`、48 项，与我重跑输出逐项一致；`strict_compare.txt` 的「新驱动+旧 lld md5 `52a6e3ff…`」因旧 lld 已被 `install-host` 覆盖无法重跑，作记录性证据采信，并由上述两条独立佐证支撑。**修改文件**与 `git diff --name-only master...HEAD` 完全一致，无越界。
**工作区对账**：验收前后 `git status --porcelain -uall` 均为空；分支 `INFRA-108t`；无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej` 残留；注入物已按 cp/mv+md5 纪律还原。
**判决：Accepted** —— 全部验收命令在我自己的重跑下通过，无约束违反（未改 musl 上游源码、未改 LLVM target 行为、未提交 git）。
