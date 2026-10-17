# INTEG-036m: M8 integ 模块里程碑核验（无内核 Linux 用户态栈）

**模块**：integ
**项目里程碑**：M8
**状态**：待开始
**目标**：核验 **M8 = 无内核的 Linux 用户态栈**（`ADR-0025`）：musl（静态 → 动态）+ QEMU user-mode（`P1`→`P3`），并把「与 RISC-V + musl 的 golden 对照」留在 `P4`（`ADR-0025 D7`）。
**关联任务**：见下「阶段—任务—门控」表（逐行给真实任务号）；核验载体 = 本册。

> **补记说明（2026-10-17）**：本册为**事后补齐**，非开工时建立。M8 自 2026-10-13 起推进时未立 `INTEG-036m`；本笔按 `.opencode/agents/architect.md` 的 `m` 册格式补记，**不伪造当时记录**（当时的计划/裁定仍以 `milestones.md`「M8 规划区」与各任务书为准）。

## 目标与判据

1. **目标** = 无内核 Linux 用户态栈：musl 静态（`P1`）→ 动态（`P2`）→ `qemu-user` 两档跑（`P3`）。
2. **达成判据** ① **静态档 + 动态档都能编能跑**（`build-musl*` rc=0 + `qemu-dadao` 两档 E2E）；② 三套大型测试（embench-iot / libc-test / llvm-test-suite）两档跑通并**如实分类**（pass / fail / known-fail / blocked>0 ⇒ rc=1 / excluded 逐条 reason）；③ **golden 对照（RISC-V + musl）归 `P4`**（`ADR-0025 D7`）——`P4` 未完 ⇒ **本册不得置 `里程碑`**。

## 阶段—任务—门控

| 阶段 | 任务（真实号） | 门控 / 判据 |
|---|---|---|
| `P0` 契约 | `SPEC-138t`（Linux syscall 映射）、`SPEC-139t`（动态链接 ABI）、`SPEC-140t`（musl TLS 硬依赖查证） | L1 `make check`（`check-spec-drift` / `check-contracts-dir` / `check-contract-relocs`） |
| `P1` 静态 | `INFRA-076t`（musl 1.2.6 取源锁定）、`INFRA-082t`（静态最小集）、`QEMU-060t`（`dadao-m1` syscall 服务回退）、`TESTCASES-045t`（P1 能力边界度量） | L1 + `make build-musl` rc=0；运行验证由 `P3` 承接 |
| `P2` 动态（生产者侧） | `LLVM-094t`（PIC/LLD 动态）、`LLVM-095t`（`PCREL_HI/LO` + PLT）、`LLVM-096t`（A1 四项阻塞）、`LLVM-097t`（`bswap`）、`LLVM-098t`（`-fPIC` `.rodata`）、`LLVM-099t`（`rotl`/`rotr`）、`LLVM-101t`（可变参聚合 `union semun` + `shmat()` 指针返回 bank；`047t` 静态档暴露）、`SPEC-145t`（`rela.si`）、`QEMU-061t`（`rela.si` 解码/语义） | L1 `check-patch-tree` / `check-instrinfo` / `check-contract-relocs` + **单跑** `install-host`（`ISS-210`、`ISS-229` 串行） |
| `P2` 动态（消费/构建） | `INFRA-085t`（`libc.so` + 动态可执行）、`INFRA-079t`（compiler-rt builtins，**全量**；排期见下） | `make build-musl-shared` rc=0 + `PT_INTERP` / `DT_NEEDED` 静态可核 |
| `P3` 运行 | `QEMU-062t`（`qemu-dadao` 静态 + 动态两档 E2E） | L2 `check-modules` + L3 `check-full`（`check-qemu-semantics`） |
| 测试面 | `TESTCASES-044t` / `LLVM-093t`（语料取源锁定）、`TESTCASES-046t` / `TESTCASES-047t` / `TESTCASES-048t`（两档跑）、`INFRA-087t`（`strptime %s` 语义归属与分类订正；`047t` 静态档暴露） | runner 自身 rc（`blocked>0 ⇒ rc=1`，`ISS-248` 口径）；**不入 L1/L2/L3**（curated，`Process-07 §3`）；**`046t` = ✅ 静态 38/38 + 动态 38/38**（2026-10-17；动态档复跑于 `ISS-258` 处置后，driver rc=0）；**`047t` = ✅ 两档 `fail=0`**（静态=安装根，2026-10-17 第 4 轮：`pass 303 / fail 0 / known-fail 9 / blocked 25`，excluded 30；`known-fail 9` = TLS 3（`ISS-246`）+ `strptime` 1（`ISS-251`）+ `long double` 5（`ADR-0030`→`M9`）；`blocked 25` = `ISS-252`/`ISS-253`/`ISS-254`/`ISS-255` + compiler-rt；`pthread_create-oom` 计数抖动 = `ISS-257`）；**动态档 ✅（2026-10-17 第 5 轮）= `pass 298 / fail 0 / known-fail 8 / blocked 31`**（excluded 30；`blocked 31` = `ISS-252` 19 + `ISS-253`/`ISS-254`/`ISS-255` 各 1 + COPY 8（`ADR-0026 D7②`，待裁定 `ISS-259`）+ `pleval` 1（上游不构建，同上）） |
| `P4` golden 对照 | **未立册**（`ADR-0025 D7`：RISC-V + musl 跑同程序作对照） | 立册后另行定义；**未完 ⇒ 不置 `里程碑`** |

## 已知限制 / 后置

- **`long double` = IEEE binary128 ⇒ `M9`**（`ADR-0030` **`Accepted`**，用户 2026-10-17 逐条确认；`D1` = binary128 / `D2` = RF 双槽 = **与 RISC-V64 一致** / `D7` = 排 `M9`）；`M8` 判据**不含** `ISS-250` 的 5 例（`math/{acoshl,asinhl,erfcl,lgammal,tgammal}`），由 `M9` 覆盖。
- **`LLVM-100t`（`__thread` 用户变量 TLS codegen）⇒ `M9`**（用户 2026-10-17 原话「**tls 可以推到 M9**」）；`M8` 不要求 `dlopen`/模块级 TLS。
- **线程面 `__clone`**（musl 端口无 `clone.s`）⇒ **`M9`**；`TESTCASES-047t` 静态档 20 例 `blocked` 按此归类（`ISS-252`）。
- **`INFRA-079t` = 全量** compiler-rt builtins（7 类接入点 + 独立库 + 移除 picolibc vendored 副本 + driver/`-print-libgcc-file-name` 落点）；**排期 = 先于 `M8` 收尾**（2026-10-17 用户原话「**既然要做，就做好；所以，要做，就把compiler-rt都做完，该调整任务链就调整任务链**」⇒ 撤销「只提前 `__muldc3`/`__mulsc3`」的窄化）。
- **其它挂账（不阻断 `M8`）**：`ISS-232`（`--show-encoding` 低半显示断言）、`ISS-235`（L3 载体 3/16 册）、`ISS-243`（i32 窄返回值 canonical 化）、`ISS-245`（静态 PIE `_DYNAMIC`）、`ISS-247`（`dadao.lds` 基址超宿主 VA）；`ISS-249` **已 `closed`**（argmask 收口）；`ISS-250`–`ISS-255`（`TESTCASES-047t` 余下失败 / `blocked` 归类）+ `ISS-256`（`ipc_sem`/`ipc_shm` 两个 codegen 缺陷 ⇒ `LLVM-101t`；`ISS-251` ⇒ `INFRA-087t`）+ `ISS-257`（`pthread_create-oom` 的 `RLIMIT_AS` 直通宿主 flake）。

## 核验

- **关联任务是否均已 `已验证`**：**否** —— `LLVM-096t`–`LLVM-099t`、`INFRA-079t`、`SPEC-141t`、`TESTCASES-046t`/`047t`/`048t` 仍非终态 ⇒ **不置 `里程碑`**。
- **`P1`/`P2`/`P3` 能力**：`QEMU-062t` 静态 + 动态两档 E2E **已通**（`已验证`）；`INFRA-085t` 交付 A1/B1/C1 + `D1` 部分（`已验证`），`D2` 推迟 `M9+`。
- **三套测试两档进度（现场）**：`TESTCASES-046t` 静态 √ 38/38 / 动态 √ 38/38（2026-10-17，`ISS-258` 处置后复跑）；`TESTCASES-047t` 静态 √ **`fail=0`**（第 4 轮 = 安装根：`pass=303 / fail=0 / known-fail=9 / blocked=25 / excluded=30`；`known-fail 9` 与 `blocked 25` 归属见上「测试面」行；第 2 轮 `301/8` 的收口链见任务书）/ 动态 √ `fail=0`（第 5 轮 = 安装根：`pass=298 / fail=0 / known-fail=8 / blocked=31 / excluded=30`；COPY 8 / `pleval` 1 见任务书第 5 轮；任务级 `状态` 本笔未改，仍 `待开始`）；`TESTCASES-048t` 未跑。
- **`P4` golden 对照**：**未开工、未立册** ⇒ **`M8` 未达成**。
- **门控**：本批跑 `make check`(L1) / `check-patch-tree` / `check-contracts-pending` / `check-contract-relocs` / `check-milestone` 并如实记录；**L2/L3 本笔未跑**（`ISS-229` 并发禁令）。
