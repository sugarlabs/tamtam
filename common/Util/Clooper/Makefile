CC=gcc

CXXFLAGS = $(shell python-config --cflags) \
		   -Wall -Werror -fPIC -O2 -finline 
LDFLAGS+=  $(python-config --libs) \
		   -lasound -lcsound

all : aclient.so

aclient.so : aclient.cpp audio.cpp
	g++ $(CXXFLAGS) -shared -o $@ $< $(LDFLAGS)

clean :
	rm aclient.so

