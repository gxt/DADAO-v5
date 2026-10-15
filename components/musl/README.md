# musl 组件（musl）

DADAO 的 Linux 用户态 C 库底座（**M8**：无内核的 Linux 用户态栈，`ADR-0025 D2/D6`）。上游基线与补丁序列由 `manifests/components.lock.toml` 锁定（`shallow_ref = "v1.2.6"`，精确 commit `9fa28ece…`）；工作树由 `make fetch` + `make apply-series` 在 `.work/source/musl` 建立（浅裸镜像 `.cache/musl.git`）。

## 补丁集

- 形态：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁），清单见 `series`。
- 规范：`docs/Process-01-组件补丁组织与构建编排.md`；上位决策：`ADR-0005`（多源锁）、`ADR-0006`（浅裸镜像）、`ADR-0025`（M8 路线：`P1` 静态全在 musl 上）。
- 范围（`INFRA-082t` 阶段 A2/A3）：**静态最小集**——`arch/dadao/**`（12 文件）+ `src/setjmp/dadao/**` + `src/thread/dadao/__set_thread_area.s` + `configure`（唯一被改的上游文件：加 `dadao*) ARCH=dadao` 分支）。

### 移植要点

- **平台事实**：64 位、**大端**（`contract-abi.md §1.7`；`bits/alltypes.h.in` 的 `__BYTE_ORDER 4321`）、`long double == double`（clang 预定义 `__SIZEOF_LONG_DOUBLE__=8`）、LP64。号表**沿用 RISC-V Linux 编号**（`contract-syscall.md §1`）：`bits/syscall.h.in` 与锁定的 RISC-V 号表**逐名同值**（314 个共同名 0 冲突，现场复算）。
- **syscall stub**（`arch/dadao/syscall_arch.h`，真源 = `contract-syscall.md`）：号在 **`rd15`**、发起 `trap cfx_umon, 0`（`immu18 = 0` = `SBI_UMON_SYSCALL`）、返回 **`rd8`**、**errno = `rd8` 负值** ⇒ musl `__syscall_ret()` **零改**。参数**按类型分 bank**：整数参数 `rd16+n`、指针参数 `rb16+n`（各自独立计数，`§3` 的 `read` 例）。musl 交给 stub 的是 `long`，指针性只剩「号」可查 ⇒ 用 `__dadao_argmask()` 把「哪个槽位是指针」按号恢复；该表必须与**服务方**（`dadao-m1` 的 `umon` 服务，`INFRA-082t` 阶段 A1）逐槽一致，**加服务即须同步加表项**。
- **TLS/TP**（`arch/dadao/pthread_arch.h` + `src/thread/dadao/__set_thread_area.s`）：**TP = `rb3`**（`contract-abi.md §1.2`）；`__get_tp()` 用 `rb2rd` 读；`__set_thread_area` 是纯寄存器写（`rb2rb {rb3}, {rb16}`，返回 0）。模型取 `TLS_ABOVE_TP` + `GAP_ABOVE_TP 0` + `TP_OFFSET 0` + `DTP_OFFSET 0` + `TPOFF_K 0`（`contract-dynlink.md §7` 把方向/偏置留给 arch 定值：此处取「无偏置」口径，与 `§4.3` 的 `DTPOFF(sym) + A` / `TPOFF(sym) + A` 公式一致）。
- **crt**（`arch/dadao/crt_arch.h`）：`crt1.c` 与 `ldso/dlstart.c` 共用同一份入口 asm（`START` / `SHARED` 分支）。**裸机没有内核造的初始栈**（`ADR-0004 D6.5`）⇒ 静态入口把 `argc/argv/envp/auxv` 帧**静态构造**在 `.data`，只放 `__init_libc` 真正会读的项（`AT_PAGESZ`/`AT_UID`·`EUID`·`GID`·`EGID`/`AT_HWCAP`/`AT_EXECFN`），不存在的项按 0 ⇒ `__init_libc` 在 poll/open 之前返回，启动期不需要任何服务。
- **setjmp/longjmp**（`src/setjmp/dadao/{setjmp.S,longjmp.S}`）：真实现——保存/恢复 `ra0–ra63`（RegRAS 可软件读写，`contract-isa.md §3.3`）+ `rb1` + callee-saved `rd32–63`/`rb32–63`/`rf32–63`（`contract-abi.md §4.5`，共 **161** octa，见 `bits/setjmp.h`）。限制与 picolibc 端口（`INFRA-068t`）相同：仅 `MRPTR == 0` 精确。
- **原子**（`arch/dadao/atomic_arch.h`）：机器**没有**可用原子——LR-SC 与 `fence` 属 `scope: excluded`（`contract-isa.md §14`，QEMU 侧 `trans_mem.c.inc`/`trans_ctrl.c.inc` 均为 ILLI 桩）⇒ 只能给出**单线程**语义的 `a_cas`/`a_cas_p`/编译器屏障。`P1` 是静态单线程子集（`ADR-0025 D2`），且 `__clone` 由通用 `src/thread/clone.c` 返回 `-ENOSYS`（线程显式失败）；开线程前必须换真原子。
- **`GETFUNCSYM`**（`arch/dadao/reloc.h`）：musl 默认实现用**内存操作数** inline asm，而 DADAO 后端对任何 `m` 操作数都在 ISel 崩（最小复现 `asm("" : "+m"(x))`），而 `ldso/dlstart.c` 是全树唯一一处 ⇒ 按 musl 给 arch 留的口子（12 个 arch 都这么干）改写成「算出符号地址、经输出寄存器交出」。当前给的是**链接期绝对地址**（静态成立）；动态路径（`P2`）须改为基于加载基址。
- **后端缺口过滤**（`arch/dadao/arch.mak`）：13 个源文件因后端缺 `rotl`/`rotr`、`bswap`、`dynamic_stackalloc`（alloca/VLA）而**无法编译**（`Cannot select`），列为显式排除并由 `$(info …)` 每次构建打印 ⇒ 相关符号/能力**链接期显式失败**，不静默：`crypt()`/`crypt_r()`（`crypt_r.o` 引用被排除的 `__crypt_sha512`）、`exec*` 族、`getcwd`、`sigdelset`、`.mo` 本地化（`__mo_lookup`/`dcngettext`）、`getgrouplist`/`getgr_a`、`nscd_query`、resolver（`res_msend`）。做法与 picolibc 端口的后端受阻源过滤同源（`INFRA-066t`/`ISS-193`）。
- **inline asm 口径（重要）**：clang 的 DADAO target **不能**把 `%N` 操作数代进 inline asm 模板（代入结果是空串）⇒ 本端口所有 inline asm **只写字面寄存器名**，C 侧用 GCC/clang 的「局部寄存器变量」把同一个物理寄存器绑上（`register … __asm__("rd8")` + `"=r"(x)`），后端会正确打印该寄存器。

### 已知边界（`P1` 静态最小集之外；均显式失败或已登记）

动态链接 / `ldso`（`P2`）、`QEMU linux-user`（`P3`）、线程（`__clone` = `-ENOSYS`）、信号（无 DADAO 信号帧 ABI；`bits/signal.h` 的 `mcontext_t` 仅够编译，标 `[OPEN]`）、静态 `__thread`（未提供 `AT_PHDR/PHNUM/PHENT` ⇒ `tls_cnt = 0`；`errno`/TCB 正常）、`sigsetjmp`/`siglongjmp`（未实现 ⇒ 使用即链接失败）、后端受阻源（见上）。

## 构建与验证

```
make fetch apply-series                 # 建工作树 + 应用补丁集
tools/infra/build_musl.py               # configure + make（幂等）+ 链一个静态最小程序并核 ELF
make check-patch-tree                   # 补丁集机械校验（含 musl）
```

`tools/infra/build_musl.py` 用交叉工具链（`.dadao/cross-toolchain/bin`）配置 `--target=dadao-unknown-elf --disable-shared` 并 `make`，产出 `.work/source/musl/lib/{libc.a,crt1.o}`；随后用 `tests/scripts/dadao.lds` 把 `crt1.o` + 最小程序 + `libc.a` 链成静态 `ET_EXEC`，核对 `ELF64 / MSB / machine 0xDA0 / statically linked`。运行（`dadao-m1` E2E）属 `P1` 阶段 B，不在本组件的构建脚本内。
