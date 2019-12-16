#include <Python.h>

#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

#include <csound/csound.hpp>
#include <csound/csound_threaded.hpp>

#include <array>
#include <cmath>
#include <map>
#include <memory>
#include <unordered_map>
#include <vector>

#include "log.cpp"

int VERBOSE = 3;
FILE* _debug = nullptr;
struct TamTamSound;
struct Music;
TamTamSound* g_tt = nullptr;
Music* g_music = nullptr;
static log_t* g_log = nullptr;
const int STEP_eventMax = 16; //this is the most events that will be queued by a loop per step()

/**
 * Event is the type of event that Clooper puts in the loop buffer.
 * It corresponds to a line of csound that starts with an 'i'
 */
struct Event
{
    char type; ///< if this event were listed in a csound file, the line would begin with this letter
    int onset; ///< the onset time of this event (its temporal position)
    bool time_in_ticks; ///< if true, then some parameters will be updated according to the tempo
    bool active; ///< if true, then event() will actually do something
    MYFLT prev_secs_per_tick; ///< normally used for ____, sometimes set to -1 to force recalculation of param[] entries
    MYFLT duration, attack, decay; ///< canonical values of some tempo-dependent parameters
    std::vector<MYFLT> param; ///< parameter buffer for csound

    Event(char type, MYFLT* p, int param_count, bool in_ticks, bool active)
        : type(type), onset(0), time_in_ticks(in_ticks), active(active), param(param_count)
    {
        assert(param_count >= 4);
        onset = (int) p[1];
        duration = p[2];
        attack = param_count > 8 ? p[8] : 0.0; //attack
        decay = param_count > 9 ? p[9] : 0.0; //decay
        prev_secs_per_tick = -1.0;
        for (int i = 0; i < param_count; ++i) param[i] = p[i];

        param[1] = 0.0; //onset
    }
    /*
    bool operator<(const Event &e) const
    {
        return onset < e.onset;
    }
    */
    void ev_print(FILE* f)
    {
        fprintf(f, "INFO: scoreEvent %c ", type);
        for (size_t i = 0; i < param.size(); ++i) fprintf(f, "%lf ", param[i]);
        fprintf(f, "[%s]\n", active ? "active" : "inactive");
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
        if ((unsigned) idx >= param.size())
        {
            if (_debug && (VERBOSE > 0)) fprintf(_debug, "ERROR: updateEvent request for too-high parameter %i\n", idx);
            return;
        }
        if (time_in_ticks)
        {
            switch (idx)
            {
                case 1: onset = (int) val; break;
                case 2: duration = val; break;
                case 8: attack = val; break;
                case 9: decay = val; break;
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
     * An Event instance can be in an active or inactive state.  If an Event instance
     * is active, then event() will call a corresponding csoundScoreEvent().  If an
     * Event instance is inactive, then event() is a noop.
     */
    void activate_cmd(int cmd)
    {
        switch (cmd)
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
    void event(CSOUND* csound, MYFLT secs_per_tick)
    {
        if (!active) return;

        if (time_in_ticks && (secs_per_tick != prev_secs_per_tick))
        {
            param[2] = duration * secs_per_tick;
            if (param.size() > 8) param[8] = std::max((MYFLT) 0.002f, attack * param[2]);
            if (param.size() > 9) param[9] = std::max((MYFLT) 0.002f, decay * param[2]);
            prev_secs_per_tick = secs_per_tick;
            if (_debug && (VERBOSE > 2)) fprintf(_debug, "setting duration to %f\n", param[5]);
        }
        csoundScoreEvent(csound, type, &param[0], param.size());
    }
};

/** 
 *
 * Loop is a repeat-able loop of Event instances.
 * */
struct Loop
{
    typedef int onset_t;
    typedef int id_t;
    using event_multimap_t = std::multimap<onset_t, std::unique_ptr<Event>>;
    using idmap_t = std::unordered_map<id_t, event_multimap_t::iterator>;

    int tick_prev;
    int tickMax;
    MYFLT rtick;

    // a container of all events, sorted by onset time
    // used for efficient playback
    event_multimap_t ev;
    // the playback head
    event_multimap_t::iterator ev_pos;
    // a container of pointers into ev, indexed by note id
    // used for deleting, updating notes
    idmap_t idmap;
    int steps;
    int playing; //true means that step() works, else step() is no-op

    Loop() : tick_prev(0), tickMax(1), rtick(0.0), ev(), ev_pos(ev.end()), steps(0), playing(0)
    {
    }
    ~Loop()
    {
    }
    void deactivateAll()
    {
        for (auto& item : ev)
        {
            item.second->activate_cmd(0);
        }
    }
    MYFLT getTickf()
    {
        return fmod(rtick, (MYFLT) tickMax);
    }
    void setNumTicks(int nticks)
    {
        tickMax = nticks;
        MYFLT fnticks = nticks;
        if (rtick > fnticks)
        {
            rtick = fmodf(rtick, fnticks);
        }
    }
    void setTickf(MYFLT t)
    {
        rtick = fmodf(t, (MYFLT) tickMax);
        ev_pos = ev.lower_bound((int) rtick);
    }
    /**  advance in play loop by rtick_inc ticks, possibly generate some
     * csoundScoreEvent calls.
     */
    void step(MYFLT rtick_inc, MYFLT secs_per_tick, CSOUND* csound)
    {
        if (!playing) return;
        rtick += rtick_inc;
        int tick = (int) rtick % tickMax;
        if (tick == tick_prev) return;

        int events = 0;
        int loop0 = 0;
        int loop1 = 0;
        if (!ev.empty())
        {
            if (steps && (tick < tick_prev)) // should be true only after the loop wraps (not after insert)
            {
                while (ev_pos != ev.end())
                {
                    if (_debug && (VERBOSE > 3)) ev_pos->second->ev_print(_debug);
                    if (events < STEP_eventMax) ev_pos->second->event(csound, secs_per_tick);
                    ++ev_pos;
                    ++events;
                    ++loop0;
                }
                ev_pos = ev.begin();
            }
            while ((ev_pos != ev.end()) && (tick >= ev_pos->first))
            {
                if (_debug && (VERBOSE > 3)) ev_pos->second->ev_print(_debug);
                if (events < STEP_eventMax) ev_pos->second->event(csound, secs_per_tick);
                ++ev_pos;
                ++events;
                ++loop1;
            }
        }
        tick_prev = tick;
        if (_debug && (VERBOSE > 1) && (events >= STEP_eventMax)) fprintf(_debug, "WARNING: %i/%i events at once (%i, %i)\n", events, (int) ev.size(), loop0, loop1);
        ++steps;
    }
    void addEvent(int id, char type, MYFLT* p, int np, bool in_ticks, bool active)
    {
        auto e = std::unique_ptr<Event>(new Event(type, p, np, in_ticks, active));

        auto id_iter = idmap.find(id);
        if (id_iter == idmap.end())
        {
            //this is a new id
            auto e_iter = ev.emplace(e->onset, std::move(e));

            //TODO: optimize by thinking about whether to do ev_pos = e_iter
            ev_pos = ev.upper_bound(tick_prev);
            idmap[id] = e_iter;
        }
        else
        {
            g_log->printf(1, "%s duplicate note %i\n", __FUNCTION__, id);
        }
    }
    void delEvent(int id)
    {
        idmap_t::iterator id_iter = idmap.find(id);
        if (id_iter != idmap.end())
        {
            auto e_iter = id_iter->second; //idmap[id];
            if (e_iter == ev_pos) ++ev_pos;

            ev.erase(e_iter);
            idmap.erase(id_iter);
        }
        else
        {
            g_log->printf(1, "%s unknown note %i\n", __FUNCTION__, id);
        }
    }
    void updateEvent(int id, int idx, MYFLT val, int activate_cmd)
    {
        auto id_iter = idmap.find(id);
        if (id_iter != idmap.end())
        {
            //this is a new id
            auto e_iter = id_iter->second;
            Event* e = e_iter->second.get();
            int onset = e->onset;
            e->update(idx, val);
            e->activate_cmd(activate_cmd);
            if (onset != e->onset)
            {
                auto e_ptr = std::move(e_iter->second);
                ev.erase(e_iter);

                e_iter = ev.emplace(e->onset, std::move(e_ptr));

                //TODO: optimize by thinking about whether to do ev_pos = e_iter
                ev_pos = ev.upper_bound(tick_prev);
                idmap[id] = e_iter;
            }
        }
        else
        {
            g_log->printf(1, "%s unknown note %i\n", __FUNCTION__, id);
        }
    }
    void reset()
    {
        steps = 0;
    }
    void setPlaying(int tf)
    {
        playing = tf;
    }
};

/** management of loops */
struct Music
{
    typedef int loopIdx_t;
    using eventMap_t = std::unordered_map<int, std::unique_ptr<Loop>>;

    eventMap_t loop;
    int loop_nextIdx;
    void* mutex; //modification and playing of loops cannot be interwoven

    Music() : loop(),
              loop_nextIdx(0),
              mutex(csoundCreateMutex(0))
    {
    }
    ~Music()
    {
        csoundDestroyMutex(mutex);
    }

    void step(MYFLT amt, MYFLT secs_per_tick, CSOUND* csound)
    {
        csoundLockMutex(mutex);
        for (auto& item : loop)
        {
            item.second->step(amt, secs_per_tick, csound);
        }
        csoundUnlockMutex(mutex);
    }

    /** allocate a new loop, and return its index */
    loopIdx_t alloc()
    {
        csoundLockMutex(mutex);
        //find a loop_nextIdx that isn't in loop map already
        while (loop.find(loop_nextIdx) != loop.end()) ++loop_nextIdx;
        loop.emplace(loop_nextIdx, std::unique_ptr<Loop>(new Loop()));
        csoundUnlockMutex(mutex);
        return loop_nextIdx;
    }
    /** de-allocate a loop */
    void destroy(loopIdx_t loopIdx)
    {
        if (loop.find(loopIdx) != loop.end())
        {
            csoundLockMutex(mutex);
            //TODO: save the note events to a cache for recycling
            loop.erase(loopIdx);
            csoundUnlockMutex(mutex);
        }
        else
        {
            g_log->printf(1, "%s() called on non-existant loop %i\n", __FUNCTION__, loopIdx);
        }
    }
    /** set the playing flag of the given loop */
    void playing(loopIdx_t loopIdx, int tf)
    {
        if (loop.find(loopIdx) != loop.end())
        {
            csoundLockMutex(mutex);
            loop[loopIdx]->setPlaying(tf);
            csoundUnlockMutex(mutex);
        }
        else
        {
            g_log->printf(1, "%s() called on non-existant loop %i\n", __FUNCTION__, loopIdx);
        }
    }
    /** set the playing flag of the given loop */
    void addEvent(loopIdx_t loopIdx, int eventId, char type, MYFLT* p, int np, bool in_ticks, bool active)
    {
        auto it = loop.find(loopIdx);
        if (it != loop.end())
        {
            csoundLockMutex(mutex);
            it->second->addEvent(eventId, type, p, np, in_ticks, active);
            csoundUnlockMutex(mutex);
        }
        else
        {
            g_log->printf(1, "%s() called on non-existant loop %i\n", __FUNCTION__, loopIdx);
        }
    }
    void delEvent(loopIdx_t loopIdx, int eventId)
    {
        auto it = loop.find(loopIdx);
        if (it != loop.end())
        {
            csoundLockMutex(mutex);
            it->second->delEvent(eventId);
            csoundUnlockMutex(mutex);
        }
        else
        {
            g_log->printf(1, "%s() called on non-existant loop %i\n", __FUNCTION__, loopIdx);
        }
    }
    void updateEvent(loopIdx_t loopIdx, int eventId, int pIdx, MYFLT pVal, int activate_cmd)
    {
        auto it = loop.find(loopIdx);
        if (it != loop.end())
        {
            csoundLockMutex(mutex);
            it->second->updateEvent(eventId, pIdx, pVal, activate_cmd);
            csoundUnlockMutex(mutex);
        }
        else
        {
            g_log->printf(1, "%s() called on non-existant loop %i\n", __FUNCTION__, loopIdx);
        }
    }
    MYFLT getTickf(loopIdx_t loopIdx)
    {
        auto it = loop.find(loopIdx);
        if (it != loop.end())
        {
            return it->second->getTickf();
        }
        else
        {
            g_log->printf(1, "%s() called on non-existant loop %i\n", __FUNCTION__, loopIdx);
            return 0.0;
        }
    }
    void setTickf(loopIdx_t loopIdx, MYFLT tickf)
    {
        auto it = loop.find(loopIdx);
        if (it != loop.end())
        {
            it->second->setTickf(tickf);
        }
        else
        {
            g_log->printf(1, "%s() called on non-existant loop %i\n", __FUNCTION__, loopIdx);
        }
    }
    void setNumTicks(loopIdx_t loopIdx, int numTicks)
    {
        auto it = loop.find(loopIdx);
        if (it != loop.end())
        {
            it->second->setNumTicks(numTicks);
        }
        else
        {
            g_log->printf(1, "%s() called on non-existant loop %i\n", __FUNCTION__, loopIdx);
        }
    }
    void deactivateAll(loopIdx_t loopIdx)
    {
        auto it = loop.find(loopIdx);
        if (it != loop.end())
        {
            it->second->deactivateAll();
        }
        else
        {
            g_log->printf(1, "%s() called on non-existant loop %i\n", __FUNCTION__, loopIdx);
        }
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
    /** our csound object */
    CsoundThreaded csound;
    /** our note sources */
    Music music;

    MYFLT secs_per_tick;
    MYFLT ticks_per_period;
    MYFLT tick_adjustment; //the default time increment in thread_fn
    MYFLT tick_total;

    /** the upsampling ratio from csound */
    int csound_frame_rate;
    long csound_period_size;

    log_t* ll;

    TamTamSound(log_t* ll, const char* orc, int framerate)
        : csound(),
          music(),
          ticks_per_period(0.0),
          tick_adjustment(0.0),
          tick_total(0.0),
          csound_frame_rate(framerate), //must agree with the orchestra file
          ll(ll)
    {
        auto argv = std::array<const char*, 4>{
            "csound",
            "-m0",
            "-+rtaudio=alsa",
            orc};

        ll->printf(1, "loading csound orchestra file %s\n", orc);
        int result = csound.Compile(argv.size(), (const char**) argv.data());
        if (result)
        {
            ll->printf("ERROR: csoundCompile of orchestra %s failed with code %i\n", orc, result);
        }
        csound_period_size = csound.GetOutputBufferSize();
        csound_period_size /= 2; /* channels */
        setTickDuration(0.05);
    }
    ~TamTamSound()
    {
        ll->printf(2, "TamTamSound destroyed\n");
    }
    bool good()
    {
        return true;
    }

    // TODO: Merge music.step logic into a custom thread.
    uintptr_t thread_fn()
    {
        tick_total = 0.0f;
        //while (PERF_STATUS == CONTINUE)
        {
            // if (csoundPerformBuffer(csound)) break;
            if (tick_adjustment > -ticks_per_period)
            {
                MYFLT tick_inc = ticks_per_period + tick_adjustment;
                // music.step(tick_inc, secs_per_tick, csound);
                tick_adjustment = 0.0;
                tick_total += tick_inc;
            }
            else
            {
                tick_adjustment += ticks_per_period;
            }
        }

        ll->printf(2, "INFO: performance thread returning 0\n");
        return 0;
    }
    static uintptr_t csThread(void* clientData)
    {
        return ((TamTamSound*) clientData)->thread_fn();
    }
    int start(int)
    {
        if (csound.IsPlaying())
        {
            ll->printf("INFO(%s:%i) skipping duplicate request to launch a thread\n", __FILE__, __LINE__);
            return 1;
        }
        csound.PerformAndReset();
        return 0;
    }
    int stop()
    {
        if (!csound.IsPlaying())
        {
            return 1;
        }
        csound.Stop();
        csound.Join();
        return 0;
    }

    /** pass an array event straight through to csound.  only works if perf. thread is running */
    void scoreEvent(char type, MYFLT* p, int np)
    {
        if (!csound.IsPlaying())
        {
            if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping %s\n", __FUNCTION__);
            return;
        }
        if (_debug && (VERBOSE > 2))
        {
            fprintf(_debug, "INFO: scoreEvent %c ", type);
            for (int i = 0; i < np; ++i) fprintf(_debug, "%lf ", p[i]);
            fprintf(_debug, "\n");
        }
        csound.ScoreEvent(type, p, np);
    }
    /** pass a string event straight through to csound.  only works if perf. thread is running */
    void inputMessage(const char* msg)
    {
        if (!csound.IsPlaying())
        {
            if (_debug && (VERBOSE > 1)) fprintf(_debug, "skipping %s\n", __FUNCTION__);
            return;
        }
        if (_debug && (VERBOSE > 3)) fprintf(_debug, "%s\n", msg);
        csound.InputMessage(msg);
    }
    /** pass a setChannel command through to csound. only works if perf. thread is running */
    void setChannel(const char* name, MYFLT vol)
    {
        csound.SetChannel(name, vol);
    }

    /** adjust the global tick value by this much */
    void adjustTick(MYFLT dtick)
    {
        tick_adjustment += dtick;
    }
    void setTickDuration(MYFLT d)
    {
        secs_per_tick = d;
        ticks_per_period = csound_period_size / (secs_per_tick * csound_frame_rate);
        ll->printf(3, "INFO: duration %lf := ticks_per_period %lf\n", secs_per_tick, ticks_per_period);
    }
    MYFLT getTickf()
    {
        return tick_total + tick_adjustment;
    }
};

static void cleanup(void)
{
    if (g_tt)
    {
        delete g_tt;
        g_tt = nullptr;
    }
}

#define DECL(s) static PyObject* s(PyObject* self, PyObject* args)
#define RetNone         \
    Py_INCREF(Py_None); \
    return Py_None;

//call once at end
DECL(sc_destroy)
{
    if (!PyArg_ParseTuple(args, ""))
    {
        return nullptr;
    }
    if (g_tt)
    {
        delete g_tt;
        g_tt = nullptr;
        if (_debug) fclose(_debug);
    }
    RetNone;
}
//call once at startup, should return 0
DECL(sc_initialize) //(char * csd)
{
    char* str;
    char* log_file;
    int framerate;
    if (!PyArg_ParseTuple(args, "ssii", &str, &log_file, &VERBOSE, &framerate))
    {
        return nullptr;
    }
    if (log_file[0])
    {
        _debug = fopen(log_file, "w");
        if (_debug == nullptr)
        {
            fprintf(stderr, "WARNING: fopen(%s) failed, logging to stderr\n", log_file);
            _debug = stderr;
        }
    }
    else
    {
        _debug = nullptr;
        fprintf(stderr, "Logging disabled on purpose\n");
    }
    g_log = new log_t(_debug, VERBOSE);
    g_tt = new TamTamSound(g_log, str, framerate);
    g_music = &g_tt->music;
    atexit(&cleanup);
    if (g_tt->good())
        return Py_BuildValue("i", 0);
    else
        return Py_BuildValue("i", -1);
}
//compile the score, connect to device, start a sound rendering thread
DECL(sc_start)
{
    int ppb;
    if (!PyArg_ParseTuple(args, "i", &ppb))
    {
        return nullptr;
    }
    return Py_BuildValue("i", g_tt->start(ppb));
}
//stop csound rendering thread, disconnect from sound device, clear tables.
DECL(sc_stop)
{
    if (!PyArg_ParseTuple(args, ""))
    {
        return nullptr;
    }
    return Py_BuildValue("i", g_tt->stop());
}
DECL(sc_scoreEvent) //(char type, farray param)
{
    char ev_type;
    PyObject* o;
    if (!PyArg_ParseTuple(args, "cO", &ev_type, &o))
    {
        return nullptr;
    }
    if (o->ob_type && o->ob_type->tp_as_buffer && (1 == o->ob_type->tp_as_buffer->bf_getsegcount(o, nullptr)))
    {
        if (o->ob_type->tp_as_buffer->bf_getreadbuffer)
        {
            void* ptr;
            size_t len;
            len = o->ob_type->tp_as_buffer->bf_getreadbuffer(o, 0, &ptr);
            MYFLT* fptr = (MYFLT*) ptr;
            size_t flen = len / sizeof(MYFLT);
            g_tt->scoreEvent(ev_type, fptr, flen);

            Py_INCREF(Py_None);
            return Py_None;
        }
        else
        {
            assert(!"asdf");
        }
    }
    assert(!"not reached");
    return nullptr;
}
DECL(sc_inputMessage) //(const char *msg)
{
    char* msg;
    if (!PyArg_ParseTuple(args, "s", &msg))
    {
        return nullptr;
    }
    g_tt->inputMessage(msg);
    RetNone;
}
DECL(sc_setChannel) //(string name, float value)
{
    const char* str;
    float v;
    if (!PyArg_ParseTuple(args, "sf", &str, &v))
    {
        return nullptr;
    }
    g_tt->setChannel(str, v);
    Py_INCREF(Py_None);
    return Py_None;
}
DECL(sc_getTickf) // () -> float
{
    if (!PyArg_ParseTuple(args, ""))
    {
        return nullptr;
    }
    return Py_BuildValue("f", g_tt->getTickf());
}
DECL(sc_adjustTick) // (MYFLT ntick)
{
    float spt;
    if (!PyArg_ParseTuple(args, "f", &spt))
    {
        return nullptr;
    }
    g_tt->adjustTick(spt);
    RetNone;
}
DECL(sc_setTickDuration) // (MYFLT secs_per_tick)
{
    float spt;
    if (!PyArg_ParseTuple(args, "f", &spt))
    {
        return nullptr;
    }
    g_tt->setTickDuration(spt);
    RetNone;
}
DECL(sc_loop_new) // () -> int
{
    if (!PyArg_ParseTuple(args, "")) return nullptr;
    return Py_BuildValue("i", g_music->alloc());
}
DECL(sc_loop_delete) // (int loopIdx)
{
    int loopIdx;
    if (!PyArg_ParseTuple(args, "i", &loopIdx)) return nullptr;
    g_music->destroy(loopIdx);
    RetNone;
}
DECL(sc_loop_getTickf) // (int loopIdx) -> float
{
    int idx;
    if (!PyArg_ParseTuple(args, "i", &idx))
    {
        return nullptr;
    }
    return Py_BuildValue("f", g_music->getTickf(idx));
}
DECL(sc_loop_setNumTicks) //(int loopIdx, int nticks)
{
    int loopIdx;
    int nticks;
    if (!PyArg_ParseTuple(args, "ii", &loopIdx, &nticks)) return nullptr;
    g_music->setNumTicks(loopIdx, nticks);
    RetNone;
}
DECL(sc_loop_setTickf) // (int loopIdx, float pos)
{
    int loopIdx;
    MYFLT pos;
    if (!PyArg_ParseTuple(args, "if", &loopIdx, &pos)) return nullptr;
    g_music->setTickf(loopIdx, pos);
    RetNone;
}
DECL(sc_loop_addScoreEvent) // (int loopIdx, int id, int duration_in_ticks, char type, farray param)
{
    int loopIdx, qid, inticks, active;
    char ev_type;
    PyObject* o;
    if (!PyArg_ParseTuple(args, "iiiicO", &loopIdx, &qid, &inticks, &active, &ev_type, &o)) return nullptr;

    if (o->ob_type && o->ob_type->tp_as_buffer && (1 == o->ob_type->tp_as_buffer->bf_getsegcount(o, nullptr)))
    {
        if (o->ob_type->tp_as_buffer->bf_getreadbuffer)
        {
            void* ptr;
            size_t len;
            len = o->ob_type->tp_as_buffer->bf_getreadbuffer(o, 0, &ptr);
            MYFLT* fptr = (MYFLT*) ptr;
            size_t flen = len / sizeof(MYFLT);

            g_music->addEvent(loopIdx, qid, ev_type, fptr, flen, inticks, active);

            RetNone;
        }
        else
        {
            assert(!"asdf");
        }
    }
    assert(!"not reached");
    return nullptr;
}
DECL(sc_loop_delScoreEvent) // (int loopIdx, int id)
{
    int loopIdx, id;
    if (!PyArg_ParseTuple(args, "ii", &loopIdx, &id))
    {
        return nullptr;
    }
    g_music->delEvent(loopIdx, id);
    RetNone;
}
DECL(sc_loop_updateEvent) // (int loopIdx, int id, int paramIdx, float paramVal, int activate_cmd))
{
    int loopIdx, eventId;
    int idx;
    float val;
    int cmd;
    if (!PyArg_ParseTuple(args, "iiifi", &loopIdx, &eventId, &idx, &val, &cmd)) return nullptr;
    g_music->updateEvent(loopIdx, eventId, idx, val, cmd);
    RetNone;
}
DECL(sc_loop_deactivate_all) // (int id)
{
    int loopIdx;
    if (!PyArg_ParseTuple(args, "i", &loopIdx)) return nullptr;
    g_music->deactivateAll(loopIdx);
    RetNone;
}
DECL(sc_loop_playing) // (int loopIdx, int tf)
{
    int loopIdx, tf;
    if (!PyArg_ParseTuple(args, "ii", &loopIdx, &tf)) return nullptr;
    g_music->playing(loopIdx, tf);
    RetNone;
}

#define MDECL(s)                                                      \
    {                                                                 \
        "" #s, s, METH_VARARGS, "documentation of " #s "... nothing!" \
    }
static PyMethodDef SpamMethods[] = {
    MDECL(sc_destroy),
    MDECL(sc_initialize),
    MDECL(sc_start),
    MDECL(sc_stop),

    MDECL(sc_setChannel),
    MDECL(sc_inputMessage),
    MDECL(sc_scoreEvent),

    MDECL(sc_getTickf),
    MDECL(sc_adjustTick),
    MDECL(sc_setTickDuration),

    MDECL(sc_loop_new),
    MDECL(sc_loop_delete),
    MDECL(sc_loop_getTickf),
    MDECL(sc_loop_setTickf),
    MDECL(sc_loop_setNumTicks),
    MDECL(sc_loop_delScoreEvent),
    MDECL(sc_loop_addScoreEvent),
    MDECL(sc_loop_updateEvent),
    MDECL(sc_loop_deactivate_all),
    MDECL(sc_loop_playing),
    {nullptr, nullptr, 0, nullptr} /*end of list */
};

PyMODINIT_FUNC
initaclient(void)
{
    (void) Py_InitModule("aclient", SpamMethods);
}
