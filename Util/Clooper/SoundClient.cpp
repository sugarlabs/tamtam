#include <pthread.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>
#include <sys/time.h>

#include <csound/csound.hpp>
#include "SoundClient.h"
#include <vector>

struct ev_t
{
    int onset;
    char type;
    std::vector<MYFLT> param;

    ev_t(char type, MYFLT p1, MYFLT p2, MYFLT p3, MYFLT p4, MYFLT p5, MYFLT p6, MYFLT p7, MYFLT p8, MYFLT p9, MYFLT p10, MYFLT p11, MYFLT p12, MYFLT p13, MYFLT p14, MYFLT p15)
        : onset(onset), type(type), param(15)
    {
        onset = (int) p2;
        param[0] = p1;
        param[1] = 0.0;
        param[2] = p3;
        param[3] = p4;
        param[4] = p5;
        param[5] = p6;
        param[6] = p7;
        param[7] = p8;
        param[8] = p9;
        param[9] = p10;
        param[10] = p11;
        param[11] = p12;
        param[12] = p13;
        param[13] = p14;
        param[14] = p15;
    }
    bool operator<(const ev_t &e) const
    {
        return onset < e.onset;
    }
    void print(FILE *f)
    {
        fprintf(f, "INFO: scoreEvent %c ", type);
        for (size_t i = 0; i < param.size(); ++i) fprintf(f, "%lf ", param[i]);
        fprintf(f, "\n");
    }
};
struct EvLoop
{
    int tick_prev;
    int tickMax;
    double rtick;
    double ticks_per_ksmp;
    size_t pos;
    std::vector<ev_t *> ev;
    CSOUND * csound;
    void * mutex;

    EvLoop(CSOUND * cs) : tick_prev(0), tickMax(1), rtick(0.0), ticks_per_ksmp(0.3333), pos(0), csound(cs), mutex(NULL)
    {
        mutex = csoundCreateMutex(0);
    }
    ~EvLoop()
    {
        csoundLockMutex(mutex);
        for (size_t i = 0; i < ev.size(); ++i)
        {
            delete ev[i];
        }
        csoundUnlockMutex(mutex);
        csoundDestroyMutex(mutex);
    }
    void clear()
    {
        csoundLockMutex(mutex);
        for (size_t i = 0; i < ev.size(); ++i)
        {
            delete ev[i];
        }
        ev.clear();
        csoundUnlockMutex(mutex);
        pos = 0;
    }
    int getTick()
    {
        return (int)rtick % tickMax;
    }
    void setNumTicks(int nticks)
    {
        tickMax = nticks;
        if ((int)rtick > nticks)
        {
            int t = (int)rtick % nticks;
            rtick = t;
        }
    }
    void setTick(int t)
    {
        t = t % tickMax;
        rtick = (double)(t % tickMax);
        //TODO: binary search would be faster
        csoundLockMutex(mutex);
        for (pos = 0; pos < ev.size() && ev[pos]->onset < t; ++pos) ;
        if (ev.size() == pos) pos = 0;
        csoundUnlockMutex(mutex);
    }
    void setTickDuration(double d)
    {
        ticks_per_ksmp = d / csoundGetKr(csound);
    }
    void step(FILE * f)
    {
        if (ev.empty()) return;

        csoundLockMutex(mutex);
        rtick += ticks_per_ksmp;
        int tick = (int)rtick % tickMax;
        if (tick < tick_prev)
        {
            while (pos < ev.size())
            {
                if (f) ev[pos]->print(f);
                csoundScoreEvent(csound, ev[pos]->type, &ev[pos]->param[0], ev[pos]->param.size());
                ++pos;
            }
            pos = 0;
        }
        while ((pos < ev.size()) && (tick >= ev[ pos ]->onset))
        {
            if (f) ev[pos]->print(f);
            csoundScoreEvent(csound, ev[pos]->type, &ev[pos]->param[0], ev[pos]->param.size());
            ++pos;
        }
        csoundUnlockMutex(mutex);
        tick_prev = tick;
    }
    void addEvent(ev_t *e)
    {
        csoundLockMutex(mutex);
        ev.push_back(e);
        csoundUnlockMutex(mutex);
    }
};
struct TamTamSound
{
    void * ThreadID;
    CSOUND * csound;
    enum {CONTINUE, STOP} PERF_STATUS;
    int verbosity;
    FILE * _debug;
    int thread_playloop;
    int thread_measurelag;
    EvLoop * loop;

    TamTamSound(char * orc)
        : ThreadID(NULL), PERF_STATUS(STOP), verbosity(3), _debug(NULL), thread_playloop(0), thread_measurelag(0), loop(NULL)
    {
        _debug = fopen("debug.log", "w");

        csound = csoundCreate(NULL);
        int argc = 2;
        char * prog = "fake_progname";
        char ** argv = (char **) malloc(argc * sizeof(char*));
        argv[0] = prog;
        argv[1] = orc;

        csoundInitialize(&argc, &argv, 0);
        int result = csoundCompile( csound, argc, argv);
        free(argv);
        if (!result)
        {
            //PERF_STATUS = CONTINUE;
            //ThreadID = csoundCreateThread(csThread, (void*)this);
        }
        else
        {
            fprintf(_debug, "ERROR: csoundCompile() returned %i\n", result);
            csoundDestroy(csound);
            csound = NULL;
            ThreadID = NULL;
        }

        loop = new EvLoop(csound);
    }
    ~TamTamSound()
    {
        if (csound)
        {
            stop();
            delete loop;
            csoundDestroy(csound);
        }
        fclose(_debug);
    }
    static double pytime(const struct timeval * tv)
    {
        return (double) tv->tv_sec + (double) tv->tv_usec / 1000000.0;
    }
    uintptr_t thread_fn()
    {
        struct timeval tv;
        double t_prev;
        double m = 0.0;

        int loops = 0;

        while ( (csoundPerformKsmps(csound) == 0) 
                && (PERF_STATUS == CONTINUE))
        {
            if (thread_measurelag)
            {
                gettimeofday(&tv, 0);
                double t_this = pytime(&tv);
                if (loops)
                {
                    if (m < t_this - t_prev)
                    {
                        m = t_this - t_prev;
                        fprintf(_debug, "maximum lag %lf\n", m);
                    }
                }
                t_prev = t_this;
            }
            if (thread_playloop)
            {
                loop->step(_debug);
            }
            ++loops;
        }
        csoundDestroy(csound);
        return 1;
    }
    static uintptr_t csThread(void *clientData)
    {
        return ((TamTamSound*)clientData)->thread_fn();
    }

    void scoreEvent(char type, MYFLT * p, int np)
    {
        if (!csound)
        {
            fprintf(_debug, "ERROR: TamTamSound::%s() csound not loaded\n", __FUNCTION__);
            return;
        }
        if (verbosity > 2)
        {
            fprintf(_debug, "INFO: scoreEvent %c ", type);
            for (int i = 0; i < np; ++i) fprintf(_debug, "%lf ", p[i]);
            fprintf(_debug, "\n");
        }
        csoundScoreEvent(csound, type, p, np);
    }
    void scoreEvent(char type, MYFLT p1, MYFLT p2, MYFLT p3, MYFLT p4, MYFLT p5, MYFLT p6, MYFLT p7, MYFLT p8, MYFLT p9, MYFLT p10, MYFLT p11, MYFLT p12, MYFLT p13, MYFLT p14, MYFLT p15)
    {
        MYFLT p[15];
        p[0] = p1;
        p[1] = p2;
        p[2] = p3;
        p[3] = p4;
        p[4] = p5;
        p[5] = p6;
        p[6] = p7;
        p[7] = p8;
        p[8] = p9;
        p[9] = p10;
        p[10] = p11;
        p[11] = p12;
        p[12] = p13;
        p[13] = p14;
        p[14] = p15;
        scoreEvent(type, p, 15);
    }
    void inputMessage(const char * msg)
    {
        if (!csound)
        {
            fprintf(_debug, "ERROR: TamTamSound::%s() csound not loaded\n", __FUNCTION__);
            return;
        }
        if (verbosity > 2) fprintf(_debug, "%s\n", msg);
        csoundInputMessage(csound, msg);
    }
    bool good()
    {
        return csound != NULL;
    }


    void instrumentLoad(int table, const char * fname)
    {
        char str[512];
        sprintf(str, "f%d 0 0 -1 \"%s\" 0 0 0", table, fname);
        inputMessage(str);
    }
    void instrumentUnloadBatch(int count)
    {
        MYFLT p[4] = {5000.0, 0.0, 0.1, 0.0};
        p[3] = (MYFLT) count;
        scoreEvent('i', p, 4);
    }
    void micRecord(int table)
    {
        MYFLT p[4] = {5201.0, 0.0, 5.0, 0.0};
        p[3] = (MYFLT) table;
        scoreEvent('i', p, 4);
    }
    void setMasterVolume(MYFLT vol)
    {
        MYFLT *p;
        if (!(csoundGetChannelPtr(csound, &p, "masterVolume", CSOUND_CONTROL_CHANNEL | CSOUND_INPUT_CHANNEL)))
            *p = (MYFLT) vol;
        else
        {
            fprintf(_debug, "ERROR: failed to set master volume\n");
        }
    }
    void start()
    {
        if (!ThreadID)
        {
            PERF_STATUS = CONTINUE;
            ThreadID = csoundCreateThread(csThread, (void*)this);
        }
    }
    void stop()
    {
        if (ThreadID)
        {
            PERF_STATUS = STOP;
            if (verbosity > 0) fprintf(_debug, "INFO: stop()");
            uintptr_t rval = csoundJoinThread(ThreadID);
            if (rval) fprintf(stderr, "INFO: thread returned %zu\n", rval);
            ThreadID = NULL;
            csoundReset(csound);
        }
    }

};

TamTamSound * sc_tt = NULL;

int sc_initialize(char * csd)
{
    sc_tt = new TamTamSound(csd);
    if (sc_tt->good()) return 0;
    else return -1;
}
void sc_destroy()
{
    delete sc_tt;
    sc_tt = NULL;
}
void sc_instrumentLoad(int table, const char * fname)
{
    sc_tt->instrumentLoad(table, fname);
}
void sc_instrumentUnloadBatch(int count)
{
    sc_tt->instrumentUnloadBatch(count);
}
void sc_micRecord(int table)
{
    sc_tt->micRecord(table);
}
void sc_setMasterVolume(double v)
{
    sc_tt->setMasterVolume(v);
}
void sc_scoreEvent15(char type, MYFLT p1, MYFLT p2, MYFLT p3, MYFLT p4, MYFLT p5, MYFLT p6, MYFLT p7, MYFLT p8, MYFLT p9, MYFLT p10, MYFLT p11, MYFLT p12, MYFLT p13, MYFLT p14, MYFLT p15)
{
    sc_tt->scoreEvent(type, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12, p13, p14, p15);
}
void sc_start()
{
    sc_tt->start();
}
void sc_stop()
{
    sc_tt->stop();
}

int sc_loop_getTick()
{
    return sc_tt->loop->getTick();
}
void sc_loop_setNumTicks(int nticks)
{
    sc_tt->loop->setNumTicks(nticks);
}
void sc_loop_setTick(int ctick)
{
    sc_tt->loop->setTick(ctick);
}
void sc_loop_setTickDuration(double secs_per_tick)
{
    sc_tt->loop->setTickDuration(secs_per_tick);
}
void sc_loop_addScoreEvent15(char type, MYFLT p1, MYFLT p2, MYFLT p3, MYFLT p4, MYFLT p5, MYFLT p6, MYFLT p7, MYFLT p8, MYFLT p9, MYFLT p10, MYFLT p11, MYFLT p12, MYFLT p13, MYFLT p14, MYFLT p15)
{
    sc_tt->loop->addEvent( new ev_t(type, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12, p13, p14, p15));
}
void sc_loop_clear()
{
    sc_tt->loop->clear();
}
void sc_loop_playing(int tf)
{
    sc_tt->thread_playloop = tf;
}

