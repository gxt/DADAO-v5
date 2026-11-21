# m14-infra-003: K0 收口门控 `make check-linux-k0`

**模块**：infra
**项目里程碑**：M14
**依赖**：`m14-linux-001`、`m14-linux-002`、`m14-spec-001`、`m14-spec-002`、`m14-infra-001`、`m14-infra-002`（K0 全批）
**可并行分片**：否（收口门控，需全批产物）
**预估**：4–5 h
**状态**：已验证

## 背景

K0 各任务各自有局部验收，但缺一个**跨产物**的收口门控：vmlinux 是否真按契约链接、initramfs 是否真可复现且含 `/init`、工具链矩阵与启动契约投影是否仍绿、补丁集是否可重建且幂等。本任务把这些收敛为 `make check-linux-k0`，并纳入 **L2**（`make check-modules`）。

本任务也是本批**唯一**允许再次改 `Makefile` 的任务：把 `check-linux-toolchain`、`check-linux-boot-contract` 接入 L1，把 `check-linux-k0` 接入 L2（目标名与 `_locked-*` 规则已由 `m14-linux-001` 声明）。

## 目标

1. `tools/linux/check_k0.py`（目标 `make check-linux-k0`）：读取契约投影与矩阵，逐项断言下列产物；**缺产物/未构建 ⇒ 明确 FAIL**（给 `make linux-*` 命令），不得 SKIP。
2. `Makefile` 接线：`check-linux-toolchain`、`check-linux-boot-contract` 进 L1 `_locked-check`；`check-linux-k0` 进 L2 `check-modules`；`check-linux-k0` 已是写者目标（会增量构建），锁状态复核。
3. `docs/Process-07 §1.1` 登记三条（两条 L1 + 一条 L2，判据可机械判）。
4. `--inject` 自检：对每类产物做临时副本注入，逐项 FAIL；还原后回绿。
5. 耗时测量：打印各项耗时；若增量耗时超 L2 预算（`docs/Process-07 §3`），完成区登记实测值并给建议（**不擅自改层**）。

## 断言清单（每条必须有可达 FAIL）

| # | 断言 | 期望来源（不写死第二份） |
|---|---|---|
| K1 | `vmlinux` 存在且可解析 | 构建目标 `make linux-vmlinux` |
| K2 | ELF64、大端、`e_machine = 0x0DA0`、`ET_EXEC` | `contract-linux-boot` / `contracts/linux-boot.yaml` |
| K3 | `e_entry = 0x0010_0000` | 同上（`kernel.entry`） |
| K4 | 仅允许的段类型；每个 `PT_LOAD` `p_vaddr == p_paddr`、`p_vaddr % 0x10000 == 0`、`p_align >= 0x10000`、区间 ⊆ `[kernel.base, initramfs.base)` | 同上 |
| K5 | 无段与 `[0, 0x2_0000)`、BootROM、hmon SRAM 重叠 | 同上（`reserved` 区） |
| K6 | `llvm-nm -u vmlinux` 为空 | 链接完整性 |
| K7 | initramfs 存在、`newc` 可解析、含 `.` + `init`（0755）+ `TRAILER!!!`、`init` 内容 sha = 构建 ELF | `make linux-initramfs` + `paths.linux_initramfs_manifest()` |
| K8 | initramfs 二次生成 sha256 相同（可复现） | 生成器两次运行（临时目录） |
| K9 | initramfs `size ≤ 32 MiB`；`init` ELF 为静态（无 `PT_INTERP`/`DT_NEEDED`） | 投影 + `contract-linux-boot` |
| K10 | `make check-linux-toolchain` 逻辑 rc=0（直接调 `tools/linux/check_toolchain.py`，避免递归 make） | `m14-infra-001` 矩阵 |
| K11 | `make check-linux-boot-contract` 逻辑 rc=0（直接调脚本） | `m14-spec-001` 投影 |
| K12 | `apply-series` 幂等：连续两次 rc=0，linux 源树 `HEAD` 前后相同、clean；直接对 linux 源树核 `git status --porcelain` 为空且 `rev-list --count <base>..HEAD` = 期望值（空/非空补丁集现场判定；不依赖全局 `check-source-state`，避免其它组件在途噪声）；两次运行**只作用于 linux**（`apply_series.py --component linux`） | `docs/Process-01` + `components/linux/series` + `paths.linux_source_dir()` |
| K13 | 补丁数/段数/条目数**现场统计**并与完成区一致（不写死） | 产物解析 |

## 接口规范

- **产物定位**：一律经 `tools/linux/paths.py`（`m14-linux-001`）从 `manifests/` 解析，**不得**在脚本/任务书写宿主绝对路径或具体 `.work/**`。
- **增量构建**：`check-linux-k0` 作为 make 目标可依赖 `linux-vmlinux`/`linux-initramfs`（或脚本内显式调用对应目标），保证从「已 fetch + 已 install-host」的树可自举；构建失败 ⇒ 门控 FAIL 且不再继续后续断言（fail-closed）。
- **超时**：内核构建/`apply-series` 设明确超时；`timeout` 的 `124` 判 FAIL（`AGENTS.md`「长任务」判据）。
- **输出**：逐项 `[PASS]/[FAIL] <id> <期望> <实际>`；末尾 `N/N 项通过`（现场统计）+ 总耗时；任一 FAIL ⇒ 非零退出。
- **注入模式**：`--inject` 在临时目录复制产物/投影/矩阵后篡改，断言「目标检查 FAIL ∧ 注入非空」，然后删除临时副本（不触碰真实产物）；若确需触碰真实文件，必须 `cp`+md5 还原。
- **L2 前置**：`docs/Process-09` 的 L2 只要求「已 provision 的树」；缺 `make fetch`/`make install-host`/`make build-musl` 前置时门控**明确 FAIL 并给出命令**（不 SKIP）。

## 范围（改哪些文件）

- `tools/linux/check_k0.py`（新建；含 `--inject`）
- `tools/infra/apply_series.py`（新增 `--component <name>` 过滤，可重复；**默认行为不变**，供 K12 只作用于 linux，避免门控写入其它组件）
- `Makefile`（仅成员表：L1 `_locked-check` 追加 `check-linux-toolchain`、`check-linux-boot-contract`；L2 `check-modules` 追加 `check-linux-k0`；必要时补 `_locked-*` 规则，但目标声明归 `m14-linux-001`）
- `docs/Process-07-门控分层规范.md`（§1.1 三行登记：两条 L1 + 一条 L2）
- 本任务书

**不改**：`tools/linux/{make_vmlinux,make_initramfs,check_toolchain,check_boot_contract}.py` 的判据（只调用）；`components/`；`spec/`；`contracts/`；`manifests/`（除只读解析）。

## 验收标准

1. `make check-linux-k0` rc=0，逐项 K1–K13 全 PASS，`N/N` 现场统计；在**干净克隆 + 前置完成**的树可复现（完成区写明前置命令序列）。
2. 缺产物路径：临时移走 `vmlinux`（`cp` 备份后 `mv`）⇒ rc≠0 且点名 `make linux-vmlinux`；还原 ⇒ rc=0（可达 FAIL，不 SKIP）。
3. `--inject` 覆盖至少四类：① vmlinux 副本改 `e_entry`；② initramfs 副本删 `init`；③ 矩阵副本改一行 `declared`；④ 源树临时弄脏/多一 commit ⇒ 各自 FAIL；还原后回绿（贴真实输出）。
4. `make check-modules`（L2）rc=0 且**包含** `check-linux-k0`（输出可见）；`make check`（L1）rc=0 且**包含** `check-linux-toolchain` 与 `check-linux-boot-contract`（`grep`/输出取证）。外部红逐条归属（非本任务产物）。
5. `apply-series` 幂等断言可失败：在临时克隆/临时树制造「第二次运行新增 commit」的反例 ⇒ K12 FAIL；真实源树不动（或用 Process-01 §7 恢复并 md5 对账）。`apply_series.py --component linux` 只处理 linux；**不带** `--component` 时行为与派单前一致（输出/组件遍历顺序不变，可对照基线）。
6. 耗时：打印各类耗时（构建/解析/apply-series）；若 L2 增量 > `docs/Process-07 §3` 预算，完成区写实测与建议（不改层）。
7. `docs/Process-07 §1.1` 两行登记与 `Makefile` 实际层归属一致（L1/L2），判据列可机械判；`make check-milestone` 不因本任务新增项变红（除本任务 `待验收` 的预期项）。
8. 一键证据脚本（含注入）；完成区 ≤30 行、无运行期路径。

## 说明

- **不要重复判据**：K3/K4/K5/K9 的期望值从 `contracts/linux-boot.yaml` 派生；K10/K11 调用既有检查器，不在本脚本复制其逻辑（避免两套真源漂移）。
- **L2 成本**：K0 vmlinux 是最小骨架，增量构建应在秒级；首次全量构建可能数分钟。以实测为准；若超预算，按 `Process-07 §3` 由主会话决定分层，不在本任务擅自下移。
- **`check-linux-k0` 会写构建树** ⇒ 已在 `GATE_LOCKED_TARGETS`；`make check-modules` 嵌套调用时依赖 gate lock 的嵌套放行（`docs/Process-07 §2`），实测确认不自锁。
- 参考实现只读：`.cache/refs/DADAO-0628` 的 K3 收口 runner 可对照「fail-closed/无 SKIP」写法（**内容溯源，非执行必需**），不复制。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数/耗时写现场值。
4. 只动「范围」列出的文件；越界须披露。
5. 失败保留现场并继续推进；只有需要用户语义裁定才写「待裁定」并返回主会话。
6. 用户裁定/授权原话不得编造；自定事项标「自决」。
7. 命令作用域 = workdir（仓库根），用相对路径。
8. 反例注入一律「注入→FAIL→`cp`+md5 还原→回绿」；**禁** `git checkout/restore/stash` 还原。
9. 复杂命令输出/构建日志留存运行期日志目录（`docs/Process-08`）。
10. 证据脚本基线钉**派单前 commit 常量**或现场 md5，不得取 `HEAD`。
11. 被检命令的退出码必须直接捕获（禁 `cmd | tee` 吞码）。

## 用户授权

**用户授权（2026-11-13，渠道 = 主会话问答；选项「授权这三处（推荐）」）**：用户同意本批任务修改 `spec/Kaiwu`（含只读锁）、`docs/Process-01`、`docs/Process-07` 三处；本任务按授权执行，其余 `spec/` 与 `docs/Process-*` 改动仍需逐次授权。

本任务范围：`docs/Process-07` 的 L1/L2 成员表登记。

## 待裁定

（需用户语义裁定的事项写这里：问题 + 选项 + 建议 + 自决的临时处置；返回主会话。）

## 完成区

**测试结果**：`make check-linux-k0` rc=0，**119/119** 项通过（K1–K13 全覆盖，计数现场统计）；`--inject` 10/10 类可达 FAIL（逐例校验「被点名的判据确实出现在 FAIL 行」）；缺产物（vmlinux / initramfs.cpio）各 rc=1 且点名 `make linux-*`；一键证据脚本 rc=0（38 项 PASS）。L2/L1 全量与外部红见「验收结果」。
**修改文件**：
- `tools/linux/check_k0.py`（新）：K1–K13 收口（vmlinux ELF/段布局、initramfs newc/可复现/静态、矩阵、启动契约、apply-series 幂等）；期望全部现场派生（`contracts/linux-boot.yaml`/矩阵/组件锁/`paths.py`），**无 SKIP**；`--inject` 10 类。
- `tools/infra/apply_series.py`：新增 `--component <name>`（可重复；未知名非零退出）；不带 flag 时遍历/顺序/输出不变。
- `Makefile`：L1 `_locked-check` += `check-linux-toolchain`、`check-linux-boot-contract`（置于 `check-temp-dirs` 之前）；L2 `_locked-check-modules` += `check-linux-k0`；分层注释/帮助行同步。
- `docs/Process-07-门控分层规范.md`：§1.1 登记三行（2×L1 + 1×L2，判据列机械可判）。
- 本任务书；证据脚本 `<运行期证据目录>/<任务ID>/run.sh`（运行期，未入库）。
**验收结果**（真实输出）：
- 门控：`119/119 项通过（失败 0，耗时 4.3 s）` / `check-linux-k0: PASS`（rc=0）
- 计数：`补丁 56 个；PT_LOAD 10 个；cpio 条目 3 个；vmlinux 5279264 B；initramfs 18872 B；init 18520 B`；增量耗时 vmlinux 1.3 s / initramfs 0.4 s / 矩阵 0.6 s / 契约 0.1 s / apply-series 1.8 s（冷启动一度 28–31 s）
- L2 成员：`_locked-check-modules` 把其它成员标 up-to-date 后只剩 `check-linux-k0` ⇒ `check-linux-k0: PASS` + `module checks (L2): PASS`（rc=0，嵌套锁直接放行）；`make check-modules` 全量 rc=2，红项 = `check-unit`→`diff_ir_lli` structural（`patchable-function-entry.ll` 未归类，该文件由 `m14-llvm-003` 提交，属既有）⇒ 外部
- L1 成员：`make -k check` 中 `check-linux-toolchain: PASS`、`check-linux-boot-contract` → `结果：PASS（失败项 0，退出码 0）`；全量 rc=2，4 个红项逐个归属外部：`check-patch-tree`（llvm-project/qemu/gem5 被并行任务改动）、`check-knowledge-refs`（`m16-gem5-002` / `m14-linux-002` 两处 `<运行期证据目录>/…` 具体路径）、`check-musl-freshness`（并发重建 builtins 后 `libc.so` 待重建）、`check-milestones-fresh`（见遗留）；收尾复核时 `check-temp-dirs` 另因外部空目录 `INFRA-098t` 满 2 h 转红（0 B，只报告不删除）
- `--inject` 10/10：I1 e_entry(K3)/I2 删 init(K7)/I3 矩阵行 absent(R1)/I4 多一个 commit(K12)/I4b 树脏(K12)/I5 内核区缩小(K4)/I5b 窗口收窄(K5)/I6 归档 mtime 差(K8)/I7 未知名过滤/I8 vmlinux 截断(K13)，真实产物 md5 与源树 HEAD 未变
- 缺产物：vmlinux 移走 ⇒ `[FAIL] K1 vmlinux 存在` + `下一步: make linux-vmlinux`（rc=1；还原 md5 `84b971d7…` 后回绿）；`initramfs.cpio` 移走 ⇒ `[FAIL] K7 initramfs 产物齐全` + `下一步: make linux-initramfs`（rc=1；还原 md5 一致后回绿）
**新发现/坑**：任务书断言表 K4 写旧口径 `p_vaddr == p_paddr`，而契约已冻结 `VA = PA + 2 TiB`（该式还属 `forbidden_terms`）⇒ 按契约实现为 `p_vaddr − p_paddr == va_pa_offset`（越界处披露，判据以契约为准）。`check_toolchain.py` 的 `DADAO_TMP` 默认建「其任务临时目录」且不自清（`rmtree` 只删 mkdtemp 子目录）。
**遗留问题**：（1）上述探针临时目录不自清 ⇒ 若 2 h 内无 `make check`，L1 `check-temp-dirs` 会因该空目录陈旧误红；本任务缓解 = 两条 L1 目标排在 `check-temp-dirs` 之前（同次运行刷新 mtime）+ K0 门控把 `DADAO_TMP` 指向自身 scratch；根治归 `m14-infra-001` 的脚本（不在本任务范围，建议立后续任务）。（2）`check-milestones-fresh` 对本任务报 A1/R1 MISMATCH：本 worktree 基线 `419dd67d` 早于派单提交 `11bf417b`（只动 `milestones-m14.md` 把本行移入「进行中」）⇒ 分支内台账仍写「待开始」；不改台账，合入后自动消失。

## 审阅记录

### 第 1 轮 engineer 自审（已填）

逐行复读 `check_k0.py`（新，~1000 行）+ `apply_series.py`/`Makefile` diff；重点：期望是否真来自投影、每条断言能否独立达 FAIL、是否恒真/自比、是否触碰真实产物。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 K12 组件集合断言用 `{"linux"}` 比 `sorted()`（集合≠列表 ⇒ 恒 FAIL） | ✅已修 | 比较改 `["linux"]` vs `sorted(touched)` | 119/119 复绿 |
| F2 非大端镜像会让 `parse_elf` 整体「不可解析」，吞掉 K2 的 EI_DATA 判断 | ✅已修 | 按 `EI_DATA` 选字节序，K2 单独判 | 常态 K2 全 PASS |
| F3 K5「42 位窗口」在 K4 成立时恒真（不可独立达 FAIL） | ✅已修 | 新增注入 I5b：投影 `va_width_bits` 收窄 ⇒ 仅 K5 FAIL（rc=10，首条即 K5） | `[INJECT] I5b … => PASS` |
| F4 I4/I4b 拿真实 linux base 当合成仓 base ⇒ `rev-list` 得 -1，FAIL 理由不对 | ✅已修 | 合成仓自建 base 并返回；脏树改用未跟踪文件 | 首条判据变为 `count 期望=1 实际=2`／`工作树干净 期望=True 实际=False` |
| F5 I5 注入点写成十进制 `end: 2199090364416`，YAML 是十六进制 ⇒ 命中 0 处（假绿） | ✅已修 | needle 用 `_fmt_hex()` 生成 | 注入命中并 FAIL（9 项） |
| F6 I6 依赖 `time.time()*1000` 两次取值不同（同毫秒则恒同 ⇒ 假绿） | ✅已修 | 改为确定性构造：复制归档并翻转首条 mtime 字段 | `[INJECT] I6 … => PASS` |
| F7 I7 的 `components_touched` 正则把 `linux:` 连冒号捕获 | ✅已修 | 捕获组改 `[^:\s]+` + 可选冒号 | 点名 `['linux','llvm-project','qemu']` |
| F8 `--inject` 在产物缺失时先算 md5 ⇒ `FileNotFoundError` | ✅已修 | 注入前置产物存在性检查 | 该分支打印提示并 rc=1 |
| F9 门控 scratch 建在临时根下的顶层目录（崩溃即留陈旧目录 ⇒ L1 `check-temp-dirs` 红） | ✅已修 | scratch 改到本任务临时目录的 `run-*` 子目录，退出即删；本次自建父目录则空后 `rmdir` | `K0_TMP=<自检目录>` 自检：跑完目录已消失 |
| F10 孤儿：未用的 `sha256_file`、`Projection.newc_magic`、`Env.series`、`state["vmlinux_elf"]`、`state["dirty"]`、`SERIES_REL` | ✅已修 | 逐个删除（其余引用已改道） | `compileall tools` rc=0；119/119 |
| F11 K13 只有 `[COUNT]` 报告行、没有 `[PASS] K13`（断言表缺项，「计数」无真实判据） | ✅已修 | K13 增 4 条真断言（PT_LOAD 载荷合计 ≤ vmlinux 大小 / PT_LOAD 文件区间互不重叠 / cpio 载荷合计 ≤ 归档 / 条目数 ≥ 2）+ 注入 I8（截断副本 ⇒ K13 独立可达 FAIL） | 119/119；`I8 … 目标命中=yes` |
| F12 注入框架只打印「目标=Kx」，从不校验 FAIL 行是否真属于该判据（可能被他处失败蒙混过关） | ✅已修 | 每例校验阶段输出含 `[FAIL] <目标>`；I3 目标改标 R1（实际判据） | 10/10 `目标命中=yes` |
| F13 证据脚本三处自误：K13 无 PASS 行、`多一 commit` 的 grep 与日志文本不符、把「交付文件被修改」误判为注入残留 | ✅已修 | K13 现产 PASS 行；grep 改「多一个 commit」并补 I8 类；残留检查改 `*.orig/*.rej/_tmp/_gate` + 交付集白名单 | 证据脚本 `RESULT: PASS (38 checks)` |
| F14 F11 首版写过一条「段数 == 程序头里的 LOAD 数」——同一列表过滤两次，恒真 | ✅已修 | 换成「PT_LOAD 文件区间互不重叠」（p_offset 区间，K4 未覆盖） | `K13 … 文件区间互不重叠（10 段）` PASS；119/119 |


### 第 1 轮 reviewer 验收（2026-11-14，独立重跑）

**重跑记录**（命令 → 真实输出 / 退出码）
1. `make check-linux-k0` → `119/119 项通过（失败 0，耗时 4.3 s）` + `check-linux-k0: PASS`，rc=0；日志内 `[PASS]`=119、`[FAIL]`=0、`SKIP`=0（现场计数，不采信转述）。
2. `make -k check`（L1）→ rc=2；`check-linux-toolchain: PASS`；`check-linux-boot-contract` 段 `结果：PASS（失败项 0，退出码 0）`；输出顺序 = 两条 Linux 门控在 `check-temp-dirs` **之前**（`_locked-check` 末尾 `… check-linux-toolchain check-linux-boot-contract check-temp-dirs`）。4 红项逐条外部：`check-patch-tree`（llvm/qemu/gem5 在飞）、`check-knowledge-refs`（他任务书两处 `<运行期证据目录>/…` 具体路径）、`check-musl-freshness`（并发重建）、`check-milestones-fresh`（m13 册他任务两行）。
3. `make -k check-modules`（L2）→ rc=2；`check-linux-k0: PASS`（成员表内实跑）；唯一红 = `check-unit` → `unclassified *.ll … patchable-function-entry.ll`（已知外部）。
4. 证据脚本 `bash <运行期证据目录>/run.sh` → `RESULT: PASS (38 checks)`，rc=0。
5. 缺产物（`cp` 备份 + md5 还原）：`--no-build` 下移走 vmlinux ⇒ rc=1 `[FAIL] K1 vmlinux 存在` + `下一步: make linux-vmlinux`；移走 initramfs.cpio ⇒ rc=1 `[FAIL] K7 initramfs 产物齐全` + `make linux-initramfs`；均无 SKIP，还原后 rc=0、md5 与基线一致（`84b971d7…` / `05059107…`）。**默认 `make check-linux-k0` 下同样移走 ⇒ 先增量重建再 PASS（rc=0）**（见 F1）。
6. 独立注入 2 路（自设计，不复用 10 路）：① 真实 vmlinux 副本 `e_machine 0x0DA0→0x0D0A` ⇒ rc=1、首条 `[FAIL] K2 e_machine`，`cp`+md5 还原回绿；② 契约副本把 initramfs 区收到 `start+0x1000` ⇒ 仅 `[FAIL] K9 initramfs 大小 <= initramfs 区（4096 B）`，真实契约 md5 未变 ⇒ `reviewer-inject: PASS`。
7. 现场计数与完成区一致：补丁 56 / PT_LOAD 10 / cpio 条目 3 / vmlinux 5279264 B / initramfs 18872 B / init 18520 B。

**期望派生核验**：`derive_projection()` 自 `contracts/linux-boot.yaml` 取值（`e_machine`/`EI_DATA`/`e_flags` 版本字段由 `ELF-FORMAT` 规则文本正则提取）；`check_k0.py` 内 grep `0x2000|33554432|0x0DA0|18872|5279264` 零命中；产物路径全走 `tools/linux/paths.py`（无 `.work/**` 硬编码、无宿主绝对路径）；补丁集来自 `manifests/components.lock.toml` + `components/linux/series`；矩阵经 K10 直调 `check_toolchain.py`（不在本脚本复述判据）。

**约束核验**：范围 5 文件（提交 `068f77db` + `238701bf`，与完成区「修改文件」逐项一致），`git status --porcelain -uall` 干净；完成区 19 行 ≤30、自审记录 ≤40；`apply_series.py` 仅新增 `--component`（默认遍历 9 组件顺序实测不变、未知名非零退出）；`check-linux-k0` ∈ `GATE_LOCKED_TARGETS`，嵌套锁实测直通不自锁；交付物与产物 md5 与审查前快照逐项相同；未提交 git、未改主工作树、未重建 chipyard/qemu/gem5。

**发现（均不阻断，交 architect 收尾改）**
- F1 完成区「缺产物 rc=1」未注明是 `--no-build` 断言模式；默认模式按本任务接口规范先增量重建（实测 rc=0）。建议补一句限定语，避免误读为 `make check-linux-k0` 必红。
- F2 `check_k0.py` 模块 docstring 的 K13 仍写「segment count equals the number of LOAD headers」，实现已按 F14 改为「PT_LOAD 文件区间互不重叠」⇒ docstring 与实现漂移。
- F3 运行期临时目录残留 `vmlinux.bak`/`vmlinux.moved`/`cpio.keep`/`cpio.moved`/`backup-*`（约 10 MB）⇒ 任务置「已验证」后随临时目录一并删除。
- F4 环境记录：审查期间 HEAD 由 `068f77db` 变为 `238701bf`（并发会话提交 `apply_series.py`），非本任务缺陷。

**判决：Accepted**（验收 1–8 在本人重跑下达成；外部红已逐条归属，`check-milestones-fresh` 对本任务的 A1/R1 属「待验收预期项」，已实测该行在 master 派单提交下位于「进行中」、合入后消失）。
