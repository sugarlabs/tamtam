activitydir = $(datadir)/sugar/activities/tamtam
activity_PYTHON =	\
	__init__.py	\
	TamTam.py

EXTRA_DIST = tamtam.activity \
	     _csnd.so

SUBDIRS = Player \
	  Resources 

install-data-local:
	sugar-setup-activity $(srcdir)/tamtam.activity
