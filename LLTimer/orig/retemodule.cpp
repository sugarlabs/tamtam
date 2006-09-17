/*
 *   This file is part of Rete, a neural network simulator.
 * 
 *   Rete is free software; you can redistribute it and/or modify
 *   it under the terms of the GNU General Public License as published by
 *   the Free Software Foundation; either version 2 of the License, or
 *   (at your option) any later version.
 *
 *   Rete is distributed in the hope that it will be useful,
 *   but WITHOUT ANY WARRANTY; without even the implied warranty of
 *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *   GNU General Public License for more details.
 *
 *   You should have received a copy of the GNU General Public License
 *   along with Rete; if not, write to the Free Software
 *   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 *   or visit http://www.fsf.org/copyleft/gpl.html.
 * 
 *   (C) 2000, 2001, 2002 Douglas Eck (doug@idsia.ch) -- initial implementation
 * 
*/


//#define PY_ARRAY_UNIQUE_SYMBOL boogaBooga


#include "Python.h"
#include "Numeric/arrayobject.h"
#include "librete/Rete.h"
#include "librete/Factories.h"
static int reteInitialized=0;
static int callbackInitialized=0;
static NetworkInterface * net;
static Group * groupData;
static Group * groupNet;
static PyObject * ReteError;
static PyObject * pyCbFunction;
static PyObject * arglist = Py_BuildValue("()");
static PyObject * result;
extern "C" 
{


  static PyObject *  rete_clear(PyObject * self, PyObject * args) {
    char *argStr;
    int sts=0;
    if (!PyArg_ParseTuple(args, "", &argStr))
      return NULL;

    if (reteInitialized==1) {
      cout << "Deleting groups and network" << endl;
      delete groupNet;
      delete groupData;
      delete net;
    }
    reteInitialized=0;
    return Py_BuildValue("i", sts);
  }


  static int do_callback() {
    int retval=1;
    if (callbackInitialized==0) {
      //cout << "No callback set" << endl;
      return 1;
    }

    result=PyEval_CallObject(pyCbFunction, arglist);
    if (result == NULL)
      return 1; /* Pass error back */

    if (PyInt_Check(result)) {
      retval=PyInt_AsLong(result);
    } else {
      cout << "Error in do_callback: return value not an int" << endl;
    }
    Py_DECREF(result);
    return retval;
  }    

  static PyObject *  rete_set_callback(PyObject * self, PyObject * args) {
    int sts=0;
    if (!PyArg_ParseTuple(args, "O:set_callback", &pyCbFunction))
      return NULL;
    if (!PyCallable_Check(pyCbFunction)) {
      PyErr_SetString(PyExc_TypeError, "parameter must be callable");
      return NULL;
    }
    Py_XINCREF(pyCbFunction);         /* Add a reference to new callback */
    callbackInitialized=1;
    return Py_BuildValue("i", sts);
  }

  static PyObject *  rete_init(PyObject * self, PyObject * args) {
    char * gNetName;
    char * gDataName;
    int sts=0;
    if (!PyArg_ParseTuple(args, "ss", &gNetName,&gDataName))
      return NULL;


    if (reteInitialized==1) {
      delete groupNet;
      delete groupData;
      delete net;
    }

    groupNet=new GroupNC(gNetName,"netGroup",1);
    groupData=new GroupNC(gDataName,"dataGroup",1);
    net = makeNet(groupNet,groupData);
    //set the callback
    net->setCallback((int (*)(void)) do_callback);
    reteInitialized=1;
    return Py_BuildValue("i", sts);
  }

  


  static PyObject *  rete_learn(PyObject * self, PyObject * args) {
    int * dims=new int[16];
    int numDims=0;
    char *argStr;
    if (!PyArg_ParseTuple(args, "", &argStr))
      return NULL;
    groupNet=net->learn();
    int dataType=0;//we ignore this
    //char * data=net->getData("maxErrorsTest",numDims,dims,dataType);
    char * data=net->getData("errorByEpoch",numDims,dims,dataType);

    int numElems=1;
    for (int i=0;i<numDims;i++) {
      numElems*=dims[i];
    }

    PyArrayObject * pArr=NULL;
    pArr=(PyArrayObject *)PyArray_FromDims(numDims,dims,PyArray_DOUBLE);
    memcpy(pArr->data,(double *)data,numElems*sizeof(double));

    return PyArray_Return(pArr);
    //do not! delete netGroup. It stayes open
    //return Py_BuildValue("d", ((double *)data)[0]);
  }

  static PyObject *  rete_predict_small(PyObject * self, PyObject * args) {
    int idx;
    int predType;     
    int testOrTrain;  //train=0, test=1
    int sts=0;
    if (!PyArg_ParseTuple(args, "iii", &idx, &predType,&testOrTrain))
      return NULL;
    net->predictSmall(idx,predType,testOrTrain);
    return Py_BuildValue("i", sts);
  }


  static PyObject *  rete_predict_small_store(PyObject * self, PyObject * args) {
    int sts=0;
    net->predictSmallStore();//stores data
    return Py_BuildValue("i", sts);
  }

  static PyObject *  rete_predict(PyObject * self, PyObject * args) {
    int idx;
    int predType;     
    int testOrTrain;  //train=0, test=1
    int sts=0;
    if (!PyArg_ParseTuple(args, "iii", &idx, &predType,&testOrTrain))
      return NULL;
    int makeSmall=0;
    net->predict(idx,predType,testOrTrain,makeSmall);
    //groupNet=net->predict();
    //delete groupNet ; //delete predGroup. It gets recreated / reopened each time
    return Py_BuildValue("i", sts);
  }

  static PyObject *  rete_predict_freely(PyObject * self, PyObject * args) {
    char *argStr;
    int sts=0;
    if (!PyArg_ParseTuple(args, "", &argStr))
      return NULL;
    //groupNet=net->predictFreely();
    net->predictFreely();
    //cout << "About to NOT delete group" << endl;
    //delete groupNet;  //delete predGroup. It gets recreated /reopened each time
    //cout << "deleting group" << endl;
    return Py_BuildValue("i", sts);
  }

  static PyObject *  rete_check_error(PyObject * self, PyObject * args) {
    char *argStr;
    int sts=0;
    if (!PyArg_ParseTuple(args, "", &argStr))
            return NULL;
    groupNet=net->checkError();
    return Py_BuildValue("i", sts);
  }

  static PyObject *  rete_get_data(PyObject * self, PyObject * args) {
    int dataType;
    char * data;
    char *argStr;
    if (!PyArg_ParseTuple(args, "s", &argStr))
      return NULL;
    int * dims=new int[16];
    int numDims=0;
    int numElems=1;
    data=net->getData(argStr,numDims,dims,dataType);
    for (int i=0;i<numDims;i++) {
      numElems*=dims[i];
    }

    PyArrayObject * pArr=NULL;
    if (dataType==RETE_GETDATA_DOUBLE) {
      pArr=(PyArrayObject *)PyArray_FromDims(numDims,dims,PyArray_DOUBLE);
      memcpy(pArr->data,(double *)data,numElems*sizeof(double));
    } else if (dataType==RETE_GETDATA_INT) {
      pArr=(PyArrayObject *)PyArray_FromDims(numDims,dims,PyArray_INT);
      memcpy(pArr->data,(int *)data,numElems*sizeof(int));
    }

    return PyArray_Return(pArr);
  }
  
  //static PyObject *  rete_get_data(PyObject * self, PyObject * args) {
  //  double * data;
  // char *argStr;
  // if (!PyArg_ParseTuple(args, "s", &argStr))
  //   return NULL;
  // int * dims=new int[16];
  // int numDims=0;
  // int numElems=1;
  // data=net->getData(argStr,numDims,dims);
  // for (int i=0;i<numDims;i++) {
  //   numElems*=dims[i];
  // }
  // PyArrayObject * pArr;
  // pArr=(PyArrayObject *)PyArray_FromDims(numDims,dims,PyArray_DOUBLE);
  // memcpy(pArr->data,data,numElems*sizeof(double));
  // return PyArray_Return(pArr);
  //}

  
}  



static PyMethodDef ReteMethods[] = {
  {"set_callback",  rete_set_callback, METH_VARARGS},
  {"learn",  rete_learn, METH_VARARGS},
  {"predict",  rete_predict, METH_VARARGS},
  {"predict_small",  rete_predict_small, METH_VARARGS},
  {"predict_small_store",  rete_predict_small_store, METH_VARARGS},
  {"predict_freely",  rete_predict_freely, METH_VARARGS},
  {"check_error",  rete_check_error, METH_VARARGS},
  {"init",  rete_init, METH_VARARGS},
  {"clear",  rete_clear, METH_VARARGS},
  {"get_data",  rete_get_data, METH_VARARGS},
  {NULL,      NULL}        /* Sentinel */
};


extern "C" 
{
  void  initrete() {
    PyObject *m, *d;
    m = Py_InitModule("rete", ReteMethods);
    d = PyModule_GetDict(m);
    ReteError = PyErr_NewException("rete.error", NULL, NULL);
    PyDict_SetItemString(d, "error", ReteError);
    import_array();
  }
}

