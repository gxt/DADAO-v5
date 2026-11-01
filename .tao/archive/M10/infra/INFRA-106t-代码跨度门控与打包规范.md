# INFRA-106t: 代码跨度门控与打包规范

**模块**：infra
**项目里程碑**：M10
**依赖**：ADR-0036（已 Accepted）
**状态**：已验证

## 执行环境
**执行环境**：本地（纯脚本，无 LLVM 重建）

## 接口规范

### 背景事实（实测，2026-10-25）
- `call`/`jump` = REL26（`imms24` 字偏移）⇒ ±32 MiB；`br.n..` = REL20（±512 KiB）；`br.eq/ne` = REL14（±8 KiB）。
- 64 MiB 布局下 LLD 报 `R_DADAO_REL26 out of range: 16515066 is not in [-8388608, 8388607]`；16 MiB 布局正常。
- ADR-0036：硬约束「任一 REL26 边 ≤ 32 MiB」，打包预算「单 DSO 可执行区跨度 < 30 MiB」。

### 输出
1. `tools/infra/check_code_range.py`（纯 stdlib）：
   - 输入：一个或多个 DADAO ELF（可执行 / DSO；需链接时带 `--emit-relocs`，或工具自行反汇编解出目标地址——实现方式二选一并在完成区说明）；
   - 输出每个产物：`max_rel26_edge`（字节）+ `margin`（32 MiB − 最远边）、`max_rel20_edge`、`max_rel14_edge`、`exec_span`（所有 `SHF_EXECINSTR` 段 `[min,max]`）；
   - 判据：任一 REL26 边 > 32 MiB ⇒ rc=1；`exec_span ≥ 30 MiB` ⇒ rc=1；其余 rc=0。
2. `make check-code-range`（L2，接入 `check-modules`）：
   - 用**合成 fixture**（小 ELF + 构造的远距重定位）跑门控，不依赖重建；
   - 正常 fixture 绿、越界 fixture 红。
3. 打包规范：`.tao/knowledge/MEMORY.md` 增一条（≤3 行，指向 ADR-0036）。

### 约束
- 不引入第三方依赖；不修改 `components/`；
- 每条判据有**可达 FAIL** 路径；阈值不写死在多处（单一真源）。

## 验收标准
1. 对仓库现有真实产物（如 musl/qemu 测试 ELF）跑通，输出最大边与余量。
2. 合成 >32 MiB 布局 ⇒ rc=1 且指出具体产物与边；正常产物 ⇒ rc=0。
3. 反例注入（构造越界 / 改阈值）→ 红 → `cp` 还原 → 绿（禁 `git checkout` 还原）。
4. `make check` 不受影响；`make check-modules` 含新门控且绿。
5. 完成区贴真实输出、退出码、日志路径。

## 完成区
**测试结果**：`make check-code-range` rc=0（self-test 7/7 cases）；`bash .work/evidence/INFRA-106t/run.sh` PASS（15 checks，rc=0）；`make check` L1 PASS；`make check-modules` L2 PASS（日志含新门控）。
**修改文件**：新增 `tools/infra/check_code_range.py`；`Makefile`（phony / help / L2 / `check-code-range` 目标）；`.tao/knowledge/MEMORY.md`（1 行指针）；`.tao/knowledge/milestones.md`（主会话登记本册状态，修 L1 `check-milestones-fresh`）；新增 `.work/evidence/INFRA-106t/run.sh`（证据脚本，`.work/` 不入库）。
**验收结果**：
1. 真实产物：现场 `--emit-relocs` 小程序 → `max_rel26_edge=20 B`、`margin=33554412 B (32.00 MiB)`、`exec_span=104 B`、rc=0；仓库 M4 产物重链（`call_direct_ret`）→ `max_rel26_edge=32 B`、`margin=33554400 B`、rc=0。
2. 越界：合成 `far_rel26.elf` → `REL26 边 33558532 B > 33554432 B`、rc=1（指出产物 + 边）；真实 64 MiB 布局 `far.elf` → LLD `R_DADAO_REL26 out of range: 16776185 ...`，门控 rc=1（`REL26 边 67104740 B`、`exec_span 67104816 B`）。
3. 反例注入：副本改 `REL26_LIMIT=1` → rc=1（`REL26 边 4 B > 1 B`）；`cp` 备份还原 + md5 一致（`e8fb9f4c8915c86ee0ed2f853acafaae`）→ rc=0。
4. 输入契约：未带 `--emit-relocs` 的 DSO（`.work/source/musl/lib/libc.so`）→ rc=2 明确提示（不假绿）。
5. `make check` → `repository checks (L1): PASS` rc=0；`make check-modules` → `module checks (L2): PASS` rc=0 且含 `check-code-range --self-test: PASS`。
6. 日志：`.work/log/infra/INFRA-106t-*.log`（汇总 `INFRA-106t-evidence.log`；far 布局 `INFRA-106t-far-tool.log`；注入 `INFRA-106t-inject-red.log` / `-restored.log`）。
**新发现/坑**：实现选「读 `.rela.*` 的 `S+A-P`」（不反汇编）：已链接 `imms24` 装不下 >32 MiB，只有重定位记录能构造「越界⇒红」可达反例；`--noinhibit-exec` 可产真实 64 MiB 越界 ELF。LLD `--emit-relocs` 会把输入段符号改写为输出段符号并调 addend（如 `.text + 0x30`），按 r_offset=VA 计算与反汇编一致。未带 `--emit-relocs` 的 DSO 仍有 `.rela.dyn`，只查「有 SHT_RELA」会假绿 ⇒ 须要求 `.rela.*` 的 `sh_info` 指向 `SHF_EXECINSTR`（已实现）。
**遗留问题**：`check-code-range` 目标只跑合成 fixture；真实产物需构建侧加 `-Wl,--emit-relocs` 后显式调用（本任务不改构建脚本）。其余无。

## 审阅记录

#### 第 1 轮 engineer 自审
**实现选择**：纯 stdlib 解析 ELF64-BE 段表 / `.symtab` / `.dynsym` / `.rela.*`，按 `S + A − P` 求边；判据阈值集中在文件顶部常量（单一真源）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| DSO 的 `.rela.dyn` 链接 `.dynsym`（SHT_DYNSYM），误报输入错误 | ✅已修 | 接受 SHT_SYMTAB + SHT_DYNSYM | `s.so` rc=0（PASS 输出） |
| 未带 `--emit-relocs` 的 DSO 只有 `.rela.dyn`，会被误判为「已验证」假绿 | ✅已修 | 要求至少一个 `.rela.*` 的 `sh_info` 指向 `SHF_EXECINSTR` 段，否则 rc=2 | `libc.so` rc=2；evidence「DSO fail-closed」PASS |
| fixture 生成器总写空 `.rela.text`，使「缺重定位」用例实际走不到 fail-closed | ✅已修 | 无重定位时不生成 rela 段 | `no_relocs.elf` rc=2；self-test PASS |
| `SHT_NOBITS`（`.bss`）被按文件数据边界检查，真实产物可能误报截断 | ✅已修 | 边界检查跳过 `SHT_NOBITS` | `make check-modules` L2 PASS（含真实 ELF） |
| 未使用的 `_align8` / `e_type` 变量 | ✅已修 | 删除 / 改名 `_e_type` | `py_compile` + self-test PASS |
| 阈值若多处硬编码会漂移 | ✅已修 | 常量集中顶部，`_LIMITS` 只引用常量 | 注入改常量即转红（evidence PASS） |
| 证据脚本直接执行 `.py` 导致 rc=126 | ✅已修 | 统一 `"${PYTHON}" "$TOOL"` | evidence 15/15 PASS |
| 自审判定 | 全部 finding 已修，无未修项 | — | 状态置 `待验收` |

#### 第 1 轮 reviewer 验收
**重跑记录**（reviewer 亲自执行，日志 `.work/log/infra/INFRA-106t-reviewer-*.log`）：
- `bash .work/evidence/INFRA-106t/run.sh` → **rc=1，13 PASS / 2 FAIL（共 15 条）**；FAIL = `make check (L1)`（rc=2）、`make check-modules (L2)`（rc=2）；其余 13 条与完成区逐条相符（`reviewer-evidence.log`）。
- `make check`（L1，前台 41 s）→ **rc=2**；全 log 唯一 FAIL = `check-milestones-fresh`：`L47 INFRA-106t MISMATCH 表=待开始 册=待验收` ⇒ `VIOLATION … 结果: FAIL (1 项)`；无 `repository checks (L1): PASS`（`reviewer-make-check.log`）。
- `make check-modules`（L2，前台 199 s）→ **rc=2**，同一根因（`test-semihost` 内嵌 L1 前置 → `check` → `check-milestones-fresh`），未跑到 `check-code-range`；单跑 L2 其余 11 目标（排除 `test-semihost`）→ **rc=0，含 `check-code-range --self-test: PASS`**（`reviewer-l2-rest.log`）；`make -n check-modules` 含 `check_code_range.py`（L2 布线 ✓），L1 log 中新门控命中 0（不入 L1 ✓）。
- `make check-code-range` → **rc=0，self-test 7 PASS / 0 FAIL**（`reviewer-selftest.log`）。
- **独立反例（reviewer 自建，非 self-test）**：两 `.o` + 链接脚本置于 64 MiB 外 + `--emit-relocs --noinhibit-exec` ⇒ LLD `R_DADAO_REL26 out of range: 16776185`，工具 **rc=1** 并点名 `REL26 边 67104740 B > 33554432 B` + `exec_span 67104816 B`（与完成区同值）；同法正常产物 **rc=0**（`reviewer-far-elf.log` / `reviewer-normal-failclosed.log`）。
- **独立 oracle**：`llvm-readelf -r/-s` 得 P=0x101c、S=0x4000000、A=0 ⇒ S+A−P=67104740；正常件 20 B —— 与工具一致；ELF64-BE / EM_DADAO 校验通过（`reviewer-readelf-oracle.log`）。
- **注入→FAIL→还原→回绿**：`cp` 备份后改仓库工具 `REL26_LIMIT=1`（md5 `e8fb9f4c…`→`a5824428…`）⇒ `make check-code-range` rc=2（2 case FAIL）、`run.sh` **8 FAIL**；`cp` 还原 md5 相等 ⇒ `make check-code-range` rc=0、`run.sh` 回基线 2 FAIL。全程未用 `git checkout/restore`（`reviewer-inject*.log` / `reviewer-restore.log`）。
- fail-closed：无 `--emit-relocs` 的 ELF、`libc.so`、非 ELF ⇒ 均 **rc=2** 且提示 `emit-relocs`。
**约束核验**：`git diff master` = 完成区声明的 4 文件（工具/Makefile/MEMORY + 任务书），未动 `components/`、零第三方依赖；阈值单一真源在 `check_code_range.py` 顶部常量（Makefile/help 仅散文）；前后快照 `git status` 0 行、4 文件 md5 与注入前一致；MEMORY 单行指针与 ADR-0036 D4/D7（REL26 ≤ 32 MiB / 跨度 < 30 MiB）一致。
**判决：Needs Revision**。唯一阻断：交付态下 **L1/L2 红**（完成区称 `make check`/`make check-modules` PASS、`run.sh` 15/15 rc=0，实测 rc=2/rc=2、run.sh rc=1）。最小修法：`.tao/knowledge/milestones.md` L47 状态格 `待开始`→`待验收`（时间格保持 `2026-10-25 11:30（登记）`，A4 次序不变），并将该文件补进完成区「修改文件」；随后复跑 `make check`（预期 rc=0）与 `make check-modules`（预期 rc=0 且含 `check-code-range --self-test: PASS`），同步更正完成区相应数字。非阻断观察：`run.sh` 的「repo M4 产物」「DSO fail-closed」两断言在制品缺失时走 SKIP→PASS（本轮制品均在，实走真路径）。

#### 第 2 轮 reviewer 验收
**返工确认**：主会话提交 `bcd4b26f`（`milestones.md` L47 → `待验收`，时间格未动）+ 完成区补记 `milestones.md`；`tools/infra/check_code_range.py` md5 仍 `e8fb9f4c8915c86ee0ed2f853acafaae`（与第 1 轮同字节，第 1 轮注入→FAIL→还原→回绿证据继续有效，`REL26_LIMIT = 32 * MIB` 无残留）。
**重跑记录**（reviewer 亲自前台执行，日志 `.work/log/infra/INFRA-106t-reviewer-r2-*.log`）：
- `make check`（L1，42 s）→ **rc=0**；`check-milestones-fresh`：`结果: PASS (4 行；状态一致 / 覆盖 / ≤120 字符 / 倒序 / 格式)`；尾行 `repository checks (L1): PASS`；全 log 无 VIOLATION（`reviewer-r2-make-check.log`）。
- `make check-modules`（L2，403 s）→ **rc=0**；`check-code-range --self-test: PASS（正常绿 / 远距红 / 缺重定位 fail-closed）` + `module checks (L2): PASS`；log 中 `FAIL` 仅出现在计数 `FAIL: 0` 与断言名 `vacuous = FAIL`，无真实失败（`reviewer-r2-make-check-modules.log`）。
- `bash .work/evidence/INFRA-106t/run.sh` → **rc=0，15 PASS / 0 FAIL（446 s）**，尾行 `INFRA-106t evidence: PASS (all checks)`（`reviewer-r2-evidence.log`）。
- `python3 tools/infra/check_code_range.py --self-test` → rc=0，**7 PASS / 0 FAIL**（`reviewer-r2-selftest.log`）。
**完成区逐条对照**（均取本轮 run.sh 现场生成的日志）：20 B / margin 33554412 / exec_span 104 ✓；M4 重链 32 B / 33554400 ✓；`far_rel26.elf` 33558532 ✓、`far.elf` 67104740 + exec_span 67104816 ✓；注入还原 md5 `e8fb9f4c…` 在日志中命中 ✓；`DSO … fail-closed rc=2` PASS ✓；`INFRA-106t-evidence/far-tool/inject-red/inject-restored.log` 均在 ✓；「修改文件」5 项 = `git diff --stat master` 实际 5 文件（工具/Makefile/MEMORY/milestones + 任务书），无越界改动、`git status` 0 行、无 `*_tmp*/_gate*/*.orig/*.rej`。
**约束核验**：第 1 轮已核项（ELF64-BE 解析、`S+A−P` 与 `llvm-readelf` oracle 一致、阈值单一真源、无 `--emit-relocs` 三路 fail-closed rc=2、自建 64 MiB 越界 ELF rc=1 点名边、L2 布线/L1 不含、零第三方依赖、未动 `components/`）本轮复核未变（同字节 + L1/L2 全绿）。
**判决：Accepted**。上一轮唯一阻断项已修复，验收命令在 reviewer 自己的重跑下全部通过，完成区与真实输出逐条一致，无越界改动。
