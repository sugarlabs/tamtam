#include <Python.h>

#include <pthread.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>
#include <sys/time.h>
#include <sched.h>

#include <vector>
#include <map>
#include <cmath>

#include <csound/csound.h>
#include <alsa/asoundlib.h>

static double pytime(const struct timeval * tv)
{
    struct timeval t;
    if (!tv)
    {
        tv = &t;
        gettimeofday(&t, NULL);
    }
    return (double) tv->tv_sec + (double) tv->tv_usec / 1000000.0;
}
#include "log.cpp"
#include "audio.cpp"

#define ERROR_HERE if (_debug && (VERBOSE > 0)) fprintf(_debug, "ERROR: %s:%i\n", __FILE__, __LINE__)

#define IF_DEBUG(N) if (_debug && (VERBOSE > N))
#define FLOAT_TO_SHORT(in,out)  __asm__ __volatile__ ("fistps %0" : "=m" (out) : "t" (in) : "st") ;

int VERBOSE = 3;
FILE * _debug = NULL;
struct TamTamSound;
TamTamSound * sc_tt = NULL;
log_t * g_log = NULL;

/**
 * ev_t is the type of event that Clooper puts in the loop buffer.
 * It corresponds to a line of csound that starts with an 'i'
 */
struct ev_t
{
    char type;  ///< if this event were listed in a csound file, the line would begin with this letter
    int onset;  ///< the onset time of this event (its temporal position)
    bool time_in_ticks; ///< if true, then some parameters will be updated according to the tempo
    bool active; ///< if true, then event() will actually do something
    MYFLT prev_secs_per_tick; ///< normally used for ____, sometimes set to -1 to force recalculation of param[] entries
    MYFLT duration, attack, decay;///< canonical values of some tempo-dependent parameters
    std::vector<MYFLT> param;     ///< parameter buffer for csound

    ev_t(char type, MYFLT * p, int param_count, bool in_ticks, bool active)
        : type(type), onset(0), time_in_ticks(in_ticks), active(active), param(param_count)
    {
        assert(param_count >= 4);
        onset = (int) p[1];
        duration = p[2];
        attack = param_count > 8 ? p[8]: 0.0; //attack
        decay = param_count > 9 ? p[9]: 0.0; //decay
        prev_secs_per_tick = -1.0;
        for (int i = 0; i < param_count; ++i) param[i] = p[i];

        param[1] = 0.0; //onset
    }
    /*
    bool operator<(const ev_t &e) const
    {
        return onset < e.onset;
    }
    */
    void ev_print(FILE *f)
    {
        fprintf(f, "INFO: scoreEvent %c ", type);
        for (size_t i = 0; i < param.size(); ++i) fprintf(f, "%lf ", param[i]);
        fprintf(f, "[%s]\n", active ? "active": "inactive");
    }
    /**
     *  Update the idx'th param value to have a certain value.
     *
     * Certain of the parameters are linked in strange hack-y ways, as defined by
     * the constructor, and update()  (which should be consistent with one another!)
     *
     * These events are for use with the file: TamTam/Resources/univorc.csd.
     * So that file defines how the parameters will be interpreted by csound.
     */
    void update(int idx, MYFLT val)
    {
        if ( (unsigned)idx >= param.size())
        {
            if (_debug && (VERBOSE > 0)) fprintf(_debug, "ERROR: updateEvent request for too-high parameter %i\n", idx);
            return;
        }
        if (time_in_ticks)
        {
            switch(idx)
            {
                case 1: onset = (int) val; break;
                case 2: duration =    val; break;
                case 8: attack =      val; break;
                case 9: decay  =      val; break;
                default: param[idx] = val; break;
            }
            prev_secs_per_tick = -1.0; //force recalculation
        }
        else
        {
            param[idx] = val;
        }
    }
    /**
     * An ev_t instance can be in an active or inactive state.  If an ev_t instance
     * is active, then event() will call a corresponding csoundScoreEvent().  If an
     * ev_t instance is inactive, then event() is a noop.
     */
    void activate_cmd(int cmd)
    {
        switch(cmd)
        {
            case 0: active = false; break;
            case 1: active = true; break;
            case 2: active = !active; break;
        }
    }

    /**
     * Iff this instance is active, this call generates a csound event.
     * Parameters are passed directly as a buffer of floats.  If secs_per_tick
     * != prev_secs_per_tick (possibly because prev_secs_per_tick was set to -1
     * by update() ) then this call will do some floating point ops to
     * recalculate the parameter buffer.
     */
    void event(CSOUND * csound, MYFLT secs_per_tick)
    {
        if (!active) return;

        if (time_in_ticks && (secs_per_tick != prev_secs_per_tick))
        {
            param[2] = duration * secs_per_tick;
            if (param.size() > 8) param[8] = std::max(0.002f, attack * param[2]);
            if (param.size() > 9) param[9] = std::max(0.002f, decay * param[2]);
            prev_secs_per_tick = secs_per_tick;
            if (_debug && (VERBOSE > 2)) fprintf(_debug, "setting duration to %f\n", param[5]);
        }
        csoundScoreEvent(csound, type, &param[0], param.size());
    }
};

/** 
 *
 * EvLoop is a repeat-able loop of ev_t instances.
 * */
struct EvLoop
{
    int tick_prev;
    int tickMax;
    MYFLT rtick;
    MYFLT secs_per_tick;
    typedef std::pair<int, ev_t *> pair_t;
    typedef std::multimap<int, ev_t *>::iterator iter_t;
    typedef std::map<int, iter_t>::iterator idmap_t;

    std::multimap<int, ev_t *> ev;
    std::multimap<int, ev_t *>::iterator ev_pos;
    std::map<int, iter_t> idmap;
    CSOUND * csound;
    void * mutex; //this is locked when changing ev
    int steps;    // 
    TamTamSound * tt;

    EvLoop(CSOUND * cs, TamTamSound * tt) : tick_prev(0), tickMax(1), rtick(0.0), ev(), ev_pos(ev.end()), csound(cs), mutex(NULL), steps(0), tt(tt)
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
        idmap.erase(idmap.begin(), idmap.end());
        csoundUnlockMutex(mutex);
    }
    void deactivateAll()
    {
        csoundLockMutex(mutex); //not really necessary I think
        for (iter_t i = ev.begin(); i != ev.end(); ++i)
        {
            i->second->activate_cmd(0);
        }
        csoundUnlockMutex(mutex);
    }
    int getTick()
    {
        return (int)rtick % tickMax;
    }
    float getTickf(bool mod)
    {
        if (mod)
        {
            return fmod(rtick, (MYFLT)tickMax);
        }
        else
        {
            return rtick;
        }
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
        if (!csound) {
            if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping setTickDuration, csound==NULL\n");
            return;
        }
        secs_per_tick = d;
    }
    /**  advance in play loop by rtick_inc ticks, possibly generate some
     * csoundScoreEvent calls.
     */
    void step(MYFLT rtick_inc )
    {
        rtick += rtick_inc;
        int tick = (int)rtick % tickMax;
        if (tick == tick_prev) return;

        csoundLockMutex(mutex);
        int events = 0;
        int loop0 = 0;
        int loop1 = 0;
        const int eventMax = 8;  //NOTE: events beyond this number will be ignored!!!
        if (!ev.empty()) 
        {
            if (steps && (tick < tick_prev)) // should be true only after the loop wraps (not after insert)
            {
                while (ev_pos != ev.end())
                {
                    if (_debug && (VERBOSE > 3)) ev_pos->second->ev_print(_debug);
                    if (events < eventMax) ev_pos->second->event(csound, secs_per_tick);
                    ++ev_pos;
                    ++events;
                    ++loop0;
                }
                ev_pos = ev.begin();
            }
            while ((ev_pos != ev.end()) && (tick >= ev_pos->first))
            {
                if (_debug && (VERBOSE > 3)) ev_pos->second->ev_print(_debug);
                if (events < eventMax) ev_pos->second->event(csound, secs_per_tick);
                ++ev_pos;
                ++events;
                ++loop1;
            }
        }
        csoundUnlockMutex(mutex);
        tick_prev = tick;
        if (_debug && (VERBOSE>1) && (events >= eventMax)) fprintf(_debug, "WARNING: %i/%i events at once (%i, %i)\n", events,ev.size(),loop0,loop1);
        ++steps;
    }
    void addEvent(int id, char type, MYFLT * p, int np, bool in_ticks, bool active)
    {
        ev_t * e = new ev_t(type, p, np, in_ticks, active);

        idmap_t id_iter = idmap.find(id);
        if (id_iter == idmap.end())
        {
            //this is a new id
            csoundLockMutex(mutex);

            iter_t e_iter = ev.insert(pair_t(e->onset, e));

            //TODO: optimize by thinking about whether to do ev_pos = e_iter
            ev_pos = ev.upper_bound( tick_prev );
            idmap[id] = e_iter;

            csoundUnlockMutex(mutex);
        }
        else
        {
            if (_debug && (VERBOSE > 0)) fprintf(_debug, "ERROR: skipping request to add duplicate note %i\n", id);
        }
    }
    void delEvent(int id)
    {
        idmap_t id_iter = idmap.find(id);
        if (id_iter == idmap.end())
        {
            if (_debug && (VERBOSE > 0)) fprintf(_debug, "ERROR: delEvent request for unknown note %i\n", id);
        }
        else
        {
            csoundLockMutex(mutex);
            iter_t e_iter = id_iter->second;//idmap[id];
            if (e_iter == ev_pos) ++ev_pos;

            delete e_iter->second;
            ev.erase(e_iter);
            idmap.erase(id_iter);

            csoundUnlockMutex(mutex);
        }
    }
    void updateEvent(int id, int idx, float val, int activate_cmd)
    {
        idmap_t id_iter = idmap.find(id);
        if (id_iter == idmap.end())
        {
            if (_debug && (VERBOSE > 0)) fprintf(_debug, "ERROR: updateEvent request for unknown note %i\n", id);
            return;
        }

        //this is a new id
        csoundLockMutex(mutex);
        iter_t e_iter = id_iter->second;
        ev_t * e = e_iter->second;
        int onset = e->onset;
        e->update(idx, val);
        e->activate_cmd(activate_cmd);
        if (onset != e->onset)
        {
            ev.erase(e_iter);

            e_iter = ev.insert(pair_t(e->onset, e));

            //TODO: optimize by thinking about whether to do ev_pos = e_iter
            ev_pos = ev.upper_bound( tick_prev );
            idmap[id] = e_iter;
        }
        csoundUnlockMutex(mutex);
    }
    void reset()
    {
        steps = 0;
    }
};

/**
 * The main object of control in the Clooper plugin.
 *
 * This guy controls the sound rendering thread, loads and unloads ALSA, 
 * maintains a csound instance, and maintains a subset of notes from the
 * currently-loaded TamTam.
 */
struct TamTamSound
{
    /** the id of an running sound-rendering thread, or NULL */
    void * ThreadID;
    /** a flag to tell the thread to continue, or break */
    enum {CONTINUE, STOP} PERF_STATUS;
    /** our csound object, NULL iff there was a problem creating it */
    CSOUND * csound;

    EvLoop * loop;
    /** a flag, true iff the thread should play&advance the loop */
    int thread_playloop;

    /** the upsampling ratio from csound */
    unsigned int csound_ksmps;
    snd_pcm_uframes_t csound_frame_rate;
    snd_pcm_uframes_t csound_period_size;
    snd_pcm_uframes_t period0;
    unsigned int period_per_buffer; //should be 2
    int up_ratio;  //if the hardware only supports a small integer multiple of our effective samplerate, do a real-time conversion

    MYFLT ticks_per_period, tick_adjustment; //the default time increment in thread_fn

    log_t * ll;
    SystemStuff * sys_stuff;

    TamTamSound(log_t * ll, char * orc, snd_pcm_uframes_t period0, unsigned int ppb, int ksmps, int framerate )
        : ThreadID(NULL), PERF_STATUS(STOP), csound(NULL),
        loop(NULL), thread_playloop(0),
        csound_ksmps(ksmps),                    //must agree with the orchestra file
        csound_frame_rate(framerate),           //must agree with the orchestra file
        period0(period0),
        period_per_buffer(ppb),
        up_ratio(1),
        ticks_per_period(1.0),
        tick_adjustment(0.0),
        ll( ll ),
        sys_stuff(NULL)
    {
        sys_stuff = new SystemStuff(ll);
        if (0 > sys_stuff->open(csound_frame_rate, 4, period0, period_per_buffer))
        {
            return;
        }
        sys_stuff->close(0);
        up_ratio = sys_stuff->rate / csound_frame_rate;
        csound_period_size = (sys_stuff->period_size % up_ratio == 0)
                  ? sys_stuff->period_size / up_ratio
                  : csound_ksmps * 4;

        csound = csoundCreate(NULL);
        int argc=3;
        char  **argv = (char**)malloc(argc*sizeof(char*));
        argv[0] = "csound";
        argv[1] = "-m0";
        argv[2] = orc;

        ll->printf(1,  "loading csound orchestra file %s\n", orc);
        //csoundInitialize(&argc, &argv, 0);
        csoundPreCompile(csound);
        csoundSetHostImplementedAudioIO(csound, 1, csound_period_size);
        int result = csoundCompile(csound, argc, &(argv[0]));
        if (result)
        {
            csound = NULL;
            ll->printf( "ERROR: csoundCompile of orchestra %s failed with code %i\n", orc, result);
        }
        free(argv);
        loop = new EvLoop(csound, this);
    }
    ~TamTamSound()
    {
        if (csound)
        {
            stop();
            delete loop;
            ll->printf(2, "Going for csoundDestroy\n");
            csoundDestroy(csound);
        }
        ll->printf(2, "TamTamSound destroyed\n");
        if (sys_stuff) delete sys_stuff;
        delete ll;
    }
    uintptr_t thread_fn()
    {
        assert(csound);

        const int nchannels = 2;
        int nloops = 0;
        long int csound_nsamples = csoundGetOutputBufferSize(csound);
        long int csound_nframes = csound_nsamples / nchannels;

        ll->printf(2, "INFO: nsamples = %li nframes = %li\n", csound_nsamples, csound_nframes);

        if (0 > sys_stuff->open(csound_frame_rate, 4, period0, period_per_buffer))
        {
            ll->printf( "ERROR: failed to open alsa device, thread abort\n");
            return 1;
        }
                 
        assert(up_ratio == (signed)(sys_stuff->rate / csound_frame_rate));

        bool do_upsample = (signed)sys_stuff->period_size != csound_nframes;
        short *upbuf = new short[ sys_stuff->period_size * nchannels ];
        int cbuf_pos = csound_nframes; // trigger a call to csoundPerformBuffer immediately
        float *cbuf = NULL;
        int up_pos = 0;
        int ratio_pos = 0;

        while (PERF_STATUS == CONTINUE)
        {
            if ( do_upsample ) //fill one period of audio buffer data by 0 or more calls to csound
            {
                up_pos = 0;
                int messed = 0;
                short cursample[2]={0,0};
                while(!messed)
                {
                    if (cbuf_pos == csound_nframes)
                    {
                        cbuf_pos = 0;
                        if (csoundPerformBuffer(csound)) { messed = 1;break;}
                        cbuf = csoundGetOutputBuffer(csound);
                    }
                    upbuf[2*up_pos+0] = cursample[0];
                    upbuf[2*up_pos+1] = cursample[1];

                    if (++ratio_pos == up_ratio)
                    {
                        ratio_pos = 0;
                        ++cbuf_pos;
                        cbuf[cbuf_pos*2+0] *= (float) ((1<<15)-100.0f);
                        cbuf[cbuf_pos*2+1] *= (float) ((1<<15)-100.0f);
                        FLOAT_TO_SHORT( cbuf[cbuf_pos*2+0], cursample[0]);
                        FLOAT_TO_SHORT( cbuf[cbuf_pos*2+1], cursample[1]);
                    }

                    if (++up_pos == (signed)sys_stuff->period_size) break;
                }
                if (messed || (up_pos != (signed)sys_stuff->period_size)) break;

                if (0 > sys_stuff->writebuf(sys_stuff->period_size, upbuf)) break;
            }
            else               //fill one period of audio directly from csound
            {
                if (csoundPerformBuffer(csound)) break;
                cbuf = csoundGetOutputBuffer(csound);
                for (int i = 0; i < csound_nframes * nchannels; ++i)
                {
                    cbuf[i] *= (float) ((1<<15)-100.0f);
                    FLOAT_TO_SHORT( cbuf[i], upbuf[i]);
                }
                if (0 > sys_stuff->writebuf(csound_nframes,upbuf)) break;
            }

            if (thread_playloop)
            {
                if (tick_adjustment > - ticks_per_period)
                {
                    loop->step(ticks_per_period + tick_adjustment);
                    tick_adjustment = 0.0;
                }
                else
                {
                    tick_adjustment += ticks_per_period;
                }
            }
            ++nloops;
        }

        sys_stuff->close(1);
        delete [] upbuf;
        ll->printf(2, "INFO: performance thread returning 0\n");
        return 0;
    }
    static uintptr_t csThread(void *clientData)
    {
        return ((TamTamSound*)clientData)->thread_fn();
    }
    int start(int )
    {
        if (!csound) {
            ll->printf(1, "skipping %s, csound==NULL\n", __FUNCTION__);
            return 1;
        }
        if (!ThreadID)
        {
            PERF_STATUS = CONTINUE;
            ThreadID = csoundCreateThread(csThread, (void*)this);
            ll->printf( "INFO(%s:%i) aclient launching performance thread (%p)\n", __FILE__, __LINE__, ThreadID );
            return 0;
        }
        ll->printf( "INFO(%s:%i) skipping duplicate request to launch a thread\n", __FILE__, __LINE__ );
        return 1;
    }
    int stop()
    {
        if (!csound) {
            ll->printf(1, "skipping %s, csound==NULL\n", __FUNCTION__);
            return 1;
        }
        if (ThreadID)
        {
            PERF_STATUS = STOP;
            ll->printf( "INFO(%s:%i) aclient joining performance thread\n", __FILE__, __LINE__ );
            uintptr_t rval = csoundJoinThread(ThreadID);
            ll->printf( "INFO(%s:%i) ... joined\n", __FILE__, __LINE__ );
            if (rval)  ll->printf( "WARNING: thread returned %zu\n", rval);
            ThreadID = NULL;
            return 0;
        }
        return 1;
    }

    void scoreEvent(char type, MYFLT * p, int np)
    {
        if (!csound) {
            ll->printf(1, "skipping %s, csound==NULL\n", __FUNCTION__);
            return;
        }
        if (!ThreadID)
        {
            if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping %s, ThreadID==NULL\n", __FUNCTION__);
            return ;
        }
        if (_debug && (VERBOSE > 2))
        {
            fprintf(_debug, "INFO: scoreEvent %c ", type);
            for (int i = 0; i < np; ++i) fprintf(_debug, "%lf ", p[i]);
            fprintf(_debug, "\n");
        }
        csoundScoreEvent(csound, type, p, np);
    }
    void inputMessage(const char * msg)
    {
        if (!csound) {
            ll->printf(1, "skipping %s, csound==NULL\n", __FUNCTION__);
            return;
        }
        if (!ThreadID)
        {
            if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping %s, ThreadID==NULL\n", __FUNCTION__);
            return ;
        }
        if (_debug &&(VERBOSE > 3)) fprintf(_debug, "%s\n", msg);
        csoundInputMessage(csound, msg);
    }
    bool good()
    {
        return csound != NULL;
    }

    void setChannel(const char * name, MYFLT vol)
    {
        if (!csound) {
            ll->printf(1, "skipping %s, csound==NULL\n", __FUNCTION__);
            return;
        }
        if (!ThreadID)
        {
            if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping %s, ThreadID==NULL\n", __FUNCTION__);
            return ;
        }
        MYFLT *p;
        if (!(csoundGetChannelPtr(csound, &p, name, CSOUND_CONTROL_CHANNEL | CSOUND_INPUT_CHANNEL)))
            *p = (MYFLT) vol;
        else
        {
            if (_debug && (VERBOSE >0)) fprintf(_debug, "ERROR: failed to set channel: %s\n", name);
        }
    }

    void loopPlaying(int tf)
    {
        thread_playloop= tf;
        if (tf) loop->reset();
    }

    void setTickDuration(MYFLT secs_per_tick )
    {
        if (loop) loop->setTickDuration( secs_per_tick);
        ticks_per_period = csound_period_size / ( secs_per_tick  * csound_frame_rate);
        ll->printf( 3, "INFO: duration %lf := ticks_per_period %lf\n", secs_per_tick , ticks_per_period);
    }
    void adjustTick(MYFLT dtick)
    {
        tick_adjustment += dtick;
    }
};


static void cleanup(void)
{
    if (sc_tt)
    {
        delete sc_tt;
        sc_tt = NULL;
    }
}

#define DECL(s) static PyObject * s(PyObject * self, PyObject *args)
#define RetNone Py_INCREF(Py_None); return Py_None;

//call once at end
DECL(sc_destroy)
{
    if (!PyArg_ParseTuple(args, ""))
    {
        return NULL;
    }
    if (sc_tt)
    {
        delete sc_tt;
        sc_tt = NULL;
        if (_debug) fclose(_debug);
    }
    RetNone;
}
//call once at startup, should return 0
DECL(sc_initialize) //(char * csd)
{
    char * str;
    char * log_file;
    int period, ppb, ksmps, framerate;
    if (!PyArg_ParseTuple(args, "ssiiiii", &str, &log_file, &period, &ppb, &VERBOSE, &ksmps, &framerate ))
    {
        return NULL;
    }
    if ( log_file[0] )
    {
        _debug = fopen(log_file,"w"); 
        if (_debug==NULL) 
        {
            fprintf(stderr, "WARNING: fopen(%s) failed, logging to stderr\n", log_file);
            _debug = stderr;
        }
    }
    else
    {
        _debug = NULL;
        fprintf(stderr, "Logging disabled on purpose\n");
    }
    g_log = new log_t(_debug, VERBOSE);
    sc_tt = new TamTamSound(g_log, str, period, ppb, ksmps, framerate);
    atexit(&cleanup);
    if (sc_tt->good()) 
        return Py_BuildValue("i", 0);
    else
        return Py_BuildValue("i", -1);
}
//compile the score, connect to device, start a sound rendering thread
DECL(sc_start)
{
    int ppb;
    if (!PyArg_ParseTuple(args, "i", &ppb ))
    {
        return NULL;
    }
    return Py_BuildValue("i", sc_tt->start(ppb));
}
//stop csound rendering thread, disconnect from sound device, clear tables.
DECL(sc_stop) 
{
    if (!PyArg_ParseTuple(args, "" ))
    {
        return NULL;
    }
    return Py_BuildValue("i", sc_tt->stop());
}
DECL(sc_scoreEvent) //(char type, farray param)
{
    char ev_type;
    PyObject *o;
    if (!PyArg_ParseTuple(args, "cO", &ev_type, &o ))
    {
        return NULL;
    }
    if (o->ob_type
            &&  o->ob_type->tp_as_buffer
            &&  (1 == o->ob_type->tp_as_buffer->bf_getsegcount(o, NULL)))
    {
        if (o->ob_type->tp_as_buffer->bf_getreadbuffer)
        {
            void * ptr;
            size_t len;
            len = o->ob_type->tp_as_buffer->bf_getreadbuffer(o, 0, &ptr);
            float * fptr = (float*)ptr;
            size_t flen = len / sizeof(float);
            sc_tt->scoreEvent(ev_type, fptr, flen);

            Py_INCREF(Py_None);
            return Py_None;
        }
        else
        {
            assert(!"asdf");
        }
    }
    assert(!"not reached");
    return NULL;
}
DECL(sc_setChannel) //(float v)
{
    const char * str;
    float v;
    if (!PyArg_ParseTuple(args, "sf", &str,&v))
    {
        return NULL;
    }
    sc_tt->setChannel(str,v);
    Py_INCREF(Py_None);
    return Py_None;
}
DECL(sc_loop_getTick) // -> float
{
    if (!PyArg_ParseTuple(args, "" ))
    {
        return NULL;
    }
    return Py_BuildValue("f", sc_tt->loop ? sc_tt->loop->getTickf(true):-1.0f);
}
DECL(sc_loop_setNumTicks) //(int nticks)
{
    int nticks;
    if (!PyArg_ParseTuple(args, "i", &nticks ))
    {
        return NULL;
    }
    if (sc_tt->loop) sc_tt->loop->setNumTicks(nticks);
    RetNone;
}
DECL(sc_loop_setTick) // (int ctick)
{
    int ctick;
    if (!PyArg_ParseTuple(args, "i", &ctick ))
    {
        return NULL;
    }
    if (sc_tt->loop) sc_tt->loop->setTick(ctick);
    RetNone;
}
DECL(sc_loop_setTickDuration) // (MYFLT secs_per_tick)
{
    float spt;
    if (!PyArg_ParseTuple(args, "f", &spt ))
    {
        return NULL;
    }
    sc_tt->setTickDuration(spt);
    RetNone;
}
DECL(sc_loop_adjustTick) // (MYFLT ntick)
{
    float spt;
    if (!PyArg_ParseTuple(args, "f", &spt ))
    {
        return NULL;
    }
    sc_tt->adjustTick(spt);
    RetNone;
}
DECL(sc_loop_addScoreEvent) // (int id, int duration_in_ticks, char type, farray param)
{
    int qid, inticks, active;
    char ev_type;
    PyObject *o;
    if (!PyArg_ParseTuple(args, "iiicO", &qid, &inticks, &active, &ev_type, &o ))
    {
        return NULL;
    }
    if (o->ob_type
            &&  o->ob_type->tp_as_buffer
            &&  (1 == o->ob_type->tp_as_buffer->bf_getsegcount(o, NULL)))
    {
        if (o->ob_type->tp_as_buffer->bf_getreadbuffer)
        {
            void * ptr;
            size_t len;
            len = o->ob_type->tp_as_buffer->bf_getreadbuffer(o, 0, &ptr);
            float * fptr = (float*)ptr;
            size_t flen = len / sizeof(float);
            if (sc_tt->loop) sc_tt->loop->addEvent(qid, ev_type, fptr, flen, inticks, active);

            Py_INCREF(Py_None);
            return Py_None;
        }
        else
        {
            assert(!"asdf");
        }
    }
    assert(!"not reached");
    return NULL;
}
DECL(sc_loop_delScoreEvent) // (int id)
{
    int id;
    if (!PyArg_ParseTuple(args, "i", &id ))
    {
        return NULL;
    }
    if (sc_tt->loop) sc_tt->loop->delEvent(id);
    RetNone;
}
DECL(sc_loop_updateEvent) // (int id)
{
    int id;
    int idx;
    float val;
    int cmd;
    if (!PyArg_ParseTuple(args, "iifi", &id, &idx, &val, &cmd))
    {
        return NULL;
    }
    if (sc_tt->loop) sc_tt->loop->updateEvent(id, idx, val, cmd);
    RetNone;
}
DECL(sc_loop_deactivate_all) // (int id)
{
    if (!PyArg_ParseTuple(args, ""))
    {
        return NULL;
    }
    if (sc_tt->loop) sc_tt->loop->deactivateAll();
    RetNone;
}
DECL(sc_loop_clear)
{
    if (!PyArg_ParseTuple(args, "" ))
    {
        return NULL;
    }
    if (sc_tt->loop) sc_tt->loop->clear();
    RetNone;
}
DECL(sc_loop_playing) // (int tf)
{
    int i;
    if (!PyArg_ParseTuple(args, "i", &i ))
    {
        return NULL;
    }
    if (sc_tt->loop) sc_tt->loopPlaying(i);
    RetNone;
}
DECL (sc_inputMessage) //(const char *msg)
{
    char * msg;
    if (!PyArg_ParseTuple(args, "s", &msg ))
    {
        return NULL;
    }
    sc_tt->inputMessage(msg);
    RetNone;
}

#define MDECL(s) {""#s, s, METH_VARARGS, "documentation of "#s"... nothing!"}
static PyMethodDef SpamMethods[] = {
    MDECL(sc_destroy),
    MDECL(sc_initialize),
    MDECL(sc_start),
    MDECL(sc_stop),
    MDECL(sc_scoreEvent),
    MDECL(sc_setChannel),
    MDECL(sc_loop_getTick),
    MDECL(sc_loop_setNumTicks),
    MDECL(sc_loop_setTick),
    MDECL(sc_loop_setTickDuration),
    MDECL(sc_loop_adjustTick),
    MDECL(sc_loop_delScoreEvent),
    MDECL(sc_loop_addScoreEvent),
    MDECL(sc_loop_updateEvent),
    MDECL(sc_loop_clear),
    MDECL(sc_loop_deactivate_all),
    MDECL(sc_loop_playing),
    MDECL(sc_inputMessage),
    {NULL, NULL, 0, NULL} /*end of list */
};

PyMODINIT_FUNC
initaclient(void)
{
    (void) Py_InitModule("aclient", SpamMethods);
}


