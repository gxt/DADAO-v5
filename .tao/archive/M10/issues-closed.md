# M10 阶段已关闭 Issue（2026-10-25 ~ 2026-11-01）

> **来源**：M10 归档（2026-11-01）从 `.tao/knowledge/issues.yaml` 提取全部 `closed` 项（`Process-04 §4.4/§7`）。
> **判据**：`resolved_by` 指向的任务提交日 / 实际关闭提交日 **≤ M10 达成日 2026-11-01**；逐条按 `git log --all --grep <id>` 取关闭提交（下表「关闭（日期/提交）」列）。
> **计数**：本文件 **17 条**（M10 期关闭全集；提取后活台账 `issues.yaml` 为空 = `0 open / 0 closed`），数量以本表实际行为准。
> **边界说明**：`ISS-223`/`ISS-305`/`ISS-333` 的 `resolved_by` 字段指向登记期任务（`INFRA-085t`/`LLVM-130t`/`INFRA-107t`），实际关闭提交分别为 `522acca9`/`8d582f9d`（2026-10-25），按「实际关闭日」计入 M10；早期（M1–M9 阶段）关闭项已在各里程碑归档，不在本表。

| id | scope | resolved_by | 关闭（日期/提交） | title |
| --- | --- | --- | --- | --- |
| ISS-098 | [testcases, qemu] | TESTCASES-063t | 2026-10-26 `69b8d240` | harness 对 ret 语义用例的 pre-existing 失败（ctrl-ret[0..3] 0x01、ctrl-call[5] loader 宽度推导） |
| ISS-223 | [infra] | INFRA-085t | 2026-10-25 `522acca9` | 【P3】musl 移植**显式排除 13 个源文件**（`arch/dadao/arch.mak`）⇒ `crypt()`/`crypt_r()`、`exec*` 族、`getcwd`、`sigdelset`、`.mo` 本地化、`getgr*`、resolver 在**链接期显式失败**（不静默） |
| ISS-232 | [llvm] | LLVM-132t | 2026-10-25 `8d582f9d` | 【P3】`llvm-mc --show-encoding` 对低半 `%pcrel_lo`（`rbha ≥ 4`）命中上游断言 ⇒ SIGABRT（rc=134）；**仅显示模式**（`-filetype=obj` 不受影响）；修法触及被 `check_mc` A7 与契约 §2.2 钉住的 fixup 元数据表 ⇒ **须裁定** |
| ISS-247 | [qemu] | TESTCASES-046t/TESTCASES-047t | 2026-10-25 `6af69417` | 【P2】`qemu-user`（`qemu-dadao`）无法装载按 `dadao.lds` 基址（`0xFC00_0000_0000`）链接的静态 ELF（47 位宿主 VA ⇒ `Unable to find a guest_base`）⇒ 静态/动态测试需在 lld 默认基址链接 |
| ISS-255 | [qemu] | TESTCASES-068t | 2026-10-27 `c39e6faa` | 【P3】`qemu-dadao` 上两条 `libc-test` 回归用例以宿主 `SIGBUS`/`SIGTRAP` 终止（`regression/flockfile-list`、`regression/setenv-oom`）⇒ 归 qemu 面诊断 |
| ISS-257 | [qemu] | TESTCASES-068t | 2026-10-27 `c39e6faa` | 【P3】`libc-test` 静态档 `regression/pthread_create-oom` 不稳定：一次记 `pass`、其后全 `blocked`（guest `setrlimit(RLIMIT_AS)` 直通宿主 ⇒ qemu 侧分配失败 / 宿主 `SIGTRAP`；与 `ISS-255` 同类） |
| ISS-266 | [qemu] | TESTCASES-069t | 2026-10-27 `7e5ef5c1` | 【P3】`qemu-dadao` 在 4 个 `llvm-test-suite` 程序上以**宿主 SIGSEGV** 终止（SPASS / consumer-typeset / 8b10b / dbms）⇒ 归 qemu-user 面诊断 |
| ISS-303 | [llvm] | INFRA-108t | 2026-10-26 `46a953e2` | 【P2】`-static-pie` 无法用 musl `libc.a` 链接：归档成员非 PIC ⇒ lld 逐条拒绝 `R_DADAO_ABS48`；仓库**未提供 PIC 版 `libc.a`** |
| ISS-304 | [testcases] | TESTCASES-064t | 2026-10-26 `348ef281` | 【P2】picolibc `test-printf`/`test-printf-int` 的 `%p` 用例失败（serial 277/278：期望 `0x39`、实得 `0x8`/`0x3`）——期望值或格式实现待判 |
| ISS-305 | [llvm] | LLVM-130t | 2026-10-25 `522acca9` | 【P2】`-g` 下 DADAO 汇编器报 `relocatable operand in a 1/2/4-byte data field`（48-bit 地址装不进 DWARF 的 4 字节重定位） |
| ISS-333 | [spec, infra] | INFRA-107t | 2026-10-25 `8d582f9d` | 【P3】`gen_spec_archive --verify` 对 `SimRISC-0.5.3` 报 PROVENANCE 缺版本组合 sha 与逐文件表（L1 门控不查此细节） |
| ISS-334 | [spec] | SPEC-177t | 2026-10-26 `88793a92` | 【P3】semihosting 新区间 0x3FF00–0x3FFFF 与 SBI 保留值 0x3FFFF 冲突（ADR-0038 D3；已裁定删除保留值） |
| ISS-335 | [testcases, spec] | TESTCASES-070t | 2026-10-27 `68500c34` | 【P3】`generate_rev_vectors.py --check` 红：62 例 `spec_cite` 陈旧、`rev` 向量未进门控 |
| ISS-336 | [testcases, llvm] | TESTCASES-070t | 2026-10-26 `b3f24298` | 【P2】`make test-m6` 红：`diff_ir_lli` 2 个未分类 `.ll`（`cmp-u-branch.ll`/`code-model-large.ll`） |
| ISS-337 | [docs, spec] | INFRA-110t | 2026-10-26 `50e7b298` | 【P3】semihosting 旧口径文档残留（README M5 历史、DDLN DD/TT-D002、Machine-00 Draft、audits 快照） |
| ISS-338 | [testcases] | TESTCASES-078t | 2026-10-27 `c41e4e57` | 【P3】SPASS 修掉 UB 强转后 DADAO 输出 == 宿主 gcc，但仍 ≠ 上游参考 md5（参考方差） |
| ISS-339 | [testcases, infra] | TESTCASES-079t | 2026-10-27 `32f4b609` | 【P3】consumer-typeset：语料未查 catopen 失败 + musl catclose(-1) 无守卫（glibc 返回 EBADF） |
