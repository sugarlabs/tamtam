/*
 *  Latency test program
 *
 *     Author: Jaroslav Kysela <perex@suse.cz>
 *
 *  This small demo program can be used for measuring latency between
 *  capture and playback. This latency is measured from driver (diff when
 *  playback and capture was started). Scheduler is set to SCHED_RR.
 *
 *
 *   This program is free software; you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation; either version 2 of the License, or
 *   (at your option) any later version.
 *
 *   This program is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with this program; if not, write to the Free Software
 *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 USA
 *
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sched.h>
#include <errno.h>
#include <getopt.h>
#include <sys/time.h>
#include <math.h>

#include <string>
#include <alsa/asoundlib.h>

#define ERROR_HERE ll->printf("ERROR_HERE: %s %i\n", __FILE__, __LINE__);

struct SystemStuff
{
    log_t * ll;

    snd_pcm_t *phandle, *chandle;
    snd_pcm_uframes_t period_size;
    unsigned int      rate;

    float * bonusbuf;
    unsigned bonuspos;

    SystemStuff(log_t * ll) : ll(ll), phandle(NULL), chandle(NULL), period_size(0), rate(0), bonusbuf( NULL )
    {
        bonusbuf = new float[16000 * 2];
        bonuspos = 0;
    }
    ~SystemStuff()
    {
        delete[] bonusbuf;
        if (phandle) close(0);
    }

    void setscheduler(void)
    {
        struct sched_param sched_param;

        if (sched_getparam(0, &sched_param) < 0) {
                ll->printf( "Scheduler getparam failed...\n");
                return;
        }
        sched_param.sched_priority = sched_get_priority_max(SCHED_RR);
        if (!sched_setscheduler(0, SCHED_RR, &sched_param)) {
            ll->printf( "Scheduler set to Round Robin with priority %i...\n", sched_param.sched_priority);
            return;
        }
        ll->printf( "!!!Scheduler set to Round Robin with priority %i FAILED!!!\n", sched_param.sched_priority);
    }

    int open(unsigned int rate0, int upsample_max, snd_pcm_uframes_t period0, unsigned int p_per_buff)
    {
        snd_pcm_hw_params_t *hw;

        if (phandle)
        {
            ll->printf( "ERROR: open called twice! First close the sound device\n");
            return -1;
        }

        if ( 0 > snd_pcm_open(&phandle, "default", SND_PCM_STREAM_PLAYBACK, 0)) { ERROR_HERE; return -1; }
        if ( 0 > snd_pcm_open(&chandle, "default", SND_PCM_STREAM_CAPTURE, 0)) { ERROR_HERE; return -1; }
        if ( 0 > snd_pcm_hw_params_malloc(&hw))                                 { ERROR_HERE; snd_pcm_close(phandle); phandle = NULL; return -1; }

        //now we can be a bit flexible with the buffer size and the sample-rate...

        int upsample;
        for (upsample = 1; upsample < upsample_max; ++upsample)
        {
            rate = rate0 * upsample;

            if ( 0 > snd_pcm_hw_params_any(phandle, hw))                               { ERROR_HERE; goto open_error;}

            //first do the compulsory steps... interleaved float, 2 channel
            if ( 0 > snd_pcm_hw_params_set_rate_resample(phandle, hw, 0))              { ERROR_HERE; goto open_error;}
            if ( 0 > snd_pcm_hw_params_test_access(phandle, hw, SND_PCM_ACCESS_RW_INTERLEAVED)){ ERROR_HERE; goto open_error;}
            if ( 0 > snd_pcm_hw_params_set_access(phandle, hw, SND_PCM_ACCESS_RW_INTERLEAVED)){ ERROR_HERE; goto open_error;}
            if ( 0 > snd_pcm_hw_params_test_format(phandle, hw, SND_PCM_FORMAT_FLOAT)) { ERROR_HERE; goto open_error;}
            if ( 0 > snd_pcm_hw_params_set_format(phandle, hw, SND_PCM_FORMAT_FLOAT))  { ERROR_HERE; goto open_error;}
            if ( 0 > snd_pcm_hw_params_set_channels(phandle, hw, 2))                   { ERROR_HERE; goto open_error;}

            if ( snd_pcm_hw_params_test_rate(phandle, hw, rate, 0)) 
            {
                ll->printf("test_rate failed( %i\n", rate);
                continue;
            }
            else
            {
                ll->printf(1, "success! setting rate :  %i\n", rate);
                if (0 > snd_pcm_hw_params_set_rate(phandle, hw, rate, 0))        { ERROR_HERE; goto open_error;}

                snd_pcm_uframes_t minb=0, maxb= 0;
                int mind=0, maxd=0;
                snd_pcm_hw_params_get_period_size_min(hw, &minb,&mind);
                snd_pcm_hw_params_get_period_size_max(hw, &maxb,&maxd);
                ll->printf(2, "FYI: period size range is [%li/%i,%li/%i]\n", minb,mind, maxb, maxd);

                assert(mind == 0); //rate_resample 0 makes this true right?
                assert(maxd == 0); //rate_resample 0 makes this true right?

                if (period0 < minb) 
                {
                    ll->printf(1, "requested period size (%li) < min (%li), adjusting to min\n", period_size, minb);
                    period_size = minb;
                }
                else if (period0 > maxb) 
                {
                    ll->printf(2, "requested period size (%li) < max (%li), adjusting to min\n", period_size, maxb);
                    period_size = maxb;
                }
                else
                {
                    period_size = period0;
                }

                ll->printf(1, "testing period size :  %li\n", period_size);
                if ( 0 > snd_pcm_hw_params_test_period_size(phandle, hw, period_size, 0)){ ERROR_HERE; goto open_error;}


                ll->printf(1, "setting period size :  %li\n", period_size);
                if ( 0 > snd_pcm_hw_params_set_period_size(phandle, hw, period_size, 0)){ ERROR_HERE; goto open_error;}
                
                ll->printf(1, "setting buffer size :  %i * %li = %li\n", p_per_buff, period_size, p_per_buff * period_size);
                if ( 0 > snd_pcm_hw_params_set_buffer_size(phandle, hw, p_per_buff*period_size)) { ERROR_HERE; goto open_error;}

                break;
            }
        }

        if (upsample_max == upsample) { ERROR_HERE; goto open_error; }

        if (0 > snd_pcm_hw_params(phandle, hw)) { ERROR_HERE; goto open_error; }
        if (0 > snd_pcm_hw_params(chandle, hw)) { ERROR_HERE; goto open_error; }

        snd_pcm_hw_params_free (hw);
        return 0;

open_error:
        snd_pcm_hw_params_free (hw);
        snd_pcm_close(phandle);
        phandle = NULL;
        return -1;
    }
    void close(int drain = 0)
    {
        if (!phandle) 
        {
            ll->printf(0, "WARNING: attempt to close already-closed pcm\n");
            return;
        }
        ll->printf(1, "INFO: closing phandle device\n");
        if (drain) snd_pcm_drain(phandle);
        snd_pcm_close(phandle);
        snd_pcm_close(chandle);
        phandle = NULL;
        chandle = NULL;
    }
    void prepare()
    {
        if (!phandle)
        {
            ll->printf(0, "ERROR: attempt to prepare a closed pcm\n");
            return;
        }
        if (0 > snd_pcm_prepare(phandle)) { ERROR_HERE; }
    }
    int writebuf(snd_pcm_uframes_t frame_count, float * frame_data)
    {
        if (!phandle)
        {
            ll->printf(0, "ERROR: attempt to write a closed phandle\n");
            return -1;
        }
        int err;
        err = snd_pcm_writei (phandle, frame_data, frame_count );
        if (err == (signed)frame_count) return 0; //success

        assert(err < 0);

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
        ll->printf(1,  "WARNING: write failed (%s)\tstate = %s\ttime=%lf\n", snd_strerror (err), msg, pytime(NULL));
        if (0 > snd_pcm_recover(phandle, err, 0)) { ERROR_HERE; return err;}
        if (0 > snd_pcm_prepare(phandle))         { ERROR_HERE; return err;}
        return 1; //warning
    }
    int readbuf(snd_pcm_uframes_t frame_count, float * frame_data)
    {
        int tries=0;
        int err=1;
        while (err && (tries<2))
        {
            ++tries;
            err = snd_pcm_readi (chandle, frame_data, frame_count );
            if (err < 0)
            {
                const char * msg = NULL;
                snd_pcm_state_t state = snd_pcm_state(chandle);
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
                ll->printf(1,  "WARNING: read failed (%s)\tstate = %s\ttime=%lf\n", snd_strerror (err), msg, pytime(NULL));
                if (0 > snd_pcm_recover(chandle, err, 0)) { ERROR_HERE; return err;}
                if (0 > snd_pcm_prepare(chandle))         { ERROR_HERE; return err;}
            }
        }
        if (0)
        {
            float a = 0.0;
            for (unsigned i = 0; i < frame_count; ++i)
            {
                a = a + frame_data[i] * frame_data[i];
            }
            fprintf(stderr, "%lf %i\n", a, err);
        }
        return (err == (signed)frame_count) ? 0 : err;
    }
};
#undef ERROR_HERE

struct AlsaStuff
{
    bool good_to_go;
    std::string pdevice, cdevice; 
    snd_pcm_format_t format;
    int rate;
    int channels;
    int buffer_size;
    int period_size;
    snd_output_t *output;
    snd_pcm_t *phandle, *chandle;
    log_t *ll;
    int frame_bytes;
    int allow_resample;
    int streams_linked;

    snd_pcm_hw_params_t *pt_params, *ct_params;	/* templates with rate, format and channels */
    snd_pcm_hw_params_t *p_params, *c_params;
    snd_pcm_sw_params_t *p_swparams, *c_swparams;

    AlsaStuff( const char * pdev, const char * cdev, snd_pcm_format_t fmt, int chnl, int r0, int p0, int upsample_max, log_t * ll)
        : good_to_go(false), 
        pdevice(pdev), 
        cdevice(cdev),
        format(fmt),
        rate(0), 
        channels(chnl),
        buffer_size(0),
        period_size(0),
        phandle(NULL), chandle(NULL),
        ll(ll),
        frame_bytes((snd_pcm_format_width(format) / 8) * channels),
        allow_resample(0)
    {
	int err;
	snd_pcm_uframes_t p_size, c_size, p_psize, c_psize;
	unsigned int p_time, c_time;

	snd_pcm_hw_params_alloca(&p_params);
	snd_pcm_hw_params_alloca(&c_params);
	snd_pcm_hw_params_alloca(&pt_params);
	snd_pcm_hw_params_alloca(&ct_params);
	snd_pcm_sw_params_alloca(&p_swparams);
	snd_pcm_sw_params_alloca(&c_swparams);


        if ((err = snd_output_stdio_attach(&output, ll->_file, 0)) < 0) {
            ll->printf("Output failed: %s\n", snd_strerror(err));
            return;
        }

        setscheduler();

        if ((err = snd_pcm_open(&phandle, pdevice.c_str(), SND_PCM_STREAM_PLAYBACK, 0 )) < 0) {
            ll->printf("Playback open error: %s\n", snd_strerror(err));
            return;
        }
        if ((err = snd_pcm_open(&chandle, cdevice.c_str(), SND_PCM_STREAM_CAPTURE, 0 )) < 0) {
            ll->printf("Record open error: %s\n", snd_strerror(err));
            return;
        }

        int upsample=0;
        while(upsample < upsample_max)
        {
            ++upsample;

            rate += r0;
            period_size += p0;

            // set stream params
            if ((err = setparams_stream(phandle, pt_params, "playback")) < 0) {
                ll->printf( "Unable to set parameters for playback stream: %s\n", snd_strerror(err));
                continue;
            }
            if ((err = setparams_stream(chandle, ct_params, "capture")) < 0) {
                ll->printf("Unable to set parameters for playback stream: %s\n", snd_strerror(err));
                continue;
            }

            // set buffer params
            
            if ((err = setparams_bufsize(phandle, p_params, pt_params, period_size, "playback")) < 0) {
                    printf("Unable to set sw parameters for playback stream: %s\n", snd_strerror(err));
                    continue;
            }
            if ((err = setparams_bufsize(chandle, c_params, ct_params, period_size, "capture")) < 0) {
                    printf("Unable to set sw parameters for playback stream: %s\n", snd_strerror(err));
                    continue;
            }

            snd_pcm_hw_params_get_period_size(p_params, &p_psize, NULL);
            if (p_psize < (unsigned int)period_size) continue;

            snd_pcm_hw_params_get_period_size(c_params, &c_psize, NULL);
            if (c_psize < (unsigned int)period_size) continue;

            snd_pcm_hw_params_get_period_time(p_params, &p_time, NULL);
            snd_pcm_hw_params_get_period_time(c_params, &c_time, NULL);
            if (p_time != c_time) continue;

            snd_pcm_hw_params_get_buffer_size(p_params, &p_size);
            if (p_psize * 2 < p_size) continue;

            snd_pcm_hw_params_get_buffer_size(c_params, &c_size);
            if (c_psize * 2 < c_size) continue;

            if ((err = setparams_set(phandle, p_params, p_swparams, "playback")) < 0) {
                    printf("Unable to set sw parameters for playback stream: %s\n", snd_strerror(err));
                    continue;
            }
            if ((err = setparams_set(chandle, c_params, c_swparams, "capture")) < 0) {
                    printf("Unable to set sw parameters for playback stream: %s\n", snd_strerror(err));
                    continue;
            }
            break;
        }

        if (upsample == upsample_max) return;

        ll->printf("Preparing audio devices\n");
	if ((err = snd_pcm_prepare(phandle)) < 0) {
            printf("Prepare playback error: %s\n", snd_strerror(err));
            return;
	}
	if ((err = snd_pcm_prepare(chandle)) < 0) {
            printf("Prepare capture error: %s\n", snd_strerror(err));
            return;
	}
        good_to_go = true;
	snd_pcm_dump(phandle, output);
	snd_pcm_dump(chandle, output);
	char * silence = (char*)malloc(period_size * frame_bytes);
        if (snd_pcm_format_set_silence(format, silence, period_size*channels) < 0) {
            ll->printf( "silence error\n");
        }
        if (writebuf(silence) < 0) {
            ll->printf( "write error\n");
            good_to_go=false;
        }
        if (writebuf(silence) < 0) {
            ll->printf( "write error\n");
            good_to_go=false;
        }
        free(silence);
        ll->printf("Starting audio devices\n");
        if ((err = snd_pcm_start(chandle)) < 0) {
            ll->printf( "Go capture error: %s\n", snd_strerror(err));
            good_to_go=false;
            return;
        }
        if ((err = snd_pcm_start(phandle)) < 0) {
            ll->printf( "Go playback error: %s\n", snd_strerror(err));
            good_to_go=false;
            return;
        }
    }
    ~AlsaStuff()
    {
        snd_pcm_drop(chandle);
        snd_pcm_drain(phandle);
        snd_pcm_hw_free(phandle);
        snd_pcm_hw_free(chandle);
        snd_pcm_close(phandle);
        snd_pcm_close(chandle);
    }

    void setscheduler(void)
    {
        struct sched_param sched_param;

        if (sched_getparam(0, &sched_param) < 0) {
                ll->printf( "Scheduler getparam failed...\n");
                return;
        }
        sched_param.sched_priority = sched_get_priority_max(SCHED_RR);
        if (!sched_setscheduler(0, SCHED_RR, &sched_param)) {
            ll->printf( "Scheduler set to Round Robin with priority %i...\n", sched_param.sched_priority);
            return;
        }
        ll->printf( "!!!Scheduler set to Round Robin with priority %i FAILED!!!\n", sched_param.sched_priority);
    }
    long readbuf(char *buf)
    {
        return 0;
        if (!good_to_go) return -1;
        long frames = period_size;
        while( frames )
        {
            ll->printf( "reading %li\n", frames);
            long r = snd_pcm_readi(chandle, buf, frames);
            if (r < 0)
            {
                ll->printf( "error in snd_pcm_readi(): %s\n", snd_strerror(r));
                return r;
            }
            buf += r * frame_bytes;
            frames -= r;
        }
        return 0;
    }
    long writebuf(const char *buf)
    {
        long frames = period_size;
        if (!good_to_go) return -1;
        while ( frames ) {
            ll->printf("snd_pcm_writei ! (%li)\n", frames);
            long r = snd_pcm_writei(phandle, buf, frames);
            if (r == frames) break;
            if (r >= 0)
            {
                ll->printf("snd_pcm_writei wrote only some of the frames! (%li)\n", r);
                break;
            }

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
            ll->printf( "WARNING: write failed (%s)\tstate = %s\t\n", snd_strerror (r), msg); 
            if (0 > snd_pcm_recover(phandle, r, 0))   { ll->printf( "fuck\n"); return r;}
            ll->printf( "made it end of recover... looping\n");
            if (0 > snd_pcm_prepare(phandle))         { ll->printf( "fuck\n"); return r;}
            ll->printf( "made it end of writebuf... looping\n");
        }
        return 0;
    }

    int setparams_stream(snd_pcm_t *handle, snd_pcm_hw_params_t *params, const char *id)
    {
            int err;
            unsigned int rrate=rate;

            err = snd_pcm_hw_params_any(handle, params);
            if (err < 0) {
                    printf("Broken configuration for %s PCM: no configurations available: %s\n", snd_strerror(err), id);
                    return err;
            }
            err = snd_pcm_hw_params_set_rate_resample(handle, params, allow_resample);
            if (err < 0) {
                    printf("Resample setup failed for %s (val %i): %s\n", id, allow_resample, snd_strerror(err));
                    return err;
            }
            err = snd_pcm_hw_params_set_access(handle, params, SND_PCM_ACCESS_RW_INTERLEAVED);
            if (err < 0) {
                    printf("Access type not available for %s: %s\n", id, snd_strerror(err));
                    return err;
            }
            err = snd_pcm_hw_params_set_format(handle, params, format);
            if (err < 0) {
                    printf("Sample format not available for %s: %s\n", id, snd_strerror(err));
                    return err;
            }
            err = snd_pcm_hw_params_set_channels(handle, params, channels);
            if (err < 0) {
                    printf("Channels count (%i) not available for %s: %s\n", channels, id, snd_strerror(err));
                    return err;
            }
            err = snd_pcm_hw_params_set_rate_near(handle, params, &rrate, 0);
            if (err < 0) {
                    printf("Rate %iHz not available for %s: %s\n", rate, id, snd_strerror(err));
                    return err;
            }
            if ((int)rrate != rate) {
                    printf("Rate doesn't match (requested %iHz, get %iHz)\n", rate, err);
                    return -EINVAL;
            }
            return 0;
    }

    int setparams_bufsize(snd_pcm_t *handle,
                          snd_pcm_hw_params_t *params,
                          snd_pcm_hw_params_t *tparams,
                          snd_pcm_uframes_t bufsize,
                          const char *id)
    {
        int err;
        snd_pcm_uframes_t periodsize;

        snd_pcm_hw_params_copy(params, tparams);
        periodsize = bufsize * 2;
        err = snd_pcm_hw_params_set_buffer_size_near(handle, params, &periodsize);
        if (err < 0) {
                printf("Unable to set buffer size %li for %s: %s\n", bufsize * 2, id, snd_strerror(err));
                return err;
        }
        if (period_size > 0)
                periodsize = period_size;
        else
                periodsize /= 2;
        err = snd_pcm_hw_params_set_period_size_near(handle, params, &periodsize, 0);
        if (err < 0) {
                printf("Unable to set period size %li for %s: %s\n", periodsize, id, snd_strerror(err));
                return err;
        }
        return 0;
    }

    int setparams_set(snd_pcm_t *handle,
                      snd_pcm_hw_params_t *params,
                      snd_pcm_sw_params_t *swparams,
                      const char *id)
    {
        int err;

        err = snd_pcm_hw_params(handle, params);
        if (err < 0) {
                printf("Unable to set hw params for %s: %s\n", id, snd_strerror(err));
                return err;
        }
        err = snd_pcm_sw_params_current(handle, swparams);
        if (err < 0) {
                printf("Unable to determine current swparams for %s: %s\n", id, snd_strerror(err));
                return err;
        }
        err = snd_pcm_sw_params_set_start_threshold(handle, swparams, 0x7fffffff);
        if (err < 0) {
                printf("Unable to set start threshold mode for %s: %s\n", id, snd_strerror(err));
                return err;
        }
        err = snd_pcm_sw_params_set_xfer_align(handle, swparams, 1);
        if (err < 0) {
                printf("Unable to set transfer align for %s: %s\n", id, snd_strerror(err));
                return err;
        }
        err = snd_pcm_sw_params(handle, swparams);
        if (err < 0) {
                printf("Unable to set sw params for %s: %s\n", id, snd_strerror(err));
                return err;
        }
        return 0;
    }

    void showstat(snd_pcm_t *handle, size_t frames)
    {
        int err;
        snd_pcm_status_t *status;

        snd_pcm_status_alloca(&status);
        if ((err = snd_pcm_status(handle, status)) < 0) {
                printf("Stream status error: %s\n", snd_strerror(err));
                exit(0);
        }
        printf("*** frames = %li ***\n", (long)frames);
        snd_pcm_status_dump(status, output);
        snd_pcm_status_free(status);
    }
};

typedef char frame_t;

struct Upsampler
{
    AlsaStuff * dev;
    int ratio;
    int blocklen;

    frame_t * rbuf;
    frame_t * wbuf;
    frame_t * rptr;
    frame_t * wptr;

    Upsampler( AlsaStuff * dev, int ratio, int blocklen )
        : dev(dev), 
        ratio(ratio), 
        blocklen(blocklen), 
        rbuf( new frame_t[dev->period_size * dev->frame_bytes ]),
        wbuf( new frame_t[dev->period_size * dev->frame_bytes ]),
        rptr(rbuf),
        wptr(wbuf)
    {
    }
    ~Upsampler()
    {
        delete[] rbuf;
        delete[] wbuf;
    }
    //store blocklen * dev->frame_bytes in framebuf
    long readbuf(frame_t * framebuf)
    {
        if ((ratio == 1) && (blocklen == dev->period_size))
        {
        }
        else
        {
        }
        return 0;
    }
    //write blocklen * dev->frame_bytes in framebuf
    long writebuf(const frame_t * __restrict__ framebuf)
    {
        if ((ratio == 1) && (blocklen == dev->period_size))
        {
        }
        else
        {
        }
        return 0;
    }
};


