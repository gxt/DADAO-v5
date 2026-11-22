/* picolibc_clock_probe.c — picolibc clock() 与 gettimeofday 一致性探针
 * （m16-testcases-011 从 `ansibench_clock_probe.c` 改名归位：它只验证
 * picolibc 的 times()/clock() 口径，与 ansibench 四件无依赖）。
 *
 * 判据（ADR-0058 D5 ①）：同一段忙等里，clock()/CLOCKS_PER_SEC 与
 * gettimeofday() 的秒数在 5% 内一致。semihosting 的 clock() 走
 * SYS_ELAPSED（tick 频率 SYS_TICKFREQ），gettimeofday() 也按同一 tick 频率
 * 缩放，所以二者应一致。
 *
 * 历史对照（只记录、不作断言）：修 ISS-502 之前 picolibc 的 times() 不按
 * SYS_TICKFREQ 缩放，clock()/CLOCKS_PER_SEC 报出的秒数比真实值大 1000×
 * （基线日志里 raw≈94.7 s vs wall≈0.095 s）。m15-infra-010 已更正 times()，
 * 本探针只按修后口径判定。
 *
 * 探针只打印观测值（clock 秒数、wall 秒数、相对差）；5% 断言在驱动
 * `run_picolibc_clock_probe.py` 里做。忙等是固定的，不做时间校准。
 */
#include <stdio.h>
#include <sys/time.h>
#include <time.h>

static double
seconds_since(const struct timeval *a, const struct timeval *b)
{
    return (double)(b->tv_sec - a->tv_sec) +
           (double)(b->tv_usec - a->tv_usec) / 1e6;
}

int
main(void)
{
    struct timeval w0, w1;
    clock_t c0, c1;
    volatile unsigned long acc = 0;
    unsigned long i;
    double wall, clk;

    gettimeofday(&w0, NULL);
    c0 = clock();
    for (i = 0; i < 10000000UL; i++)
        acc += i;
    c1 = clock();
    gettimeofday(&w1, NULL);

    wall = seconds_since(&w0, &w1);
    clk = (double)(c1 - c0) / (double)CLOCKS_PER_SEC;
    printf("probe clock=%.6f wall=%.6f rel=%+.4f acc=%lu\n",
           clk, wall, wall > 0.0 ? (clk - wall) / wall : 0.0, acc);
    return 0;
}
