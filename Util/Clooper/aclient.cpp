#include <python2.4/Python.h>

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

#define ACFG(cmd) {int err = 0; if ( (err = cmd) < 0) { if (_debug && (VERBOSE > 0)) fprintf(_debug, "ERROR: %s:%i (%s)\n", __FILE__, __LINE__, snd_strerror(err)); return err;} }
#define ERROR_HERE if (_debug) fprintf(_debug, "ERROR: %s:%i\n", __FILE__, __LINE__);

int VERBOSE = 1;
FILE * _debug = NULL;
unsigned int SAMPLE_RATE = 16000;

static int setparams (snd_pcm_t * phandle, int periods_per_buffer, snd_pcm_uframes_t period_size )
{
    snd_pcm_hw_params_t *hw;
    int srate_dir = 0;
    snd_pcm_uframes_t buffer_size = period_size * periods_per_buffer, bsize, psize;

    ACFG(snd_pcm_hw_params_malloc(&hw));
    ACFG(snd_pcm_hw_params_any(phandle, hw));
    ACFG(snd_pcm_hw_params_set_access(phandle, hw, SND_PCM_ACCESS_RW_INTERLEAVED));
    ACFG(snd_pcm_hw_params_set_format(phandle, hw, SND_PCM_FORMAT_FLOAT));
    ACFG(snd_pcm_hw_params_set_rate_near(phandle, hw, &SAMPLE_RATE, &srate_dir));
    ACFG(snd_pcm_hw_params_set_channels(phandle, hw, 2));
    ACFG(snd_pcm_hw_params_set_buffer_size_near(phandle, hw, &buffer_size));
    ACFG(snd_pcm_hw_params_set_period_size_near(phandle, hw, &period_size, 0));
    ACFG(snd_pcm_hw_params_get_buffer_size(hw, &bsize));
    ACFG(snd_pcm_hw_params_get_period_size(hw, &psize, 0));

    assert(bsize == buffer_size);
    assert(psize == period_size);

    ACFG(snd_pcm_hw_params(phandle, hw));

    snd_pcm_hw_params_free (hw);
    return 0;
}
static int setswparams(snd_pcm_t *phandle)
{
    /* not sure what to do here */
    return 0;
}

static void setscheduler(void)
{
	struct sched_param sched_param;

	if (sched_getparam(0, &sched_param) < 0) {
		printf("Scheduler getparam failed...\n");
		return;
	}
	sched_param.sched_priority = sched_get_priority_max(SCHED_RR);
	if (!sched_setscheduler(0, SCHED_RR, &sched_param)) {
		printf("Scheduler set to Round Robin with priority %i...\n", sched_param.sched_priority);
		fflush(stdout);
		return;
	}
	printf("!!!Scheduler set to Round Robin with priority %i FAILED!!!\n", sched_param.sched_priority);
}

#if 0
static double pytime(const struct timeval * tv)
{
    return (double) tv->tv_sec + (double) tv->tv_usec / 1000000.0;
}
#endif

struct ev_t
{
    char type;
    int onset;
    bool time_in_ticks;
    bool active;
    MYFLT prev_secs_per_tick;
    MYFLT duration, attack, decay;
    std::vector<MYFLT> param;

    ev_t(char type, MYFLT * p, int np, bool in_ticks, bool active)
        : type(type), onset(0), time_in_ticks(in_ticks), active(active), param(np)
    {
        assert(np >= 4);
        onset = (int) p[1];
        duration = p[2];
        attack = np > 8 ? p[8]: 0.0; //attack
        decay = np > 9 ? p[9]: 0.0; //decay
        prev_secs_per_tick = -1.0;
        for (int i = 0; i < np; ++i) param[i] = p[i];

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
    void update(int idx, MYFLT val)
    {
        if ( (unsigned)idx >= param.size())
        {
            if (_debug && (VERBOSE > 0)) fprintf(stderr, "ERROR: updateEvent request for too-high parameter %i\n", idx);
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
    void activate_cmd(int cmd)
    {
        switch(cmd)
        {
            case 0: active = false; break;
            case 1: active = true; break;
            case 2: active = !active; break;
        }
    }

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
struct EvLoop
{
    int tick_prev;
    int tickMax;
    MYFLT rtick;
    MYFLT secs_per_tick;
    MYFLT ticks_per_step;
    typedef std::pair<int, ev_t *> pair_t;
    typedef std::multimap<int, ev_t *>::iterator iter_t;
    typedef std::map<int, iter_t>::iterator idmap_t;

    std::multimap<int, ev_t *> ev;
    std::multimap<int, ev_t *>::iterator ev_pos;
    std::map<int, iter_t> idmap;
    CSOUND * csound;
    void * mutex;
    int steps;

    EvLoop(CSOUND * cs, snd_pcm_uframes_t period_size) : tick_prev(0), tickMax(1), rtick(0.0), ev(), ev_pos(ev.end()), csound(cs), mutex(NULL), steps(0)
    {
        setTickDuration(0.05, period_size);
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
        csoundLockMutex(mutex);
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
    void setTickDuration(MYFLT d, int period_size)
    {
        if (!csound) {
            if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping setTickDuration, csound==NULL\n");
            return;
        }
        secs_per_tick = d;
        ticks_per_step = period_size / ( d * 16000);
        if (_debug && (VERBOSE > 2)) fprintf(_debug, "INFO: duration %lf := ticks_per_step %lf\n", d, ticks_per_step);
    }
    void step()
    {
        rtick += ticks_per_step;
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
struct TamTamSound
{
    void * ThreadID;
    CSOUND * csound;
    enum {CONTINUE, STOP} PERF_STATUS;
    FILE * _light;
    int thread_playloop;
    int thread_measurelag;
    EvLoop * loop;
    const snd_pcm_uframes_t period_size;
    int               periods_per_buffer;

    TamTamSound(char * orc)
        : ThreadID(NULL), csound(NULL), PERF_STATUS(STOP),
        _light(fopen("/sys/bus/platform/devices/leds-olpc/leds:olpc:keyboard/brightness", "w")),
        thread_playloop(0), thread_measurelag(0), loop(NULL),
        period_size(1<<8), periods_per_buffer(2)
    {
        if (1)
        {
            csound = csoundCreate(NULL);
            int argc=3;
            char  **argv = (char**)malloc(argc*sizeof(char*));
            argv[0] = "csound";
            argv[1] ="-m0";
            argv[2] = orc;
            if (_debug && (VERBOSE>1)) fprintf(_debug, "loading file %s\n", orc);

            //csoundInitialize(&argc, &argv, 0);
            csoundPreCompile(csound);
            csoundSetHostImplementedAudioIO(csound, 1, period_size);
            int result = csoundCompile(csound, argc, &(argv[0]));
            if (result)
            {
                csound = NULL;
                if (_debug && (VERBOSE>0)) fprintf(_debug, "ERROR: csoundCompile of orchestra %s failed with code %i\n",
                        orc, result);
            }
            free(argv);
        }
        else
        {
            csound = NULL;
        }
        loop = new EvLoop(csound, period_size);
    }
    ~TamTamSound()
    {
        if (csound)
        {
            stop();
            delete loop;
            //if (_debug && (VERBOSE>2)) fprintf(_debug, "Going for csoundReset\n");
            //csoundReset(csound);
            if (_debug && (VERBOSE > 2)) fprintf(_debug, "Going for csoundDestroy\n");
            csoundDestroy(csound);
        }
        if (_light) fclose(_light);

        if (_debug && (VERBOSE > 2)) fprintf(_debug, "TamTam aclient destroyed\n");
    }
    uintptr_t thread_fn()
    {
        struct timeval tv0;

        int nloops = 0;
        long int nsamples = csoundGetOutputBufferSize(csound);
        long int nframes = nsamples/2; /* nchannels == 2 */ /* nframes per write */
        assert((unsigned)nframes == period_size);
        float * buf = (float*)malloc(nsamples * sizeof(float));
        if (_debug && (VERBOSE > 2)) fprintf(_debug, "INFO: nsamples = %li nframes = %li\n", nsamples, nframes);

        snd_pcm_t * phandle;
        ACFG(snd_pcm_open(&phandle, "default", SND_PCM_STREAM_PLAYBACK,0));
        if (setparams(phandle, periods_per_buffer, period_size))
        {
            goto thread_fn_cleanup;
        }
        if (setswparams(phandle))
        {
            goto thread_fn_cleanup;
        }
        if (0 > snd_pcm_prepare(phandle))
        {
            ERROR_HERE;
            goto thread_fn_cleanup;
        }
        for (int i = 0; i < nframes; ++i)
        {
            buf[i*2] = buf[i*2+1] = 0.5 * sin( i / (float)nframes * 10.0 * M_PI);
        }

        setscheduler();

        while (PERF_STATUS == CONTINUE)
        {
            int err = 0;
            float *cbuf = csoundGetOutputBuffer(csound);
            gettimeofday(&tv0, 0);
            if (1 && csoundPerformBuffer(csound)) break;
            assert(sizeof (MYFLT) == 4);

            if ((err = snd_pcm_writei (phandle, cbuf, nframes)) != nframes) 
            {
                const char * msg = NULL;
                snd_pcm_state_t state = snd_pcm_state(phandle);
                switch (state)
                {
                    case SND_PCM_STATE_OPEN:    msg = "open"; break;
                    case SND_PCM_STATE_SETUP:   msg = "setup"; break;
                    case SND_PCM_STATE_PREPARED:msg = "prepared"; break;
                    case SND_PCM_STATE_RUNNING: msg = "running"; break;
                    case SND_PCM_STATE_XRUN:    msg = "xrun"; break;
                    case SND_PCM_STATE_DRAINING: msg = "draining"; break;
                    case SND_PCM_STATE_PAUSED:  msg = "paused"; break;
                    case SND_PCM_STATE_SUSPENDED: msg = "suspended"; break;
                    case SND_PCM_STATE_DISCONNECTED: msg = "disconnected"; break;
                }
                //if (state != SND_PCM_STATE_XRUN)
                if (_debug && (VERBOSE > 0)) fprintf (_debug, "WARNING: write to audio interface failed (%s)\tstate = %s\n", snd_strerror (err), msg);
                ACFG(snd_pcm_recover(phandle, err, 0));
                if (0 > snd_pcm_prepare(phandle))
                {
                    ERROR_HERE;
                    goto thread_fn_cleanup;
                }
                state = snd_pcm_state(phandle);

                assert(state == SND_PCM_STATE_PREPARED || state == SND_PCM_STATE_RUNNING);
            }
            if (thread_playloop)
            {
                loop->step();
            }
            ++nloops;
        }

thread_fn_cleanup:
        free(buf);
        snd_pcm_drain(phandle);

        snd_pcm_close (phandle);

        if (_debug && (VERBOSE > 2)) fprintf(_debug, "INFO: returning from performance thread\n");
        return 0;
    }
    static uintptr_t csThread(void *clientData)
    {
        return ((TamTamSound*)clientData)->thread_fn();
    }
    int start(int p_per_b)
    {
        if (!csound) {
            if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping %s, csound==NULL\n", __FUNCTION__);
            return 1;
        }
        if (!ThreadID)
        {
            PERF_STATUS = CONTINUE;
            periods_per_buffer = p_per_b;
            ThreadID = csoundCreateThread(csThread, (void*)this);
            return 0;
        }
        return 1;
    }
    int stop()
    {
        if (!csound) {
            if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping %s, csound==NULL\n", __FUNCTION__);
            return 1;
        }
        if (ThreadID)
        {
            PERF_STATUS = STOP;
            if (_debug && (VERBOSE > 2)) fprintf(_debug, "INFO: aclient joining performance thread\n");
            uintptr_t rval = csoundJoinThread(ThreadID);
            if (rval) 
                if (_debug && (VERBOSE > 0)) fprintf(_debug, "WARNING: thread returned %zu\n", rval);
            ThreadID = NULL;
            return 0;
        }
        return 1;
    }

    void scoreEvent(char type, MYFLT * p, int np)
    {
        if (!csound) {
            if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping %s, csound==NULL\n", __FUNCTION__);
            return ;
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
            if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping %s, csound==NULL\n", __FUNCTION__);
            return ;
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

    void setMasterVolume(MYFLT vol)
    {
        if (!csound) {
            if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping %s, csound==NULL\n", __FUNCTION__);
            return ;
        }
        if (!ThreadID)
        {
            if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping %s, ThreadID==NULL\n", __FUNCTION__);
            return ;
        }
        MYFLT *p;
        if (!(csoundGetChannelPtr(csound, &p, "masterVolume", CSOUND_CONTROL_CHANNEL | CSOUND_INPUT_CHANNEL)))
            *p = (MYFLT) vol;
        else
        {
            if (_debug && (VERBOSE >0)) fprintf(_debug, "ERROR: failed to set master volume\n");
        }
    }

    void setTrackVolume(MYFLT vol, int Id)
    {
        if (!csound) {
            fprintf(stderr, "skipping %s, csound==NULL\n", __FUNCTION__);
            return ;
        }
        MYFLT *p;
        char buf[128];
        sprintf( buf, "trackVolume%i", Id);
        fprintf(stderr, "DEBUG: setTrackvolume string [%s]\n", buf);
        if (!(csoundGetChannelPtr(csound, &p, buf, CSOUND_CONTROL_CHANNEL | CSOUND_INPUT_CHANNEL)))
            *p = (MYFLT) vol;
        else
        {
            if (_debug) fprintf(_debug, "ERROR: failed to set track volume\n");
        }
    }

    void setTrackpadX(MYFLT value)
    {
        if (!csound) {
            if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping %s, csound==NULL\n", __FUNCTION__);
            return ;
        }
        if (!ThreadID)
        {
            if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping %s, ThreadID==NULL\n", __FUNCTION__);
            return ;
        }
        MYFLT *p;
        if (!(csoundGetChannelPtr(csound, &p, "trackpadX", CSOUND_CONTROL_CHANNEL | CSOUND_INPUT_CHANNEL)))
            *p = (MYFLT) value;
        else
        {
            if (_debug && (VERBOSE > 0)) fprintf(_debug, "ERROR: failed to set trackpad X value\n");
        }
    }

    void setTrackpadY(MYFLT value)
    {
        if (!csound) {
            if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping %s, csound==NULL\n", __FUNCTION__);
            return ;
        }
        if (!ThreadID)
        {
            if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping %s, ThreadID==NULL\n", __FUNCTION__);
            return ;
        }
        MYFLT *p;
        if (!(csoundGetChannelPtr(csound, &p, "trackpadY", CSOUND_CONTROL_CHANNEL | CSOUND_INPUT_CHANNEL)))
            *p = (MYFLT) value;
        else
        {
             if (_debug && (VERBOSE >0)) fprintf(_debug, "ERROR: failed to set trackpad Y value\n");
        }
    }
    void loopPlaying(int tf)
    {
        thread_playloop= tf;
        if (tf) loop->reset();
    }
};

TamTamSound * sc_tt = NULL;

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
    }
    RetNone;
}
//call once at startup, should return 0
DECL(sc_initialize) //(char * csd)
{
    char * str;
    if (!PyArg_ParseTuple(args, "s", &str ))
    {
        return NULL;
    }
    _debug = stdout; // ideally this gets echoed to the TamTam.log file
    sc_tt = new TamTamSound(str);
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
            if (0) fprintf(stderr, "writeable buffer of length %zu at %p\n", len, ptr);
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
DECL(sc_setMasterVolume) //(float v)
{
    float v;
    if (!PyArg_ParseTuple(args, "f", &v))
    {
        return NULL;
    }
    sc_tt->setMasterVolume(v);
    Py_INCREF(Py_None);
    return Py_None;
}
DECL(sc_setTrackVolume) //(float v)
{
    float v;
    int i;
    if (!PyArg_ParseTuple(args, "fi", &v, &i))
    {
        return NULL;
    }
    sc_tt->setTrackVolume(v,i);
    Py_INCREF(Py_None);
    return Py_None;
}
DECL(sc_setTrackpadX) //(float v)
{
    float v;
    if (!PyArg_ParseTuple(args, "f", &v))
    {
        return NULL;
    }
    sc_tt->setTrackpadX(v);
    Py_INCREF(Py_None);
    return Py_None;
}
DECL(sc_setTrackpadY) //(float v)
{
    float v;
    if (!PyArg_ParseTuple(args, "f", &v))
    {
        return NULL;
    }
    sc_tt->setTrackpadY(v);
    Py_INCREF(Py_None);
    return Py_None;
}
DECL(sc_loop_getTick) // -> int
{
    if (!PyArg_ParseTuple(args, "" ))
    {
        return NULL;
    }
    return Py_BuildValue("i", sc_tt->loop->getTick());
}
DECL(sc_loop_setNumTicks) //(int nticks)
{
    int nticks;
    if (!PyArg_ParseTuple(args, "i", &nticks ))
    {
        return NULL;
    }
    sc_tt->loop->setNumTicks(nticks);
    RetNone;
}
DECL(sc_loop_setTick) // (int ctick)
{
    int ctick;
    if (!PyArg_ParseTuple(args, "i", &ctick ))
    {
        return NULL;
    }
    sc_tt->loop->setTick(ctick);
    RetNone;
}
DECL(sc_loop_setTickDuration) // (MYFLT secs_per_tick)
{
    float spt;
    if (!PyArg_ParseTuple(args, "f", &spt ))
    {
        return NULL;
    }
    sc_tt->loop->setTickDuration(spt, sc_tt->period_size);
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
            if (0) fprintf(stderr, "writeable buffer of length %zu at %p\n", len, ptr);
            float * fptr = (float*)ptr;
            size_t flen = len / sizeof(float);
            sc_tt->loop->addEvent(qid, ev_type, fptr, flen, inticks, active);

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
    sc_tt->loop->delEvent(id);
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
    sc_tt->loop->updateEvent(id, idx, val, cmd);
    RetNone;
}
DECL(sc_loop_deactivate_all) // (int id)
{
    if (!PyArg_ParseTuple(args, ""))
    {
        return NULL;
    }
    sc_tt->loop->deactivateAll();
    RetNone;
}
DECL(sc_loop_clear)
{
    if (!PyArg_ParseTuple(args, "" ))
    {
        return NULL;
    }
    sc_tt->loop->clear();
    RetNone;
}
DECL(sc_loop_playing) // (int tf)
{
    int i;
    if (!PyArg_ParseTuple(args, "i", &i ))
    {
        return NULL;
    }
    sc_tt->loopPlaying(i);
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

#define MDECL(s) {""#s, s, METH_VARARGS, "documentation of "#s"... nothing!"},
static PyMethodDef SpamMethods[] = {
    {"sc_destroy", sc_destroy, METH_VARARGS,""},
    {"sc_initialize", sc_initialize, METH_VARARGS,""},
    {"sc_start", sc_start, METH_VARARGS,""},
    {"sc_stop", sc_stop, METH_VARARGS,""},
    {"sc_scoreEvent", sc_scoreEvent, METH_VARARGS, ""},
    {"sc_setMasterVolume", sc_setMasterVolume, METH_VARARGS, ""},
    {"sc_setTrackVolume", sc_setTrackVolume, METH_VARARGS, ""},
    {"sc_setTrackpadX", sc_setTrackpadX, METH_VARARGS, ""},
    {"sc_setTrackpadY", sc_setTrackpadY, METH_VARARGS, ""},
    MDECL(sc_loop_getTick)
    MDECL(sc_loop_setNumTicks)
    MDECL(sc_loop_setTick)
    MDECL(sc_loop_setTickDuration)
    MDECL(sc_loop_delScoreEvent)
    MDECL(sc_loop_addScoreEvent) // (int id, int duration_in_ticks, char type, farray param)
    MDECL(sc_loop_updateEvent) // (int id)
    MDECL(sc_loop_clear)
    MDECL(sc_loop_deactivate_all)
    MDECL(sc_loop_playing)
    MDECL(sc_inputMessage)
    {NULL, NULL, 0, NULL} /*end of list */
};

PyMODINIT_FUNC
initaclient(void)
{
    (void) Py_InitModule("aclient", SpamMethods);
}


