/*
 * musl_sigframe_probe_user.c — end-to-end signal-frame probe for the DADAO
 * musl port (m14-infra-005).
 *
 * Runs as the initramfs `/init.musl` on the real K5 kernel (the K5 syscall
 * selftest execs it, so the production syscall table is in force).  It installs a
 * SIGUSR1 handler, fills one callee-saved slot of every 寄存器组 with a
 * sentinel, raises the signal with a bare `trap cfx_umon, 0` whose following
 * instruction is a global label, and reports what the handler was handed:
 *
 *   - rd[32] / rb[32] / rf[32]  (sentinel values, one per group)
 *   - status                    (the frame's mode word; DADAO_STATUS_USER)
 *   - ra[0]                     ({RACNT, MRPTR}, must be a live RAS state)
 *   - ip                        (must equal the label right after the trap:
 *                                the kernel resumes 4 bytes on)
 *
 * Then the handler returns through musl's __restore_rt (SA_SIGINFO selects
 * it in src/signal/sigaction.c) and the main flow must continue; a second
 * round uses a plain handler (no SA_SIGINFO) so the other restorer entry,
 * __restore, is exercised as well.  A third round installs a sigaltstack and
 * checks the frame is built inside it (SA_ONSTACK).  The last round asks the
 * kernel for its own sigaltstack bounds: below MINSIGSTKSZ the call must be
 * refused (ENOMEM), at and above it accepted.
 *
 * Output is one `SIGFRAME <key>=<value>` line per fact on fd 1 (write(2)
 * directly, so a phase that dies still leaves its lines behind); the gate
 * parses those lines.  Exit status 0 = every phase reached its end.
 */
#include <signal.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
#include <sys/syscall.h>

#define SENT_RD 0x1234UL
#define SENT_RB 0x5678UL
#define SENT_RF 0x9abcUL

static char out[128];

static unsigned long slen(const char *s)
{
	unsigned long n = 0;
	while (s[n])
		n++;
	return n;
}

static void emit_key(const char *key, unsigned long value)
{
	static const char hex[] = "0123456789abcdef";
	char *p = out;
	unsigned long n = slen(key);
	int i;

	for (i = 0; i < (int)n; i++)
		*p++ = key[i];
	*p++ = '=';
	*p++ = '0';
	*p++ = 'x';
	for (i = 60; i >= 0; i -= 4)
		*p++ = hex[(value >> i) & 0xf];
	*p++ = '\n';
	write(1, out, p - out);
}

static void emit_str(const char *key, const char *value)
{
	char *p = out;
	unsigned long n = slen(key);
	int i;
	for (i = 0; i < (int)n; i++)
		*p++ = key[i];
	*p++ = '=';
	while (*value)
		*p++ = *value++;
	*p++ = '\n';
	write(1, out, p - out);
}

/* "SIGFRAME sigaltstack.<size>.<field>=<value>" without printf. */
static void emit_size(int size, const char *field, long value)
{
	char key[48];
	char digits[8];
	char *p = key;
	const char *q;
	int n = 0;

	for (q = "SIGFRAME sigaltstack."; *q; q++)
		*p++ = *q;
	do {
		digits[n++] = (char)('0' + size % 10);
		size /= 10;
	} while (size);
	while (n)
		*p++ = digits[--n];
	*p++ = '.';
	for (q = field; *q; q++)
		*p++ = *q;
	*p = '\0';
	emit_key(key, (unsigned long)value);
}

/* Filled by the handler, printed by the main flow (the handler prints its own
 * lines too, but these keep the ordering verifiable). */
static volatile unsigned long frame_ip, frame_rd32, frame_rb32, frame_rf32;
static volatile unsigned long frame_status, frame_ra0, frame_alt;
static volatile unsigned long handler_sp;

extern char sig_after_trap[];

/* SP = rb1.  __builtin_frame_address(0) is not usable on this ABI (clang
 * answers 0 when the frame pointer is not materialised), so read the register
 * the same way arch/dadao/pthread_arch.h reads the TP. */
static unsigned long read_sp(void)
{
	register unsigned long sp __asm__("rd9");
	__asm__ __volatile__("rb2rd {rd9}, {rb1}" : "=r"(sp) : : "memory");
	return sp;
}

static void siginfo_handler(int sig, siginfo_t *info, void *ctx)
{
	ucontext_t *uc = ctx;

	(void)sig;
	(void)info;
	frame_ip = uc->uc_mcontext.ip;
	frame_rd32 = uc->uc_mcontext.rd[32];
	frame_rb32 = uc->uc_mcontext.rb[32];
	frame_rf32 = uc->uc_mcontext.rf[32];
	frame_status = uc->uc_mcontext.status;
	frame_ra0 = uc->uc_mcontext.ra[0];
	frame_alt = (unsigned long)uc->uc_stack.ss_sp;
	handler_sp = read_sp();

	emit_str("SIGFRAME handler", "ran");
	emit_key("SIGFRAME handler.ip", frame_ip);
	emit_key("SIGFRAME handler.rd32", frame_rd32);
	emit_key("SIGFRAME handler.rb32", frame_rb32);
	emit_key("SIGFRAME handler.rf32", frame_rf32);
	emit_key("SIGFRAME handler.status", frame_status);
	emit_key("SIGFRAME handler.ra0", frame_ra0);
	emit_key("SIGFRAME handler.sp", handler_sp);
	emit_key("SIGFRAME handler.altbase", frame_alt);
	emit_key("SIGFRAME handler.ucflags", uc->uc_flags);
}

static void plain_handler(int sig)
{
	(void)sig;
	emit_str("SIGFRAME plain", "ran");
}

/* Raise `sig` to this process with the sentinels live in the four 寄存器组.
 * Contract-syscall §3: kill = SYS_kill in rd15, pid_t in rd16, int in rd17.
 * The global label right after the trap is the address the kernel must
 * resume at (its dispatch policy adds 4 bytes to the trap's ip). */
__attribute__((noinline))
static void raise_with_sentinels(int sig)
{
	register long nr __asm__("rd15") = SYS_kill;
	register long pid __asm__("rd16") = (long)getpid();
	register long arg __asm__("rd17") = sig;

	__asm__ __volatile__(
		"set.zw rd32, wp0, 0x1234\n\t"
		"set.zw rb32, wp0, 0x5678\n\t"
		"set.fo rf32, 0x9abc\n\t"
		"trap cfx_umon, 0\n\t"
		".globl sig_after_trap\n\t"
		"sig_after_trap:\n\t"
		:
		: "r"(nr), "r"(pid), "r"(arg)
		: "rd32", "rb32", "rf32", "memory");
}

static char altstack[SIGSTKSZ] __attribute__((aligned(16)));
static char smallstack[2048] __attribute__((aligned(16)));

int main(void)
{
	struct sigaction sa;
	stack_t ss;
	int rc;

	emit_str("SIGFRAME begin", "m14-infra-005");

	/* Round 1: SA_SIGINFO -> __restore_rt, sentinels in all four groups. */
	memset(&sa, 0, sizeof sa);
	sa.sa_sigaction = siginfo_handler;
	sa.sa_flags = SA_SIGINFO;
	sigemptyset(&sa.sa_mask);
	if (sigaction(SIGUSR1, &sa, 0) != 0) {
		emit_key("SIGFRAME install.errno", errno);
		return 2;
	}
	emit_key("SIGFRAME minsigstksz", MINSIGSTKSZ);
	emit_key("SIGFRAME sigstksz", SIGSTKSZ);
	emit_key("SIGFRAME frame-size", sizeof(ucontext_t));
	emit_key("SIGFRAME mc-off",
		 (unsigned long)__builtin_offsetof(ucontext_t, uc_mcontext));
	emit_key("SIGFRAME ip-off",
		 (unsigned long)__builtin_offsetof(ucontext_t, uc_mcontext.ip));
	emit_key("SIGFRAME rd-off",
		 (unsigned long)__builtin_offsetof(ucontext_t, uc_mcontext.rd));
	emit_key("SIGFRAME ra-off",
		 (unsigned long)__builtin_offsetof(ucontext_t, uc_mcontext.ra));
	emit_key("SIGFRAME rf-off",
		 (unsigned long)__builtin_offsetof(ucontext_t, uc_mcontext.rf));
	emit_key("SIGFRAME sigmask-off",
		 (unsigned long)__builtin_offsetof(ucontext_t, uc_sigmask));
	emit_key("SIGFRAME sigmask-size", sizeof(sigset_t));
	emit_key("SIGFRAME sa-restorer-flag", SA_RESTORER);

	raise_with_sentinels(SIGUSR1);
	emit_key("SIGFRAME resume-label", (unsigned long)sig_after_trap);
	emit_key("SIGFRAME rd32-sentinel", SENT_RD);
	emit_key("SIGFRAME rb32-sentinel", SENT_RB);
	emit_key("SIGFRAME rf32-sentinel", SENT_RF);
	emit_str("SIGFRAME after-handler", "ran");

	/* Round 2: the plain (non-SA_SIGINFO) handler selects __restore. */
	memset(&sa, 0, sizeof sa);
	sa.sa_handler = plain_handler;
	sigemptyset(&sa.sa_mask);
	if (sigaction(SIGUSR2, &sa, 0) != 0) {
		emit_key("SIGFRAME install2.errno", errno);
		return 3;
	}
	rc = kill(getpid(), SIGUSR2);
	emit_key("SIGFRAME plain.kill", (unsigned long)rc);
	emit_str("SIGFRAME after-plain", "ran");

	/* Round 3: SA_ONSTACK -- the frame must be built on the alternate stack. */
	memset(&sa, 0, sizeof sa);
	sa.sa_sigaction = siginfo_handler;
	sa.sa_flags = SA_SIGINFO | SA_ONSTACK;
	sigemptyset(&sa.sa_mask);
	if (sigaction(SIGUSR1, &sa, 0) != 0) {
		emit_key("SIGFRAME install3.errno", errno);
		return 4;
	}
	ss.ss_sp = altstack;
	ss.ss_flags = 0;
	ss.ss_size = sizeof altstack;
	rc = sigaltstack(&ss, 0);
	emit_key("SIGFRAME altstack.install", (unsigned long)rc);
	frame_alt = 0;
	handler_sp = 0;
	raise_with_sentinels(SIGUSR1);
	emit_key("SIGFRAME altstack.base", (unsigned long)altstack);
	emit_key("SIGFRAME altstack.end", (unsigned long)(altstack + sizeof altstack));
	emit_key("SIGFRAME altstack.sp", handler_sp);
	emit_key("SIGFRAME altstack.insideness",
		 handler_sp >= (unsigned long)altstack &&
		 handler_sp < (unsigned long)(altstack + sizeof altstack));
	emit_key("SIGFRAME after-altstack", 1);

	/* Round 4: the kernel's own sigaltstack bounds, at the two sides of the
	 * libc minimum: anything below MINSIGSTKSZ (2376 = the frame size) is
	 * refused with ENOMEM, the minimum itself and a bigger stack accepted. */
	ss.ss_flags = 0;
	ss.ss_sp = smallstack;

	ss.ss_size = 1024;
	errno = 0;
	rc = sigaltstack(&ss, 0);
	emit_size(1024, "rc", rc);
	emit_size(1024, "errno", errno);

	ss.ss_size = 2375;
	errno = 0;
	rc = sigaltstack(&ss, 0);
	emit_size(2375, "rc", rc);
	emit_size(2375, "errno", errno);

	ss.ss_size = 2376;
	errno = 0;
	rc = sigaltstack(&ss, 0);
	emit_size(2376, "rc", rc);

	ss.ss_sp = altstack;			/* leave a consistent alternate stack */
	ss.ss_size = sizeof altstack;
	errno = 0;
	rc = sigaltstack(&ss, 0);
	emit_size(8192, "rc", rc);

	emit_str("SIGFRAME after-bounds", "ran");
	emit_key("SIGFRAME done", 1);
	return 0;
}
