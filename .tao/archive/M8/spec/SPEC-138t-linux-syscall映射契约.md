# SPEC-138t: Linux syscall 映射契约（`contract-syscall.md`）

**模块**：spec
**项目里程碑**：M8
**依赖**：`ADR-0025`（M8 范围与 Linux 兼容路线，`Accepted`，`D1`= 沿用 RISC-V 编号）；`SPEC-139t`（并列契约，无先后硬依赖）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 背景 / 依据

- **M8 主线**（`ADR-0025`）：无内核的 Linux 用户态栈；**P0 = 契约先行**（`ADR-0025 D6`）。
- **上游已有 syscall ABI（勿重复发明）**：`spec/DADAO-21-ABI §4` 已定发起方式 / 传参 / 返回；`spec/DADAO-22-SBI §2` 已定 `umon(cfx0)` / `jmon(cfx1)` 的 `SBI_*_SYSCALL`（`immu18=0`）。**缺的是 Linux 语义映射**（号表 / errno / 参数与返回值语义）。
- **号表口径 = 沿用 RISC-V 编号**（`ADR-0025 D1`；用户原话「沿用 RISC-V 编号（推荐）」）。
- **errno 约定待定**：`rderrno`（`rd1`，`spec/DADAO-21-ABI §1`）与 musl 的关系**本任务内待定 / 需查证**；**不得臆造**。

## 接口规范

- **输入**：`spec/DADAO-21-ABI §4`、`spec/DADAO-22-SBI §2`、`ADR-0025`、`ADR-0004`（exit port 协议）、RISC-V Linux 号表（**外部参照，仅作内容溯源，非执行依赖**）。
- **输出**（落点 `.tao/knowledge/contract-syscall.md`）：
  1. **号表口径**：syscall 号在 `rd15`、**沿用 RISC-V Linux 编号**（`ADR-0025 D1`）；**不复制**上游正文，**指针**到 `spec/DADAO-21-ABI §4` / `spec/DADAO-22-SBI §2`。
  2. **入口**：`trap cfxha, immu18`（`umon` 路径）与 SBI `SBI_UMON_SYSCALL`（`immu18=0`）的关系（**引用**，不重复正文）。
  3. **参数与返回**：参数 `rd16–31` / `rb16–31` / `rf16–31`、返回 `rd8`（**指针** `spec/DADAO-21-ABI §4`）。
  4. **errno 约定**：`rderrno`（`rd1`）与 musl 的关系——**待定**，须在任务内查证或标为待用户裁定（**不得臆造**）。
  5. **独立 oracle 口径**：期望值 / 对照来源（与 `ADR-0025 D7` golden 对照衔接）；**不从实现反推**。
- **约束**：**不复制**上游 `spec/` 正文（只**指针**）；**不改** `spec/`、`contracts/` 机器数据、组件补丁。
- **落点迁移接口**：本契约暂落 `.tao/knowledge/contract-syscall.md`（`check-knowledge-dir` 白名单允许 `contract-*.md`）；若 `INFRA-071t`（`contract-*.md` → `contracts/`，**待用户授权**）获批，本契约**随之整体迁移** ⇒ 引用路径须**可切换**（不写死具体目录）。

## 验收标准

1. `contract-syscall.md` 落 `.tao/knowledge/`，含上述 5 项；对外引用均**指针**到 `spec/DADAO-21-ABI §4` / `spec/DADAO-22-SBI §2`（`grep` 真实输出），**无**上游正文复制。
2. 号表口径与 `ADR-0025 D1` 一致（`rd15` + 沿用 RISC-V 编号），`grep` 可证。
3. errno 一项**有明确归属**（已定 **或** 标「待用户裁定」并给出选项），**无臆造**。
4. 门控：`make check` / `check-knowledge-dir` / `check-knowledge-refs` / `check-no-residue` / `python3 tools/infra/check_issues.py` 各 rc=0。
5. （若 errno 需裁定）用户裁定**原话**原样写入本任务书。

## 完成区

**测试结果**：一键证据脚本 `.work/evidence/<任务ID>/run.sh` 常模 **56/56 PASS（rc=0）**；`--inject` **8/8 PASS（rc=0）**——注入①（复制 `DADAO-21 §4` 正文句 + `#define __NR_read 63`）⇒ 检查 **rc=1**（C3 反例命中）⇒ cp+md5 还原 ⇒ 回绿；注入②（锁定 sha256 全改 0）⇒ **rc=1**（C4 命中）⇒ 还原 ⇒ 回绿。门控：`make check` / `check-knowledge-refs` / `check-no-residue` / `check-knowledge-dir` / `python3 tools/infra/check_issues.py` **各 rc=0**（25 open / 2 closed）〔09:30 曾因并行任务半写 `manifests/components.lock.toml` 捕到一次 `make check` **rc=2**，现场与归因见「新发现/坑」；重跑 rc=0〕；另以**临时树**证明两知识门控可失败（bogus 文件 ⇒ rc=1、悬空 `.work/**` 引用 ⇒ rc=1）。
**修改文件**：`.tao/knowledge/contract-syscall.md`（**新增**）；`.tao/knowledge/milestones.md`（`SPEC-138t` 行 状态→`待验收`；**已由 architect 随 `f90f01d` 提交**）；本任务书（状态 + 完成区 + 自审）；`.work/evidence/<任务ID>/{run.sh, foreign-paths.txt}`（新增，`.work/` 忽略区）。**本任务的 contract/task 文件未提交 git**（提交权归 architect）。
**验收结果**（逐条对齐 §验收标准）：① 落点+5 项 ✓——`grep '^## '` 得 §1 号表口径与来源锁定／§2 入口（`umon`/`jmon`）／§3 参数与返回／§4 errno／§5 独立 oracle 口径／§6 QEMU 角色与边界／§7 待裁定清单／附录 A；指针 `[DADAO-21 §4. 系统调用规范]`×12、`[DADAO-22 §2. 用户态异常处理（umon / jmon）]`×8；`check-spec-refs` **PASS**（0 violations）；上游正文 3 条切片（现场取自 spec/）**absent**。② `rd15` +「沿用 RISC-V Linux 编号」（`ADR-0025 D1`）grep 可证 ✓。③ errno **标「待用户逐条确认」** + A/B/C 三选项（查证 = musl 上游 `src/internal/syscall_ret.c` 负值约定 + qemu `linux-user/riscv/cpu_loop.c`）；`ADR-0025` 未定 ⇒ **未臆造** ✓。④ 门控见上 ✓。⑤ **本任务未取得用户裁定**（errno 待裁）⇒ 原话待裁定后回填。
**新发现/坑**：
- **号表来源已双向锁定（可核 / 可复算）**：**上游** = 内核 **`7.2.10`**（身份 = 签名 tarball sha256 `2feaa704…`，`.cache/linux-<版本>.tar.xz`；pin 由兄弟任务 `INFRA-075t` 落到 `manifests`：`source_kind="tarball"`/`patchless`）；**本仓快照** = qemu（`c3d48b7d…`＝`v11.1.1`）的 `linux-user/riscv/syscall.tbl`（`8872daa6…`）+ `asm-riscv/unistd.h`（`0134f2d3…`）+ `asm-generic/unistd.h`（`9ec1fadd…`）+ 展开派生 `asm-riscv/unistd_64.h`（`5845303a…`）。**本任务独立复核（非采信他任务结论）**：tarball sha256 重算一致；内核 `asm-generic/unistd.h` 与 `arch/riscv/…/unistd.h` 与快照**逐字节相同**；内核 `scripts/syscall.tbl` ↔ 快照 tbl 共同名集（322 名）**0 冲突**（内核多 9 条更新号）、↔ 快照展开头（328 名）**0 冲突**；宿主 `linux-libc-dev 6.8` uapi ↔ 快照（315 名）**0 冲突**。
- **号段**：asm-generic 预留「各架构自有 syscall 自 244 起至多 16 个」，RISC-V 占 258/259；DADAO 是否另设私有号待裁。**`AUDIT_ARCH_*`（由 `EM_DADAO` 0x0DA0 派生）是 audit 子系统标识、非 syscall 号段**；参考实现（0628，内容溯源）取 `__AUDIT_ARCH_LE`，而 v5 为**大端** ⇒ 端序位待确认。
- **共享工作树并发（重要）**：本工作树**共享且被并发修改**（兄弟任务 `INFRA-075t` + architect 收尾：`AGENTS.md`/`manifests/`/`tools/infra/manifest_check.py`/`.tao/knowledge/lessons.md`）——非本任务改动已在 C6 用**人工声明清单** `.work/evidence/<任务ID>/foreign-paths.txt` 显式声明（**未声明即 FAIL**）；09:30 曾捕到 `make check` **rc=2**（`check-patch-tree: KeyError: 'patch_series'`＝该 manifest **半写**态，约 1 min 后重跑 **rc=0**）⇒ 并发瞬态、非本任务所致。
- **脚本坑（自审发现）**：`printf | grep -q` 在 `set -o pipefail` 下因 SIGPIPE 使断言**随机假红**（首轮 5 项）⇒ 改**文件型 grep**；`--inject` 多次调用后全局 `FAILED` 未清零 ⇒ 第三次误报 FAIL ⇒ 改**按调用快照计数** + INJ 独立计数器；契约 §4 内层 `**` 未闭合已修。
**遗留问题**：**待用户裁定 3 项**（契约 §7；原第 4 项「上游内核版本」**已消解** = 内核 `7.2.10`，见上）：① errno 载体（A `rd8` 负值 / B `rd1` rderrno / C 双写）；② DADAO 是否另设 arch-specific 私有号；③ `AUDIT_ARCH_*` 端序位。契约按任务要求**不重抄号表**（号值以 §1.2 锁定来源为准）；`.work/evidence/<任务ID>/foreign-paths.txt` 为**点时刻**声明，architect 收尾时可按当时 `git status` 复核/更新。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：`.tao/knowledge/contract-syscall.md`（新增）、`.tao/tasks/spec/SPEC-138t-*.md`、`.tao/knowledge/milestones.md`（1 行）、`.work/evidence/<任务ID>/run.sh`（另有并行兄弟任务 `INFRA-075t` 的改动，已声明为外任务、不在本自审范围）。
**逐行审查**：契约 §1–§7 全部断言回读 spec/ 原文核对（`rd15`/`umon`/`jmon`/`rd8`/参数三组/`immu18=0` 表）；事实与推测/待定**分列**（§4 选项、§7 清单）；无号值、无 `#define __NR_`、无 syscall.tbl 行；四个快照 sha256 + 内核 `7.2.10` 三项（tarball / 两 uapi）现场重算匹配。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `printf \| grep -q` + `pipefail` ⇒ SIGPIPE 致断言**随机假红**（首轮 C1/C2/C3/C4 共 5 项假红） | ✅已修 | `run.sh` 断言改**文件型**（`grep -qF -- pat <file>`），新增 `DOC_FILE` 快照 | 48/48 PASS rc=0；连跑 2 次结果一致 |
| F2 `--inject` 第三次 `run_checks` 误报 FAIL（全局 `FAILED` 被注入轮次置 1 后未清零） | ✅已修 | `check_invariants/check_gates` 改 `local before=$FAILS` 快照返回 rc；INJ 判定用独立计数 `jbad` | `--inject` 8/8 PASS rc=0（bad=0） |
| F3 `C3.no-__NR_-definitions` 误判：契约 §1.3 合法引用 `__NR_arch_specific_syscall` 被计为 1 | ✅已修 | 断言收窄为「无 `#define __NR_` **定义行**」 | C3.no-__NR_-definitions 0/0 PASS |
| F4 契约 §4 内层 `**` 未闭合（`**候选口径（三选一，**待用户…**）**`） | ✅已修 | 去掉内层 `**` | 渲染粗体成对；`check-spec-refs` PASS |
| F5 双册版本风险：版本头若同列 `DADAO-21`(0.9.2)+`DADAO-22`(0.7.1) ⇒ `check-spec-drift` 必红 | ✅已处置 | 版本头只取 ABI 册前缀（0.9.2），正文另设「版本基准」行说明 SBI 0.7.1 为入口参照 | `check-spec-drift` `[PASS] contract-syscall.md → AEE / ABI 0.9.2` |
| F6 号表只锁到**派生快照**，未锁上游内核版本 | ✅已修（升级） | 契约 §1.2 增「上游 = 内核 `7.2.10`（tarball `sha256`）」+ 与快照的一致性五条；§7 #4 改「**已锁定**」；证据脚本加 **C4k**（tarball sha / 内核 uapi 逐字节 / tbl 0 冲突） | `C4k.tarball-sha256-matches`、`C4k.kernel-uapi-identical-to-snapshot`×2、`C4k.kernel-tbl-vs-snapshot-0-conflicts` **全 PASS** |
| F7 `C4.sha256-recompute` 在 `clean-work` 后可 SKIP（构建源区可重建） | ❌不修 | 保持显式 `SKIP` 打印（非静默通过）；契约另记 commit/sha256 供复算 | 本次实测 4/4 `C4.sha256-matches` PASS；SKIP 分支不影响当前结论 |
| F8 工作树内**并发**外任务改动使 C6「仅允许文件」断言误报越界（`INFRA-075t` → 后又见 architect 收尾改动） | ✅已修 | C6 改为「owned 集（3 文件）+ **人工声明外任务清单** `foreign-paths.txt`（`grep -xF` 精确匹配；未声明即 FAIL）」；主交付物断言改「changed **或**已入索引」 | `C6.no-undeclared-path-changed` PASS；声明清单现场打印（5 条） |
| F9 09:30 一次 `make check` rc=2（`check-patch-tree: KeyError: 'patch_series'`）——根因 = 兄弟任务**半写** `manifests/components.lock.toml` | ✅已处置 | 不改任何文件（不得覆盖他人未提交改动）；保留现场 + 重跑 | 现场 `.work/log/spec/`；约 1 min 后重跑 `make check` **rc=0**（`manifest validation: PASS`）|

**判决**：无未修 finding（F7 为设计选择；原 F6「上游版本待锁定」已**升级为已锁定**：内核 `7.2.10` + 本任务独立复核）；判据对账 = 状态 `待验收`。

#### 第 1 轮 reviewer 验收

**方式**：判决全凭本人重跑/重算（命令 + 真实 rc），未采信完成区转述；未改任何交付物（注入一律 cp+md5 还原）。并发改动（`INFRA-075t`：`manifests/`、`tools/infra/{fetch,manifest_check}.py`、`AGENTS.md`、`lessons.md`、其任务书）非本任务、不计入范围。
**① 号表锁定（自己重算，逐位比对契约）**：tarball `.cache/linux-7.2.10.tar.xz` sha256=`2feaa704…cff2ebf3` ✓；内核 `include/uapi/asm-generic/unistd.h`=`9ec1fadd…`、`arch/riscv/…/asm/unistd.h`=`0134f2d3…`，与 qemu 快照同名文件**逐字节同值** ✓；qemu 4 快照（`8872daa6…`/`0134f2d3…`/`9ec1fadd…`/`5845303a…`）逐位一致 ✓；内核 Makefile `7.2.10` ✓；manifests pin（linux-kernel tarball sha / qemu commit `c3d48b7d…`）一致 ✓。
**② 零冲突（独立脚本重算，非采信）**：内核 `scripts/syscall.tbl` ↔ qemu tbl：common=322、conflicts=0、内核独有 9 条（`file_getattr` 等）＝契约所称 ✓；内核 tbl ↔ `unistd_64.h`：common=328、conflicts=0 ✓；宿主 `riscv64-linux-gnu-cpp -D__LP64__ -dM`（`__NR3264_*` 别名归一）↔ 快照：common=315、conflicts=0 ✓；抽查 read=63/openat=56/exit_group=94/riscv_hwprobe=258/riscv_flush_icache=259 三方一致 ✓。
**③ 引用非复制（grep 真实输出）**：`#define __NR_` 定义行=0、tbl 行=0（两 grep 均 rc=1 无匹配）✓；上游正文 3 切片（现场取自 spec/）absent ✓；指针 `[DADAO-21 §4…]`×12、`[DADAO-22 §2…]`×8，`spec/DADAO-21` L381「## 4. 系统调用规范」、`spec/DADAO-22` L35「## 2. 用户态异常处理」真实存在 ✓。
**④ 条款一致性（逐条对原文）**：`rd15`+`immu18` 双层、参数三组各自独立计数自 16、返回 `rd8`、read 示例 rd16/rb16/rd17 ⇔ `DADAO-21 §4/§3.2.1–3.2.4` 与 `contract-abi §4.1/§4.2/§4.3`（caller 扩展、全局声明序单栈区 8B）无矛盾 ✓；`umon(cfx0)`/`jmon(cfx1)`、`immu18=0`、`rd15=nr`/`rd8=result`、两入口独立编号 ⇔ `DADAO-22 §2` 表逐条一致 ✓；`escape cfxha,[excp_cause_ip,4]` ⇔ `DADAO-22 §1` ✓。
**⑤ §4 errno**：仍标「待用户逐条确认」+ A/B/C 三选项、`ADR-0025` 未定、未臆造 ✓。用户 2026-10-14 已裁定（A 等 3 项）尚未写入 ⇒ architect 按裁定写入，**非阻断**。
**⑥ oracle 口径**：§5「不得从 v5 自身实现反推」+ 期望值=spec/Linux 语义/RISC-V musl golden（`ADR-0025 D7`）✓；§6 QEMU user-mode=转发层且「不得充当 §5 期望值来源」✓。
**⑦ 门控（自跑，各捕自身 rc，无 tee 吞码）**：`make check`=0、`check-knowledge-refs`=0、`check-no-residue`=0、`check-knowledge-dir`=0、`check_issues.py`=0（25 open/2 closed）✓。
**⑧ 独立反例（cp+md5，禁 git 还原）**：备份 md5=`4bd49e38d1d2e0f40c3669b3b1a68f3a`；单字符篡改 tbl sha256 末位（`…d41d→…d41e`）⇒ **同一证据脚本** rc=1、新 FAIL=`C4.sha256-matches (…syscall.tbl…)`（基线 FAIL 集仅 C6）⇒ cp 还原 md5 回 `4bd49e38…` ⇒ 重跑 C4 回 PASS ✓。另复跑 `--inject`：INJ1/INJ2 注入→检测→md5 还原全按预期；INJ3「回绿」红 = 下述并发项所致。
**并发现场（非本任务、不计入）**：证据脚本 `C6.no-undeclared-path-changed` 现红 = `tools/infra/fetch.py`（`INFRA-075t` 09:43 改动，**晚于** 09:38 的外任务声明清单；diff= tarball 组件 fetch 守卫，确属外任务）⇒ 非交付物缺陷；`--inject` INJ3 随之红。**处置（非阻断）**：收尾时按当时 `git status` 刷新外任务声明清单（任务书已注明由收尾复核/更新）。
**非阻断 findings**：N1 §1.2 交叉核验句「名集差异仅 4 项 feature-gate 名 + 1 项新增号」不可精确复现（按其方法我数得 host-only 3 项元/别名名 + snap-only 5–7 项；核心数 315 名/0 冲突可复现 ✓）⇒ 建议收尾订正描述（该行自标「环境相关、非锁定真源」）。N2 §3「扩展由 caller 负责」实为 `contract-abi §4.2`（`ADR-0018 C4`）口径而来源标 `[DADAO-21 §3.2.2]` ⇒ 句内已声明同口径、不矛盾，建议补标。
**工作区对账**：验收前后 `git status --porcelain -uall` 逐行一致（仅本任务书+新增契约属本任务，余为已声明外任务）；契约 md5 注入前后同为 `4bd49e38…` ✓。
**判决：Accepted**（验收标准 1–5 于本人重跑下全部成立；阻断项=无；余见上述非阻断 2 项 + 并发处置项）。

---

## 追加：用户裁定落地 + reviewer 非阻断订正（2026-10-14，architect；**不改写**上文既有完成区 / 审阅记录）

### 用户裁定（**原话 / 选项标签**，2026-10-14，渠道 = 经主会话问答）
1. **errno 载体** = 「**A：`rd8` 负值（推荐）**」⇒ 落契约 §4（首条）/ §7 #1。
2. **arch-specific syscall** = 「**沿用 RISC-V arch-specific（推荐）**」⇒ 落契约 §1.3 / §7 #2（DADAO **不另设**私有号段）。
3. **`AUDIT_ARCH_*`** = 「**定义 AUDIT_ARCH_DADAO，BE，64位**」⇒ 落纸 `AUDIT_ARCH_DADAO = EM_DADAO(0x0DA0) | AUDIT_ARCH_64BIT`，**不带** `AUDIT_ARCH_LE`（契约 §1.3 / §7 #3；与 `contract-elf §1` `EI_DATA=ELFDATA2MSB`、`ADR-0003` 一致）。

### reviewer 非阻断订正（第 1 轮 N1/N2）
- **N1**（§1.2 交叉核验行）：删去不可精确复现的「名集差异仅 4 项 feature-gate 名 + 1 项新增号」；改为「**以独立复算为准 = 共同名集 315 名、号值 0 冲突**」，并声明名集差异项随宿主 libc 版本 / 别名归一方式而变 = **非稳定量**。
- **N2**（§3）：补 `[ADR-0018 C4]` 来源（`contract-abi.md §4.2` 的 caller 扩展口径），附录 A §3 行同步标注。

### 源形态同步（承接 `INFRA-075t` ⓐ 组件名裁定）
- 契约 §1.2 / §7 #4 的号表 pin 由「tarball `sha256` / `linux-kernel` / `source_kind`」同步为 **git 基线**：`linux` 条目（`commit = 7b20d05f…` = annotated tag `v7.2.10` peel commit；`shallow_ref = "v7.2.10"`；`patchless = true`）；tarball 明文标为**校验物 / 下载原件，不作组件源**。

### 状态与留痕
- 第 1 轮 reviewer 判决 **Accepted**（0 阻断）；本追加 + 上列订正落地后 **状态 → `已验证`**；`milestones.md` 回填 `完成时间`。
- **待办（请用户裁定是否立 ADR）**：上述 3 项裁定属**外部契约 / 结论固化**性质，现仅落本 `contract-syscall.md`（未入任何 ADR）⇒ 是否另立 ADR（或经授权修订 `ADR-0025` / `ADR-0003`）由用户裁定。
