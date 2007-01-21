
#include <stdio.h>
#include <csound/csound.hpp>

#include <pthread.h>
#include <stdio.h>
#include <time.h>
#include <unistd.h>
#include <sys/time.h>

struct TamTamSound
{
    void * ThreadID;
    CSOUND * csound;
    enum {CONTINUE, STOP} PERF_STATUS;
    int playnote;

    TamTamSound(char * orc)
        : playnote(0)
    {
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
            PERF_STATUS = CONTINUE;
            ThreadID = csoundCreateThread(csThread, (void*)this);
        }
        else
        {
            fprintf(stderr, "ERROR: csoundCompile() returned %i\n", result);
            csoundDestroy(csound);
            csound = NULL;
            ThreadID = NULL;
        }
    }
    ~TamTamSound()
    {
        if (csound)
        {
            PERF_STATUS = STOP;
            uintptr_t rval = csoundJoinThread(ThreadID);
            if (1) fprintf(stderr, "INFO: thread returned %zu\n", rval);
            csoundDestroy(csound);
        }
    }
    static double pytime(const struct timeval * tv)
    {
        return (double) tv->tv_sec + (double) tv->tv_usec / 1000000.0;
    }
    uintptr_t thread_fn()
    {
        struct timeval tv;
        double t_prev, t_this;
        double m = 0.0;

        int loops = 0;

        while ( (csoundPerformKsmps(csound) == 0) 
                && (PERF_STATUS == CONTINUE))
        {
            gettimeofday(&tv, 0);
            double t_this = pytime(&tv);
            if (loops)
            {
                if (m < t_this - t_prev)
                {
                    m = t_this - t_prev;
                    fprintf(stderr, "maximum lag %lf\n", m);
                }
            }
            ++loops;
            t_prev = t_this;
            if (playnote)
            {
                play_note(playnote);
                playnote = 0;
            }
        }
        csoundDestroy(csound);
        return 1;
    }
    static uintptr_t csThread(void *clientData)
    {
        return ((TamTamSound*)clientData)->thread_fn();
    }

    void load_instrument(int table, const char * fname)
    {
        if (!csound)
        {
            fprintf(stderr, "ERROR: TamTamSound::%s() csound not loaded\n", __FUNCTION__);
            return;
        }
        char str[512];
        sprintf(str, "f%d 0 0 -1 \"%s\" 0 0 0", table, fname);
        if (1) fprintf(stdout, "%s\n", str);
        csoundInputMessage(csound, str);
    }
    void play_note(int table)
    {
        if (!csound)
        {
            fprintf(stderr, "ERROR: TamTamSound::%s() csound not loaded\n", __FUNCTION__);
            return;
        }
        MYFLT p[16];
        p[0] = 0.0;
        p[1] = 5003.1;
        p[2] = 0.0;
        p[3] = 0.5;
        p[4] = 1.0;
        p[5] = 0.0;
        p[6] = 0.8;
        p[7] = 0.5;
        p[8] = (MYFLT) table;
        p[9] = 0.002;
        p[10] = 0.05;
        p[11] = 0.0;
        p[12] = 1000.0;
        p[13] = 0.0;
        p[14] = 0.0;
        p[15] = 0.0;
        csoundScoreEvent(csound, 'i', p+1, 15);

    }
    void setMasterVolume(MYFLT vol)
    {
        MYFLT *p;
        if (!(csoundGetChannelPtr(csound, &p, "masterVolume", CSOUND_CONTROL_CHANNEL | CSOUND_INPUT_CHANNEL)))
            *p = (MYFLT) vol;
        else
        {
            fprintf(stderr, "ERROR: failed to set master volume\n");
        }
    }

    bool good()
    {
        return csound != NULL;
    }
};

int main( int argc, char ** argv)
{
    int userInput = 200;
    TamTamSound * tt = new TamTamSound(argv[1]);
    tt->setMasterVolume(30.0);

    while ((userInput != 0) && (tt->good()))
    {
        fprintf(stderr, "Enter a pitch\n");
        scanf("%i", &userInput);
        tt->load_instrument(5083, "/home/olpc/tamtam/Resources/Sounds/sitar");
        scanf("%i", &userInput);
        tt->playnote = (5083);
    }

    delete tt;
    return 0;
}
