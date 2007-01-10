
#include <pthread.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>
#include <sys/time.h>

int usleep(int);
static void * threadfn(void * _arg)
{
    double pytime(const struct timeval * tv)
    {
        return (double) tv->tv_sec + (double) tv->tv_usec / 1000000.0;
    }
    struct timeval tv0, tv1;
    double m = 0.0;
    double sleeptime = 0.05;

    while (1)
    {
        gettimeofday(&tv0, 0);
        usleep( (int) (sleeptime * 1000000) );
        gettimeofday(&tv1, 0);
        double t0 = pytime(&tv0);
        double t1 = pytime(&tv1);
        if (t1 - t0 > 2.0 * sleeptime)
        {
            fprintf(stderr, "critical lagginess %lf\n", t1 - t0);
        }
        if (m < t1 - t0)
        {
            m = t1 - t0;
            fprintf(stderr, "maximum lag %lf\n", m);
        }
    }
    return NULL;
}
void testtimer()
{
    pthread_t pth;

    pthread_create( &pth, NULL, &threadfn, NULL );
}

