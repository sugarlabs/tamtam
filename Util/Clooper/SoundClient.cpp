#include <pthread.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>
#include <sys/time.h>

#include <csound/csound.hpp>
#include "SoundClient.h"
#include <vector>
#include <map>
#include <cmath>

using namespace std;

struct ev_t
{
    char type;
    int onset;
    bool time_in_ticks;
    MYFLT prev_secs_per_tick;
    MYFLT duration, attack, decay;
    std::vector<MYFLT> param;

    ev_t(char type, bool in_ticks, MYFLT p1, MYFLT p2, MYFLT p3, MYFLT p4, MYFLT p5, MYFLT p6, MYFLT p7, MYFLT p8, MYFLT p9, MYFLT p10, MYFLT p11, MYFLT p12, MYFLT p13, MYFLT p14, MYFLT p15)
        : type(type), onset(0), time_in_ticks(in_ticks), param(15)
    {
        onset = (int) p2;
        duration = p3;
        attack = p9;
        decay = p10;
        prev_secs_per_tick = -1.0;

        param[0] = p1;
        param[1] = 0.0; //onset
        param[2] = p3;  //duration
        param[3] = p4;  //pitch
        param[4] = p5;  //reverbSend
        param[5] = p6;  //amplitude
        param[6] = p7;  //pan
        param[7] = p8;  //table
        param[8] = p9;  //attack
        param[9] = p10; //decay
        param[10] = p11;//filterType
        param[11] = p12;//filterCutoff
        param[12] = p13;//loopStart
        param[13] = p14;//loopEnd
        param[14] = p15;//crossDur
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

    void event(CSOUND * csound, MYFLT secs_per_tick)
    {
        if (time_in_ticks && (secs_per_tick != prev_secs_per_tick))
        {
            param[2] = duration * secs_per_tick;
            param[8] = max(0.002f, attack * secs_per_tick);
            param[9] = max(0.002f, decay * secs_per_tick);
            prev_secs_per_tick = secs_per_tick;
            fprintf(stdout, "setting duration to %f\n", param[5]);
        }
        csoundScoreEvent(csound, type, &param[0], param.size());
    }
};
struct EvLoop
{
    int tick_prev;
    int tickMax;
    MYFLT rtick;
    MYFLT secs_per_tick;
    MYFLT ticks_per_ksmp;
    typedef std::pair<int, ev_t *> pair_t;
    typedef std::multimap<int, ev_t *>::iterator iter_t;
    std::multimap<int, ev_t *> ev;
    std::multimap<int, ev_t *>::iterator ev_pos;
    CSOUND * csound;
    void * mutex;

    EvLoop(CSOUND * cs) : tick_prev(0), tickMax(1), rtick(0.0), ev(), ev_pos(ev.end()), csound(cs), mutex(NULL)
    {
        setTickDuration(0.05);
        mutex = csoundCreateMutex(0);
    }
    ~EvLoop()
    {
        csoundLockMutex(mutex);
        for (iter_t i = ev.begin(); i != ev.end(); ++i)
        {
            delete i->second;
        }
        csoundUnlockMutex(mutex);
        csoundDestroyMutex(mutex);
    }
    void clear()
    {
        csoundLockMutex(mutex);
        for (iter_t i = ev.begin(); i != ev.end(); ++i)
        {
            delete i->second;
        }
        ev.erase(ev.begin(), ev.end());
        ev_pos = ev.end();
        csoundUnlockMutex(mutex);
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
        rtick = (MYFLT)(t % tickMax);
        //TODO: binary search would be faster
        csoundLockMutex(mutex);
        ev_pos = ev.lower_bound( t );
        csoundUnlockMutex(mutex);
    }
    void setTickDuration(MYFLT d)
    {
        secs_per_tick = d;
        ticks_per_ksmp = 1.0 / (d * csoundGetKr(csound));
        if (0) fprintf(stderr, "INFO: duration %lf -> ticks_pr_skmp %lf\n", d, ticks_per_ksmp);
    }
    void step(FILE * f)
    {
        rtick += ticks_per_ksmp;
        int tick = (int)rtick % tickMax;
        if (tick == tick_prev) return;

        csoundLockMutex(mutex);
        int events = 0;
        int loop0 = 0;
        int loop1 = 0;
        const int eventMax = 6;  //NOTE: events beyond this number will be ignored!!!
        if (!ev.empty()) 
        {
            if (tick < tick_prev) // should be true only after the loop wraps (not after insert)
            {
                while (ev_pos != ev.end())
                {
                    if (f) ev_pos->second->print(f);
                    if (events < eventMax) ev_pos->second->event(csound, secs_per_tick);
                    ++ev_pos;
                    ++events;
                    ++loop0;
                }
                ev_pos = ev.begin();
            }
            while ((ev_pos != ev.end()) && (tick >= ev_pos->first))
            {
                if (f) ev_pos->second->print(f);
                if (events < eventMax) ev_pos->second->event(csound, secs_per_tick);
                ++ev_pos;
                ++events;
                ++loop1;
            }
        }
        csoundUnlockMutex(mutex);
        tick_prev = tick;
        if (events >= eventMax) fprintf(stderr, "WARNING: %i/%i events at once (%i, %i)\n", events,ev.size(),loop0,loop1);
    }
    void addEvent(ev_t *e)
    {
        csoundLockMutex(mutex);
        ev.insert(pair_t(e->onset, e));
        ev_pos = ev.upper_bound( tick_prev );
        csoundUnlockMutex(mutex);
    }
};
struct TamTamSound
{
    void * ThreadID;
    CSOUND * csound;
    char * csound_orc;
    enum {CONTINUE, STOP} PERF_STATUS;
    int verbosity;
    FILE * _debug;
    int thread_playloop;
    int thread_measurelag;
    EvLoop * loop;

    TamTamSound(char * orc)
        : ThreadID(NULL), csound(NULL), PERF_STATUS(STOP), verbosity(3), _debug(NULL), thread_playloop(0), thread_measurelag(0), loop(NULL)
    {
        _debug = fopen("debug.log", "w");

        csound = csoundCreate(NULL);
        csound_orc = strdup(orc);

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
        free(csound_orc);
        fclose(_debug);
    }
    static double pytime(const struct timeval * tv)
    {
        return (double) tv->tv_sec + (double) tv->tv_usec / 1000000.0;
    }
    uintptr_t thread_fn()
    {
        struct timeval tv;
        double t_prev = 0.0; //value will be ignored
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
        return 0;
    }
    static uintptr_t csThread(void *clientData)
    {
        return ((TamTamSound*)clientData)->thread_fn();
    }
    int start()
    {
        if (!ThreadID)
        {
            int argc=3;
            char  **argv = (char**)malloc(argc*sizeof(char*));
            argv[0] = "csound";
            argv[1] ="-m0";
            argv[2] = csound_orc;
            fprintf(_debug, "loading file %s\n", csound_orc);

            csoundInitialize(&argc, &argv, 0);
            int result = csoundCompile(csound, argc, &(argv[0]));
            free(argv);

            if (!result)
            {
                PERF_STATUS = CONTINUE;
                ThreadID = csoundCreateThread(csThread, (void*)this);
                return 0;
            }
            else
            {
                fprintf(_debug, "ERROR: failed to compile orchestra\n");
                ThreadID =  NULL;
                return 1;
            }
        }
        return 1;
    }
    int stop()
    {
        if (ThreadID)
        {
            PERF_STATUS = STOP;
            if (verbosity > 0) fprintf(_debug, "INFO: stop()");
            uintptr_t rval = csoundJoinThread(ThreadID);
            if (rval) fprintf(_debug, "WARNING: thread returned %zu\n", rval);
            ThreadID = NULL;
            csoundReset(csound);
            return 0;
        }
        return 1;
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

    void setTrackpadX(MYFLT value)
    {
        MYFLT *p;
        if (!(csoundGetChannelPtr(csound, &p, "trackpadX", CSOUND_CONTROL_CHANNEL | CSOUND_INPUT_CHANNEL)))
            *p = (MYFLT) value;
        else
        {
            fprintf(_debug, "ERROR: failed to set trackpad X value\n");
        }
    }

    void setTrackpadY(MYFLT value)
    {
        MYFLT *p;
        if (!(csoundGetChannelPtr(csound, &p, "trackpadY", CSOUND_CONTROL_CHANNEL | CSOUND_INPUT_CHANNEL)))
            *p = (MYFLT) value;
        else
        {
            fprintf(_debug, "ERROR: failed to set trackpad Y value\n");
        }
    }
};

TamTamSound * sc_tt = NULL;

//call once at startup, should return 0
int sc_initialize(char * csd)
{
    sc_tt = new TamTamSound(csd);
    atexit(&sc_destroy);
    if (sc_tt->good()) return 0;
    else return -1;
}
//call once at end
void sc_destroy()
{
    if (sc_tt)
    {
        delete sc_tt;
        sc_tt = NULL;
    }
}
//compile the score, connect to device, start a sound rendering thread
int sc_start()
{
    return sc_tt->start();
}
//stop csound rendering thread, disconnect from sound device, clear tables.
int sc_stop()
{
    return sc_tt->stop();
}
//set the output volume to given level.  max volume is 100.0
void sc_setMasterVolume(MYFLT v)
{
    sc_tt->setMasterVolume(v);
}

void sc_setTrackpadX(MYFLT v)
{
    sc_tt->setTrackpadX(v);
}

void sc_setTrackpadY(MYFLT v)
{
    sc_tt->setTrackpadY(v);
}

void sc_inputMessage(const char *msg)
{
    sc_tt->inputMessage(msg);
}
void sc_scoreEvent4(char type, MYFLT p0, MYFLT p1, MYFLT p2, MYFLT p3)
{
    MYFLT p[4];
    p[0] = p0;
    p[1] = p1;
    p[2] = p2;
    p[3] = p3;
    sc_tt->scoreEvent(type, p, 4);
}
void sc_scoreEvent15(char type, MYFLT p1, MYFLT p2, MYFLT p3, MYFLT p4, MYFLT p5, MYFLT p6, MYFLT p7, MYFLT p8, MYFLT p9, MYFLT p10, MYFLT p11, MYFLT p12, MYFLT p13, MYFLT p14, MYFLT p15)
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
    sc_tt->scoreEvent(type, p, 15);
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
void sc_loop_setTickDuration(MYFLT secs_per_tick)
{
    sc_tt->loop->setTickDuration(secs_per_tick);
}
void sc_loop_addScoreEvent15(int in_ticks, char type, MYFLT p1, MYFLT p2, MYFLT p3, MYFLT p4, MYFLT p5, MYFLT p6, MYFLT p7, MYFLT p8, MYFLT p9, MYFLT p10, MYFLT p11, MYFLT p12, MYFLT p13, MYFLT p14, MYFLT p15)
{
    sc_tt->loop->addEvent( new ev_t(type, in_ticks, p1, p2, p3, p4, p5, p6, p7, p8, p9, p10, p11, p12, p13, p14, p15));
}
void sc_loop_clear()
{
    sc_tt->loop->clear();
}
void sc_loop_playing(int tf)
{
    sc_tt->thread_playloop = tf;
}

