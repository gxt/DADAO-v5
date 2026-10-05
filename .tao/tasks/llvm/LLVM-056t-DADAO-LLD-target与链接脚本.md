# LLVM-056t: DADAO LLD target + 链接脚本 `dadao.lds`

**模块**：llvm
**项目里程碑**：M4
**依赖**：`INFRA-043t`、`LLVM-050t`、`SPEC-107t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `INFRA-043t` 产出的 `ld.lld`（`.work/build/llvm/bin/ld.lld`）；`LLVM-050t` 的 `.o`（含 `SHT_RELA` + `R_DADAO_*`）。
  - `.tao/knowledge/contract-elf.md §1–§6`（`SPEC-105t`/`SPEC-107t` 后版本：`EM_DADAO=0x0DA0`、`e_flags=0x1`、`SHT_RELA`、4 类 reloc、公式无 −4、`ABS48` 3 片、段对齐/VA=PA、pipeline）；`.tao/adr/adr-0019`（Accepted）；`.tao/adr/adr-0004`（`SPEC-107t` 调整后的加载约定：RAM 基址 `0xffff_0000_0000` 作 `.text`/entry、`FILEHDR PHDRS`、段序 `.text→.rodata→.data→.bss`）。
  - `lld/ELF/Arch/RISCV.cpp`、`lld/ELF/Arch/PPC64.cpp`、`lld/ELF/Target.{cpp,h}`、`lld/ELF/CMakeLists.txt`（**只读对照**：主流 LLD target 范式）。
  - `DADAO-0628 DL-061c`（标准 `ld.lld` + `dadao.ld`，**只读对照**；注意其地址基址/`-4`/reloc 集与 v5 不同，**不照抄**）。
- **输出**（组件源码改在 `.work/source/llvm-project`；导出补丁）：
  1. `lld/ELF/Arch/DADAO.cpp`：实现 `relocate()`（`R_DADAO_ABS48`/`REL26`/`REL20`/`REL14`；大端写回；偏移溢出 ⇒ **link-time error**，不截断/wrap）与 `getRelExpr`（`R_PC`/`R_ABS`）。
  2. `lld/ELF/Target.{cpp,h}` 注册 `EM_DADAO (0x0DA0)` → DADAO target；`lld/ELF/CMakeLists.txt` 增列 `Arch/DADAO.cpp`。
  3. 链接脚本 **`dadao.lds`**（落点建议 `tests/scripts/dadao.lds`，随产物入库）：`ENTRY`（入口符号，如 `_start` 或 `e_entry` 约定）；`.text` 起于 RAM 基址 `0xffff_0000_0000`（`ADR-0004`）；段序 `.text→.rodata→.data→.bss`；对齐依 `contract-elf §5`（`.text` 4B、其余 8B）；`FILEHDR PHDRS` 使 `.text` file-offset 0；权限 RX/RW。
  4. 导出的 `components/llvm-project/patches/**` + `series`。
- **约束**：
  - **relaxation 禁用**（`ADR-0019 D7`）：不缩短序列、不重排，linker 只做原地补丁。
  - **溢出 = link-time error**（`ADR-0019 D6`）：越界 relocation 必须 `ld.lld` 报错并非零退出。
  - **大端** 写回；`EM_DADAO`/`e_flags` 正确（`ET_EXEC` 头）。
  - **reloc/fixup 坑预防（5 条，同 `LLVM-050t`）**；linker 侧尤其②（同段/跨段判定）与⑤（不得用受限字段承载大值）。
  - **不做**：`RELA_PAGE`/`RELA_LO`（留后）、relaxation、绝对调用约定扩展。
  - **补丁纪律（`spec/Process-01`）**；`commit --amend` 收敛 base+1 → `make_patch.py` → `check-patch-tree`；不手改补丁。
  - 构建：`make build-lld`（`INFRA-043t`）；受 `JOBS` 限制；失败即停。
  - 临时目录 `/tmp/opencode/LLVM-056t/`；**不提交 git**；复杂命令输出留存 `.work/log/llvm/`。

## 验收标准

1. `make build-lld` / `ninja -j8 -C .work/build/llvm ld.lld` EXIT=0。
2. **ET_EXEC**：对 ≥1 个含跨段/外部符号引用的 `.o`，`ld.lld -T dadao.lds`（或等价）EXIT=0；`llvm-readobj -h` 显示 `Type: EXEC`、`Machine: 0xDA0`、`Flags [ (0x1)`、`Entry: <addr>`；`.text` file-offset = 0（`FILEHDR PHDRS`）。
3. **reloc 解析**：`ABS48`（3 片，读指令内 `wyde-position`）、`REL26/REL20/REL14`（`(S+A−P)>>2`，**无 −4**）逐条真实解析；给出链接前后 `llvm-readobj -r`/`-s` 对照与手算核对（≥1 每类）。
4. **大端**：段/数据字节序核对（hexdump）。
5. **溢出负例**：构造 `REL14`/`ABS48` 越界 → `ld.lld` **报错、非零退出**（不截断/wrap）；给出真实 stderr。
6. **链接脚本**：`dadao.lds` 存在且内容与 `ADR-0004`/`contract-elf §5` 一致（地址/段序/对齐/`FILEHDR PHDRS`）。
7. **不回归**：`make check` EXIT=0；`check-patch-tree` OK；`make test-codegen` 不回归。
8. 一键证据脚本 `.work/evidence/LLVM-056t/run.sh`（含 `--inject`：改 `relocate` 公式（加 −4/改掩码）→ 期望 FAIL → 还原+**重建 ld.lld** → 回绿）；完成区贴真实输出。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
