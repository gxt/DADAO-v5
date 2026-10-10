# LLVM-067m: M6 llvm 里程碑

**模块**：llvm
**项目里程碑**：M6
**状态**：里程碑
**目标**：LLVM 支持 M6——整数**完整调用约定**（变参/聚合/`sret`/多返回/间接调用）+ 小欠账收口；**DADAO clang target + driver/sysroot**（仅 freestanding）；大帧四形态寻址 + `mem*` 内建 + `MaxStoresPerMem*=16`；**lld reloc 完善**（`REL12` + `ld/st` 符号偏移新类型 + `FK_Data_1/2/4` 静默 0 + `ABS48` 数据表示）；FP/RF codegen；`make build-mc`/`build-clang`/`check`/`check-patch-tree`/`check-lit` 绿；`ISS-110` 留后。
**关联任务**：`LLVM-062t`、`LLVM-063t`、`LLVM-064t`、`LLVM-065t`、`LLVM-066t`

## 核验
- 关联任务是否均已 `已验证`：✅ `062t`/`063t`/`064t`/`065t`/`066t` **均 `已验证`**；本里程碑启动后新增 `069t`–`078t` 亦**均 `已验证`**（现场逐一读任务书 `**状态**` 字段）
- 产出是否存在：✅ `components/llvm-project/patches/llvm/lib/Target/DADAO/**`（含 `AsmParser`/`MCTargetDesc`/`Disassembler`）、clang `lib/Basic/Targets/DADAO.{h,cpp}`（`TargetInfo`）+ `lib/Driver/ToolChains/DADAO.{h,cpp}`（driver）+ `lib/CodeGen/Targets/DADAO.cpp`、`lld/ELF/Arch/DADAO.cpp`、`series`/`changelog.md`；对应 lit 向量（`tests/llvm/lit/MC|CodeGen/DADAO/*`、`tests/e2e/lit/*`）齐
- 不回归（真实输出，日志 `.work/log/llvm/LLVM-067m-*.log`）：
  - `make check-source-state` EXIT=0（llvm-project `HEAD=47eb2396a44c count=1 clean=True`）
  - `make build-mc` EXIT=0（PASS）
  - `make check` EXIT=0（lit 89/89；`check_issues` 24 open / 0 blocking；repository checks PASS）
  - `make check-patch-tree` EXIT=0（断言⑥：3 component(s), 109 patches OK）
  - `make check-lit` EXIT=0（89/89）
- ADR 前置（`SPEC-122t` 的 ADR）均已 `Accepted` 后方进入实现：✅ `ADR-0018`（`§C7 D4`/`D6` 就地修订版）`Accepted`、`ADR-0021`（`REL12`+`ABS12`）`Accepted`、`ADR-0022`（Embench）`Accepted`
- **如实记（M6 内 LLVM 侧补口）**：里程碑启动后因 Embench 接入暴露的缺口清单 **G1–G6**（`ISS-175`–`180`）+ `ISS-181`–`186`、`ISS-182` 由新增任务 `LLVM-069t`–`078t` 收口（含 `-O2` 静默错码 G6/`ISS-180`、跳转表 G3、128 位乘高半 G2、真尾调用、`.p2align` 崩溃 `ISS-182`）；**Embench `-O0`/`-O2` 双 19/19 退出码 0**（`LLVM-077t`/`078t` 现场统计）。**`ISS-110` 留后（M6 边界）**、`ISS-108` 推迟 M7。
- 核验通过 ⇒ `**状态**` 置为 `里程碑`。

## 审阅记录

#### 第 1 轮 architect 里程碑核验
- 关联任务状态：`062t`/`063t`/`064t`/`065t`/`066t` + `069t`–`078t` 全部 `**状态**：已验证`（逐文件 grep 复核）。
- 产出：`patches/llvm/lib/Target/DADAO/**`（27 `.patch` + `AsmParser`/`MCTargetDesc`/`Disassembler`）、`patches/lld/ELF/Arch/DADAO.cpp.patch`、`patches/clang/lib/{Basic,Driver,CodeGen}/…/DADAO*.patch`、`series`（含 `dadao` 全部条目）/`changelog.md` 均存在。
- 门控重跑（本机，真实 EXIT）：`check-source-state`=0、`build-mc`=0、`check`=0（89/89）、`check-patch-tree`=0、`check-lit`=0（89/89）。日志落 `.work/log/llvm/LLVM-067m-*.log`。
- ADR 前置：`ADR-0018`/`ADR-0021`/`ADR-0022` 均 `Accepted`。
- 判决：**通过 ⇒ 置 `里程碑`**。
