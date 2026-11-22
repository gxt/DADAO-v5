# m16-testcases-005: 签名脚本迁 `tests/shared/`

**模块**：testcases
**项目里程碑**：M16
**依赖**：无（与 `m16-testcases-004` 可并行）
**可并行分片**：否（机械迁移，单点收口）
**预估**：小（机械迁移）
**档位**：小改（复核 ≤20 min）
**状态**：已验证

## 背景（用户 2026-11-22 裁定）

签名机制要集中到 `tests/shared/`：汇编侧 `tests/shared/asm/signature.inc` 已在该处，host 侧 `tools/testcases/lib/signature.py` 仍在 `tools/` 下。用户要求「签名区的脚本移动到 `tests/shared` 目录下」，避免 `tools/` 继续膨胀。

## 要做

1. `tools/testcases/lib/signature.py` → `tests/shared/signature.py`（保留文件内容与 API，只改必要的路径注释）。
2. 更新全部引用（现场至少 6 处，以 `git grep -n "testcases/lib"` 与 `grep -rn "import signature"` 现场核实为准）：
   - `tests/ee-tiny/run_inst_tiny.py`
   - `tools/testcases/arch/min_rom_probe_tlb.py`
   - `tools/testcases/arch/node_probe_prelude.py`
   - `tools/testcases/inst/check_inst_sig.py`
   - `tools/testcases/lib/inst_expected.py`
   - `tools/idl/qemu_final_state.py`
   以及 `sys.path` 插入点、`__pycache__` 清理。
3. 更新说明文档：`tests/shared/README.md`（谁用）、`tests/arch/README.md`（host 侧路径）。
4. 删除旧文件 `tools/testcases/lib/signature.py`，不留转发壳（避免两份实现）。

## 不做

- 不改 `signature.py` 的语义/API；
- 不改 `tests/shared/asm/signature.inc`；
- 不动其它 `tools/testcases/lib/*` 文件。

## 约束

- 独立 `git worktree`；**不提交 git**；
- 变更集 = {本任务书, `tests/shared/signature.py`, 6 处引用文件, 两份 README, 删除旧文件}；不改组件源码；
- 不写运行期路径到入库文件；
- 逐项 staging 语义（本任务不提交，只保证完成区清单与 `git status` 对账）。

## 验证

运行期证据目录内的 `run.sh`，至少检查：

1. `tests/shared/signature.py` 存在，导入成功（`python3 -c "import signature"` 在 `tests/shared` 下）；
2. 全仓 `grep -rn "testcases/lib/signature"` 0 命中（排除 `.tao/archive/**` 与历史任务书）；
3. 迁移前后同一输入/期望的 `parse`/`compare` 结果逐字节相同（构造固定 blob，本地断言）；
4. `check-inst-asm` 代表册（01 册）与 `check-arch-smoke` 冒烟跑通，记录 rc；
5. `--inject` 1 路（把旧路径写回一个引用）⇒ FAIL，`cp`+md5 还原后回绿；
6. `make check-knowledge-refs` 与 `make check-tasks` 记录 rc。

## 完成区

**测试结果**：通过 12/12（运行期证据目录内 `run.sh`，rc=0）；`--inject` 自检 rc=0（注入 ⇒ C2 rc=1 ⇒ `cp`+md5 还原 ⇒ 回绿，md5 前后相同）。
**修改文件**（与 `git status` 逐项一致）：`tests/shared/signature.py`（由 `tools/testcases/lib/signature.py` `git mv`，内容逐字节未改，md5 `f69cb9069d3c8c945edb261bae4a9741`）；改 `tests/ee-tiny/run_inst_tiny.py`、`tools/testcases/arch/{node_probe_prelude,min_rom_probe_tlb}.py`、`tools/testcases/inst/check_inst_sig.py`、`tools/testcases/lib/inst_expected.py`、`tools/idl/qemu_final_state.py`、`tests/shared/README.md`、`tests/arch/README.md`、`tests/data/inst-signature/README.md`（越界披露：仅一行文档旧路径）；删旧文件（不留转发壳）；本任务书。`__pycache__` 已清（无 `signature*.pyc`）。
**验收结果**：① C1 新文件在/旧文件无/`cd tests/shared && python3 -c "import signature"` rc=0/`cmp` 基线 rc=0；② C2 code=0 doc=0 other=0（`.inc` 注释残留 2 行，脚本逐条断言均为 `@@` 且无非注释引用）；③ 行为等价 14/14（`parse`/`compare`/`unwritten`/`Emitter` + 4 类 parse 错误）；④ `check-inst-asm` 代表册（01-load-store）`run_asm_suite: 38/38 镜像通过`、rc=0；⑤ `check-arch-smoke` rc=0（`10/10 passed` + 25 服务 `RESULT: PASS`）；⑥ `check-knowledge-refs` PASS rc=0、`check-tasks` rc=0。附加：`check_inst_sig.py --data-only` rc=0（272 镜像/4539 槽）；`min_rom_probe_tlb.py --selfcheck` rc=0（15 cases/29 checks）。
**新发现/坑**：① 任务书「`grep -rn "testcases/lib/signature"` 0 命中」与「不改 `.inc`」冲突：`tests/shared/asm/signature.inc:4`、`tests/inst/macros/inst_test.inc:153` 为纯注释引用，按指令未改；`run.sh` 只放行 `.inc` 内的 `@@` 注释。② 本 worktree 未建构建树/安装根：安装根以符号链接复用主仓已构建的工具链，bootrom 在本树用 `make _locked-build-bootrom` 重建；`check-arch-smoke` 未跑 `install-host`（无构建树），改以 `_locked-check-arch-smoke` 的 recipe 体执行（跳过 `install-host`/`build-bootrom` 两个重建前置，两段检查均实跑）。③ 迁移后 4 个入口须显式把 `tests/shared` 加入 `sys.path`；该目录只有 `signature.py` 一个 `.py`，无模块遮蔽风险。
**遗留问题**：① `tools/testcases/lib/README.md:34` 仍把 `signature.py` 列在本目录（不在变更集，且被「不改其它 `tools/testcases/lib/*`」约束，未改，建议后续订正）。② `.inc` 两处旧路径注释是否允许纯注释订正（以达到字面 0 命中）待裁定。③ `install-host` 未执行（依赖不存在的构建树），以既有安装根二进制完成门控。

## 审阅记录

### 第 1 轮 engineer 自审

自主逐行审查（无嵌套子代理）：4 个 import 入口的 `sys.path` 插入与导入顺序、`signature.py` 迁移内容（`cmp` 基线）、6 处注释/文档路径、两份 README 表述、证据脚本每条断言的可失败路径与注入还原。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 迁移后 4 个入口仍在旧目录取 `signature`，否则 `ImportError` | ✅已修 | `run_inst_tiny`/`check_inst_sig`/`tlb`/`prelude` 显式加 `tests/shared` 到 `sys.path` | 4 模块 import rc=0；C4 38/38 |
| F2 任务书 0 命中与「不改 `.inc`」冲突，按字面判会恒红 | ✅已修（口径） | `run.sh` 拆 code/doc/other 三类 0 命中 + `.inc` 仅允许 `@@` 注释，并逐条打印残留 | `--inject` 注入 `.py` ⇒ C2 rc=1；还原 ⇒ rc=0 |
| F3 注入必须可回绿且禁 git 还原 | ✅已修 | `--inject` 用 `cp` 备份 + md5 对账（注入前/还原后相同） | inject rc=0，md5 同为 `6370a198b1c9a9e4088708d4dc2c2ef8` |
| F4 `tests/data/inst-signature/README.md` 文档旧路径不在变更集 | ✅已修（越界披露） | 仅改一行路径 | `git status` 与完成区清单逐项一致 |
| F5 `tools/testcases/lib/README.md:34` 仍列 `signature.py` | ⏸延后 | 未改（任务约束禁止改动该目录其它文件） | 已登记遗留① |
| F6 `__pycache__` 残留可能误导后续 import | ✅已修 | 删除 `tests/shared/__pycache__` 等；确认无 `signature*.pyc` | `find … -name 'signature*.pyc'` 空 |

**判决**：可修 finding 已全部处置；无未修代码项；状态 → 待验收。

### 第 1 轮 reviewer 验收（2026-11-22，本人重跑，不采信完成区）

**重跑（仓库根执行运行期证据目录内的 `run.sh`）**
- 全量第 1 次：12 PASS / 0 FAIL，`RESULT: PASS`，rc=0；明细 `C2 code=0 doc=0 other=0 inc 非注释=0`、`behavior 14/14`、`run_asm_suite: 38/38 镜像通过`、`check-arch-smoke: PASS (forward + permission + 25-service)`、`check-knowledge-refs` PASS、`check-tasks` rc=0（报告型提示，不阻断）。
- 独立注入①（向 `.py` 引用写回旧路径，`cp` 备份）：同一脚本 rc=1，`C2 code=1`、`[FAIL] 旧路径引用`、`RESULT: FAIL`；`cp` 还原后 md5 `1f3b9cde…` 前后相同，重跑 rc=0 回绿。
- 独立注入②（向 `.inc` 写回非注释旧路径行）：rc=1，`inc 非注释=1` → FAIL；`cp` 还原后 md5 `e0d09a31…` 前后相同、`git diff` 干净，重跑 rc=0（12 PASS）。全程未用 `git checkout/restore/stash`。
- 快照对账：审查前后 `git status --porcelain -uall` 逐行相同（SNAP_IDENTICAL）；`tests/shared/signature.py` md5 `f69cb906…` = 基线副本 = `git show HEAD:tools/testcases/lib/signature.py`（我独立比对 `diff` 空）。

**事实核验**：旧文件已不存在（`git status` 为 `D` 且盘上无）；`cd tests/shared && python3 -c "import signature"` rc=0（脚本内）；6 处引用 diff 逐条核过，4 个 `import signature` 入口均补 `tests/shared` 到 `sys.path`——我自跑 `run_inst_tiny`/`check_inst_sig`/`node_probe_prelude` 导入 rc=0、`min_rom_probe_tlb --selfcheck` rc=0（15 cases/29 checks）、`check_inst_sig --data-only` rc=0（272 镜像/4539 槽）；非 `.tao` 全仓旧路径仅 2 行 `.inc` `@@` 注释，`.inc` 未改（diff 空）；无第二份 `signature.py`。

**约束核验**：变更集 = 完成区清单 11 项，`tools/testcases/lib/` 只动 `inst_expected.py` + 删旧文件，`components/` 未动，入库 diff 无运行期/宿主绝对路径（命中的均为既有常量、非本任务新增）；未提交 git。

**finding（均不阻断，留 architect 终审）**
1. `run.sh` C2 排除整个任务书目录，宽于任务书字面「排除 archive 与历史任务书」：`m17-testcases-001`（2 处）、`m19-chipyard-002`（2 处）两本**未来**任务书仍含非注释旧路径，不在本任务变更集 ⇒ 建议补订正或入 backlog。
2. C5 以 noop 覆盖 `install-host`/`build-bootrom` 两前置后跑 `check-arch-smoke` recipe 体（本树无构建树，已披露）；我核到两段检查体实跑（10/10 + 25 服务 PASS），且 `signature.py` 非安装输入 ⇒ 不掩盖本任务回归，属门控配方偏离，需追认。
3. `tools/testcases/lib/README.md:34` 仍列 `signature.py`（约束禁改，遗留①）；`.inc` 两处注释与「不改 `.inc`」一致，是否纯注释订正待裁定。

**判决**：Accepted —— 验收命令在我本人重跑下全绿（rc=0、12 PASS），两条独立注入均 FAIL 且 `cp`+md5 还原回绿，快照一致，约束无违反。
