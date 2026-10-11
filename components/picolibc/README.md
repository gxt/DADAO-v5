# Picolibc 组件（picolibc）

DADAO 的 C 库组件（**M7 test 重心**：picolibc 自带 test 套件）。上游基线与补丁序列由 `manifests/components.lock.toml` 锁定（`shallow_ref = "1.8.12"`，精确 commit `2ae376c6…`）；工作树由 `make fetch` + `make apply-series` 在 `.work/source/picolibc` 建立（**浅裸镜像** `.cache/picolibc.git`）。

## 补丁集

- 形态：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁），清单见 `series`。
- 规范：`docs/Process-01-组件补丁组织与构建编排.md`；上位决策：`ADR-0005`（多源锁）、`ADR-0006`（浅裸镜像）、`adr-0023`（picolibc 上游）。
- 现状（`INFRA-057t`）：**真移植**——cross file（`scripts/cross-dadao.txt`）、machine/board 目录（`libc/machine/dadao/**`）、semihosting syscall stub（`libos/semihost/machine/dadao/semihost-dadao.S` + 复用 `libos/semihost/common/` 的 25 服务客户端）、大端/`jmp_buf`/位操作配置（`libc/include/machine/{ieeefp,setjmp,endian}.h`、`libc/include/sys/cdefs.h`、`libc/string/fls*.c`）。

### 移植要点

- **cross file**：`scripts/cross-dadao.txt`（meson `--cross-file`）。目标 `dadao-unknown-elf`，大端，`long double`=f64（clang 预定义 `__SIZEOF_LONG_DOUBLE__=8`）。
- **machine 目录**：`libc/machine/dadao/`（meson 以 `cpu_family` 选择；`machine/` 头目录；`setjmp.S`）。`setjmp/longjmp` 因 DADAO RegRAS 深度无法从软件修复，**显式失败**（`abort`），见 `setjmp.S` 注释。
- **syscall stub**：`libos/semihost/machine/dadao/semihost-dadao.S` 提供 `sys_semihost(op,param)`（`rd2rb` 把参数块指针送入 `rb16`，`trap cfx_umon, 0x30000`，结果在 `rd8`）；picolibc 通用半托管客户端据此实现 `write`→`SYS_WRITE(0x05)`、`_exit`→`SYS_EXIT(0x18)`、`sbrk`→`__heap_*`（`libos/fallback/sbrk.c`）。服务号口径见 `.tao/knowledge/contract-semihosting.md`。
- **大端**：clang 不为 `dadao` 预定义 `__FLOAT_WORD_ORDER__`，故在 `libc/include/machine/ieeefp.h` 显式 `__IEEE_BIG_ENDIAN`。

### 当前移植范围（`INFRA-057t`）

DADAO LLVM 后端尚不能 select 部分 DAG 节点（`f64/i64 bitcast`、FP `setcc`/`select_cc`、浮点分支、`ctlz/cttz/bswap`、FP 取整 libcall）。`meson.build` 中有一段 **DADAO 源过滤**，把命中这些节点的源（整个 `libm/` 与约 20 个 libc 浮点/字节交换文件）排除，使构建**确定性**失败为零、而非半途而废。这些源码的补齐归 **`LLVM-079t`（P0）/`LLVM-080t`（P1）**；后端补齐后**删除过滤条目**即得全量库（`TESTCASES-042t` 的 `test/test-math` 依赖此项）。

## 构建与验证

```
make fetch apply-series     # 建工作树 + 应用补丁集
make install-host           # 需要 install-root clang
make build-picolibc         # 编 picolibc 并装到 .dadao/dadao-unknown-elf（幂等）
make test-picolibc-smoke    # 最小 E2E：printf("hi") 编/链/跑，QEMU semihosting
make check                  # 含 check-patch-tree（9 断言）+ check-index-blobs
```

`test-picolibc-smoke` 用 `tests/scripts/{codegen_crt0.s,dadao.lds}`（v5 ELF 直载路径）链接；`picolibc_noflash.ld` 是单 RAM 目标的正解（`picolibc.ld` 的 flash/ram 段在本目标同址重叠、不可用）。
