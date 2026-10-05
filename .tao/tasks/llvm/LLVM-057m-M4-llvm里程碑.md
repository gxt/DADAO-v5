# LLVM-057m: M4 llvm 里程碑

**模块**：llvm
**项目里程碑**：M4
**状态**：待开始
**目标**：LLVM 侧 M4 收口——① ELF writer 改 `SHT_RELA` 并实现 4 类 `getRelocType`（`ABS48/REL26/REL20/REL14`）；② 汇编器遗留落地（`set.*` 伪指令展开、`.dd.*` 指导符、`-multiple-to-single`、越界立即数报错）；③ 全局数据 `.data`/`.rodata` lower + `ABS48`/RELA fixup；④ DADAO LLD target + `dadao.lds` 产出 `ET_EXEC`。为 `INTEG-016t`（多 TU/多段 E2E）提供 `llc`/`llvm-mc`/`ld.lld` 全链能力。
**关联任务**：`LLVM-050t`、`LLVM-051t`、`LLVM-052t`、`LLVM-053t`、`LLVM-054t`、`LLVM-055t`、`LLVM-056t`（7 个）

## 核验
- 关联任务是否均已 `已验证`（严格串行链 `050t → 051t → 052t → 053t → 054t → 055t → 056t`，见 `SPEC-104k`）
- 产出是否存在：`DADAOELFObjectWriter` RELA + 4 类 `getRelocType`；`AsmParser` 伪指令/指导符/选项/诊断；CodeGen 全局数据 + `ABS48` fixup；`lld/ELF/Arch/DADAO.cpp` + `lld/ELF/Target.{cpp,h}` + `dadao.lds`
- 补丁集完整：`components/llvm-project/patches/**` + `series` 与工作树一致；`make check-patch-tree` EXIT=0；`check-source-state` clean
- `make check`/`make check-lit` EXIT=0；`make test-codegen`（M3 15/15）不回归
- 各任务「一键证据脚本」均含 `--inject` 反例自检（注入→FAIL→还原+**重建**→回绿）
- reloc/fixup 坑预防 5 条在 `LLVM-050t`/`055t`/`056t` 落实（尤其②同段判定、⑤大常量材料化）

## 核验记录（主会话）
（核验命令、输出与退出码；结论）
