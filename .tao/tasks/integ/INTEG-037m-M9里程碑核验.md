# INTEG-037m: M9 整体里程碑核验（FP 完备性 + ISA 收口 + 规范重组）

**模块**：integ
**项目里程碑**：M9
**状态**：已验证
**里程碑结论**：M9 达成（2026-10-24，用户授权收尾）
**目标**：核验 **M9 = FP 完备性 + ISA 收口 + 规范重组**（用户 2026-10-24 裁定「M9 确实该收尾了，不用等我确认」）。

## 达成判据（用户 2026-10-24 确认）

1. 所有 `t` 册（本里程碑期）`已验证`；
2. **终局全量复跑绿**：L3 `check-full` PASS；libc-test 静态 331 pass / 0 fail、动态 338 pass / 0 fail；llvm-test-suite 静态 204 pass / 0 fail、动态 203 pass / 0 fail（`blocked>0 ⇒ rc=1` 为 `ISS-248` 既定口径）；
3. open issue ≤ 10，且全部为 M10 已登记项；
4. 关闭项已归档 `.tao/archive/M9/issues-closed.md`，`issues.yaml` 仅留 open。

## 本期任务（67 册，全部 `已验证`）

`TESTCASES-062t`, `INFRA-105t`, `SPEC-171t`, `QEMU-073t`, `INFRA-103t`, `TESTCASES-053t`, `SPEC-170t`, `SPEC-168t`, `SPEC-167t`, `TESTCASES-057t`, `INFRA-104t`, `LLVM-129t`, `LLVM-126t`, `TESTCASES-058t`, `SPEC-158t`, `LLVM-123t`, `QEMU-070t`, `SPEC-157t`, `LLVM-127t`, `TESTCASES-059t`, `LLVM-128t`, `TESTCASES-061t`, `SPEC-164t`, `INFRA-102t`, `SPEC-166t`, `SPEC-165t`, `SPEC-160t`, `LLVM-124t`, `QEMU-071t`, `SPEC-159t`, `TESTCASES-060t`, `SPEC-162t`, `LLVM-125t`, `QEMU-072t`, `SPEC-161t`, `SPEC-163t`, `INFRA-101t`, `SPEC-155t`, `LLVM-122t`, `QEMU-068t`, `QEMU-069t`, `SPEC-156t`, `INFRA-099t`, `INFRA-098t`, `TESTCASES-054t`, `INFRA-097t`, `SPEC-154t`, `SPEC-153t`, `TESTCASES-056t`, `LLVM-121t`, `INFRA-100t`, `QEMU-067t`, `SPEC-141t`, `TESTCASES-055t`, `INFRA-096t`, `LLVM-118t`, `LLVM-119t`, `LLVM-120t`, `LLVM-100t`, `LLVM-117t`, `QEMU-066t`, `QEMU-065t`, `INFRA-095t`, `SPEC-152t`, `TESTCASES-052t`, `LLVM-116t`, `QEMU-064t`

## 关键里程碑事件

- **ISA**：`ftfma`/`fofma`（`rrrr` 四操作数）、`OPC-MISC` 迁 `opc 0x47`（含 `ct*` 并入）、`fence`/`lr`/`sc` 解 `excluded`（`excluded` 余 2 条）；`fp` 66 条、`m9` 34 条、`total` 266 条。
- **后端**：窄位 `i8/i16/i32` 全做（各 1 条指令）、`ctlz/cttz/ctpop`+`rev` 各 1 条、FMA 零拷贝、`ldm`/`stm` post-RA 合并、FP 接线 8 类 + `__builtin_dadao_remainder`。
- **规范**：`MISC-`→`OPC-` 485 处、分册重组（11=核芯功能扩展 / 12=其它指令 / 非法指令并入 00）、changelog 30→14 条、**发布 0.5.5**。
- **门控**：去写死计数（改集合不变量）、+7 项覆盖缺口、`br.nz` 偏移修正（失败路径可信化）、musl `-ffp-contract=off`（`math/yn` 回绿）。

## 遗留（M10，见 `issues.yaml` 的 10 条 open）

qemu-user 47 位基址、`-static-pie` PIC libc、picolibc `%p`、`-g` DWARF 重定位、`llvm-mc` 显示断言、harness `ret`、musl 排除 13 文件、qemu 稳定性合并条、5.3 归档 PROVENANCE、`ISS-282` ③ 后续。
