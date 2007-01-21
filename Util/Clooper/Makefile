CC=gcc

CFLAGS+=-g -Wall -Werror --std=c99   -fPIC

PYTHON=/usr/include/python2.4

all : _ttest.so cmd_csound

%.o: %.c %.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

%.o: %.c
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

clean : 
	rm -f *.o _ttest.so

ttest_wrap.c: ttest.i
	swig -python ttest.i

ttest_wrap.o: ttest_wrap.c
	gcc -fPIC -I$(PYTHON) -o $@ -c $<

cmd_csound: cmd_csound.cpp
	g++ -o $@ $^ -lcsound

_ttest.so : ttest_wrap.o ttest.o
	gcc -shared -o $@ $^ 
