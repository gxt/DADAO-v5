# OpenCode watchdog

定时检查一个 OpenCode 会话，只在它真正空闲时发送一条巡检 prompt：

- 主会话或它的子代理在 `running` → 跳过；
- 同仓库有运行中的 shell → 跳过；
- 有 pending form/permission → 跳过；
- 最近 `WATCHDOG_IDLE_AFTER` 秒内有活动 → 跳过；
- 通过后发一条 queue 模式的巡检消息，并记录 `last_wake`，冷却期内不重复。

巡检 prompt 要求先盘点队列，不得只看 `.tao/tasks` 就判空：

1. `.tao/tasks` 中待开始/待验收/已完成未合并；
2. `discussing.md` 中已批准但尚未立册的事项；
3. `milestones.md` 中未完成行；
4. `issues.yaml` 中 open 项；
5. ADR/任务书中待确认项。

只要任一来源存在“已批准、依赖满足、无阻塞”的任务，就继续推进；已批准未立册的必须当场立册；被语义阻塞的任务不等于队列空，应登记阻塞原因并继续找其它可推进项。只有所有来源都没有可推进任务时才停。不改 SPEC/契约语义，未经授权不 push。

## 脚本

```text
.opencode/watchdog/watchdog.sh
```

默认：

- 仓库：脚本所在仓库根目录（可用 `WATCHDOG_REPO` 覆盖）
- 会话：按“仓库目录 + 无 parent 的最近活动会话”自动发现（可用 `WATCHDOG_SESSION_ID` 指定）
- 状态/日志：`<repo>/.work/`
- 冷却：1800 秒
- 空闲阈值：600 秒

可用环境变量：

```text
WATCHDOG_REPO
WATCHDOG_SESSION_ID
WATCHDOG_STATE
WATCHDOG_COOLDOWN
WATCHDOG_IDLE_AFTER
OPENCODE_BIN
WATCHDOG_SKIP_SHELL_CHECK=1   # 仅测试时忽略自身 shell 检查
```

## 手动测试

```bash
# 当前会话/子代理在跑时，应输出 SKIP active
.opencode/watchdog/watchdog.sh --dry-run

# 用一个已结束的旧会话验证 WAKE 判定（不会真的发 prompt）
WATCHDOG_SESSION_ID=<old-session-id> \
WATCHDOG_SKIP_SHELL_CHECK=1 \
.opencode/watchdog/watchdog.sh --dry-run

tail -n 20 .work/check-opencode-watchdog.log
```

## 安装 cron

`crontab -e` 加入示例内容（路径按仓库实际位置调整）：

```cron
SHELL=/bin/bash
PATH=/home/ubuntu/.local/bin:/usr/local/bin:/usr/bin:/bin
MAILTO=""
*/30 * * * * /mnt/tao/DADAO-v5/.opencode/watchdog/watchdog.sh >> /mnt/tao/DADAO-v5/.work/check-opencode-watchdog-cron.log 2>&1
```

停用：删除对应 cron 行。

当前不自动安装 cron；安装前先跑 `--dry-run`。
