# m18-linux-008: K1–K4 门控断言补强（ISS-444/457/487/488）

**模块**：linux
**项目里程碑**：M18
**依赖**：无（涉及既有 K1–K5 门控与探针）
**可并行分片**：是（按 issue 四条，文件不重叠）；执行仍受 linux 组件写者互斥约束
**预估**：2–3 h（标定：同档最近 5 件派单→合入实测 31/62/86/124/182 min，中位 86 min；本任务为四条既有 finding 的补强，取 1.5–2× 中位）
**档位**：中改（门控/探针断言）
**状态**：待开始
**执行环境**：本地（QEMU system；K1/K2/K4 既有镜像）

## 背景

M14 遗留四条 P3 finding 已分诊到 M18（`issues.yaml` 的 `milestone: M18`），均属「断言不可达 FAIL / 证据间接 / 措辞归属错」：

- `ISS-444`：K1 三阶段顺序只有间接证据（共享 BootROM 不打印）；需给 hmon/smon/power 各加 1 行 semihosting 标记，门控改直接断言顺序。
- `ISS-457`：K2 两条明确要求缺可达 FAIL 断言（`local_irq_save` 的 flags 截断、`enable` 全清 0 仍全绿）；需补 P1/P5 绝对断言并订正注入标签。
- `ISS-487`：`k4_switch_probe.py` 的 S6 只钉调用字面量、可被注释命中；需改钉调用形态并补 `clocksource_register_hz` 同判；旧断言翻转须补 §4a 退役台账；WARNING 白名单按文本而非 `file:line`。
- `ISS-488`：`TASK_UNMAPPED_BASE` 页对齐半修复无断言；完成区计数不准；补丁树判据缺现场统计行。

## 目标

按 `docs/Process-07` 的「断言可达 FAIL」与 §4a 退役口径逐条闭合上述四条；**不放宽既有判据**，不改内核行为。

## 验收（逐条贴真实 rc）

1. 四条 issue 逐条有处置证据（文件 + 断言 + 注入记录），并在 `issues.yaml` 关闭（`closed_in: M18`、`resolved_by` 指向本任务）。
2. 每条新增/修改断言至少 1 路**可达 FAIL**：注入 → 目标断言红 → `cp`+md5 还原 → 回绿；证据脚本一键跑。
3. `ISS-444`：BootROM 三阶段标记在 `check-linux-k0` 与 `check-linux-k1` 上均可观测；顺序断言可直接判红（注入乱序或去标记）。
4. `ISS-457`：P1（高位参与比较）与 P5（`enable == disable & ~SOURCE_BITS`）在注入下判红；`run.sh --inject` 标签与实况一致。
5. `ISS-487`：S6 在「删除注册行」注入下判红、注释命中不再假绿；WARNING 白名单按文本匹配；补 §4a 退役记录。
6. `ISS-488`：补「exec 后 `mm->mmap_base` 页对齐」断言；计数现场派生；补丁树判据打印问题总数。
7. 不回归：`check-linux-k0`、`check-linux-k1`、`check-linux-k2`、`check-linux-k5`、`check-linux-k6` 全 rc=0；`check-knowledge-refs` rc=0；`make check` 与基线逐行相同。
8. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动：`tests/unit/linux/**`、`tools/linux/**`、`tests/shared/bootrom/**`、`docs/Process-07*.md`（仅 §4a 退役记录）、`.tao/knowledge/issues.yaml`、本任务书。不改 `components/**`、`Makefile`。
3. 每条断言有可达 FAIL；禁恒真、禁两支写同一结果、禁同源自比；计数现场派生。
4. 源码还原一律 `cp`+md5；禁 `git checkout`/`restore`/`stash`；还原后重建。
5. 不改版本号；术语「bank = 寄存器组」。

## 待裁定

无。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（工程师自审意见、问题、判决及 finding 处置）

### 第 1 轮 reviewer 验收
（审查者独立重跑记录、约束核验、判决）
