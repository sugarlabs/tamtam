
include ../../make.osrules

COMPILER =
ifeq (CYGWIN,$(findstring CYGWIN,$(OS_ARCH)))
	COMPILER = --compiler=mingw32
endif

PYHOME = --home=$(SHAREDIR)/$(ARCH)



default: 
	python setup.py build $(COMPILER) install $(PYHOME) 

clean:
	rm -rf build





