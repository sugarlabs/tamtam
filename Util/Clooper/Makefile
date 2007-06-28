CC=gcc

CXXFLAGS+=-g -Wall -Werror  -fPIC -O3 -finline
LDFLAGS+=  -lasound 

LDFLAGS+=  -L/usr/local/lib -lcsound

CPPFLAGS+=-I/home/james/cvs/sugar-jhbuild/build/include/python2.5
LDFLAGS+=-L/home/james/cvs/sugar-jhbuild/build/lib 

CPPFLAGS+=-I/usr/include/python2.4
LDFlAGS+=-lpython2.4

all : aclient.so

aclient.so : aclient.cpp audio.cpp
	g++ $(CPPFLAGS) $(CXXFLAGS) -shared -o $@ $< $(LDFLAGS)

clean :
	rm aclient.so

