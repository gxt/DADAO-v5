# feedback_007：证据脚本断言「已提交变更」须带提交范围（`BASE..HEAD`）

**来源**：`SPEC-115t` round1 证据脚本 `.work/evidence/SPEC-115t/run.sh` 用裸 `git diff` 检测已提交的变更 ⇒ 假 FAIL（EXIT=1），round2 改用 `BASE_COMMIT..HEAD` 范围后回绿。教训记录见 `lessons.md §7.9`。

## 规则

1. **凡断言「某变更存在 / 某文件被改」的 git 调用，若被测产物可能已被提交，必须带提交范围**：用 `git diff "$BASE_COMMIT"..HEAD -- <path>`（或 `--name-only`），`BASE_COMMIT` = 本任务**基线提交**（前置任务提交/分支点），**禁**裸 `git diff`（裸 `git diff` 比较**工作树 vs HEAD**，变更已入 HEAD 时返回空 ⇒ 假 FAIL）。
2. **`BASE_COMMIT` 须可经环境变量覆盖**（默认基线），以便用 `BASE_COMMIT=HEAD` 重放脚本、验证该断言**确实可 FAIL**（非恒真）。
3. **只有「检测工作树残留」才用 `git status --porcelain`**（其语义就是查工作树，不依赖变更是否已提交，合理保留）；若需在**提交后**仍抓越界，另加一条 `$BASE_COMMIT..HEAD` 的越界断言（用同一 allow-list 正则）。
4. **证据脚本本身也是交付物**：其 git 调用须经受「**提交后仍应回绿**」的自检；reviewer 审核脚本时**须逐条核 git 调用是否带 range**（不得只看脚本是否 PASS），engineer 修一处缺陷时须**全脚本同类排查**（`grep -nE '\bgit\s+(diff|status|log|show)\b'`）。

## 指向

- 落地：`SPEC-115t` round2（新增 `BASE_COMMIT`〔默认 = 前置 `LLVM-060t` 提交 `ebb9ef2`〕+ 检查 8/9 改 `$BASE_COMMIT..HEAD` + 检查 7 追加越界检查）；reviewer round2 逐条核 5 处 git 调用（3 处带 range、1 处工作树残留保留、1 处注释）。
- 同类：`lessons.md §2.1`（管道退出码陷阱）——均为「证据脚本自身缺陷」类。
