CC=gcc

CFLAGS+=-g -Wall -Werror  -fPIC #-O3 -finline

PYTHON=/usr/include/python2.4

all : sclient.so aclient.so

sclient.so : SoundClient.cpp
	g++ $(CFLAGS) -shared -o $@ $< -lpython2.4 -lcsound

aclient.so : aclient.cpp
	g++ $(CFLAGS) -shared -o $@ $< -lpython2.4 -lcsound -lasound

clean :
	rm sclient.so

