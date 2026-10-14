# .tao/contracts/ — 人读契约正文（归一化叙述）

**机器可读投影在 `../../contracts/`**（`opcodes.yaml` / `abi.yaml` / `legality_rules.yaml` / `fp_semantics.yaml`）——本目录是**源**（叙述型正文），仓库根 `contracts/` 是**派生**（机器数据）。

本目录由 `INFRA-071t`（Phase B，2026-10-14）自 `.tao/knowledge/` 迁入（`INFRA-070t` 为 Phase A）；顶层白名单门控 = `check-contracts-dir`（`tools/infra/check_contracts_dir.py`，L1 成员）。

## 文件说明

| 文件 | 一句话 |
|------|--------|
| `contract-abi.md` | ABI 合约（M1 最小 ABI + M3 标量调用约定；0.9.2） |
| `contract-asm-list.md` | DADAO 汇编指令表（**机械生成投影**；生成器 `tools/llvm/gen_asm_list.py`） |
| `contract-asm.md` | DADAO 汇编语言合约（`spec/Toolchain-01` 归一化；0.5.0） |
| `contract-cfx-aliases.md` | cfx 别名表（**机械生成投影**；生成器 `tools/spec/gen_cfx_aliases.py`） |
| `contract-dynlink.md` | 动态链接 ABI 合约（M8：无内核的 Linux 用户态栈） |
| `contract-elf.md` | SimRISC M1 ELF 合约（Object ABI） |
| `contract-fp.md` | `scope: fp` 60 条浮点语义合约（0.5.4） |
| `contract-isa.md` | SimRISC ISA 规范合约（M1 范围；0.5.4） |
| `contract-see.md` | SEE/HEE 运行环境合约（M5；0.7.1） |
| `contract-semihosting.md` | semihosting 合约（M5；0.7.1） |
| `contract-syscall.md` | Linux syscall 映射合约（M8：无内核的 Linux 用户态栈） |

## 迁移授权链（留纸）

- **三项裁定**（用户 2026-10-14，渠道 = 经主会话问答；原话「**1、a；2、a；3、a**」）：① 只读锁册（`manifests/spec-readonly.lock.toml`）**授权改 + 重算 `sha256`**；② `contracts/*.yaml` 内嵌旧路径字段**改值指向新路径**；③ 只动范围**扩到 `tools/**` / `components/**` / `tests/**`**。
- **目标目录裁定**（用户 2026-10-14；原话「**我改主意了，contracts-*.md改到 .tao/contracts/ 目录下，是不是更合适**」/「**同意**」）。
- **落纸位置**：`.tao/tasks/infra/INFRA-071t-contract迁移至tao-contracts目录.md` §用户授权落纸 / §目标目录变更。
- **口径**：本仓库**无** `LICENSE` / 署名文件惯例 ⇒ 三要素之「许可」= 上述**用户授权链留纸**（**非**随附许可文件）。
