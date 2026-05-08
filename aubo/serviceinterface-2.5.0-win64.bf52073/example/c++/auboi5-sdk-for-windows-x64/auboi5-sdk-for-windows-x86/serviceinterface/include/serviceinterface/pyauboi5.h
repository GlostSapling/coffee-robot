#ifndef PYAUBOI5_H
#define PYAUBOI5_H
#include "math.h"
#ifdef PYTHON_VERSION_3
#if defined(__WIN32__) || defined(WIN32)
#include <python3.7.win32/Python.h>
#else
#include <python3.5m/Python.h>
#endif
#else
#if defined(__WIN32__) || defined(WIN32)
#include <python2.7.win32/Python.h>
#else
#include <python2.7/Python.h>
#endif
#endif

#ifdef __cplusplus
extern "C"
{
#endif

#ifdef PYTHON_VERSION_3
    void PyInit_libpyauboi5();
#else
PyMODINIT_FUNC initlibpyauboi5();
#endif

#ifdef __cplusplus
}
#endif

#endif // PYAUBOI5_H
