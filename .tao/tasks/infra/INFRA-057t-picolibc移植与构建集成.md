# INFRA-057t: picolibc 移植补丁集 + 构建集成

**模块**：infra
**项目里程碑**：M7
**依赖**：`INFRA-055t`（组件接入，`已验证`）、`QEMU-056t`（RAM 基址，**先于本任务**）、`INFRA-056t`（`clang++`；同改 `Makefile` ⇒ 串行）；`SPEC-131t`（oracle/半托管口径）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 用户裁定（2026-10-11）：M7 test 重心 = **picolibc 自带 test**（`INTEG-033k §裁定汇总 #2`）；组件锁 = `manifests/components.lock.toml` 的 picolibc 条目（tag `1.8.12` @`2ae376c6`）。
  - 参考经验（**内容溯源，非执行必需**）：`DADAO-0628/docs/adr/0014-libc-syscall-charter.md` D5/D5.1（picolibc 先行、tinystdio、最小 syscall stub `_write`/`_exit`/`_sbrk`）；`docs/development-roadmap.md`（`__heap_start`/`__heap_end` sbrk fallback；heap 段与 `PT_LOAD` 关系）。
  - 现行：`components/picolibc/{README.md,patches/dadao/README.md.patch(占位),series,changelog.md}`（`INFRA-055t`）；`components/picolibc/patches` 补丁集体例见 `spec/Process-01-组件补丁组织与构建编排.md`；`tests/scripts/dadao.lds`（`INFRA`/`QEMU-056t` 后为新基址）。
- **输出**：
  1. **真移植补丁集**（`components/picolibc/patches/**`，一文件一补丁，`series` 非空）：cross file（`dadao` target）、machine/board 支持（`libc/machine/dadao` 头/`machine/` 目录、`picolibc.h` 配置）、**syscall stub**（`_write`→semihosting `SYS_WRITE`；`_exit`→`SYS_EXIT`；`_sbrk`→`SYS_HEAPINFO`/`__heap_*`）。
  2. **构建集成**（`Makefile` / `tools/infra/**`）：编 picolibc（`clang -target dadao-unknown-elf`）产出静态库 + 落 `.dadao` 安装点；target 可复跑。
  3. **半托管/ABI 口径确认**：`_write`/`_exit`/`_sbrk` 映射到 `contract-semihosting` 服务；若合约有缺口，登记并交由 `SPEC-131t`。
- **约束**：
  - **不改上游只读册**；补丁只动 picolibc 组件源（`components/picolibc/patches` 内）。
  - **补丁导出纪律**：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥（`AGENTS.md`「组件补丁」）。
  - **依赖顺序**：`QEMU-056t`（RAM 基址）**必须先落地**（`INTEG-033k` Wave 串行）。
  - **不引动态链接/C++ 标准库**（M7 排除项）。
  - **计数不写死**；只动任务范围，越界须披露。

## 避坑清单

- **heap 段与 `PT_LOAD`**：`__heap_start`/`__heap_end` 若不在任何 `PT_LOAD` `memsz` 内，QEMU 加载语义/`sbrk` 须复核（0628 经验；本 v5 `dadao.lds` 亦须核）。
- **`long double` = f64**（`sizeof=8`）⇒ 与宿主 80-bit 不同（过渡 oracle 边界，`SPEC-131t`）。
- **`check_patch_tree` 断言⑧/⑨**：`.work/source/picolibc` 须 `base+1`（≥1 补丁且 `apply-series`）；占位补丁须被真补丁**替代或并存**（不得留空 `series`）。
- **浅克隆**：`.cache/picolibc.git` 为浅镜像；新增补丁不入镜像（补丁在 `components/`，`make fetch` 后 `apply-series`）。
- **失败保留现场并继续推进**（`AGENTS.md`「最小安全设计」）。

## 验收标准

1. **补丁集**：`components/picolibc/patches/**` 含 cross file / machine-dir / syscall stub 补丁（真实 `find` 输出）；`series` 非空；`make check-patch-tree` EXIT=0。
2. **可构建**：`make` 目标编出 picolibc 静态库（EXIT=0，真实输出 + 库文件存在）。
3. **最小 E2E**：一个最小 picolibc 程序（如 `printf("hi")` 或 `test/test-cplusplus`）编/链/跑正确退出码（QEMU semihosting）。
4. **门控**：`make check`、`check-patch-tree`、`check-no-residue` EXIT=0。
5. **反例门控**：`check-patch-tree` 注入反例（清空 `series` 或删补丁）⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿。
6. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
