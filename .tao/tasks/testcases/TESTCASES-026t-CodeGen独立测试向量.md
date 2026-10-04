# TESTCASES-026t: CodeGen 独立测试向量

**模块**：testcases
**项目里程碑**：M3
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`SPEC-096k` §边界（M3 = 标量整数/指针）；`.tao/knowledge/contract-abi.md`（+ `SPEC-097t` 的 §4 正文）。
- **输出**：
  - `tests/codegen/*.ll`：M3 标量程序的源 IR（每程序一个文件），覆盖 **算术 / 访存 / 分支 / 调用** 四类，每类 ≥1，且**互不依赖外部符号/全局变量/变参/聚合**。
  - `tests/codegen/expected.yaml`（或等价）：每程序的**期望结果**（退出码/返回值），带**独立推导依据**（见约束）。
  - `tools/testcases/validate_codegen_vectors.py`：校验向量 schema/覆盖/期望值格式（可失败）。
- **约束**：
  - **Independent oracle**（project 硬约束）：期望值**不得**由 LLVM（`llc`）或 QEMU 生成，必须**独立派生**——在 host 侧用独立脚本/Python 按 IR 语义算出（或手算并写明推导）。
  - **程序形态**：IR 层可被 M3 后端编译（标量、无变参/聚合/sret/间接调用/全局变量/`.data`）；入口约定与 `INTEG-012t` 的 harness 对齐（程序把结果写入 exit port 或返回码，harness 读退出码比较；具体接口在 `INTEG-012t` 冻结，本任务与之对齐）。
  - **覆盖矩阵（对齐 §5 判定）**：算术（add/sub/常量材料化，含负常数与高位 wyde 序列 → C12）、访存（load/store + 偏移，含**大端窄访存** `ld.ub/uw/ut`/`ld.sb/sw/st` 的字节偏移/扩展 → C13/`ADR-0018（C13）`）、分支（有符号谓词 + 循环；`==`/`!=` 用 `br.eq/ne`、`p==NULL` 用 `br.z/nz {rb}`、`p==q` 用 `cmp.uo`（`dbb`）+`br.z` → C17）、调用（直接 call/ret + 返回值 + 多参数/栈参数至少一例；堆溢出按**全局声明序**、窄参数 caller 扩展 → C4/`ADR-0018（C4）`）；另含**指针参数/返回 bank**（指针落 GPRB/`rb31` → C1/C5）与**指针算术**各 ≥1：`add.o`（orrr，rb 目的，base+offset）、`cmp.uo`（orrr `dbb`）指针比较（→ C14/`ADR-0018（C14）`）、**`ptr−ptr` 指针差**（两指针相减，后端选出新增指令 `sub.o_orrr_dbb` = RB−RB→RD；语义见 `SPEC-100t`/`adr-0012 D9`；期望值 = 两地址整数差，**独立按 IR 语义推导**，不得从 `llc`/QEMU 反推）。给出「程序 ↔ 覆盖点」表。
  - **期望值**：每条给出最小/边界/负值样本（如算术含负操作数、访存含非零偏移与窄宽度大端字节序、分支覆盖 taken/not-taken、指针算术含非零偏移、**`ptr−ptr` 含负差（小地址 − 大地址）与正差各 ≥1**、调用含指针参数）。
  - **validator 能失败**：对注入的反例（改期望值 / 改 IR / 少一个覆盖类别）必须报 FAIL；完成区给出反例注入真实输出。
  - 不改 `contracts/**`、不改既有 `tests/vectors/**`（M3 codegen 向量独立目录）；不提交 git。

## 验收标准

1. `tests/codegen/` 含四类程序文件 + 期望值；`tools/testcases/validate_codegen_vectors.py` 退出 0，且**覆盖矩阵四类齐全**（≥1 算术/访存/分支/调用），且含**指针差 `ptr−ptr`** 用例 ≥1（期望值为两地址整数差，**独立派生**自 IR 语义）。
2. 每条期望值有**独立推导证据**（host 计算脚本输出或手算说明），**非**来自 `llc`/QEMU。
3. validator 反例门控：注入反例 → 非零退出（真实输出留存 `.work/log/testcases/`）；还原 → 回绿。
4. 不引入仓库残留（`make check-dirs`/`check-no-residue` 干净）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
