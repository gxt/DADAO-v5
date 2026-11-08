#!/usr/bin/env bash
# OpenCode watchdog: wake the target session only when it is truly idle.
# Intended for cron/systemd timer; state is kept directly under .work.
set -u

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
REPO=${WATCHDOG_REPO:-$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || { cd -- "$SCRIPT_DIR/../.." && pwd -P; })}
OPENCODE=${OPENCODE_BIN:-$(command -v opencode || true)}
[ -n "$OPENCODE" ] || OPENCODE=/home/ubuntu/.opencode/bin/opencode
STATE=${WATCHDOG_STATE:-$REPO/.work}
TARGET_ENV=${WATCHDOG_SESSION_ID:-}
COOLDOWN=${WATCHDOG_COOLDOWN:-1800}
IDLE_AFTER=${WATCHDOG_IDLE_AFTER:-600}
export WATCHDOG_IDLE_AFTER="$IDLE_AFTER"
LOCK="$STATE/check-opencode-watchdog-lock.log"
LOG="$STATE/check-opencode-watchdog.log"
LAST="$STATE/check-opencode-watchdog-last-wake.log"
mkdir -p "$STATE" || exit 1
exec 9>"$LOCK" || exit 1
flock -n 9 || exit 0

log() { printf '%s %s\n' "$(date '+%F %T')" "$*" >> "$LOG"; }
fail() { log "ERROR: $*"; exit 2; }

[ -x "$OPENCODE" ] || fail "opencode not executable: $OPENCODE"
command -v python3 >/dev/null 2>&1 || fail "python3 missing"

now=$(date +%s)
last=0
[ -f "$LAST" ] && last=$(cat "$LAST" 2>/dev/null || echo 0)
if [ "$last" -gt 0 ] && [ $((now - last)) -lt "$COOLDOWN" ]; then
  log "SKIP cooldown $((now-last))s < ${COOLDOWN}s"
  exit 0
fi

sessions_file=$(mktemp "$STATE/sessions.XXXXXX") || exit 1
active_file=$(mktemp "$STATE/active.XXXXXX") || exit 1
trap 'rm -f "$sessions_file" "$active_file"' EXIT

timeout 25 "$OPENCODE" api get /api/session >"$sessions_file" 2>>"$LOG" \
  || fail "GET /api/session failed"
timeout 25 "$OPENCODE" api get /api/session/active >"$active_file" 2>>"$LOG" \
  || fail "GET /api/session/active failed"

decision=$(python3 - "$sessions_file" "$active_file" "$REPO" "$TARGET_ENV" <<'PY'
import json, os, sys
sp, ap, repo, env_id = sys.argv[1:]
try:
    sessions = json.load(open(sp)).get("data", [])
    active = json.load(open(ap)).get("data", {})
except Exception as e:
    print("ERR\tjson\t%s" % e); raise SystemExit(0)
if env_id:
    target = next((s for s in sessions if s.get("id") == env_id), None)
else:
    candidates = [s for s in sessions
                  if (s.get("location") or {}).get("directory") == repo
                  and not s.get("parentID")]
    target = max(candidates, key=lambda s: (s.get("time") or {}).get("updated", 0), default=None)
if not target:
    print("ERR\tnotarget\tno session for %s" % repo); raise SystemExit(0)
sid = target["id"]
parent = {s["id"]: s.get("parentID") for s in sessions}
def is_active_descendant(x):
    cur = x
    seen = set()
    while cur and cur not in seen:
        if cur == sid:
            return True
        seen.add(cur)
        cur = parent.get(cur)
    return False
busy = [x for x in active if is_active_descendant(x)]
updated = (target.get("time") or {}).get("updated", 0)
age = max(0, int(__import__("time").time()) - (updated // 1000 if updated > 10**12 else updated))
if busy:
    print("SKIP\tactive\t%s\t%s" % (sid, ",".join(busy))); raise SystemExit(0)
if age < int(os.environ.get("WATCHDOG_IDLE_AFTER", "600")):
    print("SKIP\trecent\t%s\t%ss" % (sid, age)); raise SystemExit(0)
print("WAKE\tidle\t%s\t%ss" % (sid, age))
PY
)

case "$decision" in
  SKIP*) log "$decision"; exit 0 ;;
  ERR*)  fail "$decision" ;;
  WAKE*) ;; 
  *) fail "unexpected decision: $decision" ;;
esac

sid=$(printf '%s' "$decision" | cut -f3)
age=$(printf '%s' "$decision" | cut -f4)

# A background shell must block the wake-up too. Cron has no session shell here,
# but this catches shells started by tools / background commands.
if [ "${WATCHDOG_SKIP_SHELL_CHECK:-0}" != "1" ]; then
  shell_file=$(mktemp "$STATE/shell.XXXXXX") || exit 1
  trap 'rm -f "$sessions_file" "$active_file" "$shell_file"' EXIT
  shell_q=$(python3 - "$REPO" <<'PY'
import sys, urllib.parse
print("location%5Bdirectory%5D=" + urllib.parse.quote(sys.argv[1], safe=""))
PY
)
  timeout 25 "$OPENCODE" api get "/api/shell?$shell_q" >"$shell_file" 2>>"$LOG" \
    || fail "GET /api/shell failed"
  shell_running=$(python3 - "$shell_file" <<'PY'
import json,sys
try:
    d=json.load(open(sys.argv[1])).get("data", [])
except Exception:
    print("ERR"); raise SystemExit(0)
print("YES" if any(x.get("status") == "running" for x in d) else "NO")
PY
)
  if [ "$shell_running" = "YES" ]; then
    log "SKIP shell-running $sid"
    exit 0
  fi
  [ "$shell_running" = "NO" ] || fail "shell query parse failed"
fi

# A pending form/permission means the session is waiting for the user, not idle.
form_file=$(mktemp "$STATE/form.XXXXXX") || exit 1
perm_file=$(mktemp "$STATE/perm.XXXXXX") || exit 1
trap 'rm -f "$sessions_file" "$active_file" "$form_file" "$perm_file"' EXIT
timeout 25 "$OPENCODE" api get "/api/session/$sid/form" >"$form_file" 2>>"$LOG" || fail "form query failed"
timeout 25 "$OPENCODE" api get "/api/session/$sid/permission" >"$perm_file" 2>>"$LOG" || fail "permission query failed"
pending=$(python3 - "$form_file" "$perm_file" <<'PY'
import json,sys
try:
    f=json.load(open(sys.argv[1])).get("data", [])
    p=json.load(open(sys.argv[2])).get("data", [])
except Exception as e:
    print("ERR %s" % e); raise SystemExit(0)
print("PENDING" if f or p else "NONE")
PY
)
if [ "$pending" != "NONE" ]; then
  log "SKIP waiting-user $sid forms/permissions=$pending"
  exit 0
fi

payload=$(python3 - <<'PY'
import json
print(json.dumps({"text":"定时巡检：先检查子代理/后台 shell/EXIT/任务状态，再盘点队列，不得只看 .tao/tasks 就判空。必须逐项检查：① .tao/tasks 中待开始/待验收/已完成未合并；② discussing.md 中已批准但尚未立册的事项；③ milestones.md 中未完成行；④ issues.yaml 中 open 项；⑤ ADR/任务书中待确认项。只要任一来源存在“已批准、依赖满足、无阻塞”的任务，就当场立任务书、派单、验收或合并；已批准但未立册的必须当场立册，不得以“没有现成任务书”判空；被语义阻塞的任务不等于队列空，应登记阻塞原因并继续找其它可推进项。只有所有来源都没有可推进任务时才停。不要自行修改 SPEC/契约语义，未经授权不要 push。另外做两项一致性检查并给出建议（由主会话处置）：① **台账**：`milestones.md`「进行中」表须与在跑任务一致——有分支/worktree 的任务必须已移入「进行中」并填派单时间；发现漏移直接指出是哪一行；② **清理**：`git worktree list` 之外不得残留任务临时目录（`/tmp/opencode/<任务ID>/`），并检查 `/tmp` 占用（用 `df -h /tmp`）；超过 70% 或有非在用目录时列出可清理项。","delivery":"queue"}, ensure_ascii=False))
PY
)
printf 'DRY-RUN would wake session=%s age=%s\n' "$sid" "$age" >> "$LOG"
if [ "${1:-}" = "--dry-run" ]; then
  log "DRY-RUN $sid age=$age"
  printf 'DRY-RUN target=%s age=%s\n' "$sid" "$age"
  exit 0
fi

if timeout 30 "$OPENCODE" api post "/api/session/$sid/prompt" --data "$payload" >>"$LOG" 2>&1; then
  printf '%s\n' "$now" > "$LAST"
  log "WAKE ok session=$sid age=$age"
else
  log "WAKE failed session=$sid age=$age"
  exit 2
fi
