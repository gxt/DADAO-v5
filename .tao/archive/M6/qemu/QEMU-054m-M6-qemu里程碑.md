# QEMU-054m: M6 qemu 里程碑

**模块**：qemu
**项目里程碑**：M6
**状态**：里程碑
**目标**：QEMU 支持 M6——**改走 `load_elf()`**（取消自建 `dadao_load_regions[]` 白名单；多段 `PT_LOAD`/RELA/`e_entry`/栈初始化作验证项）；**RAM@0 step2**（旧向量/harness/`crt0`/e2e 迁 `0` + 删旧 RAM 段 `0xffff_0000_0000` + 收紧 `check-interface` 断言）并含 **`ISS-169`**（6 个 M1/M2 手写探针退出通道改 `SYS_EXIT`）；`make check`/`check-interface`/`check-qemu-semantics` 绿。
**关联任务**：`QEMU-052t`、`QEMU-053t`、`QEMU-055t`

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`components/qemu/patches/{hw/dadao/**,target/dadao/**}`、`series`/`changelog.md`；迁移后的旧向量/harness/`crt0`/e2e（EA=0 语义已更新）
- 不回归：`make check`/`check-interface`/`check-qemu-semantics` EXIT=0；`check-patch-tree` 断言⑥绿
（核验通过后，主会话将 `**状态**` 置为 `里程碑`）

## 完成区（核验结论，2026-10-11）
- **关联任务**：`QEMU-052t` / `QEMU-053t` / `QEMU-055t` **均 `已验证`**（读各自任务书 `**状态**` 字段）✔
- **产出存在**（逐项现场核查）：
  - `components/qemu/patches/hw/dadao/**`（3 补丁：`Kconfig`/`dadao-machine.c`/`meson.build`）+ `target/dadao/**`（19 补丁）＋ `target/meson.build.patch` 等；`series` 34 行、`changelog.md` 在 ✔
  - **改走 `load_elf()`（钉子②）**：代码无 `dadao_load_regions`/`dadao_load_elf`/`DadaoLoadRegion` 残留（旧白名单已删）；`dadao-machine.c.patch` 调上游 `load_elf(...)` + 调用前薄校验 ✔
  - **RAM@0 step2**：`cpu.h.patch` `DADAO_RAM_BASE=0x000000000000`（旧 `0xffff_0000_0000` 已删）；向量/harness/`crt0`（`tests/scripts/codegen_crt0.s`）/e2e（`tests/e2e/*.s`）**EA=0 语义**（RAM@0=0、`SYS_EXIT` 停机）✔
  - **`QEMU-055t`**：`common-semi-target.c.patch` `DADAO_SEMI_RET_REG=8`（`common_semi_set_ret()`→`rd8`）+ 域 B（`tests/llvm/codegen/m5/m5_semi_write.s`+`expected.yaml`）✔
  - `ISS-165`（**RAM@0 step2 收口**）/`ISS-169`（6 探针退出通道→`SYS_EXIT`）由 `QEMU-053t` 收口（`QEMU-053t` 任务书完成区 + `changelog.md` 第 19 行 + `milestones.md`）✔
- **不回归（真实 EXIT，日志 `.work/log/qemu/QEMU-054m-*.log`）**：
  - `make check` **EXIT=0**（lit **89/89**；`repository checks: PASS`；`check_issues: 24 open, 18 closed, 0 blocking`）
  - `make check-interface` **EXIT=0**（ELF 5/5、ADR 29/29、Schema 41/41、Opcodes 8/8；含负断言「旧 RAM 段已删」「exit-port 已删」）
  - `make check-qemu-semantics` **EXIT=0**（149 total / 149 passed / 0 failed）
  - `make check-patch-tree` **EXIT=0**（断言⑥：3 component(s), **109 patches OK**）
- **证据指针**：`.work/log/qemu/QEMU-054m-{make-check,check-interface,check-qemu-semantics,check-patch-tree}.log`（md5 `0e86303b…`/`0118c662…`/`31c01497…`/`ecfceb29…`）
- **结论**：核验三项全部通过 ⇒ 置 `**状态**` = `里程碑`。（`components/qemu/README.md` L10 仍留「exit-port 可靠 halt」一句旧述，非门控、非阻断，已随本次记录披露。）

## 审阅记录

#### 第 1 轮 architect 里程碑核验
- 关联任务状态：`QEMU-052t`/`053t`/`055t` 均 `**状态**：已验证`（逐文件 grep 复核）。
- 产出：`patches/hw/dadao/**`（3）+ `target/dadao/**`（19+1）、`series`（34 行）、`changelog.md`；`load_elf()` 已改走（无旧白名单残留）；RAM@0（`DADAO_RAM_BASE=0`）向量/harness/`crt0`/e2e 迁 `0`；`DADAO_SEMI_RET_REG=8`。
- 跨模块（`ISS-165`/`ISS-169`）处置：均由 `QEMU-053t` 收口、无未处置跨模块影响。
- 门控重跑（本机，真实 EXIT）：`make check`=0（89/89）、`check-interface`=0（83 项）、`check-qemu-semantics`=0（149/149）、`check-patch-tree`=0（断言⑥，109 patches）。日志落 `.work/log/qemu/QEMU-054m-*.log`。
- 判决：**通过 ⇒ 置 `里程碑`**。
