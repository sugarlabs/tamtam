CC=gcc

CXXFLAGS+=-g -Wall -Werror  -fPIC -I/home/james/cvs/sugar-jhbuild/build/include #-O3 -finline
LDFLAGS+= -L/home/james/cvs/sugar-jhbuild/build/lib -L/usr/local/lib -lpython2.5 -lcsound -lasound

all : aclient.so

aclient.so : aclient.cpp
	g++ $(CXXFLAGS) $(PYTHON) -shared -o $@ $< $(LDFLAGS)

clean :
	rm aclient.so

