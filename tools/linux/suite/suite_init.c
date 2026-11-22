// SPDX-License-Identifier: GPL-2.0
/*
 * suite_init.c — PID 1 of the kselftest suite image (m18-linux-005).
 *
 * The K6 image hands PID 1 to busybox's `sh`; the suite image must not depend
 * on that shell, must give every test a *guest-side* per-case timeout, and must
 * bracket each test's output with markers the host can attribute it by.  So the
 * suite's `/init` is this supervisor:
 *
 *   1. mount `/proc` (proc) and a writable `/tmp` (ramfs, tmpfs as fallback);
 *   2. read `/cases` — one `<id> <timeout-seconds> <argv...>` line per test;
 *   3. for each case: print `SUITE CASE BEGIN <id>`, fork+exec the test, arm
 *      `alarm(timeout)` (kernel tick based — ADR-0058), and print
 *      `SUITE CASE END <id> rc=<n> status=<exit|timeout|signal>`;
 *   4. print `SUITE DONE` and park (the host stops QEMU on that marker).
 *
 * The supervisor blocks in `waitpid()` and relies on SIGALRM (kernel tick based,
 * ADR-0058) to break out: a test that overruns its own budget is recorded as
 * `timeout` and killed.  A test that wedges the *kernel* — e.g. the
 * `timers/nanosleep` absolute-time sleep observed in this pilot — also stops the
 * tick, so no guest-side net can fire; `run_suite.py` ends that run on its
 * no-progress timeout and labels the case `HOST_TIMEOUT`.
 *
 * Exit status: the supervisor never returns; the host kills QEMU after
 * `SUITE DONE`.  A missing `/cases`, an unreadable line or a failed fork is
 * printed as `SUITE FATAL: ...` and also ends in `SUITE DONE` so the run is
 * still collected (and judged) instead of hanging until the host timeout.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#define MAX_CASES 64
#define MAX_ARGS 8
#define LINE_MAX_LEN 512

struct case_spec {
	char id[64];
	unsigned int timeout;
	char *argv[MAX_ARGS + 1];
	char line[LINE_MAX_LEN];
};

static volatile sig_atomic_t timed_out;

static void on_alarm(int sig)
{
	(void)sig;
	timed_out = 1;
}

static void say(const char *fmt, ...)
{
	va_list ap;

	va_start(ap, fmt);
	vfprintf(stdout, fmt, ap);
	va_end(ap);
	fflush(stdout);
}

/* Split `line` in place on spaces; returns the token count or -1 on overflow. */
static int split(char *line, char *tok[], int max_tokens)
{
	int count = 0;
	char *p = line;

	while (*p) {
		while (*p == ' ' || *p == '\t')
			p++;
		if (!*p || *p == '\n' || *p == '#')
			break;
		if (count == max_tokens)
			return -1;
		tok[count++] = p;
		while (*p && *p != ' ' && *p != '\t' && *p != '\n')
			p++;
		if (*p)
			*p++ = '\0';
	}
	return count;
}

/* ramfs is always built in; tmpfs is only there if the image enabled it. */
static void setup_mounts(void)
{
	if (mount("proc", "/proc", "proc", 0, ""))
		say("SUITE MOUNT /proc rc=%d type=proc errno=%d\n", -1, errno);
	else
		say("SUITE MOUNT /proc rc=0 type=proc errno=0\n");

	if (mount("none", "/tmp", "ramfs", 0, "") &&
	    mount("none", "/tmp", "tmpfs", 0, ""))
		say("SUITE MOUNT /tmp rc=%d type=ramfs,tmpfs errno=%d\n", -1, errno);
	else
		say("SUITE MOUNT /tmp rc=0 type=ramfs-or-tmpfs errno=0\n");
}

static int load_cases(struct case_spec *cases)
{
	char *text;
	ssize_t len;
	int fd, count = 0, offset = 0;

	fd = open("/cases", O_RDONLY);
	if (fd < 0) {
		say("SUITE FATAL: open(/cases) errno=%d\n", errno);
		return 0;
	}
	text = malloc(65536);
	if (!text) {
		close(fd);
		say("SUITE FATAL: out of memory for /cases\n");
		return 0;
	}
	len = read(fd, text, 65535);
	close(fd);
	if (len <= 0) {
		say("SUITE FATAL: read(/cases) len=%ld errno=%d\n", (long)len, errno);
		free(text);
		return 0;
	}
	text[len] = '\0';

	while (offset < len && count < MAX_CASES) {
		char *line = text + offset;
		char *nl = strchr(line, '\n');
		char *tok[MAX_ARGS + 3];
		int ntok, i;

		if (nl)
			*nl = '\0';
		offset += (nl ? (size_t)(nl - line) + 1 : (size_t)strlen(line) + 1);
		if (strlen(line) >= LINE_MAX_LEN) {
			say("SUITE FATAL: /cases line too long\n");
			continue;
		}
		if (line[0] == '#' || line[0] == '\0')
			continue;
		snprintf(cases[count].line, sizeof(cases[count].line), "%s", line);
		ntok = split(cases[count].line, tok, MAX_ARGS + 2);
		if (ntok < 3 || ntok > MAX_ARGS + 2) {
			say("SUITE FATAL: bad /cases line (%d tokens)\n", ntok);
			continue;
		}
		snprintf(cases[count].id, sizeof(cases[count].id), "%s", tok[0]);
		cases[count].timeout = (unsigned int)strtoul(tok[1], NULL, 10);
		if (cases[count].timeout == 0) {
			say("SUITE FATAL: case %s has timeout 0\n", cases[count].id);
			continue;
		}
		for (i = 2; i < ntok; i++)
			cases[count].argv[i - 2] = tok[i];
		cases[count].argv[ntok - 2] = NULL;
		count++;
	}
	free(text);
	return count;
}

static void reap_zombies(void)
{
	while (waitpid(-1, NULL, WNOHANG) > 0)
		;
}

static void run_case(const struct case_spec *spec)
{
	pid_t pid;
	int status = 0, rc;

	say("SUITE CASE BEGIN %s\n", spec->id);
	fflush(stdout);
	reap_zombies();
	timed_out = 0;

	pid = fork();
	if (pid == 0) {
		execv(spec->argv[0], spec->argv);
		fprintf(stdout, "SUITE FATAL: execv(%s) errno=%d\n",
			spec->argv[0], errno);
		fflush(stdout);
		_exit(127);
	}
	if (pid < 0) {
		say("SUITE CASE END %s rc=127 status=exit\n", spec->id);
		return;
	}

	alarm(spec->timeout);
	for (;;) {
		pid_t got = waitpid(pid, &status, 0);

		if (got == pid)
			break;
		if (got < 0 && errno == EINTR) {
			if (timed_out) {
				say("SUITE CASE END %s rc=124 status=timeout\n",
				    spec->id);
				kill(pid, SIGKILL);
				alarm(0);
				return;
			}
			continue;
		}
		/* ECHILD or anything else: the case cannot be attributed. */
		say("SUITE CASE END %s rc=125 status=exit\n", spec->id);
		alarm(0);
		return;
	}
	alarm(0);

	if (WIFEXITED(status)) {
		rc = WEXITSTATUS(status);
		say("SUITE CASE END %s rc=%d status=exit\n", spec->id, rc);
	} else if (WIFSIGNALED(status)) {
		rc = 128 + WTERMSIG(status);
		say("SUITE CASE END %s rc=%d status=signal\n", spec->id, rc);
	} else {
		say("SUITE CASE END %s rc=125 status=exit\n", spec->id);
	}
}

int main(void)
{
	static struct case_spec cases[MAX_CASES];
	struct sigaction sa;
	int count, i;

	setvbuf(stdout, NULL, _IOLBF, 0);

	memset(&sa, 0, sizeof(sa));
	sigemptyset(&sa.sa_mask);
	sa.sa_handler = on_alarm;
	sigaction(SIGALRM, &sa, NULL);

	setup_mounts();
	say("SUITE START\n");

	count = load_cases(cases);
	for (i = 0; i < count; i++)
		run_case(&cases[i]);

	say("SUITE DONE\n");
	for (;;)
		pause();
	return 0;
}
