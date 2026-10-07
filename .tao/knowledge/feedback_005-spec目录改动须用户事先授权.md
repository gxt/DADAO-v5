# feedback_005：改 `spec/` 目录须用户事先明确授权

**来源**：`SPEC-114t` round1 擅改上游只读册（`spec/DADAO-12`/`spec/DADAO-22`）事故，用户 2026-10-07 裁定。教训记录见 `lessons.md §7.5`。

## 规则

1. **`spec/` 目录下任何新增/修改/删除**（含 v5 自定册 `Machine-*`/`Process-*` 与 `spec/README.md`）**须用户"事先"明确允许**，授权**原话落盘**（任务书/审阅记录）；未获授权而拟改 `spec/` ⇒ **BLOCKED**。
2. **上游只读册**（`DADAO-1x`〔11/12/13〕、`DADAO-2x`〔21/22/23〕、`SimRISC-00..12`、`Toolchain-01`，共 **20 册**）**只作只读引用**（引 `§` 章节号，**不改一字**）；确需修改须先经用户授权，并在**同一变更**内更新 `manifests/spec-readonly.lock.toml` 的 `sha256` 锁。
3. **任务书「输出」不得把上游只读册列为可改对象**——架构阶段即须守住；需要的新正文一律落 **v5 自定册**（`spec/Machine-*` 等）。
4. **三处固定检查**：① 下发前预检**第 5 项**（拟改文件清单 × `spec/` 清单）；② reviewer 验收；③ architect 提交——均以 `git diff --name-only`（提交前 `git diff --cached --name-only`）与 `spec/` 清单交叉，**有交集而缺授权证据 ⇒ 阻断**（reviewer 判 `Needs Revision` / architect 拒绝提交）。

## 指向

- 机制落地：`SPEC-119t`（`manifests/spec-readonly.lock.toml` + `tools/infra/check_spec_readonly.py` + `make check-spec-readonly`，**纳入 `make check`**）。
- 规则正文：`spec/Process-06-spec目录保护规范.md`（`SPEC-119t` 产出）。
