# TESTCASES-079t: consumer-typeset 的 musl catclose(-1) 守卫

**模块**：testcases（组件补丁涉 musl）
**项目里程碑**：M10
**依赖**：TESTCASES-076t、TESTCASES-069t
**状态**：待验收

## 背景（自包含，2026-10-27 全量实测）
`MultiSource/Benchmarks/MiBench/consumer-typeset` 在 static 全量中 `FAIL`（guest SIGBUS，si_addr=0x7）：

- 语料 `z01.c:229` 存 `catopen` 结果、`z01.c:856` **无条件** `catclose(MsgCat)`；guest 无 catalog（`openat("lout.lib/locale/C/LC_MESSAGES/errors.C") = -1 ENOENT`）⇒ musl `catopen` 返回 `(nl_catd)-1`。
- musl `catclose` **无 -1 守卫**，解引用 `map+8`（地址 0x7）⇒ guest SIGBUS；宿主 glibc `catclose((nl_catd)-1)` 返回 `-1/EBADF`（本机实测），故上游参考在 glibc 下不崩。
- 已登记 **ISS-339**（P3）：语料未查返回值 + musl 端口健壮性差异；不是 qemu 指令语义/后端误编译。

## 目标
1. 在 **musl 组件补丁**中给 `catclose` 加对无效 catalog（含 `(nl_catd)-1`）的守卫，返回 `-1` 并置 `errno = EBADF`（与 glibc 行为对齐）；按 `docs/Process-01` 组件补丁树（一文件一补丁 + `git apply` + `check-patch-tree`）落地。
2. 重建 musl（`make build-musl`，申报耗时）并确认：`catclose((nl_catd)-1) == -1`、`errno == EBADF`；合法 catalog 的 `catopen/catclose` 行为不变。
3. `consumer-typeset` static+dynamic 均 **pass**（输出+exit 与参考一致），不再 SIGBUS。
4. 回归：`check-tset-libc-full`（static+dynamic）rc=0（含既有 known-fail 口径）；`make check` rc=0。
5. 更新 `ISS-339`（resolved_by/关闭）与 musl 组件 changelog（如项目有此约定）。

## 验收
- 定向：typeset 两档 pass；负例（`catclose(-1)`）返回 `-1/EBADF`，且不崩。
- `check-patch-tree` rc=0；`make check` rc=0；`check-tset-libc-full` 两档 rc=0。
- 证据 `.work/evidence/<任务号>/run.sh`（含注入→FAIL→`cp`+md5 还原→PASS）。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/TESTCASES-079t/`。

## 约束
- 只动 `components/musl/patches/**`、musl changelog、本任务测试/证据/任务书/milestones；不改 spec/qemu/LLVM 语义、不改语料期望。
- 若 musl 补丁方案被证明不可行，**先报告**再考虑语料侧检查；不得静默放宽 typeset 断言。
- **不提交、不 push**；重建 musl 前申报预计耗时；不跑无关全量。

## 完成区

**状态**：待验收

### 修改文件
- `components/musl/patches/src/locale/catclose.c.patch`（新增，唯一功能改动）
- `components/musl/series`（+1 行：24 → 25）
- `components/musl/changelog.md`（M10 追加一条）
- `.tao/knowledge/issues.yaml`（ISS-339 → closed / `resolved_by=TESTCASES-079t`）
- `.tao/knowledge/milestones.md`（本行状态与摘要）
- `.work/evidence/TESTCASES-079t/{run.sh,verify.py,catclose_probe.c,catclose_noguard.c}`（证据；`.work/` 不入库）
- 本任务书；musl 源码改动在 `.work/source/musl`（E1：base+1 且干净），仅经补丁集体现

### 验收命令与结果（真实输出）
**测试结果**：6/6 组通过；`make check` rc=0；证据脚本 **34/34 PASS**
1. `make check-patch-tree` rc=0（5 components / **204** patches；musl series 25 == patches 25，现场统计）
2. `make build-musl` / `make build-musl-shared` 各约 15 s rc=0（源码 digest 变 ⇒ `make clean` 全量重编；10/10 ELF 检查）；`check-musl-freshness` PASS
3. 静态探针（qemu-dadao）：`catclose(m1).rc=-1 errno=9`、`catclose(NULL).rc=-1 errno=9`、`catopen(valid).is_m1=0`、`catgets(valid).fallback=1`、`catclose(valid).rc=0`、rc=0（不崩）
4. consumer-typeset `--link-mode both`：static/dynamic 均 `pass`、exit=0、`matched (byte-exact)`（`consumer-typeset.reference_output`），无 guest SIGBUS（原 si_addr=0x7）
5. libc 定向两档不变：flockfile-list `known-fail`(ISS-255)、setenv-oom `pass`、pthread_create-oom `pass`、pleval static `pass` / dynamic 结构性 excluded（上游 `pleval.mk`）；`check-tset-libc-full` 两档 rc=0（pass 335/338、known-fail 2/2、fail 0）；`check-tset-libc-smoke` rc=0
6. `.work/evidence/TESTCASES-079t/run.sh` → 34/34：C3 注入上游无守卫 `catclose` ⇒ 同探针 SIGBUS（rc=135）；C4 注入 patch（md5 变）⇒ `check-patch-tree` rc=1 → `cp` 还原（md5 相同）→ rc=0

### 遗留
- 语料 `z01.c` 仍未查 `catopen` 返回值（UB 仍在，库侧已不崩）；按约束未改语料
- `run_llvm_ts_user.py::GUEST_FAULT_NOTES` 的 typeset 条目仍描述历史故障（仅故障路径打印），本任务范围外未改
- 未跑 `make check-full` / `make check-night`（用户 2026-10-27 裁定不下发）；libc 全量已按任务跑（3 min）

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-27）

**审查方式**：自主逐行（本会话 `subagent_depth=1`，不作嵌套子代理；独立验收由 `/complete` 的 reviewer 承担）。

**逐行审查结论**
- 补丁本体：只对 `(char*)-1` / `NULL` 早退；合法路径 `munmap(map, V(map+8)+20); return 0;` 逐字未改；`<errno.h>` 是 `errno` 宏所需（musl 库内映射到 `___errno_location`，静态/共享两档均编译链接通过）；两值都是不可解映射的哨兵（`0x7` / `0x0`），早退不改变任何合法调用语义。
- 补丁集：由 `make_patch.py` 导出（非手编），一文件一补丁、`series` 字典序；`check-patch-tree` ①–⑨ 全绿（含 ⑥ 应用产物 == 工作树、⑨ HEAD 净 diff == 补丁集）。
- 证据脚本：每条断言均有可达 FAIL —— C2 逐行比对真实探针输出；C3 用上游无守卫对象复现 SIGBUS（rc=135）；C4 改 patch 内容 ⇒ 门控真红 → `cp`+md5 还原 → 真绿；计数（series/patches、204 patches）现场统计、未写死；无 `tee` 吞码。
- 诚实性：`make check` 在最终树（含 issues/milestones/changelog 改动）上运行；typeset 结论取自 `run.json` 的 `klass/exit/reason`，非人工判读。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| 首轮证据 C1 以单 tab 匹配 patch 加行（实为两 tab）⇒ 1 红 | ✅已修 | needle 改为 `errno = EBADF;` | 二次运行 34/34 PASS |
| C3 初稿 `assert_has … /dev/null` 恒真（vacuous） | ✅已修 | 改为 `assert_lacks` 检查无守卫构建的真实输出 | C3 两项 PASS；无守卫输出确无 `probe.failures=0` |
| `verify.py` 的 dynamic pleval 排除判定用 `split`+子串，脆弱 | ✅已修 | 改为精确 id `cid + ".c" in excluded` | C6 dynamic 两项 PASS |
| 守卫只覆盖 `-1`/`NULL`，任意野指针仍读 `map+8` | ❌不修 | 无 | C 层无法机械校验任意地址；glibc 同样只判 `-1`；本任务验收面即 `(nl_catd)-1`（外加必然无效的 `NULL`） |
| 补丁注释首版写「Report them the way glibc does (EBADF)」，对 `NULL` 属过度声明（glibc 只特判 `-1`，`NULL` 会崩） | ✅已修 | 注释改为「EBADF —— glibc 用于 `(nl_catd)-1` 的 errno」 | 重新导出补丁 + `build-musl(-shared)` + 证据 34/34 + `make check` rc=0 |
