#!/bin/sh
rm -rf /usr/share/activities/TamTamEdit.activity
rm -rf /usr/share/activities/TamTamJam.activity
rm -rf /usr/share/activities/TamTamSynthlab.activity

ln -s /home/olpc/tamtam/TamTamEdit.activity /usr/share/activities/TamTamEdit.activity
ln -s /home/olpc/tamtam/TamTamJam.activity /usr/share/activities/TamTamJam.activity
ln -s /home/olpc/tamtam/TamTamSynthLab.activity /usr/share/activities/TamTamSynthLab.activity
