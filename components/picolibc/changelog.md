# Picolibc 组件变更记录

> 粒度：**按任务一条**，追加式。**体例 = 列表式（不用表格）+ 按里程碑分节**：每条 = `- **<日期> <任务号或 —>**`，**摘要另起缩进行** `  - 摘要：<摘要正文，逐字保留>`；原表其余列各占一条缩进行（如 `  - 执行者：engineer`）。节 = `## M<k>`（节序 M1→M2→…），**节内按日期升序**；**新里程碑到来时在文末开新节**（不留空节）。补丁集的生成/应用/校验规范见 `docs/Process-01-组件补丁组织与构建编排.md §10`。

## M7

- **2026-10-11 `INFRA-055t`**
  - 摘要：**组件接入骨架**：`manifests/components.lock.toml` 追加 picolibc 条目（`enabled=true`、精确 commit `2ae376c6cdf4fef90ca2388ecf7a07457fa63cff`、`shallow=true`、`shallow_ref="release-1.8.12"`）；建 `components/picolibc/{README.md,patches,series,changelog}`；首个补丁 = 新增 `dadao/README.md`（占位，**声明无行为**；真移植归 M7）。浅裸镜像 `.cache/picolibc.git` + 工作树 `.work/source/picolibc`（`make fetch`）。

- **2026-10-11 `INFRA-057t`**
  - 摘要：**真移植补丁集 + 构建集成**：占位补丁由真补丁**替代**（删 `dadao/README.md`）。补丁 14 份（计数现场统计）：cross file `scripts/cross-dadao.txt`；machine dir `libc/machine/dadao/{meson.build,machine/meson.build,setjmp.S}`；semihost stub `libos/semihost/machine/dadao/{meson.build,semihost-dadao.S}`；配置 `libc/include/machine/{ieeefp.h,setjmp.h,endian.h}`、`libc/include/sys/cdefs.h`、`libc/string/{fls,flsl,flsll}.c`；`meson.build`（DADAO 源过滤）。构建集成 `make build-picolibc`（`tools/infra/build_picolibc.py`，meson+ninja，幂等，装 `.dadao/dadao-unknown-elf`）+ `make test-picolibc-smoke`（`printf("hi")` 编/链/跑，QEMU semihosting，EXIT=0）。**范围**：LLVM 后端缺口（bitcast/setcc/select_cc/ctlz/cttz/bswap）致 `libm/` 及 ~20 libc 浮点文件暂排除，待 `LLVM-079t`/`080t`。

- **2026-10-12 `INFRA-066t`**
  - 摘要：**恢复 `libm`：删源过滤表 + 最小化**：删 `meson.build` 的**整目录 `libm/` 排除**，把后端受阻源过滤**最小化到 41 条**（由本构建**全部 1120 个编译项逐条重编**得出的精确失败集，`ISS-193` 登记 6 类根因）。重建后 `libc.a` 1,241,616 → **1,686,214 B**，8 符号（`floor`/`ceil`/`trunc`/`round`/`rint`/`nearbyint`/`fmin`/`fmax`）`nm` 全命中（`libm.a` 为上游**空壳**，见 README「移植要点」）。`make test-picolibc-smoke` 增 **libm E2E 阶段**（8 符号真实调用 + C99 语义自检 + 退出码）。**仍不可链接**：`pow`/`hypot`/`j0`/`y0`/复数/`scanf` 族/`memset_s`（`ISS-193`）。

- **2026-10-12 `INFRA-067t`**
  - 摘要：**提供 `__muldc3`/`__mulsc3`（编译器复数乘辅助）**：移植 compiler-rt **单文件**入 `libm/common/`——`muldc3.c`/`mulsc3.c`（函数体逐字未改）取自 `compiler-rt/lib/builtins/`（llvm-project `6dfe1677`/`llvmorg-23.1.1`，**Apache-2.0 WITH LLVM-exception**，文件头标出处+版本+许可），另加支撑头 `compiler_rt_builtins.h`（compiler-rt 内部宏→compiler builtins）；`libm/common/meson.build` 纳入。补丁 **18 份**（现场统计）。`libc.a` 1,799,920 → 1,803,498 B，两符号 `nm` 为 **`T`**；`nm -u` 证明二者无其它 runtime 依赖。全量 test：**pass 197→203 / blocked 16→10 / fail 0 / excluded 22**；解锁 **6**（`test-cacos`/`test-cacosh`/`test-casin`/`test-casinh`/`test-catanh`/`test-complex-funcs`），第 7 条 `test-math-funcs` 现可链接、**移因** `ISS-195`（QEMU 软浮点 2-NaN，基线已有同类）。

- **2026-10-12 `INFRA-068t`**
  - 摘要：**`setjmp`/`longjmp` 真实现（用 RA 存取/块赋值）**：`libc/machine/dadao/setjmp.S` 由「显式失败桩」改为真实现——`setjmp` 用 `st.o ra0` + `stm.o {ra1:ra63}` 保存返回地址栈（`ra0` = RACNT/MRPTR）、`st.o rb1` 保存 SP、`stm.o {rd32:rd63}`/`{rb32:rb63}` 保存 callee-saved（`contract-abi.md §4.5`）；`longjmp` 反向 `ldm.o` 恢复 + `cs.z` 实现 `val==0⇒1`，最后 `ret` 完成 `setjmp` 返回。`machine/setjmp.h` `_JBLEN` 66→**129**。更正桩注释里「ISA 无指令可恢复 RegRAS」的错误陈述，改引 `contract-isa.md §1.3.4`/`SimRISC-01/02`。**限制登记**：仅 `MRPTR==0`（纯 RegRAS）路径；M7 环境实测 `MRPTR=0`。

- **2026-10-12 `INFRA-068t`（返工 1）**
  - 摘要：**补 FP callee-saved 银行 `rf32–rf63`**：`contract-abi.md §4.5` CSR = `rd32–rd63 ∪ rb32–rb63 ∪ rf32–rf63`（`spec/DADAO-21` rf32–rf63 callee saved），原实现漏存漏复 RF 银行 ⇒ C 级实证 FP 局部量跨 `setjmp`/`longjmp` 被中间帧同 bank 覆盖（`expect=4.75 got=3.25`）。`setjmp` 加 `stm.o {rf32:rf63}`、`longjmp` 加 `ldm.o {rf32:rf63}`（RF 形态，`scope:fp`；偏移 1032）；`machine/setjmp.h` `_JBLEN` 129→**161**（= 64(ra)+1(sp)+32(rd)+32(rb)+32(rf)）。全量 test 不回归（`pass 205/fail 0/excluded 22/blocked 8`）。

## M8

- **2026-10-17 `INFRA-079t`**
  - 摘要：**移除 compiler-rt builtins 的 vendored 副本**（`ADR-0027 Consequences 1` / `D5`）：删 `libm/common/{muldc3.c,mulsc3.c,compiler_rt_builtins.h}` 三件源及其 `.patch`，`libm/common/meson.build` 恢复上游 `srcs_common = ['signgam.c']`（该文件的唯一补丁 hunk 即两源插入，故整份 `meson.build.patch` 一并消失）；`series` 18→**14**。`__muldc3`/`__mulsc3` 改由独立 `libclang_rt.builtins.a` 提供；重建后全量四分类 **pass 213 / fail 0 / excluded 22 / blocked 0**（与改前逐项一致）。

- **2026-10-19 `LLVM-109t`（迁移漏项修复，`ISS-281`）**
  - 摘要：**汇编注释符 `;` → `@@`：`semihost-dadao.S` 尾注释收口**。`libos/semihost/machine/dadao/semihost-dadao.S` 的 3 行行尾注释由 `;` 改 `@@`（C 块注释与其它 DADAO `.S` 不动），E1 收敛后重导出该补丁（`series` 14 不变）。实测安装根 clang 汇编 rc=0；本次按派单未重跑 `make build-picolibc`（重建范围限于 musl）。
  - 执行者：engineer

- **2026-10-19 `LLVM-110t`**
  - 摘要：**`_JBLEN` 161→162：`jmp_buf` 增 1 个 octa 保存帧指针 `rb2`**（FP 由 `rb63` 迁回 `rb2` 后 `rb2` 不在 CSR；同 musl 端口）：`libc/include/machine/setjmp.h` `_JBLEN 162` + 布局注释；`libc/machine/dadao/setjmp.S` `setjmp`/`longjmp` 增 `st.o`/`ld.o rb2, [rb16, 1288]`（`rb32:rb63` 批量保存不变，`rb63` 现为普通 callee-saved）。`series` **14 不变**（2 份既有补丁改）。真值：`_Static_assert(_JBLEN==162 && sizeof(jmp_buf)==1296)` 通过；`setjmp.S` 汇编/反汇编含 `[rb16,1288]`；E2E：新编译器 + 旧端口 ⇒ exit 1，新端口 ⇒ exit 0。**注意**：`make build-picolibc` 全量重建在 `strtold.c` 撞既有后端缺口（`uint_to_fp i128→f128` 未注册 libcall，见 `ISS-193` 同类），与本笔无关，见 `LLVM-110t` 完成区。
  - 执行者：engineer

- **2026-10-19 `LLVM-115t`**
  - 摘要：**`ld128` 数学引擎 `__atold_engine` 接入**（`ISS-287`，`ISS-193` (f) 落点）：binary128 落地后 `atold_engine.c` 已可编译（单源 `-O2`/构建默认 flags 实测 rc=0），故只从 `meson.build` 的 `_dadao_backend_blocked` 删该 1 条（过滤表 2→**1**），并同步注释；picolibc 上游源零改动，`series` **14 不变**（`meson.build.patch` 一份既有补丁改）。`libc.a` 中 `__atold_engine` 由 `U` 转 `T`，`strtold`/`wcstold` 链接解阻。
  - 执行者：engineer

## M9

- **2026-10-20 `LLVM-118t`**
  - 摘要：**`_dadao_backend_blocked` 清零（1 → 0）**（`ISS-193` 收口；上游源零改动）：按「全量重编」口径现场重枚举 —— 在 `/tmp` 源副本把过滤表置空后 `meson setup` 得**全部 1120 个编译项**，逐条真实 `-c` 重编 **0 条失败**（`non_ok=0`），故删最后一条 `hash_page.c`（`ISS-193` (c) i64 `bswap`，早由 `LLVM-097t` 的 `Expand` 收口）并同步注释；过滤机制保留（`_dadao_backend_blocked = []`，供未来缺口按同一格式登记）。`series` **14 不变**（`meson.build.patch` 一份既有补丁改）。**真值**：`make build-picolibc` rc=0，`libc.a` 2,028,044 → **2,041,338 B**；`llvm-nm` 中 `__hash_open`/`__delpair`/`__addel`/`__get_page`/`__put_page`/`__ibitmap`/`__split_page`/`__add_ovflpage`/`__free_ovflpage` 等由 `U` 转 **`T`**（修前 `dbm_open` 链接失败于 `undefined symbol: __delpair` 等 9 条；修后链接 rc=0、运行 guest exit 0）。**未跑**：`install-host`/L2/L3（按派单；picolibc 定点测试 `--only` 7/7 pass）。
  - 执行者：engineer
