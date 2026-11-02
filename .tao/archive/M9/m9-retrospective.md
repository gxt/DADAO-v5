# M9 回顾（FP 完备性 + ISA 收口 + 规范重组）

> 作者：architect（2026-10-25）｜ 依据：`.tao/knowledge/milestones.md`、`issues-closed.md`、`INTEG-037m`。

## 1. 达成判据与结果

1. **全部 `t` 册 `已验证`**：68 册（含 67 册本批 + `SPEC-141t` 结册）。
2. **终局复跑 0 fail**：L3 PASS；libc-test 331/338 pass、llvm-ts 204/203 pass（`blocked` 逐例有归属）。
3. **open issue ≤ 12**：实际 **11 条**，全部为 M10 登记项（`qemu-user` 基址、`-static-pie`、picolibc `%p`、`-g` DWARF、`llvm-mc` 断言、harness `ret`、musl 排除源、qemu 稳定性 3 条、0.5.3 归档 PROVENANCE、`ISS-282③`）。
4. **归档闭环**：83 条已关 issue 归档；68 册任务书归档；`issues.yaml` 仅留 open。

## 2. 主要成果

- **ISA（发布 0.5.5）**：FMA `rrrr` 四操作数（`0x5E/0x5F`）；`OPC-MISC` 迁 `opc 0x47`（`ct*` 并入）；`fence`/`lr`/`sc` 解 `excluded`（余 2 条）；`fp` 66 / `m9` 34 / `total` 266。
- **后端**：窄位 `i8/i16/i32` 全做（各 1 条指令）；`ctlz/cttz/ctpop`+`rev` 各 1 条；FMA 零拷贝；`ldm`/`stm` post-RA 合并；FP 接线 8 类 + `__builtin_dadao_remainder`。
- **规范**：`MISC-`→`OPC-` 485 处；分册重组（11=核芯功能扩展 / 12=其它指令 / 非法指令并入 00）；changelog 30→14 条；附录 A/B 归位；`spec_cite` 改「手册: 助记符」。
- **门控**：去写死计数（集合不变量）；+7 项覆盖缺口；`br.nz` 偏移修复（失败路径可信化）；musl `-ffp-contract=off`（`math/yn` 回绿）。

## 3. 经验（已入 `lessons.md` 的保留条目）

- 文档级小错不阻断（reviewer 口径收敛）；纯文档迁移不跑 L1/L2、不做注入。
- 证据脚本基线须锚定"任务基线提交"，不得用 `HEAD`（提交后必漂）。
- 「不改断言」优先于"变绿"：放宽断言 ⇒ 打回。
- 覆盖披露：新增/删除用例数必须在完成区显式写明（`LLVM-127t`/`TESTCASES-061t` 各踩一次）。

## 4. 遗留

见 `INTEG-037m` §遗留（11 条 M10 项）。风格统一改写（`SPEC-169t`）未立册，留 M10。
