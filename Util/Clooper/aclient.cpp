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

#define ERROR_HERE if (_debug && (VERBOSE > 0)) fprintf(_debug, "ERROR: %s:%i\n", __FILE__, __LINE__)

#define IF_DEBUG(N) if (_debug && (VERBOSE > N))

int VERBOSE = 2;
FILE * _debug = NULL;

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
struct SystemStuff
{
    static void setscheduler(void)
    {
        struct sched_param sched_param;

        if (sched_getparam(0, &sched_param) < 0) {
                printf("Scheduler getparam failed...\n");
                return;
        }
        sched_param.sched_priority = sched_get_priority_max(SCHED_RR);

        if (sched_setscheduler(0, SCHED_RR, &sched_param)) 
        {
            if (_debug && (VERBOSE > 2)) printf("WARNING: Scheduler set to Round Robin with priority %i failed!\n", sched_param.sched_priority);
        }
        else
        {
            if (_debug && (VERBOSE > 2)) printf("INFO: Scheduler set to Round Robin with priority %i.\n", sched_param.sched_priority);
        }
    }

    /** the currently opened pcm hande */
    snd_pcm_t * pcm;
    snd_pcm_uframes_t period_size;
    unsigned int      frame_rate;

    SystemStuff() : pcm(NULL), period_size(0), frame_rate(0)
    {
    }
    ~SystemStuff()
    {
        if (pcm) close(0);
    }

    int open(unsigned int rate0, int upsample_max, snd_pcm_uframes_t period0, unsigned int p_per_buff)
    {
        snd_pcm_hw_params_t *hw;

        if (pcm)
        {
            IF_DEBUG(0) fprintf(_debug, "ERROR: open called twice! First close the sound device\n");
            return -1;
        }

        if ( 0 > snd_pcm_open(&pcm, "default", SND_PCM_STREAM_PLAYBACK, 0)) { ERROR_HERE; return -1; }
        if ( 0 > snd_pcm_hw_params_malloc(&hw))                             { ERROR_HERE; snd_pcm_close(pcm); pcm = NULL; return -1; }

        //now we can be a bit flexible with the buffer size and the sample-rate...

        int upsample;
        for (upsample = 1; upsample < upsample_max; ++upsample)
        {
            frame_rate = rate0 * upsample;

            if ( 0 > snd_pcm_hw_params_any(pcm, hw))                               { ERROR_HERE; goto open_error;}

            //first do the compulsory steps... interleaved float, 2 channel
            if ( 0 > snd_pcm_hw_params_set_rate_resample(pcm, hw, 0))              { ERROR_HERE; goto open_error;}
            if ( 0 > snd_pcm_hw_params_test_access(pcm, hw, SND_PCM_ACCESS_RW_INTERLEAVED)){ ERROR_HERE; goto open_error;}
            if ( 0 > snd_pcm_hw_params_set_access(pcm, hw, SND_PCM_ACCESS_RW_INTERLEAVED)){ ERROR_HERE; goto open_error;}
            if ( 0 > snd_pcm_hw_params_test_format(pcm, hw, SND_PCM_FORMAT_FLOAT)) { ERROR_HERE; goto open_error;}
            if ( 0 > snd_pcm_hw_params_set_format(pcm, hw, SND_PCM_FORMAT_FLOAT))  { ERROR_HERE; goto open_error;}
            if ( 0 > snd_pcm_hw_params_set_channels(pcm, hw, 2))                   { ERROR_HERE; goto open_error;}

            IF_DEBUG(1) fprintf(_debug, "testing rate :  %i\t", frame_rate);
            if ( snd_pcm_hw_params_test_rate(pcm, hw, frame_rate, 0)) 
            {
                fprintf(_debug, "failed.\n");
                continue;
            }
            else
            {
                IF_DEBUG(1) fprintf(_debug, "success! setting rate :  %i\n", frame_rate);
                if (0 > snd_pcm_hw_params_set_rate(pcm, hw, frame_rate, 0))        { ERROR_HERE; goto open_error;}

                snd_pcm_uframes_t minb=0, maxb= 0;
                int mind=0, maxd=0;
                snd_pcm_hw_params_get_period_size_min(hw, &minb,&mind);
                snd_pcm_hw_params_get_period_size_max(hw, &maxb,&maxd);
                IF_DEBUG(1) fprintf(_debug, "FYI: period size range is [%li/%i,%li/%i]\n", minb,mind, maxb, maxd);

                assert(mind == 0); //rate_resample 0 makes this true right?
                assert(maxd == 0); //rate_resample 0 makes this true right?

                if (period0 < minb) 
                {
                    IF_DEBUG(1) fprintf(_debug, "requested period size (%li) < min (%li), adjusting to min\n", period_size, minb);
                    period_size = minb;
                }
                else if (period0 > maxb) 
                {
                    IF_DEBUG(1) fprintf(_debug, "requested period size (%li) < max (%li), adjusting to min\n", period_size, maxb);
                    period_size = maxb;
                }
                else
                {
                    period_size = period0;
                }

                IF_DEBUG(1) fprintf(_debug, "testing period size :  %li\n", period_size);
                if ( 0 > snd_pcm_hw_params_test_period_size(pcm, hw, period_size, 0)){ ERROR_HERE; goto open_error;}


                IF_DEBUG(1) fprintf(_debug, "setting period size :  %li\n", period_size);
                if ( 0 > snd_pcm_hw_params_set_period_size(pcm, hw, period_size, 0)){ ERROR_HERE; goto open_error;}
                
                IF_DEBUG(1) fprintf(_debug, "setting buffer size :  %i * %li = %li\n", p_per_buff, period_size, p_per_buff * period_size);
                if ( 0 > snd_pcm_hw_params_set_buffer_size(pcm, hw, p_per_buff*period_size)) { ERROR_HERE; goto open_error;}

                break;
            }
        }

        if (upsample_max == upsample) { ERROR_HERE; goto open_error; }

        if (0 > snd_pcm_hw_params(pcm, hw)) { ERROR_HERE; goto open_error; }

        snd_pcm_hw_params_free (hw);
        return 0;

open_error:
        snd_pcm_hw_params_free (hw);
        snd_pcm_close(pcm);
        pcm = NULL;
        return -1;
    }
    void close(int drain = 0)
    {
        if (!pcm) 
        {
            IF_DEBUG(2) fprintf(_debug, "WARNING: attempt to close already-closed pcm\n");
            return;
        }
        IF_DEBUG(1) fprintf(_debug, "INFO: closing pcm device\n");
        if (drain) snd_pcm_drain(pcm);
        snd_pcm_close(pcm);
        pcm = NULL;
    }
    void prepare()
    {
        if (!pcm)
        {
            IF_DEBUG(0) fprintf(_debug, "ERROR: attempt to prepare a closed pcm\n");
            return;
        }
        if (0 > snd_pcm_prepare(pcm)) { ERROR_HERE; }
    }
    int write(snd_pcm_uframes_t frame_count, float * frame_data)
    {
        if (!pcm)
        {
            IF_DEBUG(0) fprintf(_debug, "ERROR: attempt to write a closed pcm\n");
            return -1;
        }
        int err;
        err = snd_pcm_writei (pcm, frame_data, frame_count );
        if (err == (signed)frame_count) return 0; //success

        assert(err < 0);

        const char * msg = NULL;
        snd_pcm_state_t state = snd_pcm_state(pcm);
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
        if (_debug && (VERBOSE > 1)) fprintf (_debug, "WARNING: write failed (%s)\tstate = %s\ttime=%lf\n", snd_strerror (err), msg, pytime(NULL));
        if (0 > snd_pcm_recover(pcm, err, 0)) { ERROR_HERE; return err;}
        if (0 > snd_pcm_prepare(pcm))         { ERROR_HERE; return err;}
        return 1; //warning
    }
};
struct TamTamSound
{
    /** the id of an running sound-rendering thread, or NULL */
    void * ThreadID;
    /** a flag to tell the thread to continue, or break */
    enum {CONTINUE, STOP} PERF_STATUS;
    /** our csound object, NULL iff there was a problem creating it */
    CSOUND * csound;

    /** the event loop */
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
        void setTickDuration(MYFLT d)
        {
            if (!csound) {
                if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping setTickDuration, csound==NULL\n");
                return;
            }
            secs_per_tick = d;
            ticks_per_step = tt->csound_period_size / ( d * tt->csound_frame_rate);
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
    EvLoop * loop;
    /** a flag, true iff the thread should play&advance the loop */
    int thread_playloop;

    /** the upsampling ratio from csound */
    unsigned int csound_ksmps;
    snd_pcm_uframes_t csound_frame_rate;
    snd_pcm_uframes_t csound_period_size;
    snd_pcm_uframes_t period0;
    unsigned int period_per_buffer;
    int up_ratio;

    SystemStuff sys_stuff;

    TamTamSound(char * orc, snd_pcm_uframes_t period0, unsigned int ppb)
        : ThreadID(NULL), PERF_STATUS(STOP), csound(NULL),
        loop(NULL), thread_playloop(0),
        csound_ksmps(64),           //MAGIC: must agree with the orchestra file
        csound_frame_rate(16000),           //MAGIC: must agree with the orchestra file
        period0(period0),
        period_per_buffer(ppb),
        up_ratio(0),
        sys_stuff()
    {
        if (0 > sys_stuff.open(csound_frame_rate, 4, period0, period_per_buffer))
        {
            return;
        }
        sys_stuff.close(0);
        up_ratio = sys_stuff.frame_rate / csound_frame_rate;
        csound_period_size = (sys_stuff.period_size % up_ratio == 0)
            ? sys_stuff.period_size / up_ratio
            : csound_ksmps * 4;

        csound = csoundCreate(NULL);
        int argc=3;
        char  **argv = (char**)malloc(argc*sizeof(char*));
        argv[0] = "csound";
        argv[1] ="-m0";
        argv[2] = orc;
        if (_debug && (VERBOSE>1)) fprintf(_debug, "loading file %s\n", orc);

        //csoundInitialize(&argc, &argv, 0);
        csoundPreCompile(csound);
        csoundSetHostImplementedAudioIO(csound, 1, csound_period_size);
        int result = csoundCompile(csound, argc, &(argv[0]));
        if (result)
        {
            csound = NULL;
            if (_debug && (VERBOSE>0)) fprintf(_debug, "ERROR: csoundCompile of orchestra %s failed with code %i\n",
                    orc, result);
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
            //if (_debug && (VERBOSE>3)) fprintf(_debug, "Going for csoundReset\n");
            //csoundReset(csound);
            if (_debug && (VERBOSE > 2)) fprintf(_debug, "Going for csoundDestroy\n");
            csoundDestroy(csound);
        }
        if (_debug && (VERBOSE > 2)) fprintf(_debug, "TamTam aclient destroyed\n");
    }
    uintptr_t thread_fn()
    {
        assert(csound);

        const int nchannels = 2;
        int nloops = 0;
        long int csound_nsamples = csoundGetOutputBufferSize(csound);
        long int csound_nframes = csound_nsamples / nchannels;

        if (_debug && (VERBOSE > 2)) fprintf(_debug, "INFO: nsamples = %li nframes = %li\n", csound_nsamples, csound_nframes);

        if (0 > sys_stuff.open(csound_frame_rate, 4, period0, period_per_buffer))
        {
            IF_DEBUG(0) fprintf(_debug, "ERROR: failed to open alsa device, thread abort\n");
            return 1;
        }
        
        assert(up_ratio = sys_stuff.frame_rate / csound_frame_rate);

        float *upbuf = new float[ sys_stuff.period_size * nchannels ]; //2 channels
        int cbuf_pos = csound_nframes;
        float *cbuf = NULL;
        unsigned up_pos = 0;
        int ratio_pos = 0;

        sys_stuff.setscheduler(); //it might work...

        while (PERF_STATUS == CONTINUE)
        {
            if (sys_stuff.period_size == (unsigned)csound_nframes )
            {
                if (csoundPerformBuffer(csound)) break;
                if (0 > sys_stuff.write(sys_stuff.period_size, csoundGetOutputBuffer(csound))) break;
            }
            else
            {
                up_pos = 0;
                int messed = 0;
                while(!messed)
                {
                    if (cbuf_pos == csound_nframes)
                    {
                        cbuf_pos = 0;
                        if (csoundPerformBuffer(csound)) {messed = 1;break;}
                        cbuf = csoundGetOutputBuffer(csound);
                    }
                    upbuf[2*up_pos+0] = cbuf[cbuf_pos*2+0];
                    upbuf[2*up_pos+1] = cbuf[cbuf_pos*2+1];

                    if (++ratio_pos == up_ratio)
                    {
                        ratio_pos = 0;
                        ++cbuf_pos;
                    }

                    if (++up_pos == sys_stuff.period_size) break;
                }
                if (messed || (up_pos != sys_stuff.period_size)) break;

                if (0 > sys_stuff.write(sys_stuff.period_size, upbuf)) break;
            }

            if (thread_playloop)
            {
                loop->step();
            }
            ++nloops;
        }

        sys_stuff.close(1);
        if (_debug && (VERBOSE > 2)) fprintf(_debug, "INFO: returning from performance thread\n");
        return 0;
    }
    static uintptr_t csThread(void *clientData)
    {
        return ((TamTamSound*)clientData)->thread_fn();
    }
    int start(int )
    {
        if (!csound) {
            if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping %s, csound==NULL\n", __FUNCTION__);
            return 1;
        }
        if (!ThreadID)
        {
            PERF_STATUS = CONTINUE;
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
            if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping %s, csound==NULL\n", __FUNCTION__);
            return ;
        }
        if (!ThreadID)
        {
            if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping %s, ThreadID==NULL\n", __FUNCTION__);
            return ;
        }
        MYFLT *p;
        char buf[128];
        sprintf( buf, "trackVolume%i", Id);
        if (_debug && (VERBOSE > 10)) fprintf(_debug, "DEBUG: setTrackvolume string [%s]\n", buf);
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
        if (_debug) fclose(_debug);
    }
    RetNone;
}
//call once at startup, should return 0
DECL(sc_initialize) //(char * csd)
{
    char * str;
    char * log_file;
    int period, ppb;
    if (!PyArg_ParseTuple(args, "ssii", &str, &log_file, &period, &ppb ))
    {
        return NULL;
    }
    if ( log_file[0] )
        _debug = fopen(log_file,"w"); 
    else
        _debug = NULL;
    sc_tt = new TamTamSound(str, period, ppb);
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
    return Py_BuildValue("i", sc_tt->loop ? sc_tt->loop->getTick():-1);
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
    if (sc_tt->loop) sc_tt->loop->setTickDuration(spt);
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


