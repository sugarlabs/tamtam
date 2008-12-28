# non-XO installl

pythondir = $(shell python -c "from distutils import sysconfig; print sysconfig.get_python_lib()")

TamTamEdit TamTamJam TamTamMini TamTamSynthLab:
	sed -i '/Resources/d; /Clooper/d' $@.activity/MANIFEST
	cd $@.activity && python setup.py build
	cd $@.activity && python setup.py install --prefix=$(DESTDIR)/usr

all clean:
	$(MAKE) -C common/Util/Clooper $@

install:
	install -Dm 0644 common/Util/Clooper/aclient.so $(DESTDIR)/$(pythondir)/tamtam/aclient.so
	touch $(DESTDIR)/$(pythondir)/tamtam/__init__.py
	cd common/Resources && find -type f ! -name '*.py' -exec install -Dm 0644 {} $(DESTDIR)/usr/share/tamtam/{} \;
