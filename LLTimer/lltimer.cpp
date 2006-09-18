#include "Python.h"
#include "Numeric/arrayobject.h"

#include <pthread.h>
#include <signal.h>

static int lltimerState=0;
static int callbackSet=0;
static unsigned long lltimerMSecs=1000;
static PyObject * pyCbFunction;
static PyObject * arglist = Py_BuildValue("()");
static PyObject * LltimerError;
static pthread_t thread;

 

extern "C" 
{

  //adapted from csound5 code (Vercoe et.al)
  static void millisleep(size_t milliseconds)  {
    struct timespec ts;
    register size_t n, s;
    
    s = milliseconds / (size_t) 1000;
    n = milliseconds - (s * (size_t) 1000);
    n = (size_t) ((int) n * 1000000);
    ts.tv_sec = (time_t) s;
    ts.tv_nsec = (long) n;
    while (nanosleep(&ts, &ts) != 0)
      ;
  }

  //return a timestamp in msecs
  //this is a millisecond timestamp. 
  static timeval startTime;
  static int startTimeInit=0;
  static unsigned long timestamp()  {
    if (startTimeInit==0) {
      gettimeofday(&startTime,NULL);
      startTimeInit=1;
      return 0;
    } 
    timeval currTime;
    gettimeofday(&currTime,NULL);
    return (unsigned long)((currTime.tv_sec - startTime.tv_sec)*1000 + (currTime.tv_usec - startTime.tv_usec)/1000) ;
  }

  //this is a millisecond delta timestamp
  static timeval lastTime;
  static int startDTimeInit=0;
  static unsigned long dtimestamp()  {
    if (startDTimeInit==0) {
      gettimeofday(&lastTime,NULL);
      startDTimeInit=1;
      return 0;
    } 
    timeval currTime;
    gettimeofday(&currTime,NULL);
    unsigned long retval= (unsigned long)((currTime.tv_sec - lastTime.tv_sec)*1000 + (currTime.tv_usec - lastTime.tv_usec)/1000) ;
    lastTime.tv_sec=currTime.tv_sec;
    lastTime.tv_usec=currTime.tv_usec;
    return retval;
  }




  void * periodicTimer(void * ignore) {
    if (callbackSet==0) {
      printf("No callback set!\n");
    } else {
      //try to update the priority of scheduler
      struct sched_param param;
      param.sched_priority = 50;   // Is this the best number?
      int sresult = sched_setscheduler( 0, SCHED_RR, &param);
      printf("Reult for setscheduler %i\n",sresult);
 
     // Check we have done what we hoped.
      int sched = sched_getscheduler(0);
      switch (sched) {
      case SCHED_RR:
	printf( " RR scheduler loaded \n" );   // running as root I now get this.
	break;
      case SCHED_FIFO:
	printf( " FIFO scheudler loaded\n" );
	break;
      default:
	printf( " priority =  %d \n",sched );
      }
      
      
      //now loop on our callback
      unsigned long starttime=timestamp();
      unsigned long nexttime=starttime+lltimerMSecs;
      while (lltimerState==1) {
	PyEval_CallObject(pyCbFunction, arglist);
	unsigned long sleeptime = nexttime-timestamp();
	if (sleeptime>0) {
	  millisleep(sleeptime);
	} else {
	  printf("LLTIMER: Cannot keep up. Slowing timer from %li to %li\n",lltimerMSecs,lltimerMSecs*2);
	  lltimerMSecs*=2;
	}
	nexttime+=lltimerMSecs;
      }
    }
    return NULL;
  }    





  //creates and starts timer. 
  static PyObject *  lltimer_timeout_add(PyObject * self, PyObject * args) {
    int msecs=1000;
 
   //parse args to be sure it was called as lltimer.start(msecs)
    if (!PyArg_ParseTuple(args, "iO:timeout_add", &msecs,&pyCbFunction)) {
      printf("Error in LLTimer.start. Syntax: lltimer.timeout_add(msecs,callback)\n");
      return NULL;
    }

    lltimerMSecs=(unsigned long) msecs; 

    if (!PyCallable_Check(pyCbFunction)) {
      PyErr_SetString(PyExc_TypeError, "Callback function must be callable");
      return NULL;
    }
    Py_XINCREF(pyCbFunction);         /* Add a reference to new callback */
    callbackSet=1;

    if (lltimerState==0) {
      //create and start the timer (Thanks to Gary Scavone @ McGill Univ. and his RtAudio for help on this!)
      pthread_attr_t attr;
      pthread_attr_init(&attr);
      //pthread_attr_setdetachstate(&attr, PTHREAD_CREATE_JOINABLE);
      pthread_attr_setschedpolicy(&attr, SCHED_RR);
      int err = pthread_create(&thread, &attr, periodicTimer, NULL);
      //pthread_attr_destroy(&attr);
      if (err) {
	printf("Error initializing pthread\n");
	lltimerState=0;
      } else {
	printf("PThread initialized\n");
	lltimerState=1;
      }
    }	else {
      printf("Timer already started\n");
    }
    
    return Py_BuildValue("i", lltimerState);
  }



  static PyObject *  lltimer_stop(PyObject * self, PyObject * args) {
    char *argStr;
    if (!PyArg_ParseTuple(args, "", &argStr)) {
      printf("Error in LLTimer stop. Syntax: stop()\n");
      return NULL;
    }
    lltimerState=0;
    return Py_BuildValue("i", 0);
  }


}  



static PyMethodDef LltimerMethods[] = {
  {"stop",  lltimer_stop, METH_VARARGS},
  {"timeout_add",  lltimer_timeout_add, METH_VARARGS},
  {NULL,      NULL}        /* Sentinel */
};


extern "C" 
{
  void  initlltimer() {
    PyObject *m, *d;
    m = Py_InitModule("lltimer", LltimerMethods);
    d = PyModule_GetDict(m);
    LltimerError = PyErr_NewException("lltimer.error", NULL, NULL);
    PyDict_SetItemString(d, "error", LltimerError);
    import_array();
  }
}

