# kselftest suite（试点，m18-linux-005）

本目录是**套件级回归**的第一块骨架：把锁定内核树里的 kselftest 用例交叉构建、装进
独立的 suite initramfs、在 QEMU `-M kaiwu-vast` 上逐例跑，产出机器可读结果与
**在库分诊台账**。它只覆盖 8 个试点用例，目标不是通过率，而是把「Linux 在 DADAO
上可用到什么程度」变成可复现、可归因、可复评的记录。

一条命令：

```sh
python3 tools/linux/suite/run_suite.py            # = --suite kselftest
```

同一骨架还跑第二块套件（LTP 子集，`m18-linux-006`）：`run_suite.py --suite ltp`，
用例清单/台账/口径见 `ltp/README.md`；两套件的 `results.json` 各自带 `suite` 字段，
校验永远重载本套件的用例与台账，互不串判。

它依次做：交叉构建 → 生成镜像 → 重建带该镜像的内核 → 启动 QEMU → 按用例
归属输出 → 写 `results.json` + `summary.txt` → 跑本目录的校验。退出码**只反映
骨架自身**（构建/启动/记录/校验失败才非零）；单个用例 FAIL 本身不决定退出码。

## 文件

| 文件 | 作用 |
| --- | --- |
| `suite.yaml` | 用例白名单、guest 侧超时、**记录的基线 verdict**、`stall` 标记 |
| `triage.yaml` | 在库分诊台账：每条非 PASS 一行（分类 + 证据 + 复评条件） |
| `patches/kselftest/` | 适配补丁 + `manifest.yaml`（上游 commit、补丁本体 sha256、逐补丁「应用前/后」目标文件哈希） |
| `check_suite.py` | 校验入口：台账/结果一致性；`--patches-only` 只校验补丁可干净应用 |

## 如何新增一个套件/用例

1. 在 `suite.yaml` 里加一行：`id`（唯一）、`dir`（kselftest 目录，可嵌套）、
   `prog`（目录里的程序名）、`timeout`（**guest 侧**秒数）、`expect`（当前实况）。
2. 跑一次 `run_suite.py`；若该用例非 PASS，就在 `triage.yaml` 加一行，写清分类与
   证据（用例输出里的一句话 + 退出码）与复评条件。
3. 只要用例依赖的设施在本机不存在（`CONFIG_*` 关着、没有 loader 等），就记
   `SUITE_ENV`/`UNSUPPORTED`，**不要**改成静态/删断言来让它「通过」。

顶层 `dir` 会被拷贝进运行期的套件副本，上游源码树只读；补丁只作用于副本。

**补丁只认 manifest**：`build_suite.py` 按 `patches/kselftest/manifest.yaml` 的顺序应用补丁（不 glob
目录），目录里多出未登记的 `*.patch`、或 manifest 登记的文件不存在，构建与 `--patches-only` 都判红；
每个补丁还逐条校验「补丁本体 sha256 + 应用前哈希 + 应用后哈希」，两个补丁触及同一文件时也不会互撞。

## 如何分诊（四类，互斥）

- `KERNEL_BUG`：内核行为错（例如 `futex_waitv` 返回 EINVAL、`mlock2` 路径让用例
  SIGSEGV、`clock_nanosleep(TIMER_ABSTIME)` 让整机停摆）。
- `TEST_ADAPT`：用例把 x86 假设写死了（4 KiB 页、glibc 扩展、x86 指令），修法在
  `patches/kselftest/`。
- `UNSUPPORTED`：本移植根本没有该设施（如 SysV IPC、socket），需要产品决策。
- `SUITE_ENV`：环境暂时不具备（镜像缺 tmpfs、以 root 跑导致用例跳过、依赖
  `m18-infra-002` 的动态加载器），写明依赖与重跑条件。

**「内核红」与「测试假设红」的区分办法**：先看证据里的判据来源。判据用到
`sysconf(_SC_PAGESIZE)`/`getpagesize()` 的，64 KiB 页不是理由；出现字面 4096、
`_sigev_un._tid`、`#include <asm/...>` 等 x86/glibc 专有物的，先按 `TEST_ADAPT`
怀疑，再用补丁验证（补丁后仍失败 ⇒ 才是内核问题）。

## 如何复现与复评

```sh
# 全套（构建 + 镜像 + 启动 + 采集 + 校验）
python3 tools/linux/suite/run_suite.py

# 只跑某个用例（调试；仍会重建镜像与内核）
python3 tools/linux/suite/run_suite.py --only mm-map-fixed-noreplace

# 只校验台账/结果（用最近一次运行）
python3 tests/unit/linux/suite/check_suite.py --latest

# 只校验适配补丁：目录与 manifest 双向相等 + 逐补丁增量应用（不适用/未登记即红）
python3 tests/unit/linux/suite/check_suite.py --patches-only
```

运行期产物（控制台全日志、`results.json`、`summary.txt`、逐例构建日志）在
`tools/linux/suite/suite_paths.py` 解析出的运行期目录里，任务书/文档只写结论与
路径名。每个用例的原始输出都在控制台日志里由
`SUITE CASE BEGIN <id>` / `SUITE CASE END <id> rc=… status=…` 包住，可直接逐字定位。

## 已知边界

- **静态链接**：guest 目前没有动态加载器（`m18-infra-002` 在建），所有用例静态链接
  musl。需要共享库/`dlopen` 的用例记 `SUITE_ENV`，不得用静态替代硬凑。
- **单 hart、无网络**：`socketpair`/SysV IPC 等不可用，相关用例记 `SUITE_ENV`。
- **停摆用例**：`clock_nanosleep(TIMER_ABSTIME)` 会让整机无输出，guest 侧
  `alarm` 也无法触发。这类用例在 `suite.yaml` 标 `stall: true`，排在最后，
  结果记 `HOST_TIMEOUT`（宿主看门狗是唯一兜底）。
