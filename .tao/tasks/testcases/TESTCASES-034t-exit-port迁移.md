# TESTCASES-034t: exit-port → `SYS_EXIT` 迁移（范围 = 全部）

**模块**：testcases
**项目里程碑**：M5
**依赖**：`QEMU-046t`、`TESTCASES-033t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **定位**：M1–M4 的停机协议依赖 **exit port**（`ADR-0004 D3`，MMIO `0xffff_8000_0000` 8B 只写）。M5 起 `SYS_EXIT` **替代** exit-port（`ADR-0020 D8`）；**迁移范围 = 全部**（`INTEG-019k` 裁定 7）：M1–M4 **所有**依赖 exit-port 的向量/harness/oracle 全迁到 `SYS_EXIT`。
- **输入**：
  - `QEMU-046t`（semihosting `EXIT`/`EXIT_EXTENDED` → host `$?`；exit port 仍并存）+ `TESTCASES-033t`（semihosting 向量 + 退出码约定）。
  - `.tao/adr/adr-0020-see-semihosting.md`（`Accepted`，**D8**）；`adr-0004` 修订（**R2**：`SYS_EXIT` 替代 exit-port，迁移 = 全部）。
  - **现状（实测，`grep` 为准）**：依赖 exit-port 的向量/harness——如 `tests/vectors/**`（`expected_exit` 通过 `st.o` 写 exit port 的用例构造）、`tests/scripts/**`（`codegen_crt0.s`/`trampoline.bin`）、`tools/qemu/min_rom_probe_*.py`、`tools/integ/run_{codegen,elf}_e2e.py`、`tests/llvm/lit/**` 中依赖退出码的用例、`tools/testcases/build_test_binary.py` 等。**逐个 `grep` 列表（`0xffff_8000_0000`/`exit`/`st.o`）后迁移，不臆测**。
  - `.tao/knowledge/issues.yaml` 的 `ISS-147`（exit 码与 fault 区重叠：`137==0x89==UNDI` false-PASS 风险）。
- **输出**：
  - **逐个迁移**：把上列**全部**依赖 exit-port 的向量/harness/oracle 的**退出机制**改为经 `SYS_EXIT`（semihosting `EXIT`/`EXIT_EXTENDED`），并**同步更新期望值**（退出码语义/构造序列）。
  - **迁移后全量重跑确认绿**（`INTEG-019k` `/plan` 审阅 6 项建议）：`test-codegen` 15/15、`test-elf` 5/5、`check-lit`、`check-qemu-semantics`、`validate-vectors` 等逐项与改前**逐项相等**（`git` 差分/对拍）。
  - **`ISS-147` 随迁处置**：把 E2E/向量期望退出码**约束到 `0x00–0x7F`**（避开 fault 区 `0x80–0xFF`）；如迁到 `SYS_EXIT` 后语义已天然规避，则**结案**（`status: closed`，`resolved_by: TESTCASES-034t`），否则登记处置结论。
  - **兼容性说明**：exit-port 机制**不删**（`QEMU-046t` 保留）；本任务只把**测试侧**迁移到 `SYS_EXIT`；若个别用例因架构原因必须留 exit-port，须**逐条披露理由**（默认 = 全部迁）。
- **约束（硬）**：
  - **范围 = 全部迁移**（用户裁定）；**不得**只迁部分、**不得**保留 exit-port 兼容为默认。
  - **迁移 = 改退出机制 + 同步期望值 + 迁移后全量重跑确认绿**（三者齐备；`INTEG-019k` `/plan` 建议）。
  - 不改 `components/**`/`spec/`；`contracts/**` 如需（`expected_exit` 字段）须**停下报告**（跨组件）。
  - **期望值独立派生**；`test-codegen`/`test-elf` 通过数**逐项不回归**。
  - 临时目录 `/tmp/opencode/TESTCASES-034t/`；**不提交 git**；复杂命令输出留存 `.work/log/testcases/`（**禁 `tee`**）。
  - **重建成本申报**：依赖 `build-mc`/`build-lld`/`build-qemu`（增量；`build-qemu` 5–20 分钟）；开工前说明。

## 验收标准

1. **迁移覆盖**：`grep -rln "0xffff_8000_0000\|exit.port\|exit_port" tests/ tools/ | grep -v __pycache__ | grep -v archive` **为空**（或仅剩**逐条披露**的例外，附理由）；给真实 `grep` 输出列表（迁移前/后对照）。
2. **退出机制**：迁移后向量/harness 经 `SYS_EXIT` 获退出码（给 ≥2 条真实链路逐步输出）。
3. **期望值同步**：迁移后 `test-codegen` 15/15、`test-elf` 5/5、`check-lit`（通过数）、`check-qemu-semantics` 与改前**逐项相等**（给对拍/差分）。
4. **`ISS-147`**：E2E/向量期望退出码**全部落 `0x00–0x7F`**（`grep`/脚本枚举，真实输出）；`issues.yaml` 处置（closed 或登记结论）。
5. **反例门控**：注入反例（把某用例期望退出码改错 ⇒ 门控**非零退出** ⇒ 还原 ⇒ 回绿）；给真实输出。
6. **门控**：`make check` EXIT=0；`make check-no-residue` EXIT=0。
7. **一键证据脚本**：`.work/evidence/TESTCASES-034t/run.sh`——非交互、失败非零、逐项打印、含注入自检、结尾**禁 `tee`**。
8. **无残留**：`git status --untracked-files=all` 仅迁移的向量/harness/oracle + `issues.yaml` + 本任务书。

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
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例** + 独立核 `grep` 覆盖/退出码区/对拍 + 判决）
