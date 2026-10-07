# feedback_003：判 target 是否在 `make check` 依赖链，须读 `check:` 依赖行而非 `.PHONY` 清单

> 操作规范（"应该这样做 / 不该那样做"）。来源：`SPEC-117t`（`Process-05 §6` 落点规则补正，2026-10-07）下发前预检的错误引用，由工程师实测、主会话更正、reviewer 独立复核、architect 交叉复核确认。

## 背景（触发事件）

`SPEC-117t` 的约束原写「`make check`（`check-spec-refs` 等）EXIT=0」，下发前预检据此**断言**「`check-spec-refs` 确在 `make check` 依赖链内」，并引 `Makefile:41` 为据。实测：`Makefile:41` 是 `.PHONY` 清单的**续行**（`... check-spec-refs check-spec-drift ...`），**不是**依赖；`check:`（`Makefile:297`）的依赖行**不含** `check-spec-refs`；其目标处（`Makefile:336`）注释明示 `# Standalone target, not part of \`make check\`.`。

## 规律（应固化）

1. **判「某 target 是否随 `make check` 跑」只看 `check:` 目标的依赖行**（`check: dep1 dep2 …`），**不得**以 `.PHONY:` 清单为准——`.PHONY` 只是「伪目标声明」（声明它不是文件名），与依赖关系无关。
   - 反例：把 `Makefile:41`（`.PHONY` 续行）当成「`check` 的依赖」⇒ 误判 `check-spec-refs` 会被 `make check` 带上。
   - 做法：`grep -n '^check:' Makefile` 看依赖行；再 `grep -n '^<target>:' Makefile` 看目标处注释（常标 `standalone`）。

2. **规范/任务书要求「另跑 standalone target」时，须显式写明「standalone，不在 `make check` 依赖链内」并各自单独跑、各自报 EXIT**，不得与 `make check` 合并成一句「`make check`（含 X）」。

3. **`.PHONY`、`check:` 依赖行、目标处注释三者都要核，行号引用须逐行核对**再落纸（本任务记录中 F4/reviewer 曾把注释行 `336` 误记为 `337`，仅行号偏一、不影响结论，但行号引用仍应精确）。
