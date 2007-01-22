CC=gcc

CFLAGS+=-g -Wall -Werror  -fPIC

PYTHON=/usr/include/python2.4

all : _SClient.so cmd_csound

%.o: %.c %.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

%.o: %.c
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

%.o: %.cpp %.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

clean : 
	rm -f *.o _ttest.so

cmd_csound: cmd_csound.cpp SoundClient.o
	g++ -o $@ $^ -lcsound

SoundClient_wrap.c: SoundClient.i SoundClient.h
	swig -python $<

SoundClient_wrap.o: SoundClient_wrap.c
	gcc -fPIC -I$(PYTHON) -o $@ -c $<

_SClient.so : SoundClient_wrap.o SoundClient.o
	g++ -shared -o $@ $^ -lcsound

ttest_wrap.c: ttest.i
	swig -python ttest.i

ttest_wrap.o: ttest_wrap.c
	gcc -fPIC -I$(PYTHON) -o $@ -c $<

_ttest.so : ttest_wrap.o ttest.o
	gcc -shared -o $@ $^ 


