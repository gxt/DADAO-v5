# Picolibc 组件（picolibc）

DADAO 的 C 库组件（**M7 test 重心**：picolibc 自带 test 套件）。上游基线与补丁序列由 `manifests/components.lock.toml` 锁定（`shallow_ref = "1.8.12"`，精确 commit `2ae376c6…`）；工作树由 `make fetch` + `make apply-series` 在 `.work/source/picolibc` 建立（**浅裸镜像** `.cache/picolibc.git`）。

## 补丁集

- 形态：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁），清单见 `series`。
- 规范：`docs/Process-01-组件补丁组织与构建编排.md`；上位决策：`ADR-0005`（多源锁）、`ADR-0006`（浅裸镜像）、`adr-0023`（picolibc 上游）。
- 现状（`INFRA-057t`）：**真移植**——cross file（`scripts/cross-dadao.txt`）、machine/board 目录（`libc/machine/dadao/**`）、semihosting syscall stub（`libos/semihost/machine/dadao/semihost-dadao.S` + 复用 `libos/semihost/common/` 的 25 服务客户端）、大端/`jmp_buf`/位操作配置（`libc/include/machine/{ieeefp,setjmp,endian}.h`、`libc/include/sys/cdefs.h`、`libc/string/fls*.c`）。

### 移植要点

- **cross file**：`scripts/cross-dadao.txt`（meson `--cross-file`）。目标 `dadao-unknown-elf`，大端，`long double`=f64（clang 预定义 `__SIZEOF_LONG_DOUBLE__=8`）。
- **machine 目录**：`libc/machine/dadao/`（meson 以 `cpu_family` 选择；`machine/` 头目录；`setjmp.S`）。`setjmp/longjmp` 是**真实现**（`INFRA-068t`，`INFRA-068t` 返工 1 补 RF）：DADAO 可由软件读写返回地址栈（`ra0`–`ra63`，见 `contract-isa.md §1.3.4`），故 `setjmp` 保存 `ra0..ra63` + `rsp` + callee-saved 三个块（`rd32–rd63`/`rb32–rb63`/`rf32–rf63`，后二者见 `contract-abi.md §4.5` CSR），`longjmp` 反向恢复后执行 `ret` 完成 `setjmp` 返回。FP 块（`rf32–rf63`）用 `stm.o`/`ldm.o` 的 RF 形态一指令搬运。唯一限制：仅 `MRPTR == 0`（纯 RegRAS，≤63 深度）路径（`MRPTR != 0` 时 MemRAS 内容未随 `jmp_buf` 保存）。
- **syscall stub**：`libos/semihost/machine/dadao/semihost-dadao.S` 提供 `sys_semihost(op,param)`（`rd2rb` 把参数块指针送入 `rb16`，`trap cfx_umon, 0x30000`，结果在 `rd8`）；picolibc 通用半托管客户端据此实现 `write`→`SYS_WRITE(0x05)`、`_exit`→`SYS_EXIT(0x18)`、`sbrk`→`__heap_*`（`libos/fallback/sbrk.c`）。服务号口径见 `.tao/contracts/contract-semihosting.md`。
- **大端**：clang 不为 `dadao` 预定义 `__FLOAT_WORD_ORDER__`，故在 `libc/include/machine/ieeefp.h` 显式 `__IEEE_BIG_ENDIAN`。
- **`libm.a` 是空壳，数学符号在 `libc.a`（上游设计）**：picolibc 自 1.7 起把 libc/libm **合并为单一库**（上游 README「Picolibc version 1.7 §1」），`libm.a`/`libg.a`/`libnosys.a` 由 `empty-libs/meson.build` 生成**空库**以兼容 `-lm` 链接行。故**核对数学符号要查 `libc.a`**（`nm`），`libm.a` 只有 `empty.c.o` 的 876 B 空壳。
- **compiler-rt 复数乘辅助（`ISS-196`）**：DADAO 工具链不带 compiler-rt/libgcc builtins，而 clang 对 C `_Complex` 乘法生成的 `__muldc3`/`__mulsc3` 是编译器辅助（缩放复乘，语义 ≠ 普通复乘）⇒ `libm/common/{muldc3,mulsc3}.c` **逐字移植** compiler-rt（`compiler_rt_builtins.h` 把其内部宏映射到 compiler builtins，算法未改）编入 `libc.a`。

### 当前移植范围（`INFRA-066t`）

`LLVM-079t`（P0）/ `LLVM-080t`（P1）收口后，`INFRA-066t` **删除**了 `meson.build` 里的**整目录 `libm/` 排除**，并把后端受阻源过滤**最小化到 41 条**——该 41 条由「把本构建的**全部 1120 个编译项逐条重编**（全量、非抽样）」精确得出（条目 / 失败签名 / 根因见 `ISS-193`）。数学库主体（f64 三角 / 指数 / 对数 / 取整 / `fmin`-`fmax`）因此并入 `libc.a`，`nm` 复核 8 符号全命中。**仍不可链接**：`pow`/`hypot`/`j0`/`y0`/复数函数/`scanf` 族/`memset_s`（`ISS-193` 六类根因——最大类是缺 FP 谓词 `SETO`/`SETUO`/`SETUNO` 的 lowering，占 30/41）。

## 构建与验证

```
make fetch apply-series     # 建工作树 + 应用补丁集
make install-host           # 需要 install-root clang
make build-picolibc         # 编 picolibc 并装到 .dadao/dadao-unknown-elf（幂等）
make test-picolibc-smoke    # 最小 E2E：printf("hi") + libm 8 符号，编/链/跑，QEMU semihosting
make check                  # 含 check-patch-tree（9 断言）+ check-index-blobs
```

`test-picolibc-smoke` 用 `tests/scripts/{codegen_crt0.s,dadao.lds}`（v5 ELF 直载路径）链接；`picolibc_noflash.ld` 是单 RAM 目标的正解（`picolibc.ld` 的 flash/ram 段在本目标同址重叠、不可用）。
