#!/bin/sh
rm -R /usr/share/activities/TamTam.activity
rm -R /home/olpc/.sugar/default/tamtam
python setup.py install /usr
rm TamTam-*.xo
