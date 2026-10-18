# QEMU-063t: `qemu-dadao` 宿主信号与挂死（8 例信号 + 1 例卡死）诊断与收口

**模块**：qemu
**项目里程碑**：M8
**依赖**：`QEMU-062t`（`qemu-dadao` user-mode 后端，已验证）、`TESTCASES-048t`（4 例 `SIGSEGV` 现场 + `unix-smail` 卡死现场）、`TESTCASES-047t`（`flockfile-list` `SIGBUS` / `setenv-oom` `SIGTRAP` 现场）、`TESTCASES-050t`（`lua` 宿主信号 + `lemon` guest 信号现场，2026-10-18 追加表行）、`ISS-255`/`ISS-266`/`ISS-269`（本册对应 issue）、`ISS-247`（用户态基址 = lld 默认 `0x10000`）、`ISS-248`（`blocked>0 ⇒ rc=1` 口径）、`ISS-257`（同族 `RLIMIT_AS` flake，**仅关联、非本册交付**）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 问题根源

`qemu-dadao`（`linux-user`）上 9 例非 guest 正常退出 / 卡死（8 例信号 + 1 例挂死），两档 `blocked`（driver 如实记 `rc<0` / timeout / 平台缺口，不冒充 pass/fail）：

| 例（来源） | 现场签名 |
| --- | --- |
| `MultiSource/Applications/SPASS`（`048t`） | `qemu killed by host signal 11`；`combined.out` 0 B |
| `MultiSource/Benchmarks/MiBench/consumer-typeset`（`048t`） | 同上（`large.lout`，0 B） |
| `MultiSource/Benchmarks/VersaBench/8b10b`（`048t`） | 同上（`input.txt`，0 B） |
| `MultiSource/Benchmarks/VersaBench/dbms`（`048t`） | 同上，**先产出 18151 B 后崩** |
| `regression/flockfile-list`（`047t` 静态档） | 宿主 **signal 7**（`SIGBUS`） |
| `regression/setenv-oom`（`047t` 静态档） | 宿主 **signal 5**（`SIGTRAP`）；**偶发 pass** |
| `MultiSource/Benchmarks/Prolangs-C/unix-smail`（`048t`） | 只打印 `resolve 'ALL' = 'ALL' @ '' (LOCAL)` 后**卡死**（300 s 超时，非信号） |
| `MultiSource/Applications/lua`（`050t`，**2026-10-18 追加**） | 宿主 **signal 11**（两档同签名；静态档停 `bench/process.lua` 666.9 s、动态档停 `bench/meteor.lua` 375.2 s；已并入 `ISS-266`） |
| `MultiSource/Applications/lemon`（`050t`，**2026-10-18 追加**） | **guest `SIGSEGV`**（每个 `fork` 子进程都崩；父进程 `first_error = Error while running on: <input>`、无 parser 产出；最小复现 = `example1.y`、`-O0` 亦可复现；`ISS-269`） |

- **两类新现场的区别（勿混）**：`lua` = **宿主**侧 `SIGSEGV`（与上 6 例同族，`ISS-266` 第 5 例，driver 记 `qemu killed by host signal 11`）；`lemon` = **guest** 侧 `SIGSEGV`（qemu 如实回传 guest 故障，driver 按平台缺口记 `blocked`，`ISS-269`）⇒ 前者查宿主信号帧/地址映射，后者查 guest 故障路径/指令语义。

- **性质（未定根因，不预设）**：上 7 例为**宿主侧**故障/挂死（非 guest 退出码）；`lemon` 例外 = **guest** `SIGSEGV`（qemu 如实回传 guest 故障）。宿主侧可能是 `linux-user` 的地址映射 / 信号帧路径 / 指令语义 / `setrlimit(RLIMIT_AS)` 直通宿主（`setenv-oom` 同族见 `ISS-257`：guest 设 `RLIMIT_AS` 作用于**宿主 qemu 进程** ⇒ 其后宿主侧分配失败）；guest 侧查故障路径/指令语义。
- **输入数据已排除**：`048t` 已按上游 `llvm_test_data()` + `WORKDIR %S` 就位（`testimg.ppm`/`mei16v2.m2v` 等同类处理），**不得**再以「缺输入」结案。
- **时间盒（用户 2026-10-18 裁定）**：诊断**总投入 1–2 小时**（追加 `lua`/`lemon` 两例后**不变**）；超时即**登记归因 + 保留现场**（不硬耗、不无限试错），剩余面如实留在 issue。

## 接口规范

- **输入**：
  - `components/qemu/patches/linux-user/**`（含 `dadao/{cpu_loop.c,signal.c,elfload.c,target_signal.h,…}.patch`）+ `series` + `changelog.md`
  - `.work/build/qemu/qemu-dadao`（构建树）与安装根 `qemu-dadao`（**证据须注明用的哪一个**）
  - 语料：`.work/source/llvm-test-suite/**`（只读）、`.work/source/libc-test/**`（只读）
  - 驱动：`tools/testcases/run_llvm_ts_user.py`、`tools/testcases/run_libc_test_user_suite.py`
- **输出**（**二选一/逐例**，可混合）：
  - **修**：`components/qemu/patches/**` 补丁更新 + `changelog.md`；修后该例在两档 `pass`（按各自 oracle）
  - **归因**：逐例「信号来源（宿主 `si_code`/`si_addr`）+ guest `PC`（`MC_PC`）+ 命中的地址映射/系统调用 + 归属面（qemu / LLVM / musl / 语料）」写入完成区，并更新 `ISS-255`/`ISS-266`/`ISS-269` notes（**不擅自 `closed`**：归因不等于修复）
  - 证据：`.work/evidence/<任务号>/run.sh`（default + `--inject`）+ 现场日志（`-strace`/`-d in_asm`/core 或等价）落 `.work/log/qemu/`
  - 本任务书完成区
- **约束**：只改 `components/qemu/**`（+ 必要时 `tools/testcases/**` 的**过期叙述**）+ 本任务书；**不动** `spec/`、`.tao/contracts/`、`contracts/`、语料/期望值；**不得**用「抬超时/改分类/改标签」当修复。

## 复现（自包含）

```bash
# 048t 面（4 信号 + 1 卡死；静态档先行，两档同）
python3 tools/testcases/run_llvm_ts_user.py --link-mode both --jobs 1 --timeout 300 \
  --only 'SPASS$' --only 'consumer-typeset$' --only '8b10b$' --only 'dbms$' \
  --only 'unix-smail$' --work-dir /tmp/opencode/QEMU-063t

# 047t 面（2 信号；静态档）
python3 tools/testcases/run_libc_test_user_suite.py --link-mode static --timeout 300 \
  --filter 'flockfile-list|setenv-oom' --work-dir /tmp/opencode/QEMU-063t-libc

# 050t 追加面（lua 宿主信号 + lemon guest 信号；lua 取表值 840 s，两档整批约 25–35 min）
python3 tools/testcases/run_llvm_ts_user.py --link-mode both --jobs 1 --timeout 300 \
  --only 'lua$' --only 'lemon$' --work-dir /tmp/opencode/QEMU-063t

# 单例现场（示例：把 host 信号落盘）
.work/build/qemu/qemu-dadao -strace -d in_asm,cpu <elf> <args> 2> /tmp/opencode/QEMU-063t/x.log
```

> 复现口径：**基址 = lld 默认**（不得 `-T dadao.lds`，`ISS-247`）；`timeout 124` ⇒ `blocked`，不得记 pass/fail（`ISS-248`）。

## 验收标准

1. **逐例诊断表**（9 行，每行必填）：宿主信号号 / `si_code` / `si_addr`（或 timeout 的最后一处 guest `PC` 与最后一条输出）、guest 侧落点（`MC_PC` + 反汇编附近指令）、归属判断（qemu / LLVM 后端 / musl / 语料）、处置（修 / 归因）。
2. **时间盒**：完成区写实际诊断耗时；**>2 h 必须停**，其后只做「归因落纸 + 现场归档」，不得继续试错。
3. **修的情形**：该例修后**两档** `pass`（`048t` 按参考 oracle / exit-only；`047t` 按用例退出码），且 `048t blocked 27 → 27−k`、`047t 静态 blocked 25 → 25−m`（k/m = 实际修复数，**现场派生不写死**）；**无回归**（逐例 JSON diff）。
4. **归因的情形**：不得改标 `pass`；`blocked` 保留 + `reason` 指向新证据；`ISS-255`/`ISS-266` notes 追加「归因结论 + 证据路径 + 仍待修的面」，`status` **保持 `open`**。
5. **`unix-smail` 单列**：必须给出「卡在哪一 guest 系统调用 / 宿主侧等待点」（`-strace` 末行 + 宿主 `strace`/`/proc/<pid>/stack` 之一）；若判定为上游程序语义（例如等待不存在的 DNS/交互输入）⇒ 归**语料/驱动口径**并转 `TESTCASES-050t` 处置，附证据。
6. **可达 FAIL（≥2）**：注入须能让判据真红（例如把已知 `pass` 的冒烟例改成超时、或篡改诊断表字段使一致性断言失败）⇒ `cp`+md5 还原 ⇒ 回绿（**禁** `git checkout`/`restore`/`stash`）。
7. **门控（各留自身 rc）**：`check-patch-tree`、`check-component-changelog`、`check-qemu-smoke`（L2 代表集，**按需单跑，不与其它测试集并发**）、`make check`(L1)；证据脚本自身 rc。
8. **构建前置申报**：改 `components/qemu/**` ⇒ 需 `make build-qemu`（+ `install-host` 后安装根复核）；**启动前申报预计耗时**、`JOBS=8`、**不并发**（`ISS-229`/`ISS-210`）。

## 不做

- **不**把超时从 300 s 直接抬到很大来「消除」卡死（超时抬升属 `TESTCASES-050t` 且只对「真慢」例；本册卡死例必须诊断）。
- **不**改语料/期望值/`known-fail` 依据表；**不**改 `spec/`、`.tao/contracts/`、`contracts/`。
- **不**做线程/`__clone`（`ISS-252`，`M9`）、TLS（`M9`）、`ISS-253`（`wchar_t`）、`ISS-254`（`INFRA-089t`）。
- **不**顺带重构 `linux-user` 其它面；`ISS-257`（`pthread_create-oom` flake）只作同族参考。

## 硬约束

1. 临时目录 `/tmp/opencode/QEMU-063t/`；workdir = 仓库根、相对路径；禁出界 `cd`；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. 完成区与真实输出逐条对齐；留证捕被检命令自身退出码；长日志落 `.work/log/qemu/`（`timeout` 的 `124` 判 FAIL/超时，不得当 pass）。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；**时间盒到点即归因留问**（属「需用户语义裁定」之外的可自行处置面，但**不得**扩大试错）。
6. 用户裁定须把**原话**写入本任务书；本册已落：「**同意**」（= 6 个宿主信号**追 1–2 小时**、定位不了就登记归因）。
7. 补丁导出纪律：`/tmp` 写入、非空 blob、`check-patch-tree` 全绿。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
