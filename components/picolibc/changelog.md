# Picolibc 组件变更记录

> 粒度：**按任务一条**，追加式。补丁集的生成/应用/校验规范见 `docs/Process-01-组件补丁组织与构建编排.md`。

| 日期 | 任务 | 变更 |
|---|---|---|
| 2026-10-11 | `INFRA-055t` | **组件接入骨架**：`manifests/components.lock.toml` 追加 picolibc 条目（`enabled=true`、精确 commit `2ae376c6cdf4fef90ca2388ecf7a07457fa63cff`、`shallow=true`、`shallow_ref="release-1.8.12"`）；建 `components/picolibc/{README.md,patches,series,changelog}`；首个补丁 = 新增 `dadao/README.md`（占位，**声明无行为**；真移植归 M7）。浅裸镜像 `.cache/picolibc.git` + 工作树 `.work/source/picolibc`（`make fetch`）。 |
| 2026-10-11 | `INFRA-057t` | **真移植补丁集 + 构建集成**：占位补丁由真补丁**替代**（删 `dadao/README.md`）。补丁 14 份（计数现场统计）：cross file `scripts/cross-dadao.txt`；machine dir `libc/machine/dadao/{meson.build,machine/meson.build,setjmp.S}`；semihost stub `libos/semihost/machine/dadao/{meson.build,semihost-dadao.S}`；配置 `libc/include/machine/{ieeefp.h,setjmp.h,endian.h}`、`libc/include/sys/cdefs.h`、`libc/string/{fls,flsl,flsll}.c`；`meson.build`（DADAO 源过滤）。构建集成 `make build-picolibc`（`tools/infra/build_picolibc.py`，meson+ninja，幂等，装 `.dadao/dadao-unknown-elf`）+ `make test-picolibc-smoke`（`printf("hi")` 编/链/跑，QEMU semihosting，EXIT=0）。**范围**：LLVM 后端缺口（bitcast/setcc/select_cc/ctlz/cttz/bswap）致 `libm/` 及 ~20 libc 浮点文件暂排除，待 `LLVM-079t`/`080t`。 |
| 2026-10-12 | `INFRA-066t` | **恢复 `libm`：删源过滤表 + 最小化**：删 `meson.build` 的**整目录 `libm/` 排除**，把后端受阻源过滤**最小化到 41 条**（由本构建**全部 1120 个编译项逐条重编**得出的精确失败集，`ISS-193` 登记 6 类根因）。重建后 `libc.a` 1,241,616 → **1,686,214 B**，8 符号（`floor`/`ceil`/`trunc`/`round`/`rint`/`nearbyint`/`fmin`/`fmax`）`nm` 全命中（`libm.a` 为上游**空壳**，见 README「移植要点」）。`make test-picolibc-smoke` 增 **libm E2E 阶段**（8 符号真实调用 + C99 语义自检 + 退出码）。**仍不可链接**：`pow`/`hypot`/`j0`/`y0`/复数/`scanf` 族/`memset_s`（`ISS-193`）。 |

