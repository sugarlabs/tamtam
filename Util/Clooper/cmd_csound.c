
#include <stdio.h>
#include "csound.hpp"

int main( int argc, char ** argv)
{
    CSOUND * csound = csoundCreate(0);
    csoundInitialize(&argc, &argv, 0);

    int rval = csoundCompile(csound, argc, argv);

    if (!rval)
    {
        while (csoundPerformKsmps(csound) == 0) 
            ;
    }
    csoundDestroy(csound);
    return rval;
}
