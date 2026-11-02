# M8 回顾：无内核 Linux 用户态栈（2026-10-13 ~ 2026-10-19）

> **状态**：**项目里程碑 M8 = 达成（2026-10-19）**。本文为收口回顾（结论层）；事实以各任务书、ADR、契约为准，任务清单/流水见同目录 `README.md`。

## 1. 主题与路线

- **主题（`ADR-0025`）**：**无内核的 Linux 用户态栈** = musl（静态 → 动态）+ QEMU user-mode；`P0` 契约 → `P1` 静态 → `P2` 动态 → `P3` qemu-user → `P4`（**不作**）。
- **与 `DADAO-0628` 的差异**：v5 无内核（`D2`）、沿用 RISC-V syscall 号（`D1`，号寄存器 `rd15`）、musl 自带 `ldso`（`D3`）、用户态承担动态/TLS；0628 的真内核路线**不借鉴**，只借工程流程。
- **`P4` 取消（用户 2026-10-18）**：不做 RISC-V 交叉对照；判据改为「两档如实分类 + 失败逐条归因」。`ADR-0025 D7` 只加就地修订注记。

## 2. 交付与能力

- **静态档**：musl 1.2.6 静态最小集（`arch/dadao` + crt + syscall + TLS/TP=`rb3`），`hello`/`exit` E2E。
- **动态档**：`libc.so` + `ld-musl-dadao.so.1` + `PT_INTERP`/`DT_NEEDED`/GNU hash/GOT/PLT；LLD `ET_DYN`、PIC、`aip.si`（原 `rela.si`）配对重定位；driver 转发 `-shared`/`-static`/`-pie`。
- **运行**：`qemu-dadao` user-mode（静态 + 动态两档 E2E、`AT_*` 对账、宿主 syscall 直通、信号/进程宿主兜底）。
- **ABI/后端收口**：变参三游标七字段 `va_list` + callee 快照（`ADR-0031`）；16 B 值 RF 双槽（高半在偶号）；调用点 SP **16 B 对齐**；`rb2` = 帧指针无条件保留；`brind`、f128 libcall、i32 窄返回 canonical 化、vector `SetCC`、`wchar_t` 有符号、注释符 `@@`。
- **`long double` = IEEE binary128**（`ADR-0030`）：musl `bits/float.h` + 前端三宏 + `rf16/17` + `f128` libcall/builtins；`libc-test` 5 个 `_l` 用例两档 pass。
- **compiler-rt builtins**：独立库全量接入（`ADR-0027`），driver 默认链接。

## 3. 三套测试（权威跑，两档）

- **`embench-iot`（`TESTCASES-046t`）**：静态 38/38、动态 38/38。
- **`libc-test`（`TESTCASES-047t`）**：静态 `pass 309 / fail 0 / known-fail 4 / blocked 24`；动态 `312 / 0 / 4 / 21`；`excluded 30`、`total 337`、discovered 367。`known-fail 4` = TLS 3（`ISS-246`）+ `strptime` 1（`ISS-251`）；5 个 binary128 用例已转 pass。
- **`llvm-test-suite`（`TESTCASES-048t`）**：两档逐数相同 `total 220 / pass 201 / fail 3 / known-fail 0 / blocked 16 / excluded 2`（discovered 222）。3 `fail` = `Ptrdist/ft` / `ClamAV` / `obsequi` = 参考输出可移植性（`ISS-265`，用户裁定归 `known-fail`）；`blocked` 逐条有根因（编译/方言、超时、qemu 宿主信号、`re_comp`、`RUNTIME_INIT`、语料 UB）。
- **权威产物**：`.work/tests/authoritative/`（六次跑 × 三件套 + `latest`，`INFRA-093t` 规矩）。

## 4. 门控

- 收口现场：L1 `make check` rc=0；L2 `make check-modules` rc=0；L3 `make check-full` rc=0；`check-patch-tree` **181**。
- 新增/强化的门控与规矩：`check-run-artifacts`（A1–A3）、`check-milestones-fresh`、`check-patch-tree` 补丁计数、`check-spec-readonly`、`check-syscall-abi`、`check-musl-freshness`。

## 5. 决策载体

`ADR-0025`（范围/路线）· `ADR-0026`（动态链接行为）· `ADR-0027`（compiler-rt builtins）· `ADR-0030`（binary128）· `ADR-0031`（变参 ABI）· `ADR-0018 C7/C9 D3`（`rb2` FP、SP 16 B）· `ADR-0019 D10`–`D12`（重定位编号）· `ADR-0029`（`aip.si` 配对）· `ADR-0028` = `Superseded`。

## 6. 未决 / 下一里程碑

- **`M9` 候选**：`__thread` 用户变量 TLS（`LLVM-100t`）、线程 `__clone`（`ISS-252`）、`dlopen` 4 例（`ISS-260`）、`D2` TLS 类动态重定位、`ror`/`rori`（用户 2026-10-17）、`bswap64` 用 `rev.o`。
- **不阻断 M8 的挂账**：`ISS-261`（`llvm-nm`）、`ISS-278`/`282`（日志搬迁与门控小遗留）、`ISS-288`/`289`（stale 证据/进程纪律）、`ISS-265`（`known-fail` 分类迁移）、`ISS-266`/`255`/`257`（qemu 宿主信号族）、`ISS-193`（picolibc 过滤表 stale 1 条）。
- **`SPEC-141t`**（M8 标签、只读预研、未开工）留活；`SPEC-141t` 口径见 `.tao/knowledge/milestones.md`「M9」。

## 7. 教训（指针）

- 进程/构建纪律：共享安装根与构建树**单写者**（`ISS-229`/`ISS-289`）；长链 `setsid nohup` + `XXX_EXIT`。
- 证据脚本随产物长期保留、须能失败；stale 基线需刷新（`ISS-288`）。
- 组件补丁漏项（注释符迁移漏 `components/**`/`tools/**`）由 `check-patch-tree` 补强（`ISS-281`/`ISS-286`）。
