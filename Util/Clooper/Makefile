CC=gcc

CFLAGS+=-g -Wall -Werror  -fPIC -O3 -finline

PYTHON=/usr/include/python2.4

all : sclient.so

sclient.so : SoundClient.cpp
	g++ $(CFLAGS) -shared -o $@ $< -lpython2.4 -lcsound

clean :
	rm sclient.so

